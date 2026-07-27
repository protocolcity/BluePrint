# {{CITY_NAME}} — Workspace instructions (L0)

<!-- Copy this file to your CITY ROOT as AGENTS.md (the folder or repo all
     your projects live under). Fill every {{PLACEHOLDER}}, delete these
     guidance comments, and delete any section that honestly doesn't apply
     yet. Law you don't enforce is worse than no law. -->

This folder is the root of the workspace. Sessions opened here are
**cross-project sessions**; for deep work on one project, open that
neighborhood's folder directly so its own law (AGENTS.md) loads.

## Project registry

<!-- One row per project. If you only have one project, see "city of one"
     in the Charter §3 — merge this file into that project's AGENTS.md
     until a second neighborhood exists. -->

| Folder | What it is | Work orders (prefix) | Status |
|---|---|---|---|
| `{{FOLDER_1}}/` | {{WHAT_IT_IS}} | `{{PREFIX_1}}-*` | {{live / drafting / dormant}} |
| `{{FOLDER_2}}/` | {{WHAT_IT_IS}} | `{{PREFIX_2}}-*` | {{...}} |

## Cross-project rules

- **Scope every ticket explicitly.** In sessions at this level, never rely on
  a default project — pass the project's slug on every ticket call.
- **Work spanning two projects = two tickets**, one per neighborhood,
  each scoped to its side of the boundary.
- **Capture via chat + MCP or `tk` CLI.** The suite Map is live glass — it
  does not host a ticket compose form. Identity default for session actions:
  **you** (any display label you configure; do not teach vendor host ids as the
  product default).
- **Route before ready.** Label every work order `worker:<id>` before marking
  it ready. Without a routing label no schedule drains it — it stays ready but
  invisible to every worker queue. Unlabeled tickets should carry `needs:routing`.

## Coordination (You in chat — any vendor)

BluePrint is vendor-neutral: pick any chat host + MCP/`tk` for capture, any
CLI for hired hands, suite as **glass**.

- **Capture** = chat + MCP (`wl_create` / `tk create`) — not suite Map forms
- **Hands** drain only tickets labeled `worker:<id>`
- **Coord sessions** file / label / dispatch / escalate — they do **not** claim
  `worker:*` work when a hand runtime exists
- **Feed ready; do not stockpile For You.** Three board columns: **Ready** (worker feed) · **For You** (act now) · **Deferred** (`gate_type=deferred` — parked for later, not golded). Park later work with `gate_type=deferred`. Reserve `gate_type=human` for real act-now decisions. Do not bulk-snooze as a substitute for reclassifying.
- **Identity** default wire id: **`you`** (UI shows **You**)
- Full ladder: product docs `INSTRUCTION_LADDER.md` + `SUITE_VIEWER.md` when
  present in your BluePrint install

## Boundaries

<!-- How projects are allowed to talk to each other. The strongest
     version names the mechanism and bans the rest, e.g.:
     "app consumes the store via HTTP only; importing its code is an
      automatic reject." -->

- {{PROJECT_A}} talks to {{PROJECT_B}} via {{MECHANISM}} only.

## Gates that need You (workspace-wide)

Anything below is prepared by workers but shipped only by a citizen:

- Publishing or making anything public
- Releases and version tags
- Money, credentials, and permissions
- Deleting anything that can't be regenerated
<!-- Add your own. Err on the side of gating; ungate by evidence. -->

## Vendor pointers (optional)

The canonical law file at every level is `AGENTS.md`. Vendor files are
optional thin pointers when a CLI needs its own filename — see
`templates/vendor-pointers.md`.
