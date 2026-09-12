"""ntfy.sh push helper for Blueprint city alerts (pc-712).

Config precedence — workspace-scoped wins:
  {ws}/.protocolcity/ntfy.json > ~/.protocolcity/ntfy.json

Schema:
  {"enabled": true, "topic": "my-city-abc123", "server": "https://ntfy.sh"}

Kill switch: BLUEPRINT_NTFY_DISABLE=1 forces dry-run.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

_DISABLE_ENV = "BLUEPRINT_NTFY_DISABLE"
_DEFAULT_SERVER = "https://ntfy.sh"


def _find_config(name: str, city_root: Optional[Path]) -> Optional[Path]:
    if city_root is not None:
        p = Path(city_root).expanduser().resolve() / ".protocolcity" / name
        if p.is_file():
            return p
    p = Path.home() / ".protocolcity" / name
    return p if p.is_file() else None


def load_ntfy_config(city_root: Optional[Path] = None) -> dict:
    """Load ntfy config. Returns {} when not found or unparseable."""
    p = _find_config("ntfy.json", city_root)
    if p is None:
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def push(
    title: str,
    body: str,
    *,
    city_root: Optional[Path] = None,
    topic_override: Optional[str] = None,
) -> dict:
    """Push a notification to ntfy.

    Returns {ok, dry_run, status?, error?}.
    Dry-runs silently when config is absent, disabled, or env kill switch set.
    """
    if os.environ.get(_DISABLE_ENV, "").lower() in ("1", "true", "yes"):
        return {"ok": True, "dry_run": True, "reason": "env_disable"}

    cfg = load_ntfy_config(city_root)
    if not cfg:
        return {"ok": True, "dry_run": True, "reason": "no_config"}
    if not cfg.get("enabled", True):
        return {"ok": True, "dry_run": True, "reason": "disabled"}

    topic = (topic_override or cfg.get("topic") or "").strip()
    if not topic:
        return {"ok": True, "dry_run": True, "reason": "no_topic"}

    server = (cfg.get("server") or _DEFAULT_SERVER).rstrip("/")
    url = "%s/%s" % (server, topic)

    try:
        req = urllib.request.Request(
            url,
            data=body.encode("utf-8"),
            method="POST",
            headers={
                "Title": title[:250],
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"ok": True, "dry_run": False, "status": resp.status}
    except Exception as e:
        return {"ok": False, "dry_run": False, "error": str(e)}
