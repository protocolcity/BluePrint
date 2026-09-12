import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from protocolcity.open_work_audit import load_roster, main


class AuditWorkspaceTests(unittest.TestCase):
    def test_selected_workspace_never_uses_foreign_roster_environment(self):
        with tempfile.TemporaryDirectory() as selected, tempfile.TemporaryDirectory() as other:
            foreign = Path(other) / 'roster.json'
            foreign.write_text(json.dumps({'workers': {'foreign': {}}}))
            with patch.dict(os.environ, {'WORKFORCE_ROSTER': str(foreign)}):
                _, workers, _ = load_roster(city_root=Path(selected))
                self.assertEqual(workers, {})
                local = Path(selected) / '.protocolcity/workforce/local/roster.json'
                local.parent.mkdir(parents=True)
                local.write_text(json.dumps({'workers': {'local': {'kind': 'lane'}}}))
                path, workers, _ = load_roster(city_root=Path(selected))
                self.assertEqual(Path(path), local.resolve())
                self.assertEqual(set(workers), {'local'})

    def test_cli_passes_workspace_from_wrapper_environment(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'WORKSPACE_ROOT': root}):
            with patch('sys.argv', ['open-work-audit', '--json']), patch('protocolcity.open_work_audit.run_audit', return_value={}) as audit, patch('sys.stdout'):
                self.assertEqual(main(), 0)
                self.assertEqual(audit.call_args.kwargs['city_root'], Path(root).resolve())
