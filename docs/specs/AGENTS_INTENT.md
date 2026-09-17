# Agents INTENT — seats, jobs and the supervisor, as evidence

Status: design record for pc-1461, 2026-09-13. Companion to [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md) and [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md). Decision spec, not a token registry; paint follows [OVERVIEW_THEME.md](OVERVIEW_THEME.md).

## One sentence

Agents shows what each registered seat and job is doing right now, what it last did and why it stopped, and the one action an operator can take, from the engine's own evidence and nothing else.

## Is / Is-not

| Agents IS | Agents IS NOT |
|---|---|
| The WorkForce registry read with fresh runtime evidence beside each row | A scheduler, an orchestrator, or a place to edit rosters |
| Three groups with different jobs: implementation seats, scheduled jobs, the supervisor | One grid of identical cards |
| Honest about liveness: open shift from the ledger, lock held, heartbeat age, stale shift | A dashboard that infers "running" from a process guess or paints activity to look busy |
| A reader of supervisor passes: proposals, validations, dispatch outcomes, escalation state | A view that paints the supervisor as a running worker |
| One clear operator action per row when one applies | A row of buttons |

## Sources and freshness

| Fact | Source | Freshness shown as |
|---|---|---|
| Registry row, kind, schedule, model, command configured | roster | file read time |
| Heartbeat | daemon last tick | fresh under 120 s, else stale, else unknown |
| Open shift, candidates, budget, lock held, stale | ledger START without STOP/ERROR; locks dir | started at, elapsed, source "engine ledger" |
| Last run and reason | last terminal ledger row | time, outcome, reason text |
| Held work and verified owner | WorkForce `/api/worker/<name>` holding | WorkLane owner verified true/false |
| Supervisor passes | WorkForce `/api/supervisor` | pass time, outcome, counts |
| Recovery attempts | ledger rows tagged recovery=1; reservation receipts | attempt number, reason |
| Job report | `.blueprint/job-reports/<id>.json` | observed time, mode |

Nothing on the surface may claim a fact without one of these sources. Missing source: label unavailable.

## Information hierarchy

```
AGENTS                                   heartbeat: fresh · 12s ago      Supervisor: last pass 03:41 · dispatched 1

SEATS (implementation lanes)                                   [what they can claim: project + label]
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ● wf-claude-implementer   WorkForce · Claude · manual                     WORKING    │
│   Shift open 6m · budget 25m · holds wf-255 (owner verified) · lock held  [engine ledger]
│   Last run: recovery single pass complete · 04:04 · 21s                              │
│   Action: none (in flight)                                                            │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ○ wf-cursor-implementer   WorkForce · Cursor · manual                     IDLE       │
│   Ready for it: 0 · Last run: single-pass complete · 03:12 · 106s                     │
│   Action: Dispatch now (nothing ready: will stop cleanly)                             │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ! shop-claude-implementer  Shop · Claude · manual                     LAST RUN FAILED
│   Last run: agent exit rc 1 · Sep 12 19:41 · evidence run/shop-claude-implementer.out  │
│   Action: Recover preserved reservation (shop-12) or clear the stale flag            │
└──────────────────────────────────────────────────────────────────────────────────────┘

JOBS (scheduled duties)                                          next run · last report
  chief-of-staff        weekdays 09:00   next Sep 14 09:00   completed · 146 open · 36 ready
  health-patrol         weekdays 11,15   next Sep 14 11:00   completed
  workspace-efficiency  daily 09:30,16:30 next Sep 13 09:30  completed · coverage: none configured
  claude-reviewer · cursor-reviewer · workflow-reviewer   manual review jobs · last run + duration

SUPERVISOR (bp-supervisor · manual · budget 35m)                           stop file: absent
  Last pass 03:41 execute · proposals 1 · valid 1 · dispatched 1 · failed 1
    wf-claude-implementer → wf-255 · failed (agent exit rc 1) → recovered 04:04
  Earlier: 03:38 no eligible ready work (provider not called) · 03:10 execute 2/2 completed
  Escalation: none (0 consecutive provider failures)                      [ /api/supervisor ]
```

Rows are ordered by state (working, failed, idle), then name. A seat's header line names its project and provider because that is what routing is about. The badge vocabulary is fixed: WORKING · IDLE · STALE SHIFT · LAST RUN FAILED · UNKNOWN (heartbeat stale) · NOT CONFIGURED · OFF.

## States and what they mean

| Badge | Evidence | Operator action offered |
|---|---|---|
| WORKING | open shift within budget plus grace (ledger) or daemon in_flight | none |
| IDLE | last terminal row is STOP or DONE and no open shift | Dispatch now |
| STALE SHIFT | START past budget plus grace with no terminal row | Inspect (link to ledger tail); dispatch disabled until the engine reclaims |
| LAST RUN FAILED | last terminal row is ERROR | Recover (when a preserved reservation exists) or Dispatch now with the failure shown |
| UNKNOWN | heartbeat stale or missing | none; the heartbeat is the fix |
| NOT CONFIGURED / OFF | placeholder command / enabled false | none |

Failed is failed: an ERROR row is never softened into "stopped". The reason text and the evidence file name are shown on the row.

## Supervisor panel

Reads only `/api/supervisor` and the supervisor config the engine reports (stop file present or absent, escalation streak). Shows the last pass and the two before it, each with pass outcome, proposal counts, and per-seat dispatch outcome with the candidate order. It never shows the supervisor as a worker card; it is a pass record. A "Run a pass" action dispatches the registered `bp-supervisor` job through the engine and says so.

## Held (not in this pass)

Roster editing; schedule changes; provider quota meters (no live source); a per-seat cost meter beyond what the ledger records; any animation of activity; cross-workspace views.

## Acceptance for the implementation order

Grouped layout with the three sections; badge vocabulary and sources exactly as above; supervisor panel from `/api/supervisor`; recovery attempts shown from ledger rows; one action per row; disposable-fixture tests for every badge state and for the supervisor panel; verified on the running app during a real shift and after a real failure (both exist in the wf-252 evidence).

## Compact rows and a selected-run inspector (pc-1485, 2026-09-13)

Seats moved from tall repeated cards to one compact comparable row each,
ordered by state then name (unchanged from §"Information hierarchy" above).
A row states only what an operator scans a roster for: project, seat name
and provider/model, badge, the current work-order title+id (a reader link,
or "No current work"), elapsed run time against budget (a time budget,
never a percent), the last meaningful update, and the one supported action
from the existing badge-to-action table. Raw identity slugs, full ledger
paths, and the cumulative recovery count move behind selecting the row.

Selecting a seat's row (click or Enter/Space, `aria-pressed` on the row)
opens one shared inspector panel beneath the seat rows with a
source-labelled run timeline, in this fixed order:

| Step | Source | Shown as |
|---|---|---|
| Dispatch candidate | ledger CANDIDATE rows in the last START block (open or closed) | ticket list, or "Not reported" |
| Verified claim | WorkForce holding compared against the dispatch candidates | "Verified: holds X", "Holds X · not yet verified", or a no-longer-held explanation |
| Observed run start | open-shift `started_at` | timestamp, or "Not reported" when no shift is open |
| Recovery attempts | ledger START rows tagged `recovery=1` | the count (0 is a fact, not a gap) |
| Terminal outcome | last terminal ledger row | outcome, reason, time, or "Open — no terminal row yet" |

A missing phase always reads "Not reported"; nothing is inferred from
absence. When a seat reads LAST RUN FAILED but no longer holds an order,
the Verified claim step says so explicitly ("the failed ticket may
already be resolved by another provider") instead of implying the
current seat is still failing — an old failure is not automatically a
current task failure. Jobs keep a compact schedule/report line (schedule,
next run, badge, last report or last run) with no timeline, since a job
never claims a work order to verify. The supervisor panel keeps its
previously held placement and shape; this order does not revisit it.

## Parked handoffs while a shift is still open (pc-1495, 2026-09-13)

A seat's current-work cell follows fixed precedence: an in_progress claim
(title · id link); else parked in_review orders it owns (`Parked: … ·
awaiting integration`); else "No current work". When the engine shift is
still open but the seat no longer holds anything in_progress and has parked
during that shift, the badge stays **WORKING** and the cell reads
**Finishing · parked pc-…** instead of going blank. After the shift closes,
the row returns to **IDLE** (or another terminal badge) but still lists
parked orders awaiting integration. The inspector's Verified claim step uses
the parked order's park time when that is the terminal claim state.

## Live floor pulse (pc-1513, 2026-09-17)

Agents opens on a Working / Idle / Error strip with counts from the same
badge `state` the roster already publishes. Off, unknown, and not-configured
rows never inflate Idle; they sit behind a Quiet disclosure so the floor is
not a dead Off wall. Stale shift is named on a remainder line, not folded
into Error — a failed run stays failed. Seat rows that are working or failed
keep claim/state on the card (live cue on an open in-budget shift). Next fire
stays the Calendar door from pc-1512 (`calendar_doors.next_fire_line`); this
order does not invent a second countdown. The Map A ten-page nav is unchanged.
When nothing is working the strip reads 0 and the empty line says so.
