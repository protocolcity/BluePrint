"""PyPI distro names for the BluePrint suite (pc-553 / ADR-004).

Import package is always ``import protocolcity``. Distribution (PyPI) names:

- **Preferred:** ``protocolcity-blueprint`` (full wheel with suite + CLI)
- **Forever-compat alias:** ``protocolcity`` (thin meta package → preferred)

Bare PyPI name ``blueprint`` is taken by unrelated software.
"""

from __future__ import annotations

import importlib.metadata
from typing import Iterable, Optional, Sequence, Tuple

# Preferred first — pip / docs teach this after dual-publish.
PREFERRED_DISTRO = "protocolcity-blueprint"
COMPAT_DISTRO = "protocolcity"
DISTRO_NAMES: Tuple[str, ...] = (PREFERRED_DISTRO, COMPAT_DISTRO)


def distro_version(
    names: Optional[Sequence[str]] = None,
    *,
    default: str = "not-installed",
) -> str:
    """Return the installed suite version from either distro name.

    Tries preferred name first, then the forever-compat alias. Returns
    ``default`` when neither distribution is installed.
    """
    for name in names or DISTRO_NAMES:
        try:
            ver = importlib.metadata.version(name)
            if ver:
                return str(ver).strip()
        except Exception:
            continue
    return default


def any_distro_installed(names: Optional[Iterable[str]] = None) -> bool:
    """True when preferred or compat distro is present in the environment."""
    return distro_version(list(names) if names is not None else None) != "not-installed"


def pip_upgrade_specs(*, with_engines: bool = True) -> list[str]:
    """pip install --upgrade targets for the suite.

    Prefer the preferred distro; also upgrade the compat alias when it is
    already installed so hosts that started on ``protocolcity`` keep pace.
    """
    extra = "[engines]" if with_engines else ""
    specs: list[str] = []
    preferred_here = distro_version([PREFERRED_DISTRO]) != "not-installed"
    compat_here = distro_version([COMPAT_DISTRO]) != "not-installed"
    if preferred_here or not compat_here:
        # Fresh / preferred install path, or both present → always upgrade preferred.
        specs.append(f"{PREFERRED_DISTRO}{extra}")
    if compat_here:
        specs.append(f"{COMPAT_DISTRO}{extra}")
    if not specs:
        specs.append(f"{PREFERRED_DISTRO}{extra}")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in specs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
