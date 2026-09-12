"""Host secrets inventory + MCP env_required check (pc-1061).

Pairs with the city MCP registry (pc-1055 / pc-1078):

* **Registry** (``.agents/mcp/<id>/manifest.json``) lists env var **NAMES**
  in ``env_required`` — what headless use needs.
* **Inventory paper** (``.agents/secrets/inventory.json``) tracks lifecycle
  metadata only (expiry, provenance, notes). **Never secret values.**
* **This check** joins registry requirements with host env (+ inventory
  expiry) and reports gaps. Optional gold For You when provision is missing.

Cadence (documented, not auto-scheduled by this module):

  python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT"
  python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT" --gold

See ``docs/specs/HOST_SECRETS_INVENTORY.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1
SECRETS_DIR_REL = Path(".agents") / "secrets"
INVENTORY_NAME = "inventory.json"
INVENTORY_REL = SECRETS_DIR_REL / INVENTORY_NAME
REPORT_REL = Path("local") / "reports" / "secrets" / "mcp-env-check.md"

# Optional: inventory-only keys not yet in any manifest still appear in paper.
_EMPTY_INVENTORY: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "description": (
        "Host secret NAMES + lifecycle metadata only. "
        "NEVER store secret values in this file (or in git)."
    ),
    "keys": {},
}

_README_BODY = """# Host secrets shelf (pc-1061)

**Names + lifecycle only.** Secret *values* live on the host (env / keychain),
never in this tree.

| Path | Role |
|---|---|
| `.agents/secrets/inventory.json` | Lifecycle paper — expiry, provenance, notes |
| `.agents/mcp/<id>/manifest.json` `env_required` | What each MCP needs (names only) |
| Host env / keychain | Actual secret values |

## Commands

```bash
# report only (exit 1 when a required name is unset or past expiry)
python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT"

# same + gold For You when gaps exist (idempotent per day)
python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace "$WORKSPACE_ROOT" --gold

# plant empty shelf
python3 ProtocolCity/scripts/check_mcp_secrets.py plant --workspace "$WORKSPACE_ROOT"
```

## Edit rules

1. When you add an MCP that needs a key, put the name in that manifest's
   `env_required` and (optionally) add a lifecycle row under `keys` here.
2. Provision the value on the host (export / keychain / launchd) — never commit it.
3. Record expiry / rotation notes in `inventory.json` when you know them.
4. Run the check after provisioning; clear any gold card when the gap is gone.

Law: `docs/specs/HOST_SECRETS_INVENTORY.md` · design:
`docs/research/byo-mcp-library-design-2026-08.md` §5.
"""


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return _pkg_dir().parent


def _templates_dir() -> Path:
    packaged = _pkg_dir() / "templates"
    if packaged.is_dir():
        return packaged
    monorepo = _repo_root() / "templates"
    if monorepo.is_dir():
        return monorepo
    return packaged


def secrets_dir(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / SECRETS_DIR_REL


def inventory_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / INVENTORY_REL


def report_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / REPORT_REL


def _today_iso() -> str:
    return date.today().isoformat()


def _parse_expiry(raw: Any) -> Optional[date]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    # Accept YYYY-MM-DD only (no secret-looking blobs).
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def load_inventory(workspace: Path) -> Dict[str, Any]:
    """Load inventory paper; missing file → empty skeleton (not an error)."""
    path = inventory_path(workspace)
    if not path.is_file():
        return dict(_EMPTY_INVENTORY)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("inventory is not valid JSON: %s (%s)" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise ValueError("inventory root must be an object: %s" % path)
    keys = data.get("keys")
    if keys is None:
        data = dict(data)
        data["keys"] = {}
    elif not isinstance(keys, dict):
        raise ValueError("inventory.keys must be an object: %s" % path)
    return data


def collect_registry_requirements(
    workspace: Path,
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Map env name → {servers, seats, vendor_locked} from MCP registry.

    Returns (requirements, notes). Missing registry → empty requirements
    with a note (not a hard error — pc-1079 seeds the shelf).
    """
    notes: List[str] = []
    req: Dict[str, Dict[str, Any]] = {}
    try:
        from protocolcity.mcp_sync import load_registry, registry_dir
    except ImportError:
        notes.append("protocolcity.mcp_sync unavailable")
        return req, notes

    root = workspace.expanduser().resolve()
    if not registry_dir(root).is_dir():
        notes.append("MCP registry missing (.agents/mcp/) — plant/import first")
        return req, notes

    try:
        manifests = load_registry(root)
    except (FileNotFoundError, ValueError) as exc:
        notes.append(str(exc))
        return req, notes

    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        sid = str(m.get("id") or "").strip() or "?"
        seats = m.get("seats") if isinstance(m.get("seats"), list) else ["*"]
        vendor_locked = bool(m.get("vendor_locked"))
        names = m.get("env_required") or []
        if not isinstance(names, list):
            continue
        for name in names:
            if not isinstance(name, str) or not name.strip():
                continue
            key = name.strip()
            row = req.setdefault(
                key,
                {
                    "servers": [],
                    "seats": [],
                    "vendor_locked_servers": [],
                },
            )
            if sid not in row["servers"]:
                row["servers"].append(sid)
            if vendor_locked and sid not in row["vendor_locked_servers"]:
                row["vendor_locked_servers"].append(sid)
            for seat in seats:
                s = str(seat).strip()
                if s and s not in row["seats"]:
                    row["seats"].append(s)
    return req, notes


def _env_provisioned(name: str, environ: Optional[Dict[str, str]] = None) -> bool:
    env = environ if environ is not None else os.environ
    val = env.get(name)
    return val is not None and str(val) != ""


def build_rows(
    workspace: Path,
    *,
    environ: Optional[Dict[str, str]] = None,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """Join registry requirements + inventory metadata + live host state."""
    as_of = as_of or date.today()
    inventory = load_inventory(workspace)
    inv_keys = inventory.get("keys") or {}
    if not isinstance(inv_keys, dict):
        inv_keys = {}

    requirements, notes = collect_registry_requirements(workspace)
    # Union: registry names + inventory-only names (lifecycle tracking ahead of use)
    all_names = sorted(set(requirements.keys()) | set(inv_keys.keys()))

    rows: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []

    for name in all_names:
        inv = inv_keys.get(name) if isinstance(inv_keys.get(name), dict) else {}
        reg = requirements.get(name) or {}
        servers = list(reg.get("servers") or [])
        inv_consumers = inv.get("consumers") if isinstance(inv.get("consumers"), list) else []
        consumers: List[str] = []
        for s in servers:
            tag = "mcp:%s" % s
            if tag not in consumers:
                consumers.append(tag)
        for c in inv_consumers:
            cs = str(c).strip()
            if cs and cs not in consumers:
                consumers.append(cs)

        seats = list(reg.get("seats") or [])
        provisioned = _env_provisioned(name, environ)
        expiry = _parse_expiry(inv.get("expiry") if inv else None)
        expired = bool(expiry and expiry < as_of)
        in_registry = name in requirements
        in_inventory = name in inv_keys

        status = "ok"
        gap_reason = ""
        if in_registry and not provisioned:
            status = "missing"
            gap_reason = "env_required unset on host"
        elif expired:
            status = "expired"
            gap_reason = "past expiry %s" % expiry.isoformat()
        elif not in_registry and in_inventory and not provisioned:
            # Inventory-only row without value — advisory, not a hard gap unless
            # callers want strict. Treat as missing_inventory_only (report, soft).
            status = "unprovisioned_paper"
            gap_reason = "inventory row has no host value (not in any env_required)"

        row = {
            "name": name,
            "consumers": consumers,
            "servers": servers,
            "seats": seats,
            "provisioned": provisioned,
            "expiry": expiry.isoformat() if expiry else None,
            "expired": expired,
            "rotation_note": (inv.get("rotation_note") if inv else None) or "",
            "provenance": (inv.get("provenance") if inv else None) or "",
            "notes": (inv.get("notes") if inv else None) or "",
            "in_registry": in_registry,
            "in_inventory": in_inventory,
            "status": status,
            "gap_reason": gap_reason,
            "vendor_locked_servers": list(reg.get("vendor_locked_servers") or []),
        }
        rows.append(row)

        # Hard gaps: missing registry env_required OR expired provisioned key.
        # Soft unprovisioned_paper does not fail the check (lifecycle prep).
        if status in ("missing", "expired"):
            gaps.append(
                {
                    "name": name,
                    "servers": servers,
                    "status": status,
                    "detail": "provision key %s for MCP %s (%s)"
                    % (
                        name,
                        ", ".join(servers) if servers else "(unknown)",
                        gap_reason,
                    ),
                }
            )

    ok = len(gaps) == 0
    detail = (
        "ok: %d key row(s), 0 gaps" % len(rows)
        if ok
        else "FAIL: %d gap(s) of %d key row(s)" % (len(gaps), len(rows))
    )
    return {
        "ok": ok,
        "workspace": str(workspace.expanduser().resolve()),
        "inventory": str(inventory_path(workspace)),
        "inventory_present": inventory_path(workspace).is_file(),
        "as_of": as_of.isoformat(),
        "rows": rows,
        "gaps": gaps,
        "gap_count": len(gaps),
        "row_count": len(rows),
        "notes": notes,
        "detail": detail,
        "codes": (["MCP-ENV-MISSING"] if any(g["status"] == "missing" for g in gaps) else [])
        + (["SECRET-EXPIRED"] if any(g["status"] == "expired" for g in gaps) else []),
    }


def check_secrets(
    workspace: Path,
    *,
    environ: Optional[Dict[str, str]] = None,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """Public entry: full secrets check result."""
    return build_rows(workspace, environ=environ, as_of=as_of)


def render_report_markdown(result: Dict[str, Any]) -> str:
    """Human report (local/ only — may list names, never values)."""
    lines: List[str] = [
        "# MCP / host secrets check",
        "",
        "> Names only. Never paste secret values into this report or into git.",
        "",
        "## Builder",
        "",
        "- **As of:** %s" % result.get("as_of"),
        "- **Workspace:** `%s`" % result.get("workspace"),
        "- **Inventory:** `%s` (%s)"
        % (
            result.get("inventory"),
            "present" if result.get("inventory_present") else "missing — plant recommended",
        ),
        "- **Status:** %s" % ("ok" if result.get("ok") else "GAPS"),
        "- **Rows / gaps:** %s / %s"
        % (result.get("row_count"), result.get("gap_count")),
        "",
    ]
    for note in result.get("notes") or []:
        lines.append("- Note: %s" % note)
    if result.get("notes"):
        lines.append("")

    gaps = result.get("gaps") or []
    if gaps:
        lines.append("### Gaps (act-now)")
        lines.append("")
        for g in gaps:
            lines.append(
                "- **%s** — %s" % (g.get("name"), g.get("detail") or g.get("status"))
            )
        lines.append("")
    else:
        lines.append("### Gaps")
        lines.append("")
        lines.append("_None — all registry `env_required` names resolve on this host._")
        lines.append("")

    lines.extend(
        [
            "### Inventory table",
            "",
            "| key | consumers | provisioned | expiry | status | provenance |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in result.get("rows") or []:
        lines.append(
            "| `%s` | %s | %s | %s | %s | %s |"
            % (
                row.get("name"),
                ", ".join(row.get("consumers") or []) or "—",
                "yes" if row.get("provisioned") else "no",
                row.get("expiry") or "—",
                row.get("status"),
                (row.get("provenance") or "—").replace("|", "/"),
            )
        )
    if not result.get("rows"):
        lines.append("| _(empty)_ | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## User",
            "",
            "Some connected tools need a key on this computer. When a key is missing,",
            "Map **For You** may list a card: provision the named key for the named",
            "tool, then re-run the check. Ordinary work drains without gold when",
            "keys are present.",
            "",
            "Cadence: weekly or after adding an MCP —",
            "`python3 ProtocolCity/scripts/check_mcp_secrets.py --workspace \"$WORKSPACE_ROOT\"`.",
            "",
            "Generated: %s · pc-1061"
            % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "",
        ]
    )
    return "\n".join(lines)


def write_report(workspace: Path, result: Dict[str, Any]) -> Path:
    path = report_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_markdown(result), encoding="utf-8")
    return path


def gold_for_you(
    workspace: Path,
    result: Dict[str, Any],
    report: Path,
    *,
    project: str = "protocolcity",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Drop/refresh a human-gated For You card when gaps exist.

    No-op (ok, action=skip) when there are no gaps — clears the need to spam.
    """
    if not result.get("gaps"):
        return {
            "ok": True,
            "action": "skip",
            "detail": "no gaps — no gold card",
        }
    try:
        # Prefer importable module path used by scripts/report_to_for_you.py
        from scripts.report_to_for_you import drop_report  # type: ignore
    except ImportError:
        # Load sibling script as module
        import importlib.util

        script = _repo_root() / "scripts" / "report_to_for_you.py"
        if not script.is_file():
            return {
                "ok": False,
                "action": "error",
                "detail": "report_to_for_you.py not found",
            }
        spec = importlib.util.spec_from_file_location(
            "report_to_for_you_pc1061", script
        )
        if spec is None or spec.loader is None:
            return {
                "ok": False,
                "action": "error",
                "detail": "could not load report_to_for_you",
            }
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        drop_report = mod.drop_report  # type: ignore[attr-defined]

    gap_names = [str(g.get("name")) for g in (result.get("gaps") or [])]
    title = "Provision MCP keys · %s gap(s)" % len(gap_names)
    return drop_report(
        workspace=workspace.expanduser().resolve(),
        project=project,
        key="mcp-secrets",
        title=title,
        report_path=report,
        dry_run=dry_run,
        priority=2,
        extra_labels=["secrets", "mcp", "pc-1061"],
    )


def plant_secrets_kit(workspace: Path, *, force: bool = False) -> Dict[str, Any]:
    """Plant empty `.agents/secrets/` shelf + inventory + README."""
    root = workspace.expanduser().resolve()
    shelf = secrets_dir(root)
    shelf.mkdir(parents=True, exist_ok=True)
    planted: List[str] = []
    skipped: List[str] = []

    inv = inventory_path(root)
    if inv.is_file() and not force:
        skipped.append(str(INVENTORY_REL))
    else:
        body = dict(_EMPTY_INVENTORY)
        inv.write_text(
            json.dumps(body, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        planted.append(str(INVENTORY_REL))

    readme = shelf / "README.md"
    if readme.is_file() and not force:
        skipped.append(str(SECRETS_DIR_REL / "README.md"))
    else:
        # Prefer packaged template when present
        tmpl = _templates_dir() / "agents" / "secrets" / "README.md"
        if tmpl.is_file():
            readme.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            readme.write_text(_README_BODY, encoding="utf-8")
        planted.append(str(SECRETS_DIR_REL / "README.md"))

    return {
        "ok": True,
        "workspace": str(root),
        "planted": planted,
        "skipped": skipped,
        "detail": "secrets shelf ready at %s" % shelf,
    }


def _resolve_workspace(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = (
        os.environ.get("WORKSPACE_ROOT")
        or os.environ.get("BLUEPRINT_WORKSPACE")
        or os.environ.get("SUITE_CITY_ROOT")
        or ""
    )
    if env:
        return Path(env).expanduser().resolve()
    try:
        from protocolcity.workspace import resolve_workspace_root

        return resolve_workspace_root(Path.cwd())
    except Exception:
        return Path.cwd().resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_mcp_secrets",
        description=(
            "Check host env for MCP registry env_required names + inventory "
            "expiry (pc-1061). Names only — never prints secret values."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "plant", "show"),
        help="check (default) | plant | show",
    )
    parser.add_argument(
        "--workspace",
        default="",
        help="workspace root (default: WORKSPACE_ROOT or cwd walk)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--gold",
        action="store_true",
        help="when gaps exist, drop/refresh Map For You gold card",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write local/reports/secrets/mcp-env-check.md",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="plant: overwrite existing inventory/README",
    )
    parser.add_argument(
        "--project",
        default="protocolcity",
        help="WorkLane project for --gold (default: protocolcity)",
    )
    parser.add_argument(
        "--dry-run-gold",
        action="store_true",
        help="with --gold: do not call desk, print would-create/update",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = _resolve_workspace(args.workspace)
    out: Dict[str, Any]
    exit_code = 0

    if args.command == "plant":
        out = plant_secrets_kit(root, force=bool(args.force))
    elif args.command == "show":
        out = check_secrets(root)
    else:
        out = check_secrets(root)
        if not args.no_report:
            try:
                rpath = write_report(root, out)
                out["report"] = str(rpath)
            except OSError as exc:
                out["report_error"] = str(exc)
        if args.gold:
            report = Path(out["report"]) if out.get("report") else write_report(root, out)
            gold = gold_for_you(
                root,
                out,
                report,
                project=args.project,
                dry_run=bool(args.dry_run_gold),
            )
            out["gold"] = gold
        if not out.get("ok"):
            exit_code = 1

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if args.command == "plant":
            print("ok: %s" % out.get("detail"))
            for p in out.get("planted") or []:
                print("  planted: %s" % p)
            for s in out.get("skipped") or []:
                print("  skipped: %s" % s)
        else:
            status = "ok" if out.get("ok") else "FAIL"
            print("%s: %s" % (status, out.get("detail")))
            for note in out.get("notes") or []:
                print("  note: %s" % note)
            for g in out.get("gaps") or []:
                print("  gap: %s — %s" % (g.get("name"), g.get("detail")))
            if out.get("report"):
                print("  report: %s" % out["report"])
            if out.get("codes"):
                print("  codes: %s" % ", ".join(out["codes"]))
            gold = out.get("gold")
            if isinstance(gold, dict):
                print(
                    "  gold: %s (%s)"
                    % (gold.get("action"), gold.get("task_id") or gold.get("detail") or "")
                )
            if not out.get("ok"):
                print(
                    "  hint: provision missing names on the host, update "
                    ".agents/secrets/inventory.json expiry/provenance, re-run"
                )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
