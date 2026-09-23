#!/usr/bin/env python3
"""Check matching package versions, exact engine pins and public artifact hygiene.

Builds wheel/sdist candidates without uploading. Findings show only file paths
and rule names, never possible credential values. Release notes, templates and
public tests are checked alongside both preferred and compatibility packages.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
PREFERRED_PYPROJECT = ROOT / "pyproject.toml"
COMPAT_PYPROJECT = ROOT / "packaging" / "pypi" / "protocolcity" / "pyproject.toml"
RELEASE_NOTES = ROOT / "docs" / "releases"

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


def check_metadata() -> List[str]:
    failures: List[str] = []
    metadata = []
    for path in (PREFERRED_PYPROJECT, COMPAT_PYPROJECT):
        try:
            metadata.append(tomllib.loads(_read(path))["project"])
        except (OSError, ValueError, KeyError) as exc:
            failures.append(f"{path.name}: invalid project metadata ({type(exc).__name__})")
    if len(metadata) != 2:
        return failures
    preferred, compat = metadata
    version = preferred.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)", version):
        failures.append("preferred package: invalid or missing static version")
    if compat.get("version") != version:
        failures.append("compatibility and preferred package versions differ")
    expected_alias = f"protocolcity-blueprint=={version}"
    if compat.get("dependencies") != [expected_alias]:
        failures.append("compatibility dependency must match preferred version exactly")
    engine_names = ("protocolcity-worklane", "protocolcity-workforce")
    preferred_pins = preferred.get("optional-dependencies", {}).get("engines", [])
    compat_pins = compat.get("optional-dependencies", {}).get("engines", [])
    if not all(isinstance(pins, list) and all(isinstance(pin, str) for pin in pins)
               for pins in (preferred_pins, compat_pins)):
        return failures + ["engine dependencies must be string lists"]
    for name in engine_names:
        matches = [pin for pin in preferred_pins if isinstance(pin, str) and pin.startswith(name + "==")]
        if len(matches) != 1 or not re.fullmatch(re.escape(name) + r"==[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)", matches[0]):
            failures.append(f"preferred engines need one exact {name} version")
        elif matches[0] not in compat_pins:
            failures.append(f"compatibility engines must match {name} pin")
    if len(preferred_pins) != 2 or set(compat_pins) != set(preferred_pins + [f"protocolcity-blueprint[engines]=={version}"]):
        failures.append("unexpected or mismatched engine dependencies")
    text = _read(PREFERRED_PYPROJECT)
    if ".mcp.json" not in text or "exclude-package-data" not in text:
        failures.append("preferred package must exclude host .mcp.json files")
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
    notes = sorted(RELEASE_NOTES.glob("*.md"))
    if not notes:
        return ["missing release notes directory or Markdown notes"]
    failures: List[str] = []
    for path in notes:
        text = _read(path)
        label = path.relative_to(ROOT)
        if HOST_USERS.search(text) or HOST_HOME.search(text):
            failures.append(f"{label}: host-path fingerprint")
        if SECRET_MATERIAL.search(text):
            failures.append(f"{label}: secret material")
        if "twine upload" in text and "dry-run" not in text.lower():
            failures.append(f"{label}: live twine upload instruction")
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
        "matching package versions and exact engine pins, "
        "no host MCP/runtime/paths in artifacts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
