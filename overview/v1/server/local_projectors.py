"""Phase-B local projectors — WorkForce agents + WorkLane jobs under a binder.

When ``--binder DIR`` is set and ``<binder>/.blueprint/overview.json`` is
absent, Overview Agents / Jobs paint from these public local shapes:

Agents (WorkForce roster)::

    <binder>/.protocolcity/workforce/local/roster.json
    <binder>/workforce/local/roster.json          # twin fallback

    Optional runtime twin in the same dir: ``daemon.json`` (``in_flight``).
    Daemon is **not** SoT for which rows exist — only idle/working polish.

Jobs (WorkLane product stores)::

    Read SQLite ``<binder>/worklane/worklane/local/data/<slug>.db``
    table ``tasks`` when present. Never infer workspace ownership from a
    server listening on localhost; it may serve a different workspace.

Never invent seats or WOs. Missing / malformed → honest empty.
``overview.json`` (when present) still wins at the BinderOverview layer.
"""
from __future__ import annotations

import json
import shlex
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Any

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


# ── Engine ledger shifts ───────────────────────────────────────────────────

_TERMINAL_SHIFT_EVENTS = frozenset({"STOP", "ERROR"})
SHIFT_GRACE_SECS = 600
_LEDGER_TAIL_BYTES = 16384
_IDENTITY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")


def _split_row(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError:
        return []


def _row_fields(parts: list[str]) -> dict[str, str]:
    return dict(item.split("=", 1) for item in parts[2:] if "=" in item)


def _ledger_tail_lines(path: Path) -> list[str]:
    try:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - _LEDGER_TAIL_BYTES))
            return stream.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _parse_stamp(value: str) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return stamp if stamp.tzinfo is not None else None


def ledger_open_shift(ledger_path: Path, now: datetime,
                      grace_secs: int = SHIFT_GRACE_SECS) -> dict | None:
    """Newest START row with no later STOP/ERROR → open-shift evidence.

    This is the engine's own ledger, not a process check: a shift dispatched
    outside the daemon tick (bounded supervisor pass, manual engine dispatch)
    is visible here while ``daemon.json`` ``in_flight`` stays empty. A START
    older than its budget plus grace with no terminal row is ``stale``: the
    shift may have died without writing one, so it is never painted working.
    """
    lines = _ledger_tail_lines(ledger_path)
    start_index = None
    for index in range(len(lines) - 1, -1, -1):
        parts = _split_row(lines[index])
        if len(parts) >= 2 and parts[1] == "START":
            start_index = index
            break
    if start_index is None:
        return None
    start = _split_row(lines[start_index])
    if _row_fields(start).get("dry_run") == "1":
        # Engine dry runs write START/DONE without STOP and never spawn a
        # provider; they are not open shifts.
        return None
    candidates: list[str] = []
    for line in lines[start_index + 1:]:
        parts = _split_row(line)
        if len(parts) < 2:
            continue
        if parts[1] in _TERMINAL_SHIFT_EVENTS:
            return None
        if parts[1] == "CANDIDATE":
            ticket = _row_fields(parts).get("ticket", "")
            if ticket and ticket not in candidates:
                candidates.append(ticket)
    try:
        budget = int(_row_fields(start).get("budget_secs") or 0)
    except ValueError:
        budget = 0
    started = _parse_stamp(start[0])
    age = (now - started).total_seconds() if started is not None else None
    stale = age is None or age < -30 or age > budget + grace_secs
    return {
        "started_at": start[0],
        "budget_secs": budget,
        "candidates": candidates,
        "age_seconds": int(age) if age is not None else None,
        "stale": stale,
        "source": "engine ledger",
    }


def engine_open_shift(daemon_path: Path | None, root: Path, identity: str,
                      now: datetime) -> dict | None:
    """Open shift for ``identity`` from the ledger beside the runtime daemon file.

    Paths stay inside ``root``; an identity outside the engine's slug charset
    is never used to build a path. ``lock_held`` reports whether the engine's
    per-worker lock directory exists — evidence, not liveness.
    """
    if daemon_path is None or not identity or any(c not in _IDENTITY_CHARS for c in identity):
        return None
    runtime = daemon_path.resolve().parent
    ledger = runtime / "ledger" / (identity + ".log")
    try:
        if not ledger.resolve().is_relative_to(root.resolve()):
            return None
    except OSError:
        return None
    shift = ledger_open_shift(ledger, now)
    if shift is None:
        return None
    shift["lock_held"] = (runtime / "locks" / (identity + ".lock")).is_dir()
    return shift


# ── Agents ─────────────────────────────────────────────────────────────────


def project_agents(binder: Path) -> list[dict]:
    """Project WorkForce roster workers → ``[{name, state}, …]``.

    Rows come only from ``workers``. ``daemon.json`` ``in_flight`` or an open
    engine-ledger shift (START without STOP/ERROR, within budget plus grace)
    may flip a known worker to ``working``; neither invents a seat.
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
    now = datetime.now(timezone.utc)
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
        if state == "idle" and daemon_path.is_file():
            shift = engine_open_shift(daemon_path, binder, identity, now)
            if shift is not None and not shift["stale"]:
                state = "working"
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

    Read only the selected binder’s SQLite stores. An unrelated local
    WorkLane service must never supply this workspace’s work orders.
    Missing stores → ``([], zeros)``.
    """
    binder = Path(binder)
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
