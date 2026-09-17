"""pc-1512: Calendar doors for Overview Due and Agents next-fire.

Schedule truth stays on Calendar (work_dates + local events + WorkForce
next_fire). Overview and Agents only show a count and a one-liner.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from .attention_view import local_today

DUE_CLOCKS = ('deadline', 'reminder')
DUE_HREF_WORK = '/work?attention=due'
DUE_HREF_CALENDAR = '/calendar'
NONE_FIRE_LINE = 'Next fire · none reported'


def empty_calendar_doors() -> dict:
    return {
        'due_count': 0,
        'due_href': DUE_HREF_CALENDAR,
        'items': [],
        'next_fire': None,
        'next_fire_line': NONE_FIRE_LINE,
    }


def _parse_iso(value: Any) -> datetime | None:
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
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def clock_day(value: Any, all_day: Any, now: datetime) -> date | None:
    """Local calendar day of a work-date clock (pc-1489 / pc-1494)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone().date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    if all_day or (len(raw) == 10 and raw[4] == '-' and raw[7] == '-'):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    stamp = _parse_iso(raw)
    if stamp is None:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return stamp.astimezone().date()


def calendar_due_items(work_dates: list | None, events: list | None, now: datetime) -> list[dict]:
    """Unique arrived Due/Remind clocks from Calendar sources.

    Deadline and reminder clocks that have reached the host's local day
    count. Mentioned dates and holds do not. Local calendar.json rows
    count only when their state is ``due``.
    """
    today = local_today(now)
    items: dict[str, dict] = {}
    for row in work_dates or []:
        if not isinstance(row, dict):
            continue
        kind = str(row.get('kind') or '').strip()
        if kind not in DUE_CLOCKS:
            continue
        day = clock_day(row.get('dtstart'), row.get('all_day'), now)
        if day is None or day > today:
            continue
        product = str(row.get('product') or '').strip()
        task_id = str(row.get('task_id') or '').strip()
        key = f'{product}:{task_id}' if product or task_id else f"date:{row.get('dtstart')}|{row.get('summary')}"
        label = 'due' if kind == 'deadline' else 'remind'
        existing = items.get(key)
        if existing and existing['kind'] == 'due':
            continue
        items[key] = {
            'key': key,
            'kind': label,
            'title': str(row.get('summary') or '').strip() or 'Dated work',
            'at': str(row.get('dtstart') or ''),
            'source': str(row.get('source') or ''),
            'product': product,
            'task_id': task_id,
        }
    for event in events or []:
        if not isinstance(event, dict):
            continue
        if str(event.get('state') or '').strip().lower() != 'due':
            continue
        title = str(event.get('title') or '').strip() or 'Untitled event'
        at = str(event.get('at') or '')
        key = f'event:{title}|{at}'
        items[key] = {
            'key': key,
            'kind': 'due',
            'title': title,
            'at': at,
            'source': str(event.get('source') or 'Local calendar'),
            'product': '',
            'task_id': '',
        }
    return list(items.values())


def calendar_due_count(work_dates: list | None, events: list | None, now: datetime) -> int:
    return len(calendar_due_items(work_dates, events, now))


def calendar_due_href(items: list[dict]) -> str:
    if any(item.get('task_id') for item in items):
        return DUE_HREF_WORK
    return DUE_HREF_CALENDAR


def countdown_words(seconds: float) -> str:
    if seconds <= 0:
        return 'now'
    minutes = max(0, int(seconds // 60))
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days and hours:
        return f'in {days}d {hours}h'
    if days:
        return f'in {days}d'
    if hours and minutes:
        return f'in {hours}h {minutes}m'
    if hours:
        return f'in {hours}h'
    if minutes:
        return f'in {minutes}m'
    return 'in <1m'


def next_schedule_fire(agents: list | None, now: datetime) -> dict | None:
    """Soonest future WorkForce next_fire among roster rows."""
    candidates = []
    for agent in agents or []:
        if not isinstance(agent, dict):
            continue
        at = _parse_iso(agent.get('next_fire'))
        if at is None or at <= now:
            continue
        name = str(agent.get('name') or agent.get('id') or '').strip() or 'Scheduled job'
        candidates.append({
            'name': name,
            'id': str(agent.get('id') or ''),
            'at': at.isoformat(),
            'group': str(agent.get('group') or ''),
            'seconds': (at - now).total_seconds(),
        })
    if not candidates:
        return None
    candidates.sort(key=lambda row: row['seconds'])
    return candidates[0]


def next_fire_line(fire: dict | None) -> str:
    if not fire:
        return NONE_FIRE_LINE
    name = str(fire.get('name') or 'Scheduled job').strip() or 'Scheduled job'
    try:
        seconds = float(fire.get('seconds'))
    except (TypeError, ValueError):
        return f'Next fire · {name}'
    return f'Next fire · {name} {countdown_words(seconds)}'


def build_calendar_doors(
    work_dates: list | None,
    events: list | None,
    agents: list | None,
    now: datetime,
) -> dict:
    items = calendar_due_items(work_dates, events, now)
    fire = next_schedule_fire(agents, now)
    return {
        'due_count': len(items),
        'due_href': calendar_due_href(items),
        'items': items,
        'next_fire': fire,
        'next_fire_line': next_fire_line(fire),
    }
