"""activate(): no-op probe budget and resolved legacy ports (pc-1497)."""
import json
import os
import plistlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from protocolcity import deploy as deploy_mod

FAKE_LAUNCHCTL = "#!/bin/sh\ncase \"$1\" in\n  print) exit 1 ;;\n  bootout) exit 0 ;;\n  *) exit 0 ;;\nesac\n"


class ActivateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.release = self.workspace / 'local/blueprint/releases/1.0.0-test'
        self.release.mkdir(parents=True)
        self.executable = self.release / 'venv/bin/blueprint-overview'
        self.executable.parent.mkdir(parents=True)
        self.executable.write_text('#!/bin/sh\n')
        self.executable.chmod(0o755)
        receipt = {
            'version': '1.0.0-test',
            'entrypoint': str(self.executable),
            'built_at': datetime.now(timezone.utc).isoformat(),
        }
        deploy_mod.write_json(self.release / 'build.json', receipt)
        current = self.workspace / 'local/blueprint/current'
        current.parent.mkdir(parents=True, exist_ok=True)
        current.symlink_to(self.release, target_is_directory=True)

        self.agents_dir = self.root / 'Library' / 'LaunchAgents'
        self.agents_dir.mkdir(parents=True)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        launchctl = bin_dir / 'launchctl'
        launchctl.write_text(FAKE_LAUNCHCTL)
        launchctl.chmod(0o755)
        old_path = os.environ.get('PATH', '')
        os.environ['PATH'] = str(bin_dir) + os.pathsep + old_path
        self.addCleanup(lambda: os.environ.__setitem__('PATH', old_path))

        home_patch = patch('pathlib.Path.home', return_value=self.root)
        home_patch.start()
        self.addCleanup(home_patch.stop)

        self.probe_calls = []
        self.activate_calls = []

        def fake_probe(port, expected, workspace=None, timeout=deploy_mod.DEFAULT_PROBE_TIMEOUT, interval=deploy_mod.DEFAULT_PROBE_INTERVAL):
            self.probe_calls.append(timeout)
            return {'projects': [{'id': 'demo'}], 'build': expected}

        probe_patch = patch.object(deploy_mod, 'probe', side_effect=fake_probe)
        probe_patch.start()
        self.addCleanup(probe_patch.stop)

        def fake_activate_agent(executable, receipt, workspace, port, legacy_ports=None, backup_dir=None, probe_timeout=deploy_mod.DEFAULT_PROBE_TIMEOUT):
            self.activate_calls.append({'legacy_ports': list(legacy_ports or []), 'probe_timeout': probe_timeout})
            return {'projects': []}

        activate_patch = patch.object(deploy_mod, 'activate_agent', side_effect=fake_activate_agent)
        activate_patch.start()
        self.addCleanup(activate_patch.stop)

    def _write_matching_agent(self, legacy_ports=()):
        agent_path = self.agents_dir / f'{deploy_mod.LABEL}.plist'
        arguments = [str(self.executable), '--binder', str(self.workspace), '--port', '8803']
        for legacy_port in legacy_ports:
            arguments.extend(['--legacy-port', str(legacy_port)])
        agent_path.write_bytes(plistlib.dumps({'Label': deploy_mod.LABEL, 'ProgramArguments': arguments}))
        deploy_mod.write_json(self.workspace / '.blueprint/deployment.json', {
            'version': '1.0.0-test',
            'entrypoint': str(self.executable),
            'port': 8803,
            'active': True,
            'activated_at': datetime.now(timezone.utc).isoformat(),
        })

    def test_already_active_uses_probe_timeout_not_hardcoded_five_seconds(self):
        self._write_matching_agent()
        deploy_mod.activate(self.release, self.workspace, 8803, probe_timeout=42.0)
        self.assertEqual(self.probe_calls, [42.0])
        self.assertEqual(self.activate_calls, [])

    def test_fallthrough_passes_resolved_legacy_from_existing_plist(self):
        self._write_matching_agent(legacy_ports=(8801, 8802))
        with patch.object(deploy_mod, 'deployment_matches', return_value=False):
            deploy_mod.activate(self.release, self.workspace, 8803, legacy_ports=None)
        self.assertEqual(self.activate_calls[0]['legacy_ports'], [8801, 8802])


if __name__ == '__main__':
    unittest.main()
