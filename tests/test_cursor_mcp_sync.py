import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from protocolcity.mcp_sync import (
    apply_mcp, check_drift, check_vendor_toml, diagnose_mcp_findings,
    render_toml_mcp_server_block, sync_existing_cursor_entries,
    sync_existing_workspace_codex_entries,
)


class WorkspaceCodexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.config = self.root / '.codex' / 'config.toml'
        self.entry = {'command': 'python3', 'args': ['-m', 'worklane.mcp'],
                      'env': {'WORKLANE_AUTHOR': 'worker', 'WORKLANE_PROJECT': 'sample'}}
        self.managed = {'worklane': self.entry,
                        'additional': {'command': 'python3', 'args': []}}
        for sid, entry in self.managed.items():
            directory = self.root / '.agents' / 'mcp' / sid
            directory.mkdir(parents=True)
            manifest = dict(entry, id=sid, description='test', transport='stdio',
                            capability='read', risk='low', seats=['*'], level='L0',
                            vendor_locked=False, enabled=True)
            (directory / 'manifest.json').write_text(json.dumps(manifest))

    def write_config(self, entry):
        self.config.parent.mkdir(exist_ok=True)
        personal = 'model = "personal-model"\n\n[mcp_servers.personal]\ncommand = "keep"\n\n'
        self.config.write_text(personal + render_toml_mcp_server_block('worklane', entry))
        return personal

    def test_stale_override_repaired_without_enrolling_servers_or_touching_host(self):
        personal = self.write_config(dict(self.entry, command='/old/development/python'))
        before = self.config.read_text()
        with patch('protocolcity.mcp_sync._is_live_workspace_root', return_value=False):
            # Produce the JSON mirror without repairing the deliberately stale override.
            with patch('protocolcity.mcp_sync.sync_existing_workspace_codex_entries', return_value={'ok': True}):
                apply_mcp(self.root, touch_vendors=False)
            self.assertFalse(check_drift(self.root)['ok'])
            self.assertEqual(self.config.read_text(), before)
            findings = diagnose_mcp_findings(self.root, check_vendors=False)
            self.assertEqual(findings[0]['path'], str(self.config))
            with patch('protocolcity.mcp_sync.apply_vendor_toml', side_effect=AssertionError('host write')):
                self.assertTrue(apply_mcp(self.root)['ok'])
            self.assertTrue(check_drift(self.root)['ok'])
        after = self.config.read_text()
        self.assertTrue(after.startswith(personal))
        self.assertNotIn('mcp_servers.additional', after)
        self.assertNotIn('/old/development/python', after)
        sync_existing_workspace_codex_entries(self.root, self.managed, apply=True)
        self.assertEqual(after, self.config.read_text())

    def test_complete_args_and_env_drift_with_same_command(self):
        variants = [
            dict(self.entry, args=['-m', 'worklane.mcp', '--author', '${AUTHOR}']),
            dict(self.entry, args=['worklane.mcp', '-m']),
            dict(self.entry, env=dict(self.entry['env'], WORKLANE_AUTHOR='${AUTHOR}')),
            dict(self.entry, env=dict(self.entry['env'], EXTRA_IDENTITY='other')),
            dict(self.entry, env={}),
        ]
        for entry in variants:
            with self.subTest(entry=entry):
                self.write_config(entry)
                self.assertFalse(check_vendor_toml(self.config, {'worklane': self.entry})['ok'])
                self.assertTrue(sync_existing_workspace_codex_entries(self.root, self.managed, apply=True)['ok'])
                self.assertTrue(check_vendor_toml(self.config, {'worklane': self.entry})['ok'])

    def test_missing_config_and_personal_only_config_do_not_enroll(self):
        apply_mcp(self.root, touch_vendors=False)
        self.assertFalse(self.config.exists())
        self.assertTrue(check_drift(self.root)['ok'])
        self.config.parent.mkdir()
        personal = 'model = "custom"\n[mcp_servers.personal]\ncommand = "keep"\n'
        self.config.write_text(personal)
        apply_mcp(self.root, touch_vendors=False)
        self.assertEqual(self.config.read_text(), personal)
        self.assertTrue(check_drift(self.root)['ok'])

    def test_nested_identity_override_is_repaired(self):
        self.write_config(dict(self.entry, env={}))
        with self.config.open('a') as stream:
            stream.write('[mcp_servers.worklane.env]\nWORKLANE_AUTHOR = "${AUTHOR}"\n')
        self.assertFalse(sync_existing_workspace_codex_entries(self.root, self.managed)['ok'])
        self.assertTrue(sync_existing_workspace_codex_entries(self.root, self.managed, apply=True)['ok'])
        self.assertNotIn('${AUTHOR}', self.config.read_text())

    def test_dead_outside_workspace_command_still_fails(self):
        entry = dict(self.entry, command=str(self.root.parent / 'missing-mcp-test' / 'python'))
        self.write_config(entry)
        result = check_vendor_toml(self.config, {'worklane': entry}, workspace=self.root)
        self.assertFalse(result['ok'])
        self.assertTrue(result['dead_commands'])


class CursorMirrorTests(unittest.TestCase):
    def test_existing_entry_updates_without_enrolling_other_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / '.cursor' / 'mcp.json'
            config.parent.mkdir()
            original = {'mcpServers': {'worklane': {'command': '/old/python'}, 'personal': {'command': 'keep'}}, 'preference': True}
            config.write_text(json.dumps(original))
            expected = {'worklane': {'command': '/installed/python'}, 'additional': {'command': 'do-not-add'}}
            with patch('pathlib.Path.home', return_value=home), patch('protocolcity.mcp_sync.should_apply_host_vendor', return_value=True):
                self.assertFalse(sync_existing_cursor_entries(home, expected)['ok'])
                self.assertEqual(json.loads(config.read_text()), original)
                self.assertTrue(sync_existing_cursor_entries(home, expected, apply=True)['ok'])
                updated = json.loads(config.read_text())
                self.assertEqual(updated['mcpServers']['worklane'], expected['worklane'])
                self.assertEqual(updated['mcpServers']['personal'], original['mcpServers']['personal'])
                self.assertNotIn('additional', updated['mcpServers'])
                self.assertTrue(updated['preference'])
                self.assertTrue(sync_existing_cursor_entries(home, expected)['ok'])

    def test_non_live_workspace_does_not_touch_host(self):
        with patch('protocolcity.mcp_sync.should_apply_host_vendor', return_value=False), patch('pathlib.Path.home', side_effect=AssertionError('host must not be read')):
            self.assertTrue(sync_existing_cursor_entries(Path('/disposable'), {}, apply=True)['ok'])
