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
| [`PROGRAMS.md`](PROGRAMS.md) | each **project** root | `PROGRAMS.md` (3–5 named lines of work) |
| [`FEATURES.md`](FEATURES.md) | each project `docs/` (or root when no `docs/`) | `FEATURES.md` (citizen-named surfaces: name · where · verify · notes) |
| [`BOUNDARIES.md`](BOUNDARIES.md) | workspace root (next to `AGENTS.md`) | `BOUNDARIES.md` (L0 cross-project grants — **citizen name**) |
| [`PERIMETER.md`](PERIMETER.md) | *(forever alias)* → prefer `BOUNDARIES.md` | still accepted at runtime |
| [`OFFICE_PERIMETER.md`](OFFICE_PERIMETER.md) | *(legacy alias)* → use `BOUNDARIES.md` | legacy name |
| [`CITY_EDGES.md`](CITY_EDGES.md) | *(legacy alias)* → use `BOUNDARIES.md` | legacy name for older FOUNDING paths |
| [`neighborhood-AGENTS.md`](neighborhood-AGENTS.md) | *(legacy alias)* → prefer **project-AGENTS.md** | still plants as project `AGENTS.md` if used |
| [`worker-CONTRACT.md`](worker-CONTRACT.md) | `<project>/workers/<worker-id>/` | `CONTRACT.md` |
| [`worker-prompt.md`](worker-prompt.md) | `<project>/workers/<worker-id>/` | `prompt.md` (This run) |
| [`vendor-pointers.md`](vendor-pointers.md) | (optional instructions, not a law file) | — |
| [`skills-README.md`](skills-README.md) | workspace `.claude/skills/README.md` | L0 skills shelf rules (planted by `found`) |

**Words:** workspace · project · work order · Agents · You.
Do not teach city · neighborhood · cabinet as operating nouns.

Start with product `docs/FOUNDING.md` when present. A **workspace of one**
(single project) may use `project-AGENTS.md` as both L0 and L1 until a second
project exists.

**Skills** are the local agent coordination layer (not cloud): L0 under
workspace `.claude/skills/` / `.agents/skills/`; L1 under each project.
Product law: `docs/INSTRUCTION_LADDER.md` §Skills.

Filled examples of every template live under product `example/` when present
in this checkout.

## Loading and verification

`protocolcity.found._template` and `protocolcity.seed_ops._templates_dir` prefer
`protocolcity/templates/`; the root tree is a fallback when packaged templates
are absent. `pyproject.toml` includes the mirror as package data; setuptools
does not synchronize it. Run `bash scripts/templates_sync.sh` after authoring,
and `bash scripts/templates_sync.sh --check` before building. Unknown files in
the mirror are reported and preserved for review rather than deleted.

`overview/v1/tests/test_template_packaging.py` checks every template's bytes,
builds a wheel outside the checkout, and exercises the actual hire and seed
planting functions from the extracted wheel in a disposable workspace with
network/SQLite access denied. It also verifies existing customized papers are
preserved. CI runs these checks in the overview suite. Existing workspaces are
not rewritten by a template update; host review must verify a fresh installed
sample before treating an installed founding outcome as accepted.
