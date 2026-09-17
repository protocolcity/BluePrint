"""Overview mini throughput spark — last-24h WorkLane closes.

Door, not dashboard. Counts claim→done / Completed ticks from registered
stores only. Honest empty when nothing closed; unavailable when the desk
could not read a store. Canceled is not a close.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import sqlite3

HOURS = 24
THROUGHPUT_HREF = '/timeline?period=1'
WINDOW = timedelta(hours=HOURS)


def empty_throughput(state: str = 'empty') -> dict:
    return {
        'closes': 0,
        'hours': [0] * HOURS,
        'href': THROUGHPUT_HREF,
        'state': state,
    }


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


def _row_value(row: Any, key: str, index: int):
    if isinstance(row, sqlite3.Row) or hasattr(row, 'keys'):
        try:
            return row[key]
        except (KeyError, IndexError, TypeError):
            pass
    return row[index]


def _consider(ticks: dict[Any, datetime], task_id: Any, raw: Any, start: datetime, now: datetime) -> None:
    if task_id in ticks:
        return
    stamp = parse_stamp(raw)
    if stamp is None or stamp < start or stamp > now:
        return
    ticks[task_id] = stamp


def store_close_ticks(conn: sqlite3.Connection, now: datetime) -> list[datetime]:
    """Unique close instants in the last 24 hours from one WorkLane store.

    Prefer ``task_events`` status_change→done, then ``Completed:`` comments,
    then a done-row ``updated_at`` fallback for stores that lack events.
    One tick per task so an event/comment pair is not two closes.
    """
    start = now - WINDOW
    ticks: dict[Any, datetime] = {}
    try:
        rows = conn.execute(
            """
            SELECT task_id, created_at
              FROM task_events
             WHERE event_type = 'status_change'
               AND lower(coalesce(status, '')) = 'done'
            """
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        _consider(ticks, _row_value(row, 'task_id', 0), _row_value(row, 'created_at', 1), start, now)

    try:
        rows = conn.execute(
            'SELECT task_id, body, created_at FROM task_comments'
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        body = _row_value(row, 'body', 1) or ''
        first = body.strip().splitlines()[0] if str(body).strip() else ''
        if not first.startswith('Completed:'):
            continue
        _consider(ticks, _row_value(row, 'task_id', 0), _row_value(row, 'created_at', 2), start, now)

    try:
        rows = conn.execute(
            "SELECT id, updated_at FROM tasks WHERE lower(coalesce(status, '')) = 'done'"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    for row in rows:
        _consider(ticks, _row_value(row, 'id', 0), _row_value(row, 'updated_at', 1), start, now)

    return list(ticks.values())


def build_throughput(ticks: list[datetime] | None, now: datetime, *, readable: bool = True) -> dict:
    if not readable:
        return empty_throughput('unavailable')
    start = now - WINDOW
    hours = [0] * HOURS
    count = 0
    for stamp in ticks or []:
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
    return {
        'closes': count,
        'hours': hours,
        'href': THROUGHPUT_HREF,
        'state': 'healthy' if count else 'empty',
    }
