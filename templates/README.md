# Templates — the forms of the law

Fill-in-the-blank files for the four levels of law
([Charter §3](../CHARTER.md)). Copy, fill every `{{PLACEHOLDER}}`, delete
the guidance comments.

| Template | Copy to | As |
|---|---|---|
| [`city-AGENTS.md`](city-AGENTS.md) | your city root | `AGENTS.md` |
| [`neighborhood-AGENTS.md`](neighborhood-AGENTS.md) | each neighborhood root | `AGENTS.md` |
| [`worker-CONTRACT.md`](worker-CONTRACT.md) | `<neighborhood>/workers/<worker-id>/` | `CONTRACT.md` |
| [`worker-prompt.md`](worker-prompt.md) | `<neighborhood>/workers/<worker-id>/` | `prompt.md` |
| [`vendor-pointers.md`](vendor-pointers.md) | (instructions, not a law file) | — |

Start with [FOUNDING.md](../FOUNDING.md) — it walks you through which of
these you need and in what order. A **city of one** (single project) starts
with just `neighborhood-AGENTS.md` serving as both city and neighborhood law.

Filled examples of every template live in [`example/`](../example/).
