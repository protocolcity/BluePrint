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
_FAILED = frozenset({'failure', 'cancelled', 'timed_out', 'action_required', 'stale'})
_PENDING = frozenset({'queued', 'in_progress', 'waiting', 'requested', 'pending'})


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
    if item.get('merged_at') or item.get('merged'):
        return 'merged'
    if str(item.get('state') or '') == 'open':
        return 'opened'
    return 'closed'


def _pull_event(item):
    if item.get('merged_at') or item.get('merged'):
        return 'merged'
    if item.get('pr_event'):
        return item.get('pr_event')
    if str(item.get('state') or '') == 'open':
        return 'opened'
    return item.get('state') or 'unknown'


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
            'merged_at': item.get('merged_at'),
            'merged': bool(item.get('merged_at') or item.get('merged')),
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


def _read_json(path, root):
    try:
        if not path.resolve().is_relative_to(root.resolve()):
            return None
    except (OSError, AttributeError):
        return None
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def _deployment_receipt(root, spec):
    relative = spec.get('receipt')
    if not isinstance(relative, str) or not relative.strip():
        project = str(spec.get('project') or '')
        if project in ('protocolcity', 'blueprint'):
            relative = '.blueprint/deployment.json'
        elif project:
            relative = f'local/{project}/deployment.json'
        else:
            return None
    return _read_json((root / relative).resolve(), root)


def _workflow_state(item):
    return str(item.get('state') or 'unknown').lower()


def _group_priority(items):
    best = 9
    for item in items:
        kind = item.get('kind')
        if kind == 'workflow':
            state = _workflow_state(item)
            if state in _FAILED:
                best = min(best, 0)
            elif state in _PENDING or state not in ('success', 'completed'):
                best = min(best, 1)
            else:
                best = min(best, 5)
        elif kind == 'pull_request':
            if item.get('state') == 'open' or item.get('pr_event') == 'opened':
                best = min(best, 2)
            elif _pull_event(item) == 'merged':
                best = min(best, 3)
            else:
                best = min(best, 4)
        elif kind == 'release':
            best = min(best, 3)
    return best


def _group_key(item):
    sha = item.get('sha')
    if sha:
        return f'sha:{sha}'
    if item.get('kind') == 'release':
        return f'release:{item.get("title")}'
    if item.get('kind') == 'pull_request' and item.get('number') is not None:
        return f'pr:{item.get("number")}'
    return f'{item.get("kind")}:{item.get("url")}'


def _deploy_state(items, receipt):
    if not receipt:
        return 'unknown'
    source_head = receipt.get('source_head')
    version = str(receipt.get('version') or '').strip()
    shas = {str(item.get('sha') or '') for item in items if item.get('sha')}
    if source_head and str(source_head) in shas:
        return 'deployed'
    for item in items:
        if item.get('kind') != 'release':
            continue
        tag = str(item.get('title') or '').strip()
        if version and tag and (tag == version or tag.lstrip('v') == version.lstrip('v')):
            return 'version_note'
    return 'unknown'


def _group_headline(items):
    pr = next((item for item in items if item.get('kind') == 'pull_request'), None)
    if pr:
        event = _pull_event(pr)
        number = pr.get('number')
        prefix = f'PR #{number} · ' if number is not None else 'PR · '
        return prefix + str(pr.get('title') or 'Pull request') + f' · {event}'
    release = next((item for item in items if item.get('kind') == 'release'), None)
    if release:
        return f'Release · {release.get("title") or "release"}'
    workflow = next((item for item in items if item.get('kind') == 'workflow'), None)
    if workflow:
        commit = (workflow.get('sha') or 'no commit')[:7]
        count = workflow.get('count', 1)
        suffix = f' · ×{count}' if count > 1 else ''
        return f'CI · {workflow.get("workflow_name") or workflow.get("title")} · {_workflow_state(workflow)} · {commit}{suffix}'
    item = items[0]
    return f'{item.get("kind", "event").replace("_", " ")} · {item.get("title") or "event"}'


def _group_badge(items):
    pr = next((item for item in items if item.get('kind') == 'pull_request'), None)
    if pr:
        return _pull_event(pr)
    workflow = next((item for item in items if item.get('kind') == 'workflow'), None)
    if workflow:
        return _workflow_state(workflow)
    release = next((item for item in items if item.get('kind') == 'release'), None)
    if release:
        return str(release.get('state') or 'published')
    return 'unknown'


def _group_kind(items):
    kinds = {item.get('kind') for item in items}
    if 'pull_request' in kinds:
        return 'pull_request'
    if 'release' in kinds:
        return 'release'
    return 'workflow'


def _group_updated_at(items):
    stamps = [_parse_time(item.get('updated_at')) for item in items]
    stamps = [stamp for stamp in stamps if stamp]
    return max(stamps).isoformat() if stamps else items[0].get('updated_at')


def _build_groups(items, receipt):
    buckets = {}
    for item in items:
        buckets.setdefault(_group_key(item), []).append(item)
    groups = []
    for key, bucket in buckets.items():
        _sort_rows(bucket)
        deploy_state = _deploy_state(bucket, receipt)
        groups.append({
            'id': key,
            'kind': _group_kind(bucket),
            'headline': _group_headline(bucket),
            'badge': _group_badge(bucket),
            'deploy_state': deploy_state,
            'priority': _group_priority(bucket),
            'updated_at': _group_updated_at(bucket),
            'sha': bucket[0].get('sha'),
            'url': next((item.get('url') for item in bucket if item.get('url')), ''),
            'items': bucket,
        })
    groups.sort(key=lambda group: (
        group['priority'],
        -(_parse_time(group.get('updated_at')) or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
    ))
    return groups


def _build_summary(groups, receipt):
    summary = {
        'open_prs': 0,
        'failed_checks': 0,
        'pending_checks': 0,
        'recent_merges': 0,
        'recent_releases': 0,
        'loaded': len(groups),
        'truncated': False,
    }
    for group in groups:
        for item in group['items']:
            if item.get('kind') == 'pull_request':
                if item.get('state') == 'open' or item.get('pr_event') == 'opened':
                    summary['open_prs'] += 1
                elif _pull_event(item) == 'merged':
                    summary['recent_merges'] += 1
            elif item.get('kind') == 'workflow':
                state = _workflow_state(item)
                if state in _FAILED:
                    summary['failed_checks'] += item.get('count', 1)
                elif state in _PENDING or state not in ('success', 'completed'):
                    summary['pending_checks'] += item.get('count', 1)
            elif item.get('kind') == 'release':
                summary['recent_releases'] += 1
    deployment = None
    if receipt:
        version = str(receipt.get('version') or '').strip()
        sha = receipt.get('source_head') or receipt.get('revision')
        activated = receipt.get('activated_at') if isinstance(receipt.get('activated_at'), str) else None
        if version or sha:
            state = 'verified' if any(group.get('deploy_state') == 'deployed' for group in groups) else 'unknown'
            deployment = {'version': version or None, 'sha': sha, 'activated_at': activated, 'state': state}
    return summary, deployment


def _load_repo(executable, spec, root=None):
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
    truncated = False
    for row in _collapse_workflows(workflow_rows):
        if _in_window(row.get('updated_at')):
            rows.append(row)
    if len(workflow_rows) >= 100:
        truncated = True
    _sort_rows(rows)
    connected = 'connected' if not failures else 'partial'
    receipt = _deployment_receipt(root, spec) if root is not None else None
    groups = _build_groups(rows, receipt)
    summary, deployment = _build_summary(groups, receipt)
    summary['truncated'] = truncated
    return {'repo': repo, 'project': spec.get('project', ''), 'role': spec.get('role', 'repository'),
            'private': metadata.get('private'), 'branch': metadata.get('default_branch'),
            'state': connected, 'missing': sorted(set(failures)),
            'quiet': connected == 'connected' and not groups,
            'observed_at': datetime.now(timezone.utc).isoformat(), 'items': rows,
            'groups': groups, 'summary': summary, 'deployment': deployment}


def _refresh(key, executable, specs, root):
    repositories = []
    for spec in specs:
        try:
            repositories.append(_load_repo(executable, spec, root))
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
            with _LOCK:
                old = next((r for r in _CACHE[key]['data'].get('repositories', []) if r['repo'] == spec['repo']), None)
            repositories.append({**(old or spec), 'repo': spec['repo'], 'state': 'unavailable',
                                 'error': 'Unable to read GitHub. Check repository access and GitHub CLI sign-in.',
                                 'items': (old or {}).get('items', []), 'quiet': False})
    fetched_at = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        _CACHE[key]['data'] = {'state': 'connected' if all(r['state']=='connected' for r in repositories) else 'partial',
            'repositories': repositories, 'refreshing': False, 'refresh_interval_seconds': _TTL,
            'fetched_at': fetched_at, 'cache_age_seconds': 0,
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
            _POOL.submit(_refresh, key, executable, specs, root)
        age = max(0, int(time.monotonic() - entry['checked']))
        payload = {**entry['data'], 'refreshing': entry['busy'], 'cache_age_seconds': age}
        if entry['data'].get('fetched_at'):
            payload['fetched_at'] = entry['data']['fetched_at']
        return payload
