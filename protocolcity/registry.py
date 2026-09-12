"""Known workspace registry — enables uninstall list without scanning $HOME.

Path resolution (pc-385):
1. ``$PROTOCOLCITY_CONFIG_DIR`` (always wins)
2. ``$XDG_CONFIG_HOME/protocolcity`` when set
3. Windows: ``%APPDATA%/protocolcity`` (or LOCALAPPDATA fallback)
4. Else: ``~/.config/protocolcity`` (macOS / Linux default)

Place records (pc-1056 / PLACE_MODEL.md § Registry):
Each cities.json row is a **place** with additive fields
``{slug, level, parent, managed}``. Workspace roots are the sentinel
``{slug: "__root__", level: 0, parent: null, managed: true}``.
Legacy scalar rows (path/name/added_at only) upgrade on next
``register_city`` / ``ensure_root_place`` (found or doctor --fix).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# --- Place model (pc-1056) -------------------------------------------------

ROOT_SLUG = "__root__"
PLACE_LEVEL_ROOT = 0
PLACE_LEVEL_PROJECT = 1

# Names that resolve as the workspace root place (not a project folder).
ROOT_PLACE_ALIASES = frozenset(
    {
        ROOT_SLUG,
        "root",
        "__workspace__",
        "workspace",
        "city",
    }
)


def config_dir() -> Path:
    env = (os.environ.get("PROTOCOLCITY_CONFIG_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    xdg = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg:
        return Path(xdg).expanduser().resolve() / "protocolcity"
    # Windows native config root (pc-385) — not ~/.config
    if sys.platform == "win32":
        appdata = (os.environ.get("APPDATA") or "").strip()
        if appdata:
            return Path(appdata).expanduser().resolve() / "protocolcity"
        local = (os.environ.get("LOCALAPPDATA") or "").strip()
        if local:
            return Path(local).expanduser().resolve() / "protocolcity"
    return Path.home() / ".config" / "protocolcity"


def registry_path() -> Path:
    return config_dir() / "cities.json"


def _empty() -> Dict[str, Any]:
    return {"version": 1, "cities": []}


def _load() -> Dict[str, Any]:
    path = registry_path()
    if not path.is_file():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    cities = data.get("cities")
    if not isinstance(cities, list):
        data = _empty()
    else:
        data.setdefault("version", 1)
    return data


def _save(data: Dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _norm(path: Path) -> str:
    return str(path.expanduser().resolve())


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _disk_managed(path: Path) -> bool:
    """Join marker on disk (``path/.protocolcity/managed``)."""
    try:
        return (path.expanduser().resolve() / ".protocolcity" / "managed").is_file()
    except OSError:
        return False


def normalize_place_row(
    row: Dict[str, Any],
    *,
    default_managed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Upgrade a legacy scalar cities.json row to a place record (additive).

    Workspace roots become the sentinel
    ``{slug: "__root__", level: 0, parent: null, managed: …}``.
    Existing place fields are preserved when already set.
    """
    if not isinstance(row, dict):
        return {}
    p = (row.get("path") or "").strip()
    if not p:
        return dict(row)

    out = dict(row)
    out["path"] = p
    out["name"] = row.get("name") or Path(p).name
    out["added_at"] = row.get("added_at") or ""

    # Place identity — default to root sentinel for host-registry city rows.
    slug = row.get("slug")
    if slug is None or str(slug).strip() == "":
        out["slug"] = ROOT_SLUG
    else:
        out["slug"] = str(slug).strip()

    level = row.get("level")
    if level is None:
        # Infer: root slug → 0; otherwise project (1) when parent set.
        out["level"] = (
            PLACE_LEVEL_ROOT
            if out["slug"] == ROOT_SLUG
            else PLACE_LEVEL_PROJECT
        )
    else:
        try:
            out["level"] = int(level)
        except (TypeError, ValueError):
            out["level"] = PLACE_LEVEL_ROOT

    if "parent" not in row:
        out["parent"] = None if out["level"] == PLACE_LEVEL_ROOT else ROOT_SLUG
    else:
        parent = row.get("parent")
        out["parent"] = None if parent in (None, "", "null") else str(parent)

    if "managed" in row and row.get("managed") is not None:
        out["managed"] = bool(row.get("managed"))
    elif default_managed is not None:
        out["managed"] = bool(default_managed)
    else:
        # Prefer disk marker when path exists; else True for registered roots.
        try:
            path_obj = Path(p)
            if path_obj.is_dir():
                out["managed"] = _disk_managed(path_obj)
            else:
                out["managed"] = True
        except OSError:
            out["managed"] = True

    return out


def root_place_identity(
    path: Optional[Path] = None,
    *,
    managed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Canonical root place fields for citylens / Map alignment (pc-1056).

    Does not require a registry write. *managed* defaults to disk marker when
    *path* is given, else True.
    """
    if managed is None:
        if path is not None:
            managed = _disk_managed(path) or True
        else:
            managed = True
    # Disk marker is authoritative when present; registered roots without a
    # marker still report managed once they are in cities.json (caller may
    # override). For snapshot we prefer marker OR explicit True for founded.
    if path is not None and _disk_managed(path):
        managed = True
    elif path is not None and (path.expanduser() / "AGENTS.md").is_file():
        # Pre-migration fallback: AGENTS + registry later; bare AGENTS is not
        # enough for is_managed, but snapshot identity still reports marker.
        pass
    return {
        "slug": ROOT_SLUG,
        "level": PLACE_LEVEL_ROOT,
        "parent": None,
        "managed": bool(managed),
    }


def list_cities() -> List[Dict[str, Any]]:
    """Return registry rows (path, name, added_at + place fields).

    Stale paths stay listed. Place fields are normalized in memory so readers
    always see ``slug`` / ``level`` / ``parent`` / ``managed`` without forcing
    a write (migration writes happen on register / ensure_root_place).
    """
    data = _load()
    out: List[Dict[str, Any]] = []
    for row in data.get("cities") or []:
        if not isinstance(row, dict):
            continue
        p = (row.get("path") or "").strip()
        if not p:
            continue
        out.append(normalize_place_row(row))
    return out


def place_for_path(path: Path) -> Optional[Dict[str, Any]]:
    """Return the place record for *path*, or None if not registered."""
    try:
        key = _norm(path)
    except OSError:
        return None
    for row in list_cities():
        try:
            if _norm(Path(str(row.get("path") or ""))) == key:
                return row
        except OSError:
            continue
    return None


def managed_from_registry(path: Path) -> Optional[bool]:
    """Return place-record managed flag when *path* is registered, else None."""
    row = place_for_path(path)
    if row is None:
        return None
    if "managed" not in row:
        return None
    return bool(row.get("managed"))


def register_city(
    path: Path,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    level: Optional[int] = None,
    parent: Optional[str] = None,
    managed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Idempotent: upsert by absolute path as a place record (pc-1056).

    Defaults to the root sentinel (level 0). Refuses OS temp trees (pytest /
    setup junk) so cities.json never accumulates ephemeral roots that later
    poison login-service heal (pc-832).
    """
    root = path.expanduser().resolve()
    key = _norm(root)
    now = _now()
    display = (name or root.name).strip() or root.name
    try:
        from protocolcity.service import is_ephemeral_root

        if is_ephemeral_root(root):
            entry = normalize_place_row(
                {
                    "path": key,
                    "name": display,
                    "added_at": now,
                    "slug": slug if slug is not None else ROOT_SLUG,
                    "level": level if level is not None else PLACE_LEVEL_ROOT,
                    "parent": parent,
                    "managed": True if managed is None else managed,
                }
            )
            entry["skipped"] = "ephemeral"
            return entry
    except Exception:
        pass

    data = _load()
    cities: List[Dict[str, Any]] = list(data.get("cities") or [])
    found_idx = None
    prev: Dict[str, Any] = {}
    for i, row in enumerate(cities):
        if isinstance(row, dict) and _norm(Path(str(row.get("path") or ""))) == key:
            found_idx = i
            prev = row if isinstance(row, dict) else {}
            break

    # Preserve place fields on upsert when caller omits them.
    use_slug = slug if slug is not None else prev.get("slug", ROOT_SLUG)
    use_level = level if level is not None else prev.get("level", PLACE_LEVEL_ROOT)
    if parent is not None:
        use_parent = parent
    elif "parent" in prev:
        use_parent = prev.get("parent")
    else:
        use_parent = None
    if managed is not None:
        use_managed = bool(managed)
    elif "managed" in prev:
        use_managed = bool(prev.get("managed"))
    else:
        # Registration implies a managed place; disk marker confirms.
        use_managed = True

    entry = normalize_place_row(
        {
            "path": key,
            "name": display,
            "added_at": now,
            "slug": use_slug,
            "level": use_level,
            "parent": use_parent,
            "managed": use_managed,
        },
        default_managed=use_managed,
    )
    if found_idx is not None:
        if prev.get("added_at"):
            entry["added_at"] = prev["added_at"]
        entry["name"] = display or prev.get("name") or display
        cities[found_idx] = entry
    else:
        cities.append(entry)
    data["cities"] = cities
    data["version"] = 1
    _save(data)
    return entry


def ensure_root_place(
    path: Path,
    *,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Write/upgrade the root place sentinel for a workspace (pc-1056).

    Called from ``found`` and city-wide ``doctor --fix``. Idempotent.
    """
    root = path.expanduser().resolve()
    disk = _disk_managed(root)
    return register_city(
        root,
        name=name or root.name,
        slug=ROOT_SLUG,
        level=PLACE_LEVEL_ROOT,
        parent=None,
        managed=True if disk else True,
    )


def prune_ephemeral_cities() -> Dict[str, Any]:
    """Drop temp/pytest paths from cities.json. Safe for all BluePrint hosts."""
    try:
        from protocolcity.service import is_ephemeral_root
    except Exception:
        return {"ok": False, "removed": [], "kept": 0, "error": "service import failed"}

    data = _load()
    kept: List[Dict[str, Any]] = []
    removed: List[str] = []
    for row in data.get("cities") or []:
        if not isinstance(row, dict):
            continue
        p = str(row.get("path") or "").strip()
        if not p:
            continue
        try:
            if is_ephemeral_root(Path(p)):
                removed.append(p)
                continue
        except Exception:
            pass
        kept.append(row)
    if removed:
        data["cities"] = kept
        data["version"] = 1
        _save(data)
    return {"ok": True, "removed": removed, "kept": len(kept)}


def unregister_city(path: Path) -> bool:
    """Remove path from registry. Returns True if something was removed."""
    key = _norm(path)
    data = _load()
    cities = data.get("cities") or []
    new_cities = []
    removed = False
    for row in cities:
        if not isinstance(row, dict):
            continue
        if _norm(Path(str(row.get("path") or ""))) == key:
            removed = True
            continue
        new_cities.append(row)
    if removed:
        data["cities"] = new_cities
        _save(data)
    return removed
