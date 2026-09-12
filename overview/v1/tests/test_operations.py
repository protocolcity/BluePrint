import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from server.operations import operations_snapshot
from server.work_order import read_work_order

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def seed(self, name='product', registered=True):
        if registered:
            manifest=self.root/name/'.protocolcity/desk-join.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({'slug':name,'prefix':'pc','display':name}))
        data=self.root/'worklane/worklane/local/data';data.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(data/(name+'.db')) as conn:
            conn.executescript('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT); CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);')
            conn.execute("INSERT INTO tasks VALUES(1,NULL,'<script>unsafe</script>','in_progress',1,'2026-09-12','[\"worker:agent\"]','human','Decide')")
            conn.execute("INSERT INTO tasks VALUES(2,NULL,'finished','done',1,'2026-09-12','[]',NULL,NULL)")
    def test_registered_only_and_detail_identity(self):
        self.seed();self.seed('product.backup',False)
        result=operations_snapshot(self.root)
        self.assertEqual(len(result['orders']),1)
        row=result['orders'][0]
        self.assertEqual(row['id'],'pc-1');self.assertEqual(row['owner'],'agent')
        self.assertEqual(row['status'],'in_progress');self.assertTrue(row['attention'])
        self.assertEqual(result['excluded_stores'],['product.backup.db'])
        self.assertEqual(read_work_order(self.root,row['project'],row['id'])['title'],row['title'])
    def test_partial_store_does_not_erase_readable_records(self):
        self.seed();self.seed('broken')
        (self.root/'worklane/worklane/local/data/broken.db').write_bytes(b'not sqlite')
        result=operations_snapshot(self.root)
        self.assertEqual(len(result['orders']),1)
        self.assertEqual(result['sources'][0]['state'],'partial')
    def test_unregistered_work_labels_do_not_create_agents(self):
        self.seed()
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{}}))
        result=operations_snapshot(self.root)
        self.assertEqual(result['orders'][0]['owner'],'agent')
        self.assertEqual(result['agents'],[])
    def test_first_read_includes_deferred_open_work(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog',gate_type='deferred' WHERE id=1")
        result=operations_snapshot(self.root)
        self.assertEqual(len(result['orders']),1)
        self.assertEqual(result['orders'][0]['status'],'backlog')
        self.assertFalse(result['orders'][0]['attention'])
    def test_stale_daemon_never_claims_idle_or_working(self):
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'agent':{'display':'Agent','command':['example-agent'],'env':{'SECRET':'do not expose'}}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),'in_flight':['agent']}))
        result=operations_snapshot(self.root)
        self.assertEqual(result['agents'][0]['state'],'unknown')
        self.assertNotIn('SECRET',json.dumps(result))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':['agent']}))
        self.assertEqual(operations_snapshot(self.root)['agents'][0]['state'],'working')
    def test_workspace_isolation(self):
        self.seed()
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(operations_snapshot(Path(other))['orders'],[])
        self.assertEqual(len(operations_snapshot(self.root)['orders']),1)
    def test_external_store_not_read(self):
        self.seed()
        with tempfile.TemporaryDirectory() as other:
            path=self.root/'worklane/worklane/local/data/product.db'; path.rename(Path(other)/'outside.db');path.symlink_to(Path(other)/'outside.db')
            result=operations_snapshot(self.root)
            self.assertEqual(result['orders'],[])
            self.assertEqual(result['projects'][0]['state'],'unavailable')
    def test_no_binder_is_not_healthy_empty(self):
        result=operations_snapshot(None)
        self.assertEqual(result['sources'][0]['state'],'unavailable')
        self.assertEqual(result['remote']['state'],'not_connected')

    def test_placeholder_job_is_not_presented_as_working(self):
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'job':{'command':['true'],'kind':'job'}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':['job']}))
        result=operations_snapshot(self.root)
        self.assertEqual(result['agents'][0]['state'],'not_configured')
        self.assertFalse(result['agents'][0]['configured'])
        self.assertTrue(any(s['name']=='Agent/job configuration' for s in result['sources']))
    def test_work_order_deadlines_project_without_a_second_date_store(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',(json.dumps(['worker:agent','deadline:2026-09-20']),))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(len(dates),1)
        self.assertEqual(dates[0]['task_id'],'pc-1')
        self.assertEqual(dates[0]['product'],'product')
        self.assertEqual(dates[0]['dtstart'],'2026-09-20')
