import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from protocolcity.mcp_sync import sync_existing_cursor_entries


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
