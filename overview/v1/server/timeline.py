"""Timeline projection — one source-labelled stream across the desk (pc-1471).

Read-only merge of WorkLane events and comments, WorkForce ledger rows,
supervisor passes, and cached GitHub delivery evidence. Bounded by a time
window and row cap; never infers liveness or synthesizes rows.
"""
from __future__ import annotations

import base64
import json
import re
import shlex
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener

from .local_projectors import resolve_daemon_path, worklane_data_dir
from .operations import _NoRedirect, _ledger_tail_lines, project_registry, read_json, supervisor_snapshot
from .remote_activity import remote_snapshot

PAGE_SIZE = 200
WINDOW_SECONDS = 14 * 86400
SOURCE_ROW_CAP = 500
_CURSOR_SEP = '\x1f'

_OWNER_RE = re.compile(r'(?m)^Owner:\s*(\S+)')
_STATUS_WORD = {
    ('created', None): 'filed',
    ('status_change', 'in_progress'): 'claimed',
    ('status_change', 'in_review'): 'parked',
    ('status_change', 'done'): 'closed',
    ('status_change', 'canceled'): 'canceled',
    ('status_change', 'cancelled'): 'canceled',
    ('status_change', 'backlog'): 'released',
}
_LEDGER_EVENTS = frozenset({'START', 'CANDIDATE', 'DONE', 'STOP', 'ERROR', 'SKIP'})
_LEDGER_WORD = {
    'START': 'started',
    'CANDIDATE': 'dispatched',
    'DONE': 'stopped',
    'STOP': 'stopped',
    'ERROR': 'failed',
    'SKIP': 'skipped',
}
_SUPERVISOR_WORD = {
    'dispatched': 'dispatched',
    'pass': 'passed',
    'passed': 'passed',
    'provider_failed': 'failed',
    'failed': 'failed',
    'stopped_by_operator': 'released',
    'no_eligible_ready_work': 'skipped',
    'escalated': 'failed',
    'proposed': 'passed',
}
_WORKFLOW_WORD = {
    'success': 'passed',
    'failure': 'failed',
    'cancelled': 'released',
    'canceled': 'released',
    'skipped': 'skipped',
    'timed_out': 'failed',
    'action_required': 'failed',
    'stale': 'failed',
    'neutral': 'passed',
    'completed': 'passed',
    'in_progress': 'started',
    'queued': 'started',
    'pending': 'started',
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
    return stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=timezone.utc)


def _normalize_at(value) -> str:
    """Canonical UTC timestamp for sort keys and cursor paging (second precision, Z)."""
    stamp = _parse_time(value)
    if stamp is None:
        return str(value or '')
    return stamp.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _event_fields(word: str | None, raw: str) -> dict:
    if word:
        return {'event': word}
    return {'event': 'event', 'event_title': raw}


def _in_window(value) -> bool:
    observed = _parse_time(value)
    if observed is None:
        return False
    return (datetime.now(timezone.utc) - observed).total_seconds() <= WINDOW_SECONDS


def _display_actor(author: str) -> str:
    text = (author or '').strip()
    return 'You' if text.lower() == 'you' else text or 'Unknown'


def _work_order_link(project: str, task_id: str) -> dict:
    return {'href': '/work-order?' + urlencode({'project': project, 'id': task_id}), 'label': task_id}


def _encode_cursor(row: dict) -> str:
    payload = f"{row['at']}{_CURSOR_SEP}{row['id']}"
    return base64.urlsafe_b64encode(payload.encode('utf-8')).decode('ascii').rstrip('=')


def _decode_cursor(cursor: str) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        pad = '=' * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode('ascii')).decode('utf-8')
        at, row_id = raw.split(_CURSOR_SEP, 1)
        return at, row_id
    except (ValueError, UnicodeError):
        return None


def _comment_event_word(body: str) -> str:
    # A parked/closeout body carries its own "Owner: <author>" line as
    # provenance under the lifecycle heading (worklane write.py: "Parked:
    # {reason}\nOwner: {author}"); a bare anywhere-in-body Owner search must
    # not outrank the first-line heading that actually names the transition,
    # or a parked/closed row misreads as a fresh claim.
    first = (body or '').strip().splitlines()[0] if body else ''
    lowered = first.lower()
    if first.startswith('Intake:'):
        return 'filed'
    if first.startswith('Parked:'):
        return 'parked'
    if first.startswith('Released by'):
        return 'released'
    if first.startswith('Completed:'):
        return 'closed'
    if lowered.startswith('canceled:') or lowered.startswith('cancelled:'):
        return 'canceled'
    if first.startswith('Blocked:') or 'gate:' in lowered:
        return 'gated'
    if first.startswith('Owner:') or _OWNER_RE.search(body or ''):
        return 'claimed'
    return 'note'


def _event_word(event_type: str, status: str | None) -> dict:
    key = (event_type, (status or '').strip().lower() or None)
    mapped = _STATUS_WORD.get(key)
    if mapped:
        return _event_fields(mapped, '')
    raw = event_type if not status else f'{event_type}/{status}'
    return _event_fields(None, raw)


def _ledger_event_word(event_type: str, fields: dict[str, str]) -> dict:
    if event_type == 'START' and fields.get('recovery') == '1':
        return _event_fields('recovered', '')
    mapped = _LEDGER_WORD.get(event_type)
    return _event_fields(mapped, event_type)


def _supervisor_event_word(outcome: str) -> dict:
    normalized = (outcome or '').strip().lower().replace(' ', '_')
    mapped = _SUPERVISOR_WORD.get(normalized)
    return _event_fields(mapped, outcome or 'unknown')


def _github_event_word(item: dict) -> dict:
    kind = item.get('kind')
    if kind == 'pull_request':
        pr_event = str(item.get('pr_event') or item.get('state') or '').lower()
        mapped = {'opened': 'opened', 'merged': 'merged', 'closed': 'closed'}.get(pr_event)
        return _event_fields(mapped, pr_event or 'pull_request')
    if kind == 'workflow':
        state = str(item.get('state') or '').lower()
        mapped = _WORKFLOW_WORD.get(state)
        return _event_fields(mapped, state or 'workflow')
    if kind == 'release':
        return _event_fields('released', '')
    raw = str(kind or 'delivery')
    return _event_fields(None, raw)


def _registered_dbs(root: Path) -> list[tuple[str, str, Path]]:
    """(project slug, id prefix, db path) for registered stores only."""
    registry = project_registry(root)
    data = worklane_data_dir(root)
    rows: list[tuple[str, str, Path]] = []
    if not data.is_dir():
        return rows
    for db_path in sorted(data.glob('*.db')):
        slug = db_path.stem
        if slug not in registry:
            continue
        prefix = registry[slug].get('prefix') or slug
        rows.append((slug, prefix, db_path))
    return rows


def _task_public_id(prefix: str, ext_id, numeric_id) -> str:
    if ext_id:
        text = str(ext_id)
        return text if '-' in text else f'{prefix}-{text}'
    return f'{prefix}-{numeric_id}'


def _collapse_worklane_pairs(rows: list[dict]) -> list[dict]:
    """One row per action when an event and its marker comment describe the same thing."""
    comment_index: dict[tuple, list[dict]] = {}
    merged_comment_ids: set[str] = set()
    collapsed: list[dict] = []
    for row in rows:
        if row.get('_kind') != 'comment':
            continue
        event_key = row.get('_event_key')
        if event_key == 'note':
            continue
        key = (row['project'], row['_task_id'], row['at'], row['actor'], event_key)
        comment_index.setdefault(key, []).insert(0, row)
    for row in rows:
        if row.get('_kind') != 'event':
            continue
        event_key = row.get('_event_key')
        key = (row['project'], row['_task_id'], row['at'], row['actor'], event_key)
        comments = comment_index.get(key)
        if comments:
            comment = comments.pop(0)
            merged_comment_ids.add(comment['id'])
            body = (comment.get('_body') or '').strip()
            headline = body.splitlines()[0] if body else row['title']
            extra = {'title': headline}
            # The merged headline is only the comment's first line; the
            # reader must still be able to reach the rest of the original
            # comment (a failure/decision reason must never be clipped away
            # silently — pc-1488 Done-when).
            if body and body != headline:
                extra['detail'] = body
            collapsed.append({k: v for k, v in row.items() if not k.startswith('_')} | extra)
        else:
            collapsed.append({k: v for k, v in row.items() if not k.startswith('_')})
    for row in rows:
        if row.get('_kind') != 'comment':
            continue
        if row['id'] in merged_comment_ids:
            continue
        out = {k: v for k, v in row.items() if not k.startswith('_')}
        body = (row.get('_body') or '').strip()
        if body:
            out['title'] = body
        collapsed.append(out)
    return collapsed


def _worklane_rows(root: Path) -> tuple[list[dict], dict]:
    observed = _now_iso()
    rows: list[dict] = []
    unreadable = 0
    for project, prefix, db_path in _registered_dbs(root):
        try:
            conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=0.5)
        except sqlite3.Error:
            unreadable += 1
            continue
        conn.row_factory = sqlite3.Row
        try:
            try:
                event_rows = conn.execute(
                    """
                    SELECT e.id, e.task_id, e.event_type, e.status, e.actor, e.created_at,
                           t.ext_id, t.title
                      FROM task_events e
                      JOIN tasks t ON t.id = e.task_id
                     ORDER BY e.id DESC
                     LIMIT ?
                    """,
                    (SOURCE_ROW_CAP,),
                ).fetchall()
            except sqlite3.OperationalError:
                event_rows = []
            try:
                comment_rows = conn.execute(
                    """
                    SELECT c.id, c.task_id, c.body, c.author, c.created_at,
                           t.ext_id, t.title
                      FROM task_comments c
                      JOIN tasks t ON t.id = c.task_id
                     ORDER BY c.id DESC
                     LIMIT ?
                    """,
                    (SOURCE_ROW_CAP,),
                ).fetchall()
            except sqlite3.OperationalError:
                comment_rows = []
            for row in event_rows:
                if not _in_window(row['created_at']):
                    continue
                task_id = _task_public_id(prefix, row['ext_id'], row['task_id'])
                mapped = _event_word(row['event_type'], row['status'])
                rows.append({
                    'id': f'worklane:{project}:evt:{row["id"]}',
                    'at': _normalize_at(row['created_at']),
                    'source': 'worklane',
                    'project': project,
                    'actor': _display_actor(row['actor'] or ''),
                    **mapped,
                    'title': str(row['title'] or task_id),
                    'link': _work_order_link(project, task_id),
                    '_kind': 'event',
                    '_task_id': row['task_id'],
                    '_event_key': mapped['event'],
                })
            for row in comment_rows:
                if not _in_window(row['created_at']):
                    continue
                task_id = _task_public_id(prefix, row['ext_id'], row['task_id'])
                word = _comment_event_word(row['body'] or '')
                rows.append({
                    'id': f'worklane:{project}:cmt:{row["id"]}',
                    'at': _normalize_at(row['created_at']),
                    'source': 'worklane',
                    'project': project,
                    'actor': _display_actor(row['author'] or ''),
                    **_event_fields(word, ''),
                    'title': str(row['title'] or task_id),
                    'link': _work_order_link(project, task_id),
                    '_kind': 'comment',
                    '_task_id': row['task_id'],
                    '_event_key': word,
                    '_body': row['body'] or '',
                })
        finally:
            conn.close()
    rows = _collapse_worklane_pairs(rows)
    if not _registered_dbs(root):
        state = 'empty' if not (worklane_data_dir(root).is_dir()) else 'available'
    elif unreadable and not rows:
        state = 'unavailable'
    elif unreadable:
        state = 'partial'
    else:
        state = 'available' if rows or _registered_dbs(root) else 'empty'
    return rows, {'name': 'worklane', 'state': state, 'observed_at': observed,
                  'detail': 'WorkLane store unreadable.' if state == 'unavailable' else ''}


def _split_ledger(line: str) -> list[str]:
    if not line.strip():
        return []
    try:
        return shlex.split(line)
    except ValueError:
        return []


def _ledger_fields(parts: list[str]) -> dict[str, str]:
    return dict(item.split('=', 1) for item in parts[2:] if '=' in item)


def _project_prefix_map(root: Path) -> dict[str, str]:
    """Ticket id prefix (e.g. 'pc') -> registered project slug."""
    return {prefix: slug for slug, prefix, _ in _registered_dbs(root)}


def _resolve_ticket_project(ticket: str, prefix_map: dict[str, str]) -> str:
    if '-' not in ticket:
        return ''
    return prefix_map.get(ticket.split('-', 1)[0], '')


def _workforce_rows(root: Path) -> tuple[list[dict], dict]:
    observed = _now_iso()
    rows: list[dict] = []
    prefix_map = _project_prefix_map(root)
    daemon = resolve_daemon_path(root)
    if daemon is None:
        return rows, {'name': 'workforce', 'state': 'not_configured', 'observed_at': observed,
                      'detail': 'No WorkForce runtime directory found.'}
    ledger_dir = daemon.resolve().parent / 'ledger'
    try:
        if not ledger_dir.resolve().is_relative_to(root.resolve()):
            raise OSError('outside workspace')
    except OSError:
        return rows, {'name': 'workforce', 'state': 'unavailable', 'observed_at': observed,
                      'detail': 'WorkForce ledger path is outside the workspace.'}
    if not ledger_dir.is_dir():
        return rows, {'name': 'workforce', 'state': 'empty', 'observed_at': observed, 'detail': ''}
    for path in sorted(ledger_dir.iterdir()):
        if not path.is_file() or path.suffix != '.log':
            continue
        if len(rows) >= SOURCE_ROW_CAP:
            break
        identity = path.stem
        lines = _ledger_tail_lines(daemon, root, identity)
        if not lines:
            continue
        for index in range(len(lines) - 1, -1, -1):
            if len(rows) >= SOURCE_ROW_CAP:
                break
            line = lines[index]
            parts = _split_ledger(line)
            if len(parts) < 2 or parts[1] not in _LEDGER_EVENTS:
                continue
            if not _in_window(parts[0]):
                continue
            fields = _ledger_fields(parts)
            event_key = parts[1].lower()
            if parts[1] == 'START' and fields.get('recovery') == '1':
                event_key = 'recovery'
            ticket = fields.get('ticket', '')
            title = {
                'start': f'Shift started · {identity}',
                'recovery': f'Recovery shift · {identity}',
                'candidate': f'Candidate {ticket or "order"}',
                'done': f'Shift done · {fields.get("reason", identity)}',
                'stop': f'Shift stopped · {fields.get("reason", identity)}',
                'error': f'Shift failed · {fields.get("reason", identity)}',
                'skip': f'Shift skipped · {fields.get("reason", identity)}',
            }.get(event_key, f'{parts[1]} · {identity}')
            # A blank ledger project= must not become an ambiguous
            # work-order link (observed against pc-1480): resolve it from
            # the ticket's own id prefix against the registered project
            # stores, and otherwise fall back to a plain seat link rather
            # than a link with an unresolved project.
            project = fields.get('project', '') or _resolve_ticket_project(ticket, prefix_map)
            if ticket and project:
                link = _work_order_link(project, ticket)
            elif ticket:
                link = {'href': '/agents', 'label': ticket}
            else:
                link = {'href': '/agents', 'label': identity}
            rows.append({
                'id': f'workforce:{identity}:{index}:{_normalize_at(parts[0])}',
                'at': _normalize_at(parts[0]),
                'source': 'workforce',
                'project': project,
                'actor': identity,
                **_ledger_event_word(parts[1], fields),
                'title': title,
                'link': link,
                # Verified correlation key (identity + ticket, both
                # structured ledger fields) for grouping a shift's
                # dispatch/start/recovery/terminal rows together (pc-1488
                # Done-when); never grouped on prose/time similarity alone.
                'group_key': f'workforce:{identity}:{ticket}' if ticket else '',
            })
    state = 'available' if rows else 'empty'
    return rows, {'name': 'workforce', 'state': state, 'observed_at': observed, 'detail': ''}


def _supervisor_fetch(root: Path, limit: int = 100) -> dict:
    """Read supervisor passes with a higher limit than the Agents panel."""
    receipt = read_json(root / 'local/workforce/deployment.json', root) or {}
    origin = receipt.get('api_origin', '')
    parsed = urlparse(origin)
    if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1')
            or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment):
        return supervisor_snapshot(root)
    request = Request(origin.rstrip('/') + f'/api/supervisor?limit={int(limit)}')
    opener = build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=3) as response:
            payload = json.load(response)
    except Exception:
        return supervisor_snapshot(root)
    passes = payload.get('passes') if isinstance(payload, dict) else None
    if not isinstance(passes, list):
        return supervisor_snapshot(root)
    return {'state': 'available', 'detail': '', 'passes': passes}


def _supervisor_rows(root: Path) -> tuple[list[dict], dict]:
    observed = _now_iso()
    snapshot = _supervisor_fetch(root)
    state = snapshot.get('state', 'unavailable')
    detail = snapshot.get('detail', '')
    if state != 'available':
        return [], {'name': 'supervisor', 'state': state, 'observed_at': observed, 'detail': detail}
    rows = []
    for index, pass_row in enumerate(snapshot.get('passes') or []):
        if not isinstance(pass_row, dict):
            continue
        at = pass_row.get('generated_at')
        if not at or not _in_window(at):
            continue
        outcome = str(pass_row.get('pass_outcome') or 'pass')
        evidence = str(pass_row.get('evidence_file') or 'supervisor pass')
        event = _supervisor_event_word(outcome)
        rows.append({
            'id': f'supervisor:{evidence}:{index}',
            'at': _normalize_at(at),
            'source': 'supervisor',
            'project': '',
            'actor': 'bp-supervisor',
            **event,
            'title': f'Supervisor pass · {event["event"]}',
            'link': {'href': '/agents', 'label': evidence},
        })
    return rows, {'name': 'supervisor', 'state': 'available', 'observed_at': observed, 'detail': ''}


def _github_kind_key(item: dict) -> str:
    return f"{item.get('kind')}:{item.get('number') or item.get('sha') or item.get('workflow_name')}"


def _github_cache_observed(snapshot: dict) -> str:
    """Most recent cache fill time from remote_activity repositories."""
    stamps = [_parse_time(repo.get('observed_at'))
              for repo in (snapshot.get('repositories') or []) if isinstance(repo, dict)]
    stamps = [stamp for stamp in stamps if stamp is not None]
    if not stamps:
        return _now_iso()
    return max(stamps).isoformat()


def _github_source_state(snapshot: dict, rows: list[dict]) -> str:
    """Mirror /api/remote-activity: unavailable only with no cache or a failed client."""
    state = snapshot.get('state', 'not_configured')
    repositories = snapshot.get('repositories') or []
    if state in ('not_configured', 'invalid_config'):
        return state
    if state == 'unavailable' and not repositories:
        return 'unavailable'
    if rows:
        if state in ('connected', 'loading'):
            return 'connected'
        return 'partial'
    if repositories:
        if state in ('connected', 'partial', 'loading'):
            return 'connected' if state in ('connected', 'loading') else 'partial'
        return 'empty'
    if state == 'unavailable':
        return 'unavailable'
    return 'empty'


def _github_rows(root: Path) -> tuple[list[dict], dict]:
    snapshot = remote_snapshot(root)
    state = snapshot.get('state', 'not_configured')
    repositories = [repo for repo in (snapshot.get('repositories') or []) if isinstance(repo, dict)]
    observed = _github_cache_observed(snapshot) if repositories else _now_iso()
    detail = str(snapshot.get('error') or '')
    if state in ('not_configured', 'invalid_config'):
        return [], {'name': 'github', 'state': state, 'observed_at': observed,
                    'detail': detail or 'GitHub delivery is not configured.'}
    if state == 'unavailable' and not repositories:
        return [], {'name': 'github', 'state': 'unavailable', 'observed_at': observed,
                    'detail': detail or 'GitHub delivery is unavailable.'}
    rows = []
    for repo in repositories:
        project = str(repo.get('project') or '')
        for item in repo.get('items') or []:
            if not isinstance(item, dict):
                continue
            at = item.get('updated_at')
            if not at or not _in_window(at):
                continue
            url = str(item.get('url') or '')
            # A PR and its CI runs share the same head commit (verified by
            # GitHub, not inferred from prose/time); group them on that sha
            # so a "PR opened → CI passed → merged" run reads as one story
            # (pc-1488 Done-when). Releases carry no head sha and stay
            # ungrouped.
            sha = str(item.get('sha') or '') if item.get('kind') in ('pull_request', 'workflow') else ''
            rows.append({
                'id': f'github:{repo.get("repo")}:{_github_kind_key(item)}:{_normalize_at(at)}',
                'at': _normalize_at(at),
                'source': 'github',
                'project': project,
                'actor': 'GitHub',
                **_github_event_word(item),
                'title': str(item.get('title') or repo.get('repo') or 'Repository event'),
                'link': {'href': url, 'label': str(item.get('repo') or repo.get('repo') or 'PR'), 'external': True},
                'group_key': f'github:{repo.get("repo")}:{sha}' if sha else '',
            })
    repo_state = _github_source_state(snapshot, rows)
    return rows, {'name': 'github', 'state': repo_state, 'observed_at': observed, 'detail': detail}


def _sort_key(row: dict) -> tuple:
    stamp = _parse_time(row.get('at')) or datetime.min.replace(tzinfo=timezone.utc)
    return (stamp, row.get('id', ''))


def _apply_filters(rows: list[dict], *, project: str, source: str, actor: str) -> list[dict]:
    filtered = rows
    if project:
        filtered = [r for r in filtered if r.get('project') == project]
    if source:
        filtered = [r for r in filtered if r.get('source') == source]
    if actor:
        want = actor.lower()
        filtered = [r for r in filtered if str(r.get('actor', '')).lower() == want]
    return filtered


def timeline_snapshot(root: Path | None, *, project: str = '', source: str = '', actor: str = '',
                      cursor: str = '') -> dict:
    if root is None:
        return {'rows': [], 'next_cursor': None, 'sources': [], 'filters': {'project': project, 'source': source, 'actor': actor}}
    root = Path(root).resolve()
    merged: list[dict] = []
    sources: list[dict] = []
    for reader in (_worklane_rows, _workforce_rows, _supervisor_rows, _github_rows):
        part, meta = reader(root)
        merged.extend(part)
        sources.append(meta)
    merged.sort(key=_sort_key, reverse=True)
    merged = _apply_filters(merged, project=project, source=source, actor=actor)
    decoded = _decode_cursor(cursor)
    if decoded is not None:
        cursor_at, cursor_id = decoded
        start = 0
        for index, row in enumerate(merged):
            if row['at'] == cursor_at and row['id'] == cursor_id:
                start = index + 1
                break
            if row['at'] < cursor_at:
                start = index
                break
        merged = merged[start:]
    page = merged[:PAGE_SIZE]
    next_cursor = _encode_cursor(page[-1]) if len(merged) > PAGE_SIZE and page else None
    return {
        'rows': page,
        'next_cursor': next_cursor,
        'sources': sources,
        'filters': {'project': project, 'source': source, 'actor': actor},
    }
