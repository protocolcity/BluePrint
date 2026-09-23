#!/usr/bin/env python3
"""Report unittest skips and explicit environment gates in Overview and Map suites."""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def _scan(path: Path) -> list[tuple[str, int, str]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    hits: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name != "skipTest":
                continue
            reason = ast.get_source_segment(text, node.args[0]) if node.args else "?"
            hits.append((str(path), node.lineno, reason))
    return hits


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    targets = [
        root / "overview/v1/tests",
        root / "map/v1/tests",
        root / "tests",
    ]
    rows: list[tuple[str, int, str]] = []
    for base in targets:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("test_*.py")):
            rows.extend(_scan(path))
    print("skip audit — overview/map component suites")
    print("file:line reason")
    for path, line, reason in rows:
        print(f"{path}:{line} {reason}")
    print(f"total explicit skips: {len(rows)}")
    print(
        "notes: BP_TEST_WORKLANE_PYTHON gates installed-engine integration; "
        "node unavailable gates in-process DOM harness checks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
