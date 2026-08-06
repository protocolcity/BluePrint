# City policy (permissions SoT)

**Ticket:**  · **Pattern:** generate, don't document (skills_sync family)

Security posture for hands is **city-owned**, not per-vendor. Edit this shelf;
regenerate vendor mirrors. Do not hand-author `.claude/settings.json`.

## Placement

| Path | Role |
|---|---|
| `.agents/policy/permissions.json` | **SoT** — allow/deny classes, path boundaries, hooks (vendor-neutral) |
| `.claude/settings.json` | **Generated** Claude mirror — run `bash scripts/policy_sync.sh` |
| `.claude/settings.local.json` | **Host-personal** escape hatch — never generated; never committed as city law |
| Codex / Grok config | **Reserved** (schema lists mirrors; generators land in a follow-on slice) |

## Commands

```bash
bash scripts/policy_sync.sh            # generate Claude settings from SoT
bash scripts/policy_sync.sh --check    # exit 1 if generated file drifted
bash scripts/policy_sync.sh import     # one-time: seed SoT from existing settings
bash scripts/policy_sync.sh plant      # plant stub SoT + script into this city
```

## Edit rules

1. Change **allow/deny** (or hooks) in `permissions.json`.
2. Run `bash scripts/policy_sync.sh` (or `python3 -m protocolcity.policy_sync apply`).
3. Commit the SoT + regenerated `.claude/settings.json` together when both live in the city tree.
4. Put machine-only grants in `settings.local.json` (gitignored or host-private).

## Boundaries

`path_boundaries.respect_files` points at city law (`BOUNDARIES.md` /
`PERIMETER.md`). Product-boundary rulings (runtime-isolation ADRs) remain
product law — this paper does not restate the full perimeter; it names the
files hands must respect.
