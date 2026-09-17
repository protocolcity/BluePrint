"""pc-1513: Agents live-floor pulse counts stay truthful."""
import unittest

from server.agents_floor import build_agents_floor, empty_agents_floor, floor_bucket


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


if __name__ == '__main__':
    unittest.main()
