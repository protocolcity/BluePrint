"""blueprint upgrade: three-lane install -> single consolidated app (pc-1469).

Uses a disposable fake LaunchAgents directory and a fake ``launchctl`` on
PATH; never touches this host's real launchd state.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from protocolcity import deploy as deploy_mod
from protocolcity import service as service_mod

FAKE_LAUNCHCTL = "#!/bin/sh\ncase \"$1\" in\n  print) exit 1 ;;\n  bootout) exit 0 ;;\n  *) exit 0 ;;\nesac\n"


class LegacyAgentFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
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

        agents_patch = patch.object(service_mod, 'AGENTS_DIR', self.agents_dir)
        agents_patch.start()
        self.addCleanup(agents_patch.stop)
        macos_patch = patch.object(service_mod, 'is_macos', return_value=True)
        macos_patch.start()
        self.addCleanup(macos_patch.stop)

    def _write_plist(self, label):
        (self.agents_dir / ('%s.plist' % label)).write_bytes(b'<plist/>')


class RetireLegacyAgentsTests(LegacyAgentFixture):
    def test_fresh_install_is_a_no_op(self):
        result = service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True)
        self.assertIsNone(result['retired_dir'])
        self.assertTrue(all(not entry['found'] for entry in result['agents']))

    def test_three_lane_install_boots_out_and_retires_both_plists(self):
        self._write_plist('com.protocolcity.suite')
        self._write_plist('com.protocolcity.blueprint-map')
        result = service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True)
        by_label = {entry['label']: entry for entry in result['agents']}
        self.assertTrue(by_label['com.protocolcity.suite']['found'])
        self.assertTrue(by_label['com.protocolcity.blueprint-map']['found'])
        self.assertFalse(by_label['com.protocolcity.citylens']['found'])
        retire_dir = Path(result['retired_dir'])
        self.assertTrue((retire_dir / 'com.protocolcity.suite.plist').is_file())
        self.assertTrue((retire_dir / 'com.protocolcity.blueprint-map.plist').is_file())
        self.assertFalse((self.agents_dir / 'com.protocolcity.suite.plist').exists())

    def test_citylens_present_is_retired_too(self):
        self._write_plist('com.protocolcity.citylens')
        result = service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True)
        entry = next(e for e in result['agents'] if e['label'] == 'com.protocolcity.citylens')
        self.assertTrue(entry['found'])
        retire_dir = Path(result['retired_dir'])
        self.assertTrue((retire_dir / 'com.protocolcity.citylens.plist').is_file())

    def test_second_run_is_idempotent(self):
        self._write_plist('com.protocolcity.suite')
        service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True)
        result = service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True)
        self.assertTrue(all(not entry['found'] for entry in result['agents']))

    def test_dry_run_writes_nothing(self):
        self._write_plist('com.protocolcity.suite')
        result = service_mod.retire_legacy_agents(workspace=self.workspace, quiet=True, dry_run=True)
        entry = next(e for e in result['agents'] if e['label'] == 'com.protocolcity.suite')
        self.assertTrue(entry['found'])
        self.assertTrue((self.agents_dir / 'com.protocolcity.suite.plist').is_file())
        self.assertFalse((self.workspace / 'local/blueprint/retired-services').exists())


class UpgradeTests(LegacyAgentFixture):
    def setUp(self):
        super().setUp()
        home_patch = patch('pathlib.Path.home', return_value=self.root)
        home_patch.start()
        self.addCleanup(home_patch.stop)

        self.entrypoint = self.root / 'bin' / 'blueprint-overview'
        self.entrypoint.write_text('#!/bin/sh\n')
        self.entrypoint.chmod(0o755)
        resolve_patch = patch.object(deploy_mod, 'resolve_installed_executable', return_value=self.entrypoint)
        resolve_patch.start()
        self.addCleanup(resolve_patch.stop)
        version_patch = patch.object(deploy_mod, 'installed_version', return_value='9.9.9-test')
        version_patch.start()
        self.addCleanup(version_patch.stop)

        self.activate_calls = []

        def fake_activate_agent(executable, receipt, workspace, port, legacy_ports=None, backup_dir=None):
            self.activate_calls.append(receipt)
            import plistlib
            agent_path = Path.home() / 'Library/LaunchAgents' / ('%s.plist' % deploy_mod.LABEL)
            agent_path.parent.mkdir(parents=True, exist_ok=True)
            arguments = [str(executable), '--binder', str(workspace), '--port', str(port)]
            for legacy_port in (legacy_ports or []):
                arguments += ['--legacy-port', str(legacy_port)]
            agent_path.write_bytes(plistlib.dumps({'Label': deploy_mod.LABEL, 'ProgramArguments': arguments}))
            deploy_mod.write_json(workspace / '.blueprint/deployment.json', {
                **receipt, 'port': port, 'launch_agent': str(agent_path), 'active': True,
                'activated_at': datetime.now(timezone.utc).isoformat(),
            })
            return {'projects': []}

        activate_patch = patch.object(deploy_mod, 'activate_agent', side_effect=fake_activate_agent)
        activate_patch.start()
        self.addCleanup(activate_patch.stop)

    def test_fresh_install_is_a_no_op_plus_agent_write(self):
        result = deploy_mod.upgrade(self.workspace, quiet=True)
        self.assertEqual(result['action'], 'activated')
        self.assertEqual(len(self.activate_calls), 1)
        deployment = json.loads((self.workspace / '.blueprint/deployment.json').read_text())
        for key in ('version', 'entrypoint', 'built_at', 'port', 'launch_agent', 'active', 'activated_at'):
            self.assertIn(key, deployment)
        self.assertEqual(deployment['version'], '9.9.9-test')

    def test_three_lane_install_boots_out_both_agents_and_retires_both_plists(self):
        self._write_plist('com.protocolcity.suite')
        self._write_plist('com.protocolcity.blueprint-map')
        result = deploy_mod.upgrade(self.workspace, quiet=True)
        by_label = {e['label']: e for e in result['legacy_agents']['agents']}
        self.assertTrue(by_label['com.protocolcity.suite']['found'])
        self.assertTrue(by_label['com.protocolcity.blueprint-map']['found'])
        retire_dir = Path(result['legacy_agents']['retired_dir'])
        self.assertTrue((retire_dir / 'com.protocolcity.suite.plist').is_file())
        self.assertTrue((retire_dir / 'com.protocolcity.blueprint-map.plist').is_file())

    def test_citylens_present_is_handled(self):
        self._write_plist('com.protocolcity.citylens')
        result = deploy_mod.upgrade(self.workspace, quiet=True)
        by_label = {e['label']: e for e in result['legacy_agents']['agents']}
        self.assertTrue(by_label['com.protocolcity.citylens']['found'])

    def test_second_run_is_idempotent(self):
        deploy_mod.upgrade(self.workspace, quiet=True)
        result = deploy_mod.upgrade(self.workspace, quiet=True)
        self.assertEqual(result['action'], 'no-op')
        self.assertEqual(len(self.activate_calls), 1)

    def test_dry_run_writes_nothing(self):
        self._write_plist('com.protocolcity.suite')
        result = deploy_mod.upgrade(self.workspace, quiet=True, dry_run=True)
        self.assertEqual(result['action'], 'dry-run')
        self.assertEqual(self.activate_calls, [])
        self.assertFalse((self.workspace / '.blueprint/deployment.json').exists())
        self.assertTrue((self.agents_dir / 'com.protocolcity.suite.plist').is_file())
        self.assertFalse((self.workspace / 'local/blueprint/retired-services').exists())

    def test_engine_files_untouched(self):
        blueprint_dir = self.workspace / '.blueprint'
        blueprint_dir.mkdir(parents=True)
        connections = blueprint_dir / 'connections.json'
        connections.write_text('{}')
        desk_join_dir = self.workspace / 'project/.protocolcity'
        desk_join_dir.mkdir(parents=True)
        desk_join = desk_join_dir / 'desk-join.json'
        desk_join.write_text('{}')
        before = (connections.stat().st_mtime, desk_join.stat().st_mtime)
        deploy_mod.upgrade(self.workspace, quiet=True)
        after = (connections.stat().st_mtime, desk_join.stat().st_mtime)
        self.assertEqual(before, after)

    def test_receipt_shape_matches_activate(self):
        deploy_mod.upgrade(self.workspace, quiet=True)
        deployment = json.loads((self.workspace / '.blueprint/deployment.json').read_text())
        expected_keys = {'version', 'entrypoint', 'built_at', 'port', 'launch_agent', 'active', 'activated_at'}
        self.assertTrue(expected_keys.issubset(deployment.keys()))

    def test_non_macos_fails_clearly_instead_of_crashing(self):
        with patch.object(service_mod, 'is_macos', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'macOS'):
                deploy_mod.upgrade(self.workspace, quiet=True)


if __name__ == '__main__':
    unittest.main()
