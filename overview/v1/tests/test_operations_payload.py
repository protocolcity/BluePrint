"""operations snapshot payload budget and surface key subsets."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from server.operations import operations_snapshot, task_comment_index
from server.operations_surface import (
    FORBIDDEN_SURFACE_KEYS,
    OVERVIEW_ORDER_KEYS,
    PAYLOAD_BASELINE_BYTES,
    WORK_ORDER_REQUIRED_KEYS,
    project_operations_surface,
)


def _seed_compact_workspace(root: Path, projects: int = 12, open_each: int = 100) -> None:
    data = root / 'worklane' / 'worklane' / 'local' / 'data'
    data.mkdir(parents=True)
    for index in range(projects):
        slug = f'proj{index:02d}'
        prefix = f'p{index:02d}'
        manifest = root / slug / '.protocolcity' / 'desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({
            'slug': slug, 'prefix': prefix, 'display': f'Project {index:02d}',
        }))
        with sqlite3.connect(data / f'{slug}.db') as conn:
            conn.executescript(
                'CREATE TABLE tasks('
                'id INTEGER, ext_id TEXT, title TEXT, status TEXT, priority INTEGER, '
                'updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);'
                'CREATE TABLE task_comments('
                'id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            open_rows = []
            comments = []
            comment_id = 1
            for number in range(1, open_each + 1):
                status = 'in_progress' if number % 20 == 0 else 'backlog'
                labels = '["worker:agent"]' if status == 'in_progress' else '[]'
                open_rows.append((
                    number, None, f'Order {number:03d}', status, 3,
                    '2026-09-12T00:00:00Z', labels, None, None,
                ))
                if number % 10 == 0:
                    comments.append((
                        comment_id, number, 'Progress: compact note', 'agent',
                        '2026-09-12T01:00:00Z',
                    ))
                    comment_id += 1
                if status == 'in_progress':
                    comments.append((
                        comment_id, number,
                        'Owner: agent\nStart: 2026-09-12T02:00:00Z', 'agent',
                        '2026-09-12T02:00:00Z',
                    ))
                    comment_id += 1
            done_start = open_each + 1
            for number in range(done_start, done_start + 5):
                open_rows.append((
                    number, None, f'Done {number}', 'done', 3,
                    '2026-09-11T00:00:00Z', '[]', None, None,
                ))
                for extra in range(20):
                    comments.append((
                        comment_id, number, f'Closed history {extra}', 'agent',
                        f'2026-09-11T00:{extra:02d}:00Z',
                    ))
                    comment_id += 1
            conn.executemany(
                'INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)', open_rows,
            )
            conn.executemany(
                'INSERT INTO task_comments VALUES(?,?,?,?,?)', comments,
            )


class OperationsPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_twelve_by_hundred_surfaces_beat_the_recorded_budget(self):
        _seed_compact_workspace(self.root)
        started = time.perf_counter()
        snapshot = operations_snapshot(self.root)
        snapshot_ms = (time.perf_counter() - started) * 1000
        self.assertEqual(len(snapshot['orders']), 1200)
        full = json.dumps(snapshot).encode('utf-8')
        overview = json.dumps(project_operations_surface(snapshot, 'overview')).encode('utf-8')
        work = json.dumps(project_operations_surface(snapshot, 'work')).encode('utf-8')
        # Recorded budget: 887KB for 1200 compact orders. Surfaces
        # must shrink Work/Overview bytes without dropping required fields.
        self.assertLess(len(overview), len(full),
                        f'overview={len(overview)} full={len(full)} snapshot_ms={snapshot_ms:.1f}')
        self.assertLess(len(work), len(full),
                        f'work={len(work)} full={len(full)} snapshot_ms={snapshot_ms:.1f}')
        self.assertLess(len(overview), PAYLOAD_BASELINE_BYTES,
                        f'overview={len(overview)} baseline={PAYLOAD_BASELINE_BYTES}')
        self.assertLess(len(work), PAYLOAD_BASELINE_BYTES,
                        f'work={len(work)} baseline={PAYLOAD_BASELINE_BYTES}')
        self.assertGreater(len(full), 100_000)
        self.assertLess(snapshot_ms, 15_000)

    def test_overview_and_work_payload_keys(self):
        _seed_compact_workspace(self.root, projects=2, open_each=10)
        snapshot = operations_snapshot(self.root)
        original_canvas = snapshot.get('agents_canvas')
        overview = project_operations_surface(snapshot, 'overview')
        work = project_operations_surface(snapshot, 'work')
        for key in FORBIDDEN_SURFACE_KEYS:
            self.assertNotIn(key, overview)
            self.assertNotIn(key, work)
        self.assertIn('throughput', overview)
        self.assertNotIn('work_flow', overview)
        self.assertIn('work_flow', work)
        self.assertNotIn('throughput', work)
        self.assertIn('orders', overview)
        self.assertIn('orders', work)
        self.assertTrue(overview['orders'])
        self.assertTrue(work['orders'])
        for order in overview['orders']:
            self.assertTrue(set(OVERVIEW_ORDER_KEYS).issuperset(order))
            for key in ('id', 'project', 'project_name', 'title', 'status', 'needs_routing'):
                self.assertIn(key, order)
            self.assertNotIn('last_note', order)
            self.assertNotIn('blockers', order)
            self.assertNotIn('face_reason', order)
        for order in work['orders']:
            self.assertTrue(set(WORK_ORDER_REQUIRED_KEYS).issubset(order))
            self.assertNotIn('attention', order)
            self.assertNotIn('priority', order)
        noted = [row for row in snapshot['orders'] if row.get('last_note')]
        self.assertTrue(noted)
        work_by_id = {row['id']: row for row in work['orders']}
        for row in noted:
            self.assertEqual(work_by_id[row['id']]['last_note'], row['last_note'])
        self.assertEqual(snapshot.get('agents_canvas'), original_canvas)
        self.assertIsNot(overview, snapshot)
        overview['orders'] = []
        self.assertTrue(snapshot['orders'])

    def test_unknown_surface_keeps_the_full_snapshot(self):
        _seed_compact_workspace(self.root, projects=1, open_each=2)
        snapshot = operations_snapshot(self.root)
        self.assertIs(project_operations_surface(snapshot, ''), snapshot)
        self.assertIs(project_operations_surface(snapshot, 'map'), snapshot)
        self.assertIn('agents_canvas', snapshot)
        self.assertIn('work_dates', snapshot)

    def test_comment_index_uses_loaded_ids_and_keeps_owner_semantics(self):
        _seed_compact_workspace(self.root, projects=1, open_each=4)
        path = self.root / 'worklane' / 'worklane' / 'local' / 'data' / 'proj00.db'
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                "INSERT INTO task_comments VALUES(900,1,'Owner: first\nStart: t','first','2026-09-12T03:00:00Z')"
            )
            conn.execute(
                "INSERT INTO task_comments VALUES(901,1,'Released by first — returning','first','2026-09-12T04:00:00Z')"
            )
            conn.execute(
                "INSERT INTO task_comments VALUES(902,1,'Owner: second\nStart: t','second','2026-09-12T05:00:00Z')"
            )
            conn.execute(
                "INSERT INTO task_comments VALUES(903,5,'Owner: done-seat\nStart: t','done-seat','2026-09-11T12:00:00Z')"
            )
            conn.commit()
            owners, notes, parked = task_comment_index(conn, [1, 2, 3, 4])
        self.assertEqual(owners[1]['identity'], 'second')
        self.assertNotIn(5, owners)
        self.assertNotIn(5, notes)
        self.assertTrue(notes[1].startswith('Owner: second'))
        self.assertEqual(parked, {})


if __name__ == '__main__':
    unittest.main()
