"""Resolve citylens / Office package paths across install layouts.

Drawer pointer law (Charter §3) lives in citylens paper/drawer discovery —
those flags read the *city* filesystem, not the Office package path. This
module only keeps *serve* findable when Office moves with citylens:

  - package owner (pc-573): ``protocolcity/citylens.py`` + sibling ``office/``
  - host-debug shim:        ``<repo>/tools/citylens.py`` (re-exports package)
  - override:               ``PROTOCOLCITY_CITYLENS=/abs/path/citylens.py``

Office static assets resolve via ``protocolcity.citylens`` lumber dir (package
``office/`` or editable ``tools/office/``). Prefer the package path so CLI
``_load_citylens`` does not depend on the tools shim.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent


def citylens_candidates() -> List[Path]:
    """Ordered search paths for citylens.py (first existing wins)."""
    out: List[Path] = []
    env = (os.environ.get("PROTOCOLCITY_CITYLENS") or "").strip()
    if env:
        out.append(Path(env).expanduser())
    out.extend(
        [
            _PKG_DIR / "citylens.py",  # single owner (pc-573)
            _REPO_ROOT / "tools" / "citylens.py",  # thin shim / host debug
            _PKG_DIR / "tools" / "citylens.py",
        ]
    )
    # de-dupe while preserving order
    seen = set()
    unique: List[Path] = []
    for p in out:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def resolve_citylens() -> Path:
    """Return the first existing citylens path, or the preferred default.

    Callers should check ``.is_file()`` and raise a clear error when missing.
    """
    for cand in citylens_candidates():
        if cand.is_file():
            return cand
    # Preferred default for error messages (package owner, pc-573).
    return _PKG_DIR / "citylens.py"


def office_dir_beside(citylens: Path) -> Path:
    """Office package directory that must travel with citylens on a path move."""
    return citylens.resolve().parent / "office"
