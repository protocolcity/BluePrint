"""Suite vocabulary — prefix→product + store-slug aliases + light task rows.

pc-1123: one authoritative copy farm for Map / desk BFF (generate, don't
document). Importers: ``suite/serve.py``, ``suite/api/wo_gates.py``.
Drift: ``scripts/check_vocabulary_drift.py``.

No host-absolute paths. Relative imports only (script-path safe).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .task_glance import extract_task_glance

# Composite work-order id prefix → WorkLane store product slug.
# Superset of live-strip + /api/tasks inventories (pc-1123 + pc-1114).
# Includes both reci and rc → recipes; scra → scratch-cab; register store.
PREFIX_PRODUCT: Dict[str, str] = {
    "pc": "protocolcity",
    "tp": "worklane",  # legacy prefix; store is worklane (tp-207)
    "wl": "worklane",
    "wf": "workforce",
    "oc": "workforce",  # legacy workforce prefix
    "ts": "tradeos",
    "t": "tradeos",  # legacy tradeos prefix
    "gf": "gridfinity",
    "so": "socials",
    "osp": "oneseo-pos",
    "regi": "oneseo-pos",  # legacy oneseo-pos prefix
    "conn": "connector",
    "career": "career",
    "reci": "recipes",
    "rc": "recipes",
    "pr": "presentations",
    "scra": "scratch-cab",
    "register": "register",
}

# Folder / display / legacy aliases → canonical WorkLane store slug.
# Suite-owned (desk_v1 FOLDER_STORE is gone); Map JS STORE_SLUG_ALIASES
# should stay lockstep (suite/map/wo-buckets.js · pc-1090).
FOLDER_STORE: Dict[str, str] = {
    "worklane": "worklane",
    "ticketingprotocol": "worklane",
    "tp": "worklane",
    "wl": "worklane",
    # pc-1044: folder/display aliases → canonical WorkLane store slug
    "register": "oneseo-pos",
    "regi": "oneseo-pos",
    "oneseo_pos": "oneseo-pos",
    "oc": "workforce",
    "blueprint": "protocolcity",
}


def normalize_store_slug(product: Any) -> str:
    """Map UI project folder / display name to WorkLane store slug (pc-557).

    Spaces and mixed case become hyphenated slugs (``SE Local HC`` →
    ``se-local-hc``). ``se+local+hc`` form encoding also collapses. Aliases
    in ``FOLDER_STORE`` still win for known engines.
    """
    pk = (product or "").strip().lower() if product is not None else ""
    if not pk:
        return ""
    # form-urlencoded spaces often arrive as +
    pk = pk.replace("+", " ")
    # Canonical hyphen slug (same rule as protocolcity.slugs.slugify)
    pk = "-".join(pk.split())
    return FOLDER_STORE.get(pk, pk)


def product_of_task_id(tid: Any, fallback: Optional[str] = None) -> Optional[str]:
    """Best-effort store product from composite id prefix (e.g. pc-1123)."""
    if fallback:
        return fallback
    s = str(tid or "")
    if "-" not in s:
        return None
    pre = s.split("-", 1)[0].lower()
    return PREFIX_PRODUCT.get(pre)


def light_task_row(
    t: Any, product_fallback: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Suite light task card — glance only (pc-921 / pc-881 / pc-1123).

    Single serializer for live-strip, /api/tasks, ready, and unrouted.
    pc-1054: pass through real ``owner`` when the upstream pull requested
    ``with_preview``. Do not hardcode empty — Map LIVE Owner: join needs it.
    """
    if not isinstance(t, Mapping):
        return None
    tid = t.get("id")
    prod = (
        t.get("product")
        or t.get("store")
        or product_of_task_id(tid, product_fallback)
    )
    glance = ""
    try:
        glance = extract_task_glance(t.get("description") or "") or ""
    except Exception:
        glance = ""
    return {
        "id": tid,
        "title": t.get("title"),
        "status": t.get("status"),
        "priority": t.get("priority"),
        "labels": t.get("labels") or [],
        "gate_type": t.get("gate_type"),
        "gate_note": t.get("gate_note"),
        "gate_until": t.get("gate_until"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "product": prod,
        "owner": (t.get("owner") or "") or "",
        "glance": glance,
    }
