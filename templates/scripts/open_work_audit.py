#!/usr/bin/env python3
"""CLI shim — open-work audit lives in protocolcity.open_work_audit.

Planted by found / seed-ops. Requires the blueprint / protocolcity package.

  python scripts/open_work_audit.py [--json] [--feeds] [--history] [--process]
  blueprint doctor   # includes feeds + history by default
"""

from __future__ import annotations

import sys


def main() -> int:
    from protocolcity.open_work_audit import main as _main

    return int(_main())


if __name__ == "__main__":
    raise SystemExit(main())
