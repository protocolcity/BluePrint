# {{CITY_NAME}} — City Law (L0)

<!-- Copy this file to your CITY ROOT as AGENTS.md (the folder or repo all
     your projects live under). Fill every {{PLACEHOLDER}}, delete these
     guidance comments, and delete any section that honestly doesn't apply
     yet. Law you don't enforce is worse than no law. -->

This folder is the root of the city. Sessions opened here are
**cross-neighborhood sessions**; for deep work on one project, open that
neighborhood's folder directly so its own law (AGENTS.md) loads.

## Neighborhood registry

<!-- One row per project. If you only have one project, see "city of one"
     in the Charter §3 — merge this file into that project's AGENTS.md
     until a second neighborhood exists. -->

| Folder | What it is | Work orders (prefix) | Status |
|---|---|---|---|
| `{{FOLDER_1}}/` | {{WHAT_IT_IS}} | `{{PREFIX_1}}-*` | {{live / drafting / dormant}} |
| `{{FOLDER_2}}/` | {{WHAT_IT_IS}} | `{{PREFIX_2}}-*` | {{...}} |

## Cross-neighborhood rules

- **Scope every ticket explicitly.** In sessions at this level, never rely on
  a default project — pass the neighborhood's slug on every ticket call.
- **Work spanning two neighborhoods = two tickets**, one per neighborhood,
  each scoped to its side of the boundary.

## Boundaries

<!-- How neighborhoods are allowed to talk to each other. The strongest
     version names the mechanism and bans the rest, e.g.:
     "app consumes the store via HTTP only; importing its code is an
      automatic reject." -->

- {{NEIGHBORHOOD_A}} talks to {{NEIGHBORHOOD_B}} via {{MECHANISM}} only.

## Citizen gates (city-wide)

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
