#!/usr/bin/env bash
# policy_sync.sh — city permissions SoT → generated vendor settings (pc-1059)
#
# Problem: security posture was per-vendor (hand-authored .claude/settings.json
# allowlists). A hand's permissions then depend on which vendor runs it.
#
# Fix: one city SoT (.agents/policy/permissions.json) and this bridge that
# generates .claude/settings.json. Host-personal overrides stay in
# .claude/settings.local.json (never touched here).
#
# Placement / SoT (same family as skills_sync):
#   **SoT (this file):** ProtocolCity/scripts/policy_sync.sh in the monorepo /
#   product parcel.
#   **Monorepo mirror:** <workspace>/scripts/policy_sync.sh MAY be a symlink
#   to the ProtocolCity parcel when present.
#   **Found plant:** templates/scripts/policy_sync.sh seeds bare cities.
#
# Usage (from workspace root, or pass WORKSPACE_ROOT):
#   bash scripts/policy_sync.sh              # apply (generate Claude mirror)
#   bash scripts/policy_sync.sh --check      # report only (exit 1 if drift)
#   bash scripts/policy_sync.sh apply
#   bash scripts/policy_sync.sh import       # seed SoT from existing settings
#   bash scripts/policy_sync.sh plant        # plant SoT stub + script
#   bash scripts/policy_sync.sh show
#
# Implementation: protocolcity.policy_sync (Python). This shell is a thin CLI.

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
  # Bare city plant may not ship lib/ — fall back to walk / env.
  if [ -n "${WORKSPACE_ROOT:-}" ]; then
    WS_ROOT="$(cd "$WORKSPACE_ROOT" && pwd)"
  else
    WS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  fi
fi

CMD="apply"
FORCE=0
JSON=0
EXTRA=()

for arg in "$@"; do
  case "$arg" in
    --check)
      CMD="check"
      ;;
    apply|check|import|plant|show)
      CMD="$arg"
      ;;
    --force)
      FORCE=1
      ;;
    --json)
      JSON=1
      ;;
    -h|--help)
      sed -n '2,30p' "$0"
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
if [ ${#EXTRA[@]} -gt 0 ]; then
  PY_ARGS+=("${EXTRA[@]}")
fi

# Prefer package module; fall back to repo path on PYTHONPATH.
if python3 -c "import protocolcity.policy_sync" 2>/dev/null; then
  exec python3 -m protocolcity.policy_sync "${PY_ARGS[@]}"
fi

# Dev / worktree: add package parent
REPO_CANDIDATES=(
  "$SCRIPT_DIR/.."
  "$WS_ROOT/ProtocolCity"
  "$WS_ROOT"
)
for cand in "${REPO_CANDIDATES[@]}"; do
  if [ -f "$cand/protocolcity/policy_sync.py" ]; then
    export PYTHONPATH="${cand}${PYTHONPATH:+:$PYTHONPATH}"
    exec python3 -m protocolcity.policy_sync "${PY_ARGS[@]}"
  fi
done

echo "error: protocolcity.policy_sync not importable; install blueprint/protocolcity or run from a ProtocolCity checkout" >&2
exit 1
