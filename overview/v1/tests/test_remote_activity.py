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
    def test_workflow_collapse_happens_before_window_filter(self):
        run_a={'name':'CI','status':'completed','conclusion':'success','head_sha':'abc','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/1'}
        run_b={'name':'CI','status':'completed','conclusion':'failure','head_sha':'def','updated_at':_OLD,'html_url':'https://github.com/org/repo/actions/runs/2'}
        run_c=dict(run_a, html_url='https://github.com/org/repo/actions/runs/3')
        values=[{'private':False},[],[],{'workflow_runs':[run_a,dict(run_a),run_b,run_c]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        workflows=[row for row in result['items'] if row['kind']=='workflow']
        self.assertEqual(len(workflows),2)
        self.assertEqual(workflows[0]['count'],2)
        self.assertEqual(workflows[1]['count'],1)
    def test_cache_key_includes_window_seconds(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'.blueprint').mkdir()
            spec=[{'repo':'org/repo'}]
            (root/'.blueprint/connections.json').write_text(json.dumps({'github':{'repositories':spec}}))
            remote._CACHE.clear()
            specs_json=json.dumps(spec,sort_keys=True)
            key=(str(root.resolve()),specs_json,remote._WINDOW_SECONDS)
            remote._CACHE[key]={'checked':0,'busy':False,'data':{'state':'loading','repositories':[]}}
            values=[{'private':False},[],[],{'workflow_runs':[]},[]]
            with patch.object(remote,'_github',side_effect=values):
                remote._refresh(key,'gh',spec,root)
            self.assertIn(key,remote._CACHE)
            old_key=(str(root.resolve()),specs_json)
            self.assertNotIn(old_key,remote._CACHE)
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

    def test_groups_checks_under_shared_commit_and_sort_exceptions_first(self):
        pr={'title':'Ship','html_url':'https://github.com/org/repo/pull/2','state':'open','updated_at':_RECENT,'number':2,'head':{'sha':'abc'}}
        fail={'name':'CI','status':'completed','conclusion':'failure','head_sha':'abc','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/1'}
        ok={'name':'CI','status':'completed','conclusion':'success','head_sha':'def','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/2'}
        values=[{'private':False},[pr],[],{'workflow_runs':[ok,fail]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertEqual(len(result['groups']),2)
        self.assertEqual(result['groups'][0]['priority'],0)
        self.assertEqual(len(result['groups'][0]['items']),2)
        kinds={item['kind'] for item in result['groups'][0]['items']}
        self.assertEqual(kinds,{'pull_request','workflow'})

    def test_installed_revision_matches_deployment_receipt_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'.blueprint').mkdir()
            (root/'.blueprint/deployment.json').write_text(json.dumps({
                'version':'1.2.3','source_head':'abc123full','activated_at':_RECENT}))
            pr={'title':'Ship','html_url':'https://github.com/org/repo/pull/2','state':'closed','merged_at':_RECENT,'number':2,'head':{'sha':'abc123full'}}
            run={'name':'CI','status':'completed','conclusion':'success','head_sha':'abc123full','updated_at':_RECENT,'html_url':'https://github.com/org/repo/actions/runs/1'}
            values=[{'private':False},[],[pr],{'workflow_runs':[run]},[]]
            spec={'repo':'org/repo','project':'protocolcity'}
            with patch.object(remote,'_github',side_effect=values):
                result=remote._load_repo('gh',spec,root)
        self.assertEqual(result['deployment']['state'],'verified')
        self.assertEqual(result['groups'][0]['deploy_state'],'deployed')
        self.assertEqual(result['summary']['recent_merges'],1)

    def test_revision_without_source_head_does_not_mark_deployed(self):
        receipt={'version':'1.2.3','revision':'abc123full'}
        items=[{'kind':'pull_request','sha':'abc123full'}]
        self.assertEqual(remote._deploy_state(items,receipt),'unknown')

    def test_version_only_release_match_is_version_note_not_installed(self):
        receipt={'version':'1.2.3','revision':'other'}
        items=[{'kind':'release','title':'v1.2.3','sha':'zzz'}]
        self.assertEqual(remote._deploy_state(items,receipt),'version_note')

    def test_merged_pull_request_without_pr_event_badges_merged(self):
        pr={'kind':'pull_request','title':'Ship','state':'closed','merged_at':_RECENT,'number':2}
        self.assertEqual(remote._group_badge([pr]),'merged')
        self.assertIn('merged',remote._group_headline([pr]))

    def test_merged_flag_without_pr_event_badges_merged(self):
        pr={'kind':'pull_request','title':'Ship','state':'closed','merged':True,'number':3}
        self.assertEqual(remote._group_badge([pr]),'merged')

    def test_missing_deployment_evidence_stays_unknown(self):
        pr={'title':'Ship','html_url':'https://github.com/org/repo/pull/2','state':'closed','merged_at':_RECENT,'number':2,'head':{'sha':'zzz'}}
        values=[{'private':False},[],[pr],{'workflow_runs':[]},[]]
        with patch.object(remote,'_github',side_effect=values):
            result=remote._load_repo('gh',{'repo':'org/repo'})
        self.assertIsNone(result['deployment'])
        self.assertEqual(result['groups'][0]['deploy_state'],'unknown')
        self.assertEqual(result['groups'][0]['badge'],'merged')

    def test_remote_snapshot_reports_cache_age(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'.blueprint').mkdir()
            (root/'.blueprint/connections.json').write_text(json.dumps({'github':{'repositories':[{'repo':'org/repo'}]}}))
            remote._CACHE.clear()
            with patch.object(remote,'shutil') as shutil_mod, patch.object(remote,'_github',side_effect=[{'private':False},[],[],{'workflow_runs':[]},[]]):
                shutil_mod.which.return_value='gh'
                first=remote.remote_snapshot(root)
                second=remote.remote_snapshot(root)
        self.assertIn('cache_age_seconds', second)
        self.assertGreaterEqual(second['cache_age_seconds'], 0)

class DeployStateShaMatchTests(unittest.TestCase):
    """pc-1487 second pass: an abbreviated receipt head must match a full group sha."""

    def test_short_source_head_matches_full_sha(self):
        from server.remote_activity import _deploy_state
        items = [{'kind': 'pull_request', 'sha': 'a7a1c60f0e2b4c1d9e8f7a6b5c4d3e2f1a0b9c8d'}]
        self.assertEqual(_deploy_state(items, {'source_head': 'a7a1c60'}), 'deployed')
        self.assertEqual(_deploy_state(items, {'source_head': 'a7a1c6'}), 'unknown')
        self.assertEqual(_deploy_state(items, {'source_head': 'ffffffff'}), 'unknown')

