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

## Shipped paper packs (this tree)

| Seat | Role |
|---|---|
| `workspace-efficiency` | Drain hygiene job (seed-ops default) |
| `papers-patrol` | Weekly AGENTS generated-block refresh |
| `chief-of-staff` | Mode B capacity stage+approve |

Plant / hire:

```text
blueprint hire chief-of-staff \
  --workdir <workspace>/.protocolcity/ops \
  --kind job \
  --role 'capacity Mode B stager'
```

Papers also plant via `protocolcity.seed_ops.plant_ops_seat_papers` without
roster arm (detect surfaces `scope=workspace_ops`).

See suite doctrine: *First-user boundary — BluePrint consumer vs product project*.
