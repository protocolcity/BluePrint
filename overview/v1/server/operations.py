"""Read-only operations projection. Sources, freshness and gaps travel with data."""
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import shlex
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, parse_qs
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


def _blocker_resolution(blocker_id, open_ids, status_by_id, unavailable_slugs, prefix_to_slug):
    """Return open, clear, or unknown for one declared blocker id."""
    if blocker_id in open_ids:
        return 'open'
    status = status_by_id.get(blocker_id)
    if status is not None:
        return 'clear' if status in ('done', 'canceled', 'cancelled') else 'open'
    prefix = blocker_id.rsplit('-', 1)[0] if '-' in blocker_id else ''
    slug = prefix_to_slug.get(prefix)
    if slug is None or slug in unavailable_slugs:
        return 'unknown'
    return 'unknown'


def blocked_on_state(blockers, open_ids, status_by_id, unavailable_slugs, prefix_to_slug):
    """Three-valued blocker gate: open, unknown, or clear."""
    if not blockers:
        return 'clear', ''
    state = 'clear'
    notes = []
    for blocker_id in blockers:
        resolution = _blocker_resolution(blocker_id, open_ids, status_by_id, unavailable_slugs, prefix_to_slug)
        if resolution == 'open':
            state = 'open'
        elif resolution == 'unknown' and state != 'open':
            state = 'unknown'
            prefix = blocker_id.rsplit('-', 1)[0] if '-' in blocker_id else ''
            slug = prefix_to_slug.get(prefix)
            if slug in unavailable_slugs:
                notes.append(f'dependency unknown: {blocker_id} (store unavailable)')
            else:
                notes.append(f'dependency unknown: {blocker_id}')
    return state, '; '.join(notes)


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
_PROVIDER_DISPLAY = {'claude': 'Claude', 'cursor-agent': 'Cursor', 'grok': 'Grok', 'codex': 'Codex'}


def _executable_name(command):
    if not isinstance(command, list) or not command or not isinstance(command[0], str):
        return None
    return Path(command[0]).name


def _is_python_executable(name):
    return name in ('python', 'python3') or (name or '').startswith('python3.')


_PLACEHOLDER_COMMANDS = (['true'], ['/usr/bin/true'], ['/bin/true'], ['sh', '-c', 'true'], ['bash', '-c', 'true'])


def _seat_command_configured(command):
    """A seat's command names real work, not a no-op placeholder stub."""
    return isinstance(command, list) and bool(command) and command not in _PLACEHOLDER_COMMANDS


def _command_is_template(command):
    """True when a roster command still carries an unfilled ``{placeholder}``
    token (pc-1477 scope addition: a legacy template-shaped seat command like
    ``claude --model {model} -p {prompt_text} ...`` names its provider on the
    bare first token and expects the roster's own fields substituted in at
    dispatch time — it is not yet a resolved, literal invocation)."""
    if not isinstance(command, list):
        return False
    return any(isinstance(item, str) and '{' in item and '}' in item for item in command)


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


def _launcher_config_fallback(command):
    """``<launcher dir>/runner.json`` when a thin launcher names no ``--config``
    (pc-1474 scope addition: pos-cursor-implementer's ``launch.py`` carries no
    ``--config`` argument — the roster command still names the launcher script,
    so the sibling runner file is the seat's own config)."""
    if not isinstance(command, list):
        return None
    for item in command:
        if isinstance(item, str) and Path(item).name == 'launch.py':
            return str(Path(item).parent / 'runner.json')
    return None


def _codex_model_value(item):
    if not isinstance(item, str):
        return None
    match = re.match(r'^model=(.*)$', item)
    if not match:
        return None
    value = match.group(1)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value or None


def _codex_model_flag(command):
    """The value of a Codex ``-c model="..."`` argument (pc-1474 scope
    addition: Codex names its pin through ``-c``, not ``--model``/``-m``)."""
    if not isinstance(command, list):
        return None
    for index, item in enumerate(command):
        if item == '-c' and index + 1 < len(command):
            value = _codex_model_value(command[index + 1])
            if value:
                return value
    return None


def _provider_model_flag(provider, command):
    model = _model_flag(command)
    if model:
        return model
    if provider == 'Codex':
        return _codex_model_flag(command)
    return None


def resolve_provider_model(row, root, config_cache=None):
    """Provider/model display text, in the order AGENTS_INTENT.md fixes:

    the roster's own ``model``, prefixed with the provider name resolved
    from the seat's own command when the pin is a bare token like
    ``claude-sonnet-5`` (pc-1476: a bare first token such as ``claude``
    still names its provider, so the pin alone is never the whole story);
    else the seat's runner config (the actual provider command it names,
    read via the roster command's ``--config`` path, or the sibling
    ``runner.json`` next to a thin launcher script when no ``--config`` is
    named); else the roster command's own executable, with the model left
    blank at that tier. Never returns the literal "Not specified".

    ``config_cache`` is an optional dict shared across one snapshot's rows,
    keyed by resolved config path, so a runner file shared by several seats
    is only read once.

    A template-shaped command (pc-1477 scope addition: unfilled
    ``{placeholder}`` tokens like ``claude --model {model} -p
    {prompt_text}``) skips the bare-model short-circuit so the provider still
    resolves from the command's own bare first token and combines with the
    roster's model.
    """
    command = row.get('command')
    roster_model = row.get('model')
    model = roster_model.strip() if isinstance(roster_model, str) and roster_model.strip() else None
    if model and not _command_is_template(command):
        provider = _seat_executable_provider(row, root, config_cache)
        if provider:
            first_token, _, rest = model.partition(' ')
            if first_token.lower() == provider.lower():
                rest = rest.strip()
                return f'{provider} {rest}' if rest else provider
            return f'{provider} {model}'
        return model
    config_path = _config_argument(command) or _launcher_config_fallback(command)
    resolved_path = _resolved_config_path(config_path, root)
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
            resolved_model = model or _provider_model_flag(provider, inner_command)
            return f'{provider} {resolved_model}' if resolved_model else provider
    executable = _executable_name(command)
    provider = _PROVIDER_DISPLAY.get(executable)
    if provider:
        resolved_model = model or _provider_model_flag(provider, command)
        return f'{provider} {resolved_model}' if resolved_model else provider
    if model:
        return model
    if _is_python_executable(executable):
        return 'Local job'
    return 'Provider unknown'


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


def verified_local_origin(receipt):
    """Return a verified http://127.0.0.1|localhost origin, or None.

    Prefers ``api_origin`` when present (WorkForce receipts). WorkLane
    receipts typically carry ``port`` instead; only a 1–65535 integer is
    accepted, always bound to 127.0.0.1.
    """
    if not isinstance(receipt, dict):
        return None
    origin = receipt.get('api_origin', '')
    if isinstance(origin, str) and origin.strip():
        parsed = urlparse(origin)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1')
                or parsed.username or parsed.password or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment):
            return None
        return origin.rstrip('/')
    port = receipt.get('port')
    if isinstance(port, str) and port.isdigit():
        port = int(port)
    if isinstance(port, int) and 1 <= port <= 65535:
        return 'http://127.0.0.1:%d' % port
    return None


# Canonical WorkLane health-check (README / INSTALL). `/health` is not a
# documented API; an HTTP 404 there is reachable, not a usable capability.
WORKLANE_API_PATH = '/api/admin/products'
_SUPERVISOR_FAILED = frozenset({'failed', 'provider_failed', 'escalated'})


def _read_bounded(stream, limit=65536):
    try:
        try:
            data = stream.read(limit)
        except TypeError:
            data = stream.read()
    except (OSError, ValueError, AttributeError):
        return b''
    if isinstance(data, str):
        data = data.encode('utf-8', errors='replace')
    if not isinstance(data, (bytes, bytearray)):
        return b''
    return bytes(data[:limit])


def _json_object(body):
    if not body:
        return None
    if isinstance(body, bytes):
        try:
            raw = body.decode('utf-8')
        except UnicodeDecodeError:
            return None
    elif isinstance(body, str):
        raw = body
    else:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _worklane_api_usable(body):
    payload = _json_object(body)
    return bool(payload and payload.get('ok') is True and isinstance(payload.get('products'), list))


def _normalize_outcome(value):
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().lower().replace(' ', '_')


def probe_local_http(origin, path):
    """GET ``origin+path`` without following redirects.

    Any HTTP reply means the origin responded (reachable). That is not
    usability; callers must interpret ``status`` and ``body``.
    """
    request = Request(origin.rstrip('/') + path)
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=3) as response:
            status = getattr(response, 'status', None) or getattr(response, 'code', 200)
            return {'ok': True, 'status': status, 'body': _read_bounded(response)}
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return {'ok': False, 'redirect': True, 'status': exc.code}
        return {'ok': True, 'status': exc.code, 'body': _read_bounded(exc)}
    except (URLError, TimeoutError, ValueError, OSError):
        return {'ok': False}


def supervisor_snapshot(root):
    """Read GET /api/supervisor on the verified local WorkForce origin.

    Same origin-verification shape as agent_actions.dispatch_agent, but a
    plain read with a 3 s timeout — the one upstream call this surface adds.
    An HTTP reply proves reachability even when the body is malformed;
    usability still requires a JSON object with a ``passes`` list.
    """
    receipt = read_json(root / 'local/workforce/deployment.json', root) or {}
    origin = verified_local_origin(receipt)
    if not origin:
        return {'state': 'unavailable', 'detail': 'A verified local WorkForce connection is required.',
                'passes': [], 'reachable': False, 'http_status': None, 'probed': False}
    probe = probe_local_http(origin, '/api/supervisor?limit=3')
    if probe.get('redirect'):
        return {'state': 'unavailable', 'detail': 'WorkForce redirected the supervisor read; refusing to leave the verified origin.',
                'passes': [], 'reachable': False, 'http_status': probe.get('status'), 'probed': True}
    if not probe.get('ok'):
        return {'state': 'unavailable', 'detail': 'WorkForce is not reachable.',
                'passes': [], 'reachable': False, 'http_status': None, 'probed': True}
    status = probe.get('status')
    if status == 404:
        return {'state': 'not_configured', 'detail': 'This WorkForce engine does not report supervisor passes.',
                'passes': [], 'reachable': True, 'http_status': 404, 'probed': True}
    if status != 200:
        return {'state': 'unavailable', 'detail': 'WorkForce declined the supervisor read.',
                'passes': [], 'reachable': True, 'http_status': status, 'probed': True}
    payload = _json_object(probe.get('body'))
    passes = payload.get('passes') if isinstance(payload, dict) else None
    if not isinstance(passes, list):
        return {'state': 'unavailable', 'detail': 'Supervisor endpoint returned an unexpected shape.',
                'passes': [], 'reachable': True, 'http_status': status, 'probed': True}
    return {'state': 'available', 'detail': '', 'passes': passes[:3],
            'reachable': True, 'http_status': status, 'probed': True}


def read_json(path, root):
    if path is None or not path.resolve().is_relative_to(root):
        return None
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _engine_record(*, state, source, detail, version=None, observed_at=None,
                   activated_at=None, last_success_at=None, outcome=None,
                   reachable=None, usable=None, http_status=None, next_step=None):
    return {
        'state': state,
        'version': version,
        'source': source,
        'observed_at': observed_at,
        'activated_at': activated_at,
        'last_success_at': last_success_at,
        'outcome': outcome,
        'reachable': reachable,
        'usable': usable,
        'http_status': http_status,
        'detail': detail,
        'next_step': next_step,
    }


def _empty_engine(source, detail, next_step=None, state='unavailable'):
    return _engine_record(state=state, source=source, detail=detail,
                          usable=False, next_step=next_step)


def _engine_receipt(root, relative):
    """Version + activation time from a workspace installation receipt.

    A receipt establishes installed identity, not live daemon health.
    """
    source = Path(relative).as_posix()
    missing_step = 'Install or activate this engine in the selected workspace so a deployment receipt exists.'
    receipt = read_json(root / relative, root)
    if not receipt:
        return _empty_engine(source, 'No installation receipt in this workspace.', missing_step)
    version = receipt.get('version')
    activated = receipt.get('activated_at') if isinstance(receipt.get('activated_at'), str) else None
    if not isinstance(version, str) or not version.strip():
        return _engine_record(
            state='unavailable', source=source, activated_at=activated,
            usable=False, next_step=missing_step,
            detail='Installation receipt is missing a version.')
    return _engine_record(
        state='installed', version=version.strip(), source=source,
        activated_at=activated, usable=True,
        detail='Version ' + version.strip())


def _worklane_reachability(root, now):
    source_file = 'local/worklane/deployment.json'
    receipt = read_json(root / source_file, root)
    if not receipt:
        return _empty_engine(
            source_file, 'No installation receipt in this workspace.',
            'Install or activate WorkLane in the selected workspace so a deployment receipt exists.')
    origin = verified_local_origin(receipt)
    if not origin:
        return _empty_engine(
            source_file, 'A verified local WorkLane connection is required.',
            'Use this workspace installation receipt; do not fall back to another workspace or a default port.')
    source = origin + WORKLANE_API_PATH
    probe = probe_local_http(origin, WORKLANE_API_PATH)
    observed = now.isoformat()
    if probe.get('redirect'):
        return _engine_record(
            state='unavailable', source=source, observed_at=observed,
            reachable=False, usable=False, http_status=probe.get('status'),
            next_step='Confirm the installation receipt origin stays on this machine.',
            detail='WorkLane redirected the products read; refusing to leave the verified origin.')
    if not probe.get('ok'):
        return _engine_record(
            state='unavailable', source=source, observed_at=observed,
            reachable=False, usable=False,
            next_step='Start WorkLane on the verified local origin from the installation receipt.',
            detail='WorkLane API is not reachable.')
    status = probe.get('status')
    usable = status == 200 and _worklane_api_usable(probe.get('body'))
    if usable:
        return _engine_record(
            state='available', source=source, observed_at=observed,
            last_success_at=observed, reachable=True, usable=True,
            http_status=status,
            detail='Reachable · usable' + ((' · HTTP %s' % status) if status else ''))
    return _engine_record(
        state='reachable', source=source, observed_at=observed,
        reachable=True, usable=False, http_status=status,
        next_step='Confirm GET /api/admin/products on the verified origin returns the product list.',
        detail='Reachable · health not verified' + ((' · HTTP %s' % status) if status else ''))


def _supervisor_pass_fields(payload, now):
    source = 'WorkForce /api/supervisor'
    probed = bool(payload.get('probed'))
    observed = now.isoformat() if probed else None
    state = payload.get('state') or 'unavailable'
    reachable = payload.get('reachable')
    http_status = payload.get('http_status')
    if state == 'not_configured':
        return _engine_record(
            state='not_configured', source=source, observed_at=observed,
            reachable=True if reachable is None else reachable, usable=False,
            http_status=http_status,
            detail=payload.get('detail') or 'This WorkForce engine does not report supervisor passes.')
    if state != 'available':
        down = reachable is False or (isinstance(payload.get('detail'), str) and 'not reachable' in payload['detail'].lower())
        return _engine_record(
            state='unavailable', source=source, observed_at=observed,
            reachable=False if down else (True if reachable is None else reachable),
            usable=False, http_status=http_status,
            next_step='Confirm the WorkForce origin in the installation receipt.' if probed or down else None,
            detail=payload.get('detail') or 'Supervisor pass record unavailable.')
    passes = [item for item in (payload.get('passes') or []) if isinstance(item, dict)]
    if not passes:
        return _engine_record(
            state='empty', source=source, observed_at=observed,
            last_success_at=observed, reachable=True, usable=True,
            http_status=http_status,
            detail='No supervisor passes recorded yet.')
    latest = max(passes, key=lambda item: str(item.get('generated_at') or ''))
    generated = latest.get('generated_at') if isinstance(latest.get('generated_at'), str) else None
    outcome = _normalize_outcome(latest.get('pass_outcome'))
    failed = outcome in _SUPERVISOR_FAILED
    detail = (outcome or 'outcome not reported').replace('_', ' ') + ' · last pass ' + (generated or 'time not reported')
    return _engine_record(
        state='failed' if failed else 'available', source=source,
        observed_at=observed, last_success_at=observed, outcome=outcome,
        reachable=True, usable=True, http_status=http_status,
        next_step='Open Agents for the last pass; a readable failed report is evidence, not a green pass.' if failed else None,
        detail=detail)


def _unavailable_engines(detail):
    return {
        'worklane': _empty_engine('local/worklane/deployment.json', detail),
        'workforce': _empty_engine('local/workforce/deployment.json', detail),
        'worklane_api': _empty_engine('local/worklane/deployment.json', detail),
        'supervisor': _empty_engine('WorkForce /api/supervisor', detail),
    }


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


# Standard seat set (AGENT_ADOPTION.md D12) — the four providers, in the
# order the desk lists them, with the host command each is detected by, the
# pin the desk offers on Hire, and a one-line install hint for NOT CONFIGURED.
_PROVIDER_ORDER = ('Claude', 'Cursor', 'Grok', 'Codex')
_PROVIDER_COMMAND = {'Claude': 'claude', 'Cursor': 'cursor-agent', 'Grok': 'grok', 'Codex': 'codex'}
_PROVIDER_PIN = {'Claude': 'claude-sonnet-5', 'Cursor': 'composer-2.5', 'Grok': 'grok-4.6', 'Codex': 'gpt-6-astra'}
# workforce hire's --provider choices (workforce/cli.py) — lowercase adapter
# keys, distinct from the desk's display names above (review finding
# pc-1477: the printed hire command must use these, not "Cursor"/"Codex").
_PROVIDER_ADAPTER_KEY = {'Claude': 'claude', 'Cursor': 'cursor', 'Grok': 'grok', 'Codex': 'codex'}
_PROVIDER_INSTALL_HINT = {
    'Claude': 'not on PATH — install: https://docs.claude.com/en/docs/claude-code',
    'Cursor': 'not on PATH — install: https://cursor.com/cli',
    'Grok': 'not on PATH — install the Grok CLI (`grok`) from your xAI account',
    'Codex': 'not on PATH — install the ChatGPT desktop app (ships '
             '/Applications/ChatGPT.app/Contents/Resources/codex) or the codex CLI',
}
# Codex on this host ships inside the ChatGPT app rather than on PATH
# (AGENT_ADOPTION.md scope addition, pc-1474).
_CODEX_APP_PATH = '/Applications/ChatGPT.app/Contents/Resources/codex'


def _well_known_candidates(command, home):
    candidates = [home / '.local' / 'bin' / command,
                  Path('/opt/homebrew/bin') / command,
                  Path('/usr/local/bin') / command]
    if command == 'grok':
        candidates.insert(1, home / '.grok' / 'bin' / 'grok')
    return candidates


# Roots an executable path must resolve under to count as proof of an
# installed provider (review finding pc-1476): the running user's home,
# the two Homebrew/local prefixes the well-known bins live under, or the
# Codex app bundle. A path outside all four — even one a roster seat names
# directly, or one a well-known bin symlinks to — proves nothing; it is
# not a location this host trusts as an install site.
def _trusted_executable_roots(home_dir):
    try:
        home_dir = home_dir.resolve()
    except OSError:
        pass
    return (home_dir, Path('/opt/homebrew').resolve(), Path('/usr/local').resolve())


def _is_trusted_path(resolved, home_dir):
    codex_app = Path(_CODEX_APP_PATH).resolve()
    if resolved == codex_app or resolved.is_relative_to(codex_app):
        return True
    return any(resolved.is_relative_to(root) for root in _trusted_executable_roots(home_dir))


def _resolved_trusted_file(path, home_dir):
    """``path`` accepted only when it is a file whose target — after
    resolving any symlink — still lies under a trusted install root; a
    symlink pointing outside those locations proves nothing (review
    finding pc-1476)."""
    if not path.is_file():
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return _is_trusted_path(resolved, home_dir)


def _seat_proof(provider, workers, root, config_cache, home_dir):
    """The absolute executable path a roster seat's resolved command names
    for ``provider``, when that path resolves to a file under a trusted
    install root — proof the provider is installed even though its own
    binary sits outside the well-known checked locations (pc-1476). A
    seat naming a path outside the trusted roots proves nothing."""
    if not isinstance(workers, dict):
        return None
    for row in workers.values():
        if not isinstance(row, dict):
            continue
        seat_provider, token = _seat_resolved_executable(row, root, config_cache)
        if seat_provider != provider or not token:
            continue
        path = Path(token)
        if path.is_absolute() and _resolved_trusted_file(path, home_dir):
            return str(path)
    return None


def detect_providers(env=None, app_path_exists=None, home=None, workers=None, root=None,
                      config_cache=None, sources=None):
    """``{display name: executable path or None}`` for the four providers.

    Proof is checked in order: the process ``PATH`` (``env`` overrides
    ``os.environ`` for tests — a fake PATH); a well-known install location
    (``~/.local/bin/<name>``, ``~/.grok/bin/grok``, ``/opt/homebrew/bin/<name>``,
    ``/usr/local/bin/<name>``, or the Codex app path this host ships — ``home``
    overrides ``Path.home()`` for tests); or any roster seat's resolved
    command naming an absolute executable that exists on disk (``workers``
    plus ``root``/``config_cache`` to resolve it). A provider absent from all
    three reads ``None`` — the caller shows NOT CONFIGURED with the install
    hint (AGENT_ADOPTION.md D15). When ``sources`` is a dict it is filled in
    place with ``{display name: 'PATH'|'well-known location'|'seat command'}``
    for each provider found, so the caller can name which proof won.
    """
    search_env = env if env is not None else os.environ
    home_dir = home if home is not None else Path.home()
    found = {}
    for provider, command in _PROVIDER_COMMAND.items():
        path = shutil.which(command, path=search_env.get('PATH'))
        source = 'PATH' if path else None
        if not path:
            for candidate in _well_known_candidates(command, home_dir):
                if _resolved_trusted_file(candidate, home_dir):
                    path, source = str(candidate), 'well-known location'
                    break
        if not path and provider == 'Codex':
            app_present = (Path(_CODEX_APP_PATH).is_file() if app_path_exists is None
                           else app_path_exists)
            if app_present:
                path, source = _CODEX_APP_PATH, 'well-known location'
        if not path:
            seat_path = _seat_proof(provider, workers, root, config_cache, home_dir)
            if seat_path:
                path, source = seat_path, 'seat command'
        found[provider] = path
        if sources is not None:
            sources[provider] = source
    return found


def hire_command(provider, *, project_slug, project_path, prefix, remote=None):
    """The exact ``workforce hire`` command text for one missing seat
    (AGENT_ADOPTION.md D13/D15) — host-run only; BP never writes the roster.

    Canonical shape on this host (WorkForce 0.1.9+consolidation.9, review
    finding pc-1474): ``workforce hire <name> --provider <p> --project <slug>
    --repository <path> --remote <url> --schedule manual --model <pin>``, with
    ``--remote`` only when the project's registration names one. Every
    argument is shell-quoted — a project path or remote can carry spaces or
    shell metacharacters. ``--provider`` prints the hire CLI's lowercase
    adapter key (review finding pc-1477: the display name printed here fails
    the hire CLI's ``choices=("claude", "cursor", "grok", "codex")``).
    """
    name = f'{(prefix or project_slug).rstrip("-")}-{provider.lower()}-implementer'
    parts = ['workforce', 'hire', name, '--provider', _PROVIDER_ADAPTER_KEY[provider],
             '--project', project_slug, '--repository', project_path]
    if remote:
        parts += ['--remote', remote]
    parts += ['--schedule', 'manual', '--model', _PROVIDER_PIN[provider]]
    return shlex.join(parts)


def _project_remote(root, slug):
    """The project's git remote URL from ``.blueprint/connections.json``
    (review finding pc-1474: the Hire command should name the repository the
    hired seat pushes to, when the workspace's registration knows it), or
    ``None`` when the project carries no registered repository."""
    config = read_json(root / '.blueprint/connections.json', root) or {}
    specs = (config.get('github') or {}).get('repositories')
    if not isinstance(specs, list):
        return None
    for spec in specs:
        if isinstance(spec, dict) and spec.get('project') == slug and isinstance(spec.get('repo'), str) \
                and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', spec['repo']):
            return f'https://github.com/{spec["repo"]}'
    return None


def _row_project_slug(row):
    """The project slug a seat's queue is bound to, from its ``queue_url``
    ``product`` parameter, or ``None`` when the queue carries no product
    (AGENT_ADOPTION.md scope addition, pc-1474: every seat's header should
    name its project, not just held seats)."""
    scope = parse_qs(urlparse(str(row.get('queue_url', ''))).query).get('product')
    return scope[0] if scope else None


_PIN_PROVIDER_PREFIXES = (('claude', 'Claude'), ('composer', 'Cursor'), ('cursor', 'Cursor'),
                          ('grok', 'Grok'), ('gpt', 'Codex'), ('codex', 'Codex'))


def _provider_from_pin(pin):
    """The provider family a bare model pin belongs to — ``claude-*`` ->
    Claude, ``composer-*``/``cursor-*`` -> Cursor, ``grok-*`` -> Grok,
    ``gpt-*``/``codex`` -> Codex (review finding pc-1474: a roster ``model``
    of a bare pin like ``claude-sonnet-5`` names no display text, only the
    pin family), or ``None`` when the pin matches no known family."""
    if not isinstance(pin, str):
        return None
    lowered = pin.strip().lower()
    for prefix, provider in _PIN_PROVIDER_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + '-'):
            return provider
    return None


def _seat_resolved_executable(row, root, config_cache):
    """``(provider display name, first command token)`` from the seat's
    actually resolved executable — its own roster command, or the runner
    config it names via ``--config``/the launcher fallback — independent of
    what the roster's ``model`` field says (review finding pc-1474: a bare
    pin in ``model`` should not block resolving the real command). Both are
    ``None`` when no known provider resolves."""
    command = row.get('command')
    provider = _PROVIDER_DISPLAY.get(_executable_name(command))
    if provider:
        token = command[0] if isinstance(command, list) and command and isinstance(command[0], str) else None
        return provider, token
    config_path = _config_argument(command) or _launcher_config_fallback(command)
    resolved_path = _resolved_config_path(config_path, root)
    if resolved_path is None:
        return None, None
    if config_cache is not None and resolved_path in config_cache:
        config = config_cache[resolved_path]
    else:
        config = read_json(resolved_path, root)
        if config_cache is not None:
            config_cache[resolved_path] = config
    inner_command = (config or {}).get('command')
    provider = _PROVIDER_DISPLAY.get(_executable_name(inner_command))
    token = inner_command[0] if provider and isinstance(inner_command, list) and inner_command \
        and isinstance(inner_command[0], str) else None
    return provider, token


def _seat_executable_provider(row, root, config_cache):
    """The provider display name from the seat's actually resolved
    executable (see ``_seat_resolved_executable``)."""
    provider, _token = _seat_resolved_executable(row, root, config_cache)
    return provider


def _seat_executable_status(row, root, config_cache, home_dir=None):
    """The trust status of the seat's resolved absolute executable —
    ``'missing'`` when the path does not exist, ``'untrusted'`` when it
    exists but resolves outside the trusted install roots (neither proves
    nor stages the provider — review finding pc-1476), ``'ok'`` when it
    exists and is trusted, or ``None`` when the seat names no absolute
    executable at all."""
    _provider, token = _seat_resolved_executable(row, root, config_cache)
    if not token:
        return None
    path = Path(token)
    if not path.is_absolute():
        return None
    if not path.is_file():
        return 'missing'
    home_dir = home_dir if home_dir is not None else Path.home()
    try:
        resolved = path.resolve()
    except OSError:
        return 'missing'
    return 'ok' if _is_trusted_path(resolved, home_dir) else 'untrusted'


def _seat_executable_missing(row, root, config_cache):
    """``True`` when the seat's resolved command names an absolute
    executable that neither exists on disk nor resolves to a trusted
    install root (pc-1476: a seat that once proved a provider present
    should not silently keep counting once its binary is gone or is
    proven to sit outside a trusted location)."""
    return _seat_executable_status(row, root, config_cache) in ('missing', 'untrusted')


def _row_is_seat_kind(kind):
    """A lane, or a row with no ``kind`` — the Seats group counts both as a
    seat (review finding pc-1474), only an explicit non-``lane`` kind
    (e.g. ``job``) excludes it."""
    return kind in (None, 'lane')


def _row_is_held(row, kind):
    """Shared held predicate for coverage and the Agents snapshot (review
    finding pc-1477): disabled outright, or a seat-kind row carrying the
    wf-259 generator's held state — an empty ``schedule``. Coverage and the
    Agents snapshot must agree on this so a held seat never reads present in
    one and OFF in the other."""
    return row.get('enabled') is False or (_row_is_seat_kind(kind) and row.get('schedule') == '')


def _seat_model_text(row, root, config_cache):
    """The provider/model display text for one seat's own row — extends
    ``resolve_provider_model`` with the same executable/pin fallbacks
    coverage uses (pc-1479: a seat's own Agents row must never disagree
    with what provider coverage counts it as; both call this one helper
    rather than resolving the provider through separate paths). A pin
    ``resolve_provider_model`` returned bare (unresolved command) gets its
    provider name prefixed when the executable or the pin family resolves
    one; otherwise the bare text is returned unchanged.

    ``None`` from ``resolve_provider_model`` passes through as ``None``
    (review finding, pc-1479 follow-up: an unresolvable seat still yields a
    row with no provider rather than raising). The fallback only applies to
    rows the Seats group counts as seats — a lane, or a row with no
    ``kind`` (``_row_is_seat_kind``); a job row keeps
    ``resolve_provider_model``'s text as is, never gaining a provider
    prefix from the executable or pin heuristics. The pin heuristic itself
    only ever reads the roster's own ``model`` field, never the resolved
    display text, so a provider name appearing inside unrelated command
    text (a path, a module name) is never mistaken for a pin."""
    model_text = resolve_provider_model(row, root, config_cache)
    if model_text is None:
        return None
    if any(model_text == p or model_text.startswith(p + ' ') for p in _PROVIDER_ORDER):
        return model_text
    if not _row_is_seat_kind(row.get('kind')):
        return model_text
    provider = _seat_executable_provider(row, root, config_cache) or _provider_from_pin(row.get('model'))
    if not provider:
        return model_text
    pin = model_text if model_text and model_text != provider else None
    return f'{provider} {pin}' if pin else provider


def _project_seat_providers(workers, project_slug, root, config_cache):
    """``{provider display: 'present'|'held'}`` for one project's implementer
    seats — a seat's ``queue_url`` names its project (AGENT_ADOPTION.md D12:
    one bounded implementation seat per project x provider). A seat with no
    ``kind`` still counts as a seat here, consistent with the Seats group
    (review finding pc-1474); only an explicit non-``lane`` kind excludes it.
    An unarmed ``demo-worker`` paper stub (found.py: planted with no real
    command) still never counts as staffing (OVERVIEW_INTENT.md: demo-worker
    alone is not employment) — but once armed with a real command (pc-1477
    scope addition), it is a seat like any other.
    """
    result = {}
    if not isinstance(workers, dict):
        return result
    for identity, row in workers.items():
        if not isinstance(row, dict):
            continue
        if identity == 'demo-worker' and not _seat_command_configured(row.get('command')):
            continue
        if not _row_is_seat_kind(row.get('kind')):
            continue
        if _row_project_slug(row) != project_slug:
            continue
        model_text = _seat_model_text(row, root, config_cache)
        provider = next((p for p in _PROVIDER_ORDER
                          if model_text == p or (model_text and model_text.startswith(p + ' '))), None)
        if not provider:
            continue
        if _seat_executable_missing(row, root, config_cache):
            continue
        result[provider] = 'held' if _row_is_held(row, row.get('kind')) else 'present'
    return result


def provider_coverage(root, registry, workers, config_cache, host_providers=None, host_provider_sources=None):
    """One coverage row per registered project (AGENT_ADOPTION.md D15):
    present/held providers, missing ones (installed but no seat), and
    providers this host does not have installed at all. Each row's
    ``sources`` names, for every provider, which proof (PATH, well-known
    location, or a seat's own command) established it, or 'not detected'
    when the host has no proof for it at all — the payload always names a
    source for all four providers, not just present/held ones (pc-1476).
    """
    if host_providers is None:
        host_provider_sources = {}
        host_providers = detect_providers(workers=workers, root=root, config_cache=config_cache,
                                           sources=host_provider_sources)
    host_provider_sources = host_provider_sources or {}
    rows = []
    for slug, project in sorted(registry.items(), key=lambda kv: kv[1].get('name') or kv[0]):
        seats = _project_seat_providers(workers, slug, root, config_cache)
        present, held, missing, not_configured = [], [], [], []
        for provider in _PROVIDER_ORDER:
            if not host_providers.get(provider):
                not_configured.append(provider)
                continue
            state = seats.get(provider)
            if state == 'present':
                present.append(provider)
            elif state == 'held':
                held.append(provider)
            else:
                missing.append(provider)
        name = project.get('name') or slug
        staffed = present + [f'{p} OFF' for p in held]
        text = f'{name}: ' + (', '.join(staffed) if staffed else 'none staffed')
        if missing:
            text += f' · missing {", ".join(missing)}'
        if not_configured:
            text += f' · not configured: {", ".join(not_configured)}'
        project_path = str(root / project['folder']) if project.get('folder') else slug
        remote = _project_remote(root, slug)
        rows.append({
            'project': slug, 'name': name, 'present': present, 'held': held,
            'missing': missing, 'not_configured': not_configured, 'text': text,
            'sources': {p: host_provider_sources.get(p) or 'not detected' for p in _PROVIDER_ORDER},
            'install_hints': {p: _PROVIDER_INSTALL_HINT[p] for p in not_configured},
            'hire_commands': {p: hire_command(p, project_slug=slug, project_path=project_path,
                                               prefix=project.get('prefix') or slug, remote=remote)
                               for p in missing},
        })
    return rows


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
              'events': [], 'work_dates': [], 'excluded_stores': [], 'coverage': [],
              'engines': _unavailable_engines('No workspace selected.'),
              'remote': {'state': 'not_connected', 'message': 'Remote AI execution is not configured. GitHub delivery is reported separately in Activity.'}}
    if binder is None:
        result['sources'].append({
            'name': 'Workspace', 'state': 'unavailable', 'detail': 'No workspace selected.',
            'reachable': False, 'usable': False, 'next_step': 'Start BluePrint with a workspace selected.',
            'source': None})
        return result
    root = Path(binder).resolve()
    result['workspace'] = {'name': root.name, 'path': str(root)}
    registry = project_registry(root)
    data = worklane_data_dir(root)
    if not data.resolve().is_relative_to(root):
        result['sources'].append({
            'name': 'WorkLane', 'state': 'unavailable',
            'detail': 'Store directory is outside this workspace.',
            'reachable': False, 'usable': False,
            'next_step': 'Select a workspace whose WorkLane data directory is inside it.',
            'source': 'worklane data directory'})
        paths = []
    else:
        paths = sorted(data.glob('*.db'))
    result['excluded_stores'] = [p.name for p in paths if p.stem not in registry]
    paths = [p for p in paths if p.stem in registry]
    status_by_id = {}
    store_available = {}
    for path in paths:
        project = registry.get(path.stem, {'name': path.stem, 'prefix': '', 'folder': None})
        summary = {'id': path.stem, **project, 'open': 0, 'attention': 0, 'claimed': 0, 'running': 0, 'state': 'available'}
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
                prefix = project.get('prefix') or ''
                for task_row in conn.execute('SELECT id, ext_id, status FROM tasks').fetchall():
                    task_id = task_row['ext_id'] or (f"{prefix}-{task_row['id']}" if prefix else str(task_row['id']))
                    status_by_id[task_id] = task_row['status']
                for row in rows[:2000]:
                    item = dict(row)
                    try:
                        labels = json.loads(item.get('labels') or '[]')
                    except (ValueError, TypeError):
                        labels = []
                    labels = labels if isinstance(labels, list) else []
                    workers = [x[7:] for x in labels if isinstance(x, str) and x.startswith('worker:') and x[7:]]
                    routable_workers = [w for w in workers if w != 'you']
                    has_worker_you = 'you' in workers
                    # worker:you (with or without you:host or persona qualifiers)
                    # is Assignment = You unless a registered seat is also
                    # routed. A human gate with nobody routed is also You
                    # (STATES_AND_TERMS.md §5).
                    assigned_you = (has_worker_you and not routable_workers) or (
                        item.get('gate_type') == 'human' and not routable_workers
                    )
                    gate_expired = False
                    if item.get('gate_type') == 'timer' and item.get('gate_until'):
                        from suite.api.calendar import parse_gate_until
                        due = parse_gate_until(item['gate_until'])
                        gate_expired = due is not None and due <= now
                    from .attention_view import face, face_reason, persona_text
                    attention_face = face(item, labels, now)
                    attention = bool(attention_face)
                    order_id = item.get('ext_id') or (f"{project['prefix']}-{item['id']}" if project['prefix'] else str(item['id']))
                    from suite.api.calendar import events_from_task
                    for event in events_from_task({**item, 'id':order_id, 'labels':labels, 'product':path.stem}):
                        result['work_dates'].append({
                            **event,
                            'dtstart': event['dtstart'].isoformat(),
                            'attention': attention_face == 'decide',
                            'attention_face': attention_face,
                        })
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
                        'gate_expired': gate_expired,
                        'gate_note': item.get('gate_note') or '',
                        'workers': workers,
                        'needs_routing': not routable_workers and not (item.get('gate_type') or '') and not has_worker_you,
                        'blocked_on': 'clear',
                        'blocked_note': '',
                        'persona': persona_text(item, labels),
                        'assigned_you': assigned_you,
                        'owner': 'You' if assigned_you else (', '.join(routable_workers) or 'Unassigned'),
                        'live_with': marker['identity'] if marker and status == 'in_progress' else None,
                        'parked_by': marker['identity'] if marker and status == 'in_review' else None,
                        'since': marker['since'] if marker and status in ('in_progress', 'in_review') else None,
                        'last_note': last_note_by_task.get(item['id']) or '',
                        'parent': parent, 'blockers': declared_blockers(item.get('description')),
                        'ready_for': None})
                    summary['attention'] += int(attention)
                    # A claim (in_progress with a signed Owner marker) is not
                    # execution evidence — a days-old human claim counts here
                    # the same as a fresh agent shift. 'running' below is the
                    # separate, agent-evidence-only signal (pc-1483).
                    summary['claimed'] += int(status == 'in_progress' and marker is not None)
            store_available[path.stem] = True
        except (OSError, sqlite3.Error):
            summary['state'] = 'unavailable'
            store_available[path.stem] = False
        result['projects'].append(summary)
    found = {p.stem for p in paths}
    for slug, project in registry.items():
        if slug not in found:
            result['projects'].append({'id': slug, **project, 'open': 0, 'attention': 0, 'claimed': 0, 'running': 0, 'state': 'unavailable'})
            store_available[slug] = False
    unavailable_slugs = {slug for slug, ok in store_available.items() if not ok}
    prefix_to_slug = {proj['prefix']: slug for slug, proj in registry.items() if proj.get('prefix')}
    open_ids = {o['id'] for o in result['orders']}
    for order in result['orders']:
        seat = next((w for w in order['workers'] if w != 'you'), None)
        blocked_state, blocked_note = blocked_on_state(
            order['blockers'], open_ids, status_by_id, unavailable_slugs, prefix_to_slug)
        order['blocked_on'] = blocked_state
        order['blocked_note'] = blocked_note
        if seat and order['status'] == 'backlog' and not order['gate_type'] and blocked_state == 'clear':
            order['ready_for'] = seat
    failed = [p['name'] for p in result['projects'] if p['state'] != 'available']
    readable = sum(p['state'] == 'available' for p in result['projects'])
    if not paths:
        lane_state, lane_next = 'unavailable', 'Register a project store inside this workspace.'
    elif failed:
        lane_state, lane_next = 'partial', 'Inspect the unavailable stores listed in the detail.'
    else:
        lane_state, lane_next = 'available', None
    result['sources'].append({
        'name': 'WorkLane', 'state': lane_state,
        'detail': f"{readable} project stores readable" + ('. Unavailable: ' + ', '.join(failed) if failed else ''),
        'reachable': True, 'usable': readable > 0, 'next_step': lane_next,
        'source': 'worklane data directory'})
    roster = read_json(resolve_roster_path(root), root)
    daemon = read_json(resolve_daemon_path(root), root)
    tick = (daemon or {}).get('last_tick')
    age = age_seconds(tick, now)
    fresh = age is not None and age <= 120
    roster_ok = isinstance((roster or {}).get('workers'), dict)
    result['sources'].append({
        'name': 'WorkForce roster', 'state': 'available' if roster_ok else 'unavailable',
        'detail': 'Local agent registry' if roster else 'Registry could not be read.',
        'reachable': roster is not None, 'usable': roster_ok,
        'next_step': None if roster_ok else 'Confirm the WorkForce roster path in this workspace.',
        'source': 'WorkForce roster'})
    heartbeat_state = 'fresh' if fresh else ('stale' if age is not None else 'unknown')
    heartbeat_next = None
    if heartbeat_state == 'stale':
        heartbeat_next = 'The daemon last tick is older than two minutes; this is not a process health check.'
    elif heartbeat_state == 'unknown':
        heartbeat_next = 'No daemon tick has been observed.'
    result['sources'].append({
        'name': 'WorkForce heartbeat', 'state': heartbeat_state,
        'detail': 'Last reported activity; not a process health check.', 'last_at': tick,
        'reachable': age is not None, 'usable': fresh,
        'next_step': heartbeat_next, 'source': 'WorkForce daemon'})
    passes_payload = supervisor_snapshot(root)
    result['engines'] = {
        'worklane': _engine_receipt(root, 'local/worklane/deployment.json'),
        'workforce': _engine_receipt(root, 'local/workforce/deployment.json'),
        'worklane_api': _worklane_reachability(root, now),
        'supervisor': _supervisor_pass_fields(passes_payload, now),
    }
    workers = (roster or {}).get('workers', {})
    runtime = (daemon or {}).get('workers', {})
    flight = (daemon or {}).get('in_flight', [])
    if not isinstance(runtime, dict): runtime = {}
    if not isinstance(flight, list): flight = []
    daemon_path = resolve_daemon_path(root)
    runner_config_cache = {}
    result['coverage'] = provider_coverage(root, registry, workers, runner_config_cache)
    if isinstance(workers, dict):
        for identity, row in workers.items():
            if not isinstance(row, dict): continue
            if identity == 'demo-worker' and not _seat_command_configured(row.get('command')): continue
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
            configured = _seat_command_configured(command)
            executable_status = _seat_executable_status(row, root, runner_config_cache) if configured else None
            if executable_status in ('missing', 'untrusted'): configured = False
            kind = row.get('kind') or 'agent'
            if not configured: state = 'not_configured'
            # Same held predicate as coverage (review finding pc-1477): a
            # seat-kind row (lane, or no kind — _row_is_seat_kind) carrying
            # the wf-259 generator's held state reads OFF here too, not just
            # explicit lane rows.
            if _row_is_held(row, row.get('kind')):
                state = 'off'
            live = runtime.get(identity, {})
            report = read_json(root / '.blueprint/job-reports' / (identity + '.json'), root) if identity in ('chief-of-staff','health-patrol','workspace-efficiency') else None
            group = 'supervisor' if identity == 'bp-supervisor' else ('seat' if kind == 'lane' else 'job')
            held = next((o for o in result['orders'] if o['status'] == 'in_progress' and identity in o['workers']), None) if group == 'seat' else None
            last_candidates = last_shift_candidates(daemon_path, root, identity)
            verified = bool(held and held['id'] in last_candidates)
            reservation = bool(held and state == 'last_run_failed' and preserved_reservation(root, command, held['id']))
            project_slug = _row_project_slug(row)
            project_name = registry.get(project_slug, {}).get('name') if project_slug else None
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
                'group': group, 'configured':configured,
                'configuration': ('Command configured' if configured else
                                  'provider missing on disk' if executable_status == 'missing' else
                                  'provider outside trusted locations' if executable_status == 'untrusted' else
                                  'Placeholder command — no operational work runs'),
                'kind': kind, 'schedule': row.get('schedule') or 'Not scheduled',
                'next_fire': live.get('next_fire') if isinstance(live, dict) else None,
                'model': _seat_model_text(row, root, runner_config_cache), 'last_at': tick, 'source': 'Local WorkForce',
                'project': project_slug, 'project_name': project_name,
                'held': {'id': held['id'], 'project': held['project'], 'project_name': held['project_name'], 'title': held['title']} if held else None,
                'held_verified': verified, 'last_candidates': last_candidates,
                'recovery_attempts': recovery_attempts(daemon_path, root, identity),
                'preserved_reservation': reservation, 'action': action}
            if group == 'supervisor':
                result['supervisor'] = {**agent_row, 'passes': passes_payload}
            else:
                result['agents'].append(agent_row)
    result['agents'].sort(key=lambda a: (STATE_ORDER.get(a['state'], 9), a['name']))
    # 'running' is agent-evidence-only (fresh heartbeat plus an open shift or
    # in-flight ticket) — never inflated by a WorkLane claim's age, unlike
    # 'claimed' above (pc-1483: "a days-old human claim" must not read as a
    # running agent). It is also seats-only, the same rule overview()
    # applies on the Overview metric (STATES_AND_TERMS §2): a working job
    # (a scheduled duty that never claims work) shows as running on Agents
    # but must not count toward a project's execution (review finding,
    # pc-1483 recovery 2 — a working job made Map disagree with Overview).
    project_index = {p['id']: p for p in result['projects']}
    for agent in result['agents']:
        if agent['group'] == 'seat' and agent['state'] == 'working' and agent['project'] in project_index:
            project_index[agent['project']]['running'] += 1
    placeholders = [a['name'] for a in result['agents'] if not a['configured']]
    if placeholders:
        result['sources'].append({
            'name':'Agent/job configuration','state':'partial',
            'detail':'Placeholder commands: ' + ', '.join(placeholders) + '. These jobs do not execute operational work.',
            'reachable': True, 'usable': False,
            'next_step': 'Placeholder commands do not execute operational work.',
            'source': 'roster command'})
    calendar_path = root / '.blueprint' / 'calendar.json'
    calendar = read_json(calendar_path, root)
    calendar_valid = calendar is not None and isinstance(calendar.get('events'), list)
    if calendar_valid:
        calendar_state, calendar_next = 'available', None
    elif calendar_path.exists():
        calendar_state, calendar_next = 'unavailable', 'The calendar file exists but could not be read.'
    else:
        calendar_state, calendar_next = 'not_configured', None
    result['sources'].append({
        'name': 'Calendar', 'state': calendar_state,
        'detail': 'Local calendar events' if calendar_valid else 'No readable local calendar file; agent schedules are shown separately.',
        'reachable': calendar_path.exists() or calendar_valid, 'usable': calendar_valid,
        'next_step': calendar_next, 'source': '.blueprint/calendar.json'})
    if calendar_valid:
        for event in calendar['events']:
            if isinstance(event, dict):
                result['events'].append({key: str(event.get(key) or '') for key in ['title', 'at', 'source', 'state', 'notes']})
    result['orders'].sort(key=lambda x: (not x['attention'], x['priority'] if isinstance(x['priority'], int) else 99, x['project'], x['id']))
    return result
