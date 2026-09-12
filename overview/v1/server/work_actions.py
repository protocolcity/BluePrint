"""Narrow work-order note bridge through installed WorkLane tool handlers."""
import json
import os
from pathlib import Path
import re
import subprocess
from .operations import project_registry
from .work_order import read_work_order

# Inputs travel on stdin, never interpolated into executable code. The engine
# resolves the project again; verify its tracker before invoking its write tool.
_BRIDGE = '''
import json, sys
from pathlib import Path
from worklane.products import get_product, product_tracker
from worklane.mcp.handlers import TPHandlers
request = json.load(sys.stdin)
try:
    spec = get_product(request['project'])
    if spec is None or spec.slug != request['project']:
        raise ValueError('Project is not registered in WorkLane.')
    tracker = product_tracker(spec)
    if Path(tracker._db_path).resolve() != Path(request['expected_db']).resolve():
        raise ValueError('WorkLane resolves to a different workspace store.')
    handler = TPHandlers(author='you')
    def tool(name):
        return getattr(handler, 'wl_' + name, None) or getattr(handler, 'tp_' + name)
    identity = str(request['raw_id'])
    project = request['project']
    action = request.get('action', 'note')
    if action != 'note':
        task = tracker.get_task(request['raw_id'])
        if task is None or task.updated_at != request['expected_updated_at']:
            raise ValueError('This record changed. Reload it before applying an action.')
    if action == 'note':
        result = tool('comment')(identity, request['body'], product=project)
    elif action == 'priority':
        result = tool('update')(identity, product=project, priority=request['value'])
    elif action == 'hold':
        result = tool('update')(identity, product=project, gate_type='human', gate_note=request['value'])
    elif action == 'resume':
        result = tool('update')(identity, product=project, gate_type='', gate_note='')
    elif action == 'assign':
        labels = list(task.labels or [])
        result = tool('label')(identity, product=project, add=['worker:' + request['value']],
            remove=[label for label in labels if label.startswith('worker:') and label != 'worker:' + request['value']])
    else:
        raise ValueError('Unsupported work-order action.')
    print(json.dumps(result))
except Exception as exc:
    from worklane.mcp.handlers import ToolError
    message = str(exc) if isinstance(exc, (ToolError, ValueError)) else 'WorkLane rejected the action. Refresh before retrying.'
    print(json.dumps({'ok': False, 'error': message}))
'''


def add_note(binder, project, order_id, body):
    if not isinstance(body, str) or not body.strip() or len(body) > 12000:
        raise ValueError('Write a note between 1 and 12,000 characters.')
    if re.search(r'(?im)^\s*(?:#+\s*)?(?:owner|start|plan|completed|verification|blocked|next\s+step)\s*:', body):
        raise ValueError('This note contains WorkLane status-command markers. Use ordinary prose here; status changes need a dedicated action.')
    if binder is None or not isinstance(project, str) or not project:
        raise ValueError('A workspace and explicit project are required.')
    root = Path(binder).resolve()
    if project not in project_registry(root):
        raise ValueError('Only registered workspace projects accept notes.')
    order = read_work_order(root, project, order_id)
    return _invoke(root, project, order, {'action': 'note', 'body': body.strip()})


def _invoke(root, project, order, action):
    installed = root / 'local/worklane/current/venv/bin/python'
    executable = installed if installed.is_file() else root / 'worklane/.venv/bin/python'
    if not executable.is_file():
        raise RuntimeError('The workspace WorkLane runtime is unavailable.')
    db = root / 'worklane/worklane/local/data' / (project + '.db')
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': os.environ.get('HOME', ''),
           'PYTHONDONTWRITEBYTECODE': '1', 'WORKLANE_RUNTIME_DIR': str(db.parent.parent),
           'WORKLANE_DB': str(db), 'TRADEOS_TRACKER': 'sqlite', 'WL_AGENT_ID': 'you', 'TP_AGENT_ID': 'you'}
    try:
        result = subprocess.run([str(executable), '-c', _BRIDGE],
            input=json.dumps({'project': project, 'raw_id': order['id'], 'expected_db': str(db), **action}),
            cwd=str(root / 'worklane'), env=env, text=True, capture_output=True, timeout=15)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('WorkLane timed out. The action may have been saved; refresh the record before retrying.') from exc
    except OSError as exc:
        raise RuntimeError('WorkLane could not be started.') from exc
    try:
        payload = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError('WorkLane returned an unreadable response. Refresh before retrying.') from exc
    if result.returncode or not payload.get('ok'):
        raise RuntimeError(payload.get('error') or 'WorkLane rejected the action.')
    return payload


def work_action(binder, project, order_id, action, value, expected_updated_at):
    if action not in ('priority', 'hold', 'resume', 'assign'):
        raise ValueError('Unsupported work-order action.')
    if not binder or not isinstance(project, str) or not project or project not in project_registry(Path(binder).resolve()):
        raise ValueError('A registered project is required.')
    if not isinstance(expected_updated_at, str) or not expected_updated_at:
        raise ValueError('Reload the record before applying an action.')
    root = Path(binder).resolve()
    order = read_work_order(root, project, order_id)
    if order['status'] in ('done', 'canceled', 'cancelled'):
        raise ValueError('This work order is closed.')
    if action == 'priority' and (type(value) is not int or value not in (1,2,3,4)):
        raise ValueError('Select a priority from 1 to 4.')
    if action == 'hold' and (not isinstance(value, str) or not value.strip() or len(value)>2000):
        raise ValueError('Describe the decision needed in 1 to 2,000 characters.')
    if action == 'assign':
        from .operations import read_json
        from .local_projectors import resolve_roster_path
        from urllib.parse import urlparse, parse_qs
        roster = read_json(resolve_roster_path(root), root) or {}
        workers = roster.get('workers', {})
        row = workers.get(value) if isinstance(value, str) and isinstance(workers, dict) else None
        if not isinstance(row, dict): raise ValueError('Choose a registered agent.')
        scope = parse_qs(urlparse(str(row.get('queue_url', ''))).query).get('product', [])
        if scope != [project]: raise ValueError('That agent is not assigned to this project store.')
    return _invoke(root, project, order, {'action':action, 'value':value, 'expected_updated_at':expected_updated_at})


def assignment_options(binder, project):
    from .operations import read_json
    from .local_projectors import resolve_roster_path
    from urllib.parse import urlparse, parse_qs
    if not binder: return []
    root = Path(binder).resolve()
    workers = (read_json(resolve_roster_path(root), root) or {}).get('workers', {})
    if not isinstance(workers, dict): return []
    return [{'id': identity, 'name': str(row.get('name') or identity)}
        for identity, row in workers.items() if identity != 'demo-worker' and isinstance(row, dict)
        and parse_qs(urlparse(str(row.get('queue_url', ''))).query).get('product') == [project]]
