#!/usr/bin/env bash
# mcp_sync.sh — city MCP registry SoT → generated vendor mirrors (pc-1078)
#
# Problem: MCP server defs were hand-authored in workspace .mcp.json and each
# vendor's config.toml. Drift is inevitable (pc-1069 dead path; audit evidence).
#
# Fix: one city SoT (.agents/mcp/<id>/manifest.json) and this bridge that
# generates .mcp.json (+ patches managed [mcp_servers.<id>] in Grok/Codex).
# Personal / non-registry vendor servers are never deleted.
#
# Placement / SoT (same family as skills_sync / policy_sync):
#   **SoT (this file):** ProtocolCity/scripts/mcp_sync.sh in the monorepo /
#   product parcel.
#   **Monorepo mirror:** <workspace>/scripts/mcp_sync.sh MAY be a symlink
#   to the ProtocolCity parcel when present.
#   **Found plant:** templates/scripts/mcp_sync.sh seeds bare cities.
#
# Usage (from workspace root, or pass WORKSPACE_ROOT):
#   bash scripts/mcp_sync.sh              # apply (generate + patch vendors)
#   bash scripts/mcp_sync.sh --check      # report only (exit 1 if drift)
#   bash scripts/mcp_sync.sh --list       # inventory registry
#   bash scripts/mcp_sync.sh apply
#   bash scripts/mcp_sync.sh import       # seed SoT from existing .mcp.json
#   bash scripts/mcp_sync.sh seed         # L0 worklane (+ optional workforce) (pc-1079)
#   bash scripts/mcp_sync.sh migrate      # import + seed L0 + apply (live host)
#   bash scripts/mcp_sync.sh plant        # plant shelf + script + seed L0
#   bash scripts/mcp_sync.sh show
#
# Implementation: protocolcity.mcp_sync (Python). This shell is a thin CLI.

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

CMD="apply"
FORCE=0
JSON=0
NO_VENDORS=0
CHECK_VENDORS=0
EXTRA=()

for arg in "$@"; do
  case "$arg" in
    --check)
      CMD="check"
      ;;
    --list)
      CMD="list"
      ;;
    apply|check|import|plant|list|show|seed|migrate)
      CMD="$arg"
      ;;
    --force)
      FORCE=1
      ;;
    --json)
      JSON=1
      ;;
    --no-vendors)
      NO_VENDORS=1
      ;;
    --check-vendors)
      CHECK_VENDORS=1
      ;;
    -h|--help)
      sed -n '2,32p' "$0"
      exit 0
      ;;
    *)
      EXTRA+=("$arg")
      ;;
  esac
done

export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$WS_ROOT}"

PY_ARGS=("$CMD" "--workspace" "$WS_ROOT")
if [ "$FORCE" -eq 1 ]; then
  PY_ARGS+=(--force)
fi
if [ "$JSON" -eq 1 ]; then
  PY_ARGS+=(--json)
fi
if [ "$NO_VENDORS" -eq 1 ]; then
  PY_ARGS+=(--no-vendors)
fi
if [ "$CHECK_VENDORS" -eq 1 ]; then
  PY_ARGS+=(--check-vendors)
fi
if [ ${#EXTRA[@]} -gt 0 ]; then
  PY_ARGS+=("${EXTRA[@]}")
fi

if python3 -c "import protocolcity.mcp_sync" 2>/dev/null; then
  exec python3 -m protocolcity.mcp_sync "${PY_ARGS[@]}"
fi

REPO_CANDIDATES=(
  "$SCRIPT_DIR/.."
  "$WS_ROOT/ProtocolCity"
  "$WS_ROOT"
)
for cand in "${REPO_CANDIDATES[@]}"; do
  if [ -f "$cand/protocolcity/mcp_sync.py" ]; then
    export PYTHONPATH="${cand}${PYTHONPATH:+:$PYTHONPATH}"
    exec python3 -m protocolcity.mcp_sync "${PY_ARGS[@]}"
  fi
done

echo "error: protocolcity.mcp_sync not importable; install blueprint/protocolcity or run from a ProtocolCity checkout" >&2
exit 1
