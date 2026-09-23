"""Selected-workspace diagnostics; optional probes and explicit narrow repairs."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

SCHEMA = "blueprint.doctor/v1"


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root)


def _object(path: Path, root: Path) -> dict:
    if not _inside(path, root) or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("outside workspace or oversized")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("expected an object")
    return value


def _origin(receipt: dict) -> str | None:
    value = receipt.get("api_origin")
    if not value and type(receipt.get("port")) is int:
        value = "http://127.0.0.1:" + str(receipt["port"])
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1")
                or url.username or url.password or not url.port
                or url.path not in ("", "/") or url.query or url.fragment):
            return None
    except ValueError:
        return None
    return value.rstrip("/")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _probe(origin: str, path: str) -> dict:
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(Request(origin + path, headers={"Accept": "application/json"}), timeout=2) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("oversized response")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("invalid response")
    return value


def diagnose(root: Path, *, probe: bool = False) -> dict:
    root = root.expanduser().resolve()
    observed = datetime.now(timezone.utc).isoformat()
    report = {"schema": SCHEMA, "observed_at": observed,
              "workspace_id": hashlib.sha256(str(root).encode()).hexdigest()[:16],
              "probe_requested": probe, "checks": []}

    def add(code, severity, state, source, summary, next_step=""):
        report["checks"].append(dict(code=code, severity=severity, state=state,
            source=source, observed_at=observed, summary=summary, next_step=next_step))

    if not root.is_dir():
        add("WORKSPACE_MISSING", "error", "missing", "workspace", "Selected workspace does not exist.",
            "Select an existing workspace or create one with blueprint setup.")
        report["ok"] = False
        return report
    for name in ("AGENTS.md", "CLAUDE.md", "GROK.md"):
        path = root / name
        if path.is_symlink() and not _inside(path, root):
            add("INSTRUCTION_EXTERNAL", "error", "refused", name, "Instruction path leaves the selected workspace.",
                "Review this link and restore an in-workspace instruction source.")
        elif not path.is_file():
            add("INSTRUCTION_MISSING", "warning", "missing", name, "Workspace instruction or provider pointer is missing.",
                "Create AGENTS.md first; missing provider pointers can be planted with --repair vendor-pointers.")
        else:
            add("INSTRUCTION_PRESENT", "info", "ok", name, "Instruction source is present; content alignment needs review.")

    seen = set()
    for manifest in sorted(root.glob("*/.protocolcity/desk-join.json")):
        source = manifest.relative_to(root).as_posix()
        try:
            record = _object(manifest, root)
            slug = record.get("slug") or record.get("product")
            if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", slug):
                raise ValueError("invalid project")
            if slug in seen:
                add("PROJECT_DUPLICATE", "error", "conflict", source, "Multiple folders register the same store.",
                    "Keep one canonical registration; preserve reference and export folders separately.")
                continue
            seen.add(slug)
            database = root / "worklane/worklane/local/data" / (slug + ".db")
            if not _inside(database, root):
                raise ValueError("external store")
            if not database.exists():
                add("STORE_MISSING", "warning", "missing", source, "Registered project's store is unavailable.",
                    "Verify the selected WorkLane runtime and project registration.")
                continue
            with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=.2)) as connection:
                result = connection.execute("PRAGMA quick_check").fetchone()
                has_tasks = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
            if result != ("ok",) or not has_tasks:
                raise ValueError("invalid store")
            add("STORE_READABLE", "info", "ok", source, "Registered store passed a read-only structural check.")
        except (OSError, ValueError, sqlite3.Error):
            add("PROJECT_STORE_INVALID", "error", "invalid", source, "Registration or store is unreadable, invalid or outside this workspace.",
                "Inspect the registration and restore the store through WorkLane recovery; do not delete its history.")
    if not seen:
        add("PROJECTS_EMPTY", "info", "empty", "project registry", "No project stores are registered.")

    for component, relative in (("blueprint", ".blueprint/deployment.json"),
                                ("worklane", "local/worklane/deployment.json"),
                                ("workforce", "local/workforce/deployment.json")):
        path = root / relative
        if not path.exists():
            add("INSTALLATION_MISSING", "warning", "not_configured", relative,
                "Component has no workspace installation receipt.", "Install or select this component explicitly; no default port will be probed.")
            continue
        try:
            receipt = _object(path, root)
            if not isinstance(receipt.get("version"), str) or not receipt["version"]:
                raise ValueError("missing version")
            if component == "worklane":
                runtime = receipt.get("runtime")
                if not isinstance(runtime, str) or Path(runtime).resolve() != (root / "worklane/worklane/local").resolve():
                    raise ValueError("different runtime")
            if component == "workforce":
                data_home = receipt.get("data_home")
                if not isinstance(data_home, str) or not _inside(Path(data_home), root):
                    raise ValueError("different runtime")
            add("INSTALLATION_RECORDED", "info", "installed", relative,
                "Installation receipt is readable and scoped; it does not establish process health.")
            if not probe:
                continue
            origin = _origin(receipt)
            if origin is None:
                raise ValueError("no verified local origin")
            if component == "blueprint":
                value = _probe(origin, "/api/operations")
                workspace = value.get("workspace") or {}
                if (not isinstance(workspace, dict) or workspace.get("path") != str(root)
                        or value.get("build") != receipt["version"]):
                    add("BP_IDENTITY_MISMATCH", "error", "mismatch", relative,
                        "Responding build or workspace differs from this deployment receipt.",
                        "Use blueprint status and activate the intended verified release for this workspace.")
                else:
                    add("BP_IDENTITY_VERIFIED", "info", "ok", relative, "Responding BP build and workspace match the receipt.")
            elif component == "worklane":
                value = _probe(origin, "/api/admin/products")
                if value.get("ok") is not True or not isinstance(value.get("products"), list):
                    raise ValueError("unusable response")
                add("WORKLANE_API_REACHABLE", "info", "usable", relative,
                    "WorkLane returned its documented API shape; this read does not establish write or process identity.")
            else:
                # WorkForce's API does not provide a universal host attestation.
                add("WORKFORCE_PROBE_UNVERIFIED", "warning", "unknown", relative,
                    "Verify WorkForce's selected data home, heartbeat and live process separately.",
                    "Inspect Agents and the engine's local status; GitHub evidence is not liveness.")
        except (OSError, ValueError, TypeError):
            add("INSTALLATION_UNVERIFIED", "error", "unverified", relative,
                "Receipt, selected origin or optional live response could not be verified.",
                "Inspect the selected component's installation and receipt; no fallback service was contacted.")

    roster_paths = [root / "workforce/local/roster.json", root / ".protocolcity/workforce/local/roster.json"]
    roster_path = next((path for path in roster_paths if path.exists()), None)
    if roster_path:
        try:
            roster = _object(roster_path, root)
            if not isinstance(roster.get("workers"), dict):
                raise ValueError("invalid roster")
            add("ROSTER_READABLE", "info", "configured", "WorkForce roster",
                "Roster is readable; provider authentication, tools and quota require separate qualification.")
        except (OSError, ValueError):
            add("ROSTER_INVALID", "error", "invalid", "WorkForce roster", "Roster cannot be read inside this workspace.",
                "Validate the selected WorkForce data home and roster without overwriting execution history.")
    report["ok"] = not any(item["severity"] == "error" for item in report["checks"])
    return report


def support_bundle(report: dict) -> dict:
    """Allowlist structural evidence; never include paths, names, logs or config."""
    return {"schema": "blueprint.support/v1", "observed_at": report["observed_at"],
            "ok": report["ok"], "probe_requested": report["probe_requested"],
            "checks": [{key: row[key] for key in ("code", "severity", "state", "summary", "next_step")}
                       for row in report["checks"]]}


def repair_vendor_pointers(root: Path) -> list[str]:
    root = root.expanduser().resolve()
    if not (root / "AGENTS.md").is_file() or not _inside(root / "AGENTS.md", root):
        raise ValueError("A workspace-local AGENTS.md is required before planting pointers.")
    created = []
    for name in ("CLAUDE.md", "GROK.md"):
        try:
            with (root / name).open("x") as output:
                output.write("@AGENTS.md\n")
            created.append(name)
        except FileExistsError:
            pass  # Existing instructions and symlinks are never overwritten.
    return created


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="blueprint doctor", description=__doc__)
    parser.add_argument("workspace", nargs="?", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--probe", action="store_true", help="probe only origins in selected workspace receipts")
    parser.add_argument("--repair", choices=["vendor-pointers"], help="plant missing provider pointers; preserve existing files")
    parser.add_argument("--support-bundle", type=Path, help="write a new sanitized JSON report without paths or configuration")
    options = parser.parse_args(argv)
    if options.root and options.workspace:
        parser.error("Select the workspace once, with --root or the positional path.")
    root = options.root or options.workspace or Path.cwd()
    try:
        created = repair_vendor_pointers(root) if options.repair else []
        report = diagnose(root, probe=options.probe)
        if created:
            report["created_pointers"] = created
        if options.support_bundle:
            with options.support_bundle.open("x") as output:
                json.dump(support_bundle(report), output, indent=2)
                output.write("\n")
        if options.json:
            print(json.dumps(report, indent=2))
        else:
            for row in report["checks"]:
                print("{severity}: {code} [{state}] — {summary}".format(**row))
                if row["next_step"]:
                    print("  " + row["next_step"])
        return 0 if report["ok"] else 1
    except (OSError, ValueError):
        print("Doctor could not complete the selected repair or write a new support report. Check the path and keep existing files.", file=sys.stderr)
        return 2
