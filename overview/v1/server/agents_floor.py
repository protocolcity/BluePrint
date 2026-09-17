"""pc-1513: Agents live-floor pulse counts.

Working / Idle / Error are derived from the same badge ``state`` the
roster already publishes. Off, unknown, and not-configured never inflate
Idle. Stale shift is counted separately so a failed run is never softened.
"""
from __future__ import annotations

from typing import Any

BUCKETS = ('working', 'idle', 'error', 'stale', 'quiet')


def empty_agents_floor() -> dict[str, int]:
    return {key: 0 for key in BUCKETS}


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
