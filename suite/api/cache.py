"""Process-local short TTL cache for suite upstream proxies (pc-269 / pc-373)."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

# Live deltas ride pulse/SSE. Keep short enough for filed-slip theater.
CACHE_TTL = 5  # seconds
_cache: dict[str, tuple[bytes, float]] = {}
# Single-flight: parallel map-bootstrap / tabs must not stampede citylens.
_inflight: dict[str, threading.Condition] = {}
_inflight_lock = threading.Lock()


def cached_fetch(url: str, timeout: float = 5) -> Optional[bytes]:
    """Short-TTL GET proxy with single-flight coalesce. Returns raw bytes or None."""
    now = time.monotonic()
    hit = _cache.get(url)
    if hit is not None:
        raw, ts = hit
        if now - ts < CACHE_TTL:
            return raw

    leader = False
    with _inflight_lock:
        hit = _cache.get(url)
        if hit is not None and (time.monotonic() - hit[1]) < CACHE_TTL:
            return hit[0]
        cond = _inflight.get(url)
        if cond is None:
            cond = threading.Condition()
            _inflight[url] = cond
            leader = True
        else:
            cond = _inflight[url]

    if not leader:
        # pc-901: wait at least for the leader's fetch budget (was timeout+1,
        # but followers returned None while leader still ran → empty bootstrap
        # and Map "Fast path" after 4s aborts).
        with cond:
            cond.wait(timeout=max(float(timeout) * 2.0, 8.0))
        hit = _cache.get(url)
        if hit is not None and (time.monotonic() - hit[1]) < CACHE_TTL:
            return hit[0]
        return None

    raw: Optional[bytes] = None
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        _cache[url] = (raw, time.monotonic())
        return raw
    except Exception:
        return None
    finally:
        with _inflight_lock:
            done = _inflight.pop(url, None)
        if done is not None:
            with done:
                done.notify_all()


def cached_json(url: str, timeout: float = 5) -> Any:
    raw = cached_fetch(url, timeout=timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return None


def fetch_json_raw(url: str, timeout: float = 3) -> Any:
    """Uncached JSON fetch for pulse (must be fresh every poll)."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except Exception:
        return None


def invalidate(*urls: str) -> None:
    for u in urls:
        if u:
            _cache.pop(u, None)


def clear() -> None:
    _cache.clear()
