"""Phase-B local projectors — WorkForce agents + WorkLane jobs under a binder.

When ``--binder DIR`` is set and ``<binder>/.blueprint/overview.json`` is
absent, Overview Agents / Jobs paint from these public local shapes:

Agents (WorkForce roster)::

    <binder>/.protocolcity/workforce/local/roster.json
    <binder>/workforce/local/roster.json          # twin fallback

    Optional runtime twin in the same dir: ``daemon.json`` (``in_flight``).
    Daemon is **not** SoT for which rows exist — only idle/working polish.

Jobs (WorkLane product stores)::

    Prefer Desk HTTP ``http://127.0.0.1:8799/api/admin/products`` (+ tasks)
    with a short timeout; fail → empty, never invent.
    Else read SQLite ``<binder>/worklane/worklane/local/data/<slug>.db``
    table ``tasks`` when present.

Never invent seats or WOs. Missing / malformed → honest empty.
``overview.json`` (when present) still wins at the BinderOverview layer.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# Desk HTTP — short timeout, fail closed.
_DESK_BASE = "http://127.0.0.1:8799"
_DESK_TIMEOUT_S = 0.35

# Open-family statuses we may paint. Terminal statuses are omitted.
_TERMINAL = frozenset({"done", "canceled", "cancelled"})

def _read_json(path: Path) -> Any | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    return raw


def _file_stamp(path: Path) -> tuple | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size, st.st_ino)


def _workforce_local_dirs(binder: Path) -> list[Path]:
    """Candidate WorkForce local dirs under the binder (primary then twin)."""
    return [
        binder / ".protocolcity" / "workforce" / "local",
        binder / "workforce" / "local",
    ]


def resolve_roster_path(binder: Path) -> Path | None:
    for d in _workforce_local_dirs(binder):
        p = d / "roster.json"
        if p.is_file():
            return p
    return None


def resolve_daemon_path(binder: Path) -> Path | None:
    """Daemon beside the roster we would use (runtime only)."""
    roster = resolve_roster_path(binder)
    if roster is None:
        return None
    daemon = roster.parent / "daemon.json"
    return daemon if daemon.is_file() else None


def worklane_data_dir(binder: Path) -> Path:
    return binder / "worklane" / "worklane" / "local" / "data"


def _list_sqlite_dbs(binder: Path) -> list[Path]:
    data = worklane_data_dir(binder)
    if not data.is_dir():
        return []
    return sorted(p for p in data.glob("*.db") if p.is_file())


def projector_stamp(binder: Path) -> tuple:
    """Identity tuple for projector inputs — changes force a re-read.

    Always a tuple (never ``None``) so BinderOverview can distinguish
    "projectors considered" from "overview.json present".
    """
    binder = Path(binder)
    parts: list[object] = ["projectors"]
    roster = resolve_roster_path(binder)
    parts.append(_file_stamp(roster) if roster else None)
    daemon = resolve_daemon_path(binder)
    parts.append(_file_stamp(daemon) if daemon else None)
    dbs = _list_sqlite_dbs(binder)
    parts.append(tuple(_file_stamp(p) for p in dbs))
    join = binder / "worklane" / ".protocolcity" / "desk-join.json"
    parts.append(_file_stamp(join) if join.is_file() else None)
    return tuple(parts)


# ── Agents ─────────────────────────────────────────────────────────────────


def project_agents(binder: Path) -> list[dict]:
    """Project WorkForce roster workers → ``[{name, state}, …]``.

    Rows come only from ``workers``. ``daemon.json`` ``in_flight`` may flip
    a known worker to ``working``; it never invents a seat.
    """
    binder = Path(binder)
    roster_path = resolve_roster_path(binder)
    if roster_path is None:
        return []
    raw = _read_json(roster_path)
    if not isinstance(raw, dict):
        return []
    workers = raw.get("workers")
    if not isinstance(workers, dict):
        return []

    in_flight: set[str] = set()
    daemon_path = roster_path.parent / "daemon.json"
    if daemon_path.is_file():
        daemon = _read_json(daemon_path)
        if isinstance(daemon, dict):
            flight = daemon.get("in_flight")
            if isinstance(flight, list):
                in_flight = {str(x) for x in flight if x is not None}

    agents: list[dict] = []
    for wid, row in workers.items():
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "").strip().lower()
        # Only lane/job seats paint as agents; unknown kinds skipped (no invent).
        if kind and kind not in ("lane", "job"):
            continue
        identity = str(row.get("identity") or wid).strip() or str(wid)
        display = str(row.get("display") or "").strip()
        # Prefer roster ``display`` for paint (Design soft watch). Keep
        # ``demo-worker`` as the wire name so the alone→No agents filter still
        # keys on identity.
        if identity == "demo-worker" or str(wid) == "demo-worker":
            name = "demo-worker"
        else:
            name = display or identity
        if not name:
            continue
        state = "working" if (identity in in_flight or str(wid) in in_flight) else "idle"
        agents.append({"name": name, "state": state})
    return agents


# ── Jobs ───────────────────────────────────────────────────────────────────


def _labels_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        # SQLite often stores JSON text for labels.
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return [p.strip() for p in raw.split(",") if p.strip()]
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    return []


def _is_blocked_fields(gate_type: str | None, labels: list[str]) -> bool:
    """Only mark blocked when fields clearly say so — never invent."""
    gt = (gate_type or "").strip().lower()
    if gt == "human":
        return True
    for lab in labels:
        low = lab.strip().lower()
        if low in ("blocked", "gate:human") or low.startswith("blocked:"):
            return True
        if low.startswith("needs:") and "block" in low:
            return True
    return False


def classify_task(
    status: str,
    *,
    gate_type: str | None = None,
    gate_note: str | None = None,
    labels: list[str] | None = None,
) -> str | None:
    """Map a WorkLane task → Overview job state, or ``None`` to omit.

    CoS-conservative::

        backlog / in_review → waiting
        in_progress          → ready
        done / canceled      → omit
        blocked              → only when labels/gate_type clearly say so
    """
    st = (status or "").strip().lower().replace(" ", "_")
    if st in _TERMINAL or not st:
        return None
    labels = labels or []
    if _is_blocked_fields(gate_type, labels):
        return "blocked"
    if st == "in_progress":
        return "ready"
    if st in ("backlog", "in_review"):
        # Deferred ice stays waiting, never ready.
        return "waiting"
    # Unknown status — omit rather than invent a bucket.
    return None


def _task_to_job(row: dict) -> dict | None:
    status = str(row.get("status") or "")
    gate_type = row.get("gate_type")
    gate_note = row.get("gate_note")
    labels = _labels_list(row.get("labels"))
    state = classify_task(
        status,
        gate_type=None if gate_type is None else str(gate_type),
        gate_note=None if gate_note is None else str(gate_note),
        labels=labels,
    )
    if state is None:
        return None
    title = str(row.get("title") or "").strip()
    ext = str(row.get("ext_id") or row.get("id") or "").strip()
    name = title or ext
    if not name:
        return None
    return {"name": name, "state": state}


def _buckets_from_jobs(jobs: list[dict]) -> dict:
    buckets = {"waiting": 0, "ready": 0, "blocked": 0}
    for row in jobs:
        st = row.get("state")
        if st in buckets:
            buckets[st] += 1
    return buckets


def _http_get_json(url: str) -> Any | None:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DESK_TIMEOUT_S) as resp:
            body = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        return None


def _project_jobs_via_desk() -> list[dict] | None:
    """Try live Desk HTTP. Returns ``None`` on any failure (caller falls through)."""
    products_payload = _http_get_json(f"{_DESK_BASE}/api/admin/products")
    if not isinstance(products_payload, dict) or not products_payload.get("ok"):
        return None
    products = products_payload.get("products")
    if not isinstance(products, list):
        return None

    jobs: list[dict] = []
    # Empty product list is a successful empty projection (not a fallthrough).
    for prod in products:
        if not isinstance(prod, dict):
            continue
        slug = str(prod.get("slug") or "").strip()
        if not slug:
            continue
        # Open-family only — ask per status to avoid pulling done/canceled.
        for status in ("backlog", "in_progress", "in_review"):
            payload = _http_get_json(
                f"{_DESK_BASE}/api/admin/tasks?project={urllib.parse.quote(slug)}"
                f"&status={status}&limit=200"
            )
            if not isinstance(payload, dict):
                return None  # mid-flight failure → degrade to SQLite / empty
            tasks = payload.get("tasks")
            if not isinstance(tasks, list):
                return None
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                job = _task_to_job(task)
                if job is not None:
                    jobs.append(job)
    return jobs



def _project_jobs_via_sqlite(binder: Path) -> list[dict]:
    jobs: list[dict] = []
    for db_path in _list_sqlite_dbs(binder):
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.5)
        except sqlite3.Error:
            continue
        try:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT id, ext_id, title, status, labels, "
                    "gate_type, gate_note FROM tasks "
                    "WHERE status NOT IN ('done', 'canceled', 'cancelled')"
                ).fetchall()
            except sqlite3.Error:
                # Older DBs may lack gate_* — fall back to core columns.
                try:
                    rows = conn.execute(
                        "SELECT id, ext_id, title, status, labels "
                        "FROM tasks "
                        "WHERE status NOT IN ('done', 'canceled', 'cancelled')"
                    ).fetchall()
                except sqlite3.Error:
                    continue
            for row in rows:
                keys = row.keys()
                as_dict = {
                    "id": row["id"],
                    "ext_id": row["ext_id"] if "ext_id" in keys else "",
                    "title": row["title"] if "title" in keys else "",
                    "status": row["status"] if "status" in keys else "",
                    "labels": row["labels"] if "labels" in keys else "[]",
                    "gate_type": row["gate_type"] if "gate_type" in keys else None,
                    "gate_note": row["gate_note"] if "gate_note" in keys else None,
                }
                job = _task_to_job(as_dict)
                if job is not None:
                    jobs.append(job)
        finally:
            conn.close()
    return jobs


def project_jobs(binder: Path) -> tuple[list[dict], dict]:
    """Project WorkLane open tasks → ``(jobs, buckets)``.

    Desk HTTP first (short timeout); on any failure, SQLite under the binder.
    Missing stores → ``([], zeros)``.
    """
    binder = Path(binder)
    desk = _project_jobs_via_desk()
    if desk is not None:
        jobs = desk
    else:
        jobs = _project_jobs_via_sqlite(binder)
    return jobs, _buckets_from_jobs(jobs)


# ── Combined overview slice ────────────────────────────────────────────────


def project_local_overview(binder: Path) -> dict:
    """Agents + jobs slice for BinderOverview when overview.json is absent.

    Returns only the keys projectors own; caller merges onto ``empty_state()``
    and keeps pulse / project / charter / cellar_tip honest-empty / pinned.
    """
    binder = Path(binder).expanduser().resolve()
    agents = project_agents(binder)
    jobs, buckets = project_jobs(binder)
    return {"agents": agents, "jobs": jobs, "buckets": buckets}
