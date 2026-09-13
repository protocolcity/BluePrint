import os
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from server.attention_view import face, face_reason, kind_of
from suite.api.calendar import events_from_task


@contextmanager
def _host_timezone(name):
    """Force the process's local timezone for the duration of the block
    (Unix stdlib only, via TZ + tzset). Used to test the Due face's local-day
    rule without depending on the CI machine's own timezone."""
    previous = os.environ.get('TZ')
    os.environ['TZ'] = name
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = previous
        time.tzset()

class AttentionViewTests(unittest.TestCase):
    def test_faces_keep_gates_and_dated_items_distinct(self):
        now=datetime(2026,9,12,12,tzinfo=timezone.utc)
        examples=[({'gate_type':'human'}, [], 'decide'),
                  ({'gate_type':'human'}, ['inbox-report'], 'read'),
                  ({'gate_type':'timer'}, [], 'watch'),
                  ({'status':'in_progress','updated_at':'2026-09-12T09:00:00Z'}, [], 'watch'),
                  ({'gate_type':'deferred'}, ['inbox-report'], ''),
                  ({'gate_type':'human','gate_note':'parked: later'}, [], ''),
                  # D16: an undated personal item is Kind only, never a face.
                  ({}, ['you:note'], ''), ({}, ['you:todo'], ''), ({}, ['you:remind'], ''),
                  # D16: Due fires only when the reminder/deadline date has arrived.
                  ({}, ['reminder:2026-12-20'], ''), ({}, ['reminder:2026-09-12'], 'due'),
                  ({}, ['reminder:2026-09-01'], 'due'), ({}, ['deadline:2026-09-12'], 'due'),
                  ({}, ['deadline:2026-12-20'], '')]
        for order,labels,expected in examples:
            with self.subTest(order=order,labels=labels):self.assertEqual(face(order,labels,now),expected)
    def test_face_reason_never_says_stalled(self):
        now=datetime(2026,9,12,12,tzinfo=timezone.utc)
        order={'status':'in_progress','updated_at':'2026-09-12T10:20:00Z'}
        reason=face_reason(order,[],'watch',now)
        self.assertIn('No update for',reason)
        self.assertNotIn('stalled',reason.lower())
        self.assertEqual(face_reason({'gate_type':'timer'},[],'watch',now),'Held by a timer gate')
        self.assertEqual(face_reason({'gate_type':'human','gate_note':'Ratify the budget'},[],'decide',now),'Ratify the budget')
        self.assertEqual(face_reason({},['inbox-report'],'read',now),'A report was written for you')
        self.assertEqual(face_reason({},['reminder:2026-09-01'],'due',now),'Reminder due 2026-09-01')
        self.assertEqual(face_reason({},['deadline:2026-09-01'],'due',now),'Deadline due 2026-09-01')
        self.assertEqual(face_reason({},[],'',now),'')
    def test_watch_exempts_a_seat_parked_handoff(self):
        """PROTOCOL 7a / review finding (pc-1494 recovery): a parked handoff
        is the host integrator's queue, not a person's attention, once the
        parker is a registered seat. Held by You (no seat identity on the
        marker) still earns Watch after 90 minutes untouched."""
        now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
        old = {'status': 'in_review', 'updated_at': '2026-09-12T09:00:00Z'}
        self.assertEqual(face({**old, 'parked_by_seat': True}, [], now), '')
        self.assertEqual(face({**old, 'parked_by_seat': False}, [], now), 'watch')

    def test_reminder_date_is_not_a_timer(self):
        task={'id':'pc-1','status':'backlog','labels':['reminder:2026-12-20'],'gate_type':''}
        events=events_from_task(task)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['kind'],'reminder')
        self.assertEqual(str(events[0]['dtstart']),'2026-12-20')
        self.assertEqual(task['gate_type'],'')
    def test_kind_axis_is_independent_of_the_clock(self):
        """STATES_AND_TERMS.md §5/D16: Kind is the item type, computed the
        same whether or not the date has arrived."""
        self.assertEqual(kind_of({}, []), 'work')
        self.assertEqual(kind_of({}, ['you:todo']), 'todo')
        self.assertEqual(kind_of({}, ['you:remind']), 'todo')
        self.assertEqual(kind_of({}, ['you:note']), 'note')
        self.assertEqual(kind_of({}, ['reminder:2026-09-01']), 'reminder')
        self.assertEqual(kind_of({}, ['you:remind', 'reminder:2026-12-20']), 'reminder')
        self.assertEqual(kind_of({}, ['inbox-report']), 'report')

    def test_kind_of_treats_deadline_the_same_as_reminder(self):
        """Review finding (pc-1494 recovery): a deadline-only order is Kind
        reminder (§6), not Kind work."""
        self.assertEqual(kind_of({}, ['deadline:2026-09-20']), 'reminder')

    def test_due_is_evaluated_on_the_workspace_local_calendar_day(self):
        """Review finding (pc-1494 recovery): a bare UTC now.date() reads a
        reminder dated tomorrow as due once it is past ~19:00 in a timezone
        west of UTC. now is a fixed late-evening UTC instant that is still
        today in Chicago but already tomorrow in UTC."""
        now = datetime(2026, 9, 13, 1, 30, tzinfo=timezone.utc)  # 2026-09-12 20:30 Chicago (CDT, UTC-5)
        with _host_timezone('America/Chicago'):
            self.assertEqual(face({}, ['reminder:2026-09-12'], now), 'due')
            self.assertEqual(face({}, ['reminder:2026-09-13'], now), '')

    def test_due_takes_the_earliest_date_across_reminder_and_deadline_labels(self):
        """Review finding (pc-1494 recovery): the first label in list order
        used to win; a future reminder short-circuited a past deadline. The
        earliest parsed date across every reminder:/deadline: label decides,
        and the reason names whichever label produced it."""
        now = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        # Future reminder listed first, past reminder listed second: still due.
        labels = ['reminder:2026-12-20', 'reminder:2026-09-01']
        self.assertEqual(face({}, labels, now), 'due')
        # Future reminder plus a past deadline: due, and the deadline is named.
        labels = ['reminder:2026-12-20', 'deadline:2026-09-01']
        self.assertEqual(face({}, labels, now), 'due')
        self.assertEqual(face_reason({}, labels, 'due', now), 'Deadline due 2026-09-01')
