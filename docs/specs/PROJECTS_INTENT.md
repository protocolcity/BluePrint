# Projects INTENT — where the work is, who is on it, what moved

Status: design record for pc-1481, 2026-09-13. Owning implementation order: pc-1486. Companion to [STATES_AND_TERMS.md](STATES_AND_TERMS.md), [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md) and [AGENTS_INTENT.md](AGENTS_INTENT.md). Paint follows [OVERVIEW_THEME.md](OVERVIEW_THEME.md); no new tokens, fonts or libraries.

## One sentence

Projects compares the registered project stores of the selected workspace on one scannable page: how much open work each holds and how it is distributed, which agents are on it right now, when something last actually changed, and one direct path into that project's work, attention, papers and Map context.

## Is / Is-not

| Projects IS | Projects IS NOT |
|---|---|
| The registry of project stores (`.protocolcity/desk-join.json`) read with the same operations projection every other surface uses | A second work list, a second Agents page or a folder browser (Map owns place) |
| A comparison: rows with the same columns so twelve projects can be read against each other | Twelve equal cards that give a quiet personal folder the same weight as the product in flight |
| Honest about missing data: store unavailable, truncated, no activity recorded, no seats | A card that prints zero when the store could not be read |
| A scoped door: every count is a link that opens Work, For You, Agents, papers or Map already filtered to that project | A place where work orders are edited |

## Primary hierarchy

```
PROJECTS                                     12 stores · 2 unavailable · read 12s ago

  Project     Open  For You  Deferred  Live/Parked   Agents now         Last change            Go
  BluePrint    31      4        9      2 live        cursor · working     14:58 claim            Work · For You · Papers · Map
  WorkForce     6      1        2      0             none staffed         11:41 note             …
  Shop         12      2        4      0             Claude, Cursor idle  Sep 12 close           …
  Notes         7      5        1      1 live (You)  none staffed         07:24 filed            …
  …
  Quiet projects (no open work, no seats): Tools, Docs, Samples   [show]
```

Rows are ordered by activity: projects with an agent working first, then by For You count, then open count, then name. Projects with no open work and no seats collapse into one "quiet" line with a disclosure, so the page leads with what is moving. On narrow widths the same row becomes a stacked card with the same fields in the same order; nothing is dropped.

## Sources and freshness

| Column | Source | Notes |
|---|---|---|
| Project name, folder, instructions present | project registry (`desk-join.json`, `AGENTS.md`) | file read time |
| Open, For You, Deferred/Tracking | operations projection of that store; counts follow STATES_AND_TERMS §5 (All open includes every gate) | "Store unavailable" or "partial (limited to 2,000)" replaces the number, never zero |
| Live / Parked | WorkLane Owner markers (in_progress / in_review) | a claim is a claim; it is never painted as execution |
| Agents now | WorkForce coverage for the project plus a working/idle read of its seats | "none staffed" when no seat is registered for the project; "working" needs an open shift in the ledger or daemon in-flight |
| Last change | most recent WorkLane event or comment in that store (from the change feed / timeline projection), with actor and order id | "no activity recorded" when the store has no events; never the read time |
| Go links | `/work?project=`, `/work?project=&status=attention`, `/agents` (project filter when available), `/documents?project=`, `/map` project node | links, not buttons; they carry the project id |

Every number opens the surface that explains it. A count with no explanation reachable in one click is a defect.

**Known mismatch:** the running Projects table reads a simpler working/idle
state per seat (open ledger shift or daemon in-flight), not the full
WORKING/IDLE/STALE SHIFT/LAST RUN FAILED/UNKNOWN/NOT CONFIGURED/OFF badge
vocabulary from [AGENTS_INTENT.md](AGENTS_INTENT.md). Agents (the surface)
remains the source of truth for a seat's exact badge; Projects' "Agents now"
column is a coarser at-a-glance read, not a duplicate of it. Closing this gap
is JS/backend work for a future order, not this paper.

## Interactions

- Sort is fixed by activity (above); a text filter narrows rows by name or id. Filter and disclosure state survive refresh and reader return.
- Expanding a row (disclosure, keyboard reachable) shows the per-project breakdown: open by status word, gate counts, the live/parked orders with their holders, the seats registered for the project with their last outcome, and the last three changes. This is the "scoped drill-down"; it reads from the same snapshot and does not fetch a second projection.
- A change-feed event for a store updates that row in place with the one restrained changed-row transition; unchanged rows do not flash.

## Empty, error and held states

| State | Row reads |
|---|---|
| No project stores registered | "No local project stores found." with the registration hint (a folder with `.protocolcity/desk-join.json`) |
| Store unavailable | name, "Store unavailable", the detail from Connections, no counts |
| Store truncated | counts marked "partial"; the limit stated |
| Registered project with no seats | Agents now: "none staffed"; hiring stays on Agents |
| Engine unavailable (WorkForce) | Agents now: "unknown", never idle |

Held (not in pc-1486): editing project registration; project-level settings; per-project cost meters; any cross-workspace view.

How the desk's own vocabulary maps onto this page (Projects = stores, Agents = hired seats + live shifts, Delivery = GitHub evidence, WorkLane/WorkForce stay separate packages): [README.md § How the desk works](../../README.md#how-the-desk-works-in-one-breath) or [SUITE_VOCABULARY.md](SUITE_VOCABULARY.md).

## Acceptance for pc-1486

Rows with the columns above from a live-shaped fixture; activity ordering and quiet-project collapse; unavailable/partial states; disclosure breakdown keyboard reachable; links carry the project id; desktop and 400px installed screenshots; both suites green.
