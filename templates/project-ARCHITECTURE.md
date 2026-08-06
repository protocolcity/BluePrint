# {{PROJECT_NAME}} — Architecture (L1)

<!-- Copy this file to the PROJECT ROOT as ARCHITECTURE.md (next to AGENTS.md).
     Fill every {{PLACEHOLDER}}, delete these comments. Agents read this before
     structural work — it is product law, not a vault research note. -->

> **Change rule:** any structural change (new layer, new owner of a fact, new
> data-flow direction, broken invariant) updates this paper **in the same
> close-out** as the code. Prose-only law that drifts is debt.

## What this system is

{{ONE_PARAGRAPH: the product shape an implementer must hold — major
subsystems, what is in-repo vs engines, and what "done" means for a change
here.}}

## Layers and boundaries

<!-- Name the layers (e.g. Truth / Projection / View, or domain packages).
     Each layer has one job; edges say what may import or call what. -->

| Layer | Owns | Must not |
|---|---|---|
| {{LAYER_1}} | {{OWNS_1}} | {{MUST_NOT_1}} |
| {{LAYER_2}} | {{OWNS_2}} | {{MUST_NOT_2}} |
| {{LAYER_3}} | {{OWNS_3}} | {{MUST_NOT_3}} |

## Single sources of truth

<!-- One owner per fact. If two places can write the same truth, name the
     conflict and pick a winner. -->

| Domain / fact | Owner (path or store) | Readers only |
|---|---|---|
| {{DOMAIN_1}} | {{OWNER_1}} | {{READERS_1}} |
| {{DOMAIN_2}} | {{OWNER_2}} | {{READERS_2}} |

## Data-flow direction

<!-- Happy path: where truth is written, how projections form, how the UI
     or CLI reads. Prefer arrows over prose walls. -->

```
{{DATA_FLOW: e.g. disk/DB → engine API → suite/CLI view}}
```

## Invariants agents must not violate

- {{INVARIANT_1}}
- {{INVARIANT_2}}
- {{INVARIANT_3}}

## Out of scope for this paper

<!-- Point at AGENTS.md for process/desk routing; point at research vault
     notes for historical design. This file is only live structural law. -->

- Process, tickets, hire seats → `AGENTS.md`
- Historical design notes → `docs/research/` (not enforceable law)
