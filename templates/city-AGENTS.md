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
