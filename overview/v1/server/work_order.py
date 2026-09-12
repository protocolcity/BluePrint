"""Read work orders from the selected workspace without initializing stores."""
from contextlib import closing
import json
import re
import sqlite3
from pathlib import Path
from .local_projectors import worklane_data_dir
from .operations import project_registry
from urllib.parse import urlencode


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
            result.append({'label':value, 'href':'/map?'+urlencode(params),
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
