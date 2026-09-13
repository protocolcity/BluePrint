"""Found a workspace — scaffold law from BluePrint templates.

M1 first-run (pc-20 / pc-134): point at a blank folder *you* name, get a
workspace root that citylens can walk, and print the demo path. Does not
force a project folder name (no default ``project`` / ``app`` / ``my-city``).
Optional ``--project`` creates one named folder; otherwise drop existing
folders under the root and ``blueprint adopt`` them (or pass
``--adopt-existing`` / ``--all-unmanaged`` at found time — pc-571). Does not
start daemons by default.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from protocolcity.desk import (
    DEFAULT_DESK,
    bootstrap_desk,
    desk_reachable,
    queue_pending_join,
    soft_append_desk_identity,
    write_desk_join,
)
from protocolcity.slugs import slugify

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent


def _templates_dir() -> Path:
    """Templates ship inside the package for pip/brew; monorepo keeps root copy."""
    packaged = _PKG_DIR / "templates"
    if packaged.is_dir() and (packaged / "city-AGENTS.md").is_file():
        return packaged
    monorepo = _REPO_ROOT / "templates"
    if monorepo.is_dir() and (monorepo / "city-AGENTS.md").is_file():
        return monorepo
    return packaged


_TEMPLATES = _templates_dir()


def _template(name: str) -> Path:
    p = _templates_dir() / name
    if not p.is_file():
        raise FileNotFoundError(
            "BluePrint template missing: %s (expected under %s)" % (name, _templates_dir())
        )
    return p


def _strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->\n?", "", text, flags=re.S).strip() + "\n"


def _blank_placeholders(text: str) -> str:
    return re.sub(r"\{\{[^}]+\}\}", "(fill me)", text)


def project_agents_body(
    *,
    title: str,
    store_slug: str,
    prefix: str,
    worker_id: str = "demo-worker",
    origin: str = "adopt",
) -> str:
    """Fill project L1 AGENTS from the shared BluePrint template (pc-1041).

    ``found --project`` and ``adopt`` both plant through this path so entry
    door does not change the L1 law shape. Prefers ``project-AGENTS.md``
    (templates/README.md); falls back to legacy ``neighborhood-AGENTS.md``.
    """
    try:
        raw = _template("project-AGENTS.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        raw = _template("neighborhood-AGENTS.md").read_text(encoding="utf-8")
    text = (
        raw.replace("{{PROJECT_NAME}}", title)
        .replace("{{NEIGHBORHOOD_NAME}}", title)
        .replace("{{STORE_SLUG}}", store_slug)
        .replace("{{PREFIX}}", prefix)
        .replace("{{WORKER_ID}}", worker_id)
    )
    text = _blank_placeholders(text)
    text = _strip_html_comments(text)
    if (origin or "").strip().lower() == "found":
        lead = (
            "%s — founded by `blueprint found`. Replace fill-mes with real "
            "project law." % title
        )
    else:
        lead = (
            "%s — adopted by ProtocolCity BluePrint. Replace fill-mes with "
            "real project law." % title
        )
    # Lead the "what this place is" section with a concrete plant line.
    text = text.replace("(fill me)", lead, 1)
    return text


def project_architecture_body(
    *,
    title: str,
    origin: str = "adopt",
) -> str:
    """Fill project L1 ARCHITECTURE.md from the shared template (pc-1087).

    Planted next to AGENTS.md by ``found --project`` and ``adopt``. Scaffold
    remains fill-me until the project authors real layers / SoTs / invariants.
    """
    raw = _template("project-ARCHITECTURE.md").read_text(encoding="utf-8")
    text = raw.replace("{{PROJECT_NAME}}", title).replace(
        "{{NEIGHBORHOOD_NAME}}", title
    )
    text = _blank_placeholders(text)
    text = _strip_html_comments(text)
    if (origin or "").strip().lower() == "found":
        lead = (
            "%s — founded by `blueprint found`. Replace fill-mes with real "
            "architecture law (layers, sources of truth, data flow, invariants)."
            % title
        )
    else:
        lead = (
            "%s — adopted by ProtocolCity BluePrint. Replace fill-mes with "
            "real architecture law (layers, sources of truth, data flow, "
            "invariants)." % title
        )
    text = text.replace("(fill me)", lead, 1)
    return text


def project_programs_body(
    *,
    title: str,
    origin: str = "adopt",
) -> str:
    """Fill project PROGRAMS.md from the shared template (pc-1264).

    Planted next to AGENTS.md by ``found --project`` and ``adopt``. Stub stays
    3–5 named lines — not an atlas, not a dogfood roster.
    """
    raw = _template("PROGRAMS.md").read_text(encoding="utf-8")
    text = raw.replace("{{PROJECT_NAME}}", title)
    text = _blank_placeholders(text)
    text = _strip_html_comments(text)
    if (origin or "").strip().lower() == "found":
        lead = (
            "%s — founded by `blueprint found`. Replace fill-mes with 3–5 "
            "named lines of work. Twigs stay off the Wall." % title
        )
    else:
        lead = (
            "%s — adopted by ProtocolCity BluePrint. Replace fill-mes with "
            "3–5 named lines of work. Twigs stay off the Wall." % title
        )
    text = text.replace("(fill me)", lead, 1)
    return text


def looks_like_programs_scaffold(text: str) -> bool:
    """True when PROGRAMS.md is still BluePrint template / fill-me (pc-1264)."""
    if not text:
        return True
    lower = text.lower()
    markers = (
        "(fill me)",
        "fill me —",
        "replace fill-mes with 3–5",
        "{{project_name}}",
        "{{prog_1}}",
        "{{name_1}}",
    )
    return any(m in lower for m in markers)


def project_features_path(cab: Path) -> Path:
    """docs/FEATURES.md when that file or a docs/ dir exists; else project root.

    Prefer an existing file (docs/ wins if both). When missing, plant under
    ``docs/`` if that directory is already present, otherwise next to
    AGENTS.md (pc-1317).
    """
    docs_dir = cab / "docs"
    docs_feat = docs_dir / "FEATURES.md"
    root_feat = cab / "FEATURES.md"
    if docs_feat.is_file():
        return docs_feat
    if root_feat.is_file():
        return root_feat
    if docs_dir.is_dir():
        return docs_feat
    return root_feat


def project_features_body(
    *,
    title: str,
    origin: str = "adopt",
) -> str:
    """Fill project FEATURES.md from the shared template (pc-1317).

    Planted at ``docs/FEATURES.md`` when ``docs/`` exists, else next to
    AGENTS.md by ``found --project`` and ``adopt``.
    """
    raw = _template("FEATURES.md").read_text(encoding="utf-8")
    text = raw.replace("{{PROJECT_NAME}}", title)
    text = _blank_placeholders(text)
    text = _strip_html_comments(text)
    if (origin or "").strip().lower() == "found":
        lead = (
            "%s — founded by `blueprint found`. Replace fill-mes with "
            "founder-named surfaces (where they live, how a hand verifies them)."
            % title
        )
    else:
        lead = (
            "%s — adopted by ProtocolCity BluePrint. Replace fill-mes with "
            "founder-named surfaces (where they live, how a hand verifies them)."
            % title
        )
    text = text.replace("(fill me)", lead, 1)
    return text


def looks_like_features_scaffold(text: str) -> bool:
    """True when FEATURES.md is still BluePrint template / fill-me (pc-1317)."""
    if not text:
        return True
    lower = text.lower()
    markers = (
        "(fill me)",
        "fill me —",
        "replace fill-mes with founder-named",
        "{{project_name}}",
        "{{feature_1}}",
        "{{where_1}}",
        "{{verify_1}}",
    )
    return any(m in lower for m in markers)


def plant_project_features(
    cab: Path,
    *,
    title: str,
    origin: str = "adopt",
    force: bool = False,
) -> Optional[Path]:
    """Plant FEATURES.md if missing, or force-rewrite a fill-me stub.

    Never clobbers an authored table. Returns the path written, else None.
    """
    path = project_features_path(cab)
    write = False
    if not path.is_file():
        write = True
    elif force:
        try:
            write = looks_like_features_scaffold(path.read_text(encoding="utf-8"))
        except OSError:
            write = True
    if not write:
        return None
    path.write_text(
        project_features_body(title=title, origin=origin),
        encoding="utf-8",
    )
    return path


def looks_like_architecture_scaffold(text: str) -> bool:
    """True when ARCHITECTURE.md is still BluePrint template / fill-me (pc-1087).

    Mirrors :func:`protocolcity.adopt.looks_like_blueprint_scaffold` for the
    architecture paper so doctor can flag unfilled product law.
    """
    if not text:
        return True
    lower = text.lower()
    markers = (
        "(fill me)",
        "fill me —",
        "replace fill-mes with real architecture",
        "{{project_name}}",
        "{{layer_1}}",
        "{{domain_1}}",
        "{{invariant_1}}",
        "{{data_flow:",
    )
    return any(m in lower for m in markers)


def _surface_vocab(city_body: str) -> str:
    """Prefer project/workspace wording in planted L0 law."""
    return (
        city_body.replace("Neighborhood registry", "Project registry")
        .replace("Cross-neighborhood rules", "Cross-project rules")
        .replace("neighborhood's", "project's")
        .replace("neighborhood", "project")
        .replace("Neighborhood", "Project")
        .replace("cross-neighborhood", "cross-project")
        .replace("City Law", "Workspace instructions")
        .replace("the city", "the workspace")
        .replace("this city", "this workspace")
    )


def _honest_city_agents(name: str, hood: Optional[str], prefix: Optional[str]) -> str:
    """Fill city-AGENTS template — optional first project, never a forced name.

    Ship-honest (pc-20): leftover ``(fill me)`` registry / boundary lines make a
    founded workspace look half-drafted. With no first project, leave an empty
    registry and point at adopt; with one, keep a single live row.
    """
    city_tpl = _template("city-AGENTS.md").read_text(encoding="utf-8")
    if hood and prefix:
        city_body = (
            city_tpl.replace("{{CITY_NAME}}", name)
            .replace("{{FOLDER_1}}", hood)
            .replace("{{PREFIX_1}}", prefix)
            .replace("{{WHAT_IT_IS}}", "first project", 1)
            .replace("{{live / drafting / dormant}}", "drafting", 1)
        )
    else:
        # No forced folder — strip first-project row with the rest of fill-mes.
        city_body = city_tpl.replace("{{CITY_NAME}}", name)
    city_body = _blank_placeholders(city_body)
    city_body = _strip_html_comments(city_body)
    # Drop any markdown table body row that still has a fill-me cell.
    city_body = re.sub(
        r"^\|[^|\n]*\(fill me\)[^|\n]*\|.*\n",
        "",
        city_body,
        flags=re.M,
    )
    # Boundary bullet in the template is a multi-placeholder stub — replace
    # with the honest found default (matches empty PERIMETER grants).
    city_body = re.sub(
        r"^- \(fill me\) talks to \(fill me\) via \(fill me\) only\.\s*$",
        "- Every project is sovereign at home — no cross-grants yet "
        "(add rows to `BOUNDARIES.md` when two projects share a boundary).\n",
        city_body,
        flags=re.M,
    )
    # Any remaining fill-me list lines (shouldn't, after boundary rewrite).
    city_body = re.sub(r"^- .*?\(fill me\).*$\n?", "", city_body, flags=re.M)
    city_body = _surface_vocab(city_body)
    if not hood:
        # Empty registry: help the user see how to grow (name is theirs).
        if "## Project registry" in city_body:
            city_body = city_body.replace(
                "## Project registry\n",
                "## Project registry\n\n"
                "_None yet._ Name folders whatever you want — drop existing "
                "repos under this workspace, then "
                "`blueprint adopt <workspace> <folder>` (or "
                "`blueprint found … --project <name>` next time).\n\n",
                1,
            )
    return city_body


def detect_vendor_clis() -> List[Tuple[str, str]]:
    names = ("claude", "codex", "cursor-agent", "grok")
    found: List[Tuple[str, str]] = []
    for name in names:
        path = shutil.which(name)
        if path:
            found.append((name, path))
    return found


def _prefix_for(name: str) -> str:
    prefix = re.sub(r"[^a-z0-9]", "", name.lower())[:4] or "proj"
    if len(prefix) < 2:
        prefix = (prefix + "xx")[:2]
    return prefix


def _write_first_run(
    root: Path,
    *,
    city_name: str,
    hood: Optional[str],
    store_slug: Optional[str],
    prefix: Optional[str],
    clis: List[Tuple[str, str]],
    desk: Optional[Dict],
    map_port: int,
) -> Path:
    """Citizen-facing first-run card at the workspace root."""
    path = root / "FIRST_RUN.md"
    cli_lines = (
        "\n".join("- `%s` — %s" % (n, p) for n, p in clis)
        if clis
        else "- (none detected — install claude / codex / cursor-agent / grok to staff)"
    )

    # What was written table — project rows only if we created one.
    if hood:
        papers_table = (
            "| Path | Role |\n"
            "|---|---|\n"
            "| `AGENTS.md` | Workspace instructions — project registry |\n"
            "| `BOUNDARIES.md` | Cross-project grants (empty at found — add only when needed) |\n"
            "| `.claude/skills/README.md` | L0 skills shelf — local agent coordination (not cloud) |\n"
            "| `.agents/skills/workspace-efficiency/` | L0 drain-hygiene skill (ready seats / You-starve) |\n"
            "| `scripts/skills_sync.sh` | Bridge L0 skills into project folders for Claude/Cursor |\n"
            "| `scripts/open_work_audit.py` | Open/ready/feeds audit CLI |\n"
            "| `%s/AGENTS.md` | First **project** instructions (name you chose) |\n"
            "| `%s/ARCHITECTURE.md` | Project architecture law (layers / SoT / invariants) |\n"
            "| `%s/PROGRAMS.md` | Named lines of work (3–5) — Wall programs paper |\n"
            "| `%s/FEATURES.md` | Named surfaces (or `docs/FEATURES.md` when `docs/` exists) |\n"
            "| `%s/workers/demo-worker/` | Agent paper stubs (not armed — not live on Agents yet) |\n"
            "| `FIRST_RUN.md` | This card |\n"
        ) % (hood, hood, hood, hood, hood)
    else:
        papers_table = (
            "| Path | Role |\n"
            "|---|---|\n"
            "| `AGENTS.md` | Workspace instructions — project registry (empty until you add folders) |\n"
            "| `BOUNDARIES.md` | Cross-project grants (empty at found — add only when needed) |\n"
            "| `.claude/skills/README.md` | L0 skills shelf — local agent coordination (not cloud) |\n"
            "| `.agents/skills/workspace-efficiency/` | L0 drain-hygiene skill (ready seats / You-starve) |\n"
            "| `scripts/skills_sync.sh` | Bridge L0 skills into project folders for Claude/Cursor |\n"
            "| `scripts/open_work_audit.py` | Open/ready/feeds audit CLI |\n"
            "| `FIRST_RUN.md` | This card |\n"
        )

    desk_block = (
        "Desk was offline during founding — scaffold only. "
        + (
            "The store join is queued (`.protocolcity/pending-desk.json`) and "
            "runs automatically on the next `blueprint serve --with-engines`.\n"
            if hood
            else "Join a store when you adopt or create a project.\n"
        )
    )
    if desk and desk.get("reachable") and hood and store_slug:
        store = desk.get("store") or {}
        ticket = desk.get("ticket") or {}
        tid = None
        if isinstance(ticket, dict) and ticket.get("task"):
            tid = ticket["task"].get("id")
        elif isinstance(ticket, dict) and ticket.get("ok"):
            t = ticket.get("task") or ticket
            tid = t.get("id") if isinstance(t, dict) else None
        desk_block = (
            "- Desk: `http://127.0.0.1:%d/desk`\n"
            "- Store slug: `%s` (%s)\n"
            "- Sample ticket: %s\n"
            % (
                map_port,
                store_slug,
                "created" if (store or {}).get("created") else "already present",
                tid or "(none — check desk errors on the found receipt)",
            )
        )
    elif desk and desk.get("reachable") and not hood:
        desk_block = (
            "Desk is up at `http://127.0.0.1:%d/desk`. No project store yet — "
            "create or adopt a folder first, then the Desk join runs for that slug.\n"
            % map_port
        )

    if hood and store_slug:
        open_hint = (
            "You should see **Explorer** with **%s** as a **project** (folder name "
            "you chose — rename or add projects as you grow). If a sample ticket "
            "was filed, that folder shows an open count.\n\n"
            "Click a project node on the Map to scope its tickets and hands. "
            "The Map is the only door.\n"
        ) % (hood,)
        next_block = (
            "- Edit `%s/AGENTS.md` — what this project is, run/test commands, no-go zones.\n"
            "- Edit `%s/ARCHITECTURE.md` — layers, single sources of truth, data flow, invariants.\n"
            "- Edit `%s/PROGRAMS.md` — 3–5 named lines of work (twigs stay off the Wall).\n"
            "- Edit `%s/FEATURES.md` (or `docs/FEATURES.md`) — founder-named surfaces and how to verify them.\n"
            "- Drop more folders under this workspace, then Map right-click → **Adopt**, "
            "or ask your agent: `blueprint adopt %s <folder>`.\n"
            "- Friendly first-run: `blueprint setup` · leave: `blueprint uninstall` "
            "(never deletes folders).\n"
            "- **Workspace jobs** (seeded by setup/serve / `blueprint seed-ops`): "
            "**chief of staff** (Mode B capacity — stages pin diffs for you to "
            "approve, never silent), **health-patrol**, **workspace-efficiency**.\n"
            "  Papers: `%s/.protocolcity/ops/workers/chief-of-staff/` · re-seed: "
            "`blueprint seed-ops --root %s`\n"
            "- Gates that need a human (publish, credentials, destructive ops) stay with You.\n"
        ) % (hood, hood, hood, hood, root, root, root)
    else:
        open_hint = (
            "You should see the Map with an empty project list — that is correct. "
            "No default project was planted. Add work your way:\n\n"
            "1. **Create or drop a folder** inside this workspace (any name).\n"
            "2. **On the Map:** right-click that folder → **Adopt**.\n"
            "3. **Or ask your AI agent** (agents know the CLI):\n"
            "   ```bash\n"
            "   blueprint adopt %s <folder-name>\n"
            "   ```\n"
            "4. **Friendly entry** — `blueprint setup` · leave: `blueprint uninstall` "
            "(uninstall never deletes your folders).\n"
        ) % (root,)
        next_block = (
            "- Soft default workspace path is `~/BluePrint` — rename freely.\n"
            "- Projects keep *their* names — BluePrint does not rename your folders.\n"
            "- Edit root `AGENTS.md` as you register projects.\n"
            "- **Workspace jobs** (seeded by setup/serve / `blueprint seed-ops`): "
            "**chief of staff** (Mode B capacity — stages pin diffs for you to "
            "approve, never silent), **health-patrol**, **workspace-efficiency**.\n"
            "  Papers: `%s/.protocolcity/ops/workers/chief-of-staff/` · re-seed: "
            "`blueprint seed-ops --root %s`\n"
            "- Gates that need a human (publish, credentials, destructive ops) stay with You.\n"
        ) % (root, root)

    # pc-810 / pc-876: Grok (and similar) only walk CWD→git root; L0 needs bridge.
    skills_bridge = (
        "## Agent skills — L0 follows into project sessions\n\n"
        "Workspace coordination skills live under "
        "`.agents/skills/` and `.claude/skills/` (local disk, not cloud).\n\n"
        "Planted L0 skill: **workspace-efficiency** (drain hygiene — ready seats, "
        "You-starve, assign ≠ escalate). Cadence job is hired by "
        "`blueprint seed-ops` / first serve (09:30 + 16:30 local).\n\n"
        "Many CLIs only scan **the project repo you opened**, so they miss "
        "parent workspace L0 skills.\n\n"
        "**Grok:** paste once into `~/.grok/config.toml`:\n\n"
        "```toml\n"
        "[skills]\n"
        'paths = ["%s/.agents/skills"]\n'
        "```\n\n"
        "**Claude / Cursor:** after you adopt projects, bridge L0 into each "
        "project folder:\n\n"
        "```bash\n"
        "bash %s/scripts/skills_sync.sh\n"
        "```\n\n"
        "Source of truth stays in this workspace — do not copy skills into "
        "`~/.grok/skills`. Details: `.claude/skills/README.md` · product "
        "`INSTRUCTION_LADDER.md` §Skills.\n"
    ) % (root, root)

    body = """# %s — first run

Founded by ProtocolCity (`blueprint setup` or `found`). This **workspace**
is a folder **you named** + instructions + (optional) ticket desk. Nothing
here forces `project`, `app`, or `my-city` — those were never product requirements.

## What was written

%s
## Desk join

%s
## Vendor CLIs on this machine

%s

## Open BluePrint (right now)

```bash
# Stranger / clean machine: start suite + engines (Explorer · Desk · Agents).
# Ctrl-C stops the suite and any engines this process started.
blueprint serve --root %s --port %d --with-engines
# Host already running launchd engines? omit --with-engines (honest bind).
# open http://127.0.0.1:%d/   ← Map (tickets + hands in-Map)
```

%s
%s
## Next

%s""" % (
        city_name,
        papers_table,
        desk_block,
        cli_lines,
        root,
        map_port,
        map_port,
        open_hint,
        skills_bridge,
        next_block,
    )
    path.write_text(body, encoding="utf-8")
    return path


def found(
    target: Path,
    *,
    city_name: Optional[str] = None,
    neighborhood: Optional[str] = None,
    force: bool = False,
    with_desk: bool = True,
    desk_url: str = DEFAULT_DESK,
    sample_ticket: bool = True,
    map_port: int = 8801,
    plant_seats: bool = False,
    hire_seats: bool = False,
    held_providers: Optional[Iterable[str]] = None,
    workforce_bin: str = "workforce",
) -> Dict[str, object]:
    """Scaffold a workspace at *target*. Returns a receipt dict for the CLI/proof.

    *neighborhood* (CLI: ``--project`` / ``--neighborhood``) is **optional**.
    When omitted, only workspace law is planted — no default project folder.
    When set, that string is the folder name the user chose (not a product default).
    """
    root = target.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    name = city_name or root.name
    agents = root / "AGENTS.md"
    if agents.exists() and not force:
        raise FileExistsError(
            "%s already has AGENTS.md — refuse to overwrite (pass --force)" % root
        )

    # Optional first project — name is entirely the caller's choice.
    # Never default to "project" / "app" / "my-city".
    raw_hood = (neighborhood or "").strip().strip("/").replace("\\", "/")
    if raw_hood in (".", "..") or "/" in raw_hood or raw_hood.startswith("."):
        raise ValueError(
            "project name must be a single top-level folder name "
            "(you pick it — e.g. recipes, tradeOS, client-acme)"
        )
    hood: Optional[str] = raw_hood or None
    hood_title = (
        hood.replace("-", " ").replace("_", " ").title() if hood else None
    )
    prefix: Optional[str] = _prefix_for(hood) if hood else None
    store_slug: Optional[str] = slugify(hood) if hood else None

    agents.write_text(_honest_city_agents(name, hood, prefix), encoding="utf-8")

    # pc-427: workspace is BluePrint-founded — stamp join marker
    from protocolcity.adopt import stamp_managed

    stamp_managed(root)

    # pc-1056: root place sentinel in cities.json (slug __root__, level 0)
    try:
        from protocolcity.registry import ensure_root_place

        ensure_root_place(root, name=name)
    except Exception:
        pass

    # Vendor pointers planted later (pc-1063 thin @AGENTS.md defaults).
    edges_dst = root / "BOUNDARIES.md"
    if not edges_dst.exists() or force:
        try:
            edges_body = _template("BOUNDARIES.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            try:
                edges_body = _template("PERIMETER.md").read_text(encoding="utf-8")
            except FileNotFoundError:
                try:
                    edges_body = _template("OFFICE_PERIMETER.md").read_text(
                        encoding="utf-8"
                    )
                except FileNotFoundError:
                    edges_body = _template("CITY_EDGES.md").read_text(encoding="utf-8")
        edges_dst.write_text(
            _strip_html_comments(_blank_placeholders(edges_body)),
            encoding="utf-8",
        )

    # pc-801 / pc-810: local skills shelf — coordination layer for agents (not cloud).
    # Plant placement README + .agents/skills so L0 SoT path exists for vendor bridges.
    agents_skills = root / ".agents" / "skills"
    agents_skills.mkdir(parents=True, exist_ok=True)
    skills_dir = root / ".claude" / "skills"
    skills_readme = skills_dir / "README.md"
    if not skills_readme.exists() or force:
        skills_dir.mkdir(parents=True, exist_ok=True)
        try:
            skills_body = _template("skills-README.md").read_text(encoding="utf-8")
            # Concrete workspace path for Grok [skills] paths bridge (pc-810).
            skills_body = skills_body.replace("{{WORKSPACE_ROOT}}", str(root))
            skills_readme.write_text(
                _strip_html_comments(_blank_placeholders(skills_body)),
                encoding="utf-8",
            )
        except FileNotFoundError:
            # Older package without the template — still create a minimal shelf.
            skills_readme.write_text(
                "# Workspace skills (L0 toolkit)\n\n"
                "Local coordination layer for AI agents. Add "
                "`.claude/skills/<id>/SKILL.md` (or `.agents/skills/<id>/` "
                "with a `.claude` mirror). Not cloud; CLI homes may symlink here.\n"
                "L0 must load in project sessions — Grok: "
                "`[skills] paths = [\"%s/.agents/skills\"]` in ~/.grok/config.toml.\n"
                "See BluePrint `INSTRUCTION_LADDER.md` §Skills.\n"
                % (root,),
                encoding="utf-8",
            )

    # pc-876: plant portable L0 workspace-efficiency skill + discovery scripts
    # (skills_sync + open_work_audit) so every founded workspace drains queues
    # on a cadence — not only the host monorepo.
    try:
        from protocolcity.seed_ops import plant_efficiency_kit

        plant_efficiency_kit(root, force=force, quiet=True)
    except Exception:
        pass

    # pc-1063 + pc-1079: full vendor-agnostic layer by default on every fresh city.
    # Order: plant SoT shelves (+ seed L0 worklane) → baseline .mcp.json
    # (portable worklane/workforce) → import extras → re-seed L0 canonical
    # → regenerate mirror with _bp marker.
    vendor_cfg: Optional[Dict] = None
    mcp_layer: Optional[Dict] = None
    secrets_layer: Optional[Dict] = None
    try:
        from protocolcity.mcp_sync import (
            apply_mcp,
            import_from_mcp_json,
            plant_mcp_kit,
            seed_l0_mcp_manifests,
        )
        from protocolcity.vendor_config import plant_vendor_configs

        plant_mcp_kit(root, force=force, write_mcp_json=False, seed_l0=True)
        # found in temp/CI: skip ~/.grok mutation unless this is a real home city
        vendor_cfg = plant_vendor_configs(
            root, force=force, touch_grok=False
        )
        # Import any extra servers from planted baseline .mcp.json (non-L0 extras)
        import_from_mcp_json(root, force=False)
        # Design-canonical L0 wins over crude import fields (tokens + field law)
        seed_l0_mcp_manifests(root, force=True, include_worklane=True)
        mcp_layer = apply_mcp(root, touch_vendors=False)
        if isinstance(vendor_cfg, dict):
            vendor_cfg = dict(vendor_cfg)
            vendor_cfg["mcp_sync"] = mcp_layer
    except Exception as e:
        if vendor_cfg is None:
            vendor_cfg = {"ok": False, "error": str(e)}
        mcp_layer = {"ok": False, "error": str(e)}

    # pc-1059: city policy SoT + policy_sync bridge → generated Claude settings.
    # Host-personal overrides stay in .claude/settings.local.json only.
    try:
        from protocolcity.policy_sync import plant_policy_kit

        plant_policy_kit(root, force=force, write_settings=True)
    except Exception:
        pass

    # pc-1061 / pc-1063: host secrets inventory shelf (names + lifecycle only).
    try:
        from protocolcity.secrets_inventory import plant_secrets_kit

        secrets_layer = plant_secrets_kit(root, force=force)
    except Exception as e:
        secrets_layer = {"ok": False, "error": str(e)}

    # pc-1063: thin vendor pointers by default (SoT remains AGENTS.md only).
    # One-line @AGENTS.md — never a second law body. force rewrites diverged.
    _THIN_POINTER = "@AGENTS.md\n"
    for ptr_name in ("CLAUDE.md", "GROK.md"):
        ptr = root / ptr_name
        if ptr.exists() and not force:
            continue
        try:
            if ptr.is_symlink():
                ptr.unlink()
            ptr.write_text(_THIN_POINTER, encoding="utf-8")
        except OSError:
            pass

    hood_dir: Optional[Path] = None
    if hood and hood_title and prefix and store_slug:
        hood_dir = root / hood
        # project folder stamped after its AGENTS plant below
        hood_dir.mkdir(parents=True, exist_ok=True)
        hood_agents = hood_dir / "AGENTS.md"
        if not hood_agents.exists() or force:
            # pc-1041: same template path as adopt (project-AGENTS.md)
            hood_agents.write_text(
                project_agents_body(
                    title=hood_title,
                    store_slug=store_slug,
                    prefix=prefix,
                    origin="found",
                ),
                encoding="utf-8",
            )
            stamp_managed(hood_dir)
            readme = hood_dir / "README.md"
            if not readme.exists() or force:
                readme.write_text(
                    "# %s\n\nProject under workspace **%s**.\n" % (hood_title, name),
                    encoding="utf-8",
                )
        # pc-1087: ARCHITECTURE.md is L1 product law beside AGENTS.md
        hood_arch = hood_dir / "ARCHITECTURE.md"
        if not hood_arch.exists() or force:
            plant_arch = True
            if hood_arch.exists() and force:
                try:
                    plant_arch = looks_like_architecture_scaffold(
                        hood_arch.read_text(encoding="utf-8")
                    )
                except OSError:
                    plant_arch = True
            if plant_arch:
                hood_arch.write_text(
                    project_architecture_body(title=hood_title, origin="found"),
                    encoding="utf-8",
                )
        # pc-1264: PROGRAMS.md beside AGENTS — 3–5 named lines, not an atlas
        hood_progs = hood_dir / "PROGRAMS.md"
        if not hood_progs.exists() or force:
            plant_progs = True
            if hood_progs.exists() and force:
                try:
                    plant_progs = looks_like_programs_scaffold(
                        hood_progs.read_text(encoding="utf-8")
                    )
                except OSError:
                    plant_progs = True
            if plant_progs:
                hood_progs.write_text(
                    project_programs_body(title=hood_title, origin="found"),
                    encoding="utf-8",
                )
        # pc-1317: FEATURES.md — docs/ preferred, root fallback when no docs/
        plant_project_features(
            hood_dir, title=hood_title, origin="found", force=force
        )

        workers_dir = hood_dir / "workers" / "demo-worker"
        if not workers_dir.exists() or force:
            workers_dir.mkdir(parents=True, exist_ok=True)
            for src_name, dest_name in (
                ("worker-CONTRACT.md", "CONTRACT.md"),
                ("worker-prompt.md", "prompt.md"),
            ):
                body = _template(src_name).read_text(encoding="utf-8")
                # Found knows identity and store even though execution remains
                # unconfigured. Never blank these into misleading claim targets.
                for key, value in {
                    "WORKER_ID": "demo-worker",
                    "STORE_SLUG": store_slug,
                    "NEIGHBORHOOD_NAME": hood_title,
                }.items():
                    body = body.replace("{{" + key + "}}", value)
                (workers_dir / dest_name).write_text(
                    _strip_html_comments(_blank_placeholders(body)),
                    encoding="utf-8",
                )

    clis = detect_vendor_clis()

    seats_result: Optional[Dict] = None
    desk_result: Optional[Dict] = None
    if with_desk and hood and store_slug and hood_title and prefix:
        if desk_reachable(desk_url):
            desk_result = bootstrap_desk(
                store_slug,
                display=hood_title,
                prefix=prefix,
                desk_url=desk_url,
                sample_ticket=sample_ticket,
                project_root=str(hood_dir) if hood_dir is not None else None,
            )
            if desk_result.get("ok") and hood_dir is not None:
                # pc-487: durable join under the neighborhood
                write_desk_join(
                    hood_dir,
                    slug=store_slug,
                    prefix=prefix,
                    display=hood_title,
                    desk_url=desk_url,
                )
                soft_append_desk_identity(
                    hood_dir / "AGENTS.md",
                    slug=store_slug,
                    prefix=prefix,
                )
        else:
            # pc-314: don't lose the join — queue it for serve --with-engines.
            queue_pending_join(
                root,
                store_slug,
                display=hood_title,
                prefix=prefix,
                sample_ticket=sample_ticket,
            )
            desk_result = {
                "ok": False,
                "reachable": False,
                "desk_url": desk_url,
                "pending": True,
                "error": "desk offline — scaffold only; join queued for "
                "`blueprint serve --with-engines` (desk at %s)"
                % desk_url,
            }
    elif with_desk and not hood:
        # Workspace-only found: report desk reachability for honesty, no store.
        reachable = desk_reachable(desk_url)
        desk_result = {
            "ok": True,
            "reachable": reachable,
            "desk_url": desk_url,
            "skipped": True,
            "reason": "no project at found — adopt or --project first",
        }

    if plant_seats and hood and store_slug and hood_dir is not None:
        from protocolcity.adopt import plant_standard_seats

        seats_result = plant_standard_seats(
            root,
            store_slug,
            project_path=hood_dir,
            prefix=prefix,
            hire=hire_seats,
            held=held_providers,
            workforce_bin=workforce_bin,
        )

    first_run = _write_first_run(
        root,
        city_name=name,
        hood=hood,
        store_slug=store_slug,
        prefix=prefix,
        clis=clis,
        desk=desk_result,
        map_port=map_port,
    )

    next_steps = [
        "blueprint serve --root %s --port %d --with-engines" % (root, map_port),
        "open http://127.0.0.1:%d/  (Overview · Explorer /map · Desk · Agents /roster)" % map_port,
        "read %s" % first_run,
    ]
    if hood and store_slug:
        if desk_result and desk_result.get("reachable") and desk_result.get("ok"):
            next_steps.append(
                "desk store `%s` ready — sample work order on the board" % store_slug
            )
        elif desk_result and not desk_result.get("reachable"):
            next_steps.append(
                "start WorkLane desk then re-run with --force or create store slug `%s`"
                % store_slug
            )
        next_steps.append(
            "hire: fill %s/workers/demo-worker/ + WorkForce roster row" % hood
        )
        next_steps.append(
            "more projects: drop folders here + `blueprint adopt %s <name>`" % root
        )
    else:
        next_steps.append(
            "add work: put existing folders under %s (keep their names)" % root
        )
        next_steps.append(
            "then: blueprint adopt %s <folder-name>" % root
        )
        next_steps.append(
            "or adopt all safe unmanaged folders: "
            "blueprint adopt %s --adopt-existing" % root
        )
        next_steps.append(
            "or scaffold one named project: blueprint found %s --project <your-name> --force"
            % root
        )

    return {
        "root": str(root),
        "city_name": name,
        "neighborhood": hood,  # optional; None when workspace-only
        "neighborhood_path": str(hood_dir) if hood_dir else None,
        "agents": str(agents),
        "first_run": str(first_run),
        "store_slug": store_slug,
        "prefix": prefix,
        "vendor_clis": [{"name": n, "path": p} for n, p in clis],
        "vendor_configs": vendor_cfg,
        "mcp_layer": mcp_layer,
        "secrets_layer": secrets_layer,
        "desk": desk_result,
        "seats": seats_result,
        "map_port": map_port,
        "next_steps": next_steps,
    }


def print_receipt(receipt: Dict[str, object]) -> None:
    print("Founded workspace at %s" % receipt["root"])
    print("  instructions: %s" % receipt["agents"])
    hood_path = receipt.get("neighborhood_path")
    hood = receipt.get("neighborhood")
    if hood_path and hood:
        print("  project:      %s  (name you chose)" % hood_path)
    else:
        print(
            "  project:      (none yet — drop folders + adopt, or found --project <name>)"
        )
    print("  first-run:    %s" % receipt.get("first_run"))
    clis = receipt.get("vendor_clis") or []
    if clis:
        print(
            "  vendor CLIs:  "
            + ", ".join(c["name"] for c in clis)  # type: ignore[index]
        )
    else:
        print(
            "  vendor CLIs:  (none on PATH — install claude/codex/"
            "cursor-agent/grok to staff)"
        )
    desk = receipt.get("desk")
    if isinstance(desk, dict):
        if desk.get("skipped"):
            print(
                "  desk:         %s — no project store yet (%s)"
                % (
                    "up" if desk.get("reachable") else "offline/unknown",
                    desk.get("reason") or "adopt or --project first",
                )
            )
        elif desk.get("reachable") and desk.get("ok"):
            store = desk.get("store") or {}
            ticket = desk.get("ticket") or {}
            tid = None
            if isinstance(ticket, dict):
                t = ticket.get("task") if isinstance(ticket.get("task"), dict) else ticket
                if isinstance(t, dict):
                    tid = t.get("id")
            print(
                "  desk:         %s · store `%s` %s · ticket %s"
                % (
                    desk.get("desk_url"),
                    receipt.get("store_slug"),
                    "created" if store.get("created") else "joined",
                    tid or "—",
                )
            )
            if desk.get("ticket_error"):
                print("  desk note:    ticket: %s" % desk.get("ticket_error"))
        else:
            print(
                "  desk:         offline/skipped — %s"
                % (desk.get("error") or desk.get("desk_url") or "n/a")
            )
    print("Next:")
    for step in receipt.get("next_steps") or []:
        print("  · %s" % step)
