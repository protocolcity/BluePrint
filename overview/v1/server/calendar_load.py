"""Calendar load-by-day bars — schedule truth, not a WO dump.

Issue #153. Counts dated clocks, local events, and WorkForce next_fire
onto a Monday–Sunday week. Mentioned dates and open work orders do not
count. Unavailable is not a fake zero chart.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .attention_view import local_today
from .calendar_doors import clock_day

LOAD_DAYS = 7
SCHEDULE_KINDS = ('deadline', 'reminder', 'timer')
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def empty_calendar_load(state: str = 'empty', origin: str = '') -> dict:
    return {
        'state': state,
        'origin': origin,
        'days': [],
        'total': 0,
    }


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekday_label(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def _week_days(origin: date) -> list[dict]:
    start = week_monday(origin)
    days = []
    for offset in range(LOAD_DAYS):
        day = start + timedelta(days=offset)
        days.append({'day': day.isoformat(), 'label': weekday_label(day), 'count': 0})
    return days


def build_calendar_load(
    work_dates: list | None,
    events: list | None,
    agents: list | None,
    now: datetime,
    *,
    origin: date | None = None,
    project: str = '',
    readable: bool = True,
) -> dict:
    """Bucket schedule clocks onto the week that contains ``origin``.

    ``work_dates`` contribute deadline / reminder / timer clocks only.
    Local calendar rows and WorkForce ``next_fire`` land on their day.
    Mentioned dates and open work-order rows are not load.
    """
    if not readable:
        return empty_calendar_load('unavailable')
    clock = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    start_day = origin or local_today(clock)
    days = _week_days(start_day)
    index = {row['day']: row for row in days}

    for row in work_dates or []:
        if not isinstance(row, dict):
            continue
        if str(row.get('kind') or '').strip() not in SCHEDULE_KINDS:
            continue
        if project and str(row.get('product') or '') != project:
            continue
        day = clock_day(row.get('dtstart'), row.get('all_day'), clock)
        bucket = index.get(day.isoformat()) if day is not None else None
        if bucket is not None:
            bucket['count'] += 1

    for event in events or []:
        if not isinstance(event, dict):
            continue
        day = clock_day(event.get('at'), False, clock)
        bucket = index.get(day.isoformat()) if day is not None else None
        if bucket is not None:
            bucket['count'] += 1

    for agent in agents or []:
        if not isinstance(agent, dict):
            continue
        day = clock_day(agent.get('next_fire'), False, clock)
        bucket = index.get(day.isoformat()) if day is not None else None
        if bucket is not None:
            bucket['count'] += 1

    total = sum(row['count'] for row in days)
    return {
        'state': 'healthy' if total else 'empty',
        'origin': week_monday(start_day).isoformat(),
        'days': days,
        'total': total,
    }
