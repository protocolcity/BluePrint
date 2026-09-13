# Activity INTENT — delivery evidence, or a joined timeline

Status: design record for pc-1459, 2026-09-13. Companion to [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md), [OVERVIEW_INTENT.md](OVERVIEW_INTENT.md) (which holds "activity feeds" as later chrome) and [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md).

## What exists

`/activity` is a cached GitHub read per allowlisted repository: open pull requests (8), the last 8 workflow runs, the latest release; refreshed every two minutes; labelled truthfully as not agent liveness. On 2026-09-13 it showed eight "Source validation" rows because that is the name of BluePrint's CI workflow. Merged PRs, commits, WorkLane events, WorkForce shifts and supervisor passes do not appear anywhere as a stream.

## Why it reads wrong

The name promises a feed of what happened; the accepted design deliberately deferred activity feeds; and the content is a CI status list. A surface named Activity that never shows the agents' activity contradicts the desk's own voice.

## Two options

**A. Delivery (rename and finish what it is).** Rename the tab Delivery. Group by repository with the repository's role. Show CI runs as "CI · workflow name · result · commit", collapse identical consecutive runs, include merged and closed PRs from the last 14 days, label repositories with no rows as quiet rather than empty, and keep the two-minute cache. No new sources. Small order; can ship this week.

**B. Timeline (the joined feed).** A read-only, source-labelled stream across the desk: WorkLane events (filed, claimed, parked, closed, gated), WorkForce shifts (started, stopped, failed, recovered), supervisor passes, and GitHub delivery (PR opened, merged, CI result, release). One row per event with time, source, project, actor and a link to the order, seat, pass or PR. Filters by project and source. Requires the change feed (SURFACES_REVIEW decision D2) to be live, plus event readers for WorkLane comments and the WorkForce ledger. Larger order; honest only if every row carries its source and observation time.

## Recommendation

Do A now and file B as the follow-on once the change feed exists. A fixes the wrong promise immediately; B is the surface the operator actually wants and should be built on push, not polling.

## Is / Is-not (both options)

| IS | IS NOT |
|---|---|
| Evidence with a source and a time | Liveness or progress inference |
| Grouped or filtered by project | A wall that hides the projects |
| Honest quiet states | Empty cards padded to look busy |
| Links into Work, Agents and GitHub | A second reader |

## Held

Synthetic activity, motion, notifications, any write action, cross-workspace feeds.
