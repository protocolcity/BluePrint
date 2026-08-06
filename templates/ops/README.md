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
| `workspace-efficiency` | Drain hygiene job |

## Optional paper packs (this tree)

| Seat | Role |
|---|---|
| `papers-sync` | Weekly AGENTS generated-block refresh (was `papers-patrol`; citizen install) |

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
