"""Field subsets for GET /api/operations?surface=overview|work.

The cached snapshot stays the full projection. Work and Overview fetch a
page subset so those polls do not carry Map/Agents/Calendar blobs or
unused order fields. Unknown or empty surface returns the snapshot
unchanged.
"""
from __future__ import annotations

SURFACES = frozenset({'overview', 'work'})

# Recorded 12×100 compact-order budget: 887KB full snapshot.
PAYLOAD_BASELINE_BYTES = 887 * 1024

FORBIDDEN_SURFACE_KEYS = (
    'agents_canvas',
    'agents_floor',
    'work_dates',
    'events',
    'coverage',
    'portfolio',
    'calendar_load',
    'remote',
    'excluded_stores',
    'supervisor',
)

OVERVIEW_TOP_KEYS = (
    'observed_at', 'build', 'workspace', 'orders', 'projects', 'agents',
    'sources', 'truncated', 'order_limit', 'calendar_doors', 'throughput',
    'engines',
)
WORK_TOP_KEYS = (
    'observed_at', 'build', 'workspace', 'orders', 'projects', 'agents',
    'sources', 'truncated', 'order_limit', 'calendar_doors', 'work_flow',
    'engines',
)

OVERVIEW_ORDER_KEYS = (
    'id', 'project', 'project_name', 'title', 'status', 'live_with',
    'attention_face', 'needs_routing',
)
WORK_ORDER_REQUIRED_KEYS = (
    'id', 'project', 'project_name', 'title', 'status', 'status_word',
    'updated_at', 'attention_face', 'gate_type', 'workers', 'needs_routing',
    'kind', 'blocked_on', 'assigned_you', 'owner', 'board_band', 'row_face',
    'row_status',
)
WORK_ORDER_OPTIONAL_KEYS = (
    'gate_until', 'gate_expired', 'gate_note', 'blocked_note', 'persona',
    'you_host', 'live_with', 'parked_by', 'since', 'last_note', 'parent',
    'blockers', 'ready_for', 'face_reason',
)
WORK_ORDER_KEYS = WORK_ORDER_REQUIRED_KEYS + WORK_ORDER_OPTIONAL_KEYS

OVERVIEW_PROJECT_KEYS = ('id', 'name', 'open', 'state')
WORK_PROJECT_KEYS = ('id', 'name', 'state')
OVERVIEW_AGENT_KEYS = ('id', 'name', 'group', 'state')
WORK_AGENT_KEYS = ('id', 'name', 'group')
OVERVIEW_DOOR_KEYS = ('due_count', 'due_href')
WORK_DOOR_ITEM_CAP = 4


def _pick(row, keys):
    if not isinstance(row, dict):
        return {}
    return {key: row[key] for key in keys if key in row}


def _is_empty(value):
    return value is None or value is False or value == '' or value == []


def _work_order(order):
    picked = _pick(order, WORK_ORDER_REQUIRED_KEYS)
    for key in WORK_ORDER_OPTIONAL_KEYS:
        if key in order and not _is_empty(order[key]):
            picked[key] = order[key]
    return picked


def _calendar_doors(snapshot, surface):
    doors = snapshot.get('calendar_doors') or {}
    if surface == 'overview':
        return _pick(doors, OVERVIEW_DOOR_KEYS)
    items = list(doors.get('items') or [])[:WORK_DOOR_ITEM_CAP]
    return {
        'due_count': doors.get('due_count', 0),
        'due_href': doors.get('due_href') or '/calendar',
        'items': items,
    }


def project_operations_surface(snapshot, surface=''):
    """Return a page subset. Never mutates the cached snapshot."""
    name = (surface or '').strip().lower()
    if name not in SURFACES or not isinstance(snapshot, dict):
        return snapshot
    top_keys = OVERVIEW_TOP_KEYS if name == 'overview' else WORK_TOP_KEYS
    projected = {key: snapshot[key] for key in top_keys if key in snapshot}
    if name == 'overview':
        projected['orders'] = [
            _pick(order, OVERVIEW_ORDER_KEYS) for order in snapshot.get('orders') or []
        ]
        projected['projects'] = [
            _pick(row, OVERVIEW_PROJECT_KEYS) for row in snapshot.get('projects') or []
        ]
        projected['agents'] = [
            _pick(row, OVERVIEW_AGENT_KEYS) for row in snapshot.get('agents') or []
        ]
    else:
        projected['orders'] = [_work_order(order) for order in snapshot.get('orders') or []]
        projected['projects'] = [
            _pick(row, WORK_PROJECT_KEYS) for row in snapshot.get('projects') or []
        ]
        projected['agents'] = [
            _pick(row, WORK_AGENT_KEYS) for row in snapshot.get('agents') or []
        ]
    projected['calendar_doors'] = _calendar_doors(snapshot, name)
    return projected
