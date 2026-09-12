"""Daily workspace digest: dated markdown + optional ntfy push (pc-712 / pc-711).

Writes {ws}/.protocolcity/digests/YYYY-MM-DD.md and optionally fires a
≤500-char ntfy summary. Dry-runs silently when ntfy is not configured.

Config precedence — workspace-scoped wins:
  {ws}/.protocolcity/digest.json > ~/.protocolcity/digest.json

Schema:
  {
    "schedule":           "0 8 * * *",
    "workspace":          true,
    "projects":           ["tradeos", "protocolcity"],
    "include_done_hours": 24,
    "ntfy_topic":         "",
    "pulse_paths": [
      {
        "label": "tradeOS · maru desk brief",
        "path":  "tradeOS/local/reports/maru/{date}-desk-brief.md"
      }
    ]
  }

pulse_paths (pc-899): optional Project pulses footer. Each entry is a string
path template or {label, path}. Templates may use {date} (YYYY-MM-DD).
When the key is omitted, known default slots are scanned. Section is omitted
entirely when no matching file exists on disk (no second For You gold card).
"""
from __future__ import annotations

import datetime
import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

_DESK = os.environ.get("CITY_DESK", "http://127.0.0.1:8799")
_WORKFORCE = os.environ.get("CITY_WORKFORCE", "http://127.0.0.1:8797")

_DIGEST_JOB: Dict[str, str] = {
    "name": "digest",
    "role": "daily workspace digest",
    "schedule": "0 8 * * *",
    "kind": "job",
}

# Known on-disk report slots linked from the digest when present (not gold).
# Override / extend via digest.json "pulse_paths".
_DEFAULT_PULSE_PATHS: List[Dict[str, str]] = [
    {
        "label": "tradeOS · maru desk brief",
        "path": "tradeOS/local/reports/maru/{date}-desk-brief.md",
    },
]


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get_json(url: str, timeout: float = 5.0) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


# ── Config ────────────────────────────────────────────────────────────────────

def _find_config(name: str, city_root: Optional[Path]) -> Optional[Path]:
    if city_root is not None:
        p = Path(city_root).expanduser().resolve() / ".protocolcity" / name
        if p.is_file():
            return p
    p = Path.home() / ".protocolcity" / name
    return p if p.is_file() else None


def load_digest_config(city_root: Optional[Path] = None) -> dict:
    """Load digest config. Returns {} when not found or unparseable."""
    p = _find_config("digest.json", city_root)
    if p is None:
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _fetch_done(*, product: Optional[str] = None, since_hours: int = 24) -> List[dict]:
    q = "status=done&limit=200"
    if product:
        q += "&product=%s" % product
    data = _get_json("%s/api/admin/tasks?%s" % (_DESK, q)) or {}
    tasks = data.get("tasks") or []
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=since_hours)
    out = []
    for t in tasks:
        ts_str = (t.get("updated_at") or "").replace("Z", "+00:00")
        try:
            if datetime.datetime.fromisoformat(ts_str) >= cutoff:
                out.append(t)
        except Exception:
            pass
    return out


def _fetch_in_progress(*, product: Optional[str] = None) -> List[dict]:
    q = "status=in_progress&limit=100"
    if product:
        q += "&product=%s" % product
    data = _get_json("%s/api/admin/tasks?%s" % (_DESK, q)) or {}
    return data.get("tasks") or []


def _fetch_attention() -> List[dict]:
    data = _get_json("%s/api/dev/attention" % _DESK, timeout=6.0) or {}
    return data.get("items") or []


def _fetch_workforce() -> dict:
    return _get_json("%s/api/scene?light=1" % _WORKFORCE, timeout=4.0) or {}


# ── Formatting helpers ────────────────────────────────────────────────────────

def _store_prefix(task: dict) -> str:
    tid = task.get("id") or ""
    return tid.rsplit("-", 1)[0] if "-" in tid else ""


def _worker_label(task: dict) -> str:
    for lbl in (task.get("labels") or []):
        if str(lbl).startswith("worker:"):
            return str(lbl)[len("worker:"):]
    return ""


def _age_str(task: dict) -> str:
    ts_str = (task.get("updated_at") or task.get("created_at") or "").replace("Z", "+00:00")
    try:
        delta = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ts_str)
        h = int(delta.total_seconds() // 3600)
        return ("%dh" % h) if h < 24 else ("%dd" % (h // 24))
    except Exception:
        return ""


def _task_line(task: dict, *, show_age: bool = False) -> str:
    store = _store_prefix(task)
    title = (task.get("title") or "").strip()
    worker = _worker_label(task)
    age = _age_str(task) if show_age else ""
    meta = ", ".join(x for x in [worker, age] if x)
    suffix = " (%s)" % meta if meta else ""
    prefix = "[%s] " % store if store else ""
    return "- %s%s%s" % (prefix, title, suffix)


def _attention_line(item: dict) -> str:
    tid = item.get("id") or ""
    store = tid.rsplit("-", 1)[0] if "-" in tid else ""
    title = (item.get("title") or "").strip()
    note = (item.get("note") or "").strip()
    suffix = " — %s" % note if note else ""
    prefix = "[%s] " % store if store else ""
    return "- %s%s%s" % (prefix, title, suffix)


# ── Section builders ──────────────────────────────────────────────────────────

def _ws_section(
    done: List[dict],
    attention: List[dict],
    in_progress: List[dict],
    agents: dict,
    since_hours: int,
) -> str:
    lines: List[str] = []

    lines.append("## Done (last %d h)" % since_hours)
    if done:
        lines.extend(_task_line(t) for t in done)
    else:
        lines.append("_none_")

    gold = [it for it in attention if it.get("kind") == "human_gate"]
    lines += ["", "## For You"]
    if gold:
        lines.extend(_attention_line(it) for it in gold)
    else:
        lines.append("_none_")

    lines += ["", "## In Progress"]
    if in_progress:
        lines.extend(_task_line(t, show_age=True) for t in in_progress)
    else:
        lines.append("_none_")

    in_flight = agents.get("in_flight") or []
    live = len(in_flight) if isinstance(in_flight, list) else 0
    lines += ["", "## Agents", "- live: %d" % live]
    if isinstance(in_flight, list):
        for name in in_flight:
            lines.append("  - %s" % name)

    return "\n".join(lines)


def _project_section(
    slug: str,
    done: List[dict],
    in_progress: List[dict],
    attention: List[dict],
) -> str:
    lines = ["## %s" % slug, "### Done"]
    if done:
        lines.extend(_task_line(t) for t in done)
    else:
        lines.append("_none_")

    proj_att = [it for it in attention if (it.get("product") or "") == slug and it.get("kind") == "human_gate"]
    lines += ["", "### Open / In Progress"]
    if in_progress:
        lines.extend(_task_line(t, show_age=True) for t in in_progress)
    else:
        lines.append("_none_")

    lines += ["", "### For You"]
    if proj_att:
        lines.extend(_attention_line(it) for it in proj_att)
    else:
        lines.append("_none_")

    return "\n".join(lines)


def _normalize_pulse_entries(
    raw: Optional[Sequence[Union[str, dict]]],
) -> List[Dict[str, str]]:
    """Normalize config/default pulse entries to [{label, path}, ...]."""
    if raw is None:
        return [dict(e) for e in _DEFAULT_PULSE_PATHS]
    out: List[Dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            path = item.strip()
            if path:
                out.append({"label": path, "path": path})
        elif isinstance(item, dict):
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            label = str(item.get("label") or path).strip() or path
            out.append({"label": label, "path": path})
    return out


def _resolve_pulse_hits(
    city_root: Path,
    date_str: str,
    entries: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Return {label, rel_path, abs_path} for pulse templates whose file exists."""
    root = Path(city_root).expanduser().resolve()
    hits: List[Dict[str, str]] = []
    for entry in entries:
        template = entry.get("path") or ""
        rel = template.replace("{date}", date_str)
        if not rel:
            continue
        abs_path = (root / rel).resolve()
        # Stay under workspace root (reject path escape).
        try:
            abs_path.relative_to(root)
        except ValueError:
            continue
        if abs_path.is_file():
            hits.append(
                {
                    "label": entry.get("label") or rel,
                    "rel_path": rel,
                    "abs_path": str(abs_path),
                }
            )
    return hits


def _project_pulse_section(
    city_root: Optional[Path],
    date_str: str,
    *,
    config: Optional[dict] = None,
) -> str:
    """Optional **Project pulses** footer: paths to on-disk project reports.

    Omitted (empty string) when city_root is missing or no configured/default
    pulse file exists. Links only — does not mint For You gold cards.
    """
    if city_root is None:
        return ""
    cfg = config if config is not None else {}
    # Explicit empty list disables pulses; omitted key → defaults.
    if "pulse_paths" in cfg:
        entries = _normalize_pulse_entries(cfg.get("pulse_paths"))
    else:
        entries = _normalize_pulse_entries(None)
    if not entries:
        return ""
    hits = _resolve_pulse_hits(Path(city_root), date_str, entries)
    if not hits:
        return ""
    lines = ["## Project pulses"]
    for hit in hits:
        lines.append("- **%s** — `%s`" % (hit["label"], hit["rel_path"]))
    return "\n".join(lines)


# ── ntfy body ─────────────────────────────────────────────────────────────────

def _ntfy_body(
    date_str: str,
    city_name: str,
    done_ct: int,
    gold_ct: int,
    ip_ct: int,
    attention: List[dict],
    disk_path: Optional[str],
) -> str:
    gold = [it for it in attention if it.get("kind") == "human_gate"]
    parts = [
        "[%s] %s — %d done · %d For You · %d in-progress" % (
            date_str, city_name, done_ct, gold_ct, ip_ct),
    ]
    if gold:
        parts.append("")
        parts.append("For You:")
        for it in gold[:3]:
            tid = it.get("id") or ""
            title = (it.get("title") or "").strip()
            parts.append("• %s: %s" % (tid, title) if tid else "• %s" % title)
        if len(gold) > 3:
            parts.append("… and %d more" % (len(gold) - 3))
    if disk_path:
        parts += ["", "Full digest: %s" % disk_path]
    body = "\n".join(parts)
    return body[:497] + "…" if len(body) > 500 else body


# ── Public API ────────────────────────────────────────────────────────────────

def build_digest(city_root: Optional[Path] = None, *, config: Optional[dict] = None) -> dict:
    """Build the digest markdown and write to disk.

    Returns {md, disk_path, ntfy_body, done_count, for_you_count, in_progress_count}.
    """
    cfg = config if config is not None else load_digest_config(city_root)
    since_hours = int(cfg.get("include_done_hours") or 24)
    projects = list(cfg.get("projects") or [])
    include_ws = cfg.get("workspace", True)

    now_local = datetime.datetime.now()
    date_str = now_local.strftime("%Y-%m-%d")
    time_str = now_local.strftime("%H:%M")

    city_name = "Workspace"
    if city_root is not None:
        city_name = Path(city_root).resolve().name

    done_all = _fetch_done(since_hours=since_hours)
    ip_all = _fetch_in_progress()
    attention = _fetch_attention()
    agents = _fetch_workforce()

    done_ct = len(done_all)
    gold_ct = sum(1 for it in attention if it.get("kind") == "human_gate")
    ip_ct = len(ip_all)

    parts = [
        "# [%s] %s — daily digest" % (date_str, city_name),
        "_Generated: %s local · %d done · %d For You · %d in-progress_" % (
            time_str, done_ct, gold_ct, ip_ct),
        "",
    ]

    if include_ws:
        parts.append(_ws_section(done_all, attention, ip_all, agents, since_hours))
        parts.append("")

    for slug in projects:
        proj_done = _fetch_done(product=slug, since_hours=since_hours)
        proj_ip = _fetch_in_progress(product=slug)
        parts.append(_project_section(slug, proj_done, ip_all, attention))
        parts.append("")

    # Footer: on-disk project report links when present (pc-899).
    pulse = _project_pulse_section(city_root, date_str, config=cfg)
    if pulse:
        parts.append(pulse)
        parts.append("")

    md = "\n".join(parts).rstrip() + "\n"

    disk_path: Optional[str] = None
    if city_root is not None:
        digests_dir = Path(city_root).expanduser().resolve() / ".protocolcity" / "digests"
        digests_dir.mkdir(parents=True, exist_ok=True)
        p = digests_dir / ("%s.md" % date_str)
        p.write_text(md, encoding="utf-8")
        disk_path = str(p)

    ntfy_b = _ntfy_body(date_str, city_name, done_ct, gold_ct, ip_ct, attention, disk_path)

    return {
        "md": md,
        "disk_path": disk_path,
        "ntfy_body": ntfy_b,
        "city_name": city_name,
        "date_str": date_str,
        "done_count": done_ct,
        "for_you_count": gold_ct,
        "in_progress_count": ip_ct,
    }


def run_digest(
    city_root: Optional[Path] = None,
    *,
    dry_run: bool = False,
    quiet: bool = False,
) -> dict:
    """Build digest, write to disk, push ntfy. Returns receipt."""
    from protocolcity import ntfy as _ntfy  # lazy — ntfy.py may not be co-installed

    cfg = load_digest_config(city_root)
    result = build_digest(city_root, config=cfg)
    disk_path = result["disk_path"]
    date_str = result["date_str"]
    city_name = result["city_name"]
    ntfy_b = result["ntfy_body"]
    topic_override = (cfg.get("ntfy_topic") or "").strip() or None

    if not quiet and disk_path:
        print("digest: wrote %s" % disk_path)

    if dry_run:
        push_result: dict = {"ok": True, "dry_run": True, "reason": "cli_flag"}
    else:
        push_result = _ntfy.push(
            "[%s] %s — daily digest" % (date_str, city_name),
            ntfy_b,
            city_root=city_root,
            topic_override=topic_override,
        )

    if not quiet:
        if push_result.get("dry_run"):
            print("ntfy: dry-run (%s)" % push_result.get("reason", ""))
        elif push_result.get("ok"):
            print("ntfy: pushed (status %s)" % push_result.get("status", "?"))
        else:
            print("ntfy: error — %s" % push_result.get("error", "unknown"))

    # For You inbox: digest MD alone is invisible on Map — drop human-gate card
    inbox: dict = {"ok": False, "skipped": True}
    if disk_path and city_root is not None and not dry_run:
        try:
            from pathlib import Path as _P
            import importlib.util

            root = _P(city_root).expanduser().resolve()
            helper = root / "scripts" / "report_to_for_you.py"
            if not helper.is_file():
                helper = (
                    _P(__file__).resolve().parents[1] / "scripts" / "report_to_for_you.py"
                )
            if helper.is_file():
                # inline import without package path issues
                spec = importlib.util.spec_from_file_location(
                    "report_to_for_you", helper
                )
                mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
                assert spec and spec.loader
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                inbox = mod.drop_report(
                    workspace=root,
                    project="protocolcity",
                    key="workspace-digest",
                    title="Workspace · daily digest · %s" % date_str,
                    report_path=_P(disk_path),
                    day=date_str,
                    priority=2,
                )
                if not quiet:
                    print(
                        "for-you: %s %s"
                        % (inbox.get("action"), inbox.get("task_id") or "")
                    )
        except Exception as e:
            inbox = {"ok": False, "error": str(e)}
            if not quiet:
                print("for-you: skip (%s)" % e)

    return {
        "ok": True,
        "disk_path": disk_path,
        "done_count": result["done_count"],
        "for_you_count": result["for_you_count"],
        "in_progress_count": result["in_progress_count"],
        "push": push_result,
        "inbox": inbox,
    }


def install_digest_job(city_root: Path, *, quiet: bool = False) -> dict:
    """Hire the digest job on the WorkForce roster (idempotent)."""
    from protocolcity.seed_ops import seed_workspace_ops

    cfg = load_digest_config(city_root)
    schedule = (cfg.get("schedule") or _DIGEST_JOB["schedule"]).strip()
    job = dict(_DIGEST_JOB)
    job["schedule"] = schedule

    return seed_workspace_ops(city_root, jobs=[job], quiet=quiet)
