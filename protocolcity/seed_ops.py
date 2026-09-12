"""Seed workspace ops kit; routines stay off the WorkForce roster by default.

Office/workspace **jobs** (default trio: chief-of-staff · health-patrol ·
workspace-efficiency) are BluePrint **routines**, not product-lane seats.
After an intentional retire (local roster = product lanes only), seed-ops
must not put those three back. Pass ``hire_routines=True`` to opt in
through the Python API. Non-routine ``jobs=`` (digest,
demo-worker / product lanes) still hire.

Idempotent: skips names already on the WorkForce roster. Old seat names
(marshal, papers-patrol, …) count as aliases so renames never double-seed
(pc-988). clerk / correspondent are no longer defaults (leave existing).

Also plants L0 skill + discovery scripts when templates ship with the package.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Workspace ops — function-named jobs (not product lanes).
# Schedules are LOCAL machine time (cron on this host). Laptop off = no fire.
# Default to weekday work hours so 9–5 users are more likely to be on
# (founder 2026-07-26 / pc-430). Users may re-pin any schedule after hire.
#
# pc-988 · three-seat model (ratified pc-987): chief-of-staff + health-patrol
# + workspace-efficiency. clerk/correspondent dropped from defaults (brief/
# rollup fold into chief-of-staff). marshal renamed → health-patrol.
DEFAULT_OPS_JOBS: List[Dict[str, str]] = [
    {
        "name": "chief-of-staff",
        "role": "coordination — routing, capacity staging, inbox triage",
        "schedule": "0 9 * * 1-5",  # 09:00 Mon–Fri local
        "kind": "job",
    },
    {
        "name": "health-patrol",
        "role": "health patrol",
        "schedule": "0 11,15 * * 1-5",  # 11:00 + 15:00 Mon–Fri local
        "kind": "job",
    },
    {
        "name": "workspace-efficiency",
        "role": "workspace drain hygiene",
        "schedule": "30 9,16 * * *",  # 09:30 + 16:30 daily local
        "kind": "job",
    },
]

# Canonical seat → prior names that already satisfy the seat (no re-hire).
# Existing installs with marshal keep that seat; re-seed does not add
# health-patrol beside it. papers-sync is optional (not in DEFAULT_OPS_JOBS)
# but plant/hire paths share the same alias law.
OPS_JOB_ALIASES: Dict[str, Tuple[str, ...]] = {
    "health-patrol": ("marshal", "city-marshal"),
    "papers-sync": ("papers-patrol",),
}

# BluePrint routines — not WorkForce product-lane seats. Default seed
# (hire_routines=False) skips these so a restart / seed-ops cannot reseat
# them after an intentional retire.
OPS_ROUTINE_SLUGS: frozenset = frozenset(
    {
        "chief-of-staff",
        "health-patrol",
        "workspace-efficiency",
    }
)


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return _pkg_dir().parent


def _templates_dir() -> Path:
    """Templates ship inside the package for pip/brew; monorepo keeps root copy."""
    packaged = _pkg_dir() / "templates"
    if packaged.is_dir():
        return packaged
    monorepo = _repo_root() / "templates"
    if monorepo.is_dir():
        return monorepo
    return packaged


def _roster_path(city_root: Path) -> Path:
    return (
        city_root.expanduser().resolve()
        / ".protocolcity"
        / "workforce"
        / "local"
        / "roster.json"
    )


def _ops_workdir(city_root: Path) -> Path:
    """Papers + workdir for workspace ops (Map paints via .protocolcity/ops)."""
    return city_root.expanduser().resolve() / ".protocolcity" / "ops"


def _existing_names(roster_path: Path) -> set:
    if not roster_path.is_file():
        return set()
    try:
        data = json.loads(roster_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    workers = data.get("workers") if isinstance(data, dict) else data
    names: set = set()
    if isinstance(workers, dict):
        for k, w in workers.items():
            names.add(str(k).lower())
            if isinstance(w, dict) and w.get("name"):
                names.add(str(w["name"]).lower())
    elif isinstance(workers, list):
        for w in workers:
            if isinstance(w, dict) and w.get("name"):
                names.add(str(w["name"]).lower())
    return names


def _seat_already_present(name: str, existing: set) -> bool:
    """True when roster has the canonical name or a recognized old alias."""
    key = (name or "").strip().lower()
    if not key:
        return False
    if key in existing:
        return True
    for alias in OPS_JOB_ALIASES.get(key, ()):
        if alias.lower() in existing:
            return True
    return False


def _is_ops_routine(name: str) -> bool:
    """True for the local routine trio or a recognized old alias of one."""
    key = (name or "").strip().lower()
    if not key:
        return False
    if key in OPS_ROUTINE_SLUGS:
        return True
    for canon, aliases in OPS_JOB_ALIASES.items():
        if canon not in OPS_ROUTINE_SLUGS:
            continue
        if key in {a.lower() for a in aliases}:
            return True
    return False


def plant_efficiency_kit(
    city_root: Path,
    *,
    force: bool = False,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Plant L0 workspace-efficiency skill + scripts (skills_sync, open_work_audit).

    Idempotent. Safe to call from seed-ops and found. Does not hire.
    """
    root = city_root.expanduser().resolve()
    tdir = _templates_dir()
    planted: List[str] = []
    skipped: List[str] = []

    # Skill SoT
    skill_src = tdir / "skills" / "workspace-efficiency" / "SKILL.md"
    skill_dst = root / ".agents" / "skills" / "workspace-efficiency" / "SKILL.md"
    if skill_src.is_file():
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        if not skill_dst.exists() or force:
            shutil.copy2(skill_src, skill_dst)
            planted.append(str(skill_dst.relative_to(root)))
        else:
            skipped.append(str(skill_dst.relative_to(root)))
        # Discovery mirror under .claude/skills
        claude_link = root / ".claude" / "skills" / "workspace-efficiency"
        claude_link.parent.mkdir(parents=True, exist_ok=True)
        if not claude_link.exists() or (force and claude_link.is_symlink()):
            try:
                if claude_link.is_symlink() or claude_link.exists():
                    if claude_link.is_symlink():
                        claude_link.unlink()
                rel = os.path.relpath(skill_dst.parent, claude_link.parent)
                os.symlink(rel, claude_link)
                planted.append(".claude/skills/workspace-efficiency → .agents")
            except OSError:
                # Windows / no symlink — copy tree as fallback
                if not claude_link.exists() or force:
                    if claude_link.exists() and not claude_link.is_dir():
                        claude_link.unlink()
                    claude_link.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(skill_src, claude_link / "SKILL.md")
                    planted.append(".claude/skills/workspace-efficiency (copy)")
        elif not quiet:
            skipped.append(".claude/skills/workspace-efficiency")

    # Scripts
    scripts_dst = root / "scripts"
    # Monorepo SoT (pc-958 / pc-1059 / pc-1191): when the ProtocolCity parcel
    # ships the script, plant a discovery mirror (symlink) at <ws>/scripts/
    # rather than a second independent copy. Bare cities (no ProtocolCity/)
    # still get a real plant from templates/scripts/.
    # open_work_audit.py is included so workspace-root
    # `python3 scripts/open_work_audit.py` resolves the parcel package
    # without a ProtocolCity/.venv workaround.
    _MONOREPO_MIRROR_SCRIPTS = frozenset(
        {
            "skills_sync.sh",
            "policy_sync.sh",
            "open_work_audit.py",
        }
    )
    for name in (
        "skills_sync.sh",
        "policy_sync.sh",
        "open_work_audit.py",
        "report_to_for_you.py",
    ):
        scripts_dst.mkdir(parents=True, exist_ok=True)
        dst = scripts_dst / name

        pc_sot = root / "ProtocolCity" / "scripts" / name
        if (
            name in _MONOREPO_MIRROR_SCRIPTS
            and pc_sot.is_file()
            and not pc_sot.is_symlink()
        ):
            rel = os.path.relpath(pc_sot, scripts_dst)
            if dst.is_symlink() and os.readlink(str(dst)) == rel and not force:
                skipped.append(f"scripts/{name} → ProtocolCity (mirror)")
                continue
            # Independent real file: leave unless force (one-shot adopt mirror).
            if dst.exists() and not dst.is_symlink() and not force:
                skipped.append(
                    f"scripts/{name} (independent copy; re-run force to mirror)"
                )
                continue
            if dst.is_symlink() or dst.is_file():
                dst.unlink()
            try:
                os.symlink(rel, dst)
                planted.append(f"scripts/{name} → {rel}")
                continue
            except OSError:
                # No symlink support — copy SoT bytes instead.
                shutil.copy2(pc_sot, dst)
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
                planted.append(str(dst.relative_to(root)))
                continue

        src = tdir / "scripts" / name
        if not src.is_file():
            # monorepo fallback: ProtocolCity/scripts/
            alt = _repo_root() / "scripts" / name
            src = alt if alt.is_file() else src
        if not src.is_file():
            continue
        if not dst.exists() or force:
            shutil.copy2(src, dst)
            if name.endswith(".sh") or name.endswith(".py"):
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
            planted.append(str(dst.relative_to(root)))
        else:
            skipped.append(str(dst.relative_to(root)))

    # pc-1059: plant city policy SoT shelf (permissions paper + README).
    # Does not overwrite existing .claude/settings.json unless force — import path
    # handles migration. Fresh cities get settings when write_settings plants them.
    try:
        from protocolcity.policy_sync import plant_policy_kit

        pol = plant_policy_kit(
            root, force=force, write_settings=not (root / ".claude" / "settings.json").exists()
        )
        for p in pol.get("planted") or []:
            if p not in planted:
                planted.append(p)
        for p in pol.get("skipped") or []:
            if p not in skipped:
                skipped.append(p)
    except Exception:
        pass

    return {"ok": True, "planted": planted, "skipped": skipped}


# Files planted from templates/ops/<name>/ into .protocolcity/ops/workers/<name>/
_OPS_PAPER_FILES = ("CONTRACT.md", "prompt.md", "capacity_policy.json")


def _apply_job_papers(
    ops_wd: Path,
    name: str,
    *,
    force: bool = False,
) -> bool:
    """Overwrite generic hire stubs with job-specific templates when present.

    Copies CONTRACT.md, prompt.md, and optional capacity_policy.json (pc-979
    chief-of-staff Mode B envelope). Idempotent unless force=True.
    """
    tdir = _templates_dir() / "ops" / name
    if not tdir.is_dir():
        return False
    dest = ops_wd / "workers" / name
    dest.mkdir(parents=True, exist_ok=True)
    wrote = False
    for fname in _OPS_PAPER_FILES:
        src = tdir / fname
        if not src.is_file():
            continue
        out = dest / fname
        if out.exists() and not force:
            continue
        shutil.copy2(src, out)
        wrote = True
    return wrote


def plant_ops_seat_papers(
    city_root: Path,
    name: str,
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Plant ops-kit papers for one seat without hiring (detect/surface).

    Used by hire (pc-979) and tests. Live path:
    ``.protocolcity/ops/workers/<name>/`` with scope workspace_ops.
    """
    root = city_root.expanduser().resolve()
    ops_wd = _ops_workdir(root)
    ops_wd.mkdir(parents=True, exist_ok=True)
    wrote = _apply_job_papers(ops_wd, name, force=force)
    dest = ops_wd / "workers" / name
    files = []
    if dest.is_dir():
        for fname in _OPS_PAPER_FILES:
            if (dest / fname).is_file():
                files.append(str((dest / fname).relative_to(root)))
    return {
        "ok": bool(files),
        "name": name,
        "wrote": wrote,
        "files": files,
        "ops_workdir": str(ops_wd),
        "path": str(dest) if dest.is_dir() else "",
    }


def seed_workspace_ops(
    city_root: Path,
    *,
    jobs: Optional[List[Dict[str, str]]] = None,
    quiet: bool = False,
    hire_routines: bool = False,
) -> Dict[str, Any]:
    """Plant the L0 ops kit; do not reseat BluePrint routines unless asked.

    Default ``hire_routines=False`` (serve/start, seed-ops, Map CTA) plants
    the efficiency kit but does **not** hire chief-of-staff / health-patrol /
    workspace-efficiency into WorkForce. Explicit ``jobs=`` entries that are
    not routines still hire (digest, product lanes). Opt in with
    ``hire_routines=True``.

    Returns a receipt: {ok, seeded, skipped, routines, errors, roster}.
    Also plants the workspace-efficiency skill + scripts kit.
    """
    root = city_root.expanduser().resolve()
    if not root.is_dir():
        return {
            "ok": False,
            "error": "city root missing: %s" % root,
            "seeded": [],
            "skipped": [],
            "errors": [],
        }

    kit = plant_efficiency_kit(root, force=False, quiet=quiet)
    if kit.get("planted") and not quiet:
        print("seed-ops: kit %s" % ", ".join(kit["planted"]), flush=True)

    ops_wd = _ops_workdir(root)
    ops_wd.mkdir(parents=True, exist_ok=True)
    roster_path = _roster_path(root)
    roster_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _existing_names(roster_path)
    want = jobs if jobs is not None else DEFAULT_OPS_JOBS
    seeded: List[str] = []
    skipped: List[str] = []
    routines: List[str] = []
    errors: List[str] = []
    papers_updated: List[str] = []
    to_hire: List[Dict[str, str]] = []

    for job in want:
        name = (job.get("name") or "").strip()
        if not name:
            continue
        if not hire_routines and _is_ops_routine(name):
            routines.append(name)
            skipped.append(name)
            continue
        to_hire.append(job)

    def _receipt(**extra: Any) -> Dict[str, Any]:
        out = {
            "ok": not errors,
            "seeded": seeded,
            "skipped": skipped,
            "routines": routines,
            "errors": errors,
            "roster": str(roster_path),
            "ops_workdir": str(ops_wd),
            "kit": kit,
            "papers_updated": papers_updated,
            "hire_routines": hire_routines,
        }
        out.update(extra)
        return out

    if not to_hire:
        return _receipt()

    try:
        from workforce.hire import hire, RosterError  # type: ignore
    except ImportError:
        # Best-effort: sibling checkout (developer city)
        import sys

        here = Path(__file__).resolve()
        try:
            from protocolcity.workspace import resolve_workspace_root

            ws = resolve_workspace_root(start=here, use_registry=True)
        except Exception:
            ws = None
        cands = [here.parents[2] / "workforce"]
        if ws is not None:
            cands.append(ws / "workforce")
        for cand in cands:
            if (cand / "workforce" / "hire.py").is_file():
                p = str(cand)
                if p not in sys.path:
                    sys.path.insert(0, p)
                break
        try:
            from workforce.hire import hire, RosterError  # type: ignore
        except ImportError as e:
            return _receipt(
                ok=False,
                error="protocolcity-workforce not installed (%s)" % e,
                errors=[str(e)],
            )

    for job in to_hire:
        name = (job.get("name") or "").strip()
        if not name:
            continue
        if _seat_already_present(name, existing):
            skipped.append(name)
            # Still refresh job-specific papers if missing (never force overwrite).
            # Alias-only installs (e.g. marshal without health-patrol dir) keep
            # papers under the live roster name — plant under canonical only when
            # that folder is the one present or we just hire the new name.
            if name.lower() in existing and _apply_job_papers(
                ops_wd, name, force=False
            ):
                papers_updated.append(name)
            continue
        try:
            result = hire(
                name=name,
                workdir=str(ops_wd),
                role=job.get("role") or "",
                kind=job.get("kind") or "job",
                schedule=job.get("schedule") or "0 8 * * *",
                model="",
                command=["true"],  # cheap until user pins a real CLI
                project="workspace-ops",
                roster_path=str(roster_path),
                plant=True,
                dry_run=False,
            )
            if result.get("ok"):
                seeded.append(name)
                existing.add(name.lower())
                if _apply_job_papers(ops_wd, name, force=True):
                    papers_updated.append(name)
                if not quiet:
                    print("seed-ops: hired %s → %s" % (name, ops_wd), flush=True)
            else:
                errors.append("%s: %s" % (name, result.get("error") or result))
        except RosterError as e:
            # Already exists race
            msg = str(e).lower()
            if "already" in msg or "duplicate" in msg:
                skipped.append(name)
                if _apply_job_papers(ops_wd, name, force=False):
                    papers_updated.append(name)
            else:
                errors.append("%s: %s" % (name, e))
        except Exception as e:
            errors.append("%s: %s" % (name, e))

    return _receipt()
