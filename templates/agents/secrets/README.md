# Host secrets shelf

**Names + lifecycle only.** Secret *values* live on the host (env / keychain),
never in this tree.

| Path | Role |
|---|---|
| `.agents/secrets/inventory.json` | Lifecycle paper — expiry, provenance, notes |
| `.agents/mcp/<id>/manifest.json` `env_required` | What each MCP needs (names only) |
| Host env / keychain | Actual secret values |

## Commands

```bash
# report only (exit 1 when a required name is unset or past expiry)
python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT"

# same + gold For You when gaps exist (idempotent per day)
python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT" --gold

# plant empty shelf
python3 ProtocolCity/scripts/check_mcp_secrets.py plant --workspace "$WORKSPACE_ROOT"
```

## Edit rules

1. When you add an MCP that needs a key, put the name in that manifest's
   `env_required` and (optionally) add a lifecycle row under `keys` here.
2. Provision the value on the host (shell env, OS keychain, or the service manager) — never commit it.
3. Record expiry / rotation notes in `inventory.json` when you know them.
4. Run the check after provisioning; clear any gold card when the gap is gone.

Law: `docs/specs/HOST_SECRETS_INVENTORY.md` · design:
`docs/research/byo-mcp-library-design-2026-08.md` §5.
