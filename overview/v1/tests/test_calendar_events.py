"""Date-event projection and ICS provenance for pc-1489.

Disposable fixtures only. Does not open live WorkLane stores.
"""
from datetime import date, datetime, timedelta, timezone
import unittest

from suite.api.calendar import events_from_task, render_vevent, render_vcalendar


def _task(**fields):
    base = {'id': 'pc-1', 'title': 'Sample order', 'status': 'backlog', 'labels': [], 'gate_type': '', 'product': 'protocolcity'}
    base.update(fields)
    return base


class EventProvenanceTests(unittest.TestCase):
    def test_deadline_label_is_due_with_source_field(self):
        events = events_from_task(_task(labels=['deadline:2026-09-20']))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'deadline')
        self.assertEqual(events[0]['source'], 'deadline:2026-09-20')
        self.assertTrue(events[0]['all_day'])
        self.assertEqual(events[0]['dtstart'], date(2026, 9, 20))

    def test_reminder_label_is_reminder_not_a_timer(self):
        events = events_from_task(_task(labels=['reminder:2026-12-20']))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'reminder')
        self.assertEqual(events[0]['source'], 'reminder:2026-12-20')
        self.assertTrue(events[0]['all_day'])

    def test_timer_hold_uses_gate_until(self):
        when = datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc)
        events = events_from_task(_task(gate_type='timer', gate_until=when.isoformat(), gate_note='Review capacity'))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'timer')
        self.assertEqual(events[0]['source'], 'gate_until')
        self.assertFalse(events[0]['all_day'])
        self.assertEqual(events[0]['dtstart'], when)

    def test_human_gate_note_iso_date_is_mentioned_not_due(self):
        note = 'Founder ratification of the paper. Gated human per STATES_AND_TERMS D10/D11 (2026-09-13): a decision is You\'s.'
        events = events_from_task(_task(gate_type='human', gate_note=note, title='FOUNDER · Ratify Banking leftover stack'))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['kind'], 'mentioned')
        self.assertEqual(events[0]['source'], 'gate_note')
        self.assertEqual(events[0]['dtstart'], date(2026, 9, 13))
        self.assertIn('not a deadline', events[0]['description'])

    def test_calendar_tilde_in_gate_note_is_mentioned(self):
        events = events_from_task(_task(gate_type='human', gate_note='CALENDAR · ~2026-09-01 — target first week of September'))
        self.assertEqual(events[0]['kind'], 'mentioned')
        self.assertEqual(events[0]['source'], 'gate_note')
        self.assertEqual(events[0]['dtstart'], date(2026, 9, 1))

    def test_deadline_label_wins_over_same_day_gate_note(self):
        events = events_from_task(_task(
            gate_type='human',
            gate_note='CALENDAR · ~2026-09-20 decide the cutover',
            labels=['deadline:2026-09-20'],
        ))
        kinds = [event['kind'] for event in events]
        self.assertEqual(kinds, ['deadline'])
        self.assertEqual(events[0]['source'], 'deadline:2026-09-20')

    def test_title_date_is_not_extracted(self):
        events = events_from_task(_task(title='FOUNDER · Desk brief 2026-08-31', gate_type='', labels=[]))
        self.assertEqual(events, [])

    def test_dual_clocks_emit_separate_events_with_sources(self):
        events = events_from_task(_task(
            gate_type='timer',
            gate_until='2026-09-22T12:00:00+00:00',
            labels=['deadline:2026-09-20', 'reminder:2026-09-21'],
        ))
        by_kind = {event['kind']: event for event in events}
        self.assertEqual(set(by_kind), {'deadline', 'reminder', 'timer'})
        self.assertEqual(by_kind['deadline']['source'], 'deadline:2026-09-20')
        self.assertEqual(by_kind['reminder']['source'], 'reminder:2026-09-21')
        self.assertEqual(by_kind['timer']['source'], 'gate_until')
        self.assertTrue(by_kind['deadline']['all_day'])
        self.assertTrue(by_kind['reminder']['all_day'])
        self.assertFalse(by_kind['timer']['all_day'])


class CalendarExportTests(unittest.TestCase):
    def test_all_day_uses_value_date_not_utc_midnight(self):
        event = {
            'uid': 'pc-1-deadline-2026-09-20@blueprint.calendar',
            'summary': 'pc-1 · Sample',
            'dtstart': date(2026, 9, 20),
            'all_day': True,
            'kind': 'deadline',
            'source': 'deadline:2026-09-20',
        }
        text = render_vevent(event, dtstamp=datetime(2026, 9, 13, tzinfo=timezone.utc))
        self.assertIn('DTSTART;VALUE=DATE:20260920', text)
        self.assertIn('DTEND;VALUE=DATE:20260921', text)
        self.assertNotIn('DTSTART:20260920T000000Z', text)
        self.assertIn('CATEGORIES:deadline', text)
        self.assertIn('X-BLUEPRINT-SOURCE:deadline:2026-09-20', text)

    def test_dst_spring_forward_and_fall_back_stay_utc(self):
        # America/Chicago 2026-03-08 01:30 CST and 03:30 CDT.
        spring = datetime(2026, 3, 8, 1, 30, tzinfo=timezone(timedelta(hours=-6)))
        fall = datetime(2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-5)))
        spring_event = events_from_task(_task(id='pc-spring', gate_type='timer', gate_until=spring.isoformat()))[0]
        fall_event = events_from_task(_task(id='pc-fall', gate_type='timer', gate_until=fall.isoformat()))[0]
        self.assertEqual(spring_event['dtstart'], datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc))
        self.assertEqual(fall_event['dtstart'], datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))
        spring_text = render_vevent(spring_event, dtstamp=datetime(2026, 9, 13, tzinfo=timezone.utc))
        fall_text = render_vevent(fall_event, dtstamp=datetime(2026, 9, 13, tzinfo=timezone.utc))
        self.assertIn('DTSTART:20260308T073000Z', spring_text)
        self.assertIn('DTSTART:20261101T063000Z', fall_text)
        self.assertIn('CATEGORIES:timer', spring_text)
        self.assertIn('X-BLUEPRINT-SOURCE:gate_until', spring_text)

    def test_dual_clock_feed_keeps_distinct_categories(self):
        events = events_from_task(_task(
            gate_type='timer',
            gate_until='2026-09-22T12:00:00+00:00',
            labels=['deadline:2026-09-20', 'reminder:2026-09-21'],
        ))
        feed = render_vcalendar(events, dtstamp=datetime(2026, 9, 13, tzinfo=timezone.utc))
        self.assertIn('CATEGORIES:deadline', feed)
        self.assertIn('CATEGORIES:reminder', feed)
        self.assertIn('CATEGORIES:timer', feed)
        self.assertIn('DTSTART;VALUE=DATE:20260920', feed)
        self.assertIn('DTSTART;VALUE=DATE:20260921', feed)
        self.assertIn('DTSTART:20260922T120000Z', feed)
        self.assertIn('X-BLUEPRINT-SOURCE:deadline:2026-09-20', feed)
        self.assertIn('X-BLUEPRINT-SOURCE:reminder:2026-09-21', feed)
        self.assertIn('X-BLUEPRINT-SOURCE:gate_until', feed)

    def test_mentioned_date_category_is_not_deadline(self):
        events = events_from_task(_task(gate_type='human', gate_note='Decide by 2026-09-13'))
        feed = render_vcalendar(events, dtstamp=datetime(2026, 9, 13, tzinfo=timezone.utc))
        self.assertIn('CATEGORIES:mentioned', feed)
        self.assertNotIn('CATEGORIES:deadline', feed)
        self.assertIn('X-BLUEPRINT-SOURCE:gate_note', feed)


if __name__ == '__main__':
    unittest.main()
