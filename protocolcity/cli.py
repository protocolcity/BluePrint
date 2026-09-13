"""protocolcity CLI — setup · found · adopt · serve · uninstall (pc-134 / first-run)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import List, Optional, Set, Tuple

from protocolcity.desk import DEFAULT_DESK, flush_pending_joins
from protocolcity.doctor import diagnose, fix, fix_papers, print_report
from protocolcity.found import found, print_receipt
from protocolcity.paths import resolve_citylens
from protocolcity.registry import register_city
from protocolcity.setup_flow import (
    _maybe_unmanaged_prompt,
    _print_adopt_all,
    adopt_all_unmanaged,
    run_setup,
    run_uninstall,
    stop_suite_processes,
)
from protocolcity.slugs import slugify

_REPO_ROOT = Path(__file__).resolve().parent.parent


def format_post_adopt_checklist(
    name: str,
    *,
    store_slug: Optional[str] = None,
    prefix: Optional[str] = None,
) -> str:
    """pc-513: post-adopt manual checklist (city law never auto-rewritten).

    Unit-testable pure formatter — print via ``print_post_adopt_checklist``.
    """
    from protocolcity.adopt import _prefix_for

    slug = (store_slug or "").strip() or slugify(name)
    pref = (prefix or "").strip() or _prefix_for(name)
    return (
        "✓ Adopted {name}  (store: {store_slug}  prefix: {prefix})\n"
        "\n"
        "Post-adopt checklist — complete manually:\n"
        "  [ ] workspace AGENTS.md — add `{name}/` row to the ## Projects table\n"
        "  [ ] ProtocolCity/ATLAS.md — add Tier-3 row for ../{name}/AGENTS.md\n"
        "  [ ] .claude/skills/ticket-routing — add prefix row (if workspace skill present)\n"
        "  [ ] GitHub remote — create remote + push (founder call)\n"
    ).format(name=name, store_slug=slug, prefix=pref)


def print_post_adopt_checklist(
    name: str,
    *,
    store_slug: Optional[str] = None,
    prefix: Optional[str] = None,
) -> None:
    """Write the post-adopt checklist to stdout (always — not diagnostics)."""
    print(format_post_adopt_checklist(name, store_slug=store_slug, prefix=prefix))


def _checklist_from_adopt_payload(payload: Optional[dict], fallback_name: str = "") -> None:
    """Print checklist from an adopt/fix result dict when a neighborhood name is known."""
    if not isinstance(payload, dict):
        if fallback_name:
            print_post_adopt_checklist(fallback_name)
        return
    name = str(payload.get("name") or fallback_name or "").strip()
    if not name:
        return
    store = payload.get("store_slug")
    pref = payload.get("prefix")
    print_post_adopt_checklist(
        name,
        store_slug=str(store) if store else None,
        prefix=str(pref) if pref else None,
    )

# Default engine ports (suite proxies these). Overridable via env when spawning.
# pc-575: census is in-process on the suite — no citylens :8796 engine.
_DEFAULT_DESK_PORT = 8799
_DEFAULT_WORKFORCE_PORT = 8797
_ENGINE_READY_TIMEOUT_S = 15.0
_ENGINE_POLL_S = 0.25
_SERVICE_READY_TIMEOUT_S = 45.0

# Display-only hide list (pc-239 / pc-257) — same path suite/serve.py uses.
# Never an operational scope for engines, exports, backups, or patrols.
_DEFAULT_HIDDEN_NOTE = (
    "Display-only (pc-239): folders hidden from the Map. Never an operational scope."
)


def _url_ready(url: str, timeout: float = 1.0) -> bool:
    """True when GET url returns any HTTP response (2xx–4xx); false on network error.

    HTTPError (e.g. citylens `/` → 404) still means the listener is up — do not
    treat as down or we re-spawn and get Address already in use.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= int(r.status) < 500
    except urllib.error.HTTPError as e:
        # Any HTTP status from the peer = process is listening
        return 100 <= int(getattr(e, "code", 0) or 0) < 600
    except Exception:
        return False


def _wait_ready(url: str, timeout_s: float = _ENGINE_READY_TIMEOUT_S) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _url_ready(url):
            return True
        time.sleep(_ENGINE_POLL_S)
    return False


def _wait_for_service_cli_ready(port: int, *, action: str) -> bool:
    """Do not report a service action complete until its suite answers (GH #14)."""
    url = "http://127.0.0.1:%d/" % int(port)
    print("Waiting for %s after service %s …" % (url, action))
    if _wait_ready(url, timeout_s=_SERVICE_READY_TIMEOUT_S):
        print("Service ready: %s" % url)
        return True
    print(
        "error: suite port %d not ready within %.0fs after service %s."
        % (int(port), _SERVICE_READY_TIMEOUT_S, action),
        file=sys.stderr,
    )
    print(
        "  Check: blueprint service status · workspace .protocolcity/logs/",
        file=sys.stderr,
    )
    return False


def _desk_product_count(desk_url: str, timeout: float = 2.0) -> int:
    """Return registered product count from GET /api/admin/products (pc-637)."""
    try:
        with urllib.request.urlopen(
            desk_url + "/api/admin/products", timeout=timeout
        ) as r:
            return len(json.loads(r.read().decode()).get("products") or [])
    except Exception:
        return 0


def _engine_log_open(city_root: Optional[Path], name: str):
    """Open a log sink for an engine subprocess (pc-312).

    Engine stdout/stderr used to go to DEVNULL, so a crash at import (e.g. a
    broken wheel) surfaced only as "did not become ready within 15s". Logs
    land under ``<city-root>/.protocolcity/logs/`` (system temp dir when no
    root); the readiness-failure path prints the tail.
    """
    base = (
        city_root / ".protocolcity" / "logs"
        if city_root is not None
        else Path(tempfile.gettempdir()) / "protocolcity-logs"
    )
    base.mkdir(parents=True, exist_ok=True)
    path = base / ("%s.log" % name)
    return path, open(path, "ab")


def _engine_failed(name: str, url: str, log_path: Optional[Path]) -> None:
    print(
        "error: %s did not become ready on %s within %.0fs"
        % (name, url, _ENGINE_READY_TIMEOUT_S),
        file=sys.stderr,
    )
    if log_path is None:
        return
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        tail = ""
    if tail:
        print("── %s log tail (%s) ──" % (name, log_path), file=sys.stderr)
        print("\n".join(tail.splitlines()[-20:]), file=sys.stderr)
    else:
        print("(engine log empty: %s)" % log_path, file=sys.stderr)


def _walk_up_city_root(start: Path) -> Optional[Path]:
    """Outermost ancestor with AGENTS.md (workspace root, not nested project).

    Thin wrapper over ``protocolcity.workspace.walk_up_workspace_root`` (pc-956).
    """
    from protocolcity.workspace import walk_up_workspace_root

    return walk_up_workspace_root(start)


def _resolve_city_root(root_arg: Optional[str]) -> Optional[Path]:
    """City root for engine wiring: --root, env, walk-up, or registry (pc-956)."""
    from protocolcity.workspace import resolve_workspace_root

    return resolve_workspace_root(root_arg, start=Path.cwd(), use_registry=True)


def _hidden_json_path(city_root: Path) -> Path:
    """Owner-of-truth path: ``<city-root>/.protocolcity/hidden.json`` (suite README)."""
    return city_root / ".protocolcity" / "hidden.json"


def _folder_slug(folder: str) -> str:
    """Normalize a folder name or path to the Map slug (canonical, pc-313)."""
    return slugify(Path(str(folder).rstrip("/")).name)


def _read_hidden_doc(city_root: Path) -> dict:
    """Load hidden.json; create-shaped defaults when absent or unreadable.

    Preserves a custom ``note`` when present. Schema:
    ``{ "note": "...", "hidden": ["slug", ...] }``.
    """
    path = _hidden_json_path(city_root)
    if not path.is_file():
        return {"note": _DEFAULT_HIDDEN_NOTE, "hidden": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"note": _DEFAULT_HIDDEN_NOTE, "hidden": []}
    if not isinstance(data, dict):
        return {"note": _DEFAULT_HIDDEN_NOTE, "hidden": []}
    note = data.get("note")
    if not isinstance(note, str) or not note.strip():
        note = _DEFAULT_HIDDEN_NOTE
    raw = data.get("hidden") or []
    if not isinstance(raw, list):
        raw = []
    hidden = [str(s).strip().lower() for s in raw if str(s).strip()]
    return {"note": note, "hidden": hidden}


def _write_hidden_doc(city_root: Path, doc: dict) -> Path:
    """Write hidden.json (create parent dir if needed). Preserves note field."""
    path = _hidden_json_path(city_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    note = doc.get("note") if isinstance(doc.get("note"), str) else ""
    note = note.strip() or _DEFAULT_HIDDEN_NOTE
    slugs: Set[str] = set()
    for s in doc.get("hidden") or []:
        t = str(s).strip().lower()
        if t:
            slugs.add(t)
    out = {"note": note, "hidden": sorted(slugs)}
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return path


# STAFFING.md model tier law → default pins (pc-204)
_TIER_MODELS = {
    "heavy": "grok-4.5",
    "generalist": "claude-sonnet-4-6",
    "patrol": "claude-haiku-4-5-20251001",
    "specialty": "cursor-agent",
    "script": "",
}
# Match live roster argv patterns (WorkForce hire / engine substitution).
_TIER_COMMANDS = {
    "heavy": [
        "grok", "--prompt-file", "{prompt_path}", "--always-approve",
        "--output-format", "plain", "--model", "{model}",
    ],
    "generalist": [
        "claude", "--model", "{model}", "-p", "{prompt_text}",
        "--dangerously-skip-permissions", "--no-session-persistence",
        "--output-format", "json",
    ],
    "patrol": [
        "claude", "--model", "{model}", "-p", "{prompt_text}",
        "--dangerously-skip-permissions", "--no-session-persistence",
        "--output-format", "json",
    ],
    "specialty": ["cursor-agent", "--force", "-p", "{prompt_text}"],
    "script": ["true"],  # no LLM — pure runner; replace on restaff
}

# Workspace ops **job** function ids (Map diamond / seed-ops). Not project hands.
# Aliases match suite OPS_FUNCTION_IDS core set (pc-435).
# pc-988: default trio is chief-of-staff · health-patrol · workspace-efficiency.
# Legacy names (clerk/marshal/correspondent/papers-patrol) stay reserved so
# hire --kind job still works; seed-ops treats marshal as health-patrol alias.
_RESERVED_OPS_JOB_NAMES = frozenset(
    {
        # Current defaults (pc-988)
        "chief-of-staff",
        "health-patrol",
        "workspace-efficiency",
        # Optional / citizen-gated
        "papers-sync",
        "github-desk",
        "ship-desk",
        # Legacy aliases (still reserved; not re-seeded as defaults)
        "clerk",
        "marshal",
        "correspondent",
        "papers-patrol",
        "city-clerk",
        "city-marshal",
        "city-correspondent",
    }
)


def _normalize_hire_kind(kind: Optional[str]) -> str:
    """Roster kind: lane (worker/hand) or job (scheduled duty)."""
    k = (kind or "lane").strip().lower()
    if k in ("worker", "agent", "hand", "lane"):
        return "lane"
    if k in ("job", "ops", "automation", "duty"):
        return "job"
    return k


def hire_kind_guard(name: str, kind: str) -> Optional[str]:
    """Return an error string when name/kind is ambiguous (pc-435), else None.

    Reserved ops function names default to **job**. Creating them as a project
    worker (lane) is almost always a mistake — redirect to seed-ops.
    """
    slug = slugify(name) if name else ""
    if not slug:
        slug = (name or "").strip().lower().replace("_", "-")
    k = _normalize_hire_kind(kind)
    if slug in _RESERVED_OPS_JOB_NAMES and k != "job":
        return (
            "%r is a workspace ops **job** name (scheduled duty on the Map "
            "diamond ring), not a project worker/hand.\n"
            "  Prefer:  blueprint seed-ops --root <workspace>\n"
            "  Or:      blueprint hire %s --workdir <.protocolcity/ops or project> "
            "--kind job --role \"…\"\n"
            "  For a project hand that claims work orders, pick a persona name "
            "(neo, riley, …) and omit --kind (defaults to lane)."
            % (name, name)
        )
    if k not in ("lane", "job"):
        return (
            "unknown --kind %r (use lane|worker for hands that claim work orders, "
            "or job for scheduled duties)" % kind
        )
    return None


# Paper template packs for hire (pc-968 / ALWAYS_WORK §3 director seat).
_HIRE_TEMPLATE_CHOICES = ("auto", "worker", "director")
_TIER_CLI_COMMAND = {
    "heavy": "grok",
    "generalist": "claude",
    "patrol": "claude",
    "specialty": "cursor-agent",
    "script": "true",
}


def resolve_hire_template(
    name: str,
    template: Optional[str] = None,
) -> str:
    """Pick paper pack: ``worker`` (default) or ``director`` (queue triage).

    ``auto`` (default CLI): slug ending in ``-desk`` → director; else worker.
    Explicit ``worker`` / ``director`` always wins.
    """
    raw = (template or "auto").strip().lower() or "auto"
    if raw not in _HIRE_TEMPLATE_CHOICES:
        raise ValueError(
            "unknown --template %r (use auto|worker|director)" % template
        )
    if raw in ("worker", "director"):
        return raw
    slug = slugify(name) if name else ""
    if not slug:
        slug = (name or "").strip().lower().replace("_", "-")
    if slug.endswith("-desk"):
        return "director"
    return "worker"


def _fill_hire_placeholders(body: str, mapping: dict) -> str:
    """Replace ``{{KEY}}`` / ``{KEY}`` tokens; soft-blank leftovers."""
    out = body
    for key, val in mapping.items():
        out = out.replace("{{" + key + "}}", val)
        out = out.replace("{" + key + "}", val)
    out = re.sub(r"\{\{[A-Z0-9_/'\" —.-]+\}\}", "…", out)
    return out


def plant_hire_papers(
    workdir: str,
    slug: str,
    *,
    template: str = "worker",
    store: str = "",
    neighborhood: str = "",
    role: str = "",
    cli_command: str = "claude",
    model: str = "",
    force: bool = False,
) -> Tuple[str, str, str]:
    """Write CONTRACT.md + prompt.md from BluePrint templates (pc-968).

    Returns absolute ``(contract_path, prompt_path, template_kind)``.
    """
    from protocolcity.found import _template

    workdir_abs = os.path.abspath(workdir)
    if not os.path.isdir(workdir_abs):
        raise FileNotFoundError("workdir does not exist: %s" % workdir_abs)
    kind = (template or "worker").strip().lower()
    if kind not in ("worker", "director"):
        raise ValueError("template must be worker|director, got %r" % template)
    workers_dir = os.path.join(workdir_abs, "workers", slug)
    os.makedirs(workers_dir, exist_ok=True)
    contract = os.path.join(workers_dir, "CONTRACT.md")
    prompt = os.path.join(workers_dir, "prompt.md")
    store = store or os.path.basename(workdir_abs).lower().replace(" ", "-")
    neighborhood = neighborhood or os.path.basename(workdir_abs)
    model_pin = (model or "").strip() or "vendor default"
    mapping = {
        "WORKER_ID": slug,
        "slug": slug,
        "STORE_SLUG": store,
        "store": store,
        "NEIGHBORHOOD_NAME": neighborhood,
        "neighborhood": neighborhood,
        "CLI_COMMAND": cli_command or "claude",
        'MODEL_OR_"vendor default"': model_pin,
        "CLAIM_CRITERIA — e.g. \"single-file, verifiable by the test suite, no schema changes\"": (
            role or "work assigned to this cabinet"
        ),
        "FORBIDDEN_AREA_1": "local/ employment records (roster, ledger locks)",
        "FORBIDDEN_AREA_2": "other cabinets' workers/ trees",
    }
    src_pair = (
        ("director-CONTRACT.md", "director-prompt.md")
        if kind == "director"
        else ("worker-CONTRACT.md", "worker-prompt.md")
    )
    for dest, src_name in ((contract, src_pair[0]), (prompt, src_pair[1])):
        if os.path.exists(dest) and not force:
            continue
        body = _template(src_name).read_text(encoding="utf-8")
        body = _fill_hire_placeholders(body, mapping)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(body)
    return contract, prompt, kind


def _cmd_hire(args: argparse.Namespace) -> int:
    """First-hire arming wizard (pc-204): tier + schedule → WorkForce hire."""
    kind = _normalize_hire_kind(getattr(args, "kind", None))
    guard = hire_kind_guard(args.name, kind)
    if guard:
        print("error: %s" % guard, file=sys.stderr)
        return 2

    try:
        paper_template = resolve_hire_template(
            args.name, getattr(args, "template", None)
        )
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    try:
        from workforce.hire import hire, RosterError  # type: ignore
    except ImportError:
        # Editable city checkout: try sibling workforce package roots (pc-956:
        # no Path.home()/Developer fallback — discover workspace root).
        here = Path(__file__).resolve()
        from protocolcity.workspace import resolve_workspace_root

        ws = resolve_workspace_root(start=here, use_registry=True)
        candidates = [
            here.parents[2] / "workforce",  # …/<workspace>/workforce
            here.parents[1].parent / "workforce",
        ]
        if ws is not None:
            candidates.append(ws / "workforce")
        for _wf in candidates:
            try:
                root = _wf.resolve()
            except OSError:
                continue
            if root.is_dir() and (root / "workforce" / "hire.py").is_file():
                p = str(root)
                if p not in sys.path:
                    sys.path.insert(0, p)
        try:
            from workforce.hire import hire, RosterError  # type: ignore
        except ImportError as e:
            print(
                "error: protocolcity-workforce not installed — "
                "pip install protocolcity-workforce  (or brew formula engines) "
                "(%s)" % e,
                file=sys.stderr,
            )
            return 2

    tier = (args.tier or "generalist").lower()
    model = (args.model or "").strip() or _TIER_MODELS.get(tier, "")
    schedule = (args.schedule or "").strip()
    if schedule.lower() in ("manual", "none", "off", "-"):
        schedule = "manual"  # informational — not daemon-owned
    command = list(_TIER_COMMANDS.get(tier) or _TIER_COMMANDS["generalist"])
    if tier == "script":
        command = ["true"]
    cli_command = _TIER_CLI_COMMAND.get(tier, "claude")

    workdir = os.path.abspath(args.workdir)
    # Prefer env when daemon/serve already set the roster home; else workspace
    # from cwd / walk-up from workdir (hire inside a project folder).
    env_roster = (os.environ.get("WORKFORCE_ROSTER") or "").strip()
    city = _resolve_city_root(None) or _walk_up_city_root(Path(workdir))
    # Canonical roster path matches serve --with-engines (pc-351 / pc-437):
    #   {city}/.protocolcity/workforce/local/roster.json
    # Legacy {city}/workforce/local/ is NOT the daemon home.
    roster_path = args.roster
    if not roster_path and env_roster:
        roster_path = env_roster
    if not roster_path and city is not None:
        candidate = (
            Path(city) / ".protocolcity" / "workforce" / "local" / "roster.json"
        )
        candidate.parent.mkdir(parents=True, exist_ok=True)
        roster_path = str(candidate)
    if not roster_path:
        # Last resort: under workdir's workspace-ish parent — never bare cwd
        # package local/ which is invisible to serve --with-engines.
        fallback_city = _walk_up_city_root(Path(workdir)) or Path(workdir).resolve()
        candidate = (
            fallback_city / ".protocolcity" / "workforce" / "local" / "roster.json"
        )
        candidate.parent.mkdir(parents=True, exist_ok=True)
        roster_path = str(candidate)

    # pc-968: plant paper pack from BluePrint before roster arm so *-desk
    # hires get director templates (workforce.hire always plants worker/*).
    # pc-979: named ops seats (chief-of-staff, …) use templates/ops/<slug>/.
    slug = slugify(args.name)
    store = (args.project or "").strip() or os.path.basename(workdir).lower().replace(
        " ", "-"
    )
    neighborhood = os.path.basename(workdir)
    force_papers = bool(args.force_papers)
    papers_via = "workforce"
    ops_pack_applied = False
    # Prefer shipped ops-kit pack when workdir is the ops kit (or reserved name).
    workdir_norm = os.path.realpath(workdir).replace("\\", "/")
    is_ops_workdir = "/.protocolcity/ops" in workdir_norm or workdir_norm.endswith(
        "/.protocolcity/ops"
    )
    if is_ops_workdir or slug in _RESERVED_OPS_JOB_NAMES:
        try:
            from protocolcity.seed_ops import plant_ops_seat_papers
            from protocolcity.workspace import resolve_workspace_root

            city_for_ops = city
            if city_for_ops is None:
                city_for_ops = resolve_workspace_root(
                    start=Path(workdir), use_registry=True
                )
            if city_for_ops is None:
                # workdir may already be …/.protocolcity/ops
                parent = Path(workdir).resolve().parent
                if parent.name == ".protocolcity":
                    city_for_ops = parent.parent
                else:
                    city_for_ops = Path(workdir).resolve()
            # Always prefer product ops pack over generic worker stubs on hire.
            receipt = plant_ops_seat_papers(
                Path(city_for_ops), slug, force=True
            )
            if receipt.get("ok"):
                papers_via = "blueprint:ops/%s" % slug
                ops_pack_applied = True
        except Exception:
            ops_pack_applied = False

    if not ops_pack_applied:
        try:
            plant_hire_papers(
                workdir,
                slug,
                template=paper_template,
                store=store,
                neighborhood=neighborhood,
                role=args.role or "",
                cli_command=cli_command,
                model=model,
                force=force_papers or paper_template == "director",
            )
            papers_via = "blueprint:%s" % paper_template
        except FileNotFoundError as e:
            if paper_template == "director":
                print("error: director template plant failed: %s" % e, file=sys.stderr)
                return 2
            # Worker fallback: let workforce plant if BluePrint templates missing.
            papers_via = "workforce-fallback"

    # When we planted (especially director / ops pack), do not let workforce
    # overwrite with worker-CONTRACT/prompt — plant=False reuses paths we wrote.
    plant_via_workforce = papers_via == "workforce-fallback"

    print(
        "hire template: %s (papers via %s)" % (paper_template, papers_via),
        file=sys.stderr,
    )

    # pc-1241: anchor roster paths to the workforce home (WORKFORCE_DATA_DIR =
    # {city}/.protocolcity/workforce) so the daemon (base=WORKFORCE_DATA_DIR)
    # and serve.py both resolve workdir to the correct absolute project path.
    # Without this, hiring from inside the project dir produces workdir="."
    # which the daemon resolves to its own data-dir (wrong project on Map).
    if city is not None:
        hire_base = str(Path(city) / ".protocolcity" / "workforce")
    elif roster_path:
        hire_base = str(Path(roster_path).parent.parent)
    else:
        hire_base = str(Path(workdir).parent)
    try:
        result = hire(
            name=args.name,
            workdir=workdir,
            role=args.role or "",
            kind=kind,
            schedule=schedule,
            model=model,
            command=command,
            project=args.project or "",
            roster_path=roster_path,
            plant=plant_via_workforce,
            force_papers=bool(args.force_papers) if plant_via_workforce else False,
            dry_run=bool(args.dry_run),
            base=hire_base,
        )
    except RosterError as e:
        print("error: hire failed: %s" % e, file=sys.stderr)
        return 1
    except Exception as e:
        print("error: hire failed: %s" % e, file=sys.stderr)
        return 2

    if isinstance(result, dict):
        result["paper_template"] = paper_template
        result["papers_via"] = papers_via
    print(json.dumps(result, indent=2, default=str))
    if result.get("ok"):
        # One-file roster law (pc-437 / founder 2026-07-27): after hire always
        # re-assert legacy workforce/local/roster.json → canonical symlink so
        # dual full copies cannot reappear when someone hires with --roster
        # under the package tree or an old path.
        if city is not None and not bool(args.dry_run):
            try:
                from protocolcity.doctor import fix_roster_path_split

                link = fix_roster_path_split(Path(city))
                if link.get("symlinked") or link.get("skipped") == "already linked":
                    result["roster_single_home"] = link
            except Exception as exc:  # pragma: no cover — best-effort
                result["roster_single_home_error"] = str(exc)
            # pc-820: best-effort refresh hands block in neighborhood AGENTS.md
            try:
                workdir_path = Path(os.path.abspath(args.workdir))
                if workdir_path.parent == Path(city):
                    fix_papers(Path(city), neighborhood=workdir_path.name)
            except Exception:
                pass
        kind_note = (
            "job (scheduled duty · Map diamond · does not claim work orders)"
            if kind == "job"
            else "lane/worker (Map hand · claims work orders)"
        )
        print(
            "\nArmed as kind=%s · tier=%s model=%r schedule=%r · papers=%s"
            % (kind, tier, model, schedule, paper_template),
            file=sys.stderr,
        )
        print("  · %s" % kind_note, file=sys.stderr)
        for step in result.get("next_steps") or []:
            print("  · %s" % step, file=sys.stderr)
        if kind == "lane":
            print(
                "  · Need a workspace ops job instead? "
                "blueprint seed-ops --root <workspace>",
                file=sys.stderr,
            )
    return 0 if result.get("ok") else 1


def _cmd_hide_unhide(args: argparse.Namespace, *, hide: bool) -> int:
    """blueprint hide|unhide <folder> — display-only Map preference (pc-257)."""
    city_root = _resolve_city_root(getattr(args, "root", None))
    if city_root is None:
        print(
            "error: workspace root not found (pass --root or run from a workspace with AGENTS.md)",
            file=sys.stderr,
        )
        return 2
    slug = _folder_slug(args.folder)
    if not slug:
        print("error: folder slug is empty", file=sys.stderr)
        return 2
    doc = _read_hidden_doc(city_root)
    current = set(doc.get("hidden") or [])
    if hide:
        current.add(slug)
        verb = "hid"
    else:
        current.discard(slug)
        verb = "unhid"
    doc["hidden"] = sorted(current)
    path = _write_hidden_doc(city_root, doc)
    print(
        "%s %s · %d hidden · %s"
        % (verb, slug, len(doc["hidden"]), path)
    )
    return 0


def _module_importable(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _terminate_children(children: List[subprocess.Popen]) -> None:
    """Stop processes we spawned, reverse order, escalate to kill if needed."""
    for proc in reversed(children):
        if proc.poll() is not None:
            continue
        try:
            proc.terminate()
        except Exception:
            continue
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=2)
            except Exception:
                pass


def _under_launchd() -> bool:
    """True when this process is a launchd job (login agent / daemon).

    pc-536: under launchd, suite restarts must not tear down engine children
    (or process-group kill them) — dual ownership amplifies thrash.
    """
    name = (os.environ.get("XPC_SERVICE_NAME") or "").strip()
    if name:
        return True
    return bool((os.environ.get("LAUNCH_JOB_LABEL") or "").strip())


def _serve_via_login_service(
    city_root: Optional[Path],
    port: int,
) -> Optional[int]:
    """pc-1072: prefer launchd-owned suite when the login service is installed.

    Returns an exit code when handled via bootstrap/kickstart, or ``None`` to
    fall through to foreground ``suite/serve.py`` (no service, non-macOS, or
    this process *is* the launchd job).
    """
    if _under_launchd():
        return None
    try:
        from protocolcity import service as svc_mod
    except Exception:
        return None
    if not svc_mod.is_macos() or not svc_mod.login_service_configured():
        return None
    receipt = svc_mod.ensure_service_running(
        preferred_root=city_root,
        quiet=False,
        force=False,
    )
    if receipt.get("skipped"):
        return None
    if not receipt.get("ok"):
        print("error: %s" % receipt.get("error"), file=sys.stderr)
        print(
            "  login service present but could not restart — try:\n"
            "    blueprint service start\n"
            "    # or one-shot FG: blueprint serve --foreground",
            file=sys.stderr,
        )
        return 1
    state = svc_mod.service_status().get("state") or {}
    ready_port = int(receipt.get("port") or state.get("port") or port or 8801)
    print(
        "Serving via login LaunchAgent (pc-1072) — suite stays up after this "
        "shell exits. Use --foreground for a one-shot terminal child."
    )
    return 0 if _wait_for_service_cli_ready(ready_port, action="serve") else 1


def _engine_popen_kwargs() -> dict:
    """Detached process group so suite SIGTERM does not cascade to engines.

    POSIX: start_new_session → new session/process group.
    Windows: CREATE_NEW_PROCESS_GROUP (pc-391 portable).
    """
    if sys.platform == "win32":
        # 0x00000200 = CREATE_NEW_PROCESS_GROUP
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)}
    return {"start_new_session": True}


def _uid_str() -> str:
    """User numeric ID as a string (for launchctl gui/<uid>/... paths)."""
    try:
        return str(os.getuid())
    except AttributeError:
        return "501"


def _external_desk_launchd_label() -> Optional[str]:
    """Return the launchd label of a registered external desk service, or None.

    On macOS: checks com.worklane.server.
    A registered label — even when the service is currently down — means an
    external process owns :8799 and the suite must not spawn its bundled engine
    over it (pc-668: dual-desk takeover incident 2026-07-29).
    Non-macOS always returns None.
    """
    if sys.platform != "darwin":
        return None
    label = "com.worklane.server"
    try:
        r = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode == 0:
            return label
    except Exception:
        pass
    return None


def _start_engines(
    city_root: Optional[Path],
    *,
    desk_port: int = _DEFAULT_DESK_PORT,
    workforce_port: int = _DEFAULT_WORKFORCE_PORT,
) -> tuple:
    """Spawn WorkLane + WorkForce when not already listening (pc-575).

    Census (citylens) is in-process on the suite process — no :8796 spawn.
    Returns (children, suite_env_extra). Only processes we started are in
    children (for try/finally cleanup). Honest bind: if a port already
    answers, skip spawn for that engine.
    """
    children: List[subprocess.Popen] = []
    suite_urls: dict = {}
    base_env = dict(os.environ)

    if city_root is not None:
        base_env["TP_CITY_ROOT"] = str(city_root)
        base_env["SUITE_CITY_ROOT"] = str(city_root)
        # Wire WorkLane runtime to where engine data actually lives (pc-637).
        # Priority: env-pin → worklane checkout adjacent to city → city-scoped dir.
        if "TICKETING_PROTOCOL_RUNTIME_DIR" not in os.environ:
            _wl_checkout = None
            for _parent in (city_root, city_root.parent):
                _co = _parent / "worklane"
                # Package dir is worklane/ (wl-280).
                _co_data = _co / "worklane" / "local" / "data"
                if _co_data.is_dir() and any(_co_data.glob("*.db")):
                    _wl_checkout = _co
                    break
            if _wl_checkout is not None:
                base_env["TICKETING_PROTOCOL_RUNTIME_DIR"] = str(_wl_checkout)
                print("── engines: WorkLane runtime → checkout %s ──" % _wl_checkout)
            else:
                wl_runtime = city_root / ".protocolcity" / "worklane"
                wl_runtime.mkdir(parents=True, exist_ok=True)
                base_env["TICKETING_PROTOCOL_RUNTIME_DIR"] = str(wl_runtime)
        # WorkForce home under city so roster/local never depends on CWD.
        # Keep under .protocolcity/ so census does not treat it as a neighborhood.
        # Daemon writes local/daemon.json every tick — local/ must exist.
        # Canonical roster (pc-351): .protocolcity/workforce/local/roster.json
        # — same path hire writes; suite SUITE_WF_ROSTER must match.
        wf_home = city_root / ".protocolcity" / "workforce"
        wf_local = wf_home / "local"
        wf_local.mkdir(parents=True, exist_ok=True)
        wf_roster = wf_local / "roster.json"
        base_env.setdefault("WORKFORCE_DATA_DIR", str(wf_home))
        base_env.setdefault("WORKFORCE_ROSTER", str(wf_roster))
        suite_urls["SUITE_WF_ROSTER"] = str(wf_roster)
        # Plug-and-play: L0 workspace ops jobs
        # (chief-of-staff · health-patrol · workspace-efficiency)
        # so Map JOBS ring is not empty for first users.
        try:
            from protocolcity.seed_ops import seed_workspace_ops

            receipt = seed_workspace_ops(city_root, quiet=False)
            if receipt.get("seeded"):
                print(
                    "── seed-ops: %s ──"
                    % ", ".join(receipt["seeded"])
                )
            elif receipt.get("error") and not receipt.get("skipped"):
                print(
                    "── seed-ops: skipped (%s) ──" % receipt.get("error"),
                    file=sys.stderr,
                )
        except Exception as e:
            print("── seed-ops: failed (%s) ──" % e, file=sys.stderr)

    # ── WorkLane (Desk) ──────────────────────────────────────────────
    # Public package imports as `worklane` (protocolcity-worklane on PyPI).
    desk_url = "http://127.0.0.1:%d" % desk_port
    suite_urls["SUITE_DESK_URL"] = desk_url
    if _url_ready(desk_url + "/"):
        _n = _desk_product_count(desk_url)
        if _n > 0:
            print(
                "── engines: WorkLane already up at :%d (%d store%s) ──"
                % (desk_port, _n, "s" if _n != 1 else "")
            )
        else:
            print("── engines: WorkLane already up at :%d ──" % desk_port)
    else:
        # pc-668: ownership detection — never shadow an external desk service.
        # If a host launchd service owns :8799, do not spawn the bundled engine.
        # The suite's stop/reinstall cycle would otherwise create a takeover
        # window serving the wrong (empty) desk data with healthy-looking 200s.
        _ext_label = _external_desk_launchd_label()
        if _ext_label is not None:
            _uid = _uid_str()
            print(
                "\n── EXTERNAL DESK SERVICE DETECTED ──\n"
                "   WorkLane is managed by launchd service %s\n"
                "   but :%d is not answering. The suite will not shadow it\n"
                "   with its bundled engine. To restart the external service:\n"
                "     launchctl kickstart -k gui/%s/%s\n"
                "   or check: launchctl print gui/%s/%s"
                % (_ext_label, desk_port, _uid, _ext_label, _uid, _ext_label),
                file=sys.stderr,
            )
            _terminate_children(children)
            raise SystemExit(4)
        if _module_importable("worklane"):
            wl_mod = "worklane.server"
        else:
            print(
                "error: WorkLane not importable (worklane). "
                "Install protocolcity-worklane, or omit --with-engines and "
                "start the desk separately.",
                file=sys.stderr,
            )
            _terminate_children(children)
            raise SystemExit(2)
        env = dict(base_env)
        env["TASK_PORT"] = str(desk_port)
        env["TASK_HOST"] = "127.0.0.1"
        print("── engines: starting WorkLane on :%d ──" % desk_port)
        wl_log_path, wl_log = _engine_log_open(city_root, "worklane")
        children.append(
            subprocess.Popen(
                [sys.executable, "-m", wl_mod],
                env=env,
                stdout=wl_log,
                stderr=wl_log,
                **_engine_popen_kwargs(),
            )
        )
        wl_log.close()
        if not _wait_ready(desk_url + "/"):
            _engine_failed("WorkLane", desk_url, wl_log_path)
            _terminate_children(children)
            raise SystemExit(3)

    # pc-314: desk answers — run store joins deferred while it was offline
    # (found/adopt with the desk down queue into .protocolcity/pending-desk.json).
    if city_root is not None:
        try:
            for r in flush_pending_joins(city_root, desk_url=desk_url):
                state = (
                    "joined"
                    if r.get("ok")
                    else "join failed: %s" % (r.get("error") or "unknown")
                )
                print("── engines: pending desk join · %s — %s ──" % (r.get("slug"), state))
        except Exception as e:  # never block serve on the backfill
            print("warning: pending desk joins not flushed: %s" % e, file=sys.stderr)

    # ── WorkForce (Roster) ───────────────────────────────────────────
    wf_url = "http://127.0.0.1:%d" % workforce_port
    suite_urls["SUITE_WORKFORCE_URL"] = wf_url
    if _url_ready(wf_url + "/"):
        print("── engines: WorkForce already up at :%d ──" % workforce_port)
    else:
        if not _module_importable("workforce"):
            print(
                "error: WorkForce not importable (workforce). "
                "Install protocolcity-workforce, or omit --with-engines.",
                file=sys.stderr,
            )
            _terminate_children(children)
            raise SystemExit(2)
        env = dict(base_env)
        env["WORKFORCE_PORT"] = str(workforce_port)
        print("── engines: starting WorkForce on :%d ──" % workforce_port)
        wf_log_path, wf_log = _engine_log_open(city_root, "workforce")
        children.append(
            subprocess.Popen(
                # package __main__ → workforce.cli:main (same as console script)
                [sys.executable, "-m", "workforce", "daemon"],
                env=env,
                stdout=wf_log,
                stderr=wf_log,
                **_engine_popen_kwargs(),
            )
        )
        wf_log.close()
        if not _wait_ready(wf_url + "/"):
            _engine_failed("WorkForce", wf_url, wf_log_path)
            _terminate_children(children)
            raise SystemExit(3)

    # pc-637: if the desk came up with 0 products but the city has joined folders,
    # the engine is pointing at the wrong data dir — warn loudly.
    if city_root is not None and _desk_product_count(desk_url) == 0:
        try:
            _joined = [
                f
                for f in city_root.iterdir()
                if f.is_dir() and (f / ".protocolcity" / "desk-join.json").exists()
            ]
        except OSError:
            _joined = []
        if _joined:
            _names = ", ".join(f.name for f in _joined[:3])
            if len(_joined) > 3:
                _names += " …"
            # pc-668: if an external desk label is registered, this is a
            # MISMATCHED DESK (bundled engine shadowing the real one).
            _ext = _external_desk_launchd_label()
            if _ext:
                _mismatch = (
                    "\n   MISMATCHED DESK (pc-668): the bundled engine is\n"
                    "   serving empty data. Kill it and restore the host service:\n"
                    "     launchctl kickstart -k gui/%s/%s" % (_uid_str(), _ext)
                )
            else:
                _mismatch = (
                    "\n   Fix: set TICKETING_PROTOCOL_RUNTIME_DIR to your WorkLane\n"
                    "   checkout root, then: blueprint serve --root %s" % city_root
                )
            print(
                "\n── WARNING: WorkLane has 0 product stores but\n"
                "   %d joined folder%s found (%s).\n"
                "   Your desk data is intact but invisible — the engine is\n"
                "   pointing at the wrong data dir.%s ──\n"
                % (len(_joined), "s" if len(_joined) != 1 else "", _names, _mismatch),
                file=sys.stderr,
            )

    # pc-575: no citylens :8796 — suite serves census in-process (fold B pc-574).
    print(
        "── engines ready: desk :%d · roster :%d ── (census in suite)"
        % (desk_port, workforce_port)
    )
    return children, suite_urls


def _load_citylens():
    citylens = resolve_citylens()
    if not citylens.is_file():
        raise FileNotFoundError(
            "citylens not found at %s — install from the ProtocolCity repo "
            "(editable: pip install -e .) or set PROTOCOLCITY_CITYLENS"
            % citylens
        )
    # pc-639: office/ was archived (pc-581) and is no longer shipped with the
    # package. citylens itself handles missing assets gracefully via
    # _resolve_lumber_dir(). The hard asset check here blocked snapshot on
    # every packaged install.
    spec = importlib.util.spec_from_file_location("protocolcity_citylens", citylens)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load citylens from %s" % citylens)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["protocolcity_citylens"] = mod
    spec.loader.exec_module(mod)
    return mod


def _cmd_demo(args: argparse.Namespace) -> int:
    """End-to-end founding proof for install-ready demos."""
    import tempfile

    root = Path(args.path) if args.path else Path(tempfile.mkdtemp(prefix="pc-demo-"))
    port = args.port
    print("── demo workspace at %s ──" % root)
    try:
        receipt = found(
            root,
            city_name=args.name or "Demo City",
            neighborhood=args.neighborhood,
            force=True,
            with_desk=not args.no_desk,
            desk_url=args.desk,
            sample_ticket=not args.no_ticket,
            map_port=port,
        )
    except Exception as e:
        print("error: found failed: %s" % e, file=sys.stderr)
        return 2
    print_receipt(receipt)

    print("── snapshot ──")
    citylens = _load_citylens()
    # capture snapshot via function if available
    try:
        from io import StringIO
        import contextlib

        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            citylens.main(["--root", str(root), "snapshot"])
        raw = buf.getvalue()
        data = json.loads(raw)
    except Exception as e:
        print("snapshot failed: %s" % e, file=sys.stderr)
        return 2
    hoods = [h.get("name") for h in data.get("neighborhoods") or []]
    print("projects:", hoods)
    if args.neighborhood not in hoods:
        print("error: expected project %r in %r" % (args.neighborhood, hoods), file=sys.stderr)
        return 3
    store = None
    for h in data.get("neighborhoods") or []:
        if h.get("name") == args.neighborhood:
            store = h.get("store")
            print("store:", store, "flags:", h.get("flags"))
    print("SNAPSHOT OK")

    if args.serve:
        print("── demo serve on :%d (Ctrl-C to stop) ──" % port)
        return citylens.main(["--root", str(root), "serve", "--port", str(port)])

    # smoke-serve briefly — pick a free port so we never collide with :8796/live
    import socket

    def _free_port(preferred: int) -> int:
        for p in (preferred, preferred + 1, preferred + 2, 0):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
                assigned = s.getsockname()[1]
                s.close()
                return assigned
            except OSError:
                s.close()
                continue
        return preferred

    port = _free_port(port)
    print("── serve smoke (port %d) ──" % port)
    citylens_path = resolve_citylens()
    proc = subprocess.Popen(
        [sys.executable, str(citylens_path), "--root", str(root), "serve", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        code = None
        for _ in range(30):
            time.sleep(0.2)
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:%d/" % port, timeout=1
                ) as r:
                    code = r.status
                    break
            except Exception:
                continue
        api_ok = False
        root_ok = False
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/city" % port, timeout=3
            ) as r:
                api = json.loads(r.read().decode())
                names = [h.get("name") for h in api.get("neighborhoods") or []]
                api_ok = args.neighborhood in names
                # resolve symlinks / private tmp paths
                served = str(api.get("city_root") or "")
                root_ok = (
                    Path(served).resolve() == Path(root).resolve()
                    or served.rstrip("/") == str(root).rstrip("/")
                    or str(Path(root).resolve()) in served
                    or served in str(Path(root).resolve())
                )
        except Exception:
            api_ok = False
        print(
            "GET / →",
            code,
            "· project →",
            api_ok,
            "· workspace_root match →",
            root_ok,
        )
        if code != 200 or not api_ok or not root_ok:
            return 4
        print("── DEMO PROOF PASSED ──")
        print("Engine: :%d (citylens smoke — run `blueprint serve` for the suite)" % port)
        print("Root: %s" % root)
        print("(smoke server stopped; re-run with --serve to keep the engine up)")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


def _resolve_suite_serve_py() -> Optional[Path]:
    """Locate suite/serve.py for the serve child process.

    BLUEPRINT_SUITE_DIR (env) = ProtocolCity repo root → forces source tree,
    skipping the Cellar copy (dev mode, pc-788). Otherwise importlib.resources
    wins when installed; editable checkout is the final fallback.
    """
    # Dev override: set BLUEPRINT_SUITE_DIR to the ProtocolCity repo root and
    # blueprint serve reads directly from source — no Cellar sync needed.
    dev_root = os.environ.get("BLUEPRINT_SUITE_DIR", "").strip()
    if dev_root:
        cand = Path(dev_root) / "suite" / "serve.py"
        if cand.is_file():
            return cand.resolve()
    try:
        import importlib.resources

        suite_ref = importlib.resources.files("suite").joinpath("serve.py")
        if suite_ref.is_file():
            with importlib.resources.as_file(suite_ref) as p:
                path = Path(p)
                if path.is_file():
                    return path
    except Exception:
        pass
    # Editable / source tree: …/ProtocolCity/protocolcity/cli.py → ../suite/serve.py
    here = Path(__file__).resolve().parent
    cand = here.parent / "suite" / "serve.py"
    if cand.is_file():
        return cand
    # PYTHONPATH / CWD
    for base in (Path.cwd(), Path(os.environ.get("SUITE_PACKAGE_ROOT") or "")):
        if not base or str(base) in (".", ""):
            continue
        cand = base / "suite" / "serve.py"
        if cand.is_file():
            return cand
    return None


def _run_serve_with_engines(city_root: Path, port: int) -> int:
    """Shared serve path for `serve` and `setup --serve`.

    Stops any prior suite/engine listeners first so non-technical open after
    reinstall never hits Address already in use (0.1.10).
    """
    suite_script = _resolve_suite_serve_py()
    if suite_script is None:
        print(
            "error: suite/serve.py not found "
            "(install protocolcity package or run from the ProtocolCity tree)",
            file=sys.stderr,
        )
        return 2

    # Free suite port only — do NOT kill engines (may be other launchd units)
    # and do NOT bootout this login agent (would kill launchd-started serve).
    stop_suite_processes(
        quiet=False,
        bootout_login_agent=False,
        ports=[port],
        kill_patterns=False,
    )

    env = dict(os.environ)
    env["SUITE_PORT"] = str(port)
    root = city_root.expanduser().resolve()
    env["SUITE_CITY_ROOT"] = str(root)
    # Ensure suite package dir is importable if serve.py does relative imports
    suite_dir = str(suite_script.parent)
    prev_pp = env.get("PYTHONPATH") or ""
    if suite_dir not in prev_pp.split(os.pathsep):
        env["PYTHONPATH"] = (
            suite_dir + (os.pathsep + prev_pp if prev_pp else "")
        )
    # Parent of suite/ so `import suite` works for any helpers
    pkg_root = str(suite_script.parent.parent)
    if pkg_root not in env["PYTHONPATH"].split(os.pathsep):
        env["PYTHONPATH"] = pkg_root + os.pathsep + env["PYTHONPATH"]

    engine_children: List[subprocess.Popen] = []
    suite_proc: Optional[subprocess.Popen] = None

    # pc-1008: AbandonProcessGroup=true in the plist means launchd only sends
    # SIGTERM to this parent process, NOT to serve.py child — so the child
    # survives as an orphan holding :port. Converting SIGTERM→SystemExit lets
    # the finally block reap serve.py before this process exits.
    _prev_sigterm = None
    if sys.platform != "win32":
        _prev_sigterm = signal.getsignal(signal.SIGTERM)

        def _sigterm_to_exit(sig: int, frame: object) -> None:
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, _sigterm_to_exit)

    try:
        engine_children, suite_urls = _start_engines(
            root,
            desk_port=int(
                os.environ.get("PROTOCOLCITY_DESK_PORT") or _DEFAULT_DESK_PORT
            ),
            workforce_port=int(
                os.environ.get("PROTOCOLCITY_WORKFORCE_PORT")
                or _DEFAULT_WORKFORCE_PORT
            ),
        )
        env.update(suite_urls)
        print(
            "── suite http://127.0.0.1:%d/  (Ctrl-C stops suite + "
            "engines we started) ──" % port
        )
        # launchd path: stay foreground; do not kill engines we did not start
        # when login agent only runs the suite (engines may be separate).
        suite_proc = subprocess.Popen(
            [sys.executable, str(suite_script)],
            env=env,
            cwd=str(suite_script.parent.parent),
        )
        suite_proc.wait()
        return suite_proc.returncode
    finally:
        if sys.platform != "win32" and _prev_sigterm is not None:
            signal.signal(signal.SIGTERM, _prev_sigterm)
        # Always reap suite_proc — under launchd or not. Unlike engine children
        # (separate launchd units we leave up), serve.py is our direct child.
        if suite_proc is not None and suite_proc.poll() is None:
            suite_proc.terminate()
            try:
                suite_proc.wait(timeout=5)
            except Exception:
                suite_proc.kill()
        # pc-536: under launchd KeepAlive, suite restarts every thrash cycle.
        # Killing engines we started (WorkLane especially) dual-owns the desk
        # and amplifies mid-shift death. Leave them up; next start honest-binds.
        # Interactive Ctrl-C (no XPC_SERVICE_NAME) still stops our children.
        if engine_children:
            if _under_launchd():
                print(
                    "── engines: leaving %d child(ren) up "
                    "(launchd suite restart; honest-bind next time) ──"
                    % len(engine_children)
                )
            else:
                print("── engines: stopping children we started ──")
                _terminate_children(engine_children)


def main(argv: Optional[List[str]] = None) -> int:
    actual = list(sys.argv[1:] if argv is None else argv)
    if actual and actual[0] in ('serve', 'status', 'service', 'stage', 'activate', 'update', 'install', 'uninstall'):
        from .operations_cli import main as current
        return current(actual)
    # Taught face is blueprint; fall back to argv basename for module form.
    _prog = "blueprint"
    try:
        _base = Path(sys.argv[0]).name if sys.argv else ""
        if _base and _base not in ("__main__.py", "-c", "python", "python3"):
            _prog = _base
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog=_prog,
        description=(
            "ProtocolCity BluePrint — setup a workspace, serve the suite, "
            "or uninstall."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_setup = sub.add_parser(
        "setup",
        help=(
            "first-run: create or adopt a workspace "
            "(interactive menu, or flags for scripts)"
        ),
    )
    p_setup.add_argument(
        "path",
        nargs="?",
        default=None,
        help=(
            "workspace folder path (create: default prompt ~/ProtocolCity; "
            "adopt-workspace: required — full path to existing folder)"
        ),
    )
    p_setup.add_argument(
        "--create",
        action="store_true",
        help="create / found a new workspace at path",
    )
    p_setup.add_argument(
        "--adopt-workspace",
        action="store_true",
        help="use an existing folder as the workspace (plant L0 law only)",
    )
    p_setup.add_argument(
        "--adopt-project",
        metavar="NAME",
        default=None,
        help=(
            "agent/script: manage one top-level project under a founded workspace "
            "(humans: Map right-click → Adopt, or blueprint adopt)"
        ),
    )
    p_setup.add_argument(
        "--all-unmanaged",
        "--adopt-existing",
        action="store_true",
        dest="all_unmanaged",
        help=(
            "after workspace is ready, adopt every safe unmanaged top-level folder "
            "(alias: --adopt-existing; pc-571 / GH#6)"
        ),
    )
    p_setup.add_argument(
        "--project",
        default=None,
        help="optional first project name when using --create",
    )
    p_setup.add_argument(
        "--demo",
        action="store_true",
        help=argparse.SUPPRESS,  # removed — setup never plants a default/demo project
    )
    p_setup.add_argument(
        "--no-demo",
        action="store_true",
        help=argparse.SUPPRESS,  # no-op; setup never plants a demo project
    )
    p_setup.add_argument(
        "--serve",
        action="store_true",
        help="open the suite with engines after setup",
    )
    p_setup.add_argument(
        "--service",
        action="store_true",
        help=(
            "install macOS login LaunchAgent after setup "
            "(required for --yes / scripts; interactive default is Yes with opt-out)"
        ),
    )
    p_setup.add_argument(
        "--no-service",
        action="store_true",
        help="skip login service after setup (opt out of always-on)",
    )
    p_setup.add_argument(
        "--isolated",
        action="store_true",
        help=(
            "test-only service repro: dedicated launchd label/config, no engines; "
            "requires --service and a non-production --port"
        ),
    )
    p_setup.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="non-interactive defaults (no prompts)",
    )
    p_setup.add_argument("--force", action="store_true")
    p_setup.add_argument("--no-desk", action="store_true")
    p_setup.add_argument("--no-ticket", action="store_true")
    p_setup.add_argument("--desk", default=DEFAULT_DESK)
    p_setup.add_argument("--port", type=int, default=8801)

    p_stop = sub.add_parser(
        "stop",
        help=(
            "stop suite + engines on default ports (idempotent; "
            "bootouts login LaunchAgent first so KeepAlive does not revive)"
        ),
    )
    p_stop.add_argument(
        "--quiet",
        action="store_true",
        help="no console noise when nothing is running",
    )

    p_service = sub.add_parser(
        "service",
        help=(
            "macOS login LaunchAgent — keep suite+engines up without a terminal "
            "(pc-433)"
        ),
    )
    svc_sub = p_service.add_subparsers(dest="service_cmd")
    p_svc_install = svc_sub.add_parser(
        "install",
        help="install RunAtLoad+KeepAlive agent for this workspace",
    )
    p_svc_install.add_argument(
        "--root",
        default=None,
        help="workspace root (default: SUITE_CITY_ROOT / registry / cwd walk-up)",
    )
    p_svc_install.add_argument(
        "--port",
        type=int,
        default=8801,
        help="suite port (default 8801)",
    )
    p_svc_install.add_argument(
        "--isolated",
        action="store_true",
        help=(
            "test-only: use com.protocolcity.suite.test, isolated config, "
            "and no engines"
        ),
    )
    p_svc_install.add_argument(
        "--force",
        action="store_true",
        help="replace a registration that points at a different workspace root",
    )
    p_svc_install.add_argument(
        "--dogfood",
        action="store_true",
        help=(
            "founder host: serve Map glass from ProtocolCity source "
            "(BLUEPRINT_SUITE_DIR). Resolves <workspace>/ProtocolCity or "
            "env BLUEPRINT_SUITE_DIR unless --suite-dir is set."
        ),
    )
    p_svc_install.add_argument(
        "--suite-dir",
        default=None,
        help=(
            "ProtocolCity repo root for dogfood glass "
            "(sets BLUEPRINT_SUITE_DIR; implies --dogfood)"
        ),
    )
    p_svc_uninstall = svc_sub.add_parser(
        "uninstall",
        help="bootout + remove the login agent (does not delete workspace)",
    )
    p_svc_uninstall.add_argument(
        "--isolated",
        action="store_true",
        help="remove only the isolated test service",
    )
    p_svc_status = svc_sub.add_parser(
        "status",
        help="show whether the login agent is loaded",
    )
    p_svc_status.add_argument(
        "--isolated",
        action="store_true",
        help="inspect only the isolated test service",
    )
    p_svc_start = svc_sub.add_parser(
        "start",
        help=(
            "bootstrap/kickstart existing agent; reinstall if root is missing "
            "or --root points at a different live workspace"
        ),
    )
    p_svc_start.add_argument(
        "--root",
        default=None,
        help="reinstall agent onto this workspace when set (or when stored root is dead)",
    )
    p_svc_start.add_argument(
        "--force",
        action="store_true",
        help="allow --root to replace a live registration for another workspace",
    )

    p_uninstall = sub.add_parser(
        "uninstall",
        help=(
            "stop suite/engines, forget registry paths (files always stay on disk), "
            "optionally the Homebrew app"
        ),
    )
    p_uninstall.add_argument(
        "--root",
        action="append",
        dest="roots",
        default=None,
        help="workspace path (repeatable); default = all registered",
    )
    p_uninstall.add_argument(
        "--keep-workspace",
        action="store_true",
        help="legacy no-op — workspace files are always kept on disk",
    )
    p_uninstall.add_argument(
        "--delete-workspace",
        action="store_true",
        help=argparse.SUPPRESS,  # rejected in run_uninstall — never delete user folders
    )
    p_uninstall.add_argument(
        "--app",
        action="store_true",
        help="also run: brew uninstall protocolcity/tap/blueprint",
    )
    p_uninstall.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="non-interactive (files always kept; registry left unless --forget)",
    )
    p_uninstall.add_argument(
        "--forget",
        action="store_true",
        help="remove workspace path(s) from BluePrint's list only (files stay)",
    )
    p_uninstall.add_argument(
        "--no-stop",
        action="store_true",
        help="do not stop suite/engine processes (default: stop like quitting the app)",
    )
    p_uninstall.add_argument(
        "--isolated",
        action="store_true",
        help=(
            "test-only: remove the isolated service/config registry without "
            "stopping production ports"
        ),
    )

    p_found = sub.add_parser(
        "found",
        help=(
            "scaffold workspace instructions into a directory you name "
            "(optional first project via --project)"
        ),
    )
    p_found.add_argument(
        "path",
        help=(
            "workspace root path — you choose the name "
            "(e.g. ~/Developer, ~/my-city, ~/work); created if missing"
        ),
    )
    p_found.add_argument(
        "--name",
        default=None,
        help="display name (default: basename of path)",
    )
    p_found.add_argument(
        "--project",
        "--neighborhood",
        default=None,
        dest="neighborhood",
        metavar="NAME",
        help=(
            "optional first project folder under the workspace — any name you want "
            "(no default; omit to found an empty registry and adopt existing folders later)"
        ),
    )
    p_found.add_argument("--force", action="store_true", help="overwrite existing papers")
    p_found.add_argument(
        "--no-desk",
        action="store_true",
        help="skip WorkLane store/ticket bootstrap even if desk is up",
    )
    p_found.add_argument(
        "--no-ticket",
        action="store_true",
        help="create store but do not file a sample work order",
    )
    p_found.add_argument(
        "--desk",
        default=DEFAULT_DESK,
        help="WorkLane base URL (default: CITY_DESK or http://127.0.0.1:8799)",
    )
    p_found.add_argument(
        "--port",
        type=int,
        default=8801,
        help="Map port printed in FIRST_RUN.md (default 8801)",
    )
    p_found.add_argument(
        "--adopt-existing",
        "--all-unmanaged",
        action="store_true",
        dest="adopt_existing",
        help=(
            "after founding, adopt every safe unmanaged top-level folder already "
            "under the workspace (pc-571 / GH#6; same as setup --adopt-existing)"
        ),
    )
    p_found.add_argument(
        "--hire",
        action="store_true",
        help=(
            "run the printed standard-seat-set `workforce hire` commands for "
            "--project (AGENT_ADOPTION D12) — default is print only"
        ),
    )
    p_found.add_argument(
        "--held",
        action="append",
        default=[],
        metavar="PROVIDER",
        help="mark PROVIDER's standard-seat hire command --held (repeatable)",
    )
    p_found.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan (law + standard-seat commands) — write nothing",
    )

    p_adopt = sub.add_parser(
        "adopt",
        help=(
            "manage an existing top-level folder as a project "
            "(keeps the folder name you already have; plants law + desk join; "
            "worker stubs only with --with-demo-worker)"
        ),
    )
    p_adopt.add_argument(
        "city",
        metavar="WORKSPACE",
        help="workspace root (the folder you founded)",
    )
    p_adopt.add_argument(
        "neighborhood",
        metavar="PROJECT",
        nargs="?",
        default=None,
        help=(
            "existing top-level folder name to adopt as a project "
            "(your name, not ProtocolCity's — e.g. tradeOS, recipes, client-acme). "
            "Omit when using --all-unmanaged."
        ),
    )
    p_adopt.add_argument(
        "--all-unmanaged",
        "--adopt-existing",
        action="store_true",
        dest="all_unmanaged",
        help=(
            "adopt every safe unmanaged top-level folder under the workspace "
            "(alias: --adopt-existing; pc-571 / GH#6)"
        ),
    )
    p_adopt.add_argument("--force", action="store_true", help="overwrite existing papers")
    p_adopt.add_argument("--no-desk", action="store_true", help="skip desk store join")
    p_adopt.add_argument(
        "--live-desk",
        action="store_true",
        help=(
            "allow desk store join when zone is foreign/export/archive "
            "(founder-present; default refuses live WorkLane pollution — pc-1186)"
        ),
    )
    p_adopt.add_argument("--desk", default=DEFAULT_DESK, help="WorkLane base URL")
    p_adopt.add_argument(
        "--with-demo-worker",
        action="store_true",
        help=(
            "plant unarmed workers/demo-worker CONTRACT+prompt stubs "
            "(default: no stubs — work-order-only projects stay clean; pc-489)"
        ),
    )
    p_adopt.add_argument(
        "--hire",
        action="store_true",
        help=(
            "run the printed standard-seat-set `workforce hire` commands "
            "(AGENT_ADOPTION D12) — default is print only, adoption never "
            "registers agents silently"
        ),
    )
    p_adopt.add_argument(
        "--held",
        action="append",
        default=[],
        metavar="PROVIDER",
        help="mark PROVIDER's standard-seat hire command --held (repeatable)",
    )
    p_adopt.add_argument(
        "--dry-run",
        action="store_true",
        help="explicit no-op — printing the standard-seat commands without --hire is the default",
    )

    p_doctor = sub.add_parser(
        "doctor",
        help="diagnose (and optionally fix) missing workspace/project BluePrint papers",
    )
    p_doctor.add_argument(
        "city",
        nargs="?",
        default=".",
        metavar="WORKSPACE",
        help="workspace root (default: cwd)",
    )
    p_doctor.add_argument(
        "--neighborhood",
        default=None,
        dest="neighborhood",
        help="top-level folder to diagnose/fix (Adopt path)",
    )
    p_doctor.add_argument(
        "--cabinet",
        default=None,
        dest="cabinet",
        help="back-compat alias for --neighborhood (pc-320)",
    )
    p_doctor.add_argument(
        "--fix",
        action="store_true",
        help="plant missing papers only (never clobber diverged law without --force)",
    )
    p_doctor.add_argument(
        "--force",
        action="store_true",
        help=(
            "clobber existing thin stubs / seed files when refreshing "
            "(not required to plant *missing* L0 kits — use --fix alone; pc-1162)"
        ),
    )
    p_doctor.add_argument(
        "--no-desk",
        action="store_true",
        help="skip desk store join when fixing a project",
    )
    p_doctor.add_argument(
        "--live-desk",
        action="store_true",
        help=(
            "allow desk join when project zone is foreign/export/archive "
            "(founder-present; default refuses — pc-1186)"
        ),
    )
    p_doctor.add_argument("--desk", default=DEFAULT_DESK, help="WorkLane base URL")
    p_doctor.add_argument("--json", action="store_true", help="print JSON report")
    p_doctor.add_argument(
        "--fix-papers",
        action="store_true",
        dest="fix_papers",
        help="regenerate bp:generated blocks in AGENTS files from desk scene and roster",
    )
    p_doctor.add_argument(
        "--check-paths",
        action="store_true",
        dest="check_paths",
        help=(
            "lint suite/protocolcity/scripts for host-path hardcodes "
            "(~/Developer, /Users/…); see scripts/check_no_host_paths.py (pc-956)"
        ),
    )

    p_reloc = sub.add_parser(
        "relocate-root",
        help=(
            "after renaming/moving a workspace folder: rewrite service, "
            "registry, roster, LaunchAgents, skill bridges, grok paths, "
            "and project vendor configs (GH #7 · pc-959 · portable cities)"
        ),
    )
    p_reloc.add_argument(
        "--from",
        dest="from_root",
        required=True,
        help="previous workspace path (may no longer exist on disk)",
    )
    p_reloc.add_argument(
        "--to",
        dest="to_root",
        required=True,
        help="new workspace path (must exist)",
    )
    p_reloc.add_argument(
        "--name",
        default=None,
        help="display name in registry (default: new folder basename)",
    )
    p_reloc.add_argument(
        "--no-reload",
        action="store_true",
        help="rewrite LaunchAgent plists but do not bootout/bootstrap",
    )
    p_reloc.add_argument(
        "--no-service",
        action="store_true",
        help="skip suite service reinstall (still rewrites paths)",
    )
    p_reloc.add_argument(
        "--no-sync",
        action="store_true",
        help="skip skills_sync.sh after path rewrites",
    )
    p_reloc.add_argument(
        "--dry-run",
        action="store_true",
        help="show full plan without writing, reloading, or reinstalling",
    )
    p_reloc.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable receipt",
    )

    p_update = sub.add_parser(
        "update",
        help=(
            "upgrade BluePrint suite to the latest release (Homebrew or pip) "
            "— pair with --agent-prompt for Cursor/any AI (pc-565)"
        ),
    )
    p_update.add_argument(
        "--method",
        choices=("auto", "brew", "pip"),
        default="auto",
        help="install channel (default: auto-detect brew, else pip)",
    )
    p_update.add_argument(
        "--restart",
        action="store_true",
        help="after upgrade: stop suite and try service start (or print serve hint)",
    )
    p_update.add_argument(
        "--root",
        default=None,
        help="workspace root for --restart (default: cwd)",
    )
    p_update.add_argument(
        "--agent-prompt",
        action="store_true",
        help="print the paste-into-AI upgrade ritual only (no upgrade)",
    )
    p_update.add_argument(
        "--dry-run",
        action="store_true",
        help="show detected method and versions without upgrading",
    )

    p_feedback = sub.add_parser(
        "feedback",
        help=(
            "paste-ready beta bug report (versions, doctor, logs) — local only "
            "(pc-317/pc-434); pair with --agent-prompt for Cursor/any AI"
        ),
    )
    p_feedback.add_argument(
        "city",
        nargs="?",
        default=".",
        help="workspace root (default: cwd)",
    )
    p_feedback.add_argument(
        "--full-paths",
        action="store_true",
        help="include absolute paths (default: scrub home → ~)",
    )
    p_feedback.add_argument(
        "--agent-prompt",
        action="store_true",
        help="print the paste-into-AI ritual only (no doctor/logs)",
    )
    p_feedback.add_argument(
        "--symptoms",
        default="",
        help="one-line or short summary to prefill the Summary section",
    )
    p_feedback.add_argument(
        "--write",
        action="store_true",
        help="also write .protocolcity/reports/feedback-*.md under the workspace",
    )
    p_feedback.add_argument(
        "--open",
        action="store_true",
        help="open BluePrint issues page in the browser (still no upload)",
    )

    p_serve = sub.add_parser(
        "serve",
        help=(
            "serve BluePrint suite (Overview landing · Map · Desk · Roster); "
            "when a login LaunchAgent is installed, kickstarts it (pc-1072) "
            "instead of a foreground orphan"
        ),
    )
    p_serve.add_argument("--root", default=None, help="workspace root (sets SUITE_CITY_ROOT)")
    p_serve.add_argument("--port", type=int, default=8801)
    p_serve.add_argument(
        "--foreground",
        action="store_true",
        help=(
            "force a terminal-owned suite process even when a login service is "
            "installed (pc-1072; dies with the shell — prefer launchd restart)"
        ),
    )
    p_serve.add_argument(
        "--with-engines",
        action="store_true",
        help=(
            "start WorkLane (:8799) + WorkForce (:8797) before the suite "
            "(pc-575: census is in-process — no citylens/:8796). Default when "
            "a workspace root is resolved (pc-421); this flag is kept for scripts."
        ),
    )
    p_serve.add_argument(
        "--no-engines",
        action="store_true",
        help="suite UI only — do not start WorkLane / WorkForce",
    )

    p_snap = sub.add_parser("snapshot", help="print /api/city JSON (no server)")
    p_snap.add_argument("--root", default=None, help="workspace root")

    p_hide = sub.add_parser(
        "hide",
        help="hide a folder from Map plots (display-only; writes .protocolcity/hidden.json)",
    )
    p_hide.add_argument("folder", help="folder name or path (slug = basename, lowercased)")
    p_hide.add_argument(
        "--root",
        default=None,
        help="workspace root (default: SUITE_CITY_ROOT or cwd with AGENTS.md)",
    )

    p_unhide = sub.add_parser(
        "unhide",
        help="restore a folder to Map plots (display-only)",
    )
    p_unhide.add_argument("folder", help="folder name or path (slug = basename, lowercased)")
    p_unhide.add_argument(
        "--root",
        default=None,
        help="workspace root (default: SUITE_CITY_ROOT or cwd with AGENTS.md)",
    )

    p_detect = sub.add_parser("detect", help="list vendor agent CLIs on PATH")

    # pc-204: first-hire arming wizard (model tier + schedule before owned)
    p_hire = sub.add_parser(
        "hire",
        help="arm a worker (lane) or job: tier + schedule → papers + roster",
        description=(
            "Hire a project **worker/hand** (default, roster kind=lane) that "
            "claims work orders, or a scheduled **job** (kind=job) for duties "
            "like custom automations. Workspace ops jobs "
            "(chief-of-staff/health-patrol/workspace-efficiency) → prefer "
            "`seed-ops`, not a lane hire."
        ),
        epilog=(
            "Grammar (pc-435): worker/hand/agent = claims tickets; "
            "job = scheduled duty (Map diamond). "
            "Paper packs (pc-968): names ending in -desk auto-pick director "
            "CONTRACT/prompt; override with --template worker|director. "
            "Examples:\n"
            "  blueprint hire neo --workdir ~/ws/recipes --role 'notes helper'\n"
            "  blueprint hire recipes-desk --workdir ~/ws/recipes "
            "--role 'Queue director' --project recipes\n"
            "  blueprint seed-ops --root ~/ws\n"
            "  blueprint hire health-patrol --workdir ~/ws/.protocolcity/ops "
            "--kind job --role 'health patrol'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_hire.add_argument(
        "name",
        help="persona name for a hand (e.g. neo, riley) — not reserved ops "
        "ids (chief-of-staff/health-patrol/…) unless --kind job",
    )
    p_hire.add_argument(
        "--workdir",
        required=True,
        help="project root (workers/ planted here)",
    )
    p_hire.add_argument(
        "--role",
        default="",
        help="role title for display (e.g. 'Docs steward')",
    )
    p_hire.add_argument(
        "--kind",
        default="lane",
        metavar="KIND",
        help="lane|worker (default: claims work orders) or job (scheduled duty)",
    )
    p_hire.add_argument(
        "--tier",
        choices=("heavy", "generalist", "patrol", "specialty", "script"),
        default="generalist",
        help="model tier law (STAFFING): heavy=Grok, generalist=Sonnet, "
        "patrol=Haiku, specialty=Cursor/Codex, script=no LLM",
    )
    p_hire.add_argument(
        "--model",
        default="",
        help="override model pin (else tier default)",
    )
    p_hire.add_argument(
        "--schedule",
        default="*/30 * * * *",
        help="five-field cron to arm as owned (default every 30m); "
        "use 'manual' for unscheduled",
    )
    p_hire.add_argument(
        "--project",
        default="",
        help="WorkLane store slug for ready queue (default: workdir basename)",
    )
    p_hire.add_argument(
        "--roster",
        default=None,
        help="path to roster.json (default: "
        "{workspace}/.protocolcity/workforce/local/roster.json)",
    )
    p_hire.add_argument(
        "--dry-run",
        action="store_true",
        help="plant papers only preview; do not write roster",
    )
    p_hire.add_argument(
        "--force-papers",
        action="store_true",
        help="overwrite existing CONTRACT/prompt stubs",
    )
    p_hire.add_argument(
        "--template",
        choices=_HIRE_TEMPLATE_CHOICES,
        default="auto",
        help=(
            "paper pack for CONTRACT/prompt (pc-968): auto picks director when "
            "name ends in -desk, else worker; or force worker|director"
        ),
    )

    p_seed_ops = sub.add_parser(
        "seed-ops",
        help=(
            "plant workspace operations papers without rehiring retired jobs"
        ),
        description=(
            "Plant workspace operations papers; leave employment unchanged by default. "
            "chief-of-staff (coordination), health-patrol, and "
            "workspace-efficiency (drain hygiene). Also plants the L0 "
            "workspace-efficiency skill + scripts/skills_sync.sh. "
            "These are not project workers — they do not claim ordinary work orders. "
            "Idempotent (legacy marshal counts as health-patrol). "
            "For a project hand that claims tickets, use `hire` instead."
        ),
    )
    p_seed_ops.add_argument(
        "--root",
        default=None,
        help="workspace root (default: SUITE_CITY_ROOT or registry)",
    )
    p_seed_ops.add_argument(
        "--quiet",
        action="store_true",
        help="only print JSON receipt",
    )

    p_digest = sub.add_parser(
        "digest",
        help="daily workspace digest — write dated MD + optional ntfy push (pc-712)",
        description=(
            "Run or install the daily workspace digest job. "
            "Writes {ws}/.protocolcity/digests/YYYY-MM-DD.md. "
            "Reads ntfy config from ~/.protocolcity/ntfy.json (or workspace-scoped). "
            "Dry-runs ntfy when config absent or disabled."
        ),
    )
    p_digest.add_argument(
        "--root",
        default=None,
        help="workspace root (default: SUITE_CITY_ROOT or registry)",
    )
    _dig_group = p_digest.add_mutually_exclusive_group()
    _dig_group.add_argument(
        "--run",
        action="store_true",
        default=True,
        help="build and write digest now (default action)",
    )
    _dig_group.add_argument(
        "--install",
        action="store_true",
        help="hire the digest job on the WorkForce roster (idempotent)",
    )
    p_digest.add_argument(
        "--dry-run",
        action="store_true",
        help="skip ntfy push even if configured",
    )
    p_digest.add_argument(
        "--quiet",
        action="store_true",
        help="only print JSON receipt",
    )

    p_demo = sub.add_parser(
        "demo",
        help="found a temp (or given) workspace, snapshot, smoke-serve — install-ready proof",
    )
    p_demo.add_argument(
        "path",
        nargs="?",
        default=None,
        help="optional workspace root (default: fresh temp dir)",
    )
    p_demo.add_argument("--name", default="Demo City")
    # Demo picks an explicit sample name so the proof has a project to assert.
    # Not a product default for `found` (which defaults to no project folder).
    p_demo.add_argument(
        "--project",
        "--neighborhood",
        default="recipes",
        dest="neighborhood",
        metavar="NAME",
        help="demo project folder name (default: recipes — demo-only sample)",
    )
    p_demo.add_argument("--port", type=int, default=8795)
    p_demo.add_argument("--desk", default=DEFAULT_DESK)
    p_demo.add_argument("--no-desk", action="store_true")
    p_demo.add_argument("--no-ticket", action="store_true")
    p_demo.add_argument(
        "--serve",
        action="store_true",
        help="keep the suite server running after the proof",
    )

    args = parser.parse_args(argv)

    if args.cmd == "setup":
        mode = None
        if args.create:
            mode = "create"
        elif args.adopt_workspace:
            mode = "adopt-workspace"
        elif args.adopt_project:
            mode = "adopt-project"
        demo_flag = None
        if getattr(args, "demo", False):
            demo_flag = True
        if getattr(args, "no_demo", False):
            demo_flag = False
        service_flag = None
        if getattr(args, "service", False):
            service_flag = True
        if getattr(args, "no_service", False):
            service_flag = False
        isolated = bool(getattr(args, "isolated", False))
        if isolated and service_flag is not True:
            print(
                "error: --isolated is a service-repro mode and requires --service",
                file=sys.stderr,
            )
            return 2
        previous_config = os.environ.get("PROTOCOLCITY_CONFIG_DIR")
        if isolated:
            from protocolcity.service import (
                PRODUCTION_PORTS,
                isolated_config_dir,
            )

            if int(args.port) in PRODUCTION_PORTS:
                print(
                    "error: --isolated requires a non-production --port "
                    "(for example 18801)",
                    file=sys.stderr,
                )
                return 2
            os.environ["PROTOCOLCITY_CONFIG_DIR"] = str(isolated_config_dir())
        try:
            return run_setup(
                path=args.path,
                mode=mode,
                adopt_project=args.adopt_project,
                all_unmanaged=args.all_unmanaged,
                project=args.project,
                yes=args.yes,
                serve=args.serve,
                force=args.force,
                with_desk=not args.no_desk,
                desk_url=args.desk,
                no_ticket=args.no_ticket,
                map_port=args.port,
                serve_fn=_run_serve_with_engines,
                demo=demo_flag,
                service=service_flag,
                service_isolated=isolated,
            )
        finally:
            if isolated:
                if previous_config is None:
                    os.environ.pop("PROTOCOLCITY_CONFIG_DIR", None)
                else:
                    os.environ["PROTOCOLCITY_CONFIG_DIR"] = previous_config

    if args.cmd == "stop":
        # Best-effort always — brew post_install and upgrades must not fail.
        # Bootout login agent so KeepAlive does not revive (pc-433).
        stop_suite_processes(
            quiet=bool(getattr(args, "quiet", False)),
            bootout_login_agent=True,
        )
        return 0

    if args.cmd == "service":
        from protocolcity.service import (
            install_service,
            service_status,
            uninstall_service,
        )

        sc = getattr(args, "service_cmd", None)
        if sc == "install":
            root = _resolve_city_root(getattr(args, "root", None))
            if root is None:
                print(
                    "error: workspace root not found "
                    "(pass --root or run from a founded workspace)",
                    file=sys.stderr,
                )
                return 2
            suite_dir_arg = getattr(args, "suite_dir", None)
            suite_path = Path(suite_dir_arg).expanduser() if suite_dir_arg else None
            receipt = install_service(
                root,
                port=int(getattr(args, "port", 8801) or 8801),
                isolated=bool(getattr(args, "isolated", False)),
                force=bool(getattr(args, "force", False)),
                dogfood=bool(getattr(args, "dogfood", False) or suite_path),
                suite_dir=suite_path,
            )
            if not receipt.get("ok"):
                print("error: %s" % receipt.get("error"), file=sys.stderr)
                return 1
            port = int(receipt.get("port") or getattr(args, "port", 8801) or 8801)
            return 0 if _wait_for_service_cli_ready(port, action="install") else 1
        if sc == "uninstall":
            receipt = uninstall_service(
                quiet=False,
                isolated=bool(getattr(args, "isolated", False)),
            )
            return 0 if receipt.get("ok") else 1
        if sc == "status":
            print(
                json.dumps(
                    service_status(
                        isolated=bool(getattr(args, "isolated", False))
                    ),
                    indent=2,
                    default=str,
                )
            )
            return 0
        if sc == "start":
            from protocolcity.service import ensure_service_running

            pref = getattr(args, "root", None)
            preferred = Path(pref).expanduser() if pref else None
            receipt = ensure_service_running(
                preferred_root=preferred,
                quiet=False,
                force=bool(getattr(args, "force", False)),
            )
            if not receipt.get("ok"):
                print("error: %s" % receipt.get("error"), file=sys.stderr)
                return 1
            if receipt.get("skipped"):
                return 0
            state = service_status().get("state") or {}
            port = int(receipt.get("port") or state.get("port") or 8801)
            return 0 if _wait_for_service_cli_ready(port, action="start") else 1
        print(
            "usage: blueprint service {install|uninstall|status|start}",
            file=sys.stderr,
        )
        return 2

    if args.cmd == "uninstall":
        forget = True if getattr(args, "forget", False) else None
        isolated = bool(getattr(args, "isolated", False))
        previous_config = os.environ.get("PROTOCOLCITY_CONFIG_DIR")
        if isolated:
            from protocolcity.service import isolated_config_dir

            os.environ["PROTOCOLCITY_CONFIG_DIR"] = str(isolated_config_dir())
        try:
            return run_uninstall(
                roots=args.roots,
                keep_workspace=args.keep_workspace,
                delete_workspace=args.delete_workspace,
                remove_app=args.app,
                yes=args.yes,
                stop_processes=not args.no_stop,
                forget_registry=forget,
                isolated=isolated,
            )
        finally:
            if isolated:
                if previous_config is None:
                    os.environ.pop("PROTOCOLCITY_CONFIG_DIR", None)
                else:
                    os.environ["PROTOCOLCITY_CONFIG_DIR"] = previous_config

    if args.cmd == "adopt":
        with_demo = bool(getattr(args, "with_demo_worker", False))
        if args.all_unmanaged:
            result = adopt_all_unmanaged(
                Path(args.city),
                force=args.force,
                with_desk=not args.no_desk,
                desk_url=args.desk,
                with_demo_worker=with_demo,
            )
            print(json.dumps(result, indent=2, default=str))
            # pc-513: checklist for each successful adopt (city law hand-edits)
            for row in result.get("adopted") or []:
                if not isinstance(row, dict):
                    continue
                adopt_payload = row.get("adopt") if isinstance(row.get("adopt"), dict) else None
                _checklist_from_adopt_payload(
                    adopt_payload,
                    fallback_name=str(row.get("name") or ""),
                )
            return 0 if result.get("ok") else 1
        if not args.neighborhood:
            print(
                "error: adopt needs a project folder name, or --all-unmanaged",
                file=sys.stderr,
            )
            return 2
        dry_run = bool(getattr(args, "dry_run", False))
        try:
            if dry_run:
                # Dry run previews adopt_neighborhood directly — never routes
                # through doctor.fix()'s city-wide/neighborhood side plants.
                from protocolcity.adopt import adopt_neighborhood

                adopt_payload = adopt_neighborhood(
                    Path(args.city),
                    args.neighborhood,
                    force=args.force,
                    with_desk=not args.no_desk,
                    desk_url=args.desk,
                    with_demo_worker=with_demo,
                    allow_live_desk=bool(getattr(args, "live_desk", False)),
                    plant_seats=True,
                    hire_seats=False,
                    held_providers=getattr(args, "held", None),
                    dry_run=True,
                )
                result = {"ok": adopt_payload.get("ok"), "adopt": adopt_payload}
            else:
                # Adopt = doctor --neighborhood --fix (same plant path)
                result = fix(
                    Path(args.city),
                    neighborhood=args.neighborhood,
                    force=args.force,
                    with_desk=not args.no_desk,
                    desk_url=args.desk,
                    with_demo_worker=with_demo,
                    allow_live_desk=bool(getattr(args, "live_desk", False)),
                    plant_seats=True,
                    hire_seats=bool(getattr(args, "hire", False)),
                    held_providers=getattr(args, "held", None),
                )
                adopt_payload = result.get("adopt") if isinstance(result.get("adopt"), dict) else None
        except Exception as e:
            print("error: adopt failed: %s" % e, file=sys.stderr)
            return 2
        print(json.dumps(adopt_payload or result, indent=2, default=str))
        # pc-513: always remind citizens of manual city-law rows (never auto-fixed)
        if not dry_run:
            _checklist_from_adopt_payload(
                adopt_payload,
                fallback_name=str(args.neighborhood or ""),
            )
        seats = (adopt_payload or {}).get("seats") if isinstance(adopt_payload, dict) else None
        if isinstance(seats, dict) and seats.get("commands"):
            verb = "ran" if getattr(args, "hire", False) and not dry_run else "standard seat set —"
            print("\n%s:" % verb)
            for row in seats["commands"]:
                print("  %s" % row["command"])
        return 0 if result.get("ok") else 1

    if args.cmd == "doctor":
        root = Path(args.city)
        nhood = getattr(args, "neighborhood", None) or getattr(args, "cabinet", None)
        if getattr(args, "check_paths", False):
            # pc-956: host-path hardcode gate
            from protocolcity.host_paths import run_check_paths
            from protocolcity.workspace import resolve_workspace_root

            repo = _REPO_ROOT if (_REPO_ROOT / "suite" / "serve.py").is_file() else None
            if repo is None:
                ws = resolve_workspace_root(start=Path.cwd(), use_registry=True)
                if ws is not None:
                    for cand in (ws / "ProtocolCity", ws):
                        if (cand / "suite" / "serve.py").is_file():
                            repo = cand
                            break
            if repo is None:
                repo = root.expanduser().resolve()
            return run_check_paths(
                repo,
                json_out=bool(getattr(args, "json", False)),
            )
        if getattr(args, "fix_papers", False):
            try:
                result = fix_papers(root, neighborhood=nhood, desk_url=args.desk)
            except Exception as e:
                print("error: doctor --fix-papers failed: %s" % e, file=sys.stderr)
                return 2
            print(json.dumps(result, indent=2, default=str))
            return 0 if result.get("ok") else 1
        try:
            if args.fix:
                result = fix(
                    root,
                    neighborhood=nhood,
                    force=args.force,
                    with_desk=not args.no_desk,
                    desk_url=args.desk,
                    allow_live_desk=bool(getattr(args, "live_desk", False)),
                )
            else:
                result = diagnose(root, neighborhood=nhood)
        except Exception as e:
            print("error: doctor failed: %s" % e, file=sys.stderr)
            return 2
        print_report(result, json_out=args.json)
        summary = (result.get("report") or result).get("summary") or {}
        # exit 1 when missing/conflict remain after diagnose or fix
        bad = int(summary.get("missing") or 0) + int(summary.get("conflict") or 0)
        return 0 if bad == 0 else 1

    if args.cmd == "relocate-root":
        from protocolcity.relocate import relocate_root

        receipt = relocate_root(
            Path(args.from_root),
            Path(args.to_root),
            name=getattr(args, "name", None),
            reload_agents=not bool(getattr(args, "no_reload", False)),
            reinstall_suite_service=not bool(getattr(args, "no_service", False)),
            run_sync=not bool(getattr(args, "no_sync", False)),
            dry_run=bool(getattr(args, "dry_run", False)),
            quiet=bool(getattr(args, "json", False)),
        )
        if getattr(args, "json", False):
            print(json.dumps(receipt, indent=2, default=str))
        if not receipt.get("ok"):
            print("error: %s" % (receipt.get("error") or "relocate failed"), file=sys.stderr)
            return 1
        return 0

    if args.cmd == "update":
        from protocolcity.update import print_update_report

        method = None if args.method == "auto" else args.method
        root = Path(args.root).expanduser() if args.root else None
        return print_update_report(
            agent_prompt=bool(args.agent_prompt),
            method=method,
            restart=bool(args.restart),
            workspace=root,
            dry_run=bool(args.dry_run),
        )

    if args.cmd == "feedback":
        from protocolcity.feedback import print_report as print_feedback

        return print_feedback(
            Path(args.city),
            full_paths=bool(getattr(args, "full_paths", False)),
            symptoms=str(getattr(args, "symptoms", "") or ""),
            write=bool(getattr(args, "write", False)),
            open_browser=bool(getattr(args, "open", False)),
            agent_prompt_only=bool(getattr(args, "agent_prompt", False)),
        )

    if args.cmd == "found":
        dry_run = bool(getattr(args, "dry_run", False))
        try:
            receipt = found(
                Path(args.path),
                city_name=args.name,
                neighborhood=args.neighborhood,
                force=args.force,
                with_desk=not args.no_desk,
                desk_url=args.desk,
                sample_ticket=not args.no_ticket,
                map_port=args.port,
                plant_seats=True,
                hire_seats=bool(getattr(args, "hire", False)) and not dry_run,
                held_providers=getattr(args, "held", None),
                dry_run=dry_run,
            )
        except FileExistsError as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        except FileNotFoundError as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
        seats = receipt.get("seats") if isinstance(receipt, dict) else None
        if dry_run:
            print(json.dumps(receipt, indent=2, default=str))
            if isinstance(seats, dict) and seats.get("commands"):
                print("\nstandard seat set —:")
                for row in seats["commands"]:
                    print("  %s" % row["command"])
            return 0 if receipt.get("ok") else 1
        root = Path(str(receipt["root"]))
        register_city(
            root,
            name=str(receipt.get("city_name") or ""),
        )
        print_receipt(receipt)
        if isinstance(seats, dict) and seats.get("commands"):
            verb = "ran" if getattr(args, "hire", False) else "standard seat set —"
            print("\n%s:" % verb)
            for row in seats["commands"]:
                print("  %s" % row["command"])
        # pc-571 / GH#6: existing top-level folders stay unmanaged unless
        # --adopt-existing, or the user accepts the TTY offer (same as setup).
        if getattr(args, "adopt_existing", False):
            return _print_adopt_all(
                root,
                force=bool(args.force),
                with_desk=not args.no_desk,
                desk_url=args.desk,
            )
        _maybe_unmanaged_prompt(
            root,
            yes=False,
            with_desk=not args.no_desk,
            desk_url=args.desk,
        )
        return 0

    if args.cmd == "detect":
        from protocolcity.found import detect_vendor_clis

        clis = detect_vendor_clis()
        if not clis:
            print(
                "No vendor CLIs found on PATH "
                "(looked for claude, codex, cursor-agent, grok)."
            )
            return 1
        for name, path in clis:
            print("%s\t%s" % (name, path))
        return 0

    if args.cmd == "hire":
        return _cmd_hire(args)
    if args.cmd == "seed-ops":
        from protocolcity.seed_ops import seed_workspace_ops

        root = None
        if getattr(args, "root", None):
            root = Path(args.root).expanduser().resolve()
        else:
            root = _resolve_city_root(None)
        if root is None:
            print(
                "error: no workspace root — pass --root or set SUITE_CITY_ROOT",
                file=sys.stderr,
            )
            return 2
        receipt = seed_workspace_ops(root, quiet=bool(args.quiet))
        print(json.dumps(receipt, indent=2, default=str))
        return 0 if receipt.get("ok") or receipt.get("skipped") else 1

    if args.cmd == "digest":
        from protocolcity.digest import install_digest_job, run_digest

        root = None
        if getattr(args, "root", None):
            root = Path(args.root).expanduser().resolve()
        else:
            root = _resolve_city_root(None)

        if getattr(args, "install", False):
            if root is None:
                print(
                    "error: no workspace root — pass --root or set SUITE_CITY_ROOT",
                    file=sys.stderr,
                )
                return 2
            receipt = install_digest_job(root, quiet=bool(getattr(args, "quiet", False)))
            print(json.dumps(receipt, indent=2, default=str))
            return 0 if receipt.get("ok") or receipt.get("skipped") else 1

        # --run (default action)
        receipt = run_digest(
            root,
            dry_run=bool(getattr(args, "dry_run", False)),
            quiet=bool(getattr(args, "quiet", False)),
        )
        if getattr(args, "quiet", False):
            print(json.dumps(receipt, indent=2, default=str))
        return 0 if receipt.get("ok") else 1

    if args.cmd == "hide":
        return _cmd_hide_unhide(args, hide=True)

    if args.cmd == "unhide":
        return _cmd_hide_unhide(args, hide=False)

    if args.cmd == "demo":
        return _cmd_demo(args)

    if args.cmd == "serve":
        city_root = _resolve_city_root(args.root)
        foreground = bool(getattr(args, "foreground", False))
        # pc-1072: when login service is installed, kickstart it — never leave a
        # shell-owned orphan after stop&&serve (Map dies when the hand exits).
        if not foreground:
            via = _serve_via_login_service(city_root, int(args.port))
            if via is not None:
                return via
        # Explicit --foreground with a live login agent: bootout so KeepAlive
        # does not fight the terminal child for :port.
        if foreground and not _under_launchd():
            try:
                from protocolcity import service as svc_mod

                if svc_mod.is_macos() and svc_mod.login_service_configured():
                    stop_suite_processes(
                        quiet=False,
                        bootout_login_agent=True,
                        ports=[args.port],
                        kill_patterns=False,
                    )
            except Exception:
                pass
        # pc-421: engines on by default when a workspace root is known.
        # --no-engines → suite only. --with-engines kept for scripts (no-op if default).
        no_engines = bool(getattr(args, "no_engines", False))
        if not no_engines and city_root is not None:
            return _run_serve_with_engines(city_root, args.port)
        if getattr(args, "with_engines", False) and city_root is None:
            print(
                "error: engines need a workspace root "
                "(--root PATH, SUITE_CITY_ROOT, or cwd with AGENTS.md)",
                file=sys.stderr,
            )
            return 2

        # Suite only — free suite port only (no login-agent bootout).
        stop_suite_processes(
            quiet=False,
            bootout_login_agent=False,
            ports=[args.port],
            kill_patterns=False,
        )
        suite_script = _resolve_suite_serve_py()
        if suite_script is None:
            print(
                "error: suite/serve.py not found "
                "(install protocolcity or run from the ProtocolCity tree)",
                file=sys.stderr,
            )
            return 2
        env = dict(os.environ)
        env["SUITE_PORT"] = str(args.port)
        if city_root is not None:
            env["SUITE_CITY_ROOT"] = str(city_root)
        pkg_root = str(suite_script.parent.parent)
        prev_pp = env.get("PYTHONPATH") or ""
        if pkg_root not in prev_pp.split(os.pathsep):
            env["PYTHONPATH"] = pkg_root + (os.pathsep + prev_pp if prev_pp else "")
        proc = subprocess.run(
            [sys.executable, str(suite_script)],
            env=env,
            cwd=pkg_root,
        )
        return int(proc.returncode)

    citylens = _load_citylens()
    if args.cmd == "snapshot":
        return citylens.main(
            ["--root", args.root, "snapshot"] if args.root else ["snapshot"]
        )

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
