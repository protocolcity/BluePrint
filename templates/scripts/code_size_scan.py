#!/usr/bin/env python3
"""Scan a project tree for oversized first-party source files.

Standalone playbook helper for L0 skill ``code-efficiency``. No
protocolcity / BluePrint package import required — this public repo and
any founded workspace can run it.

  python3 scripts/code_size_scan.py
  python3 scripts/code_size_scan.py --root <project>
  python3 scripts/code_size_scan.py --root . --json
  python3 scripts/code_size_scan.py --help

Bands (physical lines / bytes) match templates/skills/code-efficiency:

  watch   ≥ 400 LOC or ≥ 24 KiB
  split   ≥ 800 LOC or ≥ 48 KiB
  urgent  ≥ 1 200 LOC or ≥ 80 KiB

Exit 0 after a report. ``--strict`` exits 1 when any split/urgent file
is found (CI / job smell). Override bands with flags; project AGENTS.md
may document different numbers — pass those flags when you run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple


WATCH_LOC = 400
SPLIT_LOC = 800
URGENT_LOC = 1200
WATCH_BYTES = 24 * 1024
SPLIT_BYTES = 48 * 1024
URGENT_BYTES = 80 * 1024

SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".rb",
        ".php",
        ".swift",
        ".cs",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".cxx",
        ".hpp",
        ".hh",
        ".m",
        ".mm",
        ".vue",
        ".svelte",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".sh",
        ".bash",
        ".zsh",
    }
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        "out",
        "coverage",
        "vendor",
        "third_party",
        "third-party",
        "exports",
        ".eggs",
        "egg-info",
        ".idea",
        ".vscode",
        ".cursor",
    }
)

SKIP_SUFFIXES = frozenset(
    {
        ".min.js",
        ".min.css",
        ".map",
        ".lock",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".pdf",
        ".bin",
        ".wasm",
    }
)

SKIP_FILE_NAMES = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Cargo.lock",
        "go.sum",
        "poetry.lock",
        "composer.lock",
        "Gemfile.lock",
    }
)

# Instruction / paper names — not product modules.
SKIP_PAPER_NAMES = frozenset(
    {
        "agents.md",
        "architecture.md",
        "contract.md",
        "prompt.md",
        "readme.md",
        "charter.md",
        "covenant.md",
        "manifesto.md",
        "founding.md",
        "running.md",
        "changelog.md",
        "license",
        "license.md",
    }
)


def _is_skip_dir(name: str) -> bool:
    if name in SKIP_DIR_NAMES:
        return True
    if name.startswith(".") and name not in {".", ".."}:
        # Hidden dirs are usually tooling, not first-party source.
        return True
    if name.endswith(".egg-info"):
        return True
    return False


def _is_skip_file(path: Path) -> bool:
    name = path.name
    lower = name.lower()
    if lower in SKIP_FILE_NAMES:
        return True
    if lower in SKIP_PAPER_NAMES:
        return True
    if name.startswith("."):
        return True
    for suf in SKIP_SUFFIXES:
        if lower.endswith(suf):
            return True
    if path.suffix.lower() not in SOURCE_SUFFIXES:
        return True
    # Generated / vendor-ish filenames.
    if ".min." in lower:
        return True
    if lower.endswith("_pb2.py") or lower.endswith(".pb.go"):
        return True
    return False


def iter_source_files(root: Path) -> Iterator[Path]:
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _is_skip_dir(d)]
        here = Path(dirpath)
        for fn in filenames:
            p = here / fn
            if _is_skip_file(p):
                continue
            yield p


def count_lines(path: Path) -> Tuple[int, int]:
    """Return (physical_lines, nonblank_lines). Binary → (0, 0)."""
    try:
        data = path.read_bytes()
    except OSError:
        return 0, 0
    if b"\x00" in data[:4096]:
        return 0, 0
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            return 0, 0
    physical = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    if not text:
        physical = 0
    nonblank = sum(1 for line in text.splitlines() if line.strip())
    return physical, nonblank


def band_for(loc: int, size: int, watch_loc: int, split_loc: int, urgent_loc: int,
             watch_bytes: int, split_bytes: int, urgent_bytes: int) -> Optional[str]:
    if loc >= urgent_loc or size >= urgent_bytes:
        return "urgent"
    if loc >= split_loc or size >= split_bytes:
        return "split"
    if loc >= watch_loc or size >= watch_bytes:
        return "watch"
    return None


def scan(
    root: Path,
    *,
    watch_loc: int = WATCH_LOC,
    split_loc: int = SPLIT_LOC,
    urgent_loc: int = URGENT_LOC,
    watch_bytes: int = WATCH_BYTES,
    split_bytes: int = SPLIT_BYTES,
    urgent_bytes: int = URGENT_BYTES,
) -> List[dict]:
    rows: List[dict] = []
    for path in iter_source_files(root):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        loc, nonblank = count_lines(path)
        if loc == 0 and size == 0:
            continue
        band = band_for(
            loc,
            size,
            watch_loc,
            split_loc,
            urgent_loc,
            watch_bytes,
            split_bytes,
            urgent_bytes,
        )
        if band is None:
            continue
        rel = path.relative_to(root).as_posix()
        rows.append(
            {
                "path": rel,
                "loc": loc,
                "nonblank": nonblank,
                "bytes": size,
                "band": band,
            }
        )
    rank = {"urgent": 0, "split": 1, "watch": 2}
    rows.sort(key=lambda r: (rank[r["band"]], -r["loc"], r["path"]))
    return rows


def _fmt_bytes(n: int) -> str:
    if n >= 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n} B"


def render_markdown(
    root: Path,
    rows: Sequence[dict],
    *,
    watch_loc: int = WATCH_LOC,
    split_loc: int = SPLIT_LOC,
    urgent_loc: int = URGENT_LOC,
    watch_bytes: int = WATCH_BYTES,
    split_bytes: int = SPLIT_BYTES,
    urgent_bytes: int = URGENT_BYTES,
) -> str:
    counts = {"watch": 0, "split": 0, "urgent": 0}
    for r in rows:
        counts[r["band"]] += 1
    lines = [
        f"# Code size scan · `{root}`",
        "",
        f"- files over band: **{len(rows)}** "
        f"(watch={counts['watch']} · split={counts['split']} · urgent={counts['urgent']})",
        f"- bands: watch≥{watch_loc} / {_fmt_bytes(watch_bytes)} · "
        f"split≥{split_loc} / {_fmt_bytes(split_bytes)} · "
        f"urgent≥{urgent_loc} / {_fmt_bytes(urgent_bytes)}",
        "",
        "| band | path | loc | nonblank | bytes |",
        "|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| — | *(none)* | | | |")
    else:
        for r in rows:
            lines.append(
                f"| {r['band']} | `{r['path']}` | {r['loc']} | {r['nonblank']} | {_fmt_bytes(r['bytes'])} |"
            )
    lines.append("")
    lines.append(
        "Playbook: L0 skill `code-efficiency`. One split WO/PR at a time. "
        "Prefer extract module over rewrite."
    )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--root",
        default=".",
        help="project folder to walk (default: cwd)",
    )
    p.add_argument("--json", action="store_true", help="JSON object on stdout")
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when any split or urgent file is found",
    )
    p.add_argument("--watch-loc", type=int, default=WATCH_LOC)
    p.add_argument("--split-loc", type=int, default=SPLIT_LOC)
    p.add_argument("--urgent-loc", type=int, default=URGENT_LOC)
    p.add_argument("--watch-bytes", type=int, default=WATCH_BYTES)
    p.add_argument("--split-bytes", type=int, default=SPLIT_BYTES)
    p.add_argument("--urgent-bytes", type=int, default=URGENT_BYTES)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    rows = scan(
        root,
        watch_loc=args.watch_loc,
        split_loc=args.split_loc,
        urgent_loc=args.urgent_loc,
        watch_bytes=args.watch_bytes,
        split_bytes=args.split_bytes,
        urgent_bytes=args.urgent_bytes,
    )
    if args.json:
        payload = {
            "root": str(root),
            "counts": {
                "watch": sum(1 for r in rows if r["band"] == "watch"),
                "split": sum(1 for r in rows if r["band"] == "split"),
                "urgent": sum(1 for r in rows if r["band"] == "urgent"),
            },
            "files": rows,
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(
            render_markdown(
                root,
                rows,
                watch_loc=args.watch_loc,
                split_loc=args.split_loc,
                urgent_loc=args.urgent_loc,
                watch_bytes=args.watch_bytes,
                split_bytes=args.split_bytes,
                urgent_bytes=args.urgent_bytes,
            )
        )
        sys.stdout.write("\n")
    if args.strict and any(r["band"] in {"split", "urgent"} for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
