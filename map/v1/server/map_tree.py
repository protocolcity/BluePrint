"""FS/git binder projection for Map V1.

Contract (from ``docs/specs/MAP_V1_GAP.md``):

- ``GET /api/map/tree`` returns
  ``{binder: {path, name}, lots: [...], git: {head, dirty}}``
- ``GET /api/map/children?relPath=…`` returns
  ``{relPath, children: [...]}``
- ``GET /api/file?path=…&render=html`` returns rendered HTML for a ``.md``
  file (raw content when ``render`` != ``html``).

Everything else is out of V1 (Glass §Non-goals).
"""
from __future__ import annotations

import html
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_MD_SUFFIXES = frozenset({".md", ".markdown"})
_MANAGED_MARKER = ".blueprint"          # BluePrint's binder marker directory
_DEFAULT_HIDDEN_NAMES = frozenset({".git", ".DS_Store", ".venv", "node_modules"})


@dataclass(frozen=True)
class Lot:
    rel_path: str
    name: str
    is_dir: bool
    has_md: bool
    managed: bool
    hidden: bool

    git_state: str | None = None

    def to_json(self) -> dict:
        body = {
            "relPath": self.rel_path,
            "name": self.name,
            "isDir": self.is_dir,
            "hasMd": self.has_md,
            "managed": self.managed,
            "hidden": self.hidden,
        }
        if self.git_state:
            body["gitState"] = self.git_state
        return body


def load_binder(root: Path) -> dict:
    """Return the binder descriptor for the given root folder."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"binder root is not a directory: {root}")
    return {"path": str(root), "name": root.name}


def _dir_has_md(path: Path) -> bool:
    try:
        for entry in path.iterdir():
            if entry.is_file() and entry.suffix.lower() in _MD_SUFFIXES:
                return True
    except (OSError, PermissionError):
        return False
    return False


def _is_managed(path: Path) -> bool:
    return (path / _MANAGED_MARKER).exists()


def _git_lot_states(root: Path) -> dict[str, str]:
    """Top-level lot → dirty | untracked. Absent key means clean when git exists."""
    flags: dict[str, str] = {}
    try:
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return flags
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[-1]
        top = path.split("/")[0]
        if not top:
            continue
        if line.startswith("??"):
            flags.setdefault(top, "untracked")
        elif flags.get(top) != "untracked":
            flags[top] = "dirty"
    return flags


def _iter_top_children(
    root: Path,
    hidden_names: Iterable[str],
    git_flags: dict[str, str] | None = None,
) -> Iterable[Lot]:
    hidden_set = {n.lower() for n in hidden_names}
    flags = git_flags or {}
    git_on = bool(flags) or git_flags is not None
    for entry in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        name = entry.name
        low = name.lower()
        hidden = low in hidden_set or name.startswith(".")
        is_dir = entry.is_dir()
        has_md = False
        if is_dir:
            has_md = _dir_has_md(entry)
        else:
            has_md = entry.suffix.lower() in _MD_SUFFIXES
        git_state = None
        if git_on:
            git_state = flags.get(name, "clean")
        yield Lot(
            rel_path=name,
            name=name,
            is_dir=is_dir,
            has_md=has_md,
            managed=is_dir and _is_managed(entry),
            hidden=hidden,
            git_state=git_state,
        )


def _git_shape(root: Path) -> dict | None:
    """Best-effort git HEAD + dirty flag. Never raises — pure hint."""
    git_dir = root / ".git"
    if not git_dir.exists():
        return None
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=2,
        ).decode().strip()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=2,
        ).decode()
        return {"head": head, "dirty": bool(status.strip())}
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return {"head": None, "dirty": None}


def build_tree(root: Path, *, hidden_names: Iterable[str] | None = None) -> dict:
    """Full response body for ``GET /api/map/tree``."""
    root = Path(root).resolve()
    binder = load_binder(root)
    hidden = hidden_names if hidden_names is not None else _DEFAULT_HIDDEN_NAMES
    git = _git_shape(root)
    git_flags = _git_lot_states(root) if git else None
    lots = [lot.to_json() for lot in _iter_top_children(root, hidden, git_flags)]
    return {"binder": binder, "lots": lots, "git": git}


def _safe_join(root: Path, rel: str) -> Path:
    """Reject rel-paths that escape the binder root."""
    if rel in ("", "/"):
        return root
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError(f"unsafe relPath: {rel!r}")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"relPath escapes binder: {rel!r}") from exc
    return candidate


def children_at(root: Path, rel_path: str, *, hidden_names: Iterable[str] | None = None) -> dict:
    """Body for ``GET /api/map/children?relPath=…``."""
    root = Path(root).resolve()
    target = _safe_join(root, rel_path)
    if not target.is_dir():
        return {"relPath": rel_path, "children": []}
    hidden = hidden_names if hidden_names is not None else _DEFAULT_HIDDEN_NAMES
    hidden_set = {n.lower() for n in hidden}
    kids = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        name = entry.name
        low = name.lower()
        is_dir = entry.is_dir()
        kids.append({
            "relPath": f"{rel_path}/{name}" if rel_path else name,
            "name": name,
            "isDir": is_dir,
            "hasMd": _dir_has_md(entry) if is_dir else entry.suffix.lower() in _MD_SUFFIXES,
            "managed": is_dir and _is_managed(entry),
            "hidden": low in hidden_set or name.startswith("."),
        })
    return {"relPath": rel_path, "children": kids}


# ── Minimal markdown → HTML renderer ────────────────────────────────────────
# The V1 goal is a legible reader, not a full CommonMark implementation. We
# keep it deliberately small so downstream BluePrint can swap in its own
# renderer without touching the shell contract.

def _render_markdown(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_code = False
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("### "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if line == "":
            if in_list:
                out.append("</ul>"); in_list = False
            out.append("")
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        out.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def render_file(root: Path, rel_path: str, *, render: str = "html") -> tuple[str, str]:
    """Return (content, content_type) for a file under the binder."""
    root = Path(root).resolve()
    target = _safe_join(root, rel_path)
    if not target.is_file():
        raise FileNotFoundError(rel_path)
    text = target.read_text(encoding="utf-8", errors="replace")
    if render == "html" and target.suffix.lower() in _MD_SUFFIXES:
        return _render_markdown(text), "text/html; charset=utf-8"
    return text, "text/plain; charset=utf-8"
