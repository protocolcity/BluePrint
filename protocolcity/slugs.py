"""Canonical folder→store slug normalization (pc-313 · pc-570).

One slugifier for every seam that turns a folder name into a desk/product
slug: found/adopt (store creation), the CLI Map slug, and citylens' census
probes. Before this module each site invented its own rule — adopt/found
hyphenated spaces while citylens preserved them, so a folder named
``SE Local HC`` created store ``se-local-hc`` but was probed as
``se local hc`` and never joined.

citylens.py (packaged and tools/ copies) runs as a standalone script and
cannot import this package — it carries a local ``_slugify`` with this exact
implementation. Change one, change both (the doc-audit patrol checks drift).

``resolve_neighborhood`` (pc-570) is the path twin: doctor/adopt must find
the on-disk folder even when the basename has trailing spaces or the CLI
arg is the display form (``Work Folder``) while the store is ``work-folder``.

``resolve_place`` (pc-1056) is the place-level twin: root sentinel names
(``__root__`` / aliases) resolve to the workspace root as level 0; project
names still resolve via ``resolve_neighborhood``. Root is a place, not a
project — adopt refuses it after resolution.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from protocolcity.registry import (
    PLACE_LEVEL_PROJECT,
    PLACE_LEVEL_ROOT,
    ROOT_PLACE_ALIASES,
    ROOT_SLUG,
)


def slugify(name: str) -> str:
    """Folder name or basename → canonical store slug.

    Lowercase; whitespace runs collapse to a single hyphen. Idempotent on
    already-canonical slugs (``se-local-hc`` → ``se-local-hc``).
    """
    return "-".join(str(name).strip().lower().split())


def desk_slug(name: str) -> str:
    """Folder name → letter-leading desk/store slug (pc-641).

    Strips numeric dot-notation prefixes (e.g. ``2.0 ``, ``1.0 ``) so
    WorkLane store slugs always start with a letter.  Falls back to
    ``slugify(name)`` when stripping leaves nothing (purely numeric names
    remain as-is; WorkLane will still reject them — we do not invent slugs).

    Examples::

        desk_slug("2.0 Finances")   # → "finances"
        desk_slug("1.0 Corporate")  # → "corporate"
        desk_slug("3.0 Operations") # → "operations"
        desk_slug("SE Local HC")    # → "se-local-hc"   (unchanged)
        desk_slug("Finances")       # → "finances"       (unchanged)

    Must stay consistent with protocolcity/citylens.py:_desk_slug — that
    module carries its own copy because it runs as a standalone script.
    """
    stripped = re.sub(r"^[\d.]+\s*", "", str(name).strip())
    result = slugify(stripped).lstrip("-") if stripped else ""
    return result if result else slugify(name)


def is_root_place_name(name: str) -> bool:
    """True when *name* denotes the workspace root place (not a project)."""
    raw = (name or "").strip().strip("/").replace("\\", "/")
    if not raw:
        return False
    if raw in ROOT_PLACE_ALIASES:
        return True
    # Case-insensitive match for common aliases
    return raw.lower() in {a.lower() for a in ROOT_PLACE_ALIASES}


def resolve_neighborhood(
    city_root: Union[str, Path], name: str
) -> Optional[Path]:
    """Resolve a top-level **project** folder under *city_root*.

    Order:
      1. Exact ``city_root / name`` when that path is a directory.
      2. Any top-level child whose ``slugify(child.name) == slugify(name)``
         (covers spaced names, trailing/leading whitespace on disk, and
         CLI args that were strip()'d while Finder left a trailing space).

    Returns None when nothing matches. Never walks nested paths.
    Root place names (``__root__`` etc.) intentionally return None — use
    :func:`resolve_place` when the root may be addressed as a place.
    """
    if is_root_place_name(name):
        return None
    root = Path(city_root).expanduser()
    raw = (name or "").strip().strip("/").replace("\\", "/")
    if not raw or "/" in raw or raw in (".", "..") or raw.startswith("."):
        return None
    if not root.is_dir():
        return None

    exact = root / raw
    try:
        if exact.is_dir():
            return exact.resolve()
    except OSError:
        pass

    want = slugify(raw)
    if not want:
        return None
    try:
        for child in root.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            if slugify(child.name) == want:
                return child.resolve()
    except OSError:
        return None
    return None


def resolve_place(
    city_root: Union[str, Path], name: str
) -> Optional[Dict[str, Any]]:
    """Resolve a place under *city_root* — root (level 0) or project (level 1).

    Returns a dict::

        {
          "path": Path,
          "slug": str,
          "level": int,
          "parent": str | None,
        }

    or None when nothing matches. Root sentinel names resolve to *city_root*
    itself. Project names use :func:`resolve_neighborhood`.
    """
    root = Path(city_root).expanduser()
    try:
        root = root.resolve()
    except OSError:
        root = root.absolute()
    if not root.is_dir():
        return None

    raw = (name or "").strip().strip("/").replace("\\", "/")
    if is_root_place_name(raw):
        return {
            "path": root,
            "slug": ROOT_SLUG,
            "level": PLACE_LEVEL_ROOT,
            "parent": None,
        }

    cab = resolve_neighborhood(root, raw)
    if cab is None:
        return None
    return {
        "path": cab,
        "slug": desk_slug(cab.name),
        "level": PLACE_LEVEL_PROJECT,
        "parent": ROOT_SLUG,
    }
