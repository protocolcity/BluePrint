"""Doctor — diagnose + fix ProtocolCity papers (neighborhood / city).

Like a fixer helper: report what's missing, then optionally plant only the
missing BluePrint stubs. Never silent-rewrites existing law (paperwork
disposition law / pc-117) unless ``force=True``. Missing L0 kits (vendor
pointers, MCP registry, secrets/policy shelves) plant under ``--fix`` alone
— ``--force`` is not required for first plant (pc-1162 / GH #22).

Scopes:
  - city root (L0): AGENTS, PERIMETER, FIRST_RUN card
  - neighborhood (L1): AGENTS, workers/<id> stubs, optional desk join
  - vendor pointers (CLAUDE.md / GROK.md): found plants thin ``@AGENTS.md``
    (pc-1063); missing is weak (fixable); present-but-diverged is conflict
  - operational: UNROUTED-READY (pc-510) when ready work lacks ``worker:*``
    while hired hands exist for that store (same definition as suite routing)
  - manual-step surfaces (pc-960): UNREGISTERED-IDENTITY (§5.2 row missing for
    active roster lanes), RETIRED-SEAT (open tickets on retired/unknown
    ``worker:*``), SKILL-BRIDGE-DRIFT (``skills_sync.sh --check``)
  - suite Cellar drift (pc-1105): SUITE-SYNC-DRIFT when
    ``scripts/suite_sync_ui.sh --check`` exits non-zero (live brew suite ≠ repo);
    skip with a note when Cellar + LaunchAgent plist are both absent
  - open-work board health (pc-963 / ALWAYS_WORK §9): ``open_work_audit`` with
    feeds + history — You-starve with hired lanes is a hard conflict; suite
    offline is a weak note (not exit-1)
  - vendor/MCP configs (pc-966 / audit Class D): missing workspace ``.mcp.json``
    or abs paths outside the current workspace root — ``doctor --fix`` plants
    and rewrites (same file classes as relocate-root)
  - MCP registry SoT (pc-1078 / design pc-1055): ``MCP-REGISTRY-MISSING`` when
    ``.agents/mcp/`` is absent; ``MCP-MIRROR-DRIFT`` when generated ``.mcp.json``
    does not match the registry (``bash scripts/mcp_sync.sh``);
    ``MCP-COMMAND-MISSING`` when an enabled stdio ``command`` is not an
    existing file and is not on PATH (pc-1425 / GH #33). ``doctor --fix``
    rewrites a dead WorkLane sibling-checkout plant to the bottle
    entrypoint. Cursor ``mcp_auth`` on that error is not an OAuth grant.
  - vendor-agnostic shelves (pc-1063): policy SoT + drift, secrets inventory
    shelf, thin pointers; ``--fix`` plants missing kits + regenerates mirrors
  - retired CLI vocab (pc-1361 / GH #32): ``STALE-RETIRED-CLI`` when planted
    ``AGENTS.md`` / seeded efficiency skill / job prompt still teach
    ``tk create``, ``tk ready``, or ``MCP/`tk``` as a live capture path;
    ``--fix`` heals those known phrases only (never a full AGENTS rewrite;
    ``Never tk`` is current law)

``--fix`` on a neighborhood delegates to ``adopt_neighborhood`` (same path Office Manage uses).
City-root ``--fix`` only plants *missing* companion files when L0 AGENTS already
exists — it will not invent a new workspace (use ``blueprint found`` for that).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from protocolcity.adopt import (
    adopt_neighborhood,
    has_instructions,
    is_managed,
    stamp_managed,
)

# Alias for callers still importing adopt_cabinet from this module
adopt_cabinet = adopt_neighborhood
from protocolcity.desk import (
    DEFAULT_DESK,
    _neighborhood_for_slug,
    bootstrap_desk,
    desk_reachable,
    read_desk_join,
    write_desk_join,
)
from protocolcity.slugs import desk_slug, resolve_neighborhood, slugify
from protocolcity.found import _blank_placeholders, _strip_html_comments, _template
from protocolcity.open_work_audit import DEFAULT_TIMEOUT as _OW_TIMEOUT
from protocolcity.open_work_audit import run_audit as _run_open_work_audit

_OPEN_WORK_SCENE_URLS = (
    "http://127.0.0.1:8801/api/tp-scene",
    "http://127.0.0.1:8799/api/scene",
)


def _fetch_open_work_scene(
    urls: Optional[List[str]] = None, timeout: float = 3.0
) -> Optional[Dict[str, Any]]:
    """Try scene URLs in order; return parsed JSON or None if nothing is reachable."""
    for url in (urls or list(_OPEN_WORK_SCENE_URLS)):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data and (data.get("stores") is not None or data.get("ok") is not False):
                return data
        except Exception:
            continue
    return None


def build_open_work_summary(scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute open/ready/in_motion counts from a scene payload.

    Returns ``{"ok": False, "reachable": False, "projects": []}`` when scene
    is None (suite/WL offline) so callers can branch on ``reachable``.
    Kept for back-compat; prefer ``run_open_work_for_doctor`` (pc-963).
    """
    if scene is None:
        return {"ok": False, "reachable": False, "projects": []}
    stores = scene.get("stores") or []
    rows: List[Dict[str, Any]] = []
    total_open = 0
    total_ready = 0
    total_ip = 0
    for s in stores:
        if not isinstance(s, dict):
            continue
        slug = str(s.get("slug") or s.get("product") or "?")
        bl = int(s.get("backlog") or 0)
        ip = int(s.get("in_progress") or 0)
        ir = int(s.get("in_review") or 0)
        ready = int(s.get("ready") or 0)
        open_n = bl + ip + ir
        total_open += open_n
        total_ready += ready
        total_ip += ip + ir
        rows.append(
            {
                "project": slug,
                "open": open_n,
                "backlog": bl,
                "in_progress": ip,
                "in_review": ir,
                "ready": ready,
            }
        )
    rows.sort(key=lambda r: (-int(r["open"]), str(r["project"])))
    return {
        "ok": True,
        "reachable": True,
        "total_open": total_open,
        "total_ready": total_ready,
        "total_in_motion": total_ip,
        "projects": rows,
    }


def run_open_work_for_doctor(
    city_root: Optional[Path] = None,
    *,
    timeout: float = _OW_TIMEOUT,
    history_limit: int = 40,
) -> Dict[str, Any]:
    """Full open-work audit for doctor: counts + feeds + history (no process).

    Time-boxed. Offline engines return reachable=False (informational).
    """
    return _run_open_work_audit(
        feeds=True,
        history=True,
        process=False,
        city_root=city_root,
        timeout=timeout,
        history_limit=history_limit,
    )


def diagnose_open_work_health(
    open_work: Dict[str, Any], city_root: Path
) -> List[Finding]:
    """Turn open_work_audit into doctor findings (pc-963).

    Hard (conflict → exit 1):
      - YOU-STARVE-READY when bare worker:you ready exists on a store with
        hired lanes (starve with a drain path available)
      - INVALID-FEED when process audit reports shape/probe issues (optional)

    Soft (weak, no exit 1):
      - OPEN-WORK-OFFLINE when suite/WL unreachable
      - YOU-STARVE-HISTORY informational when history shows past starve/host
    """
    findings: List[Finding] = []
    if not open_work.get("reachable", True) or (
        open_work.get("ok") is False and not open_work.get("feeds")
    ):
        findings.append(
            _finding(
                level="ops",
                code="OPEN-WORK-OFFLINE",
                path=str(city_root),
                status="weak",
                detail=(
                    "Open-work audit skipped — suite/WorkLane offline "
                    "(start with: blueprint serve). Board counts/feeds not checked."
                ),
                fixable=False,
            )
        )
        return findings

    workers = _load_roster_workers(city_root)
    hired = set(_lane_hands_by_product(workers).keys())

    feeds = open_work.get("feeds") or {}
    starve_rows = feeds.get("you_starve") or []
    # Group starve tickets by product that has hired lanes
    hard_starve: List[Dict[str, Any]] = []
    soft_starve: List[Dict[str, Any]] = []
    for row in starve_rows:
        if not isinstance(row, dict):
            continue
        prod = str(row.get("product") or "").strip().lower()
        if prod and prod in hired:
            hard_starve.append(row)
        else:
            soft_starve.append(row)

    if hard_starve:
        ids = ", ".join(
            str(r.get("id") or "?") for r in hard_starve[:8]
        )
        more = " …" if len(hard_starve) > 8 else ""
        findings.append(
            _finding(
                level="ops",
                code="YOU-STARVE-READY",
                path=str(city_root),
                status="conflict",
                detail=(
                    "You-starve ready on store(s) with hired lanes: %d ticket(s) "
                    "parked on bare worker:you (wl-315). Re-seat to a hand or "
                    "add you:note|todo|remind|host / founder gate. Samples: %s%s"
                    % (len(hard_starve), ids, more)
                ),
                fixable=False,
            )
        )
    elif soft_starve:
        findings.append(
            _finding(
                level="ops",
                code="YOU-STARVE-READY",
                path=str(city_root),
                status="weak",
                detail=(
                    "You-starve ready on store(s) without hired lanes: %d ticket(s). "
                    "Hire a hand or re-label — not a hard doctor fail until a seat exists."
                    % len(soft_starve)
                ),
                fixable=False,
            )
        )

    process = open_work.get("process") or {}
    issue_n = int(process.get("issue_lane_n") or 0)
    if issue_n > 0:
        sample_findings: List[str] = []
        for lane in process.get("lanes") or []:
            for f in lane.get("findings") or []:
                sample_findings.append(
                    "%s: %s" % (lane.get("worker") or "?", f)
                )
                if len(sample_findings) >= 4:
                    break
            if len(sample_findings) >= 4:
                break
        findings.append(
            _finding(
                level="ops",
                code="INVALID-FEED",
                path=str(city_root),
                status="conflict",
                detail=(
                    "Lane feed shape/probe issues: %d lane(s). %s"
                    % (issue_n, "; ".join(sample_findings) or process.get("error") or "")
                ),
                fixable=False,
            )
        )

    # Informational history: open starve/host dumps (not exit-1 by themselves)
    hist = open_work.get("history") or {}
    by_class = hist.get("by_class") or {}
    open_starve = int(by_class.get("starve") or 0) + int(by_class.get("host") or 0)
    if open_starve and not hard_starve:
        findings.append(
            _finding(
                level="ops",
                code="YOU-STARVE-HISTORY",
                path=str(city_root),
                status="weak",
                detail=(
                    "History worker:you mixups (starve/host): n=%d  classes=%s — "
                    "re-seat implement work off You (ALWAYS_WORK / wl-315)."
                    % (open_starve, by_class)
                ),
                fixable=False,
            )
        )
    elif open_work.get("feeds") is not None and not hard_starve and not soft_starve:
        findings.append(
            _finding(
                level="ops",
                code="OPEN-WORK-OK",
                path=str(city_root),
                status="ok",
                detail=(
                    "Open work healthy: open=%s ready=%s in_motion=%s; "
                    "no You-starve ready on hired stores"
                    % (
                        open_work.get("total_open", 0),
                        open_work.get("total_ready", 0),
                        open_work.get("total_in_motion", 0),
                    )
                ),
                fixable=False,
            )
        )
    return findings


# Soft name heuristics — doctor must not offer Adopt on these.
def _desk_store_slugs(desk_url: str = DEFAULT_DESK) -> Optional[set]:
    """Store slugs the desk serves; ``None`` when the desk is unreachable (pc-314)."""
    try:
        with urllib.request.urlopen(desk_url + "/api/scene", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    stores = data.get("stores")
    if not isinstance(stores, list):
        return None
    out = set()
    for s in stores:
        slug = (
            (s.get("slug") or s.get("product") or s.get("name"))
            if isinstance(s, dict)
            else s
        )
        if slug:
            out.add(str(slug).strip().lower())
    return out


def _desk_store_map(desk_url: str = DEFAULT_DESK):
    """slug -> {slug, display, prefix} from /api/scene; None if unreachable."""
    try:
        with urllib.request.urlopen(desk_url + "/api/scene", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    stores = data.get("stores")
    if not isinstance(stores, list):
        return None
    out = {}
    for s in stores:
        if not isinstance(s, dict):
            continue
        slug = str(s.get("slug") or s.get("product") or s.get("name") or "").strip().lower()
        if not slug:
            continue
        out[slug] = {
            "slug": slug,
            "display": s.get("display") or slug,
            "prefix": str(s.get("prefix") or "").strip(),
        }
    return out


def _likely_non_adoptable(name: str) -> bool:
    n = name.lower()
    if n.endswith("-blueprint") or n.endswith("-worklane"):
        return True
    if n.endswith("-backups") or n.endswith("-backup"):
        return True
    if any(tok in n for tok in ("backup", "archive", "export")):
        return True
    # city-internal runtime dir — reserved, never a managed neighborhood (pc-1238)
    if n == "local":
        return True
    # known foreign clones in this city (soft — still report, not fixable)
    if n in ("quantmuse", "worldmonitor"):
        return True
    return False


def _folder_zone(path: Path) -> str:
    """Git-origin / name zone (staffing-blind). Empty on failure."""
    try:
        from protocolcity.adopt import _cabinet_zone

        return str(_cabinet_zone(Path(path)) or "").lower()
    except Exception:
        return ""


def _git_origin_owner(path: Path) -> str:
    """GitHub-style origin owner, or empty when no git / no origin."""
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return ""
        url = (out.stdout or "").strip()
        m = re.search(r"github\.com[:/]([^/]+)/", url)
        return m.group(1) if m else ""
    except Exception:
        return ""


def _is_foreign_consumer_folder(path: Path) -> bool:
    """Unmanaged upstream clone, or explicit consumer marker (pc-1359)."""
    try:
        from protocolcity.adopt import is_foreign_consumer

        if is_foreign_consumer(path):
            return True
    except Exception:
        pass
    return _folder_zone(path) == "foreign"


def _foreign_consumer_finding(child: Path) -> Finding:
    owner = _git_origin_owner(child)
    origin_bit = (" origin: %s" % owner) if owner else ""
    return _finding(
        level="L1",
        code="FOREIGN-CONSUMER",
        path=str(child),
        status="ok",
        detail=(
            "%s upstream-owned · automations on · adopt optional%s. "
            "Code work → upstream issues; ops → desk tickets. "
            "Desk join: Map Join desk (--force) or "
            "`blueprint adopt %s --force` (coordination only; origin stays foreign)."
            % (child.name, origin_bit, child.name)
        ),
        fixable=False,
    )


Finding = Dict[str, Any]


def _finding(
    *,
    level: str,
    code: str,
    path: str,
    status: str,
    detail: str,
    fixable: bool = False,
) -> Finding:
    return {
        "level": level,
        "code": code,
        "path": path,
        "status": status,  # ok | missing | weak | conflict
        "detail": detail,
        "fixable": fixable,
    }


def _pointer_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.is_symlink():
        try:
            return Path(os_readlink(path)).name == "AGENTS.md"  # type: ignore[name-defined]
        except OSError:
            return False
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return text in ("@AGENTS.md", "@./AGENTS.md")


def os_readlink(path: Path) -> str:
    import os

    return os.readlink(path)


def _findings_law_and_managed(
    folder: Path,
    *,
    level: str,
    missing_code: str,
    ok_code: str,
    unmanaged_code: str,
    missing_detail: str,
    ok_detail: str,
    unmanaged_detail: str,
    missing_fixable: bool,
    unmanaged_fixable: bool = True,
) -> List[Finding]:
    """Shared AGENTS present + BluePrint managed-marker check (pc-1041).

    Managed-ness is the join marker (``is_managed``), never AGENTS.md alone.
    Level-specific codes/details stay with the caller.
    """
    agents = folder / "AGENTS.md"
    if not agents.is_file():
        return [
            _finding(
                level=level,
                code=missing_code,
                path=str(agents),
                status="missing",
                detail=missing_detail,
                fixable=missing_fixable,
            )
        ]
    if is_managed(folder):
        return [
            _finding(
                level=level,
                code=ok_code,
                path=str(agents),
                status="ok",
                detail=ok_detail,
            )
        ]
    return [
        _finding(
            level=level,
            code=unmanaged_code,
            path=str(agents),
            status="warn",
            detail=unmanaged_detail,
            fixable=unmanaged_fixable,
        )
    ]


def _findings_vendor_pointers(
    folder: Path,
    *,
    agents: Path,
    level: str,
    diverged_detail_fmt: str,
    require_city_defaults: bool = False,
) -> List[Finding]:
    """One vendor-pointer check path for city + neighborhood diagnose (pc-1041).

    Present-but-diverged is conflict (not auto-fixed). Missing is silent for
    neighborhoods; at city L0 with ``require_city_defaults`` (pc-1063) missing
    thin pointers are weak + fixable (``doctor --fix`` plants ``@AGENTS.md``).
    """
    out: List[Finding] = []
    for ptr in ("CLAUDE.md", "GROK.md"):
        p = folder / ptr
        if not p.exists():
            if require_city_defaults and level == "L0":
                out.append(
                    _finding(
                        level=level,
                        code="MISSING-VENDOR-POINTER",
                        path=str(p),
                        status="weak",
                        detail=(
                            "%s missing — plant thin @AGENTS.md pointer "
                            "(pc-1063; `doctor --fix` or re-found)"
                            % ptr
                        ),
                        fixable=True,
                    )
                )
            continue
        if agents.is_file() and not _pointer_ok(p):
            out.append(
                _finding(
                    level=level,
                    code="DIVERGED-POINTER",
                    path=str(p),
                    status="conflict",
                    detail=diverged_detail_fmt % ptr,
                    fixable=False,
                )
            )
        else:
            out.append(
                _finding(
                    level=level,
                    code="VENDOR-POINTER",
                    path=str(p),
                    status="ok",
                    detail="%s ok (thin @AGENTS.md pointer)" % ptr,
                )
            )
    return out


def _markdown_table_blocks(text: str) -> List[List[str]]:
    """Split markdown into consecutive pipe-table line blocks."""
    blocks: List[List[str]] = []
    cur: List[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            cur.append(line)
            continue
        if cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def _table_cells(line: str) -> List[str]:
    """Split a markdown table row into stripped cell strings."""
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def _is_table_separator(line: str) -> bool:
    """True for GFM separator rows like ``|---|---|``."""
    cells = _table_cells(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c)


def _is_folder_registry_table(header_cells: List[str]) -> bool:
    """True when a table header includes a Folder column (project registry).

    Status legend tables (``| Status | Means … |``) and stamp/vocab tables do
    not qualify — pc-1159 / GH #19 false ORPHAN-REGISTRY-ROW on legend tokens.
    """
    for cell in header_cells:
        # strip bold/italic markers common in hand-authored headers
        label = cell.replace("*", "").replace("_", "").strip()
        if label.casefold() == "folder":
            return True
    return False


def _folder_column_index(header_cells: List[str]) -> int:
    for i, cell in enumerate(header_cells):
        label = cell.replace("*", "").replace("_", "").strip()
        if label.casefold() == "folder":
            return i
    return 0


def _name_in_projects_table(text: str, name: str) -> bool:
    """True if name is a Folder-column entry in a project registry table."""
    key = name.strip().strip("/").lower()
    if not key:
        return False
    return any(f.lower() == key for f in _projects_table_folders(text))


def _projects_table_folders(text: str) -> List[str]:
    """Basenames from Folder-column backtick entries in project registry tables.

    Scans only markdown tables whose header includes a ``Folder`` column
    (hand-authored summary and ``bp:generated:project-registry`` blocks).
    Status legend tables and other prose tables are ignored (pc-1159 / GH #19).
    Skips nested paths and duplicates.
    """
    out: List[str] = []
    seen = set()
    cell_re = re.compile(r"`([^`]+?)/?`")
    for block in _markdown_table_blocks(text):
        if len(block) < 2:
            continue
        header = _table_cells(block[0])
        if not _is_folder_registry_table(header):
            continue
        folder_idx = _folder_column_index(header)
        for row in block[1:]:
            if _is_table_separator(row):
                continue
            cells = _table_cells(row)
            if folder_idx >= len(cells):
                continue
            m = cell_re.search(cells[folder_idx])
            if not m:
                continue
            name = m.group(1).strip().strip("/")
            if not name or "/" in name or "\\" in name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(name)
    return out


def _name_in_atlas(text: str, name: str) -> bool:
    """True if a relative link to ../<name>/ appears anywhere in the ATLAS."""
    return bool(
        re.search(
            r"\.\./\b%s\b" % re.escape(name),
            text,
        )
    )


def diagnose_registry_drift(city_root: Path) -> List[Finding]:
    """pc-488 / pc-513 / pc-1097: registry ↔ disk ↔ desk store hygiene.

    Forward (managed folder missing from law tables):
      MISSING-REGISTRY-ROW, MISSING-ATLAS-ROW

    Inverse (law / desk claims a folder that is not on disk) — pc-1097 / wl-383:
      ORPHAN-REGISTRY-ROW — AGENTS.md projects table names an absent folder
      STORE-WITHOUT-FOLDER — WorkLane store slug has no workspace-root project

    Report-only — never auto-append or rewrite AGENTS.md / ATLAS.md (city law).
    """
    root = city_root.expanduser().resolve()
    out: List[Finding] = []

    managed: List[str] = []
    try:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if _likely_non_adoptable(child.name):
                continue
            if is_managed(child):
                managed.append(child.name)
    except OSError:
        return out

    city_agents = root / "AGENTS.md"
    registry_text = ""
    if city_agents.is_file():
        try:
            registry_text = city_agents.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    atlas_path = root / "ProtocolCity" / "ATLAS.md"
    atlas_text = ""
    if atlas_path.is_file():
        try:
            atlas_text = atlas_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    # Forward: managed neighborhoods absent from city law tables
    for name in managed:
        if registry_text and not _name_in_projects_table(registry_text, name):
            out.append(
                _finding(
                    level="L0",
                    code="MISSING-REGISTRY-ROW",
                    path=str(city_agents),
                    status="weak",
                    detail=(
                        "%s is managed + desk-joined but has no row in the "
                        "workspace AGENTS.md projects table — hand-edit to add "
                        "`%s/` row (never auto-fixed)" % (name, name)
                    ),
                    fixable=False,
                )
            )
        if atlas_text and not _name_in_atlas(atlas_text, name):
            out.append(
                _finding(
                    level="L1",
                    code="MISSING-ATLAS-ROW",
                    path=str(atlas_path),
                    status="weak",
                    detail=(
                        "%s/AGENTS.md has no row in ProtocolCity/ATLAS.md — "
                        "upkeep rule (ratified 2026-07-14): every new "
                        "instruction/governance file gets an ATLAS row in the "
                        "same close-out. Add Tier-3 row manually." % name
                    ),
                    fixable=False,
                )
            )

    # Inverse (a): projects table names a folder that is not on disk (pc-1097)
    if registry_text:
        for name in _projects_table_folders(registry_text):
            if _likely_non_adoptable(name):
                continue
            if resolve_neighborhood(root, name) is not None:
                continue
            out.append(
                _finding(
                    level="L0",
                    code="ORPHAN-REGISTRY-ROW",
                    path=str(city_agents),
                    status="weak",
                    detail=(
                        "workspace AGENTS.md projects table lists `%s/` but no "
                        "matching project folder exists under the workspace "
                        "root — hand-edit to remove the row or restore the "
                        "folder (never auto-fixed)" % name
                    ),
                    fixable=False,
                )
            )

    # Inverse (b): desk product store with no city-root folder (pc-1097)
    stores = _desk_store_slugs()
    if stores is not None:
        for slug in sorted(stores):
            if not slug:
                continue
            if _neighborhood_for_slug(root, slug) is not None:
                continue
            out.append(
                _finding(
                    level="L0",
                    code="STORE-WITHOUT-FOLDER",
                    path=str(root),
                    status="weak",
                    detail=(
                        "WorkLane store `%s` has no workspace-root project "
                        "folder whose desk slug matches — retire the store "
                        "or restore/adopt the folder (never auto-fixed)"
                        % slug
                    ),
                    fixable=False,
                )
            )

    return out


def diagnose_city(city_root: Path) -> List[Finding]:
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    agents = root / "AGENTS.md"
    # pc-1041: law + managed-marker share one helper with diagnose_neighborhood.
    # Root managedness is the join marker found already writes — not AGENTS alone.
    out.extend(
        _findings_law_and_managed(
            root,
            level="L0",
            missing_code="MISSING-CITY-LAW",
            ok_code="CITY-LAW",
            unmanaged_code="CITY-LAW-NOT-MANAGED",
            missing_detail=(
                "No workspace AGENTS.md — run `blueprint found` on a blank root "
                "(doctor will not invent L0 here)."
            ),
            ok_detail="Workspace instructions present (BluePrint-managed join marker)",
            unmanaged_detail=(
                "Has AGENTS.md but not BluePrint-managed — re-run "
                "`blueprint found` or stamp `.protocolcity/managed` "
                "(marker is source of truth, not AGENTS existence)"
            ),
            missing_fixable=False,
            unmanaged_fixable=False,  # doctor will not invent L0 city
        )
    )
    out.extend(
        _findings_vendor_pointers(
            root,
            agents=agents,
            level="L0",
            diverged_detail_fmt=(
                "%s is not a thin @AGENTS.md pointer — disposition card "
                "(pc-117), not auto-fixed"
            ),
            require_city_defaults=True,
        )
    )

    boundaries = root / "BOUNDARIES.md"
    perimeter = root / "PERIMETER.md"
    legacy_office = root / "OFFICE_PERIMETER.md"
    legacy_edges = root / "CITY_EDGES.md"
    if boundaries.is_file():
        out.append(
            _finding(
                level="L0",
                code="BOUNDARIES",
                path=str(boundaries),
                status="ok",
                detail="Boundaries registry present (citizen L0)",
            )
        )
    elif perimeter.is_file():
        out.append(
            _finding(
                level="L0",
                code="BOUNDARIES",
                path=str(perimeter),
                status="ok",
                detail="Boundaries present via forever-alias PERIMETER.md (prefer BOUNDARIES.md)",
            )
        )
    elif legacy_office.is_file() or legacy_edges.is_file():
        path = str(legacy_office if legacy_office.is_file() else legacy_edges)
        legacy_name = "OFFICE_PERIMETER.md" if legacy_office.is_file() else "CITY_EDGES.md"
        out.append(
            _finding(
                level="L0",
                code="BOUNDARIES",
                path=path,
                status="ok",
                detail="Boundaries present (legacy %s — prefer BOUNDARIES.md)"
                % legacy_name,
            )
        )
    else:
        out.append(
            _finding(
                level="L0",
                code="MISSING-BOUNDARIES",
                path=str(boundaries),
                status="missing",
                detail="BOUNDARIES.md missing — plant empty grants registry",
                fixable=agents.is_file(),
            )
        )

    first = root / "FIRST_RUN.md"
    if not first.is_file():
        out.append(
            _finding(
                level="L0",
                code="MISSING-FIRST-RUN",
                path=str(first),
                status="weak",
                detail="FIRST_RUN.md absent (optional after founding) — not planted by doctor",
                fixable=False,
            )
        )
    else:
        try:
            first_text = first.read_text(encoding="utf-8", errors="replace")
        except OSError:
            first_text = ""
        if re.search(
            r"\bprotocolcity\s+(serve|adopt|found|stop|doctor|setup)\b", first_text
        ):
            out.append(
                _finding(
                    level="L0",
                    code="STALE-FIRST-RUN",
                    path=str(first),
                    status="weak",
                    detail=(
                        "FIRST_RUN.md references removed `protocolcity` CLI "
                        "(renamed to `blueprint` ≥0.1.26) — "
                        "fix: blueprint doctor --fix"
                    ),
                    fixable=True,
                )
            )
        else:
            out.append(
                _finding(
                    level="L0",
                    code="FIRST-RUN",
                    path=str(first),
                    status="ok",
                    detail="First-run card present",
                )
            )
    return out


def _suite_bootstrap_remediation(root: Path, plist: str) -> str:
    """Exact reload commands for a dead/unloaded suite LaunchAgent (pc-1068)."""
    try:
        uid = int(os.getuid())
    except Exception:
        uid = 501
    return (
        "blueprint service start  "
        "# exact bootstrap: launchctl bootstrap gui/%d %s  "
        "# or reinstall: blueprint upgrade --root %s"
        % (uid, plist, root)
    )


def _suite_port_listening(port: int) -> bool:
    """True when something is TCP-LISTEN on *port* (best-effort)."""
    try:
        from protocolcity.setup_flow import _pids_listening_on

        return bool(list(_pids_listening_on(int(port))))
    except Exception:
        return False


# pc-1068: suite-service.err growth (incident ~12 MiB with no doctor flag)
_SUITE_ERR_WARN_BYTES = 8 * 1024 * 1024  # 8 MiB


def diagnose_login_service(city_root: Path) -> List[Finding]:
    """pc-560 / pc-1068: suite LaunchAgent health + one-line fix.

    Report-only (not doctor --fix): installing a login agent is an opt-in
    consent choice, never silent always-on.

    pc-1068: when service.json + plist exist but the agent is unloaded (or
    loaded with :port dead), emit **conflict** with the exact ``launchctl
    bootstrap`` remediation — Map death must not be silent.
    """
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    if not (root / "AGENTS.md").is_file():
        return out
    try:
        from protocolcity import service as svc_mod
    except Exception:
        return out
    if not svc_mod.is_macos():
        # Windows always-on is a separate path (document only on setup/service).
        return out

    st = svc_mod.service_status()
    loaded = bool(st.get("loaded"))
    state = st.get("state") if isinstance(st.get("state"), dict) else {}
    state_root = str((state or {}).get("root") or "").strip()
    try:
        suite_port = int((state or {}).get("port") or 8801)
    except (TypeError, ValueError):
        suite_port = 8801
    same_root = False
    state_exists = False
    if state_root:
        try:
            sr = Path(state_root).expanduser().resolve()
            same_root = sr == root
            state_exists = sr.is_dir()
        except OSError:
            same_root = False
            state_exists = False

    plist = str(svc_mod.plist_path())
    # Stale / temp root still in LaunchAgent or service.json (pc-579 · GH #7 / pc-622)
    if state_root and not state_exists:
        # Prefer relocate-root when doctor is run against a live workspace (folder
        # rename/move): rewrites service + registry + roster + LaunchAgents +
        # skill bridges / vendor configs (pc-959). service install alone leaves
        # roster abs paths, cities.json, and skill homes stale.
        if str(root) and Path(root).is_dir() and str(root) != state_root:
            repair = (
                "blueprint relocate-root --from %s --to %s"
                % (state_root, root)
            )
        else:
            repair = (
                "blueprint relocate-root --from %s --to <new-workspace>  "
                "# or: blueprint upgrade --root <new-workspace>"
                % state_root
            )
        out.append(
            _finding(
                level="L0",
                code="SERVICE-ROOT-MISSING",
                path=plist,
                status="conflict",
                detail=(
                    "Login suite service points at a missing workspace (%s) — "
                    "after a folder rename/move run: %s"
                    % (state_root, repair)
                ),
                fixable=False,
            )
        )
        return out

    # Ephemeral root still on disk (reboot keeps /var/folders/…/T alive briefly;
    # heal must not treat "exists" as healthy — pc-832).
    if state_root and state_exists:
        try:
            if svc_mod.is_ephemeral_root(Path(state_root)):
                repair = (
                    "blueprint upgrade --root %s"
                    % root
                    if root.is_dir()
                    else "blueprint upgrade --root <workspace>"
                )
                out.append(
                    _finding(
                        level="L0",
                        code="SERVICE-EPHEMERAL-ROOT",
                        path=plist,
                        status="conflict",
                        detail=(
                            "Login suite service points at a temp path (%s) — "
                            "Map will show a junk city after reboot. Fix: %s"
                            % (state_root, repair)
                        ),
                        fixable=False,
                    )
                )
                return out
        except Exception:
            pass

    # pc-959: service.json root ≠ doctor root → rename/move without relocate.
    # Covers loaded-for-other-workspace and not-loaded-but-stale-state alike.
    if state_root and not same_root:
        repair = (
            "blueprint relocate-root --from %s --to %s"
            % (state_root, root)
            if root.is_dir()
            else "blueprint relocate-root --from %s --to <new-workspace>" % state_root
        )
        out.append(
            _finding(
                level="L0",
                code="SERVICE-OTHER-ROOT" if loaded else "SERVICE-ROOT-DRIFT",
                path=plist,
                status="weak",
                detail=(
                    "Suite service state root (%s) ≠ doctor workspace (%s) — "
                    "after a folder rename/move run: %s  "
                    "(if this is a second workspace, not a rename: "
                    "blueprint upgrade --root %s)"
                    % (state_root, root, repair, root)
                ),
                fixable=False,
            )
        )
        return out

    if loaded and (same_root or not state_root):
        # pc-1068: launchd "loaded" is not enough — Map needs :port answering.
        if not _suite_port_listening(suite_port):
            out.append(
                _finding(
                    level="L0",
                    code="SERVICE-PORT-DEAD",
                    path=plist,
                    status="conflict",
                    detail=(
                        "Suite LaunchAgent loaded (%s) but :%d is not listening — "
                        "Map is dark. Fix: %s"
                        % (
                            svc_mod.LABEL,
                            suite_port,
                            _suite_bootstrap_remediation(root, plist),
                        )
                    ),
                    fixable=False,
                )
            )
            return out
        out.append(
            _finding(
                level="L0",
                code="SERVICE-LOADED",
                path=plist,
                status="ok",
                detail=(
                    "Login suite service loaded (%s) · :%d listening"
                    % (svc_mod.LABEL, suite_port)
                ),
            )
        )
        return out

    if st.get("plist_exists") and not loaded:
        # pc-1068: plist on disk + not loaded is the silent Map-death incident.
        # Elevate to conflict when service.json also present (always-on was chosen).
        status = "conflict" if state_root else "weak"
        out.append(
            _finding(
                level="L0",
                code="SERVICE-NOT-LOADED",
                path=plist,
                status=status,
                detail=(
                    "Suite login LaunchAgent not loaded (plist present%s) — "
                    "Map will stay dark until reloaded. Fix: %s"
                    % (
                        ", service.json present" if state_root else "",
                        _suite_bootstrap_remediation(root, plist),
                    )
                ),
                fixable=False,
            )
        )
        return out

    out.append(
        _finding(
            level="L0",
            code="SERVICE-NOT-INSTALLED",
            path=plist,
            status="weak",
            detail=(
                "Suite login LaunchAgent not installed — "
                "blueprint upgrade --root %s" % root
            ),
            fixable=False,
        )
    )
    return out


def diagnose_suite_service_logs(city_root: Path) -> List[Finding]:
    """pc-1068: flag unbounded suite-service.err growth (log rotation hint)."""
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    candidates: List[Path] = [
        root / ".protocolcity" / "logs" / "suite-service.err",
    ]
    try:
        from protocolcity import service as svc_mod

        st = svc_mod.service_status()
        state = st.get("state") if isinstance(st.get("state"), dict) else {}
        sr = str((state or {}).get("root") or "").strip()
        if sr:
            candidates.insert(
                0,
                Path(sr).expanduser().resolve()
                / ".protocolcity"
                / "logs"
                / "suite-service.err",
            )
    except Exception:
        pass

    seen: set = set()
    for path in candidates:
        try:
            rp = path.expanduser().resolve()
        except OSError:
            continue
        key = str(rp)
        if key in seen:
            continue
        seen.add(key)
        if not rp.is_file():
            continue
        try:
            size = int(rp.stat().st_size)
        except OSError:
            continue
        if size < _SUITE_ERR_WARN_BYTES:
            continue
        mb = size / (1024.0 * 1024.0)
        out.append(
            _finding(
                level="L0",
                code="SUITE-SERVICE-ERR-SIZE",
                path=str(rp),
                status="weak",
                detail=(
                    "suite-service.err is %.1f MiB (warn ≥ 8 MiB) — rotate after "
                    "inspecting thrash/crash loops: "
                    "mv %s %s.1 && : > %s"
                    % (mb, rp, rp, rp)
                ),
                fixable=False,
            )
        )
    return out


def diagnose_legacy_citylens() -> List[Finding]:
    """pc-575: leftover citylens agent/process is optional cleanup, not required.

    Doctor never requires :8796. When a legacy LaunchAgent or :8796 listener
    remains, emit one-line cutover guidance (census is in suite).
    """
    out: List[Finding] = []
    try:
        from protocolcity import service as svc_mod
        from protocolcity.setup_flow import _pids_listening_on
    except Exception:
        return out

    st: Dict[str, Any] = {}
    try:
        st = svc_mod.citylens_agent_status()
    except Exception:
        st = {}
    loaded = bool(st.get("loaded"))
    plist_exists = bool(st.get("plist_exists"))
    leftover_pids: List[int] = []
    try:
        leftover_pids = list(_pids_listening_on(8796))
    except Exception:
        leftover_pids = []

    if not loaded and not plist_exists and not leftover_pids:
        return out

    detail_bits = []
    if loaded:
        detail_bits.append("LaunchAgent loaded")
    elif plist_exists:
        detail_bits.append("plist present")
    if leftover_pids:
        detail_bits.append(":%d listening (pids %s)" % (
            8796,
            ", ".join(str(p) for p in leftover_pids[:5]),
        ))
    out.append(
        _finding(
            level="L0",
            code="LEGACY-CITYLENS",
            path=str(st.get("plist") or "com.protocolcity.citylens"),
            status="weak",
            detail=(
                "bootout citylens agent — census is in suite"
                + (" (%s)" % "; ".join(detail_bits) if detail_bits else "")
                + " — blueprint stop  # or: launchctl bootout gui/$(id -u)/"
                "com.protocolcity.citylens"
            ),
            fixable=False,
        )
    )
    return out


def find_suite_sync_script(workspace: Path) -> Optional[Path]:
    """Locate suite_sync_ui.sh under workspace (parcel ProtocolCity or root scripts/)."""
    root = workspace.expanduser().resolve()
    candidates = (
        root / "ProtocolCity" / "scripts" / "suite_sync_ui.sh",
        root / "scripts" / "suite_sync_ui.sh",
        root / "protocolcity" / "scripts" / "suite_sync_ui.sh",
    )
    for c in candidates:
        if c.is_file():
            return c
    return None


def _suite_install_paths() -> tuple:
    """Resolve Cellar + LaunchAgent paths (env overrides match suite_sync_ui.sh)."""
    cellar_env = (os.environ.get("SUITE_SYNC_CELLAR") or "").strip()
    if cellar_env:
        cellar = Path(cellar_env).expanduser()
    else:
        brew_prefix = (
            (os.environ.get("HOMEBREW_PREFIX") or "").strip()
            or "/opt/homebrew"
        )
        cellar = Path(brew_prefix) / "Cellar" / "blueprint"
    plist_env = (os.environ.get("SUITE_SYNC_PLIST") or "").strip()
    if plist_env:
        plist = Path(plist_env).expanduser()
    else:
        home = Path.home()
        plist = home / "Library" / "LaunchAgents" / "com.protocolcity.suite.plist"
    return cellar, plist


def suite_install_present() -> bool:
    """True when brew Cellar and/or suite LaunchAgent look installed."""
    cellar, plist = _suite_install_paths()
    try:
        if cellar.is_dir():
            return True
    except OSError:
        pass
    try:
        if plist.is_file():
            return True
    except OSError:
        pass
    return False


def run_suite_sync_check(workspace: Path) -> Dict[str, Any]:
    """Invoke ``scripts/suite_sync_ui.sh --check`` (pc-1105).

    Returns a small dict: ok / skipped / error / returncode / stdout / stderr / script.
    ``returncode == 1`` means drift (or live≠newest skew) — informative, not a crash.
    """
    script = find_suite_sync_script(workspace)
    if script is None:
        return {
            "ok": True,
            "skipped": "suite_sync_ui.sh not found under workspace",
            "script": None,
        }
    if not suite_install_present():
        cellar, plist = _suite_install_paths()
        return {
            "ok": True,
            "skipped": "suite not installed (no Cellar at %s and no plist at %s)"
            % (cellar, plist),
            "script": str(script),
            "not_installed": True,
        }
    cmd = ["bash", str(script), "--check"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(script.parent),
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {
            "ok": False,
            "script": str(script),
            "error": str(e),
        }
    return {
        "ok": proc.returncode == 0,
        "script": str(script),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
    }


def diagnose_suite_sync_drift(city_root: Path) -> List[Finding]:
    """pc-1105: surface ``suite_sync_ui.sh --check`` drift as a FAILED chip.

    - Non-zero check → ``SUITE-SYNC-DRIFT`` conflict (doctor exit 1)
    - Zero check → quiet pass (no finding)
    - Suite not installed (no Cellar + no plist) → weak note, not hard fail
    - Script absent → silent skip (export/minimal trees)
    """
    out: List[Finding] = []
    root = city_root.expanduser().resolve()
    result = run_suite_sync_check(root)

    if result.get("skipped"):
        if result.get("not_installed"):
            out.append(
                _finding(
                    level="L0",
                    code="SUITE-SYNC-NOT-INSTALLED",
                    path=str(result.get("script") or "scripts/suite_sync_ui.sh"),
                    status="weak",
                    detail=(
                        "Suite Cellar + LaunchAgent absent — skip suite-sync drift "
                        "check (%s). Install/serve first, then re-run doctor."
                        % result.get("skipped")
                    ),
                    fixable=False,
                )
            )
        return out

    if result.get("error"):
        out.append(
            _finding(
                level="L0",
                code="SUITE-SYNC-DRIFT",
                path=str(result.get("script") or "scripts/suite_sync_ui.sh"),
                status="weak",
                detail=(
                    "suite_sync_ui.sh --check failed to run: %s"
                    % result.get("error")
                ),
                fixable=False,
            )
        )
        return out

    rc = result.get("returncode")
    if rc == 0:
        return out

    # Drift or live≠newest skew: hard fail so doctor exits non-zero.
    combined = "\n".join(
        [
            (result.get("stdout") or "").strip(),
            (result.get("stderr") or "").strip(),
        ]
    ).strip()
    lines = [ln for ln in combined.splitlines() if ln.strip()][:8]
    preview = "; ".join(lines) if lines else "exit %s" % rc
    script = result.get("script") or "scripts/suite_sync_ui.sh"
    out.append(
        _finding(
            level="L0",
            code="SUITE-SYNC-DRIFT",
            path=str(script),
            status="conflict",
            detail=(
                "Live brew suite drifted from repo (or live≠newest Cellar). "
                "Fix: `bash %s` then restart if serve.py changed "
                "(`blueprint serve` is launchd-safe — pc-1072/pc-1104). "
                "Detail: %s" % (script, preview[:500])
            ),
            fixable=False,
        )
    )
    return out


def diagnose_suite_stale_process() -> List[Finding]:
    """pc-438: warn when a suite process may be serving a deleted Cellar path."""
    out: List[Finding] = []
    try:
        # PIDs listening on suite port (portable: setup_flow knows win32)
        try:
            from protocolcity.setup_flow import _pids_listening_on

            pids = list(_pids_listening_on(8801))
        except Exception:
            try:
                raw = subprocess.check_output(
                    ["lsof", "-nP", "-t", "-iTCP:8801", "-sTCP:LISTEN"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                pids = [int(x) for x in raw.split() if x.isdigit()]
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                return out
        if not pids:
            return out
        # Installed package version (best-effort; preferred or compat distro)
        installed = ""
        try:
            from protocolcity.distro import distro_version

            installed = distro_version(default="")
            if installed == "not-installed":
                installed = ""
        except Exception:
            installed = ""
        for pid in pids[:5]:
            try:
                cmdline = Path("/proc/%d/cmdline" % pid).read_bytes()  # Linux
                cmd = cmdline.replace(b"\x00", b" ").decode("utf-8", "replace")
            except Exception:
                try:
                    cmd = subprocess.check_output(
                        ["ps", "-p", str(pid), "-o", "command="],
                        stderr=subprocess.DEVNULL,
                        text=True,
                    ).strip()
                except Exception:
                    continue
            if "suite/serve.py" not in cmd and "suite.serve" not in cmd:
                continue
            # Cellar path with version that is not the installed version
            if "/Cellar/protocolcity/" in cmd and installed:
                # …/Cellar/protocolcity/0.1.10/...
                marker = "/Cellar/protocolcity/"
                i = cmd.find(marker)
                if i >= 0:
                    rest = cmd[i + len(marker) :]
                    ver = rest.split("/")[0]
                    if ver and ver != installed:
                        out.append(
                            _finding(
                                level="L0",
                                code="SUITE-STALE-PROCESS",
                                path=":8801",
                                status="conflict",
                                detail=(
                                    "Suite PID %d still runs Cellar %s but package "
                                    "is %s — after brew upgrade run: blueprint stop "
                                    "&& blueprint serve --root <workspace>"
                                    % (pid, ver, installed)
                                ),
                                fixable=False,
                            )
                        )
        return out
    except Exception:
        return out


# pc-945: Map live-path currency (suite compose + WF generation schema).
_DEFAULT_SUITE = "http://127.0.0.1:8801"
_DEFAULT_WORKFORCE = "http://127.0.0.1:8797"
_LIVE_PATH_BOUNCE = (
    "process drift likely — bounce suite (and WF if generation probe fails): "
    "blueprint serve  # launchd kickstart when service installed (pc-1072); "
    "not stop&&serve — see docs/research/engine-ui-live-path-2026-08.md"
)
# wf-118 ships on protocolcity-workforce ≥0.1.6 (recent_failures on generation).
_WF_BOUNCE_FOR_FAILURES = (
    "Disk has wf-118; long-lived :8797 process does not. "
    "Bounce WorkForce daemon after upgrade "
    "(not suite-only — engine is a separate package)."
)
_WF_UNKNOWN_PACKAGE_FAILURES = (
    "WorkForce /api/generation lacks ``recent_failures`` key (wf-118). "
    "If protocolcity-workforce ≥0.1.6 is installed: bounce the daemon. "
    "If engines report workforce≤0.1.5: upgrade the engine package "
    "(BluePrint suite upgrade alone does not add this field)."
)


def _workforce_package_has_recent_failures() -> Optional[bool]:
    """Whether the *importable* workforce package implements wf-118.

    Returns:
      True  — ``workforce.api.roster.recent_failures`` is present (disk current)
      False — package importable but pre-wf-118 (e.g. brew pin 0.1.5)
      None  — workforce not importable in this interpreter (cannot gate)

    pc-1160 / GH #20: doctor used to always emit GENERATION-FAILURES-DRIFT when
    the live API lacked the key and told operators to bounce. Bouncing cannot
    invent a field the installed engine never shipped — gate on package
    capability so pre-0.1.6 installs stay silent (not a process-drift false alarm).
    """
    try:
        from workforce.api import roster as roster_mod  # type: ignore
    except Exception:
        return None
    return callable(getattr(roster_mod, "recent_failures", None))


def _fetch_json(
    url: str,
    *,
    timeout: float = 3.0,
) -> Dict[str, Any]:
    """HTTP GET → structured result for live-path probes (mockable in tests).

    Keys:
      ok: bool — True when status 2xx and body parsed as JSON
      status: int | None — HTTP status when a response was received
      data: Any — parsed JSON when ok, else None
      kind: 'ok' | 'unreachable' | 'http' | 'non_json'
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            status = int(getattr(r, "status", 200) or 200)
            raw = r.read()
    except urllib.error.HTTPError as e:
        status = int(e.code)
        try:
            raw = e.read()
        except Exception:
            raw = b""
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
            return {
                "ok": False,
                "status": status,
                "data": data,
                "kind": "http",
            }
        except Exception:
            return {
                "ok": False,
                "status": status,
                "data": None,
                "kind": "non_json",
            }
    except Exception:
        return {
            "ok": False,
            "status": None,
            "data": None,
            "kind": "unreachable",
        }
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return {
            "ok": False,
            "status": status,
            "data": None,
            "kind": "non_json",
        }
    if 200 <= status < 300:
        return {"ok": True, "status": status, "data": data, "kind": "ok"}
    return {"ok": False, "status": status, "data": data, "kind": "http"}


def diagnose_live_path_probes(
    *,
    suite_url: str = _DEFAULT_SUITE,
    workforce_url: str = _DEFAULT_WORKFORCE,
    timeout: float = 3.0,
) -> List[Finding]:
    """pc-945: fail loud when Map live-path seams are stale or missing.

    Probes (cheap GETs; silent when engines offline):
      1. suite ``/api/tasks/live-strip`` — must be JSON 200 with ok shape (pc-934)
      2. suite light ``/api/tasks`` — sample rows must include ``glance`` key (pc-921)
      3. WF ``/api/generation`` — when reachable, prefer ``recent_failures`` key (wf-118)

    Schema checks only (glance may be empty string). Actionable bounce text, not --fix.

    pc-1160: generation probe is **gated** on installed workforce capability —
    missing ``recent_failures`` is only process-drift when the importable package
    already ships wf-118. Pre-0.1.6 engines stay silent (upgrade path, not bounce).
    """
    out: List[Finding] = []
    suite = (suite_url or _DEFAULT_SUITE).rstrip("/")
    wf = (workforce_url or _DEFAULT_WORKFORCE).rstrip("/")

    # --- 1) live-strip ---
    strip_url = "%s/api/tasks/live-strip?family=open&limit=2" % suite
    strip = _fetch_json(strip_url, timeout=timeout)
    suite_reachable = strip.get("kind") != "unreachable"
    if strip.get("kind") == "unreachable":
        # Suite down — skip suite probes (no DESK-UNREACHABLE dual-noise here).
        pass
    elif not strip.get("ok"):
        status = strip.get("status")
        kind = strip.get("kind")
        if kind == "non_json":
            detail = (
                "GET /api/tasks/live-strip returned non-JSON (HTTP %s) — "
                "route missing from running serve.py (pre-pc-934). %s"
                % (status if status is not None else "?", _LIVE_PATH_BOUNCE)
            )
        else:
            detail = (
                "GET /api/tasks/live-strip failed (HTTP %s) — Map WO desk tape "
                "cannot load composite. %s"
                % (status if status is not None else "?", _LIVE_PATH_BOUNCE)
            )
        out.append(
            _finding(
                level="L0",
                code="LIVE-STRIP-DRIFT",
                path=strip_url,
                status="conflict",
                detail=detail,
                fixable=False,
            )
        )
    else:
        data = strip.get("data")
        if not isinstance(data, dict) or data.get("ok") is False:
            out.append(
                _finding(
                    level="L0",
                    code="LIVE-STRIP-DRIFT",
                    path=strip_url,
                    status="conflict",
                    detail=(
                        "live-strip JSON present but ok=false or not an object — "
                        "engine proxy broken. %s" % _LIVE_PATH_BOUNCE
                    ),
                    fixable=False,
                )
            )
        # healthy live-strip → silent

    # --- 2) light list glance schema ---
    if suite_reachable:
        tasks: List[dict] = []
        sample_url = ""
        for status_name in ("backlog", "in_progress", "in_review", "done"):
            list_url = "%s/api/tasks?status=%s&limit=5" % (suite, status_name)
            resp = _fetch_json(list_url, timeout=timeout)
            if not resp.get("ok"):
                continue
            data = resp.get("data")
            if not isinstance(data, dict):
                continue
            rows = data.get("tasks") or []
            if isinstance(rows, list) and rows:
                tasks = [t for t in rows if isinstance(t, dict)]
                sample_url = list_url
                break
        if tasks:
            missing = [t for t in tasks if "glance" not in t]
            if missing:
                sample_ids = ", ".join(
                    str(t.get("id") or "?") for t in missing[:3]
                )
                out.append(
                    _finding(
                        level="L0",
                        code="LIGHT-GLANCE-DRIFT",
                        path=sample_url or ("%s/api/tasks" % suite),
                        status="conflict",
                        detail=(
                            "light /api/tasks rows omit ``glance`` key "
                            "(%d/%d sampled; e.g. %s) — server extract (pc-921) "
                            "not in running process; client hydrate stampede "
                            "only. %s"
                            % (
                                len(missing),
                                len(tasks),
                                sample_ids,
                                _LIVE_PATH_BOUNCE,
                            )
                        ),
                        fixable=False,
                    )
                )
            # key present (even empty strings) → silent

    # --- 3) WF generation recent_failures (optional schema when daemon up) ---
    # pc-1160 / GH #20: only treat missing key as process drift when the
    # *installed* package actually implements wf-118. Suite upgrade to a
    # blueprint that still pins workforce 0.1.5 cannot bounce a field into
    # existence — stay silent (capability gap) instead of false-alarming.
    gen_url = "%s/api/generation" % wf
    gen = _fetch_json(gen_url, timeout=timeout)
    if gen.get("kind") == "unreachable":
        pass
    elif not gen.get("ok") or not isinstance(gen.get("data"), dict):
        # Generation endpoint broken is rarer; weak only (Agents strip residual).
        # Still gate: pre-wf-118 package cannot serve the field either way.
        disk_has = _workforce_package_has_recent_failures()
        if disk_has is False:
            pass  # engine package pre-wf-118 — not a bounce-after-upgrade issue
        else:
            detail = (
                "WorkForce /api/generation unreachable-as-JSON while suite "
                "live path is under audit — Agents pulse cannot read "
                "recent_failures (wf-118). Bounce WF if daemon should be up."
                if disk_has is True
                else _WF_UNKNOWN_PACKAGE_FAILURES
            )
            out.append(
                _finding(
                    level="L0",
                    code="GENERATION-FAILURES-DRIFT",
                    path=gen_url,
                    status="weak",
                    detail=detail,
                    fixable=False,
                )
            )
    else:
        gdata = gen["data"]
        if "recent_failures" not in gdata:
            disk_has = _workforce_package_has_recent_failures()
            if disk_has is False:
                # Installed package never shipped the field (e.g. brew 0.1.5).
                # Silent: upgrade protocolcity-workforce ≥0.1.6, not bounce.
                pass
            elif disk_has is True:
                out.append(
                    _finding(
                        level="L0",
                        code="GENERATION-FAILURES-DRIFT",
                        path=gen_url,
                        status="weak",
                        detail=(
                            "WorkForce /api/generation lacks ``recent_failures`` key "
                            "(wf-118) — failed shifts stay invisible on Agents glass. "
                            + _WF_BOUNCE_FOR_FAILURES
                        ),
                        fixable=False,
                    )
                )
            else:
                # Package not importable here — dual-path operator guidance.
                out.append(
                    _finding(
                        level="L0",
                        code="GENERATION-FAILURES-DRIFT",
                        path=gen_url,
                        status="weak",
                        detail=_WF_UNKNOWN_PACKAGE_FAILURES,
                        fixable=False,
                    )
                )
        # key present (list, possibly empty) → silent

    return out


def diagnose_roster_paths(city_root: Path) -> List[Finding]:
    """pc-351: hire/serve/suite must share one roster home.

    Canonical: ``{city}/.protocolcity/workforce/local/roster.json``
    Legacy: ``{city}/workforce/local/roster.json`` (pre-split bug)
    """
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    canonical = root / ".protocolcity" / "workforce" / "local" / "roster.json"
    legacy = root / "workforce" / "local" / "roster.json"

    def _worker_count(path: Path) -> int:
        if not path.is_file():
            return 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return -1
        workers = raw.get("workers") if isinstance(raw, dict) else None
        if not isinstance(workers, dict):
            return 0
        return len(workers)

    can_n = _worker_count(canonical)
    leg_n = _worker_count(legacy)

    if can_n < 0:
        out.append(
            _finding(
                level="L0",
                code="ROSTER-UNREADABLE",
                path=str(canonical),
                status="conflict",
                detail="Canonical roster JSON unreadable",
                fixable=False,
            )
        )
    elif canonical.is_file():
        out.append(
            _finding(
                level="L0",
                code="ROSTER-CANONICAL",
                path=str(canonical),
                status="ok",
                detail="Canonical roster present (%d worker(s))" % max(can_n, 0),
            )
        )
    else:
        out.append(
            _finding(
                level="L0",
                code="ROSTER-CANONICAL-MISSING",
                path=str(canonical),
                status="weak",
                detail=(
                    "No canonical roster yet — `protocolcity hire` writes here; "
                    "`serve --with-engines` also uses this path"
                ),
                fixable=False,
            )
        )

    same_inode = False
    if legacy.is_file() and canonical.is_file():
        try:
            same_inode = legacy.resolve() == canonical.resolve()
        except OSError:
            same_inode = False

    if legacy.is_file() and can_n >= 0 and not same_inode:
        if not canonical.is_file() or leg_n > can_n:
            out.append(
                _finding(
                    level="L0",
                    code="ROSTER-PATH-SPLIT",
                    path=str(legacy),
                    status="conflict",
                    detail=(
                        "Legacy roster at workforce/local/ has data "
                        "(%d worker(s)) while canonical .protocolcity path "
                        "has %s — daemon reads canonical; "
                        "`doctor --fix` merges into .protocolcity/workforce/local/"
                        % (
                            max(leg_n, 0),
                            "missing" if not canonical.is_file() else "%d worker(s)" % can_n,
                        )
                    ),
                    fixable=True,
                )
            )
        elif leg_n >= 0 and leg_n != can_n and can_n >= 0:
            out.append(
                _finding(
                    level="L0",
                    code="ROSTER-PATH-SPLIT",
                    path=str(legacy),
                    status="weak",
                    detail=(
                        "Both roster paths exist with different worker counts "
                        "(legacy=%d, canonical=%d) — `doctor --fix` merges to canonical"
                        % (leg_n, can_n)
                    ),
                    fixable=True,
                )
            )
    elif same_inode:
        out.append(
            _finding(
                level="L0",
                code="ROSTER-LEGACY-LINK",
                path=str(legacy),
                status="ok",
                detail="Legacy workforce/local/roster.json points at canonical path",
            )
        )

    # Papers under workers/ but empty/missing roster → hire never armed
    stub_count = 0
    try:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            workers_dir = child / "workers"
            if not workers_dir.is_dir():
                continue
            for w in workers_dir.iterdir():
                if (
                    w.is_dir()
                    and not w.name.startswith(".")
                    and (w / "CONTRACT.md").is_file()
                ):
                    stub_count += 1
    except OSError:
        stub_count = 0

    if stub_count > 0 and (can_n == 0 or not canonical.is_file()):
        # Only flag if legacy also empty — otherwise PATH-SPLIT covers it
        if leg_n <= 0:
            out.append(
                _finding(
                    level="L0",
                    code="ROSTER-EMPTY-WHILE-STUBS",
                    path=str(canonical),
                    status="missing",
                    detail=(
                        "%d worker paper stub(s) under projects but canonical "
                        "roster empty — run `protocolcity hire` (papers alone "
                        "do not arm the daemon)"
                        % stub_count
                    ),
                    fixable=False,
                )
            )

    return out


def _worker_papers_are_stubs(paths: List[Path]) -> bool:
    """True when planted template papers still carry fill-me placeholders (pc-489)."""
    chunks: List[str] = []
    for p in paths:
        try:
            chunks.append(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    if not chunks:
        return False
    body = "\n".join(chunks)
    # found/adopt blank {{PLACEHOLDERS}} to "(fill me)"
    return "(fill me)" in body


def _findings_architecture(cab: Path, *, managed: bool) -> List[Finding]:
    """L1 ARCHITECTURE.md missing or still fill-me scaffold (pc-1087).

    Managed projects must carry architecture law next to AGENTS.md. Missing is
    fixable via adopt / doctor --fix (re-adopt plants the template). Stub
    (template fill-mes) is weak — human authors real layers/SoTs.
    """
    if not managed:
        return []
    from protocolcity.found import looks_like_architecture_scaffold

    arch = cab / "ARCHITECTURE.md"
    out: List[Finding] = []
    if not arch.is_file():
        out.append(
            _finding(
                level="L1",
                code="MISSING-ARCHITECTURE",
                path=str(arch),
                status="missing",
                detail=(
                    "No ARCHITECTURE.md — adopt / doctor --fix plants the "
                    "project-ARCHITECTURE template (layers, SoTs, data flow, "
                    "invariants)"
                ),
                fixable=True,
            )
        )
        return out
    try:
        text = arch.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if looks_like_architecture_scaffold(text):
        out.append(
            _finding(
                level="L1",
                code="STUB-ARCHITECTURE",
                path=str(arch),
                status="weak",
                detail=(
                    "ARCHITECTURE.md is still a BluePrint fill-me scaffold — "
                    "replace layers, sources of truth, data flow, and invariants "
                    "with real product law (doctor does not auto-rewrite stubs)"
                ),
                fixable=False,
            )
        )
    else:
        out.append(
            _finding(
                level="L1",
                code="ARCHITECTURE",
                path=str(arch),
                status="ok",
                detail="ARCHITECTURE.md present (authored)",
            )
        )
    return out


def _findings_features(cab: Path, *, managed: bool) -> List[Finding]:
    """FEATURES.md missing or still fill-me scaffold (pc-1317).

    Managed projects must carry founder-named surfaces (docs/FEATURES.md
    when docs/ exists, else project-root FEATURES.md). Missing is fixable
    via adopt / doctor --fix. Stub (template fill-mes) is weak — human
    authors real rows.
    """
    if not managed:
        return []
    from protocolcity.found import looks_like_features_scaffold, project_features_path

    feat = project_features_path(cab)
    out: List[Finding] = []
    if not feat.is_file():
        out.append(
            _finding(
                level="L1",
                code="MISSING-FEATURES",
                path=str(feat),
                status="missing",
                detail=(
                    "No FEATURES.md — adopt / doctor --fix plants the "
                    "FEATURES template at docs/FEATURES.md (or project root "
                    "when the project has no docs/)"
                ),
                fixable=True,
            )
        )
        return out
    try:
        text = feat.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if looks_like_features_scaffold(text):
        out.append(
            _finding(
                level="L1",
                code="STUB-FEATURES",
                path=str(feat),
                status="weak",
                detail=(
                    "FEATURES.md is still a BluePrint fill-me scaffold — "
                    "replace rows with founder-named surfaces, where they live, "
                    "and how a hand verifies them (doctor does not auto-rewrite stubs)"
                ),
                fixable=False,
            )
        )
    else:
        out.append(
            _finding(
                level="L1",
                code="FEATURES",
                path=str(feat),
                status="ok",
                detail="FEATURES.md present (authored)",
            )
        )
    return out


def diagnose_neighborhood(city_root: Path, name: str) -> List[Finding]:
    root = city_root.expanduser().resolve()
    # pc-570: slugify-match (not only exact path) so "Work Folder" / trailing
    # space on disk still diagnose instead of false NO-FOLDER.
    cab_resolved = resolve_neighborhood(root, name)
    cab = cab_resolved if cab_resolved is not None else (root / (name or "").strip())
    out: List[Finding] = []
    if cab_resolved is None or not cab.is_dir():
        return [
            _finding(
                level="L1",
                code="NO-FOLDER",
                path=str(root / (name or "").strip()),
                status="missing",
                detail="Project folder does not exist",
                fixable=False,
            )
        ]

    # Weak hint when Finder left leading/trailing whitespace on the basename.
    if cab.name != cab.name.strip():
        out.append(
            _finding(
                level="L1",
                code="TRAILING-WS-FOLDER",
                path=str(cab),
                status="warn",
                detail=(
                    "Folder basename has leading/trailing whitespace (%r) — "
                    "adopt/doctor resolve via slugify, but rename to a clean "
                    "name (e.g. spaces→hyphens) for friendlier paths"
                    % cab.name
                ),
                fixable=False,
            )
        )

    agents = cab / "AGENTS.md"
    # pc-1359: unmanaged foreign is consumer posture — not an adopt nag.
    if _is_foreign_consumer_folder(cab) and not is_managed(cab):
        out.append(_foreign_consumer_finding(cab))
    else:
        # pc-1041: same law/managed + vendor-pointer helpers as diagnose_city
        out.extend(
            _findings_law_and_managed(
                cab,
                level="L1",
                missing_code="MISSING-NEIGHBORHOOD-LAW",
                ok_code="NEIGHBORHOOD-LAW",
                unmanaged_code="INSTRUCTIONS-NOT-MANAGED",
                missing_detail=(
                    "No AGENTS.md — Adopt / doctor --fix plants project "
                    "instructions + join marker"
                ),
                ok_detail="BluePrint-managed (join marker + AGENTS.md)",
                unmanaged_detail=(
                    "Has AGENTS.md but not BluePrint-managed — run adopt "
                    "(writes .protocolcity/managed)"
                ),
                missing_fixable=True,
                unmanaged_fixable=True,
            )
        )
    out.extend(
        _findings_vendor_pointers(
            cab,
            agents=agents,
            level="L1",
            diverged_detail_fmt="%s diverged — not auto-fixed",
        )
    )

    # pc-1087: ARCHITECTURE.md is L1 product law beside AGENTS.md
    out.extend(_findings_architecture(cab, managed=is_managed(cab)))
    # pc-1317: FEATURES.md — founder-named surfaces (docs/ or project root)
    out.extend(_findings_features(cab, managed=is_managed(cab)))

    workers = cab / "workers"
    worker_names: List[str] = []
    if workers.is_dir():
        try:
            worker_names = sorted(
                n.name
                for n in workers.iterdir()
                if n.is_dir() and not n.name.startswith(".")
            )
        except OSError:
            worker_names = []

    if not worker_names:
        # pc-489: empty workers/ is fine for ticket-only neighborhoods — not a
        # hard missing. Stubs are opt-in via adopt --with-demo-worker / found.
        out.append(
            _finding(
                level="L2",
                code="NO-WORKER-HIRES",
                path=str(workers),
                status="ok",
                detail=(
                    "No workers/ hires yet — optional; hire a real lane when ready "
                    "(`protocolcity hire`) or plant unarmed stubs with "
                    "`protocolcity adopt … --with-demo-worker`"
                ),
                fixable=False,
            )
        )
    else:
        for wid in worker_names:
            wdir = workers / wid
            papers_present = []
            for req in ("CONTRACT.md", "prompt.md"):
                rp = wdir / req
                if not rp.is_file():
                    out.append(
                        _finding(
                            level="L2",
                            code="MISSING-WORKER-PAPER",
                            path=str(rp),
                            status="missing",
                            detail="%s missing under workers/%s" % (req, wid),
                            fixable=True,
                        )
                    )
                else:
                    papers_present.append(rp)
                    out.append(
                        _finding(
                            level="L2",
                            code="WORKER-PAPER",
                            path=str(rp),
                            status="ok",
                            detail="workers/%s/%s ok" % (wid, req),
                        )
                    )
            # pc-489: template fill-mes left as stub papers — weak, not hard ok
            if papers_present and _worker_papers_are_stubs(papers_present):
                out.append(
                    _finding(
                        level="L2",
                        code="STUB-WORKER-PAPERS",
                        path=str(wdir),
                        status="weak",
                        detail=(
                            "stub worker papers under workers/%s — hire a real "
                            "lane or remove the stubs (doctor --fix does not delete)"
                            % wid
                        ),
                        fixable=False,
                    )
                )

    # Desk store for this neighborhood (same gap agents hit when AGENTS-only)
    if agents.is_file() and not _likely_non_adoptable(name):
        stores = _desk_store_slugs()
        store_map = _desk_store_map()
        slug = desk_slug(name)
        join = read_desk_join(cab)
        if stores is None:
            out.append(
                _finding(
                    level="L1",
                    code="DESK-UNREACHABLE",
                    path=DEFAULT_DESK,
                    status="weak",
                    detail="desk offline — cannot verify store join for %s" % name,
                    fixable=False,
                )
            )
            # Offline: still report local join file if present
            if join:
                out.append(
                    _finding(
                        level="L1",
                        code="DESK-JOIN-FILE",
                        path=str(cab / ".protocolcity" / "desk-join.json"),
                        status="ok",
                        detail="local desk-join.json present (slug=%s prefix=%s); "
                        "desk offline — not cross-checked"
                        % (join.get("slug"), join.get("prefix")),
                    )
                )
            elif is_managed(cab):
                out.append(
                    _finding(
                        level="L1",
                        code="MISSING-DESK-JOIN-FILE",
                        path=str(cab / ".protocolcity" / "desk-join.json"),
                        status="weak",
                        detail="managed neighborhood has no desk-join.json "
                        "(desk offline — cannot rewrite from registry)",
                        fixable=False,
                    )
                )
        elif slug in stores:
            out.append(
                _finding(
                    level="L1",
                    code="DESK-STORE",
                    path=str(cab),
                    status="ok",
                    detail="%s joined to desk store `%s`" % (name, slug),
                )
            )
            live = (store_map or {}).get(slug) or {}
            live_prefix = str(live.get("prefix") or "").strip()
            if join:
                jslug = str(join.get("slug") or "").strip().lower()
                jprefix = str(join.get("prefix") or "").strip()
                mismatch = (jslug and jslug != slug) or (
                    live_prefix and jprefix and jprefix != live_prefix
                )
                if mismatch:
                    out.append(
                        _finding(
                            level="L1",
                            code="DESK-JOIN-MISMATCH",
                            path=str(cab / ".protocolcity" / "desk-join.json"),
                            status="warn",
                            detail="desk-join.json (slug=%s prefix=%s) != live "
                            "store (slug=%s prefix=%s) — doctor --fix rewrites"
                            % (jslug, jprefix, slug, live_prefix or "?"),
                            fixable=True,
                        )
                    )
                else:
                    out.append(
                        _finding(
                            level="L1",
                            code="DESK-JOIN-FILE",
                            path=str(cab / ".protocolcity" / "desk-join.json"),
                            status="ok",
                            detail="desk-join.json matches store `%s` (prefix %s)"
                            % (slug, jprefix or live_prefix or "?"),
                        )
                    )
            else:
                out.append(
                    _finding(
                        level="L1",
                        code="MISSING-DESK-JOIN-FILE",
                        path=str(cab / ".protocolcity" / "desk-join.json"),
                        status="missing",
                        detail="store `%s` exists but no desk-join.json — "
                        "doctor --fix rewrites from products registry"
                        % slug,
                        fixable=True,
                    )
                )
            # Soft hygiene: AGENTS without store/prefix mention
            try:
                agents_text = agents.read_text(encoding="utf-8")
            except OSError:
                agents_text = ""
            from protocolcity.desk import agents_has_desk_identity

            check_prefix = (join or {}).get("prefix") or live_prefix
            if check_prefix and not agents_has_desk_identity(
                agents_text, slug, str(check_prefix)
            ):
                out.append(
                    _finding(
                        level="L1",
                        code="MISSING-DESK-IDENTITY-IN-LAW",
                        path=str(agents),
                        status="weak",
                        detail="AGENTS.md does not mention store `%s` / prefix `%s` "
                        "— optional soft-append on adopt/doctor --fix"
                        % (slug, check_prefix),
                        fixable=True,
                    )
                )
        else:
            out.append(
                _finding(
                    level="L1",
                    code="MISSING-DESK-STORE",
                    path=str(cab),
                    status="missing",
                    detail="%s managed but no desk store `%s` — "
                    "doctor --fix / adopt joins WorkLane"
                    % (name, slug),
                    fixable=True,
                )
            )
            if is_managed(cab) and not join:
                out.append(
                    _finding(
                        level="L1",
                        code="MISSING-DESK-JOIN-FILE",
                        path=str(cab / ".protocolcity" / "desk-join.json"),
                        status="missing",
                        detail="no desk-join.json (store also missing)",
                        fixable=True,
                    )
                )

        # pc-557: moved workspace — venv/scripts still point at a prior root
        stale = _stale_absolute_paths(cab, city_root)
        if stale:
            out.append(
                _finding(
                    level="L1",
                    code="STALE-ABSOLUTE-PATHS",
                    path=str(cab / ".venv") if (cab / ".venv").is_dir() else str(cab),
                    status="weak",
                    detail=(
                        "project still embeds absolute paths from a prior location "
                        "(%s). Rebuild the venv after a workspace move: "
                        "`rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -e .` "
                        "(or reinstall deps). Samples: %s"
                        % (
                            ", ".join(stale.get("foreign_roots") or []) or "unknown",
                            "; ".join((stale.get("samples") or [])[:3]),
                        )
                    ),
                    fixable=False,
                )
            )

    return out


def _stale_absolute_paths(hood: Path, city_root: Path) -> Optional[Dict[str, Any]]:
    """Detect .venv / scripts that still reference paths outside city_root (pc-557)."""
    root = city_root.expanduser().resolve()
    root_s = str(root)
    home = str(Path.home())
    samples: List[str] = []
    foreign: set = set()
    candidates = [
        hood / ".venv" / "bin" / "python",
        hood / ".venv" / "bin" / "pip",
        hood / ".venv" / "pyvenv.cfg",
    ]
    # Also scan a few RECORD files for absolute prior roots
    site = hood / ".venv" / "lib"
    if site.is_dir():
        for rec in site.rglob("RECORD"):
            candidates.append(rec)
            if len(candidates) > 12:
                break
    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Shebang or embedded abs paths under home but not this city
        for line in text.splitlines()[:40]:
            if "/Users/" not in line and home not in line:
                continue
            # Extract /Users/... segments
            for m in re.finditer(r"(/Users/[^/\s\"']+(?:/[^/\s\"']+)*)", line):
                p = m.group(1)
                if p.startswith(root_s + "/") or p == root_s:
                    continue
                # Prior workspace roots (my-city, ProtocolCity, etc.)
                if "/my-city" in p or (
                    p.startswith(home + "/") and not p.startswith(root_s)
                ):
                    # Only flag if clearly outside current hood
                    if str(hood.resolve()) not in p:
                        foreign.add(p.split("/.venv")[0].rsplit("/", 1)[0] if "/.venv" in p else p[:80])
                        samples.append("%s → %s" % (path.name, p[:120]))
                        break
            if len(samples) >= 6:
                break
        if len(samples) >= 6:
            break
    if not samples:
        return None
    return {"samples": samples, "foreign_roots": sorted(foreign)[:5]}


def _roster_candidate_paths(city_root: Path) -> List[Path]:
    """Ordered roster homes: env, canonical under city, legacy under city."""
    paths: List[Path] = []
    env = (os.environ.get("WORKFORCE_ROSTER") or "").strip()
    if env:
        paths.append(Path(env).expanduser())
    root = city_root.expanduser().resolve()
    paths.append(root / ".protocolcity" / "workforce" / "local" / "roster.json")
    paths.append(root / "workforce" / "local" / "roster.json")
    # de-dupe
    seen = set()
    out: List[Path] = []
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _load_roster_workers(city_root: Path) -> Dict[str, Dict[str, Any]]:
    """Merge workers from roster candidates (earlier path wins on key conflict)."""
    merged: Dict[str, Dict[str, Any]] = {}
    for path in _roster_candidate_paths(city_root):
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        workers = raw.get("workers") if isinstance(raw, dict) else None
        if not isinstance(workers, dict):
            continue
        for wid, row in workers.items():
            key = str(wid).strip().lower()
            if not key or key in merged or not isinstance(row, dict):
                continue
            merged[key] = row
    return merged


def _product_from_queue_url(url: str) -> Optional[str]:
    """Extract product/project store slug from a WorkForce queue_url."""
    if not url or not isinstance(url, str):
        return None
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    except Exception:
        return None
    for key in ("product", "project"):
        vals = q.get(key) or []
        if vals and str(vals[0]).strip():
            return str(vals[0]).strip().lower()
    return None


def _lane_hands_by_product(
    workers: Dict[str, Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Map store slug → hired hand ids that drain a labeled ready feed.

    Only ``kind=lane`` (default/legacy) hands claim work orders. ``kind=job``
    municipal duties are ignored (same law as Map Main Street / pc-109).
    """
    by_product: Dict[str, List[str]] = {}
    for wid, row in (workers or {}).items():
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "lane").strip().lower()
        if kind in ("job", "patrol", "duty"):
            continue
        product = _product_from_queue_url(str(row.get("queue_url") or ""))
        if not product:
            # Optional explicit project field from hire
            project = str(row.get("project") or row.get("product") or "").strip().lower()
            if project:
                product = project
        if not product:
            continue
        by_product.setdefault(product, []).append(str(wid))
    for product in by_product:
        by_product[product] = sorted(set(by_product[product]))
    return by_product


def _desk_ready_tasks(
    product: str,
    desk_url: str = DEFAULT_DESK,
    *,
    limit: int = 100,
) -> Optional[List[dict]]:
    """Fetch ready tasks for one store. None = desk unreachable / error."""
    if not product:
        return None
    qs = urllib.parse.urlencode(
        {
            "product": product,
            "project": product,
            "limit": str(max(1, min(int(limit), 200))),
        }
    )
    url = "%s/api/admin/tasks/ready?%s" % (desk_url.rstrip("/"), qs)
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    tasks = data.get("tasks") or data.get("ready") or []
    if not isinstance(tasks, list):
        return []
    return [t for t in tasks if isinstance(t, dict)]


def diagnose_unrouted_ready(
    city_root: Path,
    *,
    desk_url: str = DEFAULT_DESK,
    product: Optional[str] = None,
) -> List[Finding]:
    """pc-510: ready work with no ``worker:*`` while hired hands exist for the store.

    Same unrouted definition as ``suite.api.routing`` / ``GET /api/tasks/unrouted``
    (pc-498). Emits one ``UNROUTED-READY`` finding per affected store.
    """
    out: List[Finding] = []
    workers = _load_roster_workers(city_root)
    hands = _lane_hands_by_product(workers)
    if not hands:
        return out

    try:
        from suite.api.routing import filter_unrouted_tasks
    except ImportError:
        # Wheel/layout edge: keep doctor alive; do not invent a second definition.
        return out

    products = sorted(hands.keys())
    if product:
        want = product.strip().lower()
        products = [p for p in products if p == want]
        if not products:
            # Named product has no hired hands — silent (no false alarm).
            return out

    desk = (desk_url or DEFAULT_DESK).rstrip("/")
    for prod in products:
        hand_ids = hands.get(prod) or []
        if not hand_ids:
            continue
        tasks = _desk_ready_tasks(prod, desk)
        if tasks is None:
            # Desk offline — DESK-UNREACHABLE already covers city-level; skip noise.
            continue
        unrouted = filter_unrouted_tasks(tasks)
        if not unrouted:
            continue
        n = len(unrouted)
        sample = ", ".join(
            str(t.get("id") or "?") for t in unrouted[:5]
        )
        if n > 5:
            sample = sample + ", …"
        hands_preview = ", ".join(hand_ids[:6])
        if len(hand_ids) > 6:
            hands_preview = hands_preview + ", …"
        out.append(
            _finding(
                level="L0",
                code="UNROUTED-READY",
                path="%s/api/admin/tasks/ready?product=%s" % (desk, prod),
                status="weak",
                detail=(
                    "%d ready ticket(s) in store `%s` have no worker:* label "
                    "while %d hired hand(s) drain that store (%s). "
                    "Unlabeled ready never enters a hand queue — stamp "
                    "worker:<id> (suite file hand picker or label), or "
                    "GET /api/tasks/unrouted?product=%s. Sample: %s"
                    % (n, prod, len(hand_ids), hands_preview, prod, sample)
                ),
                fixable=False,
            )
        )
    return out


# ---------------------------------------------------------------------------
# pc-960: generate-don't-document — doctor verifies manual-step surfaces
# ---------------------------------------------------------------------------

_WORKER_LABEL_RE = re.compile(r"^worker:([a-z][a-z0-9._-]*)$", re.I)
_PROCESS_ID_ROW_RE = re.compile(
    r"\|\s*`([a-z][a-z0-9._-]*)`\s*\|\s*([^|]+?)(?=\||$)",
    re.I,
)
_RETIRED_LEAD_RE = re.compile(r"^\s*(\*\*)?RETIRED\b", re.I)


def find_process_md(city_root: Path) -> Optional[Path]:
    """Locate WorkLane PROCESS.md (identity registry §5.2 home).

    Cross-cabinet *read* only — doctor never rewrites this file from ProtocolCity.
    """
    root = city_root.expanduser().resolve()
    env = (os.environ.get("WORKLANE_PROCESS") or os.environ.get("TP_PROCESS") or "").strip()
    candidates: List[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(
        [
            root / "worklane" / "PROCESS.md",
            root / "ticketingprotocol" / "PROCESS.md",
            root / "WorkLane" / "PROCESS.md",
        ]
    )
    for p in candidates:
        try:
            if p.is_file():
                return p.resolve()
        except OSError:
            continue
    return None


def parse_process_identity_registry(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse PROCESS.md §5.2 identity table → id → {retired, who}.

    Row is retired when the Who column *leads* with RETIRED (bold optional).
    History mentions of prior retirements inside an active row do not retire it.
    Handles glued rows where a literal ``\\n|`` appears mid-line (PROCESS quirk).
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not text:
        return out
    m = re.search(
        r"###\s*5\.2\).*?(?=####\s*5\.2\.1|###\s*5\.3|\Z)",
        text,
        re.S,
    )
    section = m.group(0) if m else text
    # Normalize literal backslash-n sequences so glued rows split.
    section = section.replace("\\n|", "\n|")
    for mid, who in _PROCESS_ID_ROW_RE.findall(section):
        key = mid.strip().lower()
        if not key or key in ("agent id", "id"):
            continue
        who_s = (who or "").strip()
        # Skip markdown separator / header residue
        if set(who_s) <= set("-: "):
            continue
        out[key] = {
            "retired": bool(_RETIRED_LEAD_RE.match(who_s)),
            "who": who_s[:200],
        }
    return out


def load_process_identity_registry(city_root: Path) -> Optional[Dict[str, Dict[str, Any]]]:
    """Load §5.2 registry from disk; None when PROCESS.md is not found."""
    path = find_process_md(city_root)
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return parse_process_identity_registry(text)


def _active_roster_lane_ids(city_root: Path) -> List[str]:
    """Hired claiming-lane ids on the roster (kind=lane / default)."""
    workers = _load_roster_workers(city_root)
    ids: List[str] = []
    for wid, row in (workers or {}).items():
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "lane").strip().lower()
        if kind in ("job", "patrol", "duty"):
            continue
        key = str(wid).strip().lower()
        if key:
            ids.append(key)
    return sorted(set(ids))


def _desk_tasks_for_status(
    product: str,
    status: str,
    desk_url: str = DEFAULT_DESK,
    *,
    limit: int = 200,
) -> Optional[List[dict]]:
    """List tasks for one product+status. None = desk unreachable / error."""
    if not product or not status:
        return None
    qs = urllib.parse.urlencode(
        {
            "product": product,
            "project": product,
            "status": status,
            "limit": str(max(1, min(int(limit), 500))),
        }
    )
    url = "%s/api/admin/tasks?%s" % (desk_url.rstrip("/"), qs)
    try:
        with urllib.request.urlopen(url, timeout=4) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    tasks = data.get("tasks") or []
    if not isinstance(tasks, list):
        return []
    return [t for t in tasks if isinstance(t, dict)]


def _worker_seat_from_labels(labels: Any) -> Optional[str]:
    """Return the worker:<id> seat from a label list, or None."""
    if not isinstance(labels, list):
        return None
    for lab in labels:
        s = str(lab or "").strip()
        m = _WORKER_LABEL_RE.match(s)
        if m:
            return m.group(1).lower()
    return None


def diagnose_identity_registry(
    city_root: Path,
    *,
    registry: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Finding]:
    """pc-960 (a): every active roster lane id has a PROCESS §5.2 row.

    Report-only. §5.2 lives in worklane/PROCESS.md — ProtocolCity doctor never
    auto-appends rows (cross-cabinet write → sibling wl ticket / hire emit).
    """
    out: List[Finding] = []
    root = city_root.expanduser().resolve()
    reg = registry if registry is not None else load_process_identity_registry(root)
    process_path = find_process_md(root)
    path_s = str(process_path) if process_path else "worklane/PROCESS.md §5.2"

    if reg is None:
        # No PROCESS.md in this workspace layout — skip (export cities may omit desk).
        return out

    lane_ids = _active_roster_lane_ids(root)
    if not lane_ids:
        return out

    missing = [wid for wid in lane_ids if wid not in reg]
    if missing:
        sample = ", ".join("`%s`" % w for w in missing[:8])
        if len(missing) > 8:
            sample = sample + ", …"
        out.append(
            _finding(
                level="L0",
                code="UNREGISTERED-IDENTITY",
                path=path_s,
                status="weak",
                detail=(
                    "%d active roster lane id(s) missing from Desk PROCESS §5.2 "
                    "identity table: %s. Hire/found must emit the row (or stage a "
                    "wl-* write); until then agents mis-sign or ghost-audit fails. "
                    "Manual: append a `| `id` | Who |` row under §5.2."
                    % (len(missing), sample)
                ),
                fixable=False,
            )
        )
    return out


def diagnose_retired_seats(
    city_root: Path,
    *,
    desk_url: str = DEFAULT_DESK,
    product: Optional[str] = None,
    registry: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Finding]:
    """pc-960 (b): open tickets must not sit on retired/unknown worker:* seats.

    A seat is bad when:
      - §5.2 marks the id RETIRED (leading RETIRED in Who), or
      - the id is absent from both §5.2 and the live roster (unknown).
    Live roster ids that are still registered (even if succession is pending)
    are allowed.
    """
    out: List[Finding] = []
    root = city_root.expanduser().resolve()
    reg = registry if registry is not None else load_process_identity_registry(root)
    # Without registry we can still flag unknown-vs-roster using roster alone.
    roster_ids = set(_active_roster_lane_ids(root))
    # Also include jobs so job-seated tickets aren't false-flagged as unknown.
    for wid, row in (_load_roster_workers(root) or {}).items():
        if isinstance(row, dict):
            roster_ids.add(str(wid).strip().lower())

    def _seat_is_bad(seat: str) -> Optional[str]:
        if not seat:
            return None
        if seat == "you":
            # You is a persona (D11), never a WorkForce roster seat — a
            # bare worker:you label is covered by YOU-STARVE-*, not a
            # retired/unknown seat here.
            return None
        if seat in roster_ids:
            # Live on roster — even if §5.2 says retired, employment wins for
            # dispatch (doctor can still flag UNREGISTERED / succession separately).
            return None
        if reg is not None and seat in reg:
            if reg[seat].get("retired"):
                return "retired in PROCESS §5.2 and absent from live roster"
            # Active in §5.2 but not hired here — still a bad drain target.
            return "registered in §5.2 but not on this city's live roster"
        if reg is not None:
            return "unknown id (not in §5.2, not on roster)"
        return "not on live roster (PROCESS.md unavailable)"

    products: List[str] = []
    if product:
        products = [product.strip().lower()]
    else:
        # Prefer scene stores; fall back to roster queue products.
        stores = _desk_store_slugs(desk_url)
        if stores:
            products = sorted(stores)
        else:
            products = sorted(_lane_hands_by_product(_load_roster_workers(root)).keys())

    if not products:
        return out

    desk = (desk_url or DEFAULT_DESK).rstrip("/")
    # Collect (product, ticket_id, seat, reason) samples; one finding per seat.
    by_seat: Dict[str, List[str]] = {}
    reasons: Dict[str, str] = {}
    desk_ok = False
    for prod in products:
        for status in ("backlog", "in_progress", "in_review"):
            tasks = _desk_tasks_for_status(prod, status, desk)
            if tasks is None:
                continue
            desk_ok = True
            for t in tasks:
                seat = _worker_seat_from_labels(t.get("labels"))
                if not seat:
                    continue
                why = _seat_is_bad(seat)
                if not why:
                    continue
                tid = str(t.get("id") or "?")
                by_seat.setdefault(seat, []).append("%s(%s)" % (tid, status))
                reasons[seat] = why

    if not desk_ok:
        # Desk offline — DESK-UNREACHABLE already covers; skip noise.
        return out

    for seat in sorted(by_seat.keys()):
        samples = by_seat[seat]
        preview = ", ".join(samples[:6])
        if len(samples) > 6:
            preview = preview + ", …"
        out.append(
            _finding(
                level="L0",
                code="RETIRED-SEAT",
                path="%s · worker:%s" % (desk, seat),
                status="weak",
                detail=(
                    "%d open ticket(s) seated on `worker:%s` (%s). "
                    "Re-label to the living successor (or hire that id). Sample: %s"
                    % (len(samples), seat, reasons.get(seat, "bad seat"), preview)
                ),
                fixable=False,
            )
        )
    return out


def diagnose_skill_bridges(city_root: Path) -> List[Finding]:
    """pc-960 (c): fold skills_sync.sh --check into doctor (broken/missing bridges)."""
    out: List[Finding] = []
    root = city_root.expanduser().resolve()
    try:
        from protocolcity.relocate import find_skills_sync_script, run_skills_sync
    except ImportError:
        return out

    script = find_skills_sync_script(root)
    if script is None:
        # No shelf script — export/minimal cities; not a failure mode we observed.
        return out

    # L0 shelf must exist for skills_sync to mean anything.
    l0 = root / ".agents" / "skills"
    if not l0.is_dir():
        out.append(
            _finding(
                level="L0",
                code="SKILL-BRIDGE-DRIFT",
                path=str(l0),
                status="weak",
                detail=(
                    "L0 skill shelf missing (%s) while skills_sync.sh is present — "
                    "run `blueprint found` / seed-ops, then `bash %s`"
                    % (l0, script)
                ),
                fixable=False,
            )
        )
        return out

    result = run_skills_sync(root, dry_run=True)
    rc = result.get("returncode")
    if result.get("skipped"):
        return out
    if result.get("error"):
        out.append(
            _finding(
                level="L0",
                code="SKILL-BRIDGE-DRIFT",
                path=str(script),
                status="weak",
                detail=(
                    "skills_sync --check failed to run: %s" % result.get("error")
                ),
                fixable=False,
            )
        )
        return out
    if rc == 0:
        return out

    # Drift: exit 1 from --check. Surface first lines of stdout.
    stdout = (result.get("stdout") or "").strip()
    lines = [ln for ln in stdout.splitlines() if ln.strip()][:6]
    preview = "; ".join(lines) if lines else "exit %s" % rc
    out.append(
        _finding(
            level="L0",
            code="SKILL-BRIDGE-DRIFT",
            path=str(script),
            status="weak",
            detail=(
                "Skill bridges drifted (user-home and/or project .claude/skills). "
                "Fix: `bash %s` (or `bash %s --check` to re-report). "
                "Detail: %s" % (script, script, preview[:400])
            ),
            fixable=False,
        )
    )
    return out


def diagnose_manual_step_surfaces(
    city_root: Path,
    *,
    desk_url: str = DEFAULT_DESK,
    product: Optional[str] = None,
) -> List[Finding]:
    """pc-960 aggregate: identity registry + retired seats + skill bridges."""
    root = city_root.expanduser().resolve()
    reg = load_process_identity_registry(root)
    out: List[Finding] = []
    out.extend(diagnose_identity_registry(root, registry=reg))
    out.extend(
        diagnose_retired_seats(
            root, desk_url=desk_url, product=product, registry=reg
        )
    )
    out.extend(diagnose_skill_bridges(root))
    return out


def diagnose_vendor_configs(city_root: Path) -> List[Finding]:
    """pc-966: missing / root-mismatched MCP and project vendor configs."""
    try:
        from protocolcity.vendor_config import diagnose_vendor_config_findings
    except ImportError:
        return []
    raw = diagnose_vendor_config_findings(city_root)
    out: List[Finding] = []
    for f in raw:
        out.append(
            _finding(
                level=str(f.get("level") or "L0"),
                code=str(f.get("code") or "VENDOR-CONFIG"),
                path=str(f.get("path") or ""),
                status=str(f.get("status") or "weak"),
                detail=str(f.get("detail") or ""),
                fixable=bool(f.get("fixable")),
            )
        )
    return out


def diagnose_mcp_registry(city_root: Path) -> List[Finding]:
    """pc-1078: city MCP registry SoT + generated .mcp.json drift."""
    try:
        from protocolcity.mcp_sync import diagnose_mcp_findings
    except ImportError:
        return []
    raw = diagnose_mcp_findings(city_root)
    out: List[Finding] = []
    for f in raw:
        out.append(
            _finding(
                level=str(f.get("level") or "L0"),
                code=str(f.get("code") or "MCP-REGISTRY"),
                path=str(f.get("path") or ""),
                status=str(f.get("status") or "weak"),
                detail=str(f.get("detail") or ""),
                fixable=bool(f.get("fixable")),
            )
        )
    return out


def diagnose_policy_shelf(city_root: Path) -> List[Finding]:
    """pc-1059 / pc-1063: city policy SoT + generated Claude settings drift."""
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    try:
        from protocolcity.policy_sync import (
            POLICY_REL,
            check_drift,
            policy_path,
        )
    except ImportError:
        return out

    pol = policy_path(root)
    if not pol.is_file():
        out.append(
            _finding(
                level="L0",
                code="POLICY-SHELF-MISSING",
                path=str(pol),
                status="weak",
                detail=(
                    "city policy SoT missing (%s) — plant with "
                    "`bash scripts/policy_sync.sh plant` or doctor --fix "
                    "(pc-1059 / pc-1063)" % POLICY_REL
                ),
                fixable=True,
            )
        )
        return out

    chk = check_drift(root)
    if not chk.get("ok"):
        out.append(
            _finding(
                level="L0",
                code="POLICY-MIRROR-DRIFT",
                path=str(chk.get("settings") or root / ".claude" / "settings.json"),
                status="weak",
                detail=str(
                    chk.get("detail")
                    or "Claude settings do not match .agents/policy SoT"
                ),
                fixable=True,
            )
        )
    else:
        out.append(
            _finding(
                level="L0",
                code="POLICY-SHELF",
                path=str(pol),
                status="ok",
                detail=chk.get("detail") or "policy SoT + Claude settings in sync",
            )
        )
    return out


def diagnose_secrets_shelf(city_root: Path) -> List[Finding]:
    """pc-1061 / pc-1063: secrets inventory shelf + env_required gaps."""
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    try:
        from protocolcity.secrets_inventory import (
            INVENTORY_REL,
            check_secrets,
            inventory_path,
            secrets_dir,
        )
    except ImportError:
        return out

    shelf = secrets_dir(root)
    inv = inventory_path(root)
    if not shelf.is_dir() or not inv.is_file():
        out.append(
            _finding(
                level="L0",
                code="SECRETS-SHELF-MISSING",
                path=str(inv if not inv.is_file() else shelf),
                status="weak",
                detail=(
                    "secrets inventory shelf missing (%s) — plant with "
                    "`python3 -m protocolcity.secrets_inventory plant` or "
                    "doctor --fix (pc-1061 / pc-1063)" % INVENTORY_REL
                ),
                fixable=True,
            )
        )
        return out

    out.append(
        _finding(
            level="L0",
            code="SECRETS-SHELF",
            path=str(inv),
            status="ok",
            detail="secrets inventory shelf present (names + lifecycle only)",
        )
    )

    try:
        report = check_secrets(root)
    except Exception as e:
        out.append(
            _finding(
                level="L0",
                code="SECRETS-CHECK-ERROR",
                path=str(inv),
                status="weak",
                detail="secrets check failed: %s" % e,
                fixable=False,
            )
        )
        return out

    for gap in report.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        status = str(gap.get("status") or "")
        if status == "missing":
            out.append(
                _finding(
                    level="L0",
                    code="MCP-ENV-MISSING",
                    path=str(inv),
                    status="weak",
                    detail=str(
                        gap.get("detail")
                        or "env_required unset for MCP (provision on host)"
                    ),
                    fixable=False,
                )
            )
        elif status == "expired":
            out.append(
                _finding(
                    level="L0",
                    code="SECRET-EXPIRED",
                    path=str(inv),
                    status="weak",
                    detail=str(
                        gap.get("detail") or "inventory marks secret expired"
                    ),
                    fixable=False,
                )
            )
    return out


# pc-1361 / GH #32: live teaching of retired `tk` CLI (wl-327 / wl-342 / wl-384).
# "Never `tk`" / "do not use `tk`" is current bottle law — not stale.
_TK_LIVE_RES = (
    re.compile(r"\btk\s+(create|ready|list|show|comment|status|label)\b", re.I),
    re.compile(r"MCP\s*/\s*`tk`", re.I),
    re.compile(r"MCP\s*/\s*tk\b", re.I),
    re.compile(r"Map\s*/\s*`tk`", re.I),
    re.compile(r"WorkLane\s*/\s*`tk`", re.I),
    re.compile(r"`tk`\s*/\s*MCP", re.I),
    re.compile(r"\(\s*`tk`\s*/\s*MCP\s*\)", re.I),
)

# Longest planted capture sentences first, then leftover tokens.
_TK_PHRASE_HEALS = (
    (
        "chat + MCP (`wl_create` / `tk create`) — not suite Map forms",
        "chat + MCP (`wl_create`) — not suite Map forms. Never `tk`",
    ),
    (
        "pick any chat host + MCP/`tk` for capture",
        "pick any chat host + WorkLane MCP for capture",
    ),
    (
        "on every call (`tk` / MCP)",
        "on every call (MCP)",
    ),
    (
        "chat + MCP / `tk` (any vendor)",
        "chat + WorkLane MCP (any vendor)",
    ),
    (
        "Always pass the project slug on every WorkLane / `tk` call",
        "Always pass the project slug on every WorkLane call",
    ),
    (
        "Or use Map counts + `tk ready` / MCP `wl_ready` per project.",
        "Or use Map counts + MCP `wl_ready` per project.",
    ),
    (
        "use Map/`tk` counts",
        "use Map / WorkLane API counts",
    ),
)

_TK_SEEDED_RELPATHS = (
    ".agents/skills/workspace-efficiency/SKILL.md",
    ".claude/skills/workspace-efficiency/SKILL.md",
    ".protocolcity/ops/workers/workspace-efficiency/prompt.md",
    ".agents/skills/ticket-routing/SKILL.md",
    ".claude/skills/ticket-routing/SKILL.md",
)


def _tk_teaches_live(text: str) -> bool:
    return any(rx.search(text) for rx in _TK_LIVE_RES)


def _heal_stale_retired_cli_text(text: str) -> str:
    """Replace known retired `tk` capture phrases; leave the rest of the file."""
    out = text
    for old, new in _TK_PHRASE_HEALS:
        out = out.replace(old, new)
    out = re.sub(r"MCP\s*/\s*`tk`", "WorkLane MCP", out, flags=re.I)
    out = re.sub(r"MCP\s*/\s*tk\b", "WorkLane MCP", out, flags=re.I)
    out = re.sub(r"Map\s*/\s*`tk`", "Map / WorkLane API", out, flags=re.I)
    out = re.sub(r"WorkLane\s*/\s*`tk`", "WorkLane MCP", out, flags=re.I)
    out = re.sub(r"`tk`\s*/\s*MCP", "MCP", out, flags=re.I)
    out = re.sub(r"\(\s*`tk`\s*/\s*MCP\s*\)", "(MCP)", out, flags=re.I)
    out = re.sub(r"\s*/\s*`tk create`", "", out)
    out = re.sub(r"\s*/\s*`tk ready`", "", out)
    out = re.sub(r"`tk ready`", "MCP `wl_ready`", out)
    out = re.sub(r"`tk create`", "`wl create`", out)
    out = re.sub(r"\btk\s+ready\b", "MCP wl_ready", out)
    out = re.sub(
        r"\btk\s+(create|list|show|comment|status|label)\b", r"wl \1", out
    )
    return out


def _stale_retired_cli_paths(root: Path) -> List[Path]:
    """Planted capture papers — city law, managed project law, seeded skills."""
    out: List[Path] = []
    city = root / "AGENTS.md"
    if city.is_file():
        out.append(city)
    try:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name == "local" or _likely_non_adoptable(child.name):
                continue
            if _is_foreign_consumer_folder(child):
                continue
            if not is_managed(child):
                continue
            agents = child / "AGENTS.md"
            if agents.is_file():
                out.append(agents)
    except OSError:
        pass
    for rel in _TK_SEEDED_RELPATHS:
        p = root / rel
        if p.is_file() and not p.is_symlink():
            out.append(p)
    return out


def diagnose_stale_retired_cli(city_root: Path) -> List[Finding]:
    """pc-1361: planted papers still teaching retired `tk` as a live tool."""
    root = city_root.expanduser().resolve()
    findings: List[Finding] = []
    for path in _stale_retired_cli_paths(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _tk_teaches_live(text):
            continue
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        findings.append(
            _finding(
                level="L0" if path.name == "AGENTS.md" and path.parent == root else "L1",
                code="STALE-RETIRED-CLI",
                path=str(path),
                status="weak",
                detail=(
                    "%s still teaches retired `tk` CLI (`tk create` / "
                    "`tk ready` / MCP/`tk`) — bottle templates say Never `tk`. "
                    "fix: blueprint doctor --fix (heals known planted phrases; "
                    "does not rewrite the rest of the file)"
                    % rel
                ),
                fixable=True,
            )
        )
    return findings


def heal_stale_retired_cli(city_root: Path) -> List[str]:
    """In-place known-phrase heal. Returns city-relative paths that changed."""
    root = city_root.expanduser().resolve()
    patched: List[str] = []
    for path in _stale_retired_cli_paths(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _tk_teaches_live(text):
            continue
        healed = _heal_stale_retired_cli_text(text)
        if healed == text:
            continue
        try:
            path.write_text(healed, encoding="utf-8")
        except OSError:
            continue
        try:
            patched.append(str(path.relative_to(root)))
        except ValueError:
            patched.append(str(path))
    return patched


def diagnose_seat_drift(city_root: Path) -> List[Finding]:
    """AGENT_ADOPTION.md D12 standard-seat-set drift, report-only (pc-1475):
    a provider installed on this host with no implementer seat for a
    registered project (``MISSING-SEAT`` — ``blueprint adopt --hire``
    plants it), a registered seat whose provider is no longer on this
    host (``SEAT-PROVIDER-MISSING``), and a held seat (``SEAT-HELD``).
    Never fixed here — WorkForce hire is the only roster writer.
    """
    root = city_root.expanduser().resolve()
    out: List[Finding] = []
    try:
        from overview.v1.server.operations import (
            _PROVIDER_ORDER,
            _project_seat_providers,
            detect_providers,
            project_registry,
        )
    except ImportError:
        return out
    registry = project_registry(root)
    if not registry:
        return out
    workers = _load_roster_workers(root)
    host_providers = detect_providers()
    config_cache: Dict[str, Any] = {}
    for slug, project in sorted(registry.items(), key=lambda kv: kv[1].get("name") or kv[0]):
        seats = _project_seat_providers(workers, slug, root, config_cache)
        name = project.get("name") or slug
        for provider in _PROVIDER_ORDER:
            state = seats.get(provider)
            if state == "held":
                out.append(
                    _finding(
                        level="L1",
                        code="SEAT-HELD",
                        path=slug,
                        status="weak",
                        detail="%s: %s seat held (enabled: false)" % (name, provider),
                        fixable=False,
                    )
                )
            elif state == "present" and not host_providers.get(provider):
                out.append(
                    _finding(
                        level="L1",
                        code="SEAT-PROVIDER-MISSING",
                        path=slug,
                        status="weak",
                        detail="%s: %s seat registered but %s is not installed on this host"
                        % (name, provider, provider),
                        fixable=False,
                    )
                )
            elif state is None and host_providers.get(provider):
                out.append(
                    _finding(
                        level="L1",
                        code="MISSING-SEAT",
                        path=slug,
                        status="weak",
                        detail="%s: %s installed, no seat — `blueprint adopt %s --hire`"
                        % (name, provider, project.get("folder") or slug),
                        fixable=False,
                    )
                )
    return out


def diagnose(
    city_root: Path,
    *,
    neighborhood: Optional[str] = None,
    cabinet: Optional[str] = None,  # back-compat alias (pc-320)
) -> Dict[str, Any]:
    root = city_root.expanduser().resolve()
    findings: List[Finding] = []
    findings.extend(diagnose_city(root))
    findings.extend(diagnose_stale_retired_cli(root))
    findings.extend(diagnose_registry_drift(root))
    findings.extend(diagnose_roster_paths(root))
    findings.extend(diagnose_login_service(root))
    findings.extend(diagnose_suite_service_logs(root))
    findings.extend(diagnose_legacy_citylens())
    findings.extend(diagnose_suite_stale_process())
    # pc-1105: live Cellar suite vs repo (suite_sync_ui.sh --check)
    findings.extend(diagnose_suite_sync_drift(root))
    findings.extend(diagnose_live_path_probes())
    # pc-966: vendor/MCP configs from resolved workspace root (Class D)
    findings.extend(diagnose_vendor_configs(root))
    # pc-1078: city MCP registry SoT + generated .mcp.json (BYO-MCP)
    findings.extend(diagnose_mcp_registry(root))
    # pc-1063: policy + secrets shelves (vendor-agnostic layer)
    findings.extend(diagnose_policy_shelf(root))
    findings.extend(diagnose_secrets_shelf(root))
    # pc-1475: AGENT_ADOPTION D12 standard-seat-set drift (report-only)
    findings.extend(diagnose_seat_drift(root))
    name = (neighborhood or cabinet or "").strip().strip("/") or None
    neighborhoods: List[str] = []
    if name:
        neighborhoods = [name]
        findings.extend(diagnose_neighborhood(root, name))
        # Neighborhood-scoped: only that store's unrouted ready (pc-510)
        findings.extend(
            diagnose_unrouted_ready(root, product=desk_slug(name))
        )
        # pc-960: retired seats for this store only; identity + bridges stay city-wide
        findings.extend(
            diagnose_manual_step_surfaces(root, product=desk_slug(name))
        )
    else:
        # Top-level folders: light L1 managed check (no deep walk)
        try:
            for child in sorted(root.iterdir()):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                # city-internal runtime dir — skip entirely (pc-1238)
                if child.name == "local":
                    continue
                if is_managed(child):
                    zone = _folder_zone(child)
                    detail = "%s managed" % child.name
                    if zone == "foreign":
                        detail = (
                            "%s managed · upstream-owned "
                            "(desk join; origin stays foreign)"
                            % child.name
                        )
                    findings.append(
                        _finding(
                            level="L1",
                            code="MANAGED",
                            path=str(child),
                            status="ok",
                            detail=detail,
                        )
                    )
                elif _is_foreign_consumer_folder(child):
                    findings.append(_foreign_consumer_finding(child))
                elif _likely_non_adoptable(child.name):
                    findings.append(
                        _finding(
                            level="L1",
                            code="NOT-ADOPTABLE",
                            path=str(child),
                            status="weak",
                            detail="%s looks export/archive/foreign — leave Not managed (Adopt blocked)"
                            % child.name,
                            fixable=False,
                        )
                    )
                else:
                    findings.append(
                        _finding(
                            level="L1",
                            code="NOT-MANAGED",
                            path=str(child),
                            status="weak",
                            detail="%s not managed — `doctor --neighborhood %s --fix` to Adopt"
                            % (child.name, child.name),
                            fixable=True,
                        )
                    )
                neighborhoods.append(child.name)
        except OSError:
            pass
        # pc-314: managed law without a desk store renders an empty Overview.
        # Only checkable when the desk answers — silence is not health.
        stores = _desk_store_slugs()
        managed_names = [
            f["path"] for f in findings if f.get("code") == "MANAGED"
        ]
        if stores is None:
            if managed_names:
                findings.append(
                    _finding(
                        level="L0",
                        code="DESK-UNREACHABLE",
                        path=DEFAULT_DESK,
                        status="weak",
                        detail="desk not reachable — store joins unverified "
                        "(%d managed neighborhood(s))" % len(managed_names),
                        fixable=False,
                    )
                )
        else:
            for p in managed_names:
                name = Path(p).name
                # Public export / archive clones ship AGENTS.md but never join a store
                if _likely_non_adoptable(name):
                    continue
                slug = desk_slug(name)
                if slug in stores:
                    findings.append(
                        _finding(
                            level="L1",
                            code="DESK-STORE",
                            path=p,
                            status="ok",
                            detail="%s joined to desk store `%s`" % (name, slug),
                        )
                    )
                else:
                    findings.append(
                        _finding(
                            level="L1",
                            code="MISSING-DESK-STORE",
                            path=p,
                            status="missing",
                            detail="%s managed (AGENTS.md) but no desk store `%s` — "
                            "agents must `protocolcity adopt` / doctor --fix "
                            "(or ensure_store) when founding a neighborhood; "
                            "AGENTS-only is incomplete"
                            % (name, slug),
                            fixable=True,
                        )
                    )
        # pc-510: city-wide unrouted ready (one finding per store with hands)
        findings.extend(diagnose_unrouted_ready(root))
        # pc-960: identity §5.2, retired seats, skill bridges (city-wide)
        findings.extend(diagnose_manual_step_surfaces(root))

    # pc-963 / ALWAYS_WORK §9: open_work_audit (feeds + history) for all stores
    open_work = run_open_work_for_doctor(root)
    findings.extend(diagnose_open_work_health(open_work, root))

    missing = [f for f in findings if f["status"] in ("missing", "conflict")]
    fixable = [f for f in findings if f.get("fixable")]
    # Preserve requested neighborhood scope for report (loop above may reuse `name`)
    scope_name = (neighborhood or cabinet or "").strip().strip("/") or None
    return {
        "ok": True,
        "city_root": str(root),
        "neighborhood": scope_name,
        "cabinet": scope_name,  # back-compat key (pc-320)
        "neighborhoods_seen": neighborhoods,
        "cabinets_seen": neighborhoods,  # back-compat
        "findings": findings,
        "summary": {
            "total": len(findings),
            "ok": sum(1 for f in findings if f["status"] == "ok"),
            "missing": sum(1 for f in findings if f["status"] == "missing"),
            "weak": sum(1 for f in findings if f["status"] == "weak"),
            "conflict": sum(1 for f in findings if f["status"] == "conflict"),
            "fixable": len(fixable),
        },
        "needs_attention": missing,
        "open_work": open_work,
    }


def _plant_city_companions(root: Path, *, force: bool = False) -> List[str]:
    """Plant missing L0 companions when workspace AGENTS exists. Never invent AGENTS.

    Vendor pointers are planted in ``fix()`` (pc-1063). Plants BOUNDARIES.md
    when no grants file exists under any accepted name (BOUNDARIES / PERIMETER /
    legacy).
    """
    created: List[str] = []
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return created
    edges = root / "BOUNDARIES.md"
    if (
        edges.exists()
        or (root / "PERIMETER.md").exists()
        or (root / "OFFICE_PERIMETER.md").exists()
        or (root / "CITY_EDGES.md").exists()
    ):
        return created
    try:
        body = _template("BOUNDARIES.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        try:
            body = _template("PERIMETER.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            try:
                body = _template("OFFICE_PERIMETER.md").read_text(encoding="utf-8")
            except FileNotFoundError:
                body = _template("CITY_EDGES.md").read_text(encoding="utf-8")
    edges.write_text(
        _strip_html_comments(_blank_placeholders(body)),
        encoding="utf-8",
    )
    created.append("BOUNDARIES.md")
    return created


def fix_roster_path_split(city_root: Path) -> Dict[str, Any]:
    """Merge legacy workforce/local/roster.json into canonical path (pc-437).

    Canonical: ``.protocolcity/workforce/local/roster.json``
    Legacy: ``workforce/local/roster.json``

    Merges worker keys (canonical wins on conflict), writes canonical,
    replaces legacy with a symlink (or copy if symlink fails).
    """
    root = city_root.expanduser().resolve()
    canonical = root / ".protocolcity" / "workforce" / "local" / "roster.json"
    legacy = root / "workforce" / "local" / "roster.json"
    out: Dict[str, Any] = {"ok": True, "merged": 0, "symlinked": False}

    if not legacy.is_file():
        out["ok"] = True
        out["skipped"] = "no legacy roster"
        return out

    try:
        same = canonical.is_file() and legacy.resolve() == canonical.resolve()
    except OSError:
        same = False
    if same:
        out["skipped"] = "already linked"
        return out

    def _load(p: Path) -> Dict[str, Any]:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"workers": {}}
        if not isinstance(raw, dict):
            return {"workers": {}}
        w = raw.get("workers")
        if not isinstance(w, dict):
            raw["workers"] = {}
        return raw

    can_raw = _load(canonical) if canonical.is_file() else {"workers": {}}
    leg_raw = _load(legacy)
    merged_workers = dict(leg_raw.get("workers") or {})
    # Canonical wins on key conflict
    merged_workers.update(can_raw.get("workers") or {})
    can_raw["workers"] = merged_workers
    out["merged"] = len(merged_workers)

    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        json.dumps(can_raw, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Point legacy at canonical so old scripts still work
    try:
        if legacy.is_symlink() or legacy.is_file():
            legacy.unlink()
        legacy.symlink_to(canonical)
        out["symlinked"] = True
    except OSError:
        # Windows or FS without symlink privilege — leave a small pointer file
        try:
            legacy.write_text(
                json.dumps(
                    {
                        "note": "legacy path — use .protocolcity/workforce/local/roster.json",
                        "workers": {},
                        "_redirect": str(canonical),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            out["symlinked"] = False
            out["redirect_note"] = True
        except OSError as e:
            out["ok"] = False
            out["error"] = str(e)
    return out


# L0 kits doctor --fix must plant without --force (pc-1162 / GH #22).
# --force only means "clobber existing diverged content", never "allow first plant".
_L0_PLANTABLE_CODES = frozenset(
    {
        "MISSING-VENDOR-POINTER",
        "MCP-REGISTRY-MISSING",
        "MCP-COMMAND-MISSING",
        "SECRETS-SHELF-MISSING",
        "POLICY-SHELF-MISSING",
        "VENDOR-MCP-MISSING",
        "MISSING-BOUNDARIES",
    }
)


def fix(
    city_root: Path,
    *,
    neighborhood: Optional[str] = None,
    cabinet: Optional[str] = None,  # back-compat alias (pc-320)
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    with_demo_worker: bool = False,
    allow_live_desk: bool = False,
    plant_seats: bool = False,
    hire_seats: bool = False,
    held_providers: Optional[Any] = None,
    workforce_bin: str = "workforce",
) -> Dict[str, Any]:
    """Apply safe fixes for missing papers. Returns diagnose + actions taken.

    Does not plant demo-worker stubs unless ``with_demo_worker`` (pc-489).
    Never deletes existing workers/. ``force`` rewrites existing thin stubs /
    seed files when planting is requested — it is **not** required to plant
    *missing* L0 kits (vendor pointers, MCP registry, secrets/policy shelves).
    First plant of absent files always runs under ``--fix`` alone (pc-1162).
    """
    root = city_root.expanduser().resolve()
    name = (neighborhood or cabinet or "").strip().strip("/") or None
    before = diagnose(root, neighborhood=name)
    actions: List[Dict[str, Any]] = []

    # pc-1041: neighborhood-scoped --fix must not unconditionally plant city
    # companions / rewrite roster + vendor configs. Those run only on city-wide
    # doctor --fix (no --neighborhood).
    if not name:
        roster_fix = fix_roster_path_split(root)
        if not roster_fix.get("skipped"):
            actions.append({"scope": "city", "roster_path_fix": roster_fix})

        city_created = _plant_city_companions(root, force=force)
        if city_created:
            actions.append({"scope": "city", "created": city_created})

        # pc-1056: ensure root place sentinel + upgrade legacy cities.json rows
        try:
            from protocolcity.registry import ensure_root_place

            place = ensure_root_place(root, name=root.name)
            actions.append(
                {
                    "scope": "city",
                    "place_registry": {
                        "slug": place.get("slug"),
                        "level": place.get("level"),
                        "parent": place.get("parent"),
                        "managed": place.get("managed"),
                        "path": place.get("path"),
                    },
                }
            )
        except Exception as e:
            actions.append(
                {
                    "scope": "city",
                    "place_registry": {"ok": False, "error": str(e)},
                }
            )

        # pc-966: plant missing .mcp.json + rewrite root-mismatched vendor configs.
        # Missing .mcp.json plants under --fix alone; force_mcp only rewrites an
        # existing mirror (pc-1162 — do not gate first plant on --force).
        try:
            from protocolcity.mcp_sync import _is_live_workspace_root
            from protocolcity.vendor_config import fix_vendor_configs, mcp_needs_plant

            # pc-1370: skills-path heal rewrites every old-root prefix in
            # ~/.grok (including WorkLane MCP command). Temp/pytest cities
            # must not touch the host file — same live-root gate as apply_mcp.
            vc = fix_vendor_configs(
                root,
                force_mcp=force if not mcp_needs_plant(root) else False,
                touch_grok=_is_live_workspace_root(root),
                dry_run=False,
            )
            if vc.get("actions"):
                actions.append({"scope": "city", "vendor_configs": vc})
        except Exception as e:
            actions.append(
                {
                    "scope": "city",
                    "vendor_configs": {"ok": False, "error": str(e)},
                }
            )

        # pc-1078 / pc-1063: plant missing MCP registry shelf; import baseline
        # when empty (preserve portable worklane/workforce from vendor plant);
        # then regenerate .mcp.json from SoT.
        try:
            from protocolcity.mcp_sync import (
                apply_mcp,
                import_from_mcp_json,
                list_registry_ids,
                plant_mcp_kit,
                registry_dir,
                seed_l0_mcp_manifests,
            )

            reg = registry_dir(root)
            # Missing dir OR empty registry (no manifests): plant/seed without
            # requiring --force. force only clobbers existing seed files.
            need_mcp_kit = (not reg.is_dir()) or (not list_registry_ids(root))
            if need_mcp_kit:
                planted_mcp = plant_mcp_kit(
                    root, force=force, write_mcp_json=False
                )
                actions.append({"scope": "city", "mcp_kit": planted_mcp})
            if registry_dir(root).is_dir():
                if not list_registry_ids(root) and (root / ".mcp.json").is_file():
                    imp = import_from_mcp_json(root, force=False)
                    actions.append({"scope": "city", "mcp_import": imp})
                # pc-1425 / GH #33: rewrite a dead WorkLane sibling-checkout
                # command to the bottle entrypoint without --force. Healthy
                # custom commands (including a live sibling venv) stay.
                seeded = seed_l0_mcp_manifests(
                    root,
                    force=False,
                    include_worklane=True,
                    include_workforce=False,
                )
                if seeded.get("seeded"):
                    actions.append({"scope": "city", "mcp_seed": seeded})
                # pc-1151 / pc-1150: heal Grok/Codex managed blocks too.
                # Project-only apply left doctor green while agent MCP was dead
                # (pc-1069 residual after upgrade/smoke).
                mcp = apply_mcp(root, touch_vendors=True)
                actions.append({"scope": "city", "mcp_sync": mcp})
        except FileNotFoundError as e:
            # Never silent-no-op fixable MCP plants (pc-1162).
            actions.append(
                {
                    "scope": "city",
                    "mcp_sync": {
                        "ok": False,
                        "error": "template or path missing: %s" % e,
                    },
                }
            )
        except Exception as e:
            actions.append(
                {
                    "scope": "city",
                    "mcp_sync": {"ok": False, "error": str(e)},
                }
            )

        # pc-1059 / pc-1063: plant policy kit + regenerate Claude settings mirror
        # Missing SoT plants under --fix alone (force only rewrites existing).
        try:
            from protocolcity.policy_sync import apply_policy, plant_policy_kit, policy_path

            if not policy_path(root).is_file():
                pol_plant = plant_policy_kit(
                    root, force=False, write_settings=True
                )
                actions.append({"scope": "city", "policy_kit": pol_plant})
            else:
                pol_apply = apply_policy(root)
                actions.append({"scope": "city", "policy_sync": pol_apply})
        except Exception as e:
            actions.append(
                {
                    "scope": "city",
                    "policy_sync": {"ok": False, "error": str(e)},
                }
            )

        # pc-1061 / pc-1063: plant secrets inventory shelf when missing
        # Missing shelf plants under --fix alone (pc-1162 / GH #22).
        try:
            from protocolcity.secrets_inventory import inventory_path, plant_secrets_kit

            if not inventory_path(root).is_file():
                sec = plant_secrets_kit(root, force=False)
                actions.append({"scope": "city", "secrets_kit": sec})
        except Exception as e:
            actions.append(
                {
                    "scope": "city",
                    "secrets_kit": {"ok": False, "error": str(e)},
                }
            )

        # pc-1063: plant missing thin vendor pointers (never rewrite diverged).
        # Absent pointers plant under --fix alone; never require --force.
        agents_path = root / "AGENTS.md"
        if agents_path.is_file():
            planted_ptrs: List[str] = []
            for ptr_name in ("CLAUDE.md", "GROK.md"):
                p = root / ptr_name
                if p.exists():
                    continue
                try:
                    p.write_text("@AGENTS.md\n", encoding="utf-8")
                    planted_ptrs.append(ptr_name)
                except OSError as e:
                    actions.append(
                        {
                            "scope": "city",
                            "vendor_pointers": {
                                "ok": False,
                                "error": "%s: %s" % (ptr_name, e),
                            },
                        }
                    )
            if planted_ptrs:
                actions.append(
                    {
                        "scope": "city",
                        "vendor_pointers": {"planted": planted_ptrs},
                    }
                )

        first_run = root / "FIRST_RUN.md"
        if first_run.is_file():
            first_text = first_run.read_text(encoding="utf-8", errors="replace")
            if re.search(
                r"\bprotocolcity\s+(serve|adopt|found|stop|doctor|setup)\b",
                first_text,
            ):
                from protocolcity.setup_flow import _warn_stale_first_run

                _warn_stale_first_run(root)
                actions.append({"scope": "city", "patched": "FIRST_RUN.md"})

        # pc-1361 / GH #32: heal known retired `tk` capture phrases in planted
        # AGENTS.md / seeded skills / job prompts. Phrase-level only — does
        # not rewrite citizen registry rows or custom project prose.
        tk_healed = heal_stale_retired_cli(root)
        if tk_healed:
            print(
                "\nNote: healed retired `tk` CLI teaching in %s "
                "(use WorkLane MCP / `wl`; never `tk`)."
                % ", ".join(tk_healed)
            )
            actions.append(
                {"scope": "city", "stale_retired_cli": tk_healed}
            )

    adopt_result: Optional[Dict[str, Any]] = None
    if name:
        # pc-570: prefer existing slugify-matched folder (trailing space on
        # disk); only mkdir the strip()'d name when nothing matches.
        cab = resolve_neighborhood(root, name)
        if cab is None:
            cab = root / name
            if not cab.is_dir():
                cab.mkdir(parents=True, exist_ok=True)
                actions.append({"scope": "neighborhood", "mkdir": str(cab)})
        adopt_result = adopt_neighborhood(
            root,
            cab.name if cab.is_dir() else name,
            force=force,
            with_desk=with_desk,
            desk_url=desk_url,
            sample_ticket=False,
            with_demo_worker=with_demo_worker,
            allow_live_desk=allow_live_desk,
            plant_seats=plant_seats,
            hire_seats=hire_seats,
            held_providers=held_providers,
            workforce_bin=workforce_bin,
        )
        actions.append({"scope": "neighborhood", "adopt": adopt_result})
        # pc-820: best-effort refresh hands block after adopt
        try:
            fix_papers(root, neighborhood=name, desk_url=desk_url)
        except Exception:
            pass
        # pc-487: if store exists but join file still missing, rewrite from scene
        if with_desk and desk_reachable(desk_url):
            store_map = _desk_store_map(desk_url) or {}
            slug = desk_slug(name)
            live = store_map.get(slug)
            cab_path = resolve_neighborhood(root, name) or (root / name)
            join = read_desk_join(cab_path)
            if live and (not join or str(join.get("slug") or "").lower() != slug
                         or (live.get("prefix") and join
                             and str(join.get("prefix") or "") != live.get("prefix"))):
                pref = str(live.get("prefix") or "").strip()
                if not pref:
                    import re as _re
                    pref = _re.sub(r"[^a-z0-9]", "", slug)[:4] or "app"
                write_desk_join(
                    cab_path,
                    slug=slug,
                    prefix=pref,
                    display=str(live.get("display") or name),
                    desk_url=desk_url,
                )
                actions.append(
                    {
                        "scope": "neighborhood",
                        "desk_join": str(cab_path / ".protocolcity" / "desk-join.json"),
                    }
                )
                from protocolcity.desk import soft_append_desk_identity
                if soft_append_desk_identity(
                    cab_path / "AGENTS.md", slug=slug, prefix=pref
                ):
                    actions.append(
                        {
                            "scope": "neighborhood",
                            "agents_desk_identity": True,
                        }
                    )
    else:
        # City-wide: stamp join markers for desk-joined projects (pc-427
        # migration); heal managed projects missing a desk store.
        stores: set = set()
        if with_desk and desk_reachable(desk_url):
            stores = _desk_store_slugs(desk_url) or set()
        try:
            for child in sorted(root.iterdir()):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if _likely_non_adoptable(child.name):
                    continue
                slug = desk_slug(child.name)
                # Migration: desk already has a store but pre-marker AGENTS-only.
                # pc-1359: never stamp managed onto a foreign consumer
                # (store may exist without implying code ownership).
                if (
                    has_instructions(child)
                    and not is_managed(child)
                    and slug in stores
                    and not _is_foreign_consumer_folder(child)
                ):
                    stamp_managed(child)
                    actions.append(
                        {
                            "scope": "neighborhood",
                            "stamp_managed": child.name,
                        }
                    )
                if not is_managed(child):
                    continue
                if not with_desk or not desk_reachable(desk_url):
                    continue
                if slug in stores:
                    # pc-487: store present but join file may still be missing
                    join = read_desk_join(child)
                    store_map = _desk_store_map(desk_url) or {}
                    live = store_map.get(slug) or {}
                    if not join or (
                        live.get("prefix")
                        and join
                        and str(join.get("prefix") or "") != live.get("prefix")
                    ):
                        pref = str(live.get("prefix") or "").strip()
                        if not pref:
                            import re as _re
                            pref = _re.sub(r"[^a-z0-9]", "", slug)[:4] or "app"
                        write_desk_join(
                            child,
                            slug=slug,
                            prefix=pref,
                            display=str(live.get("display") or child.name),
                            desk_url=desk_url,
                        )
                        actions.append(
                            {
                                "scope": "neighborhood",
                                "desk_join": child.name,
                            }
                        )
                    continue
                display = child.name.replace("-", " ").replace("_", " ").title()
                desk_out = bootstrap_desk(
                    slug,
                    display=display,
                    desk_url=desk_url,
                    sample_ticket=False,
                )
                if desk_out.get("ok"):
                    store = desk_out.get("store") or {}
                    product = store.get("product") or store
                    pref = ""
                    if isinstance(product, dict):
                        pref = str(product.get("prefix") or "").strip()
                    if not pref:
                        import re as _re
                        pref = _re.sub(r"[^a-z0-9]", "", slug)[:4] or "app"
                    write_desk_join(
                        child,
                        slug=slug,
                        prefix=pref,
                        display=display,
                        desk_url=desk_url,
                    )
                actions.append(
                    {
                        "scope": "neighborhood",
                        "ensure_store": slug,
                        "desk": desk_out,
                    }
                )
        except OSError:
            pass

    after = diagnose(root, neighborhood=name)

    # pc-1162: never leave silent no-ops on plantable L0 findings. Surface
    # leftovers with an explicit action so JSON/print never look empty while
    # fixable weak checks remain.
    if not name:
        leftover = sorted(
            {
                str(f.get("code") or "")
                for f in (after.get("findings") or [])
                if f.get("fixable")
                and str(f.get("code") or "") in _L0_PLANTABLE_CODES
            }
        )
        if leftover:
            hint = (
                "L0 plantable checks remain after --fix: %s. "
                "Absent files should plant under --fix alone; if content "
                "exists but is diverged, re-run with --force to clobber, or "
                "`blueprint found` when AGENTS.md is missing."
                % ", ".join(leftover)
            )
            actions.append(
                {
                    "scope": "city",
                    "unfixed_fixable": {
                        "codes": leftover,
                        "hint": hint,
                    },
                }
            )

    return {
        "ok": True,
        "city_root": str(root),
        "neighborhood": name,
        "cabinet": name,  # back-compat
        "actions": actions,
        "before": before.get("summary"),
        "after": after.get("summary"),
        "report": after,
        "adopt": adopt_result,
    }


def print_report(report: Dict[str, Any], *, json_out: bool = False) -> None:
    if json_out:
        print(json.dumps(report, indent=2))
        return
    root = report.get("city_root") or report.get("report", {}).get("city_root")
    # accept both diagnose() and fix() shapes
    data = report.get("report") if "report" in report and "findings" not in report else report
    findings = data.get("findings") or []
    summary = data.get("summary") or {}
    print("Doctor · %s" % (data.get("city_root") or root))
    n = data.get("neighborhood") or data.get("cabinet")
    if n:
        print("  project: %s" % n)
    print(
        "  summary: %(ok)s ok · %(missing)s missing · %(weak)s weak · %(conflict)s conflict · %(fixable)s fixable"
        % {
            "ok": summary.get("ok", 0),
            "missing": summary.get("missing", 0),
            "weak": summary.get("weak", 0),
            "conflict": summary.get("conflict", 0),
            "fixable": summary.get("fixable", 0),
        }
    )
    for f in findings:
        mark = {
            "ok": "✓",
            "missing": "✗",
            "weak": "·",
            "conflict": "!",
        }.get(f.get("status") or "", "?")
        fix_tag = " [fixable]" if f.get("fixable") else ""
        print(
            "  %s [%s] %s — %s%s"
            % (mark, f.get("level"), f.get("code"), f.get("detail"), fix_tag)
        )
    if report.get("actions"):
        print("  actions:")
        for a in report["actions"]:
            print("    %s" % json.dumps(a, default=str))
    # Open-work stanza (pc-814 + pc-963): counts + feeds + history
    ow = data.get("open_work") or report.get("open_work") or {}
    if ow.get("reachable"):
        rows = [r for r in (ow.get("projects") or []) if r.get("open") or r.get("ready")]
        print(
            "\nOpen work  open=%-4d  ready=%-4d  in_motion=%d"
            % (ow.get("total_open", 0), ow.get("total_ready", 0), ow.get("total_in_motion", 0))
        )
        if rows:
            print("  %-16s %5s %5s %4s %4s" % ("project", "open", "ready", "ip", "ir"))
            print("  " + "-" * 38)
            for r in rows:
                print(
                    "  %-16s %5d %5d %4d %4d"
                    % (str(r["project"])[:16], r["open"], r["ready"], r["in_progress"], r["in_review"])
                )
        else:
            print("  all stores at 0 open")
        feeds = ow.get("feeds") or {}
        if feeds:
            print("  Ready feeds by seat:")
            for prod, info in (feeds.get("by_product") or {}).items():
                if not info.get("ready_n"):
                    continue
                print("    %s: n=%s  %s" % (prod, info.get("ready_n"), info.get("by_seat")))
            sn = int(feeds.get("you_starve_n") or 0)
            print("  You-starve ready: %d" % sn)
            for t in (feeds.get("you_starve") or [])[:6]:
                print(
                    "    %s  %s"
                    % (t.get("id"), (t.get("title") or "")[:56])
                )
            if sn == 0:
                print("    (none — good)")
        hist = ow.get("history") or {}
        if hist:
            print(
                "  History worker:you: n=%s  %s"
                % (hist.get("total_worker_you"), hist.get("by_class"))
            )
        print("  Law: docs/specs/ALWAYS_WORK_PROCESS.md")
    elif "open_work" in data or "open_work" in report:
        print("\nOpen work  (suite/WL offline — start with: blueprint serve)")


# ── bp:generated block helpers (pc-820) ──────────────────────────────────────

def rewrite_generated_block(text: str, block_id: str, new_content: str) -> str:
    """Replace the content inside a bp:generated marker pair; append if absent.

    Never touches content outside the markers. If the opening marker is present
    but the closing marker is missing, returns the text unchanged to avoid
    data loss.
    """
    open_m = "<!-- bp:generated:%s -->" % block_id
    close_m = "<!-- /bp:generated:%s -->" % block_id
    oi = text.find(open_m)
    if oi == -1:
        block = "\n%s\n%s\n%s\n" % (open_m, new_content.rstrip("\n"), close_m)
        return text.rstrip("\n") + "\n" + block
    ci = text.find(close_m, oi)
    if ci == -1:
        return text  # malformed — leave untouched
    before = text[:oi]
    after = text[ci + len(close_m):]
    inner = "\n" + new_content.rstrip("\n") + "\n"
    return before + open_m + inner + close_m + after


def build_project_registry_block(desk_url: str = DEFAULT_DESK) -> str:
    """Build a project registry markdown table from desk /api/scene stores."""
    store_map = _desk_store_map(desk_url)
    if store_map is None:
        return "(desk offline — cannot build project registry)"
    if not store_map:
        return "(no stores in desk scene)"
    lines = [
        "| Folder | Store | Work orders |",
        "|---|---|---|",
    ]
    for slug, info in sorted(store_map.items()):
        display = str(info.get("display") or slug)
        prefix = str(info.get("prefix") or "").strip()
        prefix_cell = "`%s-*`" % prefix if prefix else "—"
        lines.append("| `%s/` | %s | %s |" % (slug, display, prefix_cell))
    return "\n".join(lines)


def build_hands_block(city_root: Path, store: Optional[str] = None) -> str:
    """Build a hands bullet list from roster, optionally filtered by store slug.

    Benched seats (schedule manual/none/off) are omitted — they stay on the
    roster for history/unhire trails but are not live hands (pc-1185; osp-517
    retirement parks ring/stock as schedule=manual).

    When *store* is set (L1 project AGENTS.md), only seats whose queue_url
    product/project matches that slug are listed. Empty-product rows are
    workspace jobs — they belong on L0 only, not every project dump
    (pc-1347).
    """
    workers = _load_roster_workers(city_root)
    if not workers:
        return "(no workers in roster — run `blueprint hire` to arm a hand)"
    lines: List[str] = []
    for wid, row in sorted(workers.items()):
        if not isinstance(row, dict):
            continue
        # Benched / retired-parked seats are not live hands.
        sched = str(row.get("schedule") or "").strip().lower()
        if sched in ("manual", "none", "off", "-"):
            continue
        if store:
            worker_product = _product_from_queue_url(str(row.get("queue_url") or ""))
            if not worker_product:
                worker_product = str(
                    row.get("project") or row.get("product") or ""
                ).strip().lower()
            # Empty product = workspace job (L0). Do not leak onto L1.
            if worker_product != store.lower():
                continue
        kind = str(row.get("kind") or "lane").strip().lower()
        role = str(row.get("role") or "").strip()
        model = str(row.get("model") or "").strip()
        kind_tag = "(job)" if kind in ("job", "patrol", "duty") else "(lane)"
        parts: List[str] = [wid]
        if role:
            parts += ["·", role]
        if model:
            parts.append("[%s]" % model)
        parts.append(kind_tag)
        lines.append("- " + " ".join(parts))
    if not lines:
        return "(no workers for store %s)" % (store or "any")
    return "\n".join(lines)


def _iter_managed_neighborhoods(root: Path) -> List[Path]:
    """Top-level managed project folders with AGENTS.md (city-wide papers).

    Mirrors diagnose()'s city-wide walk: skip hidden, ``local``, and
    export/archive clones. Unmanaged folders that happen to ship AGENTS.md
    stay untouched (pc-1350).
    """
    out: List[Path] = []
    try:
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name == "local":
                continue
            if _likely_non_adoptable(child.name):
                continue
            if not is_managed(child):
                continue
            if not (child / "AGENTS.md").is_file():
                continue
            out.append(child)
    except OSError:
        pass
    return out


def _rewrite_neighborhood_hands(
    root: Path,
    cab: Path,
    *,
    store: str,
    actions: List[Dict[str, Any]],
) -> None:
    """Rewrite one project's bp:generated:hands with that store's roster filter."""
    hood_agents = cab / "AGENTS.md"
    if not hood_agents.is_file():
        return
    try:
        old = hood_agents.read_text(encoding="utf-8")
    except OSError:
        old = ""
    if not old:
        return
    new_block = build_hands_block(root, store)
    new_text = rewrite_generated_block(old, "hands", new_block)
    if new_text != old:
        hood_agents.write_text(new_text, encoding="utf-8")
        actions.append(
            {
                "scope": "neighborhood",
                "patched": "AGENTS.md",
                "block": "hands",
                "store": store,
                "folder": cab.name,
            }
        )


def fix_papers(
    city_root: Path,
    *,
    neighborhood: Optional[str] = None,
    cabinet: Optional[str] = None,  # back-compat alias
    desk_url: str = DEFAULT_DESK,
) -> Dict[str, Any]:
    """Regenerate bp:generated blocks in AGENTS files from desk/roster.

    City AGENTS.md gets a ``project-registry`` block from desk /api/scene.
    Each managed project AGENTS.md gets a ``hands`` block from the roster,
    filtered to that store (pc-1347). Omit *neighborhood* to walk every
    managed project folder (pc-1350 / papers-sync). Pass a name to rewrite
    only that folder. Content outside marker pairs is never touched.
    Idempotent: identical content produces no write and an empty actions list.
    """
    root = city_root.expanduser().resolve()
    name = ((neighborhood or cabinet) or "").strip().strip("/") or None
    actions: List[Dict[str, Any]] = []

    city_agents = root / "AGENTS.md"
    if city_agents.is_file():
        try:
            old = city_agents.read_text(encoding="utf-8")
        except OSError:
            old = ""
        if old:
            new_block = build_project_registry_block(desk_url)
            # pc-1185: never clobber a live project-registry with the offline
            # placeholder when /api/scene is down (500/timeout).
            if new_block.strip().startswith("(desk offline"):
                pass
            else:
                new_text = rewrite_generated_block(old, "project-registry", new_block)
                if new_text != old:
                    city_agents.write_text(new_text, encoding="utf-8")
                    actions.append(
                        {
                            "scope": "city",
                            "patched": "AGENTS.md",
                            "block": "project-registry",
                        }
                    )

    if name:
        cab = resolve_neighborhood(root, name) or (root / name)
        if cab.is_dir():
            _rewrite_neighborhood_hands(
                root, cab, store=desk_slug(name), actions=actions
            )
    else:
        # pc-1350: city-wide papers-sync — each managed L1 dump, this store only.
        for cab in _iter_managed_neighborhoods(root):
            _rewrite_neighborhood_hands(
                root, cab, store=desk_slug(cab.name), actions=actions
            )

    return {
        "ok": True,
        "city_root": str(root),
        "neighborhood": name,
        "actions": actions,
    }
