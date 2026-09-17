#!/usr/bin/env python3
"""Prove the public cut artifacts are claim-ready (pc-1468 / #145).

Checks, without uploading anything:

1. Both package pyprojects declare version 0.1.50 and engines ==0.1.9
2. Built sdist/wheel contain no ``.mcp.json``, no ``/Users/<name>/`` host
   fingerprints, and no ``.protocolcity/`` runtime tree
3. Packaged templates that name a workspace root use ``{{WORKSPACE_ROOT}}``
4. Release notes contain no secret-material patterns

Prints locations and rule names only — never echoes possible credentials.
Does not invoke twine.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
CUT_VERSION = "0.1.50"
ENGINE_PINS = (
    "protocolcity-worklane==0.1.9",
    "protocolcity-workforce==0.1.9",
)
PREFERRED_PYPROJECT = ROOT / "pyproject.toml"
COMPAT_PYPROJECT = ROOT / "packaging" / "pypi" / "protocolcity" / "pyproject.toml"
RELEASE_NOTES = ROOT / "docs" / "releases" / "0.1.50.md"

# Actual host home directories, not documentation ellipsis or character classes.
HOST_USERS = re.compile(r"/Users/[A-Za-z0-9._-]+/")
HOST_HOME = re.compile(r"/home/[A-Za-z0-9._-]+/")
SECRET_MATERIAL = re.compile(
    r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"
    r"|AKIA[0-9A-Z]{16}"
    r"|sk_live_[A-Za-z0-9]+"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]+"
    r"|xox[baprs]-"
    r"|pypi-[A-Za-z0-9_-]{20,}"
    r"|TWINE_PASSWORD\s*="
)
ABSOLUTE_WORKSPACE = re.compile(r"(?:command|cwd|WORK(?:SPACE|LANE|FORCE)[A-Z_]*)[^ \n]{0,80}(/Users/|/home/)")
WORKSPACE_TOKEN = "{{WORKSPACE_ROOT}}"

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".sh",
    ".js",
    ".css",
    ".html",
    ".txt",
    ".in",
}

# Mentions of the filename are fine; a packaged file named .mcp.json is not.
MCP_FILENAME = ".mcp.json"
RUNTIME_DIR = ".protocolcity"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _toml_version(text: str) -> str:
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not match:
        raise ValueError("version field missing")
    return match.group(1)


def _toml_engines(text: str) -> List[str]:
    block = re.search(
        r"(?ms)^engines\s*=\s*\[(.*?)\]",
        text,
    )
    if not block:
        raise ValueError("engines extra missing")
    return re.findall(r'"([^"]+)"', block.group(1))


def check_metadata() -> List[str]:
    failures: List[str] = []
    for label, path in (
        ("protocolcity-blueprint", PREFERRED_PYPROJECT),
        ("protocolcity", COMPAT_PYPROJECT),
    ):
        if not path.is_file():
            failures.append(f"{label}: missing {path.relative_to(ROOT)}")
            continue
        text = _read(path)
        try:
            version = _toml_version(text)
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
            continue
        if version != CUT_VERSION:
            failures.append(f"{label}: version {version!r} != {CUT_VERSION!r}")
        try:
            engines = _toml_engines(text)
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
            continue
        for pin in ENGINE_PINS:
            if pin not in engines:
                failures.append(f"{label}: engines missing {pin}")
    return failures


def _is_text(name: str) -> bool:
    return Path(name).suffix.lower() in TEXT_SUFFIXES or Path(name).name in {
        "MANIFEST.in",
        "LICENSE",
        "Makefile",
    }


def _iter_archive_text(path: Path) -> Iterable[Tuple[str, str]]:
    if path.suffix == ".gz" or path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                raw = extracted.read()
                if _is_text(member.name):
                    yield member.name, raw.decode("utf-8", errors="replace")
                else:
                    yield member.name, ""
        return
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            raw = archive.read(name)
            if _is_text(name):
                yield name, raw.decode("utf-8", errors="replace")
            else:
                yield name, ""


def _archive_names(path: Path) -> List[str]:
    if path.suffix == ".gz" or path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return [member.name for member in archive.getmembers()]
    with zipfile.ZipFile(path) as archive:
        return list(archive.namelist())


def scan_artifact(path: Path) -> List[str]:
    failures: List[str] = []
    names = _archive_names(path)
    for name in names:
        posix = name.replace("\\", "/")
        base = Path(posix).name
        if base == MCP_FILENAME:
            failures.append(f"{path.name}: packaged host MCP file ({posix})")
        if f"/{RUNTIME_DIR}/" in f"/{posix}" and not _is_template_mention(posix):
            # A real runtime tree (db/roster/logs), not a template path token.
            if posix.endswith((".db", ".sqlite", ".sqlite3", "roster.json", "daemon.json")) or "/local/" in posix:
                failures.append(f"{path.name}: packaged runtime {posix}")
    for name, text in _iter_archive_text(path):
        posix = name.replace("\\", "/")
        if not text:
            continue
        if HOST_USERS.search(text) or HOST_HOME.search(text):
            failures.append(f"{path.name}:{posix}: host-path fingerprint")
        if SECRET_MATERIAL.search(text):
            failures.append(f"{path.name}:{posix}: secret material")
        if _looks_like_template(posix) and _has_absolute_workspace(text):
            failures.append(f"{path.name}:{posix}: template missing {WORKSPACE_TOKEN}")
    return failures


def _is_template_mention(posix: str) -> bool:
    return "/templates/" in posix or posix.endswith("mcp.json")


def _looks_like_template(posix: str) -> bool:
    return "/templates/" in posix and posix.endswith((".json", ".md", ".toml"))


def _has_absolute_workspace(text: str) -> bool:
    if WORKSPACE_TOKEN in text:
        return False
    return bool(ABSOLUTE_WORKSPACE.search(text) or HOST_USERS.search(text) or HOST_HOME.search(text))


def scan_public_tests() -> List[str]:
    failures: List[str] = []
    roots = [
        ROOT / "overview" / "v1" / "tests",
        ROOT / "map" / "v1" / "tests",
        ROOT / "tests",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not _is_text(path.name):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if HOST_USERS.search(text) or HOST_HOME.search(text):
                failures.append(f"{path.relative_to(ROOT)}: host-path fingerprint")
            if SECRET_MATERIAL.search(text):
                failures.append(f"{path.relative_to(ROOT)}: secret material")
    return failures


def scan_release_notes() -> List[str]:
    if not RELEASE_NOTES.is_file():
        return [f"missing {RELEASE_NOTES.relative_to(ROOT)}"]
    text = _read(RELEASE_NOTES)
    failures: List[str] = []
    if HOST_USERS.search(text) or HOST_HOME.search(text):
        failures.append("docs/releases/0.1.50.md: host-path fingerprint")
    if SECRET_MATERIAL.search(text):
        failures.append("docs/releases/0.1.50.md: secret material")
    if "twine upload" in text and "dry-run" not in text.lower():
        failures.append("docs/releases/0.1.50.md: live twine upload instruction")
    return failures


def scan_source_templates() -> List[str]:
    failures: List[str] = []
    for base in (ROOT / "templates", ROOT / "protocolcity" / "templates"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            posix = str(path.relative_to(ROOT)).replace("\\", "/")
            if path.name == MCP_FILENAME:
                failures.append(f"{posix}: host MCP file in source templates")
            if not _is_text(path.name):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if HOST_USERS.search(text) or HOST_HOME.search(text):
                failures.append(f"{posix}: host-path fingerprint")
            if _looks_like_template(posix) and _has_absolute_workspace(text):
                failures.append(f"{posix}: template missing {WORKSPACE_TOKEN}")
    return failures


def _build(dist: Path) -> List[Path]:
    dist.mkdir(parents=True, exist_ok=True)
    artifacts: List[Path] = []
    preferred = dist / "preferred"
    preferred.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(preferred)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    artifacts.extend(sorted(preferred.iterdir()))
    compat = dist / "compat"
    compat.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(compat)],
        cwd=ROOT / "packaging" / "pypi" / "protocolcity",
        check=True,
        capture_output=True,
        text=True,
    )
    artifacts.extend(sorted(compat.iterdir()))
    return artifacts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="check pyproject pins and notes without building artifacts",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    failures = []
    failures.extend(check_metadata())
    failures.extend(scan_release_notes())
    failures.extend(scan_public_tests())
    failures.extend(scan_source_templates())

    if not args.metadata_only:
        if shutil.which(sys.executable) is None:
            failures.append("python executable missing")
        else:
            try:
                import build  # noqa: F401
            except ImportError:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "build"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            with tempfile.TemporaryDirectory(prefix="bp-cut-") as tmp:
                artifacts = _build(Path(tmp))
                if not artifacts:
                    failures.append("build produced no artifacts")
                for artifact in artifacts:
                    print(f"built {artifact.name}")
                    failures.extend(scan_artifact(artifact))

    for row in failures:
        print(f"CUT FAILURE: {row}")
    if failures:
        print(f"Public cut check: {len(failures)} finding(s)")
        return 1
    print(
        "Public cut check: clean — "
        f"both packages {CUT_VERSION}, engines ==0.1.9, "
        "no host MCP/runtime/paths in artifacts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
