"""pc-1513 live-floor pulse + issue #140 seat throughput / fail-rate sparks."""
from datetime import datetime, timedelta, timezone
import unittest

from server.agents_floor import (
    HOURS,
    build_agents_floor,
    build_floor_sparks,
    build_seat_spark,
    empty_agents_floor,
    empty_seat_spark,
    floor_bucket,
    tick_from_ledger_parts,
    ticks_from_ledger_lines,
)

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


class AgentsFloorTests(unittest.TestCase):
    def test_empty_is_zero(self):
        self.assertEqual(build_agents_floor([]), empty_agents_floor())
        self.assertEqual(build_agents_floor(None), empty_agents_floor())

    def test_working_idle_error_are_exact_and_off_is_quiet(self):
        floor = build_agents_floor([
            {'id': 'a', 'state': 'working'},
            {'id': 'b', 'state': 'idle'},
            {'id': 'c', 'state': 'last_run_failed'},
            {'id': 'd', 'state': 'off'},
            {'id': 'e', 'state': 'not_configured'},
            {'id': 'f', 'state': 'unknown'},
        ])
        self.assertEqual(floor['working'], 1)
        self.assertEqual(floor['idle'], 1)
        self.assertEqual(floor['error'], 1)
        self.assertEqual(floor['quiet'], 3)
        self.assertEqual(floor['stale'], 0)

    def test_off_never_counts_as_idle(self):
        floor = build_agents_floor([
            {'state': 'off'},
            {'state': 'idle'},
            {'state': 'not_configured'},
        ])
        self.assertEqual(floor['idle'], 1)
        self.assertEqual(floor['quiet'], 2)

    def test_stale_shift_is_not_softened_into_error(self):
        self.assertEqual(floor_bucket({'state': 'stale_shift'}), 'stale')
        floor = build_agents_floor([
            {'state': 'stale_shift'},
            {'state': 'last_run_failed'},
        ])
        self.assertEqual(floor['stale'], 1)
        self.assertEqual(floor['error'], 1)

    def test_jobs_and_seats_share_the_same_buckets(self):
        floor = build_agents_floor([
            {'group': 'seat', 'state': 'working'},
            {'group': 'job', 'state': 'working'},
            {'group': 'job', 'state': 'idle'},
        ])
        self.assertEqual(floor['working'], 2)
        self.assertEqual(floor['idle'], 1)


class AgentsFloorSparkTests(unittest.TestCase):
    def test_empty_spark_is_not_a_fake_zero_chart(self):
        empty = empty_seat_spark()
        self.assertEqual(empty['hours'], [0] * HOURS)
        self.assertEqual(empty['fails'], [0] * HOURS)
        self.assertEqual(empty['runs'], 0)
        self.assertEqual(empty['errors'], 0)
        self.assertIsNone(empty['fail_rate'])
        self.assertEqual(empty['state'], 'empty')

    def test_unreadable_is_unavailable_not_a_fake_zero_spark(self):
        payload = build_seat_spark([(NOW, 'ok')], NOW, readable=False)
        self.assertEqual(payload['state'], 'unavailable')
        self.assertEqual(payload['runs'], 0)
        self.assertEqual(payload['hours'], [0] * HOURS)

    def test_buckets_last_24h_and_drops_older_or_future(self):
        ticks = [
            (NOW - timedelta(hours=23, minutes=30), 'ok'),
            (NOW - timedelta(minutes=20), 'fail'),
            (NOW - timedelta(hours=25), 'ok'),
            (NOW + timedelta(minutes=5), 'fail'),
        ]
        payload = build_seat_spark(ticks, NOW)
        self.assertEqual(payload['runs'], 2)
        self.assertEqual(payload['errors'], 1)
        self.assertEqual(payload['fail_rate'], 0.5)
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['hours'][0], 1)
        self.assertEqual(payload['hours'][-1], 1)
        self.assertEqual(payload['fails'][-1], 1)
        self.assertEqual(sum(payload['hours']), 2)

    def test_done_and_stop_on_the_same_shift_are_one_run(self):
        started = (NOW - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        stopped = (NOW - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        lines = [
            f'{started} START identity=seat kind=lane budget_secs=1500',
            f'{stopped} DONE rc=0',
            f'{stopped} STOP reason="single-pass complete"',
        ]
        ticks = ticks_from_ledger_lines(lines)
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0][1], 'ok')
        self.assertEqual(build_seat_spark(ticks, NOW)['runs'], 1)
        self.assertEqual(build_seat_spark(ticks, NOW)['errors'], 0)

    def test_error_is_a_fail_and_skip_is_not_a_run(self):
        started = (NOW - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
        skipped = (NOW - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        failed = (NOW - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        lines = [
            f'{started} START identity=job kind=job',
            f'{skipped} SKIP reason="nothing ready"',
            f'{failed} START identity=job kind=job',
            f'{failed} ERROR reason="agent exit"',
        ]
        ticks = ticks_from_ledger_lines(lines)
        self.assertEqual([tone for _stamp, tone in ticks], ['fail'])
        payload = build_seat_spark(ticks, NOW)
        self.assertEqual(payload['runs'], 1)
        self.assertEqual(payload['errors'], 1)
        self.assertEqual(payload['fail_rate'], 1.0)

    def test_open_start_is_not_throughput(self):
        started = (NOW - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.assertEqual(ticks_from_ledger_lines([
            f'{started} START identity=seat kind=lane budget_secs=1500',
            f'{started} CANDIDATE ticket=pc-9',
        ]), [])

    def test_tick_from_parts_ignores_start_and_junk(self):
        self.assertIsNone(tick_from_ledger_parts(['2026-09-17T14:00:00Z', 'START']))
        self.assertIsNone(tick_from_ledger_parts(['not-a-time', 'STOP']))
        self.assertIsNone(tick_from_ledger_parts([]))
        stamp, tone = tick_from_ledger_parts(['2026-09-17T14:00:00Z', 'STOP'])
        self.assertEqual(tone, 'ok')

    def test_floor_sparks_do_not_invent_quiet_motion(self):
        agents = [
            {'id': 'live', 'state': 'working'},
            {'id': 'off-seat', 'state': 'off'},
        ]
        ticks = {
            'live': [(NOW - timedelta(hours=1), 'ok')],
            'off-seat': None,
        }
        sparks = build_floor_sparks(agents, ticks, NOW)
        self.assertEqual(sparks['live']['runs'], 1)
        self.assertEqual(sparks['off-seat']['state'], 'unavailable')
        missing = build_floor_sparks(agents, {}, NOW)
        self.assertEqual(missing['off-seat']['state'], 'empty')
        self.assertEqual(missing['live']['state'], 'empty')


if __name__ == '__main__':
    unittest.main()
