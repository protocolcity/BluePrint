"""Read selected workspace stores with its installed WorkLane readiness policy.

The engine opens disposable SQLite backups only; the originals are read-only.
Run by open_work_audit using the selected workspace's WorkLane interpreter.
"""
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from contextlib import closing


def snapshot(root):
    from worklane.devqueue.queue import WorkQueue
    from worklane.trackers.sqlite import SQLiteTracker

    root = Path(root).resolve()
    result = {'stores': [], 'tasks': {}, 'errors': {}, 'desk_urls': {}}
    registry = {}
    for path in sorted(root.glob('*/.protocolcity/desk-join.json')):
        if not path.resolve().is_relative_to(root):
            raise ValueError('Project registration outside selected workspace')
        row = json.loads(path.read_text())
        if not isinstance(row, dict):
            raise ValueError('Invalid project registration')
        slug = row.get('slug', '')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', slug):
            raise ValueError('Invalid project registration')
        if slug in registry:
            raise ValueError('Duplicate project registration: ' + slug)
        registry[slug] = row
        result['desk_urls'][slug] = row.get('desk_url', '')
    if not registry:
        raise ValueError('No registered projects in selected workspace')
    with tempfile.TemporaryDirectory(prefix='bp-audit-') as temporary:
        for slug in registry:
            source = root / 'worklane/worklane/local/data' / (slug + '.db')
            try:
                if not source.resolve().is_relative_to(root):
                    raise ValueError('Store outside selected workspace')
                target = Path(temporary) / (slug + '.db')
                with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as original:
                    with closing(sqlite3.connect(target)) as copy:
                        original.backup(copy)
                tracker = SQLiteTracker(db_path=target, product_default='product:' + slug)
                queue = WorkQueue(tracker)
                tasks = [t.to_dict() for t in queue.all_tasks]
                ready = [t.to_dict() for t in queue.ready()]
                tasks.sort(key=lambda t: str(t.get('updated_at') or ''), reverse=True)
                counts = Counter(t['status'] for t in tasks)
                result['stores'].append({'slug': slug, **counts, 'ready': len(ready)})
                result['tasks'][slug] = {'all': tasks, 'ready': ready}
            except (OSError, ValueError, sqlite3.Error) as exc:
                result['errors'][slug] = str(exc)
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(snapshot(sys.argv[1])))
    except Exception as exc:
        print(json.dumps({'error': str(exc)}))
        raise SystemExit(1)
