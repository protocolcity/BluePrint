# Calendar + Settings IA — Four-lens extend

**Status:** DRAFT · Product design (Designer) · Brand fence glance welcome · Builder lands peels against this paper  
**Parent:** Overview Mission Control INTENT / `OVERVIEW_MC_EXT.md` · four-lens lock: **Overview · Map · Calendar · Settings**  
**Brand:** Protocol City (two words) · BluePrint = desk · Overview = Mission Control · Map = dig · no LLC cream · no Wall

## One sentence

**Calendar** is the time lens on **this desk** (local events only). **Settings** is desk configuration — quiet rows, never a second Mission Control.

## Label lock

| Label | Means |
|---|---|
| **BluePrint** | The desk |
| **Overview** | Mission Control glass (agents · jobs · pulse · local-only) |
| **Map** | Dig — glass over a folder |
| **Calendar** | Time lens — local desk events |
| **Settings** | Desk configuration lens |

Calendar and Settings are **lenses**, not Overview embeds. Overview never hosts a Calendar feed or Settings panel. Map verbs (`dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`) stay off Calendar and Settings chrome.

---

## Calendar — current (pc-1489, 2026-09-13)

Supersedes the V1 week-or-day list as the primary Calendar law. The operations Calendar at `/calendar` is the time lens: WorkForce next runs, WorkLane clocks, and an optional local calendar file. Dark PC tokens only. Map verbs stay off this surface.

### Is / Is-not

| Calendar IS | Calendar IS NOT |
|---|---|
| A Today-and-Next agenda of verified clocks on this desk | A chronological dump that opens on the oldest dated work |
| One work item with separately labelled Due, Reminder, Hold until, and Mentioned date | Two rows for the same order when it has more than one clock |
| Next scheduled jobs and latest result in the first screen | Manual seats listed as empty "not scheduled" rows |
| Source-accurate dates (the field or rule that produced each clock) | A date from a title, comment, or gate note shown as Due |
| Honest empty, missing file, and no-next-run states | Synthetic events or inferred liveness |

### Agenda

Default view centres **Today** and **Next**. Past and overdue items are counted in a collapsed group; they are not the first paint. Optional week navigation shifts the selected day by seven days and keeps that day (and project) in the URL so the work-order reader can return here.

Agenda buckets per clock, not by the latest clock on the row: any clock on the selected day → Today; else any clock before that day → Past and overdue; else Next. An overdue due with a later reminder is Past, not Next.

Timed values display in the browser timezone. All-day dates stay on the calendar day they were recorded; they are not shifted by UTC midnight. A date-only `gate_until` is an all-day hold and remains active through the end of that local calendar day.

### Clocks and provenance

Three durable WorkLane clocks plus one narrative label. Every displayed date names its source field.

| Clock on the row | Source field / rule | Not this |
|---|---|---|
| **Due** | `deadline:YYYY-MM-DD` label | A date found in a title, description, comment, or gate note |
| **Reminder** | `reminder:YYYY-MM-DD` label | A timer gate; a reminder does not embargo work |
| **Hold until** | `gate_type=timer` + `gate_until` while that instant is still in the future | A reminder; a human-gate note |
| **Expired hold** | the same timer clock after `gate_until` | Currently blocking; Needs you |
| **Mentioned date** | a date extracted from a human `gate_note` (including `CALENDAR · ~YYYY-MM-DD` and a bare ISO date in that note) | Due |

Ratification notes that happen to contain today's ISO date, and report titles that contain a historical date, are not deadlines. Needs you is the Decide face from attention policy; a date alone never paints it.

ICS keeps one VEVENT per clock, with all-day `VALUE=DATE`, timed values as UTC `Z`, `CATEGORIES` equal to the clock kind (`deadline` · `reminder` · `timer` · `mentioned`), and `X-BLUEPRINT-SOURCE` equal to the source field. A mentioned date from `gate_note` keeps the pre-change UID (`…-deadline-YYYY-MM-DD@blueprint.calendar`) so subscribers update the existing VEVENT; kind and CATEGORIES may change, the UID may not.

### Jobs and local events

Scheduled jobs (a next-run time), all-day work dates, and manual/on-demand jobs are visibly different. Manual seats collapse to one on-demand count. A job with no next run says so. Latest result is shown when the ledger has one.

A missing local calendar file is **not configured**, not empty events. An unreadable file is **unavailable**. Agent schedules do not depend on that file.

### Out of scope here

- Multi-workspace or cloud calendars
- Fabricated attendees or synthetic busy cinema
- Editing live dates, gates, or reminders
- Recurrence editors beyond what WorkForce already stores
- Map verbs / Wall feed / cream tokens

---

## Settings — V1

### Is / Is-not

| Settings IS | Settings IS NOT |
|---|---|
| Grouped config rows for **this desk** | A dashboard competing with Overview |
| Quiet label · value/control · helper | Marketing / stranger chrome |
| Cellar tip = brew face | Private ProtocolCity SHA as “version” |
| Dark PC only in V1 | Cream / LLC palette toggle |

### V1 groups (order)

1. **Desk** — binder/path honesty on this desk; Local desk label.  
2. **Appearance** — dark PC only (no cream theme in V1).  
3. **Privacy / Local-only** — local-only honesty copy; no cloud-ops toggles that lie.  
4. **About / Cellar** — Cellar tip version (brew), never private install SHA.

### Row pattern

Same density as Overview tiles: uppercase/muted group title · row label · control/value · quiet helper. Shared 2px focus ring (`#f5cf7a` family).

### Out of V1

- Theme marketplace / cream  
- Map View Options (Managed·Unmanaged·Hidden) — Map Later / RESTORE ledger  
- Settings that invent cloud workers Overview can’t see  

### Glass DoD (Settings)

1. Four-lens nav live — Settings is current.  
2. Four groups paint in order above.  
3. About/Cellar shows brew tip honesty.  
4. Dark PC only — no cream.  
5. No Overview tile duplication / no Wall.

---

## Peel order (suggested)

1. Nav shell — real surfaces for Map / Calendar / Settings (stubs OK if honest empty).  
2. Calendar list + empty.  
3. Settings groups + Cellar tip row.  
4. Bind local truth (Builder lane) — Design DoD after paint.

## Soft nits (from MC pack)

- Outbound builders = link voice (`→`), not create-plus.  
- Prefer **desk** / **this desk** over workspace.  
- Protocol City = two words.
