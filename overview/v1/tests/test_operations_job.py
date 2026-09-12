import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from protocolcity.operations_job import run_job


class OperationsJobTests(unittest.TestCase):
    def test_failed_audit_overwrites_old_success_without_claiming_health(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch('protocolcity.operations_job.subprocess.run', return_value=subprocess.CompletedProcess([],0,json.dumps(dict(reachable=True,total_open=3,total_ready=2,total_in_motion=1)))):
                self.assertEqual(run_job(root,'health-patrol'),0)
            with patch('protocolcity.operations_job.subprocess.run', side_effect=subprocess.TimeoutExpired('audit',90)):
                self.assertEqual(run_job(root,'health-patrol'),1)
            receipt=json.loads((root/'.blueprint/job-reports/health-patrol.json').read_text())
            self.assertEqual(receipt['state'],'failed')
            self.assertEqual(receipt['audit'],{})
            self.assertNotIn('3 open',receipt['summary'])
