"""Doctor must remain scoped, read-only by default and safe to share."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from protocolcity.workspace_doctor import diagnose, repair_vendor_pointers, support_bundle, _origin


class WorkspaceDoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / 'AGENTS.md').write_text('Local project instructions\n')

    def tearDown(self):
        self.temporary.cleanup()

    def receipt(self, component='blueprint', **fields):
        relative = '.blueprint/deployment.json' if component == 'blueprint' else 'local/' + component + '/deployment.json'
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'version': '1.2.3', 'port': 12345, **fields}))
        return path

    def test_default_does_not_probe_or_create_runtime(self):
        self.receipt()
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with patch('protocolcity.workspace_doctor._probe') as probe:
            report = diagnose(self.root)
        probe.assert_not_called()
        self.assertTrue(report['ok'])
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.assertTrue(all(row['source'] and row['observed_at'] for row in report['checks']))

    def test_probe_requires_selected_origin_and_build_identity(self):
        self.receipt()
        with patch('protocolcity.workspace_doctor._probe', return_value={'build': '1.2.3', 'workspace': {'path': '/another-workspace'}}) as probe:
            report = diagnose(self.root, probe=True)
        probe.assert_called_once_with('http://127.0.0.1:12345', '/api/identity')
        self.assertFalse(report['ok'])
        self.assertIn('BP_IDENTITY_MISMATCH', [row['code'] for row in report['checks']])

    def test_no_default_or_external_network_origin(self):
        for receipt in ({}, {'api_origin': 'https://example.invalid'}, {'api_origin': 'http://user:secret@localhost:12345'}, {'port': '8801'}):
            self.assertIsNone(_origin(receipt))
        self.receipt(api_origin='http://example.invalid:12345')
        with patch('protocolcity.workspace_doctor._probe') as probe:
            report = diagnose(self.root, probe=True)
        probe.assert_not_called()
        self.assertFalse(report['ok'])

    def test_corrupt_registered_store_is_reported_without_repair(self):
        join = self.root / 'example/.protocolcity/desk-join.json'
        join.parent.mkdir(parents=True)
        join.write_text('{"slug":"example"}')
        store = self.root / 'worklane/worklane/local/data/example.db'
        store.parent.mkdir(parents=True)
        store.write_bytes(b'corrupt private bytes')
        report = diagnose(self.root)
        self.assertFalse(report['ok'])
        self.assertEqual(store.read_bytes(), b'corrupt private bytes')

    def test_readable_store_is_checked_read_only(self):
        join = self.root / 'example/.protocolcity/desk-join.json'
        join.parent.mkdir(parents=True)
        join.write_text('{"slug":"example"}')
        store = self.root / 'worklane/worklane/local/data/example.db'
        store.parent.mkdir(parents=True)
        with closing(sqlite3.connect(store)) as connection:
            connection.execute('CREATE TABLE tasks(id INTEGER)')
            connection.commit()
        before = store.read_bytes()
        report = diagnose(self.root)
        self.assertIn('STORE_READABLE', [row['code'] for row in report['checks']])
        self.assertEqual(store.read_bytes(), before)

    def test_external_instruction_link_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            external = Path(other) / 'private.md'
            external.write_text('secret note')
            (self.root / 'CLAUDE.md').symlink_to(external)
            self.assertFalse(diagnose(self.root)['ok'])

    def test_support_report_omits_paths_names_and_configuration(self):
        self.receipt(secret='private credential never share')
        report = diagnose(self.root)
        report['checks'][0]['source'] = 'customer-private-name/notes.md'
        serialized = json.dumps(support_bundle(report))
        for value in (str(self.root), 'customer-private-name', 'private credential', 'workspace_id'):
            self.assertNotIn(value, serialized)

    def test_pointer_repair_preserves_existing_instruction(self):
        existing = self.root / 'CLAUDE.md'
        existing.write_text('custom instructions\n')
        self.assertEqual(repair_vendor_pointers(self.root), ['GROK.md'])
        self.assertEqual(existing.read_text(), 'custom instructions\n')
        self.assertEqual((self.root / 'GROK.md').read_text(), '@AGENTS.md\n')
        self.assertEqual(repair_vendor_pointers(self.root), [])

    def test_receipt_selected_layout_and_stale_execution_evidence(self):
        runtime = self.root / 'state/worklane'
        self.receipt('worklane', runtime=str(runtime))
        join = self.root / 'example/.protocolcity/desk-join.json'
        join.parent.mkdir(parents=True)
        join.write_text('{"slug":"example"}')
        store = runtime / 'data/example.db'
        store.parent.mkdir(parents=True)
        with closing(sqlite3.connect(store)) as connection:
            connection.execute('CREATE TABLE tasks(id INTEGER)')
            connection.commit()
        force = self.root / 'state/workforce'
        self.receipt('workforce', data_home=str(force))
        (force / 'local').mkdir(parents=True)
        (force / 'local/daemon.json').write_text('{"last_tick":"2000-01-01T00:00:00Z"}')
        report = diagnose(self.root)
        codes = [row['code'] for row in report['checks']]
        self.assertIn('STORE_READABLE', codes)
        self.assertIn('EXECUTION_EVIDENCE_STALE', codes)
        self.assertTrue(all('expected' in row and 'observed' in row for row in report['checks']))

    def test_explicit_external_runtime_never_falls_back(self):
        self.receipt('worklane', runtime='/another-workspace/runtime')
        report = diagnose(self.root)
        self.assertIn('INSTALLATION_UNVERIFIED', [row['code'] for row in report['checks']])
        self.assertFalse(report['ok'])
