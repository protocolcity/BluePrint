# Work-order operating process

This is the operating contract. A workspace follows it only where a configured runner has demonstrated the required behavior; this document does not establish installed capacity. Read the selected workspace's AGENTS.md, its current operating inventory, and the owning project's AGENTS.md before changing work.

## Ownership and evidence

You and an entry AI capture intent. WorkLane owns work orders, gates, claims and history. WorkForce owns registered workers, dispatch, limits and execution records. Project repositories own implementation. GitHub supplies collaboration and delivery evidence. Deployment receipts and observed behavior establish what is running. BluePrint presents these sources and routes supported actions through their owning engine.

A configured CLI is not authenticated capacity. A roster entry is not a running agent. A process start or queue candidate is not a signed WorkLane claim. A GitHub event is not a heartbeat. A merged change is not an installed UI fix.

## The operating loop

1. Read the existing work order or file one with the problem, owning project, allowed paths, acceptance criteria and verification. Pass explicit `project=` on every WorkLane call. Cross-product changes need one work order per owning product.
2. Discover the actual registered worker and its contract, queue and permissions. Route only work it can perform. Historical names and labels do not prove a worker exists. An authorized host session implementing now uses `worker:you` plus `you:host`; it is not unattended coverage.
3. Verify provider authentication and the execution host. Dispatch only within the contract's trigger, scope and budget. Manual workers require explicit dispatch. Keep human, hardware and independent business-runtime work outside an implementation worker's automatic queue.
4. The worker claims one ready work order under its dedicated identity, works in an isolated checkout, preserves unrelated changes, implements and verifies the outcome. It records blockers and evidence on that same work order.
5. Publish only to the reviewed destination under applicable workspace authorization. Merge, package release and deployment have distinct evidence and permission requirements. Do not expose private history or runtime data.
6. Verify the running build when acceptance concerns an installed surface. Close with Completed, Verification, Links and Follow-ups. Use real revisions and observed results. Leave unfinished acceptance open or explicitly represented by linked children.
7. A worker configured to drain returns to its own ready feed until empty, gated, budget-limited or faulted. A bounded trial or PR-stage worker may have a narrower exit contract. Empty queues stop; do not manufacture maintenance work or silently thaw unrelated deferred work.

## Gates and routing

Keep agent assignment when a genuine human decision or credential is needed. Use a human gate only when You must act; describe the exact action. Use deferred for intentionally parked work and tracking for structural umbrellas. Neither means the work is ready. A timer is an embargo, not a reminder to fabricate activity.

Do not bulk close or cancel to improve counts. Assess work orders individually against their acceptance criteria, current source, delivery and runtime evidence. Separate obsolete implementation instructions from still-valid user outcomes. A changed architecture alone does not prove the original outcome is complete.

Failures remain visible. Do not move failed agent work into a personal queue or claim an automatic result from a deterministic report. Repeated authentication, permission or verification failures stop the run with a durable reason.

## Session intake and closeout

A useful intake states: Project; Slice; In scope; Out of scope; Risk; Done when; Verify. This can live in the work-order description rather than a second planning system.

Closeout states what changed, how it was verified, the actual commit/PR/deployment where relevant, and any remaining linked work. An approval request must concern a real unresolved decision, not reconfirm an already authorized plan. Preserve customer, money, hardware, secrets and publication boundaries from the owning project.

## Reference

- [Operations interface and engine ownership](OPERATIONS_EVOLUTION_2026_09.md)
- [Build, activate and recover](../operations/DEPLOYMENT.md)
- [Runner, provider and evidence flow](../operations/WORKFLOW.md)

This current process replaces the earlier Map-only interface, standing-chew, named-seat and unconditional unattended-work descriptions. Earlier revisions remain in repository history; they are not current execution evidence.

## Human attention and three clocks

The current interface separates Decide (human action), Read (requested reports), Watch (timers or no recent work update), and Due (dated personal reminders/deadlines that have arrived). Watch is a prompt to inspect evidence, not proof that an agent is dead. Deferred/tracking work remains outside the active inbox. Human gates preserve the responsible worker.

Browser-local “Mute here for 24 hours” hides an inbox item only in that browser and workspace; WorkLane gates, assignments and readiness are unchanged. A `gate_type=timer` is an execution embargo. A `reminder:YYYY-MM-DD` label is a calendar date without an embargo: the reader sets/removes it through WorkLane and Calendar/ICS projects it. It does not send an outside notification. These are three separate clocks; do not clear a gate to snooze an item or gate work merely to create a reminder.
