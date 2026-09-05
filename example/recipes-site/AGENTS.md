# recipes-site — Project instructions (L1)

## What this place is

A static recipe website: markdown recipes in `content/`, built with a static
site generator, deployed manually by You. Nothing here handles user
data; the worst possible accident is publishing a bad recipe.

## How to run and test it

```
npm run dev      # local preview at :4321
npm test         # link checker + recipe front-matter validation
```

## The desk

- Ticket store: `recipes` (work orders `rs-*`)
  - Prefix `rs` is the canonical prefix **registered in the desk when the store
    was created**. `blueprint adopt` reads this back from `/api/scene` on every
    subsequent adopt, so re-adoption never invents a second prefix.
    Run `blueprint doctor --neighborhood recipes-site` to confirm the live
    prefix matches `desk-join.json` (`--neighborhood` is the project folder).
- Every change ties to a ticket; every ticket close-out states what was done
  and how it was verified.

## Boundaries and no-go zones

- `content/family/` — personal recipes, not for the public site; never edit,
  never link.
- `deploy.config.js` — deployment is citizen-gated; workers never touch it.

## The workforce here

| Worker | Vendor CLI | May claim | Contract |
|---|---|---|---|
| `claude-recipes` | `claude -p` | `lane:claude-recipes` tickets | `workers/claude-recipes/CONTRACT.md` |

## Citizen gates (local)

- Anything user-visible on the homepage
- Adding or removing a recipe category (information architecture is taste)
