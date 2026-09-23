"""Query current registered stores and navigable workspace names, without recency caps."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlencode

from .operations import project_registry
from .local_projectors import worklane_data_dir

EXCLUDED = {'local', 'data', 'runtime', 'secrets', 'credentials', 'customers',
            'backups', 'node_modules', 'venv', '__pycache__', 'dist', 'build'}


def permitted(root, path):
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    return not any(p.startswith('.') or p.lower() in EXCLUDED for p in relative.parts)


def find(binder, query, offset=0, limit=50, project=''):
    if not binder:
        raise ValueError('No workspace selected.')
    q = str(query).strip().casefold()
    if not q or len(q) > 200:
        raise ValueError('Enter between 1 and 200 characters.')
    offset = max(0, int(offset))
    limit = max(1, min(100, int(limit)))
    root = Path(binder).resolve()
    registry = project_registry(root)
    hits, issues = [], []
    for slug, info in registry.items():
        path = worklane_data_dir(root) / (slug + '.db')
        if not path.is_file() or not path.resolve().is_relative_to(root):
            issues.append(info['name'] + ': work store unavailable')
            continue
        try:
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=.5)) as db:
                db.row_factory = sqlite3.Row
                columns = {r[1] for r in db.execute('PRAGMA table_info(tasks)')}
                identity = "COALESCE(NULLIF(ext_id,''), ? || CAST(id AS TEXT))" if 'ext_id' in columns else "? || CAST(id AS TEXT)"
                prefix = info['prefix'] + '-' if info['prefix'] else ''
                rows = db.execute('SELECT id,title,status,' + identity + ' AS identity FROM tasks WHERE instr(lower(COALESCE(title,\'\')),?)>0 OR instr(lower(' + identity + '),?)>0',
                                  (prefix, q, prefix, q)).fetchall()
                for row in rows:
                    hits.append({'kind':'Work order', 'title':row['title'] or row['identity'],
                                 'identity':row['identity'], 'project':slug,
                                 'detail':info['name'] + ' · ' + row['identity'] + ' · ' + row['status'],
                                 'href':'/work-order?' + urlencode({'project':slug,'id':row['identity']})})
        except (OSError, sqlite3.Error):
            issues.append(info['name'] + ': work store unreadable')

    # Search names, not file contents. Do not traverse runtime/export archives,
    # hidden directories, symlinks, or dependency/build trees.
    roots = [root / item['folder'] for item in registry.values()]
    if (root / 'docs').is_dir():
        roots.append(root / 'docs')
    candidates = list(root.glob('*.md'))
    started, visited, incomplete = time.monotonic(), 0, False
    for base in roots:
        if not permitted(root, base) or base.is_symlink():
            continue
        candidates.append(base)
        for parent, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if permitted(root, Path(parent) / d) and not (Path(parent) / d).is_symlink())
            candidates.extend(Path(parent) / d for d in dirs if q in d.casefold())
            candidates.extend(Path(parent) / f for f in sorted(files) if f.lower().endswith('.md') and q in f.casefold())
            visited += len(dirs) + len(files)
            if visited > 100000 or time.monotonic() - started > 3:
                incomplete = True
                break
        if incomplete:
            break
    seen = set()
    for path in candidates:
        if q not in path.name.casefold() or not permitted(root, path) or path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if relative in seen:
            continue
        seen.add(relative)
        is_dir = path.is_dir()
        if not is_dir and not path.is_file():
            continue
        slug = next((key for key, value in registry.items() if relative == value['folder'] or relative.startswith(value['folder'] + '/')), '')
        hits.append({'kind':'Folder' if is_dir else 'Paper', 'title':path.name,
                     'identity':relative, 'project':slug, 'detail':relative,
                     'href':'/map?' + urlencode({'path':relative} if is_dir else {'md':relative,'path':str(Path(relative).parent) if Path(relative).parent != Path('.') else ''})})
    if incomplete:
        issues.append('File-name scan reached its time or size limit; narrow the query.')
    hits.sort(key=lambda h:(h['identity'].casefold() != q, h['project'] != project if project else False,
                            h['kind'] != 'Work order', h['title'].casefold(), h['identity']))
    return {'query':query, 'results':hits[offset:offset+limit], 'total':len(hits),
            'offset':offset, 'limit':limit, 'issues':issues,
            'scope':'Work titles and IDs across registered history; paper and folder names. Descriptions and comments are not searched. Runtime, hidden, dependency and archive trees are excluded.'}
