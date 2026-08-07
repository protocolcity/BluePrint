# Templates — the forms of the law

> **Dual-tree parity:** repo-root `templates/` is the **authoring SoT**
> (git export face). `protocolcity/templates/` is the **wheel mirror** that
> `blueprint found` / pip / brew plant into cities. Keep them **byte-identical**
> via `bash scripts/templates_sync.sh` (CI: `--check`). Prefer edits on the
> SoT, then sync — dual independent copies are the bug.

Fill-in-the-blank files for the four levels of law
(Charter §3 — product `docs/CHARTER.md`). Copy, fill every `{{PLACEHOLDER}}`,
delete the guidance comments.

| Template | Copy to | As |
|---|---|---|
| [`city-AGENTS.md`](city-AGENTS.md) | **workspace** root | `AGENTS.md` (L0 CORE — title: Workspace instructions) |
| [`project-AGENTS.md`](project-AGENTS.md) | each **project** root | `AGENTS.md` (L1) |
| [`project-ARCHITECTURE.md`](project-ARCHITECTURE.md) | each **project** root | `ARCHITECTURE.md` (L1 structural law) |
| [`BOUNDARIES.md`](BOUNDARIES.md) | workspace root (next to `AGENTS.md`) | `BOUNDARIES.md` (L0 cross-project grants — **citizen name**) |
| [`PERIMETER.md`](PERIMETER.md) | *(forever alias)* → prefer `BOUNDARIES.md` | still accepted at runtime |
| [`OFFICE_PERIMETER.md`](OFFICE_PERIMETER.md) | *(legacy alias)* → use `BOUNDARIES.md` | legacy name |
| [`CITY_EDGES.md`](CITY_EDGES.md) | *(legacy alias)* → use `BOUNDARIES.md` | legacy name for older FOUNDING paths |
| [`neighborhood-AGENTS.md`](neighborhood-AGENTS.md) | *(legacy alias)* → prefer **project-AGENTS.md** | still plants as project `AGENTS.md` if used |
| [`worker-CONTRACT.md`](worker-CONTRACT.md) | `<project>/workers/<worker-id>/` | `CONTRACT.md` |
| [`worker-prompt.md`](worker-prompt.md) | `<project>/workers/<worker-id>/` | `prompt.md` (This run) |
| [`vendor-pointers.md`](vendor-pointers.md) | (optional instructions, not a law file) | — |
| [`skills-README.md`](skills-README.md) | workspace `.claude/skills/README.md` | L0 skills shelf rules (planted by `found`) |

**Citizen words (foundation v2):** workspace · project · work order · Agents · You.  
Civic words (Charter only): city · neighborhood · ticket.

Start with product `docs/FOUNDING.md` when present. A **workspace of one**
(single project) may use `project-AGENTS.md` as both L0 and L1 until a second
project exists.

**Skills** are the local agent coordination layer (not cloud): L0 under
workspace `.claude/skills/` / `.agents/skills/`; L1 under each project.
Product law: `docs/INSTRUCTION_LADDER.md` §Skills.

Filled examples of every template live under product `example/` when present
in this checkout.
