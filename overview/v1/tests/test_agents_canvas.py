"""pc-1534: read-only Agents canvas projector — spatial twin of the floor."""
from datetime import datetime, timedelta, timezone
import unittest

from server.agents_canvas import (
    EMPTY_REASON,
    build_agents_canvas,
    empty_agents_canvas,
)
from server.agents_floor import floor_bucket

NOW = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)


def _agent(identity, group, state, **extra):
    row = {
        'id': identity,
        'name': extra.pop('name', identity),
        'group': group,
        'state': state,
        'badge': extra.pop('badge', state.replace('_', ' ').upper()),
    }
    row.update(extra)
    return row


class AgentsCanvasTests(unittest.TestCase):
    def test_empty_roster_is_honest(self):
        empty = empty_agents_canvas()
        self.assertTrue(empty['empty'])
        self.assertEqual(empty['nodes'], [])
        self.assertEqual(empty['edges'], [])
        self.assertEqual(empty['empty_reason'], EMPTY_REASON)
        self.assertEqual(build_agents_canvas([]), empty)
        self.assertEqual(build_agents_canvas(None), empty)
        self.assertEqual(build_agents_canvas([{'group': 'seat', 'state': 'idle'}]), empty)

    def test_nodes_reuse_floor_buckets_and_exclude_supervisor(self):
        canvas = build_agents_canvas([
            _agent('working-seat', 'seat', 'working'),
            _agent('idle-seat', 'seat', 'idle'),
            _agent('failed-seat', 'seat', 'last_run_failed'),
            _agent('off-seat', 'seat', 'off'),
            _agent('loop-health', 'job', 'idle'),
            _agent('bp-supervisor', 'supervisor', 'idle'),
        ], now=NOW)
        actors = [node for node in canvas['nodes'] if node['kind'] in ('seat', 'job')]
        by_id = {node['id']: node for node in actors}
        self.assertFalse(canvas['empty'])
        self.assertEqual(set(by_id), {'working-seat', 'idle-seat', 'failed-seat', 'off-seat', 'loop-health'})
        self.assertEqual(by_id['working-seat']['bucket'], 'working')
        self.assertEqual(by_id['idle-seat']['bucket'], 'idle')
        self.assertEqual(by_id['failed-seat']['bucket'], 'error')
        self.assertEqual(by_id['off-seat']['bucket'], 'quiet')
        self.assertEqual(by_id['loop-health']['kind'], 'job')
        self.assertEqual(by_id['working-seat']['door'], 'person')
        self.assertEqual(by_id['working-seat']['work_href'], '/work?assignment=worker%3Aworking-seat')
        self.assertNotIn('work_href', by_id['loop-health'])
        for node in actors:
            self.assertEqual(node['bucket'], floor_bucket({'state': {
                'working-seat': 'working',
                'idle-seat': 'idle',
                'failed-seat': 'last_run_failed',
                'off-seat': 'off',
                'loop-health': 'idle',
            }[node['id']]}))

    def test_claim_edge_is_seat_to_held_work_only(self):
        canvas = build_agents_canvas([
            _agent('working-seat', 'seat', 'working', held={
                'id': 'pc-9', 'project': 'blueprint', 'title': 'Live claim',
            }),
            _agent('idle-seat', 'seat', 'idle'),
            _agent('loop-health', 'job', 'idle', held={
                'id': 'pc-1', 'project': 'blueprint', 'title': 'Jobs never claim',
            }),
        ], now=NOW)
        edges = canvas['edges']
        self.assertEqual(edges, [{'from': 'working-seat', 'to': 'work:blueprint:pc-9', 'kind': 'claim'}])
        work = next(node for node in canvas['nodes'] if node['kind'] == 'work')
        self.assertEqual(work['door'], 'ticket')
        self.assertEqual(work['href'], '/work-order?project=blueprint&id=pc-9')
        self.assertIn('pc-9', work['label'])
        self.assertEqual(work['bucket'], 'target')

    def test_claimed_wo_is_visible_directly_on_the_seat_node(self):
        canvas = build_agents_canvas([
            _agent('working-seat', 'seat', 'working', held={
                'id': 'pc-9', 'project': 'blueprint', 'title': 'Live claim',
            }),
            _agent('idle-seat', 'seat', 'idle'),
            _agent('loop-health', 'job', 'idle', held={
                'id': 'pc-1', 'project': 'blueprint', 'title': 'Jobs never claim',
            }),
        ], now=NOW)
        by_id = {node['id']: node for node in canvas['nodes'] if node['kind'] in ('seat', 'job')}
        self.assertEqual(by_id['working-seat']['claim'], {
            'label': 'Live claim · pc-9',
            'href': '/work-order?project=blueprint&id=pc-9',
        })
        self.assertNotIn('claim', by_id['idle-seat'])
        self.assertNotIn('claim', by_id['loop-health'])

    def test_next_fire_ticks_are_future_only(self):
        later = (NOW + timedelta(minutes=12)).isoformat()
        past = (NOW - timedelta(minutes=3)).isoformat()
        canvas = build_agents_canvas([
            _agent('loop-health', 'job', 'idle', next_fire=later),
            _agent('spent', 'job', 'idle', next_fire=past),
            _agent('manual', 'seat', 'idle', next_fire=''),
        ], now=NOW)
        fires = [node for node in canvas['nodes'] if node['kind'] == 'fire']
        self.assertEqual(len(fires), 1)
        self.assertEqual(fires[0]['id'], 'fire:loop-health')
        self.assertEqual(fires[0]['href'], '/calendar')
        self.assertEqual(fires[0]['door'], 'calendar')
        self.assertIn('Next fire', fires[0]['label'])
        self.assertEqual(canvas['edges'], [{
            'from': 'loop-health', 'to': 'fire:loop-health', 'kind': 'next_fire',
        }])

    def test_seat_can_carry_claim_and_next_fire(self):
        later = (NOW + timedelta(hours=1)).isoformat()
        canvas = build_agents_canvas([
            _agent('lane', 'seat', 'working', held={
                'id': 'pc-2', 'project': 'blueprint', 'title': 'Held',
            }, next_fire=later),
        ], now=NOW)
        kinds = sorted(edge['kind'] for edge in canvas['edges'])
        self.assertEqual(kinds, ['claim', 'next_fire'])
        self.assertEqual({node['kind'] for node in canvas['nodes']}, {'seat', 'work', 'fire'})

    def test_last_run_targets_seats_with_a_timeline_door(self):
        canvas = build_agents_canvas([
            _agent('failed-seat', 'seat', 'last_run_failed', last_run={
                'outcome': 'error', 'reason': 'agent exit rc 1', 'at': '2026-09-17T02:00:00Z',
            }),
            _agent('ok-seat', 'seat', 'idle', last_run={
                'outcome': 'stop', 'reason': 'single-pass complete', 'at': '2026-09-17T02:00:00Z',
            }),
            _agent('skip-seat', 'seat', 'idle', last_run={'outcome': 'skip', 'at': '2026-09-17T02:00:00Z'}),
            _agent('quiet-seat', 'seat', 'idle'),
        ], now=NOW)
        by_id = {node['id']: node for node in canvas['nodes']}
        failed = by_id['run:failed-seat']
        self.assertEqual(failed['kind'], 'last_run')
        self.assertEqual(failed['door'], 'timeline')
        self.assertEqual(failed['href'], '/timeline?actor=failed-seat')
        self.assertEqual(failed['label'], 'Last run · failed')
        self.assertEqual(failed['bucket'], 'error')
        ok = by_id['run:ok-seat']
        self.assertEqual(ok['label'], 'Last run · ok')
        self.assertEqual(ok['bucket'], 'target')
        self.assertNotIn('run:skip-seat', by_id)
        self.assertNotIn('run:quiet-seat', by_id)
        edges = {(edge['from'], edge['to']): edge['kind'] for edge in canvas['edges']}
        self.assertEqual(edges[('failed-seat', 'run:failed-seat')], 'last_run')
        self.assertEqual(edges[('ok-seat', 'run:ok-seat')], 'last_run')

    def test_last_run_never_shown_on_jobs(self):
        canvas = build_agents_canvas([
            _agent('loop-health', 'job', 'idle', last_run={'outcome': 'error', 'reason': 'x'}),
        ], now=NOW)
        self.assertEqual(canvas['edges'], [])
        self.assertEqual({node['kind'] for node in canvas['nodes']}, {'job'})

    def test_seat_can_carry_claim_last_run_and_next_fire(self):
        later = (NOW + timedelta(hours=1)).isoformat()
        canvas = build_agents_canvas([
            _agent('lane', 'seat', 'working', held={
                'id': 'pc-2', 'project': 'blueprint', 'title': 'Held',
            }, last_run={'outcome': 'error', 'reason': 'agent exit'}, next_fire=later),
        ], now=NOW)
        kinds = sorted(edge['kind'] for edge in canvas['edges'])
        self.assertEqual(kinds, ['claim', 'last_run', 'next_fire'])
        self.assertEqual({node['kind'] for node in canvas['nodes']}, {'seat', 'work', 'last_run', 'fire'})

    def test_layout_places_targets_to_the_right(self):
        later = (NOW + timedelta(minutes=8)).isoformat()
        canvas = build_agents_canvas([
            _agent('seat', 'seat', 'working', held={'id': 'pc-9', 'project': 'blueprint'}),
            _agent('job', 'job', 'idle', next_fire=later),
        ], now=NOW)
        by_id = {node['id']: node for node in canvas['nodes']}
        self.assertLess(by_id['seat']['x'], by_id['work:blueprint:pc-9']['x'])
        self.assertLess(by_id['job']['x'], by_id['fire:job']['x'])
        self.assertGreater(canvas['width'], 0)
        self.assertGreater(canvas['height'], 0)


if __name__ == '__main__':
    unittest.main()
