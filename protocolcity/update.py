"""protocolcity / blueprint update — user + AI-host upgrade ritual (pc-565).

Pulls the latest BluePrint suite package (Homebrew preferred, pip fallback),
then optionally restarts the suite so the browser is not stuck on a dead
Cellar path after brew upgrade.
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


AGENT_PROMPT = """You are helping me **update the BluePrint suite** (ProtocolCity)
to the latest released package so I get bug fixes and improvements.

## Your job
1. Run (or ask me to run):
   ```bash
   blueprint update
   ```
2. If the command prints a restart hint, run:
   ```bash
   blueprint update --restart --root <my-workspace>
   ```
   (Use my real workspace path; often the folder that contains AGENTS.md.)
   That restart also re-applies city MCP mirrors to Grok/Codex (pc-1151).
   If ticket tools still fail: `bash scripts/mcp_sync.sh apply` then restart
   the agent session.
3. Confirm the new version:
   ```bash
   blueprint --version
   # or: python3 -c "from protocolcity.distro import distro_version; print(distro_version())"
   ```
4. Tell me what changed in one short paragraph (version before → after).
5. **Do not** invent unpublished fixes. If update says already latest, say so.
6. **Do not** push or publish packages. Upgrade only installs what is already
   on PyPI / Homebrew.

## If brew is missing
Use the pip path the CLI prints, or:
```bash
pip install --upgrade 'protocolcity-blueprint[engines]'
# forever-compat alias still works: pip install --upgrade 'protocolcity[engines]'
```

## After upgrade (macOS)
If Map/Desk look like blank 404s, the old process is holding ports:
```bash
blueprint stop
blueprint serve --root <workspace>
# login agent:
blueprint service install --root <workspace>
```
`blueprint update --restart` does the stop + serve/service restore when possible.

## After upgrade — heal agent tool connections
Vendor CLI configs (`~/.grok`, `.mcp.json`) can drift when the Cellar path
changes. If WorkLane MCP / `wl` stops working after upgrade:
```bash
blueprint doctor --fix --root <workspace>
# then restart your AI agent CLI (Grok / Claude / Codex) so MCP reloads
```
`blueprint update --restart --root <workspace>` already runs this heal automatically.
""".strip()


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "not-installed"


def _suite_version() -> str:
    """Installed suite version (preferred distro or forever-compat alias)."""
    try:
        from protocolcity.distro import distro_version

        return distro_version()
    except Exception:
        return _pkg_version("protocolcity")


def _brew_new_python() -> Optional[str]:
    """Return the Python inside the currently-linked blueprint brew virtualenv.

    After `brew upgrade`, the running process's sys.path still references the old
    (now-deleted) Cellar keg. Spawning the new keg's Python gives accurate metadata
    without requiring the running process to restart.

    The brew formula installs the binary at libexec/bin/blueprint (virtualenv), so
    the Python interpreter is a sibling in the same libexec/bin/ directory.
    """
    bp = shutil.which("blueprint")
    if not bp:
        return None
    try:
        real = os.path.realpath(bp)
        # real = /opt/homebrew/Cellar/blueprint/<ver>/libexec/bin/blueprint
        libexec_bin = Path(real).parent
        for name in ("python3.11", "python3", "python"):
            py = libexec_bin / name
            if py.exists():
                return str(py)
    except Exception:
        pass
    return None


def _pkg_version_fresh(name: str) -> str:
    """Read a package version via a fresh subprocess, bypassing stale in-process sys.path.

    Used post-brew-upgrade: importlib.metadata in the running process sees the old
    (deleted) Cellar site-packages and returns 'not-installed' even though the package
    is correctly installed in the new keg.
    """
    py = _brew_new_python()
    if py:
        code, out, _ = _run(
            [py, "-c", "import importlib.metadata as m; print(m.version(%r))" % name]
        )
        if code == 0 and out.strip():
            return out.strip()
    return _pkg_version(name)


def _suite_version_fresh() -> str:
    """Suite version via brew keg Python when available (tries both distro names)."""
    py = _brew_new_python()
    if py:
        code, out, _ = _run(
            [
                py,
                "-c",
                (
                    "from protocolcity.distro import distro_version; "
                    "print(distro_version())"
                ),
            ]
        )
        if code == 0 and out.strip() and out.strip() != "not-installed":
            return out.strip()
        # Older keg without distro helper — probe both names.
        for name in ("protocolcity-blueprint", "protocolcity"):
            code, out, _ = _run(
                [
                    py,
                    "-c",
                    "import importlib.metadata as m; print(m.version(%r))" % name,
                ]
            )
            if code == 0 and out.strip():
                return out.strip()
    return _suite_version()


def agent_prompt_text() -> str:
    return AGENT_PROMPT


def _run(
    cmd: Sequence[str],
    *,
    check: bool = False,
) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            check=False,
        )
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if check and p.returncode != 0:
            raise RuntimeError(
                "command failed (%s): %s\n%s"
                % (p.returncode, " ".join(cmd), err or out)
            )
        return p.returncode, out, err
    except FileNotFoundError:
        return 127, "", "not found: %s" % cmd[0]


def detect_install_method() -> str:
    """Return 'brew', 'pip', or 'unknown'."""
    brew = shutil.which("brew")
    if brew:
        for formula in (
            "protocolcity/tap/blueprint",
            "blueprint",
            # legacy formula names (pre dual-CLI cutover) — still detect installs
            "protocolcity/tap/protocolcity",
            "protocolcity",
        ):
            code, out, _ = _run([brew, "list", "--versions", formula])
            if code == 0 and out.strip():
                return "brew"
    try:
        from protocolcity.distro import any_distro_installed

        if any_distro_installed():
            return "pip"
    except Exception:
        if _pkg_version("protocolcity") != "not-installed":
            return "pip"
        if _pkg_version("protocolcity-blueprint") != "not-installed":
            return "pip"
    return "unknown"


def _brew_formula() -> str:
    """Preferred upgrade target is always the taught blueprint formula.

    Legacy protocolcity formula is detected so we can migrate hosts onto
    blueprint on the next `blueprint update`.
    """
    brew = shutil.which("brew") or "brew"
    for formula in (
        "protocolcity/tap/blueprint",
        "blueprint",
    ):
        code, out, _ = _run([brew, "list", "--versions", formula])
        if code == 0 and out.strip():
            return "protocolcity/tap/blueprint"
    # Old compat formula still installed — migrate to taught name.
    for formula in (
        "protocolcity/tap/protocolcity",
        "protocolcity",
    ):
        code, out, _ = _run([brew, "list", "--versions", formula])
        if code == 0 and out.strip():
            return "protocolcity/tap/blueprint"
    return "protocolcity/tap/blueprint"


def upgrade_package(*, method: Optional[str] = None) -> dict:
    """Upgrade installed package. Returns a result dict."""
    before = _suite_version()
    method = (method or detect_install_method()).lower()
    lines: List[str] = []
    ok = False
    cmd_used: List[str] = []

    if method == "brew":
        brew = shutil.which("brew")
        if not brew:
            return {
                "ok": False,
                "method": "brew",
                "before": before,
                "after": before,
                "error": "brew not on PATH",
                "log": "",
            }
        formula = _brew_formula()
        cmd_used = [brew, "update"]
        code, out, err = _run(cmd_used)
        lines.append("$ " + " ".join(cmd_used))
        if out:
            lines.append(out)
        if err:
            lines.append(err)
        if code != 0:
            return {
                "ok": False,
                "method": "brew",
                "before": before,
                "after": before,
                "error": "brew update failed",
                "log": "\n".join(lines),
                "cmd": cmd_used,
            }
        cmd_used = [brew, "upgrade", formula]
        code, out, err = _run(cmd_used)
        lines.append("$ " + " ".join(cmd_used))
        if out:
            lines.append(out)
        if err:
            lines.append(err)
        # brew upgrade exits 0 even when already latest sometimes; also try reinstall
        # only if still old and formula exists.
        after = _suite_version_fresh()
        if code != 0:
            # Not a hard fail if "already installed" messaging
            msg = (out + "\n" + err).lower()
            if "already installed" in msg or "up-to-date" in msg:
                ok = True
            else:
                return {
                    "ok": False,
                    "method": "brew",
                    "before": before,
                    "after": after,
                    "error": "brew upgrade failed",
                    "log": "\n".join(lines),
                    "cmd": cmd_used,
                }
        else:
            ok = True
        return {
            "ok": ok,
            "method": "brew",
            "formula": formula,
            "before": before,
            "after": _suite_version_fresh(),
            "log": "\n".join(lines),
            "cmd": cmd_used,
        }

    if method == "pip":
        py = sys.executable
        try:
            from protocolcity.distro import pip_upgrade_specs

            specs = pip_upgrade_specs(with_engines=True)
        except Exception:
            specs = ["protocolcity-blueprint[engines]"]
        cmd_used = [py, "-m", "pip", "install", "--upgrade", *specs]
        code, out, err = _run(cmd_used)
        lines.append("$ " + " ".join(cmd_used))
        if out:
            lines.append(out)
        if err:
            lines.append(err)
        after = _suite_version()
        return {
            "ok": code == 0,
            "method": "pip",
            "before": before,
            "after": after,
            "error": None if code == 0 else "pip upgrade failed",
            "log": "\n".join(lines),
            "cmd": cmd_used,
        }

    return {
        "ok": False,
        "method": "unknown",
        "before": before,
        "after": before,
        "error": (
            "Could not detect brew or pip install of BluePrint suite. "
            "Install with: brew install protocolcity/tap/blueprint "
            "or: pip install 'protocolcity-blueprint[engines]'"
        ),
        "log": "",
    }


def _verify_suite_listening(
    port: int = 8801,
    *,
    attempts: int = 6,
    delay_s: float = 1.0,
) -> dict:
    """pc-1068: after restart, require :port LISTEN (Map not dead)."""
    import time

    last: dict = {
        "ok": False,
        "loaded": False,
        "listening": False,
        "port": int(port),
    }
    for i in range(max(1, int(attempts))):
        loaded = False
        listening = False
        try:
            from protocolcity import service as svc_mod

            st = svc_mod.service_status()
            loaded = bool(st.get("loaded"))
        except Exception:
            loaded = False
        try:
            from protocolcity.setup_flow import _pids_listening_on

            listening = bool(list(_pids_listening_on(int(port))))
        except Exception:
            listening = False
        last = {
            "ok": bool(listening),
            "loaded": loaded,
            "listening": listening,
            "port": int(port),
        }
        if listening:
            return last
        if i + 1 < attempts:
            time.sleep(float(delay_s))
    return last


def restart_suite(workspace: Optional[Path] = None) -> dict:
    """Stop suite then restore login agent onto a **live** workspace root.

    When ``workspace`` is set (``update --restart --root``), always
    ``service install --root`` so a stale/temp LaunchAgent cannot win
    (pc-579: kickstart alone left a /var/folders tmp root after brew).
    Without ``workspace``, ``service start`` heals from state/registry.

    pc-1068: never report success when the suite port is still dark after
    reinstall — callers (``update --restart``, upgrade-blueprint.sh) must
    fail loudly so Map death is not a green exit.
    """
    root = (
        workspace.expanduser().resolve()
        if workspace
        else Path.cwd().resolve()
    )
    pc = shutil.which("blueprint") or shutil.which("protocolcity")
    if not pc:
        pc = sys.executable
        base = [pc, "-m", "protocolcity"]
    else:
        base = [pc]

    log: List[str] = []
    steps = []

    def step(args: List[str]) -> int:
        cmd = base + args
        code, out, err = _run(cmd)
        log.append("$ " + " ".join(cmd))
        if out:
            log.append(out)
        if err:
            log.append(err)
        steps.append({"cmd": cmd, "code": code})
        return code

    step(["stop", "--quiet"])
    # Always reinstall LaunchAgent after upgrade so Cellar python argv0
    # cannot point at a deleted path (GH #13 / pc-694 / pc-811).
    if workspace is not None and root.is_dir():
        code_svc = step(
            ["service", "install", "--root", str(root), "--force"]
        )
    else:
        # Heal: start already reinstalls when argv0 is stale; prefer force
        # reinstall from state root when known.
        state_root = ""
        try:
            from protocolcity import service as svc_mod

            st = svc_mod.service_status()
            state = st.get("state") if isinstance(st.get("state"), dict) else {}
            state_root = str((state or {}).get("root") or "").strip()
        except Exception:
            state_root = ""
        if state_root and Path(state_root).is_dir():
            code_svc = step(
                ["service", "install", "--root", state_root, "--force"]
            )
        else:
            code_svc = step(["service", "start"])
    if code_svc != 0:
        # service may not be installed — print serve recipe; fail loud (pc-1068)
        log.append(
            "error: service start failed or not installed — run:\n"
            "  blueprint serve --root %s\n"
            "  # or: blueprint service install --root %s" % (root, root)
        )
        return {
            "ok": False,
            "restarted": False,
            "healthy": False,
            "workspace": str(root),
            "log": "\n".join(log),
            "steps": steps,
            "hint": "serve",
            "error": "service install/start failed (exit %s)" % code_svc,
        }

    # Resolve port from service.json (default 8801) and require LISTEN.
    port = 8801
    try:
        from protocolcity import service as svc_mod

        st = svc_mod.service_status()
        state = st.get("state") if isinstance(st.get("state"), dict) else {}
        port = int((state or {}).get("port") or 8801)
    except Exception:
        port = 8801
    health = _verify_suite_listening(port)
    log.append(
        "health: loaded=%s listening=%s port=%s"
        % (health.get("loaded"), health.get("listening"), port)
    )
    if not health.get("ok"):
        log.append(
            "error: suite not listening on :%d after service reinstall — "
            "Map is dark. Fix: blueprint service start  "
            "# or: launchctl bootstrap gui/$(id -u) "
            "~/Library/LaunchAgents/com.protocolcity.suite.plist"
            % port
        )
        return {
            "ok": False,
            "restarted": True,
            "healthy": False,
            "workspace": str(root),
            "log": "\n".join(log),
            "steps": steps,
            "health": health,
            "error": "suite not listening on :%d" % port,
        }
    return {
        "ok": True,
        "restarted": True,
        "healthy": True,
        "workspace": str(root),
        "log": "\n".join(log),
        "steps": steps,
        "health": health,
    }


def print_update_report(
    *,
    agent_prompt: bool = False,
    method: Optional[str] = None,
    restart: bool = False,
    workspace: Optional[Path] = None,
    dry_run: bool = False,
) -> int:
    if agent_prompt:
        print(agent_prompt_text())
        return 0

    before = _suite_version()
    detected = method or detect_install_method()
    print("BluePrint suite update")
    print("─────────────────────")
    print("installed:  suite %s" % before)
    print("method:     %s" % detected)
    print(
        "os:         %s %s (%s)"
        % (platform.system(), platform.release(), platform.machine())
    )
    print("")

    if dry_run:
        print("dry-run: would upgrade via %s (no changes made)" % detected)
        print("")
        print("AI hosts: blueprint update --agent-prompt")
        return 0

    result = upgrade_package(method=detected)
    if result.get("log"):
        print(result["log"])
        print("")
    if not result.get("ok"):
        print("error: %s" % (result.get("error") or "upgrade failed"), file=sys.stderr)
        return 1

    after = result.get("after") or _suite_version_fresh()
    if before == after:
        print("Already on latest installed build: %s" % after)
    else:
        print("Updated: %s → %s" % (before, after))

    if restart:
        print("")
        print("Restarting suite…")
        rr = restart_suite(workspace)
        if rr.get("log"):
            print(rr["log"])
        # pc-1068: never exit 0 with Map dead after --restart
        if not rr.get("ok") or not rr.get("healthy", False):
            print("")
            print(
                "error: suite not healthy after restart — %s"
                % (rr.get("error") or "Map may be dark"),
                file=sys.stderr,
            )
            print(
                "  blueprint service start\n"
                "  # or: blueprint serve --root <workspace>",
                file=sys.stderr,
            )
            return 1
        # pc-1151: re-project city MCP registry → .mcp.json + Grok/Codex so
        # agent reachability survives upgrade (not suite HTTP alone).
        if workspace is not None:
            _reapply_mcp_mirrors(Path(workspace))
    else:
        print("")
        print("If Map/Desk show blank 404s after brew upgrade:")
        print("  blueprint update --restart --root <workspace>")
        print("  # or: blueprint serve --root <workspace>  # kickstarts login agent (pc-1072)")
        print("If WorkLane MCP / wl dies after upgrade:")
        print("  bash scripts/mcp_sync.sh apply")
        print("  # or: blueprint doctor --fix  (heals Grok/Codex managed blocks)")

    _wl = _pkg_version_fresh("protocolcity-worklane")
    if _wl == "not-installed":
        _wl = _pkg_version_fresh("worklane")
    _wf = _pkg_version_fresh("protocolcity-workforce")
    if _wf == "not-installed":
        _wf = _pkg_version_fresh("workforce")
    print("")
    print("engines: worklane=%s workforce=%s" % (_wl, _wf))
    return 0


def _reapply_mcp_mirrors(workspace: Path) -> None:
    """Best-effort mcp_sync apply (vendors) after suite restart (pc-1151)."""
    root = workspace.expanduser().resolve()
    if not root.is_dir():
        return
    try:
        from protocolcity.mcp_sync import apply_mcp, registry_dir
    except ImportError:
        # After brew upgrade the running process still has the old (deleted)
        # Cellar keg on sys.path, causing a spurious ImportError (pc-1239).
        # Fall back to the new keg's Python so apply runs without a second
        # invocation of `blueprint update --restart`.
        py = _brew_new_python()
        if py:
            code, out, err = _run(
                [py, "-m", "protocolcity.mcp_sync", "apply",
                 "--workspace", str(root)]
            )
            if code == 0:
                print("mcp mirrors: applied (via new keg python)")
                if out:
                    print(out)
            else:
                print("mcp mirrors: apply failed (exit %d) — %s" % (code, err or out))
                print("  fix: bash scripts/mcp_sync.sh apply")
        else:
            print("mcp mirrors: skipped (protocolcity.mcp_sync unavailable)")
        return
    if not registry_dir(root).is_dir():
        print("mcp mirrors: skipped (no .agents/mcp registry under %s)" % root)
        return
    try:
        out = apply_mcp(root, touch_vendors=True)
    except Exception as exc:  # noqa: BLE001 — upgrade must not die on mirror
        print("mcp mirrors: apply failed — %s" % exc)
        print("  fix: bash scripts/mcp_sync.sh apply")
        return
    servers = ",".join(out.get("servers") or []) or "(none)"
    print("mcp mirrors: applied (%s)" % servers)
    vendors = out.get("vendors") or {}
    for label, vout in vendors.items():
        if not isinstance(vout, dict):
            continue
        detail = vout.get("detail") or vout.get("action") or ""
        print("  %s: %s" % (label, detail or ("ok" if vout.get("ok") else "drift")))
