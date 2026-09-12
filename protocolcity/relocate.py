"""Relocate a founded workspace after folder rename/move (GH #7 · pc-622 · pc-959).

BluePrint must not depend on a fixed folder name (Developer, OneSeo, …).
Absolute paths still land in:

* ``~/.protocolcity/service.json`` + suite LaunchAgent
* ``~/.config/protocolcity/cities.json``
* ``<city>/.protocolcity/workforce/local/roster.json`` (workdir/contract/prompt)
* host LaunchAgents that embed the city path (engines)
* user-global skill bridges (``~/.claude/skills``, ``~/.codex/skills`` symlinks)
* Grok skill path list (``~/.grok/config.toml`` ``[skills].paths``)
* project vendor configs (``.mcp.json``, ``.claude/settings*.json``, ``.codex/config.toml``)

This module rewrites those surfaces old→new, runs ``skills_sync.sh`` when
present, and reports residue it deliberately does not rewrite (skill *content*
prose, CONTRACT Workplace lines, dated research docs). Call **after** the
folder exists at the new path (Finder rename or ``mv`` already done).

``dry_run=True`` prints the full plan without writing or reloading anything.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Classes relocate does **not** rewrite — reported every run so coverage is
# never silently partial (pc-959 / audit §4.2).
RESIDUE_CLASSES: Tuple[str, ...] = (
    "Skill SKILL.md body prose with absolute host paths "
    "(fix SoT under .agents/skills or project .claude/skills, then skills_sync)",
    "Worker CONTRACT/prompt Workplace lines hardcoding a host folder name",
    "Committed docs/research with dated host paths (leave historical)",
    "Homebrew Cellar install paths (reinstall/upgrade BluePrint, not relocate)",
)


# Vendor skill homes that use per-id symlink discovery (not Grok).
DEFAULT_SKILL_HOMES: Tuple[str, ...] = (
    ".claude/skills",
    ".codex/skills",
)


# Project-level vendor config basenames / relative paths under workspace.
PROJECT_VENDOR_REL_PATHS: Tuple[str, ...] = (
    ".mcp.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".codex/config.toml",
)


def _norm(p: Path) -> str:
    return str(p.expanduser().resolve())


def _is_under(path: str, root: str) -> bool:
    path_n = path.rstrip("/")
    root_n = root.rstrip("/")
    return path_n == root_n or path_n.startswith(root_n + "/")


def rewrite_abs_paths(text: str, old_root: str, new_root: str) -> Tuple[str, int]:
    """Replace absolute old_root prefix with new_root. Count replacements."""
    if not old_root or old_root == new_root:
        return text, 0
    # Prefer longer/more specific first; also handle /private/var vs /var if needed
    variants = [old_root]
    # macOS sometimes stores /private/var/… vs /var/…
    if old_root.startswith("/var/"):
        variants.append("/private" + old_root)
    if old_root.startswith("/private/var/"):
        variants.append(old_root[len("/private") :])
    # unique preserve order
    seen = set()
    ordered = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            ordered.append(v)
    n = 0
    out = text
    for v in ordered:
        if v in out:
            c = out.count(v)
            out = out.replace(v, new_root)
            n += c
    return out, n


def rewrite_json_file(
    path: Path,
    old_root: str,
    new_root: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "ok": True, "skipped": "missing", "replacements": 0}
    raw = path.read_text(encoding="utf-8")
    new, n = rewrite_abs_paths(raw, old_root, new_root)
    if n and not dry_run:
        path.write_text(new, encoding="utf-8")
    return {
        "path": str(path),
        "ok": True,
        "replacements": n,
        "dry_run": bool(dry_run and n),
    }


def rewrite_text_file(
    path: Path,
    old_root: str,
    new_root: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite any UTF-8 text file that embeds old_root (toml/json/md)."""
    if not path.is_file():
        return {"path": str(path), "ok": True, "skipped": "missing", "replacements": 0}
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {"path": str(path), "ok": False, "error": str(e), "replacements": 0}
    new, n = rewrite_abs_paths(raw, old_root, new_root)
    if n and not dry_run:
        path.write_text(new, encoding="utf-8")
    return {
        "path": str(path),
        "ok": True,
        "replacements": n,
        "dry_run": bool(dry_run and n),
    }


def migrate_registry(
    old_root: Path,
    new_root: Path,
    *,
    name: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Update cities.json: drop old path rows; register new path + display name."""
    from protocolcity.registry import list_cities, register_city, unregister_city

    try:
        old_s = _norm(old_root) if old_root.exists() else str(old_root.expanduser())
    except OSError:
        old_s = str(old_root.expanduser())
    new_s = _norm(new_root)
    display = (name or new_root.name).strip() or new_root.name
    changed = 0
    would_touch: List[str] = []
    for row in list_cities() or []:
        if not isinstance(row, dict):
            continue
        p = str(row.get("path") or "").strip()
        if not p:
            continue
        try:
            pn = _norm(Path(p))
        except Exception:
            pn = p
        if pn == old_s or p == old_s or _is_under(p, old_s) or _is_under(pn, old_s):
            would_touch.append(p)
            if not dry_run:
                try:
                    unregister_city(Path(p))
                    changed += 1
                except Exception:
                    pass
            else:
                changed += 1
    entry: Any = None
    if dry_run:
        entry = {"path": new_s, "name": display, "dry_run": True}
    else:
        entry = register_city(new_root, name=display)
    return {
        "ok": True,
        "old": old_s,
        "new": new_s,
        "name": display,
        "registry_rows_touched": changed,
        "would_touch": would_touch if dry_run else None,
        "entry": entry,
        "dry_run": dry_run,
    }


def migrate_roster(
    city_root: Path,
    old_root: str,
    new_root: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite workdir/contract/prompt abs paths under city roster."""
    roster = (
        city_root.expanduser().resolve()
        / ".protocolcity"
        / "workforce"
        / "local"
        / "roster.json"
    )
    return rewrite_json_file(roster, old_root, new_root, dry_run=dry_run)


def migrate_service_state(
    old_root: str,
    new_root: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    from protocolcity import service as svc

    path = svc.STATE_PATH
    return rewrite_json_file(path, old_root, new_root, dry_run=dry_run)


def migrate_user_launchagents(
    old_root: str,
    new_root: str,
    *,
    reload: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite plists under ~/Library/LaunchAgents that embed old_root."""
    agents = Path.home() / "Library" / "LaunchAgents"
    if not agents.is_dir():
        return {"ok": True, "files": [], "reloaded": []}
    files: List[Dict[str, Any]] = []
    reloaded: List[str] = []
    uid = os.getuid()
    domain = "gui/%d" % uid
    for plist in sorted(agents.glob("*.plist")):
        try:
            raw = plist.read_bytes()
        except OSError as e:
            files.append({"path": str(plist), "ok": False, "error": str(e)})
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # binary plist
            try:
                data = plistlib.loads(raw)
            except Exception as e:
                files.append({"path": str(plist), "ok": False, "error": str(e)})
                continue
            blob = json.dumps(data, default=str)
            if old_root not in blob and old_root.replace("/private", "") not in blob:
                continue
            # load, walk, replace strings
            def walk(o: Any) -> Any:
                if isinstance(o, str):
                    s, _ = rewrite_abs_paths(o, old_root, new_root)
                    return s
                if isinstance(o, list):
                    return [walk(x) for x in o]
                if isinstance(o, dict):
                    return {k: walk(v) for k, v in o.items()}
                return o

            new_data = walk(data)
            label = str(new_data.get("Label") or plist.stem)
            if not dry_run:
                body = plistlib.dumps(new_data, sort_keys=False)
                plist.write_bytes(body)
            files.append(
                {
                    "path": str(plist),
                    "ok": True,
                    "label": label,
                    "binary": True,
                    "dry_run": dry_run,
                }
            )
            if reload and label and not dry_run:
                subprocess.run(
                    ["launchctl", "bootout", "%s/%s" % (domain, label)],
                    capture_output=True,
                )
                subprocess.run(
                    ["launchctl", "bootstrap", domain, str(plist)],
                    capture_output=True,
                )
                reloaded.append(label)
            continue

        if old_root not in text and "/private" + old_root not in text:
            # also check without private prefix mismatch
            if not any(
                v in text
                for v in (old_root, old_root.replace("/private", "", 1))
            ):
                continue
        new, n = rewrite_abs_paths(text, old_root, new_root)
        if n == 0:
            continue
        if not dry_run:
            plist.write_text(new, encoding="utf-8")
        # label from file
        label = None
        m = re.search(r"<key>Label</key>\s*<string>([^<]+)</string>", new)
        if m:
            label = m.group(1)
        files.append(
            {
                "path": str(plist),
                "ok": True,
                "replacements": n,
                "label": label,
                "binary": False,
                "dry_run": dry_run,
            }
        )
        if reload and label and not dry_run:
            subprocess.run(
                ["launchctl", "bootout", "%s/%s" % (domain, label)],
                capture_output=True,
            )
            r = subprocess.run(
                ["launchctl", "bootstrap", domain, str(plist)],
                capture_output=True,
            )
            if r.returncode == 0:
                reloaded.append(label)
    return {"ok": True, "files": files, "reloaded": reloaded, "dry_run": dry_run}


def _skill_homes(home: Optional[Path] = None) -> List[Path]:
    """Resolve user-global skill bridge directories (Claude/Codex style)."""
    base = home or Path.home()
    env = (os.environ.get("SKILLS_SYNC_USER_HOMES") or "").strip()
    if env:
        return [Path(p).expanduser() for p in env.split() if p.strip()]
    return [base / rel for rel in DEFAULT_SKILL_HOMES]


def migrate_skill_home_symlinks(
    old_root: str,
    new_root: str,
    *,
    homes: Optional[Sequence[Path]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite user-global skill symlinks whose target embeds old_root (pc-959).

    Broken links still count — ``os.readlink`` does not need the target to exist.
    Real (non-symlink) directories are never clobbered.
    """
    fixed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for home in homes if homes is not None else _skill_homes():
        if not home.is_dir():
            skipped.append({"path": str(home), "reason": "missing"})
            continue
        try:
            entries = sorted(home.iterdir(), key=lambda p: p.name)
        except OSError as e:
            skipped.append({"path": str(home), "reason": str(e)})
            continue
        for entry in entries:
            if not entry.is_symlink():
                continue
            try:
                target = os.readlink(entry)
            except OSError as e:
                skipped.append({"path": str(entry), "reason": str(e)})
                continue
            new_target, n = rewrite_abs_paths(target, old_root, new_root)
            if n == 0:
                continue
            if not dry_run:
                try:
                    entry.unlink()
                    entry.symlink_to(new_target)
                except OSError as e:
                    fixed.append(
                        {
                            "path": str(entry),
                            "ok": False,
                            "error": str(e),
                            "from": target,
                            "to": new_target,
                        }
                    )
                    continue
            fixed.append(
                {
                    "path": str(entry),
                    "ok": True,
                    "from": target,
                    "to": new_target,
                    "replacements": n,
                    "dry_run": dry_run,
                }
            )
    return {
        "ok": True,
        "rewritten": fixed,
        "skipped_homes": skipped,
        "count": len([f for f in fixed if f.get("ok")]),
        "dry_run": dry_run,
    }


def migrate_grok_skills_paths(
    old_root: str,
    new_root: str,
    *,
    config_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite ``~/.grok/config.toml`` when it embeds old_root (skills.paths)."""
    path = config_path or (Path.home() / ".grok" / "config.toml")
    return rewrite_text_file(path, old_root, new_root, dry_run=dry_run)


def _iter_vendor_config_files(workspace: Path) -> List[Path]:
    """Workspace-root + one-level project vendor configs (no deep tree walk)."""
    found: List[Path] = []
    root = workspace.expanduser().resolve()
    for rel in PROJECT_VENDOR_REL_PATHS:
        p = root / rel
        if p.is_file():
            found.append(p)
    try:
        children = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError:
        return found
    skip = {
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "exports",
        ".venv",
        "venv",
    }
    for child in children:
        if not child.is_dir() or child.name.startswith(".") or child.name in skip:
            continue
        for rel in PROJECT_VENDOR_REL_PATHS:
            p = child / rel
            if p.is_file():
                found.append(p)
    return found


def migrate_project_vendor_configs(
    workspace: Path,
    old_root: str,
    new_root: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite abs paths in project-level MCP/settings/codex configs."""
    paths = _iter_vendor_config_files(workspace)
    files: List[Dict[str, Any]] = []
    total = 0
    for path in paths:
        rec = rewrite_text_file(path, old_root, new_root, dry_run=dry_run)
        if rec.get("replacements"):
            files.append(rec)
            total += int(rec.get("replacements") or 0)
    return {
        "ok": True,
        "files": files,
        "replacements": total,
        "scanned": len(paths),
        "dry_run": dry_run,
    }


def find_skills_sync_script(workspace: Path) -> Optional[Path]:
    """Locate skills_sync.sh under workspace (parcel ProtocolCity or root scripts/)."""
    root = workspace.expanduser().resolve()
    candidates = (
        root / "ProtocolCity" / "scripts" / "skills_sync.sh",
        root / "scripts" / "skills_sync.sh",
        root / "protocolcity" / "scripts" / "skills_sync.sh",
    )
    for c in candidates:
        if c.is_file():
            return c
    return None


def run_skills_sync(
    workspace: Path,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Invoke skills_sync.sh so bridges re-point at the new root shelf."""
    script = find_skills_sync_script(workspace)
    if script is None:
        return {
            "ok": True,
            "skipped": "skills_sync.sh not found under workspace",
            "script": None,
        }
    root_s = _norm(workspace)
    cmd = ["bash", str(script)]
    if dry_run:
        cmd.append("--check")
    env = dict(os.environ)
    env["WORKSPACE_ROOT"] = root_s
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(script.parent),
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {
            "ok": False,
            "script": str(script),
            "error": str(e),
            "dry_run": dry_run,
        }
    # --check exits 1 on drift; that is informative, not relocate failure
    ok = proc.returncode == 0 or (dry_run and proc.returncode == 1)
    return {
        "ok": ok or dry_run,
        "script": str(script),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
        "dry_run": dry_run,
        "mode": "check" if dry_run else "apply",
    }


def residue_report() -> Dict[str, Any]:
    """Explicit non-coverage — what one command will not rewrite."""
    return {
        "ok": True,
        "classes": list(RESIDUE_CLASSES),
        "note": (
            "relocate-root rewrites coordination + bridge paths only; "
            "prose hardcodes need a one-time content pass or pc-956 lint"
        ),
    }


def relocate_root(
    old_root: Path,
    new_root: Path,
    *,
    name: Optional[str] = None,
    reload_agents: bool = True,
    reinstall_suite_service: bool = True,
    run_sync: bool = True,
    dry_run: bool = False,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Full coordination + bridge relocate after workspace folder rename/move.

    Covers registry, service state, roster, LaunchAgents, skill-home symlinks,
    Grok skills.paths, project vendor configs; optionally runs skills_sync.
    Always includes a residue report for classes deliberately left alone.
    """
    new_p = new_root.expanduser().resolve()
    if not new_p.is_dir():
        return {
            "ok": False,
            "error": "new workspace root missing: %s (rename/mv first)" % new_p,
        }
    old_p = old_root.expanduser()
    try:
        old_s = str(old_p.resolve()) if old_p.exists() else str(old_p.expanduser())
    except OSError:
        old_s = str(old_p)
    # Prefer absolute form user gave if resolve fails on missing path
    if not old_s.startswith("/"):
        old_s = str(Path(old_s).expanduser())
    new_s = _norm(new_p)
    if old_s.rstrip("/") == new_s.rstrip("/"):
        return {"ok": False, "error": "old and new roots are the same path"}

    steps: Dict[str, Any] = {}
    steps["registry"] = migrate_registry(old_p, new_p, name=name, dry_run=dry_run)
    steps["service_state"] = migrate_service_state(old_s, new_s, dry_run=dry_run)
    steps["roster"] = migrate_roster(new_p, old_s, new_s, dry_run=dry_run)
    steps["launchagents"] = migrate_user_launchagents(
        old_s, new_s, reload=reload_agents and not dry_run, dry_run=dry_run
    )
    steps["skill_home_symlinks"] = migrate_skill_home_symlinks(
        old_s, new_s, dry_run=dry_run
    )
    steps["grok_config"] = migrate_grok_skills_paths(old_s, new_s, dry_run=dry_run)
    steps["project_vendor_configs"] = migrate_project_vendor_configs(
        new_p, old_s, new_s, dry_run=dry_run
    )

    suite: Dict[str, Any] = {"skipped": True}
    if reinstall_suite_service:
        if dry_run:
            suite = {
                "ok": True,
                "dry_run": True,
                "plan": "would reinstall suite service on %s" % new_s,
            }
        else:
            try:
                from protocolcity import service as svc

                if svc.is_macos():
                    suite = svc.install_service(new_p, quiet=quiet)
                else:
                    suite = {"ok": True, "skipped": "not-macos"}
            except Exception as e:
                suite = {"ok": False, "error": str(e)}
    steps["suite_service"] = suite

    if run_sync:
        steps["skills_sync"] = run_skills_sync(new_p, dry_run=dry_run)
    else:
        steps["skills_sync"] = {"ok": True, "skipped": "run_sync=False"}

    steps["residue"] = residue_report()

    critical = (
        "registry",
        "service_state",
        "roster",
        "launchagents",
        "skill_home_symlinks",
        "grok_config",
        "project_vendor_configs",
        "suite_service",
    )
    ok = all((steps.get(k) or {}).get("ok", True) is not False for k in critical)
    # skills_sync failure is soft when apply mode (bridges may still be fixed)
    if not quiet:
        verb = "Would relocate" if dry_run else "Relocated"
        print("%s workspace coordination + bridge surfaces" % verb)
        print("  from: %s" % old_s)
        print("  to:   %s" % new_s)
        print("  name: %s" % (name or new_p.name))
        if dry_run:
            print("  mode: dry-run (no writes)")
        la = steps.get("launchagents") or {}
        print(
            "  launchagents rewritten: %d  reloaded: %s"
            % (len(la.get("files") or []), ", ".join(la.get("reloaded") or []) or "—")
        )
        rost = steps.get("roster") or {}
        print("  roster path rewrites: %s" % rost.get("replacements", 0))
        sk = steps.get("skill_home_symlinks") or {}
        print("  skill-home symlinks: %s" % sk.get("count", 0))
        gc = steps.get("grok_config") or {}
        print("  grok config rewrites: %s" % gc.get("replacements", 0))
        pvc = steps.get("project_vendor_configs") or {}
        print(
            "  project vendor configs: %s file(s), %s replacement(s)"
            % (len(pvc.get("files") or []), pvc.get("replacements", 0))
        )
        if suite.get("ok") and not suite.get("skipped") and not dry_run:
            print("  suite service: installed on new root")
        elif suite.get("dry_run"):
            print("  suite service: %s" % suite.get("plan"))
        elif suite.get("error"):
            print("  suite service: %s" % suite.get("error"))
        ss = steps.get("skills_sync") or {}
        if ss.get("skipped"):
            print("  skills_sync: %s" % ss.get("skipped"))
        else:
            print(
                "  skills_sync: %s (exit %s)"
                % (ss.get("mode") or "apply", ss.get("returncode"))
            )
        print("  residue (not rewritten):")
        for line in RESIDUE_CLASSES:
            print("    · %s" % line)
    return {
        "ok": ok,
        "old": old_s,
        "new": new_s,
        "name": name or new_p.name,
        "dry_run": dry_run,
        "steps": steps,
        "residue": list(RESIDUE_CLASSES),
    }
