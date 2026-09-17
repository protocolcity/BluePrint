"""Work page band partition and orthogonal facets (pc-1510).

Presentation only — never changes stored status, gates, or eligibility.
Keep the client helpers in operations.js aligned with these predicates.
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
