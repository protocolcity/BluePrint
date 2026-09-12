"""City MCP registry SoT → generated vendor mirrors (pc-1078 / design pc-1055).

Principle (skills_sync / policy_sync family — generate, don't document):

* **SoT** lives under the city tree: ``.agents/mcp/<id>/manifest.json``
* **Vendor mirrors** are generated/patched — never hand-authored as SoT:
  - workspace ``.mcp.json`` (Claude / Cursor) — full generate with ``_bp`` marker
  - ``~/.grok/config.toml`` and ``~/.codex/config.toml`` ``[mcp_servers.<id>]``
    managed blocks only (personal servers not in the registry are left alone)
* **Secrets** stay on the host as env values; registry stores **names** only
  (``env_required``). Missing names are report-only findings here; the full
  lifecycle check + inventory paper is ``protocolcity.secrets_inventory``
  / ``scripts/check_mcp_secrets.py`` (pc-1061).

See ``docs/research/byo-mcp-library-design-2026-08.md`` and
``docs/specs/HOST_SECRETS_INVENTORY.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REGISTRY_REL = Path(".agents") / "mcp"
MANIFEST_NAME = "manifest.json"
MCP_JSON_REL = Path(".mcp.json")
GENERATED_BY = "mcp_sync"
SCHEMA_VERSION = 1

REQUIRED_FIELDS = (
    "id",
    "description",
    "transport",
    "capability",
    "risk",
    "seats",
    "level",
    "vendor_locked",
    "enabled",
)

# Legacy vendor ids that map onto a registry id (design §10 "and aliases").
# When projecting managed blocks, strip these so stale temp/Developer paths die.
MANAGED_ALIASES: Dict[str, Tuple[str, ...]] = {
    "worklane": ("ticketingprotocol",),
}

# Packaged L0 seed ids. On apply, strip these from vendor configs when they are
# *not* in the city registry (unseed / disabled-removed) so dead projections
# do not linger (pc-1079 workforce optional gate).
PACKAGE_L0_SEED_IDS: Tuple[str, ...] = ("worklane", "workforce")

# Retired module name still seen in sibling-checkout plants (pc-1425 / GH #33).
STALE_MCP_MODULE = "ticketingprotocol.mcp"
MCP_COMMAND_MISSING = "MCP-COMMAND-MISSING"

# Nested [mcp_servers.<id>.*] sections (e.g. Codex env tables) ride with the id.
_MCP_SECTION_RE = re.compile(
    r"^\[mcp_servers\.([^\].]+)(?:\.([^\]]+))?\]\s*$"
)


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


def workspace_root_norm(workspace: Path) -> str:
    return str(workspace.expanduser().resolve()).rstrip("/")


def registry_dir(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / REGISTRY_REL


def mcp_json_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / MCP_JSON_REL


def expand_tokens(value: str, workspace: Path) -> str:
    """Expand ``{{WORKSPACE_ROOT}}``; leave ``${VAR}`` templates intact."""
    root = workspace_root_norm(workspace)
    return value.replace("{{WORKSPACE_ROOT}}", root)


def stdio_command_resolves(command: str) -> bool:
    """True when *command* is an existing file or a PATH executable.

    Absolute / ``~`` paths are ``stat``-ed. Bare names (``python3``,
    ``worklane-mcp``) use ``PATH``. Empty string does not resolve.
    pc-1425 / GH #33: doctor must not paint MCP-REGISTRY ok when the
    WorkLane process cannot start.
    """
    cmd = (command or "").strip()
    if not cmd:
        return False
    expanded = os.path.expanduser(cmd)
    if os.path.isabs(expanded):
        return os.path.exists(expanded)
    return shutil.which(cmd) is not None


def check_stdio_commands(
    manifests: Sequence[Dict[str, Any]],
    workspace: Path,
) -> List[Dict[str, Any]]:
    """Flag enabled stdio servers whose command path does not resolve."""
    findings: List[Dict[str, Any]] = []
    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        if str(m.get("transport") or "stdio") != "stdio":
            continue
        raw = str(m.get("command") or "")
        cmd = expand_tokens(raw, workspace)
        if stdio_command_resolves(cmd):
            continue
        sid = str(m.get("id") or "")
        findings.append(
            {
                "server": sid,
                "command": cmd,
                "code": MCP_COMMAND_MISSING,
                "detail": (
                    "stdio command %r for MCP server %s does not exist "
                    "and is not on PATH — host-chat cannot start the "
                    "process. Cursor mcp_auth is not a fix (local stdio, "
                    "not OAuth). Heal WorkLane with `blueprint doctor "
                    "--fix` or `bash scripts/mcp_sync.sh seed` then apply "
                    "(pc-1425 / GH #33)" % (cmd, sid or "?")
                ),
            }
        )
    return findings


def worklane_manifest_needs_heal(
    man: Dict[str, Any], workspace: Path
) -> bool:
    """True when the WorkLane L0 plant cannot start or still teaches the
    retired module name. Working sibling-venv commands are left alone.
    """
    args = man.get("args") or []
    if any(str(a) == STALE_MCP_MODULE for a in args):
        return True
    cmd = expand_tokens(str(man.get("command") or ""), workspace)
    return not stdio_command_resolves(cmd)


def expand_value(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return expand_tokens(value, workspace)
    if isinstance(value, list):
        return [expand_value(v, workspace) for v in value]
    if isinstance(value, dict):
        return {str(k): expand_value(v, workspace) for k, v in value.items()}
    return value


def validate_manifest(data: Dict[str, Any], *, path: Path) -> List[str]:
    """Return human-readable validation errors (empty = ok)."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be an object: %s" % path]
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append("missing required field %r in %s" % (field, path))
    mid = data.get("id")
    if isinstance(mid, str) and mid.strip() and path.parent.name != mid.strip():
        errors.append(
            "manifest id %r must match directory name %r (%s)"
            % (mid, path.parent.name, path)
        )
    transport = data.get("transport")
    if transport == "stdio":
        if not data.get("command"):
            errors.append("stdio transport requires command: %s" % path)
    elif transport in ("sse", "http"):
        if not data.get("url"):
            errors.append("%s transport requires url: %s" % (transport, path))
    elif transport is not None:
        errors.append("unknown transport %r in %s" % (transport, path))
    return errors


def load_manifest(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("manifest is not valid JSON: %s (%s)" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object: %s" % path)
    errs = validate_manifest(data, path=path)
    if errs:
        raise ValueError("; ".join(errs))
    # Fill id from directory when omitted was already required; normalize
    data = dict(data)
    data["id"] = str(data["id"]).strip()
    return data


def list_registry_ids(workspace: Path) -> List[str]:
    root = registry_dir(workspace)
    if not root.is_dir():
        return []
    ids: List[str] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / MANIFEST_NAME).is_file():
            ids.append(child.name)
    return ids


def load_registry(
    workspace: Path,
    *,
    enabled_only: bool = False,
) -> List[Dict[str, Any]]:
    """Load all manifests under ``.agents/mcp/``. Raises on bad JSON/schema."""
    root = registry_dir(workspace)
    if not root.is_dir():
        raise FileNotFoundError("MCP registry missing: %s" % root)
    out: List[Dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        man = child / MANIFEST_NAME
        if not man.is_file():
            continue
        data = load_manifest(man)
        if enabled_only and not bool(data.get("enabled", True)):
            continue
        out.append(data)
    return out


def manifest_to_mcp_server_entry(
    manifest: Dict[str, Any],
    workspace: Path,
) -> Dict[str, Any]:
    """Project one registry row → Claude/Cursor mcpServers entry (stdio/http)."""
    transport = str(manifest.get("transport") or "stdio")
    entry: Dict[str, Any] = {}
    if transport == "stdio":
        entry["command"] = expand_tokens(str(manifest["command"]), workspace)
        args = manifest.get("args") or []
        if not isinstance(args, list):
            args = []
        entry["args"] = [expand_tokens(str(a), workspace) for a in args]
    else:
        # sse / http — vendors differ; keep url (+ optional headers_env notes)
        if manifest.get("url"):
            entry["url"] = expand_tokens(str(manifest["url"]), workspace)
        if manifest.get("command"):
            # Some remote wrappers still spawn a local proxy
            entry["command"] = expand_tokens(str(manifest["command"]), workspace)
            args = manifest.get("args") or []
            if isinstance(args, list) and args:
                entry["args"] = [expand_tokens(str(a), workspace) for a in args]
    env = manifest.get("env")
    if isinstance(env, dict) and env:
        entry["env"] = {
            str(k): expand_tokens(str(v), workspace) for k, v in env.items()
        }
    return entry


def render_mcp_json_body(
    manifests: Sequence[Dict[str, Any]],
    workspace: Path,
) -> Dict[str, Any]:
    servers: Dict[str, Any] = {}
    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        if bool(m.get("vendor_locked")) and not m.get("command") and not m.get("url"):
            # Honesty row only — nothing to project into a runnable mirror
            continue
        servers[str(m["id"])] = manifest_to_mcp_server_entry(m, workspace)
    return {
        "_bp": {
            "generated_by": GENERATED_BY,
            "source": str(REGISTRY_REL).replace("\\", "/"),
            "version": SCHEMA_VERSION,
            "do_not_hand_edit": True,
        },
        "mcpServers": servers,
    }


def dumps_mcp_json(body: Dict[str, Any]) -> str:
    return json.dumps(body, indent=2, ensure_ascii=False) + "\n"


def canonicalize_mcp_json(body: Dict[str, Any]) -> str:
    """Stable compare: only _bp ownership + mcpServers shape."""
    bp = body.get("_bp") if isinstance(body.get("_bp"), dict) else {}
    servers = body.get("mcpServers") if isinstance(body.get("mcpServers"), dict) else {}
    slim = {
        "_bp": {
            "generated_by": bp.get("generated_by"),
            "source": bp.get("source"),
            "version": int(bp.get("version") or SCHEMA_VERSION),
            "do_not_hand_edit": bool(bp.get("do_not_hand_edit", True)),
        },
        "mcpServers": servers,
    }
    return json.dumps(slim, sort_keys=True, separators=(",", ":"))


def expected_mcp_json(workspace: Path) -> Dict[str, Any]:
    return render_mcp_json_body(load_registry(workspace), workspace)


# ---------------------------------------------------------------------------
# TOML managed-block patch (stdlib only — no tomlkit)
# ---------------------------------------------------------------------------


def _toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _toml_string(s: str) -> str:
    return '"%s"' % _toml_escape(s)


def _toml_array(values: Sequence[str]) -> str:
    if not values:
        return "[]"
    inner = ",\n".join("    %s" % _toml_string(v) for v in values)
    return "[\n%s,\n]" % inner


def _toml_inline_table(env: Dict[str, str]) -> str:
    parts = ["%s = %s" % (k, _toml_string(v)) for k, v in sorted(env.items())]
    return "{ %s }" % ", ".join(parts)


def render_toml_mcp_server_block(
    server_id: str,
    entry: Dict[str, Any],
    *,
    enabled: bool = True,
) -> str:
    """Render a single ``[mcp_servers.<id>]`` block (no nested env tables)."""
    lines = ["[mcp_servers.%s]" % server_id]
    if "command" in entry:
        lines.append("command = %s" % _toml_string(str(entry["command"])))
    if "args" in entry and isinstance(entry["args"], list):
        lines.append(
            "args = %s" % _toml_array([str(a) for a in entry["args"]])
        )
    if "url" in entry:
        lines.append("url = %s" % _toml_string(str(entry["url"])))
    env = entry.get("env")
    if isinstance(env, dict) and env:
        lines.append(
            "env = %s"
            % _toml_inline_table({str(k): str(v) for k, v in env.items()})
        )
    lines.append("enabled = %s" % ("true" if enabled else "false"))
    # Ownership comment for humans + future importers
    lines.append("# bp:generated mcp_sync — edit .agents/mcp/%s/manifest.json" % server_id)
    return "\n".join(lines) + "\n"


def _iter_toml_sections(text: str) -> List[Tuple[str, Optional[str], int, int]]:
    """Return list of (id, nested_or_None, start_line, end_line_exclusive)."""
    lines = text.splitlines(keepends=True)
    headers: List[Tuple[int, str, Optional[str]]] = []
    for i, line in enumerate(lines):
        m = _MCP_SECTION_RE.match(line.rstrip("\n").strip())
        if m:
            headers.append((i, m.group(1), m.group(2)))
    if not headers:
        return []
    # A section ends at the next line that starts with '[' (any TOML table)
    section_starts = [
        i for i, line in enumerate(lines) if line.lstrip().startswith("[")
    ]
    fixed: List[Tuple[str, Optional[str], int, int]] = []
    for start, sid, nested in headers:
        end = len(lines)
        for s in section_starts:
            if s > start:
                end = s
                break
        fixed.append((sid, nested, start, end))
    return fixed


def extract_managed_toml_projection(text: str, server_id: str) -> Optional[str]:
    """Return concatenated text of all sections for mcp_servers.<id> (+ nested)."""
    lines = text.splitlines(keepends=True)
    parts: List[str] = []
    for sid, _nested, start, end in _iter_toml_sections(text):
        if sid == server_id:
            parts.append("".join(lines[start:end]))
    if not parts:
        return None
    return "".join(parts)


def expand_managed_ids_with_aliases(managed_ids: Iterable[str]) -> List[str]:
    """Registry ids plus legacy aliases that must be stripped on apply."""
    out: List[str] = []
    seen = set()
    for mid in managed_ids:
        sid = str(mid)
        if sid not in seen:
            out.append(sid)
            seen.add(sid)
        for alias in MANAGED_ALIASES.get(sid, ()):
            if alias not in seen:
                out.append(alias)
                seen.add(alias)
    return out


def strip_managed_toml_ids(text: str, managed_ids: Iterable[str]) -> str:
    """Remove [mcp_servers.<id>] (+ nested) for managed ids and aliases."""
    managed = set(expand_managed_ids_with_aliases(managed_ids))
    lines = text.splitlines(keepends=True)
    kill = set()
    for sid, _nested, start, end in _iter_toml_sections(text):
        if sid in managed:
            for i in range(start, end):
                kill.add(i)
    kept = [line for i, line in enumerate(lines) if i not in kill]
    # Collapse excess blank lines at strip sites (max 2)
    out: List[str] = []
    blank_run = 0
    for line in kept:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                out.append(line if line.endswith("\n") else line + "\n")
        else:
            blank_run = 0
            out.append(line if line.endswith("\n") else line + "\n")
    return "".join(out)


def ids_to_strip_on_apply(
    managed: Dict[str, Dict[str, Any]],
    *,
    registry_ids: Optional[Iterable[str]] = None,
) -> List[str]:
    """Managed ids + aliases + packaged L0 seeds absent from registry."""
    strip = list(expand_managed_ids_with_aliases(managed.keys()))
    seen = set(strip)
    reg = set(str(x) for x in (registry_ids or []))
    # Always strip package L0 seeds that are not currently projected
    for pid in PACKAGE_L0_SEED_IDS:
        if pid in managed:
            continue
        if pid in reg:
            # present but disabled / not projected — still strip old block
            pass
        for candidate in expand_managed_ids_with_aliases([pid]):
            if candidate not in seen:
                strip.append(candidate)
                seen.add(candidate)
    return strip


def patch_toml_mcp_servers(
    text: str,
    managed: Dict[str, Dict[str, Any]],
    *,
    registry_ids: Optional[Iterable[str]] = None,
) -> str:
    """Replace/insert managed mcp_servers blocks; leave personal servers alone.

    ``managed`` maps id → mcpServers entry dict (same shape as .mcp.json).
    Packaged L0 seed ids not in *managed* are stripped so optional unseed
    (e.g. workforce without a venv) does not leave a dead vendor block.
    """
    base = strip_managed_toml_ids(
        text, ids_to_strip_on_apply(managed, registry_ids=registry_ids)
    )
    blocks = [
        render_toml_mcp_server_block(sid, entry, enabled=True)
        for sid, entry in sorted(managed.items())
    ]
    if not blocks:
        return base
    addition = "\n" + "\n".join(blocks)
    if base and not base.endswith("\n"):
        base += "\n"
    return base.rstrip() + "\n" + addition


def project_managed_entries(
    manifests: Sequence[Dict[str, Any]],
    workspace: Path,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        if bool(m.get("vendor_locked")) and not m.get("command") and not m.get("url"):
            continue
        out[str(m["id"])] = manifest_to_mcp_server_entry(m, workspace)
    return out


def default_grok_config_path() -> Path:
    return Path.home() / ".grok" / "config.toml"


def default_codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def apply_vendor_toml(
    config_path: Path,
    managed: Dict[str, Dict[str, Any]],
    *,
    create_if_missing: bool = False,
    registry_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Patch one vendor config.toml with managed mcp_servers blocks."""
    path = config_path.expanduser()
    if not path.is_file():
        if not create_if_missing:
            return {
                "ok": True,
                "action": "skipped",
                "path": str(path),
                "detail": "vendor config absent — not created",
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        text = ""
        action = "created"
    else:
        text = path.read_text(encoding="utf-8")
        action = "patched"
    new = patch_toml_mcp_servers(text, managed, registry_ids=registry_ids)
    if new == text:
        return {
            "ok": True,
            "action": "skipped",
            "path": str(path),
            "detail": "already in sync",
        }
    path.write_text(new, encoding="utf-8")
    return {
        "ok": True,
        "action": action,
        "path": str(path),
        "detail": "wrote managed mcp_servers for: %s"
        % (", ".join(sorted(managed.keys())) or "(none)"),
    }


def check_vendor_toml(
    config_path: Path,
    managed: Dict[str, Dict[str, Any]],
    *,
    workspace: Optional[Path] = None,
) -> Dict[str, Any]:
    """Report whether managed blocks match projection (personal servers ignored).

    pc-1151: also flag **dead absolute commands outside the workspace** (smoke
    temp dirs, old relocate paths). Missing binaries *under* the city root are
    allowed (WorkLane not installed yet / test fixtures).
    """
    path = config_path.expanduser()
    ws = workspace.expanduser().resolve() if workspace is not None else None
    result: Dict[str, Any] = {
        "ok": True,
        "path": str(path),
        "drift": False,
        "detail": "",
        "missing": [],
        "mismatched": [],
    }
    if not managed:
        result["detail"] = "no managed servers to check"
        return result
    if not path.is_file():
        result["ok"] = False
        result["drift"] = True
        result["detail"] = "vendor config missing: %s" % path
        result["missing"] = list(managed.keys())
        return result
    text = path.read_text(encoding="utf-8")
    dead_commands: List[str] = []
    for sid, entry in managed.items():
        expected = render_toml_mcp_server_block(sid, entry, enabled=True).strip()
        actual = extract_managed_toml_projection(text, sid)
        if actual is None:
            result["missing"].append(sid)
            continue
        # Compare key fields loosely: command + args presence
        if "command" in entry and str(entry["command"]) not in actual:
            result["mismatched"].append(sid)
            # still scan actual for dead outside-city paths below
        elif actual.strip() != expected and str(entry.get("command", "")) not in actual:
            result["mismatched"].append(sid)
        # Actual command path (what the vendor will exec)
        m_cmd = re.search(r'(?m)^\s*command\s*=\s*"([^"]+)"', actual)
        actual_cmd = (m_cmd.group(1).strip() if m_cmd else "") or str(
            entry.get("command") or ""
        ).strip()
        # Dead absolute command outside the city (pc-1069 / pc-1151). Requires
        # workspace so under-city missing venvs (tests / pre-install) stay green.
        if (
            ws is not None
            and actual_cmd
            and not actual_cmd.startswith("${")
            and (actual_cmd.startswith("/") or (len(actual_cmd) > 2 and actual_cmd[1] == ":"))
        ):
            cmd_path = Path(actual_cmd).expanduser()
            if not cmd_path.exists():
                outside = True
                try:
                    # resolve both sides (macOS /var → /private/var)
                    cmd_res = cmd_path.resolve()
                    ws_res = ws.resolve()
                    cmd_res.relative_to(ws_res)
                    outside = False  # under city — ok if binary not built yet
                except (ValueError, OSError):
                    try:
                        outside = not str(cmd_path.resolve()).startswith(
                            str(ws.resolve()) + os.sep
                        )
                    except OSError:
                        outside = True
                if outside:
                    dead_commands.append("%s→%s" % (sid, actual_cmd))
                    if sid not in result["mismatched"]:
                        result["mismatched"].append(sid)
    if result["missing"] or result["mismatched"] or dead_commands:
        result["ok"] = False
        result["drift"] = True
        bits = []
        if result["missing"]:
            bits.append("missing: %s" % ",".join(result["missing"]))
        if result["mismatched"]:
            bits.append("mismatched: %s" % ",".join(result["mismatched"]))
        if dead_commands:
            bits.append("dead_command: %s" % ",".join(dead_commands))
            result["dead_commands"] = dead_commands
        result["detail"] = "; ".join(bits)
    else:
        result["detail"] = "ok: managed mcp_servers match registry projection"
    return result


# ---------------------------------------------------------------------------
# apply / check / import / plant
# ---------------------------------------------------------------------------


def check_env_required(
    manifests: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Report unset env_required names (report-only; pairs pc-1061)."""
    gaps: List[Dict[str, Any]] = []
    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        req = m.get("env_required") or []
        if not isinstance(req, list):
            continue
        for name in req:
            if not isinstance(name, str) or not name.strip():
                continue
            if name not in os.environ or os.environ.get(name, "") == "":
                gaps.append(
                    {
                        "server": m.get("id"),
                        "env": name,
                        "detail": "env_required %s unset for MCP %s"
                        % (name, m.get("id")),
                    }
                )
    return gaps


# Env keys that pin WorkLane / Ticketing Protocol runtime root (engine products.py).
_RUNTIME_DIR_ENV_KEYS: Tuple[str, ...] = (
    "TICKETING_PROTOCOL_RUNTIME_DIR",
    "WORKLANE_RUNTIME_DIR",
)


def _runtime_dir_has_store(runtime_root: Path) -> bool:
    """True when *runtime_root* looks like a live multi-product WorkLane store.

    Matches engine layout (``local/config/products.json`` + ``local/data/*.db``):
    either the products overlay or at least one product ``.db`` is enough.
    """
    if (runtime_root / "config" / "products.json").is_file():
        return True
    data = runtime_root / "data"
    if not data.is_dir():
        return False
    for p in data.glob("*.db"):
        stem = p.stem.strip().lower()
        if not stem or stem.startswith("_") or stem in ("tasks", "ops_tickets"):
            continue
        return True
    return False


def check_runtime_dir_wiring(
    manifests: Sequence[Dict[str, Any]],
    workspace: Path,
) -> List[Dict[str, Any]]:
    """Flag MCP env pins at an empty WorkLane runtime root (pc-1082).

    Miswire: ``TICKETING_PROTOCOL_RUNTIME_DIR`` / ``WORKLANE_RUNTIME_DIR``
    points at a directory that exists but has no ``config/products.json`` and
    no product ``.db`` files — engine then falls back to built-in ``tradeos``
    only. Missing paths are not flagged here (WorkLane not installed yet);
    only an *empty existing* pin is empty-store wiring drift.
    """
    root = workspace.expanduser().resolve()
    findings: List[Dict[str, Any]] = []
    seen = set()  # type: set
    for m in manifests:
        if not bool(m.get("enabled", True)):
            continue
        env = m.get("env")
        if not isinstance(env, dict):
            continue
        for key in _RUNTIME_DIR_ENV_KEYS:
            raw = env.get(key)
            if raw is None or str(raw).strip() == "":
                continue
            expanded = expand_tokens(str(raw), root)
            # Skip unresolved ${VAR} host templates — not our pin to validate.
            if "${" in expanded:
                continue
            pin = Path(expanded).expanduser()
            try:
                pin_key = str(pin.resolve()) if pin.exists() else str(pin)
            except OSError:
                pin_key = str(pin)
            if pin_key in seen:
                continue
            seen.add(pin_key)
            if not pin.exists():
                continue
            if not pin.is_dir():
                findings.append(
                    {
                        "server": m.get("id"),
                        "env": key,
                        "path": pin_key,
                        "code": "MCP-RUNTIME-EMPTY",
                        "detail": (
                            "runtime pin %s=%s is not a directory — "
                            "point at worklane/worklane/local "
                            "(live multi-product store root)"
                            % (key, pin_key)
                        ),
                    }
                )
                continue
            if _runtime_dir_has_store(pin):
                continue
            findings.append(
                {
                    "server": m.get("id"),
                    "env": key,
                    "path": pin_key,
                    "code": "MCP-RUNTIME-EMPTY",
                    "detail": (
                        "empty WorkLane runtime pin %s=%s — no "
                        "config/products.json and no product .db under data/; "
                        "MCP will only know built-in tradeos. Point at "
                        "worklane/worklane/local or seed/link a live "
                        "store before first MCP boot (pc-1082)"
                        % (key, pin_key)
                    ),
                }
            )
    return findings


def sync_existing_cursor_entries(root: Path, managed: Dict[str, Any], *, apply: bool = False) -> Dict[str, Any]:
    """Reconcile existing Cursor registry entries without adding permissions.

    Unmanaged servers and unrelated preferences are preserved. A missing
    Cursor configuration is reported, never silently created.
    """
    if not should_apply_host_vendor(root):
        return {"ok": True, "detail": "not a live host workspace"}
    path = Path.home() / ".cursor" / "mcp.json"
    if not path.is_file():
        return {"ok": True, "detail": "not configured"}
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        servers = body.get("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("mcpServers must be an object")
        drift = [key for key in managed if key in servers and servers[key] != managed[key]]
        if apply and drift:
            for key in drift:
                servers[key] = managed[key]
            path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        return {"ok": not drift or apply, "detail": "updated existing entries" if apply and drift else ("existing entries drift" if drift else "existing entries match"), "entries": drift, "action": "updated" if apply and drift else "checked"}
    except (OSError, ValueError, AttributeError) as exc:
        return {"ok": False, "detail": "Cursor configuration unreadable: %s" % type(exc).__name__}


def check_drift(
    workspace: Path,
    *,
    grok_config: Optional[Path] = None,
    codex_config: Optional[Path] = None,
    check_vendors: bool = False,
) -> Dict[str, Any]:
    """Return ok/drift for workspace .mcp.json (+ optional vendor homes)."""
    root = workspace.expanduser().resolve()
    result: Dict[str, Any] = {
        "ok": False,
        "workspace": str(root),
        "registry": str(registry_dir(root)),
        "mcp_json": str(mcp_json_path(root)),
        "drift": True,
        "detail": "",
        "codes": [],
        "env_gaps": [],
    }
    reg = registry_dir(root)
    if not reg.is_dir():
        result["detail"] = "MCP registry missing: %s" % reg
        result["codes"].append("MCP-REGISTRY-MISSING")
        return result

    try:
        manifests = load_registry(root)
        expected = render_mcp_json_body(manifests, root)
    except (FileNotFoundError, ValueError) as exc:
        result["detail"] = str(exc)
        result["codes"].append("MCP-REGISTRY-MISSING")
        return result

    path = mcp_json_path(root)
    if not path.is_file():
        result["detail"] = "missing generated mirror: %s" % path
        result["codes"].append("MCP-MIRROR-DRIFT")
        return result
    try:
        on_disk = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["detail"] = ".mcp.json is not valid JSON: %s" % exc
        result["codes"].append("MCP-MIRROR-DRIFT")
        return result
    if not isinstance(on_disk, dict):
        result["detail"] = ".mcp.json root must be an object"
        result["codes"].append("MCP-MIRROR-DRIFT")
        return result

    bp = on_disk.get("_bp")
    if not isinstance(bp, dict) or bp.get("generated_by") != GENERATED_BY:
        result["detail"] = (
            "hand-authored or foreign .mcp.json (missing _bp.generated_by=%s) "
            "— run mcp_sync import then apply"
            % GENERATED_BY
        )
        result["codes"].append("MCP-MIRROR-DRIFT")
        return result

    if canonicalize_mcp_json(on_disk) != canonicalize_mcp_json(expected):
        result["detail"] = (
            "drift: .mcp.json does not match .agents/mcp registry — "
            "run mcp_sync apply (do not hand-edit the generated mirror)"
        )
        result["codes"].append("MCP-MIRROR-DRIFT")
        return result

    env_gaps = check_env_required(manifests)
    result["env_gaps"] = env_gaps
    # env gaps do not fail mirror check (report alongside); strong fail is pc-1061

    cmd_missing = check_stdio_commands(manifests, root)
    result["command_missing"] = cmd_missing
    if cmd_missing:
        result["ok"] = False
        result["drift"] = True
        result["codes"].append(MCP_COMMAND_MISSING)
        result["detail"] = cmd_missing[0]["detail"]
        return result

    runtime_empty = check_runtime_dir_wiring(manifests, root)
    result["runtime_empty"] = runtime_empty
    if runtime_empty:
        result["ok"] = False
        result["drift"] = True
        result["codes"].append("MCP-RUNTIME-EMPTY")
        result["detail"] = runtime_empty[0]["detail"]
        return result

    vendor_notes: List[str] = []
    if check_vendors:
        managed = project_managed_entries(manifests, root)
        for label, cpath in (
            ("grok", grok_config or default_grok_config_path()),
            ("codex", codex_config or default_codex_config_path()),
        ):
            if not cpath.expanduser().is_file():
                continue
            vchk = check_vendor_toml(cpath, managed, workspace=root)
            if not vchk.get("ok"):
                result["ok"] = False
                result["drift"] = True
                result["codes"].append("MCP-MIRROR-DRIFT")
                result["detail"] = "%s vendor drift: %s" % (label, vchk.get("detail"))
                result["vendor"] = result.get("vendor") or {}
                result["vendor"][label] = vchk
                return result
            vendor_notes.append("%s ok" % label)
        cursor = sync_existing_cursor_entries(root, managed)
        result["cursor"] = cursor
        if not cursor["ok"]:
            result["codes"].append("MCP-MIRROR-DRIFT")
            result["detail"] = "cursor vendor drift: " + cursor["detail"]
            return result
        vendor_notes.append("cursor: " + cursor["detail"])

    result["ok"] = True
    result["drift"] = False
    detail = "ok: .mcp.json matches MCP registry"
    if vendor_notes:
        detail += " (%s)" % ", ".join(vendor_notes)
    if env_gaps:
        detail += "; env_required gaps: %d (report-only)" % len(env_gaps)
    result["detail"] = detail
    return result


def should_apply_host_vendor(
    root: Path, *, config_override: Optional[Path] = None
) -> bool:
    """Whether apply may patch a Grok/Codex config.

    Explicit ``grok_config`` / ``codex_config`` always writes (tests and
    directed CLI). Default host homes (``~/.grok``, ``~/.codex``) only
    when *root* is the live city — temp/sandbox apply otherwise poisons
    agent MCP with dead ``/var/folders/.../T/tmp*`` commands (pc-1294).
    """
    if config_override is not None:
        return True
    return _is_live_workspace_root(root)


def _skip_non_live_host_vendor(label: str, path: Path) -> Dict[str, Any]:
    return {
        "ok": True,
        "action": "skipped",
        "path": str(path),
        "detail": (
            "non-live workspace — host %s config not patched "
            "(pass %s_config to override)" % (label, label)
        ),
    }


def apply_mcp(
    workspace: Path,
    *,
    touch_vendors: bool = True,
    grok_config: Optional[Path] = None,
    codex_config: Optional[Path] = None,
    create_vendor_configs: bool = False,
) -> Dict[str, Any]:
    """Write workspace .mcp.json from registry; optionally patch vendor homes.

    Host ``~/.grok`` / ``~/.codex`` are patched only when *workspace* is the
    live city (same gate as ``check``). Pass ``grok_config`` / ``codex_config``
    to write a specific file from a temp city (tests). pc-1294.
    """
    root = workspace.expanduser().resolve()
    manifests = load_registry(root)
    body = render_mcp_json_body(manifests, root)
    path = mcp_json_path(root)
    path.write_text(dumps_mcp_json(body), encoding="utf-8")
    out: Dict[str, Any] = {
        "ok": True,
        "action": "wrote",
        "path": str(path),
        "servers": sorted(body.get("mcpServers", {}).keys()),
        "detail": "generated .mcp.json from MCP registry",
        "vendors": {},
    }
    if touch_vendors:
        managed = project_managed_entries(manifests, root)
        reg_ids = [str(m.get("id")) for m in manifests if m.get("id")]
        for label, override, default_fn in (
            ("grok", grok_config, default_grok_config_path),
            ("codex", codex_config, default_codex_config_path),
        ):
            if should_apply_host_vendor(root, config_override=override):
                out["vendors"][label] = apply_vendor_toml(
                    override or default_fn(),
                    managed,
                    create_if_missing=create_vendor_configs,
                    registry_ids=reg_ids,
                )
            else:
                out["vendors"][label] = _skip_non_live_host_vendor(
                    label, default_fn()
                )
        out["vendors"]["cursor"] = sync_existing_cursor_entries(root, managed, apply=True)
        if not out["vendors"]["cursor"]["ok"]:
            out["ok"] = False
    return out


def _server_entry_to_manifest(
    server_id: str,
    entry: Dict[str, Any],
    workspace: Path,
) -> Dict[str, Any]:
    """Best-effort import of one mcpServers entry → registry manifest."""
    root = workspace_root_norm(workspace)
    command = entry.get("command")
    args = entry.get("args") if isinstance(entry.get("args"), list) else []
    env_in = entry.get("env") if isinstance(entry.get("env"), dict) else {}
    env_out: Dict[str, str] = {}
    for k, v in env_in.items():
        s = str(v)
        if root and root in s:
            s = s.replace(root, "{{WORKSPACE_ROOT}}")
        env_out[str(k)] = s
    cmd_s = str(command) if command else ""
    if root and root in cmd_s:
        cmd_s = cmd_s.replace(root, "{{WORKSPACE_ROOT}}")
    args_out = []
    for a in args:
        s = str(a)
        if root and root in s:
            s = s.replace(root, "{{WORKSPACE_ROOT}}")
        args_out.append(s)
    man: Dict[str, Any] = {
        "id": server_id,
        "description": "Imported MCP server %s (mcp_sync import)" % server_id,
        "transport": "stdio" if cmd_s else "http",
        "capability": "mutating",
        "risk": "imported — review capability/risk before trusting headless use",
        "seats": ["*"],
        "level": "L0",
        "vendor_locked": False,
        "enabled": True,
        "env_required": [],
        "notes": "Imported from existing vendor config; review and tighten fields.",
    }
    if cmd_s:
        man["command"] = cmd_s
        man["args"] = args_out
    if entry.get("url"):
        man["transport"] = "http"
        man["url"] = str(entry["url"])
    if env_out:
        man["env"] = env_out
    return man


def _normalize_import_id(server_id: str) -> str:
    """Map legacy vendor ids onto registry ids (ticketingprotocol → worklane)."""
    sid = str(server_id).strip()
    for canonical, aliases in MANAGED_ALIASES.items():
        if sid == canonical or sid in aliases:
            return canonical
    return sid


def import_from_mcp_json(
    workspace: Path,
    *,
    force: bool = False,
    source: Optional[Path] = None,
) -> Dict[str, Any]:
    """Seed registry manifests from an existing workspace .mcp.json.

    Known L0 ids (worklane, and ticketingprotocol alias) prefer the packaged
    design-canonical template when present; other servers get best-effort import.
    """
    root = workspace.expanduser().resolve()
    src = (source or mcp_json_path(root)).expanduser().resolve()
    if not src.is_file():
        return {
            "ok": False,
            "action": "error",
            "detail": "no .mcp.json to import: %s" % src,
        }
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "action": "error", "detail": "bad JSON: %s" % exc}
    if not isinstance(data, dict):
        return {"ok": False, "action": "error", "detail": ".mcp.json root must be object"}
    servers = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {}
    if not servers:
        return {
            "ok": False,
            "action": "error",
            "detail": "no mcpServers entries to import",
        }
    reg = registry_dir(root)
    reg.mkdir(parents=True, exist_ok=True)
    imported: List[str] = []
    skipped: List[str] = []
    for raw_id, entry in servers.items():
        if not isinstance(entry, dict):
            skipped.append("%s (not an object)" % raw_id)
            continue
        sid = _normalize_import_id(str(raw_id))
        dest_dir = reg / sid
        dest = dest_dir / MANIFEST_NAME
        if dest.is_file() and not force:
            skipped.append(sid)
            continue
        # Prefer design-canonical L0 template when we know the id
        man = _load_seed_template(sid)
        if man is None:
            man = _server_entry_to_manifest(sid, entry, root)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        imported.append(sid)
    return {
        "ok": True,
        "action": "imported",
        "imported": imported,
        "skipped": skipped,
        "path": str(reg),
        "detail": "imported %d server(s) into registry" % len(imported),
    }


_DEFAULT_README = """# City MCP registry (BYO-MCP)

**Ticket:** pc-1078 · **Design:** `docs/research/byo-mcp-library-design-2026-08.md`

MCP server definitions are **city-owned**, not per-vendor. Edit manifests here;
regenerate vendor mirrors. Do **not** hand-author workspace `.mcp.json`.

## Placement

| Path | Role |
|---|---|
| `.agents/mcp/<id>/manifest.json` | **SoT** — transport, command/args or url, env **names**, capability/risk |
| `.mcp.json` | **Generated** Claude/Cursor mirror (`_bp.generated_by=mcp_sync`) |
| `~/.grok/config.toml` `[mcp_servers.<id>]` | **Managed patch** — registry ids only |
| `~/.codex/config.toml` `[mcp_servers.<id>]` | **Managed patch** — personal servers left alone |
| Host env / keychain | **Secrets** — never commit values; list names in `env_required` |
| `.agents/secrets/inventory.json` | **Lifecycle paper** (pc-1061) — expiry/provenance; never values |

## Commands

```bash
bash scripts/mcp_sync.sh              # apply — generate/patch mirrors
bash scripts/mcp_sync.sh --check      # exit 1 on drift
bash scripts/mcp_sync.sh --list       # inventory registry
bash scripts/mcp_sync.sh import       # seed registry from existing .mcp.json
bash scripts/mcp_sync.sh plant        # plant empty shelf + script

# Host secrets check (pc-1061)
bash scripts/check_mcp_secrets.sh              # exit 1 on missing/expired
bash scripts/check_mcp_secrets.sh --gold       # + For You when gaps
```

## Edit rules

1. Add or edit `.agents/mcp/<id>/manifest.json`.
2. Provision any `env_required` names on the host (You); optional lifecycle
   row in `.agents/secrets/inventory.json`.
3. Run `bash scripts/mcp_sync.sh` then `bash scripts/check_mcp_secrets.sh`.
4. Commit the registry SoT; generated `.mcp.json` is city-tree when present.
"""


def _load_seed_template(server_id: str) -> Optional[Dict[str, Any]]:
    """Load packaged canonical L0 manifest for *server_id* (pc-1079)."""
    tdir = _templates_dir()
    path = tdir / "agents" / "mcp" / server_id / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    data = dict(data)
    data["id"] = server_id
    return data


def _write_manifest_file(
    workspace: Path,
    man: Dict[str, Any],
    *,
    force: bool = False,
) -> Tuple[str, str]:
    """Write one registry manifest. Returns (action, rel_path)."""
    sid = str(man["id"]).strip()
    dest_dir = registry_dir(workspace) / sid
    dest = dest_dir / MANIFEST_NAME
    rel = str(REGISTRY_REL / sid / MANIFEST_NAME).replace("\\", "/")
    if dest.is_file() and not force:
        return "skipped", rel
    errs = validate_manifest(man, path=dest)
    if errs:
        raise ValueError("; ".join(errs))
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "wrote", rel


def worklane_present(workspace: Path) -> bool:
    """Heuristic: WorkLane is part of this city kit (folder and/or MCP package)."""
    root = workspace.expanduser().resolve()
    wl = root / "worklane"
    if wl.is_dir() and (
        (wl / ".venv" / "bin" / "python").exists()
        or (wl / "ticketingprotocol").is_dir()
        or (wl / "pyproject.toml").is_file()
    ):
        return True
    # Portable / pip install: module on path is enough for a seed intent
    return False


def workforce_seedable(workspace: Path) -> bool:
    """Optional workforce L0: package + runnable interpreter must both exist.

    Ticket law (pc-1079): seed only when WF MCP is stable enough — a module
    tree without ``.venv/bin/python`` is not stable for headless projection.
    """
    root = workspace.expanduser().resolve()
    wf = root / "workforce"
    if not wf.is_dir():
        return False
    if not (wf / "workforce" / "mcp" / "__main__.py").is_file() and not (
        wf / "workforce" / "mcp"
    ).is_dir():
        return False
    venv_py = wf / ".venv" / "bin" / "python"
    return venv_py.exists() or venv_py.is_symlink()


def seed_l0_mcp_manifests(
    workspace: Path,
    *,
    force: bool = False,
    include_workforce: Optional[bool] = None,
    include_worklane: bool = True,
) -> Dict[str, Any]:
    """Seed design-canonical L0 manifests (pc-1079).

    * **worklane** — always seeded when *include_worklane* (default True).
      Uses packaged template (bottle ``python3 -m worklane.mcp`` +
      ``.protocolcity/worklane`` runtime). Existing plants are rewritten
      without *force* when the command path is dead or still teaches
      ``ticketingprotocol.mcp`` (pc-1425 / GH #33).
    * **workforce** — optional. Default: seed only when ``workforce_seedable``.
      Pass ``include_workforce=True/False`` to force.

    Does not touch vendor mirrors — call ``apply_mcp`` after seed.
    """
    root = workspace.expanduser().resolve()
    reg = registry_dir(root)
    reg.mkdir(parents=True, exist_ok=True)

    seeded: List[str] = []
    skipped: List[str] = []
    notes: List[str] = []

    if include_worklane:
        man = _load_seed_template("worklane")
        if man is None:
            notes.append("worklane template missing from package")
        else:
            dest = registry_dir(root) / "worklane" / MANIFEST_NAME
            heal = False
            if dest.is_file() and not force:
                try:
                    existing = load_manifest(dest)
                    heal = worklane_manifest_needs_heal(existing, root)
                except (ValueError, OSError, UnicodeDecodeError):
                    heal = True
            action, rel = _write_manifest_file(
                root, man, force=force or heal
            )
            (seeded if action == "wrote" else skipped).append(rel)
            if heal and action == "wrote":
                notes.append(
                    "healed dead WorkLane MCP command → bottle "
                    "python3 -m worklane.mcp (pc-1425 / GH #33)"
                )
            if not worklane_present(root):
                notes.append(
                    "worklane manifest seeded (template); worklane/ folder "
                    "not detected — install WorkLane before headless use"
                )

    do_wf = include_workforce
    if do_wf is None:
        do_wf = workforce_seedable(root)
    if do_wf:
        man = _load_seed_template("workforce")
        if man is None:
            notes.append("workforce template missing from package")
        else:
            action, rel = _write_manifest_file(root, man, force=force)
            (seeded if action == "wrote" else skipped).append(rel)
    else:
        notes.append(
            "workforce not seeded (optional L0; enable when WF MCP is stable "
            "and workforce/ is present — seed_l0 include_workforce=True)"
        )

    return {
        "ok": True,
        "action": "seeded",
        "seeded": seeded,
        "skipped": skipped,
        "notes": notes,
        "workspace": str(root),
        "detail": "seeded %d L0 manifest(s)" % len(seeded),
    }


def migrate_live_mcp(
    workspace: Path,
    *,
    force: bool = False,
    touch_vendors: bool = True,
    grok_config: Optional[Path] = None,
    codex_config: Optional[Path] = None,
    include_workforce: Optional[bool] = None,
) -> Dict[str, Any]:
    """One-shot host migration (design §10): plant → import → seed L0 → apply.

    Import preserves any extra hand-authored servers; seed upgrades worklane
    (and optional workforce) to design-canonical tokenized manifests.
    """
    root = workspace.expanduser().resolve()
    steps: Dict[str, Any] = {}
    steps["plant"] = plant_mcp_kit(root, force=False, write_mcp_json=False, seed_l0=False)
    steps["import"] = import_from_mcp_json(root, force=False)
    # Always upgrade L0 ids to design-canonical (tokens + field law) on migrate.
    steps["seed"] = seed_l0_mcp_manifests(
        root,
        force=True,
        include_workforce=include_workforce,
        include_worklane=True,
    )
    try:
        steps["apply"] = apply_mcp(
            root,
            touch_vendors=touch_vendors,
            grok_config=grok_config,
            codex_config=codex_config,
        )
        steps["check"] = check_drift(
            root,
            grok_config=grok_config,
            codex_config=codex_config,
            check_vendors=resolve_check_vendors(
                root,
                check_vendors=bool(grok_config or codex_config),
                no_vendors=not touch_vendors,
            ),
        )
    except (FileNotFoundError, ValueError) as exc:
        return {
            "ok": False,
            "action": "migrate",
            "steps": steps,
            "detail": str(exc),
            "workspace": str(root),
        }
    ok = bool(steps["apply"].get("ok")) and bool(steps["check"].get("ok"))
    return {
        "ok": ok,
        "action": "migrate",
        "steps": steps,
        "workspace": str(root),
        "detail": (
            "migrated live MCP → registry SoT + regenerated mirrors"
            if ok
            else "migrate completed with drift/errors — see steps.check"
        ),
    }


def plant_mcp_kit(
    workspace: Path,
    *,
    force: bool = False,
    write_mcp_json: bool = False,
    seed_l0: bool = True,
    include_workforce: Optional[bool] = None,
) -> Dict[str, Any]:
    """Plant MCP registry shelf + README + mcp_sync.sh script.

    When *seed_l0* (default True), also seeds the design-canonical worklane
    manifest (and optional workforce when seedable) — pc-1079.
    """
    root = workspace.expanduser().resolve()
    tdir = _templates_dir()
    planted: List[str] = []
    skipped: List[str] = []

    reg = registry_dir(root)
    reg.mkdir(parents=True, exist_ok=True)
    if not any(reg.iterdir()) or force:
        planted.append(str(REGISTRY_REL).replace("\\", "/") + "/")
    else:
        skipped.append(str(REGISTRY_REL).replace("\\", "/") + "/")

    readme_dst = reg / "README.md"
    readme_src = tdir / "agents" / "mcp" / "README.md"
    if not readme_dst.exists() or force:
        if readme_src.is_file():
            shutil.copy2(readme_src, readme_dst)
        else:
            readme_dst.write_text(_DEFAULT_README, encoding="utf-8")
        planted.append(str(REGISTRY_REL / "README.md").replace("\\", "/"))
    else:
        skipped.append(str(REGISTRY_REL / "README.md").replace("\\", "/"))

    seed_info: Optional[Dict[str, Any]] = None
    if seed_l0:
        seed_info = seed_l0_mcp_manifests(
            root,
            force=force,
            include_workforce=include_workforce,
            include_worklane=True,
        )
        for rel in seed_info.get("seeded") or []:
            planted.append(rel)
        for rel in seed_info.get("skipped") or []:
            skipped.append(rel)

    # Script plant
    scripts_dst = root / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    name = "mcp_sync.sh"
    dst = scripts_dst / name
    pc_script = root / "ProtocolCity" / "scripts" / name
    monorepo_script = _repo_root() / "scripts" / name
    src = tdir / "scripts" / name
    if not src.is_file() and monorepo_script.is_file():
        src = monorepo_script

    if (
        pc_script.is_file()
        and not pc_script.is_symlink()
        and root.name != "ProtocolCity"
    ):
        rel = os.path.relpath(pc_script, scripts_dst)
        if dst.is_symlink() and os.readlink(str(dst)) == rel and not force:
            skipped.append("scripts/%s → ProtocolCity (mirror)" % name)
        else:
            if dst.exists() and not dst.is_symlink() and not force:
                skipped.append("scripts/%s (independent copy)" % name)
            else:
                if dst.is_symlink() or dst.is_file():
                    dst.unlink()
                try:
                    os.symlink(rel, dst)
                    planted.append("scripts/%s → %s" % (name, rel))
                except OSError:
                    if src.is_file():
                        shutil.copy2(src, dst)
                        try:
                            os.chmod(dst, 0o755)
                        except OSError:
                            pass
                        planted.append("scripts/%s" % name)
    elif not dst.exists() or force:
        if src.is_file():
            shutil.copy2(src, dst)
            try:
                os.chmod(dst, 0o755)
            except OSError:
                pass
            planted.append("scripts/%s" % name)
        elif monorepo_script.is_file():
            shutil.copy2(monorepo_script, dst)
            try:
                os.chmod(dst, 0o755)
            except OSError:
                pass
            planted.append("scripts/%s" % name)
        else:
            skipped.append("scripts/%s (template missing)" % name)
    else:
        skipped.append("scripts/%s" % name)

    mcp_action = "skipped"
    if write_mcp_json:
        # Only write when at least one manifest exists, or force empty generated
        try:
            if list_registry_ids(root) or force:
                apply_mcp(root, touch_vendors=False)
                mcp_action = "wrote"
                planted.append(".mcp.json")
            else:
                mcp_action = "skipped_empty_registry"
        except (FileNotFoundError, ValueError) as exc:
            mcp_action = "error: %s" % exc

    out: Dict[str, Any] = {
        "ok": True,
        "planted": planted,
        "skipped": skipped,
        "mcp_json_action": mcp_action,
        "workspace": str(root),
    }
    if seed_info is not None:
        out["seed"] = seed_info
    return out


def resolve_check_vendors(
    root: Path,
    *,
    check_vendors: bool = False,
    no_vendors: bool = False,
) -> bool:
    """Whether ``check`` should verify Grok/Codex managed blocks.

    Live workspace defaults on (same as doctor). ``--no-vendors`` wins.
    Temp cities stay off unless ``--check-vendors``.
    """
    if no_vendors:
        return False
    if check_vendors:
        return True
    return _is_live_workspace_root(root)


def _is_live_workspace_root(root: Path) -> bool:
    """True when *root* is the host's active city (service.json).

    Unit tests use temp cities; those must not be compared against — or
    written into — the developer's real ``~/.grok`` / ``~/.codex`` managed
    blocks (pc-1294: apply now shares this gate with check).
    """
    try:
        svc = Path.home() / ".protocolcity" / "service.json"
        if not svc.is_file():
            return False
        data = json.loads(svc.read_text(encoding="utf-8"))
        live = Path(str(data.get("root") or "")).expanduser().resolve()
        return bool(live.is_dir() and live == root.resolve())
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False


def diagnose_mcp_findings(
    workspace: Path,
    *,
    check_vendors: Optional[bool] = None,
    grok_config: Optional[Path] = None,
    codex_config: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Doctor findings: MCP-REGISTRY-MISSING / MCP-MIRROR-DRIFT /
    MCP-COMMAND-MISSING / MCP-RUNTIME-EMPTY.

    pc-1151: on the **live** workspace root, include Grok/Codex managed-block
    drift so doctor is not green when only project ``.mcp.json`` matches while
    vendor homes still point at dead temp paths (pc-1069 residual / pc-1150).
    Isolated temp cities (tests) skip vendor homes unless *check_vendors* is
    forced True (with optional temp config paths).
    """
    root = workspace.expanduser().resolve()
    findings: List[Dict[str, Any]] = []
    reg = registry_dir(root)
    if not reg.is_dir():
        findings.append(
            {
                "level": "L0",
                "code": "MCP-REGISTRY-MISSING",
                "path": str(reg),
                "status": "weak",
                "detail": (
                    "city MCP registry shelf missing (.agents/mcp/) — "
                    "plant with `bash scripts/mcp_sync.sh plant` then "
                    "import/seed manifests (pc-1078 / pc-1079)"
                ),
                "fixable": True,
            }
        )
        return findings

    if check_vendors is None:
        check_vendors = _is_live_workspace_root(root)

    chk = check_drift(
        root,
        check_vendors=bool(check_vendors),
        grok_config=grok_config,
        codex_config=codex_config,
    )
    if not chk.get("ok"):
        codes = chk.get("codes") or ["MCP-MIRROR-DRIFT"]
        # Prefer vendor config path when detail names grok/codex drift
        detail = str(chk.get("detail") or "MCP mirror drift")
        path_str = str(mcp_json_path(root))
        low = detail.lower()
        if low.startswith("grok "):
            path_str = str(grok_config or default_grok_config_path())
        elif low.startswith("codex "):
            path_str = str(codex_config or default_codex_config_path())
        for code in codes:
            code_s = str(code)
            finding_path = path_str
            status = "weak"
            fix_hint = (
                " — fix: `bash scripts/mcp_sync.sh apply` "
                "(or doctor --fix; projects + Grok/Codex mirrors)"
            )
            if code_s == MCP_COMMAND_MISSING:
                status = "missing"
                finding_path = str(
                    registry_dir(root) / "worklane" / MANIFEST_NAME
                )
                fix_hint = (
                    " — fix: `blueprint doctor --fix` (rewrites a dead "
                    "WorkLane sibling-checkout plant to python3 -m "
                    "worklane.mcp) or `bash scripts/mcp_sync.sh seed` "
                    "then apply"
                )
            findings.append(
                {
                    "level": "L0",
                    "code": code_s,
                    "path": finding_path,
                    "status": status,
                    "detail": detail + fix_hint,
                    "fixable": True,
                }
            )
    else:
        findings.append(
            {
                "level": "L0",
                "code": "MCP-REGISTRY",
                "path": str(reg),
                "status": "ok",
                "detail": chk.get("detail")
                or "MCP registry + .mcp.json + vendor mirrors in sync",
                "fixable": False,
            }
        )
    for gap in chk.get("env_gaps") or []:
        findings.append(
            {
                "level": "L0",
                "code": "MCP-ENV-MISSING",
                "path": str(reg / str(gap.get("server") or "") / MANIFEST_NAME),
                "status": "weak",
                "detail": gap.get("detail")
                or "env_required unset (provision on host; pc-1061 inventory)",
                "fixable": False,
            }
        )
    return findings


def list_registry_summary(workspace: Path) -> Dict[str, Any]:
    root = workspace.expanduser().resolve()
    reg = registry_dir(root)
    if not reg.is_dir():
        return {
            "ok": False,
            "workspace": str(root),
            "detail": "registry missing: %s" % reg,
            "entries": [],
        }
    entries: List[Dict[str, Any]] = []
    try:
        for m in load_registry(root):
            entries.append(
                {
                    "id": m.get("id"),
                    "enabled": bool(m.get("enabled", True)),
                    "transport": m.get("transport"),
                    "level": m.get("level"),
                    "vendor_locked": bool(m.get("vendor_locked")),
                    "capability": m.get("capability"),
                    "description": m.get("description"),
                }
            )
    except ValueError as exc:
        return {
            "ok": False,
            "workspace": str(root),
            "detail": str(exc),
            "entries": entries,
        }
    return {
        "ok": True,
        "workspace": str(root),
        "registry": str(reg),
        "count": len(entries),
        "entries": entries,
        "detail": "%d registry entr%s" % (len(entries), "y" if len(entries) == 1 else "ies"),
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
        prog="mcp_sync",
        description=(
            "Generate workspace .mcp.json (+ optional Grok/Codex mcp_servers) "
            "from .agents/mcp/<id>/manifest.json (pc-1078)."
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="apply",
        choices=("apply", "check", "import", "plant", "list", "show", "seed", "migrate"),
        help=(
            "apply (default) | check | import | plant | list | show | "
            "seed (L0 worklane) | migrate (import+seed+apply)"
        ),
    )
    parser.add_argument(
        "--workspace",
        default="",
        help="workspace root (default: WORKSPACE_ROOT or cwd walk)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing manifests when importing/planting",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output",
    )
    parser.add_argument(
        "--no-vendors",
        action="store_true",
        help="do not read or patch ~/.grok / ~/.codex (apply and check)",
    )
    parser.add_argument(
        "--check-vendors",
        action="store_true",
        help="check: force Grok/Codex vendor-home verify (already default on the live workspace)",
    )
    parser.add_argument(
        "--grok-config",
        default="",
        help="override path to Grok config.toml (tests / non-default home)",
    )
    parser.add_argument(
        "--codex-config",
        default="",
        help="override path to Codex config.toml",
    )
    parser.add_argument(
        "--write-mcp-json",
        action="store_true",
        help="plant: also write .mcp.json when registry has entries",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = _resolve_workspace(args.workspace)
    grok = Path(args.grok_config) if args.grok_config else None
    codex = Path(args.codex_config) if args.codex_config else None
    cmd = args.command
    out: Dict[str, Any]
    exit_code = 0

    if cmd == "check":
        out = check_drift(
            root,
            grok_config=grok,
            codex_config=codex,
            check_vendors=resolve_check_vendors(
                root,
                check_vendors=bool(args.check_vendors),
                no_vendors=bool(args.no_vendors),
            ),
        )
        if not out.get("ok"):
            exit_code = 1
    elif cmd == "import":
        out = import_from_mcp_json(root, force=args.force)
        if not out.get("ok"):
            exit_code = 1
    elif cmd == "seed":
        out = seed_l0_mcp_manifests(root, force=args.force)
        if not out.get("ok"):
            exit_code = 1
    elif cmd == "migrate":
        out = migrate_live_mcp(
            root,
            force=args.force,
            touch_vendors=not args.no_vendors,
            grok_config=grok,
            codex_config=codex,
        )
        if not out.get("ok"):
            exit_code = 1
    elif cmd == "plant":
        out = plant_mcp_kit(
            root, force=args.force, write_mcp_json=bool(args.write_mcp_json)
        )
    elif cmd == "list":
        out = list_registry_summary(root)
        if not out.get("ok"):
            exit_code = 1
    elif cmd == "show":
        try:
            manifests = load_registry(root)
            out = {
                "ok": True,
                "expected_mcp_json": render_mcp_json_body(manifests, root),
                "entries": [m.get("id") for m in manifests],
            }
        except (FileNotFoundError, ValueError) as exc:
            out = {"ok": False, "detail": str(exc)}
            exit_code = 1
    else:  # apply
        try:
            out = apply_mcp(
                root,
                touch_vendors=not args.no_vendors,
                grok_config=grok,
                codex_config=codex,
            )
            chk = check_drift(
                root,
                grok_config=grok,
                codex_config=codex,
                check_vendors=resolve_check_vendors(
                    root,
                    check_vendors=bool(grok or codex),
                    no_vendors=bool(args.no_vendors),
                ),
            )
            out["check"] = chk
            if not chk.get("ok"):
                exit_code = 1
                out["ok"] = False
        except (FileNotFoundError, ValueError) as exc:
            out = {"ok": False, "detail": str(exc)}
            exit_code = 1

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        if cmd == "list" and out.get("ok"):
            print("MCP registry @ %s (%s)" % (out.get("registry"), out.get("detail")))
            for e in out.get("entries") or []:
                flags = []
                if not e.get("enabled"):
                    flags.append("disabled")
                if e.get("vendor_locked"):
                    flags.append("vendor-locked")
                flag_s = (" [%s]" % ", ".join(flags)) if flags else ""
                print(
                    "  - %s (%s, %s)%s — %s"
                    % (
                        e.get("id"),
                        e.get("transport"),
                        e.get("level"),
                        flag_s,
                        e.get("description") or "",
                    )
                )
        elif cmd == "show" and out.get("ok"):
            print(json.dumps(out.get("expected_mcp_json"), indent=2))
        else:
            detail = out.get("detail") or out.get("action") or ""
            status = "ok" if out.get("ok") else "FAIL"
            print("%s: %s" % (status, detail))
            if out.get("path"):
                print("  path: %s" % out["path"])
            if out.get("servers"):
                print("  servers: %s" % ", ".join(out["servers"]))
            if out.get("imported"):
                print("  imported: %s" % ", ".join(out["imported"]))
            if out.get("planted"):
                for p in out["planted"]:
                    print("  planted: %s" % p)
            if out.get("codes"):
                print("  codes: %s" % ", ".join(out["codes"]))
            if out.get("drift") and not out.get("ok"):
                print("  hint: bash scripts/mcp_sync.sh apply")
            vendors = out.get("vendors") or {}
            for label, v in vendors.items():
                if isinstance(v, dict):
                    print(
                        "  %s: %s (%s)"
                        % (label, v.get("action"), v.get("detail") or v.get("path"))
                    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
