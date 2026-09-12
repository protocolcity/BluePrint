---
name: workspace-efficiency
description: Inspect workspace queues, registered execution capacity, routing gaps and process drift, and report evidence. Use for efficiency passes, queue validation and configured reporting jobs.
---

# Workspace efficiency

Read the selected workspace's AGENTS and current operating process, then the
job contract if dispatched. This skill supplies inspection and reporting;
it does not authorize store, roster, service or product changes.

BluePrint presents operations. WorkLane owns work orders, assignments, gates
and claims. WorkForce owns agent execution and the roster. A schedule, CLI on
PATH, GitHub event or roster entry alone does not prove an agent is running.
Manual seats require explicit dispatch. A fresh template installs no capacity.

## Preflight

- Resolve the explicitly selected workspace and its registered projects. Use
  that workspace's configured engine connections; never substitute a fixed
  port or another workspace when a source is unavailable.
- Pass `project=` on every WorkLane call. `project=all` is for cross-project
  reads only. Verify owning project and store identity before authorized writes.
- Read actual registered seats and their contracts, dispatch mode, limits and
  recent execution records. Report unavailable, stale, empty and healthy
  sources separately, with observation times.
- When available, inspect local discovery with
  `bash scripts/skills_sync.sh --check` and run read-only audit helpers:
  `python3 scripts/open_work_audit.py --feeds --history --process --decay --stuck`.
  Check the helper's supported options and selected workspace first. Do not
  invoke repair, `--live` or `--nudge` as part of an inspection. If helpers are
  absent, use installed WorkLane/WorkForce read tools and state the limitation.

## Inspection

1. Compare open, ready and in-progress counts per project and worker. Report
   missing routing, retired seats and ready work outside the assigned seat's
   scope. `worker:you` with `you:host` is authorized host work; personal kinds
   and human gates are intentional. Do not assume every You assignment is a gap.
2. Compare each registered seat's feed to the observed execution record and
   configured dispatch mode. Check contract/prompt paths and queue project/label
   selection. Ready work on a manual seat is not a missed scheduled fire.
3. Empty eligible feeds stop cleanly. Deferred, tracking and timer-gated work
   remains outside readiness. Report existing scope and gates; do not auto-thaw,
   refill queues, create maintenance children or propose new goals to keep
   agents busy. A large deferred pile alone is not a process failure.
4. Inspect provider errors and repeated capacity failures in WorkForce records.
   Report recurrence within a blocked window. Missing heartbeat evidence is
   unknown liveness; a quiet work order is Watch, not proof of a dead agent.
5. Check skills discovery, missing contract/prompt paths, retired assignments
   and differences between written process and demonstrated execution. Report
   missing enforcement without treating historical process sections as law.
6. Inspect deferred epics with no open children. Distinguish children never
   filed from children completed; neither automatically authorizes decomposition,
   cancellation or closing the parent. Compare remaining acceptance explicitly.
7. Inspect recent closeouts (normally seven days) that still request host/You
   verification. Record the quoted residual action and any later confirmation;
   passing source tests do not establish installed acceptance.
8. Collect short physical or browser actions already requested in gate notes
   into one report table. Preserve gates and ownership; a report is not permission
   to close, cancel or clear them. Report stalled claims without taking them over.

## Actions and report

Default to a dated local report or an ad-hoc chat summary. Do not create inbox
cards merely because feeds are empty. If explicitly authorized to route or
file findings, use an actual registered seat within its contract, one work
order per owning project, and existing orders when they cover the finding.
Keep the worker assigned on real human blockers; For You is a decision,
credential, publication or requested-reading gate, not plan approval.
Never mass-close, mass-cancel or silently clear deferred/timer/human gates.

For a configured reporting job, write under the selected workspace:
`.protocolcity/ops/reports/workspace-efficiency/YYYY-MM-DD.md`.
Append another timed pass to an existing daily report. Include:

- Observed time, selected workspace, source status and inspection limitations.
- Per-project open/ready/in-progress counts and per-seat feed/execution evidence.
- Routing and queue configuration findings, preserving intentional You work.
- Deferred/tracking scope, provider failures and process/discovery drift.
- Zero-child epics, residual installed checks, short requested You actions,
  and stalled claims, with project and order IDs.
- Actions actually authorized and taken, unresolved findings and existing links.

Finish with a concise console summary for the execution record, then stop.
The report does not establish unattended implementation or installed acceptance.
