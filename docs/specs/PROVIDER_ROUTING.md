# Provider registry and capability routing — design record

Status: design record for pc-1503, 2026-09-16. Written, not running: no hire,
no routing code and no roster change ships with this record. Companion to
[AGENT_ADOPTION.md](AGENT_ADOPTION.md) (D12's standard seat set, which this
record narrows rather than replaces), the Capability-based routing and
Supervisory contract sections of
[../operations/WORKFLOW.md](../operations/WORKFLOW.md), the workspace's
`docs/REMOTE_OPERATIONS.md` (current state: "model/capability routing...
still require implementation and acceptance" — outside this product's own
repository, cited for context only),
[STATES_AND_TERMS.md](STATES_AND_TERMS.md) section 2 (seat, job, shift, pass)
and wf-258 (cloud sessions stay evidence-only, option A, 2026-09-14).

## Why this exists

D12 hires one implementer seat per project × installed provider, so a
five-provider host ends up with five near-identical clone seats per project
running the same generic contract. That maximizes coverage, not capability:
it treats every provider as interchangeable inference behind an identical
prompt, when in practice providers differ in installed tools, context
window, cost, quota, and what they are actually good at (planning versus
mechanical edits versus fast narrow review). Industry practice — Continue's
named roles, Aider's architect/editor split, Anthropic's Haiku/Sonnet/Opus
tiers, model-orchestrator style routing tables, Cursor/Codex cloud used for
overflow — is to register capability once and route by the shape of the
work, not to stand up an identical worker per vendor. This record proposes
the registry and the routing table; it does not change who is hired or how
work is dispatched today.

## Provider as its own object

Today a provider is implicit: a name in D12's fixed list (`claude`,
`cursor-agent`, `grok`, `codex`) used only to generate one more identical
seat folder. This record promotes it to a registered object the desk and a
future router can read directly, independent of any one project:

| Field | Meaning | Source |
|---|---|---|
| `id` | provider key (`claude`, `cursor-agent`, `grok`, `codex`) | fixed list, D12 order |
| `install` | detected on this host or not | host capacity policy (existing detection D12 already performs for "missing Grok, Codex") |
| `mode` | `local-cli` (calls a hosted model from this host) or `cloud` (remote session/bot) | WORKFLOW.md "Provider, runner and host": local CLI vs. remote execution host |
| `models` | model ids available through this provider, with a `pin` per host capacity policy | existing pin mechanism (D12: "Pins come from host capacity policy") |
| `tools` | the tool/file access the adapter grants in non-interactive mode | D13 adapter output (`runner.json` tool allow list) |
| `quota_state` | `available` / `held` (installed but disabled) / `unavailable` | D12's existing held/OFF distinction, D15's NOT CONFIGURED |
| `strengths` | declared work kinds this provider is registered for (below) | this record, set by the operator, not inferred from output |

A provider is a fact about the host and the account, not a claim about
liveness: `install`, `mode` and `quota_state` are exactly what D12/D15
already detect and show on the desk (installed/missing/held/NOT
CONFIGURED). This record adds no new detection mechanism — it names the
existing fields as one object so a router can read them without re-deriving
the D12/D15 logic.

## Work kinds

A work order already carries enough shape to classify without new inference:
its product/store, its labels, and words already used elsewhere in this
family of records (design, implementation, review, supervision). This
record fixes five kinds, matched against what D12 already distinguishes
(implementer seat vs. reviewer job vs. supervisor job) plus a split D12
does not make (planning/design work versus mechanical edits):

| Kind | Shape of the work | Example |
|---|---|---|
| `design` | write a design record or decision; no source edit | this ticket, AGENT_ADOPTION.md itself |
| `implement` | bounded source change against acceptance criteria, one checkout, one PR | a D12 implementer seat's normal order |
| `review` | read-only audit of a diff or a claim, one turn, no writes | a D12 reviewer job |
| `supervise` | reconcile WorkLane/WorkForce/repository state, dispatch or recover through owning-engine controls only | `bp-supervisor` |
| `report` | scheduled deterministic health/status read, no reasoning, no dispatch | chief-of-staff, health-patrol, workspace-efficiency |

`review`, `supervise` and `report` map one-to-one onto D12's existing job
rows; they need no new registration, only the label. `design` and
`implement` both currently route to the same D12 implementer seat shape;
this record is the first place that tells them apart, because a design
record needs a provider good at holding wide context and reasoning about
tradeoffs, while a mechanical edit against a stated acceptance list does
not.

## Default routing table

A route selects a work kind and a provider preference order, not a specific
model version (pins stay in host capacity policy per D12). This is a
*default*, applied only when the work order does not already carry a
compatible claimed seat and only after D12's existing constraint check
(language/domain, repository access, tools, writes, host, review/deployment
rights, time, capacity — WORKFLOW.md "Capability-based routing") passes:

| Work kind | Preferred provider order | Why |
|---|---|---|
| `design` | Claude → Codex → Cursor | longest context / strongest unaided reasoning on the installed set; Cursor's strength is editor-integrated mechanical edits, not standalone prose |
| `implement` | project's existing registered seat provider (D12), no change | D12 already scopes one seat per project × provider; this record does not reassign standing implementer claims |
| `review` | Grok → Cursor → Claude | fast, narrow, read-only turns (WORKFLOW.md's qualification notes: Grok's narrow review completed in seconds under low reasoning effort) |
| `supervise` | fixed to `bp-supervisor` | D12/STATES_AND_TERMS already name this as the one workspace-scoped job; not a routed choice |
| `report` | fixed to the three named jobs | same: not a routed choice, already registered |

If the preferred provider for `design` or `review` is `held` or NOT
CONFIGURED, the next provider in order is used; if none in the list is
available, the order stays with its current owner and exposes a routing
exception per WORKFLOW.md ("retain the project and expose a routing
exception with a reason; do not assign a provider name as a fictional
worker"). This table is a default, not a lock: the same section already
lets an operator record a different chosen worker and reason directly on
the order.

## What stays a project-scoped seat versus what is a provider

- **Provider** (this record): a registered fact about installed inference —
  what models, what tools, what quota. Provider-level information is
  workspace-wide, not project-scoped, because the same Claude/Cursor/Grok/
  Codex account is available to every project on this host.
- **Seat** (D12, unchanged): the *authority* to claim and act on a specific
  project's work under a signed identity — project folder scope, its own
  worker-config, `worker:<name>` claim rights on that store. A seat is
  always project × provider, generated by D13, instructed by D14. This
  record does not remove, rename or merge seats; it adds one more input
  (work kind) to which already-registered seat a `design` order should
  prefer when a project has more than one implementer.
- Routing chooses **which registered seat** (or job) handles an order; it
  never grants a provider authority to claim outside a project it already
  has a seat in, and it never substitutes a provider name for a seat
  identity on a claim (WORKFLOW.md: "do not assign a provider name as a
  fictional worker").

## Cloud remains evidence/overflow

Per wf-258 (founder decision, option A, 2026-09-14): cloud sessions (Cursor
cloud agents on GitHub, Claude cloud sessions, Grok Bot) are not providers
in this registry's `install`/`mode: local-cli` sense and are not routing
targets. They stay visible only as evidence — GitHub delivery by author, or
WorkLane claims a cloud session signs under its own identity — exactly as
wf-258 closed it. If wf-258 is reopened and option B (cloud seats) is
chosen, cloud providers would enter this registry with `mode: cloud` and
their own adapter, budget model and "remote, unverified" badge as that
ticket's own follow-on design record specifies; this record does not do
that work and does not assume the reopening.

## Empty projects stay unstaffed

This record changes nothing about D12 Apply-on-a-workspace step 3: personal
or idle folders get seats only when work is filed for them, and empty
queues stop cleanly. A provider being registered in this record's registry
does not hire anything by itself; hiring still follows D13's generated
shape, still requires open work, and still requires the same explicit hire
action D15 already exposes.

## Is / is-not versus D12

| IS | IS NOT |
|---|---|
| A registry that names what D12/D15 already detect (installed, held, tools, pins) as one addressable object | A new detection mechanism or a new liveness signal |
| A default routing table by work kind, applied only when no compatible claim already exists | A replacement for D12's one-seat-per-project-×-provider standard, or a reason to stop hiring per-provider implementer seats |
| `design` split out from `implement` as a distinct kind with its own default preference | A claim that any provider is categorically "better"; the table is a starting default an operator can override per order |
| Cloud sessions still evidence-only, unchanged from wf-258 | A reopening of wf-258 or a cloud adapter |
| Written record only, no roster or engine change | A hire, a routing code change, or a mass re-staffing of existing projects |

## Out of scope this order

Supervisor routing code, the Connections UI, Grok Bot teammates, and
POS/tradeOS seats are not addressed here. Engine implementation — reading
this registry from a router, adding `work_kind` as an order field, teaching
`bp-supervisor` the default table — is later workforce/engine child work
filed only after founder ratify.

## Gate

Park for founder ratify (human gate) before any engine child order is
filed against this record.
