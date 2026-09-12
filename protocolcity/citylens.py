"""The city lens — every neighborhood, one page (pc-19 v0).

The mayor's view: the L0 join no lower board owns. WorkLane renders one
store's work; WorkForce renders one machine's workers; this walks the CITY
by convention and joins what every layer already publishes:

  neighborhoods  <- ALL non-dot top-level dirs of the city root (pc-49);
                    each carries a zone: main | outskirts | foreign |
                    archive | export | hidden (pc-256 display overlay)
  store slug     <- slugify(dirname): lowercased, whitespace → hyphens (pc-313)
  work state     <- the desk's /api/admin/tasks?product=<slug>&status=...
  worker state   <- WorkForce's /api/workers (workdir joins them to hoods)
  activity       <- each neighborhood's own git log
  the brief      <- pc-30: what needs the founder (waiting decisions, stale
                    in-flight claims w/ Owner markers, dead surfaces) and
                    what shipped in the window — same joins, founder-first.
                    Also in /api/city + `snapshot` (the pc-32 reporter seam).

Zero registration: conventions ARE the API (Charter §3 / the BluePrint
thesis). Point it at any compliant city root and it lights up. Read-only —
a lens, never a copy, never a mutation.

Stdlib only. Own port (8796), own accent (cyan — distinct from WorkForce's
amber and WorkLane's paper). Env seams: CITY_ROOT, CITY_DESK, CITY_WORKFORCE,
CITY_LAT / CITY_LON (optional sky; pc-46).

Single-owner library (pc-573 / fold A of pc-572): this package module is the
only census implementation. ``tools/citylens.py`` is a thin re-export shim for
host-debug CLI. Production suite/CLI import ``protocolcity.citylens``.
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Origin owners that count as "ours" for zone classification (pc-49).
# Everything else with a remote is foreign reference material.
OWN_REMOTE_OWNERS = frozenset({"example_user", "protocolcity"})
# Cold-storage name pattern: tp-backups, tradeOS-backups, *.backups, etc.
_ARCHIVE_NAME = re.compile(r"(?i)(^|[._-])backups?$|backups?$")
# Generated export dirs (BluePrint / WorkLane / WorkForce / Charter *export
# products*) — not live sources. Hyphen/underscore/dot *before* the product
# word: ProtocolCity-WorkLane, ProtocolCity-BluePrint, ProtocolCity-WorkForce,
# ProtocolCity-Charter. Bare engine folder `worklane` / `workforce` / `charter`
# must NOT match (tp-207 host rename — was mis-zoned export → Map
# "not managed · generated").
_EXPORT_NAME = re.compile(r"(?i).+[-_.](WorkLane|WorkForce|BluePrint|Charter)$")
# Seam marker files written by export scripts (zone-before-paper, pc-200).
_EXPORT_MARKERS = frozenset({
    ".worklane-export",
    ".workforce-export",
    ".blueprint-export",
    ".charter-export",
})
# Folder basename → WorkLane store slug (tp-207 cutover complete: store is worklane).
# Legacy folder/export names still map here if needed.
_STORE_SLUG_ALIASES = {
    "ticketingprotocol": "worklane",
    "worklane": "worklane",
}


def _slugify(name):
    """Canonical folder→store slug (pc-313): lowercase, whitespace runs → "-".

    Must stay byte-identical to protocolcity/slugs.py:slugify — citylens runs
    as a standalone script and cannot import the package. Fixes the spaced-
    folder join miss ("SE Local HC" probed as "se local hc" while adopt
    created store "se-local-hc").
    """
    return "-".join(str(name).strip().lower().split())


def _desk_slug(name):
    """Folder name → letter-leading desk/store slug (pc-641).

    Must stay consistent with protocolcity/slugs.py:desk_slug — citylens
    runs as a standalone script and cannot import the package.
    """
    stripped = re.sub(r"^[\d.]+\s*", "", str(name).strip())
    result = _slugify(stripped).lstrip("-") if stripped else ""
    return result if result else _slugify(name)


def _dir_slug(d):
    """Census slug for a neighborhood dir: letter-leading canonical slug."""
    return _desk_slug(os.path.basename(d))


_LENS_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_lumber_dir() -> str:
    """Static HTML lumber path for host-debug only (API_ONLY default = off).

    Census logic lives in this package (pc-573). Port-era HTML was archived
    under ``_archive/port-era-2026-07/`` (pc-581) — no longer shipped. Prefer
    tools/ or package-local office only if a host still has them for debug.
    """
    here = _LENS_DIR
    tools = os.path.join(os.path.dirname(here), "tools")
    archive = os.path.join(
        os.path.dirname(here), "_archive", "port-era-2026-07", "tools"
    )
    # Prefer full tools lumber when present (rare host-debug restore).
    if os.path.isdir(os.path.join(tools, "office")) and os.path.isfile(
        os.path.join(tools, "map.html")
    ):
        return tools
    if os.path.isdir(os.path.join(here, "office")):
        return here
    if os.path.isdir(os.path.join(tools, "office")):
        return tools
    # Archived snapshot (not product; host archaeology only)
    if os.path.isdir(os.path.join(archive, "office")):
        return archive
    return here


_LUMBER_DIR = _resolve_lumber_dir()
PROTO_DIR = os.path.join(_LUMBER_DIR, "proto")
# The city-hall room (pc-22, cut over 2026-07-14): the STONE living scene,
# promoted from /proto/cityhall. Static HTML polling /api/city — the server
# stays a stdlib lens; the room comes alive in the browser.
CITYHALL_HTML = os.path.join(_LUMBER_DIR, "cityhall.html")
# pc-57 graduation: THE MAP fronts the room; the street-elevation plat
# survives at /plat (the pc-22 cutover convention, one click away).
MAP_HTML = os.path.join(_LUMBER_DIR, "map.html")
# Office-of-cabinets home (BluePrint default): folders as cabinets, files as paper.
# Package under tools/office/ (index.html + css/js); legacy office.html removed.
OFFICE_DIR = os.path.join(_LUMBER_DIR, "office")
OFFICE_HTML = os.path.join(OFFICE_DIR, "index.html")

DEFAULT_PORT = 8796
DESK = os.environ.get("CITY_DESK", "http://127.0.0.1:8799")
WORKFORCE = os.environ.get("CITY_WORKFORCE", "http://127.0.0.1:8797")
# ONE DOOR (pc-277): refuse citizen HTML (Office / street map lumber) and only
# serve /api/* by default. Suite :8801 is the only human front door.
# Opt out for host debug: CITYLENS_API_ONLY=0 (or CITY_API_ONLY=0).
_API_ONLY_RAW = (os.environ.get("CITYLENS_API_ONLY") or os.environ.get("CITY_API_ONLY") or "1").strip().lower()
API_ONLY = _API_ONLY_RAW not in ("0", "false", "no", "off")
# Lumber HTML on this port is not maintained product UI.

# Briefing knobs (pc-30) — env seams per the settings taxonomy (pc-31).
# CITY_STALE_MINUTES is PRESENTATION staleness: when this lens raises an
# eyebrow at a quiet claim. Behavioral staleness — when a reaper releases
# one — belongs to each lane's contract, and the two may legitimately differ.
STALE_MINUTES = int(os.environ.get("CITY_STALE_MINUTES", "90"))
BRIEF_HOURS = int(os.environ.get("CITY_BRIEF_HOURS", "24"))
DECISION_LABEL = os.environ.get("CITY_DECISION_LABEL", "needs:founder-decision")
OPEN_STATUSES = ("backlog", "in_progress", "in_review")
# Populated opportunistically by the backlog reads snapshot() already makes.
# Keys include both public task ids and store-qualified raw ids so the desk's
# transition relay can add P1 metadata without another round of HTTP calls.
_TASK_PRIORITIES: Dict[str, int] = {}

# Optional sky knobs (pc-46) — lat/lon degrees (lon east-positive). When both
# parse as floats they ride /api/city as `sky: {lat, lon}` so the plat can
# compute local sunrise/sunset + civil twilight offline. Unset → fixed buckets.
def _sky_config() -> Optional[dict]:
    lat_s, lon_s = os.environ.get("CITY_LAT"), os.environ.get("CITY_LON")
    if not lat_s or not lon_s:
        return None
    try:
        return {"lat": float(lat_s), "lon": float(lon_s)}
    except ValueError:
        return None

CSS = """
:root { --bg:#0a0d10; --panel:#10151a; --line:#1f2830; --ink:#d5dde3;
        --dim:#77828c; --cy:#4cc9f0; --ok:#4cc38a; --err:#e5534b; --amber:#f5a623; }
* { box-sizing:border-box; margin:0; }
body { background:var(--bg); color:var(--ink); font:14px/1.5 "SF Mono",
       ui-monospace, Menlo, monospace; padding:28px; max-width:1180px; margin:0 auto; }
header { display:flex; align-items:baseline; gap:14px; border-bottom:2px solid
         var(--cy); padding-bottom:14px; margin-bottom:22px; }
h1 { font-size:17px; letter-spacing:.22em; color:var(--cy); }
h1 small { color:var(--dim); letter-spacing:.08em; font-weight:normal; }
h2 { font-size:12px; letter-spacing:.18em; color:var(--dim); margin:28px 0 10px;
     text-transform:uppercase; }
table { width:100%; border-collapse:collapse; background:var(--panel); }
th { text-align:left; color:var(--dim); font-weight:normal; font-size:11px;
     letter-spacing:.1em; text-transform:uppercase; }
th, td { padding:9px 12px; border-bottom:1px solid var(--line); }
tr:hover td { background:#141b22; }
a { color:var(--cy); text-decoration:none; } a:hover { text-decoration:underline; }
.ok { color:var(--ok); } .err { color:var(--err); } .dim { color:var(--dim); }
.amber { color:var(--amber); } .cy { color:var(--cy); }
.tag { border:1px solid var(--line); border-radius:3px; padding:1px 7px;
       font-size:11px; color:var(--dim); }
.tiles { display:flex; gap:14px; margin:16px 0 6px; flex-wrap:wrap; }
.tile { background:var(--panel); border:1px solid var(--line); border-radius:4px;
        padding:12px 18px; flex:1; min-width:130px; }
.tile .n { font-size:24px; line-height:1.2; }
.tile .l { font-size:10px; letter-spacing:.14em; text-transform:uppercase;
           color:var(--dim); margin-top:2px; }
footer { margin-top:30px; color:var(--dim); font-size:11px; }
"""


_WF_WORKERS_CACHE: Dict[str, object] = {"ts": 0.0, "workers": []}
_WF_WORKERS_TTL_SEC = 90.0
# Per-slug desk backlog — Office was N×2 serial HTTP calls; cache + parallelize.
_STORE_COUNTS_CACHE: Dict[str, Dict[str, object]] = {}
# Map filed-slip / KPI deltas need sub-poll freshness (was 45s — missed animations)
_STORE_COUNTS_TTL_SEC = 6.0
# Cabinet open-work teaser — Office Desk rail needs enough rows to fill
# top-100; inside view still slices the face (Desk owns the full film).
_OPEN_WORK_CACHE: Dict[str, Dict[str, object]] = {}
_OPEN_WORK_TTL_SEC = 45.0
_OPEN_WORK_CAP = 40
_office_cache: Dict[str, object] = {"ts": 0.0, "root": "", "data": None}
_OFFICE_TTL_SEC = 6.0
# In-flight claims by Owner: identity (holding list on worker click).
_HOLDINGS_CACHE: Dict[str, object] = {"ts": 0.0, "by_owner": {}}
_HOLDINGS_TTL_SEC = 12.0
_READY_TEASER_CAP = 12
# Office package assets: /office/office.css, /office/js/util.js, …
_OFFICE_ASSET_RE = re.compile(
    r"^/office/([A-Za-z0-9][A-Za-z0-9._/-]*\.(?:css|js))$"
)


def _office_static(path: str) -> Tuple[str, str, int]:
    """Serve tools/office/* with path sanitize (no traversal)."""
    path_only = (path or "").split("?", 1)[0]
    if path_only in ("/office", "/office/"):
        try:
            with open(OFFICE_HTML, "r", encoding="utf-8") as fh:
                return fh.read(), "text/html; charset=utf-8", 200
        except OSError:
            return "<p>office missing</p>", "text/html; charset=utf-8", 404
    m = _OFFICE_ASSET_RE.match(path_only)
    if not m:
        return "<p>not found</p>", "text/html; charset=utf-8", 404
    rel = m.group(1)
    if ".." in rel.split("/"):
        return "<p>not found</p>", "text/html; charset=utf-8", 404
    root = os.path.normpath(OFFICE_DIR)
    fp = os.path.normpath(os.path.join(root, *rel.split("/")))
    if fp != root and not fp.startswith(root + os.sep):
        return "<p>not found</p>", "text/html; charset=utf-8", 404
    if not os.path.isfile(fp):
        return "<p>not found</p>", "text/html; charset=utf-8", 404
    ext = os.path.splitext(fp)[1].lower()
    ctype = {
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
    }.get(ext, "application/octet-stream")
    with open(fp, "r", encoding="utf-8") as fh:
        return fh.read(), ctype, 200


def _get_json(url: str, timeout: float = 4) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


_DESK_CENSUS_CACHE: Dict[str, object] = {
    "desk": "",
    "ts": 0.0,
    "data": None,
}
_DESK_CENSUS_LOCK = threading.Lock()
_DESK_CENSUS_TTL_SEC = 6.0
_DESK_CENSUS_WARNED = set()


def _desk_registry_products(
    desk_url: str,
    *,
    timeout: float,
) -> List[dict]:
    """Registered WorkLane stores from the light admin endpoint."""
    data = _get_json(
        desk_url.rstrip("/") + "/api/admin/products",
        timeout=timeout,
    )
    if not isinstance(data, dict):
        return []
    out = []
    seen = set()
    for raw in data.get("products") or []:
        if not isinstance(raw, dict):
            continue
        slug = str(raw.get("slug") or "").strip().lower()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append(
            {
                "slug": slug,
                "display": raw.get("display") or slug,
                "prefix": str(raw.get("prefix") or "").strip(),
            }
        )
    return out


def _desk_admin_store_row(
    desk_url: str,
    product: dict,
    *,
    timeout: float,
) -> Optional[dict]:
    """One store's exact status counts from the legacy admin task API."""
    slug = str(product.get("slug") or "").strip().lower()
    if not slug:
        return None
    query = urllib.parse.urlencode(
        {
            "product": slug,
            "status": "backlog",
            "priority": 1,
            "limit": 1,
        }
    )
    data = _get_json(
        desk_url.rstrip("/") + "/api/admin/tasks?" + query,
        timeout=timeout,
    )
    if not isinstance(data, dict) or data.get("ok") is False:
        return None
    counts = data.get("scope_counts")
    if not isinstance(counts, dict):
        return None
    columns = data.get("column_counts")
    if not isinstance(columns, dict):
        columns = {}
    try:
        return {
            "slug": slug,
            "display": product.get("display") or slug,
            "prefix": str(product.get("prefix") or "").strip(),
            "backlog": int(counts.get("backlog") or 0),
            "in_progress": int(counts.get("in_progress") or 0),
            "in_review": int(counts.get("in_review") or 0),
            "done_total": int(counts.get("done") or 0),
            "urgent_backlog": int(columns.get("backlog") or 0),
            "ready": 0,
        }
    except (TypeError, ValueError):
        return None


def _desk_registry_scene_rows(
    desk_url: str,
    products: List[dict],
    *,
    timeout: float,
) -> Dict[str, dict]:
    """Build scene-compatible store rows from legacy admin APIs in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    rows: Dict[str, dict] = {}
    summary: dict = {}
    workers = min(12, max(2, len(products) + 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        row_futures = {
            pool.submit(
                _desk_admin_store_row,
                desk_url,
                product,
                timeout=timeout,
            ): str(product.get("slug") or "").strip().lower()
            for product in products
        }
        summary_future = pool.submit(
            _get_json,
            desk_url.rstrip("/") + "/api/dev/board-summary/all-scopes",
            timeout,
        )
        for future in as_completed(row_futures):
            slug = row_futures[future]
            try:
                row = future.result()
            except Exception:
                row = None
            if slug and isinstance(row, dict):
                rows[slug] = row
        try:
            raw_summary = summary_future.result()
            if isinstance(raw_summary, dict):
                summary = raw_summary
        except Exception:
            summary = {}

    scopes = summary.get("scopes") or {}
    if not isinstance(scopes, dict) or not scopes:
        # The first summary call can queue behind the cold /api/scene build
        # that triggered this fallback. Per-store reads above give that
        # single-flight build time to finish, so one short post-fallback retry
        # usually recovers the ready counts without another scene walk.
        raw_summary = _get_json(
            desk_url.rstrip("/") + "/api/dev/board-summary/all-scopes",
            timeout=min(timeout, 2.0),
        )
        if isinstance(raw_summary, dict):
            summary = raw_summary
        scopes = summary.get("scopes") or {}
    if not isinstance(scopes, dict):
        scopes = {}
    for slug, row in rows.items():
        scope = scopes.get(slug) or {}
        if not isinstance(scope, dict):
            continue
        try:
            row["ready"] = int(scope.get("ready_count") or 0)
        except (TypeError, ValueError):
            row["ready"] = 0
    return rows


def desk_scene_compatible(
    desk_url: Optional[str] = None,
    *,
    scene_timeout: float = 1.5,
    admin_timeout: float = 8.0,
    use_cache: bool = True,
) -> dict:
    """Return a full-store WorkLane scene across old and new engine dialects.

    ``/api/scene`` is the suite's rich feed, but legacy or cold engines can
    time out or expose fewer stores there than the light
    ``/api/admin/products`` registry. When those counts diverge, rebuild only
    the store rows from the registry + per-store admin counts while preserving
    any rich attention/activity fields the scene did return.
    """
    base = (desk_url or DESK).rstrip("/")
    now = time.monotonic()
    with _DESK_CENSUS_LOCK:
        cached = _DESK_CENSUS_CACHE.get("data")
        if (
            use_cache
            and _DESK_CENSUS_CACHE.get("desk") == base
            and isinstance(cached, dict)
            and (now - float(_DESK_CENSUS_CACHE.get("ts") or 0.0))
            < _DESK_CENSUS_TTL_SEC
        ):
            return dict(cached)

        # The registry endpoint is intentionally light. Do not inherit the
        # slower per-store fallback timeout here: when Desk is down, Map must
        # fail open promptly instead of waiting the full admin budget.
        products = _desk_registry_products(
            base,
            timeout=min(admin_timeout, 2.0),
        )
        scene = _get_json(
            base + "/api/scene",
            timeout=scene_timeout,
        )
        if products and not isinstance(scene, dict):
            # A timed-out scene build continues server-side and is
            # single-flight cached by WorkLane. Give that same build one
            # bounded coalescing retry before issuing N per-store fallbacks.
            # On the host's 12-store ledger this cuts the compatibility read
            # from ~10s to the scene's ~6s while retaining the full registry.
            scene = _get_json(
                base + "/api/scene",
                timeout=max(scene_timeout, min(admin_timeout, 5.0)),
            )
        if not isinstance(scene, dict):
            scene = {}

        scene_stores = scene.get("stores") or scene.get("products") or []
        if not isinstance(scene_stores, list):
            scene_stores = []
        scene_by_slug = {}
        for raw in scene_stores:
            if not isinstance(raw, dict):
                continue
            if not any(
                key in raw
                for key in (
                    "backlog",
                    "in_progress",
                    "in_review",
                    "done",
                    "done_total",
                    "ready",
                )
            ):
                continue
            slug = str(
                raw.get("slug") or raw.get("product") or raw.get("name") or ""
            ).strip().lower()
            if slug:
                scene_by_slug[slug] = raw

        registry_slugs = [
            str(product.get("slug") or "").strip().lower()
            for product in products
            if str(product.get("slug") or "").strip()
        ]
        scene_slugs = list(scene_by_slug)
        if not registry_slugs:
            result = dict(scene) if scene else {
                "ok": False,
                "stores": [],
                "error": "WorkLane registry and scene are unreachable",
            }
        elif set(scene_slugs) == set(registry_slugs):
            result = dict(scene)
            result["stores"] = [scene_by_slug[slug] for slug in registry_slugs]
            result["census"] = {
                "source": "scene",
                "registry_store_count": len(registry_slugs),
                "scene_store_count": len(scene_slugs),
                "resolved_store_count": len(registry_slugs),
            }
        else:
            # Capture exact counts only after a rich scene actually proves
            # incomplete. Starting these heavier per-store reads first made
            # the normal cold-start path slower than WorkLane's scene build.
            admin_rows = _desk_registry_scene_rows(
                base,
                products,
                timeout=admin_timeout,
            )
            resolved = []
            missing = []
            for product in products:
                slug = str(product.get("slug") or "").strip().lower()
                row = admin_rows.get(slug) or scene_by_slug.get(slug)
                if isinstance(row, dict):
                    resolved.append(row)
                else:
                    missing.append(slug)
            warning = (
                "WorkLane census store mismatch: /api/scene reported %d "
                "store%s while /api/admin/products registered %d; using "
                "registry-backed admin counts%s."
                % (
                    len(scene_slugs),
                    "" if len(scene_slugs) == 1 else "s",
                    len(registry_slugs),
                    " (missing: %s)" % ", ".join(missing) if missing else "",
                )
            )
            result = dict(scene)
            result.update(
                {
                    "ok": len(resolved) == len(registry_slugs),
                    "stores": resolved,
                    "census": {
                        "source": "registry-admin-fallback",
                        "registry_store_count": len(registry_slugs),
                        "scene_store_count": len(scene_slugs),
                        "resolved_store_count": len(resolved),
                        "missing_stores": missing,
                        "warning": warning,
                    },
                }
            )
            warnings = result.get("warnings")
            warnings = list(warnings) if isinstance(warnings, list) else []
            warnings.append(warning)
            result["warnings"] = warnings
            warning_key = (base, len(scene_slugs), len(registry_slugs))
            if warning_key not in _DESK_CENSUS_WARNED:
                _DESK_CENSUS_WARNED.add(warning_key)
                print("warning: %s" % warning, file=sys.stderr)

        if use_cache:
            _DESK_CENSUS_CACHE.update(
                {
                    "desk": base,
                    "ts": time.monotonic(),
                    "data": result,
                }
            )
        return dict(result)


def _workforce_workers(*, timeout: Optional[int] = None) -> List[dict]:
    """Fetch WorkForce /api/workers with last-good cache.

    A slow or down Dispatch must not wipe Office Agents / cabinet hires on
    every 30s poll (empty hall → structure flicker). Prefer fresh; else cache.
    Warm cache → short timeout so Office paint stays snappy.
    """
    now = time.time()
    cached = _WF_WORKERS_CACHE.get("workers") or []
    warm = bool(cached) and (now - float(_WF_WORKERS_CACHE.get("ts") or 0)) < _WF_WORKERS_TTL_SEC
    if timeout is None:
        timeout = 2 if warm else 5
    data = _get_json(WORKFORCE + "/api/workers", timeout=timeout)
    workers = (data or {}).get("workers") if isinstance(data, dict) else None
    if isinstance(workers, list) and workers:
        _WF_WORKERS_CACHE["ts"] = now
        _WF_WORKERS_CACHE["workers"] = workers
        return workers
    if cached and (now - float(_WF_WORKERS_CACHE.get("ts") or 0)) < _WF_WORKERS_TTL_SEC * 4:
        return list(cached)  # type: ignore[arg-type]
    return list(cached) if cached else []


def _suite_package_version() -> str:
    """Installed BluePrint kit version (PyPI distro preferred or compat alias).

    When the running package is loaded from a source checkout (dogfood / PYTHONPATH
    into a git tree — not Cellar/site-packages), append ``+dogfood`` so Map chrome
    never pretends the published release is what's running (pc-832).
    """
    base = "dev"
    try:
        from protocolcity.distro import distro_version

        base = distro_version(default="dev") or "dev"
        if base == "not-installed":
            base = "dev"
    except Exception:
        base = "dev"
    try:
        import protocolcity as _pc

        src = str(Path(_pc.__file__).resolve()).replace("\\", "/").lower()
        packaged = (
            "/site-packages/" in src
            or "/dist-packages/" in src
            or "/cellar/" in src
        )
        if not packaged and not base.endswith("+dogfood"):
            return "%s+dogfood" % base
    except Exception:
        pass
    return base


def find_city_root(start: Optional[str] = None) -> str:
    """Topmost ancestor carrying AGENTS.md — the city root, by convention."""
    d = os.path.abspath(start or os.environ.get("CITY_ROOT") or os.getcwd())
    root = d if os.path.isfile(os.path.join(d, "AGENTS.md")) else ""
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
        if os.path.isfile(os.path.join(d, "AGENTS.md")):
            root = d
    if not root:
        raise SystemExit("no AGENTS.md found walking up from %s — not inside a city" % start)
    return root


def neighborhoods(root: str) -> List[str]:
    """Complete census (pc-49): every non-hidden top-level directory is a
    parcel. Root loose files are not parcels. Zoning is applied later in
    snapshot() — discovery itself is zone-blind.

    Missing/moved roots (GH #7 / pc-622) return [] — never FileNotFoundError.
    """
    out = []
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        return out
    for name in names:
        if name.startswith("."):
            continue
        d = os.path.join(root, name)
        if os.path.isdir(d):
            out.append(d)
    return out


def _git_remote_owner(path: str) -> Optional[str]:
    """Parse origin URL → GitHub-style owner. None when no git / no origin."""
    try:
        out = subprocess.run(
            ["git", "-C", path, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            return None
        url = (out.stdout or "").strip()
        if not url:
            return None
        # https://github.com/owner/repo[.git]  or  git@host:owner/repo.git
        m = re.search(r"github\.com[:/](?P<owner>[^/]+)/", url)
        if m:
            return m.group("owner")
        # generic host:owner/repo or /owner/repo.git tail
        m = re.search(r"[:/](?P<owner>[^/]+)/[^/]+?(?:\.git)?$", url)
        return m.group("owner") if m else None
    except Exception:
        return None


def _is_lane_hire(worker: dict) -> bool:
    """Lane employment incorporates a neighborhood business (STAFFING LAW).

    kind=lane (or missing kind, legacy = lane) opens Main Street.
    kind=job is municipal / depot employment and does not incorporate
    (pc-110 recommendation; ratified on pc-141).
    """
    kind = str(worker.get("kind") or "lane").lower()
    return kind == "lane"


def _staffed_by_lanes(workers: List[dict]) -> bool:
    """True when at least one lane hire's workdir joins this parcel."""
    return any(_is_lane_hire(w) for w in workers)


def _has_export_marker(path: str) -> bool:
    """True when a seam export marker sits at the parcel root (pc-200)."""
    try:
        for marker in _EXPORT_MARKERS:
            if os.path.isfile(os.path.join(path, marker)):
                return True
    except OSError:
        return False
    return False


def zone_of(path: str, staffed: bool) -> str:
    """Assign a structural zone to one parcel (pc-49; staffed criterion pc-141).

    Order is deliberate (THE STAFFING LAW, pc-110):

      archive   — name matches cold-storage backups pattern
      export    — ours, generated export (WorkLane / WorkForce / BluePrint /
                  Charter products): name pattern *or* seam marker file
      foreign   — git origin owner not in OWN_REMOTE_OWNERS (zone by remote,
                  not by AGENTS.md — worldmonitor is foreign even with law)
      main      — ours + staffed (lane hire whose workdir is this parcel)
      outskirts — ours + unstaffed (store = books/ledger only — not zone)

    The desk store remains on the parcel model as books; it must not decide
    zone alone. Hire = incorporation. Zone precedes paper (pc-200): export
    folders never classify as managed cabinets even when they ship AGENTS.md.

    Display overlay ``hidden`` (pc-256) is applied after this function — see
    ``load_hidden_slugs`` / snapshot. Never treat hidden as operational scope.
    """
    name = os.path.basename(path)
    if _ARCHIVE_NAME.search(name):
        return "archive"
    owner = _git_remote_owner(path)
    ours = owner is None or owner.lower() in OWN_REMOTE_OWNERS
    if ours and (_EXPORT_NAME.search(name) or _has_export_marker(path)):
        return "export"
    if owner and owner.lower() not in OWN_REMOTE_OWNERS:
        return "foreign"
    if staffed:
        return "main"
    return "outskirts"


def load_hidden_slugs(root: str) -> set:
    """Display-only hide list from city-root ``.protocolcity/hidden.json`` (pc-239/pc-256).

    Schema: ``{ "note": "...", "hidden": ["slug", ...] }``. Path owner-of-truth
    matches suite/serve.py ``HIDDEN_PATH`` (city root, not ``~/.protocolcity``).

    **Never-operational-scope law:** engines, exports, backups, and patrols must
    never treat this set as an exclusion — only Map/Home plot rendering does.
    Hidden folders stay in the census with ``zone: "hidden"``.
    """
    path = os.path.join(root, ".protocolcity", "hidden.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return set()
        raw = data.get("hidden") or []
        if not isinstance(raw, list):
            return set()
        return {_slugify(s) for s in raw if str(s).strip()}
    except Exception:
        return set()


def _git_last(path: str) -> Dict[str, str]:
    try:
        out = subprocess.run(
            ["git", "-C", path, "log", "-1", "--format=%ct\t%s"],
            capture_output=True, text=True, timeout=5)
        ts, subject = out.stdout.strip().split("\t", 1)
        dt = datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc)
        return {"when": dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "subject": subject}
    except Exception:
        return {"when": "", "subject": ""}


def _store_counts_fetch(slug: str) -> Optional[Dict[str, int]]:
    """Desk counts for one store; None when the desk has no such store.

    Ready probe used to gate counts — when desk is slow/wedged every store
    became null and Map badges zeroed. Prefer tasks list; treat ready as
    optional. Cached + parallelized by callers.
    """
    d = _get_json(
        "%s/api/admin/tasks?product=%s&status=backlog" % (DESK, slug),
        timeout=2,
    )
    if not d:
        return None
    # Unknown product often returns ok:false or empty scope without product match
    if d.get("ok") is False and not (d.get("scope_counts") or d.get("tasks")):
        return None
    urgent = 0
    for task in d.get("tasks") or []:
        task_id = str(task.get("id") or "")
        try:
            priority = int(task.get("priority"))
        except (TypeError, ValueError):
            continue
        if priority == 1:
            urgent += 1
        if task_id:
            _TASK_PRIORITIES[task_id] = priority
            _TASK_PRIORITIES["%s:%s" % (slug, task_id)] = priority
            _TASK_PRIORITIES["%s:%s" % (slug, task_id.rsplit("-", 1)[-1])] = priority
    sc = d.get("scope_counts") or {}
    return {"backlog": int(sc.get("backlog", 0)),
            "in_progress": int(sc.get("in_progress", 0)),
            "in_review": int(sc.get("in_review", 0)),
            "done": int(sc.get("done", 0)),
            "urgent_backlog": urgent}


def _store_counts(slug: str) -> Optional[Dict[str, int]]:
    """Counts for one store; None when the desk has no such store. Cached."""
    now = time.time()
    hit = _STORE_COUNTS_CACHE.get(slug)
    if hit and (now - float(hit.get("ts") or 0)) < _STORE_COUNTS_TTL_SEC:
        data = hit.get("data")
        return dict(data) if isinstance(data, dict) else None  # type: ignore[arg-type]
    data = _store_counts_fetch(slug)
    _STORE_COUNTS_CACHE[slug] = {"ts": now, "data": data}
    return dict(data) if isinstance(data, dict) else None


def _store_counts_many(slugs: List[str]) -> Dict[str, Optional[Dict[str, int]]]:
    """Parallel desk counts — Office foyer must not wait on serial N×HTTP."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out: Dict[str, Optional[Dict[str, int]]] = {}
    need: List[str] = []
    now = time.time()
    for slug in slugs:
        hit = _STORE_COUNTS_CACHE.get(slug)
        if hit and (now - float(hit.get("ts") or 0)) < _STORE_COUNTS_TTL_SEC:
            data = hit.get("data")
            out[slug] = dict(data) if isinstance(data, dict) else None  # type: ignore[arg-type]
        else:
            need.append(slug)
    if not need:
        return out
    workers = min(8, max(2, len(need)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_store_counts_fetch, s): s for s in need}
        for fut in as_completed(futs):
            slug = futs[fut]
            try:
                data = fut.result()
            except Exception:
                data = None
            _STORE_COUNTS_CACHE[slug] = {"ts": time.time(), "data": data}
            out[slug] = dict(data) if isinstance(data, dict) else None
    return out


def _counts_from_desk_scene(desk_scene: dict) -> Dict[str, Optional[Dict[str, int]]]:
    """Map WorkLane /api/scene store rows → citylens store shape (one HTTP).

    Light Map bootstrap used to skip all desk counts (pc-413 N× probe tax) and
    left every parcel ``store: null`` — Map painted NO STORE until soft poll
    overlaid tp-scene, which often never stuck after 0.1.15. Scene rollups are
    the same numbers soft poll uses, without N× product task probes.
    """
    out: Dict[str, Optional[Dict[str, int]]] = {}
    if not isinstance(desk_scene, dict):
        return out
    now = time.time()
    for s in desk_scene.get("stores") or []:
        if not isinstance(s, dict):
            continue
        slug = str(s.get("slug") or "").strip()
        if not slug:
            continue
        try:
            counts: Dict[str, int] = {
                "backlog": int(s.get("backlog") or 0),
                "in_progress": int(s.get("in_progress") or 0),
                "in_review": int(s.get("in_review") or 0),
                "done": int(
                    s.get("done_total")
                    if s.get("done_total") is not None
                    else (s.get("done") or 0)
                ),
                "urgent_backlog": int(s.get("urgent_backlog") or 0),
                "ready": int(s.get("ready") or 0),
            }
        except (TypeError, ValueError):
            continue
        out[slug] = counts
        out[slug.lower()] = counts
        _STORE_COUNTS_CACHE[slug] = {"ts": now, "data": counts}
    return out


def _parse_iso(iso: str) -> Optional[datetime.datetime]:
    """Tolerant ISO parse — the desk emits +00:00 offsets, this lens's own
    timestamps are Z-form; both must age correctly."""
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _ago(iso: str) -> str:
    dt = _parse_iso(iso)
    if dt is None:
        return ""
    secs = int((datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds())
    tense = "%d%s ago" if secs >= 0 else "in %d%s"
    secs = abs(secs)
    for unit, div in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= div:
            return tense % (secs // div, unit)
    return tense % (secs, "s")


def _store_tasks(slug: str, **params: object) -> List[dict]:
    """One filtered task list from the desk; [] on any failure."""
    q = "&".join("%s=%s" % (k, urllib.parse.quote(str(v)))
                 for k, v in params.items())
    d = _get_json("%s/api/admin/tasks?product=%s&%s" % (DESK, slug, q))
    return (d or {}).get("tasks") or []


def _cabinet_open_work_fetch(slug: str) -> List[dict]:
    """Capped open-task teaser for one store — id/title/status/priority only.

    Order: in_progress → in_review → backlog (doing first; Desk owns the film).
    """
    # Prefer live work over the backlog pile for the inside teaser.
    teaser_order = ("in_progress", "in_review", "backlog")
    by_status: Dict[str, List[dict]] = {s: [] for s in teaser_order}
    per_status = max(8, _OPEN_WORK_CAP)
    for status in teaser_order:
        for t in _store_tasks(slug, status=status, limit=per_status):
            if not isinstance(t, dict):
                continue
            tid = str(t.get("id") or "")
            if not tid:
                continue
            try:
                priority = int(t.get("priority"))
            except (TypeError, ValueError):
                priority = 3
            by_status[status].append({
                "id": tid,
                "title": str(t.get("title") or ""),
                "status": str(t.get("status") or status),
                "priority": priority,
                "updated_at": str(t.get("updated_at") or t.get("created_at") or ""),
            })
    ordered: List[dict] = []
    for st in teaser_order:
        bucket = by_status[st]
        bucket.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        for t in bucket:
            ordered.append({
                "id": t["id"],
                "title": t["title"],
                "status": t["status"],
                "priority": t["priority"],
                "updated_at": t.get("updated_at") or "",
            })
            if len(ordered) >= _OPEN_WORK_CAP:
                return ordered
    return ordered


def _cabinet_open_work_many(slugs: List[str]) -> Dict[str, List[dict]]:
    """Parallel open-work teasers; cached like store counts."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out: Dict[str, List[dict]] = {}
    need: List[str] = []
    now = time.time()
    for slug in slugs:
        hit = _OPEN_WORK_CACHE.get(slug)
        if hit and (now - float(hit.get("ts") or 0)) < _OPEN_WORK_TTL_SEC:
            data = hit.get("data")
            out[slug] = list(data) if isinstance(data, list) else []
        else:
            need.append(slug)
    if not need:
        return out
    workers = min(8, max(1, len(need)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_cabinet_open_work_fetch, s): s for s in need}
        for fut in as_completed(futs):
            slug = futs[fut]
            try:
                data = fut.result()
            except Exception:
                data = []
            _OPEN_WORK_CACHE[slug] = {"ts": time.time(), "data": data}
            out[slug] = list(data)
    return out


def _owner_of(task_id: str) -> str:
    """Latest `Owner:` marker in the ticket's comment trail (PROCESS.md §5) —
    the identity a reaper would respect. Only fetched for the stale set, so
    the extra GET stays O(problems), not O(tickets)."""
    d = _get_json("%s/api/admin/tasks/%s" % (DESK, task_id))
    for c in reversed(((d or {}).get("task") or {}).get("comments") or []):
        body = c.get("body", "") or ""
        if body.startswith("Owner: "):
            # Identities are slug-like; free-form comments may also open with
            # "Owner: x. <prose>" — take only the identity token.
            line = body.split("\n", 1)[0][len("Owner: "):].strip()
            return line.split()[0].rstrip(".,;:") if line else ""
    return ""


def _owner_token(raw: str) -> str:
    """Normalize an Owner: line / identity for matching (case-fold)."""
    return (raw or "").strip().split()[0].rstrip(".,;:").lower() if raw else ""


def _worker_identity_aliases(w: dict) -> List[str]:
    """All Owner: tokens that mean this worker (name, identity, succession)."""
    out: List[str] = []
    for key in ("identity", "name", "succeeds"):
        tok = _owner_token(str(w.get(key) or ""))
        if tok and tok not in out:
            out.append(tok)
    return out


def _product_from_workdir(workdir: str) -> str:
    """City convention: store slug = canonical slug of the neighborhood basename."""
    wd = os.path.abspath(workdir or "")
    if not wd:
        return ""
    return _slugify(os.path.basename(wd))


def _parse_queue_probe(queue_url: str) -> Dict[str, str]:
    """Extract product + optional label from a WorkForce ready URL."""
    if not queue_url:
        return {}
    try:
        parts = urllib.parse.urlsplit(queue_url)
        qs = urllib.parse.parse_qs(parts.query or "")
    except Exception:
        return {}
    product = (qs.get("product") or qs.get("project") or [""])[0]
    label = (qs.get("label") or [""])[0]
    out: Dict[str, str] = {}
    if product and product != "all":
        out["product"] = str(product)
    if label:
        out["label"] = str(label)
    return out


def _task_card(t: dict, *, product: str, status: str = "",
               owner: str = "") -> Dict[str, object]:
    tid = str(t.get("id") or "")
    try:
        priority = int(t.get("priority"))
    except (TypeError, ValueError):
        priority = 3
    st = str(status or t.get("status") or "")
    return {
        "id": tid,
        "title": str(t.get("title") or ""),
        "status": st,
        "priority": priority,
        "product": product,
        "owner": owner,
        "updated_at": str(t.get("updated_at") or t.get("created_at") or ""),
        "href": "%s/admin/desk?open=%s" % (
            DESK.rstrip("/"), urllib.parse.quote(tid)),
    }


def _inflight_holdings_by_owner(slugs: List[str]) -> Dict[str, List[dict]]:
    """identity → tickets currently held (in_progress + in_review w/ Owner:).

    Owner resolution is O(in-flight), not O(backlog). Cached briefly so
    Office staff-pop + snapshot polls don't hammer the desk.
    """
    now = time.time()
    if (now - float(_HOLDINGS_CACHE.get("ts") or 0)) < _HOLDINGS_TTL_SEC:
        cached = _HOLDINGS_CACHE.get("by_owner")
        if isinstance(cached, dict):
            return {k: list(v) for k, v in cached.items()}  # type: ignore[misc]

    inflight: List[Tuple[str, dict]] = []  # (product, task)
    seen_ids: set = set()
    for slug in slugs:
        if not slug:
            continue
        for status in ("in_progress", "in_review"):
            for t in _store_tasks(slug, status=status, limit=80):
                if not isinstance(t, dict):
                    continue
                tid = str(t.get("id") or "")
                if not tid or tid in seen_ids:
                    continue
                seen_ids.add(tid)
                row = dict(t)
                row["_product"] = slug
                row["_status"] = str(t.get("status") or status)
                inflight.append((slug, row))

    by_owner: Dict[str, List[dict]] = {}
    if inflight:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _resolve(item: Tuple[str, dict]) -> Tuple[str, dict, str]:
            slug, t = item
            tid = str(t.get("id") or "")
            return slug, t, _owner_of(tid)

        workers_n = min(12, max(1, len(inflight)))
        with ThreadPoolExecutor(max_workers=workers_n) as pool:
            futs = [pool.submit(_resolve, it) for it in inflight]
            for fut in as_completed(futs):
                try:
                    slug, t, owner = fut.result()
                except Exception:
                    continue
                tok = _owner_token(owner)  # "" = unowned claim
                card = _task_card(
                    t, product=slug,
                    status=str(t.get("_status") or t.get("status") or ""),
                    owner=owner,
                )
                by_owner.setdefault(tok, []).append(card)

    # Doing first, then newest within each status.
    for key, lst in list(by_owner.items()):
        doing = [x for x in lst if x.get("status") == "in_progress"]
        review = [x for x in lst if x.get("status") != "in_progress"]
        doing.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
        review.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
        by_owner[key] = doing + review

    _HOLDINGS_CACHE["ts"] = now
    _HOLDINGS_CACHE["by_owner"] = by_owner
    return {k: list(v) for k, v in by_owner.items()}


def _holdings_for_aliases(
    aliases: List[str], by_owner: Dict[str, List[dict]]
) -> List[dict]:
    held: List[dict] = []
    seen: set = set()
    for a in aliases:
        for card in by_owner.get(a, []) or []:
            tid = str(card.get("id") or "")
            if tid and tid not in seen:
                seen.add(tid)
                held.append(card)
    return held


def _ready_teaser(product: str, *, label: str = "",
                  limit: int = _READY_TEASER_CAP) -> List[dict]:
    """Top ready / backlog tickets for a store (queue-emptying view)."""
    if not product or product == "all":
        return []
    params: Dict[str, object] = {"limit": limit}
    # Prefer the ready seam (dispatchable); fall back to backlog list.
    q = urllib.parse.urlencode({
        "product": product,
        **({"label": label} if label else {}),
    })
    d = _get_json("%s/api/admin/tasks/ready?%s" % (DESK, q), timeout=3)
    tasks = (d or {}).get("tasks") if isinstance(d, dict) else None
    if not isinstance(tasks, list) or not tasks:
        if label:
            tasks = _store_tasks(product, status="backlog", label=label,
                                 limit=limit)
        else:
            tasks = _store_tasks(product, status="backlog", limit=limit)
    out: List[dict] = []
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        card = _task_card(t, product=product,
                          status=str(t.get("status") or "backlog"))
        if card["id"]:
            out.append(card)
        if len(out) >= limit:
            break
    return out


def worker_desk_load(name: str, root: Optional[str] = None) -> Dict[str, object]:
    """What a worker is holding + top of their ready queue (Office / Roster).

    Holding = in_progress/in_review whose latest Owner: matches identity,
    name, or succession id. Ready = their product ready/backlog teaser.
    """
    root = os.path.abspath(root or find_city_root())
    workers = _workforce_workers()
    match: Optional[dict] = None
    key = (name or "").strip().lower()
    for w in workers:
        aliases = _worker_identity_aliases(w)
        if key in aliases or str(w.get("name") or "").lower() == key:
            match = w
            break
    if match is None:
        # Still return holdings for bare identity (ghost claims, retired ids).
        aliases = [key] if key else []
        product = ""
        label = ""
        queue = None
        kind = ""
        display = name
    else:
        aliases = _worker_identity_aliases(match)
        probe = _parse_queue_probe(str(match.get("queue_url") or ""))
        product = probe.get("product") or _product_from_workdir(
            str(match.get("workdir") or ""))
        label = probe.get("label") or ""
        queue = match.get("queue")
        kind = str(match.get("kind") or "")
        display = match.get("display") or match.get("name") or name

    slugs = [_dir_slug(d) for d in neighborhoods(root)]
    # Always include product if known (store may exist without a hood folder).
    if product and product not in slugs:
        slugs.append(product)
    by_owner = _inflight_holdings_by_owner(slugs)
    holding = _holdings_for_aliases(aliases, by_owner)
    # Jobs often don't claim — still show unowned? No. Only their aliases.
    ready: List[dict] = []
    if product:
        ready = _ready_teaser(product, label=label)
    # Ready count: prefer WorkForce queue probe already on the worker.
    ready_count: Optional[int] = None
    if queue is not None and str(queue) not in ("—", "?", ""):
        try:
            ready_count = int(queue)
        except (TypeError, ValueError):
            ready_count = None
    if ready_count is None and product:
        counts = _store_counts(product)
        if counts:
            ready_count = int(counts.get("backlog") or 0)

    return {
        "ok": True,
        "name": (match or {}).get("name") or name,
        "display": display,
        "identity": (match or {}).get("identity") or name,
        "aliases": aliases,
        "kind": kind,
        "product": product,
        "label": label,
        "queue": queue,
        "ready_count": ready_count,
        "holding": holding,
        "holding_count": len(holding),
        "ready": ready,
        "desk": DESK,
        "claims_desk_href": (
            "%s/admin/desk?cabinet=%s&status=in_progress" % (
                DESK.rstrip("/"), urllib.parse.quote(product))
            if product else DESK.rstrip("/") + "/admin/desk"
        ),
        "ready_desk_href": (
            "%s/admin/desk?cabinet=%s&status=backlog" % (
                DESK.rstrip("/"), urllib.parse.quote(product))
            if product else DESK.rstrip("/") + "/admin/desk"
        ),
    }


def _closeout_authors(scene: Optional[dict] = None) -> Dict[str, str]:
    """task_id → closer author from the desk's /api/scene filed[] (tp-165).
    Prefer the field TP already computes; only used to fill shipped items."""
    scene = scene if scene is not None else (_get_json(DESK + "/api/scene") or {})
    out: Dict[str, str] = {}
    for f in scene.get("filed") or []:
        tid, author = f.get("id"), f.get("author")
        if tid and author:
            out[str(tid)] = str(author)
    return out


def recent_transitions(scene: dict) -> List[dict]:
    """Sanitized desk-scene relay for city-map delivery vehicles.

    No ticket descriptions or comments cross this seam. Priority is added
    from snapshot's existing backlog reads so a P1 can dispatch the map's
    ambulance; every other field already belongs to /api/scene.
    """
    out: List[dict] = []
    for raw in (scene.get("recent_transitions") or [])[:120]:
        if not isinstance(raw, dict):
            continue
        item = {
            "id": str(raw.get("id") or ""),
            "task_id": str(raw.get("task_id") or ""),
            "from_status": str(raw.get("from_status") or ""),
            "to_status": str(raw.get("to_status") or ""),
            "author": str(raw.get("author") or ""),
            "ts": str(raw.get("ts") or ""),
            "store": str(raw.get("store") or ""),
            "priority": None,
        }
        if item["to_status"] == "backlog" and item["task_id"]:
            raw_id = item["task_id"].rsplit("-", 1)[-1]
            item["priority"] = (
                _TASK_PRIORITIES.get(item["task_id"])
                or _TASK_PRIORITIES.get("%s:%s" % (item["store"], raw_id))
            )
        out.append(item)
    return out


# Markdown links in ATLAS path cells: [`label`](href) or [label](href).
_ATLAS_MD_LINK = re.compile(r"\[`?([^\]`]+)`?\]\(([^)]+)\)")
# Bare path tokens sometimes listed without a link (e.g. `../foo/` or `~/.x`).
_ATLAS_BARE_PATH = re.compile(
    r"`((?:\.\./|~/|/)[^`\n]+|[^`\n]+\.(?:md|sh|py|txt|json)|[^`\n]+/)`"
)


def parse_atlas_registered_paths(root: str) -> List[str]:
    """Parse ATLAS.md inventory path rows into a registered-paths set (pc-77).

    Read-only, names/paths only — never file contents. Resolves markdown link
    targets (and bare path tokens) relative to the ATLAS file's directory,
    then projects anything under the city root to a posix relative path.
    Used by the map to seal framed instruction files that City Hall has on
    record; absence is intentional ATLAS drift, shown unsealed in the room.
    """
    root_real = os.path.realpath(root)
    candidates = [
        os.path.join(root_real, "ProtocolCity", "ATLAS.md"),
        os.path.join(root_real, "ATLAS.md"),
    ]
    atlas_path = next((p for p in candidates if os.path.isfile(p)), None)
    if atlas_path is None:
        return []
    try:
        text = open(atlas_path, "r", encoding="utf-8").read()
    except OSError:
        return []
    atlas_dir = os.path.dirname(atlas_path)
    registered: set = set()

    def _ingest(raw: str) -> None:
        raw = (raw or "").strip()
        if not raw or raw.startswith("#") or "://" in raw:
            return
        # Drop trailing punctuation that sometimes rides path tokens.
        raw = raw.rstrip(".,;")
        if raw.startswith("~/"):
            cand = os.path.expanduser(raw)
        elif os.path.isabs(raw):
            cand = raw
        else:
            cand = os.path.join(atlas_dir, raw)
        # Logical path (no final-symlink follow) so pointer files like GROK.md
        # stay distinct from their AGENTS.md target in the registered set.
        try:
            logical = os.path.abspath(os.path.normpath(cand))
        except OSError:
            return
        # Security: if the path exists, its realpath must stay under the city
        # root (blocks symlink-out). Missing paths still register when their
        # logical location would sit under the root (ATLAS rows can lead reality).
        if os.path.lexists(logical):
            try:
                real = os.path.realpath(logical)
            except OSError:
                return
            if not _under_city_root(root_real, real):
                return
        elif not (
            logical == root_real or logical.startswith(root_real + os.sep)
        ):
            return
        try:
            rel = os.path.relpath(logical, root_real)
        except ValueError:
            return
        if rel.startswith(".."):
            return
        rel_posix = rel.replace(os.sep, "/").rstrip("/")
        if rel_posix and rel_posix != ".":
            registered.add(rel_posix)

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        # Skip markdown separator / header-ish rows.
        if re.match(r"^\|\s*:?-{2,}", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        path_cell = cells[0]
        # Header row of the inventory tables.
        if path_cell.lower() in ("path", "path ") or path_cell.lower() == "path":
            continue
        if path_cell.lower().startswith("path"):
            continue
        for _label, href in _ATLAS_MD_LINK.findall(path_cell):
            _ingest(href)
        # Bare `…` paths that are not already link targets.
        linked = {href for _l, href in _ATLAS_MD_LINK.findall(path_cell)}
        for bare in _ATLAS_BARE_PATH.findall(path_cell):
            token = bare[0] if isinstance(bare, tuple) else bare
            if token not in linked:
                _ingest(token)
    return sorted(registered)


def parse_city_edges(root: str) -> List[dict]:
    """Parse workspace-root boundaries registry table into edges[] for the map.

    Read-only, defensive: missing file → []; malformed / short rows skipped.
    Prefers citizen name ``BOUNDARIES.md``, then forever-aliases
    ``PERIMETER.md`` / ``OFFICE_PERIMETER.md`` / ``CITY_EDGES.md``. Does
    **not** read ``docs/specs/CITY_EDGES.md`` (WIDTH LAW spec only).
    Columns: from | to | kind | rule | owner. JSON keys use
    "from" (not from_) so the map can cite law without a second join.
    """
    root_real = os.path.realpath(root)
    candidates = [
        os.path.join(root_real, "BOUNDARIES.md"),
        os.path.join(root_real, "PERIMETER.md"),
        os.path.join(root_real, "OFFICE_PERIMETER.md"),
        os.path.join(root_real, "CITY_EDGES.md"),
    ]
    edges_path = next((p for p in candidates if os.path.isfile(p)), None)
    if edges_path is None:
        return []
    try:
        text = open(edges_path, "r", encoding="utf-8").read()
    except OSError:
        return []

    out: List[dict] = []
    in_registry = False
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            # Leaving a table block ends the registry capture.
            if in_registry and s.startswith("#"):
                break
            continue
        # Skip markdown separator rows.
        if re.match(r"^\|\s*:?-{2,}", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5:
            continue
        frm, to, kind, rule, owner = (
            cells[0], cells[1], cells[2], cells[3], cells[4],
        )
        # Only the machine-readable registry header arms the parser —
        # earlier prose tables (Rule/Meaning, kind legends) are ignored.
        if (frm.lower() == "from" and to.lower() == "to"
                and kind.lower() == "kind"):
            in_registry = True
            continue
        if not in_registry:
            continue
        if not frm or not kind or not rule:
            continue
        out.append({
            "from": frm,
            "to": to,
            "kind": kind,
            "rule": rule,
            "owner": owner,
        })
    return out


# Map-row family from id prefix (CITY_MAP sections A–F).
_MAP_FAMILY = {
    "F": "Filesystem",
    "W": "Work",
    "P": "People",
    "T": "Time",
    "L": "Law",
    "C": "Chrome",
}
# Markdown cell cleanup for CITY_MAP rows (bold, links, inline code).
_MD_LINK = re.compile(r"\[`?([^\]`]+)`?\]\(([^)]+)\)")
_MD_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_MD_CODE = re.compile(r"`([^`]+)`")
_MAP_ROW_ID = re.compile(r"^[FWPTLC]\d+$")


def _strip_md_cell(s: str) -> str:
    """Strip markdown bold/links/code from a table cell; keep plain text."""
    s = _MD_LINK.sub(r"\1", s or "")
    s = _MD_BOLD.sub(r"\1", s)
    s = _MD_CODE.sub(r"\1", s)
    return s.strip()


def parse_city_map(root: str) -> List[dict]:
    """Parse CITY_MAP.md THE MAPPING TABLE (sections A–F) into map_rows (pc-85).

    Read-only, defensive: missing file → []; malformed rows skipped.
    Only the six family tables under ## THE MAPPING TABLE — not the census
    or gap seed sections. Columns: # | Entity | Source fact | Object | Level | Click.
    Rows whose Object cell contains UNMAPPED get gap: true.
    """
    root_real = os.path.realpath(root)
    candidates = [
        os.path.join(root_real, "ProtocolCity", "docs", "specs", "CITY_MAP.md"),
        os.path.join(root_real, "docs", "specs", "CITY_MAP.md"),
    ]
    map_path = next((p for p in candidates if os.path.isfile(p)), None)
    if map_path is None:
        return []
    try:
        text = open(map_path, "r", encoding="utf-8").read()
    except OSError:
        return []

    out: List[dict] = []
    in_mapping = False
    for line in text.splitlines():
        s = line.strip()
        # Arm on THE MAPPING TABLE; disarm on the next major section
        # (Spot-check, THE CENSUS, etc.) — never parse gap/census tables.
        if s.startswith("## "):
            if re.search(r"THE MAPPING TABLE", s, re.I):
                in_mapping = True
                continue
            if in_mapping:
                break
            continue
        if not in_mapping or not s.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 6:
            continue
        rid = cells[0].strip()
        if not _MAP_ROW_ID.match(rid):
            continue  # header rows (#) or non-mapping lines
        family = _MAP_FAMILY.get(rid[0])
        if not family:
            continue
        entity = _strip_md_cell(cells[1])
        # cells[2] is Source fact — not relayed; keeps payload small.
        object_raw = cells[3]
        object_txt = _strip_md_cell(object_raw)
        level = _strip_md_cell(cells[4])
        click = _strip_md_cell(cells[5])
        if not object_txt and not entity:
            continue
        row = {
            "id": rid,
            "family": family,
            "entity": entity,
            "object": object_txt,
            "level": level,
            "click": click,
        }
        if "UNMAPPED" in object_raw or "UNMAPPED" in object_txt:
            row["gap"] = True
        out.append(row)
    return out


def law_census(root: str) -> List[dict]:
    """Root-first census of L0 + neighborhood law files.

    This is intentionally metadata-only. A first markdown heading is the
    maximum content exposed; the map never becomes a file-content endpoint.
    """
    candidates = [("City-wide charter", os.path.join(root, "AGENTS.md"), "L0")]
    for d in neighborhoods(root):
        candidates.append((os.path.basename(d), os.path.join(d, "AGENTS.md"),
                           "neighborhood"))
    out: List[dict] = []
    for name, path, level in candidates:
        if not os.path.isfile(path):
            continue
        heading = ""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for _ in range(40):
                    line = fh.readline()
                    if not line:
                        break
                    m = re.match(r"^#\s+(.+?)\s*$", line)
                    if m:
                        heading = m.group(1)
                        break
        except OSError:
            pass
        out.append({"name": name, "path": path, "level": level,
                    "heading": heading})
    return out


def brief(hoods: List[dict], scene: Optional[dict] = None) -> Dict[str, object]:
    """The founder's briefing (pc-30) — three joins over what the desk
    already publishes: open tickets waiting on a founder decision, in-flight
    claims gone quiet past the staleness threshold, and everything closed
    inside the brief window. Every store, one pass."""
    now = datetime.datetime.now(datetime.timezone.utc)
    decisions: List[dict] = []
    stale: List[dict] = []
    shipped: List[dict] = []
    # pc-47: closer author per sign-off — desk scene already has it (tp-165)
    authors = _closeout_authors(scene)
    for h in hoods:
        if h["store"] is None:
            continue
        slug = h["slug"]
        for t in (_store_tasks(slug, status="in_progress")
                  + _store_tasks(slug, status="in_review")):
            ts = _parse_iso(t.get("updated_at") or "")
            if ts is None:
                continue
            quiet = int((now - ts).total_seconds())
            if quiet >= STALE_MINUTES * 60:
                stale.append({"id": t["id"], "store": slug, "title": t["title"],
                              "status": t["status"], "quiet_secs": quiet,
                              "updated_at": t.get("updated_at", ""),
                              "owner": _owner_of(t["id"])})
        for t in _store_tasks(slug, label=DECISION_LABEL):
            if t.get("status") in OPEN_STATUSES:
                decisions.append({"id": t["id"], "store": slug,
                                  "title": t["title"],
                                  "priority": int(t.get("priority") or 3),
                                  "updated_at": t.get("updated_at", "")})
        for t in _store_tasks(slug, status="done", limit=50):
            ts = _parse_iso(t.get("updated_at") or "")
            if ts and (now - ts).total_seconds() <= BRIEF_HOURS * 3600:
                tid = t["id"]
                # Prefer a field already on the task if TP adds it; else scene.
                author = (t.get("author") or authors.get(str(tid), "") or "")
                shipped.append({"id": tid, "store": slug,
                                "title": t["title"],
                                "closed_at": t.get("updated_at", ""),
                                "author": author})
    decisions.sort(key=lambda d: (d["priority"], str(d["id"])))
    stale.sort(key=lambda s: -s["quiet_secs"])
    shipped.sort(key=lambda s: str(s["closed_at"]), reverse=True)
    return {"stale_minutes": STALE_MINUTES, "window_hours": BRIEF_HOURS,
            "decision_label": DECISION_LABEL, "decisions": decisions,
            "stale_inflight": stale, "shipped": shipped}


def snapshot(
    root: str,
    with_brief: bool = False,
    *,
    light: bool = False,
) -> Dict[str, object]:
    """The whole city as one JSON document — the lens's read model.

    ``light=True`` (Map bootstrap / ``/api/city?light=1``): skip founder brief
    and heavy census — folders + workers + store rollups from one desk scene.
    Soft poll still refreshes transitions/attention. Cold full snapshot was ~3s
    mostly brief fan-out (2026-07-25).

    pc-951: light still ships shallow ``root_files`` via ``root_files_census``
    (one city-root listdir). Blanking that list hid the Map L0 Instructions
    seat on first paint; deep ``root_mds`` / brief remain full-only.

    pc-1040: full snapshot also ships ``root_mds`` (same shape as project
    ``hood_root_mds``) via workspace-mode papers census — nested docs/
    .claude/ scripts/ nests, never parcel dirs. Light keeps ``root_mds=[]``.
    """
    # GH #7 / pc-622: LaunchAgent or env can still point at a renamed folder.
    # Return a stable empty city (with repair hint) — never raise FileNotFoundError.
    root_abs = os.path.abspath(os.path.expanduser(root or ""))
    if not root_abs or not os.path.isdir(root_abs):
        city_name = os.path.basename(root_abs.rstrip("/")) or "workspace"
        repair = (
            "workspace root missing (%s) — after a folder rename/move run: "
            "blueprint relocate-root --from <old-path> --to <new-path> "
            "(rewrites service, registry, roster, LaunchAgents)"
            % (root_abs or "(unset)")
        )
        empty: Dict[str, object] = {
            "ok": False,
            "root_missing": True,
            "city_root": root_abs,
            "city_name": city_name,
            # pc-1056: root place identity (Map __workspace__ ↔ __root__)
            "slug": "__root__",
            "level": 0,
            "parent": None,
            "place": {
                "slug": "__root__",
                "level": 0,
                "parent": None,
                "managed": False,
            },
            "generated_at": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "suite_version": _suite_package_version(),
            "desk": DESK,
            "workforce": WORKFORCE,
            "daemon": "unknown",
            "alerts": [repair],
            "neighborhoods": [],
            "brief": None,
            "recent_transitions": [],
            "edges": [],
            "root_files": [],
            "root_mds": [],
            "light": bool(light),
            "laws": [],
            "atlas_paths": [],
            "map_rows": [],
            "sky": None,
            "survey": None,
            "last_export_ts": None,
            "repair_hint": (
                "blueprint relocate-root --from <old> --to <new>"
            ),
        }
        return empty

    root = root_abs
    # Prefer light scene (network-free on WorkForce) — /api/workers probes every
    # queue_url against WorkLane and freezes citylens when Desk is stuck
    # (2026-07-25 Map hang: 17×3s queue probes).
    wf_scene = _get_json(WORKFORCE + "/api/scene?light=1", timeout=3) or {}
    workers: List[dict] = []
    for sec in (wf_scene.get("sectors") or []):
        if not isinstance(sec, dict):
            continue
        wd = os.path.abspath(str(sec.get("workdir") or ""))
        for w in (sec.get("workers") or []):
            if not isinstance(w, dict):
                continue
            row = dict(w)
            if wd and not row.get("workdir"):
                row["workdir"] = wd
            workers.append(row)
    if not workers:
        # Fallback: last-good /api/workers cache (may be empty)
        wf = _get_json(WORKFORCE + "/api/workers", timeout=2) or {}
        workers = wf.get("workers") or []
        wf_scene = {"daemon": (wf.get("daemon") if isinstance(wf, dict) else None)}
    by_hood: Dict[str, List[dict]] = {}
    for w in workers:
        by_hood.setdefault(os.path.abspath(w.get("workdir", "")), []).append(w)

    # pc-256: display overlay from city-root .protocolcity/hidden.json.
    # Still include every parcel; Map hides plots via zone=="hidden".
    hidden_slugs = load_hidden_slugs(root)
    dirs = list(neighborhoods(root))
    # pc-975: light Map census must list EVERY top-level parcel (managed +
    # unmanaged + export + archive). Map bootstrap / soft poll only use
    # light=1; dropping export/backups here made View Options → Unmanaged a
    # silent no-op (filter cannot paint parcels never in city.folders).
    # Heavy payload still deferred below (git / root_mds / agent_papers /
    # brief) — membership is cheap; paint cost is View-option filtered.
    # Desk counts: full path still N× parallel product probes (urgent backlog).
    # Light path: ONE /api/scene — never null every store (Map NO STORE after
    # 0.1.15 when soft-poll tp-scene missed). Skip only if desk is down.
    products: List[str] = []
    for d in dirs:
        slug = _dir_slug(d)
        products.append(_STORE_SLUG_ALIASES.get(slug, slug))
    desk_scene: dict = {}
    counts_by: Dict[str, Optional[Dict[str, int]]] = {}
    if light:
        # pc-890: Map first paint — ONE tight scene fetch, never admin rebuild
        # (compat admin path was ~1.5–2s cold). Soft poll / tp-scene fills gaps.
        desk_scene = _get_json(DESK + "/api/scene", timeout=1.0) or {}
        if not isinstance(desk_scene, dict):
            desk_scene = {}
        counts_by = (
            _counts_from_desk_scene(desk_scene)
            if desk_scene and desk_scene.get("ok") is not False
            else {}
        )
    else:
        counts_by = _store_counts_many(products)
        # Tight timeout — hung desk must not block full /api/city.
        desk_scene = _get_json(DESK + "/api/scene", timeout=0.35) or {}

    hoods = []
    for d, product in zip(dirs, products):
        slug = _dir_slug(d)
        counts = None
        if counts_by:
            counts = counts_by.get(product)
            if counts is None and product:
                counts = counts_by.get(str(product).lower())
        # pc-557: local desk-join.json means Join succeeded even when desk
        # scene counts lag — Map must not keep the "No desk store" banner.
        if counts is None:
            counts = _store_from_desk_join_file(d, product)
        ws = by_hood.get(os.path.abspath(d), [])
        # Staffed = lane hire on parcel (pc-141). Store stays books, not zone.
        staffed = _staffed_by_lanes(ws)
        zone = zone_of(d, staffed=staffed)
        flags = []
        # Flags only for open businesses (zone=main = staffed under staffing law).
        # Unstaffed + books is a HOME (outskirts), not a starving storefront.
        if zone == "main":
            if counts and counts.get("backlog", 0) > 0 and not _staffed_by_lanes(ws):
                flags.append("starving: work queued, no worker employed")
            if any(w.get("health") == "err" for w in ws):
                flags.append("worker unhealthy")
        # Display overlay after structural flags (hidden is not an operational gate).
        if slug in hidden_slugs:
            zone = "hidden"
        hoods.append({
            "name": os.path.basename(d),
            "path": d,
            "slug": slug,
            "product": product,       # desk store slug (may differ from folder slug)
            "zone": zone,             # pc-49/pc-141/pc-256: main|outskirts|foreign|archive|export|hidden
            "managed": _cabinet_managed(d),  # join marker .protocolcity/managed (pc-427)
            "store": counts,          # None = no desk presence; books, not incorporation
            "workers": ws,
            # git last is slow (N× subprocess); Map doesn't use it — full city only
            "git": {} if light else _git_last(d),
            "flags": flags,
            # pc-115: form = the estate (survey mass), bustle = the workload.
            "estate": estate_of(os.path.basename(d)),
            # Map face vs dig-in inventory (pc-890 / pc-900):
            # light first paint must NOT walk every project MD tree (was ~80KB
            # root_mds × large projects + multi-second disk). Dig-in loads
            # deep inventory via /api/hood-inventory or /api/ground.
            # pc-900: still ship shallow root_entries (one listdir) so Map
            # papers/instructions seats can paint — legend Stacks · Papers
            # was dead on light bootstrap when both lists were empty.
            "root_entries": hood_root_entries(d),
            "root_mds": [] if light else hood_root_mds(d),
            "agent_papers": [] if light else hood_agent_papers(d),
            # deep dig deferred; surface (root_entries) is always present
            "inventory_deferred": bool(light),
        })
    daemon = (
        wf_scene.get("daemon")
        if isinstance(wf_scene.get("daemon"), str)
        else (wf_scene.get("daemon") or {}).get("status")
        if isinstance(wf_scene.get("daemon"), dict)
        else "unreachable"
    ) or "unreachable"
    desk_up = any(h["store"] is not None for h in hoods)
    alerts = []
    if not desk_up:
        alerts.append("the desk (%s) answers for no store — work state is dark" % DESK)
    if daemon != "running":
        alerts.append("workforce daemon %s — nobody is being dispatched" % daemon)
    for h in hoods:
        for f in h["flags"]:
            alerts.append("%s: %s" % (h["name"], f))
    # pc-1056: root place record — align Map __workspace__ with slug __root__
    place_id: Dict[str, object] = {
        "slug": "__root__",
        "level": 0,
        "parent": None,
        "managed": _cabinet_managed(root),
    }
    try:
        from pathlib import Path as _PathLib

        from protocolcity.registry import (
            ROOT_SLUG as _ROOT_SLUG,
            place_for_path,
            root_place_identity,
        )

        root_path = _PathLib(root)
        reg_row = place_for_path(root_path)
        if reg_row:
            place_id = {
                "slug": reg_row.get("slug") or _ROOT_SLUG,
                "level": int(reg_row.get("level") or 0),
                "parent": reg_row.get("parent"),
                "managed": (
                    bool(reg_row.get("managed"))
                    if reg_row.get("managed") is not None
                    else _cabinet_managed(root)
                ),
            }
        else:
            place_id = root_place_identity(
                root_path, managed=_cabinet_managed(root)
            )
    except Exception:
        pass

    out: Dict[str, object] = {
        "ok": True,
        "root_missing": False,
        "city_root": root,
        # Live folder basename — suite mast title (GH #7: never invent empty).
        "city_name": os.path.basename(str(root).rstrip("/")) or "City",
        # pc-1056 place identity (PLACE_MODEL root sentinel)
        "slug": place_id.get("slug") or "__root__",
        "level": place_id.get("level") if place_id.get("level") is not None else 0,
        "parent": place_id.get("parent"),
        "place": place_id,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        # BluePrint package version for suite mast title (all users).
        "suite_version": _suite_package_version(),
        "desk": DESK,
        "workforce": WORKFORCE,
        "daemon": daemon,
        "alerts": alerts,
        "neighborhoods": hoods,
        "brief": brief(hoods, desk_scene) if (with_brief and not light) else None,
        # Transitions are soft-poll / theater — skip on light first paint
        "recent_transitions": (
            [] if light else (recent_transitions(desk_scene) if desk_scene else [])
        ),
        # pc-78: THE EDGE REGISTRY — Map draws PERIMETER edges.
        "edges": parse_city_edges(root),
        # pc-101 / pc-951: city-root files (Map workspace papers + L0
        # Instructions seat). Always shallow census — cheap one listdir;
        # never blank on light first paint.
        "root_files": root_files_census(root),
        # pc-1040: deep workspace papers (same shape as project root_mds).
        # Light defers — dig uses /api/hood-inventory on empty scope.
        "root_mds": [] if light else workspace_root_mds(root),
        "light": bool(light),
    }
    if not light:
        out.update({
            "laws": law_census(root),
            # pc-77: ATLAS registered-paths set (names/paths only) for framed-license seals.
            "atlas_paths": parse_atlas_registered_paths(root),
            # pc-85: THE CITY PLAN — CITY_MAP mapping rows (groupings of scene things).
            "map_rows": parse_city_map(root),
            "sky": _sky_config(),  # pc-46: optional lat/lon for local solar windows
            # pc-95: THE LAND SURVEY — status + counts (index stays in-memory / cache).
            "survey": _survey_public_summary(),
            # pc-225 / CITY_FLOW F12 — export train trigger: BluePrint marker mtime.
            "last_export_ts": _last_export_ts(root),
        })
    else:
        # Stable keys for clients that read them unconditionally
        out.update({
            "laws": [],
            "atlas_paths": [],
            "map_rows": [],
            "sky": None,
            "survey": None,
            "last_export_ts": None,
        })
    return out


def _last_export_ts(root: str) -> Optional[str]:
    """Mtime of the BluePrint export marker — changes when export_blueprint.sh runs."""
    marker = os.path.join(root, "ProtocolCity-BluePrint", ".blueprint-export")
    try:
        mtime = os.path.getmtime(marker)
        return datetime.datetime.fromtimestamp(
            mtime, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OSError, ValueError):
        return None


def _git_recent(path: str, n: int = 8) -> List[str]:
    try:
        out = subprocess.run(
            ["git", "-C", path, "log", "-%d" % n, "--format=%h %ad %s", "--date=format:%m-%d %H:%M"],
            capture_output=True, text=True, timeout=5)
        return out.stdout.strip().splitlines()
    except Exception:
        return []


def render_hood(root: str, name: str) -> Optional[str]:
    """One neighborhood — the same join, one level down. Same conventions,
    narrower lens: this page is a city-lens row, expanded."""
    snap = snapshot(root)
    hood = next((h for h in snap["neighborhoods"] if h["name"] == name), None)  # type: ignore[union-attr]
    if hood is None:
        return None
    out = ["<!doctype html><meta charset='utf-8'><title>%s · ProtocolCity — City Hall</title>"
           % html.escape(name),
           "<style>%s</style>" % CSS,
           "<header><h1>%s <small>— project · %s</small></h1></header>"
           % (html.escape(name.upper()), html.escape(hood["path"]))]

    st = hood["store"]
    out.append("<div class='tiles'>")
    if st:
        link = "%s/admin/tickets/%s" % (snap["desk"], hood["slug"])
        out.append("<div class='tile'><div class='n amber'><a href='%s'>%d</a></div>"
                   "<div class='l'>backlog</div></div>" % (html.escape(link), st["backlog"]))
        out.append("<div class='tile'><div class='n'>%d</div><div class='l'>in progress</div></div>"
                   % st["in_progress"])
        out.append("<div class='tile'><div class='n'>%d</div><div class='l'>in review</div></div>"
                   % st["in_review"])
        out.append("<div class='tile'><div class='n ok'>%d</div><div class='l'>done, ever</div></div>"
                   % st.get("done", 0))
    else:
        out.append("<div class='tile'><div class='n dim'>—</div><div class='l'>no ticket store</div></div>")
    out.append("<div class='tile'><div class='n %s'>%d</div><div class='l'>workers employed</div></div>"
               % ("cy" if hood["workers"] else "dim", len(hood["workers"])))
    out.append("</div>")

    for f in hood["flags"]:
        out.append("<p class='amber'>⚑ %s</p>" % html.escape(f))

    out.append("<h2>Workers — from the WorkForce roster</h2>")
    if hood["workers"]:
        out.append("<table><tr><th></th><th>worker</th><th>kind</th><th>schedule</th>"
                   "<th>next fire</th><th>queue</th><th>last shift</th></tr>")
        for w in hood["workers"]:
            cls = {"ok": "ok", "err": "err", "amber": "amber"}.get(w.get("health", ""), "dim")
            last = w.get("last_shift")
            last_txt = ("%s · %s" % (last["outcome"], _ago(last["ts"])) if last
                        else "never dispatched")
            out.append("<tr><td class='%s'>●</td>"
                       "<td><a href='%s/worker/%s'>%s</a></td><td><span class='tag'>%s</span></td>"
                       "<td>%s</td><td>%s</td><td>%s</td><td class='dim'>%s</td></tr>"
                       % (cls, html.escape(str(snap["workforce"])), html.escape(w["name"]),
                          html.escape(w["name"]),
                          {"lane": "worker"}.get(w.get("kind", "?"), w.get("kind", "?")),
                          html.escape(w.get("schedule", "")),
                          html.escape(_ago(w["next_fire"]).replace(" ago", "") if w.get("next_fire") else "—"),
                          html.escape(str(w.get("queue", "—"))), html.escape(last_txt)))
        out.append("</table>")
    else:
        out.append("<p class='dim'>none employed — dispatch is citizen-by-hand (allowed per RUNNER_SPEC §9)</p>")

    out.append("<h2>Recent activity — git is the feed</h2>")
    commits = _git_recent(hood["path"])
    if commits:
        out.append("<pre>%s</pre>" % html.escape("\n".join(commits)))
    else:
        out.append("<p class='dim'>not a git repository</p>")

    rules_path = os.path.join(hood["path"], "AGENTS.md")
    out.append("<h2>Project rules — AGENTS.md, rendered from disk</h2>")
    if os.path.isfile(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as fh:
                out.append("<pre>%s</pre>" % html.escape(fh.read()))
        except OSError:
            out.append("<p class='err'>unreadable</p>")
    else:
        out.append("<p class='dim'>no AGENTS.md — zone <span class='tag'>%s</span></p>"
                   % html.escape(str(hood.get("zone") or "?")))

    out.append("<p><a href='/'>&larr; projects</a></p>")
    return "".join(out)


# Snapshot cache (pc-34): the briefed snapshot costs ~25 desk calls; with the
# page and the theme prototypes all polling, a short TTL keeps the desk quiet
# and page loads instant. Threaded server + lock: last writer wins, harmless.
# Light cache is separate so Map bootstrap never waits on founder brief.
# pc-1253: single-flight compute runs on a daemon thread; handlers wait at
# most LIGHT/FULL budget then fail-open. Never stack a second snapshot().
_SNAP_TTL = float(os.environ.get("CITY_SNAP_TTL", "10"))
_SNAP_LIGHT_BUDGET_S = float(os.environ.get("CITY_SNAP_LIGHT_BUDGET", "2.5"))
_SNAP_FULL_BUDGET_S = float(os.environ.get("CITY_SNAP_FULL_BUDGET", "8"))
_SNAP_LOADING_STALE_S = float(os.environ.get("CITY_SNAP_LOADING_STALE", "60"))
_snap_cache: Dict[str, object] = {
    "ts": 0.0, "root": "", "data": None, "token": "",
    "loading": False, "loading_ts": 0.0, "waiters": [],
}
_snap_light_cache: Dict[str, object] = {
    "ts": 0.0, "root": "", "data": None, "token": "",
    "loading": False, "loading_ts": 0.0, "waiters": [],
}
_snap_lock = threading.Lock()


def _snapshot_has_any_store(data: Optional[Dict[str, object]]) -> bool:
    if not isinstance(data, dict):
        return False
    hoods = data.get("neighborhoods") or data.get("folders") or []
    if not isinstance(hoods, list):
        return False
    for h in hoods:
        if isinstance(h, dict) and h.get("store") is not None:
            return True
    return False


def _snapshot_has_shell(data: Optional[Dict[str, object]]) -> bool:
    """Last-good / fail-open is usable if Map can paint a named city."""
    if not isinstance(data, dict):
        return False
    if data.get("city_name"):
        return True
    hoods = data.get("neighborhoods") or data.get("folders") or []
    return isinstance(hoods, list) and len(hoods) > 0


def _snapshot_fail_open(
    root: str,
    *,
    light: bool = True,
    stale: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Disk-only city so Map never falls to detect-shell (pc-1253).

    Prefer last-good cache (even expired). Otherwise one listdir per parcel
    + city-root files — no desk, no WorkForce, no brief.
    """
    if _snapshot_has_shell(stale):
        out = dict(stale)  # type: ignore[arg-type]
        out["degraded"] = True
        out["stale"] = True
        out.setdefault("light", bool(light))
        return out
    root_abs = os.path.abspath(os.path.expanduser(root or ""))
    city_name = os.path.basename(root_abs.rstrip("/")) or "workspace"
    hoods: List[dict] = []
    if os.path.isdir(root_abs):
        try:
            for d in neighborhoods(root_abs):
                slug = _dir_slug(d)
                try:
                    entries = hood_root_entries(d)
                except Exception:
                    entries = []
                try:
                    managed = _cabinet_managed(d)
                except Exception:
                    managed = False
                hoods.append({
                    "name": os.path.basename(d),
                    "path": d,
                    "slug": slug,
                    "product": _STORE_SLUG_ALIASES.get(slug, slug),
                    "zone": "outskirts",
                    "managed": managed,
                    "store": None,
                    "workers": [],
                    "git": {},
                    "flags": [],
                    "root_entries": entries,
                    "root_mds": [],
                    "agent_papers": [],
                    "inventory_deferred": True,
                })
        except Exception:
            hoods = []
    try:
        root_files = root_files_census(root_abs) if os.path.isdir(root_abs) else []
    except Exception:
        root_files = []
    return {
        "ok": True,
        "degraded": True,
        "light": bool(light),
        "root_missing": not os.path.isdir(root_abs),
        "city_root": root_abs,
        "city_name": city_name,
        "slug": "__root__",
        "level": 0,
        "parent": None,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite_version": _suite_package_version(),
        "desk": DESK,
        "workforce": WORKFORCE,
        "daemon": "unknown",
        "alerts": ["city snapshot fail-open — census still computing"],
        "neighborhoods": hoods,
        "folders": hoods,
        "brief": None,
        "recent_transitions": [],
        "edges": [],
        "root_files": root_files,
        "root_mds": [],
        "laws": [],
        "atlas_paths": [],
        "map_rows": [],
        "sky": None,
        "survey": None,
        "last_export_ts": None,
    }


def _start_snapshot_worker(
    cache: Dict[str, object],
    root: str,
    *,
    light: bool,
    tok: str,
) -> None:
    """One daemon compute; waiters never call snapshot() themselves (pc-1253)."""

    def _worker() -> None:
        result: Optional[Dict[str, object]] = None
        try:
            result = snapshot(root, with_brief=not light, light=light)
        except Exception:
            result = None
        finally:
            with _snap_lock:
                if result is not None:
                    cache.update(
                        ts=time.time(),
                        root=root,
                        data=result,
                        token=tok,
                        loading=False,
                        loading_ts=0.0,
                    )
                else:
                    cache["loading"] = False
                    cache["loading_ts"] = 0.0
                done = list(cache.get("waiters") or [])
                cache["waiters"] = []
            for w in done:
                try:
                    w.set()
                except Exception:
                    pass

    threading.Thread(
        target=_worker,
        daemon=True,
        name="city-snap-light" if light else "city-snap-full",
    ).start()


def cached_snapshot(root: str, *, light: bool = False) -> Dict[str, object]:
    """Return snapshot; bust when city generation token moves (pc-420).

    Time TTL alone left Map serving pre-folder census for up to CITY_SNAP_TTL
    seconds after pulse already saw a new token.

    Light all-null (desk blip) is only kept ~1s — not full TTL — so Map folder
    open badges are not stuck dark for 10s after a stampeded scene fetch.

    pc-1211: single-flight — concurrent paints share one snapshot() compute
    instead of stampeding N parallel disk walks.

    pc-1253: compute runs on a daemon thread. Handlers wait at most
    LIGHT/FULL budget, then fail-open (stale cache or disk shell). Waiters
    never start a second unbounded snapshot() after the wait.
    """
    cache = _snap_light_cache if light else _snap_cache
    budget = _SNAP_LIGHT_BUDGET_S if light else _SNAP_FULL_BUDGET_S
    try:
        tok = str(city_generation_token(root).get("token") or "")
    except Exception:
        tok = ""
    ev = threading.Event()
    start_worker = False
    stale: Optional[Dict[str, object]] = None
    with _snap_lock:
        age = time.time() - float(cache.get("ts") or 0)
        ttl = _SNAP_TTL
        cached = cache.get("data")
        if (
            light
            and cached is not None
            and not _snapshot_has_any_store(cached)  # type: ignore[arg-type]
        ):
            ttl = 1.0
        if isinstance(cached, dict) and cache.get("root") == root:
            stale = cached
        fresh = (
            cached is not None
            and cache.get("root") == root
            and cache.get("token") == tok
            and age < ttl
        )
        if fresh:
            return cached  # type: ignore[return-value]
        loading_age = time.time() - float(cache.get("loading_ts") or 0)
        loading_stuck = bool(cache.get("loading")) and loading_age > _SNAP_LOADING_STALE_S
        if (
            cache.get("loading")
            and not loading_stuck
            and isinstance(cache.get("waiters"), list)
        ):
            cache["waiters"].append(ev)  # type: ignore[union-attr]
        else:
            cache["loading"] = True
            cache["loading_ts"] = time.time()
            cache["waiters"] = [ev]
            start_worker = True

    if start_worker:
        _start_snapshot_worker(cache, root, light=light, tok=tok)

    # Stale-while-revalidate: last-good city paints immediately.
    if _snapshot_has_shell(stale):
        return stale  # type: ignore[return-value]

    ev.wait(timeout=budget)
    with _snap_lock:
        data = cache.get("data")
        cached_tok = cache.get("token")
        cached_root = cache.get("root")
        if isinstance(data, dict) and cache.get("root") == root:
            stale = data
    if (
        isinstance(data, dict)
        and cached_root == root
        and cached_tok == tok
    ):
        return data
    return _snapshot_fail_open(
        root,
        light=light,
        stale=stale if cached_root == root else None,
    )


def invalidate_census_caches() -> None:
    """Bust snapshot + office short-TTL caches (suite manage/survey; pc-574)."""
    with _snap_lock:
        for cache in (_snap_cache, _snap_light_cache):
            done = list(cache.get("waiters") or [])
            cache.update(
                ts=0.0,
                root="",
                data=None,
                token="",
                loading=False,
                loading_ts=0.0,
                waiters=[],
            )
            for w in done:
                try:
                    w.set()
                except Exception:
                    pass
    _office_cache.update(ts=0.0, root="", data=None)
    _STORE_COUNTS_CACHE.clear()
    with _DESK_CENSUS_LOCK:
        _DESK_CENSUS_CACHE.update(desk="", ts=0.0, data=None)
        _DESK_CENSUS_WARNED.clear()


def you_attention(*, include_snoozed: bool = False) -> Dict[str, object]:
    """Desk For-You feed shaped for suite / Map (pc-574; was /api/you-attention).

    Proxies WorkLane ``/api/dev/attention`` only — no second HTTP hop through
    a citylens process. Snooze fields pass through (visible_count, snoozes).
    """
    desk_path = DESK + "/api/dev/attention"
    if include_snoozed:
        desk_path += "?include_snoozed=1"
    att = _get_json(desk_path) or {}
    items = att.get("items") if isinstance(att.get("items"), list) else []
    snoozes = att.get("snoozes") if isinstance(att.get("snoozes"), list) else []
    try:
        count = int(
            att.get("count") if att.get("count") is not None else len(items) or 0
        )
    except (TypeError, ValueError):
        count = len(items)
    try:
        visible = int(
            att.get("visible_count")
            if att.get("visible_count") is not None
            else count
        )
    except (TypeError, ValueError):
        visible = count
    try:
        snoozed_n = int(att.get("snoozed_count") or 0)
    except (TypeError, ValueError):
        snoozed_n = 0
    return {
        "ok": bool(att.get("ok", bool(att))),
        "count": count,
        "visible_count": visible,
        "snoozed_count": snoozed_n,
        "items": items,
        "snoozes": snoozes,
        "updated_at": att.get("updated_at") or "",
    }


def city_generation_token(root: str) -> Dict[str, object]:
    """Cheap freshness token for suite pulse bus (pc-279 / LIVE-B3 / pc-420).

    Inputs that should move Map without hard refresh:
      - root law / hidden
      - every top-level name (new folder or root .md)
      - per-project shallow: AGENTS.md, child count, root .md mtimes
      - roster + ops kit (hire / seed-ops)

    Honest limits: deep nested trees (node_modules depth) are NOT walked —
    only top-level parcels + their immediate children / root papers. Deep
    resurvey remains Settings → resurvey / survey cache.
    """
    parts: List[str] = []
    root_real = os.path.realpath(root)
    watch = [
        "AGENTS.md",
        "BOUNDARIES.md",
        "PERIMETER.md",
        "CITY_EDGES.md",
        "CLAUDE.md",
        "GROK.md",
        os.path.join(".protocolcity", "hidden.json"),
        os.path.join(".protocolcity", "workforce", "local", "roster.json"),
    ]
    for rel in watch:
        p = os.path.join(root_real, rel)
        try:
            st = os.stat(p)
            parts.append("%s:%d:%d" % (rel, int(st.st_mtime), int(st.st_size)))
        except OSError:
            parts.append("%s:0" % rel)
    n_dirs = 0
    n_root_files = 0
    try:
        for name in sorted(os.listdir(root_real), key=str.lower):
            if name.startswith("."):
                continue
            p = os.path.join(root_real, name)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if os.path.isdir(p):
                n_dirs += 1
                # Shallow project dig-in signal (papers + membership)
                n_md = 0
                max_md_m = 0
                n_child = 0
                has_agents = 0
                try:
                    for child in os.listdir(p):
                        if child.startswith("."):
                            continue
                        n_child += 1
                        cp = os.path.join(p, child)
                        if child == "AGENTS.md":
                            has_agents = 1
                        if child.endswith(".md") and os.path.isfile(cp):
                            n_md += 1
                            try:
                                max_md_m = max(max_md_m, int(os.path.getmtime(cp)))
                            except OSError:
                                pass
                except OSError:
                    pass
                parts.append(
                    "d:%s:%d:%d:a%d:md%d:%d:ch%d"
                    % (
                        name,
                        int(st.st_mtime),
                        int(st.st_size),
                        has_agents,
                        n_md,
                        max_md_m,
                        n_child,
                    )
                )
            else:
                n_root_files += 1
                parts.append(
                    "f:%s:%d:%d" % (name, int(st.st_mtime), int(st.st_size))
                )
    except OSError:
        pass
    parts.append("counts:%d:%d" % (n_dirs, n_root_files))
    raw = "|".join(parts)
    token = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return {
        "token": token,
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "dirs": n_dirs,
        "root_files": n_root_files,
    }


def _under_city_root(root_real: str, cand_real: str) -> bool:
    """True when cand_real is the city root or a realpath descendant of it."""
    if cand_real == root_real:
        return True
    return cand_real.startswith(root_real + os.sep)


def resolve_open_path(root: str, requested: str) -> Optional[str]:
    """Allow-list for POST /api/open (pc-76): city root + ANY realpath
    descendant. Resolve via realpath; reject escapes and missing paths.
    Returns the realpath to open, or None when the request is out of bounds."""
    if not requested or not isinstance(requested, str):
        return None
    root_real = os.path.realpath(root)
    raw = requested.strip()
    if not raw:
        return None
    if os.path.isabs(raw):
        cand = os.path.realpath(raw)
    else:
        cand = os.path.realpath(os.path.join(root_real, raw))
    if not os.path.exists(cand):
        return None
    if not _under_city_root(root_real, cand):
        return None
    return cand


def parse_parcel_rel(raw: str) -> Optional[List[str]]:
    """Split a /api/parcel/... path into safe relative segments.

    Rejects empty input, '.'/'..' segments (escape attempts), NUL, and any
    segment that itself embeds a path separator. Dotfile-named segments are
    allowed through here so the caller can 404 them as missing/hidden —
    listing still never surfaces names starting with '.'.
    Returns None when the request is structurally bad (caller → 403).
    """
    if not raw or not isinstance(raw, str):
        return None
    parts: List[str] = []
    for piece in raw.split("/"):
        if piece == "":
            continue
        seg = urllib.parse.unquote(piece)
        if not seg or seg in (".", "..") or "\x00" in seg:
            return None
        if os.sep in seg or (os.altsep and os.altsep in seg):
            return None
        parts.append(seg)
    return parts if parts else None


def resolve_city_relpath(
    root: str, segments: List[str], *, must_dir: bool = True
) -> tuple:
    """Resolve nested relative segments against the city root via realpath.

    Returns (realpath, rel_posix, err) where err is None on success, 403 when
    the resolved path escapes the root (including symlink-out), or 404 when
    the target is missing / not a directory (when must_dir) / a hidden
    (dotfile) segment appears in the request.
    """
    if not segments:
        return None, "", 404
    # Dotfile segments stay hidden — treat as missing, never as a room.
    if any(s.startswith(".") for s in segments):
        return None, "", 404
    root_real = os.path.realpath(root)
    joined = os.path.join(root_real, *segments)
    try:
        cand = os.path.realpath(joined)
    except OSError:
        return None, "", 404
    if not _under_city_root(root_real, cand):
        return None, "", 403
    if not os.path.exists(cand):
        return None, "", 404
    if must_dir and not os.path.isdir(cand):
        return None, "", 404
    rel = "/".join(segments)
    return cand, rel, None


def _resolve_neighborhood_dir(root: str, name: str) -> Optional[str]:
    """Single non-hidden city-root child path, or None when unknown."""
    segs = parse_parcel_rel(name)
    if segs is None or len(segs) != 1:
        return None
    path, _rel, err = resolve_city_relpath(root, segs, must_dir=True)
    return path if err is None else None


def neighborhood_orders(root: str, name: str) -> Optional[Dict[str, object]]:
    """Read-only desk relay for one neighborhood's order book (pc-74).

    Open tasks (backlog / in_progress / in_review) + recent signed (done)
    work with authors. Caps: 25 open, 15 signed. No bodies or descriptions.
    Returns None when the neighborhood dir is unknown (caller → 404).
    """
    path = _resolve_neighborhood_dir(root, name)
    if path is None:
        return None
    slug = _dir_slug(path)
    open_tasks: List[dict] = []
    for status in OPEN_STATUSES:
        for t in _store_tasks(slug, status=status, limit=50):
            if not isinstance(t, dict):
                continue
            tid = str(t.get("id") or "")
            if not tid:
                continue
            open_tasks.append({
                "id": tid,
                "title": str(t.get("title") or ""),
                "status": str(t.get("status") or status),
                "created_at": str(t.get("created_at") or ""),
                "updated_at": str(t.get("updated_at") or ""),
            })
    open_tasks.sort(
        key=lambda x: x.get("updated_at") or x.get("created_at") or "",
        reverse=True)
    open_tasks = open_tasks[:25]

    # Same join the brief uses for shipped: desk done list + scene filed[] authors.
    scene = _get_json(DESK + "/api/scene") or {}
    authors = _closeout_authors(scene)
    signed: List[dict] = []
    for t in _store_tasks(slug, status="done", limit=50):
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "")
        if not tid:
            continue
        author = str(t.get("author") or authors.get(tid, "") or "")
        signed.append({
            "id": tid,
            "title": str(t.get("title") or ""),
            "author": author,
            "signed_at": str(t.get("updated_at") or ""),
        })
    signed.sort(key=lambda x: x.get("signed_at") or "", reverse=True)
    signed = signed[:15]

    return {
        "name": os.path.basename(path),
        "slug": slug,
        "open": open_tasks,
        "signed": signed,
    }


def parcel_listing(root: str, rel: str):
    """Shallow listing of one directory under the city root (pc-50 / pc-76).

    Accepts nested relative paths (tradeOS/core/…). No file contents — names,
    kinds, and per-subdir entry counts only. Dotfiles stay hidden in children.
    Returns (listing_dict, None) on success, or (None, http_status) on reject
    (403 escape / symlink-out, 404 missing or hidden).
    """
    segs = parse_parcel_rel(rel)
    if segs is None:
        return None, 403
    path, rel_posix, err = resolve_city_relpath(root, segs, must_dir=True)
    if err is not None:
        return None, err
    children: List[dict] = []
    dir_count = file_count = 0
    try:
        names = sorted(os.listdir(path), key=str.lower)
    except OSError:
        return None, 404
    for n in names:
        if n.startswith("."):
            continue
        p = os.path.join(path, n)
        try:
            is_dir = os.path.isdir(p)
        except OSError:
            continue
        if is_dir:
            dir_count += 1
            try:
                entries = sum(1 for x in os.listdir(p) if not x.startswith("."))
            except OSError:
                entries = 0
            # pc-86: founded = own AGENTS.md (case exact); cheap stat only.
            founded = os.path.isfile(os.path.join(p, "AGENTS.md"))
            children.append({
                "name": n, "kind": "dir", "entries": entries,
                "founded": founded,
            })
        else:
            file_count += 1
            child: Dict[str, object] = {
                "name": n, "kind": "file", "ftype": file_type(n),
            }
            if is_instruction_class(n):
                child["instruction"] = True
            child.update(paper_flags(p, n))
            children.append(child)
    # Room's own founding status (same rule as children).
    self_founded = os.path.isfile(os.path.join(path, "AGENTS.md"))
    return {
        "name": segs[-1],
        "rel": rel_posix,
        "path": path,
        "depth": len(segs),
        "dir_count": dir_count,
        "file_count": file_count,
        "founded": self_founded,
        "children": children,
    }, None


# ─── THE LAND SURVEY + TRUST GRADIENT (pc-95) ───────────────────────────────
# Bounded background walk of the city root. Survey data is suburb-grade;
# live walks are session-verified truth. Caps and heaps stay honest.

# _LENS_DIR set at module top (pc-573). Editable: parent of protocolcity/ or tools/.
_REPO_DIR = os.path.dirname(_LENS_DIR)  # city-hall root when editable
SURVEY_CACHE_PATH = os.path.join(_REPO_DIR, "logs", "citylens-survey.json")

SURVEY_MAX_ENTRIES = int(os.environ.get("CITY_SURVEY_MAX_ENTRIES", "30000"))
SURVEY_MAX_DEPTH = int(os.environ.get("CITY_SURVEY_MAX_DEPTH", "8"))
SURVEY_HEAP_COUNT_CAP = int(os.environ.get("CITY_SURVEY_HEAP_CAP", "50000"))
# Vendor/build heaps: excluded from the survey but COUNTED (honest skipped[]).
SURVEY_HEAPS = frozenset({
    "node_modules", ".venv", "venv", "env", "target", "build", "dist",
    "__pycache__", ".pytest_cache", "site-packages",
})
# Trust gradient: depth ≥ this is suburb-grade when served from survey.
TRUST_CORE_DEPTH = 2  # city L0 + room L1 + first paper L2; depth ≥ 3 = suburbs
SURVEY_STALE_HOURS = float(os.environ.get("CITY_SURVEY_STALE_HOURS", "24"))

_INSTRUCTION_BASENAMES = frozenset({
    "agents.md",
    "boundaries.md",  # citizen L0 name (pc-955; perimeter.md is forever-alias)
    "perimeter.md",
    "office_perimeter.md",
    "city_edges.md",
    "claude.md",
    "grok.md",
    "contract.md",
    "prompt.md",
})

# pc-101: THE FILE TYPE REGISTER — extension → class (name only, no sniffing).
# Whitelist: only recognized classes get bodies on the map. Unrecognized =
# listed-not-bodied (THE COMPATIBILITY LINE). Adding a type = ratifying a
# row in CITY_DNA §13 and extending this map.
_FTYPE_DOCUMENT = frozenset({"md", "txt", "pdf", "rtf", "mdx"})
_FTYPE_CODE = frozenset({
    "py", "js", "ts", "html", "css", "sh", "zsh", "scad", "sql", "pine",
    "mjs", "mts", "cjs", "jsx", "tsx", "cpp", "hpp", "rs", "swift", "astro",
    "proto", "nsh",
})
_FTYPE_CONFIG = frozenset({
    "json", "yaml", "yml", "toml", "ini", "plist", "env", "conf", "lock",
    "xml", "service", "target", "entitlements", "pbxproj", "geojson",
})
_FTYPE_DATA = frozenset({
    "csv", "tsv", "db", "sqlite", "parquet", "jsonl", "xlsx",
    "db-shm", "db-wal",
})
_FTYPE_IMAGE = frozenset({
    "png", "jpg", "jpeg", "svg", "gif", "webp", "ico", "icns",
})
_FTYPE_ARCHIVE = frozenset({"zip", "tar", "gz", "tgz", "dmg", "bz2", "xz"})
_FTYPE_RECOGNIZED = frozenset({
    "document", "code", "config", "data", "image", "archive",
})


def file_type(name: str) -> str:
    """Honest name-based file class from extension only (pc-101).

    No content sniffing. Returns one of document|code|config|data|image|
    archive, or ``unrecognized`` (the compatibility line — not a bodied class).
    """
    n = (name or "").lower().strip()
    if not n or n in (".", ".."):
        return "unrecognized"
    # Multi-part archive names first.
    if n.endswith(".tar.gz") or n.endswith(".tar.bz2") or n.endswith(".tar.xz"):
        return "archive"
    if "." not in n:
        return "unrecognized"
    ext = n.rsplit(".", 1)[-1]
    if not ext or ext == n:
        return "unrecognized"
    if ext in _FTYPE_DOCUMENT:
        return "document"
    if ext in _FTYPE_CODE:
        return "code"
    if ext in _FTYPE_CONFIG:
        return "config"
    if ext in _FTYPE_DATA:
        return "data"
    if ext in _FTYPE_IMAGE:
        return "image"
    if ext in _FTYPE_ARCHIVE:
        return "archive"
    return "unrecognized"


def _pointer_target(path: str) -> Optional[str]:
    """If a tiny file is a pure ``@OtherFile`` vendor pointer, return the target.

    Used for CLAUDE.md → AGENTS.md style pointers at the city root (pc-101).
    """
    try:
        st = os.stat(path)
        if st.st_size > 256:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError:
        return None
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if len(lines) != 1:
        return None
    line = lines[0]
    if line.startswith("@") and len(line) > 1:
        target = line[1:].strip()
        if target and "/" not in target and " " not in target:
            return target
    return None


# pc-116 THE FRAMED LAW + THE TRUTH: paper classes beyond instruction (name
# only — the map never reads file contents beyond the pointer probe).
_TRUTH_BASENAMES = frozenset({"architecture.md", "truth-index.md"})
_VENDOR_BASENAMES = frozenset({
    "claude.md", "grok.md", "gemini.md", "codex.md", "cursor.md",
})
# BluePrint required law basenames (Map gold piles · pc-410). Matches client PC_LAW_MD.
# pc-955: BOUNDARIES.md is the citizen L0 name; perimeter.md stays forever-alias.
_PC_RULE_BASENAMES = frozenset({
    "agents.md",
    "boundaries.md",
    "perimeter.md",
    "office_perimeter.md",
    "city_edges.md",
    "atlas.md",
    "claude.md",
    "grok.md",
    "codex.md",
    "cursor.md",
    "gemini.md",
})


def paper_flags(p: str, name: str) -> Dict[str, object]:
    """pc-116 flags for one file child: truth-class body; vendor-pointer
    status (symlink or @pointer); a vendor-named file that is NEITHER is
    DIVERGED — a Charter §3 violation the room red-flags.

    pc-410: ``rule=True`` for required BluePrint law basenames (gold on Map).
    """
    n = (name or "").lower()
    flags: Dict[str, object] = {}
    if n in _TRUTH_BASENAMES:
        flags["truth"] = True
    if n in _PC_RULE_BASENAMES:
        flags["rule"] = True
        flags["instruction"] = True
    if n in _VENDOR_BASENAMES:
        if os.path.islink(p):
            try:
                flags["pointer"] = os.path.basename(os.readlink(p)) or "AGENTS.md"
            except OSError:
                flags["pointer"] = "AGENTS.md"
        else:
            tgt = _pointer_target(p)
            if tgt:
                flags["pointer"] = tgt
            else:
                flags["diverged"] = True
    return flags


def root_files_census(root: str) -> List[dict]:
    """Visible non-hidden files at the city root (pc-101 / pc-951).

    Shallow one-listdir only — never dirs (those are parcels). Used for Map
    light first paint (L0 Instructions seat). Deep nested papers live on
    ``workspace_root_mds`` / snapshot ``root_mds`` (pc-1040).
    """
    out: List[dict] = []
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        return []
    for n in names:
        if n.startswith("."):
            continue
        p = os.path.join(root, n)
        try:
            if not os.path.isfile(p):
                continue
        except OSError:
            continue
        entry: Dict[str, object] = {
            "name": n,
            "kind": "file",
            "ftype": file_type(n),
            "path": p,
        }
        if n.lower().endswith(".md"):
            entry["md"] = True
        if is_instruction_class(n):
            entry["instruction"] = True
        entry.update(paper_flags(p, n))
        out.append(entry)
    return out


def hood_root_entries(dir_path: str) -> List[dict]:
    """All top-level files + folders in a project (Map outer inventory ring).

    Folder-level only — no recursion, no dot-entries. Map paints these as a
    quiet Finder mirror: MDs openable; everything else display-only.
    """
    out: List[dict] = []
    try:
        names = sorted(os.listdir(dir_path), key=str.lower)
    except OSError:
        return []
    for n in names:
        if n.startswith("."):
            continue
        p = os.path.join(dir_path, n)
        try:
            is_dir = os.path.isdir(p)
            is_file = os.path.isfile(p)
        except OSError:
            continue
        if not is_dir and not is_file:
            continue
        if is_dir:
            entry: Dict[str, object] = {
                "name": n,
                "kind": "dir",
                "ftype": "folder",
                "path": p,
            }
        else:
            entry = {
                "name": n,
                "kind": "file",
                "ftype": file_type(n),
                "path": p,
            }
            if n.lower().endswith(".md"):
                entry["md"] = True
            if is_instruction_class(n):
                entry["instruction"] = True
            low = n.lower()
            if low in (
                "agents.md", "perimeter.md", "office_perimeter.md", "city_edges.md",
            ):
                entry["instruction"] = True
            entry.update(paper_flags(p, n))
        out.append(entry)
    return out


# Map RULES orbit: index deep so the client can filter without a rescan.
# suite.mapMdDepth: 1…6 = levels · "all" = every indexed .md under the project.
# Heaps / VCS / agent trees still skipped (HANDS owns workers·ops papers).
_MAP_MD_MAX_DEPTH = 16  # deep enough for "all" transparency under a project
_MAP_MD_MAX_PER_PROJECT = 300  # hard cap so huge trees stay paint-safe
# Skip agent-paper trees (HANDS ring owns those) + heaps + VCS.
_MAP_MD_SKIP_DIRS = SURVEY_HEAPS | frozenset({
    ".git", "workers", "ops", ".venv", "venv",
})
# pc-1040: workspace-root nests to recurse into (not project parcels).
# Project dirs (tradeOS/, ProtocolCity/, …) are skipped at the root ring;
# only infrastructure / paper nests get a nested walk like a project would.
_WORKSPACE_NEST_DIRS = frozenset({
    "docs", "scripts", "papers", "notes", "specs", "research",
    "adr", "adrs", "drafts", "voice", "templates",
})


def _papers_md_entry(
    name: str, abs_path: str, rel: str, depth: int
) -> Dict[str, object]:
    """One Map-paper row (project + workspace root_mds share this shape)."""
    entry: Dict[str, object] = {
        "name": name,
        "kind": "file",
        "ftype": file_type(name),
        "path": abs_path,
        "md": True,
        "depth": depth,
        "rel": rel.replace("\\", "/"),
    }
    try:
        st = os.stat(abs_path)
        entry["mtime"] = int(st.st_mtime)
        entry["size"] = int(st.st_size)
    except OSError:
        entry["mtime"] = 0
        entry["size"] = 0
    if is_instruction_class(name):
        entry["instruction"] = True
    low = name.lower()
    if low in _PC_RULE_BASENAMES:
        entry["instruction"] = True
        entry["rule"] = True
    entry.update(paper_flags(abs_path, name))
    return entry


def papers_census(
    dir_path: str,
    *,
    place: str = "project",
    max_depth: int = _MAP_MD_MAX_DEPTH,
    max_n: int = _MAP_MD_MAX_PER_PROJECT,
) -> List[dict]:
    """Recursive ``*.md`` census for Map papers (pc-1040).

    One implementation for both place levels:

    * ``place="project"`` — full nested walk under a neighborhood (skips
      workers/ops/heaps; allows ``.claude`` / ``.cursor`` / ``.github``).
    * ``place="workspace"`` — city-root papers: depth-1 root ``.md`` plus
      nests in ``_WORKSPACE_NEST_DIRS`` / ``_MD_DOTDIR_ALLOW``. Top-level
      project parcel dirs are never entered.

    Entry shape matches historical ``hood_root_mds`` (name, path, depth, rel,
    rule/instruction flags, mtime/size).
    """
    out: List[dict] = []
    root = os.path.realpath(dir_path)
    place_key = (place or "project").strip().lower()
    if place_key not in ("project", "workspace", "city", "root"):
        place_key = "project"
    is_workspace = place_key in ("workspace", "city", "root")
    try:
        max_depth = max(1, min(int(max_depth), _MAP_MD_MAX_DEPTH))
    except (TypeError, ValueError):
        max_depth = _MAP_MD_MAX_DEPTH
    try:
        max_n = max(1, min(int(max_n), _MAP_MD_MAX_PER_PROJECT))
    except (TypeError, ValueError):
        max_n = _MAP_MD_MAX_PER_PROJECT

    def _add(name: str, abs_path: str, rel: str, depth: int) -> None:
        if len(out) >= max_n:
            return
        out.append(_papers_md_entry(name, abs_path, rel, depth))

    def _prune_children(dirnames: List[str], *, at_root: bool) -> List[str]:
        kept: List[str] = []
        for d in dirnames:
            if d in _MAP_MD_SKIP_DIRS:
                continue
            if d.startswith(".") and d not in _MD_DOTDIR_ALLOW:
                continue
            if at_root and is_workspace:
                # Only recurse into paper / instruction nests — never parcels.
                if d not in _WORKSPACE_NEST_DIRS and d not in _MD_DOTDIR_ALLOW:
                    continue
            kept.append(d)
        return sorted(kept, key=str.lower)

    # Depth-1 (root) first — law basenames sort naturally for the map.
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        return []
    for n in names:
        if n.startswith(".") and n not in _MD_DOTDIR_ALLOW:
            continue
        p = os.path.join(root, n)
        try:
            is_file = os.path.isfile(p)
        except OSError:
            continue
        if is_file and n.lower().endswith(".md"):
            _add(n, os.path.realpath(p), n, 1)

    if max_depth <= 1 or len(out) >= max_n:
        return out

    # Nested walk: depth 2..max_depth (folder segments under place root).
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if len(out) >= max_n:
                break
            rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
            if rel_dir == ".":
                # Already took root files; only prune children for walk.
                dirnames[:] = _prune_children(dirnames, at_root=True)
                continue
            # Folder depth: docs = 1 segment → file depth 2
            folder_depth = rel_dir.count("/") + 1
            file_depth = folder_depth + 1
            if file_depth > max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = _prune_children(dirnames, at_root=False)
            # Skip entire path if any segment is a heap / workers / ops
            parts = rel_dir.split("/")
            if any(seg in _MAP_MD_SKIP_DIRS for seg in parts):
                dirnames[:] = []
                continue
            if any(
                seg.startswith(".") and seg not in _MD_DOTDIR_ALLOW
                for seg in parts
            ):
                dirnames[:] = []
                continue
            # Workspace: first segment must be an allowed nest
            if is_workspace:
                top = parts[0]
                if top not in _WORKSPACE_NEST_DIRS and top not in _MD_DOTDIR_ALLOW:
                    dirnames[:] = []
                    continue
            for fn in sorted(filenames, key=str.lower):
                if len(out) >= max_n:
                    break
                if fn.startswith(".") or not fn.lower().endswith(".md"):
                    continue
                rel = rel_dir + "/" + fn
                abs_path = os.path.join(dirpath, fn)
                try:
                    if not os.path.isfile(abs_path):
                        continue
                except OSError:
                    continue
                _add(fn, os.path.realpath(abs_path), rel, file_depth)
    except OSError:
        pass
    return out


def hood_root_mds(
    dir_path: str,
    *,
    max_depth: int = _MAP_MD_MAX_DEPTH,
    max_n: int = _MAP_MD_MAX_PER_PROJECT,
) -> List[dict]:
    """Project ``*.md`` for the Map RULES orbit (pc-410 / pc-1040).

    Thin wrapper over :func:`papers_census` with ``place="project"``.
    """
    return papers_census(
        dir_path, place="project", max_depth=max_depth, max_n=max_n
    )


def workspace_root_mds(
    dir_path: str,
    *,
    max_depth: int = _MAP_MD_MAX_DEPTH,
    max_n: int = _MAP_MD_MAX_PER_PROJECT,
) -> List[dict]:
    """City-root ``*.md`` for Map workspace papers (pc-1040).

    Same entry shape as :func:`hood_root_mds`. Skips project parcel dirs;
    scans docs/ · scripts/ · .claude/ nests like a project would.
    """
    return papers_census(
        dir_path, place="workspace", max_depth=max_depth, max_n=max_n
    )


_AGENT_PAPER_NAMES = ("prompt.md", "CONTRACT.md", "contract.md", "PROMPT.md")


def hood_agent_papers(dir_path: str) -> List[dict]:
    """Agent-required papers for the Map papers orbit (between agents + inventory).

    Scans:
      · workers/<id>/prompt.md · CONTRACT.md
      · ops/tasks/<id>/… and ops/tasks/<id>-lane/… (tradeOS hire layout)

    Each entry is one openable markdown file with agent id for grouping.
    """
    out: List[dict] = []
    # (agent_lower, paper_kind) — case-insensitive FS can match prompt.md twice
    seen: set = set()

    def _add(agent_id: str, kind: str, abs_path: str) -> None:
        if not os.path.isfile(abs_path):
            return
        key = (str(agent_id).lower(), kind)
        if key in seen:
            return
        seen.add(key)
        display = "prompt.md" if kind == "prompt" else "CONTRACT.md"
        out.append({
            "agent": agent_id,
            "name": display,
            "file": display,
            "kind": kind,
            "path": os.path.realpath(abs_path),
            "md": True,
        })

    def _scan_agent_dir(agent_id: str, wpath: str) -> None:
        # Prefer canonical names; fall back to alt case once per kind
        for kind, cands in (
            ("prompt", ("prompt.md", "PROMPT.md")),
            ("contract", ("CONTRACT.md", "contract.md")),
        ):
            for cand in cands:
                p = os.path.join(wpath, cand)
                if os.path.isfile(p):
                    _add(agent_id, kind, p)
                    break

    # workers/<agent>/
    wroot = os.path.join(dir_path, "workers")
    try:
        wnames = sorted(os.listdir(wroot), key=str.lower)
    except OSError:
        wnames = []
    for wname in wnames:
        if not wname or wname.startswith("."):
            continue
        wpath = os.path.join(wroot, wname)
        if os.path.isdir(wpath):
            _scan_agent_dir(wname, wpath)

    # ops/tasks/<agent>/ and <agent>-lane/
    troot = os.path.join(dir_path, "ops", "tasks")
    try:
        tnames = sorted(os.listdir(troot), key=str.lower)
    except OSError:
        tnames = []
    for tname in tnames:
        if not tname or tname.startswith("."):
            continue
        tpath = os.path.join(troot, tname)
        if not os.path.isdir(tpath):
            continue
        agent_id = tname[:-5] if tname.endswith("-lane") else tname
        _scan_agent_dir(agent_id, tpath)

    out.sort(key=lambda e: (
        str(e.get("agent") or "").lower(),
        0 if e.get("kind") == "contract" else 1,
        str(e.get("file") or "").lower(),
    ))
    return out


_survey_lock = threading.Lock()
_survey_state: Dict[str, object] = {
    "status": "idle",           # idle | running | done | stale
    "surveyed_at": None,        # ISO Z
    "city_root": "",
    "parcels": 0,               # directory entries recorded
    "entries": 0,               # total entries (dirs + files)
    "skipped": [],              # [{path, count}]
    "children_of": {},          # rel -> [child summary dicts]
    "dirs": {},                 # rel -> dir meta (founded, survey_stopped, …)
    "duration_ms": 0,
    "error": None,
}
_survey_thread: Optional[threading.Thread] = None
# Paths live-walked this process lifetime (TRUSTED CORE for the session).
_walked_this_session: set = set()


def is_instruction_class(name: str) -> bool:
    """Mirror map.html isInstructionClass — names only, no content."""
    n = (name or "").lower()
    if n in _INSTRUCTION_BASENAMES:
        return True
    if n.endswith(".spec") or n.endswith(".spec.md"):
        return True
    if "spec" in n and n.endswith(".md"):
        return True
    return False


_MAP_HEADINGS = ("folder map", "repo map", "layout", "structure", "project structure")
_MAP_BULLET_RE = re.compile(r"^[-*]\s+`([^`]+)`\s*[—–:-]\s*(.+)$")


def _map_key(token: str) -> str:
    """A map row keys on the FIRST path segment (`lib/vendored/` → lib,
    `drafts/YYYY-MM-DD.md` → drafts) so the law's natural deep-path prose
    still identifies the top-level child the room renders."""
    name = token.strip().strip("`").strip().strip("/")
    return name.split("/")[0].strip() if name else ""


def parse_folder_map(dir_path: str) -> Optional[dict]:
    """Parse the folder map from a directory's AGENTS.md (pc-111).

    The law maps the room. Accepted sections: '## Folder map' / '## Repo map'
    (the kit's canonical name) plus the organic conventions already in city
    law files: '## Layout', '## Structure', '## Project structure'. Accepted
    row forms inside a section: markdown table rows (| `path` | what | tended
    by? |, multi-path cells map every listed name) and bullet lines
    (- `path/` — description). First row naming a child wins; returns
    {"rows": {name: {"what":…, "tended":…}}, "law_mtime": float} or None.
    """
    law = os.path.join(dir_path, "AGENTS.md")
    if not os.path.isfile(law):
        return None
    try:
        text = open(law, "r", encoding="utf-8").read()
        law_mtime = os.path.getmtime(law)
    except OSError:
        return None
    in_map = False
    rows: Dict[str, dict] = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip().lower()
            in_map = heading in _MAP_HEADINGS
            continue
        if not in_map:
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= {"-", " ", ":"}:
                continue
            if cells[0].lower() in ("path", "folder"):
                continue
            what = cells[1]
            tended = cells[2] if len(cells) > 2 else ""
            for token in cells[0].split(","):
                name = _map_key(token)
                if name:
                    rows.setdefault(name, {"what": what, "tended": tended})
            continue
        m = _MAP_BULLET_RE.match(s)
        if m:
            name = _map_key(m.group(1))
            if name:
                rows.setdefault(name, {"what": m.group(2).strip(), "tended": ""})
    if not rows:
        return None
    return {"rows": rows, "law_mtime": law_mtime}


def attach_folder_map(root: str, rel_posix: str, listing: dict) -> dict:
    """Annotate a parcel listing's children from the level's own law (pc-111).

    Mapped children gain child["map"]={"what","tended","drift"}; the listing
    gains folder_map={present, mapped, unmapped, law_mtime_iso}. Drift is the
    per-row trust signal (pc-112): the child dir changed after the law's map
    was last written. Missing law / no table → folder_map.present=False and
    children stay bare (the map renders them unmapped/grey).
    """
    listing = dict(listing)
    segs = [s for s in rel_posix.split("/") if s]
    dir_path = os.path.join(os.path.realpath(os.path.expanduser(root)), *segs)
    fmap = parse_folder_map(dir_path)
    children = [dict(c) for c in (listing.get("children") or [])]
    if fmap is None:
        listing["children"] = children
        listing["folder_map"] = {"present": False}
        return listing
    mapped = 0
    for child in children:
        row = fmap["rows"].get(str(child.get("name") or ""))
        if row is None:
            continue
        mapped += 1
        info = {"what": row["what"], "tended": row.get("tended") or ""}
        try:
            child_mtime = os.path.getmtime(os.path.join(dir_path, str(child["name"])))
            info["drift"] = child_mtime > fmap["law_mtime"]
        except OSError:
            pass
        child["map"] = info
    listing["children"] = children
    listing["folder_map"] = {
        "present": True,
        "mapped": mapped,
        "unmapped": max(0, len(children) - mapped),
        "law_mtime": datetime.datetime.fromtimestamp(
            fmap["law_mtime"], datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return listing


def _count_heap_entries(path: str, cap: int = SURVEY_HEAP_COUNT_CAP) -> int:
    """Cheap capped count of a vendor/build heap (scandir; no deep metadata)."""
    n = 0
    stack = [path]
    while stack and n < cap:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    n += 1
                    if n >= cap:
                        return n
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                    except OSError:
                        continue
        except OSError:
            continue
    return n


def _survey_public_summary() -> dict:
    """The survey block for /api/city — status + counts only, not the index."""
    with _survey_lock:
        st = str(_survey_state.get("status") or "idle")
        surveyed_at = _survey_state.get("surveyed_at")
        parcels = int(_survey_state.get("parcels") or 0)
        entries = int(_survey_state.get("entries") or 0)
        skipped = list(_survey_state.get("skipped") or [])
        duration_ms = int(_survey_state.get("duration_ms") or 0)
        err = _survey_state.get("error")
        # Promote done → stale when older than SURVEY_STALE_HOURS.
        confidence = None
        if st == "done" and surveyed_at:
            dt = _parse_iso(str(surveyed_at))
            if dt is not None:
                age_h = (datetime.datetime.now(datetime.timezone.utc) - dt
                         ).total_seconds() / 3600.0
                if age_h >= SURVEY_STALE_HOURS:
                    st = "stale"
                # pc-112: the survey's trust decays continuously with age —
                # 100% at completion, 0% at the stale floor. Time decay is the
                # baseline prior; event-aware decay is the ticket's mature form.
                confidence = max(0.0, min(1.0, 1.0 - age_h / SURVEY_STALE_HOURS))
        elif st == "stale":
            confidence = 0.0
        out = {
            "status": st if st != "idle" else (
                "running" if _survey_thread and _survey_thread.is_alive()
                else "done" if surveyed_at else "idle"
            ),
            "surveyed_at": surveyed_at,
            "parcels": parcels,
            "entries": entries,
            "skipped": skipped,
            "duration_ms": duration_ms,
        }
        if confidence is not None:
            out["confidence"] = round(confidence, 3)
        if err:
            out["error"] = str(err)
        return out


def estate_of(name: str) -> Optional[dict]:
    """pc-115: THE ESTATE — a neighborhood's folder mass from the land survey.

    Founder ruling (2026-07-15): form = the estate, bustle = the workload.
    `recorded` counts survey-recorded entries in the subtree (the estate on
    record — this is what shapes building form); `heap` counts vendor/build
    heaps (counted-not-surveyed, shown but never form-shaping — an unverified
    heap can't earn a tower). None until a survey has run.
    """
    with _survey_lock:
        if not _survey_state.get("surveyed_at"):
            return None
        children_of = _survey_state.get("children_of") or {}
        skipped = _survey_state.get("skipped") or []
    prefix = name + "/"
    recorded = sum(
        len(kids) for rel, kids in children_of.items()
        if rel == name or rel.startswith(prefix)
    )
    heap = sum(
        int(s.get("count") or 0) for s in skipped
        if s.get("path") == name or str(s.get("path") or "").startswith(prefix)
    )
    return {"recorded": recorded, "heap": heap, "total": recorded + heap}


# Instruction / rules files auto-discovery (cabinet drawers).
# ProtocolCity canonical law = AGENTS.md (agents.md open format).
# Everything else is vendor or custom — same product: "how my AIs work here."
# Ecosystem names (2026): agents.md, CLAUDE.md, .cursorrules, copilot-instructions,
# GEMINI.md, windsurf/cline rules — plus pattern match for *agents* *rules* etc.
_INSTRUCTION_MAX_DRAWERS = 12
# Content / vault papers (drafts, story, docs, skills) — separate from law.
_CONTENT_MAX_PAPERS = 32
_CONTENT_MAX_DEPTH = 4  # segments under cabinet (e.g. story/ch/foo.md = 3)
_CONTENT_ROOT_DIRS = frozenset({
    "drafts", "story", "docs", "voice", "notes", "papers", "specs",
    "adr", "adrs", "research",
})
_MD_READ_EXTS = (".md", ".mdc", ".txt", ".markdown")
# Dotdirs that may appear on a readable nested MD path (skills, rules).
_MD_DOTDIR_ALLOW = frozenset({".claude", ".cursor", ".github"})
# Priority: PC canonical first, then common vendor instruction files.
_INSTRUCTION_KNOWN = (
    "AGENTS.md",           # open multi-agent standard (agents.md) — PC law
    "CLAUDE.md",           # Claude Code
    "CLAUDE.local.md",
    "GROK.md",             # Grok / xAI tooling
    "GEMINI.md",           # Gemini CLI
    "CODEX.md",
    ".cursorrules",        # Cursor (legacy single file)
    ".windsurfrules",
    ".clinerules",
    ".goosehints",
    "copilot-instructions.md",
    ".github/copilot-instructions.md",
    "README.md",           # human+agent context often lives here
    "README.public.md",    # BluePrint / two-lane export landing (pc-202)
    "PERIMETER.md",        # L0 office perimeter / cross-cabinet grants
    "OFFICE_PERIMETER.md", # legacy L0 perimeter name
    "CITY_EDGES.md",       # legacy city-root name (still accepted)
    "ARCHITECTURE.md",
    "PROCESS.md",
    "MARKETING.md",
    "LAUNCH-PLAN.md",
)
_INSTRUCTION_NAME_RE = re.compile(
    r"(?i)^(agents?|claude|grok|gemini|codex|cursor|windsurf|cline|copilot|"
    r"instructions?|rules?|process|architecture|contributing|"
    r"marketing|launch[-_]?plan)([._-].*)?\.(md|txt)$"
    r"|^\.(cursorrules|windsurfrules|clinerules|goosehints)$"
)


def _quick_entry_count(path: str) -> int:
    """Depth-1 entries when survey has not shaped the estate yet."""
    try:
        return sum(1 for n in os.listdir(path) if not n.startswith("."))
    except OSError:
        return 0


def _is_instruction_file(name: str) -> bool:
    base = os.path.basename(name)
    if base in _INSTRUCTION_KNOWN or base.upper() in {k.upper() for k in _INSTRUCTION_KNOWN}:
        return True
    return bool(_INSTRUCTION_NAME_RE.match(base))


def _cabinet_instruction_drawers(
    path: str, *, max_n: int = _INSTRUCTION_MAX_DRAWERS
) -> List[dict]:
    """Auto-discover instruction/rules files for this cabinet.

    AGENTS.md is ProtocolCity's canonical law drawer when present; other
    files are vendor pointers or the user's own AI instructions — the
    customizability of the system (Claude, Cursor, Grok, Copilot, …).
    """
    found: Dict[str, str] = {}  # display name -> abs path

    def _add(rel: str, abs_path: str) -> None:
        if rel not in found and os.path.isfile(abs_path):
            found[rel] = abs_path

    try:
        names = [n for n in os.listdir(path) if n not in (".", "..")]
    except OSError:
        return []

    for n in names:
        p = os.path.join(path, n)
        if os.path.isfile(p) and _is_instruction_file(n):
            _add(n, p)

    # Nested well-known paths (still one drawer each)
    for rel in (
        ".github/copilot-instructions.md",
        ".cursor/rules",  # dir — skip; files below
    ):
        p = os.path.join(path, rel)
        if os.path.isfile(p):
            _add(rel, p)

    # .cursor/rules/*.mdc or .md (Cursor modern rules)
    cursor_rules = os.path.join(path, ".cursor", "rules")
    if os.path.isdir(cursor_rules):
        try:
            for n in sorted(os.listdir(cursor_rules)):
                if n.startswith("."):
                    continue
                if n.lower().endswith((".md", ".mdc", ".txt")):
                    _add(".cursor/rules/" + n, os.path.join(cursor_rules, n))
        except OSError:
            pass

    # Priority order: known list first, then remaining alpha
    ordered: List[str] = []
    lower_map = {k.lower(): k for k in found}
    for pref in _INSTRUCTION_KNOWN:
        key = lower_map.get(pref.lower())
        if key and key not in ordered:
            ordered.append(key)
    for k in sorted(found.keys(), key=str.lower):
        if k not in ordered:
            ordered.append(k)

    out: List[dict] = []
    for rel in ordered[:max_n]:
        base = os.path.basename(rel)
        if base.upper() == "AGENTS.MD":
            role = "canonical"
        elif base.upper() in ("PERIMETER.MD", "OFFICE_PERIMETER.MD", "CITY_EDGES.MD"):
            role = "perimeter"
        elif any(base.upper() == k.upper() or base.startswith(".")
                 for k in ("CLAUDE.md", "GROK.md", "GEMINI.md", "CODEX.md",
                           ".cursorrules", ".windsurfrules", ".clinerules")):
            role = "vendor"
        elif "copilot" in base.lower() or "cursor" in rel.lower():
            role = "vendor"
        else:
            # README / ARCHITECTURE / PROCESS / pattern matches — instruction
            # papers, not vendor entry points (Charter §3 vendor = pointer).
            role = "instruction"
        label = base if not rel.startswith(".") else base
        if label.lower().endswith(".md"):
            label = label[:-3]
        abs_path = found[rel]
        entry: Dict[str, object] = {
            "name": rel,           # path relative to cabinet (may include /)
            "label": label,
            "path": abs_path,
            "role": role,          # canonical | vendor | perimeter | instruction
        }
        # Charter §3 honesty: vendor files expose pointer target or diverged.
        flags = paper_flags(abs_path, base)
        if flags.get("pointer"):
            entry["pointer"] = flags["pointer"]
        if flags.get("diverged"):
            entry["diverged"] = True
        out.append(entry)
    return out


# Back-compat alias
def _cabinet_md_drawers(path: str, *, max_n: int = _INSTRUCTION_MAX_DRAWERS) -> List[dict]:
    return _cabinet_instruction_drawers(path, max_n=max_n)


def _is_md_basename(name: str) -> bool:
    n = (name or "").lower()
    return any(n.endswith(ext) for ext in _MD_READ_EXTS)


def _md_rel_allowed(fn: str, *, max_depth: int = _CONTENT_MAX_DEPTH) -> bool:
    """True when ``fn`` is a safe relative MD path (no heaps, depth-capped)."""
    parts = [p for p in (fn or "").replace("\\", "/").split("/") if p and p != "."]
    if not parts or ".." in parts:
        return False
    if len(parts) > max_depth:
        return False
    if not _is_md_basename(parts[-1]):
        return False
    for seg in parts[:-1]:
        if seg in SURVEY_HEAPS:
            return False
        if seg.startswith(".") and seg not in _MD_DOTDIR_ALLOW:
            return False
    # Dotdir roots only for known nests (skills / rules / github).
    if parts[0].startswith(".") and parts[0] not in _MD_DOTDIR_ALLOW:
        return False
    return True


def _paper_role_for(rel: str, base: str) -> str:
    if base.upper() == "AGENTS.MD":
        return "canonical"
    if base.upper() in ("PERIMETER.MD", "OFFICE_PERIMETER.MD", "CITY_EDGES.MD"):
        return "perimeter"
    if _is_instruction_file(base) or rel in _INSTRUCTION_KNOWN:
        if any(base.upper() == k.upper() or base.startswith(".")
               for k in ("CLAUDE.md", "GROK.md", "GEMINI.md", "CODEX.md",
                         ".cursorrules", ".windsurfrules", ".clinerules")):
            return "vendor"
        if "copilot" in base.lower() or "cursor" in rel.lower():
            return "vendor"
        return "instruction"
    if rel.startswith(".claude/skills/"):
        return "skill"
    return "content"


def _cabinet_content_papers(
    path: str, *, max_n: int = _CONTENT_MAX_PAPERS
) -> List[dict]:
    """Discover vault/content markdown under a managed cabinet (depth ≤ 4).

    Walks well-known content roots (drafts/, story/, docs/, …), depth-1
    non-instruction ``*.md``, and ``.claude/skills/*/SKILL.md``. Heaps and
    foreign dotdirs are skipped. Bodies are not read here — names only.
    """
    found: Dict[str, str] = {}

    def _add(rel: str, abs_path: str) -> None:
        rel = rel.replace("\\", "/")
        if not _md_rel_allowed(rel):
            return
        if rel not in found and os.path.isfile(abs_path):
            found[rel] = abs_path

    # Depth-1 markdown that isn't already an instruction face
    try:
        for n in sorted(os.listdir(path)):
            if n.startswith("."):
                continue
            p = os.path.join(path, n)
            if os.path.isfile(p) and _is_md_basename(n) and not _is_instruction_file(n):
                _add(n, p)
    except OSError:
        pass

    # Well-known content trees
    for root_name in sorted(_CONTENT_ROOT_DIRS):
        root_dir = os.path.join(path, root_name)
        if not os.path.isdir(root_dir):
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Prune heaps / hidden in-place
                dirnames[:] = [
                    d for d in dirnames
                    if d not in SURVEY_HEAPS
                    and (not d.startswith(".") or d in _MD_DOTDIR_ALLOW)
                ]
                rel_dir = os.path.relpath(dirpath, path).replace("\\", "/")
                depth = 0 if rel_dir == "." else rel_dir.count("/") + 1
                if depth >= _CONTENT_MAX_DEPTH:
                    dirnames[:] = []
                    continue
                for fn in sorted(filenames):
                    if fn.startswith(".") or not _is_md_basename(fn):
                        continue
                    rel = fn if rel_dir == "." else rel_dir + "/" + fn
                    if rel.count("/") + 1 > _CONTENT_MAX_DEPTH:
                        continue
                    _add(rel, os.path.join(dirpath, fn))
                    if len(found) >= max_n * 2:
                        break
                if len(found) >= max_n * 2:
                    break
        except OSError:
            continue

    # Skills: list SKILL.md as openable papers
    skills_root = os.path.join(path, ".claude", "skills")
    if os.path.isdir(skills_root):
        try:
            for sid in sorted(os.listdir(skills_root)):
                if sid.startswith("."):
                    continue
                skill_md = os.path.join(skills_root, sid, "SKILL.md")
                if os.path.isfile(skill_md):
                    _add(".claude/skills/%s/SKILL.md" % sid, skill_md)
        except OSError:
            pass

    ordered = sorted(found.keys(), key=str.lower)
    out: List[dict] = []
    for rel in ordered[:max_n]:
        base = os.path.basename(rel)
        role = _paper_role_for(rel, base)
        label = base[:-3] if base.lower().endswith(".md") else base
        if role == "skill":
            # .claude/skills/<id>/SKILL.md → show skill id
            parts = rel.split("/")
            label = parts[2] if len(parts) >= 3 else label
        out.append({
            "name": rel,
            "label": label,
            "path": found[rel],
            "role": role,
        })
    return out


def _cabinet_all_drawers(
    path: str,
    *,
    max_instr: int = _INSTRUCTION_MAX_DRAWERS,
    max_content: int = _CONTENT_MAX_PAPERS,
) -> List[dict]:
    """Instruction faces first, then content/vault papers (deduped by name)."""
    instr = _cabinet_instruction_drawers(path, max_n=max_instr)
    content = _cabinet_content_papers(path, max_n=max_content)
    seen = {d["name"] for d in instr}
    out = list(instr)
    for c in content:
        if c["name"] in seen:
            continue
        out.append(c)
        seen.add(c["name"])
    return out


def _cabinet_managed(path: str) -> bool:
    """BluePrint-managed = join marker (pc-427), not AGENTS.md alone.

    pc-1041: single reader — delegates to :func:`protocolcity.adopt.is_managed`.
    Lazy import avoids package import cycles (adopt loads citylens for zone_of).
    """
    try:
        from pathlib import Path as _Path

        from protocolcity.adopt import is_managed as _is_managed

        return bool(_is_managed(_Path(path)))
    except Exception:
        return os.path.isfile(os.path.join(path, ".protocolcity", "managed"))


def _store_from_desk_join_file(
    path: str, product: str
) -> Optional[Dict[str, int]]:
    """Zero-count store row when desk-join.json proves a join (pc-557).

    After Join Store, desk-join.json is on disk immediately while /api/scene
    counts can lag one poll — without this, Map keeps "No desk store".
    """
    join_path = os.path.join(path, ".protocolcity", "desk-join.json")
    if not os.path.isfile(join_path):
        return None
    try:
        with open(join_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    slug = str(data.get("slug") or "").strip().lower()
    if not slug:
        return None
    # Prefer joined slug as product when census product drifted
    _ = product  # reserved for future mismatch flags
    return {
        "backlog": 0,
        "in_progress": 0,
        "in_review": 0,
        "done": 0,
        "urgent_backlog": 0,
        "ready": 0,
    }


def _peek_papers(path: str, *, managed: bool) -> List[dict]:
    """Loose sheets on the cabinet — instruction + content papers."""
    if not managed:
        return []
    return [{"name": d["name"], "kind": "file", "role": d.get("role")}
            for d in _cabinet_all_drawers(path)]


def _read_md_file(path: str) -> Optional[Dict[str, object]]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(200_000)
    except OSError:
        return None
    return {"text": text, "truncated": len(text) >= 200_000}


def read_cabinet_md(city_root: str, cabinet: str, filename: str) -> Optional[Dict[str, object]]:
    """Read one markdown paper for the office reader (cabinet or L0 boot).

    cabinet = folder name, or ``_root`` / ``.`` / empty for city-root boot papers.
    Allows instruction paths plus nested content MD up to ``_CONTENT_MAX_DEPTH``.
    """
    root = os.path.abspath(city_root)
    name = (cabinet or "").strip().strip("/").replace("\\", "/")
    fn = (filename or "").strip().replace("\\", "/")
    # Strip only "./" prefixes — never str.lstrip("./") (eats leading '.' on .claude).
    while fn.startswith("./"):
        fn = fn[2:]
    fn = fn.lstrip("/")
    if not fn or ".." in fn.split("/"):
        return None
    base = os.path.basename(fn)
    if not _md_rel_allowed(fn):
        # Legacy: depth-1 non-md instruction names (.cursorrules)
        if "/" in fn or not (
            _is_instruction_file(base) or fn in _INSTRUCTION_KNOWN
            or fn.startswith(".cursor/rules/") or fn.startswith(".github/")
        ):
            return None

    # L0 boot papers at city root
    if not name or name in (".", "_root", "__root__", "root"):
        path = os.path.abspath(os.path.join(root, fn))
        try:
            if os.path.commonpath([root, path]) != root:
                return None
        except ValueError:
            return None
        if not os.path.isfile(path):
            return None
        # Nested under root: only allowlisted nests (rules / github / content dirs)
        if os.path.dirname(path) != root:
            top = fn.split("/", 1)[0]
            if not (
                fn.startswith(".cursor/")
                or fn.startswith(".github/")
                or fn.startswith(".claude/")
                or top in _CONTENT_ROOT_DIRS
            ):
                return None
        blob = _read_md_file(path)
        if blob is None:
            return None
        role = _paper_role_for(fn, base)
        return {
            "cabinet": "_root",
            "level": "L0",
            "name": fn,
            "path": path,
            "role": role,
            "text": blob["text"],
            "truncated": blob["truncated"],
        }

    if name.startswith(".") or ".." in name.split("/"):
        return None
    cab = os.path.abspath(os.path.join(root, name))
    try:
        if os.path.commonpath([root, cab]) != root:
            return None
    except ValueError:
        return None
    if not os.path.isdir(cab):
        return None
    path = os.path.abspath(os.path.join(cab, fn))
    try:
        if os.path.commonpath([cab, path]) != cab:
            return None
    except ValueError:
        return None
    if not os.path.isfile(path):
        return None
    blob = _read_md_file(path)
    if blob is None:
        return None
    role = _paper_role_for(fn, base)
    return {
        "cabinet": name,
        "level": "L1",
        "name": fn,
        "path": path,
        "role": role,
        "text": blob["text"],
        "truncated": blob["truncated"],
    }


def read_city_file_md(city_root: str, rel: str) -> Optional[Dict[str, object]]:
    """Read a city-root-relative markdown file for Map / suite inspect.

    Thin path-split over :func:`read_cabinet_md` (pc-1040 — one reader body).
    ``rel`` may be a root paper (``AGENTS.md``), a root nest
    (``.claude/skills/…``), or ``cabinet/…/file.md``.
    """
    root = os.path.abspath(city_root)
    fn = (rel or "").strip().replace("\\", "/")
    while fn.startswith("./"):
        fn = fn[2:]
    fn = fn.lstrip("/")
    if not fn or ".." in fn.split("/"):
        return None
    parts = [p for p in fn.split("/") if p]
    if not parts:
        return None
    # Root-level paper or root nest (.claude / .cursor / docs/…)
    if len(parts) == 1 or parts[0].startswith("."):
        return read_cabinet_md(root, "_root", fn)
    # Nested under a project parcel — still one reader
    nested = "/".join(parts[1:])
    if not _md_rel_allowed(nested):
        return None
    return read_cabinet_md(root, parts[0], nested)


# City-hall / government employment — jobs whose *beat* is city-wide (every
# cabinet / every TP store), even when their papers live under workforce or
# ProtocolCity. Product jobs (tradeOS backlog-snapshot, etc.) are NOT here.
# pc-1036: default seeded seats (function names) + legacy civic callsigns.
# Alias names (marshal → health-patrol, …) share dossier rows so dig still
# resolves on cities that never re-hired under the new slug.
CITY_HALL_JOB_NAMES = frozenset({
    # Default trio (pc-988 seed)
    "chief-of-staff",
    "health-patrol",
    "workspace-efficiency",
    # Prior / alias identities still present on some rosters
    "marshal",
    "city-marshal",
    "city-steward",
    "founder-brief",
    "clerk",
    "city-clerk",
    "wren",
    "correspondent",
    "city-correspondent",
})

# Citizen-facing dossier for L0 office agents (pc-166 / pc-1036).
# Roster owns runtime; this table owns the Office explanation
# (beat / truth / writes). Dig looks up by worker name.
#
# Default seeded seats (pc-988): chief-of-staff · health-patrol ·
# workspace-efficiency — function titles + citizen-register one-liners.
# Legacy civic callsigns remain for cities that still run them.
# role_tag strings map suite glyphs (suite glass rename = pc-989).
_OFFICE_AGENT_DOSSIER_CHIEF = {
    "given_name": "Chief of Staff",
    "title": "Workspace coordinator",
    "role_tag": "chief-of-staff",
    "one_liner": (
        "Coordinates the workspace — drains open epics into seated work, "
        "stages capacity restore for You to apply."
    ),
    "does": (
        "Every shift: sweeps all stores for undrained open epics and files "
        "routed implement children from recorded decisions; stages Mode B "
        "roster pin diffs under policy (never merges the live roster). "
        "Not a product-folder claiming hand."
    ),
    "surface": "Workspace ops · Map staff ring",
    "reads": [
        "WorkLane project=all (open epics + children)",
        "WorkForce capacity / pool alerts",
        "capacity_policy.json (ops seat papers)",
    ],
    "writes": [
        "Routed child work orders + signed comments (chief-of-staff)",
        "Staged roster-diff JSON under WorkForce data (Mode B only)",
        "At most one For You card per staged capacity unit",
    ],
    "output_glob": None,
    "contract_rel": "workers/chief-of-staff/CONTRACT.md",
    "rules": "CONTRACT.md · prompt.md · capacity_policy.json · ALWAYS_WORK",
    "cadence_hint": "Daily at 09:00 Mon–Fri local",
}

_OFFICE_AGENT_DOSSIER_HEALTH = {
    "given_name": "Health Patrol",
    "title": "Ticket health",
    "role_tag": "health-patrol",
    "one_liner": (
        "Patrols ticket health across stores — nothing stays stale, "
        "unlabeled, or quietly stuck."
    ),
    "does": (
        "Patrols every WorkLane store for stale claims, unlabeled ready work, "
        "and quiet dependency chains. May release a confirmed ghost claim with "
        "a signed comment; never closes others' work."
    ),
    "surface": "WorkLane · Desk (all stores)",
    "reads": [
        "All WorkLane stores (lifecycle + claims)",
        "Ticket trails / ownership markers (read-only)",
    ],
    "writes": [
        "Ticket comments only (release / Blocked notes) — no report files",
    ],
    "output_glob": None,
    "contract_rel": "workers/health-patrol/CONTRACT.md",
    "rules": "CONTRACT.md · WorkLane PROCESS §§4–5 · workspace AGENTS.md",
    "cadence_hint": "11:00 + 15:00 Mon–Fri local",
}

_OFFICE_AGENT_DOSSIER_EFFICIENCY = {
    "given_name": "Workspace Efficiency",
    "title": "Drain hygiene",
    "role_tag": "workspace-efficiency",
    "one_liner": (
        "Keeps hands fed while You are away — seats ready work, "
        "flags starve and empty-agent drift."
    ),
    "does": (
        "Audits ready-by-seat feeds, re-labels clear implement starve onto "
        "hired hands, and writes a daily efficiency report. Never mass-cancels "
        "or claims product implement tickets for itself."
    ),
    "surface": "Workspace ops · ready feeds + reports",
    "reads": [
        "WorkLane ready feeds by worker label (all stores)",
        "WorkForce roster / queue_url health",
        "L0 skill workspace-efficiency playbook",
    ],
    "writes": [
        "ops/reports/workspace-efficiency/YYYY-MM-DD.md",
        "Re-label starve ready → hired hand (narrow)",
        "At most 3 routed residual work orders when re-route is ambiguous",
    ],
    "output_glob": "reports/workspace-efficiency/*.md",
    "contract_rel": "workers/workspace-efficiency/CONTRACT.md",
    "rules": "CONTRACT.md · prompt.md · workspace-efficiency skill",
    "cadence_hint": "09:30 + 16:30 daily local",
}

_OFFICE_AGENT_DOSSIER = {
    # --- Default trio (pc-988 / pc-1036) ---------------------------------
    "chief-of-staff": _OFFICE_AGENT_DOSSIER_CHIEF,
    "health-patrol": _OFFICE_AGENT_DOSSIER_HEALTH,
    "workspace-efficiency": _OFFICE_AGENT_DOSSIER_EFFICIENCY,
    # Aliases: digs by prior seed names share the function-seat copy.
    "marshal": _OFFICE_AGENT_DOSSIER_HEALTH,
    "city-marshal": _OFFICE_AGENT_DOSSIER_HEALTH,
    # --- Legacy civic callsigns (still present on some cities) ----------
    "city-steward": {
        "given_name": "Holt",
        "title": "City Marshal",
        "role_tag": "marshal",
        "one_liner": "The cop on the ticket desk — nothing stays stale or unlabeled.",
        "does": (
            "Patrols every WorkLane store for stale claims, unlabeled backlog, "
            "and quiet dependency chains. May release a confirmed ghost claim; "
            "never closes others' work."
        ),
        "surface": "WorkLane · Desk",
        "reads": [
            "All TP / WorkLane stores (lifecycle + claims)",
            "Ticket trails / ownership markers (read-only)",
        ],
        "writes": [
            "Ticket comments only (Blocked: release note) — no report files",
        ],
        "output_glob": None,
        "contract_rel": "workers/city-steward/CONTRACT.md",
        "rules": "CONTRACT.md · WorkLane PROCESS §§4–5 · workspace AGENTS.md",
        "cadence_hint": "3× daily (06:00 / 14:00 / 22:00 local)",
    },
    "founder-brief": {
        "given_name": "Ames",
        "title": "City Clerk",
        "role_tag": "clerk",
        "one_liner": "The morning clerk — one brief so the founder sees wedges and pulse.",
        "does": (
            "Reads WorkForce + desk summaries and writes a dated morning brief. "
            "Observational only — does not operate engines or claim tickets."
        ),
        "surface": "WorkForce · Roster → founder",
        "reads": [
            "GET WorkForce /api/workers",
            "Desk board-summary / tp_counts (all stores)",
            "Prior founder-brief (deltas only)",
        ],
        "writes": [
            "workforce/local/reports/founder-brief-YYYY-MM-DD.md",
            "One signed desk comment on the standing briefs ticket",
        ],
        "output_glob": "local/reports/founder-brief-*.md",
        "contract_rel": "workers/founder-brief/CONTRACT.md",
        "rules": "CONTRACT.md · prompt.md · workspace AGENTS.md",
        "cadence_hint": "Daily at 08:00 local",
    },
    "wren": {
        "given_name": "Wren",
        "title": "City Correspondent",
        "role_tag": "correspondent",
        "one_liner": "The reporter — walks every cabinet and files what is true today.",
        "does": (
            "Observes citylens + desk + workers, then writes one brief per store "
            "plus a city rollup. Watches and reports; never claims or edits product code."
        ),
        "surface": "BluePrint · Office + every cabinet",
        "reads": [
            "citylens snapshot / Office read model",
            "WorkLane per-store open work",
            "WorkForce /api/workers",
        ],
        "writes": [
            "ProtocolCity/local/reports/wren/<store>-YYYY-MM-DD.md",
            "ProtocolCity/local/reports/wren/city-YYYY-MM-DD.md",
        ],
        "output_glob": "local/reports/wren/*.md",
        "contract_rel": "workers/wren/CONTRACT.md",
        "rules": "CONTRACT.md · prompt.md · workspace AGENTS.md",
        "cadence_hint": "Daily at 09:00 local (after the Clerk)",
    },
}
# Legacy dig aliases → same citizen copy as founder-brief / wren seats.
_OFFICE_AGENT_DOSSIER["clerk"] = _OFFICE_AGENT_DOSSIER["founder-brief"]
_OFFICE_AGENT_DOSSIER["city-clerk"] = _OFFICE_AGENT_DOSSIER["founder-brief"]
_OFFICE_AGENT_DOSSIER["correspondent"] = _OFFICE_AGENT_DOSSIER["wren"]
_OFFICE_AGENT_DOSSIER["city-correspondent"] = _OFFICE_AGENT_DOSSIER["wren"]


def _latest_report_artifact(workdir: str, pattern: Optional[str]) -> Optional[dict]:
    """Newest file matching a relative glob under workdir (gitignored evidence)."""
    if not workdir or not pattern:
        return None
    root = Path(workdir)
    try:
        hits = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    if not hits:
        return None
    p = hits[0]
    try:
        mtime = datetime.datetime.fromtimestamp(
            p.stat().st_mtime, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        mtime = None
    try:
        rel = str(p.relative_to(root))
    except ValueError:
        rel = str(p)
    return {"path": str(p), "rel": rel, "mtime": mtime, "name": p.name}


def _enrich_office_agent(entry: dict) -> dict:
    """Attach dossier + schedule + last wrote for Office staff drawer."""
    name = str(entry.get("name") or "").strip().lower()
    dossier = _OFFICE_AGENT_DOSSIER.get(name)
    if dossier:
        entry["dossier"] = dict(dossier)
        # Citizen name · title (callsign stays in dossier / Callsign field)
        given = dossier.get("given_name") or entry.get("display") or name
        title = dossier.get("title") or ""
        entry["display"] = ("%s · %s" % (given, title)) if title else str(given)
        entry["given_name"] = given
        entry["title"] = title
        wd = str(entry.get("workdir") or "")
        art = _latest_report_artifact(wd, dossier.get("output_glob"))
        if art:
            entry["last_wrote"] = art
        if wd and dossier.get("contract_rel"):
            cpath = os.path.join(wd, dossier["contract_rel"])
            if os.path.isfile(cpath):
                entry["contract_path"] = cpath
    return entry


def _is_city_hall_job(entry: dict, root: str) -> bool:
    """True for L0 government employees (city-wide beat).

    Product-scoped jobs stay on their workdir cabinet only.
    """
    if str(entry.get("kind") or "").lower() != "job":
        return False
    name = str(entry.get("name") or "").strip().lower()
    if name in CITY_HALL_JOB_NAMES:
        return True
    wd = os.path.abspath(str(entry.get("workdir") or "") or "")
    root_abs = os.path.abspath(root)
    # Papers at city root → floor staff
    if wd and wd == root_abs:
        return True
    return False


def _worker_inside_now(w: dict) -> bool:
    """Heuristic: currently working this cabinet (open-drawer signal).

    True when:
      - last_shift outcome is running / in-flight
      - last real shift is recent (hold window — default 45m)
      - next_fire has passed and we're within a post-fire window (still on shift)
      - health is wedged/err with a recent shift (stuck inside, still "in")
    Workers never jump cabinets — workdir binds them; this only answers "busy?"
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    hold = 45 * 60  # seconds — longer than a short single-pass so open plate sticks
    last = w.get("last_shift") or {}
    if not isinstance(last, dict):
        last = {}
    outcome = str(last.get("outcome") or "").lower()
    if outcome in ("running", "in_flight", "active", "work"):
        return True
    ts = _parse_iso(str(last.get("ts") or ""))
    age = (now - ts).total_seconds() if ts is not None else None
    if age is not None and age < hold and outcome not in ("skip",):
        # recent real work (ok / error / no-progress still counts as "was in")
        return True
    fire = _parse_iso(str(w.get("next_fire") or ""))
    if fire is not None and fire <= now:
        # past fire: on shift until next schedule advances or hold from fire time
        if (now - fire).total_seconds() < hold:
            return True
    health = str(w.get("health") or "").lower()
    if health in ("wedged", "err", "error") and age is not None and age < 3 * 3600:
        # stuck in the drawer — still "inside" for UI truth
        return True
    return False


def _inside_since_iso(w: dict) -> Optional[str]:
    """Best-effort start of the current inside stretch (for foyer dwell timers)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    last = w.get("last_shift") or {}
    if not isinstance(last, dict):
        last = {}
    outcome = str(last.get("outcome") or "").lower()
    ts_raw = str(last.get("ts") or "") or None
    ts = _parse_iso(ts_raw or "")
    fire_raw = str(w.get("next_fire") or "") or None
    fire = _parse_iso(fire_raw or "")
    if outcome in ("running", "in_flight", "active", "work") and ts_raw:
        return ts_raw
    if fire is not None and fire <= now and fire_raw:
        return fire_raw
    if ts_raw:
        return ts_raw
    return None


def _inside_now_payload(w: dict, *, kind: str) -> dict:
    """Foyer/cabinet presence — enough for laptop glyph + dwell timer."""
    last = w.get("last_shift") or {}
    if not isinstance(last, dict):
        last = {}
    role = "patrol" if kind == "job" else "worker"
    return {
        "name": w.get("name"),
        "display": w.get("display"),
        "given_name": w.get("given_name"),
        "title": w.get("title"),
        "health": w.get("health"),
        "kind": kind,
        "role": role,
        "next_fire": w.get("next_fire"),
        "inside_since": _inside_since_iso(w),
        "last_shift": {
            "ts": last.get("ts"),
            "outcome": last.get("outcome"),
            "reason": last.get("reason"),
        } if last else None,
    }


def _cabinet_hints(path: str, zone: str) -> List[str]:
    """Soft hints — zone truth for the office floor (pc-155)."""
    hints: List[str] = []
    if zone == "archive":
        hints.append("backup / archive — not a neighborhood")
    if zone == "export":
        hints.append("generated export — edit source, re-run export script")
    if zone == "foreign":
        hints.append(
            "upstream-owned · consumer by default — automations on; "
            "code work → upstream issues"
        )
    return hints


def _skill_frontmatter(text: str) -> Dict[str, str]:
    """Parse leading YAML-ish --- frontmatter from a SKILL.md (name/description)."""
    out: Dict[str, str] = {}
    if not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end < 0:
        return out
    block = text[3:end]
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip().strip("\"'")
        if key in ("name", "description") and val:
            out[key] = val
    return out


def _cabinet_skills(path: str, *, max_n: int = 40) -> List[dict]:
    """Discover cabinet capabilities from ``.claude/skills/<id>/SKILL.md``.

    Skills are capabilities (what can be invoked). Scheduled tasks are separate
    — roster jobs with cron — and may *reference* a skill via ``skill``.
    """
    root = os.path.join(path, ".claude", "skills")
    if not os.path.isdir(root):
        return []
    skills: List[dict] = []
    try:
        names = sorted(
            n for n in os.listdir(root)
            if not n.startswith(".") and os.path.isdir(os.path.join(root, n))
        )
    except OSError:
        return []
    for name in names:
        if len(skills) >= max_n:
            break
        skill_md = os.path.join(root, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        meta: Dict[str, str] = {}
        try:
            with open(skill_md, "r", encoding="utf-8", errors="replace") as fh:
                meta = _skill_frontmatter(fh.read(4000))
        except OSError:
            pass
        skills.append({
            "id": name,
            "name": meta.get("name") or name,
            "description": meta.get("description") or "",
            "path": skill_md,
        })
    return skills


_NON_ADOPTABLE_ZONES = frozenset({"export", "archive", "foreign"})


def _cabinet_adoptable(managed: bool, zone: str) -> bool:
    """Adopt/manage only for unmanaged folders that can become neighborhoods."""
    if managed:
        return False
    return zone not in _NON_ADOPTABLE_ZONES


def adopt_preview(path: str) -> Dict[str, object]:
    """Predict adoption effort from existing file structure (onboarding).

    Unmanaged cabinets: no PC drawers unless instruction files already exist.
    Preview answers: what will be created, what is already there, rough time.
    """
    path = os.path.abspath(path)
    has_agents = os.path.isfile(os.path.join(path, "AGENTS.md"))
    has_claude = os.path.isfile(os.path.join(path, "CLAUDE.md"))
    has_grok = os.path.isfile(os.path.join(path, "GROK.md"))
    workers_dir = os.path.join(path, "workers")
    has_workers = os.path.isdir(workers_dir)
    worker_count = 0
    if has_workers:
        try:
            worker_count = sum(
                1 for n in os.listdir(workers_dir)
                if not n.startswith(".")
                and os.path.isdir(os.path.join(workers_dir, n))
            )
        except OSError:
            worker_count = 0
    depth1 = _quick_entry_count(path)
    estate = estate_of(os.path.basename(path))
    recorded = int((estate or {}).get("recorded") or depth1)
    existing_instr = _cabinet_instruction_drawers(path)

    will_create: List[str] = []
    if not has_agents:
        will_create.append("AGENTS.md (project instructions)")
    # Vendor pointers never auto-planted (pc-425)
    will_create.append(".protocolcity/managed (BluePrint join marker)")
    # pc-489: adopt no longer plants demo-worker by default (opt-in CLI only)
    if has_workers and worker_count > 0:
        will_create.append("keep existing workers/ (%d hire(s))" % worker_count)
    else:
        will_create.append(
            "no worker stubs by default (hire later or CLI --with-demo-worker)"
        )

    # Effort heuristic: structure to write + size of tree to later staff
    score = 0
    if not has_agents:
        score += 1
    # Worker stubs optional — do not inflate manage cost for ticket-only hoods
    if recorded > 200 or depth1 > 40:
        score += 2
    elif recorded > 50 or depth1 > 15:
        score += 1
    if len(existing_instr) >= 2:
        score = max(0, score - 1)  # already has instruction culture

    if has_agents and has_workers and worker_count > 0:
        band, minutes, label = "already", 0, "already structured — manage is a no-op or refresh"
    elif has_agents:
        band, minutes, label = "quick", 1, "about a minute — join marker + desk when desk is up"
    elif score <= 1:
        band, minutes, label = "quick", 1, "about a minute — scaffold project law"
    elif score == 2:
        band, minutes, label = "short", 5, "a few minutes — law + desk join; then fill AGENTS"
    else:
        band, minutes, label = "longer", 15, "longer — large tree; scaffold is fast, staffing later takes time"

    return {
        "has_agents": has_agents,
        "has_workers_dir": has_workers,
        "worker_count": worker_count,
        "depth1_entries": depth1,
        "estate_recorded": recorded,
        "existing_instructions": [d["name"] for d in existing_instr],
        "will_create": will_create,
        "effort": {
            "band": band,           # already | quick | short | longer
            "minutes_est": minutes,
            "label": label,
        },
    }


def office_snapshot(root: str) -> Dict[str, object]:
    """Cabinet office read model — home floor for BluePrint.

    Top-level folders (pc-163 — no zone shelf on the floor):
      managed   = has AGENTS.md
      unmanaged = no AGENTS.md (prospects; Adopt blocked server-side for
                  export/archive/foreign but they share one grey shelf)
    Zone hints are NOT painted on the floor — detection stays an adopt gate,
    not a second taxonomy. Root papers = instruction files only (Obsidian-like).
    """
    root = os.path.abspath(root)
    workers = _workforce_workers()
    hoods = list(neighborhoods(root))
    store_slugs = [_dir_slug(d) for d in hoods]
    # In-flight claims by Owner: — feeds Holding now on staff click.
    holdings_by_owner = _inflight_holdings_by_owner(store_slugs)
    # Three employment shelves:
    #   lane  → cabinet workers (claim tickets; bound to workdir)
    #   job + city-wide beat → L0 City Hall / government (floor)
    #   job + product workdir → cabinet patrols (that shop only)
    by_hood_workers: Dict[str, List[dict]] = {}
    by_hood_patrols: Dict[str, List[dict]] = {}
    city_hall: List[dict] = []
    for w in workers:
        kind = str(w.get("kind") or "").lower()
        aliases = _worker_identity_aliases(w)
        probe = _parse_queue_probe(str(w.get("queue_url") or ""))
        product = probe.get("product") or _product_from_workdir(
            str(w.get("workdir") or ""))
        held = _holdings_for_aliases(aliases, holdings_by_owner)
        entry = {
            "name": w.get("name"),
            "kind": kind if kind else "lane",
            "display": w.get("display") or w.get("name"),
            "health": w.get("health"),
            "next_fire": w.get("next_fire"),
            "last_shift": w.get("last_shift"),
            "workdir": os.path.abspath(w.get("workdir") or ""),
            "schedule": w.get("schedule") or "",
            "identity": w.get("identity") or w.get("name"),
            "model": w.get("model") or "",
            "owned": bool(w.get("owned")),
            "owner": (w.get("owner") or "").strip(),
            "skill": (w.get("skill") or "").strip(),
            "succeeds": (w.get("succeeds") or "").strip(),
            "queue": w.get("queue"),
            "queue_url": w.get("queue_url") or "",
            "product": product,
            "queue_label": probe.get("label") or "",
            "holding": held,
            "holding_count": len(held),
        }
        wd = entry["workdir"]
        if kind == "job":
            if _is_city_hall_job(entry, root):
                entry["role"] = "government"
                entry["beat"] = "city"
                entry["shelf"] = "city_hall"
                city_hall.append(_enrich_office_agent(entry))
            else:
                entry["role"] = "patrol"
                entry["beat"] = "cabinet"
                entry["shelf"] = "patrol"
                if wd:
                    by_hood_patrols.setdefault(wd, []).append(entry)
            continue
        # lane / worker — cannot jump cabinets; only their workdir cabinet
        entry["role"] = "worker"
        entry["beat"] = "cabinet"
        entry["shelf"] = "worker"
        if wd:
            by_hood_workers.setdefault(wd, []).append(entry)

    managed_cabs: List[dict] = []
    unmanaged_cabs: List[dict] = []
    # Parallel desk counts — was the foyer load cliff (N×2 serial HTTP).
    count_by_slug = _store_counts_many(store_slugs)
    # Open-work teasers only for managed cabinets that have a desk store.
    open_work_slugs = [
        _dir_slug(d)
        for d in hoods
        if _cabinet_managed(d)
        and count_by_slug.get(_dir_slug(d)) is not None
    ]
    open_by_slug = _cabinet_open_work_many(open_work_slugs)
    # pc-256: display overlay — applied after adopt/managed use structural zone.
    hidden_slugs = load_hidden_slugs(root)

    for d in hoods:
        name = os.path.basename(d)
        # pc-570 residual of pc-313: must use _dir_slug (hyphenate spaces),
        # not name.lower() — otherwise spaced folders miss open-work counts.
        slug = _dir_slug(d)
        counts = count_by_slug.get(slug)
        abs_d = os.path.abspath(d)
        staff = list(by_hood_workers.get(abs_d, []))
        patrols = list(by_hood_patrols.get(abs_d, []))
        # by_hood_workers is already lane-only; staffed = any lane hire (pc-141).
        zone = zone_of(d, staffed=bool(staff))
        # Floor "managed" = live neighborhood with AGENTS. Generated exports
        # (and archive/foreign) may ship an AGENTS.md for the public repo but
        # must not look like operable cabinets on the Office floor (ship cut /
        # DEMO honesty — edit source, re-run export). Zone still drives adopt.
        managed = _cabinet_managed(d) and zone not in _NON_ADOPTABLE_ZONES
        adoptable = _cabinet_adoptable(managed, zone)
        estate = estate_of(name)
        # Managed cabinets: instruction law + content/vault papers (skills,
        # drafts, story, docs). Unmanaged outskirts: instruction-only if
        # present. export/archive/foreign: shipped instruction files are
        # payload, not city law on this machine — suppress the drawer stack
        # (zone precedes paper, pc-200). Without this guard, WorkLane export
        # AGENTS.md/README/CLAUDE render a full stack indistinguishable from
        # a live managed cabinet.
        md_drawers = (
            _cabinet_all_drawers(d) if managed
            else ([] if zone in _NON_ADOPTABLE_ZONES
                  else _cabinet_instruction_drawers(d))
        )
        preview = adopt_preview(d) if adoptable else None
        inside_workers = [w for w in staff if _worker_inside_now(w)]
        inside_patrols = [w for w in patrols if _worker_inside_now(w)]
        inside = (
            [_inside_now_payload(w, kind="worker") for w in inside_workers]
            + [_inside_now_payload(w, kind="job") for w in inside_patrols]
        )
        access = [{"name": "you", "role": "owner"}]
        for w in staff:
            access.append({
                "name": w.get("name"),
                "role": "worker",
                "kind": w.get("kind") or "lane",
            })
        for p in patrols:
            access.append({
                "name": p.get("name"),
                "role": "patrol",
                "kind": "job",
            })
        backlog = int((counts or {}).get("backlog") or 0) if counts else 0
        # pc-256: display overlay last — never rewrites managed/adoptable/drawers.
        display_zone = "hidden" if slug in hidden_slugs else zone
        cab = {
            "name": name,
            "path": d,
            "slug": slug,
            "zone": display_zone,
            "managed": managed,
            "adoptable": adoptable,
            "role": "managed" if managed else "unmanaged",
            "drawers": md_drawers,
            "drawer_count": len(md_drawers),
            "estate": estate or {"recorded": _quick_entry_count(d), "heap": 0,
                                 "total": _quick_entry_count(d)},
            "store": counts,
            "backlog": backlog,
            "open_work": (open_by_slug.get(slug) or []) if managed else [],
            "workers": staff if managed else [],
            "patrols": patrols if managed else [],
            "agents_visiting": patrols if managed else [],
            # Skills = capabilities (.claude/skills). Scheduled tasks = cron jobs
            # on this cabinet (patrol shelf); accountability via owner.
            "skills": _cabinet_skills(d) if managed else [],
            "scheduled_tasks": (
                [p for p in patrols if p.get("owned") or p.get("schedule")]
                if managed else []
            ),
            "inside_now": inside if managed else [],
            "access": access if managed else [{"name": "you", "role": "owner"}],
            "papers": (
                _peek_papers(d, managed=True) if managed
                else [{"name": x["name"], "kind": "file", "role": x.get("role")}
                      for x in md_drawers]
            ),
            # pc-163: shelves are managed | unmanaged (no second zone taxonomy
            # on the floor). Soft hints still carry export/archive/foreign
            # honesty so generated artifacts are not mistaken for rooms (pc-200).
            "hints": _cabinet_hints(d, zone),
            "flags": [],
            "adopt_preview": preview,
            "desk_href": None,
            "board_href": None,
            "dispatch_href": None,
            "hire_href": None,
        }
        if managed:
            # Suite perimeter: Desk door = D0 room home, never Board (D1).
            cab["desk_href"] = "%s/admin/desk" % DESK.rstrip("/")
            # Board is Desk furniture — available, not advertised as "Desk".
            cab["board_href"] = "%s/admin/tickets/%s" % (
                DESK.rstrip("/"), urllib.parse.quote(slug))
            cab["dispatch_href"] = "%s/?cabinet=%s" % (
                WORKFORCE.rstrip("/"), urllib.parse.quote(name))
            # Hire deep-link (pc-109): Roster opens the hire drawer for this
            # cabinet. Employment write stays on WorkForce (:8797).
            cab["hire_href"] = "%s/?cabinet=%s&workdir=%s&hire=1#hire" % (
                WORKFORCE.rstrip("/"),
                urllib.parse.quote(name),
                urllib.parse.quote(d),
            )
            # Starving only on open businesses. Unstaffed + books = HOME
            # (outskirts under staffing law) — CTA is hire (pc-109), not starve.
            if zone == "main" and backlog > 0 and not staff:
                cab["flags"].append("starving")
            managed_cabs.append(cab)
        else:
            unmanaged_cabs.append(cab)

    # Office Rules — instruction files only (Obsidian-like). PDFs/binaries and
    # other root clutter stay off the floor; open the folder in Finder.
    root_instr = _cabinet_instruction_drawers(root, max_n=_INSTRUCTION_MAX_DRAWERS)
    root_papers: List[dict] = []
    for d in root_instr:
        paper = {
            "name": d["name"],
            "label": d.get("label") or d["name"],
            "kind": "file",
            "path": d["path"],
            "role": d.get("role") or "instruction",
            "readable": True,
        }
        if d.get("pointer"):
            paper["pointer"] = d["pointer"]
        if d.get("diverged"):
            paper["diverged"] = True
        root_papers.append(paper)

    city_name = os.path.basename(root.rstrip(os.sep)) or "City"
    agents_md = os.path.join(root, "AGENTS.md")
    if os.path.isfile(agents_md):
        try:
            with open(agents_md, "r", encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r"^#\s+(.+?)\s*$", line)
                    if m:
                        city_name = m.group(1).split("—")[0].split("-")[0].strip() or city_name
                        break
        except OSError:
            pass

    # Coordination map (pc-206): ATLAS.md pinned on the L0 law shelf. Root
    # first (generic BluePrint cities), else the first managed cabinet that
    # holds one at its own root (this city: ProtocolCity/ATLAS.md — pc-4).
    atlas: Optional[Dict[str, str]] = None
    if os.path.isfile(os.path.join(root, "ATLAS.md")):
        atlas = {"cabinet": "_root", "name": "ATLAS.md"}
    else:
        for cab in managed_cabs:
            cab_name = str(cab.get("name") or "")
            if cab_name and os.path.isfile(
                    os.path.join(root, cab_name, "ATLAS.md")):
                atlas = {"cabinet": cab_name, "name": "ATLAS.md"}
                break

    # Toolkit inventory — the placement rules that govern the L0 shelf.
    toolkit_readme = (
        ".claude/skills/README.md"
        if os.path.isfile(os.path.join(root, ".claude", "skills", "README.md"))
        else None
    )

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "city_root": root,
        "city_name": city_name,
        "desk": DESK,
        "workforce": WORKFORCE,
        # Suite peer door = Desk D0 (/admin/desk), not Board (/admin/tickets/…).
        "desk_href": DESK.rstrip("/") + "/admin/desk",
        # Suite peer door = full Roster D0 (You · staff · hired cabinets).
        # ?scope=floor is an L0 agents deep-link, not the room home.
        "dispatch_href": WORKFORCE.rstrip("/") + "/",
        "city_hall": city_hall,
        "agents": city_hall,
        "managed": managed_cabs,
        "unmanaged": unmanaged_cabs,
        # pc-163: records shelf retired — zone is an adopt gate, not a floor row
        "records": [],
        "scrap": [],
        "root_papers": root_papers,
        # L0 law-shelf pins (pc-206) — the map and the shelf's own rules.
        "atlas": atlas,
        "toolkit_readme": toolkit_readme,
        # L0 city toolkit — Developer/.claude/skills (pc-192).
        "root_skills": _cabinet_skills(root),
        # CITY_FLOW indoor twins — same desk seam the map uses (F1/F7).
        "recent_transitions": recent_transitions(
            _get_json(DESK + "/api/scene") or {}),
    }


def cached_office_snapshot(root: str) -> Dict[str, object]:
    """Short TTL cache so foyer polls feel live without re-walking Desk."""
    root = os.path.abspath(root)
    fresh = (
        _office_cache.get("data") is not None
        and _office_cache.get("root") == root
        and time.time() - float(_office_cache.get("ts") or 0) < _OFFICE_TTL_SEC
    )
    if fresh:
        return _office_cache["data"]  # type: ignore[return-value]
    data = office_snapshot(root)
    _office_cache.update(ts=time.time(), root=root, data=data)
    return data


def manage_cabinet(
    root: str,
    name: str,
    *,
    force: bool = False,
    consumer: bool = False,
    allow_live_desk: bool = False,
) -> Dict[str, object]:
    """Run adopt structure scripts on a top-level folder (onboarding manage).

    ``consumer=True`` (pc-1359): stamp operate-without-adopt for foreign
    clones — no managed marker, no desk join.
    """
    root_p = Path(os.path.abspath(root))
    cab = root_p / name
    if not cab.is_dir():
        return {"ok": False, "error": "no such folder"}
    # Zone for adopt gate: foreign/export/archive only (main vs outskirts both
    # adoptable). Staffed read joins WorkForce by workdir (pc-141).
    # pc-1161: already-managed (force-adopted) cabinets re-enter doctor soft
    # path; zone gate only blocks first-time adopt without --force.
    wf = _get_json(WORKFORCE + "/api/workers") or {}
    cab_workers = [
        w for w in (wf.get("workers") or [])
        if os.path.abspath(w.get("workdir") or "") == os.path.abspath(str(cab))
    ]
    zone = zone_of(str(cab), staffed=_staffed_by_lanes(cab_workers))
    if consumer:
        from protocolcity.adopt import stamp_foreign_consumer

        if _cabinet_managed(str(cab)):
            return {
                "ok": True,
                "already_managed": True,
                "posture": "managed-foreign" if zone == "foreign" else "managed",
                "name": name,
                "path": str(cab),
                "zone": zone,
                "managed": True,
            }
        stamp_foreign_consumer(cab)
        return {
            "ok": True,
            "posture": "foreign-consumer",
            "name": name,
            "path": str(cab),
            "zone": zone,
            "managed": False,
        }
    if (
        zone in _NON_ADOPTABLE_ZONES
        and not force
        and not _cabinet_managed(str(cab))
    ):
        return {
            "ok": False,
            "error": (
                "%s is zone=%s — not adoptable as a neighborhood "
                "(export/archive/foreign stay Not managed; Adopt blocked)" % (name, zone)
            ),
            "zone": zone,
        }
    try:
        from protocolcity.doctor import fix as doctor_fix
        result = doctor_fix(
            root_p,
            cabinet=name,
            force=force,
            with_desk=True,
            allow_live_desk=allow_live_desk,
        )
        # Flatten for Office /api/manage consumers (ok + created at top level)
        adopt = result.get("adopt") if isinstance(result, dict) else None
        out: Dict[str, object] = {
            "ok": bool(result.get("ok")),
            "doctor": True,
            "before": result.get("before"),
            "after": result.get("after"),
            "actions": result.get("actions"),
        }
        if isinstance(adopt, dict):
            out.update({
                "already_managed": adopt.get("already_managed"),
                "name": adopt.get("name") or name,
                "path": adopt.get("path") or str(cab),
                "created": adopt.get("created") or [],
                "desk": adopt.get("desk"),
                "store_slug": adopt.get("store_slug"),
                "prefix": adopt.get("prefix"),
            })
        else:
            out["name"] = name
            out["path"] = str(cab)
            out["created"] = []
        return out
    except ImportError:
        try:
            from protocolcity.adopt import adopt_cabinet
            return adopt_cabinet(root_p, name, force=force, sample_ticket=False)
        except ImportError:
            # Fallback without package import — minimal AGENTS only
            agents = cab / "AGENTS.md"
            if agents.exists() and not force:
                return {"ok": True, "already_managed": True, "name": name, "path": str(cab)}
            agents.write_text(

                "# %s — Cabinet Law\n\nAdopted locally (minimal). Fill in project constraints.\n" % name,

                encoding="utf-8",

            )
            return {"ok": True, "already_managed": False, "name": name, "path": str(cab),
                    "created": ["AGENTS.md"], "desk": None}


# pc-94: THE SEARCHLIGHT — server-side survey find (never ship 30k to the page).
FIND_MAX_HITS = 40


def find_in_survey(q: str, limit: int = FIND_MAX_HITS) -> dict:
    """Name-substring search over the survey index (case-insensitive).

    Returns hits as {path, name, kind, depth}; heaps in skipped[] are NOT
    searchable — when the query matches a known heap name/label, skipped_hint
    carries the honest empty-state line (e.g. node_modules · 50,000+ · not surveyed).
    """
    q = (q or "").strip()
    try:
        lim = max(1, min(int(limit), FIND_MAX_HITS))
    except (TypeError, ValueError):
        lim = FIND_MAX_HITS
    if not q:
        return {
            "q": "",
            "hits": [],
            "limit": lim,
            "truncated": False,
            "skipped_hint": None,
            "survey": _survey_public_summary(),
        }
    q_low = q.lower()
    with _survey_lock:
        children_of = _survey_state.get("children_of") or {}
        skipped = list(_survey_state.get("skipped") or [])
        status = str(_survey_state.get("status") or "idle")
        entries = int(_survey_state.get("entries") or 0)

    # Heap empty-state: match basename or label, never return heap contents.
    skipped_hint = None
    for sk in skipped:
        path = str(sk.get("path") or "")
        base = path.rsplit("/", 1)[-1] if path else ""
        label = str(sk.get("label") or "")
        if (q_low in base.lower()) or (q_low in label.lower()):
            skipped_hint = {
                "path": path,
                "count": int(sk.get("count") or 0),
                "label": label or ("%s · not surveyed" % (base or "heap")),
            }
            break

    scored: List[tuple] = []  # (rank, path_len, path, hit)
    for rel, kids in children_of.items():
        for c in kids:
            name = str(c.get("name") or "")
            if not name:
                continue
            n_low = name.lower()
            if q_low not in n_low:
                continue
            path = (rel + "/" + name) if rel else name
            segs = path.split("/") if path else []
            depth = len(segs)
            kind = str(c.get("kind") or "file")
            # Prefer exact name, then prefix, then substring; shorter paths first.
            if n_low == q_low:
                rank = 0
            elif n_low.startswith(q_low):
                rank = 1
            else:
                rank = 2
            hit = {
                "path": path,
                "name": name,
                "kind": kind,
                "depth": depth,
            }
            # pc-101: ftype rides the hit so searchlight can draw the line.
            if kind == "file":
                ft = c.get("ftype")
                hit["ftype"] = str(ft) if ft else file_type(name)
            scored.append((rank, depth, len(path), path, hit))

    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3].lower()))
    hits = [t[4] for t in scored[:lim]]
    truncated = len(scored) > lim
    return {
        "q": q,
        "hits": hits,
        "limit": lim,
        "truncated": truncated,
        "match_count": len(scored),
        "skipped_hint": skipped_hint,
        "survey": {
            "status": status,
            "entries": entries,
        },
    }


def _listing_from_survey(root: str, rel_posix: str) -> Optional[dict]:
    """Build a parcel_listing-shaped dict from the survey cache, or None."""
    with _survey_lock:
        if _survey_state.get("city_root") and (
                os.path.realpath(str(_survey_state["city_root"]))
                != os.path.realpath(root)):
            return None
        children_of = _survey_state.get("children_of") or {}
        dirs = _survey_state.get("dirs") or {}
        if rel_posix not in children_of and rel_posix not in dirs:
            return None
        kids_raw = list(children_of.get(rel_posix) or [])
        meta = dict(dirs.get(rel_posix) or {})
        surveyed_at = _survey_state.get("surveyed_at")
    # pc-101: backfill ftype on older survey caches (extension-only, cheap).
    kids: List[dict] = []
    for c in kids_raw:
        if c.get("kind") == "file" and not c.get("ftype"):
            c = dict(c)
            c["ftype"] = file_type(str(c.get("name") or ""))
        kids.append(c)
    segs = rel_posix.split("/") if rel_posix else []
    abs_path = (os.path.join(root, *segs) if segs
                else os.path.realpath(root))
    dir_count = sum(1 for c in kids if c.get("kind") == "dir")
    file_count = sum(1 for c in kids if c.get("kind") == "file")
    return {
        "name": segs[-1] if segs else os.path.basename(root.rstrip("/")) or root,
        "rel": rel_posix,
        "path": abs_path,
        "depth": len(segs),
        "dir_count": dir_count,
        "file_count": file_count,
        "founded": bool(meta.get("founded",
                                 os.path.isfile(os.path.join(abs_path, "AGENTS.md"))
                                 if os.path.isdir(abs_path) else False)),
        "children": kids,
        "source": "survey",
        "surveyed_at": surveyed_at,
        "survey_stopped": bool(meta.get("survey_stopped")),
    }


def _child_name_set(listing: dict) -> set:
    return {str(c.get("name") or "") for c in (listing.get("children") or [])
            if c.get("name")}


def _drift_summary(survey_listing: dict, walked: dict) -> str:
    """One-line cheap set-diff of child names (and counts when useful)."""
    s_names = _child_name_set(survey_listing)
    w_names = _child_name_set(walked)
    added = sorted(w_names - s_names)
    removed = sorted(s_names - w_names)
    parts: List[str] = []
    if added:
        parts.append("+" + ", ".join(added[:5])
                     + ("…" if len(added) > 5 else ""))
    if removed:
        parts.append("−" + ", ".join(removed[:5])
                     + ("…" if len(removed) > 5 else ""))
    sc = len(s_names)
    wc = len(w_names)
    if sc != wc and not parts:
        parts.append("children %d → %d" % (sc, wc))
    elif sc != wc:
        parts.append("(%d → %d)" % (sc, wc))
    return "; ".join(parts) if parts else "children changed"


def parcel_response(root: str, rel: str, *, live: bool = False):
    """Parcel listing with trust gradient (pc-95).

    live=False: serve survey cache when present (source=survey), else walk.
    live=True: always walk, mark session-verified, attach drift vs survey.
    Returns (dict, None) or (None, http_status).
    """
    segs = parse_parcel_rel(rel)
    if segs is None:
        return None, 403
    rel_posix = "/".join(segs)

    if not live:
        cached = _listing_from_survey(root, rel_posix)
        if cached is not None:
            # pc-111: the law maps the room — annotate even survey-grade rows.
            return attach_folder_map(root, rel_posix, cached), None

    listing, err = parcel_listing(root, rel)
    if err is not None:
        return None, err
    listing = dict(listing)
    listing["source"] = "walked"
    listing = attach_folder_map(root, rel_posix, listing)
    with _survey_lock:
        _walked_this_session.add(rel_posix)
    # Drift: live walk of a previously surveyed dir disagrees on children.
    prior = _listing_from_survey(root, rel_posix)
    if prior is not None:
        if _child_name_set(prior) != _child_name_set(listing):
            listing["drift"] = True
            listing["drift_summary"] = _drift_summary(prior, listing)
        else:
            listing["drift"] = False
    return listing, None


def _load_survey_cache(root: str) -> bool:
    """Load survey JSON from disk into memory. True when loaded for this root."""
    path = SURVEY_CACHE_PATH
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    cache_root = str(data.get("city_root") or "")
    if cache_root and os.path.realpath(cache_root) != os.path.realpath(root):
        return False
    with _survey_lock:
        _survey_state.update({
            "status": "done",
            "surveyed_at": data.get("surveyed_at"),
            "city_root": cache_root or root,
            "parcels": int(data.get("parcels") or 0),
            "entries": int(data.get("entries") or 0),
            "skipped": list(data.get("skipped") or []),
            "children_of": dict(data.get("children_of") or {}),
            "dirs": dict(data.get("dirs") or {}),
            "duration_ms": int(data.get("duration_ms") or 0),
            "error": None,
        })
    return True


def _save_survey_cache(root: str) -> None:
    """Persist current survey to logs/ (gitignored). Best-effort."""
    try:
        os.makedirs(os.path.dirname(SURVEY_CACHE_PATH), exist_ok=True)
        with _survey_lock:
            payload = {
                "city_root": root,
                "surveyed_at": _survey_state.get("surveyed_at"),
                "parcels": _survey_state.get("parcels"),
                "entries": _survey_state.get("entries"),
                "skipped": _survey_state.get("skipped"),
                "children_of": _survey_state.get("children_of"),
                "dirs": _survey_state.get("dirs"),
                "duration_ms": _survey_state.get("duration_ms"),
            }
        tmp = SURVEY_CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"))
        os.replace(tmp, SURVEY_CACHE_PATH)
    except OSError:
        pass


def _run_survey_walk(root: str) -> None:
    """Bounded walk — never raises out of the thread; writes state + cache."""
    t0 = time.time()
    root_real = os.path.realpath(root)
    atlas: set = set()
    try:
        atlas = set(parse_atlas_registered_paths(root))
    except Exception:
        atlas = set()

    children_of: Dict[str, List[dict]] = {}
    dirs: Dict[str, dict] = {}
    skipped: List[dict] = []
    entry_count = 0
    parcel_count = 0
    hit_entry_cap = False

    # BFS queue: (abs_path, rel_posix, depth)
    queue: List[tuple] = [(root_real, "", 0)]
    dirs[""] = {
        "founded": os.path.isfile(os.path.join(root_real, "AGENTS.md")),
        "survey_stopped": False,
    }

    while queue:
        if entry_count >= SURVEY_MAX_ENTRIES:
            hit_entry_cap = True
            break
        abs_path, rel, depth = queue.pop(0)
        try:
            listing = sorted(os.scandir(abs_path), key=lambda e: e.name.lower())
        except OSError:
            children_of.setdefault(rel, [])
            continue

        kids: List[dict] = []
        stop_here = depth >= SURVEY_MAX_DEPTH

        for ent in listing:
            if entry_count >= SURVEY_MAX_ENTRIES:
                hit_entry_cap = True
                stop_here = True
                break
            name = ent.name
            # Heaps first (including hidden heaps like .venv) — count, don't enter.
            if name in SURVEY_HEAPS:
                try:
                    if ent.is_dir(follow_symlinks=False):
                        cnt = _count_heap_entries(ent.path)
                        sk_path = (rel + "/" + name) if rel else name
                        if cnt >= SURVEY_HEAP_COUNT_CAP:
                            count_txt = "{:,}+".format(SURVEY_HEAP_COUNT_CAP)
                        else:
                            count_txt = "{:,}".format(cnt)
                        skipped.append({
                            "path": sk_path,
                            "count": cnt,
                            "label": "%s · %s files · not surveyed" % (
                                name, count_txt),
                        })
                except OSError:
                    pass
                continue
            # Hidden names: existing exclusion — never listed, never entered.
            if name.startswith("."):
                continue
            try:
                is_dir = ent.is_dir(follow_symlinks=False)
                is_file = ent.is_file(follow_symlinks=False)
            except OSError:
                continue
            if not is_dir and not is_file:
                continue  # skip sockets/FIFOs/etc.

            child_rel = (rel + "/" + name) if rel else name
            child_depth = depth + 1
            entry_count += 1

            if is_dir:
                parcel_count += 1
                founded = False
                try:
                    founded = os.path.isfile(os.path.join(ent.path, "AGENTS.md"))
                except OSError:
                    pass
                # Immediate non-hidden child count (cheap).
                try:
                    with os.scandir(ent.path) as it:
                        n_entries = sum(
                            1 for e in it
                            if not e.name.startswith(".")
                            and e.name not in SURVEY_HEAPS
                        )
                except OSError:
                    n_entries = 0
                child = {
                    "name": name,
                    "kind": "dir",
                    "entries": n_entries,
                    "founded": founded,
                }
                kids.append(child)
                dirs[child_rel] = {
                    "founded": founded,
                    "survey_stopped": False,
                }
                if not stop_here and child_depth <= SURVEY_MAX_DEPTH:
                    queue.append((ent.path, child_rel, child_depth))
                elif stop_here or child_depth > SURVEY_MAX_DEPTH:
                    dirs[child_rel]["survey_stopped"] = True
                    child["survey_stopped"] = True
            else:
                instr = is_instruction_class(name)
                child = {
                    "name": name, "kind": "file", "ftype": file_type(name),
                }
                if instr:
                    child["instruction"] = True
                    child["atlas_sealed"] = child_rel in atlas
                kids.append(child)

        kids.sort(key=lambda c: (0 if c.get("kind") == "dir" else 1,
                                 str(c.get("name") or "").lower()))
        children_of[rel] = kids
        if stop_here and rel in dirs:
            dirs[rel]["survey_stopped"] = True
            # Mark for consumers when this directory was the depth ceiling.
            if depth >= SURVEY_MAX_DEPTH:
                dirs[rel]["stop_reason"] = "max depth"
        if hit_entry_cap and rel in dirs:
            dirs[rel]["survey_stopped"] = True
            dirs[rel]["stop_reason"] = "entry cap"

        # Live progress for the onboarding census line.
        with _survey_lock:
            _survey_state["parcels"] = parcel_count
            _survey_state["entries"] = entry_count
            _survey_state["skipped"] = list(skipped)

    duration_ms = int((time.time() - t0) * 1000)
    surveyed_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    with _survey_lock:
        _survey_state.update({
            "status": "done",
            "surveyed_at": surveyed_at,
            "city_root": root,
            "parcels": parcel_count,
            "entries": entry_count,
            "skipped": skipped,
            "children_of": children_of,
            "dirs": dirs,
            "duration_ms": duration_ms,
            "error": None,
        })
    _save_survey_cache(root)


def start_survey(root: str, *, force: bool = False) -> dict:
    """Start a background survey thread (or return current status).

    force=True always re-walks (POST /api/survey). force=False loads cache
    first and only walks when missing. Never blocks the caller on the walk.
    """
    global _survey_thread
    with _survey_lock:
        alive = _survey_thread is not None and _survey_thread.is_alive()
        if alive:
            return _survey_public_summary()

    if not force and _load_survey_cache(root):
        return _survey_public_summary()

    with _survey_lock:
        alive = _survey_thread is not None and _survey_thread.is_alive()
        if alive:
            return _survey_public_summary()
        _survey_state["status"] = "running"
        _survey_state["error"] = None
        if force:
            # Keep last counts visible while re-walking.
            pass
        else:
            _survey_state["parcels"] = 0
            _survey_state["entries"] = 0
            _survey_state["skipped"] = []

    def _target() -> None:
        try:
            _run_survey_walk(root)
        except Exception as exc:  # noqa: BLE001 — thread must not die silent
            with _survey_lock:
                _survey_state["status"] = "stale"
                _survey_state["error"] = str(exc)

    t = threading.Thread(target=_target, name="citylens-survey", daemon=True)
    with _survey_lock:
        _survey_thread = t
    t.start()
    return _survey_public_summary()


def run_survey_sync(root: str) -> dict:
    """Synchronous survey for verification / CLI — blocks until done."""
    with _survey_lock:
        _survey_state["status"] = "running"
        _survey_state["parcels"] = 0
        _survey_state["entries"] = 0
        _survey_state["skipped"] = []
        _survey_state["error"] = None
    _run_survey_walk(root)
    return _survey_public_summary()


def _ticket_link(desk: str, tid: str) -> str:
    """Suite perimeter: ticket doors land on Desk D0 with the work-order drawer."""
    base = (desk or "").rstrip("/")
    return "%s/admin/desk?open=%s" % (base, urllib.parse.quote(str(tid)))


def _pri_cls(p: int) -> str:
    return {1: "err", 2: "amber"}.get(p, "")


def _fmt_secs(secs: int) -> str:
    """Compact human duration for the burn tile: 3.3h · 25m · 40s."""
    if secs >= 3600:
        return "%.1fh" % (secs / 3600.0)
    if secs >= 60:
        return "%dm" % (secs // 60)
    return "%ds" % secs


def dispatch_vitals() -> Dict[str, object]:
    """City-vitals for the tile strip (pc-132): RENDER, never recompute.

    Two live rooms, fetched server-side with short timeouts; either may be
    down. Returns tile-ready values plus `*_up` flags so the strip shows a
    dim 'carrier down' tile instead of a traceback (tp-139 doctrine: engines
    compute facts, dashboards render them).

      stuck     — workers whose Dispatch report verdict is wedged/faulting
      burn      — top-2 vendors by busy_secs from the report capacity[] list,
                  formatted "claude 3.3h · python 25m"
      attention — the desk's /api/dev/attention count ("needs founder")
    """
    vit: Dict[str, object] = {"report_up": False, "attention_up": False,
                              "stuck": 0, "burn": "", "attention": 0}
    report = _get_json("%s/api/report?days=7" % WORKFORCE, timeout=3)
    if report is not None:
        vit["report_up"] = True
        vit["stuck"] = sum(
            1 for w in (report.get("workers") or [])
            if isinstance(w, dict) and w.get("verdict") in ("wedged", "faulting"))
        cap = [c for c in (report.get("capacity") or []) if isinstance(c, dict)]
        cap.sort(key=lambda c: c.get("busy_secs") or 0, reverse=True)
        vit["burn"] = " · ".join(
            "%s %s" % (c.get("vendor") or "?", _fmt_secs(int(c.get("busy_secs") or 0)))
            for c in cap[:2])
    attention = _get_json("%s/api/dev/attention" % DESK, timeout=3)
    if attention is not None:
        vit["attention_up"] = True
        try:
            vit["attention"] = int(attention.get("count") or 0)
        except (TypeError, ValueError):
            vit["attention"] = 0
    return vit


def render_records(root: str) -> str:
    """Office D1 Overview bench (pc-183) — brief + join tables (ex-ledger).

    Citizen name is Overview; `/records` remains a back-compat alias URL.
    Not a suite peer and not a D2 annex. Chrome = ← Office. Geography stays
    on /map; the plat elevation scene is retired.
    """
    snap = cached_snapshot(root)
    hoods: List[dict] = snap["neighborhoods"]  # type: ignore[assignment]
    total_backlog = sum((h["store"] or {}).get("backlog", 0) for h in hoods)
    total_workers = sum(len(h["workers"]) for h in hoods)
    b: Dict[str, object] = snap["brief"]  # type: ignore[assignment]
    alerts: List[str] = snap["alerts"]  # type: ignore[assignment]
    decisions: List[dict] = b["decisions"]  # type: ignore[assignment]
    stale: List[dict] = b["stale_inflight"]  # type: ignore[assignment]
    shipped: List[dict] = b["shipped"]  # type: ignore[assignment]
    needs_you = len(alerts) + len(decisions) + len(stale)

    out = ["<!doctype html><meta charset='utf-8'><title>ProtocolCity — Office · Overview</title>",
           "<style>%s</style>" % CSS,
           "<header><h1>OVERVIEW <small>· Office bench — "
           "<a href='/'>← Office</a> · %s</small></h1></header>"
           % html.escape(str(snap["city_root"]))]

    daemon = snap["daemon"]
    out.append("<div class='tiles'>")
    out.append("<div class='tile'><div class='n cy'>%d</div><div class='l'>projects</div></div>"
               % len(hoods))
    out.append("<div class='tile'><div class='n'>%d</div><div class='l'>backlog citywide</div></div>"
               % total_backlog)
    out.append("<div class='tile'><div class='n'>%d</div><div class='l'>workers employed</div></div>"
               % total_workers)
    out.append("<div class='tile'><div class='n %s'>●</div><div class='l'>workforce daemon %s</div></div>"
               % ("ok" if daemon == "running" else "err", html.escape(str(daemon))))
    out.append("<div class='tile'><div class='n %s'>%s</div><div class='l'>needs you</div></div>"
               % ("amber" if needs_you else "ok", needs_you or "✓"))
    out.append("<div class='tile'><div class='n %s'>%d</div><div class='l'>shipped, last %dh</div></div>"
               % ("ok" if shipped else "dim", len(shipped), b["window_hours"]))
    # pc-132: city-vitals from the two live rooms — render, never recompute
    # (tp-139). Each tile is the door; the room is the diagnosis. Seam down →
    # dim 'carrier down', never a traceback, never a blocked page.
    vit = dispatch_vitals()
    wf_url = html.escape(str(snap["workforce"]))
    if vit["report_up"]:
        stuck = vit["stuck"]  # type: ignore[assignment]
        # pc-161: vitals door to D0 Dispatch home — not /report as a peer room
        out.append("<div class='tile'><div class='n %s'><a href='%s'>%s</a></div>"
                   "<div class='l'>workers stuck · Roster</div></div>"
                   % ("err" if stuck else "ok", wf_url, stuck if stuck else "✓"))
        out.append("<div class='tile'><div class='n'><a href='%s'>%s</a></div>"
                   "<div class='l'>vendor burn 7d · Roster</div></div>"
                   % (wf_url, html.escape(str(vit["burn"]) or "—")))
    else:
        out.append("<div class='tile'><div class='n dim'>—</div>"
                   "<div class='l'>workforce · carrier down</div></div>")
    if vit["attention_up"]:
        att = vit["attention"]  # type: ignore[assignment]
        # pc-161: door to D0 Desk — not /admin/attention as a peer room
        out.append("<div class='tile'><div class='n %s'><a href='%s'>%s</a></div>"
                   "<div class='l'>needs founder · Desk</div></div>"
                   % ("amber" if att else "ok", html.escape(str(snap["desk"])),
                      att if att else "✓"))
    else:
        out.append("<div class='tile'><div class='n dim'>—</div>"
                   "<div class='l'>desk · carrier down</div></div>")
    out.append("</div>")

    out.append("<p class='dim'>D0 rooms: <a href='/'>Office</a> · "
               "<a href='%s'>Desk</a> · <a href='%s'>Roster</a> · "
               "geography annex: <a href='/map'>street map</a></p>"
               % (html.escape(str(snap["desk"])), html.escape(str(snap["workforce"]))))

    desk = str(snap["desk"])
    out.append("<h2>Projects</h2>")
    out.append("<table><tr><th></th><th>project</th><th>zone</th>"
               "<th>work (backlog / doing / review)</th>"
               "<th>workers</th><th>last commit</th><th>flags</th></tr>")
    for h in hoods:
        st = h["store"]
        if st is None:
            work = "<span class='dim'>no ticket store</span>"
            name_cell = ("<strong>%s</strong><br><span class='dim'>%s</span>"
                         % (html.escape(h["name"]), html.escape(h["path"])))
        else:
            link = "%s/admin/tickets/%s" % (snap["desk"], h["slug"])
            work = ("<a href='%s'><span class='amber'>%d</span></a> / %d / %d"
                    % (html.escape(link), st.get("backlog", 0),
                       st.get("in_progress", 0), st.get("in_review", 0)))
            # Project name doors to that store's Desk board (D1 of Desk) —
            # /hood/<name> room pages are retired.
            name_cell = ("<a href='%s'><strong>%s</strong></a><br>"
                         "<span class='dim'>%s</span>"
                         % (html.escape(link), html.escape(h["name"]),
                            html.escape(h["path"])))
        ws = h["workers"]
        if ws:
            chips = " ".join(
                "<span class='%s'>●</span> <a href='%s/worker/%s'>%s</a>"
                % ({"ok": "ok", "err": "err", "amber": "amber"}.get(w.get("health", ""), "dim"),
                   html.escape(str(snap["workforce"])), html.escape(w["name"]),
                   html.escape(w["name"]))
                for w in ws)
        else:
            chips = "<span class='dim'>none</span>"
        git = h["git"]
        commit = ("<span class='dim'>%s</span> %s" % (_ago(git["when"]),
                  html.escape(git["subject"][:60])) if git["when"]
                  else "<span class='dim'>—</span>")
        dot = ("<span class='amber'>●</span>" if h["flags"] else "<span class='ok'>●</span>")
        flags = "<br>".join("<span class='amber'>%s</span>" % html.escape(f)
                            for f in h["flags"]) or "<span class='dim'>—</span>"
        out.append("<tr><td>%s</td><td>%s</td>"
                   "<td><span class='tag'>%s</span></td>"
                   "<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                   % (dot, name_cell, html.escape(str(h.get("zone") or "?")),
                      work, chips, commit, flags))
    out.append("</table>")

    out.append("<h2>The brief — what needs you</h2>")
    if not needs_you:
        out.append("<p class='ok'>✓ nothing needs you — no waiting decisions, "
                   "no stale claims, all surfaces up</p>")
    for a in alerts:
        out.append("<p class='err'>⚑ %s</p>" % html.escape(a))
    if decisions:
        out.append("<table><tr><th>decision waiting</th><th>project</th>"
                   "<th>p</th><th>quiet</th><th>title</th></tr>")
        for d in decisions:
            out.append("<tr><td><a href='%s'>%s</a></td>"
                       "<td><span class='tag'>%s</span></td>"
                       "<td class='%s'>P%d</td><td class='dim'>%s</td><td>%s</td></tr>"
                       % (html.escape(_ticket_link(desk, str(d["id"]))),
                          html.escape(str(d["id"])), html.escape(d["store"]),
                          _pri_cls(d["priority"]), d["priority"],
                          html.escape(_ago(d["updated_at"])),
                          html.escape(d["title"][:90])))
        out.append("</table>")
    if stale:
        out.append("<table><tr><th>stale in-flight (&ge;%dm quiet)</th><th>project</th>"
                   "<th>status</th><th>owner</th><th>quiet for</th><th>title</th></tr>"
                   % b["stale_minutes"])
        for s in stale:
            out.append("<tr><td><a href='%s'>%s</a></td>"
                       "<td><span class='tag'>%s</span></td><td>%s</td>"
                       "<td class='amber'>%s</td><td class='amber'>%s</td><td>%s</td></tr>"
                       % (html.escape(_ticket_link(desk, str(s["id"]))),
                          html.escape(str(s["id"])), html.escape(s["store"]),
                          html.escape(s["status"]),
                          html.escape(s["owner"] or "no owner marker"),
                          html.escape(_ago(s["updated_at"])),
                          html.escape(s["title"][:90])))
        out.append("</table>")

    out.append("<h2>The brief — shipped, last %dh</h2>" % b["window_hours"])
    if shipped:
        out.append("<table><tr><th>closed</th><th>project</th><th>when</th>"
                   "<th>title</th></tr>")
        for s in shipped[:20]:
            out.append("<tr><td><a href='%s'>%s</a></td>"
                       "<td><span class='tag'>%s</span></td>"
                       "<td class='dim'>%s</td><td>%s</td></tr>"
                       % (html.escape(_ticket_link(desk, str(s["id"]))),
                          html.escape(str(s["id"])), html.escape(s["store"]),
                          html.escape(_ago(s["closed_at"])),
                          html.escape(s["title"][:90])))
        out.append("</table>")
        if len(shipped) > 20:
            out.append("<p class='dim'>… and %d more on the Tickets dashboard</p>"
                       % (len(shipped) - 20))
    else:
        out.append("<p class='dim'>nothing closed in the window</p>")

    out.append("<footer>Office Overview — the brief and join tables. "
               "Work orders live on <a href='%s'>Desk</a>; employment on "
               "<a href='%s'>Roster</a>; cabinets on <a href='/'>Office</a>. "
               "Street geography (optional) is the <a href='/map'>map annex</a>. "
               "Rendered %s.</footer>"
               % (html.escape(str(snap["desk"])), html.escape(str(snap["workforce"])),
                  html.escape(str(snap["generated_at"]))))
    # Live refresh (pc-34): fetch-poll and swap the body in place — unlike the
    # old <meta refresh>, this preserves scroll position and keeps the page
    # readable while it updates.
    out.append("<script>setInterval(async()=>{try{"
               "const t=await(await fetch('/overview',{cache:'no-store'})).text();"
               "const d=new DOMParser().parseFromString(t,'text/html');"
               "document.body.replaceChildren(...d.body.childNodes);"
               "}catch(e){}},30000)</script>")
    return "".join(out)


def render(root: str) -> str:
    """Back-compat alias — ledger/classic content now lives at /overview."""
    return render_records(root)


class _Handler(BaseHTTPRequestHandler):
    city_root = ""

    def _send(self, code: int, ctype: str, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> bytes:
        try:
            n = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            n = 0
        if n <= 0:
            return b""
        return self.rfile.read(n)

    def do_GET(self) -> None:  # noqa: N802
        # pc-62: /api/open is POST-only
        if self.path == "/api/open" or self.path.startswith("/api/open?"):
            self.send_response(405)
            self.send_header("Content-Type", "application/json")
            self.send_header("Allow", "POST")
            self.end_headers()
            self.wfile.write(b'{"error":"method not allowed; use POST"}')
            return
        path_only = (self.path or "").split("?", 1)[0]
        # API-only mode: census process is not a second human front door.
        if API_ONLY and not path_only.startswith("/api/"):
            msg = (
                b'{"ok":false,"error":"citylens HTML lumber disabled '
                b'(CITYLENS_API_ONLY); open BluePrint suite at '
                b'http://127.0.0.1:8801/","api":"/api/city"}'
            )
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        if self.path == "/" or self.path.startswith("/?"):
            # Lumber: Office foyer HTML — do not polish; suite :8801 is the door.
            try:
                with open(OFFICE_HTML, "r", encoding="utf-8") as fh:
                    body = fh.read()
            except OSError:
                try:
                    with open(MAP_HTML, "r", encoding="utf-8") as fh:
                        body = fh.read()
                except OSError:
                    body = render(self.city_root)
            ctype, code = "text/html; charset=utf-8", 200
        elif self.path == "/map" or self.path.startswith("/map?"):
            # Lumber: street map annex — radial lives on suite /skin.
            try:
                with open(MAP_HTML, "r", encoding="utf-8") as fh:
                    body = fh.read()
            except OSError:
                body = render(self.city_root)
            ctype, code = "text/html; charset=utf-8", 200
        elif self.path == "/plat" or self.path.startswith("/plat?"):
            # Retired: elevation plat superseded by Office home + map annex.
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        elif self.path == "/proto/map" or self.path.startswith("/proto/map?"):
            # graduated (pc-57): old prototype links land on the room
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        elif self.path == "/overview" or self.path.startswith("/overview?"):
            # Office D1 Overview (pc-183) — brief + join tables
            body, ctype, code = (
                render_records(self.city_root), "text/html; charset=utf-8", 200)
        elif self.path == "/records" or self.path.startswith("/records?"):
            # Back-compat alias → same Overview bench
            body, ctype, code = (
                render_records(self.city_root), "text/html; charset=utf-8", 200)
        elif self.path == "/classic" or self.path.startswith("/classic?"):
            # Legacy ledger URL → Office Overview
            self.send_response(302)
            self.send_header("Location", "/overview")
            self.end_headers()
            return
        elif self.path.startswith("/hood/"):
            # Retired neighborhood print pages — cabinets live on Office;
            # geography descend lives on the map annex.
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        elif self.path == "/api/city" or self.path.startswith("/api/city?"):
            # ?light=1 — Map bootstrap: folders + store counts, no brief/desk wait
            qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query or "")
            light_raw = (qs.get("light") or qs.get("map") or ["0"])[0]
            light = str(light_raw).lower() in ("1", "true", "yes", "map")
            body = json.dumps(
                cached_snapshot(self.city_root, light=light), indent=1
            )
            ctype, code = "application/json", 200
        elif self.path == "/api/generation" or self.path.startswith("/api/generation?") \
                or self.path == "/api/pulse" or self.path.startswith("/api/pulse?"):
            # LIVE-B3 (pc-279): tokens only for suite pulse bus
            body = json.dumps(
                {"ok": True, **city_generation_token(self.city_root)}, indent=1)
            ctype, code = "application/json", 200
        elif self.path == "/api/office":
            body = json.dumps(cached_office_snapshot(self.city_root), indent=1)
            ctype, code = "application/json", 200
        elif self.path == "/api/office/tape" or self.path.startswith("/api/office/tape?"):
            # Lightweight CITY_FLOW seam — Desk recent_transitions only (no
            # full Office walk). Office polls this every few seconds so
            # founder filings animate as paper-drops without a 30s wait.
            scene = _get_json(DESK + "/api/scene") or {}
            tape = {
                "generated_at": datetime.datetime.now(datetime.timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "recent_transitions": recent_transitions(scene),
            }
            body = json.dumps(tape, indent=1)
            ctype, code = "application/json", 200
        elif path_only == "/api/you-attention" or self.path.startswith(
                "/api/you-attention?"):
            # Host-debug same-origin seam (tp-135 / pc-216). Suite :8801 calls
            # you_attention() in-process (pc-574) — this branch is lumber only.
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query or "")
            include = (qs.get("include_snoozed") or ["0"])[0]
            body = json.dumps(
                you_attention(
                    include_snoozed=str(include).lower() in ("1", "true", "yes")
                )
            )
            ctype, code = "application/json", 200
        elif self.path.startswith("/api/cabinet-md"):
            # Office reader: instruction + content MD under a cabinet (local only).
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query or "")
            cab = (qs.get("cabinet") or qs.get("name") or [""])[0]
            fn = (qs.get("file") or qs.get("md") or [""])[0]
            data = read_cabinet_md(self.city_root, cab, fn)
            if data is None:
                body, ctype, code = (
                    json.dumps({"error": "not found or not allowed"}),
                    "application/json", 404)
            else:
                body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path.startswith("/api/file-md"):
            # Map / suite inspect: city-root-relative MD body (depth-capped).
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query or "")
            rel = (qs.get("rel") or qs.get("path") or qs.get("file") or [""])[0]
            data = read_city_file_md(self.city_root, rel)
            if data is None:
                body, ctype, code = (
                    json.dumps({"error": "not found or not allowed"}),
                    "application/json", 404)
            else:
                body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path.startswith("/api/holdings/") or self.path.startswith(
                "/api/worker-load/"):
            # Worker click: holding (Owner: claims) + ready teaser for queue clear.
            prefix = ("/api/holdings/" if self.path.startswith("/api/holdings/")
                      else "/api/worker-load/")
            who = urllib.parse.unquote(
                self.path[len(prefix):].split("?")[0].strip("/"))
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", who or ""):
                body, ctype, code = (
                    json.dumps({"ok": False, "error": "bad worker id"}),
                    "application/json", 400)
            else:
                data = worker_desk_load(who, self.city_root)
                body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path.startswith("/api/ticket/"):
            # pc-126 follow-up: tickets render IN the map's UI — the lens
            # proxies the desk's single-ticket record (browser can't cross
            # ports; the lens can). Read-only pass-through, id validated.
            tid = self.path[len("/api/ticket/"):].split("?")[0].strip("/")
            if not re.fullmatch(r"[A-Za-z]{1,8}-\d{1,8}|\d{1,8}", tid or ""):
                body, ctype, code = (
                    json.dumps({"error": "bad ticket id"}),
                    "application/json", 400)
            else:
                data = _get_json(DESK + "/api/admin/tasks/" + tid)
                if data is None:
                    body, ctype, code = (
                        json.dumps({"error": "desk unreachable or unknown ticket"}),
                        "application/json", 502)
                else:
                    body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path == "/api/desk-report" or self.path.startswith("/api/desk-report?"):
            # Office right-rail Desk Overview — same facts as Desk /api/report
            # (tp-156), proxied so the foyer stays in BP scope.
            data = _get_json(DESK + "/api/report", timeout=8)
            if data is None:
                body, ctype, code = (
                    json.dumps({"error": "desk unreachable", "ok": False}),
                    "application/json", 502)
            else:
                body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path == "/api/roster-report" or self.path.startswith("/api/roster-report?"):
            # Office left-rail Roster Overview — WorkForce /api/report (oc-22),
            # proxied so the foyer stays in BP scope.
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query or "")
            days = "7"
            if qs.get("days"):
                try:
                    days = str(max(1, min(int(qs["days"][0]), 90)))
                except (TypeError, ValueError):
                    days = "7"
            data = _get_json(
                "%s/api/report?days=%s" % (WORKFORCE, days), timeout=8)
            if data is None:
                body, ctype, code = (
                    json.dumps({"error": "roster unreachable", "ok": False}),
                    "application/json", 502)
            else:
                if isinstance(data, dict) and "ok" not in data:
                    data = dict(data, ok=True)
                body, ctype, code = json.dumps(data, indent=1), "application/json", 200
        elif self.path.startswith("/api/parcel/"):
            # pc-50/pc-76/pc-95: listing at any depth; survey cache or live walk
            parsed = urllib.parse.urlparse(self.path)
            raw = parsed.path[len("/api/parcel/"):].strip("/")
            qs = urllib.parse.parse_qs(parsed.query or "")
            live_flag = False
            for key in ("live", "verify", "walk"):
                vals = qs.get(key) or []
                if vals and str(vals[0]).lower() in ("1", "true", "yes", "on"):
                    live_flag = True
                    break
            listing, err = parcel_response(
                self.city_root, raw, live=live_flag)
            if err == 403:
                body, ctype, code = (
                    json.dumps({"error": "path escapes city root"}),
                    "application/json", 403)
            elif listing is None:
                body, ctype, code = (
                    json.dumps({"error": "no such parcel"}),
                    "application/json", 404)
            else:
                body, ctype, code = json.dumps(listing, indent=1), "application/json", 200
        elif self.path.startswith("/api/orders/"):
            # pc-74: read-only order book relay (open + recent signed, no bodies)
            raw = self.path[len("/api/orders/"):].split("?")[0]
            name = urllib.parse.unquote(raw.strip("/"))
            orders = neighborhood_orders(self.city_root, name)
            if orders is None:
                body, ctype, code = (
                    json.dumps({"error": "no such neighborhood"}),
                    "application/json", 404)
            else:
                body, ctype, code = json.dumps(orders, indent=1), "application/json", 200
        elif self.path.startswith("/proto/"):
            # Theme prototypes (pc-34) — static react-to material from
            # tools/proto/. Name is sanitized to bare alpha: no traversal.
            name = self.path.strip("/").split("/")[1].split("?")[0]
            fp = os.path.join(PROTO_DIR, name + ".html")
            if name.isalpha() and os.path.isfile(fp):
                with open(fp, "r", encoding="utf-8") as fh:
                    body, ctype, code = fh.read(), "text/html; charset=utf-8", 200
            else:
                body, ctype, code = "<p>no such prototype</p>", "text/html; charset=utf-8", 404
        elif self.path == "/office" or self.path.startswith("/office/"):
            # Office static package (css/js) — path-safe, no traversal.
            body, ctype, code = _office_static(self.path)
        elif self.path == "/api/health":
            body, ctype, code = json.dumps({"ok": True}), "application/json", 200
        elif self.path == "/api/find" or self.path.startswith("/api/find?"):
            # pc-94: THE SEARCHLIGHT — survey index find (name substring).
            qs = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query or "")
            q = (qs.get("q") or [""])[0]
            lim_raw = (qs.get("limit") or [""])[0]
            try:
                lim = int(lim_raw) if lim_raw else FIND_MAX_HITS
            except ValueError:
                lim = FIND_MAX_HITS
            body = json.dumps(find_in_survey(q, limit=lim), indent=1)
            ctype, code = "application/json", 200
        else:
            body, ctype, code = "<p>not found</p>", "text/html; charset=utf-8", 404
        self._send(code, ctype, body)

    def do_POST(self) -> None:  # noqa: N802
        # Local-only mutation endpoints (server binds 127.0.0.1).
        path_only = self.path.split("?")[0]
        # pc-484: same-origin attention snooze/unsnooze → Desk (tp-205).
        # Snooze mutes For You only — never clears gates or cancels tickets.
        if path_only in (
                "/api/you-attention/snooze",
                "/api/you-attention/unsnooze",
                "/api/attention/snooze",
                "/api/attention/unsnooze"):
            action = "unsnooze" if path_only.endswith("/unsnooze") else "snooze"
            raw = self._read_body()
            try:
                text = raw.decode("utf-8") if raw else "{}"
                payload = json.loads(text) if text.strip() else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, "application/json",
                           json.dumps({"ok": False, "error": "bad json"}))
                return
            if not isinstance(payload, dict):
                self._send(400, "application/json",
                           json.dumps({"ok": False, "error": "JSON object required"}))
                return
            desk_url = DESK + "/api/dev/attention/" + action
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                desk_url, data=data, method="POST",
                headers={"Content-Type": "application/json",
                         "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_out = resp.read().decode("utf-8")
                    try:
                        out = json.loads(raw_out) if raw_out else {"ok": True}
                    except json.JSONDecodeError:
                        out = {"ok": True, "raw": raw_out}
                    if not isinstance(out, dict):
                        out = {"ok": True, "data": out}
                    self._send(resp.status, "application/json",
                               json.dumps(out, indent=1))
            except urllib.error.HTTPError as exc:
                try:
                    raw_out = exc.read().decode("utf-8")
                    out = json.loads(raw_out) if raw_out else {
                        "ok": False, "error": exc.reason or str(exc.code)}
                except Exception:
                    out = {"ok": False, "error": exc.reason or str(exc.code)}
                if not isinstance(out, dict):
                    out = {"ok": False, "error": str(out)}
                self._send(exc.code if 400 <= exc.code < 600 else 502,
                           "application/json", json.dumps(out, indent=1))
            except Exception as exc:
                self._send(502, "application/json", json.dumps({
                    "ok": False,
                    "error": "desk unreachable — is :8799 up? (%s)" % exc,
                }))
            return
        # pc-95: re-survey the land on demand (Settings / City Hall).
        if path_only == "/api/survey":
            summary = start_survey(self.city_root, force=True)
            self._send(200, "application/json",
                       json.dumps({"ok": True, "survey": summary}, indent=1))
            return
        # Adopt / manage a top-level folder as a ProtocolCity cabinet.
        if path_only == "/api/manage":
            raw = self._read_body()
            name = ""
            force = False
            consumer = False
            allow_live_desk = False
            if raw:
                try:
                    text = raw.decode("utf-8")
                    payload = json.loads(text) if text.lstrip().startswith("{") else {}
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send(400, "application/json",
                               json.dumps({"error": "bad json"}))
                    return
                if isinstance(payload, dict):
                    name = str(payload.get("name") or payload.get("cabinet") or "").strip()
                    force = bool(payload.get("force"))
                    consumer = bool(payload.get("consumer"))
                    allow_live_desk = bool(
                        payload.get("live_desk") or payload.get("allow_live_desk")
                    )
            if not name:
                self._send(400, "application/json",
                           json.dumps({"error": "name required"}))
                return
            try:
                result = manage_cabinet(
                    self.city_root,
                    name,
                    force=force,
                    consumer=consumer,
                    allow_live_desk=allow_live_desk,
                )
            except (ValueError, FileNotFoundError, FileExistsError) as exc:
                self._send(400, "application/json",
                           json.dumps({"ok": False, "error": str(exc)}))
                return
            except Exception as exc:
                self._send(500, "application/json",
                           json.dumps({"ok": False, "error": str(exc)}))
                return
            self._send(200, "application/json", json.dumps(result, indent=1))
            return
        # pc-62/pc-76: open a path in Finder — any city-root descendant.
        # Directories: open folder. Files: reveal-in-Finder (open -R).
        if path_only != "/api/open":
            self._send(404, "application/json", json.dumps({"error": "not found"}))
            return
        requested = ""
        # Query string path=… is accepted alongside JSON/form body.
        q = urllib.parse.urlparse(self.path).query
        if q:
            qs = urllib.parse.parse_qs(q)
            if "path" in qs and qs["path"]:
                requested = qs["path"][0]
        raw = self._read_body()
        if raw:
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                self._send(400, "application/json", json.dumps({"error": "bad body encoding"}))
                return
            if ctype == "application/json" or text.lstrip().startswith("{"):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    self._send(400, "application/json", json.dumps({"error": "bad json"}))
                    return
                if isinstance(payload, dict) and payload.get("path") is not None:
                    requested = str(payload.get("path"))
            else:
                form = urllib.parse.parse_qs(text)
                if "path" in form and form["path"]:
                    requested = form["path"][0]
        if not requested:
            self._send(400, "application/json", json.dumps({"error": "path required"}))
            return
        allowed = resolve_open_path(self.city_root, requested)
        if allowed is None:
            self._send(403, "application/json",
                       json.dumps({"error": "path not allowed", "path": requested}))
            return
        # Files: reveal in Finder. Folders (and anything else): open.
        if os.path.isfile(allowed):
            cmd = ["open", "-R", allowed]
            kind = "file"
        else:
            cmd = ["open", allowed]
            kind = "dir"
        try:
            subprocess.run(cmd, check=False, timeout=10, capture_output=True)
        except Exception as exc:
            self._send(500, "application/json",
                       json.dumps({"error": "open failed", "detail": str(exc)}))
            return
        self._send(200, "application/json",
                   json.dumps({"ok": True, "path": allowed, "kind": kind}))

    def log_message(self, fmt: str, *args: object) -> None:
        pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="citylens",
                                     description="ProtocolCity — every neighborhood, one page.")
    parser.add_argument("--root", default=None, help="city root (default: walk up to topmost AGENTS.md)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_serve = sub.add_parser("serve", help="serve the lens")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub.add_parser("snapshot", help="print the city as JSON")

    args = parser.parse_args(argv)
    root = find_city_root(args.root)

    if args.cmd == "snapshot":
        print(json.dumps(snapshot(root, with_brief=True), indent=1))
        return 0

    _Handler.city_root = root
    # pc-95: land survey at daemon start — background thread; never blocks serve.
    start_survey(root, force=False)
    # Threaded (pc-34): the briefed snapshot can take seconds; polling pages
    # must not queue behind each other on a single-threaded server.
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), _Handler)
    print("ProtocolCity — Office: http://127.0.0.1:%d (root %s)" % (args.port, root))
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
