"""Intake routing labels for WorkForce hand queues (pc-498).

Hands drain ready feeds filtered by ``worker:<id>``. Suite file paths that
omit that label produce silent ready work — schedules fire empty while the
board looks "stuck." This module is the pure half of the product law:

- At most one ``worker:<id>`` label per ticket (exclusive hand feed).
- Optional ``worker`` / ``hand`` body field stamps that label.
- When no hand is chosen, stamp ``needs:routing`` so unrouted ready is
  countable and visible — never pure silent unlabeled ready from suite intake.

Desk/MCP create (slice C) stays WorkLane's job; doctor/citylens findings are
slice D. Suite only enforces this on ``POST /api/tasks``.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Sequence, Tuple

WORKER_LABEL_RE = re.compile(r"^worker:(.+)$", re.IGNORECASE)
NEEDS_ROUTING_LABEL = "needs:routing"


def _as_label_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]
    if isinstance(raw, (list, tuple)):
        out: List[str] = []
        for s in raw:
            t = str(s).strip()
            if t:
                out.append(t)
        return out
    return []


def worker_ids_from_labels(labels: Iterable[Any]) -> List[str]:
    """Return unique worker ids (lowercase) from ``worker:*`` labels, order kept."""
    seen = set()
    ids: List[str] = []
    for lab in labels or []:
        m = WORKER_LABEL_RE.match(str(lab).strip())
        if not m:
            continue
        wid = m.group(1).strip().lower()
        if not wid or wid in seen:
            continue
        seen.add(wid)
        ids.append(wid)
    return ids


def has_worker_label(labels: Iterable[Any]) -> bool:
    return bool(worker_ids_from_labels(labels))


def is_unrouted_ready(task: dict) -> bool:
    """True when a ready/backlog task has no ``worker:*`` hand label."""
    if not isinstance(task, dict):
        return False
    status = str(task.get("status") or "backlog").lower().replace(" ", "_")
    if status not in ("backlog", "ready"):
        # Ready queue items are backlog with blockers clear; still accept missing status.
        if status and status not in ("", "open"):
            return False
    return not has_worker_label(task.get("labels") or task.get("tags") or [])


def normalize_intake_labels(
    labels: Any = None,
    *,
    worker: Any = None,
    hand: Any = None,
) -> Tuple[Optional[List[str]], Optional[str], dict]:
    """Normalize labels for suite ``POST /api/tasks``.

    Returns ``(labels, error, meta)``. On error, labels is None and error is a
    short message for the JSON body. ``meta`` always describes what we did::

        {
          "worker_ids": [...],
          "stamped_worker": "drew"|None,
          "stamped_needs_routing": bool,
          "cleared_needs_routing": bool,
        }
    """
    labs = _as_label_list(labels)
    meta = {
        "worker_ids": [],
        "stamped_worker": None,
        "stamped_needs_routing": False,
        "cleared_needs_routing": False,
    }

    # Explicit hand from compose body (roster-driven picker).
    hand_raw = worker if worker not in (None, "") else hand
    if hand_raw not in (None, ""):
        slug = str(hand_raw).strip().lower()
        # Allow "worker:drew" or bare "drew"
        m = WORKER_LABEL_RE.match(slug)
        if m:
            slug = m.group(1).strip().lower()
        if not slug or not re.match(r"^[a-z0-9][a-z0-9._-]{0,63}$", slug):
            return None, "worker/hand must be a short roster id (e.g. drew, riley)", meta
        stamp = "worker:" + slug
        # Drop other worker:* then add the chosen one
        labs = [x for x in labs if not WORKER_LABEL_RE.match(x)]
        labs.append(stamp)
        meta["stamped_worker"] = slug

    wids = worker_ids_from_labels(labs)
    if len(wids) > 1:
        return (
            None,
            (
                "exactly one worker:<id> label allowed — dual hand labels "
                "dual-claim across exclusive queues (%s)"
                % ", ".join("worker:" + w for w in wids)
            ),
            meta,
        )

    meta["worker_ids"] = list(wids)

    if wids:
        # Routed: drop needs:routing if present
        before = len(labs)
        labs = [x for x in labs if x.lower() != NEEDS_ROUTING_LABEL]
        if len(labs) < before:
            meta["cleared_needs_routing"] = True
    else:
        # Unrouted: stamp needs:routing so starvation is countable
        if not any(x.lower() == NEEDS_ROUTING_LABEL for x in labs):
            labs.append(NEEDS_ROUTING_LABEL)
            meta["stamped_needs_routing"] = True

    # De-dupe preserving order (case-sensitive first wins)
    seen = set()
    deduped: List[str] = []
    for x in labs:
        key = x.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(x)

    return deduped, None, meta


def filter_unrouted_tasks(tasks: Sequence[dict]) -> List[dict]:
    """Filter a ready/backlog list to tickets with no ``worker:*`` label."""
    out: List[dict] = []
    for t in tasks or []:
        if isinstance(t, dict) and not has_worker_label(
            t.get("labels") or t.get("tags") or []
        ):
            out.append(t)
    return out
