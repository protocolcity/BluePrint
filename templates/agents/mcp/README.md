# City MCP registry (BYO-MCP)

**Ticket:**  ·  · **Design:** `docs/research/byo-mcp-library-design-2026-08.md`

MCP server definitions are **city-owned**, not per-vendor. Edit manifests here;
regenerate vendor mirrors. Do **not** hand-author workspace `.mcp.json`.

## Placement

| Path | Role |
|---|---|
| `.agents/mcp/<id>/manifest.json` | **SoT** — transport, command/args or url, env **names**, capability/risk |
| `.mcp.json` | **Generated** Claude/Cursor mirror (`_bp.generated_by=mcp_sync`) |
| `~/.grok/config.toml` `[mcp_servers.<id>]` | **Managed patch** — registry ids only |
| `~/.codex/config.toml` `[mcp_servers.<id>]` | **Managed patch** — personal servers left alone |
| Host env / keychain | **Secrets** — never commit values; list names in `env_required` |
| `.agents/secrets/inventory.json` | **Lifecycle paper** — expiry/provenance; never values |

## Commands

```bash
bash scripts/mcp_sync.sh              # apply — generate/patch mirrors
bash scripts/mcp_sync.sh --check      # exit 1 on drift
bash scripts/mcp_sync.sh --list       # inventory registry
bash scripts/mcp_sync.sh import       # seed registry from existing .mcp.json
bash scripts/mcp_sync.sh seed         # L0 worklane (+ optional workforce when seedable)
bash scripts/mcp_sync.sh migrate      # import + seed L0 + apply (live host)
bash scripts/mcp_sync.sh plant        # plant shelf + script + seed L0 worklane

# Host secrets check — env_required names resolve?
bash scripts/check_mcp_secrets.sh              # exit 1 on missing/expired
bash scripts/check_mcp_secrets.sh --gold       # + For You when gaps
```

## Edit rules

1. Add or edit `.agents/mcp/<id>/manifest.json`.
2. Provision any `env_required` names on the host (You); optional lifecycle
   row in `.agents/secrets/inventory.json` (see `docs/specs/HOST_SECRETS_INVENTORY.md`).
3. Run `bash scripts/mcp_sync.sh` then `bash scripts/check_mcp_secrets.sh`.
4. Commit the registry SoT; generated `.mcp.json` is city-tree when present.

## L0 seeds

| id | When | Path |
|---|---|---|
| `worklane` | Always on `plant` / `seed` / `migrate` | `worklane/manifest.json` |
| `workforce` | Optional — only when `workforce/` + MCP module present | `workforce/manifest.json` |

Canonical templates ship in the BluePrint package. Live hosts: `migrate` upgrades
hand-authored vendor blocks (including stale command paths and legacy package
aliases) to registry SoT + regenerated mirrors.

## Manifest sketch (v1)

```json
{
  "id": "worklane",
  "description": "WorkLane / Ticketing Protocol board",
  "transport": "stdio",
  "command": "{{WORKSPACE_ROOT}}/worklane/.venv/bin/python",
  "args": ["-m", "worklane.mcp", "--author", "you"],
  "env": {
    "TP_AGENT_ID": "${TP_AGENT_ID:-you}",
    "TICKETING_PROTOCOL_RUNTIME_DIR": "{{WORKSPACE_ROOT}}/.protocolcity/worklane"
  },
  "env_required": [],
  "capability": "mutating",
  "risk": "board write — claim/close/label; not money",
  "seats": ["*"],
  "level": "L0",
  "vendor_locked": false,
  "enabled": true
}
```
