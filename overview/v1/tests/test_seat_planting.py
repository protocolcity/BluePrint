"""pc-1475: `blueprint adopt` plants the standard seat set through
WorkForce hire (D12), `blueprint doctor` reports seat drift per project.
Disposable workspace, fake PATH, fake `workforce` executable — never a
live roster write, never the desk."""
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

from protocolcity.adopt import plant_standard_seats
from protocolcity.doctor import diagnose_seat_drift


def _write_roster(root: Path, workers: dict) -> None:
    path = root / '.protocolcity/workforce/local/roster.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'workers': workers}))


def _seat(command, project='blueprint', enabled=None):
    row = {'display': 'Seat', 'identity': 'seat', 'kind': 'lane',
           'queue_url': 'worklane://local?product=%s' % project, 'command': command}
    if enabled is not None:
        row['enabled'] = enabled
    return row


def _fake_workforce(path: Path, log: Path) -> None:
    path.write_text(
        '#!/bin/sh\n'
        'echo "$@" >> "%s"\n'
        'exit 0\n' % log
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


HOST_ALL = {'Claude': '/x/claude', 'Cursor': '/x/cursor-agent', 'Grok': '/x/grok', 'Codex': '/x/codex'}


class PlantStandardSeatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'blueprint'
        self.project.mkdir()

    def _plant(self, host_providers, **kwargs):
        with patch('overview.v1.server.operations.detect_providers', return_value=host_providers):
            return plant_standard_seats(
                self.root, 'blueprint', project_path=self.project, prefix='pc', **kwargs
            )

    def test_dry_run_prints_a_command_per_installed_provider_and_writes_nothing(self):
        result = self._plant(HOST_ALL)
        self.assertEqual(result['hired'], [])
        providers = {row['provider'] for row in result['commands']}
        self.assertEqual(providers, {'Claude', 'Cursor', 'Grok', 'Codex'})
        for row in result['commands']:
            self.assertIn('workforce hire pc-%s-implementer' % row['provider'].lower(), row['command'])
        self.assertFalse((self.root / '.protocolcity/workforce/local/roster.json').exists())

    def test_a_provider_already_seated_for_this_project_is_not_offered_again(self):
        _write_roster(self.root, {'blueprint-claude': _seat(['claude'])})
        result = self._plant(HOST_ALL)
        providers = {row['provider'] for row in result['commands']}
        self.assertNotIn('Claude', providers)
        self.assertIn('Cursor', providers)

    def test_a_provider_not_installed_on_this_host_is_not_offered(self):
        host = dict(HOST_ALL)
        host['Grok'] = None
        result = self._plant(host)
        providers = {row['provider'] for row in result['commands']}
        self.assertNotIn('Grok', providers)

    def test_held_provider_command_carries_the_held_flag(self):
        result = self._plant(HOST_ALL, held=['claude'])
        row = next(r for r in result['commands'] if r['provider'] == 'Claude')
        self.assertTrue(row['command'].endswith('--held'))

    def test_hire_calls_the_fake_workforce_executable_once_per_provider(self):
        bindir = self.root / 'bin'
        bindir.mkdir()
        log = self.root / 'hire.log'
        fake = bindir / 'workforce'
        _fake_workforce(fake, log)
        result = self._plant(HOST_ALL, hire=True, workforce_bin=str(fake))
        self.assertEqual(len(result['hired']), 4)
        self.assertTrue(all(row['returncode'] == 0 for row in result['hired']))
        lines = log.read_text().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(any('pc-claude-implementer' in line for line in lines))

    def test_dry_run_by_default_never_invokes_a_workforce_executable(self):
        bindir = self.root / 'bin'
        bindir.mkdir()
        fake = bindir / 'workforce'
        _fake_workforce(fake, self.root / 'hire.log')
        self._plant(HOST_ALL, workforce_bin=str(fake))
        self.assertFalse((self.root / 'hire.log').exists())


class DoctorSeatDriftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        manifest = self.root / 'blueprint/.protocolcity/desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'blueprint', 'prefix': 'pc', 'display': 'BluePrint'}))

    def _diagnose(self, host_providers):
        with patch('overview.v1.server.operations.detect_providers', return_value=host_providers):
            return diagnose_seat_drift(self.root)

    def test_installed_provider_with_no_seat_is_reported_missing(self):
        findings = self._diagnose(HOST_ALL)
        codes = {(f['code'], f['path']) for f in findings}
        self.assertIn(('MISSING-SEAT', 'blueprint'), codes)
        self.assertTrue(all(f['status'] == 'weak' for f in findings))

    def test_seat_whose_provider_is_no_longer_installed_is_reported(self):
        _write_roster(self.root, {'blueprint-claude': _seat(['claude'])})
        host = dict(HOST_ALL)
        host['Claude'] = None
        findings = self._diagnose(host)
        codes = {f['code'] for f in findings}
        self.assertIn('SEAT-PROVIDER-MISSING', codes)
        self.assertNotIn('MISSING-SEAT', [f['code'] for f in findings if 'Claude' in f['detail']])

    def test_held_seat_is_reported_and_never_counted_as_missing(self):
        _write_roster(self.root, {'blueprint-claude': _seat(['claude'], enabled=False)})
        findings = self._diagnose(HOST_ALL)
        held = [f for f in findings if f['code'] == 'SEAT-HELD']
        self.assertEqual(len(held), 1)
        self.assertIn('Claude', held[0]['detail'])

    def test_drift_findings_never_move_the_exit_code(self):
        # doctor's exit code counts only status missing/conflict — weak drift
        # findings must never flip it (report-only, never a fix).
        findings = self._diagnose(HOST_ALL)
        self.assertTrue(findings)
        self.assertFalse(any(f['status'] in ('missing', 'conflict') for f in findings))

    def test_no_registered_projects_reports_no_drift(self):
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(empty, ignore_errors=True))
        with patch('overview.v1.server.operations.detect_providers', return_value=HOST_ALL):
            self.assertEqual(diagnose_seat_drift(empty), [])


if __name__ == '__main__':
    unittest.main()
