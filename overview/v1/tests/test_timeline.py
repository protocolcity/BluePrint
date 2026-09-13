import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from server.timeline import (
    PAGE_SIZE,
    _comment_event_word,
    _decode_cursor,
    _encode_cursor,
    _event_word,
    timeline_snapshot,
)

_RECENT = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
_OLD = (datetime.now(timezone.utc) - timedelta(days=20)).strftime('%Y-%m-%dT%H:%M:%SZ')


class TimelineMappingTests(unittest.TestCase):
    def test_event_word_mapping(self):
        self.assertEqual(_event_word('created', None), 'filed')
        self.assertEqual(_event_word('status_change', 'in_progress'), 'claimed')
        self.assertEqual(_event_word('status_change', 'in_review'), 'parked')
        self.assertEqual(_event_word('status_change', 'done'), 'closed')

    def test_comment_word_mapping(self):
        self.assertEqual(_comment_event_word('Intake: filed by you'), 'filed')
        self.assertEqual(_comment_event_word('Owner: seat\nStart: now'), 'claimed')
        self.assertEqual(_comment_event_word('Parked: waiting'), 'parked')
        self.assertEqual(_comment_event_word('Released by seat'), 'released')
        self.assertEqual(_comment_event_word('Completed: done'), 'closed')
        self.assertEqual(_comment_event_word('Blocked: needs credentials'), 'gated')
        self.assertEqual(_comment_event_word('A regular note'), 'note')

    def test_cursor_round_trip(self):
        row = {'at': _RECENT, 'id': 'worklane:product:evt:1'}
        token = _encode_cursor(row)
        decoded = _decode_cursor(token)
        self.assertEqual(decoded, (_RECENT, row['id']))


class TimelineProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _register(self, slug='product', prefix='pc'):
        manifest = self.root / slug / '.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': slug, 'prefix': prefix, 'display': slug}))

    def _db(self, slug='product'):
        data = self.root / 'worklane/worklane/local/data'
        data.mkdir(parents=True, exist_ok=True)
        return data / f'{slug}.db'

    def test_worklane_event_and_comment_rows_merge_newest_first(self):
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, NULL, "Older task")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"created",NULL,"you",?)', (_OLD,))
            conn.execute('INSERT INTO task_events VALUES(2,1,"status_change","in_progress","seat",?)', (_RECENT,))
            conn.execute('INSERT INTO task_comments VALUES(1,1,"A note","seat",?)', (_RECENT,))
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 2)
        self.assertEqual(worklane[0]['event'], 'claimed')
        self.assertEqual(worklane[1]['event'], 'note')
        self.assertEqual(result['sources'][0]['name'], 'worklane')
        self.assertEqual(result['sources'][0]['state'], 'available')

    def test_workforce_ledger_maps_shift_rows(self):
        runtime = self.root / 'workforce/local'
        (runtime / 'ledger').mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {}}))
        (runtime / 'daemon.json').write_text(json.dumps({'last_tick': _RECENT, 'in_flight': []}))
        (runtime / 'ledger/seat.log').write_text(
            f'{_RECENT} START identity=seat kind=lane budget_secs=1500\n'
            f'{_RECENT} CANDIDATE ticket=pc-9 project=product\n'
        )
        result = timeline_snapshot(self.root)
        workforce = [r for r in result['rows'] if r['source'] == 'workforce']
        self.assertEqual({r['event'] for r in workforce}, {'start', 'candidate'})
        self.assertEqual(workforce[0]['actor'], 'seat')

    def test_supervisor_unavailable_is_labelled(self):
        runtime = self.root / 'workforce/local'
        runtime.mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {'bp-supervisor': {'kind': 'job'}}}))
        result = timeline_snapshot(self.root)
        supervisor = next(s for s in result['sources'] if s['name'] == 'supervisor')
        self.assertIn(supervisor['state'], ('unavailable', 'not_configured'))

    def test_supervisor_pass_row_when_api_available(self):
        runtime = self.root / 'workforce/local'
        runtime.mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {'bp-supervisor': {'kind': 'job'}}}))
        deployment = self.root / 'local/workforce/deployment.json'
        deployment.parent.mkdir(parents=True)
        deployment.write_text(json.dumps({'api_origin': 'http://127.0.0.1:9999'}))
        payload = {'ok': True, 'passes': [{'generated_at': _RECENT, 'pass_outcome': 'dispatched', 'evidence_file': 'pass.json'}]}
        class _FakeResponse:
            def read(self):
                return json.dumps(payload).encode('utf-8')
        with patch('server.timeline.build_opener') as build_opener:
            build_opener.return_value.open.return_value.__enter__.return_value = _FakeResponse()
            result = timeline_snapshot(self.root)
        supervisor_rows = [r for r in result['rows'] if r['source'] == 'supervisor']
        self.assertEqual(len(supervisor_rows), 1)
        self.assertEqual(supervisor_rows[0]['event'], 'dispatched')

    def test_github_source_unavailable_when_not_configured(self):
        result = timeline_snapshot(self.root)
        github = next(s for s in result['sources'] if s['name'] == 'github')
        self.assertEqual(github['state'], 'not_configured')

    def test_project_filter(self):
        self._register('alpha', 'aa')
        self._register('beta', 'bb')
        for slug, title in (('alpha', 'Alpha task'), ('beta', 'Beta task')):
            with sqlite3.connect(self._db(slug)) as conn:
                conn.executescript(
                    'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                    'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                )
                conn.execute('INSERT INTO tasks VALUES(1, NULL, ?)', (title,))
                conn.execute('INSERT INTO task_events VALUES(1,1,"created",NULL,"you",?)', (_RECENT,))
        filtered = timeline_snapshot(self.root, project='beta')
        self.assertEqual(len(filtered['rows']), 1)
        self.assertEqual(filtered['rows'][0]['project'], 'beta')

    def test_cursor_paging(self):
        self._register('alpha', 'aa')
        with sqlite3.connect(self._db('alpha')) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
            )
            for index in range(PAGE_SIZE + 5):
                conn.execute('INSERT INTO tasks VALUES(?, NULL, ?)', (index + 1, f'Task {index}'))
                conn.execute(
                    'INSERT INTO task_events VALUES(?, ?, "created", NULL, "you", ?)',
                    (index + 1, index + 1, _RECENT),
                )
        page1 = timeline_snapshot(self.root, project='alpha')
        self.assertEqual(len(page1['rows']), PAGE_SIZE)
        self.assertTrue(page1['next_cursor'])
        page2 = timeline_snapshot(self.root, project='alpha', cursor=page1['next_cursor'])
        self.assertEqual(len(page2['rows']), 5)
        self.assertIsNone(page2['next_cursor'])
