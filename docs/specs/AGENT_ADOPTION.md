# Agent adoption — the standard seat set per project

Status: product rule. Companion to [AGENTS_INTENT.md](AGENTS_INTENT.md) (how
seats are shown), [STATES_AND_TERMS.md](STATES_AND_TERMS.md) section 2 (seat,
job, shift, pass) and [SUITE_VOCABULARY.md](SUITE_VOCABULARY.md).

## Why this exists

Seats hired one at a time follow history, not the project. A new workspace
needs a named, generated set: which seats a project has, which jobs the
workspace shares, and how the desk reports what is missing. Cloud sessions
(Cursor / Claude / Grok on GitHub) are evidence, never seats.

## Decision D12: the standard seat set

A project is fully staffed when it has, **for each provider present on the
host**, one bounded implementation seat scoped to that project, and the
workspace has, for each provider, one review job and one supervisor job
shared by all projects.

| Row | Kind | Per | Name | Claims | Scope | Budget |
|---|---|---|---|---|---|---|
| Implementer | seat | project × provider | `<prefix>-<provider>-implementer` | yes, `worker:<name>` on that project's store | the project folder only; its own worker-config folder; the workspace AGENTS chain | 1800 s, one pass, turn cap |
| Reviewer | job | provider | `<provider>-reviewer` | never | read-only, no tools, one turn | 240 s |
| Supervisor | job | workspace | `bp-supervisor` | never | roster scope list; stop file | 2100 s |
| Reports | job | workspace | chief-of-staff, health-patrol, workspace-efficiency | never | read-only | 120 s |

Providers, in the order the desk lists them: **Claude** (`claude`),
**Cursor** (`cursor-agent`), **Grok** (`grok`), **Codex** (`codex`). Pins
come from host capacity policy. A provider that is installed but disabled
(credits, cost) is still hired and marked **held** in the roster, so the
desk shows it as OFF rather than missing.

Cloud sessions are **not** part of the standard set. They appear only
through the evidence they leave (Delivery, Work). See STATES_AND_TERMS
(cloud sessions are evidence, never seats).

## Decision D13: one seat shape, generated, never copied

`workforce hire` (and `blueprint adopt`, which calls it) generates the whole
seat from a provider adapter and the project: `runner.json` (provider command
with the pin, `--max-turns`, the project's repository and expected remote,
prompt and contract paths), `launch.py`, `mcp.json` (WorkLane MCP signed as
the seat), `CONTRACT.md` and `prompt.md` from the project template, and the
roster row with `model`, `scope_home`, `perimeter_grants`, `authority_chain`
and `queue_url` all pointing at the generated folder. No permission-bypass
flag anywhere by default; each adapter uses its provider's non-interactive
mode with an explicit tool allow list. The seat is dry-run dispatched once
at hire time and the receipt is kept.

## Decision D14: instructions and scopes

- **Instructions** come from three layers, read in order at dispatch:
  workspace AGENTS.md, the project's AGENTS.md, the seat's CONTRACT.md. The
  prompt names the order, the checkout, the branch, the test commands and
  the parking rule; nothing else. The contract is the same text for every
  implementer of a project; only identity and provider differ.
- **Scope** is the project folder for implementers (perimeter grant = that
  folder plus the seat's worker-config folder), read-only everywhere for
  reviewers, the roster scope list for the supervisor. A seat never touches
  another product, host configuration, credentials, rosters or runtime data;
  the person publishes, reviews, merges and installs.
- **Recovery** instructions reach the seat through the prompt and as a
  comment on the order.

## Decision D15: the desk tells you what is missing

Agents (AGENTS_INTENT) gains one line per project under the Seats group:
"BluePrint: Claude, Cursor · missing Grok, Codex" computed from the roster
against the providers detected on the host, with a Hire action that runs the
generated hire. A provider that is not installed reads NOT CONFIGURED with
the install hint; a held one reads OFF.

## Apply on a workspace

1. Refresh the engine model registry and ship a capacity policy template
   with current pins (WorkForce).
2. Make `hire` generate the D13 shape from adapters for the installed
   providers (WorkForce).
3. Re-generate existing seats from the adapters, keeping identities, then
   hire the missing ones for registered projects that have open work.
   Personal or idle folders get seats only when work is filed for them
   (empty queues stop cleanly).
4. Keep one review job per provider plus the supervisor; supervisor scope
   becomes the roster's seats list.
5. Adoption plants the set for a new project; `blueprint doctor` reports
   drift from the set.

## Is / Is-not

| IS | IS NOT |
|---|---|
| One generated seat shape per provider, identical contracts per project | Hand-copied folders, per-seat prompt drift |
| Coverage stated per project on the desk | Guessing from the roster file |
| Providers detected, missing ones named | A hard-coded four |
| Hire generated from adapters | A coordinator working around a permission denial |
| Cloud sessions as evidence | Cloud rows on the roster |
