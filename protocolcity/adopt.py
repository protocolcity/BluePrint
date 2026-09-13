"""Adopt a neighborhood — lay out ProtocolCity structure on an existing folder.

Home-office model: a top-level folder becomes managed when it has law +
optional worker stubs + desk store join. Does not rewrite city-root AGENTS.md.

Uses BluePrint ``project-AGENTS.md`` template (legacy alias
``neighborhood-AGENTS.md`` still accepted) — same plant path as ``found
--project`` (pc-1041). Office Manage and ``protocolcity doctor
--neighborhood X --fix`` share this path (``--cabinet`` remains a
back-compat alias — pc-320).

Export / archive / foreign zones stay Not managed (pc-155 / pc-190) — same
gate as citylens ``manage_cabinet`` so CLI cannot Adopt theater on them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

from protocolcity.desk import (
    DEFAULT_DESK,
    bootstrap_desk,
    desk_reachable,
    fetch_store_prefix,
    queue_pending_join,
    read_desk_join,
    soft_append_desk_identity,
    write_desk_join,
)
from protocolcity.found import (
    _blank_placeholders,
    _strip_html_comments,
    _template,
    looks_like_architecture_scaffold,
    looks_like_programs_scaffold,
    plant_project_features,
    project_agents_body,
    project_architecture_body,
    project_features_path,
    project_programs_body,
)
from protocolcity.paths import resolve_citylens
from protocolcity.slugs import desk_slug, resolve_neighborhood, slugify

# Mirror tools/citylens.py — refuse even if floor UI was bypassed.
_NON_ADOPTABLE_ZONES = frozenset({"export", "archive", "foreign"})

# pc-1186 / successai incident (2026-08-06): force-adopt of a foreign GH/fixture
# clone joined the *production* WorkLane desk (POST /api/admin/products → empty
# successai.db + products.json). Papers recovery may still use --force; live
# desk join for non-adoptable zones requires an explicit second flag.
_LIVE_DESK_RAIL_REASON = (
    "live-desk-rail: zone is export/archive/foreign — force-adopt plants papers "
    "only. Refusing production desk join (pc-1186 · successai incident). "
    "GH/fixture repro: --no-desk + sandboxed WORKLANE_RUNTIME_DIR. "
    "Deliberate live join: allow_live_desk=True / CLI --live-desk (founder-present)."
)


def _prefix_for(name: str) -> str:
    prefix = re.sub(r"[^a-z0-9]", "", name.lower())[:4] or "cab"
    if len(prefix) < 2:
        prefix = (prefix + "xx")[:2]
    return prefix


# Written by found/adopt/doctor --fix (pc-427). AGENTS.md alone is
# "has instructions" — not BluePrint-managed.
MANAGED_MARKER_REL = Path(".protocolcity") / "managed"


def has_instructions(path: Path) -> bool:
    """Folder has AGENTS.md (any source — not necessarily BluePrint)."""
    return (path / "AGENTS.md").is_file()


def is_managed(path: Path) -> bool:
    """BluePrint-managed = durable join marker (pc-427), with place-record fallback.

    Order (pc-1056):
      1. ``.protocolcity/managed`` on disk (source of truth for projects + roots).
      2. Host registry place record ``managed=true`` for registered workspace
         roots (migration path when marker missing but cities.json says managed).
      3. Never AGENTS.md alone — foreign repos with instructions stay unmanaged.

    Foreign repos that ship AGENTS.md without adopt stay unmanaged until
    `protocolcity adopt` (or doctor --fix stamps known joins).
    """
    p = Path(path)
    if (p / MANAGED_MARKER_REL).is_file():
        return True
    try:
        from protocolcity.registry import managed_from_registry

        reg = managed_from_registry(p)
        if reg is True:
            return True
    except Exception:
        pass
    return False


def stamp_managed(path: Path) -> Path:
    """Write BluePrint join marker under path/.protocolcity/managed."""
    path = Path(path)
    dest_dir = path / ".protocolcity"
    dest_dir.mkdir(parents=True, exist_ok=True)
    marker = dest_dir / "managed"
    if not marker.is_file():
        marker.write_text(
            "blueprint-managed\n# written by protocolcity adopt/found/doctor\n",
            encoding="utf-8",
        )
    return marker


# pc-1359 / GH #31: operate-without-adopt for upstream-owned clones.
FOREIGN_CONSUMER_MARKER_REL = Path(".protocolcity") / "foreign-consumer"


def is_foreign_consumer(path: Path) -> bool:
    """Explicit consumer opt-in (automations on, no managed stamp)."""
    return (Path(path) / FOREIGN_CONSUMER_MARKER_REL).is_file()


def stamp_foreign_consumer(path: Path) -> Path:
    """Write consumer marker — does not stamp managed; origin stays upstream."""
    path = Path(path)
    dest_dir = path / ".protocolcity"
    dest_dir.mkdir(parents=True, exist_ok=True)
    marker = dest_dir / "foreign-consumer"
    if not marker.is_file():
        marker.write_text(
            "blueprint-foreign-consumer\n"
            "# operate without adopt — origin stays upstream (pc-1359)\n",
            encoding="utf-8",
        )
    return marker


def _record_desk_join(
    cab: Path,
    *,
    store_slug: str,
    prefix: str,
    display: str,
    desk_result: Optional[Dict],
    desk_url: str,
) -> None:
    """Persist desk-join.json (+ optional AGENTS soft append) after a live join."""
    if not desk_result or not desk_result.get("ok"):
        return
    write_desk_join(
        cab,
        slug=store_slug,
        prefix=prefix,
        display=display,
        desk_url=desk_url,
    )
    # Soft hygiene: pre-authored AGENTS without store/prefix gets a short block.
    soft_append_desk_identity(
        cab / "AGENTS.md",
        slug=store_slug,
        prefix=prefix,
    )


def _cabinet_zone(cab: Path) -> str:
    """Zone for adopt gate via citylens ``zone_of`` (staffing-blind)."""
    citylens = resolve_citylens()
    if not citylens.is_file():
        # Name-only fallback if package is installed without tools/
        name = cab.name
        if re.search(r"(?i)(^|[._-])backups?$|backups?$", name):
            return "archive"
        if re.search(r"(?i)(WorkLane|BluePrint)$", name):
            return "export"
        return "outskirts"
    mod_name = "protocolcity_citylens_adopt_gate"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
    else:
        spec = importlib.util.spec_from_file_location(mod_name, citylens)
        if spec is None or spec.loader is None:
            return "outskirts"
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    # Zone without staffing: export/archive/foreign are name/path rules.
    # citylens API variants: zone_of(path, staffed=False) or zone_of(path, has_store).
    import inspect

    try:
        params = list(inspect.signature(mod.zone_of).parameters)
    except (TypeError, ValueError):
        params = []
    if "staffed" in params:
        return str(mod.zone_of(str(cab), staffed=False))
    if len(params) >= 2:
        return str(mod.zone_of(str(cab), False))
    return str(mod.zone_of(str(cab)))


def _neighborhood_agents_body(
    *,
    title: str,
    store_slug: str,
    prefix: str,
    worker_id: str,
) -> str:
    """Fill BluePrint project AGENTS template for adopt (pc-1041).

    Thin wrapper over :func:`protocolcity.found.project_agents_body` so
    found/adopt stay one plant path. Name kept for call-site stability.
    """
    return project_agents_body(
        title=title,
        store_slug=store_slug,
        prefix=prefix,
        worker_id=worker_id,
        origin="adopt",
    )


def looks_like_blueprint_scaffold(text: str) -> bool:
    """True when AGENTS.md is still BluePrint template / fill-me scaffold (pc-557).

    Custom project law must not be force-rewritten on Join / re-adopt.
    """
    if not text:
        return True
    lower = text.lower()
    markers = (
        "replace fill-mes with real project law",
        "(fill me)",
        "fill me —",
        "adopted by protocolcity blueprint",
        "{{neighborhood_name}}",
        "{{store_slug}}",
    )
    return any(m in lower for m in markers)


def plant_standard_seats(
    root: Path,
    project_slug: str,
    *,
    project_path: Path,
    prefix: str,
    hire: bool = False,
    held: Optional[Iterable[str]] = None,
    workforce_bin: str = "workforce",
    dry_run: bool = False,
) -> Dict[str, object]:
    """The standard-seat-set ``workforce hire`` commands for one project
    (AGENT_ADOPTION.md D12): one bounded implementer per provider the host
    has installed and this project has no seat for yet.

    Reuses ``overview/v1/server/operations.py`` detect_providers /
    hire_command / the seat-resolution helpers from pc-1474 rather than
    duplicating provider detection here. Commands are always computed and
    returned (RUNNING's rule that starting BluePrint must not hire); they
    are only run against ``workforce_bin`` when ``hire=True`` — BluePrint
    never writes the roster itself, ``workforce hire`` is the only writer.

    Refuses an unmanaged folder or a project with no desk-join.json — a
    project only gets a real seat once it is BluePrint-managed and desk
    joined (``dry_run=True`` previews the commands a later real adopt/found
    would plant, so it skips this gate). With ``hire=True`` the loop stops
    at the first non-zero-exit ``workforce hire`` call so a bad host state
    never silently skips the remaining providers.
    """
    import shlex
    import subprocess

    from overview.v1.server.operations import (
        _PROVIDER_ORDER,
        _project_remote,
        _project_seat_providers,
        detect_providers,
        hire_command,
        read_json,
        resolve_roster_path,
    )

    if not dry_run:
        if not is_managed(project_path):
            return {
                "ok": False,
                "project": project_slug,
                "error": "%s is not BluePrint-managed (.protocolcity/managed "
                "missing) — adopt or found the project before planting "
                "seats" % project_path,
                "commands": [],
                "hired": [],
            }
        if read_desk_join(project_path) is None:
            return {
                "ok": False,
                "project": project_slug,
                "error": "%s has no desk-join.json — join the desk (adopt "
                "with desk, or found --project) before planting seats"
                % project_path,
                "commands": [],
                "hired": [],
            }

    held_set = {str(p).strip().title() for p in (held or ())}
    host_providers = detect_providers()
    roster_path = resolve_roster_path(root)
    roster = read_json(roster_path, root) if roster_path else None
    workers = (roster or {}).get("workers") if isinstance(roster, dict) else None
    seats = _project_seat_providers(
        workers if isinstance(workers, dict) else {}, project_slug, root, {}
    )
    remote = _project_remote(root, project_slug)

    commands = []
    hired = []
    ok = True
    for provider in _PROVIDER_ORDER:
        if not host_providers.get(provider) or seats.get(provider):
            continue
        text = hire_command(
            provider,
            project_slug=project_slug,
            project_path=str(project_path),
            prefix=prefix,
            remote=remote,
        )
        if provider in held_set:
            text = text + " --held"
        commands.append({"provider": provider, "command": text})
        if hire and not dry_run:
            argv = [workforce_bin] + shlex.split(text)[1:]
            proc = subprocess.run(argv, capture_output=True, text=True)
            hired.append(
                {
                    "provider": provider,
                    "command": text,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            )
            if proc.returncode != 0:
                ok = False
                break

    return {"ok": ok, "project": project_slug, "commands": commands, "hired": hired}


def adopt_neighborhood(
    city_root: Path,
    name: str,
    *,
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    sample_ticket: bool = False,
    worker_id: str = "demo-worker",
    with_demo_worker: bool = False,
    allow_live_desk: bool = False,
    plant_seats: bool = False,
    hire_seats: bool = False,
    held_providers: Optional[Iterable[str]] = None,
    workforce_bin: str = "workforce",
    dry_run: bool = False,
) -> Dict[str, object]:
    """Lay out structure inside city_root/name so the office can manage it.

    Creates (if missing, or force):
      AGENTS.md (from project-AGENTS template; neighborhood-AGENTS legacy alias),
      ARCHITECTURE.md (from project-ARCHITECTURE template — pc-1087),
      PROGRAMS.md (from PROGRAMS template — pc-1264),
      FEATURES.md (from FEATURES template — pc-1317; docs/ preferred),
      .protocolcity/managed join marker
    Optionally (``with_demo_worker`` / ``--with-demo-worker`` — pc-489):
      workers/<worker_id>/{CONTRACT,prompt}.md stubs
    Default is **no** worker stubs — real product neighborhoods often join
    the desk for tickets only; hire papers come from ``hire`` or found's
    first-run path. Vendor pointers (CLAUDE.md / GROK.md) are never planted.

    **Live-desk rail (pc-1186):** when zone is export/archive/foreign, desk join
    is skipped unless ``allow_live_desk=True`` — ``--force`` alone never writes
    a product store onto the production WorkLane.
    Optionally joins WorkLane store for the folder slug.

    **Dry run:** ``dry_run=True`` writes nothing — no companions, no managed
    marker, no desk join, no roster/hire — and returns a preview (what would
    be created, the standard-seat-set commands) instead.
    """
    root = city_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError("city root not a directory: %s" % root)

    # pc-966: ensure workspace .mcp.json exists when adopting into a city
    # (found plants it; adopt heals missing so hand-copied cities catch up).
    # Dry run writes nothing, including this workspace-level heal.
    if not dry_run:
        try:
            from protocolcity.vendor_config import plant_workspace_mcp

            plant_workspace_mcp(root, force=False)
        except Exception:
            pass

    raw = (name or "").strip().strip("/").replace("\\", "/")
    if not raw or "/" in raw or raw in (".", "..") or raw.startswith("."):
        raise ValueError("neighborhood name must be a single top-level folder name")

    # pc-1056: root is a place (level 0) — resolve as place, refuse adopt-as-project.
    from protocolcity.slugs import is_root_place_name

    if is_root_place_name(raw):
        raise ValueError(
            "%s is the workspace root place (level 0, slug __root__) — "
            "not adoptable as a project. Use `blueprint found` / "
            "`blueprint doctor --fix` for the root; adopt only top-level "
            "project folders." % raw
        )

    # pc-570: resolve by exact path, then slugify match (trailing-space disk
    # names, "Work Folder" CLI arg vs work-folder store, SE Local HC, …).
    cab = resolve_neighborhood(root, raw)
    if cab is None:
        raise FileNotFoundError(
            "no such neighborhood folder: %s (looked for exact name and "
            "slugify-match under %s)" % (raw, root)
        )
    try:
        cab.relative_to(root)
    except ValueError as e:
        raise ValueError("neighborhood escapes city root") from e
    # Prefer the on-disk basename for paths; strip for display (pc-570
    # trailing-space disk names stay on disk, never in titles).
    raw = cab.name
    title_src = raw.strip() or raw

    # Refuse adopting the city root path itself if ever resolved as a child.
    try:
        if cab.resolve() == root.resolve():
            raise ValueError(
                "workspace root is a place (level 0) — not adoptable as a project"
            )
    except ValueError:
        raise
    except OSError:
        pass

    # Honesty gate (pc-155 / pc-190): export/archive/foreign stay Not managed.
    # Matches citylens manage_cabinet — force still overrides for recovery.
    # pc-1161: once force-adopted (managed marker on disk), re-entry via
    # doctor --neighborhood --fix must take the soft already-managed path
    # below — do not re-block on zone without --force.
    zone = _cabinet_zone(cab)
    if zone in _NON_ADOPTABLE_ZONES and not force and not is_managed(cab):
        raise ValueError(
            "%s is zone=%s — not adoptable as a neighborhood "
            "(export/archive/foreign stay Not managed; Adopt blocked)"
            % (raw, zone)
        )

    # pc-1186: force may plant papers on foreign; live desk join is a second gate.
    desk_join = bool(with_desk)
    desk_rail_block: Optional[Dict] = None
    if desk_join and zone in _NON_ADOPTABLE_ZONES and not allow_live_desk:
        desk_join = False
        desk_rail_block = {
            "ok": False,
            "blocked": "live-desk-rail",
            "zone": zone,
            "reason": _LIVE_DESK_RAIL_REASON,
        }

    title = title_src.replace("-", " ").replace("_", " ").title()
    store_slug = desk_slug(raw)
    prefix = _prefix_for(title_src)
    # pc-731: when the store already exists, use the desk's registered prefix so
    # re-adopt never invents a second prefix that diverges from products.json.
    if desk_join:
        live_pref = fetch_store_prefix(store_slug, desk_url)
        if live_pref:
            prefix = live_pref

    if dry_run:
        already_managed = is_managed(cab)
        would_create = _preview_companions(
            cab,
            write_agents=not already_managed or force,
            force=force,
            with_demo_worker=with_demo_worker,
        )
        seats_preview: Optional[Dict] = None
        if plant_seats:
            seats_preview = plant_standard_seats(
                root,
                store_slug,
                project_path=cab,
                prefix=prefix,
                hire=False,
                held=held_providers,
                workforce_bin=workforce_bin,
                dry_run=True,
            )
        return {
            "ok": True,
            "dry_run": True,
            "already_managed": already_managed,
            "name": raw,
            "path": str(cab),
            "store_slug": store_slug,
            "prefix": prefix,
            "would_create": would_create,
            "desk": None,
            "seats": seats_preview,
            "doctor": "dry-run",
        }

    seats_result: Optional[Dict] = None

    if is_managed(cab) and not force:
        # Soft fill missing law / optional worker stubs (never clobber)
        created_soft = _ensure_companions(
            cab,
            title=title,
            store_slug=store_slug,
            prefix=prefix,
            worker_id=worker_id,
            force=False,
            with_demo_worker=with_demo_worker,
        )
        desk_result: Optional[Dict] = desk_rail_block
        if desk_join:
            if desk_reachable(desk_url):
                desk_result = bootstrap_desk(
                    store_slug,
                    display=title,
                    prefix=prefix,
                    desk_url=desk_url,
                    sample_ticket=sample_ticket,
                )
            else:
                # pc-314: queue the join instead of dropping it silently.
                queue_pending_join(
                    root,
                    store_slug,
                    display=title,
                    prefix=prefix,
                    sample_ticket=sample_ticket,
                )
                desk_result = {"ok": False, "reason": "desk offline", "pending": True}
            _record_desk_join(
                cab,
                store_slug=store_slug,
                prefix=prefix,
                display=title,
                desk_result=desk_result,
                desk_url=desk_url,
            )
        if plant_seats:
            seats_result = plant_standard_seats(
                root,
                store_slug,
                project_path=cab,
                prefix=prefix,
                hire=hire_seats,
                held=held_providers,
                workforce_bin=workforce_bin,
            )
        return {
            "ok": True,
            "already_managed": True,
            "name": raw,
            "path": str(cab),
            "store_slug": store_slug,
            "prefix": prefix,
            "created": created_soft,
            "desk": desk_result,
            "seats": seats_result,
            "doctor": "companions-only" if created_soft else "noop",
        }

    created = _ensure_companions(
        cab,
        title=title,
        store_slug=store_slug,
        prefix=prefix,
        worker_id=worker_id,
        force=force,
        write_agents=True,
        with_demo_worker=with_demo_worker,
    )

    desk_result = desk_rail_block
    if desk_join:
        if desk_reachable(desk_url):
            desk_result = bootstrap_desk(
                store_slug,
                display=title,
                prefix=prefix,
                desk_url=desk_url,
                sample_ticket=sample_ticket,
            )
        else:
            # pc-314: queue the join instead of dropping it silently.
            queue_pending_join(
                root,
                store_slug,
                display=title,
                prefix=prefix,
                sample_ticket=sample_ticket,
            )
            desk_result = {"ok": False, "reason": "desk offline", "pending": True}
        _record_desk_join(
            cab,
            store_slug=store_slug,
            prefix=prefix,
            display=title,
            desk_result=desk_result,
            desk_url=desk_url,
        )

    if plant_seats:
        seats_result = plant_standard_seats(
            root,
            store_slug,
            project_path=cab,
            prefix=prefix,
            hire=hire_seats,
            held=held_providers,
            workforce_bin=workforce_bin,
        )

    return {
        "ok": True,
        "already_managed": False,
        "name": raw,
        "path": str(cab),
        "store_slug": store_slug,
        "prefix": prefix,
        "created": created,
        "desk": desk_result,
        "seats": seats_result,
        "doctor": "adopted",
    }


def _preview_companions(
    cab: Path,
    *,
    write_agents: bool,
    force: bool,
    with_demo_worker: bool = False,
) -> list:
    """Dry-run twin of :func:`_ensure_companions` — reads, never writes.

    Same "would this file plant" rules (missing, or force + still a
    BluePrint fill-me scaffold) without touching disk.
    """
    would: list = []

    agents = cab / "AGENTS.md"
    if write_agents:
        if not agents.exists():
            would.append("AGENTS.md")
        elif force:
            try:
                existing = agents.read_text(encoding="utf-8")
            except OSError:
                existing = ""
            if looks_like_blueprint_scaffold(existing):
                would.append("AGENTS.md")

    arch = cab / "ARCHITECTURE.md"
    if not arch.exists():
        would.append("ARCHITECTURE.md")
    elif force:
        try:
            existing_arch = arch.read_text(encoding="utf-8")
        except OSError:
            existing_arch = ""
        if looks_like_architecture_scaffold(existing_arch):
            would.append("ARCHITECTURE.md")

    progs = cab / "PROGRAMS.md"
    if not progs.exists():
        would.append("PROGRAMS.md")
    elif force:
        try:
            existing_progs = progs.read_text(encoding="utf-8")
        except OSError:
            existing_progs = ""
        if looks_like_programs_scaffold(existing_progs):
            would.append("PROGRAMS.md")

    feats = project_features_path(cab)
    if not feats.exists() or force:
        would.append(str(feats.relative_to(cab)))

    if not (cab / MANAGED_MARKER_REL).is_file():
        would.append(str(MANAGED_MARKER_REL))

    if with_demo_worker:
        workers_dir = cab / "workers" / "demo-worker"
        if not workers_dir.exists() or force:
            would.append("workers/demo-worker/CONTRACT.md")
            would.append("workers/demo-worker/prompt.md")

    return would


def _ensure_companions(
    cab: Path,
    *,
    title: str,
    store_slug: str,
    prefix: str,
    worker_id: str,
    force: bool,
    write_agents: bool = False,
    with_demo_worker: bool = False,
) -> list:
    """Create missing law / optional worker stubs. Never clobber unless force.

    Worker stubs plant only when ``with_demo_worker`` is True (pc-489).
    Existing workers/ dirs are never deleted by adopt or doctor --fix.
    Vendor pointers are optional — users add them when a CLI needs its own
    filename; adopt never plants CLAUDE.md / GROK.md.
    """
    created: list = []
    agents = cab / "AGENTS.md"
    # pc-557: never clobber non-scaffold project law — even with force.
    # force only rewrites BluePrint fill-me scaffolds / missing files.
    plant_agents = False
    if write_agents:
        if not agents.exists():
            plant_agents = True
        elif force:
            try:
                existing = agents.read_text(encoding="utf-8")
            except OSError:
                existing = ""
            plant_agents = looks_like_blueprint_scaffold(existing)
    if plant_agents:
        agents.write_text(
            _neighborhood_agents_body(
                title=title,
                store_slug=store_slug,
                prefix=prefix,
                worker_id=worker_id,
            ),
            encoding="utf-8",
        )
        created.append("AGENTS.md")

    # pc-1087: ARCHITECTURE.md beside AGENTS — plant when missing; force only
    # rewrites BluePrint fill-me scaffolds (never clobber authored architecture).
    arch = cab / "ARCHITECTURE.md"
    plant_arch = False
    if not arch.exists():
        plant_arch = True
    elif force:
        try:
            existing_arch = arch.read_text(encoding="utf-8")
        except OSError:
            existing_arch = ""
        plant_arch = looks_like_architecture_scaffold(existing_arch)
    if plant_arch:
        arch.write_text(
            project_architecture_body(title=title, origin="adopt"),
            encoding="utf-8",
        )
        created.append("ARCHITECTURE.md")

    # pc-1264: PROGRAMS.md beside AGENTS — plant when missing; force only
    # rewrites BluePrint fill-me scaffolds (never clobber authored programs).
    progs = cab / "PROGRAMS.md"
    plant_progs = False
    if not progs.exists():
        plant_progs = True
    elif force:
        try:
            existing_progs = progs.read_text(encoding="utf-8")
        except OSError:
            existing_progs = ""
        plant_progs = looks_like_programs_scaffold(existing_progs)
    if plant_progs:
        progs.write_text(
            project_programs_body(title=title, origin="adopt"),
            encoding="utf-8",
        )
        created.append("PROGRAMS.md")

    # pc-1317: FEATURES.md — docs/ preferred, root fallback when no docs/;
    # force only rewrites BluePrint fill-me scaffolds (never clobber authored).
    planted_feats = plant_project_features(
        cab, title=title, origin="adopt", force=force
    )
    if planted_feats is not None:
        created.append(str(project_features_path(cab).relative_to(cab)))

    # pc-427: join marker even when AGENTS already existed (adopt without rewrite)
    stamp_managed(cab)
    if "AGENTS.md" in created or write_agents:
        created.append(".protocolcity/managed")

    if not with_demo_worker:
        return created

    workers_dir = cab / "workers" / worker_id
    need_workers = not workers_dir.exists() or force
    if need_workers:
        workers_dir.mkdir(parents=True, exist_ok=True)
        for src_name, dest_name in (
            ("worker-CONTRACT.md", "CONTRACT.md"),
            ("worker-prompt.md", "prompt.md"),
        ):
            dest = workers_dir / dest_name
            if dest.exists() and not force:
                continue
            body = _template(src_name).read_text(encoding="utf-8")
            text = _strip_html_comments(_blank_placeholders(body))
            text = text.replace("{{WORKER_ID}}", worker_id)
            text = text.replace("{{NEIGHBORHOOD_NAME}}", title)
            dest.write_text(text, encoding="utf-8")
            created.append("workers/%s/%s" % (worker_id, dest_name))
    else:
        # Ensure papers exist even if dir was empty-ish
        for dest_name, src_name in (
            ("CONTRACT.md", "worker-CONTRACT.md"),
            ("prompt.md", "worker-prompt.md"),
        ):
            dest = workers_dir / dest_name
            if dest.exists():
                continue
            body = _template(src_name).read_text(encoding="utf-8")
            text = _strip_html_comments(_blank_placeholders(body))
            text = text.replace("{{WORKER_ID}}", worker_id)
            text = text.replace("{{NEIGHBORHOOD_NAME}}", title)
            dest.write_text(text, encoding="utf-8")
            created.append("workers/%s/%s" % (worker_id, dest_name))

    return created


# pc-320: primary name is adopt_neighborhood; cabinet kept as alias.
adopt_cabinet = adopt_neighborhood
