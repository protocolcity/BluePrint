import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from server.work_actions import add_note, work_action
from server.work_order import read_work_order

class WorkActionTests(unittest.TestCase):
    def test_invalid_notes_never_start_engine(self):
        for body in ['', 'Completed: shipped\nVerification: tests', 'Owner: agent\nPlan: work', 'Blocked: missing\nNext step: wait', 'x'*12001]:
            with patch('server.work_actions.subprocess.run') as run:
                with self.assertRaises(ValueError): add_note(None,'protocolcity','pc-1',body)
                run.assert_not_called()
    def test_unregistered_project_never_starts_engine(self):
        with tempfile.TemporaryDirectory() as path:
            with patch('server.work_actions.subprocess.run') as run:
                with self.assertRaises(ValueError): add_note(Path(path),'other','x-1','A normal note')
                run.assert_not_called()

class InstalledRuntimeTests(unittest.TestCase):
    def test_checkout_runtime_cannot_be_used_for_writes(self):
        from server.work_actions import _invoke
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / 'worklane/.venv/bin/python'
            checkout.parent.mkdir(parents=True)
            checkout.touch()
            with patch('server.work_actions.subprocess.run') as run:
                with self.assertRaisesRegex(RuntimeError, 'installed WorkLane'):
                    _invoke(root, 'example', {'id': '1'}, {'action': 'note', 'body': 'note'})
                run.assert_not_called()

    def test_missing_receipt_cannot_start_an_installed_path(self):
        from server.work_actions import _invoke
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'local/worklane/current/venv/bin/python'
            executable.parent.mkdir(parents=True)
            executable.touch()
            with patch('server.work_actions.subprocess.run') as run:
                with self.assertRaisesRegex(RuntimeError, 'receipt'):
                    _invoke(root, 'example', {'id': '1'}, {'action': 'note', 'body': 'note'})
                run.assert_not_called()

    def test_receipt_must_identify_selected_runtime_and_store(self):
        from server.work_actions import _invoke
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'local/worklane/current/venv/bin/python'
            executable.parent.mkdir(parents=True)
            executable.touch()
            receipt = root / 'local/worklane/deployment.json'
            receipt.write_text(json.dumps({'version': '1.0', 'entrypoint': [str(executable)],
                                           'runtime': str(root / 'another-store')}))
            with patch('server.work_actions.subprocess.run') as run:
                with self.assertRaisesRegex(RuntimeError, 'receipt'):
                    _invoke(root, 'example', {'id': '1'}, {'action': 'note', 'body': 'note'})
                run.assert_not_called()


class EngineIntegrationTests(unittest.TestCase):
    def test_real_engine_writes_only_selected_temporary_workspace(self):
        # Optional integration with an explicitly supplied installed WorkLane
        # interpreter. It only writes disposable databases, never live records.
        import os
        executable=os.environ.get('BP_TEST_WORKLANE_PYTHON')
        if not executable: self.skipTest('Set BP_TEST_WORKLANE_PYTHON for installed-engine integration')
        version = subprocess.check_output([executable, '-I', '-c',
            "import importlib.metadata; print(importlib.metadata.version('protocolcity-worklane'))"], text=True).strip()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            roots=[Path(a),Path(b)]
            for root in roots:
                data=root/'worklane/worklane/local/data';data.mkdir(parents=True)
                installed = root/'local/worklane/current'
                installed.mkdir(parents=True)
                (installed/'venv').symlink_to(Path(executable).parent.parent, target_is_directory=True)
                (root/'local/worklane/deployment.json').write_text(json.dumps({
                    'version': version, 'entrypoint': [str(installed/'venv/bin/python')],
                    'runtime': str(data.parent)}))
                manifest=root/'product/.protocolcity/desk-join.json';manifest.parent.mkdir(parents=True)
                manifest.write_text('{"slug":"protocolcity","prefix":"pc"}')
                script="from pathlib import Path; from worklane.trackers.sqlite import SQLiteTracker; import sys; t=SQLiteTracker(db_path=Path(sys.argv[1])); t.create_task(title='Test work order', description='Isolated verification')"
                subprocess.run([executable,'-c',script,str(data/'protocolcity.db')],check=True,capture_output=True)
            # A same-named checkout module must not shadow the installed package.
            (roots[0]/'worklane/__init__.py').write_text("raise RuntimeError('source checkout imported')\n")
            first=add_note(roots[0],'protocolcity','pc-1','A plain note <script>text only</script>')
            self.assertTrue(first['ok']);self.assertEqual(first['comment']['author'],'you')
            receipt_path = roots[0]/'local/worklane/deployment.json'
            receipt = json.loads(receipt_path.read_text())
            receipt_path.write_text(json.dumps({**receipt, 'version': '0.0-mismatch'}))
            with self.assertRaisesRegex(RuntimeError, 'version does not match'):
                add_note(roots[0], 'protocolcity', 'pc-1', 'Must not be saved')
            receipt_path.write_text(json.dumps(receipt))
            for index,root in enumerate(roots):
                with sqlite3.connect(root/'worklane/worklane/local/data/protocolcity.db') as conn:
                    self.assertEqual(conn.execute('SELECT count(*) FROM task_comments').fetchone()[0],1 if index==0 else 0)
                    self.assertEqual(conn.execute('SELECT status FROM tasks').fetchone()[0],'backlog')
            order = read_work_order(roots[0], 'protocolcity', 'pc-1')
            result = work_action(roots[0], 'protocolcity', 'pc-1', 'priority', 1, order['updated_at'])
            self.assertTrue(result['ok'])
            order = read_work_order(roots[0], 'protocolcity', 'pc-1')
            self.assertEqual(order['priority'], 1)
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                work_action(roots[0], 'protocolcity', 'pc-1', 'priority', 2, 'stale version')
            self.assertEqual(read_work_order(roots[0], 'protocolcity', 'pc-1')['priority'], 1)
            work_action(roots[0], 'protocolcity', 'pc-1', 'hold', 'A test decision', order['updated_at'])
            order = read_work_order(roots[0], 'protocolcity', 'pc-1')
            self.assertEqual(order['gate_type'], 'human')
            work_action(roots[0], 'protocolcity', 'pc-1', 'resume', None, order['updated_at'])
            order = read_work_order(roots[0], 'protocolcity', 'pc-1')
            self.assertFalse(order['gate_type'])
            with self.assertRaisesRegex(ValueError, 'registered agent'):
                work_action(roots[0], 'protocolcity', 'pc-1', 'assign', 'invented-worker', order['updated_at'])
            roster = roots[0]/'.protocolcity/workforce/local/roster.json'
            roster.parent.mkdir(parents=True)
            roster.write_text(json.dumps({'workers': {
                'test-agent': {'kind': 'lane', 'name': 'Test agent', 'queue_url': 'http://localhost/ready?product=protocolcity'},
                'other-agent': {'kind': 'lane', 'name': 'Other agent', 'queue_url': 'http://localhost/ready?product=other'},
            }}))
            with self.assertRaisesRegex(ValueError, 'not assigned'):
                work_action(roots[0], 'protocolcity', 'pc-1', 'assign', 'other-agent', order['updated_at'])
            self.assertTrue(work_action(roots[0], 'protocolcity', 'pc-1', 'assign', 'test-agent', order['updated_at'])['ok'])
            order = read_work_order(roots[0], 'protocolcity', 'pc-1')
            work_action(roots[0], 'protocolcity', 'pc-1', 'reminder', '2026-12-20', order['updated_at'])
            reminded = read_work_order(roots[0], 'protocolcity', 'pc-1')
            labels = json.loads(reminded['labels'])
            self.assertIn('worker:test-agent', labels)
            self.assertIn('reminder:2026-12-20', labels)
            self.assertEqual(reminded['status'], order['status'])
            self.assertEqual(reminded['gate_type'], order['gate_type'])
            work_action(roots[0], 'protocolcity', 'pc-1', 'reminder', '', reminded['updated_at'])
            self.assertNotIn('reminder:', read_work_order(roots[0], 'protocolcity', 'pc-1')['labels'])
            with sqlite3.connect(roots[0]/'worklane/worklane/local/data/protocolcity.db') as conn:
                labels = conn.execute('SELECT labels FROM tasks').fetchone()[0]
                self.assertIn('worker:test-agent', labels)
            with sqlite3.connect(roots[1]/'worklane/worklane/local/data/protocolcity.db') as conn:
                self.assertNotEqual(conn.execute('SELECT priority FROM tasks').fetchone()[0], 1)


class NoteHTTPTests(unittest.TestCase):
    def setUp(self):
        from test_four_lens_nav import _start_server
        self.httpd,self.port,self.thread=_start_server({})
    def tearDown(self): self.httpd.shutdown();self.httpd.server_close()
    def request(self, origin):
        import urllib.request, urllib.error
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/work-order/note',data=b'{"project":"protocolcity","id":"pc-1","body":"Note"}',headers={'Content-Type':'application/json','X-BluePrint-Action':'note',**({'Origin':origin} if origin else {})})
        try:
            with urllib.request.urlopen(req) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as error:return error.code,json.load(error)
    def test_cross_origin_and_missing_origin_never_write(self):
        with patch('server.work_actions.add_note') as action:
            self.assertEqual(self.request('https://unrelated.example')[0],403)
            self.assertEqual(self.request(None)[0],403)
            action.assert_not_called()
    def test_same_origin_routes_explicit_project(self):
        with patch('server.work_actions.add_note',return_value={'ok':True,'comment':{'body':'Note'}}) as action:
            self.assertEqual(self.request(f'http://127.0.0.1:{self.port}')[0],200)
            action.assert_called_once_with(None,'protocolcity','pc-1','Note')
