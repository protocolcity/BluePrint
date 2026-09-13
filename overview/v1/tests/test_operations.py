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
            # Seeded task 1 starts gated (human); an active gate means it never needs
            # routing regardless of labels, so these rows are also ungated here.
            ([], [], True),
            (['worker:agent'], ['agent'], False),
            # needs:routing is a stale label duplicating "no worker assigned"; the desk
            # computes routing need itself (ungated and unassigned), per STATES_AND_TERMS D10.
            (['worker:agent', 'needs:routing'], ['agent'], False),
            (['worker:agent', 'worker:second'], ['agent', 'second'], False),
        ]:
            with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
                conn.execute('UPDATE tasks SET labels=?, gate_type=? WHERE id=1', (json.dumps(labels), None))
            order = operations_snapshot(self.root)['orders'][0]
            self.assertEqual(order['project'], 'product')
            self.assertEqual(order['workers'], expected_workers)
            self.assertEqual(order['needs_routing'], needs_routing)
    def test_owner_marker_reads_live_and_parked_with_since(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='in_progress' WHERE id=1")
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Intake: filed','you','2026-09-12T00:00:00Z')")
            conn.execute("INSERT INTO task_comments VALUES(2,1,'Owner: bp-claude-implementer\nStart: 2026-09-12T05:00:00Z','bp-claude-implementer','2026-09-12T05:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['status_word'], 'Live')
        self.assertEqual(order['live_with'], 'bp-claude-implementer')
        self.assertIsNone(order['parked_by'])
        self.assertEqual(order['since'], '2026-09-12T05:00:00Z')
    def test_owner_marker_reads_parked_from_in_review(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='in_review' WHERE id=1")
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: bp-claude-implementer\nStart: t','bp-claude-implementer','2026-09-12T05:00:00Z')")
            conn.execute("INSERT INTO task_comments VALUES(2,1,'Parked: done for now','bp-claude-implementer','2026-09-12T06:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['status_word'], 'Parked')
        self.assertEqual(order['parked_by'], 'bp-claude-implementer')
        self.assertIsNone(order['live_with'])
        self.assertEqual(order['since'], '2026-09-12T05:00:00Z')
        self.assertEqual(order['last_note'], 'Parked: done for now')
    def test_release_comment_clears_prior_owner_marker(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog' WHERE id=1")
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: bp-claude-implementer\nStart: t','bp-claude-implementer','2026-09-12T05:00:00Z')")
            conn.execute("INSERT INTO task_comments VALUES(2,1,'Released by bp-claude-implementer \xe2\x80\x94 returning to backlog','bp-claude-implementer','2026-09-12T06:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['status_word'], 'Open')
        self.assertIsNone(order['live_with']);self.assertIsNone(order['parked_by']);self.assertIsNone(order['since'])
    def test_blocked_release_comment_clears_prior_owner_marker(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog' WHERE id=1")
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: bp-claude-implementer\nStart: t','bp-claude-implementer','2026-09-12T05:00:00Z')")
            conn.execute("INSERT INTO task_comments VALUES(2,1,'Blocked: waiting on credentials\nNext step: ask You','bp-claude-implementer','2026-09-12T06:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertIsNone(order['live_with']);self.assertIsNone(order['parked_by'])
    def test_backlog_reads_open_with_no_claim(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', gate_type=NULL WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['status_word'], 'Open')
        self.assertIsNone(order['live_with']);self.assertIsNone(order['parked_by']);self.assertIsNone(order['since'])
    def test_ready_for_seat_requires_backlog_ungated_unassigned_blockers_clear(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN description TEXT')
            conn.execute("UPDATE tasks SET status='backlog', gate_type=NULL, description='Depends on pc-2' WHERE id=1")
            conn.execute("UPDATE tasks SET status='backlog' WHERE id=2")  # blocker still open
        result = operations_snapshot(self.root)
        order = next(o for o in result['orders'] if o['id']=='pc-1')
        self.assertEqual(order['blockers'], ['pc-2'])
        self.assertIsNone(order['ready_for'])
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='done' WHERE id=2")  # blocker cleared
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['ready_for'], 'agent')
    def test_parent_label_surfaces_on_row(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1', (json.dumps(['worker:agent','parent:pc-99']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['parent'], 'pc-99')
    def test_face_reason_names_the_rule_that_fired(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET gate_type='human', gate_note='Ratify the plan' WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['attention_face'], 'decide')
        self.assertEqual(order['face_reason'], 'Ratify the plan')
    def test_persona_worker_you_never_shows_as_assignment(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=?, gate_type=NULL WHERE id=1', (json.dumps(['worker:you']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['owner'], 'Unassigned')
        self.assertTrue(order['needs_routing'])
    def test_persona_qualifier_labels_never_need_routing(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:todo'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['face_reason'], 'Your todo')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',
                         (json.dumps(['worker:you', 'you:remind', 'reminder:2026-12-20']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['face_reason'], 'Reminder 2026-12-20')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',
                         (json.dumps(['worker:you', 'you:note']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['face_reason'], 'Your note')
    def test_persona_remind_falls_back_to_gate_until_then_no_date(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL, gate_until=? WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:remind']), '2026-12-20T00:00:00Z'))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['face_reason'], 'Reminder 2026-12-20')
        self.assertEqual(order['persona'], 'Reminder 2026-12-20')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET gate_until=NULL WHERE id=1')
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['face_reason'], 'Reminder (no date)')
        self.assertEqual(order['persona'], 'Reminder (no date)')
    def test_persona_field_matches_face_reason_for_qualifier_rows_and_is_empty_otherwise(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:todo'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['persona'], 'Your todo')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1', (json.dumps(['worker:you']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['persona'], '')
    def test_worker_you_with_retired_host_qualifier_still_needs_routing(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:host'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['needs_routing'])
    def test_unlabeled_backlog_needs_routing(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', labels='[]', gate_type=NULL WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['needs_routing'])
    def test_deferred_gate_never_needs_routing(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', labels='[]', gate_type='deferred' WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
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
        self.assertEqual(row['state'],'last_run_failed');self.assertIsNone(row['shift']);self.assertEqual(row['last_run']['outcome'],'error')
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
    def test_due_and_hold_until_remain_two_work_dates(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_until=? WHERE id=1',
                         (json.dumps(['worker:agent','deadline:2026-09-20']),'timer','2026-09-22T12:00:00+00:00'))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(sorted(d['kind'] for d in dates),['deadline','timer'])
        self.assertEqual({d['task_id'] for d in dates},{'pc-1'})
