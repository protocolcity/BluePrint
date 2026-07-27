# Templates — the forms of the law

Fill-in-the-blank files for the four levels of law
([Charter §3](../CHARTER.md)). Copy, fill every `{{PLACEHOLDER}}`, delete
the guidance comments.

| Template | Copy to | As |
|---|---|---|
| [`city-AGENTS.md`](city-AGENTS.md) | your city root | `AGENTS.md` |
| [`PERIMETER.md`](PERIMETER.md) | city root (next to `AGENTS.md`) | `PERIMETER.md` (L0 cross-cabinet grants) |
| [`OFFICE_PERIMETER.md`](OFFICE_PERIMETER.md) | *(alias)* → use `PERIMETER.md` | legacy name |
| [`CITY_EDGES.md`](CITY_EDGES.md) | *(alias)* → use `PERIMETER.md` | legacy name for older FOUNDING paths |
| [`neighborhood-AGENTS.md`](neighborhood-AGENTS.md) | each neighborhood root | `AGENTS.md` |
| [`worker-CONTRACT.md`](worker-CONTRACT.md) | `<neighborhood>/workers/<worker-id>/` | `CONTRACT.md` |
| [`worker-prompt.md`](worker-prompt.md) | `<neighborhood>/workers/<worker-id>/` | `prompt.md` |
| [`vendor-pointers.md`](vendor-pointers.md) | (optional instructions, not a law file) | — |

Start with [FOUNDING.md](../FOUNDING.md) — it walks you through which of
these you need and in what order. A **city of one** (single project) starts
with just `neighborhood-AGENTS.md` serving as both city and neighborhood law.

Filled examples of every template live in [`example/`](../example/).

## Job vs worker (for agents filling these forms)

| Create… | Means | Command |
|---|---|---|
| **Worker / hand** | Persona that **claims** work orders on a project | `blueprint hire <name> --workdir <project>` (roster `kind=lane`) |
| **Job** | Scheduled **duty** (Map diamond; usually no claims) | `blueprint seed-ops` for clerk/marshal/correspondent, or `hire … --kind job` |

`worker-CONTRACT.md` + `worker-prompt.md` are for **workers** (and for job
rows that still plant papers). Do not invent a second hire path by only
copying files — the roster row is what arms the daemon.
