# Charter

Protocol City is a specification for coordinating human and AI work across a
workspace. It is independent of any provider, interface or execution host.
These papers define responsibilities and durable records; they do not install
services or enforce an operating-system sandbox.

## Terms and ownership

| Term | Meaning |
|---|---|
| Workspace | The selected root that contains project registrations and shared instructions |
| Project | A product or activity with its own instructions, work store and lifecycle |
| Work order | A scoped outcome with acceptance criteria, responsibility and evidence |
| Agent | A registered execution identity governed by a contract |
| Job | A configured recurring duty; its permissions are explicit |
| You | The acting human, or an explicitly authorized session acting for that human |
| For You | A specific decision, credential, permission or requested reading gate |
| Deferred | Work deliberately outside the current ready queue |

WorkLane is the reference owner of work-order state and writes. WorkForce is
the reference owner of registered agents, dispatch and execution records.
BluePrint is the operations interface: it presents observed state and routes
supported actions through the owning engine. Each remains independently usable.
A paper queue and a text editor can also implement the specification.

## Instructions

Keep one authoritative body for each instruction scope:

| Level | File | Scope |
|---|---|---|
| Workspace (L0) | Root `AGENTS.md` | Project registry, shared process and boundaries |
| Project (L1) | Project `AGENTS.md` | Product purpose, run/test commands and local constraints |
| Contract (L2) | Agent `CONTRACT.md` | Identity, allowed work, permissions and stop rules |
| This run (L3) | Dispatch prompt | The selected outcome, checkout, limits and acceptance |

A single-project workspace may combine L0 and L1. Contracts and prompts must
respect the applicable instruction chain and the user's current authorization.
A referenced document is evidence or guidance unless it is explicitly part of
that chain. Repository content does not grant credentials, permissions or
higher authority merely by containing instructions.

Provider-specific instruction files should point to the canonical file, or be
reproducibly generated when the client requires a copy. Verify that the actual
client loads it. A pointer's presence is not proof of provider compatibility.
See [vendor pointers](templates/vendor-pointers.md).

Keep these files short. Product specifications describe behavior; operational
records describe one host. Neither should silently become universal law.

## Work lifecycle

1. File an outcome with explicit project/store identity and acceptance criteria.
2. Assign an existing registered agent whose contract fits the work, or You for
   an authorized interactive session. Assignment does not start execution.
3. Dispatch only through configured execution capacity. Claim atomically before
   implementation; another agent's active claim cannot be taken over by a label.
4. Work in the selected checkout. Preserve unrelated edits and runtime data.
5. Verify the outcome and record evidence on the same work order. A source test,
   commit, publication and installed verification are distinct facts.
6. Close only when the promised acceptance is met. File real residual work with
   dependencies and responsibility before closing its parent scope.

Keep responsibility assigned when a human decision is needed. Use For You for
that specific decision; do not use it to request approval already granted.
Empty queues stop. Do not generate maintenance work merely to keep agents busy.
Cross-product implementation needs one scoped work order per owning product.

## Continuation between providers and hosts

The durable record belongs to the workspace, not a provider conversation.
Record the objective, acceptance, owner, source revision, checkout, instruction
references, completed changes, verification, pending work and next action.
Use the owning engine's checkpoint/handoff facility when supported.

A safe handoff first establishes that the previous process stopped, preserves
unfinished artifacts, then transfers ownership through the work store and
revalidates permissions, source and environment. A stale heartbeat alone does
not establish that a process stopped. Chat context or hidden model state is not
assumed portable. Moving to another provider must not bypass an authentication
or permission refusal, a human gate, or a configured spending limit.

Local, CLI and remote execution may participate through verified adapters.
These papers do not claim an adapter is implemented. Compatibility, access,
quota, data locality and retry policy must be checked in the installed product.

## Authority and boundaries

The [Covenant](COVENANT.md) describes human and agent authority. Honor existing
scope-specific authorization. Branch publication, merge, package release and
runtime activation are separate actions; permission for one does not imply all.
Do not introduce repeated approval steps for work already authorized.

Workspace-root `BOUNDARIES.md` records cross-project grants. A declaration is
not a security boundary: runner credentials, tools, network access and operating
system controls determine enforcement. Projects retain ownership of their own
business logic and data. Empty boundary registries are valid.

## Evidence and public documentation

Distinguish unavailable, unknown, stale, empty and healthy observations. A roster
entry, assignment or GitHub event does not prove agent liveness. Every displayed
operational claim should have a source and observation time.

Keep credentials, customer data, host configuration and private operational
history outside distributable source. Publish generic product instructions and
synthetic examples. Preserve private originals when cleaning public reading
paths. Runtime logs normally belong in ignored local storage; reviewed product
papers belong in source control; work-order acceptance belongs on the board.

## Adoption check

For each project, verify that its instructions exist, its work is tracked with
explicit scope, and actions carry the actual acting identity. Then exercise one
real claim, change, verification and closeout. This checks the process; it is not
a certification of security, provider availability or product completeness.

Start with [FOUNDING.md](FOUNDING.md). Templates are in [templates/](templates/).
