"""AGENT_ADOPTION.md D12/D15 (pc-1474): provider detection, per-project seat
coverage and the Hire command text. Disposable roster + fake PATH; no host
provider, no roster write."""
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

from server.operations import detect_providers, hire_command, operations_snapshot, provider_coverage


class ProviderDetectionTests(unittest.TestCase):
    def setUp(self):
        self.home_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.home_temp.cleanup)
        self.home = Path(self.home_temp.name)

    def test_fake_path_with_no_providers_reads_all_none(self):
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home)
        self.assertEqual(found, {'Claude': None, 'Cursor': None, 'Grok': None, 'Codex': None})

    def test_fake_path_finds_only_the_installed_commands(self):
        with tempfile.TemporaryDirectory() as bindir:
            claude = Path(bindir) / 'claude'
            claude.write_text('#!/bin/sh\n')
            claude.chmod(0o755)
            found = detect_providers(env={'PATH': bindir}, app_path_exists=False, home=self.home)
        self.assertEqual(found['Claude'], str(claude))
        self.assertIsNone(found['Cursor'])
        self.assertIsNone(found['Grok'])
        self.assertIsNone(found['Codex'])

    def test_codex_falls_back_to_the_chatgpt_app_path_when_not_on_path(self):
        found = detect_providers(env={'PATH': ''}, app_path_exists=True, home=self.home)
        self.assertEqual(found['Codex'], '/Applications/ChatGPT.app/Contents/Resources/codex')

    def test_codex_on_path_wins_over_the_app_path(self):
        with tempfile.TemporaryDirectory() as bindir:
            codex = Path(bindir) / 'codex'
            codex.write_text('#!/bin/sh\n')
            codex.chmod(0o755)
            found = detect_providers(env={'PATH': bindir}, app_path_exists=True, home=self.home)
        self.assertEqual(found['Codex'], str(codex))

    def test_well_known_local_bin_location_proves_a_provider_present(self):
        localbin = self.home / '.local' / 'bin'
        localbin.mkdir(parents=True)
        claude = localbin / 'claude'
        claude.write_text('#!/bin/sh\n')
        claude.chmod(0o755)
        sources = {}
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home, sources=sources)
        self.assertEqual(found['Claude'], str(claude))
        self.assertEqual(sources['Claude'], 'well-known location')

    def test_well_known_grok_bin_location_proves_grok_present(self):
        grokbin = self.home / '.grok' / 'bin'
        grokbin.mkdir(parents=True)
        grok = grokbin / 'grok'
        grok.write_text('#!/bin/sh\n')
        grok.chmod(0o755)
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home)
        self.assertEqual(found['Grok'], str(grok))

    def test_path_wins_over_well_known_location(self):
        with tempfile.TemporaryDirectory() as bindir:
            localbin = self.home / '.local' / 'bin'
            localbin.mkdir(parents=True)
            (localbin / 'claude').write_text('#!/bin/sh\n')
            (localbin / 'claude').chmod(0o755)
            claude = Path(bindir) / 'claude'
            claude.write_text('#!/bin/sh\n')
            claude.chmod(0o755)
            sources = {}
            found = detect_providers(env={'PATH': bindir}, app_path_exists=False, home=self.home, sources=sources)
        self.assertEqual(found['Claude'], str(claude))
        self.assertEqual(sources['Claude'], 'PATH')

    def test_seat_absolute_executable_proves_a_provider_present(self):
        bindir = self.home / 'bin'
        bindir.mkdir()
        exe = bindir / 'claude'
        exe.write_text('#!/bin/sh\n')
        exe.chmod(0o755)
        workers = {'seat': {'display': 'Seat', 'identity': 'seat', 'kind': 'lane',
                             'command': [str(exe), '-p', 'x']}}
        sources = {}
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home,
                                  workers=workers, root=bindir, config_cache={}, sources=sources)
        self.assertEqual(found['Claude'], str(exe))
        self.assertEqual(sources['Claude'], 'seat command')

    def test_seat_with_missing_executable_proves_nothing(self):
        workers = {'seat': {'display': 'Seat', 'identity': 'seat', 'kind': 'lane',
                             'command': ['/nowhere/claude', '-p', 'x']}}
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home,
                                  workers=workers, root=Path('/nowhere'), config_cache={})
        self.assertIsNone(found['Claude'])

    def test_seat_executable_outside_trusted_locations_proves_nothing(self):
        # A seat naming an executable under /tmp — outside the trusted
        # home/homebrew/usr-local/Codex-app roots — proves no provider,
        # even though the file genuinely exists (review finding pc-1476).
        with tempfile.TemporaryDirectory(dir='/tmp') as bindir:
            exe = Path(bindir) / 'claude'
            exe.write_text('#!/bin/sh\n')
            exe.chmod(0o755)
            workers = {'seat': {'display': 'Seat', 'identity': 'seat', 'kind': 'lane',
                                 'command': [str(exe), '-p', 'x']}}
            found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home,
                                      workers=workers, root=Path(bindir), config_cache={})
        self.assertIsNone(found['Claude'])

    def test_well_known_bin_symlink_to_untrusted_target_proves_nothing(self):
        # A well-known bin location that is a symlink pointing outside the
        # trusted roots proves nothing — Path.is_file() alone would follow
        # the symlink and wrongly accept it (review finding pc-1476).
        localbin = self.home / '.local' / 'bin'
        localbin.mkdir(parents=True)
        with tempfile.TemporaryDirectory(dir='/tmp') as outside:
            target = Path(outside) / 'claude'
            target.write_text('#!/bin/sh\n')
            target.chmod(0o755)
            (localbin / 'claude').symlink_to(target)
            found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home)
        self.assertIsNone(found['Claude'])

    def test_well_known_bin_symlink_to_trusted_target_still_proves_present(self):
        localbin = self.home / '.local' / 'bin'
        localbin.mkdir(parents=True)
        real_dir = self.home / 'real'
        real_dir.mkdir()
        target = real_dir / 'claude'
        target.write_text('#!/bin/sh\n')
        target.chmod(0o755)
        (localbin / 'claude').symlink_to(target)
        found = detect_providers(env={'PATH': ''}, app_path_exists=False, home=self.home)
        self.assertEqual(found['Claude'], str(localbin / 'claude'))


class HireCommandTests(unittest.TestCase):
    def test_hire_command_text_names_provider_pin_project_and_repository(self):
        command = hire_command('Cursor', project_slug='blueprint', project_path='/ws/blueprint', prefix='pc')
        self.assertIn('workforce hire pc-cursor-implementer', command)
        self.assertIn('--provider Cursor', command)
        self.assertIn('--repository /ws/blueprint', command)
        self.assertIn('--model composer-2.5', command)
        self.assertIn('--project blueprint', command)
        self.assertIn('--schedule manual', command)
        self.assertNotIn('--remote', command)

    def test_hire_command_names_the_remote_when_the_project_registration_knows_one(self):
        command = hire_command('Claude', project_slug='blueprint', project_path='/ws/blueprint', prefix='pc',
                                remote='https://github.com/protocolcity/BluePrint')
        self.assertIn('--remote https://github.com/protocolcity/BluePrint', command)

    def test_hire_command_quotes_every_argument_not_just_role(self):
        command = hire_command('Claude', project_slug='blue print', project_path='/ws/blue print; rm -rf ~',
                                prefix='pc', remote='https://github.com/x/y; rm -rf ~')
        parsed = shlex.split(command)
        self.assertIn('/ws/blue print; rm -rf ~', parsed)
        self.assertIn('blue print', parsed)
        self.assertIn('https://github.com/x/y; rm -rf ~', parsed)
        self.assertNotIn('rm', parsed)

    def test_hire_command_never_carries_a_permission_bypass_flag(self):
        for provider in ('Claude', 'Cursor', 'Grok', 'Codex'):
            command = hire_command(provider, project_slug='wl', project_path='/ws/worklane', prefix='wl')
            self.assertNotIn('dangerously-skip-permissions', command)


class ProviderCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def _registry(self, slug='blueprint', name='BluePrint', prefix='pc'):
        return {slug: {'name': name, 'prefix': prefix, 'folder': slug, 'has_instructions': True}}

    def _seat(self, provider_command, project='blueprint', enabled=None):
        row = {'display': 'Seat', 'identity': 'seat', 'kind': 'lane',
               'queue_url': f'worklane://local?product={project}', 'command': provider_command}
        if enabled is not None:
            row['enabled'] = enabled
        return row

    def test_present_missing_held_and_not_configured_all_compute(self):
        workers = {
            'blueprint-claude': self._seat(['claude']),
            'blueprint-codex': self._seat(['codex'], enabled=False),
        }
        host_providers = {'Claude': '/usr/local/bin/claude', 'Cursor': '/usr/local/bin/cursor-agent',
                           'Grok': None, 'Codex': '/Applications/ChatGPT.app/Contents/Resources/codex'}
        rows = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['present'], ['Claude'])
        self.assertEqual(row['held'], ['Codex'])
        self.assertEqual(row['missing'], ['Cursor'])
        self.assertEqual(row['not_configured'], ['Grok'])
        self.assertEqual(row['text'], 'BluePrint: Claude, Codex OFF · missing Cursor · not configured: Grok')

    def test_fully_staffed_project_reads_the_d15_example_text(self):
        workers = {'blueprint-claude': self._seat(['claude']), 'blueprint-cursor': self._seat(['cursor-agent'])}
        host_providers = {'Claude': '/x/claude', 'Cursor': '/x/cursor-agent', 'Grok': '/x/grok', 'Codex': '/x/codex'}
        row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['text'], 'BluePrint: Claude, Cursor · missing Grok, Codex')

    def test_missing_provider_carries_its_hire_command(self):
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), {}, {}, host_providers=host_providers)[0]
        self.assertIn('Claude', row['missing'])
        self.assertIn('workforce hire pc-claude-implementer', row['hire_commands']['Claude'])
        self.assertNotIn('Cursor', row['hire_commands'])

    def test_missing_provider_hire_command_names_the_registered_remote(self):
        connections = self.root / '.blueprint/connections.json'
        connections.parent.mkdir(parents=True)
        connections.write_text(json.dumps({'github': {'repositories': [
            {'project': 'blueprint', 'repo': 'protocolcity/BluePrint', 'role': 'Canonical product'}]}}))
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), {}, {}, host_providers=host_providers)[0]
        self.assertIn('--remote https://github.com/protocolcity/BluePrint', row['hire_commands']['Claude'])

    def test_bare_pin_model_still_counts_as_a_present_seat(self):
        workers = {'blueprint-claude': self._seat(['python', 'launch.py'])}
        workers['blueprint-claude']['model'] = 'claude-sonnet-5'
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['present'], ['Claude'])

    def test_seat_with_no_kind_field_still_counts_as_a_seat(self):
        workers = {'blueprint-claude': {'display': 'Seat', 'identity': 'seat',
                                          'queue_url': 'worklane://local?product=blueprint', 'command': ['claude']}}
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['present'], ['Claude'])

    def test_not_configured_provider_carries_an_install_hint(self):
        host_providers = {'Claude': None, 'Cursor': '/x/cursor-agent', 'Grok': '/x/grok', 'Codex': '/x/codex'}
        row = provider_coverage(self.root, self._registry(), {}, {}, host_providers=host_providers)[0]
        self.assertIn('Claude', row['not_configured'])
        self.assertIn('install', row['install_hints']['Claude'])

    def test_seat_for_another_project_does_not_count_here(self):
        workers = {'other-claude': self._seat(['claude'], project='worklane')}
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['present'], [])
        self.assertIn('Claude', row['missing'])

    def test_operations_snapshot_carries_a_coverage_row_per_registered_project(self):
        manifest = self.root / 'blueprint/.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'blueprint', 'prefix': 'pc', 'display': 'BluePrint'}))
        snapshot = operations_snapshot(self.root)
        self.assertEqual(len(snapshot['coverage']), 1)
        self.assertEqual(snapshot['coverage'][0]['project'], 'blueprint')

    def test_coverage_row_names_the_source_that_proved_each_present_provider(self):
        workers = {'blueprint-claude': self._seat(['claude']), 'blueprint-codex': self._seat(['codex'], enabled=False)}
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': '/x/codex'}

        def fake_detect(**kwargs):
            if kwargs.get('sources') is not None:
                kwargs['sources'].update({'Claude': 'well-known location', 'Codex': 'seat command'})
            return host_providers

        with patch('server.operations.detect_providers', side_effect=fake_detect):
            row = provider_coverage(self.root, self._registry(), workers, {})[0]
        self.assertEqual(row['sources'], {'Claude': 'well-known location', 'Cursor': 'not detected',
                                           'Grok': 'not detected', 'Codex': 'seat command'})

    def test_seat_with_missing_on_disk_executable_does_not_count_as_present(self):
        workers = {'blueprint-claude': self._seat(['/nowhere/claude'])}
        host_providers = {'Claude': None, 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['present'], [])
        self.assertIn('Claude', row['not_configured'])

    def test_not_configured_providers_get_a_not_detected_source_label(self):
        host_providers = {'Claude': '/x/claude', 'Cursor': None, 'Grok': None, 'Codex': None}
        row = provider_coverage(self.root, self._registry(), {}, {}, host_providers=host_providers)[0]
        self.assertEqual(row['sources']['Cursor'], 'not detected')
        self.assertEqual(row['sources']['Grok'], 'not detected')
        self.assertEqual(row['sources']['Codex'], 'not detected')

    def test_seat_executable_outside_trusted_locations_does_not_count_as_present(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as outside:
            exe = Path(outside) / 'claude'
            exe.write_text('#!/bin/sh\n')
            exe.chmod(0o755)
            workers = {'blueprint-claude': self._seat([str(exe)])}
            host_providers = {'Claude': None, 'Cursor': None, 'Grok': None, 'Codex': None}
            row = provider_coverage(self.root, self._registry(), workers, {}, host_providers=host_providers)[0]
        self.assertEqual(row['present'], [])
        self.assertIn('Claude', row['not_configured'])


if __name__ == '__main__':
    unittest.main()
