#!/usr/bin/env python3
"""CLI for protocolcity.host_paths (pc-956)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from protocolcity.host_paths import run_check_paths


if __name__ == "__main__":
    raise SystemExit(run_check_paths(ROOT, json_out="--json" in sys.argv))
