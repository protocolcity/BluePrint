"""pc-1510: band partition and orthogonal Status × Attention facets."""
import unittest

from server.work_board import (
    apply_facets,
    board_band,
    build_work_flow,
    empty_work_flow,
    flow_stage,
    is_act_now,
    is_my_todo,
    is_seat_backlog,
    load_bucket,
    matches_attention_facet,
    matches_status_facet,
    partition_bands,
    row_face,
    row_status,
    annotate_order,
    seat_hand,
)


def order(**kwargs):
    row = {
        'id': kwargs.get('id', 'pc-1'),
        'project': kwargs.get('project', 'blueprint'),
        'status': 'backlog',
        'kind': 'work',
        'workers': [],
        'assigned_you': False,
        'attention_face': '',
        'gate_type': '',
        'blocked_on': 'clear',
        'ready_for': None,
        'you_host': False,
    }
    row.update(kwargs)
    return row


class BandPartitionTests(unittest.TestCase):
    def test_human_decide_is_act_now(self):
        row = order(attention_face='decide', gate_type='human')
        self.assertTrue(is_act_now(row))
        self.assertFalse(is_my_todo(row))
        self.assertEqual(board_band(row), 'act_now')
        self.assertEqual(row_face(row), 'Decide')

    def test_read_is_act_now_even_without_human_gate(self):
        row = order(attention_face='read', kind='report')
        self.assertTrue(is_act_now(row))
        self.assertEqual(board_band(row), 'act_now')
        self.assertEqual(row_face(row), 'Read')

    def test_you_todo_without_human_gate_is_my_todos(self):
        row = order(kind='todo', workers=['you'], assigned_you=True)
        self.assertTrue(is_my_todo(row))
        self.assertFalse(is_act_now(row))
        self.assertEqual(board_band(row), 'my_todos')
        self.assertEqual(row_face(row), 'Note')

    def test_human_gated_todo_is_act_now_never_my_todos(self):
        row = order(
            kind='todo', workers=['you'], assigned_you=True,
            attention_face='decide', gate_type='human',
        )
        self.assertTrue(is_act_now(row))
        self.assertFalse(is_my_todo(row))
        self.assertNotEqual(board_band(row), 'my_todos')

    def test_no_row_is_in_both_act_now_and_my_todos(self):
        rows = [
            order(id='d', attention_face='decide', gate_type='human', kind='todo', workers=['you'], assigned_you=True),
            order(id='r', attention_face='read', kind='report', workers=['you'], assigned_you=True),
            order(id='t', kind='todo', workers=['you'], assigned_you=True),
            order(id='n', kind='note', workers=['you'], assigned_you=True),
            order(id='m', kind='reminder', workers=['you'], assigned_you=True, attention_face='due'),
            order(id='s', workers=['agent'], ready_for='agent'),
        ]
        bands = partition_bands(rows)
        act_ids = {o['id'] for o in bands['act_now']}
        todo_ids = {o['id'] for o in bands['my_todos']}
        self.assertFalse(act_ids & todo_ids)
        self.assertEqual(act_ids, {'d', 'r'})
        self.assertEqual(todo_ids, {'t', 'n', 'm'})

    def test_ready_seat_work_is_seat_backlog(self):
        row = order(workers=['agent'], ready_for='agent')
        self.assertTrue(is_seat_backlog(row))
        self.assertEqual(board_band(row), 'seat_backlog')
        self.assertEqual(row_status(row), 'Ready')
        self.assertEqual(row_face(row), 'none')

    def test_live_and_review_seat_work_are_seat_backlog(self):
        live = order(status='in_progress', workers=['agent'])
        parked = order(status='in_review', workers=['agent'])
        self.assertEqual(board_band(live), 'seat_backlog')
        self.assertEqual(row_status(live), 'Live')
        self.assertEqual(board_band(parked), 'seat_backlog')
        self.assertEqual(row_status(parked), 'Review')

    def test_deferred_open_work_is_seat_backlog_not_act_now(self):
        row = order(gate_type='deferred', workers=['agent'])
        self.assertEqual(board_band(row), 'seat_backlog')
        self.assertEqual(row_status(row), 'Deferred')
        self.assertFalse(is_act_now(row))

    def test_closed_orders_are_in_no_band(self):
        row = order(status='done', attention_face='decide', gate_type='human')
        self.assertEqual(board_band(row), '')
        self.assertEqual(row_status(row), 'Done')

    def test_host_face_for_you_implementing_work(self):
        row = order(kind='work', workers=['you'], assigned_you=True, you_host=True)
        self.assertEqual(row_face(row), 'Host')
        self.assertEqual(board_band(row), 'seat_backlog')

    def test_stalled_is_watch_from_the_clock_not_a_timer(self):
        live = order(status='in_progress', attention_face='watch', workers=['agent'])
        timer = order(status='backlog', attention_face='watch', gate_type='timer')
        self.assertEqual(row_status(live), 'Stalled')
        self.assertEqual(row_face(live), 'Watch')
        self.assertEqual(row_status(timer), 'Open')
        self.assertEqual(row_face(timer), 'Watch')

    def test_annotate_stamps_all_three_chrome_fields(self):
        row = annotate_order(order(attention_face='decide', gate_type='human'))
        self.assertEqual(row['board_band'], 'act_now')
        self.assertEqual(row['row_face'], 'Decide')
        self.assertEqual(row['row_status'], 'Open')


class OrthogonalFacetTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            order(id='decide', attention_face='decide', gate_type='human', project='blueprint'),
            order(id='read', attention_face='read', kind='report', project='blueprint'),
            order(id='todo', kind='todo', workers=['you'], assigned_you=True, project='blueprint'),
            order(id='ready', workers=['agent'], ready_for='agent', project='blueprint'),
            order(id='live', status='in_progress', workers=['agent'], project='other'),
            order(id='deferred', gate_type='deferred', workers=['agent'], project='other'),
        ]

    def test_attention_act_now_does_not_reset_status(self):
        open_only = apply_facets(self.rows, status='Open', attention='act_now')
        self.assertEqual({o['id'] for o in open_only}, {'decide', 'read'})
        ready_act = apply_facets(self.rows, status='Ready', attention='act_now')
        self.assertEqual(ready_act, [])

    def test_status_ready_does_not_reset_attention(self):
        ready_any = apply_facets(self.rows, status='Ready', attention='any')
        self.assertEqual({o['id'] for o in ready_any}, {'ready'})
        ready_seat = apply_facets(self.rows, status='Ready', attention='seat')
        self.assertEqual({o['id'] for o in ready_seat}, {'ready'})
        ready_todos = apply_facets(self.rows, status='Ready', attention='my_todos')
        self.assertEqual(ready_todos, [])

    def test_facets_compose_with_and(self):
        live_seat = apply_facets(self.rows, status='Live', attention='seat')
        self.assertEqual({o['id'] for o in live_seat}, {'live'})
        live_act = apply_facets(self.rows, status='Live', attention='act_now')
        self.assertEqual(live_act, [])

    def test_project_stays_an_independent_mast_filter(self):
        other = apply_facets(self.rows, project='other', attention='seat')
        self.assertEqual({o['id'] for o in other}, {'live', 'deferred'})
        other_live = apply_facets(self.rows, project='other', status='Live', attention='seat')
        self.assertEqual({o['id'] for o in other_live}, {'live'})

    def test_legacy_status_and_attention_values_still_match(self):
        self.assertTrue(matches_status_facet(order(status='in_progress'), 'in_progress'))
        self.assertTrue(matches_status_facet(order(status='in_progress'), 'Live'))
        self.assertTrue(matches_attention_facet(
            order(attention_face='decide', gate_type='human'), 'decide'))
        self.assertTrue(matches_attention_facet(
            order(kind='todo', workers=['you'], assigned_you=True), 'my_todos'))

    def test_seat_only_excludes_act_now_and_todos(self):
        seat = apply_facets(self.rows, attention='seat')
        self.assertEqual({o['id'] for o in seat}, {'ready', 'live', 'deferred'})


class WorkFlowStripTests(unittest.TestCase):
    """#147: seat-load / flow is additive — bands and facets stay put."""

    def test_unreadable_is_unavailable_not_a_fake_zero_strip(self):
        payload = build_work_flow([order(workers=['pepper'], ready_for='pepper')], readable=False)
        self.assertEqual(payload, empty_work_flow('unavailable'))
        self.assertEqual(payload['seats'], [])
        self.assertEqual(payload['total'], 0)

    def test_empty_orders_are_honest_empty(self):
        payload = build_work_flow([])
        self.assertEqual(payload['state'], 'empty')
        self.assertEqual(payload['flow'], {'Open': 0, 'Ready': 0, 'Live': 0, 'Done': 0})
        self.assertEqual(payload['seats'], [])

    def test_ready_claimed_stalled_per_seat_and_open_ready_live_done_flow(self):
        rows = [
            order(id='open', workers=['lili']),
            order(id='ready', workers=['pepper'], ready_for='pepper'),
            order(id='live', status='in_progress', workers=['pepper']),
            order(id='review', status='in_review', workers=['lili']),
            order(id='stall', status='in_progress', attention_face='watch', workers=['lili']),
            order(id='done', status='done', workers=['pepper']),
            order(id='decide', attention_face='decide', gate_type='human'),
        ]
        payload = build_work_flow(rows, agents=[
            {'id': 'pepper', 'name': 'pepper', 'group': 'seat'},
            {'id': 'lili', 'name': 'lili', 'group': 'seat'},
        ])
        self.assertEqual(payload['state'], 'healthy')
        self.assertEqual(payload['flow'], {'Open': 2, 'Ready': 1, 'Live': 3, 'Done': 1})
        self.assertEqual(payload['total'], 7)
        by_id = {seat['id']: seat for seat in payload['seats']}
        self.assertEqual(by_id['pepper'], {
            'id': 'pepper', 'name': 'pepper', 'ready': 1, 'claimed': 1, 'stalled': 0,
        })
        self.assertEqual(by_id['lili'], {
            'id': 'lili', 'name': 'lili', 'ready': 0, 'claimed': 1, 'stalled': 1,
        })
        self.assertEqual([seat['id'] for seat in payload['seats']], ['lili', 'pepper'])

    def test_strip_does_not_move_rows_between_bands(self):
        decide = order(id='d', attention_face='decide', gate_type='human', workers=['pepper'])
        todo = order(id='t', kind='todo', workers=['you'], assigned_you=True)
        ready = order(id='r', workers=['pepper'], ready_for='pepper')
        self.assertEqual(board_band(decide), 'act_now')
        self.assertEqual(board_band(todo), 'my_todos')
        self.assertEqual(board_band(ready), 'seat_backlog')
        build_work_flow([decide, todo, ready])
        self.assertEqual(board_band(decide), 'act_now')
        self.assertEqual(board_band(todo), 'my_todos')
        self.assertEqual(board_band(ready), 'seat_backlog')
        self.assertEqual(row_face(decide), 'Decide')
        self.assertEqual(row_status(ready), 'Ready')
        self.assertTrue(matches_attention_facet(decide, 'act_now'))
        self.assertTrue(matches_status_facet(ready, 'Ready'))

    def test_unassigned_open_is_flow_only_not_a_ghost_seat(self):
        row = order(id='u', workers=[], needs_routing=True)
        self.assertEqual(seat_hand(row), '')
        self.assertEqual(load_bucket(row), '')
        self.assertEqual(flow_stage(row), 'Open')
        payload = build_work_flow([row])
        self.assertEqual(payload['seats'], [])
        self.assertEqual(payload['flow']['Open'], 1)


if __name__ == '__main__':
    unittest.main()
