#!/usr/bin/env python3
"""For You inbox report policy — keys, thin/disk-only, dual-audience body.

Extracted seam from ``report_to_for_you.py`` (one job). Callers keep using
the CLI script; it imports and re-exports these names.

No Desk I/O. No scan-slot catalog. No rewrite.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _slug_key(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:48] or "report"


def _read_glance(path: Path, max_lines: int = 24, max_chars: int = 1200) -> str:
    if not path.is_file():
        return "_Report file not found yet — open path when available._\n"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return "_Could not read report: %s_\n" % e
    lines = text.splitlines()
    # skip pure front-matter fences
    body_lines: List[str] = []
    for line in lines[: max_lines + 20]:
        if line.strip() in ("---",) and not body_lines:
            continue
        body_lines.append(line)
        if len(body_lines) >= max_lines:
            break
    chunk = "\n".join(body_lines).strip()
    if len(chunk) > max_chars:
        chunk = chunk[: max_chars - 1] + "…"
    return chunk + ("\n" if chunk else "")

# Product display + matrix hints (FOR_YOU_INBOX_REPORTS §Dual-audience)
_PRODUCT_DISPLAY = {
    "trading": "Trading",
    "protocolcity": "protocolcity",
    "worklane": "worklane",
    "workforce": "workforce",
    "register": "register",
    "connector": "connector",
    "gridfinity": "gridfinity",
    "socials": "socials",
}

# Keys that always gold when present (never thin-skip on --scan).
# Trading product gold is ``desk-brief`` only ; RSU folds in.
_ALWAYS_GOLD_KEYS = frozenset(
    {
        "desk-brief",
        "maru-desk-brief",  # legacy alias → canonical desk-brief
        "workspace-digest",
        "correspondent-rollup",
        "workspace-thin-rollup",
    }
)

# Secondary product paths that must not mint their own gold (fold into primary).
_FOLDED_INTO_DESK_KEYS = frozenset({"rsu-window"})

# Canonical product gold key + aliases that share one inbox-report label day.
_DESK_BRIEF_ALIASES = ("desk-brief", "maru-desk-brief")

_DUAL_HEADING = re.compile(
    r"^(#{2,3})\s+(Builder|User)\b[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)
_H2_HEADING = re.compile(r"^##\s+\S", re.MULTILINE)


def product_display_name(project: str) -> str:
    return _PRODUCT_DISPLAY.get(_slug_key(project), project)


def extract_dual_sections(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Pull Builder / User bodies from report markdown .

    Accepts ``## Builder`` / ``## User`` or ``### Builder`` / ``### User``
    in either order. Prefer the higher-level (fewer ``#``) marker when both
    exist for the same name. Body ends at the next ``##`` heading or the
    other dual marker.
    """
    if not text:
        return None, None
    matches = list(_DUAL_HEADING.finditer(text))
    if not matches:
        return None, None

    # Prefer ## over ### for the same audience name
    by_name: Dict[str, Tuple[int, Any]] = {}
    for m in matches:
        name = m.group(2).lower()
        level = len(m.group(1))
        prev = by_name.get(name)
        if prev is None or level < prev[0]:
            by_name[name] = (level, m)

    out: Dict[str, str] = {}
    for name, (_level, m) in by_name.items():
        start = m.end()
        ends: List[int] = []
        for _oname, (_ol, om) in by_name.items():
            if om.start() > m.start():
                ends.append(om.start())
        for hm in _H2_HEADING.finditer(text, start):
            if hm.start() == m.start():
                continue
            ends.append(hm.start())
            break
        end = min(ends) if ends else len(text)
        body = text[start:end].strip()
        body = re.sub(r"^---\s*", "", body).strip()
        out[name] = body

    return out.get("builder"), out.get("user")


def _trim_section(s: str, max_chars: int = 900) -> str:
    s = (s or "").strip()
    if len(s) > max_chars:
        s = s[: max_chars - 1] + "…"
    return s + ("\n" if s else "")


def format_dual_description(
    *,
    project: str,
    day: str,
    key: str,
    rel: str,
    report_path: Path,
    visual_line: str = "",
    max_section_chars: int = 900,
) -> str:
    """Card body: product header + ### Builder + ### User + Report path.

    Matches FOR_YOU_INBOX_REPORTS §Report-body structure .
    Parses dual sections from the report when present; otherwise synthesizes
    both lenses from a short glance (generators still catching up).
    """
    text = ""
    if report_path.is_file():
        try:
            text = report_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""

    builder, user = extract_dual_sections(text)
    if builder is None and user is None:
        glance = _read_glance(report_path, max_lines=18, max_chars=700)
        missing = (
            "_Report has no dual headings yet "
            "(add ``## Builder`` / ``## User``). Auto glance:_\n\n"
        )
        builder = missing + glance
        user = missing + glance
    else:
        if not builder:
            builder = "_No Builder section in report — open full path._\n"
        if not user:
            user = "_No User section in report — open full path._\n"

    return (
        "## %s — %s\n\n"
        "### Builder\n\n"
        "%s\n"
        "### User\n\n"
        "%s\n"
        "**Report:** `%s`\n"
        "%s"
        "**Date:** %s · **Key:** `%s`\n"
        % (
            product_display_name(project),
            day,
            _trim_section(builder, max_section_chars),
            _trim_section(user, max_section_chars),
            rel,
            visual_line,
            day,
            key,
        )
    )


def is_always_gold_key(key: str) -> bool:
    return _slug_key(key) in _ALWAYS_GOLD_KEYS


def canonical_report_key(key: str) -> str:
    """Map legacy / secondary keys to the stable drop key ."""
    k = _slug_key(key)
    if k in _DESK_BRIEF_ALIASES:
        return "desk-brief"
    if k in _FOLDED_INTO_DESK_KEYS:
        return "desk-brief"
    return k


def is_folded_into_desk_key(key: str) -> bool:
    """True when this key must not mint a separate gold ."""
    return _slug_key(key) in _FOLDED_INTO_DESK_KEYS


def is_thin_report(
    path: Path,
    key: str,
    *,
    min_chars: int = 400,
) -> bool:
    """True when a product report is too thin for its own gold .

    Always-gold keys (maru, digest, …) never thin.
    Disk-only efficiency keys are handled separately — not via thin_rollup.
    Thin = short file, or ops-only (no User section) under a soft size cap.
    """
    if is_always_gold_key(key):
        return False
    if is_disk_only_scan_key(key):
        return False
    if not path.is_file():
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    stripped = text.strip()
    if len(stripped) < min_chars:
        return True
    builder, user = extract_dual_sections(text)
    if user and builder and (len(user) + len(builder)) >= (min_chars // 2):
        return False
    # All-ops / missing User with moderate size → roll into workspace card
    if not user and len(stripped) < (min_chars * 3):
        return True
    return False


def is_disk_only_efficiency_key(key: str) -> bool:
    """True when this report key must not mint routine For You gold .

    All efficiency keys stay on disk unless ``--act-now`` .
    Includes workspace ``workspace-efficiency`` — reports remain on disk for
    on-demand read; they do not gold For You daily.
    """
    k = _slug_key(key)
    if k in (
        "efficiency-pass",
        "suite-efficiency",
        "workspace-efficiency",
        "code-efficiency",
    ):
        return True
    if k.startswith("efficiency-"):
        return True
    if k.startswith("code-efficiency"):
        return True
    return False


def is_disk_only_scan_key(key: str) -> bool:
    """Scan keys that must not gold by default (efficiency + board-validation)."""
    k = _slug_key(key)
    if k == "board-validation":
        return True
    return is_disk_only_efficiency_key(k)
