#!/usr/bin/env python3
"""Local verification entrypoint for BluePrint source (component, browser, package and installed tiers)."""
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
    base = os.pathsep.join((str(OVERVIEW), str(ROOT)))
    if extra:
        base = extra + os.pathsep + base
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


def tier_installed(root: Path, expected_version: str) -> None:
    import json
    from urllib.request import urlopen
    workspace = root.expanduser().resolve()
    receipt = json.loads((workspace / '.blueprint/deployment.json').read_text())
    port = receipt.get('port')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Selected workspace has no valid deployment port.')
    with urlopen(f'http://127.0.0.1:{port}/api/operations', timeout=5) as response:
        actual = json.load(response)
    if (actual.get('workspace', {}).get('path') != str(workspace)
            or actual.get('build') != expected_version or receipt.get('version') != expected_version):
        raise ValueError('Responding workspace/build does not match the expected installation.')
    for path in ('/', '/work', '/agents', '/map', '/settings'):
        with urlopen(f'http://127.0.0.1:{port}' + path, timeout=5) as response:
            if response.status != 200 or b'<html' not in response.read(1024).lower():
                raise ValueError('Installed application route did not return HTML.')
    print('Installed identity and critical read-only routes verified; action acceptance is separate.')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=("edit", "pr", "release", "installed"),
        default="edit",
        help="edit=component suites; pr=+skip audit+browser; release=+packaging checks",
    )
    parser.add_argument("--root", type=Path, help="selected workspace for installed checks")
    parser.add_argument("--expected-version", help="reviewed installed version")
    args = parser.parse_args(argv)
    if args.tier == "installed":
        if not args.root or not args.expected_version:
            parser.error("installed checks require --root and --expected-version")
        tier_installed(args.root, args.expected_version)
        return 0
    steps = {
        "edit": tier_edit,
        "pr": tier_pr,
        "release": tier_release,
    }
    steps[args.tier]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
