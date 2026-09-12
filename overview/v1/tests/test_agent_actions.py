import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from server.agent_actions import dispatch_agent


class AgentDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.local = self.root / 'workforce/local'
        self.local.mkdir(parents=True)
        (self.local / 'roster.json').write_text(json.dumps({'workers': {'agent': {'command': ['runner'], 'identity': 'agent'}}}))
        self.heartbeat = {'pid': 123, 'last_tick': datetime.now(timezone.utc).isoformat(), 'in_flight': []}
        self.save_heartbeat()
        receipt = self.root / 'local/workforce/deployment.json'
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({'api_origin': 'http://127.0.0.1:1234'}))
        self.live = {'engine': {'pid': 123, 'local_root': str(self.local)}, 'workers': [{'name': 'agent', 'identity': 'agent'}]}

    def save_heartbeat(self):
        (self.local / 'daemon.json').write_text(json.dumps(self.heartbeat))

    def test_dispatches_only_after_source_identity_matches(self):
        with patch('server.agent_actions._request', side_effect=[self.live, {'ok': True, 'msg': 'dispatched'}]) as request:
            self.assertTrue(dispatch_agent(self.root, 'agent')['ok'])
            self.assertEqual(request.call_args.args[0], 'http://127.0.0.1:1234/api/dispatch/agent')
            self.assertEqual(request.call_args.kwargs, {'data': b'{}'})

    def test_wrong_process_or_workspace_never_dispatches(self):
        for field, value in [('pid', 456), ('local_root', str(self.root / 'other'))]:
            live = {**self.live, 'engine': {**self.live['engine'], field: value}}
            with patch('server.agent_actions._request', return_value=live) as request:
                with self.assertRaisesRegex(RuntimeError, 'different workspace or process'):
                    dispatch_agent(self.root, 'agent')
                self.assertEqual(request.call_count, 1)

    def test_inflight_stale_and_unregistered_never_contact_engine(self):
        with patch('server.agent_actions._request') as request:
            with self.assertRaises(ValueError): dispatch_agent(self.root, '../agent')
            with self.assertRaises(ValueError): dispatch_agent(self.root, 'unknown')
            self.heartbeat['in_flight'] = ['agent']; self.save_heartbeat()
            with self.assertRaisesRegex(RuntimeError, 'in progress'): dispatch_agent(self.root, 'agent')
            self.heartbeat.update(in_flight=[], last_tick='2000-01-01T00:00:00Z'); self.save_heartbeat()
            with self.assertRaisesRegex(RuntimeError, 'stale'): dispatch_agent(self.root, 'agent')
            request.assert_not_called()
