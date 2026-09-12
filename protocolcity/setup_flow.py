"""Friendly setup / uninstall orchestration for non-technical first runs.

Reuses found + adopt + doctor. Interactive only on a TTY (or when flags force
a branch). Brew install/uninstall stay non-interactive — caveats point here.

Uninstall stops suite/engine processes first (DMG-like quit) so ports free for
a clean reinstall.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from protocolcity.desk import DEFAULT_DESK
from protocolcity.doctor import diagnose, fix
from protocolcity.found import found, print_receipt
from protocolcity.registry import list_cities, register_city, unregister_city

# Soft default for "create a new workspace" (product face = BluePrint).
DEFAULT_CREATE_PATH = "~/BluePrint"
BREW_UNINSTALL = ["brew", "uninstall", "protocolcity/tap/blueprint"]


def _detect_brew_uninstall_target(brew: str) -> str:
    """Return the bare Homebrew formula name that is currently installed.

    Uses bare names so uninstall succeeds even when the tap formula has been
    removed (Homebrew can find the keg by bare name without needing the tap).
    Falls back to 'blueprint' (current formula) when nothing is detected.
    """
    for formula in (
        "protocolcity/tap/blueprint",
        "blueprint",
        "protocolcity/tap/protocolcity",
        "protocolcity",
    ):
        try:
            proc = subprocess.run(
                [brew, "list", "--versions", formula],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return formula.rsplit("/", 1)[-1]
        except Exception:
            pass
    return "blueprint"


# Required suite + engine listen ports (override via PROTOCOLCITY_*_PORT env).
# pc-575: three-process model — suite + WorkLane + WorkForce. Census is
# in-suite; :8796 is leftover-only (free if present, never required).
_DEFAULT_PORTS = (8801, 8799, 8797)
_LEFTOVER_PORTS = (8796,)  # pre-fold-C citylens; stop frees if still listening

# Process command-line fragments that identify suite/engine children.
# Never match bare "protocolcity" alone — that would kill `uninstall` itself.
# citylens patterns remain so stop reaps leftover :8796 processes (pc-575).
_STOP_PATTERNS = (
    "suite/serve.py",
    "suite.serve",
    # Homebrew Cellar path often appears as .../site-packages/suite/serve.py
    "site-packages/suite/serve",
    "worklane.server",
    "ticketingprotocol.server",
    "ticketingprotocol.task_server",
    "workforce.server",
    "workforce.daemon",
    "protocolcity_workforce",
    "protocolcity.citylens",
    "citylens",
    "tools/citylens.py",
    "blueprint serve",
    # legacy leftover processes from pre-cutover dual CLI installs
    "protocolcity serve",
    "protocolcity.cli serve",
    # uvicorn / hypercorn often front engines on reinstall leftovers
    "uvicorn.*worklane",
    "uvicorn.*ticketing",
    "uvicorn.*workforce",
)

# pc-668: external desk launchd labels and the patterns they own.
# blueprint stop must not kill processes managed by these services.
_EXTERNAL_DESK_LABELS: tuple = (
    "com.ticketingprotocol.server",
    "com.worklane.server",
)
# Pattern substrings that uniquely identify desk-engine processes (subset of _STOP_PATTERNS).
_DESK_ENGINE_PATTERNS: frozenset = frozenset({
    "worklane.server",
    "ticketingprotocol.server",
    "ticketingprotocol.task_server",
    "uvicorn.*worklane",
    "uvicorn.*ticketing",
})
# Default desk port (matches cli._DEFAULT_DESK_PORT; env override respected).
_DEFAULT_DESK_PORT = int((os.environ.get("PROTOCOLCITY_DESK_PORT") or "8799"))

# pc-1034: external workforce launchd label and the patterns it owns.
# blueprint stop must not kill processes managed by this KeepAlive service.
# To stop it gracefully (honors ExitTimeOut=3900): launchctl bootout gui/<uid>/com.workforce.daemon
_EXTERNAL_WORKFORCE_LABELS: tuple = (
    "com.workforce.daemon",
)
_WORKFORCE_ENGINE_PATTERNS: frozenset = frozenset({
    "workforce.daemon",
    "workforce.server",
    "protocolcity_workforce",
    "uvicorn.*workforce",
})
_DEFAULT_WORKFORCE_PORT = int((os.environ.get("PROTOCOLCITY_WORKFORCE_PORT") or "8797"))


def _external_desk_registered() -> bool:
    """True on macOS when an external desk launchd label is registered (pc-668).

    A registered label — even when its process is down — means another service
    owns :8799. blueprint stop must not kill processes on that port or matching
    desk-engine patterns, since the suite did not spawn them.
    Non-macOS always returns False.
    """
    if sys.platform != "darwin":
        return False
    for label in _EXTERNAL_DESK_LABELS:
        try:
            r = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _external_workforce_registered() -> bool:
    """True on macOS when the external workforce launchd label is registered (pc-1034).

    A registered com.workforce.daemon — even when its process is down — means
    another service owns :8797. blueprint stop must not kill processes on that
    port or matching workforce patterns; use ``launchctl bootout`` to stop it.
    Non-macOS always returns False.
    """
    if sys.platform != "darwin":
        return False
    for label in _EXTERNAL_WORKFORCE_LABELS:
        try:
            r = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass
    return False


def suite_ports() -> List[int]:
    """Required suite + engine ports (pc-575: no :8796)."""
    env_keys = (
        ("SUITE_PORT", 8801),
        ("PROTOCOLCITY_SUITE_PORT", 8801),
        ("PROTOCOLCITY_DESK_PORT", 8799),
        ("PROTOCOLCITY_WORKFORCE_PORT", 8797),
    )
    ports: Set[int] = set(_DEFAULT_PORTS)
    for key, default in env_keys:
        raw = (os.environ.get(key) or "").strip()
        if raw.isdigit():
            ports.add(int(raw))
        else:
            ports.add(default)
    return sorted(ports)


def leftover_ports() -> List[int]:
    """Pre-cutover ports freed on full stop only if still listening (pc-575)."""
    ports: Set[int] = set(_LEFTOVER_PORTS)
    cl_raw = (os.environ.get("PROTOCOLCITY_CITYLENS_PORT") or "").strip()
    if cl_raw.isdigit():
        ports.add(int(cl_raw))
    return sorted(ports)


def _pids_listening_on(port: int) -> List[int]:
    """PIDs with TCP LISTEN on port (pc-385: lsof or win32 netstat)."""
    if sys.platform == "win32":
        return _pids_listening_on_win32(port)
    lsof = shutil.which("lsof")
    if not lsof:
        system_lsof = Path("/usr/sbin/lsof")
        if system_lsof.is_file():
            lsof = str(system_lsof)
    if not lsof:
        return []
    try:
        out = subprocess.check_output(
            [lsof, "-nP", "-t", "-iTCP:%d" % port, "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    pids: List[int] = []
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def _pids_listening_on_win32(port: int) -> List[int]:
    """Parse ``netstat -ano`` for LISTENING rows on *port* (pc-385)."""
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    needle = ":%d" % port
    pids: Set[int] = set()
    for line in out.splitlines():
        # TCP    127.0.0.1:8801    0.0.0.0:0    LISTENING    1234
        parts = line.split()
        if len(parts) < 5:
            continue
        if "LISTENING" not in parts and "LISTEN" not in parts:
            # Windows uses LISTENING; some locales may differ — require it
            if not any(p.upper().startswith("LISTEN") for p in parts):
                continue
        local = parts[1] if len(parts) > 1 else ""
        if needle not in local:
            continue
        # Only exact port match (avoid :88010)
        try:
            hostport = local.rsplit(":", 1)
            if len(hostport) != 2 or int(hostport[1]) != port:
                continue
        except ValueError:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid > 0:
            pids.add(pid)
    return sorted(pids)


def _pids_matching_patterns(patterns: Sequence[str]) -> List[int]:
    """Best-effort process match (pgrep -f, or win32 wmic; pc-385)."""
    if sys.platform == "win32":
        return _pids_matching_patterns_win32(patterns)
    found: Set[int] = set()
    me = os.getpid()
    parent = os.getppid()
    for pat in patterns:
        try:
            out = subprocess.check_output(
                ["pgrep", "-f", pat],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            continue
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid not in (me, parent):
                    found.add(pid)
    return sorted(found)


def _pids_matching_patterns_win32(patterns: Sequence[str]) -> List[int]:
    """Match command lines via wmic (best-effort; no pgrep on Windows)."""
    found: Set[int] = set()
    me = os.getpid()
    parent = os.getppid()
    # Normalize patterns: drop regex-ish bits for simple substring match
    needles = []
    for pat in patterns:
        n = (
            str(pat)
            .replace(".*", " ")
            .replace("\\", "/")
            .strip()
            .lower()
        )
        if n:
            needles.append(n)
    if not needles:
        return []
    try:
        out = subprocess.check_output(
            [
                "wmic",
                "process",
                "get",
                "ProcessId,CommandLine",
                "/FORMAT:CSV",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("node,"):
            continue
        # CSV: Node,CommandLine,ProcessId
        low = line.lower()
        if not any(n in low for n in needles):
            continue
        # PID is last field
        parts = line.rsplit(",", 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[-1].strip())
        except ValueError:
            continue
        if pid > 0 and pid not in (me, parent):
            found.add(pid)
    return sorted(found)


def _force_kill_sig() -> int:
    """SIGKILL when available; else SIGTERM (Windows has no SIGKILL)."""
    return int(getattr(signal, "SIGKILL", signal.SIGTERM))


def _signal_pids(pids: Sequence[int], sig: int) -> List[int]:
    """Send signal; return pids that still need attention."""
    alive: List[int] = []
    me = os.getpid()
    for pid in pids:
        if pid == me:
            continue
        try:
            os.kill(pid, sig)
            alive.append(pid)
        except ProcessLookupError:
            pass
        except PermissionError:
            alive.append(pid)
        except OSError:
            # Windows may raise different errors for dead/foreign PIDs
            alive.append(pid)
    return alive


def stop_suite_processes(
    *,
    quiet: bool = False,
    bootout_login_agent: bool = False,
    ports: Optional[List[int]] = None,
    kill_patterns: bool = True,
) -> Dict[str, Any]:
    """Quit suite + engine processes and free ports (DMG-like).

    Safe for uninstall: never kills the current process. Idempotent if nothing
    is running.

    ``bootout_login_agent`` (default False): unload macOS LaunchAgent so
    KeepAlive does not revive. Use only from explicit ``stop`` / uninstall —
    **not** from ``serve`` (launchd serve would bootout itself).

    ``ports``: which ports to free (default: all suite+engine ports).
    ``serve`` should pass only the suite port so already-running engines
    (separate launchd units or prior serve) are not killed — that caused
    ModuleNotFoundError when re-spawning engines with system Python.
    """
    # Login agent first — only when intentionally stopping for good.
    # pc-575: also unload legacy citylens LaunchAgent (census is in suite).
    if bootout_login_agent:
        try:
            from protocolcity.service import bootout_agent, bootout_citylens_agent

            bootout_agent(quiet=True)
            bootout_citylens_agent(quiet=True, remove_plist=True)
        except Exception:
            pass

    me = os.getpid()
    # pc-668: never kill external desk services — blueprint stop only owns what
    # the suite started. If com.ticketingprotocol.server / com.worklane.server
    # is registered, skip their port (8799) and their pattern-matched processes.
    _protect_desk = _external_desk_registered()
    if (
        _protect_desk
        and not quiet
        and (ports is None or _DEFAULT_DESK_PORT in ports)
    ):
        print(
            "  note: external desk service detected — skipping port %d and "
            "desk engine patterns (not suite-owned)" % _DEFAULT_DESK_PORT
        )
    # pc-1034: never kill the external workforce daemon — it is a KeepAlive
    # launchd unit with ExitTimeOut=3900 that drains in-flight hands on SIGTERM.
    # The 0.6s grace window always escalates to SIGKILL before drain completes.
    # To stop it: launchctl bootout gui/<uid>/com.workforce.daemon
    _protect_workforce = _external_workforce_registered()
    if (
        _protect_workforce
        and not quiet
        and (ports is None or _DEFAULT_WORKFORCE_PORT in ports)
    ):
        print(
            "  note: external workforce daemon detected — skipping port %d and "
            "workforce patterns (not suite-owned; "
            "use: launchctl bootout gui/$(id -u)/com.workforce.daemon)" % _DEFAULT_WORKFORCE_PORT
        )
    # Full stop: required ports + free leftover :8796 only if still listening.
    if ports is not None:
        ports_list = list(ports)
    else:
        ports_list = list(suite_ports())
        for p in leftover_ports():
            if p not in ports_list and _pids_listening_on(p):
                ports_list.append(p)
        ports_list = sorted(set(ports_list))
    pids: Set[int] = set()
    for port in ports_list:
        if _protect_desk and port == _DEFAULT_DESK_PORT:
            continue
        if _protect_workforce and port == _DEFAULT_WORKFORCE_PORT:
            continue
        for pid in _pids_listening_on(port):
            if pid != me:
                pids.add(pid)
    if kill_patterns and ports is None:
        # Full stop only — pattern kill would murder engines during re-serve.
        # Strip patterns for any externally-owned launchd services.
        _active_patterns = [
            p for p in _STOP_PATTERNS
            if not (_protect_desk and p in _DESK_ENGINE_PATTERNS)
            and not (_protect_workforce and p in _WORKFORCE_ENGINE_PATTERNS)
        ]
        for pid in _pids_matching_patterns(_active_patterns):
            pids.add(pid)

    if not pids:
        if not quiet:
            print(
                "Stopping suite: nothing listening on %s"
                % ", ".join(str(p) for p in ports_list)
            )
        return {"ok": True, "ports": ports_list, "signaled": [], "still_alive": []}

    ordered = sorted(pids)
    if not quiet:
        print(
            "Stopping suite / engines (pids %s; ports %s)…"
            % (
                ", ".join(str(p) for p in ordered),
                ", ".join(str(p) for p in ports_list),
            )
        )

    _signal_pids(ordered, signal.SIGTERM)
    time.sleep(0.6)
    still = []
    for pid in ordered:
        try:
            os.kill(pid, 0)
            still.append(pid)
        except ProcessLookupError:
            pass
        except (PermissionError, OSError):
            still.append(pid)
    if still:
        # Escalate: SIGKILL on POSIX; SIGTERM again on Windows (pc-385)
        _signal_pids(still, _force_kill_sig())
        if sys.platform == "win32":
            # taskkill /F for stubborn console children
            for pid in still:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F", "/T"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except (FileNotFoundError, OSError):
                    pass
        time.sleep(0.2)

    still_alive = []
    for pid in ordered:
        try:
            os.kill(pid, 0)
            still_alive.append(pid)
        except ProcessLookupError:
            pass
        except (PermissionError, OSError):
            still_alive.append(pid)

    # Port re-check for honesty
    busy = [p for p in ports_list if _pids_listening_on(p)]
    if not quiet:
        if still_alive or busy:
            print(
                "  warning: still held — pids %s · ports %s"
                % (still_alive or "—", busy or "—"),
                file=sys.stderr,
            )
        else:
            print("  suite stopped; ports free.")
    return {
        "ok": not still_alive and not busy,
        "ports": ports_list,
        "signaled": ordered,
        "still_alive": still_alive,
        "busy_ports": busy,
    }


def _quiesce_isolated_port(port: int, *, settle_s: float = 2.0) -> bool:
    """Stop one test listener and watch for a late launchd child (pc-675)."""
    stop_suite_processes(
        quiet=False,
        bootout_login_agent=False,
        ports=[port],
        kill_patterns=False,
    )
    deadline = time.monotonic() + max(0.0, float(settle_s))
    while time.monotonic() < deadline:
        if _pids_listening_on(port):
            stop_suite_processes(
                quiet=True,
                bootout_login_agent=False,
                ports=[port],
                kill_patterns=False,
            )
        time.sleep(0.1)
    remaining = _pids_listening_on(port)
    if remaining:
        print(
            "warning: isolated suite port %d still has listener(s): %s"
            % (port, ", ".join(str(pid) for pid in remaining)),
            file=sys.stderr,
        )
    return not remaining


def is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def _prompt(msg: str, default: str = "") -> str:
    suffix = " [%s]" % default if default else ""
    try:
        raw = input("%s%s: " % (msg, suffix)).strip()
    except EOFError:
        return default
    return raw if raw else default


def _prompt_choice(msg: str, choices: Sequence[str], default: str) -> str:
    """choices are lowercase single-letter or short tokens; default is one of them."""
    labels = "/".join(
        c.upper() if c == default else c for c in choices
    )
    raw = _prompt("%s (%s)" % (msg, labels), default).strip().lower()
    if raw in choices:
        return raw
    # accept first letter
    for c in choices:
        if raw == c[0]:
            return c
    return default


def pick_folder_dialog(*, prompt: str = "Choose your BluePrint workspace folder") -> Optional[Path]:
    """Open a native folder picker (macOS / Windows). Returns None if cancelled or unsupported."""
    if sys.platform == "darwin":
        # osascript returns POSIX path with trailing slash; cancel → non-zero.
        script = (
            'try\n'
            '  POSIX path of (choose folder with prompt %s)\n'
            'on error\n'
            '  return ""\n'
            'end try'
        ) % json_escape_applescript(prompt)
        try:
            out = subprocess.check_output(
                ["osascript", "-e", script],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return None
        if not out:
            return None
        return Path(out).expanduser()

    if sys.platform == "win32":
        # FolderBrowserDialog via PowerShell (no extra Python deps).
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "$d.Description = '%s'; "
            "$d.ShowNewFolderButton = $true; "
            "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
        ) % prompt.replace("'", "''")
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-STA",
                    "-Command",
                    ps,
                ],
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return None
        if not out:
            return None
        return Path(out).expanduser()

    return None


def json_escape_applescript(s: str) -> str:
    """Quote a string for AppleScript."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def list_unmanaged_projects(city_root: Path) -> List[str]:
    """Top-level folders doctor marks NOT-MANAGED + fixable."""
    root = city_root.expanduser().resolve()
    if not (root / "AGENTS.md").is_file():
        return []
    report = diagnose(root)
    names: List[str] = []
    for f in report.get("findings") or []:
        if f.get("code") == "NOT-MANAGED" and f.get("fixable"):
            names.append(Path(str(f.get("path") or "")).name)
    return [n for n in names if n]


def adopt_all_unmanaged(
    city_root: Path,
    *,
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    with_demo_worker: bool = False,
) -> Dict[str, Any]:
    root = city_root.expanduser().resolve()
    names = list_unmanaged_projects(root)
    adopted: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for name in names:
        try:
            result = fix(
                root,
                neighborhood=name,
                force=force,
                with_desk=with_desk,
                desk_url=desk_url,
                with_demo_worker=with_demo_worker,
            )
            adopted.append(
                {
                    "name": name,
                    "ok": bool(result.get("ok", True)),
                    "adopt": result.get("adopt"),
                }
            )
        except Exception as e:
            errors.append({"name": name, "error": str(e)})
    return {
        "ok": not errors,
        "city_root": str(root),
        "candidates": names,
        "adopted": adopted,
        "errors": errors,
    }


def _ensure_workspace(
    path: Path,
    *,
    city_name: Optional[str] = None,
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    sample_ticket: bool = True,
    map_port: int = 8801,
) -> Dict[str, Any]:
    """Plant L0 if missing; register. Existing subfolders are left alone."""
    root = path.expanduser().resolve()
    agents = root / "AGENTS.md"
    if agents.is_file() and not force:
        register_city(root, name=city_name or root.name)
        return {
            "ok": True,
            "already": True,
            "root": str(root),
            "receipt": None,
            "message": "already a workspace (AGENTS.md present)",
        }
    receipt = found(
        root,
        city_name=city_name,
        neighborhood=None,
        force=force,
        with_desk=with_desk,
        desk_url=desk_url,
        sample_ticket=sample_ticket,
        map_port=map_port,
    )
    register_city(root, name=str(receipt.get("city_name") or root.name))
    return {
        "ok": True,
        "already": False,
        "root": str(root),
        "receipt": receipt,
        "message": "workspace ready",
    }


def _print_how_to_add_project(root: Path) -> None:
    """Human-facing: no default project — teach Map right-click + agent."""
    print("")
    print("No project folders were created (by design).")
    print("Add one when you are ready:")
    print("  1. Create or drop a folder inside:  %s" % root)
    print("  2. On the Map: right-click that folder → Adopt")
    print("  3. Or ask your AI agent to run:  blueprint adopt %s <folder>" % root)


def _prompt_workspace_path(mode: str) -> "Path | int":
    """Interactive path prompt. Returns Path, or int exit code on error.

    create: default ~/BluePrint (invent a folder).
    adopt-workspace: OS folder picker preferred; type-path fallback.
    adopt-project: agent/script path only (not in human setup menu).
    """
    if mode == "adopt-workspace":
        cities = list_cities()
        if cities:
            print("Registered workspaces:")
            for row in cities[:12]:
                print("  · %s" % (row.get("path") or ""))
        print("")
        print("Use an existing folder as your workspace")
        print("  1) Choose folder…  (opens a window — recommended)")
        print("  2) Type a path")
        print("  3) Cancel")
        choice = _prompt("Choose", "1")
        if choice in ("3", "q", "quit", "c", "cancel"):
            print("Nothing changed.")
            return 2
        if choice in ("1", "p", "pick", "browse", ""):
            picked = pick_folder_dialog(
                prompt="Choose the folder to use as your BluePrint workspace"
            )
            if picked is None:
                print(
                    "No folder selected (or this OS has no folder dialog). "
                    "Type the full path instead."
                )
                # fall through to type path
            else:
                return picked
        # type path (choice 2, or picker unavailable)
        default = ""
        if len(cities) == 1:
            default = str(cities[0].get("path") or "")
        raw = _prompt(
            "Path to your existing folder (full path, e.g. ~/Documents/MyWork)",
            default,
        )
        if not raw:
            print(
                "error: path required — pick a folder in the dialog, type a path, "
                "or choose option 1 to create a new workspace",
                file=sys.stderr,
            )
            return 2
        return Path(raw).expanduser()

    if mode == "adopt-project":
        # Agent/script only — not offered in the human setup menu.
        cities = list_cities()
        if cities:
            default = str(cities[0].get("path") or DEFAULT_CREATE_PATH)
        else:
            default = DEFAULT_CREATE_PATH
        raw = _prompt(
            "Workspace folder that holds the project (full path)",
            default,
        )
        if not raw:
            print("error: path required", file=sys.stderr)
            return 2
        return Path(raw).expanduser()

    # create — soft default ~/BluePrint; "pick" opens folder dialog
    print(
        "New workspace (Enter = %s · type another path · or 'pick' for a folder window)"
        % DEFAULT_CREATE_PATH
    )
    raw = _prompt("New workspace folder", DEFAULT_CREATE_PATH)
    if not raw:
        print("error: path required", file=sys.stderr)
        return 2
    if raw.strip().lower() in ("pick", "browse", "choose", "1"):
        picked = pick_folder_dialog(
            prompt="Choose the folder that will be your BluePrint workspace"
        )
        if picked is None:
            print(
                "error: no folder selected — try again or type a path like %s"
                % DEFAULT_CREATE_PATH,
                file=sys.stderr,
            )
            return 2
        return picked
    return Path(raw).expanduser()


_LEGACY_CLI_RE = re.compile(
    r"\bprotocolcity(\s+)(serve|adopt|found|stop|doctor|setup)\b"
)


def _warn_stale_first_run(root: Path) -> None:
    """Patch FIRST_RUN.md in-place: replace removed `protocolcity` CLI with `blueprint`."""
    first = root / "FIRST_RUN.md"
    if not first.is_file():
        return
    try:
        text = first.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if not _LEGACY_CLI_RE.search(text):
        return
    patched = _LEGACY_CLI_RE.sub(r"blueprint\1\2", text)
    try:
        first.write_text(patched, encoding="utf-8")
        print(
            "\nNote: FIRST_RUN.md refreshed — `protocolcity` CLI references "
            "updated to `blueprint` (renamed in 0.1.26)."
        )
    except OSError as exc:
        print(
            "\nNote: FIRST_RUN.md still references the removed `protocolcity` CLI "
            "(renamed to `blueprint` in 0.1.26).\n"
            "  Refresh it:  blueprint found --force %s\n"
            "  (Auto-update failed: %s)" % (root, exc)
        )


def run_setup(
    *,
    path: Optional[str] = None,
    mode: Optional[str] = None,  # create | adopt-workspace | adopt-project
    adopt_project: Optional[str] = None,
    all_unmanaged: bool = False,
    project: Optional[str] = None,  # optional first project on create
    yes: bool = False,
    serve: bool = False,
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    no_ticket: bool = False,
    map_port: int = 8801,
    serve_fn=None,  # optional callable for --serve (injected from cli)
    demo: Optional[bool] = None,  # ignored — no demo project on setup (2026-07-28)
    service: Optional[bool] = None,  # None=ask (tty macOS, default ON), True/False force
    service_isolated: bool = False,
) -> int:
    """Return process exit code."""
    tty = is_tty()
    if not mode and not yes and not path and tty:
        print("BluePrint setup")
        print("  1) Create a new workspace")
        print("  2) Use an existing folder")
        print("  3) Quit")
        choice = _prompt("Choose", "1")
        if choice in ("3", "q", "quit"):
            print("Nothing changed.")
            return 0
        if choice in ("2",):
            mode = "adopt-workspace"
        else:
            mode = "create"
    elif not mode:
        if adopt_project:
            # Agent/script flag only — not in the human menu.
            mode = "adopt-project"
        elif all_unmanaged and path:
            mode = "adopt-workspace"  # then all-unmanaged below
        else:
            mode = "create"

    if mode not in ("create", "adopt-workspace", "adopt-project"):
        print("error: unknown mode %r" % mode, file=sys.stderr)
        return 2

    if not tty and not yes and mode in ("create", "adopt-workspace") and not path:
        print(
            "error: non-interactive setup needs a path and "
            "--create or --adopt-workspace (or --yes)",
            file=sys.stderr,
        )
        return 2

    # Resolve path — mode-aware prompts (pc-556: opt 2 must not silently
    # default to ~/ProtocolCity / "name only").
    if path:
        root = Path(path).expanduser()
    elif tty and not yes:
        root_or_err = _prompt_workspace_path(mode)
        if isinstance(root_or_err, int):
            return root_or_err
        root = root_or_err
    else:
        # --yes / non-TTY without an explicit path
        if mode == "adopt-workspace":
            print(
                "error: adopt-workspace needs an explicit path "
                "(e.g. blueprint setup --adopt-workspace ~/MyFolder)",
                file=sys.stderr,
            )
            return 2
        if mode == "adopt-project":
            cities = list_cities()
            if cities:
                root = Path(str(cities[0].get("path") or DEFAULT_CREATE_PATH)).expanduser()
            else:
                root = Path(DEFAULT_CREATE_PATH).expanduser()
        else:
            root = Path(DEFAULT_CREATE_PATH).expanduser()

    if mode == "create":
        if root.exists() and any(root.iterdir()) and (root / "AGENTS.md").is_file():
            if not force:
                print(
                    "Workspace already exists at %s — use setup without --create, "
                    "or pass --force to re-plant." % root
                )
                register_city(root)
                if all_unmanaged:
                    return _print_adopt_all(
                        root, force=force, with_desk=with_desk, desk_url=desk_url
                    )
                if not yes:
                    _print_how_to_add_project(root)
                return _after_workspace_ready(
                    root,
                    serve=serve,
                    yes=yes,
                    serve_fn=serve_fn,
                    map_port=map_port,
                    service=service,
                    service_isolated=service_isolated,
                    service_force=force,
                )

        try:
            receipt = found(
                root,
                neighborhood=project,
                force=force,
                with_desk=with_desk,
                desk_url=desk_url,
                sample_ticket=not no_ticket,
                map_port=map_port,
            )
        except FileExistsError as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        except (FileNotFoundError, ValueError) as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        register_city(root, name=str(receipt.get("city_name") or root.name))
        print_receipt(receipt)
        if all_unmanaged:
            _print_adopt_all(root, force=force, with_desk=with_desk, desk_url=desk_url)
        else:
            # Do not prompt humans to mass-adopt — Map right-click / agent adopt.
            if yes:
                pass
            elif project:
                pass
            else:
                _print_how_to_add_project(root)
        return _after_workspace_ready(
            root,
            serve=serve,
            yes=yes,
            serve_fn=serve_fn,
            map_port=map_port,
            service=service,
            service_isolated=service_isolated,
            service_force=force,
        )

    if mode == "adopt-workspace":
        if not root.exists():
            if yes or (tty and _prompt_choice(
                "Folder does not exist. Create it", ("y", "n"), "y"
            ) == "y"):
                root.mkdir(parents=True, exist_ok=True)
            else:
                print("error: path does not exist: %s" % root, file=sys.stderr)
                return 2
        try:
            result = _ensure_workspace(
                root,
                force=force,
                with_desk=with_desk,
                desk_url=desk_url,
                sample_ticket=not no_ticket,
                map_port=map_port,
            )
        except FileExistsError as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        except (FileNotFoundError, ValueError) as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        if result.get("already"):
            print("Using existing workspace at %s" % result["root"])
            _warn_stale_first_run(root)
        else:
            receipt = result.get("receipt")
            if receipt:
                print_receipt(receipt)
            else:
                print("Workspace ready at %s" % result["root"])
        if all_unmanaged:
            _print_adopt_all(root, force=force, with_desk=with_desk, desk_url=desk_url)
        else:
            _print_how_to_add_project(root)
        return _after_workspace_ready(
            root,
            serve=serve,
            yes=yes,
            serve_fn=serve_fn,
            map_port=map_port,
            service=service,
            service_isolated=service_isolated,
            service_force=force,
        )

    # adopt-project — agent / --adopt-project flag only (not setup menu)
    folder = adopt_project
    if not folder and tty and not yes:
        folder = _prompt("Project folder name (top-level under the workspace)", "")
    if not folder:
        print(
            "error: adopt-project needs --adopt-project NAME (or interactive input)",
            file=sys.stderr,
        )
        return 2
    if not (root / "AGENTS.md").is_file():
        print(
            "error: %s is not a founded workspace (no AGENTS.md). "
            "Run: blueprint setup --adopt-workspace %s"
            % (root, root),
            file=sys.stderr,
        )
        return 2
    target = root / folder
    if not target.is_dir():
        print(
            "error: folder not found: %s\n"
            "Drop or create the project folder under the workspace first, then adopt."
            % target,
            file=sys.stderr,
        )
        return 2
    try:
        result = fix(
            root,
            neighborhood=folder,
            force=force,
            with_desk=with_desk,
            desk_url=desk_url,
        )
    except Exception as e:
        print("error: adopt failed: %s" % e, file=sys.stderr)
        return 2
    register_city(root)
    print("Managed project %r under %s" % (folder, root))
    import json

    print(json.dumps(result.get("adopt") or result, indent=2, default=str))
    return _after_workspace_ready(
        root,
        serve=serve,
        yes=yes,
        serve_fn=serve_fn,
        map_port=map_port,
        service=service,
        service_isolated=service_isolated,
        service_force=force,
    )


def _print_adopt_all(
    root: Path,
    *,
    force: bool,
    with_desk: bool,
    desk_url: str,
) -> int:
    result = adopt_all_unmanaged(
        root, force=force, with_desk=with_desk, desk_url=desk_url
    )
    names = result.get("candidates") or []
    if not names:
        print("No unmanaged project folders to adopt under %s" % root)
        return 0
    print("Adopting unmanaged folders: %s" % ", ".join(names))
    for row in result.get("adopted") or []:
        print("  · %s — %s" % (row.get("name"), "ok" if row.get("ok") else "failed"))
    for err in result.get("errors") or []:
        print("  · %s — error: %s" % (err.get("name"), err.get("error")), file=sys.stderr)
    return 0 if result.get("ok") else 1


def _maybe_unmanaged_prompt(
    root: Path,
    *,
    yes: bool,
    with_desk: bool,
    desk_url: str,
) -> int:
    names = list_unmanaged_projects(root)
    if not names:
        return 0
    print("Unmanaged project folders: %s" % ", ".join(names))
    print(
        "  Tip: drop folders into the workspace, then Manage in the browser "
        "or: blueprint adopt %s <folder>" % root
    )
    if yes or not is_tty():
        return 0
    ans = _prompt_choice("Adopt all of them now", ("y", "n"), "n")
    if ans == "y":
        return _print_adopt_all(root, force=False, with_desk=with_desk, desk_url=desk_url)
    return 0


def _maybe_service_install(
    root: Path,
    *,
    yes: bool,
    map_port: int = 8801,
    service: Optional[bool] = None,
    isolated: bool = False,
    force: bool = False,
) -> bool:
    """Opt-in macOS login LaunchAgent after setup (pc-560).

    Returns True when the agent is installed/loaded for this workspace.
    Never silent-installs: ``--yes`` / non-TTY skip unless ``service=True``.
    Windows: no-op (login service is macOS-only).
    """
    try:
        from protocolcity import service as svc_mod
    except Exception:
        return False
    if not svc_mod.is_macos():
        return False

    root = root.expanduser().resolve()
    st = svc_mod.service_status(isolated=isolated)
    state = st.get("state") if isinstance(st.get("state"), dict) else {}
    state_root = str((state or {}).get("root") or "").strip()
    same_root = False
    if state_root:
        try:
            same_root = Path(state_root).expanduser().resolve() == root
        except OSError:
            same_root = False
    if st.get("loaded") and (same_root or not state_root):
        print("Login service already active for this workspace.")
        return True

    want: Optional[bool] = service
    if want is None:
        if yes or not is_tty():
            # Non-interactive: never force always-on without --service (pc-560).
            return False
        # Interactive: default ON — user may opt out (2026-07-28).
        ans = _prompt_choice(
            "Keep BluePrint running after you close the terminal? (default Yes — n to opt out)",
            ("y", "n"),
            "y",
        )
        want = ans == "y"
    if not want:
        print(
            "  Skipped always-on. Later: "
            "blueprint service install --root %s" % root
        )
        return False

    try:
        receipt = svc_mod.install_service(
            root,
            port=int(map_port),
            quiet=False,
            isolated=isolated,
            force=force,
        )
    except Exception as e:
        print("warning: service install failed: %s" % e, file=sys.stderr)
        print(
            "  Tip: blueprint service install --root %s" % root,
            file=sys.stderr,
        )
        return False
    if not receipt.get("ok"):
        print(
            "warning: service install incomplete: %s"
            % (receipt.get("error") or receipt),
            file=sys.stderr,
        )
        return False
    return True


def _wait_for_port(
    port: int,
    *,
    timeout_s: float = 45.0,
    interval_s: float = 0.4,
) -> bool:
    """Poll until TCP 127.0.0.1:port accepts. Default 45s (GH #14 cold start)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(interval_s)
    return False


def _after_workspace_ready(
    root: Path,
    *,
    serve: bool,
    yes: bool,
    serve_fn,
    map_port: int,
    service: Optional[bool] = None,
    service_isolated: bool = False,
    service_force: bool = False,
) -> int:
    """pc-560: opt-in login service, then optional serve.

    When service install succeeds, **block until the suite port is ready**
    (or fail non-zero). Scripts/curl after ``setup --service`` must not race
    a cold LaunchAgent (GH #14 / pc-811).
    """
    if _maybe_service_install(
        root,
        yes=yes,
        map_port=map_port,
        service=service,
        isolated=service_isolated,
        force=service_force,
    ):
        print("")
        print("Suite stays up at login. Waiting for http://127.0.0.1:%d/ …" % map_port)
        if _wait_for_port(map_port, timeout_s=45.0):
            print("  ready — open in your browser:")
            print("  http://127.0.0.1:%d/" % map_port)
            print("  blueprint service status")
            return 0
        print(
            "error: suite port %d not ready within 45s after service install."
            % map_port,
            file=sys.stderr,
        )
        print(
            "  Check: blueprint service status · log show --predicate "
            "'process == \"python\"' --last 2m",
            file=sys.stderr,
        )
        print(
            "  Retry: blueprint service install --root %s --force" % root,
            file=sys.stderr,
        )
        print("  http://127.0.0.1:%d/" % map_port, file=sys.stderr)
        return 1
    return _maybe_serve(
        root, serve=serve, yes=yes, serve_fn=serve_fn, map_port=map_port
    )


def _maybe_serve(
    root: Path,
    *,
    serve: bool,
    yes: bool,
    serve_fn,
    map_port: int,
) -> int:
    do_serve = serve
    if not do_serve and is_tty() and not yes and serve_fn is not None:
        ans = _prompt_choice("Open the suite now (serve --with-engines)", ("y", "n"), "y")
        do_serve = ans == "y"
    if not do_serve:
        print("")
        print("Next:")
        print("  blueprint serve --root %s --with-engines" % root)
        print("  open http://127.0.0.1:%d/" % map_port)
        print(
            "  # macOS login auto-start: "
            "blueprint service install --root %s" % root
        )
        return 0
    if serve_fn is None:
        print(
            "error: serve requested but not wired — run: "
            "blueprint serve --root %s --with-engines" % root,
            file=sys.stderr,
        )
        return 2
    print("Starting suite at http://127.0.0.1:%d/ …" % map_port)
    return int(serve_fn(root, map_port))


def run_uninstall(
    *,
    roots: Optional[List[str]] = None,
    keep_workspace: bool = False,  # deprecated: always keep files on disk
    delete_workspace: bool = False,  # rejected — BP never deletes user folders
    remove_app: bool = False,
    yes: bool = False,
    stop_processes: bool = True,
    forget_registry: Optional[bool] = None,
    isolated: bool = False,
) -> int:
    """Stop suite/engines, leave all workspace files on disk, optionally brew uninstall.

    Workspace folders are never deleted by BluePrint — use the OS trash if needed.
    """
    if delete_workspace:
        print(
            "error: BluePrint does not delete workspace folders.\n"
            "  Your files always stay on disk. Trash the folder in Finder / "
            "File Explorer if you want it gone.\n"
            "  (Flag --delete-workspace was removed.)",
            file=sys.stderr,
        )
        return 2

    isolated_stop_ok = True
    # DMG-like: quit the live app before removing the package.
    if stop_processes:
        if isolated:
            isolated_port = 18801
            try:
                from protocolcity.service import (
                    ISOLATED_DEFAULT_PORT,
                    service_status,
                    uninstall_service,
                )

                st = service_status(isolated=True)
                state = st.get("state") if isinstance(st.get("state"), dict) else {}
                isolated_port = int(
                    (state or {}).get("port") or ISOLATED_DEFAULT_PORT
                )
                uninstall_service(quiet=False, isolated=True)
            except Exception:
                pass
            isolated_stop_ok = _quiesce_isolated_port(isolated_port)
        else:
            try:
                from protocolcity.service import uninstall_service

                uninstall_service(quiet=False)
            except Exception:
                pass
            stop_suite_processes(quiet=False)

    targets: List[Path] = []
    if roots:
        targets = [Path(r).expanduser().resolve() for r in roots]
    else:
        rows = list_cities()
        targets = [Path(r["path"]) for r in rows]
        if not targets and is_tty() and not yes:
            raw = _prompt(
                "No registered workspaces. Path to forget from the list (empty to skip)",
                "",
            )
            if raw:
                targets = [Path(raw).expanduser().resolve()]

    if not targets:
        print("No workspace paths in the registry.")
    else:
        print("Workspaces (files always kept on disk):")
        for t in targets:
            mark = "exists" if t.exists() else "missing on disk"
            print("  · %s  (%s)" % (t, mark))

    for root in targets:
        if not root.exists():
            unregister_city(root)
            print("Forgot missing path %s" % root)
            continue

        do_forget = forget_registry
        if do_forget is None:
            if yes or keep_workspace:
                # --yes / legacy --keep-workspace: leave registered unless we
                # only wanted a clean app remove; still drop missing above.
                do_forget = False
            elif is_tty():
                print("")
                print("Workspace: %s" % root)
                print("  Files stay on disk. Trash them yourself if you want.")
                ans = _prompt_choice(
                    "Remove this path from BluePrint's list only",
                    ("y", "n"),
                    "y",
                )
                do_forget = ans == "y"
            else:
                do_forget = False

        if do_forget:
            unregister_city(root)
            print("Kept files at %s (unregistered — BluePrint no longer tracks it)" % root)
        else:
            print("Kept files at %s (still registered)" % root)

    # App removal
    print("")
    if remove_app:
        print("Removing Homebrew app…")
        brew = shutil.which("brew")
        if brew is None:
            print(
                "brew not found — remove the app with your package manager, or:\n"
                "  pip uninstall protocolcity",
                file=sys.stderr,
            )
        else:
            formula = _detect_brew_uninstall_target(brew)
            cmd = [brew, "uninstall", formula]
            proc = subprocess.run(cmd, check=False)
            if proc.returncode != 0:
                print(
                    "brew uninstall exited %s — you can run it manually:"
                    % proc.returncode,
                    file=sys.stderr,
                )
                print("  " + " ".join(cmd), file=sys.stderr)
    else:
        print("App is still installed. To remove it:")
        print("  brew uninstall protocolcity/tap/blueprint")
        print("Or: blueprint uninstall --app")

    print("")
    print("Note: workspace folders were not deleted. Use your OS trash if needed.")

    return 0 if isolated_stop_ok else 1
