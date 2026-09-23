#!/usr/bin/env python3
"""Local verification entrypoint for BluePrint source (pc-1570 tiers)."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get("BP_VERIFY_PYTHON", sys.executable)
OVERVIEW = ROOT / "overview/v1"
MAP = ROOT / "map/v1"
BROWSER = ROOT / "browser-tests"


def _env(extra: str = "") -> dict[str, str]:
    base = f"{OVERVIEW}:{ROOT}"
    if extra:
        base = f"{extra}:{base}"
    env = os.environ.copy()
    env["PYTHONPATH"] = base
    return env


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env or os.environ.copy(), check=True)


def tier_edit() -> None:
    _run(
        [PYTHON, "-m", "unittest", "discover", "-s", str(OVERVIEW / "tests")],
        env=_env(),
    )
    _run(
        [PYTHON, "-m", "unittest", "discover", "-s", str(MAP / "tests")],
        env=_env(f"{MAP}"),
    )


def tier_pr() -> None:
    tier_edit()
    _run([PYTHON, str(ROOT / "scripts/audit_test_skips.py")])
    _run(
        [
            PYTHON,
            "-m",
            "pytest",
            str(BROWSER),
            "-q",
            "--browser",
            "chromium",
        ],
        env=os.environ.copy(),
    )


def tier_release() -> None:
    tier_pr()
    _run(["bash", str(ROOT / "scripts/templates_sync.sh"), "--check"])
    _run([PYTHON, str(ROOT / "scripts/check_source_surface.py")])
    _run([PYTHON, str(ROOT / "scripts/check_no_host_paths.py")])
    _run([PYTHON, str(ROOT / "scripts/check_release_artifacts.py")])


def tier_installed() -> None:
    print(
        "installed smoke is host-only: activate the reviewed wheel under the selected "
        "workspace, confirm /api/operations build identity, then exercise the changed "
        "lens manually. Source tiers do not substitute for installed acceptance."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("edit", "pr", "release", "installed"),
        default="edit",
        help="edit=component suites; pr=+skip audit+browser; release=+packaging checks",
    )
    args = parser.parse_args(argv)
    steps = {
        "edit": tier_edit,
        "pr": tier_pr,
        "release": tier_release,
        "installed": tier_installed,
    }
    steps[args.tier]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
