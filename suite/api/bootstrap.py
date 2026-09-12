"""Parallel first-paint bootstraps for Desk + Map (pc-267 / pc-375 / pc-373).

pc-574: city (+ optional attention) come from in-process citylens library
callables — not HTTP to :8796. WorkForce / Desk still fan via URL.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from . import cache as api_cache

# Map first paint must not wait forever when engines hang (founder 2026-07-25).
# Prefer short timeouts + empty defaults over a blank Map; soft poll fills in.
# people uses light scene (skip heavy ledger/runtimes).
# WorkLane /api/scene can CPU-spin under load — keep optional and tight.
BOOTSTRAP_UPSTREAMS = (
    ("city", "citylens", "/api/city", 6),
    ("attention", "citylens", "/api/you-attention", 2),
    ("people", "workforce", "/api/scene?light=1", 3),
    ("tpScene", "desk", "/api/scene", 2),
)

# Core first paint: city light + people. Attention is fanned via attention_fn
# in parallel when set (pc-834) — same wall budget as city, not a second hop.
# light=1 skips founder brief. Hung desk must not freeze the skeleton:
# attention_fn fails open to empty items.
MAP_CORE = (
    ("city", "citylens", "/api/city?light=1", 2.5),
    ("people", "workforce", "/api/scene?light=1", 2.0),
)
# Attention HTTP fallback only when attention_fn is None (remote citylens).
# Tight timeout — soft poll still refreshes; first paint prefers real items.
# Same budget applies to in-process attention_fn (pc-1001): do not hardcode
# a longer join — a slow Desk attention feed must fail open, not hold Map.
MAP_ATTENTION = (
    ("attention", "citylens", "/api/you-attention", 2.0),
)
MAP_ATTENTION_TIMEOUT = float(MAP_ATTENTION[0][3])
# WorkLane scene (store badges): short optional — fail open to {} so a hung
# desk never freezes first paint. Client also fetches /api/tp-scene on poll.
MAP_OPTIONAL = (
    ("tpScene", "desk", "/api/scene", 1.2),
)

BOOTSTRAP_DEFAULTS = {
    "city": None,
    "attention": {"items": []},
    "people": {},
    "tpScene": {},
}


def _base_url(kind: str, citylens: str, workforce: str, desk: str) -> str:
    if kind == "citylens":
        return citylens
    if kind == "workforce":
        return workforce
    return desk


def _fan(
    jobs: list,
    citylens: str,
    workforce: str,
    desk: str,
    fetch: Callable[..., Any],
) -> dict[str, Any]:
    resolved = []
    for key, kind, path, timeout in jobs:
        url = _base_url(kind, citylens, workforce, desk) + path
        resolved.append((key, url, timeout))

    def _one(job):
        key, url, timeout = job
        return key, fetch(url, timeout=timeout)

    out: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max(len(resolved), 1)) as ex:
        futs = {ex.submit(_one, j): j[0] for j in resolved}
        for fut in as_completed(futs):
            try:
                key, val = fut.result()
            except Exception:
                key, val = futs[fut], None
            out[key] = val if val is not None else BOOTSTRAP_DEFAULTS.get(key)
    for key, _, _, _ in jobs:
        out.setdefault(key, BOOTSTRAP_DEFAULTS.get(key))
    return out


def _safe_call(fn: Callable[[], Any], default: Any) -> Any:
    try:
        val = fn()
    except Exception:
        return default
    return val if val is not None else default


def desk_bootstrap(
    citylens: str,
    workforce: str,
    desk: str,
    cached_json: Optional[Callable[..., Any]] = None,
    *,
    city_fn: Optional[Callable[[], Any]] = None,
    attention_fn: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    """Fan out upstream calls in parallel; return merged dict.

    When ``city_fn`` / ``attention_fn`` are set (pc-574), those keys are
    filled in-process and never hit citylens HTTP.
    """
    fetch = cached_json or api_cache.cached_json
    jobs = []
    for key, kind, path, timeout in BOOTSTRAP_UPSTREAMS:
        if key == "city" and city_fn is not None:
            continue
        if key == "attention" and attention_fn is not None:
            continue
        url = _base_url(kind, citylens, workforce, desk) + path
        jobs.append((key, url, timeout))

    def _one(job):
        key, url, timeout = job
        return key, fetch(url, timeout=timeout)

    out: dict[str, Any] = {}
    n_workers = max(len(jobs) + 2, 1)
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        http_futs = {ex.submit(_one, j): j[0] for j in jobs}
        local_futs = {}
        if city_fn is not None:
            local_futs[ex.submit(_safe_call, city_fn, BOOTSTRAP_DEFAULTS["city"])] = (
                "city"
            )
        if attention_fn is not None:
            local_futs[
                ex.submit(
                    _safe_call, attention_fn, BOOTSTRAP_DEFAULTS["attention"]
                )
            ] = "attention"
        for fut in as_completed(list(http_futs.keys()) + list(local_futs.keys())):
            if fut in local_futs:
                key = local_futs[fut]
                try:
                    out[key] = fut.result()
                except Exception:
                    out[key] = BOOTSTRAP_DEFAULTS.get(key)
            else:
                try:
                    key, val = fut.result()
                except Exception:
                    key, val = http_futs[fut], None
                out[key] = val if val is not None else BOOTSTRAP_DEFAULTS.get(key)

    for key, default in BOOTSTRAP_DEFAULTS.items():
        out.setdefault(key, default)
    return out


def map_bootstrap(
    citylens: str,
    workforce: str,
    desk: str,
    *,
    hidden: Optional[list] = None,
    detect: Optional[dict] = None,
    cached_json: Optional[Callable[..., Any]] = None,
    city_fn: Optional[Callable[[], Any]] = None,
    attention_fn: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    """Map first paint: city + people + attention + optional WorkLane scene.

    Client uses one round-trip. Soft poll still refreshes tape.

    ``city_fn`` (pc-574): in-process light city snapshot — no :8796.
    ``attention_fn`` (pc-834): in-process For You tray — parallel with city so
    gold / Y# / You chip are truthful on first paint (not empty until soft poll).
    """
    fetch = cached_json or api_cache.cached_json
    data: dict[str, Any] = {}

    engine_jobs = []
    if city_fn is None:
        engine_jobs.extend(list(MAP_CORE))
    else:
        for key, kind, path, timeout in MAP_CORE:
            if key != "city":
                engine_jobs.append((key, kind, path, timeout))
    if attention_fn is None:
        engine_jobs.extend(list(MAP_ATTENTION))
    engine_jobs.extend(list(MAP_OPTIONAL))

    local_n = (1 if city_fn is not None else 0) + (
        1 if attention_fn is not None else 0
    )
    # pc-1001: do not use `with ThreadPoolExecutor` — on timeout its
    # shutdown(wait=True) still blocks until slow attention_fn finishes
    # (measured +4s wall even after result timeout). Fail open and return.
    ex = ThreadPoolExecutor(max_workers=max(len(engine_jobs) + local_n, 1))
    try:
        f_city = (
            ex.submit(_safe_call, city_fn, BOOTSTRAP_DEFAULTS["city"])
            if city_fn is not None
            else None
        )
        f_att = (
            ex.submit(
                _safe_call, attention_fn, BOOTSTRAP_DEFAULTS["attention"]
            )
            if attention_fn is not None
            else None
        )
        if engine_jobs:
            data.update(_fan(engine_jobs, citylens, workforce, desk, fetch))
        if f_city is not None:
            try:
                # pc-871: cold city light often 3–5s on dogfood hosts; 4.0s
                # timed out → empty city → Map stuck on "Building workspace map…".
                # Client BOOT_MS is 15s — keep city budget under that, not under 4s.
                data["city"] = f_city.result(timeout=12.0)
            except Exception:
                data["city"] = BOOTSTRAP_DEFAULTS["city"]
        if f_att is not None:
            try:
                # pc-1001: MAP_ATTENTION budget on in-process path too (was 4.0).
                # Slow Desk attention fails open; soft poll hydrates For You.
                data["attention"] = f_att.result(timeout=MAP_ATTENTION_TIMEOUT)
            except Exception:
                data["attention"] = dict(BOOTSTRAP_DEFAULTS["attention"])
    finally:
        # Let a timed-out attention_fn finish in the background; do not
        # hold the HTTP response. cancel_futures is best-effort (running
        # callables are not interruptible).
        try:
            ex.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python <3.9 without cancel_futures
            ex.shutdown(wait=False)

    for k, default in BOOTSTRAP_DEFAULTS.items():
        data.setdefault(k, default)
    # Normalize empty / failed attention to a stable shape.
    att = data.get("attention")
    if not isinstance(att, dict):
        data["attention"] = dict(BOOTSTRAP_DEFAULTS["attention"])
    else:
        att.setdefault("items", [])
    data["hidden"] = {"hidden": list(hidden or [])}
    data["detect"] = detect
    return data
