import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from protocolcity.seed_ops import seed_workspace_ops, _is_ops_routine


class SeedRetirementTests(unittest.TestCase):
    def test_default_seed_does_not_rehire_retired_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            roster=root/'.protocolcity/workforce/local/roster.json'
            roster.parent.mkdir(parents=True)
            roster.write_text('{"workers":{}}')
            before=roster.read_bytes()
            with patch('protocolcity.seed_ops.plant_efficiency_kit', return_value={'ok':True,'planted':[]}):
                result=seed_workspace_ops(root,quiet=True)
            self.assertTrue(result['ok'])
            self.assertEqual(result['seeded'],[])
            self.assertEqual(roster.read_bytes(),before)
            self.assertEqual(set(result['routines']),{'chief-of-staff','health-patrol','workspace-efficiency'})
            self.assertTrue(_is_ops_routine('marshal'))
