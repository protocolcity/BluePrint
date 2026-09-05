#!/usr/bin/env python3
"""Export / citizen-surface vocabulary scrub (pc-991 / pc-1144).

Single source of scrub patterns consumed by:

- ``scripts/export_blueprint.sh`` / ``export_charter.sh`` — audit DEST after
  doc surgery (``--dest``: extra suffixes + expanded ticket prefixes)
- ``scripts/suite_ship_lint.sh`` — commit-time audit of the shipped set
- Public export CI (planted ``export-surface.yml``) — same ``--dest`` scan

Historically these greps lived only in ``export_blueprint.sh`` §4, so
leaks in ``templates/`` were caught at export staging (pc-978). This module
is the shared definition so a leak fails at lint, not at publish.

Patterns (keep names stable — tests pin them):

1. personal paths / handles
2. internal ticket references
3. internal hosts / aliases
4. internal governance term (founder → citizen in public docs)
5. sibling POS product slugs (``oneseo-pos`` / ``OneSeoPOS`` / ``oneseo_pos``)
6. sibling POS ticket/prefix forms (``osp-`` / ``regi-``)
7. sibling POS customer / host-product identity (Mio Mercado / retired LAN name)
8. secret material (keys / tokens)

Ruling — what the source-set scan covers (pc-1144):

| Class | Surface | Policy |
|---|---|---|
| A | Citizen docs (``.md``) under ``DEFAULT_SOURCE_REL_PATHS`` | Full scrub |
| B | Planted ops scripts (``.py`` / ``.sh`` / ``.ps1`` under ``templates/``) | Same full scrub |
| C | MCP runtime JSON (module path / env renames) | **Out of source-set default** — dest scan skips ``mcp.json`` + ``agents/mcp/**`` |
| D | Host monorepo ``scripts/`` (not under templates) | Internal ops; not plant kit |

Source-set ticket prefixes stay ``pc|tp|so|t|oc`` because planted ``*.md``
still cite ``wf-`` / ``wl-`` law; DEST surgery strips those before ``--dest``.
``--dest`` expands tickets to ``wl|wf|gf|ts|osp|regi`` so leftovers fail
the public parcel, including planted ``*.json``.

``library/city-hall/`` is **not** on the export whitelist. Patterns still
apply if a POS term lands under the shipped set (templates / example /
export docs). Plant-kit ``BOUNDARIES.md`` may name the suite ↔ sibling POS
grant as a worked example — see ``SCRUB_ALLOW_LABELS_BY_REL``.

Machine-local commit-email history stays export-only (needs DEST ``.git``).
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Sequence, Tuple

# ── Single source of patterns (export_blueprint.sh §4 historically) ─────────
# Each: (label, regex, case_insensitive)
TICKET_SOURCE = r"\b(pc|tp|so|t|oc)-[0-9]+\b"
TICKET_DEST = r"\b(pc|tp|so|t|oc|wl|wf|gf|ts|osp|regi)-[0-9]+\b"

SCRUB_PATTERNS: Tuple[Tuple[str, str, bool], ...] = (
    (
        "personal path/handle",
        r"eliefrainseo|seoeli89|/Users/|~/Developer|Elis-Mac-mini|e\.seo@icloud\.com",
        False,
    ),
    (
        "internal ticket reference",
        TICKET_SOURCE,
        False,
    ),
    (
        "internal host/alias",
        r"tradeos|ticketingprotocol|founder-terminal|launchd",
        True,
    ),
    (
        "internal governance term (founder)",
        r"\bfounder\b",
        True,
    ),
    (
        "sibling POS product",
        r"oneseo-pos|OneSeoPOS|oneseo_pos",
        True,
    ),
    (
        "sibling POS ticket/prefix",
        # Prefix forms (osp- / legacy regi-), including bare `osp-` / `regi-`
        # and ticket ids. Do not use a bare `\bosp\b` / `\bpos\b` — those
        # smash generic words (hospital, position, register, region).
        r"\bosp-|\bregi-",
        True,
    ),
    (
        "sibling POS customer identity",
        r"Mio Mercado|mio-mercado|ops\.oneseo\.internal",
        True,
    ),
    (
        "secret material",
        r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"
        r"|AKIA[0-9A-Z]{16}"
        r"|sk_live_[A-Za-z0-9]+"
        r"|ghp_[A-Za-z0-9]{20,}"
        r"|github_pat_[A-Za-z0-9_]+"
        r"|xox[baprs]-",
        False,
    ),
)

# Plant-kit BOUNDARIES is the one instructional place a sibling POS product
# slug may appear (worked grant example). Match by trailing rel path so a
# DEST export tree (`…/templates/BOUNDARIES.md`) gets the same exception.
# Never allow personal paths, ticket ids, or customer-host identity here.
SCRUB_ALLOW_LABELS_BY_REL: Dict[str, FrozenSet[str]] = {
    "templates/BOUNDARIES.md": frozenset({"sibling POS product"}),
    "protocolcity/templates/BOUNDARIES.md": frozenset({"sibling POS product"}),
}

# File suffixes scanned on the commit-time source set (pc-1144 widens from
# ``.md``-only so planted ``templates/scripts/*.{py,sh}`` cannot re-leak).
# ``.ps1`` ships in the BluePrint parcel (install_windows.ps1).
# JSON MCP manifests stay Class C (not listed) until the engine rename lands.
# Do not widen lightly: ``launchctl`` contains the substring ``launchd``.
DEFAULT_SUFFIXES = (".md", ".py", ".sh", ".ps1")

# DEST / public-parcel scan: planted JSON + workflows after surgery.
DEST_SUFFIXES = (".md", ".py", ".sh", ".ps1", ".json", ".yml", ".yaml")

# Relative paths under the ProtocolCity repo that ship in the public export
# *as source* (no DEST surgery that rewrites founder/hosts). CHARTER is
# excluded: export rewrites its status line + strips ticket tokens before
# scrub. FIRST_RUN is not on the export whitelist (internal install guide).
DEFAULT_SOURCE_REL_PATHS: Tuple[str, ...] = (
    "templates",
    "protocolcity/templates",
    "example",
    "docs/RUNNING.md",
    "docs/FOUNDING.md",
    "docs/manifesto.md",
    "docs/WINDOWS_FIRST_USER.md",
    "README.public.md",
    "README.charter.md",
    "README.charter-templates.md",
    "scripts/install_windows.ps1",
    ".github/ISSUE_TEMPLATE",
)

# Never scan the denylist module itself (it names every banned token).
SKIP_FILENAMES = frozenset({"check_export_scrub.py"})


def allow_labels_for(path: Path) -> FrozenSet[str]:
    """Return allowlisted labels for a path (DEST-safe trailing-rel match)."""
    posix = path.as_posix().replace("\\", "/")
    for rel, labels in SCRUB_ALLOW_LABELS_BY_REL.items():
        if posix == rel or posix.endswith("/" + rel):
            return labels
    return frozenset()


def filter_allowed(
    hits: Sequence[Tuple[str, Path, int, str]],
) -> List[Tuple[str, Path, int, str]]:
    """Drop hits whose label is allowlisted for that file."""
    kept: List[Tuple[str, Path, int, str]] = []
    for hit in hits:
        label, path = hit[0], hit[1]
        if label in allow_labels_for(path):
            continue
        kept.append(hit)
    return kept


def _skip_path(path: Path, *, dest: bool) -> bool:
    if path.name in SKIP_FILENAMES:
        return True
    if not dest:
        return False
    # Class C — MCP runtime JSON. Dest still ships these; module-path rename
    # is a sister slice. Ticket leftovers in notes are stripped at source.
    if path.name == "mcp.json":
        return True
    parts = path.parts
    if "mcp" in parts and "agents" in parts:
        return True
    return False


def _compiled(*, dest: bool = False) -> List[Tuple[str, re.Pattern[str]]]:
    out: List[Tuple[str, re.Pattern[str]]] = []
    for label, pattern, ignore_case in SCRUB_PATTERNS:
        if dest and label == "internal ticket reference":
            pattern = TICKET_DEST
        flags = re.IGNORECASE if ignore_case else 0
        out.append((label, re.compile(pattern, flags)))
    return out


def iter_files(roots: Sequence[Path], suffixes: Sequence[str]) -> Iterable[Path]:
    suffix_set = {s.lower() for s in suffixes}
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in suffix_set or not suffix_set:
                yield root
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name == ".DS_Store":
                continue
            if suffix_set and path.suffix.lower() not in suffix_set:
                continue
            yield path


def scan_paths(
    roots: Sequence[Path],
    *,
    suffixes: Sequence[str] = DEFAULT_SUFFIXES,
    dest: bool = False,
) -> List[Tuple[str, Path, int, str]]:
    """Return hits as (label, path, line_no, line_text), minus allowlisted rows."""
    compiled = _compiled(dest=dest)
    hits: List[Tuple[str, Path, int, str]] = []
    for path in iter_files(roots, suffixes):
        if _skip_path(path, dest=dest):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            hits.append((f"read error: {exc}", path, 0, ""))
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for label, cre in compiled:
                if cre.search(line):
                    hits.append((label, path, i, line.rstrip()))
                    break  # one label per line is enough
    return filter_allowed(hits)


def format_hits(
    hits: Sequence[Tuple[str, Path, int, str]],
    *,
    root: Path | None = None,
    limit: int = 40,
) -> str:
    lines: List[str] = []
    for label, path, lineno, text in hits[:limit]:
        try:
            display = path.relative_to(root) if root else path
        except ValueError:
            display = path
        lines.append(f"SCRUB FAILURE: {label}: {display}:{lineno}: {text}")
    if len(hits) > limit:
        lines.append(f"... and {len(hits) - limit} more")
    return "\n".join(lines)


def run_self_test() -> int:
    """Seed one violation per pattern class; expect each to be detected."""
    samples = (
        ("personal path/handle", "see /Users/someone/secret"),
        ("internal ticket reference", "fixed in pc-991"),
        ("internal host/alias", "uses launchd for always-on"),
        ("internal governance term (founder)", "ask the founder"),
        ("sibling POS product", "leaked oneseo-pos slug"),
        ("sibling POS ticket/prefix", "see osp-123"),
        ("sibling POS customer identity", "host is Mio Mercado"),
        ("secret material", "token ghp_abcdefghijklmnopqrstuvwxyz0123456789"),
    )
    compiled = {label: cre for label, cre in _compiled()}
    failed = 0
    for label, blob in samples:
        cre = compiled[label]
        if not cre.search(blob):
            print(f"SELF-TEST FAIL: pattern {label!r} did not match {blob!r}", file=sys.stderr)
            failed = 1
        else:
            print(f"ok  self-test pattern [{label}]")
    dest_compiled = {label: cre for label, cre in _compiled(dest=True)}
    if not dest_compiled["internal ticket reference"].search("leftover wl-315 cite"):
        print("SELF-TEST FAIL: dest ticket pattern missed wl-315", file=sys.stderr)
        failed = 1
    else:
        print("ok  self-test dest ticket pattern [wl-315]")
    # End-to-end: tempfile under a fake tree must make scan_paths fail.
    with tempfile.TemporaryDirectory() as tmp:
        tdir = Path(tmp)
        bad = tdir / "seed.md"
        bad.write_text("leaked founder word\n", encoding="utf-8")
        hits = scan_paths([tdir])
        if not any(h[0].startswith("internal governance") for h in hits):
            print("SELF-TEST FAIL: scan_paths missed seeded founder", file=sys.stderr)
            failed = 1
        else:
            print("ok  self-test scan_paths seeded founder")
        pos = tdir / "pos.md"
        pos.write_text("oneseo-pos floor chip\n", encoding="utf-8")
        pos_hits = scan_paths([tdir])
        if not any("POS" in h[0] for h in pos_hits):
            print("SELF-TEST FAIL: scan_paths missed seeded POS name", file=sys.stderr)
            failed = 1
        else:
            print("ok  self-test scan_paths seeded POS name")
    if failed:
        print("check_export_scrub: SELF-TEST FAILURES", file=sys.stderr)
        return 1
    print("check_export_scrub: self-test clean")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail on internal vocabulary in export/shipped surfaces (pc-991)."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan (default: shipped source set under --repo)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repo root for default source paths (default: parent of scripts/)",
    )
    parser.add_argument(
        "--source-set",
        action="store_true",
        help="Scan DEFAULT_SOURCE_REL_PATHS under --repo (commit-time ship set)",
    )
    parser.add_argument(
        "--dest",
        action="store_true",
        help="Public-parcel mode: dest suffixes + expanded ticket prefixes; skip MCP JSON",
    )
    parser.add_argument(
        "--suffixes",
        default=None,
        help="Comma-separated suffixes to include (default: source-set or dest set)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Seed violations and assert patterns detect them; exit non-zero on miss",
    )
    parser.add_argument(
        "--list-patterns",
        action="store_true",
        help="Print pattern labels and regexes; exit 0",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_patterns:
        for label, pattern, ignore_case in SCRUB_PATTERNS:
            flag = "i" if ignore_case else ""
            print(f"{label}\t/{pattern}/{flag}")
        print(f"dest-ticket\t/{TICKET_DEST}/")
        return 0

    if args.self_test:
        return run_self_test()

    repo = args.repo
    if repo is None:
        repo = Path(__file__).resolve().parents[1]
    repo = repo.resolve()

    if args.suffixes:
        suffixes = tuple(s.strip() for s in args.suffixes.split(",") if s.strip())
    elif args.dest:
        suffixes = DEST_SUFFIXES
    else:
        suffixes = DEFAULT_SUFFIXES

    roots: List[Path] = []
    if args.dest:
        if not args.paths:
            print("check_export_scrub: --dest requires a path (the export DEST)", file=sys.stderr)
            return 2
        roots = [p if p.is_absolute() else (Path.cwd() / p) for p in args.paths]
    elif args.source_set or not args.paths:
        if args.paths and not args.source_set:
            roots = [p if p.is_absolute() else (Path.cwd() / p) for p in args.paths]
        else:
            for rel in DEFAULT_SOURCE_REL_PATHS:
                roots.append(repo / rel)
            # Allow extra paths after --source-set
            for p in args.paths:
                roots.append(p if p.is_absolute() else (Path.cwd() / p))
    else:
        roots = [p if p.is_absolute() else (Path.cwd() / p) for p in args.paths]

    roots = [r.resolve() for r in roots]
    existing = [r for r in roots if r.exists()]
    missing = [r for r in roots if not r.exists()]
    for m in missing:
        # Default source set skips optional missing files quietly.
        if (args.source_set or not args.paths) and not args.dest:
            continue
        print(f"check_export_scrub: path not found: {m}", file=sys.stderr)
        return 2

    mode = "dest" if args.dest else "export scrub"
    print(f"── {mode} ({len(existing)} path(s)) ──")
    hits = scan_paths(existing, suffixes=suffixes, dest=args.dest)
    if hits:
        print(format_hits(hits, root=repo), file=sys.stderr)
        print("SCRUB FAILURES ABOVE — fix ship copy before export/commit", file=sys.stderr)
        return 1
    print(
        "clean: no personal paths/handles, ticket refs, "
        "internal hosts, sibling POS identity, secrets, or internal governance terms"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
