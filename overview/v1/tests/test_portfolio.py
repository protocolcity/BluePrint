"""Projects portfolio pulse — stacked open/For You, honest empty, Work/Map doors."""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest

from server.portfolio import (
    HOURS,
    attention_href,
    build_hours,
    build_portfolio,
    classify_pulse,
    empty_portfolio,
    empty_project_pulse,
    map_href,
    project_pulse,
    store_motion_ticks,
    work_href,
)
from server.throughput import HOURS as THROUGHPUT_HOURS

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


def _project(**overrides):
    row = {
        'id': 'blueprint',
        'name': 'BluePrint',
        'open': 31,
        'attention': 4,
        'deferred': 9,
        'claimed': 2,
        'running': 1,
        'state': 'available',
    }
    row.update(overrides)
    return row


class PortfolioHelperTests(unittest.TestCase):
    def test_empty_is_not_a_fake_healthy_zero(self):
        empty = empty_portfolio()
        self.assertEqual(empty['state'], 'empty')
        self.assertEqual(empty['peak_open'], 0)
        self.assertEqual(empty['projects'], [])
        self.assertEqual(empty_portfolio('unavailable')['state'], 'unavailable')

    def test_doors_are_work_and_map_not_delivery_or_agents(self):
        self.assertEqual(work_href('blueprint'), '/work?project=blueprint')
        self.assertEqual(attention_href('blueprint'), '/work?project=blueprint&attention=any')
        self.assertEqual(map_href('blueprint'), '/map?project=blueprint')
        pulse = empty_project_pulse('blueprint', 'BluePrint', 'empty')
        self.assertNotIn('delivery', pulse['href'])
        self.assertNotIn('/agents', pulse['href'])
        self.assertNotIn('/delivery', pulse['map_href'])

    def test_classify_hot_blocked_quiet_unavailable(self):
        self.assertEqual(classify_pulse(_project(), readable=True), 'hot')
        self.assertEqual(classify_pulse(_project(attention=0, running=0, claimed=0, open=0, deferred=3)), 'blocked')
        self.assertEqual(
            classify_pulse(_project(attention=0, running=0, claimed=0, open=0, deferred=0), stalled=2),
            'blocked',
        )
        self.assertEqual(
            classify_pulse(_project(attention=0, running=0, claimed=0, deferred=0, open=8)),
            'hot',
        )
        self.assertEqual(
            classify_pulse(_project(attention=0, running=0, claimed=0, deferred=0, open=0)),
            'quiet',
        )
        self.assertEqual(classify_pulse(_project(), readable=False), 'unavailable')
        self.assertEqual(classify_pulse(_project(state='unavailable')), 'unavailable')

    def test_unreadable_is_unavailable_not_a_fake_zero_spark(self):
        hours, motion, state = build_hours([NOW], NOW, readable=False)
        self.assertEqual(state, 'unavailable')
        self.assertEqual(motion, 0)
        self.assertEqual(hours, [0] * HOURS)
        self.assertEqual(HOURS, THROUGHPUT_HOURS)

    def test_buckets_last_24h_and_drops_older_or_future(self):
        ticks = [
            NOW - timedelta(hours=23, minutes=30),
            NOW - timedelta(minutes=20),
            NOW - timedelta(hours=25),
            NOW + timedelta(minutes=5),
        ]
        hours, motion, state = build_hours(ticks, NOW)
        self.assertEqual(motion, 2)
        self.assertEqual(state, 'healthy')
        self.assertEqual(hours[0], 1)
        self.assertEqual(hours[-1], 1)
        self.assertEqual(sum(hours), 2)


class StoreMotionTickTests(unittest.TestCase):
    def _conn(self, events=True):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, updated_at TEXT)')
        if events:
            conn.execute(
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT)'
            )
        return conn

    def test_missing_events_table_is_empty_not_unavailable(self):
        conn = self._conn(events=False)
        self.assertEqual(store_motion_ticks(conn, NOW), [])

    def test_old_and_future_events_do_not_count(self):
        conn = self._conn()
        old = (NOW - timedelta(hours=30)).isoformat()
        future = (NOW + timedelta(minutes=5)).isoformat()
        recent = (NOW - timedelta(hours=2)).isoformat()
        conn.execute("INSERT INTO task_events VALUES(1,1,'created',NULL,'you',?)", (old,))
        conn.execute("INSERT INTO task_events VALUES(2,2,'status_change','backlog','seat',?)", (future,))
        conn.execute("INSERT INTO task_events VALUES(3,3,'status_change','in_progress','seat',?)", (recent,))
        ticks = store_motion_ticks(conn, NOW)
        self.assertEqual(len(ticks), 1)


class BuildPortfolioTests(unittest.TestCase):
    def test_no_workspace_is_unavailable(self):
        payload = build_portfolio([_project()], {'blueprint': [NOW]}, NOW, workspace=False)
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['projects'], [])

    def test_all_unreadable_stores_are_unavailable_not_zero_bars(self):
        payload = build_portfolio(
            [_project(state='unavailable', open=12, attention=3)],
            {'blueprint': [NOW]},
            NOW,
        )
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['projects'][0]['open'], 0)
        self.assertEqual(payload['projects'][0]['pulse'], 'unavailable')
        self.assertEqual(payload['projects'][0]['state'], 'unavailable')

    def test_compare_rows_carry_work_and_map_doors(self):
        payload = build_portfolio([_project()], {'blueprint': [NOW - timedelta(hours=1)]}, NOW)
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['hot'], 1)
        self.assertEqual(payload['peak_open'], 31)
        row = payload['projects'][0]
        self.assertEqual(row['pulse'], 'hot')
        self.assertEqual(row['href'], '/work?project=blueprint')
        self.assertEqual(row['attention_href'], '/work?project=blueprint&attention=any')
        self.assertEqual(row['map_href'], '/map?project=blueprint')
        self.assertEqual(row['motion'], 1)
        self.assertEqual(sum(row['hours']), 1)

    def test_quiet_and_blocked_are_counted_separately(self):
        rows = [
            _project(),
            _project(id='notes', name='Notes', open=0, attention=0, deferred=2, claimed=0, running=0),
            _project(id='tools', name='Tools', open=0, attention=0, deferred=0, claimed=0, running=0),
        ]
        payload = build_portfolio(rows, {}, NOW)
        self.assertEqual(payload['hot'], 1)
        self.assertEqual(payload['blocked'], 1)
        self.assertEqual(payload['quiet'], 1)
        by_id = {row['id']: row['pulse'] for row in payload['projects']}
        self.assertEqual(by_id['blueprint'], 'hot')
        self.assertEqual(by_id['notes'], 'blocked')
        self.assertEqual(by_id['tools'], 'quiet')

    def test_project_pulse_does_not_invent_open_on_unavailable(self):
        pulse = project_pulse(_project(state='unavailable', open=9, attention=2), [NOW], NOW)
        self.assertEqual(pulse['open'], 0)
        self.assertEqual(pulse['attention'], 0)
        self.assertEqual(pulse['hours'], [0] * HOURS)
        self.assertEqual(pulse['state'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
