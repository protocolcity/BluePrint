# Riverside — City Law (L0)

This folder is the root of the city. Sessions opened here are
**cross-neighborhood sessions**; for deep work on one project, open that
neighborhood's folder directly so its own law (AGENTS.md) loads.

## Neighborhood registry

| Folder | What it is | Work orders (prefix) | Status |
|---|---|---|---|
| `recipes-site/` | Recipe website — static site generator + content | `rs-*` | live |

## Cross-neighborhood rules

- **Scope every ticket explicitly.** Pass the neighborhood's slug on every
  ticket call, even while there's only one store.
- **Work spanning two neighborhoods = two tickets** (rule pre-registered for
  the day a second neighborhood exists).

## Boundaries

- Only one neighborhood so far; boundary rules start when the second one is
  chartered.

## Citizen gates (city-wide)

Anything below is prepared by workers but shipped only by a citizen:

- Publishing or deploying the site
- Releases and version tags
- Money, credentials, and permissions
- Deleting anything that can't be regenerated

## Vendor pointers

The canonical law file at every level is `AGENTS.md`. Vendor files are
pointers, never content.
