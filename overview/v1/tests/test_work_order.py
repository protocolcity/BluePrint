import sqlite3
import json
import tempfile
import unittest
from pathlib import Path
from server.work_order import read_work_order

class WorkOrderTests(unittest.TestCase):
    def seed(self, root, project, title):
        manifest=root/project/'.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text(json.dumps({'slug':project,'prefix':'pc'}))
        data = root / 'worklane/worklane/local/data'
        data.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(data / (project + '.db')) as conn:
            conn.executescript('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT); CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);')
            conn.execute('INSERT INTO tasks VALUES(1, ?, ?)', ('pc-1', title))
            conn.execute('INSERT INTO task_comments VALUES(1, 1, ?, ?, ?)', ('<script>untrusted</script>', 'you', '2026-09-12'))

    def test_workspace_isolation_and_comments(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for path, title in [(a, 'first'), (b, 'second')]:
                self.seed(Path(path), 'protocolcity', title)
                result = read_work_order(Path(path), 'protocolcity', 'pc-1')
                self.assertEqual(result['title'], title)
                self.assertEqual(result['comments'][0]['body'], '<script>untrusted</script>')

    def test_ambiguous_and_explicit_project(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            self.seed(root, 'one', 'first'); self.seed(root, 'two', 'second')
            with self.assertRaises(ValueError): read_work_order(root, '', 'pc-1')
            self.assertEqual(read_work_order(root, 'two', 'pc-1')['title'], 'second')
            with self.assertRaises(FileNotFoundError): read_work_order(root, 'absent', 'pc-1')
            with self.assertRaises(ValueError): read_work_order(root, '../one', 'pc-1')

    def test_external_store_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.seed(Path(a), 'one', 'external')
            data = Path(b) / 'worklane/worklane/local/data'; data.mkdir(parents=True)
            (data / 'one.db').symlink_to(Path(a) / 'worklane/worklane/local/data/one.db')
            with self.assertRaises(FileNotFoundError): read_work_order(Path(b), 'one', 'pc-1')

    def test_unregistered_backup_cannot_supply_matching_external_id(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path);self.seed(root,'one','registered')
            data=root/'worklane/worklane/local/data'
            (data/'backup.db').write_bytes((data/'one.db').read_bytes())
            self.assertEqual(read_work_order(root,'','pc-1')['project'],'one')
            with self.assertRaises(FileNotFoundError):read_work_order(root,'backup','pc-1')

    def test_native_numeric_id_uses_workspace_prefix(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            self.seed(root, 'protocolcity', 'native')
            manifest = root / 'product/.protocolcity/desk-join.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"slug":"protocolcity","prefix":"pc"}')
            with sqlite3.connect(root / 'worklane/worklane/local/data/protocolcity.db') as conn:
                conn.execute('UPDATE tasks SET ext_id = NULL')
            self.assertEqual(read_work_order(root, '', 'pc-1')['ext_id'], 'pc-1')
            with self.assertRaises(FileNotFoundError): read_work_order(root, 'protocolcity', 'wrong-1')


class RevealTests(unittest.TestCase):
    def test_only_recorded_reference_can_reach_file_manager(self):
        from unittest.mock import patch
        from server.work_order import reveal_reference
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'source.py').write_text('# source')
            order={'references':[{'path':'source.py'}]}
            with patch('server.work_order.read_work_order',return_value=order), patch('sys.platform','darwin'), patch('subprocess.run') as run:
                with self.assertRaises(ValueError):reveal_reference(root,'product','pc-1','/etc/passwd')
                run.assert_not_called()
                self.assertTrue(reveal_reference(root,'product','pc-1','source.py')['ok'])
                self.assertEqual(run.call_args.args[0],['/usr/bin/open','-R',str((root/'source.py').resolve())])
