"""Workspace root discovery — shared by suite, CLI, doctor, and scripts.

Precedence (pc-956 / workspace-path-hardcode-audit-2026-08 §5.1):

1. Explicit path argument (``--root`` / caller override)
2. Environment: ``SUITE_CITY_ROOT``, ``WORKSPACE_ROOT``, ``BLUEPRINT_WORKSPACE``
3. Walk up from ``start`` (or CWD): **outermost** ancestor with ``AGENTS.md``
   (nested project AGENTS.md is not the city root)
4. Registry (``cities.json`` first durable existing city)
5. ``None`` — callers must not invent ``~/Developer`` or any host-home default

Shell counterpart: ``scripts/lib/workspace_root.sh`` (sourced by skills_sync).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union

PathLike = Union[str, Path]

# Product-facing env names (first set wins).
DEFAULT_ENV_NAMES: Sequence[str] = (
    "SUITE_CITY_ROOT",
    "WORKSPACE_ROOT",
    "BLUEPRINT_WORKSPACE",
)


def walk_up_workspace_root(start: PathLike) -> Optional[Path]:
    """Outermost ancestor of *start* that has ``AGENTS.md``.

    Project folders often carry their own AGENTS.md; suite / hire / roster live
    under the **workspace** root (``{city}/.protocolcity/workforce/…``).
    """
    cur = Path(start).expanduser()
    try:
        cur = cur.resolve()
    except OSError:
        cur = Path(start).expanduser().absolute()
    if cur.is_file():
        cur = cur.parent
    found: Optional[Path] = None
    for _ in range(48):
        if (cur / "AGENTS.md").is_file():
            found = cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return found


def _env_root(names: Sequence[str] = DEFAULT_ENV_NAMES) -> Optional[Path]:
    for name in names:
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        p = Path(raw).expanduser()
        try:
            return p.resolve()
        except OSError:
            return p.absolute()
    return None


def _registry_root() -> Optional[Path]:
    """First registered durable city path that still exists (service helper)."""
    try:
        from protocolcity.service import _pick_registry_root

        return _pick_registry_root()
    except Exception:
        pass
    try:
        from protocolcity.registry import list_cities
        from protocolcity.service import is_ephemeral_root
    except Exception:
        return None
    for row in list_cities() or []:
        if not isinstance(row, dict):
            continue
        raw = str(row.get("path") or "").strip()
        if not raw:
            continue
        p = Path(raw).expanduser()
        try:
            if not p.is_dir():
                continue
            resolved = p.resolve()
            if is_ephemeral_root(resolved):
                continue
            return resolved
        except OSError:
            continue
    return None


def resolve_workspace_root(
    explicit: Optional[PathLike] = None,
    *,
    start: Optional[PathLike] = None,
    use_registry: bool = True,
    env_names: Sequence[str] = DEFAULT_ENV_NAMES,
) -> Optional[Path]:
    """Resolve workspace (city) root or return None.

    Never falls back to a hard-coded home path such as ``~/Developer``.
    """
    if explicit is not None and str(explicit).strip():
        p = Path(str(explicit)).expanduser()
        try:
            p = p.resolve()
        except OSError:
            p = p.absolute()
        # If given a project path, prefer outermost workspace AGENTS.md
        found = walk_up_workspace_root(p)
        return found or p

    env = _env_root(env_names)
    if env is not None:
        return env

    starts: Iterable[PathLike] = ()
    if start is not None:
        starts = (start,)
    else:
        starts = (Path.cwd(),)

    for s in starts:
        found = walk_up_workspace_root(s)
        if found is not None:
            return found

    # Also try CWD when start was set but barren (e.g. Cellar package path)
    if start is not None:
        found = walk_up_workspace_root(Path.cwd())
        if found is not None:
            return found

    if use_registry:
        reg = _registry_root()
        if reg is not None:
            return reg

    return None


def resolve_workspace_root_str(
    explicit: Optional[PathLike] = None,
    *,
    start: Optional[PathLike] = None,
    use_registry: bool = True,
    fallback: Optional[PathLike] = None,
) -> str:
    """String form of :func:`resolve_workspace_root` for suite globals.

    *fallback* is used only when discovery returns None (typically ``os.getcwd()``
    or the package repo root) — never a host-home literal.
    """
    root = resolve_workspace_root(
        explicit, start=start, use_registry=use_registry
    )
    if root is not None:
        return str(root)
    if fallback is not None and str(fallback).strip():
        p = Path(str(fallback)).expanduser()
        try:
            return str(p.resolve())
        except OSError:
            return str(p.absolute())
    try:
        return str(Path.cwd().resolve())
    except OSError:
        return str(Path.cwd())
