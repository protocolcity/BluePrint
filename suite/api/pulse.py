"""Generation-token compose for SuitePulse /api/pulse (pc-278 / pc-373).

pc-574: city token is local library (no :8796). Tickets/people still hit
WorkLane / WorkForce engines.
"""

from __future__ import annotations

import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
from urllib.parse import urlencode

from . import cache as api_cache


def build_pulse(
    citylens: str,
    desk: str,
    workforce: str,
    scope: str = "all",
    product: str = "",
    *,
    city_token_fn: Optional[Callable[[], dict]] = None,
) -> dict[str, Any]:
    """Compose scoped generation tokens from suite engines.

    Tokens only — no scene bodies. Missing upstreams degrade to token=None.

    ``city_token_fn`` (pc-574): when set, city scope uses in-process
    ``protocolcity.citylens.city_generation_token`` (or suite wrapper) and
    never HTTP to :8796. ``citylens`` URL is unused for city when fn is set.
    """
    keys = ("city", "tickets", "people") if scope == "all" else (scope,)

    def _city_local():
        if city_token_fn is None:
            return None
        try:
            data = city_token_fn()
        except Exception:
            return {"ok": False, "token": None}
        if not data or not isinstance(data, dict):
            return {"ok": False, "token": None}
        return {
            "ok": bool(data.get("ok", True)),
            "token": data.get("token"),
            "ts": data.get("ts") or "",
            "in_flight": data.get("in_flight"),
        }

    http_jobs: dict[str, str] = {}
    if "tickets" in keys:
        url = f"{desk}/api/generation"
        if product:
            url += "?" + urlencode({"project": product})
        http_jobs["tickets"] = url
    if "people" in keys:
        http_jobs["people"] = f"{workforce}/api/generation"
    # City: prefer local library; fall back to HTTP only when no fn (host debug)
    if "city" in keys and city_token_fn is None:
        http_jobs["city"] = f"{citylens}/api/generation"

    def _one_http(item):
        key, url = item
        data = api_cache.fetch_json_raw(url, timeout=2)
        if not data or not isinstance(data, dict):
            return key, {"ok": False, "token": None}
        return key, {
            "ok": bool(data.get("ok", True)),
            "token": data.get("token"),
            "ts": data.get("ts") or "",
            "in_flight": data.get("in_flight"),
        }

    sources: dict[str, Any] = {}
    if "city" in keys and city_token_fn is not None:
        sources["city"] = _city_local()

    if http_jobs:
        with ThreadPoolExecutor(max_workers=max(len(http_jobs), 1)) as ex:
            results = list(ex.map(_one_http, http_jobs.items()))
        for k, v in results:
            sources[k] = v

    for k in keys:
        sources.setdefault(k, {"ok": False, "token": None})

    if product and "tickets" in sources:
        sources["tickets"]["product"] = product
    parts = []
    for k in keys:
        tok = (sources.get(k) or {}).get("token")
        parts.append("%s=%s" % (k, tok if tok is not None else "?"))
    return {
        "ok": True,
        "token": "|".join(parts),
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "sources": sources,
    }
