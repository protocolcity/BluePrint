"""Issue #156 — Map node motion paint. Honest empty / quiet / unavailable."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from server.node_motion import (
    LIVE_MOTION,
    WINDOW_HOURS,
    classify_node_motion,
    empty_motion,
    parse_stamp,
)
from server.map_tree import attach_project_state

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


def _project(**overrides):
    row = {
        'id': 'product',
        'folder': 'recipes',
        'name': 'Recipes',
        'state': 'available',
        'open': 4,
        'attention': 1,
        'running': 0,
        'working': 0,
        'last_change': None,
    }
    row.update(overrides)
    return row


class EmptyMotionTests(unittest.TestCase):
    def test_empty_is_not_a_fake_zero_spark(self):
        quiet = empty_motion()
        self.assertEqual(quiet['state'], 'quiet')
        self.assertEqual(quiet['stroke'], 'none')
        self.assertEqual(quiet['motion'], 0)
        self.assertIsNone(quiet['last_at'])
        unavailable = empty_motion('unavailable')
        self.assertEqual(unavailable['state'], 'unavailable')
        self.assertEqual(unavailable['stroke'], 'unavailable')
        self.assertEqual(unavailable['motion'], 0)

    def test_unmatched_folder_stays_quiet(self):
        self.assertEqual(classify_node_motion(None, {'motion': 4}, now=NOW)['stroke'], 'none')
        self.assertEqual(classify_node_motion({}, {'motion': 4}, now=NOW)['stroke'], 'none')


class ClassifyNodeMotionTests(unittest.TestCase):
    def test_unavailable_store_never_paints_live_or_recent(self):
        painted = classify_node_motion(
            _project(state='unavailable', running=2, last_change={'at': NOW.isoformat()}),
            {'motion': 9, 'state': 'healthy'},
            now=NOW,
        )
        self.assertEqual(painted['state'], 'unavailable')
        self.assertEqual(painted['stroke'], 'unavailable')
        self.assertEqual(painted['motion'], 0)

    def test_unreadable_flag_wins_over_available_label(self):
        painted = classify_node_motion(_project(running=1), {'motion': 4}, now=NOW, readable=False)
        self.assertEqual(painted['stroke'], 'unavailable')

    def test_open_pile_without_recent_activity_stays_quiet(self):
        painted = classify_node_motion(
            _project(open=31, attention=4, last_change={'at': (NOW - timedelta(days=4)).isoformat()}),
            {'motion': 0, 'state': 'empty'},
            now=NOW,
        )
        self.assertEqual(painted['state'], 'quiet')
        self.assertEqual(painted['stroke'], 'none')
        self.assertEqual(painted['motion'], 0)

    def test_last_change_within_window_is_recent_not_live(self):
        painted = classify_node_motion(
            _project(last_change={'at': (NOW - timedelta(hours=2)).isoformat()}),
            {'motion': 0, 'state': 'empty'},
            now=NOW,
        )
        self.assertEqual(painted['state'], 'recent')
        self.assertEqual(painted['stroke'], 'recent')

    def test_stale_last_change_is_not_painted(self):
        painted = classify_node_motion(
            _project(last_change={'at': (NOW - timedelta(hours=WINDOW_HOURS + 1)).isoformat()}),
            None,
            now=NOW,
        )
        self.assertEqual(painted['stroke'], 'none')
        self.assertEqual(painted['state'], 'quiet')

    def test_future_last_change_is_not_painted(self):
        painted = classify_node_motion(
            _project(last_change={'at': (NOW + timedelta(hours=1)).isoformat()}),
            None,
            now=NOW,
        )
        self.assertEqual(painted['stroke'], 'none')

    def test_pulse_motion_is_recent_until_live_threshold(self):
        recent = classify_node_motion(_project(), {'motion': 1, 'state': 'healthy'}, now=NOW)
        self.assertEqual(recent['stroke'], 'recent')
        self.assertEqual(recent['motion'], 1)
        live = classify_node_motion(_project(), {'motion': LIVE_MOTION, 'state': 'healthy'}, now=NOW)
        self.assertEqual(live['stroke'], 'live')
        self.assertEqual(live['motion'], LIVE_MOTION)

    def test_running_seat_is_live(self):
        painted = classify_node_motion(_project(running=1), {'motion': 0, 'state': 'empty'}, now=NOW)
        self.assertEqual(painted['stroke'], 'live')
        self.assertEqual(painted['state'], 'live')

    def test_working_alias_counts_as_running(self):
        painted = classify_node_motion(_project(running=0, working=2), None, now=NOW)
        self.assertEqual(painted['stroke'], 'live')

    def test_missing_pulse_is_not_unavailable(self):
        painted = classify_node_motion(
            _project(last_change={'at': (NOW - timedelta(hours=1)).isoformat()}),
            None,
            now=NOW,
        )
        self.assertEqual(painted['stroke'], 'recent')

    def test_unavailable_pulse_does_not_invent_ticks(self):
        painted = classify_node_motion(
            _project(),
            {'motion': 8, 'state': 'unavailable'},
            now=NOW,
        )
        self.assertEqual(painted['stroke'], 'none')
        self.assertEqual(painted['motion'], 0)

    def test_worklane_naive_stamp_is_utc(self):
        stamp = parse_stamp('2026-09-17 14:00:00')
        self.assertEqual(stamp, datetime(2026, 9, 17, 14, 0, tzinfo=timezone.utc))
        painted = classify_node_motion(
            _project(last_change={'at': '2026-09-17 14:00:00'}),
            None,
            now=NOW,
        )
        self.assertEqual(painted['stroke'], 'recent')


class AttachMotionTests(unittest.TestCase):
    def test_matching_folder_gets_motion_unmatched_stays_quiet(self):
        tree = {
            'lots': [
                {'relPath': 'recipes', 'name': 'recipes', 'isDir': True},
                {'relPath': 'notes', 'name': 'notes', 'isDir': True},
            ],
        }
        stamped = attach_project_state(
            tree,
            [_project(running=1)],
            pulses={'product': {'motion': 2, 'state': 'healthy'}},
            now=NOW,
        )
        recipes = next(lot for lot in stamped['lots'] if lot['name'] == 'recipes')
        notes = next(lot for lot in stamped['lots'] if lot['name'] == 'notes')
        self.assertEqual(recipes['motion']['stroke'], 'live')
        self.assertNotIn('motion', notes)
        self.assertNotIn('open', notes)

    def test_unavailable_lot_is_read_only_not_a_zero_glow(self):
        tree = {'lots': [{'relPath': 'career', 'name': 'career', 'isDir': True}]}
        stamped = attach_project_state(tree, [
            _project(folder='career', state='unavailable', running=2, last_change={'at': NOW.isoformat()}),
        ], pulses={'product': {'motion': 4, 'state': 'healthy'}}, now=NOW)
        self.assertEqual(stamped['lots'][0]['storeState'], 'unavailable')
        self.assertEqual(stamped['lots'][0]['motion']['stroke'], 'unavailable')
        self.assertEqual(stamped['lots'][0]['motion']['motion'], 0)


if __name__ == '__main__':
    unittest.main()
