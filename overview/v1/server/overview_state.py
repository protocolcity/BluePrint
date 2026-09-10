"""Local-only truth stubs for the Overview V1 Mission Control glass.

Contract (from ``docs/specs/OVERVIEW_INTENT.md`` §V1 must-have chrome):

- ``GET /api/overview/agents`` → ``{"agents": [...]}``
- ``GET /api/overview/jobs``   → ``{"jobs": [...]}``
- ``GET /api/overview/pulse``  → ``{"ticks": [...], "last_at": null|str}``

The default state on this desk is **empty** — honest-empty is a first-class
PASS state per INTENT §Dogfood note. A running-process view / local job
store / local event tick will replace these stubs when the BluePrint pip
package vendors this module; until then the desk paints ``No agents`` /
``No open jobs`` / silent pulse.

Fixture loading is provided **only** for tests and demo — never invent
fake busy state in default serve. INTENT invariant: ``demo-worker`` alone
does not count as employed pulse; a fixture with only ``demo-worker`` on
the registry and no real employed event still paints ``No agents``.
"""
from __future__ import annotations

import json
from pathlib import Path


_AGENT_STATES = frozenset({"idle", "working", "error", "off"})
_DEMO_WORKER = "demo-worker"


def empty_state() -> dict:
    """The default local-only truth for this desk on a cold boot."""
    return {
        "agents": [],
        "jobs": [],
        "pulse": {"ticks": [], "last_at": None},
    }


def _sanitize_agent(row: dict) -> dict:
    """Coerce a fixture agent row to the wire shape (name + state dot)."""
    name = str(row.get("name", "")).strip()
    state = str(row.get("state", "idle")).strip().lower()
    if state not in _AGENT_STATES:
        state = "idle"
    return {"name": name, "state": state}


def _sanitize_job(row: dict) -> dict:
    name = str(row.get("name", "")).strip()
    state = str(row.get("state", "open")).strip().lower()
    return {"name": name, "state": state}


def _sanitize_tick(row: dict) -> dict:
    at = row.get("at")
    label = str(row.get("label", "")).strip()
    return {"at": at, "label": label}


def _agents_are_employed(agents: list[dict]) -> bool:
    """Are any of these agents evidence that the desk is working?

    Per INTENT §Dogfood note: a ``demo-worker`` placeholder on the local
    registry with no real employed event is **not** evidence. Only agents
    in the ``working`` state count.
    """
    for row in agents:
        if row.get("name") == _DEMO_WORKER:
            continue
        if row.get("state") == "working":
            return True
    return False


def load_from_fixture(fixture_path: Path) -> dict:
    """Read a JSON fixture that mirrors the wire shape of the V1 APIs.

    Shape::

        {
          "agents": [{"name": "...", "state": "idle|working|error|off"}, ...],
          "jobs":   [{"name": "...", "state": "..."}, ...],
          "pulse":  {"ticks": [{"at": "...", "label": "..."}], "last_at": "..."}
        }

    Only used by the ``--fixture`` flag and by tests. Absent keys default
    to empty; unknown fields are dropped so a fixture cannot smuggle
    surfaces past the V1 lock.
    """
    fixture_path = Path(fixture_path).expanduser().resolve()
    if not fixture_path.is_file():
        raise FileNotFoundError(f"fixture not found: {fixture_path}")
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"fixture must be a JSON object: {fixture_path}")

    raw_agents = raw.get("agents") or []
    agents = [_sanitize_agent(row) for row in raw_agents if isinstance(row, dict)]

    raw_jobs = raw.get("jobs") or []
    jobs = [_sanitize_job(row) for row in raw_jobs if isinstance(row, dict)]

    raw_pulse = raw.get("pulse") or {}
    ticks = [
        _sanitize_tick(row)
        for row in (raw_pulse.get("ticks") or [])
        if isinstance(row, dict)
    ]
    last_at = raw_pulse.get("last_at")

    # demo-worker alone must still paint `No agents` — Agents tile empties
    # the wire payload unless a real working agent is present. Registry
    # placeholders never masquerade as roster.
    if not _agents_are_employed(agents):
        agents = [row for row in agents if row.get("name") != _DEMO_WORKER]

    return {
        "agents": agents,
        "jobs": jobs,
        "pulse": {"ticks": ticks, "last_at": last_at},
    }


def load_agents(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/agents``."""
    st = state if state is not None else empty_state()
    return {"agents": list(st.get("agents") or [])}


def load_jobs(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/jobs``."""
    st = state if state is not None else empty_state()
    return {"jobs": list(st.get("jobs") or [])}


def load_pulse(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/pulse``."""
    st = state if state is not None else empty_state()
    pulse = st.get("pulse") or {}
    return {
        "ticks": list(pulse.get("ticks") or []),
        "last_at": pulse.get("last_at"),
    }
