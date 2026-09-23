# Provider qualification and routing

This is the product direction for capability-based routing. The installed
WorkForce version determines which checks and routing operations are available.
See [the product contract](../PRODUCT.md) and [execution workflow](../operations/WORKFLOW.md).

## Distinct identities

A provider supplies inference; a model identifies the selected inference
capability; a runner supplies the tools; a seat grants project authority; an
execution host supplies the checkout and processes. Account limits can be shared
by several seats. Installing a CLI proves none of authentication, quota or
successful execution.

Qualification records the provider, exact observed model, runner version, host,
allowed tools, project scope, result, observation time and expiry. Record unknown
quota as unknown. A denied credential, timeout, exhausted account and malformed
response are separate outcomes. Keep credentials outside qualification receipts.

## Routing policy

1. Resolve the project, work kind, scope, risk and acceptance criteria.
2. Preserve an existing valid claim. Exclude workers lacking required tools,
   language/domain capability, host access or permission for the action.
3. Require fresh applicable qualification and respect provider/account backoff,
   host concurrency and the configured time/cost budget.
4. Rank eligible workers by measured acceptance, verification quality, latency
   and cost for comparable work. A model's marketing tier is not a benchmark.
5. Record the selected registered worker, model and reason. When none fits,
   retain the order and explain the missing capability.

| Work kind | Evidence useful for selection |
|---|---|
| Design | Clear scope, coherent decisions, fidelity to product constraints |
| Implementation | Passing behavioral tests, correct boundaries, review findings |
| Review | Reproducible defects, useful coverage, low false-positive rate |
| Supervision | Correct readiness, bounded dispatch and recovery decisions |
| Reporting | Deterministic source reads, accurate failure and freshness states |

Codex, Claude, Cursor and Grok can all be eligible when their configured adapters
meet the same requirements. There is no universal vendor ranking. Start with a
bounded trial; change preferences from observed results. Reporting work that
requires no model should remain deterministic.

## Continuation

A quota stop does not complete or duplicate a work order. Preserve source,
artifacts, decisions, checks and next action. Verify the previous writer stopped,
then transfer ownership through the installed WorkLane continuation contract.
The next runner validates workspace, instructions, revision and artifact hashes
before acting. Native chat-session resume is optional provider-specific state;
it is not the portable checkpoint.

Local CLI execution may call a hosted model. Remote/cloud tools require a tested
adapter with explicit host identity, transport, scope, authentication and result
delivery. Current local-dispatch safeguards remain until that adapter exists.
Opening a project or registering a provider does not automatically hire workers.
