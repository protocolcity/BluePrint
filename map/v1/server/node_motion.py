"""Map node motion paint — stroke = recent place activity.

Issue #156. Quiet nodes stay quiet; unavailable stores are distinct from
an empty motion count. Open / For You piles are not motion. Do not invent
pulses for unmatched folders.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

WINDOW_HOURS = 24
LIVE_MOTION = 3
WINDOW = timedelta(hours=WINDOW_HOURS)


def empty_motion(state: str = 'quiet') -> dict:
    """Honest empty. ``motion: 0`` is not a painted spark."""
    if state == 'unavailable':
        return {'stroke': 'unavailable', 'motion': 0, 'last_at': None, 'state': 'unavailable'}
    return {'stroke': 'none', 'motion': 0, 'last_at': None, 'state': 'quiet'}


def parse_stamp(value: Any) -> datetime | None:
    """UTC instant from ISO or WorkLane ``YYYY-MM-DD HH:MM:SS`` text."""
    if value is None:
        return None
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is None:
            return stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(' ', 'T', 1)
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _int_count(value: Any) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return count if count > 0 else 0


def classify_node_motion(
    project: dict | None,
    pulse: dict | None = None,
    *,
    now: datetime | None = None,
    readable: bool | None = None,
) -> dict:
    """Stroke for one place node from signals Map already has.

    ``pulse`` is the Projects portfolio row (last-24h ``motion`` count) when
    the operations snapshot has already built it. A missing pulse is not
    unavailable — last_change and running still count. An unreadable store
    never paints recent/live, even if a stale pulse still has ticks.
    """
    if not isinstance(project, dict):
        return empty_motion('quiet')
    store_state = project.get('state') or project.get('storeState') or 'unavailable'
    if readable is False or store_state != 'available':
        return empty_motion('unavailable')

    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    else:
        clock = clock.astimezone(timezone.utc)

    running = _int_count(project.get('running') if project.get('running') is not None else project.get('working'))
    last_change = project.get('last_change') if isinstance(project.get('last_change'), dict) else None
    last_at = last_change.get('at') if last_change else None
    last_stamp = parse_stamp(last_at)
    recent_change = bool(last_stamp and clock - WINDOW <= last_stamp <= clock)

    motion_count = 0
    if isinstance(pulse, dict) and pulse.get('state') != 'unavailable':
        motion_count = _int_count(pulse.get('motion'))

    if running > 0 or motion_count >= LIVE_MOTION:
        state = 'live'
        stroke = 'live'
    elif motion_count > 0 or recent_change:
        state = 'recent'
        stroke = 'recent'
    else:
        state = 'quiet'
        stroke = 'none'

    return {
        'stroke': stroke,
        'motion': motion_count,
        'last_at': str(last_at) if last_at else None,
        'state': state,
    }
