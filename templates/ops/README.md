# Workspace ops kit

Pre-installed **workspace** agents (Office staff) live here — not inside a
single product folder.

```text
.protocolcity/ops/workers/<id>/CONTRACT.md
.protocolcity/ops/workers/<id>/prompt.md              # optional
.protocolcity/ops/workers/<id>/capacity_policy.json   # optional (Mode B seats)
```

Hire them into WorkForce (roster). Map paints them on the **Workspace ops**
ring next to You. Project folders keep only **project** agents.

## Default trio (auto-seed)

`blueprint seed-ops` / first serve plant exactly these three:

| Seat | Role |
|---|---|
| `chief-of-staff` | Coordination — routing, capacity staging, inbox triage (Mode B) |
| `health-patrol` | Ticket health patrol (was `marshal`) |
| `workspace-efficiency` | Drain hygiene job — **not** product-code refactors |

## Optional paper packs (this tree)

| Seat | Role |
|---|---|
| `papers-sync` | Weekly AGENTS generated-block refresh (was `papers-patrol`; citizen install) |

## Optional **project** job (sibling tree · not ops)

Per-project **code shape** — oversized / god modules, one extract-module
split at a time. Distinct from `workspace-efficiency`. Papers live at
`templates/jobs/code-efficiency/` (CONTRACT + prompt). Playbook: L0 skill
`code-efficiency`. **Not** auto-seeded by `blueprint seed-ops` (product
writes stay a citizen hire).

```text
blueprint hire efficiency-<project-slug> \
  --workdir <project>/.protocolcity \
  --kind job \
  --role 'scan oversized modules; file one split WO at a time' \
  --schedule '0 10 * * 1'
```

Copy CONTRACT/prompt into `<project>/workers/efficiency-<project-slug>/`
(or the hire papers path). Scan helper: `scripts/code_size_scan.py`.
WO shape: `templates/code-split-WO.md`.

Plist template for always-on weekly fire (public path):
`templates/host-agents/com.protocolcity.papers-sync.plist`

Plant / hire optional seats:

```text
blueprint hire papers-sync \
  --workdir <workspace>/.protocolcity/ops \
  --kind job \
  --role 'weekly AGENTS generated-block refresh' \
  --schedule '0 9 * * 1'
```

Papers also plant via `protocolcity.seed_ops.plant_ops_seat_papers` without
roster arm (detect surfaces `scope=workspace_ops`).

See suite doctrine: *First-user boundary — BluePrint consumer vs product project*.
