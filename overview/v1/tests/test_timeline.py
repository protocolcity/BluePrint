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
    _github_event_word,
    _ledger_event_word,
    _normalize_at,
    _supervisor_event_word,
    timeline_snapshot,
)

_RECENT = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
_RECENT_MICRO = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
_OLD = (datetime.now(timezone.utc) - timedelta(days=20)).strftime('%Y-%m-%dT%H:%M:%SZ')


class TimelineMappingTests(unittest.TestCase):
    def test_event_word_mapping(self):
        self.assertEqual(_event_word('created', None), {'event': 'filed'})
        self.assertEqual(_event_word('status_change', 'in_progress'), {'event': 'claimed'})
        self.assertEqual(_event_word('status_change', 'in_review'), {'event': 'parked'})
        self.assertEqual(_event_word('status_change', 'done'), {'event': 'closed'})

    def test_unmapped_event_word_falls_back_to_event_with_title(self):
        mapped = _event_word('label_change', 'urgent')
        self.assertEqual(mapped['event'], 'event')
        self.assertEqual(mapped['event_title'], 'label_change/urgent')

    def test_comment_word_mapping(self):
        self.assertEqual(_comment_event_word('Intake: filed by you'), 'filed')
        self.assertEqual(_comment_event_word('Owner: seat\nStart: now'), 'claimed')
        self.assertEqual(_comment_event_word('Parked: waiting'), 'parked')
        self.assertEqual(_comment_event_word('Released by seat'), 'released')
        self.assertEqual(_comment_event_word('Completed: done'), 'closed')
        self.assertEqual(_comment_event_word('Blocked: needs credentials'), 'gated')
        self.assertEqual(_comment_event_word('A regular note'), 'note')

    def test_parked_body_with_embedded_owner_marker_reads_as_parked_not_claimed(self):
        # wl_park's real body shape (worklane write.py): "Parked: {reason}\n
        # Owner: {author}" — the Owner line is provenance, not a fresh claim
        # (pc-1488 Done-when: distinguish terminal completion/lifecycle
        # transitions from a claim marker embedded in the body).
        self.assertEqual(_comment_event_word('Parked: waiting on review\nOwner: bp-claude-implementer'), 'parked')
        self.assertEqual(_comment_event_word('Completed: shipped\nOwner: bp-claude-implementer'), 'closed')

    def test_ledger_event_word_mapping(self):
        self.assertEqual(_ledger_event_word('START', {}), {'event': 'started'})
        self.assertEqual(_ledger_event_word('START', {'recovery': '1'}), {'event': 'recovered'})
        self.assertEqual(_ledger_event_word('CANDIDATE', {}), {'event': 'dispatched'})
        self.assertEqual(_ledger_event_word('ERROR', {}), {'event': 'failed'})
        self.assertEqual(_ledger_event_word('SKIP', {}), {'event': 'skipped'})

    def test_supervisor_event_word_mapping(self):
        self.assertEqual(_supervisor_event_word('dispatched'), {'event': 'dispatched'})
        self.assertEqual(_supervisor_event_word('provider_failed'), {'event': 'failed'})
        self.assertEqual(_supervisor_event_word('stopped_by_operator'), {'event': 'released'})

    def test_github_event_word_mapping(self):
        self.assertEqual(_github_event_word({'kind': 'pull_request', 'pr_event': 'merged'}), {'event': 'merged'})
        self.assertEqual(_github_event_word({'kind': 'workflow', 'state': 'failure'}), {'event': 'failed'})
        self.assertEqual(_github_event_word({'kind': 'workflow', 'state': 'success'}), {'event': 'passed'})
        self.assertEqual(_github_event_word({'kind': 'release'}), {'event': 'released'})

    def test_normalize_at_canonical_utc(self):
        self.assertEqual(_normalize_at(_RECENT_MICRO), _RECENT)
        self.assertEqual(_normalize_at('2026-09-13T12:34:56.789Z'), '2026-09-13T12:34:56Z')

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
        self.assertEqual(worklane[0]['at'], _RECENT)
        self.assertEqual(worklane[1]['event'], 'note')
        self.assertEqual(result['sources'][0]['name'], 'worklane')
        self.assertEqual(result['sources'][0]['state'], 'available')

    def test_claim_event_and_owner_comment_collapse_to_one_row(self):
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, "pc-9", "Claim task")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"status_change","in_progress","seat",?)', (_RECENT,))
            conn.execute('INSERT INTO task_comments VALUES(1,1,?,"seat",?)',
                         ('Owner: seat\nStart: now', _RECENT))
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 1)
        self.assertEqual(worklane[0]['event'], 'claimed')
        self.assertEqual(worklane[0]['title'], 'Owner: seat')

    def test_extra_same_second_comment_is_not_dropped(self):
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, "pc-11", "Claim task")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"status_change","in_progress","seat",?)', (_RECENT,))
            conn.execute('INSERT INTO task_comments VALUES(1,1,?,"seat",?)',
                         ('Owner: seat\nStart: now', _RECENT))
            conn.execute('INSERT INTO task_comments VALUES(2,1,"Owner: seat\nAlso parked context","seat",?)', (_RECENT,))
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 2)
        self.assertEqual(worklane[0]['event'], 'claimed')
        self.assertEqual(worklane[0]['title'], 'Owner: seat')
        self.assertEqual(worklane[1]['event'], 'claimed')
        # The extra same-second comment never pairs with an event, but it
        # must still get the same first-line title / full-body detail split
        # as a merged row — never the whole multiline body as the bold
        # headline (pc-1488 cursor-reviewer finding #1).
        self.assertEqual(worklane[1]['title'], 'Owner: seat')
        self.assertEqual(worklane[1]['detail'], 'Owner: seat\nAlso parked context')

    def test_merged_row_keeps_full_comment_behind_detail(self):
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, "pc-12", "Blocked task")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"status_change","backlog","seat",?)', (_RECENT,))
            conn.execute('INSERT INTO task_comments VALUES(1,1,?,"seat",?)',
                         ('Released by seat returning to backlog\nWaiting on credentials from ops.', _RECENT))
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 1)
        self.assertEqual(worklane[0]['title'], 'Released by seat returning to backlog')
        self.assertEqual(worklane[0]['detail'],
                          'Released by seat returning to backlog\nWaiting on credentials from ops.')

    def test_unmerged_long_parked_comment_gets_title_and_detail(self):
        """No same-second event exists to pair with (e.g. a background sweep
        wrote the comment without a matching status_change row): the comment
        must still split into a short first-line title with the full body
        reachable behind detail, not one giant bold headline (pc-1488
        cursor-reviewer finding #1)."""
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, "pc-13", "Parked task")')
            conn.execute(
                'INSERT INTO task_comments VALUES(1,1,?,"seat",?)',
                ('Parked: Implementation complete; both suites green.\nOwner: seat', _RECENT),
            )
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 1)
        self.assertEqual(worklane[0]['title'], 'Parked: Implementation complete; both suites green.')
        self.assertEqual(
            worklane[0]['detail'],
            'Parked: Implementation complete; both suites green.\nOwner: seat',
        )

    def test_release_event_and_released_comment_collapse_to_one_row(self):
        self._register()
        with sqlite3.connect(self._db()) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, "pc-10", "Release task")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"status_change","backlog","seat",?)', (_RECENT,))
            conn.execute('INSERT INTO task_comments VALUES(1,1,"Released by seat returning to backlog","seat",?)', (_RECENT,))
        result = timeline_snapshot(self.root)
        worklane = [r for r in result['rows'] if r['source'] == 'worklane']
        self.assertEqual(len(worklane), 1)
        self.assertEqual(worklane[0]['event'], 'released')
        self.assertEqual(worklane[0]['title'], 'Released by seat returning to backlog')

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
        self.assertEqual({r['event'] for r in workforce}, {'started', 'dispatched'})
        self.assertEqual(workforce[0]['actor'], 'seat')
        self.assertEqual(workforce[0]['at'], _RECENT)

    def test_workforce_ledger_reads_bounded_tail_only(self):
        runtime = self.root / 'workforce/local'
        (runtime / 'ledger').mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {}}))
        (runtime / 'daemon.json').write_text(json.dumps({'last_tick': _RECENT, 'in_flight': []}))
        ledger = runtime / 'ledger/seat.log'
        padding = 'x' * 20000
        ledger.write_text(
            f'{_OLD} START identity=seat kind=lane budget_secs=1500\n'
            f'{padding}\n'
            f'{_RECENT} ERROR identity=seat reason=tail-only\n'
        )
        result = timeline_snapshot(self.root)
        workforce = [r for r in result['rows'] if r['source'] == 'workforce']
        self.assertEqual(len(workforce), 1)
        self.assertEqual(workforce[0]['event'], 'failed')

    def test_workforce_ticket_resolves_blank_project_from_registered_prefix(self):
        self._register('product', 'pc')
        sqlite3.connect(self._db('product')).close()
        runtime = self.root / 'workforce/local'
        (runtime / 'ledger').mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {}}))
        (runtime / 'daemon.json').write_text(json.dumps({'last_tick': _RECENT, 'in_flight': []}))
        # No project= field on the ledger line (the observed pc-1480 gap):
        # the ticket's own id prefix must resolve it against the registry.
        (runtime / 'ledger/seat.log').write_text(f'{_RECENT} CANDIDATE ticket=pc-9\n')
        result = timeline_snapshot(self.root)
        workforce = [r for r in result['rows'] if r['source'] == 'workforce']
        self.assertEqual(len(workforce), 1)
        self.assertEqual(workforce[0]['project'], 'product')
        self.assertEqual(workforce[0]['link'], {'href': '/work-order?project=product&id=pc-9', 'label': 'pc-9'})
        self.assertEqual(workforce[0]['group_key'], 'workforce:seat:pc-9')

    def test_workforce_ticket_with_unresolvable_project_gets_no_ambiguous_link(self):
        runtime = self.root / 'workforce/local'
        (runtime / 'ledger').mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {}}))
        (runtime / 'daemon.json').write_text(json.dumps({'last_tick': _RECENT, 'in_flight': []}))
        (runtime / 'ledger/seat.log').write_text(f'{_RECENT} CANDIDATE ticket=zz-9\n')
        result = timeline_snapshot(self.root)
        workforce = [r for r in result['rows'] if r['source'] == 'workforce']
        self.assertEqual(len(workforce), 1)
        self.assertEqual(workforce[0]['project'], '')
        self.assertEqual(workforce[0]['link'], {'href': '/agents', 'label': 'zz-9'})

    def test_workforce_rows_capped_per_source(self):
        runtime = self.root / 'workforce/local'
        (runtime / 'ledger').mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {}}))
        (runtime / 'daemon.json').write_text(json.dumps({'last_tick': _RECENT, 'in_flight': []}))
        lines = [f'{_RECENT} START identity=seat kind=lane budget_secs=1500 ticket=pc-{index}\n'
                 for index in range(12)]
        (runtime / 'ledger/seat.log').write_text(''.join(lines))
        with patch('server.timeline.SOURCE_ROW_CAP', 5):
            result = timeline_snapshot(self.root)
        workforce = [r for r in result['rows'] if r['source'] == 'workforce']
        self.assertEqual(len(workforce), 5)

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
        self.assertEqual(supervisor_rows[0]['at'], _RECENT)

    def test_supervisor_row_title_is_outcome_only_not_source_repeated(self):
        """The source badge already reads "Supervisor"; the title must not
        repeat it (pc-1488 cursor-reviewer finding #3: headline read
        "Passed · Supervisor pass · passed")."""
        runtime = self.root / 'workforce/local'
        runtime.mkdir(parents=True)
        (runtime / 'roster.json').write_text(json.dumps({'workers': {'bp-supervisor': {'kind': 'job'}}}))
        deployment = self.root / 'local/workforce/deployment.json'
        deployment.parent.mkdir(parents=True)
        deployment.write_text(json.dumps({'api_origin': 'http://127.0.0.1:9999'}))
        payload = {'ok': True, 'passes': [
            {'generated_at': _RECENT, 'pass_outcome': 'passed', 'evidence_file': 'pass.json'},
            {'generated_at': _RECENT, 'pass_outcome': 'provider_failed', 'evidence_file': 'fail.json',
             'dispatched': [{'worker': 'bp-claude-implementer', 'outcome': 'failed'},
                            {'worker': 'bp-cursor-implementer', 'outcome': 'exception'}]},
        ]}
        class _FakeResponse:
            def read(self):
                return json.dumps(payload).encode('utf-8')
        with patch('server.timeline.build_opener') as build_opener:
            build_opener.return_value.open.return_value.__enter__.return_value = _FakeResponse()
            result = timeline_snapshot(self.root)
        supervisor_rows = [r for r in result['rows'] if r['source'] == 'supervisor']
        self.assertEqual(len(supervisor_rows), 2)
        for row in supervisor_rows:
            self.assertNotIn('Supervisor', row['title'])
            # The title must not repeat the action word the headline already
            # carries from the outcome (second-pass finding: "Passed · Passed").
            self.assertNotEqual(row['title'].lower(), str(row['event']).replace('_', ' ').lower())
        titles = {row['title'] for row in supervisor_rows}
        self.assertEqual(titles, {
            'no seat dispatched',
            '2 seats · bp-claude-implementer failed, bp-cursor-implementer exception',
        })

    def test_github_source_unavailable_when_not_configured(self):
        result = timeline_snapshot(self.root)
        github = next(s for s in result['sources'] if s['name'] == 'github')
        self.assertEqual(github['state'], 'not_configured')

    def test_github_source_available_when_remote_cache_has_rows(self):
        config = self.root / '.blueprint/connections.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'github': {'repositories': [{'repo': 'org/repo', 'project': 'product'}]}}))
        cache_fill = '2026-09-13T08:15:00+00:00'
        cached = {
            'state': 'loading',
            'repositories': [{
                'repo': 'org/repo',
                'project': 'product',
                'state': 'connected',
                'observed_at': cache_fill,
                'items': [{
                    'kind': 'pull_request',
                    'repo': 'org/repo',
                    'project': 'product',
                    'title': 'Ship it',
                    'url': 'https://github.com/org/repo/pull/1',
                    'state': 'open',
                    'pr_event': 'opened',
                    'updated_at': _RECENT,
                    'number': 1,
                }],
            }],
            'refreshing': True,
        }
        with patch('server.timeline.remote_snapshot', return_value=cached), \
                patch('server.timeline._now_iso', return_value='2026-09-13T12:00:00+00:00'):
            result = timeline_snapshot(self.root)
        github = next(s for s in result['sources'] if s['name'] == 'github')
        self.assertEqual(github['state'], 'connected')
        self.assertEqual(github['observed_at'], cache_fill)
        rows = [r for r in result['rows'] if r['source'] == 'github']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Ship it')

    def test_github_pr_and_ci_run_group_by_shared_head_sha(self):
        cached = {
            'state': 'connected',
            'repositories': [{
                'repo': 'org/repo',
                'project': 'product',
                'state': 'connected',
                'observed_at': _RECENT,
                'items': [
                    {'kind': 'pull_request', 'repo': 'org/repo', 'project': 'product', 'title': 'Ship it',
                     'url': 'https://github.com/org/repo/pull/1', 'state': 'open', 'pr_event': 'opened',
                     'updated_at': _RECENT, 'number': 1, 'sha': 'abc123'},
                    {'kind': 'workflow', 'repo': 'org/repo', 'project': 'product', 'title': 'CI',
                     'url': 'https://github.com/org/repo/actions/runs/2', 'state': 'success',
                     'workflow_name': 'CI', 'updated_at': _RECENT, 'sha': 'abc123'},
                    {'kind': 'release', 'repo': 'org/repo', 'project': 'product', 'title': 'v1',
                     'url': 'https://github.com/org/repo/releases/tag/v1', 'updated_at': _RECENT},
                ],
            }],
            'refreshing': False,
        }
        with patch('server.timeline.remote_snapshot', return_value=cached):
            result = timeline_snapshot(self.root)
        rows = {r['title']: r for r in result['rows'] if r['source'] == 'github'}
        self.assertEqual(rows['Ship it']['group_key'], 'github:org/repo:abc123')
        self.assertEqual(rows['CI']['group_key'], 'github:org/repo:abc123')
        self.assertEqual(rows['v1']['group_key'], '')

    def test_github_observed_at_uses_stale_cache_fill_on_failed_refresh(self):
        cache_fill = '2026-09-13T07:00:00+00:00'
        cached = {
            'state': 'partial',
            'repositories': [{
                'repo': 'org/repo',
                'project': 'product',
                'state': 'unavailable',
                'observed_at': cache_fill,
                'items': [{
                    'kind': 'pull_request',
                    'repo': 'org/repo',
                    'project': 'product',
                    'title': 'Stale PR',
                    'url': 'https://github.com/org/repo/pull/2',
                    'state': 'open',
                    'pr_event': 'opened',
                    'updated_at': _RECENT,
                    'number': 2,
                }],
            }],
            'refreshing': False,
            'error': 'Unable to read GitHub.',
        }
        with patch('server.timeline.remote_snapshot', return_value=cached), \
                patch('server.timeline._now_iso', return_value='2026-09-13T12:00:00+00:00'):
            result = timeline_snapshot(self.root)
        github = next(s for s in result['sources'] if s['name'] == 'github')
        self.assertEqual(github['state'], 'partial')
        self.assertEqual(github['observed_at'], cache_fill)

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

    def test_cursor_paging_with_mixed_iso_timestamps(self):
        self._register('alpha', 'aa')
        with sqlite3.connect(self._db('alpha')) as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
            )
            conn.execute('INSERT INTO tasks VALUES(1, NULL, "First")')
            conn.execute('INSERT INTO tasks VALUES(2, NULL, "Second")')
            conn.execute('INSERT INTO task_events VALUES(1,1,"created",NULL,"you",?)', (_RECENT_MICRO,))
            conn.execute('INSERT INTO task_events VALUES(2,2,"created",NULL,"you",?)', (_RECENT,))
        page1 = timeline_snapshot(self.root, project='alpha')
        self.assertEqual(len(page1['rows']), 2)
        self.assertEqual(page1['rows'][0]['at'], _RECENT)
        self.assertEqual(page1['rows'][1]['at'], _RECENT)
        cursor = _encode_cursor(page1['rows'][0])
        page2 = timeline_snapshot(self.root, project='alpha', cursor=cursor)
        self.assertEqual(len(page2['rows']), 1)
        self.assertEqual(page2['rows'][0]['title'], 'First')
