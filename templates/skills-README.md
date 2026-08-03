# Workspace skills (L0 toolkit)

Planted by `blueprint found`. Skills are the **local coordination layer** for
AI agents in this workspace — not cloud vendor packs, not CLI-home-only files.

## Placement

| Home | Meaning |
|---|---|
| Workspace `.agents/skills/<id>/` | **Preferred SoT** for cross-project (L0) skills |
| Workspace `.claude/skills/<id>/` | **Discovery** for Map toolkit + Claude-style loaders (real dir or symlink → `.agents`) |
| Project `<folder>/.claude/skills/<id>/` | **L1** — one product / domain only |
| `~/.claude/skills/`, `~/.grok/skills/`, `~/.codex/skills/` | **CLI discovery only** — symlink **into this workspace**; never invent SoT under `~/` for coordination skills |
| Cloud skill marketplaces | Out of scope for BluePrint coordination |

Each skill is a folder with `SKILL.md` (YAML frontmatter `name` + `description`,
then agent instructions). Optional `references/` and `scripts/`.

## Promote to L0 only if all hold

1. Useful in ≥2 projects in this workspace  
2. No product-private secrets or live money rules  
3. Workspace-neutral description  
4. No duplicate under another name at L0  

## L0 skills in this workspace

| id | Role |
|---|---|
| `workspace-efficiency` | Drain hygiene — ready-by-seat, You-starve, assign≠escalate, skills bridge |
| _(add more)_ | Folders under `.agents/skills/<id>/` + list here |

## L0 must load inside project sessions

**Expected:** open a product folder → L1 domain skills **and** workspace L0
coord skills (efficiency, routing, …) are available.

**CLI default (Grok and similar):** discovery walks **CWD → that project’s git
root only**. Nested product repos do **not** see parent `.agents/skills`
without a bridge.

### Grok (all BluePrint workspaces)

Add to `~/.grok/config.toml` (once per machine; path = **this** workspace root):

```toml
[skills]
paths = ["{{WORKSPACE_ROOT}}/.agents/skills"]
```

Replace `{{WORKSPACE_ROOT}}` with the absolute path of this founded folder
(see `FIRST_RUN.md` for a filled-in snippet). Source of truth stays under
`.agents/skills` — do not copy skills into `~/.grok/skills`.

### Claude / Cursor

Prefer project or workspace `.claude/skills`. After adopt, run the planted bridge:

```bash
bash scripts/skills_sync.sh
# report only:
bash scripts/skills_sync.sh --check
```

That symlinks each L0 id into every managed project’s `.claude/skills/`
(without clobbering real L1 skill directories of the same name).

### Assign ≠ escalate (queue seating)

| Intent | Labels / gate |
|---|---|
| **Assign to hand** | `worker:<persona>` on create (default for ship work) |
| **Your list** | `worker:you` + `you:note\|todo\|remind\|host` |
| **Escalate to You** | **Keep** hand seat + `gate_type=human` / Blocked — never re-seat to You |

Bare `worker:you` on implement work is **starve** (cron never claims You).
Cadence: L0 skill + job `workspace-efficiency` (seeded by `blueprint seed-ops`).

## Agents: where to put a new skill

1. Cross-project → L0 under `.agents/skills/<id>/` + `scripts/skills_sync.sh`  
2. One project only → L1 under that project’s `.claude/skills/<id>/`  
3. After adding L0, re-run skills_sync (Grok `paths` already covers the whole tree)

Product law: BluePrint `INSTRUCTION_LADDER.md` §Skills (when installed with the package docs).
