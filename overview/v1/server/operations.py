"""Read-only operations projection. Sources, freshness and gaps travel with data."""
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import re
import sqlite3
import shlex
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .local_projectors import worklane_data_dir, resolve_roster_path, resolve_daemon_path, engine_open_shift

# Fixed badge vocabulary (STATES_AND_TERMS.md §2, AGENTS_INTENT.md). Never
# invent a badge word outside this map.
BADGE_TEXT = {'working': 'WORKING', 'idle': 'IDLE', 'stale_shift': 'STALE SHIFT',
              'last_run_failed': 'LAST RUN FAILED', 'unknown': 'UNKNOWN',
              'not_configured': 'NOT CONFIGURED', 'off': 'OFF'}
BADGE_SOURCE = {'working': 'engine ledger', 'idle': 'engine ledger', 'stale_shift': 'engine ledger',
                'last_run_failed': 'engine ledger', 'unknown': 'daemon',
                'not_configured': 'roster', 'off': 'roster'}
STATE_ORDER = {'working': 0, 'last_run_failed': 1, 'stale_shift': 2, 'idle': 3,
               'unknown': 4, 'not_configured': 5, 'off': 6}


_LEDGER_TAIL_BYTES = 16384
_OWNER_RE = re.compile(r'(?m)^Owner:\s*(\S+)')
_RELEASE_RE = re.compile(r'(?m)^(?:Released by|Reopened by|Blocked:)')
_DEPENDS_RE = re.compile(r'(?i)depends on[:\s]+#?([A-Za-z][A-Za-z0-9]*-\d+)')
STATUS_WORD = {'backlog': 'Open', 'in_review': 'Parked', 'in_progress': 'Live', 'done': 'Done', 'canceled': 'Canceled'}


def task_comment_index(conn):
    """One pass over a project's comments: last Owner marker and last note per task.

    Returns (owner_by_task, last_note_by_task) keyed by task_id, each a dict
    with the fields a row needs — never a full comment history.
    """
    owner_by_task, last_note_by_task = {}, {}
    try:
        comment_rows = conn.execute('SELECT task_id, body, created_at FROM task_comments ORDER BY created_at, id').fetchall()
    except sqlite3.OperationalError:
        return owner_by_task, last_note_by_task
    for row in comment_rows:
        task_id, body, created_at = row['task_id'], row['body'] or '', row['created_at']
        snippet = body.strip().splitlines()[0] if body.strip() else ''
        last_note_by_task[task_id] = snippet[:160] + ('…' if len(snippet) > 160 else '')
        if _RELEASE_RE.search(body):
            owner_by_task.pop(task_id, None)
            continue
        match = _OWNER_RE.search(body)
        if match:
            owner_by_task[task_id] = {'identity': match.group(1), 'since': created_at}
    return owner_by_task, last_note_by_task


def declared_blockers(description):
    return sorted(set(_DEPENDS_RE.findall(description or '')))


def _split_row(line):
    """Parse one ledger row, never raising on a truncated quoted field."""
    if not line.strip():
        return []
    try:
        return shlex.split(line)
    except ValueError:
        return []


def _ledger_tail_lines(daemon_path, root, identity):
    """Read this identity's ledger tail, dropping a possibly-truncated first line.

    A byte-offset seek can land mid-line, so the first decoded line may be a
    partial row (e.g. cut inside a quoted ``title=`` field). When the seek did
    not start at offset 0 the file is longer than the tail window, so that
    first line is unreliable and is dropped rather than parsed.
    """
    if daemon_path is None or not identity or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in identity):
        return None
    path = daemon_path.resolve().parent / 'ledger' / (identity + '.log')
    try:
        if not path.resolve().is_relative_to(root):
            return None
    except OSError:
        return None
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            offset = max(0, size - _LEDGER_TAIL_BYTES)
            stream.seek(offset)
            data = stream.read()
    except OSError:
        return None
    lines = data.decode('utf-8', errors='replace').splitlines()
    if offset > 0 and lines:
        lines = lines[1:]
    return lines


def last_run(daemon_path, root, identity):
    lines = _ledger_tail_lines(daemon_path, root, identity)
    if lines is None:
        return None
    for line in reversed(lines):
        parts = _split_row(line)
        if len(parts) < 2 or parts[1] not in ('STOP', 'ERROR', 'DONE', 'SKIP'):
            continue
        fields = dict(item.split('=', 1) for item in parts[2:] if '=' in item)
        return {'at': parts[0], 'outcome': parts[1].lower(), 'reason': fields.get('reason') or ('Process exited; verify work outcome.' if parts[1] == 'DONE' else 'No reason reported.')}
    return None


def last_shift_candidates(daemon_path, root, identity):
    """Candidate tickets from the most recent START block, open or closed.

    Unlike ``engine_open_shift`` (which only speaks about an open shift),
    this also answers for a shift that already closed — the candidates a
    just-failed run held are still the ones a "verified" mark checks.
    """
    lines = _ledger_tail_lines(daemon_path, root, identity)
    if lines is None:
        return []
    start_index = None
    for index in range(len(lines) - 1, -1, -1):
        parts = _split_row(lines[index])
        if len(parts) >= 2 and parts[1] == 'START':
            start_index = index
            break
    if start_index is None:
        return []
    candidates = []
    for line in lines[start_index + 1:]:
        parts = _split_row(line)
        if len(parts) < 2 or parts[1] not in ('CANDIDATE',):
            continue
        fields = dict(item.split('=', 1) for item in parts[2:] if '=' in item)
        ticket = fields.get('ticket', '')
        if ticket and ticket not in candidates:
            candidates.append(ticket)
    return candidates


def recovery_attempts(daemon_path, root, identity):
    """Count START rows tagged recovery=1 in this identity's ledger tail."""
    lines = _ledger_tail_lines(daemon_path, root, identity)
    if lines is None:
        return 0
    count = 0
    for line in lines:
        parts = _split_row(line)
        if len(parts) < 2 or parts[1] != 'START':
            continue
        fields = dict(item.split('=', 1) for item in parts[2:] if '=' in item)
        if fields.get('recovery') == '1':
            count += 1
    return count


def _config_argument(command):
    if not isinstance(command, list):
        return None
    for index, item in enumerate(command):
        if item == '--config' and index + 1 < len(command):
            return command[index + 1]
    return None


# Executable basenames this surface recognizes as an AI provider, mapped to
# their display name (AGENTS_INTENT.md provider/model resolution).
_PROVIDER_DISPLAY = {'claude': 'Claude', 'cursor-agent': 'Cursor', 'grok': 'Grok'}


def _executable_name(command):
    if not isinstance(command, list) or not command or not isinstance(command[0], str):
        return None
    return Path(command[0]).name


def _is_python_executable(name):
    return name in ('python', 'python3') or (name or '').startswith('python3.')


def _model_flag_value(value):
    return value if isinstance(value, str) and value and '{' not in value else None


def _model_flag(command):
    """The value of a ``--model``/``-m`` argument, separate or ``=``-joined,
    ignoring an unfilled template."""
    if not isinstance(command, list):
        return None
    for index, item in enumerate(command):
        if not isinstance(item, str):
            continue
        if item in ('--model', '-m') and index + 1 < len(command):
            value = _model_flag_value(command[index + 1])
            if value:
                return value
        for prefix in ('--model=', '-m='):
            if item.startswith(prefix):
                value = _model_flag_value(item[len(prefix):])
                if value:
                    return value
    return None


def _resolved_config_path(config_path, root):
    """The runner config path, resolved against ``root`` when relative, or
    ``None`` when it falls outside the workspace."""
    if not config_path:
        return None
    path = Path(config_path)
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    return resolved if resolved.is_relative_to(root) else None


def resolve_provider_model(row, root, config_cache=None):
    """Provider/model display text, in the order AGENTS_INTENT.md fixes:

    the roster's own ``model``; else the seat's runner config (the actual
    provider command it names, read via the roster command's ``--config``
    path); else the roster command's own executable, with the model left
    blank at that tier. Never returns the literal "Not specified".

    ``config_cache`` is an optional dict shared across one snapshot's rows,
    keyed by resolved config path, so a runner file shared by several seats
    is only read once.
    """
    command = row.get('command')
    roster_model = row.get('model')
    if isinstance(roster_model, str) and roster_model.strip():
        return roster_model.strip()
    resolved_path = _resolved_config_path(_config_argument(command), root)
    if resolved_path is not None:
        if config_cache is not None and resolved_path in config_cache:
            config = config_cache[resolved_path]
        else:
            config = read_json(resolved_path, root)
            if config_cache is not None:
                config_cache[resolved_path] = config
        inner_command = (config or {}).get('command')
        provider = _PROVIDER_DISPLAY.get(_executable_name(inner_command))
        if provider:
            model = _model_flag(inner_command)
            return f'{provider} {model}' if model else provider
    executable = _executable_name(command)
    if _is_python_executable(executable):
        return 'Local job'
    provider = _PROVIDER_DISPLAY.get(executable)
    return provider or 'Provider unknown'


def preserved_reservation(root, command, order_id):
    """A task_runner preparation receipt still exists for the held order.

    Read only the worker's own recovery-config JSON (the ``--config`` path
    already on its roster command) and the reservation directory it names;
    never invents a state_dir or worker name.
    """
    config_path = _config_argument(command)
    if not config_path or not order_id:
        return False
    path = Path(config_path)
    if not path.is_absolute():
        return False
    config = read_json(path, root)
    if not isinstance(config, dict):
        return False
    state_dir = config.get('state_dir')
    worker = config.get('worker')
    if not isinstance(state_dir, str) or not state_dir or not isinstance(worker, str) or not worker:
        return False
    slug = str(order_id)
    if not re.fullmatch(r'[A-Za-z0-9._-]+', slug):
        return False
    receipt = Path(state_dir) / worker / slug / 'preparation.json'
    return read_json(receipt, root) is not None


class _NoRedirect(HTTPRedirectHandler):
    """Refuse to leave the verified origin; a 3xx becomes an HTTPError."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(newurl, code, msg, headers, fp)


def supervisor_snapshot(root):
    """Read GET /api/supervisor on the verified local WorkForce origin.

    Same origin-verification shape as agent_actions.dispatch_agent, but a
    plain read with a 3 s timeout — the one upstream call this surface adds.
    """
    receipt = read_json(root / 'local/workforce/deployment.json', root) or {}
    origin = receipt.get('api_origin', '')
    parsed = urlparse(origin)
    if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1')
            or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment):
        return {'state': 'unavailable', 'detail': 'A verified local WorkForce connection is required.', 'passes': []}
    request = Request(origin.rstrip('/') + '/api/supervisor?limit=3')
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=3) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return {'state': 'unavailable', 'detail': 'WorkForce redirected the supervisor read; refusing to leave the verified origin.', 'passes': []}
        if exc.code == 404:
            return {'state': 'not_configured', 'detail': 'This WorkForce engine does not report supervisor passes.', 'passes': []}
        return {'state': 'unavailable', 'detail': 'WorkForce declined the supervisor read.', 'passes': []}
    except (URLError, TimeoutError, ValueError, OSError):
        return {'state': 'unavailable', 'detail': 'WorkForce is not reachable.', 'passes': []}
    passes = payload.get('passes') if isinstance(payload, dict) else None
    if not isinstance(passes, list):
        return {'state': 'unavailable', 'detail': 'Supervisor endpoint returned an unexpected shape.', 'passes': []}
    return {'state': 'available', 'detail': '', 'passes': passes[:3]}


def read_json(path, root):
    if path is None or not path.resolve().is_relative_to(root):
        return None
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def project_registry(root):
    result = {}
    for path in sorted(root.glob('*/.protocolcity/desk-join.json')):
        row = read_json(path, root)
        if row and isinstance(row.get('slug'), str):
            result[row['slug']] = {'name': str(row.get('display') or row['slug']),
                                   'prefix': str(row.get('prefix') or '').rstrip('-'),
                                   'folder': str(path.parent.parent.relative_to(root)),
                                   'has_instructions': (path.parent.parent/'AGENTS.md').is_file()}
    return result


def age_seconds(value, now):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            return None
        age = (now - stamp).total_seconds()
        return max(0, age) if age >= -30 else None
    except (ValueError, TypeError):
        return None


def operations_snapshot(binder):
    now = datetime.now(timezone.utc)
    try:
        build = version('protocolcity-blueprint')
    except PackageNotFoundError:
        build = 'Source checkout'
    result = {'observed_at': now.isoformat(), 'build': build, 'workspace': None,
              'orders': [], 'projects': [], 'agents': [], 'supervisor': None, 'sources': [], 'truncated': False,
              'events': [], 'work_dates': [], 'excluded_stores': [], 'remote': {'state': 'not_connected', 'message': 'Remote AI execution is not configured. GitHub delivery is reported separately in Activity.'}}
    if binder is None:
        result['sources'].append({'name': 'Workspace', 'state': 'unavailable', 'detail': 'No workspace selected.'})
        return result
    root = Path(binder).resolve()
    result['workspace'] = {'name': root.name, 'path': str(root)}
    registry = project_registry(root)
    data = worklane_data_dir(root)
    if not data.resolve().is_relative_to(root):
        result['sources'].append({'name': 'WorkLane', 'state': 'unavailable', 'detail': 'Store directory is outside this workspace.'})
        paths = []
    else:
        paths = sorted(data.glob('*.db'))
    result['excluded_stores'] = [p.name for p in paths if p.stem not in registry]
    paths = [p for p in paths if p.stem in registry]
    for path in paths:
        project = registry.get(path.stem, {'name': path.stem, 'prefix': '', 'folder': None})
        summary = {'id': path.stem, **project, 'open': 0, 'attention': 0, 'state': 'available'}
        try:
            if not path.resolve().is_relative_to(root):
                raise OSError('external store')
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=.25)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM tasks WHERE status NOT IN ('done','canceled','cancelled') ORDER BY priority, updated_at DESC LIMIT 2001").fetchall()
                count = conn.execute("SELECT count(*) FROM tasks WHERE status NOT IN ('done','canceled','cancelled')").fetchone()[0]
                summary['open'] = count
                result['truncated'] |= count > 2000
                owner_by_task, last_note_by_task = task_comment_index(conn)
                for row in rows[:2000]:
                    item = dict(row)
                    try:
                        labels = json.loads(item.get('labels') or '[]')
                    except (ValueError, TypeError):
                        labels = []
                    labels = labels if isinstance(labels, list) else []
                    workers = [x[7:] for x in labels if isinstance(x, str) and x.startswith('worker:') and x[7:]]
                    routable_workers = [w for w in workers if w != 'you']
                    you_qualifier = any(label in ('you:todo', 'you:remind', 'you:note') for label in labels if isinstance(label, str))
                    from .attention_view import face, face_reason
                    attention_face = face(item, labels, now)
                    attention = bool(attention_face)
                    order_id = item.get('ext_id') or (f"{project['prefix']}-{item['id']}" if project['prefix'] else str(item['id']))
                    from suite.api.calendar import events_from_task
                    for event in events_from_task({**item, 'id':order_id, 'labels':labels, 'product':path.stem}):
                        result['work_dates'].append({**event, 'dtstart':event['dtstart'].isoformat(), 'attention':attention})
                    status = item.get('status')
                    marker = owner_by_task.get(item['id'])
                    parent = next((label[7:] for label in labels if isinstance(label, str) and label.startswith('parent:') and label[7:]), '')
                    result['orders'].append({'id': order_id, 'project': path.stem, 'project_name': project['name'],
                        'title': item.get('title') or order_id, 'status': status,
                        'status_word': STATUS_WORD.get(status, status),
                        'priority': item.get('priority'), 'updated_at': item.get('updated_at'),
                        'attention': attention, 'attention_face': attention_face,
                        'face_reason': face_reason(item, labels, attention_face, now),
                        'gate_until':item.get('gate_until'),
                        'gate_type': item.get('gate_type') or '',
                        'gate_note': item.get('gate_note') or '',
                        'workers': workers,
                        'needs_routing': not routable_workers and not (item.get('gate_type') or '') and not you_qualifier,
                        'owner': ', '.join(routable_workers) or 'Unassigned',
                        'live_with': marker['identity'] if marker and status == 'in_progress' else None,
                        'parked_by': marker['identity'] if marker and status == 'in_review' else None,
                        'since': marker['since'] if marker and status in ('in_progress', 'in_review') else None,
                        'last_note': last_note_by_task.get(item['id']) or '',
                        'parent': parent, 'blockers': declared_blockers(item.get('description')),
                        'ready_for': None})
                    summary['attention'] += int(attention)
        except (OSError, sqlite3.Error):
            summary['state'] = 'unavailable'
        result['projects'].append(summary)
    open_ids = {o['id'] for o in result['orders']}
    for order in result['orders']:
        seat = next((w for w in order['workers'] if w != 'you'), None)
        blocked = any(b in open_ids for b in order['blockers'])
        if seat and order['status'] == 'backlog' and not order['gate_type'] and not blocked:
            order['ready_for'] = seat
    found = {p.stem for p in paths}
    for slug, project in registry.items():
        if slug not in found:
            result['projects'].append({'id': slug, **project, 'open': 0, 'attention': 0, 'state': 'unavailable'})
    failed = [p['name'] for p in result['projects'] if p['state'] != 'available']
    result['sources'].append({'name': 'WorkLane', 'state': 'partial' if failed else ('available' if paths else 'unavailable'),
                             'detail': f"{sum(p['state'] == 'available' for p in result['projects'])} project stores readable" + ('. Unavailable: ' + ', '.join(failed) if failed else '')})
    roster = read_json(resolve_roster_path(root), root)
    daemon = read_json(resolve_daemon_path(root), root)
    tick = (daemon or {}).get('last_tick')
    age = age_seconds(tick, now)
    fresh = age is not None and age <= 120
    result['sources'].append({'name': 'WorkForce roster', 'state': 'available' if isinstance((roster or {}).get('workers'), dict) else 'unavailable',
                             'detail': 'Local agent registry' if roster else 'Registry could not be read.'})
    result['sources'].append({'name': 'WorkForce heartbeat', 'state': 'fresh' if fresh else ('stale' if age is not None else 'unknown'),
                             'detail': 'Last reported activity; not a process health check.', 'last_at': tick})
    workers = (roster or {}).get('workers', {})
    runtime = (daemon or {}).get('workers', {})
    flight = (daemon or {}).get('in_flight', [])
    if not isinstance(runtime, dict): runtime = {}
    if not isinstance(flight, list): flight = []
    daemon_path = resolve_daemon_path(root)
    runner_config_cache = {}
    if isinstance(workers, dict):
        for identity, row in workers.items():
            if not isinstance(row, dict) or identity == 'demo-worker': continue
            shift = engine_open_shift(daemon_path, root, identity, now)
            open_shift = shift is not None and not shift['stale']
            run = last_run(daemon_path, root, identity)
            if not fresh:
                state = 'unknown'
            elif identity in flight or open_shift:
                state = 'working'
            elif shift:
                state = 'stale_shift'
            elif run and run['outcome'] == 'error':
                state = 'last_run_failed'
            else:
                state = 'idle'
            command = row.get('command')
            configured = isinstance(command, list) and bool(command) and command not in (['true'], ['/usr/bin/true'], ['/bin/true'], ['sh','-c','true'], ['bash','-c','true'])
            if not configured: state = 'not_configured'
            if row.get('enabled') is False: state = 'off'
            live = runtime.get(identity, {})
            report = read_json(root / '.blueprint/job-reports' / (identity + '.json'), root) if identity in ('chief-of-staff','health-patrol','workspace-efficiency') else None
            kind = row.get('kind') or 'agent'
            group = 'supervisor' if identity == 'bp-supervisor' else ('seat' if kind == 'lane' else 'job')
            held = next((o for o in result['orders'] if o['status'] == 'in_progress' and identity in o['workers']), None) if group == 'seat' else None
            verified = bool(held and held['id'] in last_shift_candidates(daemon_path, root, identity))
            reservation = bool(held and state == 'last_run_failed' and preserved_reservation(root, command, held['id']))
            if state == 'idle':
                action = 'dispatch'
            elif state == 'stale_shift':
                action = 'inspect'
            elif state == 'last_run_failed':
                action = 'recover' if reservation else 'dispatch'
            else:
                action = None
            agent_row = {'id': identity, 'name': row.get('display') or identity,
                'last_run': run, 'shift': shift,
                'report': {k:report.get(k) for k in ('title','observed_at','state','summary','detail','mode')} if report else None,
                'state': state, 'badge': BADGE_TEXT[state],
                'badge_source': 'daemon' if (state == 'working' and not shift) else BADGE_SOURCE[state],
                'group': group, 'configured':configured, 'configuration': 'Command configured' if configured else 'Placeholder command — no operational work runs', 'kind': kind, 'schedule': row.get('schedule') or 'Not scheduled',
                'next_fire': live.get('next_fire') if isinstance(live, dict) else None,
                'model': resolve_provider_model(row, root, runner_config_cache), 'last_at': tick, 'source': 'Local WorkForce',
                'held': {'id': held['id'], 'project': held['project_name']} if held else None,
                'held_verified': verified, 'recovery_attempts': recovery_attempts(daemon_path, root, identity),
                'preserved_reservation': reservation, 'action': action}
            if group == 'supervisor':
                result['supervisor'] = {**agent_row, 'passes': supervisor_snapshot(root)}
            else:
                result['agents'].append(agent_row)
    result['agents'].sort(key=lambda a: (STATE_ORDER.get(a['state'], 9), a['name']))
    placeholders = [a['name'] for a in result['agents'] if not a['configured']]
    if placeholders:
        result['sources'].append({'name':'Agent/job configuration','state':'partial','detail':'Placeholder commands: ' + ', '.join(placeholders) + '. These jobs do not execute operational work.'})
    calendar_path = root / '.blueprint' / 'calendar.json'
    calendar = read_json(calendar_path, root)
    calendar_valid = calendar is not None and isinstance(calendar.get('events'), list)
    result['sources'].append({'name': 'Calendar', 'state': 'available' if calendar_valid else ('unavailable' if calendar_path.exists() else 'not_configured'),
                             'detail': 'Local calendar events' if calendar_valid else 'No readable local calendar file; agent schedules are shown separately.'})
    if calendar_valid:
        for event in calendar['events']:
            if isinstance(event, dict):
                result['events'].append({key: str(event.get(key) or '') for key in ['title', 'at', 'source', 'state', 'notes']})
    result['orders'].sort(key=lambda x: (not x['attention'], x['priority'] if isinstance(x['priority'], int) else 99, x['project'], x['id']))
    return result
