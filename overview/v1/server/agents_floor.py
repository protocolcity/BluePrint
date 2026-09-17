"""pc-1513 live-floor pulse + issue #140 seat throughput / fail-rate sparks.

Working / Idle / Error stay derived from the same badge ``state`` the
roster already publishes. Off, unknown, and not-configured never inflate
Idle. Stale shift is counted separately so a failed run is never softened.

Sparks are last-24h WorkForce ledger terminals (STOP/DONE = a run,
ERROR = a fail). START, SKIP, and CANDIDATE are not runs. Quiet seats
are still bucketed as quiet; they do not invent floor motion.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .throughput import parse_stamp

BUCKETS = ('working', 'idle', 'error', 'stale', 'quiet')
HOURS = 24
WINDOW = timedelta(hours=HOURS)
OK_EVENTS = frozenset({'STOP', 'DONE'})
FAIL_EVENTS = frozenset({'ERROR'})


def empty_agents_floor() -> dict[str, int]:
    return {key: 0 for key in BUCKETS}


def empty_seat_spark(state: str = 'empty') -> dict:
    return {
        'hours': [0] * HOURS,
        'fails': [0] * HOURS,
        'runs': 0,
        'errors': 0,
        'fail_rate': None,
        'state': state,
    }


def floor_bucket(agent: Any) -> str:
    """Map one roster row onto the floor strip.

    ``working`` and ``last_run_failed`` stay exact. ``stale_shift`` is
    attention, not Error. Everything else (off / unknown / not configured)
    is quiet so Idle stays a ready seat or job, not a dead wall.
    """
    if not isinstance(agent, dict):
        return 'quiet'
    state = str(agent.get('state') or '')
    if state == 'working':
        return 'working'
    if state == 'last_run_failed':
        return 'error'
    if state == 'stale_shift':
        return 'stale'
    if state == 'idle':
        return 'idle'
    return 'quiet'


def build_agents_floor(agents: list | None) -> dict[str, int]:
    counts = empty_agents_floor()
    for agent in agents or []:
        counts[floor_bucket(agent)] += 1
    return counts


def tick_from_ledger_parts(parts: Any) -> tuple[datetime, str] | None:
    """One STOP/DONE/ERROR row → ``(stamp, 'ok'|'fail')``, else None."""
    if not isinstance(parts, (list, tuple)) or len(parts) < 2:
        return None
    kind = str(parts[1] or '')
    if kind in OK_EVENTS:
        tone = 'ok'
    elif kind in FAIL_EVENTS:
        tone = 'fail'
    else:
        return None
    stamp = parse_stamp(parts[0])
    if stamp is None:
        return None
    return stamp, tone


def ticks_from_ledger_lines(lines: list | None) -> list[tuple[datetime, str]]:
    """One tick per completed shift. Last terminal in the START block wins.

    DONE and STOP on the same pass are one run, not two. An open START
    without a terminal is in-flight, not throughput. SKIP is not a run.
    """
    ticks: list[tuple[datetime, str]] = []
    current: tuple[datetime, str] | None = None
    for line in lines or []:
        parts = str(line or '').split()
        if len(parts) < 2:
            continue
        if parts[1] == 'START':
            if current is not None:
                ticks.append(current)
            current = None
            continue
        tick = tick_from_ledger_parts(parts[:2])
        if tick is not None:
            current = tick
    if current is not None:
        ticks.append(current)
    return ticks


def build_seat_spark(ticks: list | None, now: datetime, *, readable: bool = True) -> dict:
    """Bucket last-24h terminals. Unavailable is not a fake zero spark."""
    if not readable:
        return empty_seat_spark('unavailable')
    start = now - WINDOW
    hours = [0] * HOURS
    fails = [0] * HOURS
    runs = 0
    errors = 0
    for item in ticks or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        stamp, tone = item[0], item[1]
        if not isinstance(stamp, datetime):
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        else:
            stamp = stamp.astimezone(timezone.utc)
        if stamp < start or stamp > now:
            continue
        index = int((stamp - start).total_seconds() // 3600)
        index = min(HOURS - 1, max(0, index))
        hours[index] += 1
        runs += 1
        if tone == 'fail':
            fails[index] += 1
            errors += 1
    return {
        'hours': hours,
        'fails': fails,
        'runs': runs,
        'errors': errors,
        'fail_rate': (errors / runs) if runs else None,
        'state': 'healthy' if runs else 'empty',
    }


def build_floor_sparks(
    agents: list | None,
    ticks_by_id: dict[str, list | None] | None,
    now: datetime,
) -> dict[str, dict]:
    """Per-roster sparks. Missing identity ticks are empty, not invented."""
    sparks: dict[str, dict] = {}
    by_id = ticks_by_id or {}
    for agent in agents or []:
        if not isinstance(agent, dict):
            continue
        identity = str(agent.get('id') or '')
        if not identity:
            continue
        if identity not in by_id:
            sparks[identity] = empty_seat_spark()
            continue
        ticks = by_id[identity]
        if ticks is None:
            sparks[identity] = empty_seat_spark('unavailable')
        else:
            sparks[identity] = build_seat_spark(ticks, now)
    return sparks
