"""pc-1125 / pc-1181 / pc-1489: Workspace calendar — ICS from gates + dated labels.

One feed for all project stores. Sources of record stay on WorkLane tickets:
  - gate_type=timer + gate_until → timed VEVENT (kind timer, source gate_until);
    a date-only gate_until is all-day VALUE=DATE and holds through that
    local calendar day.
  - label deadline:YYYY-MM-DD → all-day Due (kind deadline, source that label)
  - label reminder:YYYY-MM-DD → all-day Reminder (kind reminder, source that label)
  - gate_type=human + gate_note CALENDAR/~/ISO date → all-day Mentioned date
    (kind mentioned, source gate_note). A narrative date is never Due.
    A deadline: label for the same day wins and the mention is omitted.
Scheduled jobs are optional (include_jobs=False by default — noise control).

No second date store. Titles, comments, and history are not scanned for dates.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# deadline:2026-08-10 (strict ISO date)
_DEADLINE_LAB = re.compile(r"^deadline:(\d{4}-\d{2}-\d{2})$", re.I)
# CALENDAR · ~YYYY-MM-DD or ~YYYY-MM-DD (optional CALENDAR prefix + mid-dot/dash)
_GATE_NOTE_CALENDAR = re.compile(
    r"(?:CALENDAR\s*[·•\u2013\-~]?\s*)?~(\d{4}-\d{2}-\d{2})",
    re.I,
)
# bare ISO date fallback in gate_note
_GATE_NOTE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_WS = re.compile(r"\s+")


def parse_deadline_label(label: Any) -> Optional[date]:
    """Return date if label is deadline:YYYY-MM-DD, else None."""
    s = str(label or "").strip()
    m = _DEADLINE_LAB.match(s)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def parse_gate_note_calendar_date(note: Any) -> Optional[date]:
    """Parse CALENDAR · ~YYYY-MM-DD, ~YYYY-MM-DD, or bare ISO from gate_note.

    Used only for gate_type=human Decide tickets (pc-1181). Prefer the
    tilde/CALENDAR form; fall back to first bare YYYY-MM-DD in the note.
    """
    s = str(note or "").strip()
    if not s:
        return None
    m = _GATE_NOTE_CALENDAR.search(s)
    if not m:
        m = _GATE_NOTE_ISO.search(s)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def gate_until_is_date_only(raw: Any) -> bool:
    """True when gate_until is a calendar day, not a timed instant.

    A date-only hold (YYYY-MM-DD, or a date instance) is all-day and must
    not be serialised as UTC midnight. Timed strings and datetime values
    stay instants even when the clock happens to be 00:00.
    """
    if raw is None:
        return False
    if isinstance(raw, datetime):
        return False
    if isinstance(raw, date):
        return True
    s = str(raw).strip()
    if len(s) != 10:
        return False
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def parse_gate_until(raw: Any) -> Optional[datetime]:
    """Parse gate_until into aware UTC datetime (or None)."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    # Accept trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        # date-only
        try:
            d = date.fromisoformat(s[:10])
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _labels_of(task: Mapping[str, Any]) -> List[str]:
    labs = task.get("labels") or []
    if not isinstance(labs, (list, tuple)):
        return []
    return [str(x) for x in labs if x is not None]


def _task_id(task: Mapping[str, Any]) -> str:
    return str(task.get("id") or task.get("task_id") or "").strip()


def _title(task: Mapping[str, Any]) -> str:
    return _WS.sub(" ", str(task.get("title") or "").strip())


def _one_liner(task: Mapping[str, Any], max_len: int = 200) -> str:
    """Prefer glance field; else first non-empty description line."""
    glance = str(task.get("glance") or "").strip()
    if glance:
        body = _WS.sub(" ", glance)
    else:
        desc = str(task.get("description") or "").replace("\r\n", "\n")
        body = ""
        for line in desc.split("\n"):
            s = line.strip()
            if not s or s.startswith("#"):
                if body:
                    break
                continue
            if s.lower() in ("glance", "where", "done when", "detail"):
                continue
            body = _WS.sub(" ", s)
            break
    if len(body) > max_len:
        cut = body[: max_len - 1].rstrip()
        sp = cut.rfind(" ")
        if sp >= int(max_len * 0.6):
            cut = cut[:sp]
        body = cut.rstrip(".,;:") + "…"
    return body


def ticket_deep_link(base_url: str, task_id: str) -> str:
    """Map dig-in deep link for a work order."""
    base = (base_url or "").rstrip("/")
    tid = (task_id or "").strip()
    if not base or not tid:
        return ""
    return "%s/ticket?id=%s" % (base, tid)


def events_from_task(
    task: Mapping[str, Any],
    *,
    base_url: str = "",
) -> List[Dict[str, Any]]:
    """Extract zero or more calendar events from one open task.

    Each event dict:
      uid, summary, description, url,
      kind: 'timer' | 'deadline' | 'reminder' | 'mentioned',
      source: durable field name that produced the clock,
      dtstart: datetime (timed) or date (all-day),
      all_day: bool,
      task_id, product (optional)
    """
    tid = _task_id(task)
    if not tid:
        return []
    title = _title(task)
    url = ticket_deep_link(base_url, tid)
    line = _one_liner(task)
    product = str(
        task.get("product")
        or task.get("project")
        or task.get("store")
        or ""
    ).strip()

    out: List[Dict[str, Any]] = []

    gt = str(task.get("gate_type") or "").strip().lower()
    if gt == "timer":
        raw_until = task.get("gate_until")
        all_day = gate_until_is_date_only(raw_until)
        if all_day:
            if isinstance(raw_until, date) and not isinstance(raw_until, datetime):
                when = raw_until
            else:
                try:
                    when = date.fromisoformat(str(raw_until).strip()[:10])
                except ValueError:
                    when = None
        else:
            when = parse_gate_until(raw_until)
        if when is not None:
            note = str(task.get("gate_note") or "").strip()
            if note:
                thaw = _WS.sub(" ", note)[:160]
            else:
                thaw = "timer thaws"
            summary = "%s · %s" % (tid, title) if title else tid
            desc_parts = [thaw]
            if line:
                desc_parts.append(line)
            if url:
                desc_parts.append(url)
            out.append(
                {
                    "uid": "%s-timer@blueprint.calendar" % tid,
                    "summary": summary,
                    "description": "\n".join(desc_parts),
                    "url": url,
                    "kind": "timer",
                    "source": "gate_until",
                    "dtstart": when,
                    "all_day": all_day,
                    "task_id": tid,
                    "product": product,
                }
            )

    for lab in _labels_of(task):
        if not lab.startswith('reminder:'):
            continue
        try:
            when = date.fromisoformat(lab[len('reminder:'):])
        except ValueError:
            continue
        out.append({'uid': '%s-reminder-%s@blueprint.calendar' % (tid, when.isoformat()),
                    'summary': '%s · %s' % (tid, title), 'description': 'Calendar reminder; work eligibility is unchanged.',
                    'url': url, 'kind': 'reminder', 'source': 'reminder:%s' % when.isoformat(),
                    'dtstart': when, 'all_day': True,
                    'task_id': tid, 'product': product})

    seen_dates = set()
    for lab in _labels_of(task):
        d = parse_deadline_label(lab)
        if d is None or d in seen_dates:
            continue
        seen_dates.add(d)
        summary = "%s · %s" % (tid, title) if title else tid
        desc_parts = ["deadline %s" % d.isoformat()]
        if line:
            desc_parts.append(line)
        if url:
            desc_parts.append(url)
        out.append(
            {
                "uid": "%s-deadline-%s@blueprint.calendar"
                % (tid, d.isoformat()),
                "summary": summary,
                "description": "\n".join(desc_parts),
                "url": url,
                "kind": "deadline",
                "source": "deadline:%s" % d.isoformat(),
                "dtstart": d,
                "all_day": True,
                "task_id": tid,
                "product": product,
            }
        )

    # pc-1489: a date in a human gate_note is a mentioned date, not Due.
    # deadline: for the same day still wins (seen_dates). Never parse
    # gate_note dates for timer/deferred/other gate types. Titles are
    # not scanned.
    if gt == "human":
        d = parse_gate_note_calendar_date(task.get("gate_note"))
        if d is not None and d not in seen_dates:
            seen_dates.add(d)
            summary = "%s · %s" % (tid, title) if title else tid
            desc_parts = ["mentioned date %s from gate_note; not a deadline" % d.isoformat()]
            note = str(task.get("gate_note") or "").strip()
            if note:
                desc_parts.append(_WS.sub(" ", note)[:160])
            if line:
                desc_parts.append(line)
            if url:
                desc_parts.append(url)
            out.append(
                {
                    # Kind and CATEGORIES are mentioned; the UID stays on the
                    # pre-pc-1489 deadline form so existing ICS subscribers
                    # update the same VEVENT instead of seeing a duplicate.
                    "uid": "%s-deadline-%s@blueprint.calendar"
                    % (tid, d.isoformat()),
                    "summary": summary,
                    "description": "\n".join(desc_parts),
                    "url": url,
                    "kind": "mentioned",
                    "source": "gate_note",
                    "dtstart": d,
                    "all_day": True,
                    "task_id": tid,
                    "product": product,
                }
            )

    return out


def collect_events(
    tasks: Iterable[Mapping[str, Any]],
    *,
    base_url: str = "",
) -> List[Dict[str, Any]]:
    """All events from a task list; stable sort by start then uid."""
    events: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, Mapping):
            continue
        events.extend(events_from_task(t, base_url=base_url))

    def _sort_key(ev: Mapping[str, Any]) -> Tuple:
        start = ev.get("dtstart")
        if isinstance(start, datetime):
            return (0, start.isoformat(), str(ev.get("uid") or ""))
        if isinstance(start, date):
            return (0, start.isoformat(), str(ev.get("uid") or ""))
        return (1, "", str(ev.get("uid") or ""))

    events.sort(key=_sort_key)
    return events


# --- ICS render -----------------------------------------------------------


def _ics_escape(text: Any) -> str:
    s = str(text or "")
    s = s.replace("\\", "\\\\")
    s = s.replace(";", "\\;")
    s = s.replace(",", "\\,")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "\\n")
    return s


def _fold_line(line: str) -> str:
    """RFC 5545 line folding at 75 octets — never split inside a UTF-8 codepoint.

    pc-1212 folded by byte slicing and backed off continuation bytes; pc-1462
    found it still emitted a lone lead byte when the remaining tail was
    exactly one multi-byte character (the back-off reached 0 and the
    ``max(cut, 1)`` floor forced a mid-character cut), which 500'd
    /calendar.ics for any description ending in "…" or "—". Folding by
    codepoints makes an invalid cut impossible: a character is placed whole
    or moved to the next physical line.
    """
    if len(line.encode("utf-8")) <= 75:
        return line
    physical: List[str] = []
    current: List[str] = []
    used = 0
    limit = 75
    for ch in line:
        size = len(ch.encode("utf-8"))
        if used + size > limit and current:
            physical.append("".join(current))
            current, used, limit = [ch], size, 74  # continuation lines start with one space
        else:
            current.append(ch)
            used += size
    if current:
        physical.append("".join(current))
    return "\r\n ".join(physical)


def _fmt_dt_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _fmt_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def render_vevent(ev: Mapping[str, Any], *, dtstamp: Optional[datetime] = None) -> str:
    """Render one VEVENT block (lines joined with CRLF, no trailing CRLF)."""
    stamp = dtstamp or _now_utc()
    lines = ["BEGIN:VEVENT"]
    lines.append("UID:%s" % _ics_escape(ev.get("uid") or "unknown@blueprint.calendar"))
    lines.append("DTSTAMP:%s" % _fmt_dt_utc(stamp))
    start = ev.get("dtstart")
    if ev.get("all_day") and isinstance(start, date) and not isinstance(start, datetime):
        lines.append("DTSTART;VALUE=DATE:%s" % _fmt_date(start))
        # DTEND exclusive next day
        end = start + timedelta(days=1)
        lines.append("DTEND;VALUE=DATE:%s" % _fmt_date(end))
    elif isinstance(start, datetime):
        lines.append("DTSTART:%s" % _fmt_dt_utc(start))
    elif isinstance(start, date):
        lines.append("DTSTART;VALUE=DATE:%s" % _fmt_date(start))
        end = start + timedelta(days=1)
        lines.append("DTEND;VALUE=DATE:%s" % _fmt_date(end))
    else:
        lines.append("DTSTART:%s" % _fmt_dt_utc(stamp))

    lines.append("SUMMARY:%s" % _ics_escape(ev.get("summary") or ""))
    desc = ev.get("description") or ""
    if desc:
        lines.append("DESCRIPTION:%s" % _ics_escape(desc))
    url = ev.get("url") or ""
    if url:
        lines.append("URL:%s" % _ics_escape(url))
    kind = str(ev.get("kind") or "").strip()
    if kind:
        lines.append("CATEGORIES:%s" % _ics_escape(kind))
    source = str(ev.get("source") or "").strip()
    if source:
        lines.append("X-BLUEPRINT-SOURCE:%s" % _ics_escape(source))
    lines.append("END:VEVENT")
    return "\r\n".join(_fold_line(ln) for ln in lines)


def render_vcalendar(
    events: Sequence[Mapping[str, Any]],
    *,
    cal_name: str = "Workspace",
    prodid: str = "-//BluePrint//Workspace Calendar//EN",
    dtstamp: Optional[datetime] = None,
) -> str:
    """Full VCALENDAR document ending with a single trailing CRLF."""
    stamp = dtstamp or _now_utc()
    head = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:%s" % _ics_escape(prodid),
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:%s" % _ics_escape(cal_name),
        "X-WR-TIMEZONE:UTC",
    ]
    chunks = ["\r\n".join(_fold_line(ln) for ln in head)]
    for ev in events:
        chunks.append(render_vevent(ev, dtstamp=stamp))
    chunks.append("END:VCALENDAR")
    return "\r\n".join(chunks) + "\r\n"


def _event_client_json(ev: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """pc-1217: one event as the client calendar's row — date-keyed, title-first."""
    start = ev.get("dtstart")
    if isinstance(start, datetime):
        d = start.astimezone(timezone.utc)
        date_s = d.strftime("%Y-%m-%d")
        iso_utc: Optional[str] = d.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(start, date):
        date_s = start.isoformat()
        iso_utc = None
    else:
        return None
    summary = str(ev.get("summary") or "")
    tid = str(ev.get("task_id") or "")
    title = summary
    if tid and summary.startswith(tid):
        title = summary[len(tid):].lstrip(" ·-–—")
    return {
        "id": tid,
        "title": title or summary,
        "kind": str(ev.get("kind") or "deadline"),
        "date": date_s,
        "isoUtc": iso_utc,
        # page is in-suite: relative deep link works on any host the founder
        # browses from (127.0.0.1, LAN name, cutover host); ICS keeps absolute
        "url": ("/ticket?id=" + tid) if tid else str(ev.get("url") or ""),
        "product": str(ev.get("product") or ""),
    }


def render_calendar_html(
    events: Sequence[Mapping[str, Any]],
    *,
    ics_href: str = "/calendar.ics",
    title: str = "Workspace calendar",
) -> str:
    """pc-1217 (pc-1214 founder grid ruling): a real calendar — Month / Week /
    Day grids + Agenda list, user-switchable. Same collect_events data embedded
    as JSON; ICS stays the Apple-sync path; board stays the only date store."""
    rows = [r for r in (_event_client_json(ev) for ev in events) if r]
    events_json = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    page = """<!doctype html>
<html lang="en" class="suite-calendar-view suite-has-spine">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/brand/favicon.svg?v=pc-1285" type="image/svg+xml">
<link rel="apple-touch-icon" href="/brand/apple-touch.png?v=pc-1285">
<title>__TITLE__</title>
<link rel="stylesheet" href="/suite.css?v=20260821-pc1298">
<script src="/esc.js?v=20260901-pc1396"></script>
<script src="/suite-nav.js?v=20260819-pc1290"></script>
<style>
  /* pc-1276: fill the stage after the spine — not a 62rem postage stamp. */
  html.suite-calendar-view, html.suite-calendar-view body {
    min-height: 100dvh;
  }
  html.suite-calendar-view body {
    display: flex;
    flex-direction: column;
  }
  html.suite-calendar-view .suite-head {
    flex: 0 0 auto;
    padding: 14px 20px 12px !important;
    box-sizing: border-box;
  }
  html.suite-calendar-view #suite-body {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .cal-wrap {
    max-width: none;
    width: 100%;
    margin: 0;
    padding: 8px 24px 28px;
    box-sizing: border-box;
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .cal-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin: 6px 0 14px; flex: 0 0 auto; }
  #cal-root { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
  .cal-views { display: inline-flex; gap: 4px; }
  .cal-views button, .cal-nav button {
    font: inherit; font-size: var(--type-caption); font-weight: var(--weight-medium);
    letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink);
    background: color-mix(in srgb, var(--card, #fffdf8) 96%, transparent);
    border: 1px solid color-mix(in srgb, var(--ink, #2a241c) 14%, transparent);
    border-radius: 999px; padding: 5px 12px; cursor: pointer; line-height: 1.3;
  }
  .cal-views button:hover, .cal-nav button:hover { border-color: color-mix(in srgb, var(--gold, #c9a227) 55%, transparent); }
  .cal-views button.is-on {
    border-color: color-mix(in srgb, var(--gold, #c9a227) 65%, transparent);
    background: color-mix(in srgb, #ffe08a 32%, var(--card, #fffdf8));
  }
  .cal-nav { display: inline-flex; gap: 4px; align-items: center; }
  .cal-period { font-size: var(--type-body); font-weight: var(--weight-medium); letter-spacing: 0.01em; min-width: 12rem; text-align: center; }
  /* ── grids ── */
  .cal-dow { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); }
  .cal-dow div { font-size: var(--type-caption); letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.5; padding: 4px 8px; }
  .cal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); border-top: 1px solid var(--line-faint, #e6ddcc); border-left: 1px solid var(--line-faint, #e6ddcc); }
  .cal-grid.cal-month {
    flex: 1 1 auto;
    min-height: 0;
    grid-auto-rows: minmax(0, 1fr);
  }
  .cal-cell { min-width: 0; border-right: 1px solid var(--line-faint, #e6ddcc); border-bottom: 1px solid var(--line-faint, #e6ddcc); min-height: 72px; padding: 6px 6px 8px; background: color-mix(in srgb, var(--card, #fffdf8) 55%, transparent); }
  .cal-cell.is-out { opacity: 0.45; background: transparent; }
  .cal-cell.is-weekend { background: color-mix(in srgb, var(--ink, #2a241c) 2%, transparent); }
  .cal-week .cal-cell { min-height: 190px; }
  .cal-daynum { font-size: var(--type-caption); font-variant-numeric: tabular-nums; opacity: 0.6; margin-bottom: 4px; display: inline-block; min-width: 1.6em; }
  .cal-cell.is-today .cal-daynum {
    opacity: 1; color: #7a5806; font-weight: var(--weight-demibold, 600);
    background: color-mix(in srgb, var(--gold, #e9c46a) 30%, var(--card, #fffdf8));
    border-radius: 999px; text-align: center; padding: 1px 4px;
  }
  .cal-ev { display: block; font-size: var(--type-caption); line-height: 1.3; margin: 0 0 3px; padding: 2px 6px; border-radius: 5px; text-decoration: none; color: var(--ink); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
  .cal-ev.is-deadline { background: color-mix(in srgb, var(--gold, #e9c46a) 22%, var(--card, #fffdf8)); border: 1px solid color-mix(in srgb, var(--gold, #c9a227) 40%, transparent); }
  .cal-ev.is-timer { background: transparent; border: 1px dashed color-mix(in srgb, #c9a227 45%, transparent); }
  .cal-ev:hover { border-color: var(--gold, #c9a227); }
  .cal-ev .cal-ev-t { font-variant-numeric: tabular-nums; opacity: 0.65; margin-right: 4px; }
  /* ── day view ── */
  .cal-day-list { border-top: 1px solid var(--line-faint, #e6ddcc); }
  .cal-day-row { display: flex; gap: 12px; align-items: baseline; padding: 10px 6px; border-bottom: 1px solid var(--line-faint, #e6ddcc); }
  .cal-day-when { flex: 0 0 5.5rem; font-size: var(--type-caption); font-variant-numeric: tabular-nums; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; }
  .cal-day-body a { color: var(--ink); text-decoration: none; font-weight: var(--weight-medium); }
  .cal-day-body a:hover { color: #7a5806; }
  .cal-day-meta { display: block; font-size: var(--type-caption); opacity: 0.6; margin-top: 2px; }
  /* ── agenda ── */
  table.cal { width: 100%; border-collapse: collapse; font-size: var(--type-body); }
  table.cal th, table.cal td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line-faint); vertical-align: top; }
  table.cal th { font-size: var(--type-label); letter-spacing: 0.12em; text-transform: uppercase; color: var(--dim); font-weight: var(--weight-medium); }
  table.cal a { color: var(--verd, var(--ink)); text-decoration: none; border-bottom: 1px solid var(--line-faint); }
  table.cal a:hover { color: var(--gold); border-bottom-color: var(--gold); }
  .cal-empty { padding: 26px 8px; font-size: var(--type-body); opacity: 0.55; text-align: center; }
  .cal-foot { margin-top: 14px; flex: 0 0 auto; font-size: var(--type-label); color: var(--dim); line-height: 1.5; }
  .cal-foot code { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 0.9em; }
</style>
</head>
<body>
<aside class="suite-spine" id="suite-spine" aria-label="BluePrint">
  <div class="suite-spine-brand">
    <a class="suite-spine-lockup" href="/" aria-label="BluePrint">
      <img class="suite-spine-mark" src="/brand/mark-cyanotype.svg?v=pc-1288" width="64" height="52" alt="">
      <span class="suite-spine-word">BluePrint</span>
    </a>
  </div>
  <nav aria-label="Lenses">
    <a id="nav-overview" href="/overview" data-spine-lens="overview">Overview</a>
    <a id="nav-map" href="/workspace-map" data-spine-lens="map">Map</a>
    <a id="nav-calendar" href="/calendar" data-spine-lens="calendar">Calendar</a>
    <a id="nav-settings-spine" href="/settings" data-spine-lens="settings">Settings</a>
  </nav>
  <p class="suite-spine-hint"><a href="https://github.com/protocolcity/BluePrint" target="_blank" rel="noopener"><span class="suite-powered-bolt" aria-hidden="true">⚡</span><span class="suite-powered-label">Powered by</span><span class="suite-powered-name">ProtocolCity</span></a></p>
</aside>
<header class="suite-head">
  <div class="suite-mast">
    <div class="suite-title">
      <h1>Calendar</h1>
      <div class="sub">Dates on work orders · all projects</div>
    </div>
  </div>
  <div class="suite-nav-cluster">
    <nav class="suite-doors" aria-label="Calendar tools">
      <a href="__ICS__">ICS feed</a>
    </nav>
  </div>
</header>
<div id="suite-body">
  <div class="cal-wrap">
    <div class="cal-toolbar">
      <div class="cal-views" role="group" aria-label="Calendar view">
        <button type="button" data-view="month">Month</button>
        <button type="button" data-view="week">Week</button>
        <button type="button" data-view="day">Day</button>
        <button type="button" data-view="agenda">Agenda</button>
      </div>
      <span class="cal-period" id="cal-period"></span>
      <div class="cal-nav">
        <button type="button" data-nav="-1" aria-label="Previous">&lsaquo;</button>
        <button type="button" data-nav="0">Today</button>
        <button type="button" data-nav="1" aria-label="Next">&rsaquo;</button>
      </div>
    </div>
    <div id="cal-root"></div>
    <p class="cal-foot">
      Subscribe in Apple Calendar (File &rarr; New Calendar Subscription) with
      <code>__ICS__</code>. Events come from open work orders &mdash;
      <code>deadline:YYYY-MM-DD</code> labels, timer gates, and
      <code>CALENDAR &middot; ~date</code> notes. No second date store.
    </p>
  </div>
</div>
<script id="cal-data" type="application/json">__EVENTS__</script>
<script>
(function () {
  "use strict";
  var EVENTS = [];
  try { EVENTS = JSON.parse(document.getElementById("cal-data").textContent) || []; } catch (e) {}
  var byDate = {};
  EVENTS.forEach(function (ev) { (byDate[ev.date] = byDate[ev.date] || []).push(ev); });
  Object.keys(byDate).forEach(function (k) {
    byDate[k].sort(function (a, b) { return (a.isoUtc || "") < (b.isoUtc || "") ? -1 : 1; });
  });
  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MON = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  var root = document.getElementById("cal-root");
  var periodEl = document.getElementById("cal-period");
  var state = { view: "month", anchor: new Date() };
  try {
    var v = localStorage.getItem("suite.calView");
    if (v && ["month","week","day","agenda"].indexOf(v) >= 0) state.view = v;
  } catch (e) {}
  function ymd(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }
  function sameDay(a, b) { return ymd(a) === ymd(b); }
  function localTime(ev) {
    if (!ev.isoUtc) return "";
    var d = new Date(ev.isoUtc);
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  function evChip(ev, withTime) {
    var a = document.createElement("a");
    a.className = "cal-ev is-" + (ev.kind === "timer" ? "timer" : "deadline");
    if (ev.url) a.href = ev.url;
    a.title = ev.id + " \\u00b7 " + ev.title + (ev.product ? " \\u00b7 " + ev.product : "");
    if (withTime && ev.isoUtc) {
      var t = document.createElement("span");
      t.className = "cal-ev-t";
      t.textContent = localTime(ev);
      a.appendChild(t);
    }
    a.appendChild(document.createTextNode(ev.title));
    return a;
  }
  function cellFor(d, refMonth, today) {
    var cell = document.createElement("div");
    cell.className = "cal-cell";
    if (refMonth != null && d.getMonth() !== refMonth) cell.className += " is-out";
    if (d.getDay() === 0 || d.getDay() === 6) cell.className += " is-weekend";
    if (sameDay(d, today)) cell.className += " is-today";
    var num = document.createElement("span");
    num.className = "cal-daynum";
    num.textContent = d.getDate();
    cell.appendChild(num);
    (byDate[ymd(d)] || []).forEach(function (ev) { cell.appendChild(evChip(ev, true)); });
    return cell;
  }
  function dowHeader() {
    var h = document.createElement("div");
    h.className = "cal-dow";
    DOW.forEach(function (n) { var c = document.createElement("div"); c.textContent = n; h.appendChild(c); });
    return h;
  }
  function renderMonth() {
    var a = state.anchor, today = new Date();
    periodEl.textContent = MON[a.getMonth()] + " " + a.getFullYear();
    var first = new Date(a.getFullYear(), a.getMonth(), 1);
    var start = new Date(first); start.setDate(1 - first.getDay());
    root.appendChild(dowHeader());
    var grid = document.createElement("div");
    grid.className = "cal-grid cal-month";
    for (var i = 0; i < 42; i++) {
      var d = new Date(start); d.setDate(start.getDate() + i);
      grid.appendChild(cellFor(d, a.getMonth(), today));
    }
    root.appendChild(grid);
  }
  function renderWeek() {
    var a = state.anchor, today = new Date();
    var start = new Date(a); start.setDate(a.getDate() - a.getDay());
    var end = new Date(start); end.setDate(start.getDate() + 6);
    periodEl.textContent = MON[start.getMonth()].slice(0, 3) + " " + start.getDate() + " \\u2013 " + MON[end.getMonth()].slice(0, 3) + " " + end.getDate() + ", " + end.getFullYear();
    root.appendChild(dowHeader());
    var grid = document.createElement("div");
    grid.className = "cal-grid cal-week";
    for (var i = 0; i < 7; i++) {
      var d = new Date(start); d.setDate(start.getDate() + i);
      grid.appendChild(cellFor(d, null, today));
    }
    root.appendChild(grid);
  }
  function renderDay() {
    var a = state.anchor;
    periodEl.textContent = DOW[a.getDay()] + " \\u00b7 " + MON[a.getMonth()] + " " + a.getDate() + ", " + a.getFullYear();
    var list = document.createElement("div");
    list.className = "cal-day-list";
    var evs = byDate[ymd(a)] || [];
    if (!evs.length) {
      var p = document.createElement("div");
      p.className = "cal-empty";
      p.textContent = "No dated work orders this day.";
      list.appendChild(p);
    }
    evs.forEach(function (ev) {
      var row = document.createElement("div");
      row.className = "cal-day-row";
      var when = document.createElement("div");
      when.className = "cal-day-when";
      when.textContent = ev.isoUtc ? localTime(ev) : "all day";
      var body = document.createElement("div");
      body.className = "cal-day-body";
      var link = document.createElement("a");
      if (ev.url) link.href = ev.url;
      link.textContent = ev.title;
      var meta = document.createElement("span");
      meta.className = "cal-day-meta";
      meta.textContent = ev.id + " \\u00b7 " + ev.kind + (ev.product ? " \\u00b7 " + ev.product : "");
      body.appendChild(link); body.appendChild(meta);
      row.appendChild(when); row.appendChild(body);
      list.appendChild(row);
    });
    root.appendChild(list);
  }
  function renderAgenda() {
    periodEl.textContent = EVENTS.length ? EVENTS.length + " dated work orders" : "";
    if (!EVENTS.length) {
      var p = document.createElement("div");
      p.className = "cal-empty";
      p.textContent = "No timer gates or deadline: labels on open work orders.";
      root.appendChild(p);
      return;
    }
    var tbl = document.createElement("table");
    tbl.className = "cal";
    tbl.innerHTML = "<thead><tr><th>When</th><th>Kind</th><th>Work order</th></tr></thead>";
    var tb = document.createElement("tbody");
    EVENTS.forEach(function (ev) {
      var tr = document.createElement("tr");
      var td1 = document.createElement("td");
      td1.textContent = ev.date + (ev.isoUtc ? " " + localTime(ev) : " (all day)");
      var td2 = document.createElement("td");
      td2.textContent = ev.kind;
      var td3 = document.createElement("td");
      var a = document.createElement("a");
      if (ev.url) a.href = ev.url;
      a.textContent = ev.id + " \\u00b7 " + ev.title;
      td3.appendChild(a);
      tr.appendChild(td1); tr.appendChild(td2); tr.appendChild(td3);
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
    root.appendChild(tbl);
  }
  function render() {
    root.innerHTML = "";
    document.querySelectorAll(".cal-views button").forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-view") === state.view);
    });
    document.querySelector(".cal-nav").style.visibility = state.view === "agenda" ? "hidden" : "visible";
    if (state.view === "month") renderMonth();
    else if (state.view === "week") renderWeek();
    else if (state.view === "day") renderDay();
    else renderAgenda();
    try { localStorage.setItem("suite.calView", state.view); } catch (e) {}
  }
  document.querySelector(".cal-views").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-view]");
    if (!b) return;
    state.view = b.getAttribute("data-view");
    render();
  });
  document.querySelector(".cal-nav").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-nav]");
    if (!b) return;
    var step = parseInt(b.getAttribute("data-nav"), 10);
    if (step === 0) state.anchor = new Date();
    else if (state.view === "month") state.anchor.setMonth(state.anchor.getMonth() + step);
    else if (state.view === "week") state.anchor.setDate(state.anchor.getDate() + 7 * step);
    else state.anchor.setDate(state.anchor.getDate() + step);
    render();
  });
  render();
})();
if (window.SuiteNav) {
  SuiteNav.apply({ room: "calendar", onCalendar: true });
}
</script>
</body>
</html>
"""
    return (
        page.replace("__TITLE__", _html_esc(title))
        .replace("__ICS__", _html_esc(ics_href))
        .replace("__EVENTS__", events_json)
    )


def _html_esc(s: str) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
