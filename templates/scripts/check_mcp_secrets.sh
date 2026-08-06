#!/usr/bin/env bash
# check_mcp_secrets.sh — host secrets inventory check (pc-1061)
#
# Walks .agents/mcp/*/manifest.json env_required names, joins
# .agents/secrets/inventory.json lifecycle paper, reports missing/expired
# keys. Never prints secret values.
#
# Usage (from workspace root, or pass WORKSPACE_ROOT):
#   bash scripts/check_mcp_secrets.sh              # check + write local report
#   bash scripts/check_mcp_secrets.sh --gold       # + For You gold when gaps
#   bash scripts/check_mcp_secrets.sh plant
#   bash scripts/check_mcp_secrets.sh --json
#
# Cadence: weekly or after adding an MCP that needs a new key.
# Implementation: protocolcity.secrets_inventory

set -euo pipefail

_src="${BASH_SOURCE[0]:-$0}"
while [ -h "$_src" ]; do
  _dir="$(cd -P "$(dirname "$_src")" && pwd)"
  _link="$(readlink "$_src")"
  case "$_link" in
    /*) _src="$_link" ;;
    *) _src="$_dir/$_link" ;;
  esac
done
SCRIPT_DIR="$(cd -P "$(dirname "$_src")" && pwd)"
unset _src _dir _link

# shellcheck source=lib/workspace_root.sh
if [ -f "$SCRIPT_DIR/lib/workspace_root.sh" ]; then
  . "$SCRIPT_DIR/lib/workspace_root.sh"
  ws_resolve_root "$SCRIPT_DIR"
else
  if [ -n "${WORKSPACE_ROOT:-}" ]; then
    WS_ROOT="$(cd "$WORKSPACE_ROOT" && pwd)"
  else
    WS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  fi
fi

export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WS_ROOT}"

# Prefer parcel next to this script's parent when it is ProtocolCity/
PC_ROOT=""
if [ -f "$SCRIPT_DIR/../protocolcity/secrets_inventory.py" ]; then
  PC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$WS_ROOT/ProtocolCity/protocolcity/secrets_inventory.py" ]; then
  PC_ROOT="$(cd "$WS_ROOT/ProtocolCity" && pwd)"
elif [ -f "$WS_ROOT/protocolcity/secrets_inventory.py" ]; then
  PC_ROOT="$WS_ROOT"
fi

if [ -n "$PC_ROOT" ]; then
  export PYTHONPATH="${PC_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
  exec python3 "$PC_ROOT/scripts/check_mcp_secrets.py" --workspace "$WS_ROOT" "$@"
fi

exec python3 -m protocolcity.secrets_inventory --workspace "$WS_ROOT" "$@"
