"""Overview last-24h close ticks stay a door, not a dashboard."""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest

from server.throughput import (
    HOURS,
    THROUGHPUT_HREF,
    build_throughput,
    empty_throughput,
    parse_stamp,
    store_close_ticks,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


class ThroughputHelperTests(unittest.TestCase):
    def test_empty_is_zero_hours_and_a_timeline_door(self):
        empty = empty_throughput()
        self.assertEqual(empty['closes'], 0)
        self.assertEqual(empty['hours'], [0] * HOURS)
        self.assertEqual(empty['href'], THROUGHPUT_HREF)
        self.assertEqual(empty['state'], 'empty')

    def test_unreadable_is_unavailable_not_a_fake_zero_spark(self):
        payload = build_throughput([NOW], NOW, readable=False)
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['closes'], 0)
        self.assertEqual(payload['hours'], [0] * HOURS)

    def test_buckets_last_24h_and_drops_older_or_future(self):
        ticks = [
            NOW - timedelta(hours=23, minutes=30),
            NOW - timedelta(minutes=20),
            NOW - timedelta(hours=25),
            NOW + timedelta(minutes=5),
        ]
        payload = build_throughput(ticks, NOW)
        self.assertEqual(payload['closes'], 2)
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['hours'][0], 1)
        self.assertEqual(payload['hours'][-1], 1)
        self.assertEqual(sum(payload['hours']), 2)

    def test_parse_sqlite_and_iso_as_utc(self):
        iso = parse_stamp('2026-09-17T14:00:00Z')
        sqlite = parse_stamp('2026-09-17 14:00:00')
        self.assertEqual(iso, sqlite)
        self.assertEqual(parse_stamp(None), None)
        self.assertEqual(parse_stamp('not a time'), None)


class StoreCloseTickTests(unittest.TestCase):
    def _conn(self, events=True):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, updated_at TEXT)')
        conn.execute('CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT)')
        if events:
            conn.execute(
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT)'
            )
        return conn

    def test_event_and_completed_comment_dedupe_to_one_close(self):
        conn = self._conn()
        at = (NOW - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        conn.execute("INSERT INTO tasks VALUES(1,'pc-1','Ship','done',?)", (at,))
        conn.execute("INSERT INTO task_events VALUES(1,1,'status_change','done','seat',?)", (at,))
        conn.execute("INSERT INTO task_comments VALUES(1,1,'Completed: done','seat',?)", (at,))
        ticks = store_close_ticks(conn, NOW)
        self.assertEqual(len(ticks), 1)

    def test_canceled_and_old_done_do_not_count(self):
        conn = self._conn()
        old = (NOW - timedelta(hours=30)).isoformat()
        recent = (NOW - timedelta(hours=3)).isoformat()
        conn.execute("INSERT INTO tasks VALUES(1,NULL,'Old','done',?)", (old,))
        conn.execute("INSERT INTO tasks VALUES(2,NULL,'Cancel','canceled',?)", (recent,))
        conn.execute("INSERT INTO task_events VALUES(1,1,'status_change','done','you',?)", (old,))
        conn.execute("INSERT INTO task_events VALUES(2,2,'status_change','canceled','you',?)", (recent,))
        conn.execute("INSERT INTO task_comments VALUES(1,2,'Canceled: dropped','you',?)", (recent,))
        self.assertEqual(store_close_ticks(conn, NOW), [])

    def test_done_row_fallback_when_events_table_is_missing(self):
        conn = self._conn(events=False)
        recent = (NOW - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("INSERT INTO tasks VALUES(9,NULL,'Closed','done',?)", (recent,))
        ticks = store_close_ticks(conn, NOW)
        self.assertEqual(len(ticks), 1)

    def test_two_tasks_are_two_closes(self):
        conn = self._conn()
        a = (NOW - timedelta(hours=1)).isoformat()
        b = (NOW - timedelta(hours=6)).isoformat()
        conn.execute("INSERT INTO task_events VALUES(1,1,'status_change','done','a',?)", (a,))
        conn.execute("INSERT INTO task_events VALUES(2,2,'status_change','done','b',?)", (b,))
        self.assertEqual(len(store_close_ticks(conn, NOW)), 2)


if __name__ == '__main__':
    unittest.main()
