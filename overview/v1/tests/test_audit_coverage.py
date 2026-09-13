import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from protocolcity.audit_coverage import coverage, snapshot_process
from protocolcity.open_work_audit import run_audit, load_roster


class CoverageTests(unittest.TestCase):
    def lane(self, schedule='manual', host='local.test'):
        return dict(kind='lane', schedule=schedule,
                    queue_url='http://' + host + '/api/admin/tasks/ready?product=demo&label=worker:builder')

    def test_categories_and_no_liveness_claim(self):
        rows = [{'id': str(n), 'labels': labels} for n, labels in enumerate(
            [[], ['worker:you'], ['worker:old'], ['worker:builder'], ['worker:you', 'worker:builder']])]
        result = coverage({'demo': rows}, {'builder': self.lane()})
        for category in ('unassigned', 'you', 'unknown_or_retired', 'manual', 'ambiguous_assignment'):
            self.assertEqual(result['counts'][category], 1)
        self.assertEqual(result['execution_state'], 'unknown')
        self.assertTrue(result['has_configured_lane_coverage'])
        self.assertEqual(coverage({'demo': rows[:3]}, {})['configured_lane_ready'], 0)

    def test_scheduled_and_foreign_scope(self):
        tasks = {'demo': [{'labels': ['worker:builder']}]}
        self.assertEqual(coverage(tasks, {'builder': self.lane('0 9 * * *')})['counts']['scheduled'], 1)
        result = coverage(tasks, {'builder': self.lane()}, desk_urls={'demo': 'http://other.test'})
        self.assertEqual(result['counts']['outside_lane_scope'], 1)
        self.assertFalse(result['has_configured_lane_coverage'])
        self.assertEqual(coverage(tasks, {'builder': self.lane('')})['counts']['unknown_dispatch'], 1)

    def test_unknown_is_not_zero(self):
        result = coverage({}, {}, feed_error='offline')
        self.assertIsNone(result['total_ready'])
        self.assertIsNone(result['has_configured_lane_coverage'])
        self.assertTrue(all(v is None for v in result['counts'].values()))
        result = coverage({'demo': [{'labels': ['worker:builder']}]}, {}, roster_error='offline')
        self.assertIsNone(result['counts']['manual'])
        self.assertEqual(result['counts']['roster_unknown'], 1)

    def test_selected_snapshot_no_network_and_retains_decay_checks(self):
        snapshot = {'stores': [{'slug': 'demo', 'backlog': 1, 'ready': 1}],
                    'tasks': {'demo': {'ready': [{'labels': []}], 'all': []}}, 'errors': {}, 'desk_urls': {}}
        with tempfile.TemporaryDirectory() as root, patch('protocolcity.open_work_audit.load_workspace_snapshot', return_value=snapshot), patch('protocolcity.open_work_audit.load_roster', return_value=('selected', {}, '')), patch('protocolcity.open_work_audit._get', side_effect=AssertionError('network')), patch('protocolcity.open_work_audit._probe_json', side_effect=AssertionError('network')):
            result = run_audit(city_root=Path(root), feeds=True, history=True, process=True, decay=True)
        self.assertEqual(result['coverage']['counts']['unassigned'], 1)
        self.assertFalse(result['decay']['ok'])
        self.assertIn('section9_unreadable', result['decay']['findings'])
        self.assertIn('Label heuristic', result['feeds']['you_starve_basis'])

    def test_unavailable_snapshot_no_foreign_fallback(self):
        with patch('protocolcity.open_work_audit.load_workspace_snapshot', return_value={'error': 'unavailable'}), patch('protocolcity.open_work_audit.load_scene', side_effect=AssertionError('fallback')):
            result = run_audit(city_root=Path('/nonexistent'))
        self.assertIsNone(result['total_ready'])
        self.assertFalse(result['ok'])

    def test_malformed_roster_is_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'roster.json'
            path.write_text(json.dumps({'workers': {'bad': []}}))
            self.assertTrue(load_roster(str(path))[2])

    def test_snapshot_process_preserves_empty_deferred_finding(self):
        result = snapshot_process({'demo': {'ready': [], 'all': [dict(status='backlog', gate_type='deferred', labels=['worker:builder'])]}}, {'builder': self.lane()}, 'selected')
        self.assertEqual(result['lanes'][0]['deferred_n'], 1)
        self.assertFalse(result['ok'])

    def test_installed_engine_snapshot_reads_only_selected_temporary_stores(self):
        import os
        import subprocess
        import hashlib
        engine = os.environ.get('BP_TEST_WORKLANE_PYTHON')
        if not engine:
            self.skipTest('Explicit WorkLane interpreter required')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registration = root / 'demo/.protocolcity/desk-join.json'
            registration.parent.mkdir(parents=True)
            registration.write_text(json.dumps(dict(slug='demo', desk_url='http://selected.test')))
            data = root / 'worklane/worklane/local/data'
            data.mkdir(parents=True)
            database = data / 'demo.db'
            setup = 'from worklane.trackers.sqlite import SQLiteTracker; import sys; t=SQLiteTracker(db_path=sys.argv[1]); t.create_task(title="Ready", description="Test")'
            subprocess.run([engine, '-c', setup, str(database)], check=True, cwd=temporary)
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            script = Path(__file__).resolve().parents[3] / 'protocolcity/audit_snapshot.py'
            result = subprocess.run([engine, str(script), str(root)], check=True, capture_output=True, text=True, cwd=temporary)
            value = json.loads(result.stdout)
            self.assertEqual(value['stores'][0]['ready'], 1)
            self.assertEqual(set(value['tasks']), {'demo'})
            self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)
            database.unlink()
            result = subprocess.run([engine, str(script), str(root)], check=True, capture_output=True, text=True, cwd=temporary)
            self.assertIn('demo', json.loads(result.stdout)['errors'])
            self.assertFalse(database.exists())
