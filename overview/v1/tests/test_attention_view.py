import unittest
from datetime import datetime, timezone
from server.attention_view import face, face_reason, kind_of
from suite.api.calendar import events_from_task

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
