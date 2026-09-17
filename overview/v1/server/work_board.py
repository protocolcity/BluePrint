"""Work page band partition and orthogonal facets (pc-1510).

Presentation only — never changes stored status, gates, or eligibility.
Keep the client helpers in operations.js aligned with these predicates.
Seat-load chips (#158) are the Work hero. Flow Open→Ready→Live→Done stays
in the payload for a later peel and does not change band membership.
"""

YOU_KINDS = frozenset({'todo', 'note', 'reminder'})
CLOSED_STATUSES = frozenset({'done', 'canceled', 'cancelled'})
OPEN_STATUSES = frozenset({'backlog', 'in_progress', 'in_review'})
STATUS_WORDS = ('Open', 'Ready', 'Live', 'Review', 'Deferred', 'Stalled', 'Done')
FACE_WORDS = ('Decide', 'Read', 'Watch', 'Note', 'Host', 'none')
ATTENTION_VALUES = ('', 'any', 'act_now', 'my_todos', 'seat', 'decide', 'read', 'watch', 'due')
STATUS_LEGACY = {
    'backlog': 'Open',
    'in_progress': 'Live',
    'in_review': 'Review',
    'done': 'Done',
    'canceled': 'Done',
    'cancelled': 'Done',
}


def is_closed(order):
    return (order.get('status') or '') in CLOSED_STATUSES


def is_you_kind(order):
    return (order.get('kind') or '') in YOU_KINDS


def has_worker_you(order):
    workers = order.get('workers') or []
    return bool(order.get('assigned_you')) or 'you' in workers


def has_seat_worker(order):
    return any(worker != 'you' for worker in (order.get('workers') or []))


def is_act_now(order):
    """Human Decide plus Read. A human-gated todo is Act now, never My todos."""
    if is_closed(order):
        return False
    face = order.get('attention_face') or ''
    gate = order.get('gate_type') or ''
    if face == 'decide' and gate == 'human':
        return True
    if face == 'read':
        return True
    return False


def is_my_todo(order):
    """worker:you + you-kind, no human gate. Never also Act now."""
    if is_closed(order) or is_act_now(order):
        return False
    if (order.get('gate_type') or '') == 'human':
        return False
    return has_worker_you(order) and is_you_kind(order)


def is_seat_backlog(order):
    """Open remainder a seat can drain or already holds — not Act now or My todos."""
    if is_closed(order) or is_act_now(order) or is_my_todo(order):
        return False
    if (order.get('status') or '') not in OPEN_STATUSES:
        return False
    if (order.get('gate_type') or '') == 'human':
        return False
    return True


def board_band(order):
    if is_act_now(order):
        return 'act_now'
    if is_my_todo(order):
        return 'my_todos'
    if is_seat_backlog(order):
        return 'seat_backlog'
    return ''


def row_face(order):
    """Face badge: Decide / Read / Watch / Note / Host / none — never Needs you."""
    face = order.get('attention_face') or ''
    if face == 'decide':
        return 'Decide'
    if face == 'read':
        return 'Read'
    if face == 'watch':
        return 'Watch'
    if face == 'due' or is_you_kind(order):
        return 'Note'
    if order.get('you_host'):
        return 'Host'
    if (order.get('kind') or 'work') == 'work' and has_worker_you(order) and not has_seat_worker(order):
        return 'Host'
    return 'none'


def _watch_is_stalled(order):
    return (order.get('attention_face') or '') == 'watch' and (order.get('gate_type') or '') != 'timer'


def row_status(order):
    """Status badge: Open / Ready / Live / Review / Deferred / Stalled / Done."""
    status = order.get('status') or ''
    if status in CLOSED_STATUSES:
        return 'Done'
    if status == 'in_progress':
        return 'Stalled' if _watch_is_stalled(order) else 'Live'
    if status == 'in_review':
        return 'Stalled' if _watch_is_stalled(order) else 'Review'
    if (order.get('gate_type') or '') == 'deferred':
        return 'Deferred'
    if order.get('ready_for'):
        return 'Ready'
    if _watch_is_stalled(order):
        return 'Stalled'
    return 'Open'


def canonicalize_status_facet(value):
    if not value:
        return ''
    if value in STATUS_WORDS:
        return value
    return STATUS_LEGACY.get(value, value)


def canonicalize_attention_facet(value):
    if value == 'note':
        return 'due'
    if value in ('seat_only', 'seat-only'):
        return 'seat'
    if value in ('my-todos',):
        return 'my_todos'
    if value in ('act-now',):
        return 'act_now'
    return value or ''


def matches_status_facet(order, value):
    value = canonicalize_status_facet(value)
    if not value:
        return True
    return row_status(order) == value


def matches_attention_facet(order, value):
    value = canonicalize_attention_facet(value)
    if not value or value == 'any':
        return True
    if value in ('act_now', 'decide', 'read'):
        if not is_act_now(order):
            return False
        if value == 'decide':
            return (order.get('attention_face') or '') == 'decide'
        if value == 'read':
            return (order.get('attention_face') or '') == 'read'
        return True
    if value == 'my_todos':
        return is_my_todo(order)
    if value == 'seat':
        return is_seat_backlog(order)
    if value in ('watch', 'due'):
        return (order.get('attention_face') or '') == value
    return True


def apply_facets(orders, *, status='', attention='', project=''):
    """AND composition. Setting one facet never clears the other."""
    matched = []
    for order in orders:
        if project and order.get('project') != project:
            continue
        if not matches_status_facet(order, status):
            continue
        if not matches_attention_facet(order, attention):
            continue
        matched.append(order)
    return matched


def partition_bands(orders):
    bands = {'act_now': [], 'my_todos': [], 'seat_backlog': []}
    seen = set()
    for order in orders:
        band = board_band(order)
        if not band:
            continue
        key = (order.get('project'), order.get('id'))
        if key in seen:
            continue
        seen.add(key)
        bands[band].append(order)
    return bands


def annotate_order(order):
    """Stamp list-chrome fields after ready_for is known."""
    order['board_band'] = board_band(order)
    order['row_face'] = row_face(order)
    order['row_status'] = row_status(order)
    return order


FLOW_STAGES = ('Open', 'Ready', 'Live', 'Done')
LOAD_BUCKETS = ('ready', 'claimed', 'stalled')
SEAT_LOAD_LIMIT = 8
SEAT_CHIP_NAMED = 2
SEAT_PREVIEW_SEATS = 3
SEAT_PREVIEW_PER_SEAT = 3
ACT_NOW_VISIBLE_CAP = 8
MY_TODOS_VISIBLE_CAP = 8
BAND_VIRTUAL_WINDOW = 50
SEAT_STATUS_RANK = {
    'Stalled': 0,
    'Ready': 1,
    'Live': 2,
    'Review': 3,
    'Open': 4,
    'Deferred': 5,
}


def seat_hand(order):
    """First factory seat, else You — never invents a hand."""
    for worker in order.get('workers') or []:
        if worker and worker != 'you':
            return worker
    if order.get('live_with'):
        return order['live_with']
    if order.get('parked_by'):
        return order['parked_by']
    if has_worker_you(order):
        return 'you'
    return ''


def load_bucket(order):
    """Ready / claimed / stalled — drain on a hand. Empty if not yet drainable."""
    status = row_status(order)
    if status == 'Ready':
        return 'ready'
    if status in ('Live', 'Review'):
        return 'claimed'
    if status == 'Stalled':
        return 'stalled'
    return ''


def flow_stage(order):
    """open → ready → live → done. Stalled stays on Live (in-flight, stuck)."""
    status = row_status(order)
    if status == 'Done':
        return 'Done'
    if status == 'Ready':
        return 'Ready'
    if status in ('Live', 'Review', 'Stalled'):
        return 'Live'
    if status in ('Open', 'Deferred'):
        return 'Open'
    return ''


def empty_work_flow(state='empty'):
    return {
        'state': state,
        'flow': {stage: 0 for stage in FLOW_STAGES},
        'seats': [],
        'chips': [],
        'total': 0,
    }


def _seat_updated_at(order):
    value = order.get('updated_at') or ''
    return str(value)


def group_seat_backlog(orders):
    """Group drainable seat work by hand. Seats rank stalled, then ready."""
    groups = {}
    for order in orders or []:
        hand = seat_hand(order) or 'unassigned'
        row = groups.setdefault(hand, {
            'id': hand,
            'name': 'You' if hand == 'you' else ('Unassigned' if hand == 'unassigned' else hand),
            'orders': [],
            'ready': 0,
            'stalled': 0,
        })
        row['orders'].append(order)
        status = row_status(order)
        if status == 'Ready':
            row['ready'] += 1
        elif status == 'Stalled':
            row['stalled'] += 1
    for row in groups.values():
        row['orders'].sort(key=_seat_updated_at, reverse=True)
        row['orders'].sort(key=lambda order: SEAT_STATUS_RANK.get(row_status(order), 9))
        row['total'] = len(row['orders'])
    return sorted(
        groups.values(),
        key=lambda item: (-item['stalled'], -item['ready'], str(item['name'])),
    )


def preview_seat_backlog(orders, *, seats=SEAT_PREVIEW_SEATS, per_seat=SEAT_PREVIEW_PER_SEAT):
    """Default Seat backlog paint: first N seats × M rows. Never a flat dump."""
    groups = group_seat_backlog(orders)
    painted = []
    visible = 0
    for group in groups[:seats]:
        rows = group['orders'][:per_seat]
        painted.append({
            'id': group['id'],
            'name': group['name'],
            'orders': rows,
            'total': group['total'],
            'ready': group['ready'],
            'stalled': group['stalled'],
        })
        visible += len(rows)
    return painted, max(0, len(orders or []) - visible)


def seat_load_chips(seats, *, named=SEAT_CHIP_NAMED):
    """Hero chips: named seats + others rollup. Ready vs stalled only."""
    ranked = sorted(
        seats or [],
        key=lambda item: (-item.get('stalled', 0), -item.get('ready', 0), str(item.get('name') or '')),
    )
    chips = []
    for seat in ranked[:named]:
        chips.append({
            'id': seat.get('id'),
            'name': seat.get('name') or seat.get('id'),
            'ready': seat.get('ready', 0),
            'stalled': seat.get('stalled', 0),
            'kind': 'seat',
        })
    rest = ranked[named:]
    if rest:
        chips.append({
            'id': 'others',
            'name': 'others',
            'ready': sum(item.get('ready', 0) for item in rest),
            'stalled': sum(item.get('stalled', 0) for item in rest),
            'kind': 'others',
            'rolled': len(rest),
        })
    return chips


def build_work_flow(orders, *, readable=True, agents=None):
    """Work drain payload. Hero chips are ready vs stalled.

    Flow Open→Ready→Live→Done is held in this object for a later peel and
    is not painted on Work.
    """
    if not readable:
        return empty_work_flow('unavailable')
    flow = {stage: 0 for stage in FLOW_STAGES}
    seats = {}
    names = {'you': 'You'}
    for agent in agents or []:
        if not isinstance(agent, dict):
            continue
        identity = agent.get('id')
        if not identity:
            continue
        if agent.get('group') == 'seat' or identity == 'you':
            names[identity] = agent.get('name') or identity
    for order in orders or []:
        stage = flow_stage(order)
        if stage:
            flow[stage] += 1
        bucket = load_bucket(order)
        hand = seat_hand(order)
        if not bucket or not hand:
            continue
        row = seats.setdefault(hand, {
            'id': hand,
            'name': names.get(hand, hand),
            'ready': 0,
            'claimed': 0,
            'stalled': 0,
        })
        row[bucket] += 1
    seat_list = sorted(
        seats.values(),
        key=lambda item: (-(item['ready'] + item['claimed'] + item['stalled']), str(item['name'])),
    )
    total = sum(flow.values())
    load_total = sum(item['ready'] + item['claimed'] + item['stalled'] for item in seat_list)
    return {
        'state': 'healthy' if (total or load_total) else 'empty',
        'flow': flow,
        'seats': seat_list,
        'chips': seat_load_chips(seat_list),
        'total': total,
    }
