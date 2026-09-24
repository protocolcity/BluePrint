# BluePrint product contract

BluePrint helps a person coordinate work across projects and AI providers. Its
primary unit is a durable work order with an objective, scope, instructions,
owner, decisions, artifacts, verification and next action. A provider session
is an execution context attached to that work, not its sole system of record.

## Ownership

| Component | Owns |
|---|---|
| BluePrint | Workspace presentation, navigation, source freshness and supported engine actions |
| WorkLane | Project work records, gates, claims, history and completion evidence |
| WorkForce | Registered executors, provider adapters, dispatch, budgets and run evidence |
| Project | Its source, business logic, data and applicable instructions |
| Person | Intent and decisions requiring human authority |

No component acquires another project's authority through a label or a provider
switch. GitHub supplies delivery evidence, not process liveness. BP does not
start engines or invent capacity merely by opening the interface.

## Experience

Overview prioritizes attention; Work carries the detailed work journey;
Projects provides scope and papers; Agents explains execution; Delivery and
Timeline show source-labelled evidence. Calendar separates schedules, dates and
embargoes. Connections explains source status; Settings explains display
preferences and build identity. Map navigates the same workspace.

Keep the shared dark visual tokens, readable density, keyboard navigation and
honest empty/error states. A status must have a source and observation time.
Preserve the person's project/filter/reader context through actions and errors.
Navigation and supported actions are specified in
[the operations interface](specs/OPERATIONS_EVOLUTION_2026_09.md).

## Capabilities

| Capability | Current contract |
|---|---|
| Selected-workspace records, display-only from WorkLane | Implemented; Work list and reader show status/priority/assignment/gate without in-page write controls — people and chat AIs file and manage work through WorkLane (`wl`) |
| Configured local agent dispatch | Implemented through WorkForce; registration does not establish authentication or quota |
| Codex, Claude, Cursor, Grok | Configurable provider adapters; qualify exact model, tools and host access before execution |
| GitHub delivery evidence | Observational; never agent liveness |
| Durable work checkpoint and provider handoff | Engine-version-dependent; verify the installed continuation contract. No universal automatic fallback is claimed |
| Native session resume | Provider-specific; separate from continuing a work order |
| Remote/cloud execution or moving a run between hosts | Extension direction; not supported by the present local dispatch path |

Cloud execution is not permanently excluded from the product. A future adapter
must provide explicit execution-host identity, credentials, scope, stopped-writer
and claim-transfer safeguards, failure states and fresh evidence before it can
be exposed as a supported action. Current local checks remain in force.

## Quality and documentation

Current instructions describe observed or tested behavior. Proposals and dated
design studies do not become execution authority by being linked from a page.
Workspace authorization, project rules, worker contracts and a scoped work order
form the execution chain; this document supplies the product definition.

Public source and packages contain reusable product material. Host rosters,
credentials, customer data and operational histories stay outside them. Tests
use synthetic workspaces and fake providers; live provider qualification is a
separate bounded activity. Source tests, installed-package checks, browser
journeys and diagnostics each supply different evidence. None proves that all
bugs are absent.
