#!/usr/bin/env python3
"""Cross-project open work + drain hygiene audit for BluePrint cities.

Importable library (``protocolcity.open_work_audit``) plus CLI used by
``scripts/open_work_audit.py`` and ``blueprint doctor`` (pc-963).

  python3 scripts/open_work_audit.py
  python3 scripts/open_work_audit.py --json
  python3 scripts/open_work_audit.py --feeds
  python3 scripts/open_work_audit.py --history
  python3 scripts/open_work_audit.py --process
  python3 scripts/open_work_audit.py --decay
  python3 scripts/open_work_audit.py --json --feeds --history --process --decay
  # monorepo parcel path (also works):
  python3 ProtocolCity/scripts/open_work_audit.py --decay
  blueprint doctor   # includes feeds + history board-health section

See docs/specs/ALWAYS_WORK_PROCESS.md and L0 skill workspace-efficiency.
Process-decay patrol (pc-965): ``--decay`` probes law-vs-enforcement drift
(skills bridge, ALWAYS_WORK §9 pending rows, retired worker seats on open work).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_SCENE = (
    "http://127.0.0.1:8799/api/scene",
)
READY_URLS = (
    "http://127.0.0.1:8799/api/admin/tasks/ready",
)

_YOU_KINDS = frozenset({"you:note", "you:remind", "you:todo", "you:host"})
_FOUNDER_MARKERS = frozenset(
    {"gate:founder", "gate:publish", "gate:human", "founder", "publish"}
)

# Default HTTP timeout for doctor / casual runs (engines down → skip, not hang)
DEFAULT_TIMEOUT = 3.0

# ProtocolCity code-lane succession (drew → carl → tom). Open work still seated
# on these ids is process decay — re-label to the live hand (pc-965).
DEFAULT_RETIRED_WORKER_IDS = frozenset({"drew", "carl"})

_SECTION9_HEADER_RE = re.compile(
    r"^##\s*9\.\s*Implement backlog", re.IGNORECASE | re.MULTILINE
)
_SECTION_NEXT_RE = re.compile(r"^##\s+\S", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$")
_LANDED_RE = re.compile(r"\*\*Landed\b", re.IGNORECASE)


def _get(url: str, timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def _probe_json(
    url: str, timeout: float = DEFAULT_TIMEOUT
) -> Tuple[Optional[int], Optional[Dict[str, Any]], str]:
    """GET one JSON object while retaining HTTP/transport failure detail."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            status = int(getattr(r, "status", 200) or 200)
            value = json.loads(r.read().decode("utf-8"))
            if not isinstance(value, dict):
                return status, None, "response is not a JSON object"
            return status, value, ""
    except urllib.error.HTTPError as exc:
        return int(exc.code), None, "HTTP %s" % exc.code
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        return None, None, str(exc) or exc.__class__.__name__


def _roster_candidates(
    explicit: str = "", city_root: Optional[Path] = None
) -> List[Path]:
    """Canonical + legacy roster homes for repo, package, and planted layouts."""
    candidates: List[Path] = []
    if explicit:
        return [Path(explicit).expanduser()]
    if city_root is not None:
        root = Path(city_root).expanduser().resolve()
        return [root / '.protocolcity/workforce/local/roster.json',
                root / 'workforce/local/roster.json']
    env = (os.environ.get("WORKFORCE_ROSTER") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())

    package_dir = Path(__file__).resolve().parent
    # package lives at <repo>/protocolcity/ when editable; Cellar when installed
    package_parent = package_dir.parent
    cwd = Path.cwd().resolve()
    roots: List[Path] = []
    if city_root is not None:
        roots.append(Path(city_root).expanduser().resolve())
    for root in (package_parent, package_dir, cwd, cwd.parent):
        if root not in roots:
            roots.append(root)
    for root in roots:
        candidates.append(
            root / ".protocolcity" / "workforce" / "local" / "roster.json"
        )
        candidates.append(root / "workforce" / "local" / "roster.json")

    seen = set()
    out: List[Path] = []
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def load_roster(
    explicit: str = "", city_root: Optional[Path] = None
) -> Tuple[str, Dict[str, Dict[str, Any]], str]:
    """Return first readable roster path + worker mapping + error detail."""
    errors: List[str] = []
    for path in _roster_candidates(explicit, city_root=city_root):
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append("%s: %s" % (path, exc))
            continue
        workers = raw.get("workers") if isinstance(raw, dict) else None
        if not isinstance(workers, dict):
            errors.append("%s: roster.workers is not an object" % path)
            continue
        clean = {
            str(worker_id): row
            for worker_id, row in workers.items()
            if isinstance(row, dict)
        }
        return str(path.resolve()), clean, ""
    if errors:
        return "", {}, "; ".join(errors)
    return "", {}, "no WorkForce roster found"


def _queue_url_shape(worker_id: str, url: str) -> Tuple[str, List[str]]:
    """Validate the lane drain URL and return its project slug."""
    issues: List[str] = []
    if not url:
        return "", ["missing queue_url"]
    try:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    except ValueError as exc:
        return "", ["invalid queue_url: %s" % exc]
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        issues.append("queue_url must be an absolute HTTP(S) URL")
    if not parsed.path.endswith("/api/admin/tasks/ready"):
        issues.append("queue_url must target /api/admin/tasks/ready")
    product_values = query.get("product") or query.get("project") or []
    product = str(product_values[0]).strip().lower() if product_values else ""
    if not product:
        issues.append("queue_url needs product=<slug>")
    expected_label = "worker:%s" % worker_id
    labels = [str(value).strip().lower() for value in query.get("label", [])]
    if expected_label.lower() not in labels:
        issues.append("queue_url needs label=%s" % expected_label)
    return product, issues


def _deferred_backlog_url(queue_url: str, product: str) -> str:
    """Build the same WorkLane host's deferred-backlog list URL."""
    parsed = urllib.parse.urlparse(queue_url)
    path = parsed.path
    if path.endswith("/ready"):
        path = path[: -len("/ready")]
    query = urllib.parse.urlencode(
        {
            "product": product,
            "status": "backlog",
            "gate_type": "deferred",
            "limit": "200",
        }
    )
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path, "", query, "")
    )


def audit_process_workers(
    workers: Dict[str, Dict[str, Any]],
    roster_path: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Probe every lane queue URL and its same-seat deferred backlog."""
    lanes: List[Dict[str, Any]] = []
    deferred_cache: Dict[Tuple[str, str], Tuple[Optional[int], Any, str]] = {}
    for worker_id, row in sorted(workers.items()):
        kind = str(row.get("kind") or "lane").strip().lower()
        if kind != "lane":
            continue
        queue_url = str(row.get("queue_url") or "").strip()
        product, shape_issues = _queue_url_shape(worker_id, queue_url)
        findings = list(shape_issues)
        http_status: Optional[int] = None
        ready_n: Optional[int] = None
        queue_error = ""
        if queue_url:
            http_status, payload, queue_error = _probe_json(queue_url, timeout=timeout)
            if payload is None:
                findings.append("queue probe failed: %s" % (queue_error or "unknown error"))
            elif payload.get("ok") is False:
                queue_error = str(payload.get("error") or "queue returned ok=false")
                findings.append("queue probe failed: %s" % queue_error)
            else:
                tasks = payload.get("tasks") or payload.get("ready") or []
                if not isinstance(tasks, list):
                    queue_error = "queue tasks is not a list"
                    findings.append(queue_error)
                else:
                    ready_n = len(tasks)

        deferred_n: Optional[int] = None
        deferred_error = ""
        if product and queue_url:
            deferred_url = _deferred_backlog_url(queue_url, product)
            cache_key = (deferred_url, product)
            if cache_key not in deferred_cache:
                deferred_cache[cache_key] = _probe_json(deferred_url, timeout=timeout)
            deferred_status, deferred_payload, deferred_error = deferred_cache[cache_key]
            if deferred_payload is None:
                findings.append(
                    "deferred backlog probe failed: %s"
                    % (deferred_error or "HTTP %s" % deferred_status)
                )
            elif deferred_payload.get("ok") is False:
                deferred_error = str(
                    deferred_payload.get("error") or "deferred query returned ok=false"
                )
                findings.append("deferred backlog probe failed: %s" % deferred_error)
            else:
                tasks = deferred_payload.get("tasks") or []
                if not isinstance(tasks, list):
                    deferred_error = "deferred backlog tasks is not a list"
                    findings.append(deferred_error)
                else:
                    expected = "worker:%s" % worker_id
                    deferred_n = sum(
                        1
                        for task in tasks
                        if isinstance(task, dict)
                        and str(task.get("gate_type") or "").lower() == "deferred"
                        and any(
                            str(label).lower() == expected.lower()
                            for label in (task.get("labels") or [])
                        )
                    )
                    if ready_n == 0 and deferred_n > 0:
                        findings.append(
                            "empty feed with %d deferred backlog item(s)" % deferred_n
                        )

        lanes.append(
            {
                "worker": worker_id,
                "product": product,
                "schedule": str(row.get("schedule") or ""),
                "queue_url": queue_url,
                "http_status": http_status,
                "ready_n": ready_n,
                "deferred_n": deferred_n,
                "findings": findings,
            }
        )
    issue_lanes = [lane for lane in lanes if lane.get("findings")]
    return {
        "ok": not issue_lanes,
        "roster": roster_path,
        "lane_n": len(lanes),
        "issue_lane_n": len(issue_lanes),
        "lanes": lanes,
        "hint": (
            "wrong queue_url shape silences a hand; empty ready plus deferred work "
            "is a parking smell, not proof that the seat needs more work"
        ),
    }


def audit_process(
    roster: str = "",
    city_root: Optional[Path] = None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    roster_path, workers, error = load_roster(roster, city_root=city_root)
    if error:
        return {
            "ok": False,
            "roster": roster_path,
            "lane_n": 0,
            "issue_lane_n": 1,
            "lanes": [],
            "error": error,
        }
    return audit_process_workers(workers, roster_path, timeout=timeout)


def _workspace_root_candidates(
    city_root: Optional[Path] = None, *, strict: bool = False
) -> List[Path]:
    """Prefer founded workspace root, then package parent / cwd.

    When ``strict`` and ``city_root`` is set, only that root is searched
    (tests / planted fixtures must not fall through to the host package tree).
    """
    roots: List[Path] = []
    if city_root is not None:
        roots.append(Path(city_root).expanduser().resolve())
        if strict:
            return roots
    env = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if env:
        roots.append(Path(env).expanduser().resolve())
    package_parent = Path(__file__).resolve().parent.parent
    cwd = Path.cwd().resolve()
    for root in (package_parent, cwd, cwd.parent):
        if root not in roots:
            roots.append(root)
    return roots


def _find_skills_sync(city_root: Optional[Path] = None) -> Optional[Path]:
    strict = city_root is not None
    for root in _workspace_root_candidates(city_root, strict=strict):
        for rel in (
            Path("scripts") / "skills_sync.sh",
            Path("ProtocolCity") / "scripts" / "skills_sync.sh",
        ):
            candidate = root / rel
            if candidate.is_file():
                return candidate
    return None


def _find_always_work_law(city_root: Optional[Path] = None) -> Optional[Path]:
    strict = city_root is not None
    for root in _workspace_root_candidates(city_root, strict=strict):
        for rel in (
            Path("docs") / "specs" / "ALWAYS_WORK_PROCESS.md",
            Path("ProtocolCity") / "docs" / "specs" / "ALWAYS_WORK_PROCESS.md",
        ):
            candidate = root / rel
            if candidate.is_file():
                return candidate
    return None


def parse_always_work_section9(text: str) -> List[Dict[str, Any]]:
    """Parse ALWAYS_WORK §9 implement-backlog table rows.

    Rows marked **Landed** are done; others are pending enforcement gaps.
    """
    match = _SECTION9_HEADER_RE.search(text)
    if not match:
        return []
    rest = text[match.end() :]
    next_h = _SECTION_NEXT_RE.search(rest)
    body = rest[: next_h.start()] if next_h else rest
    rows: List[Dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue
        item = m.group(1).strip()
        intent = m.group(2).strip()
        if item.lower() in ("item", "---", "----") or set(item) <= {"-"}:
            continue
        if intent.lower() in ("intent", "---") or set(intent) <= {"-"}:
            continue
        landed = bool(_LANDED_RE.search(item) or _LANDED_RE.search(intent))
        rows.append(
            {
                "item": item,
                "intent": intent,
                "landed": landed,
                "pending": not landed,
            }
        )
    return rows


def run_skills_sync_check(
    city_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Call ``skills_sync.sh --check`` (heal is the job's write, not this probe)."""
    script = _find_skills_sync(city_root)
    if script is None:
        return {
            "ok": False,
            "skipped": True,
            "rc": None,
            "detail": "skills_sync.sh not found under workspace candidates",
            "script": "",
        }
    try:
        proc = subprocess.run(
            ["bash", str(script), "--check"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(script.parent.parent),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "skipped": False,
            "rc": None,
            "detail": str(exc),
            "script": str(script),
        }
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    detail = out or err or ("rc=%s" % proc.returncode)
    return {
        "ok": proc.returncode == 0,
        "skipped": False,
        "rc": int(proc.returncode),
        "detail": detail[:500],
        "script": str(script),
    }


def _list_tasks_for_label(
    product: str,
    label: str,
    *,
    status: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """List tasks for product/label/status via WorkLane admin API."""
    q = urllib.parse.urlencode(
        {
            "product": product,
            "label": label,
            "status": status,
            "limit": "100",
        }
    )
    for base in (
        "http://127.0.0.1:8799/api/admin/tasks",
        "http://127.0.0.1:8801/api/admin/tasks",
    ):
        payload = _get("%s?%s" % (base, q), timeout=timeout)
        if not payload:
            continue
        tasks = payload if isinstance(payload, list) else payload.get("tasks")
        if isinstance(tasks, list):
            return [t for t in tasks if isinstance(t, dict)]
    return []


def audit_retired_seats(
    products: Sequence[str],
    retired_ids: Sequence[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Open tickets still labeled worker:<retired> (succession drift)."""
    hits: List[Dict[str, Any]] = []
    statuses = ("backlog", "in_progress", "in_review")
    for product in products:
        for retired in retired_ids:
            label = "worker:%s" % retired
            for status in statuses:
                for task in _list_tasks_for_label(
                    product, label, status=status, timeout=timeout
                ):
                    hits.append(
                        {
                            "id": task.get("id") or task.get("task_id"),
                            "product": product,
                            "status": status,
                            "retired": retired,
                            "title": (task.get("title") or "")[:80],
                        }
                    )
    return {
        "retired_ids": list(retired_ids),
        "hit_n": len(hits),
        "hits": hits[:40],
    }


def audit_decay(
    *,
    city_root: Optional[Path] = None,
    products: Optional[Sequence[str]] = None,
    retired_ids: Optional[Sequence[str]] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Process-decay patrol: law-vs-enforcement drift (pc-965).

    Bounded probes only — does not heal or file tickets. Callers (skill / job)
    report findings and file classed WOs; never mass-fix from this function.
    """
    skills = run_skills_sync_check(city_root)
    law_path = _find_always_work_law(city_root)
    section9_rows: List[Dict[str, Any]] = []
    section9_pending: List[Dict[str, Any]] = []
    section9_error = ""
    if law_path is None:
        section9_error = "ALWAYS_WORK_PROCESS.md not found"
    else:
        try:
            text = law_path.read_text(encoding="utf-8")
            section9_rows = parse_always_work_section9(text)
            section9_pending = [r for r in section9_rows if r.get("pending")]
        except OSError as exc:
            section9_error = str(exc)

    retired = list(retired_ids) if retired_ids is not None else sorted(
        DEFAULT_RETIRED_WORKER_IDS
    )
    prods = list(products) if products else ["protocolcity"]
    retired_report = audit_retired_seats(prods, retired, timeout=timeout)

    findings: List[str] = []
    if not skills.get("skipped") and not skills.get("ok"):
        findings.append("skills_sync_check_failed")
    if skills.get("skipped"):
        findings.append("skills_sync_missing")
    if section9_error:
        findings.append("section9_unreadable")
    if section9_pending:
        findings.append("section9_pending_rows")
    if int(retired_report.get("hit_n") or 0) > 0:
        findings.append("retired_seats_on_open_work")

    smell_n = len(findings)
    return {
        "ok": smell_n == 0,
        "smell_n": smell_n,
        "findings": findings,
        "skills_sync": skills,
        "section9": {
            "law": str(law_path) if law_path else "",
            "error": section9_error,
            "row_n": len(section9_rows),
            "pending_n": len(section9_pending),
            "pending": [
                {"item": r["item"], "intent": r["intent"]}
                for r in section9_pending
            ],
        },
        "retired_seats": retired_report,
        "hint": (
            "On decay: report + file classed routed WOs (or one workspace "
            "rollup For You card per ALWAYS_WORK §2i). Never mass-fix from "
            "the efficiency job."
        ),
        "rollup_policy": (
            "One workspace rollup card when decay is found — no per-item gold spam"
        ),
    }


def load_scene(
    urls: List[str], *, timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """Return first reachable scene payload, or None when engines are down."""
    for u in urls:
        d = _get(u, timeout=timeout)
        if d and (d.get("stores") is not None or d.get("ok") is not False):
            return d
    return None


def _worker_seat(labels: List[Any]) -> str:
    for lab in labels or []:
        s = str(lab).strip()
        if s.lower().startswith("worker:"):
            return s
    return "(none)"


def _is_you_starve(labels: List[Any]) -> bool:
    """True when ready work is bare worker:you (no you-kind, no founder gate).

    Classified You parks (you:note|remind|todo|host) and founder/publish gates
    are intentional. Bare worker:you is starve (wl-315 / workspace-efficiency).
    """
    labs = [str(x).strip() for x in (labels or []) if str(x).strip()]
    if not any(str(x).lower() == "worker:you" for x in labs):
        return False
    low = {x.lower() for x in labs}
    if low & _YOU_KINDS:
        return False
    if low & _FOUNDER_MARKERS or any(x.startswith("gate:founder") for x in low):
        return False
    return True


def fetch_ready_product(
    product: str, limit: int = 80, *, timeout: float = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    q = urllib.parse.urlencode({"product": product, "limit": str(limit)})
    d = _get(f"http://127.0.0.1:8799/api/admin/tasks/ready?{q}", timeout=timeout)
    if not d:
        return []
    tasks = d.get("tasks") or d.get("ready") or []
    return [t for t in tasks if isinstance(t, dict)]


def fetch_tasks_status(
    product: str,
    status: str,
    limit: int = 100,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    q = urllib.parse.urlencode(
        {"product": product, "status": status, "limit": str(limit)}
    )
    d = _get(f"http://127.0.0.1:8801/api/tasks?{q}", timeout=timeout) or _get(
        f"http://127.0.0.1:8799/api/admin/tasks?{q}", timeout=timeout
    )
    if not d:
        return []
    tasks = d.get("tasks") or []
    return [t for t in tasks if isinstance(t, dict)]


def classify_you_ticket(labels: List[Any]) -> str:
    """Return class for worker:you tickets: starve|list|host|founder|other."""
    labs = [str(x).strip() for x in (labels or []) if str(x).strip()]
    if not any(x.lower() == "worker:you" for x in labs):
        return ""
    low = {x.lower() for x in labs}
    if low & ({"you:note", "you:remind", "you:todo"}):
        return "list"
    if low & _FOUNDER_MARKERS or any(x.startswith("gate:founder") for x in low):
        return "founder"
    if "you:host" in low:
        return "host"
    if _is_you_starve(labs):
        return "starve"
    return "other"


def audit_history(
    products: List[str],
    limit: int = 80,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Scan open statuses + recent done for worker:you pattern mixups."""
    by_class: Counter = Counter()
    samples: Dict[str, List[Dict[str, Any]]] = {
        "starve": [],
        "host": [],
        "list": [],
        "founder": [],
        "other": [],
    }
    total_you = 0
    for prod in products:
        for st in ("backlog", "in_progress", "in_review", "done"):
            tasks = fetch_tasks_status(prod, st, limit=limit, timeout=timeout)
            for t in tasks:
                labs = t.get("labels") or []
                cls = classify_you_ticket(labs)
                if not cls:
                    continue
                total_you += 1
                by_class[cls] += 1
                bucket = samples.get(cls) or samples["other"]
                if len(bucket) < 12:
                    bucket.append(
                        {
                            "id": t.get("id"),
                            "status": st,
                            "product": prod,
                            "class": cls,
                            "title": (t.get("title") or "")[:72],
                            "labels": labs,
                        }
                    )
    return {
        "total_worker_you": total_you,
        "by_class": dict(by_class),
        "samples": samples,
        "hint": (
            "starve/host dumps = mis-assign; list/founder = OK; "
            "escalate should use gate_type=human + keep hand seat, not worker:you"
        ),
    }


def audit_feeds(
    products: List[str], *, timeout: float = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    by_product: Dict[str, Any] = {}
    starve: List[Dict[str, Any]] = []
    seat_hist: Counter = Counter()
    for prod in products:
        tasks = fetch_ready_product(prod, timeout=timeout)
        seats: Counter = Counter()
        for t in tasks:
            labs = t.get("labels") or []
            seat = _worker_seat(labs)
            seats[seat] += 1
            seat_hist[seat] += 1
            if _is_you_starve(labs):
                starve.append(
                    {
                        "id": t.get("id"),
                        "product": prod,
                        "title": (t.get("title") or "")[:80],
                        "labels": labs,
                    }
                )
        by_product[prod] = {
            "ready_n": len(tasks),
            "by_seat": dict(seats),
            "needs_routing": 0,
        }
        nr = sum(
            1
            for t in tasks
            if any(str(x).lower() == "needs:routing" for x in (t.get("labels") or []))
        )
        by_product[prod]["needs_routing"] = nr

    return {
        "by_product": by_product,
        "you_starve": starve,
        "you_starve_n": len(starve),
        "seat_totals": dict(seat_hist),
    }


def run_audit(
    *,
    urls: Optional[List[str]] = None,
    feeds: bool = False,
    history: bool = False,
    process: bool = False,
    decay: bool = False,
    roster: str = "",
    city_root: Optional[Path] = None,
    timeout: float = DEFAULT_TIMEOUT,
    history_limit: int = 40,
) -> Dict[str, Any]:
    """Run open-work audit. Never raises SystemExit; offline → reachable=False.

    Used by ``blueprint doctor`` (feeds+history on by default) and the CLI.
    ``decay`` probes still run when the board is offline (disk checks).
    """
    scene_urls = list(urls) if urls else list(DEFAULT_SCENE)
    scene = load_scene(scene_urls, timeout=timeout)
    if scene is None:
        out_offline: Dict[str, Any] = {
            "ok": False,
            "reachable": False,
            "total_open": 0,
            "total_ready": 0,
            "total_in_motion": 0,
            "projects": [],
            "note": "suite/WL offline — start with: blueprint serve",
            "law": "docs/specs/ALWAYS_WORK_PROCESS.md",
            "skill": ".agents/skills/workspace-efficiency/SKILL.md (or scripts/ after found plant)",
            "hints": [
                "Ready with no claims → check worker:* labels and hand schedules",
                "worker:you never drains while You are away (wl-315 starve rule)",
                "Empty shifts with ready open elsewhere → routing bug, not hire more",
                "For You is gate_type=human only — not all open work",
            ],
        }
        if decay:
            out_offline["decay"] = audit_decay(
                city_root=city_root, products=[], timeout=timeout
            )
        return out_offline

    stores = scene.get("stores") or []
    rows: List[Dict[str, Any]] = []
    total_open = 0
    total_ready = 0
    total_ip = 0
    products: List[str] = []
    for s in stores:
        if not isinstance(s, dict):
            continue
        slug = str(s.get("slug") or s.get("product") or "?")
        bl = int(s.get("backlog") or 0)
        ip = int(s.get("in_progress") or 0)
        ir = int(s.get("in_review") or 0)
        ready = int(s.get("ready") or 0)
        open_n = bl + ip + ir
        total_open += open_n
        total_ready += ready
        total_ip += ip + ir
        if open_n or ready:
            products.append(slug)
        rows.append(
            {
                "project": slug,
                "open": open_n,
                "backlog": bl,
                "in_progress": ip,
                "in_review": ir,
                "ready": ready,
                "done": s.get("done_total")
                if s.get("done_total") is not None
                else s.get("done"),
            }
        )
    rows.sort(key=lambda r: (-int(r["open"]), str(r["project"])))
    out: Dict[str, Any] = {
        "ok": True,
        "reachable": True,
        "total_open": total_open,
        "total_ready": total_ready,
        "total_in_motion": total_ip,
        "projects": rows,
        "law": "docs/specs/ALWAYS_WORK_PROCESS.md",
        "skill": ".agents/skills/workspace-efficiency/SKILL.md (or scripts/ after found plant)",
        "hints": [
            "Ready with no claims → check worker:* labels and hand schedules",
            "worker:you never drains while You are away (wl-315 starve rule)",
            "Empty shifts with ready open elsewhere → routing bug, not hire more",
            "For You is gate_type=human only — not all open work",
        ],
    }
    prods_scan = [r["project"] for r in rows if int(r.get("open") or 0) > 0]
    if not prods_scan:
        prods_scan = products

    if feeds:
        prods = [r["project"] for r in rows if int(r.get("ready") or 0) > 0]
        if not prods:
            prods = prods_scan
        out["feeds"] = audit_feeds(prods, timeout=timeout)

    if history:
        out["history"] = audit_history(
            prods_scan, limit=history_limit, timeout=timeout
        )

    if process:
        out["process"] = audit_process(
            roster, city_root=city_root, timeout=timeout
        )

    if decay:
        out["decay"] = audit_decay(
            city_root=city_root,
            products=prods_scan or products or ["protocolcity"],
            timeout=timeout,
        )

    return out


def print_audit_text(out: Dict[str, Any]) -> None:
    """Human-readable audit print (CLI and doctor section)."""
    if not out.get("reachable", True) and not out.get("ok"):
        print("Workspace open-work audit")
        print("  (suite/WL offline — start with: blueprint serve)")
        return

    total_open = int(out.get("total_open") or 0)
    total_ready = int(out.get("total_ready") or 0)
    total_ip = int(out.get("total_in_motion") or 0)
    rows = out.get("projects") or []
    print("Workspace open-work audit")
    print(f"  open={total_open}  ready={total_ready}  in_motion={total_ip}")
    print(f"  {'project':<16} {'open':>5} {'ready':>5} {'ip':>4} {'ir':>4} {'bl':>5}")
    print("  " + "-" * 48)
    for r in rows:
        if int(r["open"]) == 0 and int(r["ready"]) == 0:
            continue
        print(
            f"  {r['project']:<16} {r['open']:>5} {r['ready']:>5} "
            f"{r['in_progress']:>4} {r['in_review']:>4} {r['backlog']:>5}"
        )

    if out.get("feeds"):
        feeds = out["feeds"]
        print()
        print("Ready feeds by seat")
        for prod, info in (feeds.get("by_product") or {}).items():
            if not info.get("ready_n"):
                continue
            print(f"  {prod}: n={info['ready_n']}  {info.get('by_seat')}")
        sn = int(feeds.get("you_starve_n") or 0)
        print()
        print(f"You-starve ready (implement park on You seat): {sn}")
        for t in feeds.get("you_starve") or []:
            print(f"  {t.get('id')}  {(t.get('title') or '')[:56]}")
        if sn == 0:
            print("  (none — good)")

    if out.get("history"):
        hist = out["history"]
        print()
        print(
            f"History worker:you (open+recent done): n={hist.get('total_worker_you')}  "
            f"{hist.get('by_class')}"
        )
        print(f"  hint: {hist.get('hint')}")
        for cls in ("starve", "host", "list", "founder"):
            samples = (hist.get("samples") or {}).get(cls) or []
            if not samples:
                continue
            print(f"  · {cls}:")
            for t in samples[:6]:
                print(
                    f"      {t.get('id')} [{t.get('status')}] "
                    f"{(t.get('title') or '')[:52]}"
                )

    if out.get("process"):
        process = out["process"]
        print()
        print("Lane process feeds")
        print(f"  roster: {process.get('roster') or '(not found)'}")
        print(
            f"  lanes={process.get('lane_n', 0)}  "
            f"issue_lanes={process.get('issue_lane_n', 0)}"
        )
        if process.get("error"):
            print(f"  ! {process.get('error')}")
        for lane in process.get("lanes") or []:
            status = lane.get("http_status")
            print(
                f"  {lane.get('worker'):<20} {lane.get('product') or '?':<16} "
                f"http={status if status is not None else '-'}  "
                f"ready={lane.get('ready_n') if lane.get('ready_n') is not None else '-'}  "
                f"deferred={lane.get('deferred_n') if lane.get('deferred_n') is not None else '-'}"
            )
            for finding in lane.get("findings") or []:
                print(f"    ! {finding}")
        if not process.get("issue_lane_n"):
            print("  (all lane feeds healthy)")
        if process.get("hint"):
            print(f"  hint: {process.get('hint')}")

    if out.get("decay"):
        decay = out["decay"]
        print()
        print("Process decay (law-vs-enforcement)")
        print(
            f"  ok={'yes' if decay.get('ok') else 'no'}  "
            f"smells={decay.get('smell_n', 0)}"
        )
        skills = decay.get("skills_sync") or {}
        if skills.get("skipped"):
            print(f"  skills_sync: skipped — {skills.get('detail')}")
        else:
            print(
                f"  skills_sync: {'ok' if skills.get('ok') else 'FAIL'}  "
                f"rc={skills.get('rc')}  {(skills.get('detail') or '')[:80]}"
            )
        s9 = decay.get("section9") or {}
        if s9.get("error"):
            print(f"  §9: error — {s9.get('error')}")
        else:
            print(
                f"  §9: rows={s9.get('row_n', 0)}  "
                f"pending={s9.get('pending_n', 0)}"
            )
            for row in s9.get("pending") or []:
                print(f"    · {(row.get('item') or '')[:72]}")
        retired = decay.get("retired_seats") or {}
        print(
            f"  retired seats on open work: n={retired.get('hit_n', 0)}  "
            f"ids={retired.get('retired_ids')}"
        )
        for hit in retired.get("hits") or []:
            print(
                f"    · {hit.get('id')} [{hit.get('status')}] "
                f"worker:{hit.get('retired')}  {(hit.get('title') or '')[:48]}"
            )
        if decay.get("findings"):
            print(f"  findings: {', '.join(decay.get('findings') or [])}")
        if decay.get("hint"):
            print(f"  hint: {decay.get('hint')}")
        if decay.get("rollup_policy"):
            print(f"  rollup: {decay.get('rollup_policy')}")

    print()
    print("Law: docs/specs/ALWAYS_WORK_PROCESS.md")
    print("Skill: .agents/skills/workspace-efficiency/")
    print("Skills bridge: scripts/skills_sync.sh (or ProtocolCity/scripts/skills_sync.sh)")
    for h in out.get("hints") or []:
        print(f"  · {h}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace', default=os.environ.get('WORKSPACE_ROOT', ''),
                    help='Explicit workspace root; prevents roster discovery in another workspace')
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    ap.add_argument(
        "--feeds",
        action="store_true",
        help="Also scan ready feeds per product (worker seats + You-starve)",
    )
    ap.add_argument(
        "--history",
        action="store_true",
        help="Scan open+recent done for worker:you mixups (assign vs list vs escalate)",
    )
    ap.add_argument(
        "--process",
        action="store_true",
        help="Probe lane queue_url health and empty feeds with deferred backlog",
    )
    ap.add_argument(
        "--decay",
        action="store_true",
        help=(
            "Process-decay patrol (pc-965): skills_sync --check, ALWAYS_WORK §9 "
            "pending rows, retired worker seats on open work"
        ),
    )
    ap.add_argument(
        "--roster",
        default="",
        help="WorkForce roster.json path for --process (otherwise auto-detected)",
    )
    ap.add_argument(
        "--url",
        action="append",
        default=[],
        help="Scene URL (repeatable). Defaults to suite then Desk.",
    )
    args = ap.parse_args()
    urls = args.url or list(DEFAULT_SCENE)
    out = run_audit(
        urls=urls,
        feeds=bool(args.feeds),
        history=bool(args.history),
        process=bool(args.process),
        decay=bool(args.decay),
        roster=args.roster or "",
        timeout=DEFAULT_TIMEOUT,
        city_root=Path(args.workspace).expanduser().resolve() if args.workspace else None,
    )
    if not out.get("reachable", True):
        msg = out.get("note") or (
            "No scene reachable. Start the suite (blueprint serve) or Desk, then retry."
        )
        if args.json:
            json.dump(out, sys.stdout, indent=2)
            sys.stdout.write("\n")
            # Still useful when --decay ran disk checks
            return 1
        if out.get("decay"):
            print_audit_text(out)
            return 1
        print(msg, file=sys.stderr)
        return 1

    if args.json:
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print_audit_text(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
