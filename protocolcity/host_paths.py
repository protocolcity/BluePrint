"""Host-path hardcode lint (pc-956).

Fails on operational defaults that reintroduce Class E bugs:
``expanduser("~/Developer")``, ``Path.home() / "Developer"``, absolute
``/Users/…`` / ``/home/…`` under suite, protocolcity, scripts.

CLI entry: ``scripts/check_no_host_paths.py`` for contributor source checks.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    (
        "expanduser_Developer",
        re.compile(r"""expanduser\s*\(\s*['"]~/Developer['"]\s*\)"""),
    ),
    (
        "tilde_Developer_path",
        re.compile(r"""['"]~/Developer(?:/[^'"]*)?['"]"""),
    ),
    (
        "Path_home_Developer",
        re.compile(r"""Path\.home\s*\(\s*\)\s*/\s*['"]Developer['"]"""),
    ),
    (
        "Users_abs",
        re.compile(r"""/Users/[A-Za-z0-9._-]+/"""),
    ),
    (
        "home_abs",
        re.compile(r"""/home/[A-Za-z0-9._-]+/"""),
    ),
)

_ALLOW_LINE = re.compile(
    r"(?i)("
    r"no hard-?coded|must not|forbid|reject|assert.*not|"
    r"grep\s+-|re\.search|"
    r"legacy bad|e\.g\.|example|or their workspace|"
    r"pc-956|check_no_host_paths|workspace-path-hardcode|"
    r"host-path hardcode"
    r")"
)

_SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    "_archive",
    "local",
    "logs",
    ".pytest_cache",
    "templates",
}

_TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".css",
    ".html",
    ".md",
    ".toml",
    ".json",
    ".plist",
    ".yml",
    ".yaml",
}

_SKIP_FILE_NAMES = {
    "check_no_host_paths.py",
    "check_no_host_paths.exceptions",
    "host_paths.py",
    # Denylist self-test seeds a banned personal-path sample so the scrub
    # patterns stay live; do not treat that seed as a host fingerprint.
    "check_export_scrub.py",
    "check_release_artifacts.py",
}


def default_exceptions_path(repo: Path) -> Path:
    return repo / "scripts" / "check_no_host_paths.exceptions"


def load_exceptions(path: Path) -> List[str]:
    if not path.is_file():
        return []
    out: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def is_excepted(rel: str, line: str, exceptions: Sequence[str]) -> bool:
    for ex in exceptions:
        if "::" in ex:
            pref, sub = ex.split("::", 1)
            if rel == pref or rel.startswith(pref.rstrip("/") + "/"):
                if sub in line:
                    return True
        else:
            if rel == ex or rel.startswith(ex.rstrip("/") + "/"):
                return True
    return False


def _iter_files(roots: Sequence[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            files.append(root)
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _SKIP_DIR_NAMES for part in p.parts):
                continue
            if p.suffix.lower() not in _TEXT_SUFFIXES and p.name not in (
                "Makefile",
                "Dockerfile",
            ):
                continue
            if p.name in _SKIP_FILE_NAMES:
                continue
            files.append(p)
    return files


def scan_host_paths(
    repo: Path,
    *,
    include_workers: bool = True,
    exceptions: Optional[Sequence[str]] = None,
) -> Dict:
    """Scan product and optional worker instructions; use explicit exceptions."""
    roots = [
        repo / "suite",
        repo / "protocolcity",
        repo / "scripts",
    ]
    if include_workers:
        roots.append(repo / "workers")
    ex = list(exceptions or [])
    hits: List[Dict] = []
    excepted: List[Dict] = []

    for path in _iter_files(roots):
        try:
            rel = str(path.relative_to(repo)).replace("\\", "/")
        except ValueError:
            rel = str(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if _ALLOW_LINE.search(line):
                continue
            for kind, pat in PATTERNS:
                if not pat.search(line):
                    continue
                row = {
                    "path": rel,
                    "line": i,
                    "kind": kind,
                    "text": line.strip()[:200],
                }
                if is_excepted(rel, line, ex):
                    excepted.append(row)
                else:
                    hits.append(row)
                break

    return {
        "ok": len(hits) == 0,
        "repo": str(repo),
        "hit_count": len(hits),
        "exception_count": len(excepted),
        "hits": hits,
        "excepted": excepted,
    }


def run_check_paths(
    repo: Path,
    *,
    include_workers: bool = True,
    json_out: bool = False,
    exceptions_path: Optional[Path] = None,
) -> int:
    """Print report; return 0 if clean, 1 if hits remain."""
    ex_path = exceptions_path or default_exceptions_path(repo)
    report = scan_host_paths(
        repo,
        include_workers=include_workers,
        exceptions=load_exceptions(ex_path),
    )
    if json_out:
        print(json.dumps(report, indent=2))
    else:
        print(
            "check_no_host_paths: %d hit(s), %d excepted (repo=%s)"
            % (report["hit_count"], report["exception_count"], repo)
        )
        for h in report["hits"]:
            print(
                "  FAIL %s:%d [%s] %s"
                % (h["path"], h["line"], h["kind"], h["text"])
            )
        if report["ok"]:
            print("ok — no unexcepted host-path hardcodes in scan scope")
        else:
            print(
                "fail — fix hits or document in scripts/check_no_host_paths.exceptions",
                file=sys.stderr,
            )
    return 0 if report["ok"] else 1
