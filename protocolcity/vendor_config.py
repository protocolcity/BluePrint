"""Generate and heal project vendor/MCP configs from the workspace root (pc-966).

Class D (workspace-path-hardcode audit): absolute paths in ``.mcp.json``,
``.claude/settings*.json``, ``.codex/config.toml``, and ``~/.grok/config.toml``
are legitimate when they point at *this* workspace — but they must be
**generated** (found / adopt / doctor --fix) and rewritten by relocate-root,
never hand-copied between machines.

Plant shape for workspace ``.mcp.json`` matches ``docs/FIRST_RUN.md`` (portable
``python3 -m`` + runtime env paths under the resolved root).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from protocolcity.relocate import (
    PROJECT_VENDOR_REL_PATHS,
    _iter_vendor_config_files,
    rewrite_abs_paths,
)

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent

# Host-home absolute paths that may embed a workspace root (not /usr, /opt, …).
_HOST_ABS_RE = re.compile(
    r"(?:/Users|/home)/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._+\-@%]+)+"
)

# Skip transient / system noise when scanning for foreign workspace residue.
_SKIP_PREFIXES: Tuple[str, ...] = (
    "/private/tmp/",
    "/tmp/",
    "/var/folders/",
    "/private/var/folders/",
    "/Library/",
    "/System/",
    "/Applications/",
    "/opt/",
    "/usr/",
    "/bin/",
    "/sbin/",
)

# Marker: plant/rewrite ownership for canonical workspace MCP.
# Dual-read the retired env key so older planted files still count as ours.
MCP_MARKER = "WORKLANE_RUNTIME_DIR"
MCP_MARKERS = ("WORKLANE_RUNTIME_DIR", "TICKETING_PROTOCOL_RUNTIME_DIR")
STALE_MCP_MODULE = "ticketingprotocol.mcp"


def _templates_dir() -> Path:
    packaged = _PKG_DIR / "templates"
    if packaged.is_dir() and (packaged / "mcp.json").is_file():
        return packaged
    monorepo = _REPO_ROOT / "templates"
    if monorepo.is_dir() and (monorepo / "mcp.json").is_file():
        return monorepo
    return packaged


def workspace_root_norm(workspace: Path) -> str:
    return str(workspace.expanduser().resolve()).rstrip("/")


def render_mcp_json(workspace: Path) -> str:
    """Canonical workspace-root ``.mcp.json`` body with absolute runtime paths."""
    root = workspace_root_norm(workspace)
    tpl_path = _templates_dir() / "mcp.json"
    if tpl_path.is_file():
        body = tpl_path.read_text(encoding="utf-8")
        body = body.replace("{{WORKSPACE_ROOT}}", root)
        # Validate round-trip
        json.loads(body)
        if not body.endswith("\n"):
            body += "\n"
        return body
    # Inline fallback (older package without template file)
    payload = {
        "mcpServers": {
            "worklane": {
                "command": "python3",
                "args": ["-m", "worklane.mcp", "--author", "you"],
                "env": {
                    "TP_AGENT_ID": "you",
                    "WORKLANE_RUNTIME_DIR": (
                        "%s/.protocolcity/worklane" % root
                    ),
                },
            },
            "workforce": {
                "command": "python3",
                "args": ["-m", "workforce.mcp", "--author", "you"],
                "env": {
                    "WORKFORCE_ROSTER": (
                        "%s/.protocolcity/workforce/local/roster.json" % root
                    ),
                },
            },
        }
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def extract_host_abs_paths(text: str) -> List[str]:
    """Absolute user-home paths embedded in a config body."""
    found: List[str] = []
    seen = set()
    for m in _HOST_ABS_RE.finditer(text):
        p = m.group(0).rstrip("\",'")
        # trim trailing JSON punctuation leftovers
        while p and p[-1] in ".,;)]}":
            p = p[:-1]
        if not p or p in seen:
            continue
        seen.add(p)
        found.append(p)
    return found


def path_under_workspace(path: str, workspace_root: str) -> bool:
    root = workspace_root.rstrip("/")
    p = path.rstrip("/")
    return p == root or p.startswith(root + "/")


def is_skippable_host_path(path: str) -> bool:
    for pref in _SKIP_PREFIXES:
        if path.startswith(pref):
            return True
    return False


def foreign_paths_in_text(text: str, workspace_root: str) -> List[str]:
    """Host abs paths that do not live under the current workspace root."""
    root = workspace_root.rstrip("/")
    out: List[str] = []
    for p in extract_host_abs_paths(text):
        if is_skippable_host_path(p):
            continue
        if path_under_workspace(p, root):
            continue
        out.append(p)
    return out


def infer_foreign_root(foreign: Sequence[str], workspace_root: str) -> Optional[str]:
    """Best-effort old workspace root from a set of foreign absolute paths.

    Prefer the longest common prefix that looks like a user workspace
    (parent of a known product folder, or path ending before a vendor file).
    """
    if not foreign:
        return None
    # Normalize and take common prefix of path components
    parts_list = [Path(p).parts for p in foreign]
    if not parts_list:
        return None
    common: List[str] = []
    for comps in zip(*parts_list):
        if len(set(comps)) == 1:
            common.append(comps[0])
        else:
            break
    if len(common) < 3:
        # e.g. ('/', 'Users', 'name') alone is not a workspace
        # try first foreign path's parent that is not under workspace
        sample = foreign[0]
        # Walk up until we leave deep leaf (file) — use dirname chain
        cand = Path(sample)
        # Prefer stopping at known product names' parent
        product_names = {
            "worklane",
            "workforce",
            "ProtocolCity",
            "protocolcity",
            "tradeOS",
            "ticketingprotocol",
            ".protocolcity",
            ".agents",
            ".claude",
            ".codex",
            ".mcp.json",
        }
        while cand.name and cand.name not in ("/", ""):
            if cand.name in product_names:
                parent = str(cand.parent)
                if not path_under_workspace(parent, workspace_root):
                    return parent.rstrip("/")
            cand = cand.parent
        return None
    prefix = str(Path(*common)) if common[0] == "/" else "/" + "/".join(common[1:] if common[0] == "/" else common)
    # On POSIX Path(*('/', 'Users', …)) works
    try:
        prefix = str(Path(*common))
    except Exception:
        prefix = "/" + "/".join(c for c in common if c != "/")
    if path_under_workspace(prefix, workspace_root):
        return None
    # Prefer parent of product folder if common ends mid-product
    p = Path(prefix)
    if p.name in {
        "worklane",
        "workforce",
        "ProtocolCity",
        "protocolcity",
        "tradeOS",
        ".protocolcity",
        ".agents",
        ".claude",
        ".codex",
        "skills",
        "local",
        "bin",
    }:
        prefix = str(p.parent)
    return prefix.rstrip("/") if prefix else None


def scan_vendor_mismatches(workspace: Path) -> List[Dict[str, Any]]:
    """Scan project vendor configs for abs paths outside the workspace root."""
    root = workspace.expanduser().resolve()
    root_s = workspace_root_norm(root)
    issues: List[Dict[str, Any]] = []
    for path in _iter_vendor_config_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            issues.append(
                {
                    "path": str(path),
                    "rel": _rel_or_str(path, root),
                    "ok": False,
                    "error": str(e),
                    "foreign": [],
                }
            )
            continue
        foreign = foreign_paths_in_text(text, root_s)
        if not foreign:
            continue
        old = infer_foreign_root(foreign, root_s)
        issues.append(
            {
                "path": str(path),
                "rel": _rel_or_str(path, root),
                "ok": True,
                "foreign": foreign[:12],
                "foreign_count": len(foreign),
                "inferred_old_root": old,
            }
        )
    return issues


def _rel_or_str(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def mcp_needs_plant(workspace: Path) -> bool:
    """True when workspace-root ``.mcp.json`` is missing."""
    return not (workspace.expanduser().resolve() / ".mcp.json").is_file()


def plant_workspace_mcp(
    workspace: Path,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Plant or refresh workspace-root ``.mcp.json`` from template.

    Idempotent: existing correct file (no foreign roots, contains runtime dir
    under this workspace) is left alone unless ``force``.
    """
    root = workspace.expanduser().resolve()
    root_s = workspace_root_norm(root)
    dest = root / ".mcp.json"
    body = render_mcp_json(root)

    if dest.is_file() and not force:
        try:
            existing = dest.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return {"ok": False, "path": str(dest), "error": str(e)}
        foreign = foreign_paths_in_text(existing, root_s)
        has_marker = any(m in existing for m in MCP_MARKERS)
        # Retired module name is not "correct enough" — rewrite so found/doctor
        # cannot leave Grok/Codex pointed at ticketingprotocol.mcp.
        if STALE_MCP_MODULE in existing:
            pass
        elif not foreign and (
            has_marker
            or '"worklane"' in existing
            or "'worklane'" in existing
        ):
            # Also require that any runtime dir path is under root when present
            if root_s in existing or not has_marker:
                return {
                    "ok": True,
                    "path": str(dest),
                    "action": "skipped",
                    "reason": "existing correct",
                }
        elif not foreign and has_marker and root_s in existing:
            return {
                "ok": True,
                "path": str(dest),
                "action": "skipped",
                "reason": "existing correct",
            }

    dest.write_text(body, encoding="utf-8")
    return {
        "ok": True,
        "path": str(dest),
        "action": "planted" if not force else "rewritten",
    }


def rewrite_mismatched_vendor_files(
    workspace: Path,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite foreign abs roots → current workspace in vendor config files."""
    root = workspace.expanduser().resolve()
    root_s = workspace_root_norm(root)
    issues = scan_vendor_mismatches(root)
    files: List[Dict[str, Any]] = []
    total = 0
    for issue in issues:
        path = Path(issue["path"])
        old = issue.get("inferred_old_root")
        if not old:
            # Fall back: regenerate workspace .mcp.json only
            if path.name == ".mcp.json" and path.parent.resolve() == root:
                if not dry_run:
                    plant_workspace_mcp(root, force=True)
                files.append(
                    {
                        "path": str(path),
                        "action": "regenerated_mcp",
                        "replacements": 0,
                        "dry_run": dry_run,
                    }
                )
                total += 1
            else:
                files.append(
                    {
                        "path": str(path),
                        "action": "skipped_no_old_root",
                        "foreign": issue.get("foreign"),
                        "replacements": 0,
                    }
                )
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            files.append(
                {"path": str(path), "ok": False, "error": str(e), "replacements": 0}
            )
            continue
        new, n = rewrite_abs_paths(raw, old, root_s)
        if n and not dry_run:
            path.write_text(new, encoding="utf-8")
        files.append(
            {
                "path": str(path),
                "action": "rewrote",
                "old_root": old,
                "replacements": n,
                "dry_run": bool(dry_run and n),
            }
        )
        total += n
    return {
        "ok": True,
        "files": files,
        "replacements": total,
        "scanned_issues": len(issues),
        "dry_run": dry_run,
    }


def host_grok_config_path() -> Path:
    """Default host Grok config (``~/.grok/config.toml``)."""
    return Path.home() / ".grok" / "config.toml"


def _workspace_is_live(root: Path) -> bool:
    """True when *root* is the host's active city (same gate as mcp_sync)."""
    try:
        from protocolcity.mcp_sync import _is_live_workspace_root
    except ImportError:
        return False
    return bool(_is_live_workspace_root(root))


def ensure_grok_skills_path(
    workspace: Path,
    *,
    dry_run: bool = False,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Ensure ``~/.grok/config.toml`` ``[skills].paths`` includes L0 shelf.

    Does not create the file from scratch with a full template (user may have
    other settings). Appends a minimal skills section when missing, or rewrites
    a path entry that points at a foreign root.

    Default host home is live-city only. ``rewrite_abs_paths`` replaces *every*
    old workspace prefix in the file — including ``[mcp_servers.worklane]
    command`` — so a temp-city ``doctor --fix`` otherwise poisons Grok MCP
    onto a dead ``/var/folders/.../T/pc-640-*`` path (pc-1370 / pc-1294).
    Pass ``config_path`` to write a specific file from a sandbox (tests).
    """
    root = workspace.expanduser().resolve()
    root_s = workspace_root_norm(root)
    want = "%s/.agents/skills" % root_s
    path = config_path or host_grok_config_path()
    if config_path is None and not _workspace_is_live(root):
        return {
            "ok": True,
            "path": str(path),
            "action": "skipped",
            "reason": (
                "non-live workspace — host Grok config not patched "
                "(pass config_path to override) (pc-1370)"
            ),
            "want": want,
        }
    if not path.is_file():
        if dry_run:
            return {
                "ok": True,
                "path": str(path),
                "action": "would_create",
                "want": want,
                "dry_run": True,
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[skills]\npaths = [\"%s\"]\n" % want,
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(path),
            "action": "created",
            "want": want,
        }
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {"ok": False, "path": str(path), "error": str(e)}

    if want in text or want.replace(root_s, str(root)) in text:
        # Already has correct path
        return {
            "ok": True,
            "path": str(path),
            "action": "skipped",
            "reason": "already has workspace skills path",
            "want": want,
        }

    foreign = foreign_paths_in_text(text, root_s)
    old = infer_foreign_root(foreign, root_s) if foreign else None
    if old and old in text:
        new, n = rewrite_abs_paths(text, old, root_s)
        if n and not dry_run:
            path.write_text(new, encoding="utf-8")
        return {
            "ok": True,
            "path": str(path),
            "action": "rewrote_root",
            "old_root": old,
            "replacements": n,
            "dry_run": dry_run,
            "want": want,
        }

    # No skills paths entry — soft-append
    if "[skills]" not in text:
        addition = "\n[skills]\npaths = [\"%s\"]\n" % want
        if not dry_run:
            path.write_text(text.rstrip() + "\n" + addition, encoding="utf-8")
        return {
            "ok": True,
            "path": str(path),
            "action": "appended_skills",
            "want": want,
            "dry_run": dry_run,
        }

    # Has [skills] but wrong/missing path — leave report for human if complex
    return {
        "ok": True,
        "path": str(path),
        "action": "needs_manual",
        "detail": (
            "has [skills] section without workspace path %s — "
            "add it under paths = [...]" % want
        ),
        "want": want,
    }


def plant_vendor_configs(
    workspace: Path,
    *,
    force: bool = False,
    touch_grok: bool = True,
) -> Dict[str, Any]:
    """Plant workspace MCP (+ optional Grok skills path). Used by found / doctor."""
    root = workspace.expanduser().resolve()
    mcp = plant_workspace_mcp(root, force=force)
    grok: Dict[str, Any] = {"skipped": True}
    if touch_grok:
        grok = ensure_grok_skills_path(root, dry_run=False)
    return {
        "ok": bool(mcp.get("ok", True)),
        "mcp": mcp,
        "grok": grok,
        "workspace": workspace_root_norm(root),
    }


def fix_vendor_configs(
    workspace: Path,
    *,
    force_mcp: bool = False,
    touch_grok: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Plant missing MCP, rewrite mismatched vendor files, heal Grok skills path."""
    root = workspace.expanduser().resolve()
    actions: List[Dict[str, Any]] = []

    if dry_run:
        if mcp_needs_plant(root) or force_mcp:
            actions.append(
                {
                    "action": "would_plant_mcp",
                    "path": str(root / ".mcp.json"),
                }
            )
        rew = rewrite_mismatched_vendor_files(root, dry_run=True)
        actions.append({"action": "rewrite_scan", **rew})
        if touch_grok:
            actions.append(
                {
                    "action": "grok",
                    **ensure_grok_skills_path(root, dry_run=True),
                }
            )
        return {"ok": True, "dry_run": True, "actions": actions}

    mcp = plant_workspace_mcp(root, force=force_mcp)
    actions.append({"action": "mcp", **mcp})
    rew = rewrite_mismatched_vendor_files(root, dry_run=False)
    actions.append({"action": "rewrite", **rew})
    if touch_grok:
        grok = ensure_grok_skills_path(root, dry_run=False)
        actions.append({"action": "grok", **grok})
    return {"ok": True, "dry_run": False, "actions": actions}


def diagnose_vendor_config_findings(workspace: Path) -> List[Dict[str, Any]]:
    """Doctor findings for missing / root-mismatched vendor configs (pc-966)."""
    root = workspace.expanduser().resolve()
    root_s = workspace_root_norm(root)
    findings: List[Dict[str, Any]] = []

    mcp_path = root / ".mcp.json"
    if not mcp_path.is_file():
        findings.append(
            {
                "level": "L0",
                "code": "VENDOR-MCP-MISSING",
                "path": str(mcp_path),
                "status": "missing",
                "detail": (
                    "workspace .mcp.json missing — "
                    "`blueprint doctor --fix` plants WorkLane/WorkForce MCP "
                    "from the resolved workspace root (pc-966)"
                ),
                "fixable": True,
            }
        )
    else:
        try:
            text = mcp_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            findings.append(
                {
                    "level": "L0",
                    "code": "VENDOR-MCP-UNREADABLE",
                    "path": str(mcp_path),
                    "status": "weak",
                    "detail": "could not read .mcp.json: %s" % e,
                    "fixable": False,
                }
            )
            text = ""
        if text:
            foreign = foreign_paths_in_text(text, root_s)
            if foreign:
                findings.append(
                    {
                        "level": "L0",
                        "code": "VENDOR-CONFIG-ROOT-MISMATCH",
                        "path": str(mcp_path),
                        "status": "weak",
                        "detail": (
                            ".mcp.json embeds path(s) outside workspace root %s "
                            "(e.g. %s) — doctor --fix rewrites/regenerates "
                            "(pc-966; relocate-root for full rename)"
                            % (root_s, foreign[0])
                        ),
                        "fixable": True,
                    }
                )
            else:
                # Do not paint VENDOR-MCP ok when the WorkLane command cannot
                # start — MCP-COMMAND-MISSING is the fail from mcp_sync
                # (pc-1425 / GH #33). Skip the ok row so doctor is not green
                # on a dead sibling-checkout path.
                cmd_dead = False
                try:
                    from protocolcity.mcp_sync import stdio_command_resolves

                    data = json.loads(text)
                    servers = data.get("mcpServers")
                    if isinstance(servers, dict):
                        wl = servers.get("worklane")
                        if isinstance(wl, dict):
                            cmd = str(wl.get("command") or "")
                            if cmd and not stdio_command_resolves(cmd):
                                cmd_dead = True
                except (json.JSONDecodeError, TypeError, ValueError):
                    cmd_dead = False
                if not cmd_dead:
                    findings.append(
                        {
                            "level": "L0",
                            "code": "VENDOR-MCP",
                            "path": str(mcp_path),
                            "status": "ok",
                            "detail": ".mcp.json present under workspace root",
                            "fixable": False,
                        }
                    )

    # Other vendor files (settings / codex / project .mcp.json)
    for issue in scan_vendor_mismatches(root):
        if issue.get("path") == str(mcp_path):
            continue  # already reported
        foreign = issue.get("foreign") or []
        findings.append(
            {
                "level": "L0",
                "code": "VENDOR-CONFIG-ROOT-MISMATCH",
                "path": issue["path"],
                "status": "weak",
                "detail": (
                    "vendor config %s embeds path(s) outside workspace root %s "
                    "(e.g. %s) — doctor --fix rewrites when old root is "
                    "inferable (pc-966)"
                    % (
                        issue.get("rel") or issue["path"],
                        root_s,
                        foreign[0] if foreign else "?",
                    )
                ),
                "fixable": bool(issue.get("inferred_old_root")),
            }
        )

    return findings


# Re-export for callers that want the same file set as relocate
VENDOR_REL_PATHS = PROJECT_VENDOR_REL_PATHS
