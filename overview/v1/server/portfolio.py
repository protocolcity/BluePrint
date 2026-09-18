"""Projects portfolio pulse — open / For You sparks and compare bars.

Issue #150 / pc-1562 C9. Per-store stacked open/For You plus last-24h motion
glyphs. Unavailable stores never paint a fake zero spark. Doors go to Work
and Map, not ticket bodies, seat-shift detail, or git evidence.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from .throughput import HOURS, WINDOW, parse_stamp


def work_href(project_id: str) -> str:
    return f'/work?project={project_id}' if project_id else '/work'


def attention_href(project_id: str) -> str:
    if not project_id:
        return '/work?attention=any'
    return f'/work?project={project_id}&attention=any'


def map_href(project_id: str) -> str:
    return f'/map?project={project_id}' if project_id else '/map'


def empty_project_pulse(project_id: str = '', name: str = '', state: str = 'empty') -> dict:
    pulse = 'unavailable' if state == 'unavailable' else 'quiet'
    return {
        'id': project_id,
        'name': name or project_id,
        'open': 0,
        'attention': 0,
        'deferred': 0,
        'hours': [0] * HOURS,
        'motion': 0,
        'pulse': pulse,
        'href': work_href(project_id),
        'attention_href': attention_href(project_id),
        'map_href': map_href(project_id),
        'state': state,
    }


def empty_portfolio(state: str = 'empty') -> dict:
    return {
        'state': state,
        'peak_open': 0,
        'hot': 0,
        'quiet': 0,
        'blocked': 0,
        'projects': [],
    }


def classify_pulse(project: Any, *, readable: bool = True, stalled: int = 0) -> str:
    """One dominant label: unavailable, hot, blocked, or quiet."""
    if not readable or (isinstance(project, dict) and project.get('state') != 'available'):
        return 'unavailable'
    if not isinstance(project, dict):
        return 'quiet'
    attention = int(project.get('attention') or 0)
    running = int(project.get('running') or 0)
    claimed = int(project.get('claimed') or 0)
    if attention or running or claimed:
        return 'hot'
    deferred = int(project.get('deferred') or 0)
    if deferred or stalled:
        return 'blocked'
    if int(project.get('open') or 0):
        return 'hot'
    return 'quiet'


def _row_value(row: Any, key: str, index: int):
    if isinstance(row, sqlite3.Row) or hasattr(row, 'keys'):
        try:
            return row[key]
        except (KeyError, IndexError, TypeError):
            pass
    return row[index]


def store_motion_ticks(conn: sqlite3.Connection, now: datetime) -> list[datetime]:
    """Last-24h WorkLane event instants from one store.

    A missing ``task_events`` table is empty evidence, not unavailable.
    Every event type counts as motion; closes already have their own spark
    on Overview.
    """
    start = now - WINDOW
    ticks: list[datetime] = []
    try:
        rows = conn.execute('SELECT created_at FROM task_events').fetchall()
    except sqlite3.OperationalError:
        return []
    for row in rows:
        stamp = parse_stamp(_row_value(row, 'created_at', 0))
        if stamp is None or stamp < start or stamp > now:
            continue
        ticks.append(stamp)
    return ticks


def build_hours(ticks: list | None, now: datetime, *, readable: bool = True) -> tuple[list[int], int, str]:
    if not readable:
        return [0] * HOURS, 0, 'unavailable'
    start = now - WINDOW
    hours = [0] * HOURS
    count = 0
    for stamp in ticks or []:
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
        count += 1
    return hours, count, 'healthy' if count else 'empty'


def project_pulse(
    project: dict,
    ticks: list | None,
    now: datetime,
    *,
    stalled: int = 0,
) -> dict:
    readable = isinstance(project, dict) and project.get('state') == 'available'
    hours, motion, spark_state = build_hours(ticks, now, readable=readable)
    pulse = classify_pulse(project, readable=readable, stalled=stalled)
    open_n = int(project.get('open') or 0) if readable else 0
    attention = int(project.get('attention') or 0) if readable else 0
    deferred = int(project.get('deferred') or 0) if readable else 0
    project_id = str(project.get('id') or '')
    return {
        'id': project_id,
        'name': str(project.get('name') or project_id),
        'open': open_n,
        'attention': attention,
        'deferred': deferred,
        'hours': hours,
        'motion': motion,
        'pulse': pulse,
        'href': work_href(project_id),
        'attention_href': attention_href(project_id),
        'map_href': map_href(project_id),
        'state': spark_state if readable else 'unavailable',
    }


def build_portfolio(
    projects: list | None,
    ticks_by_id: dict[str, list | None] | None,
    now: datetime,
    *,
    stalled_by_id: dict[str, int] | None = None,
    workspace: bool = True,
) -> dict:
    """Workspace compare payload. No workspace is unavailable, not empty."""
    if not workspace:
        return empty_portfolio('unavailable')
    by_id = ticks_by_id or {}
    stalled_map = stalled_by_id or {}
    rows = []
    for project in projects or []:
        if not isinstance(project, dict):
            continue
        project_id = str(project.get('id') or '')
        if not project_id:
            continue
        ticks = by_id.get(project_id)
        if ticks is None:
            ticks = []
        rows.append(project_pulse(project, ticks, now, stalled=int(stalled_map.get(project_id) or 0)))
    if not rows:
        return empty_portfolio('empty')
    readable = [row for row in rows if row['state'] != 'unavailable']
    if not readable:
        payload = empty_portfolio('unavailable')
        payload['projects'] = rows
        payload['blocked'] = sum(1 for row in rows if row['pulse'] == 'blocked')
        return payload
    peak = max((row['open'] for row in readable), default=0)
    counts = {'hot': 0, 'quiet': 0, 'blocked': 0}
    for row in rows:
        if row['pulse'] in counts:
            counts[row['pulse']] += 1
    live = any(row['open'] or row['attention'] or row['motion'] for row in readable)
    return {
        'state': 'healthy' if live else 'empty',
        'peak_open': peak,
        'hot': counts['hot'],
        'quiet': counts['quiet'],
        'blocked': counts['blocked'],
        'projects': rows,
    }
