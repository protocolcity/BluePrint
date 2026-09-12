"""Read-only operations projection. Sources, freshness and gaps travel with data."""
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import sqlite3
import shlex

from .local_projectors import worklane_data_dir, resolve_roster_path, resolve_daemon_path


def last_run(daemon_path, root, identity):
    if daemon_path is None or not identity or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in identity):
        return None
    path = daemon_path.resolve().parent / 'ledger' / (identity + '.log')
    if not path.resolve().is_relative_to(root):
        return None
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 16384))
            lines = stream.read().decode('utf-8', errors='replace').splitlines()
        for line in reversed(lines):
            parts = shlex.split(line)
            if len(parts) < 2 or parts[1] not in ('STOP', 'ERROR', 'DONE', 'SKIP'):
                continue
            fields = dict(item.split('=', 1) for item in parts[2:] if '=' in item)
            return {'at': parts[0], 'outcome': parts[1].lower(), 'reason': fields.get('reason') or ('Process exited; verify work outcome.' if parts[1] == 'DONE' else 'No reason reported.')}
    except (OSError, ValueError):
        pass
    return None


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
                                   'folder': str(path.parent.parent.relative_to(root))}
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
              'orders': [], 'projects': [], 'agents': [], 'sources': [], 'truncated': False,
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
                for row in rows[:2000]:
                    item = dict(row)
                    try:
                        labels = json.loads(item.get('labels') or '[]')
                    except (ValueError, TypeError):
                        labels = []
                    labels = labels if isinstance(labels, list) else []
                    attention = item.get('gate_type') == 'human' or 'gate:human' in labels
                    order_id = item.get('ext_id') or (f"{project['prefix']}-{item['id']}" if project['prefix'] else str(item['id']))
                    from suite.api.calendar import events_from_task
                    for event in events_from_task({**item, 'id':order_id, 'labels':labels, 'product':path.stem}):
                        result['work_dates'].append({**event, 'dtstart':event['dtstart'].isoformat(), 'attention':attention})
                    result['orders'].append({'id': order_id, 'project': path.stem, 'project_name': project['name'],
                        'title': item.get('title') or order_id, 'status': item.get('status'),
                        'priority': item.get('priority'), 'updated_at': item.get('updated_at'),
                        'attention': attention, 'gate_note': item.get('gate_note') or '',
                        'owner': ', '.join(str(x)[7:] for x in labels if isinstance(x,str) and x.startswith('worker:')) or 'Unassigned'})
                    summary['attention'] += int(attention)
        except (OSError, sqlite3.Error):
            summary['state'] = 'unavailable'
        result['projects'].append(summary)
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
    if isinstance(workers, dict):
        for identity, row in workers.items():
            if not isinstance(row, dict) or identity == 'demo-worker': continue
            state = 'unknown' if not fresh else ('working' if identity in flight else 'idle')
            command = row.get('command')
            configured = isinstance(command, list) and bool(command) and command not in (['true'], ['/usr/bin/true'], ['/bin/true'], ['sh','-c','true'], ['bash','-c','true'])
            if not configured: state = 'not_configured'
            if row.get('enabled') is False: state = 'off'
            live = runtime.get(identity, {})
            report = read_json(root / '.blueprint/job-reports' / (identity + '.json'), root) if identity in ('chief-of-staff','health-patrol','workspace-efficiency') else None
            result['agents'].append({'id': identity, 'name': row.get('display') or identity,
                'last_run': last_run(resolve_daemon_path(root), root, identity),
                'report': {k:report.get(k) for k in ('title','observed_at','state','summary','detail','mode')} if report else None,
                'state': state, 'configured':configured, 'configuration': 'Command configured' if configured else 'Placeholder command — no operational work runs', 'kind': row.get('kind') or 'agent', 'schedule': row.get('schedule') or 'Not scheduled',
                'next_fire': live.get('next_fire') if isinstance(live, dict) else None,
                'model': row.get('model') or 'Not specified', 'last_at': tick, 'source': 'Local WorkForce'})
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
