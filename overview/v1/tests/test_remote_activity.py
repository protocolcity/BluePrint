import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from server import remote_activity as remote

_RECENT = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
_OLD = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat().replace('+00:00', 'Z')


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
        values=[{'private':True,'default_branch':'main'},[{'title':'Fix','html_url':'https://github.com/org/repo/pull/1','state':'open','updated_at':_RECENT,'head':{'sha':'abc'}}],[],{'workflow_runs':[{'name':'Tests','status':'completed','conclusion':'failure','head_sha':'abc','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/2'}]},[]]
        with patch.object(remote,'_github',side_effect=values): result=remote._load_repo('gh',{'repo':'org/repo','project':'example'})
        self.assertTrue(result['private']);self.assertEqual(result['state'],'connected')
        self.assertEqual([r['kind'] for r in result['items']],['pull_request','workflow'])
        self.assertEqual(result['items'][1]['state'],'failure')
    def test_partial_source_does_not_claim_full_connection(self):
        with patch.object(remote,'_github',side_effect=[{'private':False},RuntimeError('access'),[],{'workflow_runs':[]},[]]):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(result['state'],'partial');self.assertEqual(result['missing'],['pull_request'])
    def test_merged_pull_request_in_window_is_included(self):
        values=[{'private':False},[],[{'title':'Ship it','html_url':'https://github.com/org/repo/pull/9','state':'closed','merged_at':_RECENT,'number':9}],{'workflow_runs':[]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['pr_event'],'merged')
    def test_closed_pull_request_outside_window_is_excluded(self):
        values=[{'private':False},[],[{'title':'Old','html_url':'https://github.com/org/repo/pull/3','state':'closed','closed_at':_OLD,'number':3}],{'workflow_runs':[]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(result['items'],[])
        self.assertTrue(result['quiet'])
    def test_consecutive_identical_workflow_runs_collapse(self):
        run={'name':'Source validation','status':'completed','conclusion':'success','head_sha':'abc','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/1'}
        other=dict(run, head_sha='def', html_url='https://github.com/org/repo/actions/runs/2')
        values=[{'private':False},[],[],{'workflow_runs':[run,dict(run),other,other]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(len(result['items']),2)
        self.assertEqual(result['items'][0]['count'],2)
        self.assertEqual(result['items'][1]['count'],2)
    def test_repositories_group_rows_and_mark_quiet(self):
        spec={'repo':'org/repo','project':'example','role':'product source'}
        with patch.object(remote,'_github',side_effect=[{'private':False},[],[],{'workflow_runs':[]},[]]):
            quiet=remote._load_repo('gh',spec)
        self.assertEqual(quiet['role'],'product source')
        self.assertTrue(quiet['quiet'])
        pr={'title':'Fix','html_url':'https://github.com/org/repo/pull/1','state':'open','updated_at':_RECENT,'number':1,'head':{'sha':'abc'}}
        with patch.object(remote,'_github',side_effect=[{'private':False},[pr],[],{'workflow_runs':[]},[]]):
            active=remote._load_repo('gh',spec)
        self.assertFalse(active['quiet'])
        self.assertEqual(active['items'][0]['project'],'example')
