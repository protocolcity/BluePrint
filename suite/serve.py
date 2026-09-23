#!/usr/bin/env python3
"""Historical suite helpers retained for compatibility imports.

The supported application is overview/v1/serve.py through blueprint serve.
This module cannot start an independent HTTP application.
"""

if __name__ == "__main__":
    import sys
    print("The historical suite server is retired. Use blueprint serve --foreground --root WORKSPACE.", file=sys.stderr)
    raise SystemExit(2)

import datetime
import errno
import http.server
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, unquote, urlsplit, urlencode, quote, urlparse

# pc-1071: client closed the socket while we were writing a response (Map tab
# abandon, proxy timeout during desk bounce). Benign — never kill the suite.
_CLIENT_DISCONNECT_ERRNOS = frozenset(
    {
        errno.EPIPE,
        errno.ECONNRESET,
        getattr(errno, "ECONNABORTED", -1),
    }
)


def _iso_ts() -> str:
    """UTC ISO-8601 second precision for suite-service.err forensics (pc-1071)."""
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def is_client_disconnect(exc: BaseException) -> bool:
    """True when the peer reset/closed during request I/O (pc-1071)."""
    if isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
        return True
    if isinstance(exc, OSError):
        en = getattr(exc, "errno", None)
        if en in _CLIENT_DISCONNECT_ERRNOS:
            return True
    return False


class _TimestampedStream:
    """Prefix each stderr line with UTC ISO timestamp (pc-1071).

    launchd redirects suite-service.err without timestamps; 12MiB of interleaved
    BrokenPipe frames were unusable forensics. Idempotent if already wrapped.
    """

    __slots__ = ("_stream", "_lock", "_at_bol")

    def __init__(self, stream):
        self._stream = stream
        self._lock = threading.Lock()
        self._at_bol = True

    def write(self, s):
        if not s:
            return 0
        if not isinstance(s, str):
            s = str(s)
        with self._lock:
            out = []
            for chunk in s.splitlines(keepends=True):
                if self._at_bol and chunk not in ("\n", "\r\n"):
                    out.append("%s " % _iso_ts())
                out.append(chunk)
                self._at_bol = chunk.endswith("\n")
            data = "".join(out)
            return self._stream.write(data)

    def flush(self):
        return self._stream.flush()

    def fileno(self):
        return self._stream.fileno()

    def isatty(self):
        return self._stream.isatty()

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", "utf-8")

    def __getattr__(self, name):
        return getattr(self._stream, name)


def install_stderr_timestamps() -> None:
    """Wrap sys.stderr once so every err line carries a wall-clock stamp."""
    if isinstance(sys.stderr, _TimestampedStream):
        return
    try:
        sys.stderr = _TimestampedStream(sys.stderr)  # type: ignore[assignment]
    except Exception:
        pass

# pc-373: compose helpers live under suite/api/ (works as package or script)
try:
    from suite.api import cache as _api_cache
    from suite.api.bootstrap import desk_bootstrap as _api_desk_bootstrap
    from suite.api.bootstrap import map_bootstrap as _api_map_bootstrap
    from suite.api.pulse import build_pulse as _api_build_pulse
    from suite.api.routing import (
        filter_unrouted_tasks as _filter_unrouted_tasks,
        normalize_intake_labels as _normalize_intake_labels,
    )
    from suite.api.task_glance import extract_task_glance as _extract_task_glance
    from suite.api.vocabulary import (
        FOLDER_STORE as _FOLDER_STORE,
        PREFIX_PRODUCT as _PREFIX_PRODUCT,
        light_task_row as _vocab_light_task_row,
        normalize_store_slug as _normalize_store_slug,
        product_of_task_id as _product_of_task_id,
    )
    from suite.api.wo_gates import (
        tally_wo_gate_counts as _tally_wo_gate_counts,
        tally_wo_gate_counts_by_product as _tally_wo_gate_by_product,
    )
    from suite.api.calendar import (
        collect_events as _cal_collect_events,
        render_calendar_html as _cal_render_html,
        render_vcalendar as _cal_render_ics,
    )
except ImportError:  # python3 suite/serve.py (suite dir on sys.path)
    from api import cache as _api_cache  # type: ignore
    from api.bootstrap import desk_bootstrap as _api_desk_bootstrap  # type: ignore
    from api.bootstrap import map_bootstrap as _api_map_bootstrap  # type: ignore
    from api.pulse import build_pulse as _api_build_pulse  # type: ignore
    from api.routing import (  # type: ignore
        filter_unrouted_tasks as _filter_unrouted_tasks,
        normalize_intake_labels as _normalize_intake_labels,
    )
    from api.task_glance import extract_task_glance as _extract_task_glance  # type: ignore
    from api.vocabulary import (  # type: ignore
        FOLDER_STORE as _FOLDER_STORE,
        PREFIX_PRODUCT as _PREFIX_PRODUCT,
        light_task_row as _vocab_light_task_row,
        normalize_store_slug as _normalize_store_slug,
        product_of_task_id as _product_of_task_id,
    )
    from api.wo_gates import (  # type: ignore
        tally_wo_gate_counts as _tally_wo_gate_counts,
        tally_wo_gate_counts_by_product as _tally_wo_gate_by_product,
    )
    from api.calendar import (  # type: ignore
        collect_events as _cal_collect_events,
        render_calendar_html as _cal_render_html,
        render_vcalendar as _cal_render_ics,
    )

PORT = int(os.environ.get("SUITE_PORT", "8801"))
# pc-574: census is in-process. SUITE_CITYLENS_URL is host-debug only
# (SUITE_CITYLENS_REMOTE=1 re-enables HTTP proxy to a standalone :8796).
CITYLENS = os.environ.get("SUITE_CITYLENS_URL", "http://127.0.0.1:8796")
_CITYLENS_REMOTE = (
    os.environ.get("SUITE_CITYLENS_REMOTE", "").strip().lower()
    in ("1", "true", "yes", "on")
)
WORKFORCE = os.environ.get("SUITE_WORKFORCE_URL", "http://127.0.0.1:8797")
DESK = os.environ.get("SUITE_DESK_URL", "http://127.0.0.1:8799")
HERE = os.path.dirname(os.path.abspath(__file__))
# pc-956: discover workspace root (env → walk → registry). Never hardcode
# ~/Developer or any host-home path. Real installs still set SUITE_CITY_ROOT
# via `blueprint service install` (relocate forbids fixed folder names).
try:
    from protocolcity.workspace import resolve_workspace_root_str as _resolve_ws_str

    CITY_ROOT = _resolve_ws_str(
        start=HERE,
        use_registry=True,
        fallback=os.getcwd(),
    )
except Exception:
    # Broken package import must not invent a host path; env or CWD only.
    CITY_ROOT = (os.environ.get("SUITE_CITY_ROOT") or "").strip() or os.getcwd()
# Live WorkForce roster (contract/prompt absolute paths) — read-only enrich.
# Canonical path matches serve --with-engines + hire (pc-351).
WF_ROSTER = os.environ.get(
    "SUITE_WF_ROSTER",
    os.path.join(
        CITY_ROOT, ".protocolcity", "workforce", "local", "roster.json"
    ),
)

# Align protocolcity.citylens engine URLs with suite env (pc-574).
# citylens reads CITY_DESK / CITY_WORKFORCE at import; rebind module globals
# so in-process snapshot/attention hit the same Desk/WorkForce as suite proxies.
try:
    from protocolcity import citylens as _citylens_mod

    _citylens_mod.DESK = DESK
    _citylens_mod.WORKFORCE = WORKFORCE
except Exception:
    _citylens_mod = None  # type: ignore


def _citylens():
    """Lazy import of census library (sole owner since pc-573)."""
    global _citylens_mod
    if _citylens_mod is None:
        from protocolcity import citylens as _citylens_mod  # type: ignore
        _citylens_mod.DESK = DESK
        _citylens_mod.WORKFORCE = WORKFORCE
    return _citylens_mod


def _suite_package_version() -> str:
    """Package version; ``+dogfood`` when glass/package is a source checkout (pc-832).

    Marks dogfood when:
    - ``protocolcity`` is imported from outside site-packages/Cellar, or
    - ``BLUEPRINT_SUITE_DIR`` is set (Cellar CLI + source suite hybrid), or
    - this ``suite/serve.py`` itself is not under site-packages/Cellar.
    """
    base = "dev"
    try:
        from protocolcity.distro import distro_version

        base = distro_version(default="dev") or "dev"
        if base == "not-installed":
            base = "dev"
    except Exception:
        base = "dev"
    if base.endswith("+dogfood"):
        return base
    dogfood = False
    if (os.environ.get("BLUEPRINT_SUITE_DIR") or "").strip():
        dogfood = True
    try:
        import protocolcity as _pc

        src = os.path.realpath(_pc.__file__).replace("\\", "/").lower()
        if not (
            "/site-packages/" in src
            or "/dist-packages/" in src
            or "/cellar/" in src
        ):
            dogfood = True
    except Exception:
        pass
    try:
        here = os.path.realpath(__file__).replace("\\", "/").lower()
        if not (
            "/site-packages/" in here
            or "/dist-packages/" in here
            or "/cellar/" in here
        ):
            dogfood = True
    except Exception:
        pass
    if dogfood:
        return "%s+dogfood" % base
    return base


def city_payload(*, light: bool = False) -> dict:
    """In-process /api/city body (pc-574). Uses citylens short-TTL snap cache.

    pc-1253: cached_snapshot fail-opens inside a short budget so this
    handler never sits on a wedged census walk. Always stamp city_name so
    Map does not fall through to detect-shell (mast WORKSPACE WORKSPACE).
    """
    cl = _citylens()
    data = cl.cached_snapshot(CITY_ROOT, light=light)
    if not isinstance(data, dict):
        try:
            data = city_structure_from_disk(CITY_ROOT, with_desk=False)
            data = dict(data)
            data["degraded"] = True
        except Exception:
            return {"ok": False, "error": "city snapshot failed"}
    out = dict(data)
    out.setdefault("ok", True)
    if not out.get("city_name"):
        out["city_name"] = os.path.basename(str(CITY_ROOT).rstrip("/")) or "workspace"
    # Belt-and-suspenders for older snapshots / light paths.
    out.setdefault("suite_version", _suite_package_version())
    # pc-955 / pc-951: Map first paint is light /api/city. Never ship empty
    # root_files when the workspace root has L0 papers (stale process, old
    # cache, or remote lens blank). Same belt as map-bootstrap.
    try:
        rf = out.get("root_files")
        if not (isinstance(rf, list) and rf):
            filled = cl.root_files_census(CITY_ROOT) or []
            if filled:
                out["root_files"] = filled
    except Exception:
        pass
    # DR-1 pc-1128: citylens emits "neighborhoods"; folders is canonical, neighborhoods is compat alias.
    if "neighborhoods" in out and "folders" not in out:
        out["folders"] = out["neighborhoods"]
    elif "folders" in out and "neighborhoods" not in out:
        out["neighborhoods"] = out["folders"]
    return out


def attention_payload(*, include_snoozed: bool = False) -> dict:
    """In-process /api/attention body — Desk feed, no :8796 (pc-574)."""
    cl = _citylens()
    data = cl.you_attention(include_snoozed=include_snoozed)
    return data if isinstance(data, dict) else {"ok": False, "items": []}


def office_payload() -> dict:
    """In-process /api/office body (pc-574)."""
    cl = _citylens()
    data = cl.cached_office_snapshot(CITY_ROOT)
    if not isinstance(data, dict):
        return {"ok": False, "error": "office snapshot failed"}
    out = dict(data)
    out.setdefault("ok", True)
    return out


def city_generation_payload() -> dict:
    """In-process city pulse token (pc-574) — disk mtimes only, no HTTP."""
    cl = _citylens()
    data = cl.city_generation_token(CITY_ROOT)
    if not isinstance(data, dict):
        return {"ok": False, "token": None}
    out = dict(data)
    out.setdefault("ok", True)
    return out


def bust_census_caches() -> None:
    """After manage/survey — drop citylens snap/office caches (pc-574)."""
    try:
        _citylens().invalidate_census_caches()
    except Exception:
        pass
    # pc-1211: also drop the enrich cache so a fresh survey sees new inventory.
    try:
        with _enrich_lock:
            _enrich_cache.update(at=0.0, token="", data=None)
    except Exception:
        pass
    # Legacy suite HTTP cache keys (remote debug + stale URL entries)
    try:
        _api_cache.invalidate(
            f"{CITYLENS}/api/city",
            f"{CITYLENS}/api/city?light=1",
            f"{CITYLENS}/api/you-attention",
            f"{CITYLENS}/api/office",
        )
    except Exception:
        pass


def bust_wo_caches(*, also_scene: bool = False) -> None:
    """Drop Map rail WO list + chip tallies after desk mutations (pc-1093).

    POST/PATCH/comments busted tp-scene + census but left _live_strip_cache
    (12s) and _wo_gate_counts_cache (20s) serving pre-mutation lists — rail
    lagged every write by up to one TTL.

    pc-1244: also_scene=True additionally evicts the tp-scene HTTP cache so
    folder store counts (open-work badge) update on the next light poll instead
    of waiting up to 5s for the process-local proxy TTL.
    """
    try:
        with _live_strip_lock:
            _live_strip_cache.clear()
    except Exception:
        try:
            _live_strip_cache.clear()
        except Exception:
            pass
    try:
        _wo_gate_counts_cache.clear()
    except Exception:
        pass
    if also_scene:
        try:
            _invalidate_cache(PROXY.get("/api/tp-scene") or "")
        except Exception:
            pass


def _roster_path() -> str:
    return WF_ROSTER


# pc-555: in-process skip holds (name → meta). Survives soft polls; not a store.
_SKIP_HOLDS = {}
_SKIP_HOLDS_LOCK = threading.Lock()


def _wf_local_root() -> str:
    """Directory that holds roster.json / daemon.json / locks/."""
    return os.path.dirname(os.path.abspath(_roster_path()))


def _read_daemon_heartbeat() -> dict:
    path = os.path.join(_wf_local_root(), "daemon.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, TypeError):
        return False
    return True


def _lock_path_for(name: str) -> str:
    return os.path.join(_wf_local_root(), "locks", "%s.lock" % name)


def _release_skip_lock(name: str, expected_pid: int) -> None:
    """Drop a skip lock only if we still own it (same suite PID)."""
    path = _lock_path_for(name)
    pid_path = os.path.join(path, "pid")
    try:
        with open(pid_path, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
        if pid != expected_pid:
            return
        os.unlink(pid_path)
        os.rmdir(path)
    except Exception:
        pass


def _hold_skip_lock_until(name: str, release_at: float) -> None:
    """Background: keep engine lock until release_at so the scheduled fire SKIP."""
    pid = os.getpid()
    try:
        while time.time() < release_at:
            # Refresh mtime so stale-lock reclaim does not steal a long countdown.
            path = _lock_path_for(name)
            try:
                os.utime(path, None)
            except OSError:
                break
            time.sleep(min(15.0, max(1.0, release_at - time.time())))
    finally:
        _release_skip_lock(name, pid)
        with _SKIP_HOLDS_LOCK:
            meta = _SKIP_HOLDS.get(name)
            if meta and meta.get("pid") == pid:
                _SKIP_HOLDS.pop(name, None)


def get_skip_hold(name: str):
    """Active skip for worker, or None. Drops expired holds."""
    slug = (name or "").strip()
    if not slug:
        return None
    now = time.time()
    with _SKIP_HOLDS_LOCK:
        meta = _SKIP_HOLDS.get(slug)
        if not meta:
            return None
        if float(meta.get("until") or 0) <= now:
            _SKIP_HOLDS.pop(slug, None)
            return None
        return dict(meta)


def skip_next_scheduled_fire(name: str) -> dict:
    """Skip the imminent scheduled desk-run only (pc-555).

    Prefer WorkForce POST /api/skip/<name> when the daemon implements it.
    Fallback: hold the per-worker engine lock until shortly after next_fire so
    the scheduled tick becomes a clean ledger SKIP (not a LIVE kill). Never
    attaches when the worker is already in_flight.
    """
    slug = (name or "").strip()
    if not slug or "/" in slug or slug in (".", ".."):
        raise ValueError("bad worker name")
    row = load_wf_roster_row(slug) or load_wf_roster_row(slug.lower())
    if not row:
        # Resolve case-insensitive roster key
        workers = load_wf_roster_workers()
        key = None
        low = slug.lower()
        for k in workers:
            if str(k).lower() == low:
                key = k
                break
        if key is None:
            raise KeyError("no such worker: %s" % slug)
        slug = str(key)
        row = workers[slug]

    hb = _read_daemon_heartbeat()
    inflight = hb.get("in_flight") or []
    if not isinstance(inflight, list):
        inflight = []
    if slug in inflight or any(str(x) == slug for x in inflight):
        return {
            "ok": False,
            "name": slug,
            "msg": "shift already live — Skip is for Approaching only (use Stop when LIVE)",
            "error": "in_flight",
        }

    existing = get_skip_hold(slug)
    if existing:
        return {
            "ok": True,
            "name": slug,
            "msg": "already skipped this round",
            "skipped_fire": existing.get("next_fire") or "",
            "source": "local-hold",
        }

    # Prefer native WorkForce skip when present (future daemon API).
    wf_url = "%s/api/skip/%s" % (WORKFORCE.rstrip("/"), quote(slug))
    try:
        req = urllib.request.Request(wf_url, data=b"{}", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {"ok": True}
            except json.JSONDecodeError:
                payload = {"ok": True, "msg": raw or "skipped"}
            if isinstance(payload, dict) and payload.get("ok") is not False:
                payload = dict(payload)
                payload.setdefault("ok", True)
                payload["name"] = slug
                payload.setdefault("source", "workforce")
                payload.setdefault("msg", payload.get("msg") or "skipped")
                # Mirror hold for Map soft-state even when engine owns skip.
                nf = str(
                    payload.get("skipped_fire")
                    or payload.get("next_fire")
                    or ""
                )
                if not nf:
                    wmeta = (hb.get("workers") or {}).get(slug) or {}
                    nf = str(wmeta.get("next_fire") or "")
                until = time.time() + 180
                if nf:
                    try:
                        until = max(
                            until,
                            datetime.datetime.fromisoformat(
                                nf.replace("Z", "+00:00")
                            ).timestamp()
                            + 120,
                        )
                    except Exception:
                        pass
                with _SKIP_HOLDS_LOCK:
                    _SKIP_HOLDS[slug] = {
                        "next_fire": nf,
                        "until": until,
                        "source": "workforce",
                        "pid": os.getpid(),
                        "at": time.time(),
                    }
                return payload
    except urllib.error.HTTPError as e:
        # 404 = not implemented yet → local lock path. Other codes surface.
        if e.code not in (404, 405):
            try:
                body = e.read().decode("utf-8")
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {}
            msg = (
                (payload.get("msg") if isinstance(payload, dict) else None)
                or e.reason
                or str(e.code)
            )
            return {
                "ok": False,
                "name": slug,
                "msg": str(msg),
                "error": str(msg),
                "source": "workforce",
            }
    except Exception:
        pass  # unreachable / not found → local fallback

    wmeta = (hb.get("workers") or {}).get(slug) or {}
    next_fire = str(wmeta.get("next_fire") or "").strip()
    if not next_fire:
        # Owned workers only appear in heartbeat; refuse unknown next fire.
        return {
            "ok": False,
            "name": slug,
            "msg": "no next_fire — nothing to skip",
            "error": "no_next_fire",
        }

    try:
        fire_dt = datetime.datetime.fromisoformat(next_fire.replace("Z", "+00:00"))
        fire_ts = fire_dt.timestamp()
    except Exception:
        return {
            "ok": False,
            "name": slug,
            "msg": "next_fire unreadable",
            "error": "bad_next_fire",
        }

    now = time.time()
    if fire_ts <= now - 30:
        return {
            "ok": False,
            "name": slug,
            "msg": "next_fire already passed",
            "error": "past_fire",
        }

    # Engine lock path: scheduled fire → ledger SKIP while hold is live.
    locks_root = os.path.join(_wf_local_root(), "locks")
    os.makedirs(locks_root, exist_ok=True)
    lock_path = _lock_path_for(slug)
    pid_path = os.path.join(lock_path, "pid")
    suite_pid = os.getpid()
    try:
        os.mkdir(lock_path)
    except FileExistsError:
        try:
            with open(pid_path, "r", encoding="utf-8") as f:
                holder = int(f.read().strip())
        except Exception:
            holder = -1
        if holder == suite_pid:
            pass  # re-entry
        elif holder > 0 and _pid_alive(holder):
            return {
                "ok": False,
                "name": slug,
                "msg": "cannot skip — worker lock already held (shift or prior skip)",
                "error": "lock_held",
            }
        else:
            # Orphan lock — reclaim like the engine does.
            try:
                os.unlink(pid_path)
            except OSError:
                pass
            try:
                os.rmdir(lock_path)
            except OSError:
                # non-empty: force best-effort
                try:
                    import shutil

                    shutil.rmtree(lock_path, ignore_errors=True)
                except Exception:
                    pass
            try:
                os.mkdir(lock_path)
            except FileExistsError:
                return {
                    "ok": False,
                    "name": slug,
                    "msg": "cannot skip — lock reclaim failed",
                    "error": "lock_held",
                }
    try:
        with open(pid_path, "w", encoding="utf-8") as f:
            f.write(str(suite_pid))
    except OSError as e:
        return {
            "ok": False,
            "name": slug,
            "msg": "lock write failed: %s" % e,
            "error": "lock_write",
        }

    release_at = fire_ts + 120.0
    with _SKIP_HOLDS_LOCK:
        _SKIP_HOLDS[slug] = {
            "next_fire": next_fire,
            "until": release_at,
            "source": "local-lock",
            "pid": suite_pid,
            "at": now,
        }
    t = threading.Thread(
        target=_hold_skip_lock_until,
        args=(slug, release_at),
        daemon=True,
        name="skip-hold-%s" % slug,
    )
    t.start()
    return {
        "ok": True,
        "name": slug,
        "msg": "skipped this round — next schedule fire still stands",
        "skipped_fire": next_fire,
        "source": "local-lock",
    }


def patch_roster_worker_model(name: str, model: str) -> dict:
    """Set roster ``model`` pin for a worker (pc-428). Atomic write.

    Returns {ok, name, model, roster} or raises ValueError/OSError/KeyError.
    Does not rewrite command argv — dispatch substitutes ``{model}`` at fire.
    Empty model string = vendor default (explicit clear).
    """
    slug = (name or "").strip()
    if not slug or "/" in slug or slug in (".", ".."):
        raise ValueError("bad worker name")
    path = _roster_path()
    if not os.path.isfile(path):
        raise FileNotFoundError("roster missing: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("roster root must be object")
    workers = raw.get("workers")
    if not isinstance(workers, dict):
        raise ValueError("roster.workers missing")
    key = None
    if slug in workers:
        key = slug
    else:
        low = slug.lower()
        for k, v in workers.items():
            if str(k).lower() == low:
                key = k
                break
            if isinstance(v, dict) and str(v.get("name") or "").lower() == low:
                key = k
                break
    if key is None:
        raise KeyError("worker not on roster: %s" % slug)
    entry = workers[key]
    if not isinstance(entry, dict):
        raise ValueError("roster entry is not an object")
    pin = (model if model is not None else "").strip()
    entry["model"] = pin
    workers[key] = entry
    raw["workers"] = workers
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)
    return {"ok": True, "name": key, "model": pin, "roster": path}


# Off-the-map list is a DISPLAY truth, never an operational scope (pc-239,
# founder 2026-07-16; ship word 2026-07-23): folders held out of Overview/Map
# paint only. Still on disk. Engines, exports, backups, and patrols must never
# read it as an exclusion. API path /api/hidden + file name kept for compat.
HIDDEN_PATH = os.path.join(CITY_ROOT, ".protocolcity", "hidden.json")
MAP_LAYOUT_PATH = os.path.join(CITY_ROOT, ".protocolcity", "map_layout.json")

# BluePrint-required / law filenames (emphasized on Map; all .md still open)
RULE_NAMES = frozenset({
    "AGENTS.md", "CLAUDE.md", "GROK.md", "CODEX.md", "CURSOR.md",
    "PERIMETER.md", "CITY_EDGES.md", "OFFICE_PERIMETER.md",
    "CONTRACT.md", "prompt.md",
})

# Short-TTL process-local cache — implemented in suite/api/cache.py (pc-373).
# Keep module-level aliases so existing serve.py call sites stay readable.
_CACHE_TTL = _api_cache.CACHE_TTL
_cache = _api_cache._cache  # shared dict; invalidate via _api_cache.invalidate


def read_hidden():
    try:
        with open(HIDDEN_PATH) as f:
            data = json.load(f)
        return sorted(set(data.get("hidden", [])))
    except Exception:
        return []


def write_hidden(slugs):
    os.makedirs(os.path.dirname(HIDDEN_PATH), exist_ok=True)
    with open(HIDDEN_PATH, "w") as f:
        json.dump({
            "note": (
                "Display-only (pc-239): folders held off Overview/Map paint. "
                "Still on disk. Never an operational scope. "
                "Ship word: off the map (not OS-hidden)."
            ),
            "hidden": sorted(set(slugs)),
        }, f, indent=2)


def read_map_layout():
    try:
        with open(MAP_LAYOUT_PATH) as f:
            data = json.load(f)
        order = data.get("order", [])
        return [str(s) for s in order if isinstance(s, str)]
    except Exception:
        return []


def write_map_layout(order):
    os.makedirs(os.path.dirname(MAP_LAYOUT_PATH), exist_ok=True)
    with open(MAP_LAYOUT_PATH, "w") as f:
        json.dump({"order": order}, f, indent=2)


def safe_city_path(rel):
    """Resolve a path to a real file/dir strictly inside CITY_ROOT.

    Accepts city-root-relative paths (normal) and absolute paths under the
    city root (pc-568 — Map/dig-in sometimes emits abs paths; stripping the
    leading slash used to 404 as ``Users/…`` under CITY_ROOT).
    """
    raw = unquote(rel or "").strip()
    if not raw:
        return os.path.realpath(CITY_ROOT)
    root = os.path.realpath(CITY_ROOT)
    raw_norm = raw.replace("\\", "/")

    def _inside(p):
        if not p:
            return None
        p = os.path.realpath(p)
        if p == root or p.startswith(root + os.sep):
            return p
        return None

    # Absolute (Unix / Windows drive)
    if os.path.isabs(raw) or (len(raw) >= 3 and raw[1] == ":" and raw[2] in "\\/"):
        return _inside(raw)

    # Accidental strip of leading slash on an abs path:
    #   Users/me/{workspace}/ProtocolCity/AGENTS.md
    if raw_norm and not raw_norm.startswith("."):
        as_abs = _inside("/" + raw_norm.lstrip("/"))
        if as_abs is not None:
            return as_abs
        root_norm = root.replace("\\", "/")
        needle = "/" + raw_norm.lstrip("/")
        idx = needle.find(root_norm + "/")
        if idx >= 0:
            hit = _inside(needle[idx:])
            if hit is not None:
                return hit
        if needle.rstrip("/") == root_norm:
            return root

    rel = raw_norm.strip("/")
    if not rel:
        return root
    if any(part in ("", "..") for part in rel.split("/")):
        return None
    return _inside(os.path.join(root, rel))


def resolve_project_dir(slug):
    """Map a project slug (or folder name) to a direct child of CITY_ROOT.

    Case-insensitive match of top-level dirs so suite slugs like ``tradeos``
    resolve to on-disk ``tradeOS``. Returns absolute path or None.
    """
    slug = unquote(slug or "").strip().strip("/")
    if not slug or "/" in slug or "\\" in slug or slug in (".", ".."):
        return None
    root = os.path.realpath(CITY_ROOT)
    exact = os.path.join(root, slug)
    if os.path.isdir(exact):
        real = os.path.realpath(exact)
        if os.path.dirname(real) == root:
            return real
    try:
        names = os.listdir(root)
    except OSError:
        return None
    lower = slug.lower()
    for name in names:
        if name.lower() != lower:
            continue
        real = os.path.realpath(os.path.join(root, name))
        if os.path.isdir(real) and os.path.dirname(real) == root:
            return real
    return None


def resolve_city_rel_with_project(rel, project):
    """Resolve a city-relative path; on miss, retry inside the project folder.

    Work-order WHERE paths are usually written project-relative
    (``docs/design/x.md`` meaning ``oneseo-pos/docs/design/x.md``). With a
    ``project`` hint, fall back to ``<project-folder>/<rel>`` so ticket chips
    and relative links open instead of 404ing at city root (pc-1209).
    Returns ``(abs_target_or_None, rel_used)``.
    """
    target = safe_city_path(rel)
    if target and os.path.exists(target):
        return target, rel
    rel_norm = unquote(rel or "").replace("\\", "/").lstrip("/")
    project = unquote(project or "").strip()
    if rel_norm and project:
        pdir = resolve_project_dir(project)
        if pdir:
            leaf = os.path.basename(pdir)
            cand_rel = leaf + "/" + rel_norm
            cand = safe_city_path(cand_rel)
            if cand and os.path.exists(cand):
                return cand, cand_rel
    # No (usable) hint: scan top-level projects, accept only a UNIQUE match —
    # ambiguity stays 404 so we never open the wrong project's file. Rescues
    # clicks from stale-JS tabs and tickets whose caller sends no hint.
    if rel_norm and "/" in rel_norm:
        root = os.path.realpath(CITY_ROOT)
        try:
            names = os.listdir(root)
        except OSError:
            names = []
        hits = []
        for name in names:
            if name.startswith(".") or name in (
                "ProtocolCity-WorkLane",
                "ProtocolCity-WorkForce",
                "ProtocolCity-BluePrint",
                "ProtocolCity-Charter",
                "tp-backups",
                "tradeOS-backups",
                "homebrew-tap",
                "local",
            ):
                continue
            if not os.path.isdir(os.path.join(root, name)):
                continue
            cand_rel = name + "/" + rel_norm
            cand = safe_city_path(cand_rel)
            if cand and os.path.exists(cand):
                hits.append((cand, cand_rel))
                if len(hits) > 1:
                    break
        if len(hits) == 1:
            return hits[0]
    return target, rel


# pc-1172: project Home doors — pin tools/pages/host-actions (machine-local).
# Display + intentional pin only — not a permission grant. host-action runs are
# allowlisted (open_path / run_script under project) and loopback-only.
_DOOR_URL_KINDS = frozenset({"app", "link", "url"})
_DOOR_KINDS = frozenset({"app", "link", "url", "suite", "host-action"})
_HOST_ACTIONS = frozenset({"open_path", "run_script"})
_SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_./:@%=+\-]+$")
_MAX_DOORS = 40


def _normalize_door_label(raw):
    label = str(raw or "").strip()
    if not label:
        return ""
    if len(label) > 40:
        label = label[:40]
    return label


def _is_safe_rel_path(rel, *, allow_dot=False):
    """Reject absolute paths, .. segments, and empty/odd values."""
    s = str(rel or "").strip().replace("\\", "/")
    if not s:
        return False
    if s.startswith("/") or s.startswith("~"):
        return False
    if ".." in s.split("/"):
        return False
    if s in (".",) and not allow_dot:
        return False
    return True


def _canonicalize_retired_home_suite_path(path):
    """Rewrite retired Files/Home suite doors onto Map (pc-1278 / pc-1379).

    Query is preserved so ?project= / &path= still focus Map. Other suite
    paths are unchanged. Does not write host doors.json files.
    """
    raw = (path or "").strip()
    if not raw.startswith("/"):
        return path
    route, _, qs = raw.partition("?")
    if route != "/" and route.endswith("/"):
        route = route.rstrip("/")
    if route != "/home":
        return path
    loc = "/workspace-map"
    if qs:
        loc = loc + "?" + qs
    return loc


def normalize_door_entry(item):
    """Validate one door dict. Returns (door|None, error|None).

    Kinds:
      app|link|url — http(s) chip (url is alias of app for visual default)
      suite        — in-suite path starting with /
      host-action  — open_path | run_script (allowlisted; loopback execute)
    """
    if not isinstance(item, dict):
        return None, "door must be an object"
    label = _normalize_door_label(item.get("label"))
    if not label:
        return None, "label required"
    kind = str(item.get("kind") or "app").strip().lower()
    if kind not in _DOOR_KINDS:
        return None, "invalid kind (app|link|url|suite|host-action)"

    if kind in _DOOR_URL_KINDS:
        url = str(item.get("url") or "").strip()
        if not url:
            return None, "url required for app/link/url doors"
        # Display-only destinations — http(s) only (no javascript: / file:).
        if not (url.startswith("http://") or url.startswith("https://")):
            return None, "url must be http:// or https://"
        if len(url) > 2000:
            return None, "url too long"
        # kind "url" normalizes to "app" for primary-chip paint (back-compat).
        out_kind = "app" if kind == "url" else kind
        return {"label": label, "url": url, "kind": out_kind}, None

    if kind == "suite":
        path = str(item.get("path") or item.get("url") or "").strip()
        if not path.startswith("/"):
            return None, "suite path must start with /"
        if path.startswith("//") or "://" in path:
            return None, "suite path must be relative (no scheme)"
        if ".." in path.split("/"):
            return None, "suite path must not contain .."
        if len(path) > 500:
            return None, "suite path too long"
        path = _canonicalize_retired_home_suite_path(path)
        return {"label": label, "kind": "suite", "path": path}, None

    # host-action
    action = str(item.get("action") or "").strip().lower()
    if action not in _HOST_ACTIONS:
        return None, "host-action requires action open_path|run_script"
    if action == "open_path":
        path = str(item.get("path") or "").strip()
        if not path:
            return None, "open_path requires path"
        # Relative to project dir, or "." for project root. No free abs paths
        # outside project (resolved at execute time under project_dir).
        if not _is_safe_rel_path(path, allow_dot=True) and path != ".":
            return None, "open_path path must be relative under the project"
        if len(path) > 400:
            return None, "path too long"
        return {
            "label": label,
            "kind": "host-action",
            "action": "open_path",
            "path": path,
        }, None

    # run_script — only under <project>/scripts/
    script = str(item.get("script") or "").strip().replace("\\", "/")
    if not script:
        return None, "run_script requires script (under scripts/)"
    # Allow optional "scripts/" prefix; store without it for clarity.
    if script.startswith("scripts/"):
        script = script[len("scripts/") :]
    if not _is_safe_rel_path(script):
        return None, "script must be a relative path under scripts/"
    if not script.endswith(".sh") and not script.endswith(".command") and not script.endswith(".py"):
        return None, "script must end in .sh, .command, or .py"
    if len(script) > 200:
        return None, "script path too long"
    args_raw = item.get("args")
    args = []
    if args_raw is None:
        args = []
    elif isinstance(args_raw, list):
        if len(args_raw) > 12:
            return None, "too many script args (max 12)"
        for a in args_raw:
            s = str(a)
            if len(s) > 80:
                return None, "script arg too long"
            if not _SAFE_ARG_RE.match(s):
                return None, "script arg has disallowed characters"
            args.append(s)
    else:
        return None, "args must be a list of strings"
    return {
        "label": label,
        "kind": "host-action",
        "action": "run_script",
        "script": script,
        "args": args,
    }, None


def normalize_doors_list(raw):
    """Normalize a doors array. Returns (doors, error|None).

    Invalid entries are dropped on read; write path rejects on first error.
    """
    if not isinstance(raw, list):
        return [], "doors must be an array"
    if len(raw) > _MAX_DOORS:
        return [], "too many doors (max %d)" % _MAX_DOORS
    out = []
    for item in raw:
        door, err = normalize_door_entry(item)
        if door is not None:
            out.append(door)
    return out, None


def read_project_doors(project_dir):
    """Load local/doors.json; graceful empty list if missing/invalid."""
    path = os.path.join(project_dir, "local", "doors.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        return []
    raw = data.get("doors") if isinstance(data, dict) else None
    doors, _ = normalize_doors_list(raw if isinstance(raw, list) else [])
    return doors


def write_project_doors(project_dir, doors):
    """Write local/doors.json (creates local/ as needed). doors already normalized."""
    local_dir = os.path.join(project_dir, "local")
    os.makedirs(local_dir, exist_ok=True)
    path = os.path.join(local_dir, "doors.json")
    payload = {"doors": doors}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def _client_is_loopback(handler):
    """True when the HTTP peer is loopback (host-action gate)."""
    try:
        addr = handler.client_address[0] if handler and handler.client_address else ""
    except Exception:
        addr = ""
    if addr in ("127.0.0.1", "::1", "localhost"):
        return True
    # Suite binds 127.0.0.1 by default — still check peer.
    return str(addr).startswith("127.")


def execute_host_action(project_dir, door):
    """Run a normalized host-action door. Returns (ok_dict|None, err_str|None)."""
    if not isinstance(door, dict) or door.get("kind") != "host-action":
        return None, "not a host-action door"
    action = door.get("action")
    project_real = os.path.realpath(project_dir)
    if action == "open_path":
        rel = str(door.get("path") or ".").strip() or "."
        if rel == ".":
            target = project_real
        else:
            target = os.path.realpath(os.path.join(project_real, rel))
        if target != project_real and not target.startswith(project_real + os.sep):
            return None, "path escapes project"
        if not os.path.exists(target):
            return None, "path not found"
        if os.path.isfile(target):
            cmd = ["open", "-R", target]
            kind = "file"
        else:
            cmd = ["open", target]
            kind = "dir"
        try:
            subprocess.run(cmd, check=False, timeout=10, capture_output=True)
        except Exception as e:
            return None, "open failed: %s" % e
        return {"ok": True, "action": "open_path", "path": target, "kind": kind}, None

    if action == "run_script":
        script = str(door.get("script") or "").strip().replace("\\", "/")
        if not script:
            return None, "script missing"
        scripts_root = os.path.realpath(os.path.join(project_real, "scripts"))
        script_path = os.path.realpath(os.path.join(scripts_root, script))
        if not script_path.startswith(scripts_root + os.sep):
            return None, "script escapes scripts/"
        if not os.path.isfile(script_path):
            return None, "script not found"
        args = door.get("args") if isinstance(door.get("args"), list) else []
        cmd = [script_path] + [str(a) for a in args]
        # Prefer bash for .sh; .command is macOS shell; .py via python3.
        if script_path.endswith(".py"):
            cmd = [sys.executable or "python3", script_path] + [str(a) for a in args]
        elif script_path.endswith(".sh") or script_path.endswith(".command"):
            cmd = ["/bin/bash", script_path] + [str(a) for a in args]
        try:
            # Fire-and-forget friendly: do not capture huge output; short timeout
            # for launch only — long-lived VNC viewers may outlive the request.
            proc = subprocess.Popen(
                cmd,
                cwd=project_real,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            return None, "run failed: %s" % e
        return {
            "ok": True,
            "action": "run_script",
            "script": script,
            "args": args,
            "pid": proc.pid,
        }, None

    return None, "unknown action"


def read_project_notes(project_dir):
    """Load local/notes.md; empty string if absent."""
    path = os.path.join(project_dir, "local", "notes.md")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def write_project_notes(project_dir, text):
    """Write local/notes.md (creates local/ as needed)."""
    local_dir = os.path.join(project_dir, "local")
    os.makedirs(local_dir, exist_ok=True)
    path = os.path.join(local_dir, "notes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# pc-653 §3: per-project hygiene expected-state (planning / stable).
# Lives under <project>/.protocolcity/expected-state.json — with the project,
# not browser localStorage. Keys: handless → "planning", quiet → "stable".
_EXPECTED_STATE_HANDLESS = frozenset({"planning"})
_EXPECTED_STATE_QUIET = frozenset({"stable"})


def expected_state_path(project_dir):
    return os.path.join(project_dir, ".protocolcity", "expected-state.json")


def normalize_expected_state(raw):
    """Return {handless?, quiet?} with only valid tokens; drop unknowns."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    handless = raw.get("handless")
    if isinstance(handless, str) and handless.strip().lower() in _EXPECTED_STATE_HANDLESS:
        out["handless"] = handless.strip().lower()
    quiet = raw.get("quiet")
    if isinstance(quiet, str) and quiet.strip().lower() in _EXPECTED_STATE_QUIET:
        out["quiet"] = quiet.strip().lower()
    return out


def read_project_expected_state(project_dir):
    """Load .protocolcity/expected-state.json; empty dict if absent/invalid."""
    path = expected_state_path(project_dir)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return normalize_expected_state(data)


def write_project_expected_state(project_dir, state):
    """Write expected-state.json. Empty state removes the file."""
    clean = normalize_expected_state(state if isinstance(state, dict) else {})
    path = expected_state_path(project_dir)
    parent = os.path.dirname(path)
    if not clean:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except FileNotFoundError:
            pass
        return clean
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, sort_keys=True)
        f.write("\n")
    return clean


def merge_project_expected_state(project_dir, patch):
    """Merge PATCH into current expected-state.

    Explicit null / "" / false clears a key. Unknown keys ignored.
    """
    cur = read_project_expected_state(project_dir)
    if not isinstance(patch, dict):
        return cur
    next_state = dict(cur)
    if "handless" in patch:
        val = patch.get("handless")
        if val in (None, "", False):
            next_state.pop("handless", None)
        elif isinstance(val, str) and val.strip().lower() in _EXPECTED_STATE_HANDLESS:
            next_state["handless"] = val.strip().lower()
    if "quiet" in patch:
        val = patch.get("quiet")
        if val in (None, "", False):
            next_state.pop("quiet", None)
        elif isinstance(val, str) and val.strip().lower() in _EXPECTED_STATE_QUIET:
            next_state["quiet"] = val.strip().lower()
    return write_project_expected_state(project_dir, next_state)


def list_hygiene_expected(root=None):
    """Scan top-level folders for expected-state; keyed by folder basename."""
    root = os.path.realpath(root or CITY_ROOT)
    by_slug = {}
    try:
        names = os.listdir(root)
    except OSError:
        return by_slug
    for name in names:
        if not name or name.startswith("."):
            continue
        if name in _DETECT_SKIP_TOP:
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        state = read_project_expected_state(path)
        if state:
            by_slug[name] = state
    return by_slug


def dir_managed(path):
    """BluePrint-managed = join marker (pc-427), not AGENTS.md alone."""
    try:
        return os.path.isfile(
            os.path.join(path, ".protocolcity", "managed")
        )
    except Exception:
        return False


# Top-level names that are never projects (pc-355 always-on detect).
_DETECT_SKIP_TOP = frozenset({
    "node_modules", "dist", "build", "__pycache__", "logs", "local",
    "site-packages", "venv", ".venv",
    # pc-894: never treat exports / backup heaps as Map projects
    "ProtocolCity-BluePrint", "ProtocolCity-WorkLane", "ProtocolCity-WorkForce",
    "ProtocolCity-Charter",
    "tp-backups", "tradeOS-backups", "homebrew-tap", "scripts", "Sales",
})


def _scan_worker_papers(project_rel, workers_abs, scope="project"):
    """List agent paper folders under workers/ (CONTRACT.md and/or prompt.md).

    scope:
      project       — product project agents
      workspace_ops — Workspace ops kit (.protocolcity/ops/workers; pc-367)
    """
    out = []
    try:
        names = sorted(os.listdir(workers_abs))
    except OSError:
        return out
    for wname in names:
        if not wname or wname.startswith("."):
            continue
        wpath = os.path.join(workers_abs, wname)
        if not os.path.isdir(wpath):
            continue
        has_c = os.path.isfile(os.path.join(wpath, "CONTRACT.md"))
        has_p = os.path.isfile(os.path.join(wpath, "prompt.md"))
        if not (has_c or has_p):
            continue
        if scope == "workspace_ops":
            rel = ".protocolcity/ops/workers/%s" % wname
        else:
            rel = (
                ("%s/workers/%s" % (project_rel, wname))
                if project_rel
                else ("workers/%s" % wname)
            )
        out.append({
            "project": project_rel or "",
            "id": wname,
            "has_contract": has_c,
            "has_prompt": has_p,
            "path": rel,
            "scope": scope,
        })
    return out


def detect_workspace(root=None):
    """Always-on first-open detect (pc-355) — files on disk, no decision gate.

    Surfaces managed projects (AGENTS.md), agent papers (workers/*), and the
    canonical WorkForce roster. Independent of engines being up.
    """
    root = os.path.realpath(root or CITY_ROOT)
    managed = []
    papers = []
    try:
        top = sorted(os.listdir(root))
    except OSError:
        top = []

    for name in top:
        if not name or name.startswith("."):
            continue
        if name in _DETECT_SKIP_TOP or name.endswith("-backups"):
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        if dir_managed(path):
            managed.append({"slug": name, "name": name, "path": name})
        wdir = os.path.join(path, "workers")
        if os.path.isdir(wdir):
            papers.extend(_scan_worker_papers(name, wdir))

    # Workspace-level agent papers (found kit / staff stubs)
    root_workers = os.path.join(root, "workers")
    if os.path.isdir(root_workers):
        papers.extend(_scan_worker_papers("", root_workers, scope="project"))

    # pc-367: Workspace ops kit — not a product folder (read-only on detect)
    ops_workers = os.path.join(root, ".protocolcity", "ops", "workers")
    if os.path.isdir(ops_workers):
        papers.extend(
            _scan_worker_papers("", ops_workers, scope="workspace_ops")
        )

    roster_abs = os.path.join(
        root, ".protocolcity", "workforce", "local", "roster.json"
    )
    # Honour suite override when scanning the live CITY_ROOT
    if os.path.realpath(root) == os.path.realpath(CITY_ROOT):
        roster_abs = WF_ROSTER
    roster_exists = os.path.isfile(roster_abs)
    roster_count = 0
    roster_readable = False
    if roster_exists:
        try:
            with open(roster_abs, "r", encoding="utf-8") as f:
                raw = json.load(f)
            workers = raw.get("workers") if isinstance(raw, dict) else raw
            if isinstance(workers, dict):
                roster_count = len(workers)
                roster_readable = True
            elif isinstance(workers, list):
                roster_count = len(workers)
                roster_readable = True
        except Exception:
            roster_readable = False

    rel_roster = city_rel(roster_abs)
    if rel_roster is None:
        rel_roster = ".protocolcity/workforce/local/roster.json"

    return {
        "always_on": True,
        "managed_count": len(managed),
        "managed_projects": managed,
        "agent_papers_count": len(papers),
        "agent_papers": papers[:80],
        "roster": {
            "path": rel_roster,
            "exists": roster_exists,
            "worker_count": roster_count,
            "readable": roster_readable if roster_exists else None,
        },
    }


def city_rel(abs_path):
    """Absolute path → city-root relative, or None if outside city."""
    if not abs_path:
        return None
    root = os.path.realpath(CITY_ROOT)
    p = os.path.realpath(abs_path)
    if p == root:
        return ""
    if not p.startswith(root + os.sep):
        return None
    return os.path.relpath(p, root).replace(os.sep, "/")


def load_wf_roster_row(name):
    try:
        with open(WF_ROSTER, "r", encoding="utf-8") as f:
            data = json.load(f)
        workers = data.get("workers") or data
        if isinstance(workers, dict):
            return workers.get(name)
    except Exception:
        pass
    return None


def load_wf_roster_workers():
    """All hired workers from disk roster (dict name → row). Empty if missing."""
    try:
        with open(WF_ROSTER, "r", encoding="utf-8") as f:
            data = json.load(f)
        workers = data.get("workers") if isinstance(data, dict) else data
        if isinstance(workers, dict):
            return {str(k): v for k, v in workers.items() if isinstance(v, dict)}
        if isinstance(workers, list):
            out = {}
            for row in workers:
                if not isinstance(row, dict):
                    continue
                n = row.get("name") or row.get("id") or row.get("identity")
                if n:
                    out[str(n)] = row
            return out
    except Exception:
        pass
    return {}


def _roster_row_is_staff(row):
    """Workspace ops / staff seats — not a product-folder agent."""
    if not isinstance(row, dict):
        return False
    # Explicit roster staff pin (github-desk / ship-desk / clerk / …)
    staff_flag = row.get("staff")
    if staff_flag in (True, 1, "1", "true", "True", "yes", "YES"):
        return True
    role = str(row.get("role") or "").lower()
    if role == "staff":
        return True
    wd = os.path.realpath(str(row.get("workdir") or ""))
    root = os.path.realpath(CITY_ROOT)
    if wd == root:
        return True
    norm = wd.replace("\\", "/")
    if "/.protocolcity/ops" in norm:
        return True
    return False


# pc-922: mtime-keyed last_shift from local ledger (light people path).
_LAST_SHIFT_CACHE = {}  # name -> (mtime, dict|None)
# pc-1174: mtime-keyed last real (deeper partition) for Agents face.
_LAST_REAL_CACHE = {}  # name|path -> (mtime, pack|None)
_LEDGER_LINE_KV = re.compile(r'(\w+)=("(?:[^"]*)"|\S+)')
_LEDGER_EVENTS = frozenset(
    (
        "START",
        "DONE",
        "STOP",
        "SKIP",
        "ERROR",
        "WARN",
        "GHOST",
        "SCOPE_DENY",
        "HOST_MUTATION_DENY",
        "CLAIM",  # pc-1174: ticket id on shift for last real work
    )
)


def _ledger_shift_public(s):
    """Wire shape for dig / people last_shift (no budget_secs / internal).

    pc-1174: include ticket_id / ticket_title when ledger CLAIM stamped them.
    """
    if not s:
        return None
    out = {
        "ts": s.get("ts") or "",
        "outcome": s.get("outcome") or "",
        "passes": int(s.get("passes") or 0),
        "reason": s.get("reason") or "",
        "queue": s.get("queue") or "",
        "dry_run": bool(s.get("dry_run")),
    }
    tid = str(s.get("ticket_id") or "").strip()
    if tid:
        out["ticket_id"] = tid
    title = str(s.get("ticket_title") or "").strip()
    if title:
        out["ticket_title"] = title
    return out


def parse_ledger_shifts(text, limit=40):
    """Mirror WorkForce ledger.parse_shifts → newest-first list (pc-964).

    Pure: input is ledger tail text. Deeper lookback than WF dig's limit=10 so
    empty thrash does not hide the last real close. Dry-runs omitted.
    """
    if not text:
        return []
    shifts = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("…"):
            continue
        parts = line.split(" ")
        if len(parts) < 2 or parts[1] not in _LEDGER_EVENTS:
            continue
        ts, kind = parts[0], parts[1]
        kv = {}
        for m in _LEDGER_LINE_KV.finditer(" ".join(parts[2:])):
            kv[m.group(1)] = m.group(2).strip('"')
        if kind == "START":
            current = {
                "ts": ts,
                "outcome": "running",
                "passes": 0,
                "reason": "",
                "budget_secs": int(kv.get("budget_secs") or 0 or 0),
                "dry_run": kv.get("dry_run") == "1",
                "queue": kv.get("queue") or "",
                "ticket_id": "",
                "ticket_title": "",
            }
            shifts.append(current)
        elif kind == "CLAIM" and current is not None:
            # pc-1174: WorkForce CLAIM ticket=pc-N title="…" mid-shift
            tid = str(kv.get("ticket") or kv.get("task_id") or "").strip()
            if tid:
                current["ticket_id"] = tid
            title = str(kv.get("title") or "").strip()
            if title:
                current["ticket_title"] = title
        elif kind == "DONE" and current is not None:
            current["passes"] = int(current.get("passes") or 0) + 1
            if current.get("dry_run"):
                current["outcome"] = "ok"
                current["reason"] = "dry-run"
                current = None
        elif kind in ("STOP", "ERROR") and current is not None:
            reason = kv.get("reason") or ""
            if kind == "STOP":
                current["outcome"] = "ok"
            elif reason.startswith("vendor limit:"):
                current["outcome"] = "vendor_limit"
            else:
                current["outcome"] = "error"
            current["reason"] = reason
            current = None
        elif kind == "WARN" and current is not None:
            # pc-1184: mid-shift WARN (e.g. "shift finalize: primary dirty") must
            # not orphan the open START…CLAIM…DONE window. A standalone WARN
            # entry would wipe ticket_id and steal last_real from the close.
            # Keep current open so STOP can terminate with CLAIM intact.
            note = str(kv.get("reason") or "").strip()
            if note and not str(current.get("reason") or "").strip():
                current["warn_note"] = note
            continue
        elif kind in ("SKIP", "ERROR", "WARN", "SCOPE_DENY"):
            shifts.append(
                {
                    "ts": ts,
                    "outcome": kind.lower(),
                    "passes": 0,
                    "reason": kv.get("reason") or "",
                    "budget_secs": 0,
                    "dry_run": False,
                    "queue": "",
                }
            )
            current = None
    if not shifts:
        return []
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for s in reversed(shifts):
        if s.get("dry_run"):
            continue
        row = dict(s)
        if row.get("outcome") == "running":
            try:
                started = datetime.datetime.strptime(
                    row["ts"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=datetime.timezone.utc)
                age = (now - started).total_seconds()
                if age > (row.get("budget_secs") or 1500) + 600:
                    row["outcome"] = "crashed"
                    row["reason"] = "no terminal event past budget+grace"
            except (ValueError, TypeError, KeyError):
                pass
        pub = _ledger_shift_public(row)
        if pub:
            out.append(pub)
        if len(out) >= max(1, int(limit or 40)):
            break
    return out


def parse_ledger_last_shift(text):
    """Mirror WorkForce ledger.parse_shifts → newest non-dry-run shift (pc-922).

    Pure: input is ledger tail text. Outcomes include ok / error / vendor_limit
    / skip / running / crashed so Map Agent activities can paint failures even
    when WorkForce light scene strips last_shift (why=light).
    """
    rows = parse_ledger_shifts(text, limit=1)
    if not rows:
        return None
    s = rows[0]
    return {
        "ts": s.get("ts") or "",
        "outcome": s.get("outcome") or "",
        "passes": int(s.get("passes") or 0),
        "reason": s.get("reason") or "",
    }


def is_process_only_warn(s):
    """WARN without throughput — not last *real* ticket work (pc-1184 / §9).

    Engine emits mid/post-shift WARNs (shift finalize dirty, empty-run threshold)
    that must not masquerade as the last real close on Agents face.
    """
    if not s:
        return False
    outcome = str(s.get("outcome") or "").lower()
    if outcome != "warn":
        return False
    try:
        passes = int(s.get("passes") or 0)
    except (TypeError, ValueError):
        passes = 0
    if passes > 0:
        return False
    if str(s.get("ticket_id") or "").strip():
        return False
    reason = str(s.get("reason") or "").lower()
    # Empty thrash + shift-finalize dirty are process signals, not ticket work
    if "empty" in reason:
        return True
    if "shift finalize" in reason or "leave branch" in reason:
        return True
    if "reconcile" in reason:
        return True
    return False


def is_empty_check_shift(s):
    """Queue-empty / no-ready skips — noise, not real work (pc-964 / §9).

    Preflight skips (low disk, CLI missing) stay meaningful even with 0
    passes (pc-1378). Only queue-empty / no-ready skips collapse.
    """
    if not s:
        return True
    outcome = str(s.get("outcome") or "").lower()
    reason = str(s.get("reason") or "").lower()
    try:
        passes = int(s.get("passes") or 0)
    except (TypeError, ValueError):
        passes = 0
    if outcome in ("skip", "skipped"):
        if "queue empty" in reason or "no ready" in reason:
            return True
        return False
    if outcome == "ok" and passes <= 0 and "queue empty" in reason:
        return True
    # WARN empty-run threshold is thrash signal, not throughput
    if outcome == "warn" and "empty" in reason:
        return True
    # pc-1184: process-only WARNs collapse with empty checks for last_real
    if is_process_only_warn(s):
        return True
    return False


def is_fail_shift(s):
    """Failed / vendor-limit / crash — attention class, never collapse (pc-964)."""
    if not s:
        return False
    oc = str(s.get("outcome") or "").lower()
    return oc in (
        "error",
        "err",
        "fault",
        "failed",
        "crashed",
        "vendor_limit",
    )


def partition_shift_history(shifts, max_meaningful=6):
    """Meaningful first (incl. fails), empty checks collapsed to a count (pc-964).

    Pure. Shifts newest-first. ``empty_n`` / ``since`` describe the trailing
    empty streak (top of ledger until first real work) so dig can say
    "n empty checks since …" without listing each skip. Failed shifts stay
    in ``meaningful`` (attention, never collapsed).
    """
    list_ = list(shifts or [])
    meaningful = []
    empty_n = 0
    last_empty = None  # newest empty (head of streak)
    first_empty = None  # oldest empty in trailing streak → "since"
    seen_real = False
    for s in list_:
        if is_empty_check_shift(s):
            if not seen_real:
                empty_n += 1
                if last_empty is None:
                    last_empty = s
                first_empty = s
            # Empties after a real are noise further back — still skip listing
            continue
        seen_real = True
        if len(meaningful) < max(1, int(max_meaningful or 6)):
            meaningful.append(s)
    return {
        "meaningful": meaningful,
        "empty_n": empty_n,
        "last_empty": last_empty,
        "first_empty": first_empty,
        "last_real": meaningful[0] if meaningful else None,
    }


def _ledger_path_for_worker(name):
    """Newest existing ledger file for hand name across candidate dirs."""
    name = (name or "").strip()
    if not name or name in ("you", "You"):
        return None, -1.0
    best_path = None
    best_mtime = -1.0
    for d in _ledger_dir_candidates():
        path = os.path.join(d, "%s.log" % name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime > best_mtime:
            best_mtime = mtime
            best_path = path
    return best_path, best_mtime


def enrich_worker_shift_history(data):
    """pc-964 · ALWAYS_WORK §9: dig Recent work leads with last real work.

    WorkForce dig returns only the newest ~10 shifts. Empty thrash fills that
    window and drowns real closes. Re-read a deeper local ledger tail, keep
    meaningful (and failed) shifts, and surface empty_checks count + since.
    """
    if not isinstance(data, dict):
        return data
    name = data.get("name") or ""
    path, _mtime = _ledger_path_for_worker(name)
    deep = []
    if path:
        # Deeper than WF dig limit=10 so empty streak does not hide last real
        text, _ = _read_tail(path, max_bytes=48000)
        deep = parse_ledger_shifts(text or "", limit=80)
    # Prefer deep ledger when present; else partition what WF already sent
    source = deep if deep else list(data.get("shifts") or [])
    hist = partition_shift_history(source, max_meaningful=6)
    dig_shifts = list(hist["meaningful"])
    # One representative empty so client collapse still has a ts anchor
    if hist["empty_n"] > 0 and hist["last_empty"]:
        dig_shifts.append(dict(hist["last_empty"]))
    data["shifts"] = dig_shifts
    since_ts = ""
    if hist["first_empty"]:
        since_ts = str(hist["first_empty"].get("ts") or "")
    elif hist["last_empty"]:
        since_ts = str(hist["last_empty"].get("ts") or "")
    data["empty_checks"] = {
        "count": int(hist["empty_n"] or 0),
        "since": since_ts,
        "last_ts": str((hist["last_empty"] or {}).get("ts") or ""),
    }
    if hist["last_real"]:
        data["last_real_shift"] = dict(hist["last_real"])
    # Ticket id: CLAIM on shift → outputs.tickets → reason blob (pc-1174)
    outs = data.get("outputs") or {}
    tickets = outs.get("tickets") if isinstance(outs, dict) else None
    tid = ""
    title = ""
    if hist["last_real"]:
        tid = str(hist["last_real"].get("ticket_id") or "").strip()
        title = str(hist["last_real"].get("ticket_title") or "").strip()
    if not tid and isinstance(tickets, list) and tickets:
        tid = str(tickets[0] or "").strip()
    if not tid and hist["last_real"]:
        blob = str(hist["last_real"].get("reason") or "")
        m = re.search(r"\b([a-z]{1,12}-\d+)\b", blob, re.I)
        if m:
            tid = m.group(1)
    if tid:
        data["last_real_ticket"] = {
            "id": tid,
            "title": title,
            "ts": str((hist["last_real"] or {}).get("ts") or ""),
        }
        # Stamp onto last_real_shift for digShiftTicketId
        if isinstance(data.get("last_real_shift"), dict):
            data["last_real_shift"]["ticket_id"] = tid
            if title:
                data["last_real_shift"]["ticket_title"] = title
        if dig_shifts and not is_empty_check_shift(dig_shifts[0]):
            dig_shifts[0] = dict(dig_shifts[0])
            dig_shifts[0]["ticket_id"] = tid
            if title:
                dig_shifts[0]["ticket_title"] = title
            data["shifts"] = dig_shifts
    return data


def _ledger_dir_candidates():
    """Possible WF ledger dirs (roster path ≠ daemon WorkingDirectory on host).

    Hire/roster often lives under ``.protocolcity/workforce/local`` while the
    launchd daemon uses package ``workforce/local`` (separate ledger). Prefer
    all existing dirs; pick newest file per hand in last_shift_from_local_ledger.
    """
    out = []
    seen = set()

    def add(path):
        if not path:
            return
        ap = os.path.abspath(path)
        if ap in seen:
            return
        if os.path.isdir(ap):
            seen.add(ap)
            out.append(ap)

    env_led = (os.environ.get("SUITE_WF_LEDGER") or "").strip()
    if env_led:
        add(env_led if env_led.endswith("ledger") else os.path.join(env_led, "ledger"))
    env_local = (os.environ.get("WORKFORCE_LOCAL") or "").strip()
    if env_local:
        add(os.path.join(env_local, "ledger") if not env_local.endswith("ledger") else env_local)
    add(os.path.join(_wf_local_root(), "ledger"))
    city = (os.environ.get("SUITE_CITY_ROOT") or CITY_ROOT or "").strip()
    if city:
        add(os.path.join(city, "workforce", "local", "ledger"))
        add(os.path.join(city, ".protocolcity", "workforce", "local", "ledger"))
    # Package checkout next to ProtocolCity (OneSeo/workforce/local)
    try:
        suite_dir = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.dirname(suite_dir)
        workspace = os.path.dirname(repo)
        add(os.path.join(workspace, "workforce", "local", "ledger"))
    except Exception:
        pass
    return out


def last_shift_from_local_ledger(name):
    """Fast local ledger tail → last_shift dict (mtime-cached; pc-922)."""
    name = (name or "").strip()
    if not name or name in ("you", "You"):
        return None
    best_path = None
    best_mtime = -1.0
    for d in _ledger_dir_candidates():
        path = os.path.join(d, "%s.log" % name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime > best_mtime:
            best_mtime = mtime
            best_path = path
    if not best_path:
        return None
    cache_key = name + "|" + best_path
    cached = _LAST_SHIFT_CACHE.get(cache_key)
    if cached and cached[0] == best_mtime:
        return cached[1]
    text, _ = _read_tail(best_path, max_bytes=4000)
    last = parse_ledger_last_shift(text or "")
    _LAST_SHIFT_CACHE[cache_key] = (best_mtime, last)
    return last


def last_real_from_local_ledger(name):
    """Deeper ledger partition → last real shift + ticket (pc-1174 / §9).

    Light people scene only has last_shift (often queue-empty SKIP). Agents face
    needs last *real* work id/title so empty thrash does not hide closes.
    Mtime-cached; deeper tail than last_shift_from_local_ledger.
    """
    name = (name or "").strip()
    if not name or name in ("you", "You"):
        return None
    best_path = None
    best_mtime = -1.0
    for d in _ledger_dir_candidates():
        path = os.path.join(d, "%s.log" % name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime > best_mtime:
            best_mtime = mtime
            best_path = path
    if not best_path:
        return None
    cache_key = name + "|" + best_path
    cached = _LAST_REAL_CACHE.get(cache_key)
    if cached and cached[0] == best_mtime:
        return cached[1]
    text, _ = _read_tail(best_path, max_bytes=48000)
    deep = parse_ledger_shifts(text or "", limit=80)
    hist = partition_shift_history(deep, max_meaningful=6)
    pack = {
        "last_real_shift": None,
        "last_real_ticket": None,
        "empty_checks": {
            "count": int(hist.get("empty_n") or 0),
            "since": str((hist.get("first_empty") or {}).get("ts") or ""),
            "last_ts": str((hist.get("last_empty") or {}).get("ts") or ""),
        },
    }
    # pc-1184: prefer first meaningful *with* ticket id over process noise
    last_real = hist.get("last_real")
    meaningful = hist.get("meaningful") or []
    if meaningful:
        with_tid = None
        for row in meaningful:
            if not isinstance(row, dict):
                continue
            if is_process_only_warn(row) or is_empty_check_shift(row):
                continue
            tid_try = str(row.get("ticket_id") or "").strip()
            if not tid_try:
                blob = str(row.get("reason") or "")
                m = re.search(r"\b([a-z]{1,12}-\d+)\b", blob, re.I)
                if m:
                    tid_try = m.group(1)
            if tid_try:
                with_tid = dict(row)
                with_tid["ticket_id"] = tid_try
                break
        if with_tid is not None:
            last_real = with_tid
        elif last_real and is_process_only_warn(last_real):
            # Skip process-only head; take next real throughput if any
            for row in meaningful[1:]:
                if row and not is_process_only_warn(row) and not is_empty_check_shift(
                    row
                ):
                    last_real = row
                    break
    if last_real:
        pack["last_real_shift"] = dict(last_real)
        tid = str(last_real.get("ticket_id") or "").strip()
        if not tid:
            blob = str(last_real.get("reason") or "")
            m = re.search(r"\b([a-z]{1,12}-\d+)\b", blob, re.I)
            if m:
                tid = m.group(1)
        if tid:
            pack["last_real_ticket"] = {
                "id": tid,
                "title": str(last_real.get("ticket_title") or "").strip(),
                "ts": str(last_real.get("ts") or ""),
            }
            pack["last_real_shift"]["ticket_id"] = tid
    _LAST_REAL_CACHE[cache_key] = (best_mtime, pack)
    return pack


def enrich_people_scene(data):
    """Stamp soft homeKey / workspace_ops / staff for Map (pc-567).

    WorkForce scene groups staff but does not always emit homeKey or staff on
    each worker. Map paint + dig-in use these so ops jobs park on the city
    staff ring and never dig-in as Project · ops.

    pc-922: light WorkForce scene strips last_shift (and why=light). Bridge
    local ledger tails so Agent activities rail can show error / vendor_limit
    / SKIP without paying full-scene queue probes.

    pc-1174 / ALWAYS_WORK §9: also stamp last_real_shift + last_real_ticket so
    Agents face can show last real work when last_shift is empty-check noise.
    """
    if not isinstance(data, dict):
        return data
    roster = load_wf_roster_workers()
    sectors = data.get("sectors")
    if not isinstance(sectors, list):
        return data
    inflight = data.get("in_flight") or []
    if not isinstance(inflight, list):
        inflight = []
    inflight_set = {str(x) for x in inflight}
    for sec in sectors:
        if not isinstance(sec, dict):
            continue
        role = str(sec.get("role") or "").lower()
        sec_staff = role == "staff"
        sec_wd = str(sec.get("workdir") or "")
        for w in sec.get("workers") or []:
            if not isinstance(w, dict):
                continue
            name = str(w.get("name") or "")
            row = roster.get(name) if name else None
            if not isinstance(row, dict):
                row = {}
            w_wd = str(w.get("workdir") or row.get("workdir") or sec_wd or "")
            norm = w_wd.replace("\\", "/")
            is_staff = (
                sec_staff
                or _roster_row_is_staff(row)
                or w.get("staff") in (True, 1, "1", "true", "True")
                or w.get("workspace_ops") in (True, 1, "1", "true", "True")
                or w.get("homeKey") == "__staff__"
                or "/.protocolcity/ops" in norm
            )
            if is_staff:
                w["staff"] = True
                w["workspace_ops"] = True
                w["homeKey"] = "__staff__"
                if not w.get("project") or str(w.get("project")).lower() in (
                    "ops",
                    "",
                ):
                    w["project"] = "Workspace ops"
            else:
                if "staff" not in w:
                    w["staff"] = False
                if "workspace_ops" not in w:
                    w["workspace_ops"] = False
                if not w.get("homeKey"):
                    leaf = os.path.basename(w_wd.rstrip("/")) if w_wd else ""
                    low = leaf.lower()
                    if low and low not in ("ops", ".protocolcity", "unknown"):
                        w["homeKey"] = low
            # --- pc-922: last_shift from local ledger when light scene nulls it
            ls = w.get("last_shift")
            if not isinstance(ls, dict) or not ls.get("outcome"):
                parsed = last_shift_from_local_ledger(name) if name else None
                if parsed:
                    w["last_shift"] = parsed
                    ls = parsed
            if isinstance(ls, dict) and ls.get("outcome"):
                oc = str(ls.get("outcome") or "").lower()
                reason = str(ls.get("reason") or "").strip()
                why = str(w.get("why") or "").strip().lower()
                health = str(w.get("health") or "").strip().lower()
                live = name in inflight_set or oc == "running"
                # Surface terminal fail/skip honestly; do not overwrite live tick
                if not live and oc in (
                    "error",
                    "vendor_limit",
                    "crashed",
                    "skip",
                    "warn",
                    "scope_deny",
                ):
                    if health in ("", "ok", "healthy", "good"):
                        if oc in ("error", "crashed"):
                            w["health"] = "err"
                        elif oc == "vendor_limit":
                            w["health"] = "amber"
                        elif oc == "skip":
                            # lock-held skip with ready work is amber-ish; else ok
                            if "lock" in reason.lower():
                                w["health"] = "amber"
                    if why in ("", "light", "ok", "healthy"):
                        if oc == "vendor_limit":
                            w["why"] = reason or "vendor limit"
                        elif oc in ("error", "crashed"):
                            w["why"] = reason or "last run failed"
                        elif oc == "skip":
                            w["why"] = reason or "last fire skipped"
            # --- pc-1174: last real work past empty thrash (Agents face)
            if name and (
                not isinstance(w.get("last_real_shift"), dict)
                or not w.get("last_real_ticket")
            ):
                pack = last_real_from_local_ledger(name)
                if pack:
                    if (
                        not isinstance(w.get("last_real_shift"), dict)
                        and pack.get("last_real_shift")
                    ):
                        w["last_real_shift"] = pack["last_real_shift"]
                    if not w.get("last_real_ticket") and pack.get(
                        "last_real_ticket"
                    ):
                        w["last_real_ticket"] = pack["last_real_ticket"]
                    if not w.get("empty_checks") and pack.get("empty_checks"):
                        w["empty_checks"] = pack["empty_checks"]
    return data


def people_scene_from_disk_roster():
    """Minimal WorkForce /api/scene shape from roster.json when :8797 is down.

    Report (Overview) and map-bootstrap use this so 'No agents hired' is never
    shown when the disk roster has rows (pc-409 / pc-407). Live fields stay
    idle/unknown — no fake in_flight.
    """
    workers = load_wf_roster_workers()
    if not workers:
        return {
            "ok": True,
            "source": "disk_roster",
            "daemon": {"reachable": False, "note": "roster empty or unreadable"},
            "sectors": [],
            "in_flight": [],
        }
    # Group by home leaf (project folder name or __staff__)
    groups = {}  # key → {"role", "leaf", "workplace", "workers": []}
    for name, row in workers.items():
        kind = str(row.get("kind") or "lane").lower()
        if kind == "citizen":
            continue
        staff = _roster_row_is_staff(row)
        wd = str(row.get("workdir") or "").rstrip("/")
        leaf = os.path.basename(wd) if wd else ""
        if staff:
            key = "__staff__"
            role = "staff"
            workplace = os.path.basename(CITY_ROOT.rstrip("/")) or "workspace"
            home_leaf = workplace
        else:
            key = _slug_norm(leaf) or leaf or name
            role = "hired"
            workplace = leaf or name
            home_leaf = leaf or name
        bucket = groups.setdefault(
            key,
            {
                "role": role,
                "workdir": wd,
                "workplace": workplace,
                "leaf": home_leaf,
                "workers": [],
            },
        )
        bucket["workers"].append(
            {
                "name": name,
                "display": row.get("display") or name,
                "kind": kind if kind in ("lane", "job", "worker") else kind,
                "health": "idle",
                "queue": None,
                "next_fire": row.get("next_fire") or row.get("schedule"),
                "last_shift": None,
                # pc-567: soft Map home — staff ring, not Project · ops leaf
                "staff": bool(staff),
                "workspace_ops": bool(staff),
                "homeKey": "__staff__" if staff else (leaf or "").lower() or "",
                "project": "Workspace ops" if staff else (leaf or ""),
            }
        )
    sectors = []
    for key, g in groups.items():
        sectors.append(
            {
                "id": key,
                "role": g["role"],
                "workdir": g["workdir"],
                "workplace": g["workplace"],
                "workers": g["workers"],
            }
        )
    return {
        "ok": True,
        "source": "disk_roster",
        "daemon": {
            "reachable": False,
            "note": "WorkForce offline — hired list from disk roster",
        },
        "sectors": sectors,
        "in_flight": [],
    }


def _people_payload_usable(people):
    """True when WF scene (or fallback) has sectors we can roll up."""
    if not people or not isinstance(people, dict):
        return False
    if people.get("error"):
        return False
    sectors = people.get("sectors")
    return isinstance(sectors, list) and len(sectors) > 0


def _read_tail(path, max_bytes=6000):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            raw = f.read().decode("utf-8", errors="replace")
        if size > max_bytes:
            raw = "…\n" + raw
        return raw, size
    except Exception:
        return None, 0


def _file_mtime_iso(path):
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(
            ts, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


_PATH_IN_TEXT = re.compile(
    r"(?:report written:\s*)?(/[^\s\"']+\.(?:md|json|txt|html|log))",
    re.I,
)
_TICKET_IN_TEXT = re.compile(
    r"\bticket:\s*([a-z]{1,6}-\d+|none)\b", re.I,
)
_PASS_HDR = re.compile(r"^---\s*pass\s+(\d+)\s*---\s*$", re.I | re.M)


def _pass_from_result_obj(n, obj):
    """Map a CLI result envelope (Claude/Grok/etc.) to a showable pass."""
    if not isinstance(obj, dict):
        return None
    text = obj.get("result")
    if text is None and obj.get("type") != "result":
        text = obj.get("message") or obj.get("error")
        if text is None:
            return None
    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
    cost = obj.get("total_cost_usd")
    if cost is None and usage:
        cost = usage.get("total_cost_usd")
    return {
        "n": n,
        "kind": "result",
        "subtype": obj.get("subtype") or "",
        "is_error": bool(obj.get("is_error")),
        "text": text if isinstance(text, str) else ("" if text is None else str(text)),
        "duration_ms": obj.get("duration_ms"),
        "cost_usd": cost,
        "num_turns": obj.get("num_turns"),
        "stop_reason": obj.get("stop_reason") or "",
    }


def _parse_pass_chunk(n, chunk):
    """Parse one pass body — prefer JSON result line, else plain text."""
    chunk = (chunk or "").strip()
    if not chunk:
        return {"n": n, "kind": "plain", "text": ""}
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        parsed = _pass_from_result_obj(n, obj)
        if parsed is not None:
            return parsed
    if chunk.startswith("{"):
        try:
            obj = json.loads(chunk)
            parsed = _pass_from_result_obj(n, obj)
            if parsed is not None:
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return {"n": n, "kind": "plain", "text": chunk[:6000]}


def parse_run_stdout(text):
    """Turn raw worker .out into skimmable passes (agent JSON → prose).

    Agent CLIs often write::

        --- pass 1 ---
        {"type":"result","result":"human prose…","total_cost_usd":0.25,…}

    Person files should show the prose + cost/duration, not the JSON shell.
    """
    if not text or not str(text).strip():
        return {"format": "empty", "passes": []}
    body = str(text)
    if body.startswith("…"):
        body = body.lstrip("…").lstrip("\n")
    matches = list(_PASS_HDR.finditer(body))
    passes = []
    if matches:
        for i, m in enumerate(matches):
            n = int(m.group(1))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            passes.append(_parse_pass_chunk(n, body[start:end]))
    else:
        chunk = body.strip()
        one = _parse_pass_chunk(1, chunk)
        if one.get("kind") == "result":
            passes = [one]
        else:
            return {"format": "plain", "passes": [
                {"n": 1, "kind": "plain", "text": chunk[:6000]}
            ]}
    fmt = (
        "agent_json"
        if any(p.get("kind") == "result" for p in passes)
        else "plain"
    )
    return {"format": fmt, "passes": passes}


def extract_run_artifacts(text):
    """Pull showable paths / ticket refs from job stdout (best-effort)."""
    if not text:
        return [], []
    # Prefer human prose from agent envelopes so paths inside result: match
    search_text = text
    parsed = parse_run_stdout(text)
    if parsed.get("format") == "agent_json":
        bits = [p.get("text") or "" for p in parsed.get("passes") or []]
        if any(bits):
            search_text = "\n".join(bits) + "\n" + text
    root = os.path.realpath(CITY_ROOT)
    found = []
    seen = set()
    for m in _PATH_IN_TEXT.finditer(search_text):
        abs_p = m.group(1)
        rel = city_rel(abs_p)
        if not rel or rel in seen:
            continue
        if not os.path.isfile(abs_p):
            # still surface if under city even if rotated away
            if not abs_p.startswith(root + os.sep):
                continue
        seen.add(rel)
        found.append({
            "path": rel,
            "name": os.path.basename(rel),
            "exists": os.path.isfile(abs_p),
            "md": rel.lower().endswith(".md"),
        })
    tickets = []
    for m in _TICKET_IN_TEXT.finditer(search_text):
        tid = m.group(1)
        if tid.lower() != "none":
            tickets.append(tid)
    return found, tickets


def list_ops_reports(
    root=None,
    *,
    name: str = "",
    limit: int = 20,
) -> list:
    """Recent markdown deliverables from workspace ops / job report dirs (pc-432).

    Scans known landings under the city root and optional job workdir. Returns
    city-relative paths newest-first. Honest empty list when nothing ran.
    """
    root = os.path.realpath(root or CITY_ROOT)
    limit = max(1, min(int(limit or 20), 50))
    name_l = (name or "").strip().lower()
    # Function aliases → filename stems often used in reports
    stems = set()
    if name_l:
        stems.add(name_l)
        aliases = {
            "city-clerk": "clerk",
            "city-marshal": "marshal",
            "city-correspondent": "correspondent",
            "founder-brief": "clerk",
            "city-steward": "marshal",
            "wren": "correspondent",
        }
        if name_l in aliases:
            stems.add(aliases[name_l])
        stems.add(name_l.replace("city-", ""))

    candidate_dirs = [
        os.path.join(root, ".protocolcity", "ops", "local", "reports"),
        os.path.join(root, ".protocolcity", "ops", "reports"),
        os.path.join(root, ".protocolcity", "reports"),
        os.path.join(root, "local", "reports"),
    ]
    # Job workdir reports (seed-ops uses .protocolcity/ops)
    if name_l:
        row = load_wf_roster_row(name_l) or load_wf_roster_row(name) or {}
        wd = row.get("workdir") or ""
        if wd and os.path.isdir(wd):
            candidate_dirs.append(os.path.join(wd, "local", "reports"))
            candidate_dirs.append(os.path.join(wd, "reports"))

    found = []
    seen = set()
    for d in candidate_dirs:
        if not os.path.isdir(d):
            continue
        for dirpath, _dirnames, filenames in os.walk(d):
            # Skip deep noise
            rel_depth = os.path.relpath(dirpath, d).count(os.sep)
            if rel_depth > 3:
                continue
            for fn in filenames:
                if not fn.endswith(".md"):
                    continue
                if fn.startswith("feedback-"):
                    continue
                low = fn.lower()
                if stems:
                    if not any(s in low for s in stems):
                        # allow folder-named reports: .../clerk/foo.md
                        folder = os.path.basename(dirpath).lower()
                        if folder not in stems and not any(
                            s == folder for s in stems
                        ):
                            continue
                abs_path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(abs_path)
                except OSError:
                    continue
                rel = city_rel(abs_path)
                if not rel or rel in seen:
                    continue
                seen.add(rel)
                found.append(
                    {
                        "path": rel,
                        "name": fn,
                        "mtime": _file_mtime_iso(abs_path),
                        "mtime_epoch": st.st_mtime,
                        "bytes": st.st_size,
                    }
                )
    found.sort(key=lambda x: x.get("mtime_epoch") or 0, reverse=True)
    for item in found:
        item.pop("mtime_epoch", None)
    return found[:limit]


def enrich_worker_outputs(data):
    """Attach run log / stdout tails for person file Output vs Work panels."""
    if not isinstance(data, dict):
        return data
    name = data.get("name") or ""
    # Derive local dir from roster path (pc-351) — never hardcode workforce/local
    wf_local = os.path.dirname(os.path.abspath(WF_ROSTER))
    out_path = os.path.join(wf_local, "run", "%s.out" % name)
    log_path = os.path.join(wf_local, "ledger", "%s.log" % name)
    out_text, out_bytes = _read_tail(out_path)
    log_text, log_bytes = _read_tail(log_path, max_bytes=3000)
    artifacts, tickets = extract_run_artifacts(out_text or "")
    stdout_parsed = parse_run_stdout(out_text or "")
    kind = (data.get("kind") or "").lower()
    reports = []
    if kind == "job" or name:
        try:
            reports = list_ops_reports(name=name, limit=8)
        except Exception:
            reports = []
    data["reports"] = reports
    data["outputs"] = {
        "kind": "job" if kind == "job" else "worker",
        "stdout_path": city_rel(out_path),
        "stdout_bytes": out_bytes,
        "stdout_tail": out_text,
        "stdout_parsed": stdout_parsed,
        "stdout_mtime": _file_mtime_iso(out_path) if out_bytes else None,
        "log_path": city_rel(log_path),
        "log_bytes": log_bytes,
        "log_tail": log_text,
        "artifacts": artifacts,
        "tickets": tickets,
        "reports": reports,
        "has_showable": bool(
            artifacts or tickets or reports or
            (kind == "job" and out_text and out_text.strip()) or
            (kind != "job" and (data.get("holding") or data.get("ready")))
        ),
    }
    return data


def list_skills_near_worker(workdir: str, name: str = "") -> list:
    """Disk skills for agent dig-in (pc-411).

    Looks under project + workspace (city root) ``.claude/skills`` and
    ``.cursor/skills`` (and agent-local ``workers/<name>/skills``). Returns
    city-relative paths + skill folder id.
    """
    out = []
    seen = set()
    roots = []
    wd = (workdir or "").strip()
    if wd and os.path.isdir(wd):
        roots.append(wd)
    city = os.path.realpath(CITY_ROOT)
    if city and os.path.isdir(city) and city not in roots:
        roots.append(city)
    # Walk up once for workspace AGENTS root
    if wd:
        try:
            parent = os.path.dirname(os.path.realpath(wd))
            if parent and parent not in roots and os.path.isdir(parent):
                if os.path.isfile(os.path.join(parent, "AGENTS.md")):
                    roots.append(parent)
        except OSError:
            pass
    skill_dirs = []
    for base in roots:
        for rel in (
            os.path.join(".claude", "skills"),
            os.path.join(".cursor", "skills"),
            os.path.join(".grok", "skills"),
        ):
            skill_dirs.append(os.path.join(base, rel))
        if name:
            skill_dirs.append(
                os.path.join(base, "workers", name, "skills")
            )
            skill_dirs.append(
                os.path.join(base, "workers", name, ".claude", "skills")
            )
    for sd in skill_dirs:
        if not os.path.isdir(sd):
            continue
        try:
            names = sorted(os.listdir(sd))
        except OSError:
            continue
        for sid in names:
            if not sid or sid.startswith("."):
                continue
            sdir = os.path.join(sd, sid)
            if not os.path.isdir(sdir):
                continue
            skill_md = os.path.join(sdir, "SKILL.md")
            if not os.path.isfile(skill_md):
                skill_md = os.path.join(sdir, "skill.md")
            if not os.path.isfile(skill_md):
                continue
            rel = city_rel(skill_md)
            if not rel or rel in seen:
                continue
            seen.add(rel)
            out.append(
                {
                    "id": sid,
                    "name": sid,
                    "path": rel,
                    "file": os.path.basename(skill_md),
                }
            )
            if len(out) >= 40:
                return out
    return out


def enrich_worker_law(data):
    """Add city-relative `path` on each law stack entry for in-suite /read.

    Workspace ops jobs (``.protocolcity/ops``) are municipal seats — they have
    L0 city law + L2/L3 papers under the ops kit, **not** an L1 neighborhood
    AGENTS.md. Inventing ``.protocolcity/ops/AGENTS.md`` made Map dig-in show
    "Could not open: not found · path AGENTS.md" (2026-07-27 github-desk).
    """
    if not isinstance(data, dict):
        return data
    name = data.get("name") or ""
    workdir = data.get("workdir") or ""
    row = load_wf_roster_row(name) or {}
    contract = row.get("contract") or ""
    prompt = row.get("prompt") or ""
    # Fallback: workers/<name>/ under workdir (hire convention)
    if not contract and workdir:
        contract = os.path.join(workdir, "workers", name, "CONTRACT.md")
    if not prompt and workdir:
        prompt = os.path.join(workdir, "workers", name, "prompt.md")
    # Also try ops/tasks/<name>-lane/ (tradeOS legacy)
    if workdir and name and not os.path.isfile(contract):
        alt = os.path.join(workdir, "ops", "tasks", name + "-lane", "CONTRACT.md")
        if os.path.isfile(alt):
            contract = alt
            prompt = os.path.join(
                workdir, "ops", "tasks", name + "-lane", "prompt.md")

    wd_rel = city_rel(workdir) or ""
    norm_wd = workdir.replace("\\", "/").rstrip("/")
    is_workspace_ops = (
        "/.protocolcity/ops" in norm_wd
        or wd_rel.replace("\\", "/").startswith(".protocolcity/ops")
        or wd_rel in (".protocolcity/ops", "ops")
        or _roster_row_is_staff(row)
    )
    # Prefer roster contract/prompt paths when abs files exist under city
    if contract and not os.path.isfile(contract):
        # sometimes roster stores city-rel already
        c_abs = safe_city_path(contract) if not os.path.isabs(contract) else None
        if c_abs and os.path.isfile(c_abs):
            contract = c_abs
    if prompt and not os.path.isfile(prompt):
        p_abs = safe_city_path(prompt) if not os.path.isabs(prompt) else None
        if p_abs and os.path.isfile(p_abs):
            prompt = p_abs

    law = []
    for entry in data.get("law") or []:
        e = dict(entry)
        label = (e.get("label") or "").lower()
        fn = e.get("file") or ""
        lv = str(e.get("level") or "").upper()
        path = None
        if "city rules" in label or (lv == "L0" and fn == "AGENTS.md"):
            path = "AGENTS.md"
        elif "neighborhood" in label or (lv == "L1" and fn == "AGENTS.md"):
            # Ops / Office staff seats are not a product neighborhood — no L1.
            if is_workspace_ops:
                continue
            path = (wd_rel + "/AGENTS.md") if wd_rel else "AGENTS.md"
        elif fn == "CONTRACT.md" or "contract" in label:
            path = city_rel(contract)
        elif fn == "prompt.md" or "prompt" in label:
            path = city_rel(prompt)
        e["path"] = path
        e["readable"] = bool(
            path and safe_city_path(path) and os.path.isfile(safe_city_path(path))
        )
        # Drop unreadable invented paths (do not paint dead "open" rows)
        if path and not e["readable"] and lv in ("L1",):
            continue
        # Citizen chrome labels — match Map depth words (pc-1382 / pc-1393)
        if lv == "L0" or "city" in label or (
            path == "AGENTS.md" and not wd_rel
        ):
            e["citizen_label"] = "workspace"
        elif lv == "L1" or "neighborhood" in label or "project" in label:
            e["citizen_label"] = "project"
        elif lv == "L2" or "contract" in label or fn == "CONTRACT.md":
            e["citizen_label"] = "contract"
        elif lv == "L3" or "prompt" in label or fn == "prompt.md":
            e["citizen_label"] = "this run"
        else:
            e["citizen_label"] = e.get("label") or lv or "Paper"
        law.append(e)
    data["law"] = law
    if is_workspace_ops:
        data["project"] = "Workspace ops"
        data["workspace_ops"] = True
        data["homeKey"] = data.get("homeKey") or "__staff__"
    else:
        data["project"] = (
            os.path.basename(workdir.rstrip("/")) if workdir else ""
        )
        data["workspace_ops"] = False
    data["contract_path"] = city_rel(contract)
    data["prompt_path"] = city_rel(prompt)
    try:
        data["skills"] = list_skills_near_worker(workdir, name)
    except Exception:
        data["skills"] = []
    # outputs first (ticket ids from .out), then dig shift partition (pc-964)
    data = enrich_worker_outputs(data)
    try:
        data = enrich_worker_shift_history(data)
    except Exception:
        pass
    return data


def _fetch_json(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


# pc-1093: last-good body may ride through a brief upstream blip, but never
# as unbounded "fresh" 200s. Beyond this age, fail closed (None → 502).
_STALE_SERVE_MAX = 60.0  # seconds


def _cached_fetch(url, timeout=5):
    """Short-TTL GET proxy with process-local cache. Returns raw bytes or None.

    On upstream error: return last-good body only if younger than
    ``_STALE_SERVE_MAX`` (pc-1093). Older fossils → None. Callers shipping
    HTTP 200 must stamp degraded via ``_cache_entry_is_stale``.
    """
    entry = _cache.get(url)
    now = time.monotonic()
    if entry:
        body, ts = entry
        if now - ts < _CACHE_TTL:
            return body
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
        _cache[url] = (body, time.monotonic())
        return body
    except Exception:
        if not entry:
            return None
        body, ts = entry
        if (now - ts) > _STALE_SERVE_MAX:
            return None
        return body


def _cache_entry_age(url):
    """Seconds since last successful write for url, or None if uncached."""
    entry = _cache.get(url)
    if not entry:
        return None
    try:
        return time.monotonic() - float(entry[1])
    except (TypeError, ValueError, IndexError):
        return None


def _cache_entry_is_stale(url):
    """True when the cached body is past normal TTL (stale-on-error path)."""
    age = _cache_entry_age(url)
    return age is not None and age >= _CACHE_TTL


def _stamp_degraded_json(body, url):
    """If body is JSON object served past TTL, mark degraded (pc-1093)."""
    if body is None or not _cache_entry_is_stale(url):
        return body
    try:
        data = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    except Exception:
        return body
    if not isinstance(data, dict):
        return body
    data = dict(data)
    data["degraded"] = True
    data["cache"] = "stale"
    age = _cache_entry_age(url)
    if age is not None:
        data["cache_age_s"] = round(age, 2)
    try:
        return json.dumps(data, separators=(",", ":")).encode("utf-8")
    except Exception:
        return body


def _cached_json(url, timeout=5):
    """Cached fetch returning parsed JSON or None.

    pc-1093: past-TTL (stale-on-error) bodies get degraded=True so consumers
    do not treat fossil agent/scene state as fresh.
    """
    raw = _cached_fetch(url, timeout=timeout)
    try:
        data = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        return None
    if isinstance(data, dict) and _cache_entry_is_stale(url):
        data = dict(data)
        data["degraded"] = True
        data["cache"] = "stale"
        age = _cache_entry_age(url)
        if age is not None:
            data["cache_age_s"] = round(age, 2)
    return data


def _invalidate_cache(*urls):
    """Evict one or more URL entries from the process-local cache."""
    _api_cache.invalidate(*urls)


def _desk_bootstrap():
    """Fan out four upstream calls in parallel; return merged dict (pc-267).

    pc-574: city + attention are in-process (no :8796).
    """
    return _api_desk_bootstrap(
        CITYLENS,
        WORKFORCE,
        DESK,
        cached_json=_cached_json,
        city_fn=(None if _CITYLENS_REMOTE else (lambda: city_payload(light=False))),
        attention_fn=(None if _CITYLENS_REMOTE else attention_payload),
    )


def _store_from_desk_join_file(path):
    """Zero-count store row when desk-join.json proves a join (pc-557/pc-559).

    Degraded map-bootstrap ships city_structure_from_disk when citylens is
    down — without this, Join leaves a sticky "No desk store" banner until
    engines recover.
    """
    join_path = os.path.join(path, ".protocolcity", "desk-join.json")
    if not os.path.isfile(join_path):
        return None, None
    try:
        with open(join_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    slug = _slug_norm(data.get("slug") or "")
    if not slug:
        return None, None
    store = {
        "backlog": 0,
        "in_progress": 0,
        "in_review": 0,
        "done": 0,
        "urgent_backlog": 0,
        "ready": 0,
    }
    return store, slug


def _hood_inventory(path):
    """Project or workspace-root inventory for Map drill-in (pc-562 / pc-1040).

    Prefer protocolcity.citylens helpers (same shape as /api/city). Fall back
    to a shallow listing if the package is unavailable.

    When ``path`` is the city root, use workspace-mode papers census (nested
    docs/.claude/scripts only — never parcel dirs) and skip agent_papers.
    """
    try:
        from protocolcity.citylens import (
            hood_agent_papers,
            hood_root_entries,
            hood_root_mds,
            workspace_root_mds,
        )

        try:
            is_city = os.path.realpath(path) == os.path.realpath(CITY_ROOT)
        except OSError:
            is_city = False
        if is_city:
            return {
                "root_entries": hood_root_entries(path),
                "root_mds": workspace_root_mds(path),
                "agent_papers": [],
            }
        return {
            "root_entries": hood_root_entries(path),
            "root_mds": hood_root_mds(path),
            "agent_papers": hood_agent_papers(path),
        }
    except Exception:
        pass
    # Shallow fallback — dirs + files at project root only
    entries = []
    mds = []
    try:
        names = sorted(os.listdir(path), key=str.lower)
    except OSError:
        names = []
    for n in names:
        if not n or n.startswith("."):
            continue
        p = os.path.join(path, n)
        try:
            is_dir = os.path.isdir(p)
            is_file = os.path.isfile(p)
        except OSError:
            continue
        if is_dir:
            entries.append(
                {"name": n, "kind": "dir", "ftype": "folder", "path": p}
            )
        elif is_file:
            row = {"name": n, "kind": "file", "path": p}
            if n.lower().endswith(".md"):
                row["md"] = True
                row["ftype"] = "document"
                md_row = dict(row)
                md_row["depth"] = 1
                md_row["rel"] = n
                if n.lower() in (
                    "agents.md",
                    "perimeter.md",
                    "office_perimeter.md",
                    "city_edges.md",
                    "atlas.md",
                    "claude.md",
                    "grok.md",
                    "codex.md",
                    "cursor.md",
                    "gemini.md",
                ):
                    md_row["instruction"] = True
                    md_row["rule"] = True
                mds.append(md_row)
            entries.append(row)
    return {
        "root_entries": entries,
        "root_mds": mds,
        "agent_papers": [],
    }


def _hood_surface_inventory(path):
    """pc-900: one listdir only — Map papers/instructions seats, not dig tree.

    Prefer citylens hood_root_entries; never walk deep root_mds here.
    """
    try:
        from protocolcity.citylens import hood_root_entries

        entries = hood_root_entries(path)
        if isinstance(entries, list):
            return {"root_entries": entries}
    except Exception:
        pass
    inv = _hood_inventory(path)
    # Drop deep mds from fallback when used as surface fill
    return {"root_entries": inv.get("root_entries") or []}


def _enrich_neighborhood_inventory_shallow(hoods):
    """pc-900: fill empty root_entries only (cheap). Never deep root_mds."""
    if not isinstance(hoods, list):
        return hoods
    out = []
    for h in hoods:
        if not isinstance(h, dict):
            out.append(h)
            continue
        row = dict(h)
        entries = row.get("root_entries")
        need = not isinstance(entries, list) or len(entries) == 0
        path = row.get("path") or ""
        if need and path and os.path.isdir(path):
            inv = _hood_surface_inventory(path)
            row["root_entries"] = inv.get("root_entries") or []
        elif not isinstance(entries, list):
            row["root_entries"] = []
        if not isinstance(row.get("root_mds"), list):
            row["root_mds"] = []
        out.append(row)
    return out


def _enrich_neighborhood_inventory(hoods):
    """Fill empty root_mds/root_entries on neighborhood rows (pc-562).

    Live citylens that predates the inventory fields, or a structure shell
    that forgot them, still paints a usable Map drill-in.
    """
    if not isinstance(hoods, list):
        return hoods
    out = []
    for h in hoods:
        if not isinstance(h, dict):
            out.append(h)
            continue
        row = dict(h)
        entries = row.get("root_entries")
        mds = row.get("root_mds")
        papers = row.get("agent_papers")
        need = (
            not isinstance(entries, list)
            or not isinstance(mds, list)
            or (len(entries) == 0 and len(mds) == 0)
        )
        path = row.get("path") or ""
        if need and path and os.path.isdir(path):
            inv = _hood_inventory(path)
            if not isinstance(entries, list) or len(entries) == 0:
                row["root_entries"] = inv["root_entries"]
            if not isinstance(mds, list) or len(mds) == 0:
                row["root_mds"] = inv["root_mds"]
            if not isinstance(papers, list) or len(papers) == 0:
                row["agent_papers"] = inv["agent_papers"]
        else:
            if not isinstance(entries, list):
                row["root_entries"] = []
            if not isinstance(mds, list):
                row["root_mds"] = []
            if not isinstance(papers, list):
                row["agent_papers"] = []
        out.append(row)
    return out


# pc-1211: /api/city full-enrich cache + single-flight budget.
# Walk is unbounded (disk IO per project); one background thread at a time;
# all concurrent requests share the same walk and wait up to budget.
_ENRICH_TTL = 30.0
_ENRICH_BUDGET_S = 8.0
_enrich_cache: dict = {"at": 0.0, "token": "", "data": None, "loading": False, "waiters": []}
_enrich_lock = threading.Lock()


def _enrich_with_budget(hoods, tok=""):
    """Single-flight + hard budget for /api/city full inventory enrich (pc-1211).

    Only one background thread ever walks disk at a time. Concurrent requests
    join as waiters. If the walk exceeds ENRICH_BUDGET_S, fail open to the
    unenriched hoods so the HTTP response is never held for minutes.
    """
    now = time.monotonic()
    ev = None
    with _enrich_lock:
        c = _enrich_cache
        if (
            c.get("data") is not None
            and c.get("token") == tok
            and (now - float(c.get("at") or 0)) < _ENRICH_TTL
        ):
            return c["data"]
        ev = threading.Event()
        if c.get("loading") and isinstance(c.get("waiters"), list):
            # Join existing walk.
            c["waiters"].append(ev)
        else:
            # Become the designated walk thread; also wait for own result.
            c["loading"] = True
            c["waiters"] = [ev]

            def _worker(_hoods=hoods, _tok=tok):
                result = None
                try:
                    result = _enrich_neighborhood_inventory(_hoods)
                finally:
                    with _enrich_lock:
                        if result is not None:
                            _enrich_cache.update(
                                at=time.monotonic(), token=_tok, data=result, loading=False
                            )
                        else:
                            _enrich_cache["loading"] = False
                        done = list(_enrich_cache.get("waiters") or [])
                        _enrich_cache["waiters"] = []
                    for w in done:
                        try:
                            w.set()
                        except Exception:
                            pass

            threading.Thread(target=_worker, daemon=True, name="city-enrich-bg").start()

    ev.wait(timeout=_ENRICH_BUDGET_S)
    with _enrich_lock:
        data = _enrich_cache.get("data")
        cached_tok = _enrich_cache.get("token")
    if data is not None and cached_tok == tok:
        return data
    sys.stderr.write(
        "city-enrich: budget exceeded (%.1fs) or token mismatch — serving unenriched\n"
        % _ENRICH_BUDGET_S
    )
    return hoods


def _desk_scene_store_map(timeout=1.5):
    """One compatibility scene → {slug: store counts}. Never raises."""
    try:
        scene = _citylens().desk_scene_compatible(
            DESK,
            scene_timeout=timeout,
            admin_timeout=8.0,
        )
    except Exception:
        return {}
    if not isinstance(scene, dict) or scene.get("ok") is False:
        return {}
    out = {}
    for s in scene.get("stores") or []:
        if not isinstance(s, dict):
            continue
        slug = _slug_norm(s.get("slug") or "")
        if not slug:
            continue
        try:
            counts = {
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
        raw = str(s.get("slug") or "").strip().lower()
        if raw:
            out[raw] = counts
    return out


def _attach_desk_stores(folders, store_by=None):
    """Fill folder.store from WorkLane scene (progressive paint + JOIN STORE fix)."""
    if not folders:
        return folders
    by = store_by if store_by is not None else _desk_scene_store_map()
    if not by:
        return folders
    for f in folders:
        if not isinstance(f, dict):
            continue
        keys = [
            _slug_norm(f.get("product")),
            _slug_norm(f.get("slug")),
            _slug_norm(f.get("name")),
        ]
        hit = None
        for k in keys:
            if k and k in by:
                hit = by[k]
                break
        if hit is not None:
            f["store"] = hit
    return folders


def _store_by_from_scene(scene):
    """Build {slug: store counts} from a WorkLane scene dict (tpScene).

    Same shape as ``_desk_scene_store_map`` but pure — no network. Used by
    map-bootstrap merge (pc-933) so city light folder badges match desk truth
    already present in the bootstrap payload.
    """
    if not isinstance(scene, dict):
        return {}
    out = {}
    for s in scene.get("stores") or []:
        if not isinstance(s, dict):
            continue
        slug = _slug_norm(s.get("slug") or "")
        if not slug:
            continue
        try:
            counts = {
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
        raw = str(s.get("slug") or "").strip().lower()
        if raw:
            out[raw] = counts
    return out


def merge_tp_scene_stores_into_city(city, scene):
    """pc-933: overlay tpScene store counts onto city light neighborhoods.

    City light / join-degraded paths can ship ``store={0…}`` while the same
    ``/api/map-bootstrap`` payload's ``tpScene.stores`` already has desk truth
    (backlog/ready non-zero). Folder open badges read ``hood.store``; without
    this merge they stay dead until soft poll. Prefer tpScene when present;
    leave unmatched hoods unchanged. Shallow-clones city + hoods so a shared
    citylens cache object is never mutated in place.
    """
    if not isinstance(city, dict):
        return city
    by = _store_by_from_scene(scene)
    if not by:
        return city
    n_hoods = city.get("neighborhoods")
    f_hoods = city.get("folders")
    source = None
    if isinstance(n_hoods, list) and n_hoods:
        source = n_hoods
    elif isinstance(f_hoods, list) and f_hoods:
        source = f_hoods
    if not source:
        return city
    next_hoods = [dict(h) if isinstance(h, dict) else h for h in source]
    _attach_desk_stores(next_hoods, by)
    next_city = dict(city)
    if isinstance(n_hoods, list):
        next_city["neighborhoods"] = next_hoods
    if isinstance(f_hoods, list):
        next_city["folders"] = next_hoods
    if "neighborhoods" not in next_city and "folders" not in next_city:
        next_city["neighborhoods"] = next_hoods
        next_city["folders"] = next_hoods
    next_city["desk_stores_ready"] = True
    return next_city


def city_structure_from_disk(root=None, with_desk=True):
    """Fast city shell for progressive Map paint (pc-413).

    Disk walk for folders + managed flag. One short WorkLane /api/scene
    attaches store counts so the Map does not flash JOIN STORE for every
    managed parcel while full bootstrap is still running (2026-07-28).

    pc-562: populate root_mds/root_entries so Map project drill-in is not
    blank when citylens is slow/down (degraded bootstrap path).
    """
    root = os.path.realpath(root or CITY_ROOT)
    folders = []
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        names = []
    for name in names:
        if not name or name.startswith("."):
            continue
        if name in _DETECT_SKIP_TOP or name.endswith("-backups"):
            continue
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        # pc-313 / pc-559: spaces → hyphens (SE Local HC → se-local-hc), same
        # as citylens _dir_slug / protocolcity.slugs.slugify. name.lower() left
        # "se local hc" vs store "se-local-hc" → overlay miss + sticky banner.
        slug = _slug_norm(name) or name.lower()
        store, join_slug = _store_from_desk_join_file(path)
        product = join_slug or slug
        inv = _hood_inventory(path)
        folders.append(
            {
                "name": name,
                "slug": slug,
                "path": path,
                "product": product,
                "zone": "outskirts",
                "managed": dir_managed(path),
                "store": store,
                "workers": [],
                "flags": [],
                "root_mds": inv["root_mds"],
                "root_entries": inv["root_entries"],
                "agent_papers": inv["agent_papers"],
            }
        )
    desk_ok = False
    if with_desk:
        try:
            store_by = _desk_scene_store_map(timeout=1.5)
            if store_by:
                _attach_desk_stores(folders, store_by)
                desk_ok = True
        except Exception:
            pass
    # pc-951: degraded structure shell must still ship L0 root_files so Map
    # OneSeo hub paints Instructions (same shape as citylens light census).
    # pc-1040: also ship workspace root_mds (nested papers, same project shape).
    root_files = []
    root_mds = []
    try:
        from protocolcity.citylens import root_files_census, workspace_root_mds

        root_files = root_files_census(root) or []
        root_mds = workspace_root_mds(root) or []
    except Exception:
        root_files = root_files or []
        root_mds = root_mds or []
    return {
        "ok": True,
        "city_root": root,
        "city_name": os.path.basename(root.rstrip("/")) or "workspace",
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "neighborhoods": folders,
        "folders": folders,
        "root_files": root_files,
        "root_mds": root_mds,
        "structure_only": True,
        "light": True,
        "desk_stores_ready": desk_ok,
        "alerts": [],
        "daemon": "unknown",
    }


def _map_bootstrap():
    """Map first paint + pulse full refresh: engines + hidden + detect (pc-375).

    pc-420: uncached city/people. pc-413: detect runs in parallel with engines
    (was sequential tax on cold path). pc-759: compat scene parallel; structure
    only on degraded city (never ship 500KB+ structure on healthy boots —
    brew 0.1.31 still always attached it and Map sat on Loading forever).
    pc-890: light city omits dig inventory (root_mds); dig uses /api/hood-inventory.
    """
    detect_holder = {"d": None}
    structure_holder = {"c": None}
    compat_holder = {"scene": None}

    def _det():
        try:
            detect_holder["d"] = detect_workspace(CITY_ROOT)
        except Exception:
            detect_holder["d"] = None

    def _struct():
        try:
            structure_holder["c"] = city_structure_from_disk(CITY_ROOT)
        except Exception:
            structure_holder["c"] = None

    def _compat():
        try:
            compat_holder["scene"] = _citylens().desk_scene_compatible(
                DESK,
                scene_timeout=1.2,
                admin_timeout=4.0,
            )
        except Exception:
            pass

    # pc-759: compat used to run sequentially after bootstrap (~1–2s tax).
    # Start it in a daemon thread so it races city assembly for free.
    compat_thread = threading.Thread(target=_compat, daemon=True, name="map-compat")
    compat_thread.start()

    # Detect + city/people in parallel. Do NOT always walk disk for structure
    # (pc-759/pc-775) — that was 0.5MB JSON + CPU on every Map load.
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_det = ex.submit(_det)
        data = _api_map_bootstrap(
            CITYLENS,
            WORKFORCE,
            DESK,
            hidden=read_hidden(),
            detect=None,  # filled below
            cached_json=_fetch_json_raw,
            city_fn=(
                None if _CITYLENS_REMOTE else (lambda: city_payload(light=True))
            ),
            # pc-834: For You on first paint — parallel with city light.
            # pc-1001: map_bootstrap joins attention_fn under MAP_ATTENTION
            # budget (2.0s) and fails open — slow Desk must not hold Map.
            attention_fn=(
                None if _CITYLENS_REMOTE else attention_payload
            ),
        )
        try:
            f_det.result(timeout=2.0)
        except Exception:
            pass

    # compat_thread started before bootstrap; join with short extra budget.
    compat_thread.join(timeout=0.5)

    data = dict(data or {})
    # pc-674 / pc-759: Replace incomplete tpScene with compat scene.
    # compat_holder["scene"] was fetched in parallel — not sequentially after.
    try:
        compat_scene = compat_holder["scene"] or {}
        compat_stores = compat_scene.get("stores") or []
        direct_stores = (data.get("tpScene") or {}).get("stores") or []
        registry_count = int(
            (compat_scene.get("census") or {}).get("registry_store_count")
            or len(compat_stores)
        )
        if (
            compat_scene.get("ok") is not False
            and compat_stores
            and len(direct_stores) != registry_count
        ):
            data["tpScene"] = compat_scene
    except Exception:
        pass
    data["detect"] = detect_holder["d"]
    # Structure only when city lens failed / empty (degraded first paint).
    city = data.get("city")
    city_has_hoods = isinstance(city, dict) and bool(
        city.get("neighborhoods") or city.get("folders")
    )
    if not city_has_hoods:
        try:
            _struct()
        except Exception:
            structure_holder["c"] = None
        if structure_holder["c"]:
            data["city"] = dict(structure_holder["c"])
            data["city"]["degraded"] = True
            data["structure"] = structure_holder["c"]
        else:
            data["structure"] = None
    else:
        data["structure"] = None
    # pc-890 / pc-900: Map first paint is hierarchy + store badges + people —
    # NOT deep dig inventory (root_mds tree walk). citylens light now ships
    # shallow root_entries (one listdir) so papers/instructions seats paint.
    # Dig-in deep index still via /api/hood-inventory. Structure-degraded
    # path still full-enriches.
    # pc-951: light also ships shallow city-root root_files (L0 Instructions).
    city = data.get("city")
    if isinstance(city, dict):
        city = dict(city)
        # Drop transition tape on first paint (soft poll / SSE fills theater)
        if city.get("light") or city.get("neighborhoods"):
            city["recent_transitions"] = []
        # pc-900 belt: if light city still has empty surface inventory
        # (old cache / remote lens), fill shallow root_entries only.
        try:
            hoods = city.get("neighborhoods") or city.get("folders") or []
            if hoods and all(
                not (h.get("root_entries") or h.get("root_mds"))
                for h in hoods
                if isinstance(h, dict)
            ):
                city_hoods = _enrich_neighborhood_inventory_shallow(hoods)
                if city.get("neighborhoods") is not None:
                    city["neighborhoods"] = city_hoods
                if city.get("folders") is not None:
                    city["folders"] = city_hoods
        except Exception:
            pass
        # pc-951 belt: empty root_files on light/degraded city → shallow census
        try:
            rf = city.get("root_files")
            if not (isinstance(rf, list) and rf):
                from protocolcity.citylens import root_files_census

                filled = root_files_census(CITY_ROOT) or []
                if filled:
                    city["root_files"] = filled
        except Exception:
            pass
        data["city"] = city
    struct = data.get("structure")
    if isinstance(struct, dict) and data.get("city") and data["city"].get("degraded"):
        struct = dict(struct)
        hoods = struct.get("neighborhoods") or struct.get("folders") or []
        enriched = _enrich_neighborhood_inventory(hoods)
        if struct.get("neighborhoods") is not None:
            struct["neighborhoods"] = enriched
        if struct.get("folders") is not None:
            struct["folders"] = enriched
        data["structure"] = struct
    # pc-933: city light may ship zero store counters while tpScene already
    # has desk truth in this same payload — merge so folder open badges paint.
    try:
        city_m = data.get("city")
        tp_m = data.get("tpScene")
        if isinstance(city_m, dict) and isinstance(tp_m, dict):
            data["city"] = merge_tp_scene_stores_into_city(city_m, tp_m)
    except Exception:
        pass
    # pc-409: never ship empty people when roster has hires (WF down after reboot)
    people = data.get("people") if isinstance(data, dict) else None
    if not _people_payload_usable(people):
        data["people"] = people_scene_from_disk_roster()
    return data


def _fetch_json_raw(url, timeout=3):
    """Uncached JSON fetch for pulse (must be fresh every poll)."""
    return _api_cache.fetch_json_raw(url, timeout=timeout)


def build_pulse(scope="all", product=""):
    """Compose scoped generation tokens from suite engines (pc-278/pc-295).

    pc-574: city token is local library (disk mtimes) — no live :8796 required.
    """
    return _api_build_pulse(
        CITYLENS,
        DESK,
        WORKFORCE,
        scope=scope,
        product=product,
        city_token_fn=(
            None if _CITYLENS_REMOTE else city_generation_payload
        ),
    )


def _slug_norm(s):
    """Canonical slug normalization (pc-313) — matches protocolcity.slugs.slugify."""
    return "-".join(str(s or "").strip().lower().split())


def _eq_slug(a, b):
    return _slug_norm(a) == _slug_norm(b)


def _hood_product_key(n):
    return _slug_norm(n.get("slug") or n.get("name") or "")


def _att_is_act_now(it):
    """True when an attention item counts toward act-now gold (not stalled/embargo)."""
    return (it.get("kind") or "").lower() not in ("stalled", "embargo")


def build_overview(room, project=""):
    """Compose live brief for place / Desk / Roster (city or one project)."""
    room = (room or "desk").lower()
    if room in ("home", "place"):
        room = "map"  # place pillar; Map at city, Home at project in UI
    if room not in ("map", "desk", "roster"):
        room = "desk"
    project = (project or "").strip()
    now = datetime.datetime.now(datetime.timezone.utc)
    as_of = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fan out in parallel — sequential cold path was ~1–3s+ (attention + WF scene).
    # Always light city: Overview KPIs need folders + store counts, not founder
    # brief / desk scene (those made Map→Overview stampede hang the map).
    # pc-574: city + attention in-process (no :8796); people still WorkForce.
    def _ov_city():
        if _CITYLENS_REMOTE:
            return _cached_json(f"{CITYLENS}/api/city?light=1", timeout=4) or {}
        try:
            return city_payload(light=True)
        except Exception:
            return {}

    def _ov_att():
        if _CITYLENS_REMOTE:
            return _cached_json(f"{CITYLENS}/api/you-attention", timeout=3) or {}
        try:
            return attention_payload()
        except Exception:
            return {}

    def _ov_people():
        return _cached_json(f"{WORKFORCE}/api/scene?light=1", timeout=3) or {}

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_city = ex.submit(_ov_city)
        f_att = ex.submit(_ov_att)
        f_people = ex.submit(_ov_people)
        city = f_city.result() or {}
        att = f_att.result() or {}
        people = f_people.result() or {}
    # pc-409 / pc-407: Report must list hired agents when WorkForce is down
    people_source = "workforce"
    if not _people_payload_usable(people):
        people = people_scene_from_disk_roster()
        people_source = str(people.get("source") or "disk_roster")

    city_root = city.get("city_root") or CITY_ROOT
    city_name = (
        (city.get("city_name") or "").strip()
        or os.path.basename(str(city_root).rstrip("/"))
        or "City"
    )
    hoods = city.get("neighborhoods") or city.get("folders") or []
    items = list(att.get("items") or [])
    transitions = list(city.get("recent_transitions") or [])
    inflight = list(people.get("in_flight") or [])
    edges = list(city.get("edges") or [])

    # Scope filter
    if project:
        hoods = [
            n for n in hoods
            if _eq_slug(n.get("slug"), project) or _eq_slug(n.get("name"), project)
        ]
        items = [
            it for it in items
            if _eq_slug(it.get("product") or it.get("project"), project)
            or (hoods and _eq_slug(it.get("product"), hoods[0].get("name")))
        ]
        transitions = [
            t for t in transitions
            if _eq_slug(t.get("store"), project)
            or (hoods and _eq_slug(t.get("store"), hoods[0].get("slug")))
            or (hoods and _eq_slug(t.get("store"), hoods[0].get("name")))
        ]

    # Store rollups
    filed = claimed = review = done_total = 0
    by_house = []
    # pc-314: managed-but-storeless neighborhoods stay visible as houses with
    # status "pending desk join" (desk offline at founding, or slug drift) —
    # hiding them made a freshly scaffolded city read as completely empty.
    # Unmanaged prospects and non-city zones stay off the Overview; the
    # discovered KPI and empty-state copy account for them.
    skip_zones = {"export", "archive", "foreign", "hidden"}
    roster_workers = load_wf_roster_workers()
    for n in hoods:
        s = n.get("store") or {}
        if not s and not project:
            if not n.get("managed") or n.get("zone") in skip_zones:
                continue
        bl = int(s.get("backlog") or 0)
        ip = int(s.get("in_progress") or 0)
        ir = int(s.get("in_review") or 0)
        dn = int(s.get("done") or 0)
        open_n = bl + ip + ir
        key = _hood_product_key(n)
        gold = sum(
            1 for it in (att.get("items") or [])
            if _att_is_act_now(it)
            and (
                _eq_slug(it.get("product") or it.get("project"), key)
                or _eq_slug(it.get("product"), n.get("name"))
                or _eq_slug(it.get("product"), n.get("slug"))
            )
        )
        if project:
            gold = len(items)
        kinds = Counter()
        for it in (att.get("items") or []):
            if not _att_is_act_now(it):
                continue
            if (
                _eq_slug(it.get("product") or it.get("project"), key)
                or _eq_slug(it.get("product"), n.get("name"))
            ):
                kinds[it.get("kind") or "other"] += 1
        workers = n.get("workers") or []
        w_n = sum(
            1 for w in workers
            if str(w.get("kind") or "").lower() not in ("job", "citizen")
        )
        j_n = sum(1 for w in workers if str(w.get("kind") or "").lower() == "job")
        # When citylens has no workers list, count hired seats from disk roster
        # (same truth as Agents panel after pc-409 fallback).
        if w_n == 0 and j_n == 0:
            slug_key = n.get("slug") or key
            name_key = n.get("name") or key
            for _rn, _row in roster_workers.items():
                if _roster_row_is_staff(_row):
                    continue
                _wd = str(_row.get("workdir") or "").rstrip("/")
                _leaf = os.path.basename(_wd) if _wd else ""
                if not (
                    _eq_slug(_leaf, slug_key)
                    or _eq_slug(_leaf, name_key)
                    or _eq_slug(_row.get("project"), slug_key)
                ):
                    continue
                _k = str(_row.get("kind") or "lane").lower()
                if _k == "job":
                    j_n += 1
                elif _k != "citizen":
                    w_n += 1
        git_when = (n.get("git") or {}).get("when")
        by_house.append({
            "slug": n.get("slug") or key,
            "name": n.get("name") or n.get("slug") or key,
            "zone": n.get("zone"),
            # joined = desk store answers; pending = managed on disk, no store.
            "status": "joined" if s else "pending desk join",
            "open": open_n,
            "backlog": bl,
            "in_progress": ip,
            "in_review": ir,
            "done": dn,
            "for_you": gold,
            "for_you_kinds": dict(kinds),
            "workers": w_n,
            "jobs": j_n,
            "git_when": git_when,
            "estate_files": (n.get("estate") or {}).get("total"),
        })
        filed += bl
        claimed += ip
        review += ir
        done_total += dn

    if not project:
        # recompute for_you per house from full items for accuracy
        for h in by_house:
            h["for_you"] = sum(
                1 for it in (att.get("items") or [])
                if _att_is_act_now(it)
                and (
                    _eq_slug(it.get("product") or it.get("project"), h["slug"])
                    or _eq_slug(it.get("product"), h["name"])
                )
            )
            kinds = Counter()
            for it in (att.get("items") or []):
                if not _att_is_act_now(it):
                    continue
                if (
                    _eq_slug(it.get("product") or it.get("project"), h["slug"])
                    or _eq_slug(it.get("product"), h["name"])
                ):
                    kinds[it.get("kind") or "other"] += 1
            h["for_you_kinds"] = dict(kinds)

    by_house.sort(key=lambda h: (-h["for_you"], -h["open"], h["name"]))

    for_you_kinds = Counter(it.get("kind") or "other" for it in items if _att_is_act_now(it))
    age_buckets = {"<1d": 0, "1–3d": 0, "3–7d": 0, "7d+": 0}
    for it in items:
        m = it.get("age_minutes")
        if m is None:
            continue
        if m < 1440:
            age_buckets["<1d"] += 1
        elif m < 4320:
            age_buckets["1–3d"] += 1
        elif m < 10080:
            age_buckets["3–7d"] += 1
        else:
            age_buckets["7d+"] += 1

    # People rollup
    sectors = people.get("sectors") or []
    staff = []
    hired = []
    for sec in sectors:
        role = (sec.get("role") or "").lower()
        leaf = (sec.get("workdir") or "").split("/")[-1] or sec.get("workplace") or ""
        for w in sec.get("workers") or []:
            if w.get("kind") == "citizen":
                continue
            row = {
                "name": w.get("name"),
                "display": w.get("display") or w.get("name"),
                "kind": w.get("kind"),
                "home": "Workspace jobs" if role == "staff" else leaf,
                "health": w.get("health"),
                "queue": w.get("queue"),
                "next_fire": w.get("next_fire"),
                "last_shift": w.get("last_shift"),
                "live": w.get("name") in inflight,
            }
            if project and role != "staff":
                if not (
                    _eq_slug(leaf, project)
                    or _eq_slug(sec.get("workplace"), project)
                ):
                    continue
            if project and role == "staff":
                continue  # project overview: no city staff unless ProtocolCity
            if role == "staff":
                staff.append(row)
            else:
                hired.append(row)

    if project and _eq_slug(project, "protocolcity"):
        # include staff when viewing ProtocolCity house
        for sec in sectors:
            if (sec.get("role") or "").lower() != "staff":
                continue
            for w in sec.get("workers") or []:
                if w.get("kind") == "citizen":
                    continue
                hired.append({
                    "name": w.get("name"),
                    "display": w.get("display") or w.get("name"),
                    "kind": w.get("kind"),
                    "home": "Workspace jobs",
                    "health": w.get("health"),
                    "queue": w.get("queue"),
                    "next_fire": w.get("next_fire"),
                    "last_shift": w.get("last_shift"),
                    "live": w.get("name") in inflight,
                })

    workers = [p for p in hired if str(p.get("kind") or "").lower() != "job"]
    jobs = [p for p in hired if str(p.get("kind") or "").lower() == "job"]
    if not project:
        workers = [
            p for p in (staff + hired)
            if str(p.get("kind") or "").lower() != "job"
        ]
        jobs = [
            p for p in (staff + hired)
            if str(p.get("kind") or "").lower() == "job"
        ]
        # staff are often jobs
        pass

    live_people = [p for p in (staff + hired if not project else hired) if p.get("live")]
    skip_24 = 0
    ok_24 = 0
    # last_shift outcomes among hired
    outcomes = Counter()
    for p in (hired if project else staff + hired):
        ls = p.get("last_shift") or {}
        oc = (ls.get("outcome") or "").lower()
        if oc:
            outcomes[oc] += 1
        if oc == "skip":
            skip_24 += 1
        if oc in ("ok", "done"):
            ok_24 += 1

    # Law presence at city root
    root_files = {f.get("name") for f in (city.get("root_files") or []) if f.get("name")}
    # also listdir city root for AGENTS etc
    law_city = {
        "AGENTS.md": os.path.isfile(os.path.join(CITY_ROOT, "AGENTS.md")),
        "PERIMETER.md": os.path.isfile(os.path.join(CITY_ROOT, "PERIMETER.md")),
    }
    # pc-314 KPI split: discovered (on disk) ≥ managed (AGENTS.md) ≥ joined
    # (desk store). "Managed" used to count stores, so a managed folder with
    # the desk offline was reported as unmanaged.
    all_hoods = city.get("neighborhoods") or city.get("folders") or []
    discovered_projects = len(all_hoods)
    managed_projects = sum(
        1 for n in all_hoods if n.get("managed") or n.get("store"))
    joined_projects = sum(1 for n in all_hoods if n.get("store"))
    if project and hoods:
        wd = hoods[0].get("path") or os.path.join(CITY_ROOT, hoods[0].get("name") or project)
        law_project = {
            "AGENTS.md": os.path.isfile(os.path.join(wd, "AGENTS.md")),
        }
    else:
        law_project = None

    signed = [t for t in transitions if t.get("to_status") == "done"]
    activity = []
    for t in transitions[:25]:
        activity.append({
            "ts": t.get("ts"),
            "task_id": t.get("task_id"),
            "from": t.get("from_status"),
            "to": t.get("to_status"),
            "author": t.get("author"),
            "store": t.get("store"),
            "kind": "transition",
        })
    for name in inflight:
        activity.insert(0, {
            "ts": as_of,
            "task_id": None,
            "from": None,
            "to": "in_flight",
            "author": name,
            "store": None,
            "kind": "shift",
        })

    # Map-specific: edges, hidden count
    try:
        hidden = read_hidden()
    except Exception:
        hidden = []

    kpis = {
        "open": filed + claimed + review,
        "backlog": filed,
        "in_progress": claimed,
        "in_review": review,
        "for_you": sum(1 for it in items if _att_is_act_now(it)),
        "signed_recent": len(signed),
        "hands": claimed + review,
        "in_flight": len(inflight),
        "workers": len(workers),
        "jobs": len(jobs),
        "staff": len(staff) if not project else 0,
        "projects": len(by_house) if not project else (1 if by_house else 0),
        "discovered_projects": discovered_projects,
        "managed_projects": managed_projects,
        "joined_projects": joined_projects,
        "edges": len(edges),
        "hidden_folders": len(hidden),
    }

    return {
        "ok": True,
        "as_of": as_of,
        "room": room,
        "project": project or None,
        "city_name": city_name,
        "city_root": city_root,
        "suite_version": (
            str(city.get("suite_version") or "").strip()
            or _suite_package_version()
        ),
        "scope_label": (
            (hoods[0].get("name") if hoods else project)
            if project else city_name
        ),
        "kpis": kpis,
        "for_you_kinds": dict(for_you_kinds),
        "for_you_age": age_buckets,
        "by_house": by_house,
        "people": {
            "staff": staff if not project else [],
            "workers": workers,
            "jobs": jobs,
            "live": live_people,
            "last_shift_outcomes": dict(outcomes),
            "source": people_source,
        },
        "activity": activity[:30],
        "for_you_top": [
            {
                "id": it.get("id"),
                "title": it.get("title"),
                "kind": it.get("kind"),
                "product": it.get("product") or it.get("project"),
                "age_minutes": it.get("age_minutes"),
                "note": (it.get("note") or "")[:160],
            }
            for it in sorted(
                items, key=lambda x: -(x.get("age_minutes") or 0)
            )[:12]
        ],
        "law": {
            "city": law_city,
            "project": law_project,
        },
        "edges": [
            {
                "from": e.get("from"),
                "to": e.get("to"),
                "kind": e.get("kind"),
                "rule": e.get("rule"),
            }
            for e in edges
        ],
        "daemon": people.get("daemon") or city.get("daemon"),
        "generated_at": city.get("generated_at"),
        # pc-355: always-on disk detect (no ship toggle; engines optional)
        "detect": detect_workspace(CITY_ROOT),
        "survey": (city.get("survey") or {}),
        "delivery_note": (
            "This Overview is the Report — the text twin of the Map. "
            "Same workspace truth: projects, agents, work orders, rules."
        ),
        "people_source": people_source,
    }


def ground_entry(name, base, scoped):
    p = os.path.join(base, name)
    is_dir = os.path.isdir(p)
    dotted = name.startswith(".")
    lower = name.lower()
    e = {
        "name": name,
        "hidden": dotted,
        "dir": is_dir,
        "md": (not is_dir) and lower.endswith(".md"),
        "rule": (not is_dir) and name in RULE_NAMES,
        "managed": False,
        "n": None,
    }
    if is_dir:
        e["managed"] = dir_managed(p)
        if scoped:
            try:
                e["n"] = len(os.listdir(p))
            except Exception:
                e["n"] = None
    return e


# HTTP proxies for engines that stay separate processes (WorkLane / WorkForce).
# Census routes (/api/city, /api/attention, /api/office) are in-process (pc-574)
# unless SUITE_CITYLENS_REMOTE=1 for host debug.
PROXY = {
    "/api/people": f"{WORKFORCE}/api/scene",
    "/api/tp-scene": f"{DESK}/api/scene",
}
if _CITYLENS_REMOTE:
    PROXY["/api/city"] = f"{CITYLENS}/api/city"
    PROXY["/api/attention"] = f"{CITYLENS}/api/you-attention"
    PROXY["/api/office"] = f"{CITYLENS}/api/office"


def _proxy_citylens_json(method, path_qs, body=None, timeout=60):
    """Host-debug only: proxy JSON to standalone citylens (SUITE_CITYLENS_REMOTE).

    Production suite never calls this for census (pc-574). Error copy must not
    tell citizens to start :8796.
    """
    url = f"{CITYLENS}{path_qs}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {"ok": True}
            except json.JSONDecodeError:
                payload = {"ok": True, "raw": raw}
            return r.status, payload if isinstance(payload, dict) else {"ok": True, "data": payload}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            payload = json.loads(raw) if raw else {"ok": False, "error": e.reason or str(e.code)}
        except Exception:
            payload = {"ok": False, "error": e.reason or str(e.code)}
        if not isinstance(payload, dict):
            payload = {"ok": False, "error": str(payload)}
        return e.code, payload
    except Exception as e:
        return 502, {
            "ok": False,
            "error": "remote census host unreachable (%s)" % e,
        }

# pc-1123: FOLDER_STORE / PREFIX_PRODUCT / normalize_store_slug / product_of_task_id
# live in suite/api/vocabulary.py (imported above). Re-exports keep tests and
# Map lockstep comments pointing at serve names:
#   _FOLDER_STORE, _normalize_store_slug, _PREFIX_PRODUCT, _product_of_task_id
# Legacy name used by live-strip call sites / desk-bootstrap prefix infer:
_LIVE_STRIP_PREFIX_PRODUCT = _PREFIX_PRODUCT


def _light_task_row(t, product_fallback=None):
    """Suite light task card — glance only (pc-921 / pc-881 / pc-1123).

    Single serializer body lives in ``suite.api.vocabulary.light_task_row``.
    This thin def stays as the serve call-site surface (live-strip, /api/tasks,
    ready, unrouted) and preserves pc-1054/pc-918 source-shape anchors.

    pc-1054: pass through real owner when upstream requested with_preview —
    Map LIVE Owner: join (pc-526) needs it. Vocabulary builds:
      "owner": (t.get("owner") or "") or ""
      "glance": _extract_task_glance(t.get("description") or "")
    """
    return _vocab_light_task_row(t, product_fallback=product_fallback)


def _proxy_desk_json(method, path_qs, body=None, timeout=12):
    """Proxy JSON to WorkLane/TP desk engine. Returns (http_code, dict_or_error)."""
    url = f"{DESK}{path_qs}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {"ok": True}
            except json.JSONDecodeError:
                payload = {"ok": True, "raw": raw}
            return r.status, payload if isinstance(payload, dict) else {"ok": True, "data": payload}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            payload = json.loads(raw) if raw else {"ok": False, "error": e.reason or str(e.code)}
        except Exception:
            payload = {"ok": False, "error": e.reason or str(e.code)}
        if not isinstance(payload, dict):
            payload = {"ok": False, "error": str(payload)}
        return e.code, payload
    except Exception as e:
        return 502, {"ok": False, "error": "WorkLane unreachable — is :8799 up? (%s)" % e}


# pc-688: chip tallies must outrun MAP_WO_LIST_CAP (100) list fetches.
_WO_GATE_FETCH_LIMIT = 5000
_WO_GATE_COUNTS_TTL = 20.0
# pc-1044: keyed by product slug ("" = workspace / all stores)
_wo_gate_counts_cache = {}  # product_key -> {at, payload}

# pc-1125: workspace calendar ICS — short TTL so Apple Calendar polls are cheap
_CALENDAR_TTL = 30.0
_calendar_cache = {"at": 0.0, "events": None, "errors": None}
_calendar_lock = threading.Lock()

# pc-934: Map left-rail live-strip — one suite hop; serial WorkLane status pulls.
_LIVE_STRIP_TTL = 12.0
_live_strip_cache = {}  # family|limit|product -> {at, payload}
_live_strip_lock = threading.Lock()

# pc-1244: auto-bust WO caches when ticket generation token changes externally
# (CLI close / chat close bypass suite PATCH — caches stay warm for up to TTL).
_last_tickets_token = None  # str or None
_pulse_token_lock = threading.Lock()


def build_live_strip_payload(*, family="open", limit=100, force=False, product=""):
    """Composite desk list for Map tape (pc-934).

    Client makes one suite hop. Suite pulls each status **serially** from
    WorkLane (no parallel 4× stampede that 502s under load). Short TTL +
    single-flight so concurrent Map paints share one pull.

    pc-1044: optional ``product`` scopes desk pulls to one store (project dig-in).
    Cache key includes product so workspace and dig-in piles never share rows.
    """
    fam = str(family or "open").strip().lower()
    if fam in ("all", "recency", "tape"):
        fam = "all"
        statuses = ("backlog", "in_progress", "in_review", "done")
    else:
        fam = "open"
        statuses = ("backlog", "in_progress", "in_review")
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        lim = 100
    lim = max(1, min(lim, 100))
    prod = _normalize_store_slug(product or "")
    cache_key = "%s|%s|%s" % (fam, lim, prod or "_all")
    now = time.monotonic()
    with _live_strip_lock:
        hit = _live_strip_cache.get(cache_key)
        if (
            not force
            and isinstance(hit, dict)
            and isinstance(hit.get("payload"), dict)
            and hit["payload"].get("ok")
            and (now - float(hit.get("at") or 0)) < _LIVE_STRIP_TTL
        ):
            return hit["payload"]
        # Single-flight: another thread already building this key?
        if (
            not force
            and isinstance(hit, dict)
            and hit.get("loading")
            and isinstance(hit.get("waiters"), list)
        ):
            waiters = hit["waiters"]
            ev = threading.Event()
            waiters.append(ev)
            # fall through to wait outside lock
        else:
            _live_strip_cache[cache_key] = {
                "at": now,
                "payload": (hit or {}).get("payload") if isinstance(hit, dict) else None,
                "loading": True,
                "waiters": [],
            }
            waiters = None
            ev = None

    if waiters is not None and ev is not None:
        ev.wait(timeout=20)
        with _live_strip_lock:
            hit2 = _live_strip_cache.get(cache_key) or {}
            payload = hit2.get("payload")
            if isinstance(payload, dict) and payload.get("ok"):
                return payload
            # fall through to build if waiter woke without payload

    by_status = {st: [] for st in statuses}
    errors = []
    seen = set()
    merged = []

    for st in statuses:
        q_pairs = [("status", st), ("limit", str(lim))]
        if prod:
            q_pairs.append(("product", prod))
            q_pairs.append(("project", prod))
        # pc-1054: Owner: join for Map LIVE needs with_preview on inflight
        # only (comment-scan is expensive; backlog/done stay light — pc-881).
        # Serial status pulls preserved (pc-934 anti-stampede).
        if st in ("in_progress", "in_review"):
            q_pairs.append(("with_preview", "1"))
        q = urlencode(q_pairs)
        code, data = _proxy_desk_json(
            "GET", "/api/admin/tasks?" + q, timeout=8
        )
        if code != 200 or not isinstance(data, dict):
            err = (data or {}).get("error") if isinstance(data, dict) else None
            errors.append("%s:%s%s" % (st, code, (":" + str(err)) if err else ""))
            continue
        tasks = data.get("tasks") or []
        if not isinstance(tasks, list):
            continue
        light_rows = []
        for t in tasks:
            row = _light_task_row(t, product_fallback=prod or None)
            if not row or not row.get("id"):
                continue
            light_rows.append(row)
            tid = str(row["id"])
            if tid in seen:
                continue
            seen.add(tid)
            merged.append(row)
        by_status[st] = light_rows

    def _upd_key(t):
        return str(t.get("updated_at") or t.get("created_at") or ""), str(
            t.get("id") or ""
        )

    merged.sort(key=_upd_key, reverse=True)
    ok = len(errors) < len(statuses)  # at least one status succeeded
    # Workspace scope: cap is across ALL projects (silent without product=).
    # Product scope: cap is per store. Client badges when truncated (pc-1044).
    payload = {
        "ok": ok,
        "family": fam,
        "limit": lim,
        "product": prod or None,
        "tasks": merged[:lim] if fam == "all" else merged,
        "by_status": by_status,
        "count": len(merged),
        "errors": errors or None,
        "source": "live_strip_serial",
        "list_cap": lim,
        "cap_scope": "product" if prod else "workspace",
    }
    if not ok:
        payload["error"] = (
            "WorkLane desk unreachable or partial failure — "
            + (", ".join(errors[:4]) if errors else "no status rows")
        )

    with _live_strip_lock:
        prev = _live_strip_cache.get(cache_key) or {}
        waiters_done = list(prev.get("waiters") or [])
        _live_strip_cache[cache_key] = {
            "at": time.monotonic(),
            "payload": payload,
            "loading": False,
            "waiters": [],
        }
    for w in waiters_done:
        try:
            w.set()
        except Exception:
            pass
    return payload


def _fetch_open_tasks_uncapped(product=""):
    """Open-status tasks from Desk (limit high enough for chip truth).

    pc-881: parallel status pulls, no with_preview (gate tallies only need
    id/status/gate fields — owner card preview was 3–5× cost under thrash).
    pc-1044: optional ``product`` scopes each pull to one store.
    """
    out = []
    errors = []
    prod = _normalize_store_slug(product or "")

    def _one(status):
        q_pairs = [
            ("status", status),
            ("limit", str(_WO_GATE_FETCH_LIMIT)),
        ]
        if prod:
            q_pairs.append(("product", prod))
            q_pairs.append(("project", prod))
        q = urlencode(q_pairs)
        code, data = _proxy_desk_json(
            "GET", "/api/admin/tasks?" + q, timeout=8
        )
        return status, code, data

    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [
            ex.submit(_one, st)
            for st in ("backlog", "in_progress", "in_review")
        ]
        for fut in futs:
            try:
                status, code, data = fut.result()
            except Exception as e:
                errors.append("err:%s" % e)
                continue
            if code != 200 or not isinstance(data, dict):
                errors.append("%s:%s" % (status, code))
                continue
            tasks = data.get("tasks") or []
            if isinstance(tasks, list):
                out.extend(t for t in tasks if isinstance(t, dict))
            scope = data.get("scope_counts") or {}
            try:
                want = int(scope.get(status) or 0)
            except (TypeError, ValueError):
                want = 0
            if want > _WO_GATE_FETCH_LIMIT:
                errors.append(
                    "%s:truncated (scope=%s > fetch=%s)"
                    % (status, want, _WO_GATE_FETCH_LIMIT)
                )
    return out, errors


def _list_desk_product_slugs():
    """Registered WorkLane product store slugs (pc-1125 multi-store calendar)."""
    code, data = _proxy_desk_json("GET", "/api/admin/products", timeout=8)
    if code != 200 or not isinstance(data, dict):
        return [], ["products:%s" % code]
    slugs = []
    for p in data.get("products") or []:
        if not isinstance(p, dict):
            continue
        slug = _normalize_store_slug(p.get("slug") or p.get("product") or "")
        if slug:
            slugs.append(slug)
    return slugs, []


def _fetch_open_tasks_all_stores():
    """Open tasks across every registered product store (pc-1125).

    Unscoped /api/admin/tasks returns only the default desk surface — calendar
    must fan out per product so timer gates and deadline: labels from tradeOS,
    ProtocolCity, etc. all appear.
    """
    slugs, errs = _list_desk_product_slugs()
    if not slugs:
        # Fallback: unscoped open pull (default store only)
        tasks, e2 = _fetch_open_tasks_uncapped(product="")
        return tasks, errs + e2
    out = []
    errors = list(errs)
    # Bound fan-out: one worker per product status triple; cap concurrency.
    def _one_product(prod):
        return prod, _fetch_open_tasks_uncapped(product=prod)

    with ThreadPoolExecutor(max_workers=min(6, max(1, len(slugs)))) as ex:
        futs = [ex.submit(_one_product, s) for s in slugs]
        for fut in futs:
            try:
                prod, (tasks, e) = fut.result()
            except Exception as exc:
                errors.append("product-err:%s" % exc)
                continue
            if e:
                errors.extend("%s:%s" % (prod, x) for x in e)
            for t in tasks or []:
                if isinstance(t, dict) and not t.get("product") and not t.get("project"):
                    t = dict(t)
                    t["product"] = prod
                if isinstance(t, dict):
                    # Attach glance for event descriptions without shipping full body later
                    if not t.get("glance") and t.get("description"):
                        try:
                            t = dict(t)
                            t["glance"] = _extract_task_glance(t.get("description") or "")
                        except Exception:
                            pass
                    out.append(t)
    return out, errors


def _calendar_public_base(handler=None):
    """Absolute suite origin for dig-in URLs in ICS bodies (pc-1125)."""
    env = (os.environ.get("SUITE_PUBLIC_BASE") or "").strip().rstrip("/")
    if env:
        return env
    host = ""
    if handler is not None:
        try:
            host = (handler.headers.get("Host") or "").strip()
        except Exception:
            host = ""
    if host and "127.0.0.1" not in host and host.lower() not in ("localhost", "localhost:8801"):
        # Prefer https only when the request clearly is (rare on LAN suite)
        scheme = "http"
        try:
            if (handler.headers.get("X-Forwarded-Proto") or "").strip().lower() == "https":
                scheme = "https"
        except Exception:
            pass
        return "%s://%s" % (scheme, host)
    return "http://127.0.0.1:8801"


def build_workspace_calendar_events(*, force=False, base_url="", include_jobs=False):
    """Collect calendar events from all stores (pc-1125). Jobs stay opt-in."""
    del include_jobs  # reserved — scheduled jobs OFF by default, not implemented
    now = time.monotonic()
    with _calendar_lock:
        hit_at = float(_calendar_cache.get("at") or 0)
        hit_ev = _calendar_cache.get("events")
        if (
            not force
            and isinstance(hit_ev, list)
            and (now - hit_at) < _CALENDAR_TTL
        ):
            # Re-stamp dig-in base if caller base differs from cached empty
            return hit_ev, list(_calendar_cache.get("errors") or [])

    tasks, errors = _fetch_open_tasks_all_stores()
    events = _cal_collect_events(tasks, base_url=base_url or _calendar_public_base())
    with _calendar_lock:
        _calendar_cache["at"] = time.monotonic()
        _calendar_cache["events"] = events
        _calendar_cache["errors"] = list(errors)
    return events, errors


def build_wo_gate_counts_payload(*, force=False, product=""):
    """Authoritative live/ready/deferred chip tallies for Map (pc-688).

    pc-1044: optional ``product`` returns that store's tallies so dig-in rail
    chips match the project header (not city-wide totals under a project name).
    """
    prod = _normalize_store_slug(product or "")
    cache_key = prod or "_all"
    now = time.monotonic()
    hit_wrap = _wo_gate_counts_cache.get(cache_key) or {}
    hit = hit_wrap.get("payload")
    at = float(hit_wrap.get("at") or 0)
    if (
        not force
        and isinstance(hit, dict)
        and hit.get("ok")
        and (now - at) < _WO_GATE_COUNTS_TTL
    ):
        return hit
    tasks, errors = _fetch_open_tasks_uncapped(product=prod)
    tallies = _tally_wo_gate_counts(tasks)
    # pc-875: per-product heat for Map 🎫 — uncapped, not MAP_WO_LIST_CAP sample
    try:
        by_product = _tally_wo_gate_by_product(tasks)
    except Exception:
        by_product = {}
    # Desk scene ready = WorkQueue.ready() rollup (same family as folder.store.ready)
    ready_store = None
    scode, scene = _proxy_desk_json("GET", "/api/scene", timeout=8)
    if scode == 200 and isinstance(scene, dict):
        total_ready = 0
        saw = False
        for s in scene.get("stores") or []:
            if not isinstance(s, dict):
                continue
            if "ready" not in s:
                continue
            slug = _normalize_store_slug(
                s.get("slug") or s.get("product") or s.get("name") or ""
            )
            if prod and slug and slug != prod:
                continue
            saw = True
            try:
                total_ready += int(s.get("ready") or 0)
            except (TypeError, ValueError):
                continue
        if saw:
            ready_store = total_ready
    ready_chip = (
        ready_store if ready_store is not None else int(tallies.get("ready") or 0)
    )
    # pc-1093: empty board with a healthy desk is ok; total upstream failure
    # must not ship ok:True with all-zero chips as authoritative truth.
    scan_ok = bool(tasks) or not errors
    payload = {
        "ok": scan_ok,
        "live": int(tallies.get("live") or 0),
        "deferred": int(tallies.get("deferred") or 0),
        "ready": int(ready_chip),
        "ready_scan": int(tallies.get("ready") or 0),
        "ready_store": ready_store,
        "open": int(tallies.get("open") or 0),
        "product": prod or None,
        "by_product": by_product if isinstance(by_product, dict) else {},
        "list_cap": 100,
        "source": "desk_uncapped_scan+scene_ready",
        "errors": errors or None,
    }
    if not scan_ok:
        payload["error"] = (
            "WorkLane desk unreachable — "
            + (", ".join(errors[:4]) if errors else "no status rows")
        )
        payload["degraded"] = True
    _wo_gate_counts_cache[cache_key] = {"at": now, "payload": payload}
    return payload


# Peer / alias URLs retired from ship face (founder 2026-07-24).
# 302 → /workspace-map (preserve ?query for project= focus).
_RETIRED_PAGE_ROUTES = frozenset({
    "/skin",
    "/map",
    "/explorer",
    "/desk",
    "/roster",
    "/agents",
    "/ported",
    "/home",      # pc-1278: Files list absorbed — Map is the door
})


def _suite_package_healthy() -> bool:
    """False when brew upgrade deleted Cellar files under this process (pc-438)."""
    try:
        marker = os.path.join(HERE, "workspace_map.html")
        return os.path.isfile(marker) and os.path.isdir(HERE)
    except OSError:
        return False


_STALE_UPGRADE_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>BluePrint — restart required</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:36rem;margin:3rem auto;padding:0 1rem;line-height:1.5}
 code{background:#f4f4f5;padding:0.15em 0.4em;border-radius:4px}
</style></head><body>
<h1>BluePrint was upgraded</h1>
<p>This server is still the <strong>old process</strong> after a package upgrade
(Homebrew removed files it was serving). Routes would otherwise return a blank 404.</p>
<p>Stop and start the suite again:</p>
<pre><code>blueprint stop
blueprint serve --root &lt;your-workspace&gt;</code></pre>
<p>Compat alias: <code>blueprint stop</code> · <code>blueprint serve …</code></p>
</body></html>
"""


# pc-973: memoize gzip of large static assets (mtime+size key).
# pc-1004: never compress on the request thread — first hit serves raw while a
# daemon fills the memo (or startup pre-warm already did). Avoids head-of-line
# stalls on cold restart when map app is ~1.2MB.
_GZIP_STATIC_CACHE: dict = {}
_GZIP_CACHE_LOCK = threading.Lock()
_GZIP_PENDING: set = set()
_GZIP_MIN_BYTES = 8192
_GZIP_CACHE_MAX = 64
_GZIP_COMPRESSLEVEL = 5

# pc-1020: auto-derive ?v= on HTML asset refs (no hand-bumped stamp).
# Keyed by mtime+size so a plain touch after suite sync busts browser cache.
_ASSET_VER_LOCK = threading.Lock()
_ASSET_VER_CACHE: dict = {}  # fs_path -> (mtime, size, ver)
# href|src="/path/file.js?v=…"  (root-relative suite assets only)
_HTML_ASSET_REF_RE = re.compile(
    r'(?P<prefix>\b(?:href|src)=["\'])'
    r'(?P<path>/[^"\'?\s#]+?\.(?:js|css))'
    r'(?:\?[^"\']*)?'
    r'(?P<suffix>["\'])',
    re.IGNORECASE,
)


def _asset_version(fs_path: str) -> str:
    """Stable short stamp for a suite file (mtime-size hex; memoized)."""
    try:
        st = os.stat(fs_path)
    except OSError:
        return "0"
    mtime = int(st.st_mtime)
    size = int(st.st_size)
    with _ASSET_VER_LOCK:
        hit = _ASSET_VER_CACHE.get(fs_path)
        if hit and hit[0] == mtime and hit[1] == size:
            return hit[2]
    ver = "%x-%x" % (mtime, size)
    with _ASSET_VER_LOCK:
        _ASSET_VER_CACHE[fs_path] = (mtime, size, ver)
        # Bound memo growth (suite static set is small; defensive).
        if len(_ASSET_VER_CACHE) > 512:
            _ASSET_VER_CACHE.clear()
            _ASSET_VER_CACHE[fs_path] = (mtime, size, ver)
    return ver


def _rewrite_html_asset_versions(html, suite_root=None):
    """Rewrite local /…js|css ?v= stamps from file mtime+size (pc-1020).

    Hand-edited stamps in HTML are placeholders only — serve derives the real
    value so Cellar + BLUEPRINT_SUITE_DIR both bust cache without a bump ritual.
    """
    root = suite_root if suite_root is not None else HERE

    def _repl(m):
        rel = m.group("path").lstrip("/")
        if ".." in rel.split("/"):
            return m.group(0)
        fs_path = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(fs_path):
            return m.group(0)
        ver = _asset_version(fs_path)
        return "%s%s?v=%s%s" % (
            m.group("prefix"),
            m.group("path"),
            ver,
            m.group("suffix"),
        )

    return _HTML_ASSET_REF_RE.sub(_repl, html)


def _gzip_cache_get(fs_path: str, mtime: int, size: int):
    """Return cached gzip body or None when missing/stale."""
    with _GZIP_CACHE_LOCK:
        cached = _GZIP_STATIC_CACHE.get(fs_path)
        if cached and cached[0] == mtime and cached[1] == size:
            return cached[2]
    return None


def _gzip_schedule_fill(fs_path: str, mtime: int, size: int) -> None:
    """Compress off-thread; store under mtime+size key. Idempotent per path."""
    import gzip

    with _GZIP_CACHE_LOCK:
        if fs_path in _GZIP_PENDING:
            return
        cached = _GZIP_STATIC_CACHE.get(fs_path)
        if cached and cached[0] == mtime and cached[1] == size:
            return
        _GZIP_PENDING.add(fs_path)

    def _work() -> None:
        try:
            try:
                st = os.stat(fs_path)
            except OSError:
                return
            if int(st.st_mtime) != mtime or st.st_size != size:
                return
            with open(fs_path, "rb") as f:
                raw = f.read()
            body = gzip.compress(raw, compresslevel=_GZIP_COMPRESSLEVEL)
            with _GZIP_CACHE_LOCK:
                if len(_GZIP_STATIC_CACHE) > _GZIP_CACHE_MAX:
                    _GZIP_STATIC_CACHE.clear()
                _GZIP_STATIC_CACHE[fs_path] = (mtime, size, body)
        except OSError:
            pass
        finally:
            with _GZIP_CACHE_LOCK:
                _GZIP_PENDING.discard(fs_path)

    threading.Thread(
        target=_work, daemon=True, name="gzip-fill-%s" % os.path.basename(fs_path)
    ).start()


def _gzip_prewarm_suite_statics() -> None:
    """pc-1004: background-fill large suite statics at process start (largest first)."""
    candidates = []
    try:
        for dirpath, _dirnames, filenames in os.walk(HERE):
            for name in filenames:
                # pc-1020: HTML is rewritten on the request path; skip gzip prewarm.
                if not name.endswith((".js", ".css", ".svg", ".json")):
                    continue
                fs_path = os.path.join(dirpath, name)
                try:
                    st = os.stat(fs_path)
                except OSError:
                    continue
                if st.st_size < _GZIP_MIN_BYTES:
                    continue
                candidates.append((fs_path, int(st.st_mtime), st.st_size))
    except OSError:
        return
    candidates.sort(key=lambda row: -row[2])
    for fs_path, mtime, size in candidates[:32]:
        _gzip_schedule_fill(fs_path, mtime, size)


class Handler(http.server.SimpleHTTPRequestHandler):
    # pc-973: keep-alive + fewer TCP handshakes on Map cold reload (was HTTP/1.0).
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def _send_stale_upgrade_response(self):
        body = _STALE_UPGRADE_HTML.encode("utf-8")
        self.send_response(503, "Service Unavailable")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_redirect(self, location: str, status: int = 302) -> None:
        """Empty-body redirect that completes under HTTP/1.1 keep-alive (pc-1175).

        protocol_version is HTTP/1.1 (pc-973). Without Content-Length, clients
        wait forever for a body after Location headers (curl hang on GET /).
        Always stamp Content-Length: 0 so the response is complete.
        """
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _static_cache_control(self, path, query=""):
        """pc-973: drop blanket no-store on versioned JS/CSS; HTML revalidates.

        - .js/.css with ?v=… → max-age=1d + must-revalidate (bust via query)
        - .js/.css without v → max-age=0 must-revalidate (ETag/Last-Modified)
        - .html + room routes → no-cache must-revalidate (never sticky Planned shell)
        Returns header value or None when caller should not stamp Cache-Control.
        """
        if path.endswith((".js", ".css")):
            if "v=" in (query or ""):
                return "public, max-age=86400, must-revalidate"
            return "public, max-age=0, must-revalidate"
        if path.endswith(".html") or path in (
            "/",
            "/home",
            "/calendar",
            "/person",
            "/ticket",
            "/overview",
            "/read",
            "/workspace-map",
            "/settings",
        ):
            return "no-cache, must-revalidate"
        return None

    def end_headers(self):
        # pc-973: ETag/max-age for static; no blanket no-store (was re-download
        # of 1.2MB engine every Map reload). API / redirects set their own.
        raw = self.path or ""
        path = raw.split("?")[0]
        query = raw.split("?", 1)[1] if "?" in raw else ""
        # Skip if a prior send_header already set Cache-Control this response
        # (redirects / JSON use no-store explicitly before end_headers).
        already = False
        try:
            # BaseHTTPRequestHandler has no public peek; re-stamp is fine when
            # we own static routes. Prefer first-writer for redirects that
            # already sent Cache-Control.
            hdrs = getattr(self, "_headers_buffer", None) or []
            already = any(
                isinstance(h, (bytes, bytearray))
                and h.lower().startswith(b"cache-control:")
                for h in hdrs
            )
        except Exception:
            already = False
        if not already:
            cc = self._static_cache_control(path, query)
            if cc:
                self.send_header("Cache-Control", cc)
        super().end_headers()

    def _try_send_html_asset_versions(self):
        """pc-1020: serve .html with per-asset ?v= derived from file mtime+size.

        Bypasses raw gzip memo of HTML so placeholders are never shipped to the
        browser. HTML stays revalidate (no-cache); versioned JS/CSS keep max-age.
        """
        import gzip

        raw_path = (self.path or "").split("?")[0]
        if not raw_path.endswith(".html"):
            return False
        rel = raw_path.lstrip("/")
        if ".." in rel.split("/"):
            return False
        fs_path = os.path.join(HERE, rel.replace("/", os.sep))
        if not os.path.isfile(fs_path):
            return False
        try:
            with open(fs_path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            st = os.stat(fs_path)
            mtime = int(st.st_mtime)
        except OSError:
            return False
        body = _rewrite_html_asset_versions(raw_html, HERE).encode("utf-8")
        use_gzip = False
        ae = (self.headers.get("Accept-Encoding") or "").lower()
        if "gzip" in ae and len(body) >= _GZIP_MIN_BYTES:
            body = gzip.compress(body, compresslevel=_GZIP_COMPRESSLEVEL)
            use_gzip = True
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Last-Modified", self.date_time_string(mtime))
        # Cache-Control via end_headers → no-cache must-revalidate for HTML
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return True

    def _try_send_gzip_static(self):
        """pc-894: gzip large JS/CSS (map app is ~1.1MB raw → ~280KB gzip).

        Browser still parses full JS, but transfer + first byte drop hard.
        Only for Accept-Encoding: gzip and suite static assets under HERE.
        pc-973: memoize gzip by mtime; ETag + 304 for warm reload.
        pc-1004: cache miss never blocks — schedule background fill and return
        False so SimpleHTTP serves uncompressed until the memo is ready.
        pc-1020: .html is handled by _try_send_html_asset_versions (not here).
        """
        import mimetypes

        raw_path = (self.path or "").split("?")[0]
        query = (self.path or "").split("?", 1)[1] if "?" in (self.path or "") else ""
        # HTML always goes through asset-version rewrite (pc-1020).
        if raw_path.endswith(".html"):
            return False
        if not raw_path.endswith((".js", ".css", ".svg", ".json")):
            return False
        ae = (self.headers.get("Accept-Encoding") or "").lower()
        if "gzip" not in ae:
            return False
        # Map path to file under suite root (SimpleHTTP directory=HERE)
        rel = raw_path.lstrip("/")
        if ".." in rel.split("/"):
            return False
        fs_path = os.path.join(HERE, rel.replace("/", os.sep))
        if not os.path.isfile(fs_path):
            return False
        try:
            st = os.stat(fs_path)
            size = st.st_size
            mtime = int(st.st_mtime)
        except OSError:
            return False
        # Only compress payloads that pay for the CPU (map app, CSS, big pages)
        if size < _GZIP_MIN_BYTES:
            return False
        body = _gzip_cache_get(fs_path, mtime, size)
        if body is None:
            # Cold path: do not gzip.compress on this thread (pc-1004).
            _gzip_schedule_fill(fs_path, mtime, size)
            return False
        etag = '"%x-%x-gz"' % (mtime, size)
        inm = (self.headers.get("If-None-Match") or "").strip()
        if inm and etag in inm:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Vary", "Accept-Encoding")
            cc = self._static_cache_control(raw_path, query)
            if cc:
                self.send_header("Cache-Control", cc)
            self.end_headers()
            return True
        ctype = mimetypes.guess_type(fs_path)[0] or "application/octet-stream"
        if fs_path.endswith(".js"):
            ctype = "application/javascript; charset=utf-8"
        elif fs_path.endswith(".css"):
            ctype = "text/css; charset=utf-8"
        elif fs_path.endswith(".html"):
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", self.date_time_string(mtime))
        self.send_header("Vary", "Accept-Encoding")
        # Cache-Control set in end_headers via path
        self.end_headers()
        self.wfile.write(body)
        return True

    def _redirect_retired_page(self):
        """If path is a retired peer URL, 302 → /workspace-map. Returns True if sent."""
        raw = self.path or "/"
        route = raw.split("?")[0]
        if route != "/" and route.endswith("/"):
            route = route.rstrip("/")
        if route not in _RETIRED_PAGE_ROUTES:
            return False
        qs = urlsplit(raw).query
        loc = "/workspace-map"
        if qs:
            loc = loc + "?" + qs
        self._send_redirect(loc)
        return True

    def _redirect_settings_page(self):
        """pc-1267: /settings is the spine Settings view.

        Default: do not 302 — _rewrite_page_route serves settings_v1.html.
        Fallback (one release): ?sheet=1 still 302s into the Map FAB sheet
        (pc-661 era). Payload clone stays at /settings_v1.html.
        """
        raw = self.path or "/"
        route = raw.split("?")[0]
        if route != "/" and route.endswith("/"):
            route = route.rstrip("/")
        if route != "/settings":
            return False
        qs = parse_qs(urlsplit(raw).query, keep_blank_values=True)
        sheet = (qs.get("sheet") or [""])[0]
        if sheet != "1":
            return False
        scope = (qs.get("scope") or ["workspace"])[0] or "workspace"
        params = [("open", "settings"), ("scope", scope)]
        project = (qs.get("project") or [""])[0]
        if project:
            params.append(("project", project))
        loc = "/workspace-map?" + urlencode(params)
        self._send_redirect(loc)
        return True

    def _rewrite_page_route(self):
        """Map suite room URLs onto real files under suite/. Mutates self.path."""
        route = self.path.split("?")[0]
        if route != "/" and route.endswith("/"):
            route = route.rstrip("/")
        # Ship rooms — Overview lands at / and /overview (pc-1299).
        # /settings?sheet=1 302 via _redirect_settings_page (pc-1267 fallback).
        if route in ("/", "/overview", "/wall"):
            self.path = "/wall.html"
        elif route == "/workspace-map":
            self.path = "/workspace_map.html"
        elif route == "/settings":
            self.path = "/settings_v1.html"
        elif route == "/person":
            self.path = "/person_v1.html"
        elif route == "/ticket":
            self.path = "/ticket_v1.html"
        elif route == "/read":
            self.path = "/read_v1.html"
        # Unknown page paths: do not fall through to archived horizon.html
        # (pc-581 scrub). Leave path as-is → 404 from SimpleHTTPRequestHandler.

    def do_HEAD(self):
        if not self.path.split("?")[0].startswith("/api/"):
            if self._redirect_retired_page():
                return
            if self._redirect_settings_page():
                return
            self._rewrite_page_route()
            if self._try_send_html_asset_versions():
                return
        return super().do_HEAD()

    def _safe_wfile_write(self, data: bytes) -> None:
        """Write response body; swallow peer-gone so desk bounce never kills us."""
        try:
            self.wfile.write(data)
        except Exception as e:
            if is_client_disconnect(e):
                self.close_connection = True
                return
            raise

    def _json(self, code, obj):
        out = json.dumps(obj).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(out)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self._safe_wfile_write(out)
        except Exception as e:
            if is_client_disconnect(e):
                self.close_connection = True
                return
            raise

    def _plain(self, code, text, content_type="text/plain; charset=utf-8"):
        out = (text if isinstance(text, str) else str(text)).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(out)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self._safe_wfile_write(out)
        except Exception as e:
            if is_client_disconnect(e):
                self.close_connection = True
                return
            raise

    def handle_one_request(self):
        """pc-1071: treat client disconnect as normal close (no traceback storm)."""
        try:
            super().handle_one_request()
        except Exception as e:
            if is_client_disconnect(e):
                self.close_connection = True
                return
            raise

    def finish(self):
        """pc-1071: flush/close after broken peer must not re-raise."""
        try:
            super().finish()
        except Exception as e:
            if is_client_disconnect(e):
                return
            # Other OSErrors on close are also non-fatal for a dead client.
            if isinstance(e, OSError):
                return
            raise

    def do_POST(self):
        if not _suite_package_healthy():
            self._send_stale_upgrade_response()
            return
        route = self.path.split("?")[0]
        if route == "/api/hidden":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                slugs = set(read_hidden())
                slug = str(body.get("slug", "")).strip()
                if slug:
                    (slugs.add if body.get("hidden", True) else
                     slugs.discard)(slug)
                write_hidden(slugs)
                self._json(200, {"hidden": sorted(slugs)})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        # pc-1119: map ring / outline custom sort order (city-side, not localStorage).
        if route == "/api/map/layout":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "JSON object required"})
                return
            order = body.get("order")
            if not isinstance(order, list):
                self._json(400, {"error": "order must be an array"})
                return
            order = [str(s) for s in order if isinstance(s, (str, int))]
            try:
                write_map_layout(order)
                self._json(200, {"ok": True, "order": order})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        # pc-1172: pin doors (full replace) + run host-action by index.
        if route.startswith("/api/project/") and (
            route.endswith("/doors") or route.endswith("/doors/run")
        ):
            is_run = route.endswith("/doors/run")
            suffix = "/doors/run" if is_run else "/doors"
            mid = route[len("/api/project/") : -len(suffix)].strip("/")
            if not mid or "/" in mid:
                self._json(400, {"error": "bad project slug"})
                return
            project_dir = resolve_project_dir(mid)
            if not project_dir:
                self._json(404, {"error": "unknown project", "slug": mid})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "JSON object required"})
                return
            if is_run:
                if not _client_is_loopback(self):
                    self._json(
                        403,
                        {
                            "ok": False,
                            "error": "host-action only from loopback clients",
                        },
                    )
                    return
                doors = read_project_doors(project_dir)
                try:
                    idx = int(body.get("index"))
                except (TypeError, ValueError):
                    self._json(400, {"ok": False, "error": "index required (int)"})
                    return
                if idx < 0 or idx >= len(doors):
                    self._json(400, {"ok": False, "error": "index out of range"})
                    return
                door = doors[idx]
                if door.get("kind") != "host-action":
                    self._json(
                        400,
                        {"ok": False, "error": "door at index is not host-action"},
                    )
                    return
                # pc-1228: stale-index guard — a dig rendered before a
                # doors.json edit could post an index that now names a
                # different door. Clients send the label they showed the
                # user; mismatch means the list changed under them.
                want_label = body.get("label")
                if want_label is not None and str(want_label) != str(
                    door.get("label") or ""
                ):
                    self._json(
                        409,
                        {
                            "ok": False,
                            "error": "door list changed — reload and retry",
                        },
                    )
                    return
                result, err = execute_host_action(project_dir, door)
                if err:
                    self._json(400, {"ok": False, "error": err})
                    return
                self._json(200, result)
                return
            # Full replace of doors array (pin / edit / remove / reorder).
            raw_doors = body.get("doors")
            if not isinstance(raw_doors, list):
                self._json(400, {"ok": False, "error": "doors must be an array"})
                return
            if len(raw_doors) > _MAX_DOORS:
                self._json(
                    400,
                    {
                        "ok": False,
                        "error": "too many doors (max %d)" % _MAX_DOORS,
                    },
                )
                return
            cleaned = []
            for i, item in enumerate(raw_doors):
                door, err = normalize_door_entry(item)
                if err:
                    self._json(
                        400,
                        {
                            "ok": False,
                            "error": "door[%d]: %s" % (i, err),
                        },
                    )
                    return
                cleaned.append(door)
            try:
                write_project_doors(project_dir, cleaned)
                self._json(200, {"ok": True, "doors": cleaned})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        # Citizen notes — project Home only (pc-242). Raw markdown body.
        # pc-653 §3: expected-state — .protocolcity/expected-state.json.
        if route.startswith("/api/project/") and (
            route.endswith("/notes") or route.endswith("/expected-state")
        ):
            is_expected = route.endswith("/expected-state")
            suffix = "/expected-state" if is_expected else "/notes"
            mid = route[len("/api/project/") : -len(suffix)].strip("/")
            if not mid or "/" in mid:
                self._json(400, {"error": "bad project slug"})
                return
            project_dir = resolve_project_dir(mid)
            if not project_dir:
                self._json(404, {"error": "unknown project", "slug": mid})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if is_expected:
                if length < 0 or length > 8192:
                    self._json(413, {"error": "body too large"})
                    return
                try:
                    raw = self.rfile.read(length) if length else b"{}"
                    body = json.loads(raw or b"{}")
                except Exception:
                    self._json(400, {"error": "Invalid JSON body"})
                    return
                if not isinstance(body, dict):
                    self._json(400, {"error": "JSON object required"})
                    return
                try:
                    state = merge_project_expected_state(project_dir, body)
                    self._json(
                        200,
                        {"ok": True, "slug": mid, "expected": state},
                    )
                except Exception as e:
                    self._json(500, {"error": str(e)})
                return
            # Cap notes so a runaway client cannot fill the disk (256 KiB).
            if length < 0 or length > 262144:
                self._json(413, {"error": "notes too large (max 256KiB)"})
                return
            try:
                raw = self.rfile.read(length) if length else b""
                text = raw.decode("utf-8", errors="replace")
                write_project_notes(project_dir, text)
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        # pc-428: set model pin on local WorkForce roster (daemon reloads next tick).
        if route.startswith("/api/worker/") and route.endswith("/model"):
            mid = route[len("/api/worker/") : -len("/model")].strip("/")
            if not mid or "/" in mid or mid in (".", ".."):
                self._json(400, {"ok": False, "error": "bad worker name"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 8192:
                self._json(413, {"ok": False, "error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"ok": False, "error": "JSON object required"})
                return
            if "model" not in body:
                self._json(400, {"ok": False, "error": "model field required"})
                return
            try:
                result = patch_roster_worker_model(mid, str(body.get("model") or ""))
                _invalidate_cache(PROXY.get("/api/people") or "/api/people")
                self._json(200, result)
            except KeyError as e:
                self._json(404, {"ok": False, "error": str(e)})
            except FileNotFoundError as e:
                self._json(404, {"ok": False, "error": str(e)})
            except ValueError as e:
                self._json(400, {"ok": False, "error": str(e)})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return

        # On-demand Dispatch — same engine path as a scheduled fire (pc-243).
        # Proxies WorkForce POST /api/dispatch/<name>; suite never spawns shifts.
        # pc-390: normalize ok/msg/error/name so UI can always explain refusal.
        if route.startswith("/api/dispatch/"):
            name = unquote(route[len("/api/dispatch/"):].strip("/"))
            if not name or "/" in name or name in (".", ".."):
                self._json(400, {
                    "ok": False,
                    "name": name,
                    "msg": "bad agent name",
                    "error": "bad agent name",
                })
                return
            # Drain any body (clients may send empty JSON); ignore content.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 0:
                    self.rfile.read(length)
            except Exception:
                pass

            def _normalize_dispatch(payload, *, ok_default=True):
                if not isinstance(payload, dict):
                    payload = {"ok": ok_default, "msg": str(payload)}
                else:
                    payload = dict(payload)
                if "ok" not in payload:
                    payload["ok"] = ok_default
                msg = payload.get("msg") or payload.get("error") or (
                    "dispatched" if payload.get("ok") else "dispatch refused"
                )
                payload["msg"] = str(msg)
                payload["error"] = str(payload.get("error") or msg)
                payload["name"] = name
                # Citizen-facing rewrites of common engine phrases
                low = payload["msg"].lower()
                if "no such worker" in low:
                    payload["msg"] = (
                        "not on the roster — hire first "
                        "(blueprint hire %s --workdir <project>)" % name
                    )
                    payload["error"] = payload["msg"]
                elif "already in flight" in low or "in flight" in low:
                    payload["msg"] = "already on shift — wait for this run to finish"
                    payload["error"] = payload["msg"]
                elif "read-only" in low or "no daemon" in low:
                    payload["msg"] = (
                        "WorkForce has no daemon on this port "
                        "(start suite with engines / service install)"
                    )
                    payload["error"] = payload["msg"]
                elif "roster unreadable" in low:
                    payload["msg"] = (
                        "roster unreadable — check "
                        ".protocolcity/workforce/local/roster.json"
                    )
                    payload["error"] = payload["msg"]
                return payload

            url = f"{WORKFORCE}/api/dispatch/{quote(name)}"
            try:
                req = urllib.request.Request(url, data=b"", method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=10) as r:
                    raw = r.read().decode("utf-8")
                    try:
                        payload = json.loads(raw) if raw else {"ok": True}
                    except json.JSONDecodeError:
                        payload = {"ok": True, "msg": raw or "dispatched"}
                    payload = _normalize_dispatch(payload, ok_default=True)
                    if not payload.get("ok"):
                        self._json(409, payload)
                        return
                    _invalidate_cache(PROXY["/api/people"])
                    self._json(200, payload)
            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode("utf-8")
                    payload = json.loads(body) if body else {
                        "ok": False, "msg": e.reason or str(e.code),
                    }
                except Exception:
                    payload = {"ok": False, "msg": e.reason or str(e.code)}
                payload = _normalize_dispatch(payload, ok_default=False)
                # WorkForce uses 409 when refused (in flight / unknown / read-only).
                self._json(e.code if e.code in (400, 404, 409, 502, 503) else 502,
                           payload)
            except Exception as e:
                self._json(502, _normalize_dispatch({
                    "ok": False,
                    "msg": (
                        "WorkForce unreachable — is the agent daemon up? "
                        "blueprint serve --root <workspace>  (%s)" % e
                    ),
                }, ok_default=False))
            return

        # pc-555: skip next scheduled fire only (Approaching / countdown).
        # Never kills a LIVE shift. Proxies WF /api/skip when present; else
        # holds the engine lock until next_fire so the tick becomes ledger SKIP.
        if route.startswith("/api/skip/"):
            name = unquote(route[len("/api/skip/") :].strip("/"))
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 0:
                    self.rfile.read(length)
            except Exception:
                pass
            if not name or "/" in name or name in (".", ".."):
                self._json(
                    400,
                    {
                        "ok": False,
                        "name": name,
                        "msg": "bad agent name",
                        "error": "bad agent name",
                    },
                )
                return
            try:
                result = skip_next_scheduled_fire(name)
            except KeyError as e:
                self._json(
                    404,
                    {
                        "ok": False,
                        "name": name,
                        "msg": str(e),
                        "error": str(e),
                    },
                )
                return
            except ValueError as e:
                self._json(
                    400,
                    {
                        "ok": False,
                        "name": name,
                        "msg": str(e),
                        "error": str(e),
                    },
                )
                return
            except Exception as e:
                self._json(
                    500,
                    {
                        "ok": False,
                        "name": name,
                        "msg": str(e),
                        "error": str(e),
                    },
                )
                return
            if not result.get("ok"):
                code = 409
                err = str(result.get("error") or "")
                if err in ("no_next_fire", "past_fire", "bad_next_fire"):
                    code = 400
                self._json(code, result)
                return
            _invalidate_cache(PROXY.get("/api/people") or "/api/people")
            self._json(200, result)
            return

        # pc-484: same-origin attention snooze/unsnooze → Desk (tp-205).
        # Snooze mutes For You gold only — never clears gates or cancels tickets.
        if route in ("/api/attention/snooze", "/api/attention/unsnooze"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"ok": False, "error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"ok": False, "error": "JSON object required"})
                return
            action = "unsnooze" if route.endswith("/unsnooze") else "snooze"
            # Normalize product/project for product-scope mutes.
            payload = dict(body)
            prod = _normalize_store_slug(
                payload.get("product") or payload.get("project") or ""
            )
            if prod:
                payload["product"] = prod
            scope = str(payload.get("scope") or "product").strip().lower() or "product"
            payload["scope"] = scope
            code, data = _proxy_desk_json(
                "POST", f"/api/dev/attention/{action}", payload, timeout=8
            )
            # pc-1093: PROXY has no /api/attention key in default config
            # (in-process census). bust_census_caches already drops the
            # citylens you-attention URL + in-process snap — do not call
            # _invalidate_cache on a missing PROXY key (was a silent no-op).
            bust_census_caches()
            self._json(
                code if code in (200, 201, 400, 404, 409, 502, 503) else 502,
                data if isinstance(data, dict) else {"ok": False, "error": str(data)},
            )
            return
        # pc-288: citizen file at the Desk front window → WorkLane intake.
        if route == "/api/tasks":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"ok": False, "error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"ok": False, "error": "JSON object required"})
                return
            project = _normalize_store_slug(
                body.get("project") or body.get("product") or ""
            )
            title = str(body.get("title") or "").strip()
            description = str(body.get("description") or "").strip()
            author = str(body.get("author") or "you").strip() or "you"
            if not project:
                self._json(400, {"ok": False, "error": "project (store) is required"})
                return
            if not title:
                self._json(400, {"ok": False, "error": "title is required"})
                return
            if not description:
                self._json(400, {
                    "ok": False,
                    "error": "description is required — problem + expected outcome",
                })
                return
            try:
                priority = int(body.get("priority") or 3)
            except (TypeError, ValueError):
                self._json(400, {"ok": False, "error": "priority must be an integer"})
                return
            labels_raw = body.get("labels") or []
            # pc-498: hand picker (worker|hand) stamps worker:<id>; dual worker:*
            # rejected; unlabeled → needs:routing so ready is never silent.
            labels, route_err, route_meta = _normalize_intake_labels(
                labels_raw,
                worker=body.get("worker"),
                hand=body.get("hand"),
            )
            if route_err:
                self._json(400, {
                    "ok": False,
                    "error": route_err,
                    "routing": route_meta,
                })
                return
            payload = {
                "project": project,
                "product": project,
                "title": title,
                "description": description,
                "priority": priority,
                "labels": labels or [],
                "author": author,
            }
            code, data = _proxy_desk_json("POST", "/api/admin/tasks", payload)
            # Ticket invent can change scene/ready counts + map house open badges.
            _invalidate_cache(PROXY.get("/api/tp-scene") or "")
            bust_census_caches()
            if code in (200, 201):
                # pc-1093: rail WO list + chip tallies must see the new ticket
                bust_wo_caches()
            if isinstance(data, dict) and code in (200, 201):
                data = dict(data)
                data["routing"] = route_meta
                data["labels"] = labels or data.get("labels") or []
            self._json(code if code in (200, 201, 400, 404, 409, 502, 503) else 502, data)
            return
        # pc-288: Owner / claim comment after take-a-number.
        if route.startswith("/api/task/") and route.endswith("/comments"):
            mid = route[len("/api/task/"):-len("/comments")].strip("/")
            if not mid or "/" in mid or mid in (".", ".."):
                self._json(400, {"ok": False, "error": "bad task id"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"ok": False, "error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"ok": False, "error": "JSON object required"})
                return
            text = str(body.get("body") or body.get("comment") or "").strip()
            author = str(body.get("author") or "you").strip() or "you"
            if not text:
                self._json(400, {"ok": False, "error": "body is required"})
                return
            payload = {"body": text, "author": author}
            code, data = _proxy_desk_json(
                "POST",
                f"/api/admin/tasks/{quote(mid)}/comments",
                payload,
            )
            # pc-1093: Owner markers change live-strip owner/preview rows
            if code in (200, 201):
                _invalidate_cache(PROXY.get("/api/tp-scene") or "")
                bust_wo_caches()
            self._json(code if code in (200, 201, 400, 404, 409, 502, 503) else 502, data)
            return
        # Open path in Finder (pc-76 pattern from citylens) — city root only.
        if route == "/api/open":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                body = {}
            requested = str((body or {}).get("path") or "").strip()
            qs = parse_qs(urlsplit(self.path).query)
            if not requested and qs.get("path"):
                requested = (qs.get("path") or [""])[0]
            if not requested:
                # Empty path = city root
                allowed = os.path.realpath(CITY_ROOT)
            elif os.path.isabs(requested):
                allowed = os.path.realpath(requested)
                root = os.path.realpath(CITY_ROOT)
                if allowed != root and not allowed.startswith(root + os.sep):
                    self._json(403, {"error": "path not allowed", "path": requested})
                    return
                if not os.path.exists(allowed):
                    self._json(404, {"error": "not found", "path": requested})
                    return
            else:
                # pc-1209: project hint rescues project-relative WHERE paths
                project = str((body or {}).get("project") or "").strip()
                if not project and qs.get("project"):
                    project = (qs.get("project") or [""])[0]
                allowed, requested = resolve_city_rel_with_project(
                    requested, project
                )
                if not allowed or not os.path.exists(allowed):
                    self._json(404, {"error": "not found", "path": requested})
                    return
            if os.path.isfile(allowed):
                cmd = ["open", "-R", allowed]
                kind = "file"
            else:
                cmd = ["open", allowed]
                kind = "dir"
            try:
                subprocess.run(cmd, check=False, timeout=10, capture_output=True)
            except Exception as e:
                self._json(500, {"error": "open failed", "detail": str(e)})
                return
            self._json(200, {"ok": True, "path": allowed, "kind": kind})
            return
        # pc-302/pc-574: adopt/manage a top-level folder — in-process census.
        if route == "/api/manage":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 0 or length > 65536:
                self._json(413, {"ok": False, "error": "body too large"})
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
            except Exception:
                self._json(400, {"ok": False, "error": "Invalid JSON body"})
                return
            if not isinstance(body, dict):
                self._json(400, {"ok": False, "error": "JSON object required"})
                return
            name = str(body.get("name") or body.get("cabinet") or "").strip()
            if not name or "/" in name or name in (".", ".."):
                self._json(400, {"ok": False, "error": "name required (top-level folder)"})
                return
            force = bool(body.get("force"))
            consumer = bool(body.get("consumer"))
            live_desk = bool(
                body.get("live_desk") or body.get("allow_live_desk")
            )
            if _CITYLENS_REMOTE:
                payload = {"name": name}
                if force:
                    payload["force"] = True
                if consumer:
                    payload["consumer"] = True
                if live_desk:
                    payload["live_desk"] = True
                code, data = _proxy_citylens_json(
                    "POST", "/api/manage", payload, timeout=120
                )
            else:
                try:
                    data = _citylens().manage_cabinet(
                        CITY_ROOT,
                        name,
                        force=force,
                        consumer=consumer,
                        allow_live_desk=live_desk,
                    )
                    if not isinstance(data, dict):
                        data = {"ok": False, "error": "manage returned non-dict"}
                    code = (
                        200
                        if data.get("ok") is not False
                        else (400 if data.get("error") else 500)
                    )
                    if data.get("ok") is False and data.get("zone"):
                        code = 400
                except (ValueError, FileNotFoundError, FileExistsError) as e:
                    code, data = 400, {"ok": False, "error": str(e)}
                except Exception as e:
                    code, data = 500, {"ok": False, "error": str(e)}
            if code in (200, 201) and isinstance(data, dict) and data.get("ok") is not False:
                bust_census_caches()
            self._json(
                code if code in (200, 201, 400, 404, 409, 500, 502, 503) else 502,
                data,
            )
            return
        # pc-446: Map empty-state — seed L0 workspace ops jobs (idempotent).
        if route == "/api/seed-ops":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length > 0:
                try:
                    self.rfile.read(min(length, 65536))
                except Exception:
                    pass
            try:
                from pathlib import Path as _Path

                from protocolcity.seed_ops import seed_workspace_ops

                receipt = seed_workspace_ops(_Path(CITY_ROOT), quiet=True)
                if not isinstance(receipt, dict):
                    receipt = {"ok": False, "error": "bad receipt"}
                # People feed changes — drop caches so Map reloads roster.
                try:
                    _invalidate_cache(PROXY.get("/api/people") or "")
                    bust_census_caches()
                except Exception:
                    pass
                code = 200 if receipt.get("ok") is not False else 500
                self._json(code, receipt)
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return
        # pc-325/pc-574: Workspace Settings — force land resurvey in-process.
        # Suite owns the citizen door; citylens library owns the walk. No TP/WF mutation.
        if route == "/api/survey":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 0:
                    self.rfile.read(min(length, 65536))
            except Exception:
                pass
            if _CITYLENS_REMOTE:
                code, data = _proxy_citylens_json(
                    "POST", "/api/survey", {}, timeout=30
                )
            else:
                try:
                    summary = _citylens().start_survey(CITY_ROOT, force=True)
                    data = {"ok": True, "survey": summary}
                    code = 200
                except Exception as e:
                    code, data = 500, {"ok": False, "error": str(e)}
            if code in (200, 201, 202) and isinstance(data, dict):
                bust_census_caches()
            self._json(
                code if code in (200, 201, 202, 400, 404, 500, 502, 503) else 502,
                data if isinstance(data, dict) else {"ok": False, "error": str(data)},
            )
            return
        self.send_error(405)

    def do_PATCH(self):
        """pc-288: claim / status moves from suite Desk take-a-number."""
        route = self.path.split("?")[0]
        if not route.startswith("/api/task/"):
            self.send_error(405)
            return
        rest = route[len("/api/task/"):].strip("/")
        if not rest or "/" in rest or rest in (".", ".."):
            self._json(400, {"ok": False, "error": "bad task id"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > 65536:
            self._json(413, {"ok": False, "error": "body too large"})
            return
        try:
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
        except Exception:
            self._json(400, {"ok": False, "error": "Invalid JSON body"})
            return
        if not isinstance(body, dict):
            self._json(400, {"ok": False, "error": "JSON object required"})
            return
        # Citizen-safe subset: status + author + gate (pc-1148 Remind me on…).
        # Power edits (title/description/priority/labels) stay on the engine.
        payload = {}
        if "status" in body:
            st = str(body.get("status") or "").strip()
            if st not in (
                "backlog", "in_progress", "in_review", "done", "canceled",
            ):
                self._json(400, {"ok": False, "error": "unknown status"})
                return
            payload["status"] = st
        # pc-1148: timer/human/deferred/clear so dig-in can leave Decide gold
        # for Watch/calendar without a second engine door.
        if "gate_type" in body:
            gt_raw = body.get("gate_type")
            if gt_raw is None:
                gt = ""
            else:
                gt = str(gt_raw).strip().lower()
            if gt not in ("", "human", "timer", "deferred"):
                self._json(
                    400,
                    {
                        "ok": False,
                        "error": "gate_type must be '', 'human', 'timer', or 'deferred'",
                    },
                )
                return
            payload["gate_type"] = gt
            if "gate_until" in body:
                gu = body.get("gate_until")
                payload["gate_until"] = (
                    None if gu is None or gu == "" else str(gu).strip()
                )
            if "gate_note" in body:
                gn = body.get("gate_note")
                payload["gate_note"] = (
                    None if gn is None else str(gn).strip() or None
                )
            if gt == "timer" and not payload.get("gate_until"):
                self._json(
                    400,
                    {"ok": False, "error": "gate_until required when gate_type is timer"},
                )
                return
        elif "gate_until" in body or "gate_note" in body:
            self._json(
                400,
                {
                    "ok": False,
                    "error": "gate_type is required when setting gate_until or gate_note",
                },
            )
            return
        if payload or "author" in body or "status" in body or "gate_type" in body:
            payload["author"] = str(body.get("author") or "you").strip() or "you"
        if not payload:
            self._json(
                400,
                {
                    "ok": False,
                    "error": "status, author, and/or gate_type required",
                },
            )
            return
        code, data = _proxy_desk_json(
            "PATCH",
            f"/api/admin/tasks/{quote(rest)}",
            payload,
        )
        _invalidate_cache(PROXY.get("/api/tp-scene") or "")
        # pc-1234: close also invalidates people so in_flight clears on next light poll
        _invalidate_cache(PROXY.get("/api/people") or "")
        bust_census_caches()
        if code in (200, 201):
            # pc-1093: status/claim moves must refresh rail list + chip tallies
            bust_wo_caches()
        self._json(code if code in (200, 400, 404, 409, 502, 503) else 502, data)

    def do_GET(self):
        # pc-438: brew upgrade while suite runs → Cellar path deleted → silent 404
        if not _suite_package_healthy():
            self._send_stale_upgrade_response()
            return

        route = self.path.split("?")[0]
        qs = parse_qs(urlsplit(self.path).query)

        # pc-1125: workspace calendar — ICS feed + cheap HTML list
        if route in ("/calendar.ics", "/calendar"):
            force = str((qs.get("force") or ["0"])[0]).lower() in (
                "1", "true", "yes", "on",
            )
            base = _calendar_public_base(self)
            try:
                events, errors = build_workspace_calendar_events(
                    force=force, base_url=base
                )
            except Exception as e:
                if route == "/calendar.ics":
                    self._plain(
                        502,
                        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
                        "PRODID:-//BluePrint//Workspace Calendar//EN\r\n"
                        "END:VCALENDAR\r\n",
                        content_type="text/calendar; charset=utf-8",
                    )
                else:
                    self._json(502, {"ok": False, "error": str(e)})
                return
            if route == "/calendar.ics":
                body = _cal_render_ics(
                    events,
                    cal_name="OneSeo Workspace",
                )
                # Brief cache so Apple Calendar polls are not a desk stampede
                out = body.encode("utf-8")
                try:
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "text/calendar; charset=utf-8"
                    )
                    self.send_header("Content-Length", str(len(out)))
                    self.send_header(
                        "Cache-Control", "public, max-age=30, must-revalidate"
                    )
                    self.send_header(
                        "Content-Disposition",
                        'inline; filename="oneseo-workspace.ics"',
                    )
                    if errors:
                        self.send_header(
                            "X-BluePrint-Calendar-Errors",
                            str(len(errors)),
                        )
                    self.end_headers()
                    self._safe_wfile_write(out)
                except Exception as e:
                    if is_client_disconnect(e):
                        self.close_connection = True
                        return
                    raise
                return
            # HTML list
            html = _cal_render_html(
                events,
                ics_href="/calendar.ics",
                title="Workspace calendar",
            )
            self._plain(200, html, content_type="text/html; charset=utf-8")
            return

        # pc-890: dig-in inventory (was bundled into map-bootstrap light city)
        # pc-1040: empty path/slug = workspace root (not 404)
        if route == "/api/hood-inventory":
            rel = (qs.get("path") or qs.get("scope") or [""])[0]
            slug = (qs.get("slug") or qs.get("project") or [""])[0]
            target = safe_city_path(rel) if rel else None
            if not target or not os.path.isdir(target):
                if slug:
                    target = resolve_project_dir(slug)
            # Empty address → city root inventory (workspace papers nest)
            if (not target or not os.path.isdir(target)) and not rel and not slug:
                target = os.path.realpath(CITY_ROOT)
            if not target or not os.path.isdir(target):
                self._json(404, {"error": "not found", "path": rel})
                return
            try:
                inv = _hood_inventory(target)
            except Exception as e:
                self._json(500, {"error": str(e)})
                return
            root = os.path.realpath(CITY_ROOT)
            try:
                if os.path.realpath(target) == root:
                    rel_out = ""
                else:
                    rel_out = os.path.relpath(target, root).replace(os.sep, "/")
            except ValueError:
                rel_out = target
            self._json(
                200,
                {
                    "ok": True,
                    "path": rel_out,
                    "root_entries": inv.get("root_entries") or [],
                    "root_mds": inv.get("root_mds") or [],
                    "agent_papers": inv.get("agent_papers") or [],
                },
            )
            return

        if route == "/api/ground":
            # Finder-parity: current folder only. One algorithm for both
            # city-root and scoped paths (pc-1040): list entries; at city
            # root skip non-dotted dirs (parcels come from /api/city).
            scope = (qs.get("scope") or [""])[0]
            try:
                if scope:
                    base = safe_city_path(scope)
                    if base is None or not os.path.isdir(base):
                        raise FileNotFoundError(scope)
                else:
                    base = os.path.realpath(CITY_ROOT)
                try:
                    at_city_root = (
                        os.path.realpath(base) == os.path.realpath(CITY_ROOT)
                    )
                except OSError:
                    at_city_root = not bool(scope)
                entries = []
                for name in sorted(os.listdir(base), key=str.lower):
                    is_dir = os.path.isdir(os.path.join(base, name))
                    dotted = name.startswith(".")
                    # City root: project dirs are plots from /api/city, not
                    # repeated here. Dot-dirs + files still surface.
                    if at_city_root and is_dir and not dotted:
                        continue
                    entries.append(ground_entry(name, base, not at_city_root))
                self._json(200, {
                    "scope": scope or "",
                    "managed": (
                        True if at_city_root else dir_managed(base)
                    ),
                    "entries": entries,
                })
            except Exception:
                self._json(404, {"error": "no such folder", "scope": scope})
            return

        if route == "/api/hidden":
            self._json(200, {"hidden": read_hidden()})
            return

        if route == "/api/find":
            # pc-1225: survey-index name search on the suite door (pc-94
            # citylens seam). Files + folders across the whole workspace ride
            # the Map searchlight — heaps stay honest via skipped_hint.
            q = (qs.get("q") or [""])[0]
            lim_raw = (qs.get("limit") or [""])[0]
            try:
                cl = _citylens()
                try:
                    lim = int(lim_raw) if lim_raw else cl.FIND_MAX_HITS
                except ValueError:
                    lim = cl.FIND_MAX_HITS
                result = cl.find_in_survey(q, limit=lim)
                if not int((result.get("survey") or {}).get("entries") or 0):
                    # Cold state: load the survey cache (or kick a background
                    # walk) — never blocks the request on the walk itself.
                    cl.start_survey(CITY_ROOT, force=False)
                    result = cl.find_in_survey(q, limit=lim)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        # pc-355: always-on disk detect — cheap, no engine fan-in
        if route == "/api/detect":
            try:
                self._json(200, detect_workspace(CITY_ROOT))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if route == "/api/overview":
            room = (qs.get("room") or ["desk"])[0]
            project = (qs.get("project") or [""])[0]
            try:
                self._json(200, build_overview(room, project))
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if route == "/api/file":
            # Read-only .md for the in-suite paper reader. Path is relative
            # to city root. Never serves non-md or paths outside the city.
            # pc-1209: ?project= falls back to <project-folder>/<path> so
            # project-relative WHERE paths on work orders resolve.
            rel = (qs.get("path") or [""])[0]
            project = (qs.get("project") or qs.get("product") or [""])[0]
            target, rel = resolve_city_rel_with_project(rel, project)
            if not target or not os.path.isfile(target):
                self._json(404, {"error": "not found", "path": rel})
                return
            if not target.lower().endswith(".md"):
                self._json(415, {
                    "error": "only markdown is readable in-suite",
                    "path": rel,
                })
                return
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                self._json(500, {"error": str(e)})
                return
            name = os.path.basename(target)
            root = os.path.realpath(CITY_ROOT)
            rel_out = os.path.relpath(target, root).replace(os.sep, "/")
            self._json(200, {
                "ok": True,
                "path": rel_out,
                "name": name,
                "rule": name in RULE_NAMES,
                "bytes": len(content.encode("utf-8")),
                "content": content,
            })
            return

        # pc-884 / pc-885: raw report assets for dig-in. City-root only.
        # Truth: prefer city-rel paths (tradeOS/local/reports/…). Also accept
        # repo-rel local/reports/… + ?project= when drops used product-relative.
        if route == "/api/city-asset":
            rel = (qs.get("path") or [""])[0]
            project = (qs.get("project") or qs.get("product") or [""])[0]
            target = safe_city_path(rel)
            if (not target or not os.path.isfile(target)) and rel:
                rel_norm = unquote(rel).replace("\\", "/").lstrip("/")
                if rel_norm.startswith("local/"):
                    # product folder first
                    tried = []
                    if project:
                        pdir = resolve_project_dir(project)
                        if pdir:
                            leaf = os.path.basename(pdir)
                            cand = safe_city_path(leaf + "/" + rel_norm)
                            tried.append(leaf + "/" + rel_norm)
                            if cand and os.path.isfile(cand):
                                target = cand
                                rel = leaf + "/" + rel_norm
                    # case-insensitive scan of top-level projects
                    if not target or not os.path.isfile(target):
                        root = os.path.realpath(CITY_ROOT)
                        try:
                            names = os.listdir(root)
                        except OSError:
                            names = []
                        for name in names:
                            if name.startswith(".") or name in (
                                "ProtocolCity-WorkLane",
                                "ProtocolCity-WorkForce",
                                "ProtocolCity-BluePrint",
                                "ProtocolCity-Charter",
                                "tp-backups",
                                "tradeOS-backups",
                                "homebrew-tap",
                                "local",
                            ):
                                continue
                            cand_rel = name + "/" + rel_norm
                            cand = safe_city_path(cand_rel)
                            if cand and os.path.isfile(cand):
                                target = cand
                                rel = cand_rel
                                break
            if not target or not os.path.isfile(target):
                self._json(404, {"error": "not found", "path": rel})
                return
            low = target.lower()
            if low.endswith(".html") or low.endswith(".htm"):
                ctype = "text/html; charset=utf-8"
            elif low.endswith(".md"):
                ctype = "text/markdown; charset=utf-8"
            elif low.endswith(".json"):
                ctype = "application/json; charset=utf-8"
            elif low.endswith(".txt") or low.endswith(".log"):
                ctype = "text/plain; charset=utf-8"
            else:
                self._json(415, {
                    "error": "city-asset allows .html .md .json .txt .log only",
                    "path": rel,
                })
                return
            # Cap large dumps (reports should be small)
            try:
                size = os.path.getsize(target)
            except OSError as e:
                self._json(500, {"error": str(e)})
                return
            if size > 2 * 1024 * 1024:
                self._json(413, {"error": "file too large", "path": rel})
                return
            try:
                with open(target, "rb") as f:
                    body = f.read()
            except Exception as e:
                self._json(500, {"error": str(e)})
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return

        # Project local config — app doors + citizen notes (pc-242).
        # Paths: <city-root>/<slug>/local/{doors.json,notes.md}
        # pc-653 §3: <city-root>/<slug>/.protocolcity/expected-state.json
        if route.startswith("/api/project/"):
            rest = route[len("/api/project/"):].strip("/")
            parts = rest.split("/") if rest else []
            if len(parts) == 2 and parts[1] in ("doors", "notes", "expected-state"):
                slug, kind = parts[0], parts[1]
                project_dir = resolve_project_dir(slug)
                if not project_dir:
                    self._json(404, {"error": "unknown project", "slug": slug})
                    return
                if kind == "doors":
                    self._json(200, {"doors": read_project_doors(project_dir)})
                    return
                if kind == "expected-state":
                    self._json(
                        200,
                        {
                            "ok": True,
                            "slug": slug,
                            "expected": read_project_expected_state(project_dir),
                        },
                    )
                    return
                # notes — raw markdown (text/plain), empty string if absent
                self._plain(200, read_project_notes(project_dir))
                return
            self._json(404, {"error": "unknown project route", "path": route})
            return

        # pc-653 §3: bulk expected-state for Map hygiene pins / overview.
        if route == "/api/hygiene-expected":
            try:
                by_slug = list_hygiene_expected()
                self._json(200, {"ok": True, "by_slug": by_slug})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return

        # pc-432: list recent ops/job report markdown (workspace orbit / dig-in)
        if route == "/api/ops-reports":
            qs = parse_qs(urlsplit(self.path).query)
            who = (qs.get("name") or qs.get("job") or [""])[0]
            try:
                lim = int((qs.get("limit") or ["20"])[0])
            except ValueError:
                lim = 20
            try:
                items = list_ops_reports(name=who, limit=lim)
                self._json(
                    200,
                    {
                        "ok": True,
                        "name": who or None,
                        "count": len(items),
                        "reports": items,
                        "note": (
                            "Jobs write dated .md under ops/local/reports "
                            "(and legacy local/reports). Empty until a job runs."
                        ),
                    },
                )
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return

        # Personnel file — WorkForce worker model + city-relative law paths
        if route.startswith("/api/worker/"):
            name = unquote(route[len("/api/worker/"):].strip("/"))
            if not name or "/" in name or name in (".", ".."):
                self._json(400, {"error": "bad worker name"})
                return
            try:
                url = f"{WORKFORCE}/api/worker/{quote(name)}"
                with urllib.request.urlopen(url, timeout=5) as r:
                    data = json.loads(r.read().decode("utf-8"))
                self._json(200, enrich_worker_law(data))  # law paths + outputs
            except urllib.error.HTTPError as e:
                self._json(e.code, {"error": "worker not found", "name": name})
            except Exception as e:
                self._json(502, {"error": str(e)})
            return

        # pc-288: take-a-number — oldest ready work (city or house-scoped).
        if route == "/api/tasks/ready":
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            try:
                limit = int((qs.get("limit") or ["1"])[0])
            except ValueError:
                limit = 1
            limit = max(1, min(limit, 20))
            q = [("limit", str(limit))]
            if product:
                q.append(("product", product))
                q.append(("project", product))
            code, data = _proxy_desk_json(
                "GET", "/api/admin/tasks/ready?" + urlencode(q), timeout=12
            )
            if code != 200 or not isinstance(data, dict):
                self._json(code if code in (400, 404, 502, 503) else 502,
                           data if isinstance(data, dict) else {"ok": False, "error": str(data)})
                return
            tasks = data.get("tasks") or data.get("ready") or []
            light = []
            for t in tasks or []:
                row = _light_task_row(t, product_fallback=product or None)
                if row and row.get("id"):
                    light.append(row)
            self._json(200, {
                "ok": True,
                "product": product or data.get("product") or None,
                "count": len(light),
                "tasks": light,
            })
            return

        # pc-498: starvation surface — ready work with no worker:* hand label.
        # Schedules only drain labeled feeds; this count is the Map/Roster chip
        # and doctor input. Desk requires a single product per ready query.
        # pc-1044: city-wide unrouted intentionally scans stores with ready>0
        # (scene-driven product list) rather than one multi-store admin list —
        # WorkLane ready is single-product; aggregation here is deliberate.
        if route == "/api/tasks/unrouted":
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            try:
                limit = int((qs.get("limit") or ["40"])[0])
            except ValueError:
                limit = 40
            limit = max(1, min(limit, 100))
            products = []
            if product:
                products = [product]
            else:
                # City-wide: scan desk scene stores that report ready > 0.
                scode, scene = _proxy_desk_json("GET", "/api/scene", timeout=4)
                stores = []
                if scode == 200 and isinstance(scene, dict):
                    stores = scene.get("stores") or scene.get("products") or []
                if isinstance(stores, list):
                    for s in stores:
                        if not isinstance(s, dict):
                            continue
                        slug = _normalize_store_slug(
                            s.get("slug") or s.get("product") or s.get("name") or ""
                        )
                        try:
                            ready_n = int(s.get("ready") or 0)
                        except (TypeError, ValueError):
                            ready_n = 0
                        if slug and ready_n > 0:
                            products.append(slug)
                if not products:
                    # No ready work anywhere — do not invent product=protocolcity
                    # (pc-557: 400 when that store is absent on stranger installs).
                    products = []
            # Dedup preserve order
            seen_p = set()
            products = [p for p in products if not (p in seen_p or seen_p.add(p))]

            unrouted = []
            errors = []
            for prod in products:
                # Over-fetch then filter — labeled ready still occupies slots.
                fetch_n = min(100, max(limit * 3, 40))
                q = [("limit", str(fetch_n)), ("product", prod), ("project", prod)]
                code, data = _proxy_desk_json(
                    "GET", "/api/admin/tasks/ready?" + urlencode(q), timeout=10
                )
                if code != 200 or not isinstance(data, dict):
                    errors.append({
                        "product": prod,
                        "error": (data or {}).get("error") if isinstance(data, dict) else str(data),
                    })
                    continue
                tasks = data.get("tasks") or data.get("ready") or []
                for t in _filter_unrouted_tasks(tasks):
                    row = _light_task_row(t, product_fallback=prod or None)
                    if row and row.get("id"):
                        unrouted.append(row)
            # Oldest first when timestamps exist; then id
            def _sort_key(t):
                return (str(t.get("created_at") or ""), str(t.get("id") or ""))
            unrouted.sort(key=_sort_key)
            light = unrouted[:limit]
            self._json(200, {
                "ok": True,
                "product": product or None,
                "products_scanned": products,
                "count": len(unrouted),
                "returned": len(light),
                "tasks": light,
                "hint": (
                    "Ready work with no worker:<id> never enters a hand queue. "
                    "Route via suite file (worker/hand) or stamp worker:<id>; "
                    "needs:routing marks suite-filed gaps (pc-498)."
                ),
                "errors": errors or None,
            })
            return

        # pc-688: Map WO chip tallies — uncapped gate scan (lists stay capped).
        # pc-1044: product= scopes tallies to one store (project dig-in chips).
        if route == "/api/wo-gate-counts":
            force = (qs.get("force") or [""])[0].strip().lower() in (
                "1",
                "true",
                "yes",
            )
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            try:
                payload = build_wo_gate_counts_payload(
                    force=force, product=product
                )
            except Exception as e:
                self._json(502, {"ok": False, "error": str(e)})
                return
            self._json(200 if payload.get("ok") else 502, payload)
            return

        # pc-934: Map WO desk tape — one suite hop; serial multi-status pull.
        # family=open → backlog+in_progress+in_review; family=all adds done.
        # pc-1044: product= scopes each status pull to one store.
        if route == "/api/tasks/live-strip":
            family = (qs.get("family") or ["open"])[0]
            try:
                limit = int((qs.get("limit") or ["100"])[0])
            except ValueError:
                limit = 100
            force = (qs.get("force") or [""])[0].strip().lower() in (
                "1",
                "true",
                "yes",
            )
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            try:
                payload = build_live_strip_payload(
                    family=family, limit=limit, force=force, product=product
                )
            except Exception as e:
                self._json(
                    502,
                    {
                        "ok": False,
                        "error": "live-strip failed: %s" % e,
                        "tasks": [],
                        "by_status": {},
                    },
                )
                return
            code = 200 if payload.get("ok") else 502
            self._json(code, payload)
            return

        # Task list — WorkLane/TP (backlog / in_progress / in_review / …)
        # Omit product → multi-store city list (suite City Desk backlog).
        if route == "/api/tasks":
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            status = (qs.get("status") or [""])[0]
            label = (qs.get("label") or [""])[0].strip()
            # pc-1404: mast title search — forward Desk q= (wl-493). Empty
            # q is ignored so tape / live-strip callers stay status+limit.
            q_text = str((qs.get("q") or [""])[0] or "").strip()
            if len(q_text) > 120:
                q_text = q_text[:120]
            try:
                limit = int((qs.get("limit") or ["40"])[0])
            except ValueError:
                limit = 40
            if q_text:
                limit = max(1, min(limit, 50))  # Desk search cap (wl-493)
            else:
                limit = max(1, min(limit, 100))
            q = [("limit", str(limit))]
            if product:
                q.append(("product", product))
                q.append(("project", product))  # TP accepts either
            if status:
                q.append(("status", status))
            if label:
                q.append(("label", label))
            if q_text:
                q.append(("q", q_text))

            try:
                # pc-881: with_preview is expensive (comment-scan per row).
                # Opt-in via ?preview=1 / ?owner=1. Auto-on only for small
                # in_progress/in_review lists (Map LIVE Owner: join, pc-526).
                # Never auto for backlog/open-family gate tallies.
                # pc-1404: title search never auto-previews (cheap id+title).
                prev_raw = (qs.get("preview") or qs.get("owner") or [""])[0]
                prev_raw = str(prev_raw).strip().lower()
                if prev_raw in ("1", "true", "yes"):
                    want_preview = True
                elif prev_raw in ("0", "false", "no"):
                    want_preview = False
                elif q_text:
                    want_preview = False
                else:
                    st_l = str(status or "").lower().replace(" ", "_")
                    want_preview = st_l in ("in_progress", "in_review") and limit <= 100
                q_list = list(q)
                if want_preview:
                    q_list.append(("with_preview", "1"))
                url = f"{DESK}/api/admin/tasks?" + urlencode(q_list)
                with urllib.request.urlopen(url, timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8"))
                tasks = data.get("tasks") if isinstance(data, dict) else []
                # pc-1123: single light serializer (suite/api/vocabulary.light_task_row)
                light = []
                for t in tasks or []:
                    row = _light_task_row(t, product_fallback=product or None)
                    if row and row.get("id"):
                        light.append(row)
                self._json(200, {
                    "ok": True,
                    "product": product or None,
                    "status": status or None,
                    "tasks": light,
                    "scope_counts": (data or {}).get("scope_counts"),
                    "column_counts": (data or {}).get("column_counts"),
                    "scope_total": (data or {}).get("scope_total"),
                    "tracker": (data or {}).get("tracker"),
                })
            except Exception as e:
                self._json(502, {"error": str(e)})
            return

        # Ticket paper — WorkLane/TP store record (not a city .md file)
        if route.startswith("/api/task/"):
            tid = unquote(route[len("/api/task/"):].strip("/"))
            if not tid or "/" in tid or tid in (".", ".."):
                self._json(400, {"error": "bad task id", "id": tid})
                return
            # product prefix heuristic from id (full PREFIX_PRODUCT map; pc-1123)
            product_guess = _product_of_task_id(tid) or ""
            # Optional ?product= override (Map / deep links)
            product_q = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            product = product_q or product_guess
            try:
                path_qs = f"/api/admin/tasks/{quote(tid)}"
                if product:
                    path_qs += (
                        f"?product={quote(product)}&project={quote(product)}"
                    )
                # pc-1305: overlay paints Glance first; hydrate must not sit
                # on the default 12s desk proxy. Bound this GET so Map search
                # open fails fast instead of freezing on Opening ticket…
                code, data = _proxy_desk_json("GET", path_qs, timeout=4)
                if not isinstance(data, dict):
                    data = {"ok": False, "error": str(data)}
                if "raw" in data and "task" not in data and "id" not in data:
                    self._json(502, {
                        "error": "desk returned non-JSON",
                        "id": tid,
                        "product": product or None,
                    })
                    return
                if code != 200:
                    err_msg = (
                        data.get("error")
                        or data.get("detail")
                        or data.get("message")
                        or "task not found"
                    )
                    if not isinstance(err_msg, str):
                        err_msg = str(err_msg)
                    self._json(code if code else 502, {
                        "error": err_msg,
                        "id": tid,
                        "product": product or None,
                    })
                    return
                task = data.get("task") if isinstance(data, dict) else None
                if not task and isinstance(data, dict) and data.get("id"):
                    task = data
                if not task:
                    self._json(404, {
                        "error": "task not found",
                        "id": tid,
                        "product": product or None,
                    })
                    return
                task = dict(task)
                if product:
                    task.setdefault("product", product)
                self._json(200, {"ok": True, "task": task})
            except Exception as e:
                self._json(502, {
                    "error": str(e),
                    "id": tid,
                    "product": product or None,
                })
            return

        if route == "/api/desk-bootstrap":
            # pc-1044 / pc-267: product= pre-filters attention items server-side
            # so a scoped desk paint never paints another project's For You pile.
            # City shell + people + tpScene stay full (Map still needs hubs).
            product = _normalize_store_slug(
                (qs.get("product") or qs.get("project") or [""])[0]
            )
            data = _desk_bootstrap()
            if data["city"] is None:
                self._json(502, {"error": "city unavailable"})
                return
            if product:
                data = dict(data)
                data["product"] = product
                att = data.get("attention")
                if isinstance(att, dict):
                    items = att.get("items") or []
                    if isinstance(items, list):
                        kept = []
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            ip = _normalize_store_slug(
                                it.get("product")
                                or it.get("project")
                                or it.get("store")
                                or ""
                            )
                            if not ip:
                                # Infer from composite id prefix when field blank
                                tid = str(it.get("id") or "")
                                if "-" in tid:
                                    pre = tid.split("-", 1)[0].lower()
                                    ip = _normalize_store_slug(
                                        _LIVE_STRIP_PREFIX_PRODUCT.get(pre, "")
                                    )
                            if ip == product:
                                kept.append(it)
                        att = dict(att)
                        att["items"] = kept
                        att["count"] = len(kept)
                        att["product"] = product
                        data["attention"] = att
            self._json(200, data)
            return

        if route == "/api/city-structure":
            # pc-413: progressive Map shell — no engines
            try:
                self._json(200, city_structure_from_disk(CITY_ROOT))
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})
            return

        if route == "/api/map/snapshot":
            # pc-1122: canonical Phase-2 snapshot — tpScene always present so
            # clients never paint with stale WO badges on first load (pc-375).
            # pc-1253: city_payload / cached_snapshot fail-open inside a short
            # budget; stamp city_name so Map never paints detect-shell mast.
            data = _map_bootstrap()
            if data.get("city") is None:
                data = dict(data or {})
                data["city"] = data.get("structure") or city_structure_from_disk(
                    CITY_ROOT
                )
                if isinstance(data["city"], dict):
                    data["city"] = dict(data["city"])
                    data["city"]["degraded"] = True
                    data["city"]["error"] = "city unavailable"
                if not data.get("detect"):
                    try:
                        data["detect"] = detect_workspace(CITY_ROOT)
                    except Exception:
                        pass
            city = data.get("city")
            if isinstance(city, dict) and not city.get("city_name"):
                city = dict(city)
                city["city_name"] = (
                    os.path.basename(str(CITY_ROOT).rstrip("/")) or "workspace"
                )
                data["city"] = city
            if "tpScene" not in data:
                data["tpScene"] = {}
            self._json(200, data)
            return

        if route == "/api/map-bootstrap":
            # pc-1122: 302 → canonical /api/map/snapshot (Phase 2 anchor).
            # pc-1175: empty-body 302 must set Content-Length: 0 (HTTP/1.1).
            self._send_redirect("/api/map/snapshot")
            return

        # pc-1119: city-side custom ring order for Map + Outline.
        if route == "/api/map/layout":
            try:
                self._json(200, {"order": read_map_layout()})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if route == "/api/pulse" or route == "/api/generation":
            # LIVE-B4/B5 (pc-278/pc-295): cheap, optionally scoped tokens.
            scope = str((qs.get("scope") or ["all"])[0]).strip().lower() or "all"
            if scope not in ("city", "tickets", "people", "all"):
                self._json(400, {
                    "error": "unknown pulse scope",
                    "scope": scope,
                    "allowed": ["city", "tickets", "people", "all"],
                })
                return
            product = _normalize_store_slug(
                (qs.get("product") or [""])[0]
            )
            pulse = build_pulse(scope=scope, product=product)
            # pc-1244: bust WO caches when ticket token changes externally (CLI close
            # bypasses suite PATCH so bust_wo_caches() was never called).
            try:
                global _last_tickets_token
                new_tok = str(
                    (pulse.get("sources") or {}).get("tickets", {}).get("token") or ""
                )
                if new_tok:
                    with _pulse_token_lock:
                        prev_tok = _last_tickets_token
                        _last_tickets_token = new_tok
                    if prev_tok is not None and new_tok != prev_tok:
                        bust_wo_caches(also_scene=True)
            except Exception:
                pass
            self._json(200, pulse)
            return

        # City activity feed for map comment theater (proxies WorkLane dev activity)
        if route == "/api/activity":
            q = urlsplit(self.path).query
            url = f"{DESK}/api/dev/activity"
            if q:
                url = url + "?" + q
            try:
                req = urllib.request.Request(
                    url, headers={"Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    raw = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)
            except Exception as e:
                self._json(502, {"error": "activity unreachable: %s" % e})
            return

        # pc-1114: store prefix registry — slug↔prefix map from desk /api/admin/products
        if route == "/api/stores/prefixes":
            try:
                req = urllib.request.Request(
                    f"{DESK}/api/admin/products",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read())
                products = data.get("products", [])
                slug_to_prefix = {}
                prefix_to_slug = {}
                for p in products:
                    slug = p.get("slug")
                    prefix = p.get("prefix")
                    if slug and prefix:
                        slug_to_prefix[slug] = prefix
                        prefix_to_slug[prefix] = slug
                    for lp in p.get("legacy_prefixes") or []:
                        prefix_to_slug[lp] = slug
                self._json(200, {
                    "ok": True,
                    "slug_to_prefix": slug_to_prefix,
                    "prefix_to_slug": prefix_to_slug,
                })
            except Exception as e:
                self._json(502, {"error": str(e)})
            return

        # LIVE-C2: poll cursor feed (same-origin) — never cache (pc-392 cinema)
        if route == "/api/events":
            q = urlsplit(self.path).query
            url = f"{DESK}/api/events"
            if q:
                url = url + "?" + q
            try:
                req = urllib.request.Request(
                    url, headers={"Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as r:
                    raw = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)
            except Exception as e:
                self._json(502, {"error": "events unreachable: %s" % e})
            return

        # LIVE-C2b (pc-283): same-origin SSE proxy to WorkLane transition tape
        if route == "/api/events/stream":
            q = urlsplit(self.path).query
            url = f"{DESK}/api/events/stream"
            if q:
                url = url + "?" + q
            try:
                req = urllib.request.Request(
                    url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=600) as upstream:
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()
                    while True:
                        chunk = upstream.read(256)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except Exception as e:
                if not getattr(self, "wfile", None) or self.wfile.closed:
                    return
                try:
                    self._json(502, {"error": str(e)})
                except Exception:
                    pass
            return

        # LIVE-C (pc-280): same-origin SSE proxy to WorkForce shift-out tail
        if route.startswith("/api/worker-out/") and route.endswith("/stream"):
            name = unquote(route[len("/api/worker-out/"):-len("/stream")].strip("/"))
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name or ""):
                self._json(400, {"error": "bad worker name"})
                return
            url = f"{WORKFORCE}/api/out/{quote(name)}/stream"
            try:
                req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=600) as upstream:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()
                    while True:
                        chunk = upstream.read(256)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except Exception as e:
                # Headers may already be mid-stream; only JSON 502 if still clean
                if not getattr(self, "wfile", None) or self.wfile.closed:
                    return
                try:
                    self._json(502, {"error": str(e)})
                except Exception:
                    pass
            return

        # pc-574: census routes in-process (default). Remote only when
        # SUITE_CITYLENS_REMOTE=1 (then they appear in PROXY below).
        if not _CITYLENS_REMOTE and route == "/api/city":
            light_raw = (qs.get("light") or qs.get("map") or ["0"])[0]
            light = str(light_raw).lower() in ("1", "true", "yes", "map")
            try:
                data = city_payload(light=light)
                # pc-562 / pc-892: dig-in inventory is expensive (disk walk every
                # project). light=1 is Map first paint — never re-enrich.
                # Full city (light=0) may enrich; dig-in prefers /api/hood-inventory.
                # pc-1211: _enrich_with_budget — single background walk, hard deadline,
                # short-TTL cache; never hold a thread for minutes.
                if isinstance(data, dict) and not light:
                    hoods = data.get("neighborhoods") or data.get("folders") or []
                    try:
                        tok = str(
                            _citylens().city_generation_token(CITY_ROOT).get("token") or ""
                        )
                    except Exception:
                        tok = ""
                    enriched = _enrich_with_budget(hoods, tok=tok)
                    if data.get("neighborhoods") is not None:
                        data["neighborhoods"] = enriched
                    if data.get("folders") is not None:
                        data["folders"] = enriched
                self._json(200, data)
            except Exception as e:
                # Structure-first: never hard-blank Map when census raises.
                try:
                    shell = city_structure_from_disk(CITY_ROOT)
                    shell = dict(shell)
                    shell["degraded"] = True
                    shell["error"] = str(e)
                    self._json(200, shell)
                except Exception as e2:
                    self._json(500, {
                        "ok": False,
                        "error": "city census failed: %s" % e2,
                    })
            return

        if not _CITYLENS_REMOTE and route == "/api/attention":
            include = (qs.get("include_snoozed") or ["0"])[0]
            try:
                self._json(
                    200,
                    attention_payload(
                        include_snoozed=str(include).lower()
                        in ("1", "true", "yes")
                    ),
                )
            except Exception as e:
                self._json(200, {
                    "ok": False,
                    "count": 0,
                    "visible_count": 0,
                    "snoozed_count": 0,
                    "items": [],
                    "snoozes": [],
                    "error": str(e),
                })
            return

        if not _CITYLENS_REMOTE and route == "/api/office":
            try:
                self._json(200, office_payload())
            except Exception as e:
                self._json(500, {
                    "ok": False,
                    "error": "office census failed: %s" % e,
                })
            return

        if route == "/api/tp-scene":
            # pc-674: old/cold WorkLane scenes may time out or expose only
            # one store while /api/admin/products knows the full registry.
            # Keep rich scene fields when available; repair store counts from
            # the compatible admin surface when registry/scene diverge.
            try:
                # pc-881: tighter budgets — fail open; soft poll fills badges.
                # Long admin_timeout stacked with cold scene rebuild caused 5–8s Map hangs.
                data = _citylens().desk_scene_compatible(
                    DESK,
                    scene_timeout=1.2,
                    admin_timeout=3.0,
                )
            except Exception as e:
                data = {"ok": False, "stores": [], "error": str(e)}
            self._json(200 if data.get("ok") else 502, data)
            return

        if route in PROXY:
            upstream = PROXY[route]
            # Host-debug remote citylens light query (SUITE_CITYLENS_REMOTE).
            if route == "/api/city":
                light_raw = (qs.get("light") or qs.get("map") or ["0"])[0]
                if str(light_raw).lower() in ("1", "true", "yes", "map"):
                    upstream = f"{CITYLENS}/api/city?light=1"
            # pc-881: /api/people defaults to WorkForce light scene (ms).
            # Full ledger/runtimes scene is opt-in: ?light=0 or ?full=1.
            if route == "/api/people":
                light_raw = (qs.get("light") or ["1"])[0]
                full_raw = (qs.get("full") or ["0"])[0]
                want_full = str(full_raw).lower() in ("1", "true", "yes") or str(
                    light_raw
                ).lower() in ("0", "false", "no")
                if not want_full:
                    upstream = f"{WORKFORCE}/api/scene?light=1"
            body = _cached_fetch(
                upstream,
                timeout=4 if "light=1" in str(upstream) else 8,
            )
            if body is None:
                self._json(502, {"error": "upstream unreachable"})
                return
            # pc-567: stamp soft homeKey / workspace_ops on people scene
            if route == "/api/people":
                try:
                    pdata = json.loads(body.decode("utf-8"))
                    pdata = enrich_people_scene(pdata)
                    body = json.dumps(pdata, separators=(",", ":")).encode(
                        "utf-8"
                    )
                except Exception:
                    pass
            # pc-1093: age-capped stale-on-error must not look fresh
            body = _stamp_degraded_json(body, upstream)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if _cache_entry_is_stale(upstream):
                self.send_header("X-BluePrint-Cache", "stale")
            self.end_headers()
            self.wfile.write(body)
            return

        # Legacy /law/<path> → redirect into in-suite reader (stay in BP).
        # WorkForce opaque stacks: /law/<worker>/stackN → enriched law[N].path
        # (pc-568: bare /law/carl/stack0 used to become path=carl/stack0 404).
        if route.startswith("/law/"):
            rel = unquote(route[len("/law/"):]).strip("/")
            back = (qs.get("back") or [""])[0]
            parts = [p for p in rel.split("/") if p]
            paper_path = rel
            if (
                len(parts) == 2
                and parts[1].lower().startswith("stack")
                and parts[0] not in (".", "..")
            ):
                worker = parts[0]
                idx_s = parts[1][5:]  # after "stack"
                try:
                    idx = int(idx_s) if idx_s != "" else 0
                except ValueError:
                    idx = -1
                try:
                    wf_url = f"{WORKFORCE}/api/worker/{quote(worker)}"
                    with urllib.request.urlopen(wf_url, timeout=5) as r:
                        wdata = json.loads(r.read().decode("utf-8"))
                    wdata = enrich_worker_law(wdata)
                    law = wdata.get("law") if isinstance(wdata, dict) else None
                    if (
                        isinstance(law, list)
                        and 0 <= idx < len(law)
                        and isinstance(law[idx], dict)
                        and law[idx].get("path")
                    ):
                        paper_path = str(law[idx]["path"])
                except Exception:
                    pass
            q = {"path": paper_path}
            if back:
                q["back"] = back
            self._send_redirect("/read?" + urlencode(q))
            return

        # Retired peer / alias pages (before file rewrite)
        if self._redirect_retired_page():
            return
        # pc-1267: /settings?sheet=1 still 302s to Map; plain /settings is a view
        if self._redirect_settings_page():
            return

        self._rewrite_page_route()
        # pc-1020: HTML with derived ?v= before gzip/raw static
        if self._try_send_html_asset_versions():
            return
        # pc-894: gzip map app / CSS / large static before SimpleHTTP raw send
        if self._try_send_gzip_static():
            return
        return super().do_GET()

    def log_message(self, fmt, *args):
        pass

    def log_error(self, fmt, *args):
        # Still emit (timestamped via install_stderr_timestamps) — not silenced.
        try:
            sys.stderr.write("%s - - [%s] %s\n" % (
                self.address_string(),
                self.log_date_time_string(),
                fmt % args,
            ))
        except Exception:
            pass


# pc-1218: thread watchdog — detect wedged/runaway handler threads.
# Warn when >N concurrent handlers or any single handler runs longer than T seconds.
_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT: "dict[int, tuple[float, object]]" = {}  # ident → (monotonic_start, client_address)
_WATCHDOG_THREAD_WARN = 8   # concurrent handler threads before warning
_WATCHDOG_AGE_WARN = 60     # seconds before flagging a single long-running handler
_WATCHDOG_INTERVAL = 30     # how often the watchdog checks


def _watchdog_loop() -> None:
    """Background daemon: log hung or pile-up handler threads (pc-1218)."""
    while True:
        time.sleep(_WATCHDOG_INTERVAL)
        now = time.monotonic()
        with _INFLIGHT_LOCK:
            count = len(_INFLIGHT)
            aged = [
                (tid, now - t0, addr)
                for tid, (t0, addr) in _INFLIGHT.items()
                if now - t0 > _WATCHDOG_AGE_WARN
            ]
        if count > _WATCHDOG_THREAD_WARN:
            sys.stderr.write(
                "WATCHDOG: %d handler threads in-flight (warn at >%d)\n"
                % (count, _WATCHDOG_THREAD_WARN)
            )
        for tid, age, addr in aged:
            sys.stderr.write(
                "WATCHDOG: handler thread %d from %s running %.0fs (warn at >%ds)\n"
                % (tid, addr, age, _WATCHDOG_AGE_WARN)
            )


class SuiteHTTPServer(http.server.ThreadingHTTPServer):
    """pc-1071: suite process must outlive desk/engine restarts.

    * ``daemon_threads`` — hung urllib proxies to a bouncing desk must not
      pin the process at SIGTERM (ExitTimeOut → SIGKILL → multi-minute
      KeepAlive blackout).
    * Quiet client-disconnect ``handle_error`` — default dumps full tracebacks
      for every Map tab close; that filled suite-service.err to 12MiB and made
      real faults unreadable.
    * pc-1218: ``process_request_thread`` registers each handler in ``_INFLIGHT``
      so the watchdog can flag wedged threads without a founder report.
    """

    daemon_threads = True
    # With daemon request threads, do not block server close on stragglers.
    block_on_close = False

    def process_request_thread(self, request, client_address):
        tid = threading.current_thread().ident
        with _INFLIGHT_LOCK:
            _INFLIGHT[tid] = (time.monotonic(), client_address)
        try:
            super().process_request_thread(request, client_address)
        finally:
            with _INFLIGHT_LOCK:
                _INFLIGHT.pop(tid, None)

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if exc is not None and is_client_disconnect(exc):
            try:
                sys.stderr.write(
                    "client disconnect from %s: %s\n"
                    % (client_address, type(exc).__name__)
                )
            except Exception:
                pass
            return
        try:
            sys.stderr.write("-" * 40 + "\n")
            sys.stderr.write(
                "Exception during request from %s\n" % (client_address,)
            )
            traceback.print_exc(file=sys.stderr)
            sys.stderr.write("-" * 40 + "\n")
        except Exception:
            pass
