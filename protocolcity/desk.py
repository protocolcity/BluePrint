"""Optional WorkLane desk joins for first-run founding (pc-20 / pc-134 M1).

Never required for `found` to succeed — scaffold always works offline.
When CITY_DESK (default http://127.0.0.1:8799) answers, founding can:
  · create a product store for the first neighborhood
  · file one sample work order so the Office neighborhood shows backlog + starving

Host-neutral: all URLs are data (env / args), never hard-coded product names
beyond the neighborhood the citizen just founded.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

DEFAULT_DESK = os.environ.get("CITY_DESK", "http://127.0.0.1:8799").rstrip("/")

# Durable per-neighborhood record of the WorkLane join (pc-487).
# Survives when AGENTS.md is pre-authored and not rewritten on adopt.
DESK_JOIN_REL = Path(".protocolcity") / "desk-join.json"


def write_desk_join(
    neighborhood_path: Union[str, Path],
    *,
    slug: str,
    prefix: str,
    display: Optional[str] = None,
    desk_url: Optional[str] = None,
) -> Path:
    """Write ``.protocolcity/desk-join.json`` under a neighborhood (pc-487).

    Called on every successful desk join so agents who only read the folder
    can see store slug + prefix without grepping AGENTS.md or products.json.
    """
    path = Path(neighborhood_path)
    dest_dir = path / ".protocolcity"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "desk-join.json"
    doc: Dict[str, Any] = {
        "slug": slug,
        "prefix": prefix,
        "display": display or slug,
        "joined_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if desk_url:
        doc["desk_url"] = desk_url.rstrip("/")
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return dest


def read_desk_join(neighborhood_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load desk-join.json if present and valid; else None."""
    dest = Path(neighborhood_path) / DESK_JOIN_REL
    if not dest.is_file():
        return None
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    slug = str(data.get("slug") or "").strip()
    prefix = str(data.get("prefix") or "").strip()
    if not slug or not prefix:
        return None
    return data


def fetch_store_prefix(slug: str, desk_url: str = DEFAULT_DESK) -> Optional[str]:
    """Return the registered prefix for *slug* from /api/scene, or None.

    Called by adopt before writing desk-join.json so re-adopt never invents a
    second prefix when the store already exists with a different one (pc-731).
    Returns None when the desk is unreachable or the slug has no store yet.
    """
    try:
        with urllib.request.urlopen(desk_url + "/api/scene", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    stores = data.get("stores")
    if not isinstance(stores, list):
        return None
    want = (slug or "").strip().lower()
    for s in stores:
        if not isinstance(s, dict):
            continue
        s_slug = str(
            s.get("slug") or s.get("product") or s.get("name") or ""
        ).strip().lower()
        if s_slug == want:
            pref = str(s.get("prefix") or "").strip()
            return pref or None
    return None


def agents_has_desk_identity(text: str, slug: str, prefix: str) -> bool:
    """True when AGENTS.md already names the store/prefix as desk identity.

    Bare project title matching the slug (e.g. "# Connector") does **not**
    count — need ticket-store / work-order / prefix framing (pc-487).
    """
    if not text:
        return False
    lower = text.lower()
    slug_l = (slug or "").lower()
    prefix_l = (prefix or "").lower()
    # Structured desk lines (template + soft-append shape)
    if "ticket store" in lower:
        if slug_l and slug_l in lower:
            return True
        if prefix_l and prefix_l in lower:
            return True
    if "desk join" in lower and (slug_l in lower or (prefix_l and prefix_l in lower)):
        return True
    if prefix_l and (
        ("`%s-*" % prefix_l) in lower
        or ("work orders `%s" % prefix_l) in lower
        or ("work orders %s" % prefix_l) in lower
        or ("prefix `%s`" % prefix_l) in lower
        or ("prefix: `%s`" % prefix_l) in lower
        or ("prefix: %s" % prefix_l) in lower
    ):
        return True
    # Backticked slug near store wording
    if slug_l and ("`%s`" % slug_l) in lower and (
        "store" in lower or "ticket" in lower or "work order" in lower
    ):
        return True
    return False


def soft_append_desk_identity(
    agents_path: Union[str, Path],
    *,
    slug: str,
    prefix: str,
) -> bool:
    """Append a short Desk join block when AGENTS.md lacks store/prefix (pc-487).

    Never rewrites existing content — append-only. Returns True if appended.
    """
    path = Path(agents_path)
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if agents_has_desk_identity(text, slug, prefix):
        return False
    block = (
        "\n\n## Desk join (BluePrint)\n\n"
        "- Ticket store: `%s` (work orders `%s-*`)\n"
        "- Durable record: `.protocolcity/desk-join.json`\n"
    ) % (slug, prefix)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")
    return True


def _neighborhood_for_slug(city_root: Union[str, Path], slug: str) -> Optional[Path]:
    """Best-effort folder under city_root whose desk_slug(name) matches slug."""
    try:
        from protocolcity.slugs import desk_slug
    except Exception:
        return None
    root = Path(city_root)
    want = (slug or "").strip().lower()
    if not want or not root.is_dir():
        return None
    try:
        for child in root.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                if desk_slug(child.name) == want:
                    return child
    except OSError:
        return None
    return None


def desk_reachable(desk_url: str = DEFAULT_DESK, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(
            desk_url + "/api/admin/tasks?limit=1",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _post_json(url: str, payload: Dict[str, Any], timeout: float = 8.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            out = json.loads(body) if body else {"ok": True}
            if isinstance(out, dict):
                out.setdefault("status", r.status)
                return out
            return {"ok": True, "data": out, "status": r.status}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            out = json.loads(raw)
        except Exception:
            return {"ok": False, "error": raw or str(e), "status": e.code}
        if isinstance(out, dict):
            # Always stamp HTTP status — 409 bodies often omit it (pc-557).
            out["status"] = e.code
            return out
        return {"ok": False, "error": str(out), "status": e.code}


def ensure_store(
    slug: str,
    *,
    display: Optional[str] = None,
    prefix: Optional[str] = None,
    desk_url: str = DEFAULT_DESK,
) -> Dict[str, Any]:
    """Create product store if missing. 409 already-exists is success."""
    # pc-313: canonical rule first (whitespace → "-"), then strip the rest —
    # bare stripping turned "se local hc" into a third slug variant.
    slug = re.sub(r"[^a-z0-9_-]", "", "-".join(slug.lower().split()))
    if not slug:
        return {"ok": False, "error": "empty slug"}
    if not prefix:
        prefix = re.sub(r"[^a-z0-9]", "", slug)[:4] or "app"
        if len(prefix) < 2:
            prefix = (prefix + "xx")[:2]
    payload = {"slug": slug, "display": display or slug.title(), "prefix": prefix}
    result = _post_json(desk_url + "/api/admin/products", payload)
    if result.get("ok"):
        result["created"] = True
        return result
    err = str(
        result.get("error")
        or result.get("detail")
        or result.get("message")
        or ""
    )
    # 409 Conflict / already-exists is success (pc-557 Join Store UX).
    status = result.get("status")
    try:
        status_i = int(status) if status is not None else 0
    except (TypeError, ValueError):
        status_i = 0
    err_l = err.lower()
    if status_i == 409 or "already exists" in err_l or "conflict" in err_l:
        return {
            "ok": True,
            "created": False,
            "existed": True,
            "product": {"slug": slug, "display": display or slug, "prefix": prefix},
            "warning": err or None,
        }
    # prefix collision — retry with longer prefix once
    if "prefix" in err.lower() and "already" in err.lower():
        payload["prefix"] = (prefix + "x")[:8]
        result2 = _post_json(desk_url + "/api/admin/products", payload)
        if result2.get("ok"):
            result2["created"] = True
            return result2
        if "already exists" in str(result2.get("error") or "").lower():
            return {"ok": True, "created": False, "existed": True, "product": payload}
        return result2
    return result


def file_sample_ticket(
    project: str,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    author: str = "protocolcity-found",
    desk_url: str = DEFAULT_DESK,
    priority: int = 2,
    worker_id: Optional[str] = None,
    labels: Optional[list] = None,
) -> Dict[str, Any]:
    """File one demo work order on the neighborhood store.

    pc-594: when *worker_id* is known (hired hand or demo-worker stubs),
    stamp ``worker:<id>`` so the sample is drainable. Without a hand, leave
    labels unrouted — desk stamps ``needs:routing`` (visible stall, not silent).
    """
    title = title or "First work order — prove the desk is live"
    if worker_id:
        description = description or (
            "Founded by `blueprint found` / adopt. Routed to "
            "`worker:%s` so a hired or demo hand can claim it.\n\n"
            "Expected: claim, do a tiny real thing, close with verification."
            % worker_id
        )
    else:
        description = description or (
            "Founded by `blueprint found` / adopt. No hand was hired yet, so "
            "this ticket is unrouted (`needs:routing`).\n\n"
            "Next: `blueprint hire <persona> --workdir <project>`, then "
            "`wl label <id> --add worker:<persona>` (or re-file with the label). "
            "Until then nothing scheduled will drain this ticket."
        )
    labs = list(labels) if labels else ["demo", "founding"]
    if worker_id:
        wid = str(worker_id).strip().lower()
        if wid.startswith("worker:"):
            wid = wid[7:]
        labs = [x for x in labs if not str(x).lower().startswith("worker:")]
        labs.append("worker:" + wid)
    payload = {
        "project": project,
        "title": title,
        "description": description,
        "author": author,
        "priority": priority,
        "labels": labs,
    }
    return _post_json(desk_url + "/api/admin/tasks", payload)


def resolve_sample_worker_id(
    project_root: Optional[str] = None,
    *,
    preferred: Optional[str] = None,
) -> Optional[str]:
    """Pick a hand id for sample WOs when one is knowable (pc-594).

    Order: explicit preferred → single workers/<id> under project → demo-worker
    if that stub dir exists. Does not invent multi-hand defaults.
    """
    if preferred:
        w = str(preferred).strip().lower()
        return w[7:] if w.startswith("worker:") else w
    if not project_root:
        return None
    wdir = os.path.join(str(project_root), "workers")
    if not os.path.isdir(wdir):
        return None
    try:
        names = sorted(
            n
            for n in os.listdir(wdir)
            if n and not n.startswith(".") and os.path.isdir(os.path.join(wdir, n))
        )
    except OSError:
        return None
    if len(names) == 1:
        return names[0]
    if "demo-worker" in names:
        return "demo-worker"
    return None


def _pending_path(city_root) -> str:
    return os.path.join(str(city_root), ".protocolcity", "pending-desk.json")


def queue_pending_join(
    city_root,
    store_slug: str,
    *,
    display: Optional[str] = None,
    prefix: Optional[str] = None,
    sample_ticket: bool = False,
) -> Dict[str, Any]:
    """Record a desk join that could not run because the desk was offline (pc-314).

    found/adopt scaffold law offline, but the store join used to vanish — the
    citizen got a fully scaffolded city with no houses and no breadcrumb. The
    queue is retried by ``flush_pending_joins`` (serve --with-engines runs it
    once the desk answers).
    """
    path = _pending_path(city_root)
    doc: Dict[str, Any] = {
        "note": "Desk joins deferred while the desk was offline; "
                "flushed automatically by `blueprint serve --with-engines`.",
        "pending": [],
    }
    try:
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict) and isinstance(existing.get("pending"), list):
            doc["pending"] = existing["pending"]
    except Exception:
        pass
    entry = {
        "slug": store_slug,
        "display": display,
        "prefix": prefix,
        "sample_ticket": bool(sample_ticket),
    }
    doc["pending"] = [p for p in doc["pending"] if p.get("slug") != store_slug]
    doc["pending"].append(entry)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return entry


def flush_pending_joins(city_root, *, desk_url: str = DEFAULT_DESK) -> list:
    """Bootstrap every queued join; drop entries that succeed (pc-314).

    Returns ``[{"slug": ..., "ok": bool, ...}, ...]`` (empty when no queue).
    """
    path = _pending_path(city_root)
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        pending = doc.get("pending") or []
    except Exception:
        return []
    if not pending:
        return []
    results = []
    remaining = []
    for entry in pending:
        slug = str(entry.get("slug") or "").strip()
        if not slug:
            continue
        display = entry.get("display")
        prefix = entry.get("prefix")
        result = bootstrap_desk(
            slug,
            display=display,
            prefix=prefix,
            desk_url=desk_url,
            sample_ticket=bool(entry.get("sample_ticket")),
        )
        result["slug"] = slug
        if result.get("ok"):
            # pc-487: durable join under the neighborhood when flush lands.
            hood = _neighborhood_for_slug(city_root, slug)
            if hood is not None:
                use_prefix = prefix
                if not use_prefix:
                    store = result.get("store") or {}
                    product = store.get("product") or store
                    use_prefix = (
                        (product or {}).get("prefix")
                        if isinstance(product, dict)
                        else None
                    )
                if not use_prefix:
                    use_prefix = re.sub(r"[^a-z0-9]", "", slug)[:4] or "app"
                write_desk_join(
                    hood,
                    slug=slug,
                    prefix=str(use_prefix),
                    display=display or slug,
                    desk_url=desk_url,
                )
                soft_append_desk_identity(
                    hood / "AGENTS.md",
                    slug=slug,
                    prefix=str(use_prefix),
                )
        results.append(result)
        if not result.get("ok"):
            remaining.append(entry)
    doc["pending"] = remaining
    try:
        if remaining:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)
        else:
            os.remove(path)
    except Exception:
        pass
    return results


def bootstrap_desk(
    store_slug: str,
    *,
    display: Optional[str] = None,
    prefix: Optional[str] = None,
    desk_url: str = DEFAULT_DESK,
    sample_ticket: bool = True,
    project_root: Optional[str] = None,
    sample_worker_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure store + optional sample ticket. Soft-fail dictionary always."""
    out: Dict[str, Any] = {
        "desk_url": desk_url,
        "reachable": desk_reachable(desk_url),
        "store": None,
        "ticket": None,
    }
    if not out["reachable"]:
        out["ok"] = False
        out["error"] = "desk not reachable at %s" % desk_url
        return out
    store = ensure_store(store_slug, display=display, prefix=prefix, desk_url=desk_url)
    out["store"] = store
    if not store.get("ok"):
        out["ok"] = False
        out["error"] = store.get("error") or "store create failed"
        return out
    if sample_ticket:
        hand = sample_worker_id or resolve_sample_worker_id(project_root)
        ticket = file_sample_ticket(
            store_slug, desk_url=desk_url, worker_id=hand
        )
        out["ticket"] = ticket
        out["sample_worker"] = hand
        out["ok"] = bool(ticket.get("ok"))
        if not out["ok"]:
            out["error"] = ticket.get("error") or "ticket create failed"
            # store still succeeded
            out["ok"] = True
            out["ticket_error"] = out.pop("error", None)
    else:
        out["ok"] = True
    return out
