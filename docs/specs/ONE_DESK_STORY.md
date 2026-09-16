# One desk story — ten surfaces, one truth, no theater

Status: design record for pc-1505, 2026-09-16. Founder session: ten surfaces
do not tell the same story; work can sit in a hole (132 open, 8 Decide golds,
POS/tradeOS "none staffed"); Map and Overview feel still even when agents are
moving. The fix is not a Figma restyle — it is naming what each surface is
already for, closing the one real gap (unrouted work is invisible), and
tying the motion every surface already has a right to (the change feed) into
one law instead of ten local habits. This paper changes no code and invents
no design tokens; it composes [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md),
[SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md), [STATES_AND_TERMS.md](STATES_AND_TERMS.md),
[OVERVIEW_INTENT.md](OVERVIEW_INTENT.md), [AGENTS_INTENT.md](AGENTS_INTENT.md),
[PROJECTS_INTENT.md](PROJECTS_INTENT.md), [CONNECTIONS_INTENT.md](CONNECTIONS_INTENT.md),
[MAP_FOCUSED_PROJECT.md](MAP_FOCUSED_PROJECT.md), [ACTIVITY_INTENT.md](ACTIVITY_INTENT.md)
and [SETTINGS_INTENT.md](SETTINGS_INTENT.md). Parent tracking order: pc-1498.
Sibling: pc-1504 (the Overview Current-execution contradiction is implement-now
bug work, not this paper).

## One sentence

The desk tells one story in ten rooms: **something is either running, waiting
on you, waiting on a seat, or already moved** — and every surface answers
that same question from its own angle, never a different one.

## One story per surface

Each row is the one thing that surface is for. This is a naming pass over
decisions already made in the linked records, not a new decision; where a
surface's INTENT already states its one sentence, this table restates it
in the founder's shorthand and cites the source.

| Surface | One-word story | What it answers | Source of the fuller sentence |
|---|---|---|---|
| **Overview** | Now | What is running, what needs you, what just changed | [OVERVIEW_INTENT.md](OVERVIEW_INTENT.md) (landing lens), compact-row contract in SURFACES_REVIEW §"Compact row contract" |
| **Work** | Board | Every open order, comparable, filterable by who/what/why | STATES_AND_TERMS §5 (all open, five axes) |
| **Projects** | Coverage + live | Which project holds how much work and who is on it right now | [PROJECTS_INTENT.md](PROJECTS_INTENT.md) |
| **Agents** | Seats | What each registered seat and job is doing and the one action available | [AGENTS_INTENT.md](AGENTS_INTENT.md) |
| **Delivery** | Shipped | What actually merged, released and is installed, exceptions first | ACTIVITY_INTENT.md option A / pc-1487 |
| **Timeline** | The moving log | The one source-labelled stream of verified events across engines | ACTIVITY_INTENT.md option B / pc-1488 |
| **Map** | Place, not theater | Where a project's work, seats, papers and delivery live, one branch open at a time | [MAP_FOCUSED_PROJECT.md](MAP_FOCUSED_PROJECT.md) |
| **Calendar** | When | What is due today, what is scheduled next, with its source | OVERVIEW_CALENDAR_SETTINGS.md / pc-1489 |
| **Connections** | Providers + engines | Whether each source is reachable, usable, fresh and installed | [CONNECTIONS_INTENT.md](CONNECTIONS_INTENT.md) |
| **Settings** | This browser | What this browser prefers and what build is running | [SETTINGS_INTENT.md](SETTINGS_INTENT.md) |

Every surface reads the same operations projection (or the same WorkForce /
GitHub facts); none of them invents a second truth. A number that
disagrees between two surfaces is a bug against this table, not a style
choice — the reconciliation already required by STATES_AND_TERMS §5 ("Counts
are explicit ... per-project totals agree with Projects and Overview") is
the acceptance test for this row.

## The hole: unrouted work is invisible

The founder's evidence: 132 open orders, 8 Decide golds in For You, and
several projects read "none staffed" — but nothing on the desk answers "how
much open, ungated, eligible work has no seat at all?" That number exists
today only as a manual cross of two Work filters (Gate = none, Assignment =
Unassigned) and is not painted anywhere as a fact a person can see without
building the filter themselves.

This is not a For You gap. STATES_AND_TERMS §1.4 is correct that For You
answers "does this want a *person* now" — an Unassigned, ungated,
`execution:bounded` order does not want a person, it wants a seat, and
inflating For You with it would repeat the D16 mistake (Kind items counted
as attention). It needs its own named fact, computed the same way the
`needs:routing` chip already is (STATES_AND_TERMS §1.3, §6: ungated and
unassigned; the engine's own `needs:routing` label is history only —
BluePrint computes it fresh).

### The fact: Unrouted

**Unrouted** = an open order (backlog, not deferred/tracking) that is
ungated and carries no `worker:` label at all — no seat, no You. It is
computed exactly like the existing per-row **Needs routing** chip
(STATES_AND_TERMS §1.3), rolled up to a count. A subset, **Unrouted ·
ready**, additionally carries `execution:bounded` (or another seat's
eligibility label) and every declared blocker done — the readiness policy
already used for `wl_ready` (STATES_AND_TERMS §1.2) applied to this slice.
An order that is Unassigned but deferred, tracking, or gated (human/timer)
is not Unrouted; it is already visible under its own gate. Unrouted is
strictly about work nobody could even start yet, not work somebody is
choosing not to start.

### Where it shows

| Surface | Placement | Rule |
|---|---|---|
| Overview | A third line beside Current execution and For You, reading `Unrouted N · ready M` | Never merged into For You; zero renders as quiet text, not hidden (OVERVIEW_INTENT invariant 4, honest empty) |
| Work | Gate filter gains no new value (Gate already has "none"); the header's filtered/total line names the Unrouted count when Assignment=Unassigned and Gate=none are both active, and a standing link `Show unrouted` sets those two filters in one click | No new axis; this is a saved filter combination, not a sixth axis |
| Projects | Existing "Agents now" cell (PROJECTS_INTENT) gains no change; the per-project disclosure (already spec'd to show open by status, gate counts, seats) adds one more named count: unrouted-in-this-project | Reuses the same disclosure row shape; no new fetch |
| Agents | Unchanged — Agents answers "what are seats doing," not "what has no seat"; a person routes *from* Work or Projects, not by inventing a fifth Agents section | Keeps AGENTS_INTENT's Is-not: "a scheduler, an orchestrator, or a place to edit rosters" |

Unrouted is a read-only computed fact everywhere, exactly like For You: it
never writes a label, never assigns a seat, and never triggers a dispatch.
Routing itself (assigning a `worker:` label) stays the existing WorkLane
edit path; this paper only makes the size of the problem visible before
someone decides to route it, whether that someone is the founder, a
provider-routing table (pc-1503, parked for ratify), or bp-supervisor
proposing a seat.

## Motion is one law, not ten habits

Every surface that already animates does so from the same source — the
change feed described in SURFACES_REVIEW's decision D2 and threaded through
PROJECTS_INTENT ("a change-feed event ... updates that row in place"),
AGENTS_INTENT (shift/claim state), and MAP_FOCUSED_PROJECT ("a real
change-feed event ... may flash the matching branch"). This paper states
the law once so no future peel invents an eleventh motion rule:

1. **A pixel may move only because one of three things happened**: a
   change-feed event fired (a WorkLane store file, the WorkForce daemon
   file, the ledger, or a supervisor report changed on disk), a WorkForce
   shift opened or closed (Running / Live-state semantics table,
   SURFACES_REVIEW), or a WorkLane claim was made or released (an Owner
   marker landed or a park/close happened). No timer, no loop, no
   fabricated tick ever animates anything (OVERVIEW_INTENT's "no rot
   re-entry": fake ticks are Later-and-rejected, not paused).
2. **Reduced motion (system or saved) turns every one of those animations
   into an immediate state change**, everywhere, with no per-surface
   opt-out (already required individually by MAP_FOCUSED_PROJECT,
   PROJECTS_INTENT and Settings' Motion preference; this paper makes it
   one law all ten surfaces answer to).
3. **Unchanged rows never flash.** Only the row, tile or branch whose
   underlying fact changed gets the transition; a poll or a change-feed
   event that reads identical content is silent (STATES_AND_TERMS "Last
   change": "ignoring read times and heartbeat ticks").
4. **The transport indicator (Live / connected) is never itself evidence
   of movement.** It says the pipe is open, nothing else (CONNECTIONS_INTENT:
   "The header Updates connected / Live chip is only the change-feed
   transport... it never stands in for source freshness or capability").

This is the "symphony of verified movement" the founder asked for: real
file changes ripple into the rows that changed, on every surface that
reads them, using one mechanism — never a second projection, never an
ambient loop dressed up as liveness.

## Is-not

| Rejected | Why |
|---|---|
| Restore the FAST theater / four-lens host / folder-seat stack | Retired 2026-09-14; OPERATIONS_EVOLUTION: "must not be restored as a second projection or an apparent live activity layer" |
| A Figma plugin rewrite or new visual system | Founder said no restyle; existing dark PC desk tokens (OVERVIEW_THEME) are unchanged by this paper |
| Grok Bot (or any chat surface) as a roster seat | pc-1498 lock: "WorkLane, WorkForce, and Connector stay separate repos"; STATES_AND_TERMS §2 keeps seats/jobs to the WorkForce roster only; kloss_xyz/0xMorlex bookmarks folded into pc-1503's routing paper, not this one |
| Hire-every-project (a seat on every store regardless of load) | PROJECTS_INTENT: "none staffed" is an honest state, not a defect to paper over with headcount; D12/pc-1503 (parked for ratify) own routing policy, not this paper |
| Unrouted becoming a fifth For You face, a dispatch button, or a synthetic "someone should" nudge | For You is strictly "wants a person" (STATES_AND_TERMS §1.4); Unrouted wants a seat or a routing decision, and stays read-only here |
| A second live-event bus, SSE tape, or per-surface polling interval | One change feed (SURFACES_REVIEW D2), one law above; Settings' fallback-poll stays the fallback, not a second source of truth |

## Acceptance

- This paper lands in `blueprint/docs/specs/`.
- One-story table above is the reference every future surface order cites instead of re-deriving purpose.
- Unrouted is specified as a read-only computed fact (definition, placement, and what it is not) — implementation is a separate child order, filed after ratify.
- The motion law consolidates existing per-surface motion rules into one statement; it changes no current behavior by itself.
- Is-not table gives a future peel one place to check before re-proposing a rejected shape.

**Human gate.** Park for founder ratify before any implementation child
(an Unrouted-count order, or a further motion-law audit) is filed. This
paper authorizes no code, no routing change, and no hire.
