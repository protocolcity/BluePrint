"""pc-1534/pc-1539/pc-1545/pc-1564 Agents Canvas — live factory window.

Cap 1 (pc-1564) elevates the acquaintance canvas toward an n8n-feel
factory window: seats and jobs keep distinct shapes, state fill, a
claimed-WO badge, and next-fire ticks. Colors reuse ``floor_bucket``.
Thin edges are seat→claimed work, seat→last-run and/or next-fire ticks;
the claim edge pulses so the canvas reads as a live factory of the
floor, not a static org-chart. The claimed work order is also surfaced
directly on the seat node (not only via its edge target). Next-fire
countdown ticks sit on the seat or job when Calendar door data exists.
A seat's most recent terminal ledger row (real completion or failure —
SKIP and quiet seats report nothing) opens a Timeline door filtered to
that seat. This is not an editor: no rewire, no invented roster, no
Overview/Work dump.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from .agents_floor import floor_bucket
from .calendar_doors import _parse_iso, countdown_words

EMPTY_REASON = 'No seats or jobs on this roster.'
NODE_W = 196
NODE_H = 64
NODE_H_RICH = 92
GAP_Y = 18
PAD_X = 24
PAD_Y = 24
COL_ACTOR = PAD_X
COL_TARGET = 286
STACK_GAP = 12


def empty_agents_canvas(reason: str = EMPTY_REASON) -> dict:
    return {
        'nodes': [],
        'edges': [],
        'width': 0,
        'height': 0,
        'empty': True,
        'empty_reason': reason,
    }


def _text(value: Any, fallback: str = '') -> str:
    text = str(value or '').strip()
    return text or fallback


def _work_href(project: str, order_id: str) -> str:
    return '/work-order?' + urlencode({'project': project, 'id': order_id})


def _work_filter_href(identity: str) -> str:
    return '/work?' + urlencode({'assignment': f'worker:{identity}'})


def _timeline_href(identity: str) -> str:
    return '/timeline?' + urlencode({'actor': identity})


LAST_RUN_LABELS = {'error': 'Last run · failed', 'stop': 'Last run · ok', 'done': 'Last run · ok'}


def _held_work(agent: dict) -> dict | None:
    held = agent.get('held')
    if not isinstance(held, dict):
        return None
    order_id = _text(held.get('id'))
    project = _text(held.get('project'))
    if not order_id or not project:
        return None
    title = _text(held.get('title'), order_id)
    return {
        'id': f'work:{project}:{order_id}',
        'kind': 'work',
        'label': f'{title} · {order_id}',
        'title': title,
        'order_id': order_id,
        'project': project,
        'href': _work_href(project, order_id),
        'door': 'ticket',
    }


def _last_run(agent: dict) -> dict | None:
    """A seat's most recent terminal ledger row, real or failed.

    SKIP is neither a real run nor a failure and is left unreported, same
    as a missing ``last_run``: nothing is invented for a quiet seat.
    """
    run = agent.get('last_run')
    if not isinstance(run, dict):
        return None
    outcome = _text(run.get('outcome')).lower()
    label = LAST_RUN_LABELS.get(outcome)
    if label is None:
        return None
    identity = _text(agent.get('id'))
    return {
        'id': f'run:{identity}',
        'kind': 'last_run',
        'label': label,
        'title': _text(run.get('reason'), label),
        'outcome': outcome,
        'href': _timeline_href(identity),
        'door': 'timeline',
    }


def _next_fire(agent: dict, now: datetime) -> dict | None:
    at = _parse_iso(agent.get('next_fire'))
    if at is None or at <= now:
        return None
    identity = _text(agent.get('id'))
    name = _text(agent.get('name') or identity, 'Scheduled job')
    seconds = (at - now).total_seconds()
    return {
        'id': f'fire:{identity}',
        'kind': 'fire',
        'label': f'Next fire · {countdown_words(seconds)}',
        'title': name,
        'href': '/calendar',
        'door': 'calendar',
        'at': at.isoformat(),
        'seconds': seconds,
    }


def _actor_node(agent: dict, x: int, y: int, held: dict | None, fire: dict | None) -> dict:
    identity = _text(agent.get('id'))
    group = _text(agent.get('group'), 'job')
    bucket = floor_bucket(agent)
    kind = group if group in ('seat', 'job') else 'job'
    rich = held is not None or fire is not None or (kind == 'seat' and _text(agent.get('project_name')))
    node = {
        'id': identity,
        'kind': kind,
        'shape': 'rounded' if kind == 'seat' else 'diamond',
        'label': _text(agent.get('name'), identity),
        'project': _text(agent.get('project_name')),
        'badge': _text(agent.get('badge') or agent.get('state'), bucket),
        'bucket': bucket,
        'group': group,
        'x': x,
        'y': y,
        'w': NODE_W,
        'h': NODE_H_RICH if rich else NODE_H,
        'door': 'person' if group == 'seat' else '',
    }
    if group == 'seat':
        node['work_href'] = _work_filter_href(identity)
        if held is not None:
            node['claim'] = {
                'label': f'{held["title"]} · {held["order_id"]}',
                'href': held['href'],
                'order_id': held['order_id'],
            }
    if fire is not None:
        node['fire'] = {
            'label': fire['label'],
            'href': fire['href'],
        }
    return node


def _place_target(node: dict, x: int, y: int) -> dict:
    bucket = 'error' if node.get('outcome') == 'error' else 'target'
    return {**node, 'x': x, 'y': y, 'w': NODE_W, 'h': NODE_H, 'bucket': bucket}


def build_agents_canvas(agents: list | None, now: datetime | None = None) -> dict:
    """Project the live roster as a read-only node/edge scene.

    Supervisor rows are already excluded from ``agents``. Quiet seats stay
    visible and dim; they do not invent claims or next-fire ticks.
    """
    stamp = now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    else:
        stamp = stamp.astimezone(timezone.utc)

    seats: list[dict] = []
    jobs: list[dict] = []
    for agent in agents or []:
        if not isinstance(agent, dict) or not _text(agent.get('id')):
            continue
        group = _text(agent.get('group'))
        if group == 'seat':
            seats.append(agent)
        elif group == 'job':
            jobs.append(agent)

    if not seats and not jobs:
        return empty_agents_canvas()

    nodes: list[dict] = []
    edges: list[dict] = []
    y = PAD_Y
    bands = (('seat', seats), ('job', jobs))
    for index, (_band, rows) in enumerate(bands):
        if index and rows and nodes:
            y += 12
        for agent in rows:
            held = _held_work(agent) if _band == 'seat' else None
            fire = _next_fire(agent, stamp)
            actor = _actor_node(agent, COL_ACTOR, y, held, fire)
            nodes.append(actor)
            targets: list[tuple[str, dict]] = []
            if held is not None:
                targets.append(('claim', held))
            if _band == 'seat':
                run = _last_run(agent)
                if run is not None:
                    targets.append(('last_run', run))
            if fire is not None:
                targets.append(('next_fire', fire))
            target_y = y
            for kind, target in targets:
                placed = _place_target(target, COL_TARGET, target_y)
                nodes.append(placed)
                tone = 'error' if placed.get('bucket') == 'error' else ('working' if kind == 'claim' else kind)
                edges.append({
                    'from': actor['id'],
                    'to': placed['id'],
                    'kind': kind,
                    'tone': tone,
                })
                target_y += NODE_H + STACK_GAP
            row_bottom = target_y - STACK_GAP if targets else y + actor['h']
            y = max(y + actor['h'], row_bottom) + GAP_Y

    width = COL_TARGET + NODE_W + PAD_X
    height = max(y + PAD_Y - GAP_Y, PAD_Y + NODE_H)
    return {
        'nodes': nodes,
        'edges': edges,
        'width': width,
        'height': height,
        'empty': False,
        'empty_reason': '',
    }
