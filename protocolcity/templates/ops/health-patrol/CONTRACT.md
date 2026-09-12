# health-patrol — Employment Contract (L2)

Workspace job that patrols ticket health across stores (stale claims,
unlabeled backlog, quiet dependency chains). Renamed from **marshal**
Function name states the job (renamed from marshal with the default-ops consolidation).

## Identity

| Field | Value |
|---|---|
| Board label | **health-patrol** |
| Prior name | `marshal` (alias — seed-ops will not dual-hire) |
| Kind | `job` |
| Assignment | City-wide workspace job |
| Schedule | `0 11,15 * * 1-5` (11:00 + 15:00 Mon–Fri local) |
| Signs as | `health-patrol` on ticket comments only |

## What this job does

- Patrol WorkLane stores for stale claims, unlabeled ready work, and stuck
  dependency chains.
- May release a confirmed ghost claim with a signed comment.
- Never closes others' work; never invents product tickets.

## Never touch

- Product application code outside this workspace's ops papers.
- Human publish / export gates (citizen-present only).
- Live roster pins (capacity is chief-of-staff Mode B only).

## Seed

Auto-seeded by `blueprint seed-ops` as part of the default three-seat set
(chief-of-staff · health-patrol · workspace-efficiency).
