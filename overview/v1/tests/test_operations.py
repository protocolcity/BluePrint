import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from server.operations import operations_snapshot, store_last_change, WORKLANE_API_PATH
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
        self.assertEqual(order['since'], '2026-09-12T06:00:00Z')
        self.assertEqual(order['last_note'], 'Parked: done for now')
    def test_watch_exempts_a_seat_parked_handoff_but_not_a_you_parked_one(self):
        """PROTOCOL 7a / review finding (pc-1494 recovery): a parked order
        held by a registered seat is the host integrator's queue, not a
        person's Watch; the same order parked by You still earns Watch."""
        self.seed()
        runtime = self.root/'workforce/local'; runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps(
            {'workers': {'bp-claude-implementer': {'display': 'Seat', 'kind': 'lane'}}}))
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='in_review', gate_type=NULL, updated_at='2020-01-01T00:00:00Z' WHERE id=1")
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: bp-claude-implementer\nStart: t','bp-claude-implementer','2020-01-01T00:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['parked_by'], 'bp-claude-implementer')
        self.assertEqual(order['attention_face'], '')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('DELETE FROM task_comments')
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: you\nStart: t','you','2020-01-01T00:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['parked_by'], 'you')
        self.assertEqual(order['attention_face'], 'watch')
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
        self.assertEqual(order['board_band'], 'act_now')
        self.assertEqual(order['row_face'], 'Decide')
        self.assertNotEqual(order['row_status'], 'Needs you')
    def test_bare_worker_you_is_assigned_to_you_not_unassigned(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=?, gate_type=NULL WHERE id=1', (json.dumps(['worker:you']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['assigned_you'])
        self.assertEqual(order['owner'], 'You')
        self.assertFalse(order['needs_routing'])
    def test_persona_qualifier_labels_never_need_routing(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:todo'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['persona'], 'Your todo')
        self.assertEqual(order['kind'], 'todo')
        # D16: an undated personal item is Kind only; it never enters For You.
        self.assertEqual(order['attention_face'], '')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',
                         (json.dumps(['worker:you', 'you:remind', 'reminder:2026-09-01']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['persona'], 'Reminder 2026-09-01')
        self.assertEqual(order['kind'], 'reminder')
        self.assertEqual(order['attention_face'], 'due')
        self.assertEqual(order['face_reason'], 'Reminder due 2026-09-01')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',
                         (json.dumps(['worker:you', 'you:note']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['persona'], 'Your note')
        self.assertEqual(order['kind'], 'note')
        self.assertEqual(order['attention_face'], '')
    def test_persona_remind_without_a_date_reads_as_kind_todo(self):
        """STATES_AND_TERMS.md §6 (D16): you:remind carries no date of its
        own; without a reminder:<date> label it is an undated personal item
        and reads as Kind todo. 'Reminder (no date)' must never appear."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:remind'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['persona'], 'Your todo')
        self.assertEqual(order['kind'], 'todo')
        self.assertEqual(order['attention_face'], '')
        self.assertNotIn('no date', order['persona'])
    def test_persona_field_matches_kind_for_qualifier_rows_and_is_empty_otherwise(self):
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
        self.assertEqual(order['kind'], 'work')
    def test_worker_you_with_host_qualifier_is_assigned_to_you(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:host'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['assigned_you'])
        self.assertEqual(order['owner'], 'You')
        self.assertFalse(order['needs_routing'])
    def test_worker_you_host_in_progress_with_owner_marker_reads_live_with_you(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('in_progress', json.dumps(['worker:you', 'you:host'])))
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: you\nStart: 2026-09-13T10:00:00Z','you','2026-09-13T10:00:00Z')")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['assigned_you'])
        self.assertEqual(order['owner'], 'You')
        self.assertFalse(order['needs_routing'])
        self.assertEqual(order['live_with'], 'you')
    def test_open_blocker_sets_blocked_on_and_clears_when_dependency_done(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN description TEXT')
            conn.execute("UPDATE tasks SET status='backlog', gate_type=NULL, description='Depends on pc-2' WHERE id=1")
            conn.execute("UPDATE tasks SET status='backlog' WHERE id=2")
        result = operations_snapshot(self.root)
        order = next(o for o in result['orders'] if o['id'] == 'pc-1')
        self.assertEqual(order['blocked_on'], 'open')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='done' WHERE id=2")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['blocked_on'], 'clear')
    def test_unknown_blocker_in_unavailable_store_stays_blocked(self):
        self.seed()
        self.seed('workforce', registered=True)
        manifest = self.root/'workforce'/'.protocolcity'/'desk-join.json'
        manifest.write_text(json.dumps({'slug': 'workforce', 'prefix': 'wf', 'display': 'WorkForce'}))
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN description TEXT')
            conn.execute("UPDATE tasks SET status='backlog', gate_type=NULL, description='Depends on wf-1' WHERE id=1")
        (self.root/'worklane/worklane/local/data/workforce.db').write_bytes(b'not sqlite')
        order = next(o for o in operations_snapshot(self.root)['orders'] if o['id'] == 'pc-1')
        self.assertEqual(order['blocked_on'], 'unknown')
        self.assertIn('dependency unknown: wf-1 (store unavailable)', order['blocked_note'])
    def test_unknown_blocker_id_stays_blocked(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN description TEXT')
            conn.execute("UPDATE tasks SET status='backlog', gate_type=NULL, description='Depends on pc-999' WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['blocked_on'], 'unknown')
        self.assertEqual(order['blocked_note'], 'dependency unknown: pc-999')
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
    def test_personal_reminder_is_assigned_to_you_not_unassigned(self):
        """STATES_AND_TERMS.md §5 fixture 1: a personal reminder assigned to
        You reads Assigned to You, never Assigned to Unassigned."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['worker:you', 'you:remind'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['assigned_you'])
        self.assertEqual(order['owner'], 'You')
    def test_d16_for_you_fixtures(self):
        """STATES_AND_TERMS.md §1.4/§5 (D16): an undated todo has Kind todo
        and no face; a reminder dated today is Due; a reminder dated
        tomorrow is Kind reminder with no face; an open inbox-report is
        Read. All four fixtures are assigned to You (§5 fixture list)."""
        # Due compares against the host's local calendar day (attention_view.local_today),
        # so the fixture must use the same clock; the UTC date differs after local
        # evening and made this test fail at 00:00Z (2026-09-14).
        from server.attention_view import local_today
        today = local_today(datetime.now(timezone.utc))
        tomorrow = today + timedelta(days=1)
        self.seed()
        cases = [
            (['worker:you', 'you:todo'], '', 'todo', True),
            (['worker:you', 'you:remind', 'reminder:' + today.isoformat()], 'due', 'reminder', True),
            (['worker:you', 'you:remind', 'reminder:' + tomorrow.isoformat()], '', 'reminder', True),
            (['worker:you', 'inbox-report'], 'read', 'report', True),
        ]
        for labels, expected_face, expected_kind, expected_assigned_you in cases:
            with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
                conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                             ('backlog', json.dumps(labels)))
            order = operations_snapshot(self.root)['orders'][0]
            with self.subTest(labels=labels):
                self.assertEqual(order['assigned_you'], expected_assigned_you)
                self.assertEqual(order['attention_face'], expected_face)
                self.assertEqual(order['kind'], expected_kind)
    def test_deadline_only_order_reads_kind_reminder_not_work(self):
        """Review finding (pc-1494 recovery): a deadline:-only order is Kind
        reminder (§6), not Kind work."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET status=?, labels=?, gate_type=NULL WHERE id=1',
                         ('backlog', json.dumps(['deadline:2026-12-20'])))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['kind'], 'reminder')
    def test_agent_owned_human_gate_stays_assigned_to_the_agent_in_for_you(self):
        """STATES_AND_TERMS.md §5 fixture 2: an agent-owned human gate is
        visible in For You (attention_face='decide') but still assigned to
        the agent, not You."""
        self.seed()
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['gate_type'], 'human')
        self.assertEqual(order['attention_face'], 'decide')
        self.assertFalse(order['assigned_you'])
        self.assertEqual(order['owner'], 'agent')
    def test_human_gate_with_no_worker_is_a_decision_assigned_to_you(self):
        """An unrouted human gate is a human-owned decision: assigned to
        You, not Unassigned, per STATES_AND_TERMS.md §5."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET labels='[]', gate_type='human', gate_note='Approve the plan' WHERE id=1")
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['assigned_you'])
        self.assertEqual(order['owner'], 'You')
        self.assertEqual(order['attention_face'], 'decide')
    def test_ungated_ready_agent_order_is_visible_and_ready(self):
        """STATES_AND_TERMS.md §5 fixture 3: an ungated ready agent order."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', labels=?, gate_type=NULL WHERE id=1",
                         (json.dumps(['worker:agent']),))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertEqual(order['ready_for'], 'agent')
    def test_deferred_and_tracking_orders_are_visible_but_never_ready(self):
        """STATES_AND_TERMS.md §5 fixture 4: deferred/tracking records
        remain visible under All open (every non-done/canceled order) but
        are never reported ready."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', labels=?, gate_type='tracking' WHERE id=1",
                         (json.dumps(['worker:agent']),))
        result = operations_snapshot(self.root)
        order = next(o for o in result['orders'] if o['id'] == 'pc-1')
        self.assertEqual(order['gate_type'], 'tracking')
        self.assertIsNone(order['ready_for'])
    def test_expired_timer_is_distinguished_from_an_active_embargo(self):
        """An expired timer gate is not an active embargo (SURFACES review,
        STATES_AND_TERMS.md §5)."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute("UPDATE tasks SET status='backlog', labels='[]', gate_type='timer', gate_until=? WHERE id=1",
                         ('2020-01-01T00:00:00Z',))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['gate_expired'])
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET gate_until=? WHERE id=1", ('2099-01-01T00:00:00Z',))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['gate_expired'])
    def test_gate_expired_treats_timezone_naive_gate_until_as_utc(self):
        """Review finding (pc-1482): a naive gate_until (no offset, common in
        the stores) must be treated as UTC, not silently read as not-expired."""
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute("UPDATE tasks SET status='backlog', labels='[]', gate_type='timer', gate_until=? WHERE id=1",
                         ('2020-01-01T00:00:00',))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertTrue(order['gate_expired'])
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET gate_until=? WHERE id=1", ('2099-01-01T00:00:00',))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['gate_expired'])
    def test_gate_expired_never_raises_on_unparsable_gate_until(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute("UPDATE tasks SET status='backlog', labels='[]', gate_type='timer', gate_until=? WHERE id=1",
                         ('not-a-date',))
        order = operations_snapshot(self.root)['orders'][0]
        self.assertFalse(order['gate_expired'])
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
        self.assertEqual(result['agents_floor'], {'working': 0, 'idle': 0, 'error': 0, 'stale': 0, 'quiet': 0})
        self.assertEqual(result['throughput']['state'], 'unavailable')
        self.assertEqual(result['throughput']['closes'], 0)

    def test_placeholder_job_is_not_presented_as_working(self):
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'job':{'command':['true'],'kind':'job'}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':['job']}))
        result=operations_snapshot(self.root)
        self.assertEqual(result['agents'][0]['state'],'not_configured')
        self.assertFalse(result['agents'][0]['configured'])
        self.assertTrue(any(s['name']=='Agent/job configuration' for s in result['sources']))

    def test_seat_whose_provider_executable_is_missing_on_disk_reads_the_missing_text(self):
        """pc-1476: a seat naming an absolute provider executable that no
        longer exists on disk reads 'provider missing on disk', not the
        generic placeholder text, and counts not configured."""
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'seat':{
            'display':'Seat','identity':'seat','kind':'lane','command':['/nowhere/claude','-p','x']}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':[]}))
        result=operations_snapshot(self.root)
        agent=result['agents'][0]
        self.assertEqual(agent['state'],'not_configured')
        self.assertFalse(agent['configured'])
        self.assertEqual(agent['configuration'],'provider missing on disk')

    def test_seat_whose_provider_executable_is_outside_trusted_locations_reads_the_untrusted_text(self):
        """review finding pc-1476: a seat naming an absolute executable that
        exists but resolves outside the trusted install roots (home,
        /opt/homebrew, /usr/local, the Codex app) reads 'provider outside
        trusted locations', not 'Command configured', and counts not
        configured."""
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        with tempfile.TemporaryDirectory(dir='/tmp') as outside:
            exe=Path(outside)/'claude'
            exe.write_text('#!/bin/sh\n')
            exe.chmod(0o755)
            (runtime/'roster.json').write_text(json.dumps({'workers':{'seat':{
                'display':'Seat','identity':'seat','kind':'lane','command':[str(exe),'-p','x']}}}))
            (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':[]}))
            result=operations_snapshot(self.root)
        agent=result['agents'][0]
        self.assertEqual(agent['state'],'not_configured')
        self.assertFalse(agent['configured'])
        self.assertEqual(agent['configuration'],'provider outside trusted locations')

    def test_work_order_deadlines_project_without_a_second_date_store(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=? WHERE id=1',(json.dumps(['worker:agent','deadline:2026-09-20']),))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(len(dates),1)
        self.assertEqual(dates[0]['task_id'],'pc-1')
        self.assertEqual(dates[0]['product'],'product')
        self.assertEqual(dates[0]['dtstart'],'2026-09-20')
    def test_project_claimed_count_is_live_claim_not_status_alone(self):
        # 'claimed' is a WorkLane fact (in_progress + a signed Owner marker) —
        # it must never be labelled "working"; a days-old human claim counts
        # here exactly like a fresh agent shift, which is why Overview and
        # Map keep it separate from 'running' (pc-1483).
        self.seed()
        self.assertEqual(operations_snapshot(self.root)['projects'][0]['claimed'],0)
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: bp-grok-implementer\nStart: 2026-09-13T09:00:00Z','bp-grok-implementer','2026-09-13T09:00:00Z')")
        self.assertEqual(operations_snapshot(self.root)['projects'][0]['claimed'],1)
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog' WHERE id=1")
        self.assertEqual(operations_snapshot(self.root)['projects'][0]['claimed'],0)
    def test_project_running_count_is_agent_evidence_not_a_worklane_claim(self):
        # A days-old human claim (Owner marker, no daemon evidence) must not
        # inflate 'running' the way it inflates 'claimed' above.
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Owner: you\nStart: 2026-09-01T09:00:00Z','you','2026-09-01T09:00:00Z')")
        self.assertEqual(operations_snapshot(self.root)['projects'][0]['claimed'],1)
        self.assertEqual(operations_snapshot(self.root)['projects'][0]['running'],0)
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{'agent':{
            'display':'Agent','command':['example-agent'],'identity':'agent','kind':'lane',
            'queue_url':'https://example.invalid/queue?product=product'}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':['agent']}))
        result=operations_snapshot(self.root)
        self.assertEqual(result['agents'][0]['state'],'working')
        self.assertEqual(result['projects'][0]['running'],1)
    def test_project_summary_counts_deferred_and_parked_separately(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("UPDATE tasks SET status='backlog', gate_type='deferred' WHERE id=1")
            conn.execute("INSERT INTO tasks VALUES(3,NULL,'parked','in_review',2,'2026-09-12','[]',NULL,NULL)")
            conn.execute("INSERT INTO task_comments VALUES(1,3,'Owner: agent\nStart: 2026-09-12T05:00:00Z','agent','2026-09-12T05:00:00Z')")
        project=operations_snapshot(self.root)['projects'][0]
        self.assertEqual(project['deferred'], 1)
        self.assertEqual(project['parked'], 1)

    def test_project_last_change_uses_the_latest_meaningful_comment(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Intake: filed','you','2026-09-13T10:00:00Z')")
            conn.execute("INSERT INTO task_comments VALUES(2,1,'Owner: bp-cursor-implementer\nStart: 2026-09-13T14:58:00Z','bp-cursor-implementer','2026-09-13T14:58:00Z')")
        change=operations_snapshot(self.root)['projects'][0]['last_change']
        self.assertEqual(change['order_id'], 'pc-1')
        self.assertEqual(change['verb'], 'claim')
        self.assertEqual(change['actor'], 'bp-cursor-implementer')

    def test_store_last_change_skips_intake_boilerplate(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Intake: filed','you','2026-09-13T10:00:00Z')")
            change=store_last_change(conn, 'pc')
        self.assertIsNone(change)

    def test_project_partial_flag_when_store_exceeds_limit(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            for idx in range(2, 2003):
                conn.execute("INSERT INTO tasks VALUES(?,NULL,'task','backlog',3,'2026-09-12','[]',NULL,NULL)", (idx,))
        project=operations_snapshot(self.root)['projects'][0]
        self.assertTrue(project['partial'])
        self.assertGreater(project['open'], 2000)

    def test_project_running_count_is_seats_only_a_working_job_does_not_count(self):
        # Review finding (pc-1483 recovery 2): overview() and the project
        # rollup here must apply one shared Running rule (seats only,
        # STATES_AND_TERMS §2); a working job (kind='job') shows 'working'
        # on Agents but must not move project.running.
        self.seed()
        runtime=self.root/'workforce/local';runtime.mkdir(parents=True)
        (runtime/'roster.json').write_text(json.dumps({'workers':{
            'agent':{'display':'Agent','command':['example-agent'],'identity':'agent','kind':'lane',
                     'queue_url':'https://example.invalid/queue?product=product'},
            'health-patrol':{'display':'Health patrol','command':['example-job'],'identity':'health-patrol','kind':'job',
                     'queue_url':'https://example.invalid/queue?product=product'}}}))
        (runtime/'daemon.json').write_text(json.dumps({'last_tick':datetime.now(timezone.utc).isoformat(),'in_flight':['health-patrol']}))
        result=operations_snapshot(self.root)
        job=next(a for a in result['agents'] if a['id']=='health-patrol')
        self.assertEqual(job['group'],'job')
        self.assertEqual(job['state'],'working')
        self.assertEqual(result['projects'][0]['running'],0)
        seat=next(a for a in result['agents'] if a['id']=='agent')
        self.assertEqual(seat['group'],'seat')
        self.assertEqual(seat['state'],'idle')
    def test_date_only_gate_until_projects_as_all_day(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_until=? WHERE id=1',
                         (json.dumps(['worker:agent']),'timer','2026-09-13'))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(len(dates),1)
        self.assertEqual(dates[0]['kind'],'timer')
        self.assertTrue(dates[0]['all_day'])
        self.assertEqual(dates[0]['dtstart'],'2026-09-13')
        self.assertEqual(dates[0]['source'],'gate_until')

    def test_due_and_hold_until_remain_two_work_dates(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_until=? WHERE id=1',
                         (json.dumps(['worker:agent','deadline:2026-09-20']),'timer','2026-09-22T12:00:00+00:00'))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(sorted(d['kind'] for d in dates),['deadline','timer'])
        self.assertEqual({d['task_id'] for d in dates},{'pc-1'})
        by_kind={d['kind']:d for d in dates}
        self.assertEqual(by_kind['deadline']['source'],'deadline:2026-09-20')
        self.assertEqual(by_kind['timer']['source'],'gate_until')

    def test_human_gate_note_date_projects_as_mentioned_not_due(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_note=? WHERE id=1',
                         (json.dumps(['worker:agent']),'human','Founder ratification (2026-09-13): decide the leftover stack.'))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(len(dates),1)
        self.assertEqual(dates[0]['kind'],'mentioned')
        self.assertEqual(dates[0]['source'],'gate_note')
        self.assertEqual(dates[0]['dtstart'],'2026-09-13')
        self.assertTrue(dates[0]['attention'])
        self.assertEqual(dates[0]['attention_face'],'decide')

    def test_watch_timer_does_not_mark_calendar_needs_you(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('ALTER TABLE tasks ADD COLUMN gate_until TEXT')
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_until=?, gate_note=? WHERE id=1',
                         (json.dumps(['worker:agent']),'timer','2026-10-12T14:00:00+00:00','Held until review'))
        dates=operations_snapshot(self.root)['work_dates']
        self.assertEqual(dates[0]['kind'],'timer')
        self.assertFalse(dates[0]['attention'])
        self.assertEqual(dates[0]['attention_face'],'watch')
    def test_engine_receipts_missing_are_unavailable(self):
        with patch('server.operations.build_opener') as build_opener:
            result=operations_snapshot(self.root)
            build_opener.assert_not_called()
        for key in ('worklane','workforce','worklane_api','supervisor'):
            engine=result['engines'][key]
            self.assertEqual(engine['state'],'unavailable')
            self.assertIsNone(engine['observed_at'])
            self.assertIsNone(engine['activated_at'])
            self.assertFalse(engine['usable'])
        self.assertIn('receipt',result['engines']['worklane']['detail'].lower())
        self.assertEqual(result['engines']['worklane']['source'],'local/worklane/deployment.json')
        self.assertEqual(result['engines']['workforce']['source'],'local/workforce/deployment.json')
    def _engine_http(self, products=None, products_status=200, products_raw=None,
                     passes=None, pass_status=200, raise_products=None, raise_supervisor=None,
                     supervisor_raw=None):
        class FakeResponse(io.BytesIO):
            def __init__(self, payload=None, status=200, raw=None):
                body=raw if raw is not None else json.dumps(payload if payload is not None else {}).encode()
                super().__init__(body)
                self.status=status
            def __enter__(self): return self
            def __exit__(self, *args): return False
        def fake_open(request, timeout=3):
            url=request.full_url
            if WORKLANE_API_PATH in url:
                if raise_products: raise raise_products
                if products_raw is not None:
                    return FakeResponse(status=products_status, raw=products_raw)
                return FakeResponse(products if products is not None else {'ok':True,'products':[]}, products_status)
            if raise_supervisor: raise raise_supervisor
            if supervisor_raw is not None:
                return FakeResponse(status=pass_status, raw=supervisor_raw)
            return FakeResponse({'passes': passes if passes is not None else []}, pass_status)
        return fake_open
    def test_engine_versions_reachability_and_supervisor_pass(self):
        (self.root/'local/worklane').mkdir(parents=True)
        (self.root/'local/workforce').mkdir(parents=True)
        (self.root/'local/worklane/deployment.json').write_text(json.dumps({
            'version':'0.1.7+test','port':8799,'activated_at':'2026-09-13T00:21:04+00:00'}))
        (self.root/'local/workforce/deployment.json').write_text(json.dumps({
            'version':'0.1.9+test','api_origin':'http://127.0.0.1:8797','activated_at':'2026-09-13T08:29:50+00:00'}))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=self._engine_http(
                products={'ok':True,'products':[{'slug':'product'}]},
                passes=[{'generated_at':'2026-09-13T03:41:00Z','pass_outcome':'dispatched'}])
            result=operations_snapshot(self.root)
        receipt=result['engines']['worklane']
        self.assertEqual(receipt['state'],'installed')
        self.assertEqual(receipt['version'],'0.1.7+test')
        self.assertEqual(receipt['source'],'local/worklane/deployment.json')
        self.assertEqual(receipt['activated_at'],'2026-09-13T00:21:04+00:00')
        self.assertIsNone(receipt['observed_at'])
        self.assertEqual(result['engines']['workforce']['version'],'0.1.9+test')
        self.assertEqual(result['engines']['workforce']['state'],'installed')
        api=result['engines']['worklane_api']
        self.assertEqual(api['state'],'available')
        self.assertTrue(api['reachable'])
        self.assertTrue(api['usable'])
        self.assertEqual(api['http_status'],200)
        self.assertEqual(api['source'],'http://127.0.0.1:8799'+WORKLANE_API_PATH)
        self.assertIsNotNone(api['observed_at'])
        self.assertEqual(api['last_success_at'],api['observed_at'])
        self.assertEqual(result['engines']['supervisor']['state'],'available')
        self.assertEqual(result['engines']['supervisor']['outcome'],'dispatched')
        self.assertTrue(result['engines']['supervisor']['usable'])
        self.assertEqual(result['engines']['supervisor']['source'],'WorkForce /api/supervisor')
    def test_worklane_reachability_unavailable_when_probe_fails(self):
        (self.root/'local/worklane').mkdir(parents=True)
        (self.root/'local/worklane/deployment.json').write_text(json.dumps({'version':'0.1.7','port':8799}))
        from urllib.error import URLError
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=URLError('down')
            result=operations_snapshot(self.root)
        self.assertEqual(result['engines']['worklane']['state'],'installed')
        self.assertEqual(result['engines']['worklane_api']['state'],'unavailable')
        self.assertFalse(result['engines']['worklane_api']['reachable'])
        self.assertFalse(result['engines']['worklane_api']['usable'])
        self.assertIn('not reachable',result['engines']['worklane_api']['detail'].lower())
    def test_worklane_api_http_404_is_reachable_not_usable(self):
        from urllib.error import HTTPError
        (self.root/'local/worklane').mkdir(parents=True)
        (self.root/'local/worklane/deployment.json').write_text(json.dumps({'version':'0.1.7','port':8799}))
        error=HTTPError('http://127.0.0.1:8799'+WORKLANE_API_PATH, 404, 'Not Found', hdrs=None, fp=io.BytesIO(b''))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=self._engine_http(raise_products=error)
            result=operations_snapshot(self.root)
        api=result['engines']['worklane_api']
        self.assertEqual(api['state'],'reachable')
        self.assertTrue(api['reachable'])
        self.assertFalse(api['usable'])
        self.assertEqual(api['http_status'],404)
        self.assertIn('health not verified',api['detail'].lower())
        self.assertIn('404',api['detail'])
        self.assertIn('/api/admin/products',api['source'])
        self.assertNotIn('/health',api['source'])
        self.assertTrue(api['next_step'])
    def test_worklane_api_200_without_products_list_is_not_usable(self):
        (self.root/'local/worklane').mkdir(parents=True)
        (self.root/'local/worklane/deployment.json').write_text(json.dumps({'version':'0.1.7','port':8799}))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=self._engine_http(
                products={'ok':True}, products_status=200)
            result=operations_snapshot(self.root)
        api=result['engines']['worklane_api']
        self.assertEqual(api['state'],'reachable')
        self.assertTrue(api['reachable'])
        self.assertFalse(api['usable'])
    def test_supervisor_failed_pass_is_failed_outcome_not_available(self):
        (self.root/'local/workforce').mkdir(parents=True)
        (self.root/'local/workforce/deployment.json').write_text(json.dumps({
            'version':'0.1.9+test','api_origin':'http://127.0.0.1:8797'}))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=self._engine_http(
                passes=[{'generated_at':'2026-09-13T03:41:00Z','pass_outcome':'provider_failed'}])
            result=operations_snapshot(self.root)
        supervisor=result['engines']['supervisor']
        self.assertEqual(supervisor['state'],'failed')
        self.assertEqual(supervisor['outcome'],'provider_failed')
        self.assertTrue(supervisor['usable'])
        self.assertTrue(supervisor['reachable'])
        self.assertIn('provider failed',supervisor['detail'])
        self.assertTrue(supervisor['next_step'])
        self.assertNotEqual(supervisor['state'],'available')
    def test_supervisor_http_200_malformed_body_is_reachable_not_usable(self):
        (self.root/'local/workforce').mkdir(parents=True)
        (self.root/'local/workforce/deployment.json').write_text(json.dumps({
            'version':'0.1.9+test','api_origin':'http://127.0.0.1:8797'}))
        with patch('server.operations.build_opener') as build_opener:
            build_opener.return_value.open.side_effect=self._engine_http(
                supervisor_raw=b'not-json{', pass_status=200)
            result=operations_snapshot(self.root)
        supervisor=result['engines']['supervisor']
        self.assertTrue(supervisor['reachable'])
        self.assertFalse(supervisor['usable'])
        self.assertEqual(supervisor['http_status'],200)
        self.assertEqual(supervisor['state'],'unavailable')
        self.assertIn('unexpected shape',supervisor['detail'].lower())
        self.assertNotIn('not reachable',supervisor['detail'].lower())

    def test_calendar_doors_count_arrived_deadlines_not_mentions(self):
        self.seed()
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('UPDATE tasks SET labels=?, gate_type=?, gate_note=? WHERE id=1',
                         (json.dumps(['worker:you', 'deadline:2026-09-01']),'', ''))
        (self.root/'.blueprint').mkdir()
        (self.root/'.blueprint'/'calendar.json').write_text(json.dumps({
            'range': 'this week',
            'events': [{'title': 'Standup', 'at': '2026-09-17T10:00:00Z', 'source': 'routine', 'state': 'due'}],
        }))
        result = operations_snapshot(self.root)
        doors = result['calendar_doors']
        self.assertGreaterEqual(doors['due_count'], 2)
        self.assertIn(doors['due_href'], ('/work?attention=due', '/calendar'))
        self.assertTrue(any(item.get('task_id') == 'pc-1' for item in doors['items']))
        self.assertTrue(any(item.get('title') == 'Standup' for item in doors['items']))
        self.assertEqual(doors['next_fire_line'], 'Next fire · none reported')

    def test_disposable_desk_counts_last_24h_closes(self):
        self.seed()
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        old = (now - timedelta(hours=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with sqlite3.connect(self.root/'worklane/worklane/local/data/product.db') as conn:
            conn.execute('CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT)')
            conn.execute("INSERT INTO task_events VALUES(1,2,'status_change','done','seat',?)", (recent,))
            conn.execute("INSERT INTO task_comments VALUES(10,2,'Completed: done','seat',?)", (recent,))
            conn.execute("INSERT INTO tasks VALUES(3,NULL,'ancient','done',1,?,'[]',NULL,NULL)", (old,))
            conn.execute("INSERT INTO task_events VALUES(2,3,'status_change','done','you',?)", (old,))
        result = operations_snapshot(self.root)
        self.assertEqual([order['id'] for order in result['orders']], ['pc-1'])
        throughput = result['throughput']
        self.assertEqual(throughput['closes'], 1)
        self.assertEqual(throughput['state'], 'healthy')
        self.assertEqual(throughput['href'], '/timeline?period=1')
        self.assertEqual(sum(throughput['hours']), 1)
        self.assertEqual(len(throughput['hours']), 24)

class TimestampAndParkMarkerTests(unittest.TestCase):
    """pc-1495 second-pass findings: "Parked by" must count as a park marker and
    park times must compare as instants across the two timestamp formats."""

    def test_parked_by_marker_is_recognised(self):
        from server.operations import _PARKED_RE
        self.assertIsNotNone(_PARKED_RE.search('Parked by bp-cursor-implementer — soft-lock'))
        self.assertIsNotNone(_PARKED_RE.search('Parked: merged main; tests pass'))
        self.assertIsNone(_PARKED_RE.search('Parkeded by nobody'))
        self.assertIsNone(_PARKED_RE.search('Not parked: still live'))

    def test_ts_epoch_orders_sqlite_and_iso_forms_as_instants(self):
        from server.operations import ts_epoch
        earlier = ts_epoch('2026-09-13 21:00:00')          # WorkLane comment form (UTC)
        later = ts_epoch('2026-09-13T21:30:00Z')            # WorkForce shift form
        self.assertIsNotNone(earlier)
        self.assertIsNotNone(later)
        self.assertLess(earlier, later)
        self.assertEqual(ts_epoch('2026-09-13T21:30:00+00:00'), later)
        self.assertIsNone(ts_epoch(''))
        self.assertIsNone(ts_epoch('not a time'))
        # As strings the SQLite form sorts before "T"; the instants must not.
        self.assertTrue('2026-09-13 21:45:00' < '2026-09-13T21:30:00Z')
        self.assertGreater(ts_epoch('2026-09-13 21:45:00'), later)

