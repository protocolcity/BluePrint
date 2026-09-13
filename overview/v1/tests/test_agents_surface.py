"""D5: Agents surface — seats, jobs, supervisor as three groups (pc-1464).

Disposable-fixture tests for every badge state, grouping and ordering, the
supervisor panel (present, absent, unavailable), and the one-action rule.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from server.operations import operations_snapshot


class AgentsSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'workforce/local'
        self.runtime.mkdir(parents=True)
        (self.runtime / 'ledger').mkdir()

    def _daemon(self, in_flight=None, fresh=True):
        tick = datetime.now(timezone.utc) - (timedelta(seconds=0) if fresh else timedelta(hours=1))
        (self.runtime / 'daemon.json').write_text(json.dumps({'last_tick': tick.isoformat(), 'in_flight': in_flight or []}))

    def _roster(self, workers):
        (self.runtime / 'roster.json').write_text(json.dumps({'workers': workers}))

    @staticmethod
    def _stamp(delta):
        return (datetime.now(timezone.utc) - delta).strftime('%Y-%m-%dT%H:%M:%SZ')

    def _ledger(self, identity, text):
        (self.runtime / 'ledger' / (identity + '.log')).write_text(text)

    # ---- Badge vocabulary, one per state ----------------------------------

    def test_every_badge_state_and_source(self):
        self._daemon(fresh=True)
        self._roster({
            'working': {'display': 'Working seat', 'command': ['runner'], 'identity': 'working', 'kind': 'lane'},
            'idle': {'display': 'Idle seat', 'command': ['runner'], 'identity': 'idle', 'kind': 'lane'},
            'stale': {'display': 'Stale seat', 'command': ['runner'], 'identity': 'stale', 'kind': 'lane'},
            'failed': {'display': 'Failed seat', 'command': ['runner'], 'identity': 'failed', 'kind': 'lane'},
            'placeholder': {'display': 'Placeholder', 'command': ['true'], 'identity': 'placeholder', 'kind': 'job'},
            'off': {'display': 'Off', 'command': ['runner'], 'identity': 'off', 'kind': 'job', 'enabled': False},
        })
        started = self._stamp(timedelta(minutes=2))
        self._ledger('working', f'{started} START identity=working kind=lane budget_secs=1500\n')
        stopped = self._stamp(timedelta(minutes=1))
        self._ledger('idle', f'{started} START identity=idle kind=lane budget_secs=1500\n{stopped} STOP reason="single-pass complete"\n')
        very_old = self._stamp(timedelta(hours=3))
        self._ledger('stale', f'{very_old} START identity=stale kind=lane budget_secs=1500\n')
        errored = self._stamp(timedelta(minutes=1))
        self._ledger('failed', f'{started} START identity=failed kind=lane budget_secs=1500\n{errored} ERROR reason="agent exit" rc=1\n')
        by_id = {a['id']: a for a in operations_snapshot(self.root)['agents']}
        self.assertEqual(by_id['working']['badge'], 'WORKING')
        self.assertEqual(by_id['working']['badge_source'], 'engine ledger')
        self.assertEqual(by_id['idle']['badge'], 'IDLE')
        self.assertEqual(by_id['stale']['badge'], 'STALE SHIFT')
        self.assertEqual(by_id['failed']['badge'], 'LAST RUN FAILED')
        self.assertEqual(by_id['placeholder']['badge'], 'NOT CONFIGURED')
        self.assertEqual(by_id['off']['badge'], 'OFF')

    def test_lane_seat_with_empty_schedule_reads_off(self):
        """pc-1477 scope addition (4): wf-259's generator held state — a
        lane seat with schedule=='' is armed but held, off in the Agents
        surface, same as enabled=False."""
        self._daemon(fresh=True)
        self._roster({
            'held': {'display': 'Held seat', 'command': ['runner'], 'identity': 'held', 'kind': 'lane',
                     'schedule': ''},
        })
        by_id = {a['id']: a for a in operations_snapshot(self.root)['agents']}
        self.assertEqual(by_id['held']['badge'], 'OFF')

    def test_no_kind_seat_with_empty_schedule_reads_off(self):
        """review finding pc-1477: coverage and the Agents snapshot share one
        held predicate — a row with no ``kind`` (a seat, per the Seats group)
        carrying an empty schedule reads OFF here too, not just explicit
        ``kind: lane`` rows."""
        self._daemon(fresh=True)
        self._roster({
            'held': {'display': 'Held seat', 'command': ['runner'], 'identity': 'held', 'schedule': ''},
        })
        by_id = {a['id']: a for a in operations_snapshot(self.root)['agents']}
        self.assertEqual(by_id['held']['badge'], 'OFF')

    def test_unknown_badge_from_stale_heartbeat(self):
        self._roster({'agent': {'display': 'Agent', 'command': ['runner'], 'identity': 'agent', 'kind': 'lane'}})
        self._daemon(fresh=False)
        row = operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['badge'], 'UNKNOWN')
        self.assertEqual(row['badge_source'], 'daemon')

    # ---- Grouping and ordering ---------------------------------------------

    def test_seats_and_jobs_are_grouped_supervisor_excluded(self):
        self._daemon(fresh=True)
        self._roster({
            'seat-idle': {'display': 'Z seat', 'command': ['runner'], 'identity': 'seat-idle', 'kind': 'lane'},
            'seat-working': {'display': 'A seat', 'command': ['runner'], 'identity': 'seat-working', 'kind': 'lane'},
            'job-one': {'display': 'A job', 'command': ['runner'], 'identity': 'job-one', 'kind': 'job'},
            'bp-supervisor': {'display': 'Supervisor', 'command': ['runner'], 'identity': 'bp-supervisor', 'kind': 'job'},
        })
        started = self._stamp(timedelta(minutes=1))
        self._ledger('seat-working', f'{started} START identity=seat-working kind=lane budget_secs=1500\n')
        result = operations_snapshot(self.root)
        ids = [a['id'] for a in result['agents']]
        self.assertNotIn('bp-supervisor', ids)
        self.assertIsNotNone(result['supervisor'])
        self.assertEqual(result['supervisor']['id'], 'bp-supervisor')
        groups = {a['id']: a['group'] for a in result['agents']}
        self.assertEqual(groups['seat-idle'], 'seat')
        self.assertEqual(groups['seat-working'], 'seat')
        self.assertEqual(groups['job-one'], 'job')

    def test_rows_ordered_by_state_then_name(self):
        self._daemon(fresh=True)
        self._roster({
            'z-idle': {'display': 'Z idle', 'command': ['runner'], 'identity': 'z-idle', 'kind': 'lane'},
            'a-idle': {'display': 'A idle', 'command': ['runner'], 'identity': 'a-idle', 'kind': 'lane'},
            'working': {'display': 'Working', 'command': ['runner'], 'identity': 'working', 'kind': 'lane'},
        })
        started = self._stamp(timedelta(minutes=1))
        self._ledger('working', f'{started} START identity=working kind=lane budget_secs=1500\n')
        result = operations_snapshot(self.root)
        self.assertEqual([a['name'] for a in result['agents']], ['Working', 'A idle', 'Z idle'])

    # ---- One action per row -------------------------------------------------

    def test_one_action_per_row(self):
        self._daemon(fresh=True)
        self._roster({
            'working': {'display': 'Working', 'command': ['runner'], 'identity': 'working', 'kind': 'lane'},
            'idle': {'display': 'Idle', 'command': ['runner'], 'identity': 'idle', 'kind': 'lane'},
            'stale': {'display': 'Stale', 'command': ['runner'], 'identity': 'stale', 'kind': 'lane'},
            'failed': {'display': 'Failed', 'command': ['runner'], 'identity': 'failed', 'kind': 'lane'},
            'off': {'display': 'Off', 'command': ['runner'], 'identity': 'off', 'kind': 'job', 'enabled': False},
        })
        started = self._stamp(timedelta(minutes=1))
        self._ledger('working', f'{started} START identity=working kind=lane budget_secs=1500\n')
        very_old = self._stamp(timedelta(hours=3))
        self._ledger('stale', f'{very_old} START identity=stale kind=lane budget_secs=1500\n')
        errored = self._stamp(timedelta(minutes=1))
        self._ledger('failed', f'{started} START identity=failed kind=lane budget_secs=1500\n{errored} ERROR reason="agent exit" rc=1\n')
        by_id = {a['id']: a for a in operations_snapshot(self.root)['agents']}
        self.assertIsNone(by_id['working']['action'])
        self.assertEqual(by_id['idle']['action'], 'dispatch')
        self.assertEqual(by_id['stale']['action'], 'inspect')
        self.assertEqual(by_id['failed']['action'], 'dispatch')  # no preserved reservation
        self.assertIsNone(by_id['off']['action'])

    def test_failed_seat_with_preserved_reservation_recovers(self):
        self._daemon(fresh=True)
        config = self.root / 'runner.json'
        state_dir = self.root / 'state'
        config.write_text(json.dumps({'state_dir': str(state_dir), 'worker': 'failed'}))
        reservation = state_dir / 'failed' / 'pc-9'
        reservation.mkdir(parents=True)
        (reservation / 'preparation.json').write_text('{}')
        self._roster({'failed': {'display': 'Failed', 'command': ['runner', '--config', str(config)], 'identity': 'failed', 'kind': 'lane'}})
        started = self._stamp(timedelta(minutes=2))
        errored = self._stamp(timedelta(minutes=1))
        self._ledger('failed', f'{started} START identity=failed kind=lane budget_secs=1500\n{started} CANDIDATE ticket=pc-9\n{errored} ERROR reason="agent exit" rc=1\n')
        manifest = self.root / 'product/.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'product', 'prefix': 'pc', 'display': 'product'}))
        import sqlite3
        data = self.root / 'worklane/worklane/local/data'
        data.mkdir(parents=True)
        with sqlite3.connect(data / 'product.db') as conn:
            conn.executescript('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);')
            conn.execute("INSERT INTO tasks VALUES(9,NULL,'work','in_progress',1,'2026-09-12','[\"worker:failed\"]',NULL,NULL)")
        row = next(a for a in operations_snapshot(self.root)['agents'] if a['id'] == 'failed')
        self.assertEqual(row['state'], 'last_run_failed')
        self.assertTrue(row['held_verified'])
        self.assertTrue(row['preserved_reservation'])
        self.assertEqual(row['action'], 'recover')

    def test_reservation_lookup_does_not_normalize_order_id(self):
        # A receipt exists for a *different* order ('foo-bar'); the held order
        # is 'foo/bar', which the old regex normalization collapsed to the
        # same slug. Without normalization these must not collide.
        self._daemon(fresh=True)
        config = self.root / 'runner.json'
        state_dir = self.root / 'state'
        config.write_text(json.dumps({'state_dir': str(state_dir), 'worker': 'failed'}))
        reservation = state_dir / 'failed' / 'foo-bar'
        reservation.mkdir(parents=True)
        (reservation / 'preparation.json').write_text('{}')
        self._roster({'failed': {'display': 'Failed', 'command': ['runner', '--config', str(config)], 'identity': 'failed', 'kind': 'lane'}})
        started = self._stamp(timedelta(minutes=2))
        errored = self._stamp(timedelta(minutes=1))
        self._ledger('failed', f'{started} START identity=failed kind=lane budget_secs=1500\n{started} CANDIDATE ticket=foo/bar\n{errored} ERROR reason="agent exit" rc=1\n')
        manifest = self.root / 'product/.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'product', 'prefix': 'pc', 'display': 'product'}))
        import sqlite3
        data = self.root / 'worklane/worklane/local/data'
        data.mkdir(parents=True)
        with sqlite3.connect(data / 'product.db') as conn:
            conn.executescript('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);')
            conn.execute("INSERT INTO tasks VALUES(9,'foo/bar','work','in_progress',1,'2026-09-12','[\"worker:failed\"]',NULL,NULL)")
        row = next(a for a in operations_snapshot(self.root)['agents'] if a['id'] == 'failed')
        self.assertFalse(row['preserved_reservation'])
        self.assertEqual(row['action'], 'dispatch')

    def test_ledger_tail_truncated_inside_quoted_field_is_dropped_not_raised(self):
        # A ledger past the 16 KB tail window whose seek point lands inside a
        # quoted title= field must not raise; the partial first line is
        # dropped and the real rows after it are still read.
        self._daemon(fresh=True)
        self._roster({'recovered': {'display': 'Recovered', 'command': ['runner'], 'identity': 'recovered', 'kind': 'lane'}})
        started = self._stamp(timedelta(minutes=2))
        errored = self._stamp(timedelta(minutes=1))
        padding = self._stamp(timedelta(hours=1)) + ' CANDIDATE ticket=pc-1 title="' + ('x' * 20000) + '"\n'
        self.assertGreater(len(padding), 16384)
        self._ledger(
            'recovered',
            padding
            + f'{started} START identity=recovered kind=lane budget_secs=1500 recovery=1\n'
            + f'{started} CANDIDATE ticket=pc-2\n'
            + f'{errored} ERROR reason="agent exit" rc=1\n'
        )
        row = next(a for a in operations_snapshot(self.root)['agents'] if a['id'] == 'recovered')
        self.assertEqual(row['badge'], 'LAST RUN FAILED')
        self.assertEqual(row['recovery_attempts'], 1)

    # ---- Supervisor panel ----------------------------------------------------

    def test_supervisor_absent_when_not_on_roster(self):
        self._daemon(fresh=True)
        self._roster({'agent': {'display': 'Agent', 'command': ['runner'], 'identity': 'agent', 'kind': 'lane'}})
        self.assertIsNone(operations_snapshot(self.root)['supervisor'])

    def test_supervisor_unavailable_without_verified_origin(self):
        self._daemon(fresh=True)
        self._roster({'bp-supervisor': {'display': 'Supervisor', 'command': ['runner'], 'identity': 'bp-supervisor', 'kind': 'job'}})
        supervisor = operations_snapshot(self.root)['supervisor']
        self.assertEqual(supervisor['passes']['state'], 'unavailable')
        self.assertEqual(supervisor['passes']['passes'], [])

    def test_supervisor_present_reads_passes_from_verified_origin(self):
        self._daemon(fresh=True)
        self._roster({'bp-supervisor': {'display': 'Supervisor', 'command': ['runner'], 'identity': 'bp-supervisor', 'kind': 'job'}})
        deployment = self.root / 'local/workforce/deployment.json'
        deployment.parent.mkdir(parents=True)
        deployment.write_text(json.dumps({'api_origin': 'http://127.0.0.1:9999'}))
        payload = {'ok': True, 'passes': [{'generated_at': '2026-09-13T03:41:00Z', 'pass_outcome': 'dispatched'}], 'unreadable': 0}
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.return_value.__enter__.return_value = _FakeResponse(payload)
            supervisor = operations_snapshot(self.root)['supervisor']
        self.assertEqual(supervisor['passes']['state'], 'available')
        self.assertEqual(supervisor['passes']['passes'][0]['pass_outcome'], 'dispatched')

    def test_supervisor_redirect_refused_as_unavailable(self):
        self._daemon(fresh=True)
        self._roster({'bp-supervisor': {'display': 'Supervisor', 'command': ['runner'], 'identity': 'bp-supervisor', 'kind': 'job'}})
        deployment = self.root / 'local/workforce/deployment.json'
        deployment.parent.mkdir(parents=True)
        deployment.write_text(json.dumps({'api_origin': 'http://127.0.0.1:9999'}))
        from urllib.error import HTTPError
        import io
        error = HTTPError('http://evil.example/api/supervisor', 302, 'Found', {}, io.BytesIO(b''))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect = error
            supervisor = operations_snapshot(self.root)['supervisor']
        self.assertEqual(supervisor['passes']['state'], 'unavailable')
        self.assertEqual(supervisor['passes']['passes'], [])

    def test_supervisor_endpoint_absent_on_older_engine(self):
        self._daemon(fresh=True)
        self._roster({'bp-supervisor': {'display': 'Supervisor', 'command': ['runner'], 'identity': 'bp-supervisor', 'kind': 'job'}})
        deployment = self.root / 'local/workforce/deployment.json'
        deployment.parent.mkdir(parents=True)
        deployment.write_text(json.dumps({'api_origin': 'http://127.0.0.1:9999'}))
        from urllib.error import HTTPError
        import io
        error = HTTPError('http://127.0.0.1:9999/api/supervisor', 404, 'Not Found', {}, io.BytesIO(b'{}'))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect = error
            supervisor = operations_snapshot(self.root)['supervisor']
        self.assertEqual(supervisor['passes']['state'], 'not_configured')


class ProviderModelResolutionTests(unittest.TestCase):
    """pc-1472: provider/model resolution order and the trimmed card fields."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'workforce/local'
        self.runtime.mkdir(parents=True)
        (self.runtime / 'ledger').mkdir()
        tick = datetime.now(timezone.utc)
        (self.runtime / 'daemon.json').write_text(json.dumps({'last_tick': tick.isoformat(), 'in_flight': []}))

    def _roster(self, workers):
        (self.runtime / 'roster.json').write_text(json.dumps({'workers': workers}))

    def _agent(self, identity='agent'):
        return next(a for a in operations_snapshot(self.root)['agents'] if a['id'] == identity)

    def test_roster_model_wins_first(self):
        """pc-1476: a bare pin still gets its provider name prefixed from the
        seat's own resolved command — the demo row's 'Claude claude-sonnet-5'."""
        self._roster({'agent': {'display': 'Agent', 'command': ['claude'], 'identity': 'agent',
                                 'kind': 'lane', 'model': 'claude-sonnet-5'}})
        self.assertEqual(self._agent()['model'], 'Claude claude-sonnet-5')

    def test_roster_model_already_prefixed_with_provider_is_not_doubled(self):
        self._roster({'agent': {'display': 'Agent', 'command': ['claude'], 'identity': 'agent',
                                 'kind': 'lane', 'model': 'Claude claude-sonnet-5'}})
        self.assertEqual(self._agent()['model'], 'Claude claude-sonnet-5')

    def test_roster_model_already_prefixed_case_insensitively_is_not_doubled(self):
        # review finding pc-1476: a pin whose leading word already names the
        # provider (regardless of case) must not be prefixed again.
        self._roster({'agent': {'display': 'Agent', 'command': ['claude'], 'identity': 'agent',
                                 'kind': 'lane', 'model': 'claude sonnet'}})
        self.assertEqual(self._agent()['model'], 'Claude sonnet')

    def test_bare_provider_name_pin_is_not_doubled(self):
        # review finding pc-1476: a pin that is exactly the bare provider
        # token (lowercase) reads as the provider name alone, not doubled.
        self._roster({'agent': {'display': 'Agent', 'command': ['claude'], 'identity': 'agent',
                                 'kind': 'lane', 'model': 'claude'}})
        self.assertEqual(self._agent()['model'], 'Claude')

    def test_roster_model_with_unresolvable_command_stays_bare(self):
        self._roster({'agent': {'display': 'Agent', 'command': ['mystery-tool'], 'identity': 'agent',
                                 'kind': 'lane', 'model': 'some-pin'}})
        self.assertEqual(self._agent()['model'], 'some-pin')

    def test_runner_config_provider_and_model(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/claude', '--model', 'sonnet', '-p', 'x']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', str(config)]}})
        self.assertEqual(self._agent()['model'], 'Claude sonnet')

    def test_runner_config_provider_without_model_flag(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/cursor-agent', '--print']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', str(config)]}})
        self.assertEqual(self._agent()['model'], 'Cursor')

    def test_executable_inference_when_no_config(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'job',
                                 'command': ['/usr/local/bin/grok', '-p', 'x']}})
        self.assertEqual(self._agent()['model'], 'Grok')

    def test_python_module_reads_local_job(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'job',
                                 'command': ['/usr/bin/python3', '-m', 'protocolcity.operations_job']}})
        self.assertEqual(self._agent()['model'], 'Local job')

    def test_unrecognized_command_is_never_not_specified(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'job',
                                 'command': ['/usr/local/bin/mystery-tool']}})
        model = self._agent()['model']
        self.assertNotEqual(model, 'Not specified')
        self.assertEqual(model, 'Provider unknown')

    def test_inline_equals_model_flag_resolves(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/claude', '--model=sonnet', '-p', 'x']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', str(config)]}})
        self.assertEqual(self._agent()['model'], 'Claude sonnet')

    def test_grok_short_model_flag_resolves(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/grok', '-m', 'grok-4', '-p', 'x']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', str(config)]}})
        self.assertEqual(self._agent()['model'], 'Grok grok-4')

    def test_relative_config_path_resolves_against_workspace_root(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/claude', '--model', 'sonnet']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', 'runner.json']}})
        self.assertEqual(self._agent()['model'], 'Claude sonnet')

    def test_relative_config_path_outside_workspace_falls_through(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['/usr/local/bin/claude', '--config', '../../etc/runner.json']}})
        self.assertEqual(self._agent()['model'], 'Claude')

    def test_shared_runner_config_read_once_per_snapshot(self):
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/claude', '--model', 'sonnet']}))
        self._roster({
            'agent-one': {'display': 'Agent One', 'identity': 'agent-one', 'kind': 'lane',
                          'command': ['python', 'launch.py', '--config', str(config)]},
            'agent-two': {'display': 'Agent Two', 'identity': 'agent-two', 'kind': 'lane',
                          'command': ['python', 'launch.py', '--config', str(config)]},
        })
        from server import operations
        with patch.object(operations, 'read_json', wraps=operations.read_json) as read_json:
            snapshot = operations_snapshot(self.root)
        config_reads = [c for c in read_json.call_args_list if c.args and c.args[0] == config.resolve()]
        self.assertEqual(len(config_reads), 1)
        self.assertEqual(next(a for a in snapshot['agents'] if a['id'] == 'agent-one')['model'], 'Claude sonnet')
        self.assertEqual(next(a for a in snapshot['agents'] if a['id'] == 'agent-two')['model'], 'Claude sonnet')

    def test_codex_app_path_and_dash_c_model_flag_resolve(self):
        """pc-1474 scope addition (1): the Codex app path plus ``-c model="..."``."""
        config = self.root / 'runner.json'
        config.write_text(json.dumps({'command': [
            '/Applications/ChatGPT.app/Contents/Resources/codex', '-c', 'model="gpt-6-astra"', 'exec',
        ]}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', 'launch.py', '--config', str(config)]}})
        self.assertEqual(self._agent()['model'], 'Codex gpt-6-astra')

    def test_codex_on_path_without_model_flag_reads_bare_provider(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'job',
                                 'command': ['/usr/local/bin/codex', 'exec']}})
        self.assertEqual(self._agent()['model'], 'Codex')

    def test_bare_codex_token_no_path_resolves(self):
        """pc-1474 scope addition (3): a bare first token infers the provider."""
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'job',
                                 'command': ['codex', 'exec']}})
        self.assertEqual(self._agent()['model'], 'Codex')

    def test_launcher_without_config_falls_back_to_sibling_runner_json(self):
        """pc-1474 scope addition (2): pos-cursor-implementer's ``launch.py`` names
        no ``--config`` — the sibling runner.json in the launcher's own folder
        is the seat's config."""
        launcher_dir = self.root / 'local/worker-config/pos-cursor-implementer'
        launcher_dir.mkdir(parents=True)
        config = launcher_dir / 'runner.json'
        config.write_text(json.dumps({'command': ['/usr/local/bin/cursor-agent', '--model', 'composer-2.5']}))
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', str(launcher_dir / 'launch.py')]}})
        self.assertEqual(self._agent()['model'], 'Cursor composer-2.5')

    def test_launcher_without_config_and_without_sibling_runner_falls_through(self):
        launcher_dir = self.root / 'local/worker-config/pos-cursor-implementer'
        launcher_dir.mkdir(parents=True)
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['python', str(launcher_dir / 'launch.py')]}})
        self.assertEqual(self._agent()['model'], 'Local job')

    def test_template_shaped_command_combines_bare_token_with_roster_model(self):
        """pc-1477 scope addition (3): a legacy template command like
        ``claude --model {model} -p {prompt_text}`` names its provider on
        the bare first token; the unfilled placeholders must not send it to
        'Local job' or 'Provider unknown' — it resolves with the roster's
        own model."""
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'command': ['claude', '--model', '{model}', '-p', '{prompt_text}'],
                                 'model': 'claude-sonnet-5'}})
        self.assertEqual(self._agent()['model'], 'Claude claude-sonnet-5')

    def test_bare_pin_with_unresolvable_command_still_names_the_provider(self):
        """pc-1479: the row's own model text must agree with what
        provider_coverage counts it as — a roster row whose id differs
        from its ``identity`` field, with a command that resolves no
        executable/config, still gets its provider prefixed from the pin
        family (same fallback ``_project_seat_providers`` already used for
        coverage), instead of showing the bare pin or 'Local job'."""
        self._roster({'demo': {'display': 'Demo Worker', 'identity': 'demo-worker', 'kind': 'lane',
                                'command': ['python', 'launch.py'], 'model': 'claude-sonnet-5'}})
        self.assertEqual(self._agent('demo')['model'], 'Claude claude-sonnet-5')


class SeatProjectFieldTests(unittest.TestCase):
    """pc-1474 scope addition: every seat names its project from the queue,
    not only held seats — 'No project queue' replaces 'Unassigned'."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'workforce/local'
        self.runtime.mkdir(parents=True)
        (self.runtime / 'ledger').mkdir()
        (self.runtime / 'daemon.json').write_text(json.dumps({'last_tick': datetime.now(timezone.utc).isoformat(), 'in_flight': []}))
        manifest = self.root / 'blueprint/.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'blueprint', 'prefix': 'pc', 'display': 'BluePrint'}))

    def _roster(self, workers):
        (self.runtime / 'roster.json').write_text(json.dumps({'workers': workers}))

    def _agent(self, identity):
        return next(a for a in operations_snapshot(self.root)['agents'] if a['id'] == identity)

    def test_seat_with_a_scoped_queue_names_its_project_even_when_not_held(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane',
                                 'queue_url': 'worklane://local?product=blueprint', 'command': ['claude']}})
        row = self._agent('agent')
        self.assertEqual(row['project'], 'blueprint')
        self.assertEqual(row['project_name'], 'BluePrint')

    def test_seat_with_no_queue_product_reads_none(self):
        self._roster({'agent': {'display': 'Agent', 'identity': 'agent', 'kind': 'lane', 'command': ['claude']}})
        row = self._agent('agent')
        self.assertIsNone(row['project'])
        self.assertIsNone(row['project_name'])


class _FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode('utf-8')

    def read(self):
        return self._payload
