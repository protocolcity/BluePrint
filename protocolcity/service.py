"""macOS Login LaunchAgent — keep BluePrint suite running (pc-433).

One user agent runs ``blueprint serve --root <workspace>`` (engines default
on when root is set). Closing the terminal no longer kills the suite.

Windows: install returns a clear not-supported receipt (pc-383 later).
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

LABEL = "com.protocolcity.suite"
ISOLATED_LABEL = "com.protocolcity.suite.test"
ISOLATED_DEFAULT_PORT = 18801
PRODUCTION_PORTS = frozenset((8797, 8799, 8801))
# Legacy pre-fold-C agent (pc-575): census is in-process; unload on stop/heal.
CITYLENS_LABEL = "com.protocolcity.citylens"
# Legacy three-lane install (pc-1469): standalone Map lane, folded into the
# single consolidated blueprint-overview process on :8803.
BLUEPRINT_MAP_LABEL = "com.protocolcity.blueprint-map"
# Every launch agent a pre-consolidation host may still have running.
LEGACY_AGENT_LABELS = (LABEL, BLUEPRINT_MAP_LABEL, CITYLENS_LABEL)
AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_NAME = "%s.plist" % LABEL
CITYLENS_PLIST_NAME = "%s.plist" % CITYLENS_LABEL
STATE_DIR = Path.home() / ".protocolcity"
STATE_PATH = STATE_DIR / "service.json"


def isolated_config_dir() -> Path:
    """Config home used only by ``--isolated`` service repros."""
    raw = (os.environ.get("PROTOCOLCITY_ISOLATED_CONFIG_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".protocolcity-test"


def _service_label(isolated: bool = False) -> str:
    return ISOLATED_LABEL if isolated else LABEL


def _service_state_path(isolated: bool = False) -> Path:
    return (isolated_config_dir() / "service.json") if isolated else STATE_PATH


def is_macos() -> bool:
    return sys.platform == "darwin"


def plist_path(isolated: bool = False) -> Path:
    return AGENTS_DIR / ("%s.plist" % _service_label(isolated))


def citylens_plist_path() -> Path:
    """Legacy host LaunchAgent path (pc-575 cutover — not installed by package)."""
    return AGENTS_DIR / CITYLENS_PLIST_NAME


def _uid() -> int:
    try:
        return int(os.getuid())
    except Exception:
        return 501


def _gui_domain() -> str:
    return "gui/%d" % _uid()


def portable_interpreter(exe: str) -> str:
    """Rewrite Homebrew ``Cellar/blueprint/<ver>/…`` to ``opt/blueprint/…``.

    ``sys.executable`` inside the formula venv is the versioned Cellar path.
    Brew upgrade deletes that keg; launchd then dies on reboot with
    EX_CONFIG 78 (pc-1417). ``opt/blueprint`` is the stable keg symlink.
    pc-694 still heals after death; this prevents the death (pc-1418).
    """
    try:
        parts = Path(exe).parts
        for i, part in enumerate(parts):
            if (
                part == "Cellar"
                and i + 2 < len(parts)
                and parts[i + 1] == "blueprint"
            ):
                prefix = Path(*parts[:i]) if i else Path(parts[0])
                rest = parts[i + 3 :]
                if not rest:
                    break
                opt = prefix.joinpath("opt", "blueprint", *rest)
                if opt.exists():
                    return str(opt)
                break
    except Exception:
        pass
    return exe


def resolve_cli_argv() -> List[str]:
    """Resolve how launchd should invoke the CLI.

    Prefer ``python -m protocolcity.cli`` when *this* interpreter can import
    the package (editable checkout or venv). That beats a stale Homebrew
    ``protocolcity`` on PATH that lacks newer subcommands (``service``,
    ``stop`` bootout, …) and was leaving the suite dead after upgrade/stop.

    Homebrew interpreters are rewritten through ``portable_interpreter`` so
    the login plist does not pin a Cellar version that brew will delete.
    """
    try:
        import protocolcity  # noqa: F401

        # Confirm cli entry exists
        from protocolcity import cli as _cli  # noqa: F401

        return [portable_interpreter(sys.executable), "-m", "protocolcity.cli"]
    except Exception:
        pass
    for name in ("blueprint", "protocolcity"):
        path = shutil.which(name)
        if path:
            return [path]
    return [portable_interpreter(sys.executable), "-m", "protocolcity.cli"]


def resolve_dogfood_suite_dir(
    explicit: Optional[Path] = None,
    *,
    workspace: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve ProtocolCity repo root for suite dogfood (BLUEPRINT_SUITE_DIR).

    Accepts the repo root (…/ProtocolCity) or the suite/ folder itself.
    Returns None when the path is missing or not a BluePrint source tree.
    """
    candidates: List[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env = (os.environ.get("BLUEPRINT_SUITE_DIR") or "").strip()
    if env:
        candidates.append(Path(env))
    if workspace is not None:
        candidates.append(Path(workspace) / "ProtocolCity")
    for raw in candidates:
        try:
            p = raw.expanduser().resolve()
        except OSError:
            continue
        if (p / "suite" / "serve.py").is_file():
            return p
        if p.name == "suite" and (p / "serve.py").is_file():
            return p.parent
    return None


def state_suite_dir(*, isolated: bool = False) -> Optional[Path]:
    """Persisted dogfood suite dir from ~/.protocolcity/service.json (if any)."""
    raw = str((_read_state(isolated=isolated) or {}).get("suite_dir") or "").strip()
    if not raw:
        return None
    return resolve_dogfood_suite_dir(Path(raw))


def render_plist(
    *,
    root: Path,
    port: int = 8801,
    program: Optional[List[str]] = None,
    isolated: bool = False,
    suite_dir: Optional[Path] = None,
) -> bytes:
    """Build a KeepAlive user LaunchAgent plist (no hard-coded ~/Developer)."""
    root = root.expanduser().resolve()
    log_dir = (
        isolated_config_dir() / "logs"
        if isolated
        else root / ".protocolcity" / "logs"
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    prog = list(program or resolve_cli_argv())
    args = prog + [
        "serve",
        "--root",
        str(root),
        "--port",
        str(int(port)),
    ]
    if isolated:
        # Service-lifecycle repros exercise launchd without ever binding or
        # spawning the production WorkLane / WorkForce ports.
        args.append("--no-engines")
    label = _service_label(isolated)
    env = {
        "SUITE_CITY_ROOT": str(root),
        "PATH": os.environ.get("PATH") or "/usr/bin:/bin:/usr/sbin:/sbin",
    }
    dogfood_root = resolve_dogfood_suite_dir(suite_dir, workspace=root)
    if dogfood_root is not None:
        # Founder / dogfood host: Map glass loads from git tree (pc-788 / dogfood).
        # Survives brew reinstall of Cellar package; chrome shows +dogfood.
        env["BLUEPRINT_SUITE_DIR"] = str(dogfood_root)
    if len(prog) >= 3 and prog[-2:] == ["-m", "protocolcity.cli"]:
        # Source checkout only: launchd cwd is the workspace, so PYTHONPATH must
        # point at the git tree for ``python -m protocolcity.cli`` (dogfood).
        # Packaged installs (site-packages / Cellar) must NOT bake PYTHONPATH —
        # doing so from a dogfood shell pinned Map to +dogfood forever (pc-872).
        # Explicit --dogfood suite_dir is the supported Cellar+source hybrid.
        pkg_file = str(Path(__file__).resolve()).replace("\\", "/").lower()
        packaged = (
            "/site-packages/" in pkg_file
            or "/dist-packages/" in pkg_file
            or "/cellar/" in pkg_file
        )
        if not packaged:
            package_root = str(Path(__file__).resolve().parents[1])
            inherited_pythonpath = (os.environ.get("PYTHONPATH") or "").strip()
            env["PYTHONPATH"] = (
                package_root
                if not inherited_pythonpath
                else os.pathsep.join((package_root, inherited_pythonpath))
            )
        elif dogfood_root is not None:
            # Hybrid: Cellar interpreter runs CLI, suite glass from source tree.
            # suite/ must be importable for serve.py relative imports.
            suite_pkg = str(dogfood_root / "suite")
            inherited_pythonpath = (os.environ.get("PYTHONPATH") or "").strip()
            env["PYTHONPATH"] = (
                suite_pkg
                if not inherited_pythonpath
                else os.pathsep.join((suite_pkg, inherited_pythonpath))
            )
    if isolated:
        env["PROTOCOLCITY_CONFIG_DIR"] = str(isolated_config_dir())
        env["PROTOCOLCITY_SERVICE_MODE"] = "isolated"
    # pc-536: Background (not Interactive) — Interactive login agents without a
    # real UI session get efficiency SIGTERM thrash on modern macOS, which then
    # cascade-kills engine children. AbandonProcessGroup so suite death does
    # not process-group kill WorkLane/etc. we may have spawned. ExitTimeOut
    # gives serve a moment to exit cleanly; ThrottleInterval caps restart storms.
    data = {
        "Label": label,
        "ProgramArguments": args,
        "WorkingDirectory": str(root),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "AbandonProcessGroup": True,
        "ExitTimeOut": 30,
        "ThrottleInterval": 30,
        "StandardOutPath": str(log_dir / "suite-service.out"),
        "StandardErrorPath": str(log_dir / "suite-service.err"),
        "EnvironmentVariables": env,
    }
    return plistlib.dumps(data, sort_keys=False)


def _write_state(
    root: Path,
    port: int,
    *,
    isolated: bool = False,
    suite_dir: Optional[Path] = None,
) -> None:
    state_path = _service_state_path(isolated)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    payload: Dict[str, Any] = {
        "label": _service_label(isolated),
        "root": str(root.expanduser().resolve()),
        "port": int(port),
        "plist": str(plist_path(isolated)),
        "isolated": bool(isolated),
    }
    dogfood_root = resolve_dogfood_suite_dir(suite_dir, workspace=root)
    if dogfood_root is not None:
        payload["suite_dir"] = str(dogfood_root)
        payload["dogfood"] = True
    state_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_state(*, isolated: bool = False) -> Dict[str, Any]:
    import json

    state_path = _service_state_path(isolated)
    if not state_path.is_file():
        return {}
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
    )


def bootout_agent(
    *,
    quiet: bool = False,
    isolated: bool = False,
) -> Dict[str, Any]:
    """Unload the suite LaunchAgent if present (so KeepAlive does not revive).

    Leaves the plist on disk when present so ``service install`` / bootstrap
    can bring it back. ``stop`` uses this; use ``uninstall_service`` to delete.
    """
    if not is_macos():
        return {"ok": True, "skipped": "not-macos"}
    domain = _gui_domain()
    label = _service_label(isolated)
    path = plist_path(isolated)
    # Prefer modern bootout; fall back to unload.
    r = launchctl("bootout", "%s/%s" % (domain, label))
    if r.returncode != 0:
        r2 = launchctl("unload", str(path))
        if not quiet and r2.returncode != 0 and r.returncode != 0:
            # Not loaded is fine
            msg = (r.stderr or r.stdout or r2.stderr or "").strip()
            if "No such process" not in msg and "Could not find" not in msg:
                pass
    return {
        "ok": True,
        "label": label,
        "domain": domain,
        "bootout_rc": r.returncode,
        "plist_kept": path.is_file(),
    }


def bootout_citylens_agent(
    *,
    quiet: bool = False,
    remove_plist: bool = False,
) -> Dict[str, Any]:
    """Unload legacy ``com.protocolcity.citylens`` (pc-575).

    Census runs in-process inside the suite — a separate :8796 LaunchAgent is
    dual-ownership debt. Idempotent when absent. ``remove_plist`` deletes the
    user LaunchAgents file so reinstall cannot revive the leftover agent.
    """
    if not is_macos():
        return {"ok": True, "skipped": "not-macos"}
    domain = _gui_domain()
    path = citylens_plist_path()
    r = launchctl("bootout", "%s/%s" % (domain, CITYLENS_LABEL))
    if r.returncode != 0 and path.is_file():
        launchctl("unload", str(path))
    removed = False
    if remove_plist and path.is_file():
        try:
            path.unlink()
            removed = True
        except OSError:
            pass
    if not quiet and (r.returncode == 0 or removed or path.is_file()):
        print(
            "Legacy citylens agent %s: bootout rc=%s%s"
            % (
                CITYLENS_LABEL,
                r.returncode,
                "; plist removed" if removed else "",
            )
        )
    return {
        "ok": True,
        "label": CITYLENS_LABEL,
        "domain": domain,
        "bootout_rc": r.returncode,
        "plist_removed": removed,
        "plist_exists": path.is_file(),
    }


def citylens_agent_status() -> Dict[str, Any]:
    """Best-effort: is the legacy citylens LaunchAgent still loaded?"""
    path = citylens_plist_path()
    loaded = False
    if is_macos():
        r = launchctl("print", "%s/%s" % (_gui_domain(), CITYLENS_LABEL))
        loaded = r.returncode == 0
    return {
        "ok": True,
        "macos": is_macos(),
        "label": CITYLENS_LABEL,
        "plist": str(path),
        "plist_exists": path.is_file(),
        "loaded": loaded,
    }


def retire_legacy_agents(
    *,
    workspace: Path,
    quiet: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Boot out and retire pre-consolidation launch agents (pc-1469).

    Detects each of ``LEGACY_AGENT_LABELS`` by plist presence and by
    ``launchctl print``, boots each found agent out, and moves its plist to
    ``<workspace>/local/blueprint/retired-services/<date>/`` — never deletes.
    Idempotent: nothing found on a second run. ``dry_run`` only reports what
    would happen; it boots nothing out and moves nothing.
    """
    workspace = Path(workspace)
    domain = _gui_domain()
    retire_dir: Optional[Path] = None
    agents: List[Dict[str, Any]] = []
    for label in LEGACY_AGENT_LABELS:
        path = AGENTS_DIR / ("%s.plist" % label)
        plist_present = path.is_file()
        loaded = False
        if is_macos():
            loaded = launchctl("print", "%s/%s" % (domain, label)).returncode == 0
        found = plist_present or loaded
        entry: Dict[str, Any] = {
            "label": label,
            "plist_present": plist_present,
            "loaded": loaded,
            "found": found,
        }
        if found and not dry_run:
            if is_macos():
                bootout_rc = launchctl("bootout", "%s/%s" % (domain, label)).returncode
                entry["bootout_rc"] = bootout_rc
                if loaded and bootout_rc != 0:
                    # Agent is still loaded and launchd refused to unload it —
                    # moving the plist now would strand a running legacy
                    # process launchd still owns. Stop before touching disk.
                    raise RuntimeError(
                        "Legacy agent %s is loaded but bootout failed (rc=%d); "
                        "not moving its plist. Resolve manually (for example "
                        "`launchctl bootout %s/%s`) and re-run "
                        "`blueprint upgrade`." % (label, bootout_rc, domain, label)
                    )
            if plist_present:
                if retire_dir is None:
                    retire_dir = (
                        workspace
                        / "local/blueprint/retired-services"
                        / datetime.now().strftime("%Y-%m-%d")
                    )
                    retire_dir.mkdir(parents=True, exist_ok=True)
                destination = retire_dir / path.name
                if destination.exists():
                    destination = retire_dir / (
                        "%s-%d%s" % (path.stem, int(time.time()), path.suffix)
                    )
                shutil.move(str(path), str(destination))
                entry["retired_to"] = str(destination)
        agents.append(entry)
        if not quiet and found:
            print(
                "Legacy agent %s: %s"
                % (label, "would retire" if dry_run else "retired")
            )
    return {"retired_dir": str(retire_dir) if retire_dir else None, "agents": agents}


def is_ephemeral_root(root: Path) -> bool:
    """True for OS temp trees — never a durable login-service workspace.

    Catches /var/folders/…/T/tmp*, /tmp, $TMPDIR (pytest/brew/tooling junk).
    Permanent installs must refuse these unless allow_ephemeral=True.
    """
    try:
        s = str(root.expanduser().resolve())
    except OSError:
        s = str(root)
    low = s.replace("\\", "/").lower()
    if "/var/folders/" in low and ("/t/" in low or "/tmp" in low):
        return True
    if low.startswith("/tmp/") or low == "/tmp":
        return True
    if low.startswith("/private/tmp/") or low == "/private/tmp":
        return True
    tmp = (os.environ.get("TMPDIR") or os.environ.get("TEMP") or "").strip()
    if tmp:
        try:
            t = str(Path(tmp).expanduser().resolve()).replace("\\", "/").lower()
            if t and (low == t or low.startswith(t.rstrip("/") + "/")):
                return True
        except OSError:
            pass
    return False


def _plist_root(*, isolated: bool = False) -> Optional[str]:
    """Read --root from installed LaunchAgent ProgramArguments."""
    path = plist_path(isolated)
    if not path.is_file():
        return None
    try:
        data = plistlib.loads(path.read_bytes())
    except Exception:
        return None
    args = data.get("ProgramArguments") or []
    if not isinstance(args, list):
        return None
    for i, a in enumerate(args):
        if str(a) == "--root" and i + 1 < len(args):
            return str(args[i + 1])
    env = data.get("EnvironmentVariables") or {}
    if isinstance(env, dict) and env.get("SUITE_CITY_ROOT"):
        return str(env["SUITE_CITY_ROOT"])
    return None


def _plist_argv0(*, isolated: bool = False) -> Optional[str]:
    """Read ProgramArguments[0] (the interpreter) from the installed plist."""
    path = plist_path(isolated)
    if not path.is_file():
        return None
    try:
        data = plistlib.loads(path.read_bytes())
    except Exception:
        return None
    args = data.get("ProgramArguments") or []
    if not isinstance(args, list) or not args:
        return None
    return str(args[0])


def installed_root(*, isolated: bool = False) -> Optional[Path]:
    """Best-effort workspace path from service.json then plist."""
    state = _read_state(isolated=isolated)
    raw = str((state or {}).get("root") or "").strip() or (
        _plist_root(isolated=isolated) or ""
    )
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return Path(raw)


def _pick_registry_root() -> Optional[Path]:
    """First registered **durable** city path that still exists on disk.

    Skips OS temp trees (pytest/setup junk) so heal never re-homes onto another
    ephemeral path (pc-832).
    """
    try:
        from protocolcity.registry import list_cities

        for row in list_cities() or []:
            if not isinstance(row, dict):
                continue
            p = Path(str(row.get("path") or "")).expanduser()
            try:
                if not p.is_dir():
                    continue
                resolved = p.resolve()
                if is_ephemeral_root(resolved):
                    continue
                return resolved
            except OSError:
                continue
    except Exception:
        pass
    return None


def guard_city_root_for_serve(
    root: Path,
    *,
    port: int = 8801,
    rehome: bool = True,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Refuse production suite binds on missing/ephemeral workspace roots (pc-873).

    Launchd only execs the plist — if ``--root`` was poisoned with a temp path,
    Map boots a junk city until something rehomes. ``ensure_service_running``
    heals on *service start*; this guard closes the hole at **serve process**
    entry so reboot cannot keep serving ``/var/folders/…/T``.

    Behaviour:

    * Durable existing root → ``action=continue`` (bind OK).
    * Missing or ephemeral root on **production suite port** (``8801``):
      try registry rehome via ``ensure_service_running`` then
      ``action=rehome`` / ``refuse`` with ``should_exit=True`` (do not bind).
    * Non-production ports (isolated tests, dogfood free ports) → warn only
      and ``action=warn`` so pytest/setup sandboxes still work.
    * Escape hatch: ``PROTOCOLCITY_ALLOW_EPHEMERAL_SERVE=1`` forces continue
      (tests / deliberate temp demos).
    """
    try:
        root_p = root.expanduser().resolve()
    except OSError:
        root_p = Path(str(root))

    allow = (os.environ.get("PROTOCOLCITY_ALLOW_EPHEMERAL_SERVE") or "").strip().lower()
    if allow in ("1", "true", "yes", "on"):
        return {
            "ok": True,
            "action": "continue",
            "root": str(root_p),
            "port": int(port),
            "allow_ephemeral": True,
            "should_exit": False,
        }

    missing = not root_p.is_dir()
    ephemeral = (not missing) and is_ephemeral_root(root_p)
    production_suite = int(port) == 8801

    if not missing and not ephemeral:
        return {
            "ok": True,
            "action": "continue",
            "root": str(root_p),
            "port": int(port),
            "should_exit": False,
        }

    alt = _pick_registry_root()
    reason = "missing" if missing else "ephemeral"
    detail = (
        "SUITE_CITY_ROOT is %s: %s" % (reason, root_p)
        if reason == "missing"
        else "SUITE_CITY_ROOT is ephemeral (temp/pytest path): %s" % root_p
    )

    # Isolated / free ports: warn only — never rewrite production agent.
    if not production_suite:
        if not quiet:
            print(
                "WARNING: %s\n"
                "  Non-production port %d — continuing (tests/isolated OK).\n"
                "  Production Map uses port 8801; refuse temp roots there."
                % (detail, int(port)),
                flush=True,
            )
        return {
            "ok": True,
            "action": "warn",
            "root": str(root_p),
            "port": int(port),
            "reason": reason,
            "should_exit": False,
            "alt": str(alt) if alt is not None else None,
        }

    # Production :8801 — never bind junk; rehome login agent when possible.
    if rehome and alt is not None and is_macos():
        if not quiet:
            print(
                "ERROR: %s\n"
                "  Refusing to bind production suite :8801 on a junk root.\n"
                "  Rehoming login service onto durable city: %s"
                % (detail, alt),
                flush=True,
            )
        try:
            receipt = ensure_service_running(
                preferred_root=alt,
                quiet=quiet,
                force=True,
            )
        except Exception as e:
            receipt = {"ok": False, "error": str(e)}
        if not quiet:
            if receipt.get("ok"):
                print(
                    "  Login service rehomed — launchd will restart suite on %s.\n"
                    "  Exiting this process so the new agent can bind :8801."
                    % alt,
                    flush=True,
                )
            else:
                print(
                    "  Rehome failed: %s\n"
                    "  Fix: blueprint service install --root %s --force"
                    % (receipt.get("error") or "unknown", alt),
                    flush=True,
                )
        return {
            "ok": bool(receipt.get("ok")),
            "action": "rehome",
            "root": str(root_p),
            "port": int(port),
            "reason": reason,
            "alt": str(alt),
            "should_exit": True,
            "exit_code": 0 if receipt.get("ok") else 1,
            "receipt": receipt,
        }

    fix = (
        "blueprint service install --root %s --force" % alt
        if alt is not None
        else "blueprint service install --root <workspace> --force"
    )
    if not quiet:
        print(
            "ERROR: %s\n"
            "  Refusing to bind production suite :8801 (Map would show a junk city).\n"
            "  Fix: %s"
            % (detail, fix),
            flush=True,
        )
    return {
        "ok": False,
        "action": "refuse",
        "root": str(root_p),
        "port": int(port),
        "reason": reason,
        "alt": str(alt) if alt is not None else None,
        "should_exit": True,
        "exit_code": 2,
        "fix": fix,
    }


def ensure_service_running(
    *,
    preferred_root: Optional[Path] = None,
    quiet: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Bootstrap + kickstart existing agent — **heal stale/missing/ephemeral root**.

    - If ``preferred_root`` is a live dir, reinstall onto it when installed root
      differs or is dead (pc-579 / GH #7 class: kickstart alone kept temp paths).
    - If installed root is missing **or ephemeral** (still on disk under
      /var/folders/…/T), reinstall from preferred_root or durable registry
      (pc-832 reboot regression).
    - Never kickstart an agent whose --root no longer exists or is temp junk.
    - Dogfood ``suite_dir`` from service.json is preserved on heal reinstalls.
    """
    if not is_macos():
        return {"ok": True, "skipped": "not-macos"}

    prefer: Optional[Path] = None
    if preferred_root is not None:
        try:
            pr = preferred_root.expanduser().resolve()
            if pr.is_dir() and not is_ephemeral_root(pr):
                prefer = pr
        except OSError:
            prefer = None

    cur = installed_root()
    cur_ephemeral = bool(cur is not None and is_ephemeral_root(cur))
    cur_alive = bool(cur is not None and cur.is_dir() and not cur_ephemeral)
    state0 = _read_state() or {}
    port = int(state0.get("port") or 8801)
    dogfood = state_suite_dir()

    # Explicit preferred root wins when different or current is dead/ephemeral.
    if prefer is not None and (not cur_alive or cur != prefer):
        if not quiet and (not cur_alive or force or cur_ephemeral):
            print(
                "Reinstalling login service onto workspace %s "
                "(was: %s)"
                % (prefer, cur if cur is not None else "(none)")
            )
        return install_service(
            prefer,
            port=port,
            quiet=quiet,
            force=bool(force or not cur_alive or cur_ephemeral),
            suite_dir=dogfood,
        )

    # Ephemeral installed root — never kickstart (pc-832).
    if cur is not None and cur_ephemeral:
        alt = _pick_registry_root()
        if alt is not None:
            if not quiet:
                print(
                    "Service root is ephemeral (%s) — reinstalling from registry: %s"
                    % (cur, alt)
                )
            return install_service(
                alt, port=port, quiet=quiet, force=True, suite_dir=dogfood
            )
        return {
            "ok": False,
            "error": (
                "service root is ephemeral: %s — run: "
                "blueprint service install --root <workspace> --force"
                % cur
            ),
            "root": str(cur),
            "ephemeral": True,
        }

    # Dead installed root — recover from registry before giving up.
    if cur is not None and not cur_alive:
        alt = _pick_registry_root()
        if alt is not None:
            if not quiet:
                print(
                    "Service root missing (%s) — reinstalling from registry: %s"
                    % (cur, alt)
                )
            return install_service(
                alt, port=port, quiet=quiet, force=True, suite_dir=dogfood
            )
        return {
            "ok": False,
            "error": (
                "service root missing: %s — after a folder rename/move run: "
                "blueprint relocate-root --from %s --to <new-workspace>  "
                "(or: blueprint service install --root <workspace>)"
                % (cur, cur)
            ),
            "root": str(cur),
        }

    path = plist_path()
    state = _read_state()
    if not path.is_file() and not state:
        if prefer is not None:
            return install_service(
                prefer, port=port, quiet=quiet, suite_dir=dogfood
            )
        alt = _pick_registry_root()
        if alt is not None:
            return install_service(
                alt, port=port, quiet=quiet, suite_dir=dogfood
            )
        return {
            "ok": False,
            "error": "no service installed (run: blueprint service install --root <ws>)",
        }

    # pc-575: heal must not leave dual-ownership citylens agent running.
    bootout_citylens_agent(quiet=True, remove_plist=True)
    domain = _gui_domain()
    if path.is_file():
        # pc-694: stale Cellar interpreter guard — after brew upgrade the old
        # Cellar python is deleted; kickstarting the old plist boots a missing
        # binary. Reinstall whenever argv0 is gone, not executable, or differs.
        if cur is not None:
            plist_argv0 = _plist_argv0()
            current_argv0 = resolve_cli_argv()[0]
            if plist_argv0 and (
                not os.path.isfile(plist_argv0)
                or not os.access(plist_argv0, os.X_OK)
                or plist_argv0 != current_argv0
            ):
                if not quiet:
                    print(
                        "Stale interpreter in login service (%s) — reinstalling"
                        % plist_argv0
                    )
                return install_service(
                    cur,
                    port=port,
                    quiet=quiet,
                    force=True,
                    suite_dir=dogfood,
                )
        launchctl("bootstrap", domain, str(path))
        launchctl("enable", "%s/%s" % (domain, LABEL))
        r = launchctl("kickstart", "-k", "%s/%s" % (domain, LABEL))
        if not quiet:
            print(
                "Restarted login service %s (kickstart rc=%s)%s"
                % (
                    LABEL,
                    r.returncode,
                    (" root=%s" % cur) if cur is not None else "",
                )
            )
        return {
            "ok": r.returncode == 0,
            "kickstart_rc": r.returncode,
            "plist": str(path),
            "root": str(cur) if cur is not None else None,
            "suite_dir": str(dogfood) if dogfood is not None else None,
        }
    # State without plist — need full reinstall
    root = (state.get("root") or "").strip()
    if not root:
        return {"ok": False, "error": "service state missing root"}
    return install_service(
        Path(root),
        port=int(state.get("port") or 8801),
        quiet=quiet,
        suite_dir=dogfood,
    )


def install_service(
    root: Path,
    *,
    port: int = 8801,
    quiet: bool = False,
    allow_ephemeral: bool = False,
    isolated: bool = False,
    force: bool = False,
    suite_dir: Optional[Path] = None,
    dogfood: bool = False,
) -> Dict[str, Any]:
    """Write plist + bootstrap. macOS only.

    Registers the city in the user registry (idempotent) so rename/move
    recovery and doctor have a live path (GH #7 / pc-579 class).

    Dogfood (founder host): pass ``suite_dir`` (ProtocolCity repo root) or
    ``dogfood=True`` to set ``BLUEPRINT_SUITE_DIR`` so Map glass serves from
    the git tree. Persist in service.json so heal/brew-stale reinstall keeps it.
    """
    if not is_macos():
        return {
            "ok": False,
            "error": (
                "Login service is macOS-only today (LaunchAgents). "
                "Windows always-on is tracked under Windows install epic."
            ),
        }
    root = root.expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "error": "workspace root missing: %s" % root}
    if isolated and int(port) in PRODUCTION_PORTS:
        return {
            "ok": False,
            "error": (
                "isolated service port %d is reserved by the live suite/engines; "
                "pass a non-production --port (for example %d)"
                % (int(port), ISOLATED_DEFAULT_PORT)
            ),
            "port": int(port),
            "isolated": True,
        }
    if is_ephemeral_root(root) and not allow_ephemeral and not isolated:
        return {
            "ok": False,
            "error": (
                "refusing ephemeral service root %s "
                "(temp/pytest paths are not durable workspaces). "
                "Pass a permanent folder, e.g. blueprint service install --root ~/Developer"
                % root
            ),
            "root": str(root),
            "ephemeral": True,
        }

    current = installed_root(isolated=isolated)
    if current is not None and current != root and not force:
        label = _service_label(isolated)
        if not quiet:
            print(
                "Refusing to replace login service registration %s:" % label,
                file=sys.stderr,
            )
            print("  - existing root:  %s" % current, file=sys.stderr)
            print("  + requested root: %s" % root, file=sys.stderr)
            print("Re-run with --force only after checking both paths.", file=sys.stderr)
        return {
            "ok": False,
            "error": (
                "service root differs: existing=%s requested=%s; "
                "pass --force to replace it" % (current, root)
            ),
            "label": label,
            "existing_root": str(current),
            "requested_root": str(root),
            "force_required": True,
            "isolated": bool(isolated),
        }

    # Resolve dogfood suite dir: explicit arg → prior state → workspace/ProtocolCity
    resolved_suite: Optional[Path] = None
    if suite_dir is not None:
        resolved_suite = resolve_dogfood_suite_dir(suite_dir, workspace=root)
        if resolved_suite is None:
            return {
                "ok": False,
                "error": (
                    "dogfood suite_dir invalid (need ProtocolCity repo with "
                    "suite/serve.py): %s" % suite_dir
                ),
            }
    elif dogfood:
        resolved_suite = resolve_dogfood_suite_dir(workspace=root)
        if resolved_suite is None:
            return {
                "ok": False,
                "error": (
                    "dogfood requested but no ProtocolCity tree found "
                    "(pass --suite-dir PATH or set BLUEPRINT_SUITE_DIR; "
                    "expected <workspace>/ProtocolCity/suite/serve.py)"
                ),
            }
    else:
        # Preserve dogfood across force reinstall / heal when caller omits flag
        resolved_suite = state_suite_dir(isolated=isolated)

    label = _service_label(isolated)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    body = render_plist(
        root=root, port=port, isolated=isolated, suite_dir=resolved_suite
    )
    path = plist_path(isolated)
    # Replace any prior agent cleanly
    bootout_agent(quiet=True, isolated=isolated)
    # pc-1008: bootout SIGTERMs the parent CLI process but serve.py may survive
    # briefly as an orphan (AbandonProcessGroup=true). Drain the port before
    # kickstart so the new job's startup doesn't hit EADDRINUSE crash-loop.
    try:
        from protocolcity.setup_flow import stop_suite_processes

        stop_suite_processes(
            quiet=True,
            bootout_login_agent=False,
            ports=[port],
            kill_patterns=False,
        )
    except Exception:
        pass
    # pc-575: never re-arm legacy citylens agent; census is in-suite.
    if not isolated:
        bootout_citylens_agent(quiet=True, remove_plist=True)
    path.write_bytes(body)
    _write_state(root, port, isolated=isolated, suite_dir=resolved_suite)
    # Keep cities.json aligned with the agent (idempotent upsert by path).
    # Never register ephemeral roots; prune junk rows left by old test leaks (pc-832).
    if not isolated:
        try:
            from protocolcity.registry import prune_ephemeral_cities, register_city

            if not is_ephemeral_root(root):
                register_city(root, name=root.name)
            prune_ephemeral_cities()
        except Exception:
            pass

    domain = _gui_domain()
    r = launchctl("bootstrap", domain, str(path))
    if r.returncode != 0:
        # Already bootstrapped → kickstart enable
        r_en = launchctl("enable", "%s/%s" % (domain, label))
        r_ks = launchctl("kickstart", "-k", "%s/%s" % (domain, label))
        if r_ks.returncode != 0 and r.returncode != 0:
            return {
                "ok": False,
                "error": (r.stderr or r.stdout or r_ks.stderr or "bootstrap failed").strip(),
                "plist": str(path),
                "bootstrap_rc": r.returncode,
                "enable_rc": r_en.returncode,
                "kickstart_rc": r_ks.returncode,
            }
    else:
        launchctl("enable", "%s/%s" % (domain, label))
        launchctl("kickstart", "-k", "%s/%s" % (domain, label))

    if not quiet:
        print("Installed login service %s" % label)
        print("  workspace: %s" % root)
        print("  suite:     http://127.0.0.1:%d/" % port)
        print("  plist:     %s" % path)
        if resolved_suite is not None:
            print("  dogfood:   %s  (BLUEPRINT_SUITE_DIR)" % resolved_suite)
        print(
            "  logs:      %s"
            % (
                isolated_config_dir() / "logs"
                if isolated
                else root / ".protocolcity" / "logs"
            )
        )
        if isolated:
            print("Stop:        blueprint service uninstall --isolated")
        else:
            print("Stop:        blueprint service uninstall   # or blueprint stop")
    return {
        "ok": True,
        "label": label,
        "root": str(root),
        "port": int(port),
        "plist": str(path),
        "isolated": bool(isolated),
        "suite_dir": str(resolved_suite) if resolved_suite is not None else None,
        "dogfood": resolved_suite is not None,
    }


def uninstall_service(
    *,
    quiet: bool = False,
    isolated: bool = False,
) -> Dict[str, Any]:
    """Bootout + remove plist + state."""
    if not is_macos():
        return {"ok": True, "skipped": "not-macos"}
    label = _service_label(isolated)
    bo = bootout_agent(quiet=True, isolated=isolated)
    cl = (
        {"ok": True, "skipped": "isolated"}
        if isolated
        else bootout_citylens_agent(quiet=True, remove_plist=True)
    )
    path = plist_path(isolated)
    state_path = _service_state_path(isolated)
    removed = False
    if path.is_file():
        try:
            path.unlink()
            removed = True
        except OSError as e:
            return {"ok": False, "error": str(e), "bootout": bo}
    if state_path.is_file():
        try:
            state_path.unlink()
        except OSError:
            pass
    if not quiet:
        print(
            "Removed login service %s (%s)"
            % (label, "plist deleted" if removed else "plist was absent")
        )
    return {
        "ok": True,
        "label": label,
        "plist_removed": removed,
        "bootout": bo,
        "citylens_bootout": cl,
        "isolated": bool(isolated),
    }


def login_service_configured(*, isolated: bool = False) -> bool:
    """True when the macOS login suite unit was installed (plist and/or state).

    pc-1072: used by ``blueprint serve`` to prefer launchd kickstart over a
    foreground orphan that dies with the calling shell/hand session.
    """
    if not is_macos():
        return False
    if plist_path(isolated).is_file():
        return True
    state = _read_state(isolated=isolated)
    return bool(state)


def service_status(*, isolated: bool = False) -> Dict[str, Any]:
    """Best-effort status for humans and doctor."""
    state = _read_state(isolated=isolated)
    path = plist_path(isolated)
    label = _service_label(isolated)
    loaded = False
    if is_macos():
        r = launchctl("print", "%s/%s" % (_gui_domain(), label))
        loaded = r.returncode == 0
    dogfood = state_suite_dir(isolated=isolated)
    plist_suite = None
    if path.is_file():
        try:
            data = plistlib.loads(path.read_bytes())
            env = data.get("EnvironmentVariables") or {}
            if isinstance(env, dict) and env.get("BLUEPRINT_SUITE_DIR"):
                plist_suite = str(env["BLUEPRINT_SUITE_DIR"])
        except Exception:
            pass
    return {
        "ok": True,
        "macos": is_macos(),
        "label": label,
        "plist": str(path),
        "plist_exists": path.is_file(),
        "loaded": loaded,
        "state": state,
        "isolated": bool(isolated),
        "dogfood": dogfood is not None or bool(plist_suite),
        "suite_dir": str(dogfood) if dogfood is not None else plist_suite,
    }
