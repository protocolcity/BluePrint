# States and terms — what every word on the desk means

Status: design record for pc-1461, 2026-09-13. Source of each definition is the engine or paper named beside it; BluePrint may only show what one of them establishes. Companion to [SUITE_VOCABULARY.md](SUITE_VOCABULARY.md), [AGENTS_INTENT.md](AGENTS_INTENT.md) and [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md). WorkLane's own rules are in `worklane/PROTOCOL.md`; this paper restates them in the desk's words and fixes how each surface presents them.

## 1. A work order has four independent axes

An order is not "in one state". It has a **status** (where it is in the pool), a **gate** (whether anyone may take it), an **assignment** (who it is routed to), and a **claim** (who actually holds it). Attention (For You) is derived from those four and the clock. Every surface must keep the axes separate; collapsing them is how "in progress" got read as "an agent is working".

### 1.1 Status (WorkLane pool position)

| Status | Meaning (PROTOCOL §1, §4) | Surface word |
|---|---|---|
| backlog | Free pool; anyone eligible may take it | **Open** |
| in_review | Soft lock: reserved, parked or bundled by an identity; others skip. Not a sign-off queue | **Parked** (by whom) |
| in_progress | The live order for one identity; exactly one per identity | **Live** (with whom) |
| done | Closed with Completed / Verification / Links / Follow-ups | **Done** |
| canceled | Withdrawn with a signed reason | **Canceled** |

Rule kept from PROTOCOL 7a: finished agent work parked in_review is a handoff to the host integrator, not a request for You to approve it.

### 1.2 Gate (may anyone take it)

| gate_type | Meaning | Ready? | Surface word |
|---|---|---|---|
| none | Ungated | yes, if blockers are done | (nothing) |
| human | You must act now; gate_note says what and what clears it | no | **Needs a decision** |
| timer | Embargoed until gate_until, then thaws itself | no until then | **Held until (date)** |
| deferred | Parked on purpose; gate_note says what would thaw it | no | **Deferred** |
| tracking | Structural umbrella; children implement; never claimed | no | **Tracking** |

**Ready** (WorkLane readiness policy, wl-517): status backlog, no active gate, every declared and structured blocker done, and, for a seat, carrying that seat's `worker:` label and the seat's required eligibility label (`execution:bounded` for the bounded implementation seats). Ready is a computed fact; it is never a status.

### 1.3 Assignment (who it is routed to) versus claim (who holds it)

| Term | Evidence | Surface word |
|---|---|---|
| Assigned | one or more `worker:<id>` labels | **Assigned to** You / seat name |
| Unassigned | no `worker:` label | **Unassigned** |
| Needs routing | `needs:routing` label | **Needs routing** (a triage chip, not a state) |
| Claimed (live) | signed Owner marker comment and status in_progress | **Live with** identity, since time |
| Parked (held) | Owner marker and status in_review | **Parked by** identity, since time |
| Verified holder | WorkForce confirms the WorkLane owner matches the seat | small "verified" mark on Agents |

**Decision D10 (2026-09-13, user question on the Work filter). Partly superseded by §5 on the same day: You returns to the Assignment filter and For You leaves the Status filter.** Assignment values come from the roster, not from whatever labels happen to be on open orders: **You**, each hired seat (lanes only, listed even with zero orders) and **Unassigned**. "Needs routing" is not an assignment; it is a triage chip on a row, computed as ungated and unassigned, so a deferred or tracking order never needs routing while it is parked (today the label sits on 84 parked orders and duplicates "no worker assigned"). A human-gated order is You's by definition: it reads Assigned to You and enters For You even when no worker label was stamped. Assignment answers "who is it routed to"; For You answers "does it want a person now"; an order can be both Assigned to You and in For You, and that is two facts, not an overlap. The Status filter's "Needs you" entry becomes "For You (any face)" with the four faces beneath it; the Assignment entry reads "Assigned to You".

**Decision D11 (2026-09-13). You is a persona, not a seat. Superseded by §5 for the Work filters: You is an assignment value again; the persona qualifiers stay as item kinds.** Nobody expects You to pick up work orders the way a seat does; what You has is attention. On the desk, assignment values are therefore seats and Unassigned only. Items that belong to the person live in the project's own store (a project-related item always goes to the project store) but are classified by the You qualifier, never routed as work: `you:todo` is a personal task (Note face), `you:remind` a dated reminder (Note face with the date), a human gate a decision (Decide face), an inbox report something to read (Read face). `you:host` (You implementing on this machine) is retired as a routing target: implementation work is Unassigned with a "needs a seat" chip until a qualified seat takes it, or it is on a seat. On the wire `worker:you` remains the label WorkLane requires for persona items; the desk never shows it as an assignment. Live count at the time of the decision: 45 orders on You, of which 9 decisions, 3 reminders, 9 personal tasks, 9 parked and 15 implementation orders that belong on seats.

You qualifiers (see D11): `you:todo` (personal task), `you:remind` (dated reminder), `you:note` (personal note); `you:host` is retired as a routing target. `gate:founder` marks a publication or money gate that only You can pass. An assignment is routing intent; only a claim proves anyone is working. Work rows today print the assignment as "owner"; the record renames it **Assigned to** and adds **Live with / Parked by** from the Owner marker.

### 1.4 Attention: For You and its four faces

**For You** is the one pile of things that want a person. It has four faces, computed by BluePrint (attention_view.face) from gates, labels and the clock, never stored:

| Face | Rule (exact) | What it asks of you | Gold? |
|---|---|---|---|
| **Decide** | gate human with an act-now note (not parking language), or `gate:human` / `needs:founder-decision` label | act now; the note says what and what clears it | yes |
| **Read** | `inbox-report` label (a report was written for you) | read, then clear or snooze | yes |
| **Watch** | timer gate, or a live/parked order untouched for 90 minutes | look at evidence; not proof anything died | no |
| **Note** | `reminder:<date>` label or `you:note` / `you:todo` / `you:remind` | your own list; no gate | no |
| (none) | everything else, including all deferred and tracking orders | nothing | no |

Three clocks stay separate: a timer gate is an embargo, a reminder label is a date, a browser mute hides a card here only. A `deadline:YYYY-MM-DD` label is Due. A date taken from a gate note, title, or history is a mentioned date, not a deadline. An expired timer is labelled expired; it is not currently blocking. Needs you is the Decide face, never the existence of a date. Calendar presentation is in [OVERVIEW_CALENDAR_SETTINGS.md](OVERVIEW_CALENDAR_SETTINGS.md).

**Naming decision (D6).** Overview says "Needs you 10" while the panel opens on "Decide · 8". They measure the same pile with different filters. The record fixes one word: the metric and the panel are both **For You**, the number is the whole pile, and the breakdown shows the faces (8 decide · 2 read · 2 watch · 5 note). Decide and Read are open by default; Watch and Note are collapsed with counts. "Needs you" survives only as the badge on a Decide row.

## 2. Seats, jobs, shifts and passes (WorkForce)

| Term | Evidence | Surface word |
|---|---|---|
| Seat (lane) | roster kind lane; claims work orders under its own identity | **Seat** |
| Job | roster kind job; scheduled or manual duty; never claims | **Job** |
| Schedule | cron or manual | **Automatic (cron text)** / **On demand** |
| Heartbeat | daemon last tick | fresh under 2 min · stale · unknown |
| Shift | ledger START to STOP/ERROR | **Working** (open, within budget plus grace) · **Stale shift** (past it, no terminal row) |
| Last run | last terminal ledger row | outcome and reason verbatim |
| Recovery attempt | ledger rows tagged recovery=1; attempts/N receipts | **Recovery n** on the shift line |
| Supervisor pass | /api/supervisor row | pass outcome: no eligible ready work · stopped by operator · escalated · provider failed · proposed · dispatched |
| Dispatch outcome | per seat in a pass | completed · failed · denied · skipped · rejected at dispatch time |

Badge vocabulary and one-action-per-row rules are in AGENTS_INTENT.

## 3. What each surface must show per item

Legend: ✓ shown today · ○ missing · — not needed there.

| Field | Work row | For You card | Reader | Projects card | Calendar row | Agents row |
|---|---|---|---|---|---|---|
| id, project, title | ✓ | ✓ | ✓ | — | ✓ | held order ✓ |
| status word (Open/Live/Parked) | ✓ badge | ○ | ✓ | — | — | — |
| gate word and note | ✓ truncated | ✓ | ✓ | — | hold-until ✓ | — |
| face and why (rule that fired) | ✓ badge, ○ why | ✓ badge, ○ why | ○ | — | ✓ badge | — |
| assigned to | ✓ (as "owner") | ✓ | ✓ | ○ seats per project | — | — |
| live with / parked by, since | ○ | ○ | ○ (only in comments) | — | — | ✓ holding |
| ready for seat / eligibility label | ○ | — | ○ | — | — | ✓ ready count |
| blockers and parent | ○ | — | ○ | — | — | — |
| updated, and by whom | ✓ time | ✓ time | ✓ | ○ last activity | — | — |
| last note snippet | ○ | ✓ gate note | ✓ full | — | — | — |
| dated fields (due, hold until, reminder, mentioned date) | ○ | ○ | ✓ | — | ✓ with source field | — |
| counts: open, For You, deferred | — | — | — | ✓ open, ✓ need you, ○ deferred | — | — |

The gaps in the "live with / parked by" column are the ones that made the desk feel unwired: an order can be live with a seat and the Work row still says "you". The change feed (D2) makes the live column worth having; without push it would be stale on arrival.

## 4. Decisions recorded here

- D6 One word: For You everywhere; faces as the breakdown; "Needs you" only as a row badge. Recommended.
- D7 Rows carry both axes: Assigned to (labels) and Live with / Parked by (claim), never one word for both. Recommended.
- D8 Watch threshold stays at 90 minutes untouched; shown as "no update for 1h 40m", never as "stalled". Recommended.
- D9 Deferred and tracking never enter For You and are hidden from Work by default (D3), with counts visible. **Superseded on 2026-09-13 by §5: they stay out of For You, but All open shows them.**

## 5. Correction of 2026-09-13 — the five axes on Work (supersedes D3, D9's default hiding, D10's filter shape and D11's removal of You)

The user reviewed the installed Work surface on consolidation.47 and corrected two things: All open hid 87 of 122 open orders behind a "Show deferred and tracking" checkbox, and You had been removed from Assignment while For You sat inside Status. This section is the current rule; the earlier decisions above stay as history and must not be restored by following the old text. Owning implementation order: pc-1482.

| Axis | Question it answers | Values | Source |
|---|---|---|---|
| **Assignment** | Who is responsible | **You** · each registered seat · Unassigned | `worker:` labels and persona qualifiers; You matches `worker:you` and human-owned decisions, never an agent-owned decision |
| **Status** | Where in the lifecycle | Open · Live · Parked (plus Done, Canceled when asked for) | WorkLane status |
| **Gate** | May it execute | none · human · timer (active or expired) · deferred · tracking | WorkLane gate fields; an expired timer is not an active embargo |
| **Kind** | What sort of item | work · note · todo · reminder · report, where recorded | `you:*`, `reminder:*`, `inbox-report` labels |
| **For You** | Does it want a person now | the four faces (Decide · Read · Watch · Note) | computed attention (§1.4); a named view, not a status |

Rules:

- **All open is complete.** The default Work list is every order that is not done or canceled from every readable registered store, whatever its gate. Per-project totals agree with Projects and Overview. Unavailable or truncated stores are labelled on the page, never silently short.
- **No hidden second filter.** The "Show deferred and tracking" checkbox is removed. Gate is its own filter with an explicit value list and no default exclusion. Status holds lifecycle words only.
- **You is an assignment.** Assignment lists You beside All assignments, the registered seats and Unassigned. Persona items (`you:todo`, `you:remind`, `you:note`) and human-owned decisions match You; an agent-owned order with a human gate stays assigned to that agent and appears in For You because You must act. A row never reads "Assigned to Unassigned" for a persona item.
- **For You is attention.** It is not a Status choice; it is the named inbox view with its faces. An order can be assigned to You and in For You, or assigned to a seat and in For You; those are two facts.
- **Ready comes from the engine.** A Ready view uses WorkLane readiness (dependencies, gate expiry, seat eligibility); ungated backlog is not "ready" by itself. Deferred and tracking orders are visible under All open and remain unclaimable.
- **Counts are explicit.** The list header states filtered of total and the active filters with a clear-all. Filters, page and selection survive refresh, back/forward, reader return and reload; the old `deferred=1` and `status=gate:*` links map to the Gate filter.
- **Stored data is untouched.** No stored status is added, no gate or label is rewritten to make the view come out; the projection and the filters change, the records do not.

Fixtures every implementation must carry: a personal reminder assigned to You; an agent-owned human gate visible in For You and still assigned to the agent; an ungated ready agent order; deferred and tracking records visible under All open but not ready; an expired timer beside an active one; an unavailable store and a truncated store.

## 6. Label matrix — every tag on a work order, which axis it feeds, who writes it

Inventory taken 2026-09-13 across all twelve registered stores (133 open orders). Labels are free text in WorkLane; this table is the desk's contract for reading them. A label that is not in the table is a project tag (area, topic) and feeds nothing on the desk except search. Nothing here creates a new stored status; every row maps a label onto one of the five axes of §5 or onto a fact the reader shows.

| Label family | Meaning | Axis it feeds | Written by | Shown on the desk as |
|---|---|---|---|---|
| `product:<slug>` | Store identity stamped on every order | none (routing) | WorkLane on create | project name on the row |
| `worker:<seat>` | Routed to a registered seat | **Assignment** | filer, coordinator, seat generator | Assigned to seat; Assignment filter |
| `worker:you` | Routed to the person | **Assignment** = You | filer, coordinator | Assigned to You (pc-1493 fixes the host case) |
| `you:todo` · `you:remind` · `you:note` | Personal item kinds; `you:host` = You implementing on this machine | **Kind** (and Assignment = You) | filer | Your todo / Reminder (date) / note; Note face in For You |
| `reminder:YYYY-MM-DD` · `deadline:YYYY-MM-DD` | Dated clocks without an embargo | Calendar clocks; Note face | filer, reader | Reminder / Due with the source label named |
| `inbox-report` · `inbox-report:<kind>` | A report was written for the person | **For You** = Read | report jobs | Read face |
| `gate:founder` · `needs:founder-decision` · `needs:founder-present` | Only the person can pass this (publication, money, physical presence) | **For You** = Decide when the gate is human; otherwise a reader chip | filer | Needs you badge; chip |
| `needs:routing` | WorkLane's stamp: no seat carried it when routing was last computed | none on the desk since .50; the desk computes Needs routing from ungated plus unassigned | WorkLane (engine) | Needs routing chip only when ungated and unassigned |
| `execution:bounded` | Eligibility for the bounded implementation seats | Readiness (seat eligibility) | filer | Ready for seat |
| `seat:cloud` | Historical: routed to a cloud/citizen executor that no longer exists | none; awaiting wf-258 | historical | nothing (search only) |
| `epic` · `epic:tracking` · `epic:citizen-park` · `goal` | Structural umbrella markers | none; the **Gate** value tracking is the fact | filer | Tracking badge comes from gate_type, not the label |
| `parent:<id>` · `slice-of:<id>` | Hierarchy | reader (Part of …) | filer | Part of link |
| `adr:<n>` · `sys:<x>` · `area:<x>` · `phase:<x>` · `host:<x>` | Project taxonomy | none | project | search only |
| `worker:<retired hand>` on done orders · `gate_type:<x>` · `gate_type=<x>` | Legacy markers; a gate must be a real gate field, never a label | none | historical | nothing; corrected when found (osp-1005, pc-1287) |

What is not a label, and must not become one: status (`backlog`, `in_progress`, `in_review`, `done`, `canceled` are fields), the gate (`gate_type`, `gate_until`, `gate_note` are fields), a claim (the signed Owner marker comment), declared blockers (the `blockers` list; a declared blocker is the Gate value "Blocked on another order", pc-1493), and readiness (computed by the WorkLane policy from status, gate, blockers and eligibility).

Reading the inventory: 80 open orders carry `needs:routing` and 57 carry `seat:cloud`; almost all of them are the 77 deferred or tracking orders whose historical hands were retired. They are parked on purpose, they are Unassigned because their seats no longer exist, and they need a seat only when their gate thaws. That is the whole relationship between Unassigned and parked on the Work page: nothing drops work there today; it is the retired-seat backlog, visible since .50 and filterable by Gate.
