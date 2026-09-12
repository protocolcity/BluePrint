#!/usr/bin/env python3
"""Tiny dogfood server for the BluePrint desk — full four-lens shell.

Serves Overview (Mission Control) + Map V1 dig + Calendar + Settings from
a single origin so every lens chip in the top nav is a real page, not a
dead pill.

Endpoints (all on the same origin):

- ``GET /``                       → Overview Mission Control
- ``GET /overview``               → same
- ``GET /map``                    → Map V1 dig (embeds/serves the map shell)
- ``GET /calendar``               → Calendar week list
- ``GET /settings``               → Settings groups

- ``GET /api/overview/agents``    (agents + cloud/remote builder links)
- ``GET /api/overview/jobs``      (jobs + Waiting · Ready · Blocked buckets)
- ``GET /api/overview/pulse``     (named heartbeats + Cellar tip + last tick)
- ``GET /api/overview/project``   (project card, ``{}`` when empty)
- ``GET /api/overview/charter``   (charter drawer, ``{}`` when empty)
- ``GET /api/calendar/events``    (local events, honest ``[]`` when empty)
- ``GET /api/settings/desk``      (binder path + desk label)

- ``GET /api/map/tree``           (requires ``--binder``)
- ``GET /api/map/children``       (requires ``--binder``)
- ``GET /api/file``               (requires ``--binder``)

Usage::

    python3 overview/v1/serve.py --port 8803 --binder ~/BluePrint

The default serve is **honest empty** (`No agents` · `No open jobs` · silent
pulse · `No events`) per ``docs/specs/OVERVIEW_INTENT.md`` §Dogfood note
and ``OVERVIEW_CALENDAR_SETTINGS.md`` §Calendar empty state.

``--binder DIR`` opts local truth in: ``<binder>/.blueprint/overview.json``
seeds Agents/Jobs/Pulse (+ Project/Charter) when present (wins). When absent,
Phase-B projectors read WorkForce roster + WorkLane SQLite (optional Desk
HTTP) under the binder — honest empty when stores are missing.
``<binder>/.blueprint/calendar.json`` seeds the Calendar. Inputs are re-read
when they change on disk — no server bounce. ``--fixture`` stays boot-pinned
(tests / demo).

``--fixture PATH`` overrides the entire overview state (tests / demo only).

``--cellar-tip`` sets the brew face — never a private ProtocolCity SHA.
Omit it and the tip is read from the local brew Cellar
(``brew list --versions blueprint``), falling back to ``DEFAULT_CELLAR_TIP``
(``OVERVIEW_MC_EXT.md`` never-lie DoD).
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# ``map/v1/`` also ships a ``server/`` package; if it lands on sys.path
# alongside ours it will shadow this file's ``server.overview_state``
# import (same package name, different files). We instead load the map
# projector by file path via importlib.util below — no path merging.
_REPO_ROOT = _HERE.parent.parent
_MAP_V1 = _REPO_ROOT / "map" / "v1"

from server.overview_state import (  # noqa: E402
    BinderOverview,
    DEFAULT_CELLAR_TIP,
    detect_cellar_tip,
    empty_state,
    load_agents,
    load_charter,
    load_desk,
    load_events,
    load_from_binder,
    load_from_fixture,
    load_jobs,
    load_project,
    load_pulse,
    next_action_from_state,
)

# Map V1 projector — imported from map/v1/server/map_tree.py. We alias the
# import so it does not collide with the overview `server/` package.
import importlib.util  # noqa: E402

_MAP_TREE_SPEC = importlib.util.spec_from_file_location(
    "_bp_map_tree", _MAP_V1 / "server" / "map_tree.py"
)
if _MAP_TREE_SPEC and _MAP_TREE_SPEC.loader:
    _map_tree = importlib.util.module_from_spec(_MAP_TREE_SPEC)
    # Register before exec so decorators (e.g. @dataclass) that look up
    # cls.__module__ in sys.modules resolve correctly.
    sys.modules[_MAP_TREE_SPEC.name] = _map_tree
    _MAP_TREE_SPEC.loader.exec_module(_map_tree)
else:  # pragma: no cover — repository layout invariant
    _map_tree = None

_OV_STATIC_DIR = _HERE / "static"
_MAP_STATIC_DIR = _MAP_V1 / "static"

_MIME_BY_SUFFIX = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _rewrite_map_html(text: str) -> str:
    """Retarget the map shell's relative asset paths to /map/…

    map/v1/static/workspace_map.html loads `./css/workspace_map.css` and
    `./js/workspace_map_app.v1.js` — from `/map` those resolve to
    `/css/…` (overview's assets). Rewriting to `/map/css/…` mounts the
    map shell cleanly alongside overview without touching the standalone
    map dogfood server.
    """
    return (
        text
        .replace('href="./css/', 'href="/map/css/')
        .replace('src="./js/', 'src="/map/js/')
    )


class Handler(BaseHTTPRequestHandler):
    state: dict = empty_state()
    binder_root: Path | None = None
    # Live binder truth for Agents / Jobs / Pulse (+ Project / Charter — one
    # file). Set when --binder is on and no --fixture override; None keeps
    # ``state`` as the boot-pinned source.
    binder_overview: BinderOverview | None = None

    def _overview_state(self) -> dict:
        """State for this request.

        With a binder and no fixture, re-read ``overview.json`` when it
        changed on disk — the contract calendar already has via
        ``load_events``. A ``--fixture`` override and a binder-less desk
        both stay boot-pinned.
        """
        src = self.binder_overview
        return self.state if src is None else src.current()

    # ── low-level helpers ──────────────────────────────────────────────
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(
        self, code: int, text: str, content_type: str = "text/plain; charset=utf-8"
    ) -> None:
        self._send_bytes(code, text.encode("utf-8"), content_type)

    def log_message(self, fmt: str, *args) -> None:  # keep output quiet
        sys.stderr.write("bp-desk %s - %s\n" % (self.address_string(), fmt % args))

    # ── router ─────────────────────────────────────────────────────────
    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        route = parsed.path

        # Overview API surface — always available.
        if route == "/api/overview/agents":
            self._send_json(200, load_agents(self._overview_state()))
            return
        if route == "/api/overview/jobs":
            st = self._overview_state()
            payload = load_jobs(st)
            nxt = next_action_from_state(st, self.binder_root)
            if nxt:
                payload["next"] = nxt
            self._send_json(200, payload)
            return
        if route == "/api/overview/pulse":
            self._send_json(200, load_pulse(self._overview_state()))
            return
        if route == "/api/overview/project":
            self._send_json(200, load_project(self._overview_state()))
            return
        if route == "/api/overview/charter":
            self._send_json(200, load_charter(self._overview_state()))
            return

        # Calendar + Settings — local desk stubs.
        if route == "/api/calendar/events":
            self._send_json(200, load_events(self.binder_root))
            return
        if route == "/api/settings/desk":
            self._send_json(200, load_desk(self.binder_root))
            return

        # Map V1 dig — same-origin mount when --binder is set. When there
        # is no binder we still 200 with an honest-empty tree so the /map
        # page can paint (no dead pill).
        if route == "/api/map/tree":
            self._send_json(200, self._map_tree_body())
            return
        if route == "/api/map/children":
            self._send_json(200, self._map_children_body(query.get("relPath", "")))
            return
        if route == "/api/file":
            self._serve_file(query.get("path", ""), query.get("render", "raw"))
            return

        # HTML pages.
        if route in ("/", "/overview", "/overview/"):
            self._serve_static(_OV_STATIC_DIR, "overview.html")
            return
        if route in ("/calendar", "/calendar/"):
            self._serve_static(_OV_STATIC_DIR, "calendar.html")
            return
        if route in ("/settings", "/settings/"):
            self._serve_static(_OV_STATIC_DIR, "settings.html")
            return
        if route in ("/map", "/map/"):
            self._serve_map_shell()
            return
        if route in ("/ticket", "/ticket/"):
            self._serve_static(_OV_STATIC_DIR, "ticket.html")
            return

        # Map static (css/js/svg under /map/…) — served from map/v1/static.
        if route.startswith("/map/"):
            self._serve_static(_MAP_STATIC_DIR, route[len("/map/"):])
            return

        # Overview static (css/js/etc under /).
        if route.startswith("/"):
            self._serve_static(_OV_STATIC_DIR, route.lstrip("/"))
            return
        self._send_text(404, "not found")

    # ── map projector — honest empty when no binder ────────────────────
    def _map_tree_body(self) -> dict:
        if self.binder_root is None or _map_tree is None:
            return {
                "binder": {"path": "", "name": ""},
                "lots": [],
                "git": None,
            }
        try:
            return _map_tree.build_tree(self.binder_root)
        except Exception as exc:  # noqa: BLE001 — surface a shape, not 500
            return {"binder": {"path": str(self.binder_root), "name": self.binder_root.name}, "lots": [], "git": None, "error": str(exc)}

    def _map_children_body(self, rel: str) -> dict:
        if self.binder_root is None or _map_tree is None:
            return {"relPath": rel, "children": []}
        try:
            return _map_tree.children_at(self.binder_root, rel)
        except ValueError:
            return {"relPath": rel, "children": []}
        except Exception:  # noqa: BLE001
            return {"relPath": rel, "children": []}

    def _serve_file(self, path: str, render: str) -> None:
        if self.binder_root is None or _map_tree is None:
            self._send_text(404, "no binder")
            return
        try:
            body, ctype = _map_tree.render_file(self.binder_root, path, render=render)
            self._send_text(200, body, ctype)
        except FileNotFoundError:
            self._send_text(404, "not found")
        except ValueError as exc:
            self._send_text(400, str(exc))

    # ── static + map shell ─────────────────────────────────────────────
    def _serve_static(self, base_dir: Path, rel: str) -> None:
        if not rel:
            self._send_text(404, "not found")
            return
        candidate = (base_dir / rel).resolve()
        try:
            candidate.relative_to(base_dir)
        except ValueError:
            self._send_text(400, "path escape")
            return
        if not candidate.is_file():
            self._send_text(404, "not found")
            return
        ctype = _MIME_BY_SUFFIX.get(candidate.suffix.lower(), "application/octet-stream")
        self._send_bytes(200, candidate.read_bytes(), ctype)

    def _serve_map_shell(self) -> None:
        shell = _MAP_STATIC_DIR / "workspace_map.html"
        if not shell.is_file():
            self._send_text(404, "map shell missing")
            return
        text = _rewrite_map_html(shell.read_text(encoding="utf-8"))
        self._send_text(200, text, "text/html; charset=utf-8")


def _resolve_cellar_tip(cellar_tip: str) -> str:
    """The brew face, resolved once at boot.

    An explicit ``--cellar-tip`` is the single voice; omitted or empty, we ask
    the local brew Cellar and fall back to ``DEFAULT_CELLAR_TIP``. Resolved
    once so a live binder re-read never shells out to brew per request.
    """
    return (cellar_tip or "").strip() or detect_cellar_tip()


def _apply_cellar_tip(state: dict, cellar_tip: str) -> dict:
    """Overlay the brew-face Cellar tip onto the loaded state.

    Never a private ProtocolCity SHA.
    """
    state["cellar_tip"] = _resolve_cellar_tip(cellar_tip)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dogfood desk server for BluePrint (four-lens)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8803)
    parser.add_argument(
        "--binder",
        type=Path,
        default=None,
        help="binder folder — enables Map dig + reads local truth from <binder>/.blueprint/",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="JSON fixture of overview state (tests / demo only — overrides --binder for Overview)",
    )
    parser.add_argument(
        "--cellar-tip",
        default="",
        help=(
            "Brew-face Cellar tip painted by /api/overview/pulse. Omit to read "
            f"it from the local brew Cellar (fallback: {DEFAULT_CELLAR_TIP!r}). "
            "Never a private ProtocolCity SHA."
        ),
    )
    args = parser.parse_args(argv)

    binder: Path | None = None
    if args.binder is not None:
        binder = args.binder.expanduser().resolve()
        if not binder.is_dir():
            print(f"bp-desk: --binder is not a directory: {binder}", file=sys.stderr)
            return 2

    tip = _resolve_cellar_tip(args.cellar_tip)
    source: BinderOverview | None = None

    if args.fixture is not None:
        try:
            state = load_from_fixture(args.fixture)
        except (FileNotFoundError, ValueError) as exc:
            print(f"bp-desk: fixture error: {exc}", file=sys.stderr)
            return 2
        print(f"bp-desk: loaded fixture {args.fixture}", file=sys.stderr)
        state["cellar_tip"] = tip
    elif binder is not None:
        # Live: each GET stats overview.json and re-parses only on change.
        source = BinderOverview(binder, cellar_tip=tip)
        state = source.current()
    else:
        state = empty_state()
        state["cellar_tip"] = tip

    Handler.state = state
    Handler.binder_overview = source
    Handler.binder_root = binder

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    where = f" · binder={binder}" if binder else ""
    print(f"bp-desk: four-lens shell on http://{args.host}:{args.port}/{where}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbp-desk: shutdown")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
