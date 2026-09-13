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
_WINDOW_SECONDS = 14 * 86400


def _github(executable, endpoint):
    result = subprocess.run([executable, 'api', endpoint], capture_output=True, text=True, timeout=12)
    if result.returncode:
        raise RuntimeError('GitHub request failed; check access or rate limits.')
    return json.loads(result.stdout)


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def _in_window(value):
    observed = _parse_time(value)
    if not observed:
        return False
    return (datetime.now(timezone.utc) - observed).total_seconds() <= _WINDOW_SECONDS


def _pr_event(item):
    if item.get('merged_at'):
        return 'merged'
    if str(item.get('state') or '') == 'open':
        return 'opened'
    return 'closed'


def _workflow_item(item, repo, spec):
    return {'kind': 'workflow', 'repo': repo, 'project': spec.get('project', ''),
            'workflow_name': str(item.get('name') or 'workflow'),
            'title': str(item.get('name') or 'workflow'),
            'url': str(item.get('html_url') or ''),
            'state': str(item.get('conclusion') or item.get('status') or 'unknown'),
            'updated_at': item.get('updated_at') or item.get('created_at'),
            'sha': item.get('head_sha'), 'count': 1, 'role': spec.get('role', 'repository')}


def _pull_item(item, repo, spec, *, closed=False):
    stamp = item.get('merged_at') or item.get('closed_at') if closed else item.get('updated_at') or item.get('created_at')
    return {'kind': 'pull_request', 'repo': repo, 'project': spec.get('project', ''),
            'title': str(item.get('title') or 'Pull request'),
            'url': str(item.get('html_url') or ''),
            'state': str(item.get('state') or 'open'),
            'pr_event': _pr_event(item),
            'updated_at': stamp,
            'sha': (item.get('head') if isinstance(item.get('head'), dict) else {}).get('sha') or item.get('head_sha'),
            'number': item.get('number'), 'role': spec.get('role', 'repository')}


def _release_item(item, repo, spec):
    return {'kind': 'release', 'repo': repo, 'project': spec.get('project', ''),
            'title': str(item.get('tag_name') or item.get('name') or 'release'),
            'url': str(item.get('html_url') or ''),
            'state': str(item.get('draft') and 'draft' or 'published'),
            'updated_at': item.get('published_at') or item.get('created_at'),
            'sha': item.get('target_commitish'), 'role': spec.get('role', 'repository')}


def _collapse_workflows(rows):
    collapsed = []
    for row in rows:
        if row.get('kind') != 'workflow':
            collapsed.append(row)
            continue
        key = (row.get('workflow_name'), row.get('state'), row.get('sha'))
        if collapsed and collapsed[-1].get('kind') == 'workflow':
            previous = collapsed[-1]
            previous_key = (previous.get('workflow_name'), previous.get('state'), previous.get('sha'))
            if previous_key == key:
                previous['count'] = previous.get('count', 1) + 1
                continue
        collapsed.append({**row, 'count': row.get('count', 1)})
    return collapsed


def _sort_rows(rows):
    rows.sort(key=lambda row: _parse_time(row.get('updated_at')) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def _load_repo(executable, spec):
    repo = spec['repo']
    metadata = _github(executable, 'repos/' + repo)
    if not isinstance(metadata, dict):
        raise ValueError('Invalid repository response')
    rows = []
    workflow_rows = []
    failures = []
    queries = [
        ('pull_request', 'pulls?state=open&per_page=8'),
        ('pull_request_closed', 'pulls?state=closed&sort=updated&per_page=100'),
        ('workflow', 'actions/runs?per_page=100'),
        ('release', 'releases?per_page=8'),
    ]
    for kind, suffix in queries:
        try:
            payload = _github(executable, f'repos/{repo}/{suffix}')
            if kind == 'workflow' and not isinstance(payload, dict):
                raise ValueError('Invalid workflow response')
            items = payload.get('workflow_runs', []) if kind == 'workflow' else payload
            if not isinstance(items, list):
                raise ValueError('Invalid response')
            for item in items:
                if not isinstance(item, dict):
                    continue
                if kind == 'pull_request':
                    if not _in_window(item.get('updated_at') or item.get('created_at')):
                        continue
                    rows.append(_pull_item(item, repo, spec))
                elif kind == 'pull_request_closed':
                    stamp = item.get('merged_at') or item.get('closed_at')
                    if not _in_window(stamp):
                        continue
                    rows.append(_pull_item(item, repo, spec, closed=True))
                elif kind == 'workflow':
                    workflow_rows.append(_workflow_item(item, repo, spec))
                elif kind == 'release':
                    if not _in_window(item.get('published_at') or item.get('created_at')):
                        continue
                    rows.append(_release_item(item, repo, spec))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError):
            failures.append(kind.replace('_closed', ''))
    for row in _collapse_workflows(workflow_rows):
        if _in_window(row.get('updated_at')):
            rows.append(row)
    _sort_rows(rows)
    connected = 'connected' if not failures else 'partial'
    return {'repo': repo, 'project': spec.get('project', ''), 'role': spec.get('role', 'repository'),
            'private': metadata.get('private'), 'branch': metadata.get('default_branch'),
            'state': connected, 'missing': sorted(set(failures)),
            'quiet': connected == 'connected' and not rows,
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
                                 'items': (old or {}).get('items', []), 'quiet': False})
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
    key = (str(root), json.dumps(specs, sort_keys=True), _WINDOW_SECONDS)
    with _LOCK:
        entry = _CACHE.setdefault(key, {'checked': 0, 'busy': False, 'data': {'state': 'loading', 'repositories': []}})
        if not entry['busy'] and time.monotonic()-entry['checked']>_TTL:
            entry['busy'] = True
            _POOL.submit(_refresh, key, executable, specs)
        return {**entry['data'], 'refreshing': entry['busy']}
