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

## Coordination (You in chat — any vendor)

BluePrint is vendor-neutral: pick any chat host + MCP/`tk` for capture, any
CLI for hired hands, suite as **glass**.

- **Capture** = chat + MCP (`wl_create` / `tk create`) — not suite Map forms
- **File = decided.** When You file a work order, hands work it — they do not
  re-ask for permission. Route with `worker:<id>` on create.
- **Hands** drain only tickets labeled `worker:<id>`
- **For You** = roadblocks only (true decisions / sign-off) — not FYI, not
  “confirm this plan” after You already filed
- **Coord sessions** file / label / dispatch / escalate — they do **not** claim
  `worker:*` work when a hand runtime exists
- **Identity** default wire id: **`you`** (UI shows **You**)
- Full ladder: product docs `INSTRUCTION_LADDER.md` + `SUITE_VIEWER.md` when
  present in your BluePrint install

## Truth upkeep (board + papers — every project)

The work-order board is shared memory. **Closing a ticket hides the work.**

- **Sticky residual.** If work remains at close: keep the parent open, **or**
  file child tickets first and list those ids under `Follow-ups:`.  
  **`Follow-ups: none` means none** — not “tabled in the close comment.”
- **Docs drift.** If the change altered structural truth (entrypoints, process,
  public install lines, decision checklists / ADRs, architecture), update those
  papers **in the same close-out commit**. Name the doc updates under
  `Completed:` (or write `docs: no drift`). Stale truth files are invisible work.
- **Decisions with checklists.** When a later release lands a checklist item,
  tick the decision paper in that same slice — do not leave ratified ADRs
  half-checked forever.

WorkLane’s PROTOCOL (PROCESS) carries the full close-out rules; this section is
the short city-root reminder every neighborhood inherits.

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
