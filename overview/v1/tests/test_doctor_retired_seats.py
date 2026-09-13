"""pc-1477: `blueprint doctor` RETIRED-SEAT must read the WorkForce roster
(not just PROCESS.md) and must never count `worker:you` as a seat — You is
a persona (D11), never a WorkForce roster identity. Disposable workspace,
desk calls mocked — never the live desk."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from protocolcity.doctor import diagnose_retired_seats


def _write_roster(root: Path, workers: dict) -> None:
    path = root / '.protocolcity/workforce/local/roster.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'workers': workers}))


def _lane(identity):
    return {'display': identity, 'identity': identity, 'kind': 'lane',
            'queue_url': 'worklane://local?product=protocolcity', 'command': ['true']}


def _task(task_id, seat):
    return {'id': task_id, 'labels': ['worker:%s' % seat]}


class DoctorRetiredSeatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def _diagnose(self, tasks_by_status):
        def _fake_tasks(product, status, desk_url, **kw):
            return tasks_by_status.get(status, [])
        with patch('protocolcity.doctor._desk_tasks_for_status', side_effect=_fake_tasks):
            return diagnose_retired_seats(self.root, product='protocolcity')

    def test_seat_present_on_roster_is_never_retired(self):
        _write_roster(self.root, {'bp-claude-implementer': _lane('bp-claude-implementer')})
        findings = self._diagnose({'backlog': [_task('1', 'bp-claude-implementer')]})
        self.assertEqual(findings, [])

    def test_worker_you_is_never_reported_even_when_absent_from_roster(self):
        _write_roster(self.root, {'bp-claude-implementer': _lane('bp-claude-implementer')})
        findings = self._diagnose({'backlog': [_task('1', 'you')]})
        self.assertEqual(findings, [])

    def test_unknown_seat_absent_from_roster_is_still_reported(self):
        _write_roster(self.root, {'bp-claude-implementer': _lane('bp-claude-implementer')})
        findings = self._diagnose({'backlog': [_task('1', 'ghost-seat')]})
        codes = {f['code'] for f in findings}
        self.assertIn('RETIRED-SEAT', codes)


if __name__ == '__main__':
    unittest.main()
