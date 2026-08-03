#!/usr/bin/env bash
# skills_sync.sh — workspace L0 skill discovery bridge (not a cloud marketplace)
#
# Problem: product folders are often their own git roots. Claude/Cursor-style
# loaders only walk CWD → that project. L0 skills under <workspace>/.agents/skills
# then never load when you open a project folder.
#
# Fix: symlink each L0 skill into every managed project's .claude/skills/
# so the same SoT is discovered. Grok uses ~/.grok/config.toml paths already.
#
# Usage (from workspace root, or pass root as env WORKSPACE_ROOT):
#   bash scripts/skills_sync.sh           # apply
#   bash scripts/skills_sync.sh --check   # report only (exit 1 if drift)
#   bash scripts/skills_sync.sh --list    # inventory L0 + L1
#
# Not skillsgate / skills.sh marketplace: local workspace shelf only.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve workspace root:
#   <ws>/scripts/skills_sync.sh  → parent
#   <ws>/ProtocolCity/scripts/…  → grandparent (monorepo / host checkout)
#   WORKSPACE_ROOT env wins when set
if [ -n "${WORKSPACE_ROOT:-}" ]; then
  WS_ROOT="$(cd "$WORKSPACE_ROOT" && pwd)"
elif [ -d "$SCRIPT_DIR/../.agents/skills" ] || [ -f "$SCRIPT_DIR/../AGENTS.md" ]; then
  WS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -d "$SCRIPT_DIR/../../.agents/skills" ] || [ -f "$SCRIPT_DIR/../../AGENTS.md" ]; then
  WS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
  WS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

L0_AGENTS="$WS_ROOT/.agents/skills"
L0_CLAUDE="$WS_ROOT/.claude/skills"
CHECK_ONLY=0
LIST_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --list) LIST_ONLY=1 ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
  esac
done

if [ ! -d "$L0_AGENTS" ]; then
  echo "error: L0 shelf missing: $L0_AGENTS" >&2
  echo "hint: run from a founded BluePrint workspace (blueprint found)" >&2
  exit 1
fi

# Managed projects = top-level folders with AGENTS.md (L1 law).
# Skip export mirrors, VCS, and known non-project trees.
_skip_name() {
  case "$1" in
    .*|node_modules|__pycache__|dist|build|exports|ProtocolCity-WorkLane|ProtocolCity-BluePrint|ProtocolCity-WorkForce)
      return 0 ;;
  esac
  return 1
}

list_managed() {
  if [ -n "${SKILLS_SYNC_MANAGED:-}" ]; then
    # Space-separated override for host cities with a fixed list
    # shellcheck disable=SC2086
    for name in $SKILLS_SYNC_MANAGED; do
      printf '%s\n' "$name"
    done
    return
  fi
  for d in "$WS_ROOT"/*; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    _skip_name "$name" && continue
    if [ -f "$d/AGENTS.md" ] || [ -f "$d/.protocolcity/join.json" ] || [ -d "$d/.protocolcity" ]; then
      printf '%s\n' "$name"
    fi
  done | sort -u
}

list_l0() {
  find "$L0_AGENTS" -mindepth 1 -maxdepth 1 -type d ! -name '.*' -exec basename {} \; 2>/dev/null | sort
}

if [ "$LIST_ONLY" -eq 1 ]; then
  echo "workspace: $WS_ROOT"
  echo "=== L0 (.agents/skills) ==="
  list_l0 | sed 's/^/  /'
  echo "=== managed projects ==="
  list_managed | sed 's/^/  /'
  echo "=== L1 per project ==="
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    p="$WS_ROOT/$name/.claude/skills"
    [ -d "$p" ] || continue
    echo "-- $name"
    find "$p" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) -exec basename {} \; 2>/dev/null | sort | sed 's/^/  /'
  done < <(list_managed)
  exit 0
fi

mkdir -p "$L0_CLAUDE"
DRIFT=0

# Ensure workspace .claude/skills mirrors every L0 id
while IFS= read -r id; do
  [ -n "$id" ] || continue
  src="$L0_AGENTS/$id"
  link="$L0_CLAUDE/$id"
  if [ -L "$link" ] || [ -d "$link" ]; then
    if [ -L "$link" ] && [ ! -e "$link/SKILL.md" ]; then
      echo "broken L0 mirror: $link"
      DRIFT=1
      if [ "$CHECK_ONLY" -eq 0 ]; then
        rm -f "$link"
        ln -sfn "../../.agents/skills/$id" "$link"
        echo "  fixed → $link"
      fi
    fi
  else
    echo "missing L0 mirror: $link"
    DRIFT=1
    if [ "$CHECK_ONLY" -eq 0 ]; then
      ln -sfn "../../.agents/skills/$id" "$link"
      echo "  linked → $link"
    fi
  fi
done < <(list_l0)

# Bridge L0 into each managed project for Claude/Cursor project sessions
while IFS= read -r name; do
  [ -n "$name" ] || continue
  proj="$WS_ROOT/$name"
  [ -d "$proj" ] || continue
  dest="$proj/.claude/skills"
  mkdir -p "$dest"
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    # Do not clobber real L1 skill dirs with the same name
    if [ -d "$dest/$id" ] && [ ! -L "$dest/$id" ]; then
      continue
    fi
    target="../../../.agents/skills/$id"
    link="$dest/$id"
    if [ -L "$link" ]; then
      if [ ! -e "$link/SKILL.md" ]; then
        DRIFT=1
        echo "broken bridge $name/$id"
        if [ "$CHECK_ONLY" -eq 0 ]; then
          rm -f "$link"
          ln -sfn "$target" "$link"
          echo "  fixed $name → $id"
        fi
      fi
      continue
    fi
    if [ -e "$link" ]; then
      continue
    fi
    DRIFT=1
    echo "missing bridge $name/$id"
    if [ "$CHECK_ONLY" -eq 0 ]; then
      ln -sfn "$target" "$link"
      echo "  linked $name → $id"
    fi
  done < <(list_l0)
done < <(list_managed)

if [ "$CHECK_ONLY" -eq 1 ]; then
  if [ "$DRIFT" -eq 0 ]; then
    echo "ok: L0 skills bridged into managed projects ($WS_ROOT)"
    exit 0
  fi
  echo "drift: run without --check to apply"
  exit 1
fi

echo "done: L0 skills synced into managed project .claude/skills (discovery bridges)"
echo "SoT remains $L0_AGENTS — do not edit copies under projects"
echo "Grok: ensure ~/.grok/config.toml has paths = [\"$L0_AGENTS\"]"
exit 0
