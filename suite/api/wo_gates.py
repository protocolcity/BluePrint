"""pc-688 / pc-1084: Map Work Order chip tallies — gate-aware, uncapped.

Chip *counts* (live / ready / deferred) must not equal capped list length
(MAP_WO_LIST_CAP). Dual-read ice is the Python mirror of
``suite/map/wo-buckets.js`` ``isDeferredGate`` (wl-257). Enforced by
``scripts/check_wo_buckets_drift.py`` — do not hand-diverge markers.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

from .vocabulary import PREFIX_PRODUCT

OPEN_STATUSES = frozenset({"backlog", "in_progress", "in_review", ""})
DONE_STATUSES = frozenset({"done", "canceled"})


def is_deferred_gate(gate_type: Any, gate_note: Any) -> bool:
    """Python mirror of Map isDeferredGate (pc-547 / wl-257 dual-read)."""
    gt = str(gate_type if gate_type is not None else "").lower().strip()
    note = str(gate_note if gate_note is not None else "").lower().strip()
    if gt == "deferred":
        return True
    if not gt:
        return False
    if note.startswith("deferred:") or note.startswith("umbrella"):
        return True
    markers = (
        "deferred:",
        "post-northstar",
        "not claimable",
        "withheld from ready",
        "parked:",
        "thaw when",
    )
    for m in markers:
        if m in note:
            return True
    if "umbrella" in note:
        return True
    return False


def is_ready(status: Any, gate_type: Any, gate_note: Any) -> bool:
    """Map ready: backlog, no ice, empty/missing gate_type."""
    st = str(status or "backlog").lower().replace(" ", "_")
    if st != "backlog":
        return False
    if is_deferred_gate(gate_type, gate_note):
        return False
    return gate_type is None or str(gate_type).strip() == ""


def is_live_open(status: Any, gate_type: Any, gate_note: Any) -> bool:
    """Open without ice — backlog / in_progress / in_review, not deferred."""
    st = str(status or "").lower().replace(" ", "_")
    if st in DONE_STATUSES:
        return False
    if is_deferred_gate(gate_type, gate_note):
        return False
    return st in OPEN_STATUSES


def task_product_key(task: Mapping[str, Any]) -> str:
    """Best-effort product/store slug for a desk task (pc-875 Map heat)."""
    for field in ("product", "project", "store", "slug"):
        raw = str(task.get(field) or "").strip().lower()
        if raw:
            return raw
    labels = task.get("labels") or []
    if isinstance(labels, (list, tuple)):
        for lab in labels:
            s = str(lab or "").strip().lower()
            if s.startswith("product:") and len(s) > 8:
                return s[8:].strip()
    tid = str(task.get("id") or task.get("task_id") or "").strip().lower()
    if "-" in tid:
        pref = tid.split("-", 1)[0]
        if pref in PREFIX_PRODUCT:
            return PREFIX_PRODUCT[pref]
        if pref:
            return pref
    return ""


def tally_wo_gate_counts(tasks: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    """Authoritative chip tallies from a full open-family task set.

    ``tasks`` should be the uncapped open set (or a fixture). Counts are
    independent of any list render cap.
    """
    live = 0
    deferred = 0
    ready = 0
    open_n = 0
    seen: set[str] = set()
    for t in tasks:
        if not isinstance(t, Mapping):
            continue
        tid = str(t.get("id") or t.get("task_id") or "").strip()
        if tid:
            if tid in seen:
                continue
            seen.add(tid)
        st = str(t.get("status") or "backlog").lower().replace(" ", "_")
        if st in DONE_STATUSES:
            continue
        if st not in OPEN_STATUSES:
            continue
        open_n += 1
        gt = t.get("gate_type")
        if gt is None:
            gt = t.get("gateType")
        gn = t.get("gate_note")
        if gn is None:
            gn = t.get("gateNote")
        if is_deferred_gate(gt, gn):
            deferred += 1
        else:
            live += 1
        if is_ready(st, gt, gn):
            ready += 1
    return {
        "live": live,
        "deferred": deferred,
        "ready": ready,
        "open": open_n,
    }


def tally_wo_gate_counts_by_product(
    tasks: Iterable[Mapping[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Per-product live/deferred/ready/open from uncapped open set (pc-875).

    Each value is ``{live, deferred, ready, open, sampled: 1}`` so Map folder
    heat can trust the row without the capped open-family list sample.
    """
    by: Dict[str, Dict[str, int]] = {}
    seen: set[str] = set()
    for t in tasks:
        if not isinstance(t, Mapping):
            continue
        tid = str(t.get("id") or t.get("task_id") or "").strip()
        if tid:
            if tid in seen:
                continue
            seen.add(tid)
        st = str(t.get("status") or "backlog").lower().replace(" ", "_")
        if st in DONE_STATUSES or st not in OPEN_STATUSES:
            continue
        prod = task_product_key(t)
        if not prod:
            continue
        row = by.get(prod)
        if row is None:
            row = {"live": 0, "deferred": 0, "ready": 0, "open": 0, "sampled": 1}
            by[prod] = row
        row["open"] = int(row.get("open") or 0) + 1
        gt = t.get("gate_type")
        if gt is None:
            gt = t.get("gateType")
        gn = t.get("gate_note")
        if gn is None:
            gn = t.get("gateNote")
        if is_deferred_gate(gt, gn):
            row["deferred"] = int(row.get("deferred") or 0) + 1
        else:
            row["live"] = int(row.get("live") or 0) + 1
        if is_ready(st, gt, gn):
            row["ready"] = int(row.get("ready") or 0) + 1
    return by


def sum_store_ready(folders: Optional[Iterable[Mapping[str, Any]]]) -> Optional[int]:
    """Sum folder.store.ready (Desk scene rollup family). None if no stores."""
    if not folders:
        return None
    total = 0
    saw = False
    for f in folders:
        if not isinstance(f, Mapping):
            continue
        st = f.get("store")
        if not isinstance(st, Mapping):
            continue
        if "ready" not in st:
            continue
        saw = True
        try:
            total += int(st.get("ready") or 0)
        except (TypeError, ValueError):
            continue
    return total if saw else None
