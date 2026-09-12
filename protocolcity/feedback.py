"""protocolcity feedback — local-only paste-ready bug report (pc-317 / pc-434).

No network by default. Prints markdown the human (or their AI host) reviews
and pastes into GitHub Issues. Optional --open launches the issues page only.
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import re
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ISSUES_URL = (
    "https://github.com/protocolcity/BluePrint/issues/new/choose"
)
ISSUES_NEW_BUG = (
    "https://github.com/protocolcity/BluePrint/issues/new"
    "?template=bug_report.md"
)

# Paste this into Cursor / Claude / Grok / any host (pc-434).
AGENT_PROMPT = """You are helping me file a **BluePrint / ProtocolCity beta bug report**.

## Your job
1. Run (or ask me to paste output of):
   ```bash
   blueprint feedback
   ```
2. Ask me for: what I expected, what happened, steps to reproduce, when it started
   (e.g. after brew upgrade, after hire, only on Map).
3. **Do not upload secrets.** Redact tokens, OAuth, keychain, cookies, private
   ticket bodies. Prefer basenames over full home paths unless I opt in.
4. Fill the feedback markdown: add a clear title, Summary, Expected, Actual,
   Reproduction. Keep the Versions / Doctor / log tails from the CLI.
5. Show me the final markdown. I paste it into:
   {issues}
   (Nothing leaves my machine until **I** paste or open that URL.)

## Routing (one board)
| Symptom | File on |
|---|---|
| Overview / Map / setup / serve / brew | BluePrint |
| Work orders / WorkLane MCP / `wl` / desk stores | WorkLane |
| Hire / roster / agent daemon | WorkForce |
| Homebrew formula only | homebrew-tap |

If unsure → BluePrint issues and note the engine in the body.
""".strip()


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return "not-installed"


def _suite_version() -> str:
    """Preferred distro first, then forever-compat alias (pc-553)."""
    try:
        from protocolcity.distro import distro_version

        return distro_version()
    except Exception:
        return _pkg_version("protocolcity")


def _tail_file(path: Path, n: int = 30) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:]) if lines else "(empty)"
    except FileNotFoundError:
        return "(missing)"
    except Exception as e:
        return "(unreadable: %s)" % e


def _scrub_home(text: str, full_paths: bool) -> str:
    """Redact home prefix unless full_paths."""
    if full_paths or not text:
        return text
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "~")
    # common absolute install noise
    text = re.sub(r"/Users/[^/\s]+", "~", text)
    text = re.sub(r"/home/[^/\s]+", "~", text)
    return text


def _path_display(p: Path, full: bool) -> str:
    if full:
        return str(p)
    try:
        home = Path.home().resolve()
        resolved = p.resolve()
        if home in resolved.parents or resolved == home:
            return "~/" + str(resolved.relative_to(home))
    except Exception:
        pass
    return p.name or str(p)


def agent_prompt_text() -> str:
    return AGENT_PROMPT.format(issues=ISSUES_URL)


def gather_report(
    city_root: Optional[Path] = None,
    *,
    full_paths: bool = False,
    symptoms: str = "",
) -> str:
    """Build markdown report body (no network)."""
    root = (
        city_root.expanduser().resolve()
        if city_root
        else Path.cwd().resolve()
    )
    lines: List[str] = []
    lines.append("# ProtocolCity / BluePrint beta feedback")
    lines.append("")
    lines.append("**Paste into:** %s" % ISSUES_URL)
    lines.append("")
    lines.append("<!-- Title suggestion: BluePrint: <one-line symptom> -->")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    if symptoms.strip():
        lines.append(symptoms.strip())
    else:
        lines.append("_What broke in one or two sentences._")
    lines.append("")
    lines.append("## Expected")
    lines.append("")
    lines.append("_What should have happened._")
    lines.append("")
    lines.append("## Actual")
    lines.append("")
    lines.append("_What happened instead (error text, blank page, wrong Map state)._")
    lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("1. …")
    lines.append("2. …")
    lines.append("")
    lines.append("## Versions")
    lines.append("")
    lines.append(
        "- suite (protocolcity-blueprint / protocolcity): `%s` / `%s`"
        % (
            _pkg_version("protocolcity-blueprint"),
            _pkg_version("protocolcity"),
        )
    )
    lines.append(
        "- protocolcity-worklane / worklane: `%s` / `%s`"
        % (
            _pkg_version("protocolcity-worklane"),
            _pkg_version("worklane"),
        )
    )
    lines.append(
        "- protocolcity-workforce / workforce: `%s` / `%s`"
        % (
            _pkg_version("protocolcity-workforce"),
            _pkg_version("workforce"),
        )
    )
    lines.append("- python: `%s`" % sys.version.split()[0])
    lines.append(
        "- os: `%s %s (%s)`"
        % (platform.system(), platform.release(), platform.machine())
    )
    lines.append("- workspace: `%s`" % _path_display(root, full_paths))
    lines.append(
        "- generated_at: `%s`"
        % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    )
    lines.append("")

    # Doctor summary
    lines.append("## Doctor summary")
    lines.append("")
    try:
        from protocolcity.doctor import diagnose

        result = diagnose(root)
        summary = result.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        lines.append(
            "- missing: **%s** · conflict: **%s** · ok: **%s** · weak: **%s**"
            % (
                summary.get("missing", summary.get("bad", "?")),
                summary.get("conflict", "?"),
                summary.get("ok", "?"),
                summary.get("weak", "?"),
            )
        )
        findings = result.get("findings") or []
        hot = [
            f
            for f in findings
            if str(
                getattr(f, "status", None)
                or (f.get("status") if isinstance(f, dict) else "")
                or ""
            ).lower()
            in ("missing", "conflict", "error", "fail")
        ][:12]
        if hot:
            lines.append("")
            lines.append("Notable findings:")
            for f in hot:
                if isinstance(f, dict):
                    code = f.get("code") or "?"
                    detail = f.get("detail") or f.get("path") or ""
                else:
                    code = getattr(f, "code", "?")
                    detail = getattr(f, "detail", "") or getattr(f, "path", "")
                detail = _scrub_home(str(detail), full_paths)
                lines.append("- `%s` — %s" % (code, detail))
        else:
            lines.append("- (no missing/conflict findings)")
    except Exception as e:
        lines.append("- doctor failed: `%s`" % e)
    lines.append("")

    # Engine logs
    log_dir = root / ".protocolcity" / "logs"
    lines.append(
        "## Engine log tails (`%s`)" % _path_display(log_dir, full_paths)
    )
    lines.append("")
    if log_dir.is_dir():
        for name in sorted(log_dir.glob("*.log"))[:8]:
            lines.append("### %s" % name.name)
            lines.append("```")
            lines.append(_scrub_home(_tail_file(name, 30), full_paths))
            lines.append("```")
            lines.append("")
    else:
        lines.append(
            "(no log dir yet — run `blueprint serve --root <workspace>` once)"
        )
        lines.append("")

    # Pending desk
    pending = root / ".protocolcity" / "pending-desk.json"
    lines.append("## pending-desk.json")
    lines.append("")
    if pending.is_file():
        lines.append("```json")
        lines.append(_scrub_home(_tail_file(pending, 80), full_paths))
        lines.append("```")
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Generated locally by `blueprint feedback` (alias `protocolcity feedback`). "
        "Nothing was uploaded.*"
    )
    lines.append("")
    lines.append("### For AI hosts")
    lines.append("")
    lines.append(
        "If an agent filled this report: verify redaction, then have **You** paste "
        "into the issues URL above. Agents must not post to GitHub without You."
    )
    return "\n".join(lines)


def print_report(
    city_root: Optional[Path] = None,
    *,
    full_paths: bool = False,
    symptoms: str = "",
    write: bool = False,
    open_browser: bool = False,
    agent_prompt_only: bool = False,
) -> int:
    if agent_prompt_only:
        print(agent_prompt_text())
        print("", file=sys.stderr)
        print(
            "Copy the prompt into your AI host, then run: blueprint feedback",
            file=sys.stderr,
        )
        return 0

    body = gather_report(
        city_root, full_paths=full_paths, symptoms=symptoms
    )
    print(body)

    out_path: Optional[Path] = None
    if write and city_root is not None:
        root = city_root.expanduser().resolve()
        reports = root / ".protocolcity" / "reports"
        try:
            reports.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
            out_path = reports / ("feedback-%s.md" % stamp)
            out_path.write_text(body + "\n", encoding="utf-8")
        except OSError as e:
            print("warning: could not write report file: %s" % e, file=sys.stderr)

    print("", file=sys.stderr)
    print(
        "Review the block above, then open: %s" % ISSUES_URL,
        file=sys.stderr,
    )
    print(
        "AI hosts: blueprint feedback --agent-prompt  (paste ritual into chat)",
        file=sys.stderr,
    )
    if out_path is not None:
        print("Wrote: %s" % out_path, file=sys.stderr)

    if open_browser:
        try:
            webbrowser.open(ISSUES_URL)
            print("Opened issues page in browser.", file=sys.stderr)
        except Exception as e:
            print("warning: could not open browser: %s" % e, file=sys.stderr)

    return 0
