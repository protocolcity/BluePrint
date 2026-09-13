"""pc-1475 review fixes (workflow-reviewer grok-4.6 on commit 6fac3e4):

1. `blueprint adopt --dry-run` must write nothing (companions, desk, roster).
2. `plant_standard_seats(hire=True)` stops at the first failing provider.
3. `plant_standard_seats` refuses an unmanaged folder or one without a
   desk-join.json (names what is missing).
4. `blueprint found --project` wires plant_seats the same way `adopt` does.

Disposable workspace, fake PATH, fake `workforce` executable — never a live
roster write, never the desk."""
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from protocolcity.adopt import adopt_neighborhood, is_managed, plant_standard_seats, stamp_managed
from protocolcity.desk import DESK_JOIN_REL

HOST_ALL = {'Claude': '/x/claude', 'Cursor': '/x/cursor-agent', 'Grok': '/x/grok', 'Codex': '/x/codex'}


def _stamp_desk_join(project: Path, slug: str = 'blueprint', prefix: str = 'pc') -> None:
    dest = project / DESK_JOIN_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({'slug': slug, 'prefix': prefix, 'display': 'BluePrint'}))


def _fake_workforce_failing_on_call(path: Path, log: Path, fail_at: int) -> None:
    """Fake `workforce` that exits 1 on the fail_at'th invocation (1-based)."""
    counter = path.parent / 'calls'
    path.write_text(
        '#!/bin/sh\n'
        'n=$(( $(cat "%s" 2>/dev/null || echo 0) + 1 ))\n'
        'echo "$n" > "%s"\n'
        'echo "$@" >> "%s"\n'
        'if [ "$n" -eq %d ]; then exit 1; fi\n'
        'exit 0\n' % (counter, counter, log, fail_at)
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _walk_snapshot(root: Path) -> dict:
    """Relative path -> mtime_ns for every file under root, for a before/after diff."""
    snap = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            snap[str(p.relative_to(root))] = p.stat().st_mtime_ns
    return snap


class PlantStandardSeatsGuardTests(unittest.TestCase):
    """Finding 3: refuse an unmanaged folder or a project with no desk-join."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'blueprint'
        self.project.mkdir()

    def _plant(self, **kwargs):
        with patch('overview.v1.server.operations.detect_providers', return_value=HOST_ALL):
            return plant_standard_seats(
                self.root, 'blueprint', project_path=self.project, prefix='pc', **kwargs
            )

    def test_unmanaged_folder_is_refused_and_writes_nothing(self):
        result = self._plant()
        self.assertFalse(result['ok'])
        self.assertIn('not BluePrint-managed', result['error'])
        self.assertEqual(result['commands'], [])
        self.assertEqual(result['hired'], [])
        self.assertFalse(is_managed(self.project))

    def test_managed_project_without_desk_join_is_refused(self):
        stamp_managed(self.project)
        result = self._plant()
        self.assertFalse(result['ok'])
        self.assertIn('desk-join.json', result['error'])
        self.assertEqual(result['commands'], [])

    def test_managed_and_desk_joined_project_is_allowed(self):
        stamp_managed(self.project)
        _stamp_desk_join(self.project)
        result = self._plant()
        self.assertTrue(result['ok'])
        self.assertTrue(result['commands'])

    def test_dry_run_bypasses_the_guard_to_preview_an_unmanaged_folder(self):
        result = self._plant(dry_run=True)
        self.assertTrue(result['ok'])
        self.assertTrue(result['commands'])
        self.assertEqual(result['hired'], [])


class PlantStandardSeatsHireStopsOnFailureTests(unittest.TestCase):
    """Finding 2: --hire stops at the first non-zero-exit provider."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'blueprint'
        self.project.mkdir()
        stamp_managed(self.project)
        _stamp_desk_join(self.project)

    def test_hire_stops_at_the_first_failing_provider(self):
        bindir = self.root / 'bin'
        bindir.mkdir()
        log = self.root / 'hire.log'
        fake = bindir / 'workforce'
        _fake_workforce_failing_on_call(fake, log, fail_at=2)
        with patch('overview.v1.server.operations.detect_providers', return_value=HOST_ALL):
            result = plant_standard_seats(
                self.root, 'blueprint', project_path=self.project, prefix='pc',
                hire=True, workforce_bin=str(fake),
            )
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['hired']), 2)
        self.assertEqual(result['hired'][0]['returncode'], 0)
        self.assertNotEqual(result['hired'][1]['returncode'], 0)
        # Only 2 providers were ever invoked — the third (and fourth) never ran.
        self.assertEqual(len(log.read_text().splitlines()), 2)


class AdoptDryRunWritesNothingTests(unittest.TestCase):
    """Finding 1: --dry-run must stop every write (companions, desk, roster)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'blueprint'
        self.project.mkdir()
        (self.project / 'AGENTS.md').write_text('# BluePrint\n')
        stamp_managed(self.project)
        _stamp_desk_join(self.project)

    def test_dry_run_leaves_the_file_list_and_mtimes_identical(self):
        before = _walk_snapshot(self.root)
        with patch('overview.v1.server.operations.detect_providers', return_value=HOST_ALL):
            result = adopt_neighborhood(
                self.root, 'blueprint',
                with_desk=False,
                plant_seats=True,
                hire_seats=True,  # even if a caller passes True, dry-run must never hire
                dry_run=True,
            )
        after = _walk_snapshot(self.root)
        self.assertEqual(before, after)
        self.assertTrue(result['ok'])
        self.assertTrue(result['dry_run'])
        seats = result['seats']
        self.assertTrue(seats['commands'])
        self.assertEqual(seats['hired'], [])

    def test_dry_run_on_a_brand_new_unmanaged_folder_still_previews_and_writes_nothing(self):
        fresh = self.root / 'recipes'
        fresh.mkdir()
        before = _walk_snapshot(self.root)
        with patch('overview.v1.server.operations.detect_providers', return_value=HOST_ALL):
            result = adopt_neighborhood(
                self.root, 'recipes',
                with_desk=False,
                plant_seats=True,
                dry_run=True,
            )
        after = _walk_snapshot(self.root)
        self.assertEqual(before, after)
        self.assertTrue(result['dry_run'])
        self.assertFalse(result['already_managed'])
        self.assertIn('AGENTS.md', result['would_create'])
        # Preview bypasses the managed/desk-join guard so the plan is visible
        # even though `recipes` is not managed yet.
        self.assertTrue(result['seats']['commands'])


class CliFoundWiresPlantSeatsTests(unittest.TestCase):
    """Finding 4: `found --project` plants the standard seat set like `adopt`."""

    def _run(self, argv, receipt):
        from protocolcity import cli

        with patch.object(cli, 'found', return_value=receipt) as found_mock, \
             patch.object(cli, 'register_city') as register_mock, \
             patch.object(cli, '_maybe_unmanaged_prompt'):
            rc = cli.main(argv)
        return rc, found_mock, register_mock

    def test_found_project_passes_plant_seats_true(self):
        receipt = {
            'ok': True, 'root': '/tmp/ws', 'city_name': 'ws', 'agents': '/tmp/ws/AGENTS.md',
            'neighborhood': 'recipes', 'neighborhood_path': '/tmp/ws/recipes',
            'first_run': None, 'vendor_clis': [], 'desk': None, 'seats': None,
        }
        rc, found_mock, register_mock = self._run(
            ['found', '/tmp/ws', '--project', 'recipes', '--no-desk', '--no-ticket'],
            receipt,
        )
        self.assertEqual(rc, 0)
        found_mock.assert_called_once()
        kwargs = found_mock.call_args.kwargs
        self.assertTrue(kwargs['plant_seats'])
        self.assertFalse(kwargs['hire_seats'])
        self.assertFalse(kwargs['dry_run'])
        register_mock.assert_called_once()

    def test_found_project_hire_flag_forwards_hire_seats(self):
        receipt = {
            'ok': True, 'root': '/tmp/ws', 'city_name': 'ws', 'agents': '/tmp/ws/AGENTS.md',
            'neighborhood': 'recipes', 'neighborhood_path': '/tmp/ws/recipes',
            'first_run': None, 'vendor_clis': [], 'desk': None,
            'seats': {'ok': True, 'commands': [{'provider': 'Claude', 'command': 'workforce hire ...'}]},
        }
        rc, found_mock, _register_mock = self._run(
            ['found', '/tmp/ws', '--project', 'recipes', '--no-desk', '--no-ticket', '--hire'],
            receipt,
        )
        self.assertEqual(rc, 0)
        self.assertTrue(found_mock.call_args.kwargs['hire_seats'])

    def test_found_project_dry_run_prints_the_plan_and_never_registers(self):
        receipt = {
            'ok': True, 'dry_run': True, 'root': '/tmp/ws', 'agents': '/tmp/ws/AGENTS.md',
            'city_name': 'ws', 'neighborhood': 'recipes', 'neighborhood_path': None,
            'would_create': ['AGENTS.md'], 'first_run': None, 'vendor_clis': [], 'desk': None,
            'seats': {'ok': True, 'commands': [{'provider': 'Claude', 'command': 'workforce hire pc-claude-implementer'}]},
        }
        rc, found_mock, register_mock = self._run(
            ['found', '/tmp/ws', '--project', 'recipes', '--dry-run'],
            receipt,
        )
        self.assertEqual(rc, 0)
        self.assertTrue(found_mock.call_args.kwargs['dry_run'])
        register_mock.assert_not_called()


class CliAdoptDryRunNeverCallsFixTests(unittest.TestCase):
    """Finding 1 at the CLI seam: --dry-run must never route through doctor.fix()."""

    def test_adopt_dry_run_calls_adopt_neighborhood_directly(self):
        from protocolcity import cli

        preview = {
            'ok': True, 'dry_run': True, 'name': 'recipes', 'path': '/tmp/ws/recipes',
            'store_slug': 'recipes', 'prefix': 'rc', 'would_create': [],
            'seats': {'ok': True, 'commands': []},
        }
        with patch('protocolcity.adopt.adopt_neighborhood', return_value=preview) as adopt_mock, \
             patch.object(cli, 'fix') as fix_mock:
            rc = cli.main(['adopt', '/tmp/ws', 'recipes', '--dry-run', '--no-desk'])
        self.assertEqual(rc, 0)
        fix_mock.assert_not_called()
        adopt_mock.assert_called_once()
        self.assertTrue(adopt_mock.call_args.kwargs['dry_run'])
        self.assertFalse(adopt_mock.call_args.kwargs['hire_seats'])

    def test_adopt_without_dry_run_still_calls_fix(self):
        from protocolcity import cli

        result = {'ok': True, 'adopt': {'name': 'recipes', 'seats': None}}
        with patch('protocolcity.adopt.adopt_neighborhood') as adopt_mock, \
             patch.object(cli, 'fix', return_value=result) as fix_mock:
            rc = cli.main(['adopt', '/tmp/ws', 'recipes', '--no-desk'])
        self.assertEqual(rc, 0)
        fix_mock.assert_called_once()
        adopt_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
