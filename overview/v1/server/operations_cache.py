"""Single-flight /api/operations cache (pc-1554).

Concurrent browser tabs and the change-feed refresh herd share one snapshot
build. A slow WorkLane/WorkForce probe must not start a second full
projection on the next client, and a waiter must not sit past the
browser's 10s abort.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

SNAPSHOT_TTL_SECS = 2.0
SNAPSHOT_WAIT_SECS = 8.0


class OperationsCache:
    """One in-flight build per workspace; waiters share that result."""

    def __init__(
        self,
        builder: Callable[[], dict],
        ttl: float = SNAPSHOT_TTL_SECS,
        wait: float = SNAPSHOT_WAIT_SECS,
    ) -> None:
        self._builder = builder
        self._ttl = ttl
        self._wait = wait
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._ready.set()
        self._inflight = False
        self._value: dict | None = None
        self._error: BaseException | None = None
        self._built_at = 0.0

    def get(self) -> dict:
        with self._lock:
            now = time.monotonic()
            if (
                self._value is not None
                and not self._inflight
                and (now - self._built_at) < self._ttl
            ):
                return self._value
            if self._inflight:
                wait_for = self._ready
            else:
                self._inflight = True
                self._ready = threading.Event()
                wait_for = None
        if wait_for is not None:
            finished = wait_for.wait(timeout=self._wait)
            with self._lock:
                if self._value is not None:
                    return self._value
                if finished and self._error is not None:
                    raise self._error
            raise TimeoutError('Operations snapshot did not finish in time.')
        try:
            value = self._builder()
            with self._lock:
                self._value = value
                self._error = None
                self._built_at = time.monotonic()
            return value
        except Exception as exc:
            with self._lock:
                self._error = exc
            if self._value is not None:
                return self._value
            raise
        finally:
            with self._lock:
                self._inflight = False
                self._ready.set()


_caches: dict[str, OperationsCache] = {}
_caches_lock = threading.Lock()


def cache_key(binder) -> str:
    if binder is None:
        return ''
    try:
        return str(Path(binder).resolve())
    except OSError:
        return str(binder)


def reset_operations_cache() -> None:
    with _caches_lock:
        _caches.clear()


def cached_operations_snapshot(binder, builder=None, **kwargs) -> dict:
    from .operations import operations_snapshot

    key = cache_key(binder)
    build = builder or (lambda: operations_snapshot(binder))
    with _caches_lock:
        cache = _caches.get(key)
        if cache is None:
            cache = OperationsCache(build, **kwargs)
            _caches[key] = cache
    return cache.get()
