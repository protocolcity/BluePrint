# {{NEIGHBORHOOD_NAME}} — Neighborhood Law (L1)

<!-- Copy this file to the NEIGHBORHOOD ROOT (the project's repo/folder) as
     AGENTS.md. Fill every {{PLACEHOLDER}}, delete these comments. This is
     the first thing any agent reads before touching your project — write
     it for a competent stranger. -->

## What this place is

{{ONE_PARAGRAPH: what the project does, who it's for, and anything an agent
must know before acting — e.g. "handles real customer data", "deploys
automatically on push", "prototype, nothing depends on it".}}

## How to run and test it

```
{{RUN_COMMAND}}
{{TEST_COMMAND}}
```

<!-- If verification is more than one command, link a doc. An agent that
     can't verify its work must stop and say so, not guess. -->

## The desk

- Ticket store: `{{STORE_SLUG}}` (work orders `{{PREFIX}}-*`)
- Every change ties to a ticket; every ticket close-out states what was done
  and how it was verified.

## Boundaries and no-go zones

<!-- The most valuable section. Name what agents must never touch and why,
     e.g. payment code, production configs, migration files, another
     neighborhood's internals. -->

- {{NO_GO_1}} — {{WHY}}
- {{NO_GO_2}} — {{WHY}}

## The workforce here

| Worker | Vendor CLI | May claim | Contract |
|---|---|---|---|
| `{{WORKER_ID}}` | {{CLI}} | `lane:{{WORKER_ID}}` tickets | `workers/{{WORKER_ID}}/PROTOCOL.md` |

<!-- No workers yet? Delete the table, keep the heading, write "Citizen
     sessions only for now." Still compliant — law first, workforce later. -->

## Citizen gates (local)

<!-- What needs a human in THIS neighborhood, beyond city-wide gates.
     e.g. schema migrations, dependency upgrades, anything user-visible. -->

- {{LOCAL_GATE_1}}
