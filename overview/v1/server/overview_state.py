"""Local-only truth stubs for the Overview V1 Mission Control glass.

Contract (from ``docs/specs/OVERVIEW_INTENT.md`` §V1 must-have chrome +
``OVERVIEW_MC_EXT.md`` §APIs extended):

- ``GET /api/overview/agents``  →
    ``{"agents":[...], "cloud_builders":[...], "remote_builders":[...]}``
- ``GET /api/overview/jobs``    →
    ``{"jobs":[...], "buckets":{"waiting":n,"ready":n,"blocked":n}}``
- ``GET /api/overview/pulse``   →
    ``{"heartbeats":[...], "cellar_tip": "<brew face>", "last_at": null|str,
       "ticks":[...]}``
- ``GET /api/overview/project`` → project card or ``{}``
- ``GET /api/overview/charter`` → charter drawer or ``{}``

The default state on this desk is **empty** — honest-empty is a first-class
PASS state per INTENT §Dogfood note. A running-process view / local job
store / local event tick will replace these stubs when the BluePrint pip
package vendors this module; until then the desk paints ``No agents`` /
``No open jobs`` / silent pulse.

Fixture loading is provided **only** for tests and demo — never invent
fake busy state in default serve. INTENT invariant: ``demo-worker`` alone
does not count as employed pulse; a fixture with only ``demo-worker`` on
the registry and no real employed event still paints ``No agents``.

Never-lie contract (MC_EXT):

- Cloud / remote builders are outbound **links**, never painted as local
  agents. They come back in their own arrays; the client renders them as
  link chips, never as rows in the agent roster.
- Cellar tip is the brew app version (e.g. ``blueprint 0.1.50_9``), not a
  private ProtocolCity SHA. It is resolved from the local brew Cellar by
  ``detect_cellar_tip()`` and injected by ``serve.py``; when brew is
  missing or fails we fall back to ``DEFAULT_CELLAR_TIP`` rather than
  invent a version.
- Heartbeat rows carry a state string; a missing heartbeat paints muted
  (``off``), never working green.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
from pathlib import Path


_AGENT_STATES = frozenset({"idle", "working", "error", "off"})
_HEARTBEAT_STATES = frozenset(
    {"watching", "idle", "connected", "scanning", "paused", "off", "error"}
)
_DEMO_WORKER = "demo-worker"

# Named local heartbeats — the pulse tile paints these five, in this order.
# A heartbeat missing from state paints as ``off`` (muted), not working green.
HEARTBEAT_NAMES = ("FS Watch", "Builder", "Cellar", "Index", "Sync")

DEFAULT_CELLAR_TIP = "blueprint 0.1.50_9"

# Brew face detection. ``brew list --versions blueprint`` is the stable
# query — it prints ``blueprint <version> [<version> …]`` and exits
# non-zero when the formula is not installed. Short timeout, failures
# swallowed: the desk never blocks on brew and never invents a version.
_CELLAR_FORMULA = "blueprint"
_BREW_TIMEOUT_S = 2.0
_VERSION_RE = re.compile(r"^[0-9][0-9A-Za-z._+-]*$")


def _brew_blueprint_version() -> str | None:
    """Installed brew version of the ``blueprint`` formula, or ``None``."""
    try:
        proc = subprocess.run(
            ["brew", "list", "--versions", _CELLAR_FORMULA],
            capture_output=True,
            text=True,
            timeout=_BREW_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    parts = (proc.stdout or "").split()
    # ``blueprint 0.1.50_8 0.1.50_9`` — brew lists oldest keg first, so
    # the tip is last. Anything that is not a version string (a SHA, a
    # path, an error line) is refused rather than painted.
    if len(parts) < 2 or parts[0] != _CELLAR_FORMULA:
        return None
    version = parts[-1]
    return version if _VERSION_RE.match(version) else None


def detect_cellar_tip() -> str:
    """Brew face for the pulse tile — detected, else ``DEFAULT_CELLAR_TIP``."""
    version = _brew_blueprint_version()
    return f"{_CELLAR_FORMULA} {version}" if version else DEFAULT_CELLAR_TIP



def empty_state() -> dict:
    """The default local-only truth for this desk on a cold boot."""
    return {
        "agents": [],
        "cloud_builders": [],
        "remote_builders": [],
        "jobs": [],
        "buckets": {"waiting": 0, "ready": 0, "blocked": 0},
        "pulse": {"heartbeats": [], "ticks": [], "last_at": None},
        "cellar_tip": DEFAULT_CELLAR_TIP,
        "project": {},
        "charter": {},
    }


def _sanitize_agent(row: dict) -> dict:
    name = str(row.get("name", "")).strip()
    state = str(row.get("state", "idle")).strip().lower()
    if state not in _AGENT_STATES:
        state = "idle"
    return {"name": name, "state": state}


def _sanitize_link(row: dict) -> dict:
    """Cloud / remote builder link. Outbound only — never a local agent row."""
    name = str(row.get("name", "")).strip()
    url = str(row.get("url", "")).strip()
    return {"name": name, "url": url}


def _sanitize_job(row: dict) -> dict:
    name = str(row.get("name", "")).strip()
    state = str(row.get("state", "open")).strip().lower()
    return {"name": name, "state": state}


def _sanitize_buckets(raw: dict) -> dict:
    def _n(key: str) -> int:
        v = raw.get(key, 0)
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return 0

    return {"waiting": _n("waiting"), "ready": _n("ready"), "blocked": _n("blocked")}


def _sanitize_tick(row: dict) -> dict:
    at = row.get("at")
    label = str(row.get("label", "")).strip()
    return {"at": at, "label": label}


def _sanitize_heartbeat(row: dict) -> dict:
    name = str(row.get("name", "")).strip()
    state = str(row.get("state", "off")).strip().lower()
    if state not in _HEARTBEAT_STATES:
        state = "off"
    last_at = row.get("last_at")
    if last_at is not None:
        last_at = str(last_at)
    return {"name": name, "state": state, "last_at": last_at}


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


def _sanitize_project(raw: dict) -> dict:
    """Project card. Path voice is always **on this desk** — never `workspace`,
    never a cloud path."""
    if not isinstance(raw, dict) or not raw:
        return {}
    title = str(raw.get("title", "")).strip()
    slug = str(raw.get("project", "")).strip()
    # ``path_hint`` is copy — enforce the honesty string, no path theater.
    path_hint = str(raw.get("path_hint", "on this desk")).strip() or "on this desk"
    excerpt = str(raw.get("charter_excerpt", "")).strip()
    raw_badges = raw.get("badges") or {}
    badges = {
        "local_write": bool(raw_badges.get("local_write", False)),
        # Consume ≠ MANAGED — the badge is lit only when the desk holds a
        # live consume lease. Fixture booleans are the truth source here.
        "consume": bool(raw_badges.get("consume", False)),
        "upstream": bool(raw_badges.get("upstream", False)),
        "local_only": bool(raw_badges.get("local_only", False)),
    }
    return {
        "title": title,
        "project": slug,
        "path_hint": path_hint,
        "badges": badges,
        "charter_excerpt": excerpt,
    }


def _charter_md_to_sections(text: str) -> tuple[str, list[dict]]:
    """Best-effort CHARTER.md → excerpt + sections. Local paper only."""
    lines = text.replace("\r\n", "\n").split("\n")
    excerpt_parts: list[str] = []
    sections: list[dict] = []
    current: dict | None = None
    for line in lines:
        if line.startswith("## "):
            if current and (current.get("heading") or current.get("body")):
                sections.append(current)
            current = {"heading": line[3:].strip(), "body": ""}
            continue
        if line.startswith("# "):
            continue
        if current is None:
            stripped = line.strip()
            if stripped and not stripped.startswith("**Status"):
                excerpt_parts.append(stripped)
            continue
        if line.strip():
            body = current.get("body") or ""
            current["body"] = f"{body} {line.strip()}".strip() if body else line.strip()
    if current and (current.get("heading") or current.get("body")):
        sections.append(current)
    excerpt = " ".join(excerpt_parts).strip()
    if len(excerpt) > 280:
        excerpt = excerpt[:277].rstrip() + "…"
    return excerpt, sections[:8]


def project_desk_papers(binder: Path | None, cellar_tip: str = "") -> tuple[dict, dict]:
    """CHARTER.md / AGENTS.md on this desk → project card + charter drawer.

    Missing papers → empty ``{}`` (honest). Never invent a cloud path.
    """
    if binder is None:
        return {}, {}
    binder = Path(binder).expanduser().resolve()
    if not binder.is_dir():
        return {}, {}
    tip = (cellar_tip or "").strip() or DEFAULT_CELLAR_TIP
    charter_path = binder / "CHARTER.md"
    agents_md = binder / "AGENTS.md"
    if not charter_path.is_file() and not agents_md.is_file():
        return {}, {}
    excerpt = ""
    sections: list[dict] = []
    if charter_path.is_file():
        try:
            excerpt, sections = _charter_md_to_sections(
                charter_path.read_text(encoding="utf-8")
            )
        except OSError:
            excerpt, sections = "", []
    has_git = (binder / ".git").exists()
    project = _sanitize_project(
        {
            "title": binder.name,
            "project": binder.name,
            "path_hint": "on this desk",
            "badges": {
                "local_write": True,
                "consume": False,
                "upstream": has_git,
                "local_only": True,
            },
            "charter_excerpt": excerpt,
        }
    )
    charter: dict = {}
    if sections or excerpt:
        charter = _sanitize_charter(
            {
                "title": "Charter for Local Desk",
                "sections": sections
                or [{"heading": "Charter", "body": excerpt}],
                "footer": (
                    f"Cellar app tip {tip} — not private Protocol City install"
                ),
            }
        )
    return project, charter


def next_action_from_state(state: dict | None, binder: Path | None = None) -> dict:
    """One verb + one object. Hidden when nothing real is on this desk."""
    st = state if state is not None else empty_state()
    for job in st.get("jobs") or []:
        if isinstance(job, dict) and job.get("state") == "ready" and job.get("name"):
            return {"verb": "Open", "object": str(job["name"]), "href": ""}
    if binder is not None:
        agents_md = Path(binder).expanduser().resolve() / "AGENTS.md"
        if agents_md.is_file():
            return {
                "verb": "Read",
                "object": "AGENTS.md",
                "href": "/map?md=AGENTS.md",
            }
    if st.get("charter"):
        return {"verb": "Open", "object": "Charter", "href": "#charter"}
    if st.get("project"):
        return {"verb": "Open", "object": "Map", "href": "/map"}
    return {}


def _sanitize_charter(raw: dict) -> dict:
    """Charter drawer. Operator voice OK — stranger / marketing voice is not."""
    if not isinstance(raw, dict) or not raw:
        return {}
    title = str(raw.get("title", "")).strip()
    footer = str(raw.get("footer", "")).strip()
    sections = []
    for section in raw.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = str(section.get("heading", "")).strip()
        body = str(section.get("body", "")).strip()
        if heading or body:
            sections.append({"heading": heading, "body": body})
    return {"title": title, "sections": sections, "footer": footer}


def load_from_fixture(fixture_path: Path) -> dict:
    """Read a JSON fixture that mirrors the wire shape of the V1 APIs."""
    fixture_path = Path(fixture_path).expanduser().resolve()
    if not fixture_path.is_file():
        raise FileNotFoundError(f"fixture not found: {fixture_path}")
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"fixture must be a JSON object: {fixture_path}")

    raw_agents = raw.get("agents") or []
    agents = [_sanitize_agent(row) for row in raw_agents if isinstance(row, dict)]

    raw_cloud = raw.get("cloud_builders") or []
    cloud_builders = [_sanitize_link(row) for row in raw_cloud if isinstance(row, dict)]

    raw_remote = raw.get("remote_builders") or []
    remote_builders = [
        _sanitize_link(row) for row in raw_remote if isinstance(row, dict)
    ]

    raw_jobs = raw.get("jobs") or []
    jobs = [_sanitize_job(row) for row in raw_jobs if isinstance(row, dict)]
    buckets = _sanitize_buckets(raw.get("buckets") or {})

    raw_pulse = raw.get("pulse") or {}
    ticks = [
        _sanitize_tick(row)
        for row in (raw_pulse.get("ticks") or [])
        if isinstance(row, dict)
    ]
    heartbeats = [
        _sanitize_heartbeat(row)
        for row in (raw_pulse.get("heartbeats") or [])
        if isinstance(row, dict)
    ]
    last_at = raw_pulse.get("last_at")

    # demo-worker alone must still paint `No agents` — Agents tile empties
    # the wire payload unless a real working agent is present.
    if not _agents_are_employed(agents):
        agents = [row for row in agents if row.get("name") != _DEMO_WORKER]

    return {
        "agents": agents,
        "cloud_builders": cloud_builders,
        "remote_builders": remote_builders,
        "jobs": jobs,
        "buckets": buckets,
        "pulse": {"heartbeats": heartbeats, "ticks": ticks, "last_at": last_at},
        "cellar_tip": str(raw.get("cellar_tip") or DEFAULT_CELLAR_TIP),
        "project": _sanitize_project(raw.get("project") or {}),
        "charter": _sanitize_charter(raw.get("charter") or {}),
    }


def _normalize_heartbeats(rows: list[dict]) -> list[dict]:
    """Return one row per named local heartbeat, in HEARTBEAT_NAMES order.

    Missing heartbeats paint as ``off`` (muted) — never working green.
    A fixture may name additional heartbeats; those append after the named
    five in the order the fixture provided them, but the five named local
    heartbeats always render.
    """
    by_name = {row.get("name"): row for row in rows if isinstance(row, dict)}
    out: list[dict] = []
    for name in HEARTBEAT_NAMES:
        row = by_name.get(name)
        if row is None:
            out.append({"name": name, "state": "off", "last_at": None})
        else:
            out.append(_sanitize_heartbeat(row))
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if name in HEARTBEAT_NAMES:
            continue
        out.append(_sanitize_heartbeat(row))
    return out


def load_agents(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/agents``.

    Cloud / remote builders come back in their own arrays — the client
    renders them as outbound links, never as employed local agent rows.
    """
    st = state if state is not None else empty_state()
    return {
        "agents": list(st.get("agents") or []),
        "cloud_builders": list(st.get("cloud_builders") or []),
        "remote_builders": list(st.get("remote_builders") or []),
    }


def load_jobs(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/jobs``.

    ``buckets`` carries Waiting · Ready · Blocked counts (zeros PASS).
    """
    st = state if state is not None else empty_state()
    buckets = st.get("buckets") or {}
    return {
        "jobs": list(st.get("jobs") or []),
        "buckets": _sanitize_buckets(buckets),
    }


def load_pulse(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/pulse``.

    Returns named local heartbeats (missing ones as ``off``), the Cellar
    tip (brew face — not a private ProtocolCity SHA), and last-tick.
    """
    st = state if state is not None else empty_state()
    pulse = st.get("pulse") or {}
    heartbeats = _normalize_heartbeats(pulse.get("heartbeats") or [])
    return {
        "heartbeats": heartbeats,
        "ticks": list(pulse.get("ticks") or []),
        "last_at": pulse.get("last_at"),
        "cellar_tip": str(st.get("cellar_tip") or DEFAULT_CELLAR_TIP),
    }


def load_project(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/project``.

    Empty ``{}`` when nothing selected — honest default is no card.
    """
    st = state if state is not None else empty_state()
    project = st.get("project") or {}
    if not project:
        return {}
    return _sanitize_project(project)


def load_charter(state: dict | None = None) -> dict:
    """Body for ``GET /api/overview/charter``.

    Empty ``{}`` when the drawer has no content — honest default is closed.
    """
    st = state if state is not None else empty_state()
    charter = st.get("charter") or {}
    if not charter:
        return {}
    return _sanitize_charter(charter)


# ── Binder local-truth loaders ──────────────────────────────────────────────
# When the desk server is launched with ``--binder DIR``, we look for a
# ``.blueprint/`` marker directory and read a small set of JSON files off it:
#
#   <binder>/.blueprint/overview.json  → same wire shape as the fixtures
#   <binder>/.blueprint/calendar.json  → { "events": [...], "range": "..." }
#
# Every file is optional. Missing file = honest empty (`No agents` / `No
# events`). This is deliberately the smallest local-truth surface that can
# feed the four-lens shell without inventing state.



# Sentinel for BinderOverview first-read (distinct from absent-file None stamp).
_UNREAD = object()

# Phase-B: when overview.json is absent, project WorkForce roster /
# WorkLane SQLite (optional Desk HTTP) into agents[] / jobs[]+buckets.
# overview.json still wins when present. Missing stores → empty_state.
# See ``server.local_projectors``.


def _apply_projected_slice(projected: dict) -> dict:
    """Merge a projector slice onto empty_state with the same sanitizers
    fixtures use — including the demo-worker-alone → No agents filter.
    """
    agents_raw = projected.get("agents") or []
    agents = [_sanitize_agent(row) for row in agents_raw if isinstance(row, dict)]
    jobs_raw = projected.get("jobs") or []
    jobs = [_sanitize_job(row) for row in jobs_raw if isinstance(row, dict)]
    buckets = _sanitize_buckets(projected.get("buckets") or {})
    if not _agents_are_employed(agents):
        agents = [row for row in agents if row.get("name") != _DEMO_WORKER]
    state = empty_state()
    state["agents"] = agents
    state["jobs"] = jobs
    state["buckets"] = buckets
    return state


class BinderOverview:
    """mtime-aware binder truth for Overview Agents / Jobs / Pulse.

    Precedence per request:

    1. ``<binder>/.blueprint/overview.json`` present → live re-read (wins).
    2. Else Phase-B projectors (WorkForce roster + WorkLane stores).
    3. Missing / malformed → ``empty_state()``.

    ``current()`` stats on the hot path and re-parses only when inputs
    change. Thread-safe — the desk runs on a ``ThreadingHTTPServer``.

    ``cellar_tip`` pins the resolved brew face (CLI ``--cellar-tip`` or
    ``detect_cellar_tip()``), so a live re-read never shells out to brew on
    the request path and a binder file can never re-voice the Cellar tip.
    """

    def __init__(self, binder: Path, cellar_tip: str = "") -> None:
        self.binder = Path(binder).expanduser().resolve()
        self.path = self.binder / ".blueprint" / "overview.json"
        self.cellar_tip = (cellar_tip or "").strip() or DEFAULT_CELLAR_TIP
        self._stamp: object = _UNREAD
        self._state: dict = empty_state()
        self._lock = threading.Lock()

    def _overview_stamp(self) -> tuple | None:
        """overview.json identity — ``None`` when the file is absent."""
        try:
            st = self.path.stat()
        except OSError:
            return None
        return (st.st_mtime_ns, st.st_size, st.st_ino)

    def _stamp_now(self) -> tuple:
        """Combined identity for overview.json **or** projector inputs.

        Always a tuple so an absent overview.json still re-reads when the
        roster / WorkLane DBs change under the binder.
        """
        ov = self._overview_stamp()
        papers = []
        for name in ("CHARTER.md", "AGENTS.md"):
            try:
                st = (self.binder / name).stat()
                papers.append((name, st.st_mtime_ns, st.st_size))
            except OSError:
                papers.append((name, 0, 0))
        if ov is not None:
            return ("overview", ov, tuple(papers))
        # Local import keeps the cold path light when only fixtures are used.
        from server.local_projectors import projector_stamp  # noqa: PLC0415

        return ("projectors", projector_stamp(self.binder), tuple(papers))

    def _read(self, stamp: tuple) -> dict:
        if stamp and stamp[0] == "overview":
            try:
                state = load_from_fixture(self.path)
            except (OSError, ValueError):
                state = empty_state()
        else:
            from server.local_projectors import project_local_overview  # noqa: PLC0415

            try:
                projected = project_local_overview(self.binder)
            except Exception:  # noqa: BLE001 — never 500 the desk on projector bugs
                projected = {}
            state = _apply_projected_slice(projected)
        project, charter = project_desk_papers(self.binder, self.cellar_tip)
        if not state.get("project"):
            state["project"] = project
        if not state.get("charter"):
            state["charter"] = charter
        return state

    def current(self) -> dict:
        """State for this request — re-read only when inputs changed."""
        stamp = self._stamp_now()
        with self._lock:
            if stamp != self._stamp:
                state = self._read(stamp)
                state["cellar_tip"] = self.cellar_tip
                self._state = state
                self._stamp = stamp
            return self._state


def load_from_binder(binder: Path) -> dict:
    """Read binder local truth (overview.json wins; else Phase-B projectors).

    Returns the full state (same shape as ``load_from_fixture``). Missing
    stores → ``empty_state()`` — honest-empty is a first-class PASS.
    Boot-time read; the live serve path uses ``BinderOverview`` so a binder
    edit lands on the next GET.
    """
    binder = Path(binder).expanduser().resolve()
    marker = binder / ".blueprint" / "overview.json"
    if marker.is_file():
        try:
            state = load_from_fixture(marker)
        except (OSError, ValueError):
            state = empty_state()
    else:
        from server.local_projectors import project_local_overview  # noqa: PLC0415

        try:
            state = _apply_projected_slice(project_local_overview(binder))
        except Exception:  # noqa: BLE001
            state = empty_state()
    project, charter = project_desk_papers(binder)
    if not state.get("project"):
        state["project"] = project
    if not state.get("charter"):
        state["charter"] = charter
    return state


def _sanitize_event(row: dict) -> dict:
    """One calendar event row. Source ∈ routine·WO·manual; state ∈
    scheduled·due·done — anything else silently drops back to `manual` /
    `scheduled`."""
    title = str(row.get("title", "")).strip()
    at = row.get("at")
    if at is not None:
        at = str(at)
    source = str(row.get("source", "manual")).strip()
    if source not in ("routine", "WO", "manual"):
        source = "manual"
    state = str(row.get("state", "scheduled")).strip().lower()
    if state not in ("scheduled", "due", "done"):
        state = "scheduled"
    notes = str(row.get("notes", "")).strip()
    return {
        "title": title,
        "at": at,
        "source": source,
        "state": state,
        "notes": notes,
    }


def load_events(binder: Path | None = None) -> dict:
    """Body for ``GET /api/calendar/events``.

    Reads ``<binder>/.blueprint/calendar.json`` if present. Missing file →
    ``{"events": [], "range": ""}`` (honest empty — `No events` copy).
    """
    if binder is None:
        return {"events": [], "range": ""}
    binder = Path(binder).expanduser().resolve()
    marker = binder / ".blueprint" / "calendar.json"
    if not marker.is_file():
        return {"events": [], "range": ""}
    try:
        raw = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"events": [], "range": ""}
    events = [
        _sanitize_event(row)
        for row in (raw.get("events") or [])
        if isinstance(row, dict)
    ]
    range_str = str(raw.get("range") or "").strip()
    return {"events": events, "range": range_str}


def load_desk(binder: Path | None = None) -> dict:
    """Body for ``GET /api/settings/desk``.

    Reports the binder path (**on this desk** when no binder was pinned) and
    the local desk label. Never says `workspace`.
    """
    if binder is None:
        return {"binder_path": "on this desk", "desk_label": "Local desk"}
    binder = Path(binder).expanduser().resolve()
    return {"binder_path": str(binder), "desk_label": "Local desk"}
