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

    def test_assignment_and_routing_are_separate_from_project(self):
        self.seed()
        for labels, expected_workers, needs_routing in [
            ([], [], True),
            (['worker:agent'], ['agent'], False),
            (['worker:agent', 'needs:routing'], ['agent'], True),
            (['worker:agent', 'worker:second'], ['agent', 'second'], False),
        ]:
            with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
                conn.execute('UPDATE tasks SET labels=? WHERE id=1', (json.dumps(labels),))
            order = operations_snapshot(self.root)['orders'][0]
            self.assertEqual(order['project'], 'product')
            self.assertEqual(order['workers'], expected_workers)
            self.assertEqual(order['needs_routing'], needs_routing)
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
        self.assertEqual(result['orders'][0]['gate_type'],'deferred')
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
    def _runtime_with_ledger(self, ledger_text, in_flight=None, fresh=True):
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True,exist_ok=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'agent':{'display':'Agent','command':['example-agent'],'identity':'agent','kind':'lane'}}}))
        tick=datetime.now(timezone.utc)-(timedelta(seconds=0) if fresh else timedelta(hours=1))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':tick.isoformat(),'in_flight':in_flight or []}))
        (runtime/'ledger').mkdir(exist_ok=True)
        (runtime/'ledger/agent.log').write_text(ledger_text)
        return runtime
    @staticmethod
    def _stamp(delta):
        return (datetime.now(timezone.utc)-delta).strftime('%Y-%m-%dT%H:%M:%SZ')
    def test_open_ledger_shift_paints_working_with_candidates(self):
        started=self._stamp(timedelta(minutes=2))
        self._runtime_with_ledger(f'{started} START identity=agent kind=lane model=default budget_secs=1500 max_passes=1 queue=1\n{started} CANDIDATE ticket=wf-9 title="Real work" product=workforce priority=2\n')
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'working')
        self.assertEqual(row['shift']['candidates'],['wf-9'])
        self.assertFalse(row['shift']['stale'])
        self.assertEqual(row['shift']['budget_secs'],1500)
        self.assertEqual(row['shift']['source'],'engine ledger')
        self.assertFalse(row['shift']['lock_held'])
        self.assertIsNone(row['last_run'])
    def test_terminal_row_closes_shift_and_keeps_last_run(self):
        started=self._stamp(timedelta(minutes=5));stopped=self._stamp(timedelta(minutes=1))
        self._runtime_with_ledger(f'{started} START identity=agent kind=lane budget_secs=1500\n{started} CANDIDATE ticket=wf-9\n{stopped} DONE rc=0 on_pass=1 secs=240\n{stopped} STOP reason="single-pass complete"\n')
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'idle')
        self.assertIsNone(row['shift'])
        self.assertEqual(row['last_run']['outcome'],'stop')
    def test_error_row_closes_shift(self):
        started=self._stamp(timedelta(minutes=5));errored=self._stamp(timedelta(minutes=1))
        self._runtime_with_ledger(f'{started} START identity=agent kind=lane budget_secs=1500\n{errored} ERROR reason="agent exit" rc=143 on_pass=1\n')
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'idle');self.assertIsNone(row['shift']);self.assertEqual(row['last_run']['outcome'],'error')
    def test_stale_open_shift_is_never_working(self):
        started=self._stamp(timedelta(hours=3))
        self._runtime_with_ledger(f'{started} START identity=agent kind=lane budget_secs=1500\n{started} CANDIDATE ticket=wf-9\n')
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'stale_shift')
        self.assertTrue(row['shift']['stale'])
        self.assertEqual(row['shift']['candidates'],['wf-9'])
    def test_open_shift_with_stale_heartbeat_stays_unknown(self):
        started=self._stamp(timedelta(minutes=2))
        self._runtime_with_ledger(f'{started} START identity=agent kind=lane budget_secs=1500\n',fresh=False)
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'unknown')
        self.assertFalse(row['shift']['stale'])
    def test_daemon_in_flight_still_paints_working_without_ledger_rows(self):
        self._runtime_with_ledger('',in_flight=['agent'])
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'working');self.assertIsNone(row['shift'])
    def test_ledger_outside_workspace_is_not_read(self):
        started=self._stamp(timedelta(minutes=2))
        runtime=self._runtime_with_ledger('')
        with tempfile.TemporaryDirectory() as other:
            outside=Path(other)/'agent.log';outside.write_text(f'{started} START identity=agent kind=lane budget_secs=1500\n')
            (runtime/'ledger/agent.log').unlink();(runtime/'ledger/agent.log').symlink_to(outside)
            row=operations_snapshot(self.root)['agents'][0]
            self.assertEqual(row['state'],'idle');self.assertIsNone(row['shift'])
    def test_dry_run_start_is_not_an_open_shift(self):
        started=self._stamp(timedelta(minutes=1))
        self._runtime_with_ledger(f'{started} START identity=agent kind=job budget_secs=2100 max_passes=1 dry_run=1 chain_len=0\n{started} DONE dry_run=1 argv_head=/usr/bin/python argv_len=6\n')
        row=operations_snapshot(self.root)['agents'][0]
        self.assertEqual(row['state'],'idle');self.assertIsNone(row['shift'])
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
