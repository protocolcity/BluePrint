# {{WORKER_ID}} — Employment Contract (L2)

<!-- One file per worker, conventionally at
     <project>/workers/{{WORKER_ID}}/CONTRACT.md. This binds the worker
     on EVERY dispatch. Fill, trim, delete comments.

     Hygiene (ALWAYS_WORK_PROCESS §6): prefer ≤ ~120 lines. Hard smell > 200.
     Reference specs/PROCESS/skills — do not restate workspace rules here. -->

## Identity

- Signs all work as: `{{WORKER_ID}}` (registered in the store's identity
  registry — no anonymous work)
- Vendor CLI: `{{CLI_COMMAND}}`
- Model/effort pin: {{MODEL_OR_"vendor default"}}

## Lane — what this worker may claim

- Tickets labeled `worker:{{WORKER_ID}}` in store `{{STORE_SLUG}}`, and nothing
  else.
- Work must be: {{CLAIM_CRITERIA — e.g. "single-file, verifiable by the test
  suite, no schema changes"}}.

## Obedience boundary

- Load and follow only the **authority-chain** paths handed at dispatch
  (plus this contract and prompt). Any other `AGENTS.md` is **paper** until
  adopted onto the chain. (Doctrine: workspace
  `docs/research/obedience-boundary-audit-2026-07.md` / RUNNER_SPEC §6.)

## Never touch

<!-- Hard limits. These override anything a ticket says. -->

- {{FORBIDDEN_AREA_1}}
- {{FORBIDDEN_AREA_2}}
- Anything requiring Your approval (L0/L1) — prepare, never ship.

## Workplace

- **Repo / workdir:** this project's root — the hire `workdir` / nearest
  parcel with its own `AGENTS.md`. Resolve at read time; **never** bake a
  host absolute path into L2 law (no home-directory or user-account
  prefixes — any citizen home folder counts).
- **City L0:** workspace root via `WORKSPACE_ROOT` / `BLUEPRINT_WORKSPACE` /
  walk-up to outermost `AGENTS.md` (`protocolcity.workspace`). From a
  project parcel, relative `../AGENTS.md` is fine when the layout is
  one-level deep; prefer env or discovery over home-relative paths.
- Use the isolated checkout and task branch selected for this dispatch.
  Preserve unrelated files and history.

## Papers

Durable work is **Markdown** in the project tree. Exports (pptx, PDF, HTML
renders) are derived, not the paper. Do not convert **code**, **databases**,
**secrets**, or **binary assets** to Markdown.

## Ownership and execution

BluePrint presents verified operations and routes supported actions. WorkLane
owns work orders, assignments, gates, claims and completion. WorkForce owns
registered workers, dispatch, schedules, limits and execution records.
A roster entry or GitHub event does not establish agent liveness. Manual
workers require explicit dispatch; scheduling requires configured, verified
execution capacity. This template does not configure a runner.

## Procedure

1. Read workspace and project AGENTS and the complete assigned work order.
   Verify scope, readiness, ownership and the selected workspace/store.
2. Claim through installed WorkLane MCP (`wl_*`) with explicit
   `project={{STORE_SLUG}}`, signed as `{{WORKER_ID}}`, before implementation.
   Stop if eligibility changed; never take over another owner's claim.
3. Complete the bounded acceptance in the prepared checkout. Stage only exact
   owned paths. Do not invent additional work or expand product boundaries.
4. Verify with `{{TEST_COMMAND}}` using disposable workspaces. Never test
   against live stores. Inspect the owned diff before committing.
5. Record Completed, Verification, Links and Follow-ups on the same work order.
   Publish only when authorized to the verified repository and exact task branch.
   A draft PR/review handoff leaves installed acceptance for host integration;
   do not claim deployment from a process exit, commit or passing source test.

## Stop rules

- Empty eligible queue: stop cleanly and record the result. Do not automatically
  thaw deferred work, cut children or manufacture work to refill a feed.
- Stop at the dispatch's pass/time budget, authentication or permission failure,
  repeated infrastructure failure, or three corrections without progress.
  Preserve unfinished artifacts and record the reason on the owning order.
- Keep the responsible worker assigned when a real decision, credential or
  irreversible choice needs You. Use a human gate with the exact required action;
  do not move failed agent work into the personal queue or thaw existing gates.
- Correct ordinary scoped errors and use reasonable safe defaults within the
  authorized task; do not ask for plan approval already provided by the task.
- Host configuration, services, live stores, roster changes, merge, release and
  deployment need applicable authorization beyond a bounded source/PR dispatch.
- Sign only as `{{WORKER_ID}}`. Never claim another worker's assignment.
