import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from server import remote_activity as remote

class RemoteTests(unittest.TestCase):
    def test_unconfigured_has_no_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(remote, '_github') as api:
            self.assertEqual(remote.remote_snapshot(Path(folder))['state'], 'not_configured')
            api.assert_not_called()
    def test_bad_repo_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.blueprint').mkdir()
            (root/'.blueprint/connections.json').write_text(json.dumps({'github':{'repositories':[{'repo':'https://elsewhere.example/secret'}]}}))
            self.assertEqual(remote.remote_snapshot(root)['state'],'invalid_config')
    def test_records_keep_kind_state_and_privacy(self):
        values=[{'private':True,'default_branch':'main'},[{'title':'Fix','html_url':'https://github.com/org/repo/pull/1','state':'open','head':{'sha':'abc'}}],{'workflow_runs':[{'name':'Tests','status':'completed','conclusion':'failure','head_sha':'abc','html_url':'https://github.com/org/repo/actions/runs/2'}]},[]]
        with patch.object(remote,'_github',side_effect=values): result=remote._load_repo('gh',{'repo':'org/repo','project':'example'})
        self.assertTrue(result['private']);self.assertEqual(result['state'],'connected')
        self.assertEqual([r['kind'] for r in result['items']],['pull_request','workflow'])
        self.assertEqual(result['items'][1]['state'],'failure')
    def test_partial_source_does_not_claim_full_connection(self):
        with patch.object(remote,'_github',side_effect=[{'private':False},RuntimeError('access'),{'workflow_runs':[]},[]]):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(result['state'],'partial');self.assertEqual(result['missing'],['pull_request'])
