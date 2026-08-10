#!/usr/bin/env python3
"""CLI shim for protocolcity.open_work_audit.

Works from workspace-root plants and parcel scripts without a repo venv:

  python3 scripts/open_work_audit.py [--json] [--feeds] [--history] [--process] [--decay]
  python3 ProtocolCity/scripts/open_work_audit.py
  blueprint doctor
"""

from __future__ import annotations

import sys
from pathlib import Path


def _package_roots(script: Path) -> list[Path]:
    """Candidate roots that may host the protocolcity package."""
    here = script.resolve()
    root = here.parent.parent
    roots = [root, root / "ProtocolCity"]
    raw = script.absolute()
    if raw != here:
        raw_root = raw.parent.parent
        roots.extend([raw_root, raw_root / "ProtocolCity"])
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main() -> int:
    try:
        from protocolcity.open_work_audit import main as _main

        return int(_main())
    except ImportError as first_err:
        err: BaseException = first_err
        for root in _package_roots(Path(__file__)):
            if not (root / "protocolcity" / "__init__.py").is_file():
                continue
            root_s = str(root)
            if root_s not in sys.path:
                sys.path.insert(0, root_s)
            try:
                from protocolcity.open_work_audit import main as _main  # type: ignore

                return int(_main())
            except ImportError as e:
                err = e
        raise SystemExit(
            "protocolcity package not found. Install blueprint/protocolcity "
            "or run from a monorepo with ProtocolCity/ next to scripts/."
        ) from err


if __name__ == "__main__":
    raise SystemExit(main())
