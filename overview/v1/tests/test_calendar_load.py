"""Issue #153: Calendar load-by-day bars from schedule clocks only."""
from datetime import date, datetime, timezone
import unittest

from server.calendar_load import (
    LOAD_DAYS,
    WEEKDAYS,
    build_calendar_load,
    empty_calendar_load,
    week_monday,
    weekday_label,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)
ORIGIN = date(2026, 9, 17)


class CalendarLoadTests(unittest.TestCase):
    def test_empty_is_not_a_fake_healthy_zero(self):
        empty = empty_calendar_load()
        self.assertEqual(empty['state'], 'empty')
        self.assertEqual(empty['days'], [])
        self.assertEqual(empty['total'], 0)
        self.assertEqual(empty_calendar_load('unavailable')['state'], 'unavailable')

    def test_week_is_monday_through_sunday(self):
        self.assertEqual(week_monday(ORIGIN).isoformat(), '2026-09-14')
        self.assertEqual(weekday_label(date(2026, 9, 14)), 'Mon')
        self.assertEqual(WEEKDAYS, ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'))
        self.assertEqual(LOAD_DAYS, 7)

    def test_unreadable_is_unavailable_not_a_fake_zero_chart(self):
        payload = build_calendar_load(
            [{'kind': 'deadline', 'dtstart': '2026-09-17', 'all_day': True}],
            [],
            [],
            NOW,
            origin=ORIGIN,
            readable=False,
        )
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['days'], [])
        self.assertEqual(payload['total'], 0)

    def test_quiet_week_is_honest_empty_with_seven_days(self):
        payload = build_calendar_load([], [], [], NOW, origin=ORIGIN)
        self.assertEqual(payload['state'], 'empty')
        self.assertEqual(payload['origin'], '2026-09-14')
        self.assertEqual(payload['total'], 0)
        self.assertEqual([row['label'] for row in payload['days']], list(WEEKDAYS))
        self.assertEqual([row['count'] for row in payload['days']], [0] * 7)

    def test_counts_deadline_reminder_event_and_next_fire(self):
        dates = [
            {'kind': 'deadline', 'product': 'blueprint', 'task_id': 'pc-1',
             'dtstart': '2026-09-16', 'all_day': True},
            {'kind': 'reminder', 'product': 'blueprint', 'task_id': 'pc-1',
             'dtstart': '2026-09-17', 'all_day': True},
            {'kind': 'mentioned', 'product': 'blueprint', 'task_id': 'pc-2',
             'dtstart': '2026-09-16', 'all_day': True},
            {'kind': 'timer', 'product': 'blueprint', 'task_id': 'pc-3',
             'dtstart': '2026-09-18', 'all_day': True},
        ]
        events = [{'title': 'Standup', 'at': '2026-09-18', 'state': 'scheduled'}]
        agents = [{'name': 'loop-health', 'next_fire': '2026-09-18'}]
        payload = build_calendar_load(dates, events, agents, NOW, origin=ORIGIN)
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['total'], 5)
        self.assertEqual([row['count'] for row in payload['days']], [0, 0, 1, 1, 3, 0, 0])

    def test_mentioned_and_open_orders_are_not_load(self):
        dates = [{'kind': 'mentioned', 'dtstart': '2026-09-17', 'all_day': True,
                  'product': 'a', 'task_id': 'pc-9'}]
        payload = build_calendar_load(dates, [], [], NOW, origin=ORIGIN)
        self.assertEqual(payload['state'], 'empty')
        self.assertEqual(payload['total'], 0)

    def test_project_filter_skips_other_stores(self):
        dates = [
            {'kind': 'deadline', 'product': 'shop', 'dtstart': '2026-09-17', 'all_day': True},
            {'kind': 'deadline', 'product': 'blueprint', 'dtstart': '2026-09-17', 'all_day': True},
        ]
        payload = build_calendar_load(dates, [], [], NOW, origin=ORIGIN, project='blueprint')
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['days'][3]['count'], 1)

    def test_outside_week_does_not_count(self):
        dates = [{'kind': 'deadline', 'dtstart': '2026-09-10', 'all_day': True}]
        events = [{'title': 'Later', 'at': '2026-09-22'}]
        payload = build_calendar_load(dates, events, [], NOW, origin=ORIGIN)
        self.assertEqual(payload['total'], 0)
        self.assertEqual(payload['state'], 'empty')


if __name__ == '__main__':
    unittest.main()
