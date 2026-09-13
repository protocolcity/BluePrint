"""Read work orders from the selected workspace without initializing stores."""
from contextlib import closing
import json
import re
import sqlite3
from pathlib import Path
from .local_projectors import worklane_data_dir
from .markdown import render_reader_content
from .operations import project_registry
from urllib.parse import urlencode

_STATUS_WORD = {
    'backlog': 'Open',
    'in_progress': 'Live',
    'in_review': 'Parked',
    'done': 'Done',
    'canceled': 'Canceled',
    'cancelled': 'Canceled',
}

_PROJECTION_KEYS = (
    'status_word', 'gate_type', 'gate_expired', 'gate_note', 'gate_until',
    'needs_routing', 'owner', 'live_with', 'parked_by', 'since', 'parent',
    'blockers', 'blocked_on', 'blocked_note', 'ready_for', 'persona',
    'assigned_you', 'last_note', 'attention_face',
)


def source_references(root, project, description):
    """Resolve existing Where paths; never turn arbitrary text into executable links."""
    from .workspace_search import permitted
    root=Path(root).resolve()
    registry=project_registry(root)
    folder=root/registry[project]['folder']
    section=re.search(r'(?ims)^\s*(?:#{1,6}\s*)?where\s*:?[ \t]*\n(.*?)(?=^\s*#{1,6}\s|\Z)', description or '')
    if not section:return []
    text=section.group(1)
    candidates=re.findall(r'`([^`]+)`|\[[^\]]+\]\(([^)]+)\)|([^\s·;,]+)',text)
    result=[];seen=set()
    for parts in candidates:
        value=next((p for p in parts if p),'').strip(' .()')
        if not value or value in seen:continue
        for candidate in (root/value,folder/value):
            if not permitted(root,candidate) or not candidate.exists():continue
            relative=str(candidate.resolve().relative_to(root.resolve()))
            is_paper=candidate.is_file() and candidate.suffix.lower()=='.md'
            directory=relative if candidate.is_dir() else str(Path(relative).parent)
            if directory == '.':directory=''
            params={'path':directory}
            if is_paper:params['md']=relative
            result.append({'label':value, 'path':relative, 'href':'/map?'+urlencode(params),
                           'action':'Read paper' if is_paper else 'Open folder'})
            seen.add(value);break
    return result


def read_work_order(binder: Path | None, project: str, order_id: str) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', order_id or ''):
        raise ValueError('A valid work-order id is required.')
    if project and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', project):
        raise ValueError('Invalid project.')
    if binder is None:
        raise FileNotFoundError('No workspace selected.')
    root = Path(binder).resolve()
    data = worklane_data_dir(root)
    prefixes = {}
    for manifest in root.glob('*/.protocolcity/desk-join.json'):
        if not manifest.resolve().is_relative_to(root):
            continue
        try:
            entry = json.loads(manifest.read_text())
            if entry.get('slug') and entry.get('prefix'):
                prefixes.setdefault(entry['slug'], set()).add(entry['prefix'].rstrip('-'))
        except (OSError, ValueError, AttributeError):
            continue
    matches = []
    if project and project not in prefixes:
        raise FileNotFoundError('Project is not registered in this workspace.')
    for path in sorted(data.glob('*.db')):
        if path.stem not in prefixes:
            continue
        if project and path.stem != project:
            continue
        if not path.resolve().is_relative_to(root):
            continue
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=0.5)) as conn:
            conn.row_factory = sqlite3.Row
            prefix, separator, number = order_id.rpartition('-')
            numeric_id = int(number) if separator and number.isdigit() and prefix in prefixes.get(path.stem, set()) else -1
            if project and order_id.isdigit():
                numeric_id = int(order_id)
            rows = conn.execute('SELECT * FROM tasks WHERE ext_id = ? OR id = ?', (order_id, numeric_id)).fetchall()
            for row in rows:
                item = dict(row)
                item['project'] = path.stem
                item['ext_id'] = item.get('ext_id') or order_id
                item['comments'] = [dict(c) for c in conn.execute(
                    'SELECT body, author, created_at FROM task_comments WHERE task_id = ? ORDER BY created_at, id',
                    (row['id'],))]
                item['references'] = source_references(root,path.stem,item.get('description',''))
                matches.append(item)
    if len(matches) > 1:
        raise ValueError('This id occurs in multiple projects. Include project in the link.')
    if not matches:
        raise FileNotFoundError('Work order not found in this workspace.')
    return matches[0]


def enrich_work_order(binder, order: dict) -> dict:
    """Merge the operations projection so the reader shows lifecycle, gate and blockers."""
    order['status_word'] = _STATUS_WORD.get(order.get('status') or '', order.get('status') or '')
    if not binder:
        return order
    try:
        from .operations import operations_snapshot
        snap = operations_snapshot(binder)
        ext_id = order.get('ext_id') or order.get('id')
        project = order.get('project')
        projected = next(
            (item for item in snap.get('orders', [])
             if item.get('id') == ext_id and item.get('project') == project),
            None,
        )
        if projected:
            for key in _PROJECTION_KEYS:
                if key in projected:
                    order[key] = projected[key]
        order['observed_at'] = snap.get('observed_at')
        order['project_name'] = next(
            (item.get('name') for item in snap.get('projects', []) if item.get('id') == project),
            project,
        )
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return order


def prepare_work_order(binder, project: str, order_id: str) -> dict:
    order = read_work_order(binder, project, order_id)
    enrich_work_order(binder, order)
    description = render_reader_content(order.get('description') or '')
    order['description_html'] = description['html']
    order['description_outline'] = description['outline']
    for comment in order.get('comments') or []:
        rendered = render_reader_content(comment.get('body') or '')
        comment['body_html'] = rendered['html']
    return order


def reveal_reference(binder, project, order_id, relative):
    """Reveal an existing permitted source reference; never open it for execution."""
    import subprocess
    import sys
    if sys.platform != 'darwin':
        raise RuntimeError('File-manager reveal is not available on this host. Use Open folder.')
    if not binder or not project:
        raise ValueError('An explicit workspace and project are required.')
    if not isinstance(relative,str) or not relative:
        raise ValueError('Choose an existing source reference.')
    order=read_work_order(binder,project,order_id)
    if relative not in {ref['path'] for ref in order['references']}:
        raise ValueError('This path is not a permitted source reference on the work order.')
    target=(Path(binder).resolve()/relative).resolve()
    from .workspace_search import permitted
    if not permitted(Path(binder).resolve(),target):
        raise ValueError('Source reference is outside the permitted workspace.')
    try:
        subprocess.run(['/usr/bin/open','-R',str(target)],check=True,capture_output=True,timeout=5)
    except (subprocess.SubprocessError,OSError) as exc:
        raise RuntimeError('The file manager could not reveal this reference.') from exc
    return {'ok':True}
