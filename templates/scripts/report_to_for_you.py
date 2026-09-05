#!/usr/bin/env python3
"""Drop a report into Map For You (human-gate inbox) for BluePrint workspaces.

Citizen model: For You is the workspace inbox — notes/reminders with snooze.
Reports that only land on disk are invisible. This tool creates or refreshes a
**human-gated** work order tagged to You so Map · You · FOR YOU lists it.

  # after writing a report
  python3 scripts/report_to_for_you.py \\
    --project myproject \\
    --key desk-brief \\
    --title "Desk brief · 2026-08-02" \\
    --path myproject/local/reports/2026-08-02-desk-brief.md \\
    --workspace /path/to/workspace

  # scan common report slots and drop missing inbox items for today
  python3 scripts/report_to_for_you.py --scan --workspace /path/to/workspace

  # per-product efficiency stays disk-only unless act-now smell 
  python3 scripts/report_to_for_you.py --scan --workspace /path/to/workspace --act-now

Idempotent: label ``inbox-report:<project>:<key>:<date>`` — re-run updates
description/title, does not spam duplicate gold items for the same day.

**Efficiency policy (FOR_YOU_INBOX_REPORTS / DAILY_REPORTS_MAP):**
engine ``efficiency-*``, Trading ``efficiency-pass``, ``suite-efficiency``,
per-project ``code-efficiency``, and the workspace ``workspace-efficiency``
rollup are **disk-only** by default.
Jobs still write dated reports; For You does not gold them. Opt in with
``--act-now`` only when a product has a true act-now smell (stuck hand,
critical feed failure).

**Dual-audience (FOR_YOU_INBOX_REPORTS §Dual-audience):**
every gold card body carries ``### Builder`` + ``### User`` (one holistic
card per project per day). ``--scan`` skips thin/all-ops product files
(``reason=thin_rollup``) instead of minting per-product gold; fold those
paths into one workspace thin-rollup card when any exist.

**One product gold / day :** Trading desk brief + HTML
glance + RSU pack are **one** human-gated card (key ``desk-brief``, same
idempotency label as Trading ``for_you_drop``). ``--scan`` does not mint a
second ``maru-desk-brief`` or a separate ``rsu-window`` gold. RSU alone
(no desk brief file) still golds once under ``desk-brief``. Efficiency /
board-validation and all efficiency keys stay disk-only unless ``--act-now``.

Requires Desk up (default http://127.0.0.1:8799). Sign as author=you (system
drop) or REPORT_TO_FOR_YOU_AUTHOR.

Inbox policy (keys, thin/disk-only, dual-audience body) lives in
``for_you_inbox_policy.py`` — imported and re-exported from this CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from for_you_inbox_policy import (  # re-export seam — callers keep these names
    _DESK_BRIEF_ALIASES,
    _read_glance,
    _slug_key,
    canonical_report_key,
    extract_dual_sections,
    format_dual_description,
    is_always_gold_key,
    is_disk_only_efficiency_key,
    is_disk_only_scan_key,
    is_folded_into_desk_key,
    is_thin_report,
    product_display_name,
)


DEFAULT_DESK = os.environ.get("WL_DESK_URL") or os.environ.get(
    "TP_DESK_URL", "http://127.0.0.1:8799"
)
DEFAULT_AUTHOR = os.environ.get("REPORT_TO_FOR_YOU_AUTHOR") or "you"


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _local_today() -> str:
    return date.today().isoformat()


def _req(
    method: str,
    url: str,
    body: Optional[dict] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(err)
        except Exception:
            return {"ok": False, "error": err or str(e)}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"ok": False, "error": str(e)}


def _rel_display(path: Path, workspace: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def _inbox_label(project: str, key: str, day: str) -> str:
    return "inbox-report:%s:%s:%s" % (
        _slug_key(project),
        _slug_key(key),
        day,
    )


def find_open_by_label(
    desk: str, project: str, label: str
) -> Optional[Dict[str, Any]]:
    q = urllib.parse.urlencode(
        {"product": project, "label": label, "limit": 20}
    )
    data = _req("GET", "%s/api/admin/tasks?%s" % (desk.rstrip("/"), q))
    tasks = data.get("tasks") or data.get("items") or []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        st = str(t.get("status") or "").lower()
        if st in ("canceled", "done", "cancelled"):
            continue
        labs = [str(x) for x in (t.get("labels") or [])]
        if label in labs:
            return t
    return None


def find_open_inbox_for_key(
    desk: str, project: str, key: str, day: str
) -> Optional[Dict[str, Any]]:
    """Open inbox card for key, including desk-brief / maru-desk-brief aliases."""
    keys = [canonical_report_key(key)]
    if keys[0] == "desk-brief":
        for alias in _DESK_BRIEF_ALIASES:
            if alias not in keys:
                keys.append(alias)
    for k in keys:
        found = find_open_by_label(desk, project, _inbox_label(project, k, day))
        if found:
            return found
    return None


def drop_report(
    *,
    workspace: Path,
    project: str,
    key: str,
    title: str,
    report_path: Path,
    desk: str = DEFAULT_DESK,
    author: str = DEFAULT_AUTHOR,
    day: Optional[str] = None,
    visual_path: Optional[Path] = None,
    related_paths: Optional[List[Path]] = None,
    priority: int = 3,
    extra_labels: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create or refresh a For You inbox item for one report."""
    workspace = workspace.expanduser().resolve()
    day = day or _local_today()
    # legacy maru-desk-brief / rsu-window → one desk-brief card
    key = canonical_report_key(key)
    label = _inbox_label(project, key, day)
    abs_path = report_path.expanduser()
    if not abs_path.is_absolute():
        abs_path = (workspace / abs_path).resolve()
    else:
        abs_path = abs_path.resolve()

    rel = _rel_display(abs_path, workspace)
    visual_line = ""
    if visual_path:
        vp = visual_path.expanduser()
        if not vp.is_absolute():
            vp = (workspace / vp).resolve()
        if vp.is_file():
            visual_line = "\n**Visual:** `%s`\n" % _rel_display(vp, workspace)
    if related_paths:
        extra_lines: List[str] = []
        for rp in related_paths:
            rpp = rp.expanduser()
            if not rpp.is_absolute():
                rpp = (workspace / rpp).resolve()
            else:
                rpp = rpp.resolve()
            if rpp.is_file():
                extra_lines.append(
                    "**Also:** `%s`\n" % _rel_display(rpp, workspace)
                )
        if extra_lines:
            visual_line = (visual_line or "\n") + "".join(extra_lines)

    full_title = title if title.startswith("Inbox ·") else ("Inbox · %s" % title)
    # Dual-audience body  — dig-in still uses REPORT face; **Report:**
    # path stays parseable for path buttons.
    description = format_dual_description(
        project=project,
        day=day,
        key=key,
        rel=rel,
        report_path=abs_path,
        visual_line=visual_line,
    )

    labels = [
        "worker:you",
        "you:todo",
        "inbox-report",
        label,
        "product:%s" % project,
    ]
    if extra_labels:
        for x in extra_labels:
            x = str(x).strip()
            if x and x not in labels:
                labels.append(x)

    existing = find_open_inbox_for_key(desk, project, key, day)
    receipt: Dict[str, Any] = {
        "ok": True,
        "project": project,
        "key": key,
        "day": day,
        "label": label,
        "path": rel,
        "action": "none",
    }

    if dry_run:
        receipt["action"] = "would_update" if existing else "would_create"
        receipt["existing_id"] = (existing or {}).get("id")
        return receipt

    if existing:
        tid = str(existing.get("id") or "")
        # Prefer composite id for PATCH
        patch_id = tid
        body = {
            "title": full_title[:200],
            "description": description,
            "gate_type": "human",
            "gate_note": "Report ready",
            "priority": priority,
        }
        out = _req(
            "PATCH",
            "%s/api/admin/tasks/%s?product=%s"
            % (desk.rstrip("/"), urllib.parse.quote(patch_id), project),
            body,
        )
        if not out.get("ok") and out.get("task") is None:
            # try bare id
            bare = tid.split("-")[-1] if "-" in tid else tid
            out = _req(
                "PATCH",
                "%s/api/admin/tasks/%s?product=%s"
                % (desk.rstrip("/"), bare, project),
                body,
            )
        receipt["action"] = "updated"
        receipt["task_id"] = (out.get("task") or existing).get("id")
        receipt["api"] = out
        return receipt

    create_body = {
        "title": full_title[:200],
        "description": description,
        "author": author,
        "labels": labels,
        "priority": priority,
        "intake": "report-to-for-you",
        "project": project,  # body + query — do not land everything on default store
    }
    out = _req(
        "POST",
        "%s/api/admin/tasks?product=%s" % (desk.rstrip("/"), project),
        create_body,
    )
    task = out.get("task") or {}
    tid = str(task.get("id") or "")
    if not tid:
        receipt["ok"] = False
        receipt["error"] = out.get("error") or out
        receipt["action"] = "create_failed"
        return receipt

    # Prefer composite id from list-by-label (create may return t-N)
    import time as _time

    listed = None
    for _ in range(4):
        _time.sleep(0.35)
        listed = find_open_by_label(desk, project, label)
        if listed and listed.get("id"):
            tid = str(listed.get("id"))
            break

    gate_ok = False
    for attempt in range(5):
        gout = _req(
            "PATCH",
            "%s/api/admin/tasks/%s?product=%s"
            % (desk.rstrip("/"), urllib.parse.quote(str(tid)), project),
            {
                "gate_type": "human",
                "gate_note": "Report ready",
            },
        )
        if gout.get("ok") or (gout.get("task") or {}).get("gate_type") == "human":
            gate_ok = True
            task = gout.get("task") or task
            break
        _time.sleep(0.8 * (attempt + 1))

    receipt["action"] = "created"
    receipt["task_id"] = (task or {}).get("id") or tid
    receipt["gate_ok"] = gate_ok
    if not gate_ok:
        receipt["ok"] = False
        receipt["error"] = "created but human gate not set — re-run drop or wl_update"
    receipt["api"] = out
    return receipt


def _first_existing(workspace: Path, candidates: List[str]) -> Optional[Path]:
    for c in candidates:
        p = workspace / c
        if p.is_file():
            return p
    return None


def _rsu_candidates(day: str, day_utc: str) -> List[str]:
    """Common RSU pack paths (folded into desk-brief gold, not separate)."""
    # Month pack + day-stamped variants
    month = (day or "")[:7] or "2026-08"
    month_utc = (day_utc or "")[:7] or month
    return [
        "Trading/local/reports/maru/%s-rsu-window.md" % month,
        "Trading/local/reports/maru/%s-rsu-window.md" % month_utc,
        "Trading/local/reports/maru/%s-rsu-window.md" % day,
        "Trading/local/reports/maru/%s-rsu-window.md" % day_utc,
        "Trading/local/reports/maru/2026-08-rsu-window.md",
    ]


def scan_and_drop(
    workspace: Path,
    *,
    desk: str,
    day: Optional[str] = None,
    dry_run: bool = False,
    act_now: bool = False,
) -> List[Dict[str, Any]]:
    """Drop For You items for known report slots that exist today.

    Efficiency / board-validation slots are disk-only unless ``act_now``
    . That includes workspace ``workspace-efficiency``.

    Thin / all-ops product files skip per-product gold  and
    fold into one workspace ``workspace-thin-rollup`` card when any exist.

    Trading product gold is one ``desk-brief`` card  — same key as
    ``for_you_drop``. RSU pack paths fold into that card; no second gold.
    """
    workspace = workspace.expanduser().resolve()
    day = day or _local_today()
    day_utc = _utc_today()
    results: List[Dict[str, Any]] = []
    thin_hits: List[Tuple[str, str, Path]] = []  # project, key, path

    # (project, key, title, path candidates, optional visual)
    # Disk-only efficiency keys still listed so --scan can report them as
    # skipped (and gold them only with --act-now).
    # Trading: one desk-brief slot (not maru + rsu) — .
    slots: List[Tuple[str, str, str, List[str], Optional[str]]] = [
        (
            "trading",
            "desk-brief",
            "Trading · desk brief · %s" % day,
            [
                "Trading/local/reports/maru/%s-desk-brief.md" % day,
                "Trading/local/reports/maru/%s-desk-brief.md" % day_utc,
            ],
            "Trading/local/reports/for-you/latest.html",
        ),
        # rsu-window listed only so scan can report folded/skip (not gold)
        (
            "trading",
            "rsu-window",
            "Trading · RSU window pack",
            _rsu_candidates(day, day_utc),
            "Trading/local/reports/for-you/latest.html",
        ),
        (
            "trading",
            "efficiency-pass",
            "Trading · efficiency pass · %s" % day,
            [
                "Trading/local/reports/efficiency-pass/%s.md" % day,
                "Trading/local/reports/efficiency-pass/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "trading",
            "board-validation",
            "Trading · board validation · %s" % day,
            [
                "Trading/local/reports/board-validation-%s.md" % day,
                "Trading/local/reports/board-validation-%s.md" % day_utc,
            ],
            None,
        ),
        (
            "protocolcity",
            "workspace-digest",
            "Workspace · daily digest · %s" % day,
            [
                ".protocolcity/digests/%s.md" % day,
                ".protocolcity/digests/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "protocolcity",
            "workspace-efficiency",
            "Workspace · efficiency · %s" % day,
            [
                ".protocolcity/ops/reports/workspace-efficiency/%s.md" % day,
                ".protocolcity/ops/reports/workspace-efficiency/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "protocolcity",
            "suite-efficiency",
            "BluePrint · suite efficiency · %s" % day,
            [
                "ProtocolCity/local/reports/suite-efficiency/%s.md" % day,
                "ProtocolCity/local/reports/suite-efficiency/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "register",
            "efficiency-register",
            "register · efficiency · %s" % day,
            [
                "register/local/reports/efficiency-register/%s.md" % day,
                "register/local/reports/efficiency-register/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "worklane",
            "efficiency-worklane",
            "WorkLane · efficiency · %s" % day,
            [
                "worklane/local/reports/efficiency-worklane/%s.md" % day,
                "worklane/local/reports/efficiency-worklane/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "workforce",
            "efficiency-workforce",
            "WorkForce · efficiency · %s" % day,
            [
                "workforce/local/reports/efficiency-workforce/%s.md" % day,
                "workforce/local/reports/efficiency-workforce/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "connector",
            "efficiency-connector",
            "Connector · efficiency · %s" % day,
            [
                "connector/local/reports/efficiency-connector/%s.md" % day,
                "connector/local/reports/efficiency-connector/%s.md" % day_utc,
            ],
            None,
        ),
        (
            "gridfinity",
            "efficiency-gridfinity",
            "gridfinity · efficiency · %s" % day,
            [
                "gridfinity/local/reports/efficiency-gridfinity/%s.md" % day,
                "gridfinity/local/reports/efficiency-gridfinity/%s.md" % day_utc,
            ],
            None,
        ),
    ]

    # Correspondent / clerk — prefer latest day files (rollup if many)
    corr_dir = workspace / ".protocolcity" / "ops" / "local" / "reports" / "correspondent"
    if corr_dir.is_dir():
        day_files = sorted(corr_dir.glob("*-%s.md" % day)) + sorted(
            corr_dir.glob("*-%s.md" % day_utc)
        )
        if day_files:
            # write curated rollup then drop once
            inbox_dir = workspace / ".protocolcity" / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            rollup = inbox_dir / ("%s-correspondent.md" % day)
            lines = [
                "# Correspondent rollup · %s\n" % day,
                "Ops narrative per project. Open any path for full report.\n\n",
            ]
            for f in day_files:
                rel = _rel_display(f, workspace)
                lines.append("## %s\n\n" % f.stem)
                lines.append("**Path:** `%s`\n\n" % rel)
                lines.append(_read_glance(f, max_lines=12, max_chars=600))
                lines.append("\n---\n\n")
            if not dry_run:
                rollup.write_text("".join(lines), encoding="utf-8")
            slots.append(
                (
                    "protocolcity",
                    "correspondent-rollup",
                    "Workspace · correspondent · %s" % day,
                    [str(rollup.relative_to(workspace))],
                    None,
                )
            )

    clerk = _first_existing(
        workspace,
        [
            ".protocolcity/ops/local/reports/clerk-%s.md" % day,
            ".protocolcity/ops/local/reports/clerk-%s.md" % day_utc,
        ],
    )
    if clerk:
        slots.append(
            (
                "protocolcity",
                "clerk-brief",
                "Workspace · clerk brief · %s" % day,
                [str(clerk.relative_to(workspace))],
                None,
            )
        )

    # Resolve Trading desk brief + RSU once so we can fold 
    desk_brief_path = _first_existing(
        workspace,
        [
            "Trading/local/reports/maru/%s-desk-brief.md" % day,
            "Trading/local/reports/maru/%s-desk-brief.md" % day_utc,
        ],
    )
    rsu_path = _first_existing(workspace, _rsu_candidates(day, day_utc))
    trading_desk_dropped = False

    for project, key, title, cands, visual in slots:
        path = _first_existing(workspace, cands)
        if not path:
            results.append(
                {
                    "ok": True,
                    "skipped": True,
                    "project": project,
                    "key": key,
                    "reason": "no report file for day",
                }
            )
            continue
        # never mint N× per-product efficiency (or board-validation) gold
        if is_disk_only_scan_key(key) and not act_now:
            results.append(
                {
                    "ok": True,
                    "skipped": True,
                    "project": project,
                    "key": key,
                    "reason": "disk_only",
                    "path": _rel_display(path, workspace),
                }
            )
            continue
        # RSU never mints its own gold — fold into desk-brief
        if is_folded_into_desk_key(key):
            if desk_brief_path is not None:
                results.append(
                    {
                        "ok": True,
                        "skipped": True,
                        "project": project,
                        "key": key,
                        "reason": "folded_into_desk_brief",
                        "path": _rel_display(path, workspace),
                    }
                )
                continue
            # RSU alone (no desk brief MD) → one desk-brief gold using RSU body
            if trading_desk_dropped:
                results.append(
                    {
                        "ok": True,
                        "skipped": True,
                        "project": project,
                        "key": key,
                        "reason": "folded_into_desk_brief",
                        "path": _rel_display(path, workspace),
                    }
                )
                continue
            key = "desk-brief"
            title = "Trading · desk brief · %s" % day
            # fall through to drop as desk-brief
        # thin product output → workspace rollup, not gold spam
        if is_thin_report(path, key):
            thin_hits.append((project, key, path))
            results.append(
                {
                    "ok": True,
                    "skipped": True,
                    "project": project,
                    "key": key,
                    "reason": "thin_rollup",
                    "path": _rel_display(path, workspace),
                }
            )
            continue
        vis = Path(visual) if visual else None
        related: Optional[List[Path]] = None
        if canonical_report_key(key) == "desk-brief" and rsu_path is not None:
            # Attach RSU pack path on the single product gold (not a 2nd gold)
            if path.resolve() != rsu_path.resolve():
                related = [rsu_path]
        r = drop_report(
            workspace=workspace,
            project=project,
            key=key,
            title=title,
            report_path=path,
            desk=desk,
            day=day,
            visual_path=vis,
            related_paths=related,
            dry_run=dry_run,
        )
        if project == "trading" and canonical_report_key(key) == "desk-brief":
            trading_desk_dropped = True
        results.append(r)

    # One workspace card for thin product signals (not N per-product golds)
    if thin_hits:
        inbox_dir = workspace / ".protocolcity" / "inbox"
        rollup = inbox_dir / ("%s-thin-rollup.md" % day)
        lines = [
            "# Workspace thin rollup · %s\n\n" % day,
            "Per-product reports were thin or all-ops — folded here instead of "
            "minting one gold each (FOR_YOU dual-audience).\n\n",
            "## Builder\n\n",
            "Thin product slots skipped from per-product gold:\n\n",
        ]
        for project, key, path in thin_hits:
            rel = _rel_display(path, workspace)
            lines.append("- **%s** / `%s` → `%s`\n" % (project, key, rel))
            glance_one = _read_glance(path, max_lines=6, max_chars=280)
            lines.append(
                "  %s\n" % glance_one.replace("\n", " ").strip()
            )
        lines.append("\n## User\n\n")
        lines.append(
            "_No separate product-purpose brief for these slots today. "
            "Open a path above if needed; otherwise ignore._\n"
        )
        if dry_run:
            results.append(
                {
                    "ok": True,
                    "action": "would_create",
                    "project": "protocolcity",
                    "key": "workspace-thin-rollup",
                    "path": str(rollup.relative_to(workspace)),
                    "thin_count": len(thin_hits),
                }
            )
        else:
            inbox_dir.mkdir(parents=True, exist_ok=True)
            rollup.write_text("".join(lines), encoding="utf-8")
            r = drop_report(
                workspace=workspace,
                project="protocolcity",
                key="workspace-thin-rollup",
                title="Workspace · thin product rollup · %s" % day,
                report_path=rollup,
                desk=desk,
                day=day,
                dry_run=False,
            )
            r["thin_count"] = len(thin_hits)
            results.append(r)

    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workspace",
        default=os.environ.get("SUITE_CITY_ROOT") or os.getcwd(),
        help="BluePrint workspace root",
    )
    ap.add_argument("--desk", default=DEFAULT_DESK)
    ap.add_argument("--author", default=DEFAULT_AUTHOR)
    ap.add_argument("--day", default=None, help="YYYY-MM-DD (default local today)")
    ap.add_argument("--scan", action="store_true", help="drop all known slots for day")
    ap.add_argument(
        "--act-now",
        action="store_true",
        help=(
            "allow gold for disk-only efficiency / board-validation keys "
            "(act-now smell only; default is disk-only — )"
        ),
    )
    ap.add_argument("--project", default=None)
    ap.add_argument("--key", default=None, help="stable report key (idempotency)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--path", default=None, help="report file path")
    ap.add_argument("--visual", default=None, help="optional visual HTML path")
    ap.add_argument("--priority", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ws = Path(args.workspace).expanduser().resolve()
    if not ws.is_dir():
        print("error: workspace missing: %s" % ws, file=sys.stderr)
        return 2

    if args.scan:
        results = scan_and_drop(
            ws,
            desk=args.desk,
            day=args.day,
            dry_run=args.dry_run,
            act_now=args.act_now,
        )
        if args.json:
            print(json.dumps({"ok": True, "results": results}, indent=2, default=str))
        else:
            for r in results:
                if r.get("skipped"):
                    print("skip  %s/%s — %s" % (r.get("project"), r.get("key"), r.get("reason")))
                else:
                    print(
                        "%s %s/%s → %s  %s"
                        % (
                            r.get("action"),
                            r.get("project"),
                            r.get("key"),
                            r.get("task_id") or "",
                            r.get("path") or "",
                        )
                    )
        bad = [r for r in results if r.get("ok") is False]
        return 1 if bad else 0

    if not (args.project and args.key and args.title and args.path):
        print(
            "error: need --scan OR --project --key --title --path",
            file=sys.stderr,
        )
        return 2

    # Single-drop: refuse efficiency / board-validation gold unless --act-now
    # . Also refuse standalone rsu-window gold (— fold to desk).
    if is_disk_only_scan_key(args.key) and not args.act_now:
        r = {
            "ok": True,
            "skipped": True,
            "action": "disk_only",
            "project": args.project,
            "key": args.key,
            "reason": (
                "efficiency / board-validation keys are disk-only by default; "
                "pass --act-now only for a true stuck-hand / feed-failure smell"
            ),
            "path": args.path,
        }
        if args.json:
            print(json.dumps(r, indent=2, default=str))
        else:
            print(
                "disk_only %s/%s — %s"
                % (args.project, args.key, r["reason"])
            )
        return 0

    if is_folded_into_desk_key(args.key) and not args.act_now:
        r = {
            "ok": True,
            "skipped": True,
            "action": "folded_into_desk_brief",
            "project": args.project,
            "key": args.key,
            "reason": (
                "rsu-window folds into the single Trading desk-brief gold "
                "; drop with --key desk-brief (and RSU as related "
                "path via --scan) or pass --act-now only for true act-now"
            ),
            "path": args.path,
        }
        if args.json:
            print(json.dumps(r, indent=2, default=str))
        else:
            print(
                "folded %s/%s — %s"
                % (args.project, args.key, r["reason"])
            )
        return 0

    r = drop_report(
        workspace=ws,
        project=args.project,
        key=args.key,
        title=args.title,
        report_path=Path(args.path),
        desk=args.desk,
        author=args.author,
        day=args.day,
        visual_path=Path(args.visual) if args.visual else None,
        priority=args.priority,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        print(
            "%s %s → %s"
            % (r.get("action"), r.get("label"), r.get("task_id") or r.get("error"))
        )
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
