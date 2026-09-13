# Agent adoption — the standard seat set per project

Status: design record, 2026-09-13, from the founder's observation during the BP design pass: "all agents need a reset or a pass to ensure we can use them all; per project we need x y z agents; ensure they have the right instructions and the right scopes to get the most out of all the AI providers plus the cloud agents, for every provider a BP user may have." Companion to [AGENTS_INTENT.md](AGENTS_INTENT.md) (how seats are shown), [STATES_AND_TERMS.md](STATES_AND_TERMS.md) section 2 (seat, job, shift, pass) and [SUITE_VOCABULARY.md](SUITE_VOCABULARY.md).

## What exists (this host, 2026-09-13)

| Fact | Evidence |
|---|---|
| Four provider CLIs installed: Claude (`claude`), Cursor (`cursor-agent`), Grok Build (`grok`), Codex (`codex`) | `command -v` on the host |
| 14 roster rows, grown by hand over three months: 7 seats (2 BluePrint, 2 WorkForce, 2 POS, 1 demo), 4 reviewer/supervisor jobs, 3 report jobs | `.protocolcity/workforce/local/roster.json` |
| Implementation seats exist only for Claude and Cursor; Grok is a reviewer and the supervisor's proposal provider only; the Codex seat is parked on a credit instruction | roster commands; `local/worker-config/*` |
| WorkLane, comms, career, connector, gridfinity, presentations, recipes, socials, tradeOS have no implementation seat at all | roster queue URLs |
| `blueprint adopt` / `found --project` plant one `demo-worker` stub per project and know nothing about providers | `protocolcity/adopt.py`, `found.py` |
| `workforce hire` plants a template contract and prompt and a roster command whose default carries `--dangerously-skip-permissions` | `workforce/hire.py` line 123 |
| The engine's canonical model list is stale (sonnet-4-6, grok-4.5, cursor-grok-4.5-low, haiku) and no capacity policy file exists on this host, so `hire --model` rejects current pins (composer-2.5, grok-4.6, claude-sonnet-5) | `hire.py` CANONICAL_MODEL_IDS; `local/capacity_policy.json` missing |
| Every working seat on this host was made by copying a folder and editing five files by hand (runner.json, launch.py, mcp.json, CONTRACT.md, prompt.md) and then repairing the roster row (scope_home, perimeter, authority chain, queue URL) | this session's evidence under `local/reports/parallel-plan-pass` |
| The coordinator's own permission classifier refuses to create or register seats ("Create Unsafe Agents"); the founder runs the hire step by hand | session record |

## Why it reads wrong

Seats were hired one at a time when a task needed them, so coverage follows history, not the projects. The permission-bypass default in the hire template makes every hire look unsafe, which is exactly what the classifier objects to. The roster cannot say which provider a seat runs (`model` is blank on 11 of 14 rows) because the truth sits in a runner file the roster does not read. Nothing tells a new BP user, or this host, what a fully staffed project looks like.

## Decision D12: the standard seat set

A project is fully staffed when it has, **for each provider present on the host**, one bounded implementation seat scoped to that project, and the workspace has, for each provider, one review job and one supervisor job shared by all projects.

| Row | Kind | Per | Name | Claims | Scope | Budget |
|---|---|---|---|---|---|---|
| Implementer | seat | project x provider | `<prefix>-<provider>-implementer` | yes, `worker:<name>` on that project's store | the project folder only; its own worker-config folder; the workspace AGENTS chain | 1800 s, one pass, turn cap |
| Reviewer | job | provider | `<provider>-reviewer` | never | read-only, no tools, one turn | 240 s |
| Supervisor | job | workspace | `bp-supervisor` | never | roster scope list; stop file | 2100 s |
| Reports | job | workspace | chief-of-staff, health-patrol, workspace-efficiency | never | read-only | 120 s |

Providers, in the order the desk lists them: **Claude** (`claude`, pin `claude-sonnet-5`), **Cursor** (`cursor-agent`, pin `composer-2.5`), **Grok** (`grok`, pin `grok-4.6`), **Codex** (`codex`, pin per host policy). A provider that is installed but disabled by the founder (credits, cost) is still hired and marked **held** in the roster, so the desk shows it as OFF rather than missing.

Cloud sessions (Cursor cloud agents on GitHub, Claude cloud, Grok Bot) are **not** part of the standard set until [wf-258](../../../workforce) is decided; they appear only through the evidence they leave (Delivery, Work).

## Decision D13: one seat shape, generated, never copied

`workforce hire` (and `blueprint adopt`, which calls it) generates the whole seat from a provider adapter and the project: `runner.json` (provider command with the pin, `--max-turns`, the project's repository and expected remote, prompt and contract paths), `launch.py` (the thin launcher that strips `--config` and forwards recovery flags), `mcp.json` (WorkLane MCP signed as the seat, `WORKLANE_COMMENT_TRANSITIONS=0`), `CONTRACT.md` and `prompt.md` from the project template with the project's test commands filled in, and the roster row with `model`, `scope_home`, `perimeter_grants`, `authority_chain` and `queue_url` all pointing at the generated folder. No permission-bypass flag anywhere by default; each adapter uses its provider's non-interactive mode with an explicit tool allow list. The seat is dry-run dispatched once at hire time and the receipt is kept.

## Decision D14: instructions and scopes

- **Instructions** come from three layers, read in order at dispatch: workspace AGENTS.md, the project's AGENTS.md, the seat's CONTRACT.md. The prompt names the order, the checkout, the branch, the test commands and the parking rule; nothing else. The contract is the same text for every implementer of a project; only identity and provider differ.
- **Scope** is the project folder for implementers (perimeter grant = that folder plus the seat's worker-config folder), read-only everywhere for reviewers, the roster scope list for the supervisor. A seat never touches another product, host configuration, credentials, rosters or runtime data; the host publishes, reviews, merges and installs.
- **Recovery** instructions reach the seat through the prompt (wf-257) and as a comment on the order.

## Decision D15: the desk tells you what is missing

Agents (AGENTS_INTENT) gains one line per project under the Seats group: "BluePrint: Claude, Cursor · missing Grok, Codex" computed from the roster against the providers detected on the host, with a "Hire" action that runs the generated hire (host-run while the coordinator's classifier refuses it). A provider that is not installed reads NOT CONFIGURED with the install hint; a held one reads OFF.

## Apply to this host (the reset pass)

1. Refresh the engine model registry and ship a capacity policy template with current pins (WorkForce).
2. Make `hire` generate the D13 shape from adapters for the four providers (WorkForce).
3. Re-generate the existing seven seats from the adapters, keeping identities, then hire the missing ones: BluePrint Cursor and Grok (Codex held), WorkForce Grok, WorkLane Claude/Cursor/Grok, POS Grok (POS stays deferred for dispatch but staffed). tradeOS and the personal projects get seats only when work is filed for them (empty queues stop cleanly).
4. Add the Grok review job's implementer twin and keep the three reviewer jobs; supervisor scope becomes the roster's seats list.
5. Adoption plants the set for a new project; `blueprint doctor` reports drift from the set.

## Is / Is-not

| IS | IS NOT |
|---|---|
| One generated seat shape per provider, identical contracts per project | Hand-copied folders, per-seat prompt drift |
| Coverage stated per project on the desk | Guessing from the roster file |
| Providers detected, missing ones named | A hard-coded four |
| Founder-run hire while the classifier refuses, with the script generated | The coordinator working around a permission denial |
| Cloud sessions as evidence until wf-258 decides | Cloud rows on the roster today |
