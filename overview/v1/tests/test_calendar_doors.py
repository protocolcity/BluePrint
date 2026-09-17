"""pc-1512: Calendar Due count and Agents next-fire helpers."""
from datetime import datetime, timedelta, timezone
import unittest

from server.calendar_doors import (
    DUE_HREF_CALENDAR,
    DUE_HREF_WORK,
    NONE_FIRE_LINE,
    build_calendar_doors,
    calendar_due_count,
    calendar_due_href,
    calendar_due_items,
    countdown_words,
    next_fire_line,
    next_schedule_fire,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


class CalendarDueCountTests(unittest.TestCase):
    def test_deadline_today_or_past_counts_once_per_order(self):
        dates = [
            {'kind': 'deadline', 'product': 'blueprint', 'task_id': 'pc-1',
             'summary': 'Ship', 'dtstart': '2026-09-17', 'all_day': True,
             'source': 'deadline:2026-09-17'},
            {'kind': 'reminder', 'product': 'blueprint', 'task_id': 'pc-1',
             'summary': 'Ship', 'dtstart': '2026-09-16', 'all_day': True,
             'source': 'reminder:2026-09-16'},
        ]
        items = calendar_due_items(dates, [], NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['kind'], 'due')
        self.assertEqual(calendar_due_href(items), DUE_HREF_WORK)

    def test_future_deadline_and_mentioned_hold_do_not_count(self):
        dates = [
            {'kind': 'deadline', 'product': 'a', 'task_id': 'pc-2',
             'dtstart': '2026-09-20', 'all_day': True, 'summary': 'Later'},
            {'kind': 'mentioned', 'product': 'a', 'task_id': 'pc-3',
             'dtstart': '2026-09-17', 'all_day': True, 'summary': 'Note'},
            {'kind': 'timer', 'product': 'a', 'task_id': 'pc-4',
             'dtstart': '2026-09-17T12:00:00+00:00', 'all_day': False, 'summary': 'Hold'},
        ]
        self.assertEqual(calendar_due_count(dates, [], NOW), 0)

    def test_arrived_reminder_counts_as_remind_without_a_deadline(self):
        dates = [{'kind': 'reminder', 'product': 'home', 'task_id': 'pc-9',
                  'dtstart': '2026-09-01', 'all_day': True,
                  'summary': 'Pay', 'source': 'reminder:2026-09-01'}]
        items = calendar_due_items(dates, [], NOW)
        self.assertEqual([(item['kind'], item['task_id']) for item in items], [('remind', 'pc-9')])

    def test_calendar_json_due_events_count_and_route_to_calendar(self):
        events = [
            {'title': 'Standup', 'at': '2026-09-17T10:00:00Z', 'state': 'due', 'source': 'routine'},
            {'title': 'Done already', 'at': '2026-09-16T10:00:00Z', 'state': 'done', 'source': 'manual'},
            {'title': 'Later', 'at': '2026-09-18T10:00:00Z', 'state': 'scheduled', 'source': 'WO'},
        ]
        items = calendar_due_items([], events, NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Standup')
        self.assertEqual(calendar_due_href(items), DUE_HREF_CALENDAR)

    def test_empty_sources_are_zero(self):
        self.assertEqual(calendar_due_count([], [], NOW), 0)
        self.assertEqual(calendar_due_count(None, None, NOW), 0)


class NextFireTests(unittest.TestCase):
    def test_soonest_future_job_wins(self):
        later = (NOW + timedelta(hours=2)).isoformat()
        sooner = (NOW + timedelta(minutes=12)).isoformat()
        past = (NOW - timedelta(minutes=5)).isoformat()
        fire = next_schedule_fire([
            {'id': 'integrator', 'name': 'integrator', 'group': 'job', 'next_fire': later},
            {'id': 'loop-health', 'name': 'loop-health', 'group': 'job', 'next_fire': sooner},
            {'id': 'spent', 'name': 'spent', 'group': 'job', 'next_fire': past},
            {'id': 'manual', 'name': 'Seat', 'group': 'seat', 'next_fire': None},
        ], NOW)
        self.assertEqual(fire['id'], 'loop-health')
        self.assertEqual(fire['name'], 'loop-health')
        self.assertAlmostEqual(fire['seconds'], 12 * 60, delta=1)
        self.assertEqual(next_fire_line(fire), 'Next fire · loop-health in 12m')

    def test_no_upcoming_fire_is_honest(self):
        self.assertIsNone(next_schedule_fire([
            {'name': 'spent', 'next_fire': (NOW - timedelta(minutes=1)).isoformat()},
            {'name': 'manual', 'next_fire': ''},
        ], NOW))
        self.assertEqual(next_fire_line(None), NONE_FIRE_LINE)

    def test_countdown_words(self):
        self.assertEqual(countdown_words(0), 'now')
        self.assertEqual(countdown_words(30), 'in <1m')
        self.assertEqual(countdown_words(12 * 60), 'in 12m')
        self.assertEqual(countdown_words(2 * 3600 + 5 * 60), 'in 2h 5m')
        self.assertEqual(countdown_words(26 * 3600), 'in 1d 2h')

    def test_build_calendar_doors_shape(self):
        doors = build_calendar_doors(
            [{'kind': 'deadline', 'product': 'p', 'task_id': 'pc-1',
              'dtstart': '2026-09-16', 'all_day': True, 'summary': 'Due'}],
            [],
            [{'name': 'loop-health', 'id': 'loop-health',
              'next_fire': (NOW + timedelta(minutes=8)).isoformat()}],
            NOW,
        )
        self.assertEqual(doors['due_count'], 1)
        self.assertEqual(doors['due_href'], DUE_HREF_WORK)
        self.assertEqual(doors['next_fire']['name'], 'loop-health')
        self.assertEqual(doors['next_fire_line'], 'Next fire · loop-health in 8m')


if __name__ == '__main__':
    unittest.main()
