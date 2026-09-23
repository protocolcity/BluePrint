# Configure agents for a project

Status: current product contract. See [the product definition](../PRODUCT.md)
and [architecture](../../ARCHITECTURE.md) for component ownership.

A worker is a registered execution identity with project scope, a contract,
provider/model configuration, tools, host, trigger and budget. A provider being
installed does not mean every project needs a seat for it. Register capacity
that matches actual work; do not manufacture agents or tasks to fill a roster.

WorkForce's provider adapters support generated seats for Codex, Claude, Cursor
and Grok. Use the installed `workforce hire --help` and dry-run path; generation
and model availability are version-dependent. A generated folder or successful
dry run is configuration evidence, not authenticated execution.

## Instructions and authority

Read workspace AGENTS.md, project AGENTS.md, the registered worker CONTRACT.md,
then the scoped work order and dispatch prompt. Provider discovery files are
thin pointers. Skills supply relevant capabilities; they do not grant broader
scope or replace current authorization.

Implementers claim under their own identity before editing. Review/supervision
jobs have their own contracts and must not imply an implementation claim.
Publication, integration and deployment follow the workspace's applicable
authority. No provider-specific blanket policy overrides an authorized task.

## Qualification

Verify exact model, authenticated account, allowed tools, execution host,
project/store identity and budget. Record dated evidence from a bounded task:
claim, edit, test, artifact/revision and review handoff. Provider selection should
use observed task fit and capacity, not a permanent vendor ranking. Unknown quota
remains unknown. Permission or authentication failure is not permission to find
a less restricted executor.

## Continuation and cloud boundary

The work record can outlive a provider session. A supported handoff preserves a
checkpoint and artifacts, verifies that the previous writer stopped, transfers
ownership through WorkLane and validates context before the next executor claims.
Native provider session continuation and execution on another host are distinct.

Current BP dispatch is local-only. Remote/cloud execution is a future extension
requiring an explicitly configured runtime and equivalent scope/evidence checks;
it is not permanently forbidden and is not currently implemented. Repository
activity and provider session URLs remain observations, not remote-agent health.

## Display

Agents distinguishes configured, unavailable, held, running, stopped and unknown
states only when supported by source evidence. Explain a missing capability or
refusal precisely. Do not infer a missing required seat just because a vendor CLI
is present. See [states and terms](STATES_AND_TERMS.md).
