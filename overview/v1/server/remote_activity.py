"""Cached, read-only GitHub evidence. No inference of agent runtime state."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time

_LOCK = threading.Lock()
_CACHE = {}
_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix='bp-github')
_TTL = 120


def _github(executable, endpoint):
    result = subprocess.run([executable, 'api', endpoint], capture_output=True, text=True, timeout=12)
    if result.returncode:
        raise RuntimeError('GitHub request failed; check access or rate limits.')
    return json.loads(result.stdout)


def _load_repo(executable, spec):
    repo = spec['repo']
    metadata = _github(executable, 'repos/' + repo)
    if not isinstance(metadata, dict): raise ValueError('Invalid repository response')
    rows = []
    failures = []
    queries = [('pull_request', 'pulls?state=open&per_page=8'), ('workflow', 'actions/runs?per_page=8'), ('release', 'releases?per_page=1')]
    for kind, suffix in queries:
        try:
            payload = _github(executable, f'repos/{repo}/{suffix}')
            if kind == 'workflow' and not isinstance(payload, dict): raise ValueError('Invalid workflow response')
            items = payload.get('workflow_runs', []) if kind == 'workflow' else payload
            if not isinstance(items, list): raise ValueError('Invalid response')
            for item in items:
                if not isinstance(item, dict): continue
                rows.append({'kind': kind, 'repo': repo, 'project': spec.get('project', ''),
                    'title': str(item.get('title') or item.get('name') or item.get('tag_name') or kind),
                    'url': str(item.get('html_url') or ''),
                    'state': str(item.get('conclusion') or item.get('status') or ('draft' if item.get('draft') else item.get('state')) or 'published'),
                    'updated_at': item.get('updated_at') or item.get('published_at') or item.get('created_at'),
                    'sha': item.get('head_sha') or (item.get('head') if isinstance(item.get('head'), dict) else {}).get('sha'),
                    'number': item.get('number'), 'role': spec.get('role', 'repository')})
        except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError):
            failures.append(kind)
    return {'repo': repo, 'project': spec.get('project', ''), 'role': spec.get('role', 'repository'),
            'private': metadata.get('private'), 'branch': metadata.get('default_branch'),
            'state': 'partial' if failures else 'connected', 'missing': failures,
            'observed_at': datetime.now(timezone.utc).isoformat(), 'items': rows}


def _refresh(key, executable, specs):
    repositories = []
    for spec in specs:
        try:
            repositories.append(_load_repo(executable, spec))
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
            with _LOCK:
                old = next((r for r in _CACHE[key]['data'].get('repositories', []) if r['repo'] == spec['repo']), None)
            repositories.append({**(old or spec), 'repo': spec['repo'], 'state': 'unavailable',
                                 'error': 'Unable to read GitHub. Check repository access and GitHub CLI sign-in.',
                                 'items': (old or {}).get('items', [])})
    with _LOCK:
        _CACHE[key]['data'] = {'state': 'connected' if all(r['state']=='connected' for r in repositories) else 'partial',
            'repositories': repositories, 'refreshing': False, 'refresh_interval_seconds': _TTL,
            'agent_runtime': 'Not connected. GitHub events do not establish agent liveness.'}
        _CACHE[key]['busy'] = False
        _CACHE[key]['checked'] = time.monotonic()


def remote_snapshot(binder):
    if binder is None:
        return {'state': 'not_configured', 'repositories': [], 'refreshing': False}
    root = Path(binder).resolve()
    config = root / '.blueprint/connections.json'
    if not config.resolve().is_relative_to(root):
        return {'state': 'invalid_config', 'repositories': [], 'refreshing': False}
    try:
        raw = json.loads(config.read_text())
        specs = raw.get('github', {}).get('repositories', [])
        if not isinstance(specs, list) or len(specs)>30: raise ValueError('Invalid repository list')
        if any(not isinstance(s, dict) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', s.get('repo', '')) for s in specs):
            raise ValueError('Invalid repository identity')
    except FileNotFoundError:
        return {'state': 'not_configured', 'repositories': [], 'refreshing': False}
    except (ValueError, OSError, AttributeError, TypeError):
        return {'state': 'invalid_config', 'repositories': [], 'refreshing': False}
    executable = shutil.which('gh')
    if not executable:
        return {'state': 'unavailable', 'error': 'GitHub CLI is not available to this application.', 'repositories': [], 'refreshing': False}
    if not specs: return {'state': 'not_configured', 'repositories': [], 'refreshing': False}
    key = (str(root), json.dumps(specs, sort_keys=True))
    with _LOCK:
        entry = _CACHE.setdefault(key, {'checked': 0, 'busy': False, 'data': {'state': 'loading', 'repositories': []}})
        if not entry['busy'] and time.monotonic()-entry['checked']>_TTL:
            entry['busy'] = True
            _POOL.submit(_refresh, key, executable, specs)
        return {**entry['data'], 'refreshing': entry['busy']}
