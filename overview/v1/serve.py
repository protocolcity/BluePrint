#!/usr/bin/env python3
"""Serve the current BluePrint operations application and Map from one origin.

The selected workspace supplies project stores, roster/run evidence and optional
calendar/configuration. /api/operations is the current shared projection;
/api/overview/* and fixture/Cellar options are retained compatibility paths.
Current routes and ownership are documented in docs/PRODUCT.md and ARCHITECTURE.md.

Use blueprint serve --foreground --root /path/to/workspace --port 8801.
Synthetic fixtures are for tests or explicitly labelled demonstrations.
"""
from __future__ import annotations

import argparse
import json
import queue
import re
import select
import socket
import sys
import time
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
)
from server.change_feed import ChangeFeed, HEARTBEAT_SECS  # noqa: E402

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


def _operations_shell_parts(active_page: str | None = None) -> tuple[str, str, str]:
    operations = (_OV_STATIC_DIR / "operations.html").read_text(encoding="utf-8")
    header = '<header class="bp-header">' + operations.split('<header class="bp-header">', 1)[1].split('</header>', 1)[0] + '</header>'
    nav = '<nav class="bp-nav"' + operations.split('<nav class="bp-nav"', 1)[1].split('</nav>', 1)[0] + '</nav>'
    if active_page:
        nav = nav.replace(f'data-page="{active_page}"', f'data-page="{active_page}" aria-current="page"')
    footer = '<footer class="bp-footer"><span>BluePrint · local operations</span><span id="footer-status">Connecting…</span></footer>'
    return header, nav, footer


def _inject_reader_shell(html: str, *, brand_suffix: str, back_href: str = '/work') -> str:
    header, nav, footer = _operations_shell_parts()
    skip = '<a class="bp-skip" href="#detail">Skip to content</a>'
    search = (_OV_STATIC_DIR / 'workspace-search.html').read_text(encoding='utf-8')
    brand = f'BluePrint <small>{brand_suffix}</small>'
    html = re.sub(
        r'<header class="bp-header">.*?</header>\s*<nav class="bp-nav".*?</nav>',
        skip + header + nav + search,
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(r'BluePrint <small>[^<]+</small>', brand, html, count=1)
    back_link = '<a id="reader-back" href="/work">Back</a>'
    html = html.replace('</header>', back_link + '</header>', 1)
    if '</main>' in html and footer not in html:
        html = html.replace('</main>', '</main>' + footer)
    html = html.replace(
        '</body>',
        '<script src="/js/workspace-search.js"></script>'
        '<script src="/js/reader-shell.js"></script></body>',
    )
    return html


class Handler(BaseHTTPRequestHandler):
    state: dict = empty_state()
    binder_root: Path | None = None
    # Live binder truth for Agents / Jobs / Pulse (+ Project / Charter — one
    # file). Set when --binder is on and no --fixture override; None keeps
    # ``state`` as the boot-pinned source.
    binder_overview: BinderOverview | None = None
    change_feed: ChangeFeed | None = None

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

    def do_POST(self) -> None:
        from server.work_actions import add_note, work_action
        import sqlite3
        if self.path not in ("/api/work-order/note", "/api/work-order/action", "/api/agents/dispatch", "/api/work-order/reveal"):
            self._send_json(404, {"error": "Unknown action."})
            return
        # A local browser write must originate on this exact local origin.
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        expected_port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{expected_port}", f"localhost:{expected_port}"}
        action_header = "agent-dispatch" if self.path == "/api/agents/dispatch" else ("note" if self.path.endswith("/note") else "work-order")
        if host not in allowed or origin != f"http://{host}" or self.headers.get("X-BluePrint-Action") != action_header:
            self._send_json(403, {"error": "This action must come from the local BluePrint page."})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self._send_json(415, {"error": "JSON is required."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("Invalid request size.")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Invalid action request.")
            if self.path == "/api/agents/dispatch":
                from server.agent_actions import dispatch_agent
                result = dispatch_agent(self.binder_root, payload.get("identity"))
            elif self.path.endswith('/reveal'):
                from server.work_order import reveal_reference
                result = reveal_reference(self.binder_root, payload.get('project'), payload.get('id'), payload.get('path'))
            elif self.path.endswith("/note"):
                result = add_note(self.binder_root, payload.get("project"), payload.get("id"), payload.get("body"))
            else:
                result = work_action(self.binder_root, payload.get("project"), payload.get("id"), payload.get("action"), payload.get("value"), payload.get("expected_updated_at"))
            self._send_json(200, result)
        except (ValueError, TypeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except FileNotFoundError:
            self._send_json(404, {"error": "Work order not found."})
        except (RuntimeError, OSError, sqlite3.Error) as exc:
            message = str(exc) if isinstance(exc, RuntimeError) else "Work-order source is unavailable."
            self._send_json(503, {"error": message})

    def do_HEAD(self) -> None:  # noqa: N802 — http.server contract
        """GET headers without a body (pc-1536 / GH #170 HEAD hygiene).

        The event-stream route stays open indefinitely on GET; HEAD there
        would hang a request thread forever, so refuse it explicitly.
        """
        if urlparse(self.path).path == "/api/changes":
            self.send_response(405)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        real_wfile = self.wfile

        class _HeadersOnlyWriter:
            """Pass the first write (headers) through; drop the body write."""

            def __init__(self, real):
                self._real = real
                self._sent = False

            def write(self, data):
                if not self._sent:
                    self._sent = True
                    return self._real.write(data)
                return len(data)

            def flush(self):
                self._real.flush()

        self.wfile = _HeadersOnlyWriter(real_wfile)
        try:
            self.do_GET()
        finally:
            self.wfile = real_wfile

    # ── router ─────────────────────────────────────────────────────────
    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        route = parsed.path

        if route in ("/desk", "/roster", "/workspace-map", "/tickets"):
            from server.legacy_redirect import target
            self.send_response(307)
            self.send_header("Location", target(self.path))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if route in ("/work-order", "/work-order/", "/ticket", "/ticket/"):
            self._serve_reader_page("work-order.html", brand_suffix="Work order")
            return
        if route == '/api/find':
            from server.workspace_search import find
            try:
                self._send_json(200, find(self.binder_root, query.get('q', ''), query.get('offset', 0), project=query.get('project', '')))
            except ValueError as exc:
                self._send_json(400, {'error':str(exc)})
            return
        if route == "/api/work-order":
            from server.work_order import prepare_work_order
            import sqlite3
            try:
                result = prepare_work_order(self.binder_root, query.get("project", ""), query.get("id", ""))
                from server.work_actions import assignment_options
                result['reveal_supported'] = sys.platform == 'darwin'
                result["assignment_options"] = assignment_options(self.binder_root, result["project"])
                self._send_json(200, result)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except (sqlite3.Error, OSError):
                self._send_json(503, {"error": "Work-order store is unavailable. Try again shortly."})
            return

        if route in ("/documents", "/documents/"):
            self._serve_reader_page("documents.html", brand_suffix="Project papers")
            return
        if route in ("/api/documents", "/api/document"):
            from server.documents import catalog, read_document
            try:
                result = catalog(self.binder_root, query.get("project", "")) if route == "/api/documents" else read_document(self.binder_root, query.get("project", ""), query.get("path", ""))
                self._send_json(200, result)
            except (ValueError, UnicodeError) as exc:
                self._send_json(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except OSError:
                self._send_json(503, {"error": "Project papers could not be read."})
            return
        if route == "/calendar.ics":
            from suite.api.calendar import render_vcalendar
            from datetime import date, datetime
            from urllib.parse import urlencode
            from server.operations_cache import cached_operations_snapshot
            snapshot = cached_operations_snapshot(self.binder_root)
            lane = next((s for s in snapshot["sources"] if s["name"] == "WorkLane"), {})
            if lane.get("state") != "available" or snapshot.get("truncated"):
                self._send_json(503, {"error": "Calendar cannot be exported while work-order sources are incomplete."})
                return
            events=[]
            for row in snapshot["work_dates"]:
                events.append({**row, "dtstart":date.fromisoformat(row["dtstart"]) if row["all_day"] else datetime.fromisoformat(row["dtstart"]),
                    "uid":row["product"] + "-" + row["uid"],
                    "url":"http://127.0.0.1:" + str(self.server.server_address[1]) + "/work-order?" + urlencode({"project":row["product"],"id":row["task_id"]})})
            self._send_text(200, render_vcalendar(events), "text/calendar; charset=utf-8")
            return
        if route == "/api/remote-activity":
            from server.remote_activity import remote_snapshot
            self._send_json(200, remote_snapshot(self.binder_root))
            return
        if route == "/api/timeline":
            import sqlite3
            from server.timeline import timeline_snapshot
            def _q(name: str) -> str:
                value = query.get(name, "")
                return value[0] if isinstance(value, list) else value
            try:
                self._send_json(200, timeline_snapshot(
                    self.binder_root,
                    project=_q("project"),
                    source=_q("source"),
                    actor=_q("actor"),
                    cursor=_q("cursor"),
                ))
            except (OSError, ValueError, sqlite3.Error):
                self._send_json(503, {"error": "Timeline could not be read."})
            return
        if route == "/api/identity":
            from importlib.metadata import version, PackageNotFoundError
            try:
                build = version("protocolcity-blueprint")
            except PackageNotFoundError:
                build = "Source checkout"
            self._send_json(200, {"schema": "blueprint.identity/v1", "build": build,
                "workspace": {"path": str(self.binder_root.resolve())} if self.binder_root else None})
            return
        if route == "/api/operations":
            from server.operations_cache import cached_operations_snapshot
            try:
                self._send_json(200, cached_operations_snapshot(self.binder_root))
            except Exception:
                # An uncaught snapshot error used to drop the socket with 0
                # bytes — the dogfood hang (pc-1554). Always answer.
                self._send_json(503, {"error": "Workspace sources could not be read."})
            return
        if route == "/api/changes":
            self._serve_changes()
            return
        if route in ("/activity", "/activity/"):
            location = "/delivery"
            if parsed.query:
                location += "?" + parsed.query
            self.send_response(307)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if route in ("/", "/overview", "/overview/", "/work", "/agents", "/delivery", "/delivery/", "/timeline", "/timeline/", "/projects", "/connections", "/calendar", "/calendar/", "/settings", "/settings/"):
            self._serve_static(_OV_STATIC_DIR, "operations.html")
            return

        # Overview API surface — always available.
        if route == "/api/overview/agents":
            self._send_json(200, load_agents(self._overview_state()))
            return
        if route == "/api/overview/jobs":
            self._send_json(200, load_jobs(self._overview_state()))
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

        # Map uses its own shell within the current operations navigation.
        if route in ("/map", "/map/"):
            self._serve_map_shell()
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

    def _client_gone(self) -> bool:
        """True when the peer has half-closed (Tailscale drop, tab gone).

        An SSE slot held by a dead socket is what turns 2–3 browser clients
        into /api/changes 503s (pc-1554). Peek instead of waiting for the
        20s heartbeat write to fail.
        """
        conn = getattr(self, "connection", None)
        if conn is None:
            return False
        try:
            ready, _, _ = select.select([conn], [], [], 0)
            if not ready:
                return False
            data = conn.recv(1, socket.MSG_PEEK)
            return not data
        except (OSError, ValueError, AttributeError):
            return True

    # ── change feed (D2) — text/event-stream, one connection per client ─
    def _serve_changes(self) -> None:
        feed = self.change_feed
        subscription = feed.subscribe() if feed is not None else None
        if subscription is None:
            self._send_text(503, "Too many open change-feed connections.")
            return
        client_id, inbox = subscription
        try:
            try:
                self.connection.settimeout(HEARTBEAT_SECS + 10)
            except OSError:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            last_sent = time.monotonic()
            while True:
                if self._client_gone():
                    break
                try:
                    event = inbox.get(timeout=1.0)
                    self.wfile.write(f"event: changed\ndata: {json.dumps(event)}\n\n".encode("utf-8"))
                except queue.Empty:
                    if self._client_gone():
                        break
                    if time.monotonic() - last_sent < HEARTBEAT_SECS:
                        continue
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
                last_sent = time.monotonic()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.close_connection = True
            if feed is not None:
                feed.unsubscribe(client_id)

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
        if candidate.name == 'operations.html':
            text = candidate.read_text(encoding='utf-8')
            search = (_OV_STATIC_DIR / 'workspace-search.html').read_text(encoding='utf-8')
            text = text.replace('<section id="overview-view" hidden>', '<section id="overview-view" hidden>' + search)
            text = text.replace('</body>', '<script src="/js/workspace-search.js"></script></body>')
            self._send_text(200, text, ctype)
        else:
            self._send_bytes(200, candidate.read_bytes(), ctype)

    def _serve_reader_page(self, name: str, *, brand_suffix: str) -> None:
        candidate = (_OV_STATIC_DIR / name).resolve()
        if not candidate.is_file():
            self._send_text(404, "not found")
            return
        text = _inject_reader_shell(candidate.read_text(encoding='utf-8'), brand_suffix=brand_suffix)
        self._send_text(200, text, "text/html; charset=utf-8")

    def _serve_map_shell(self) -> None:
        shell = _MAP_STATIC_DIR / "workspace_map.html"
        if not shell.is_file():
            self._send_text(404, "map shell missing")
            return
        text = _rewrite_map_html(shell.read_text(encoding="utf-8"))
        header, nav, _footer = _operations_shell_parts()
        nav = nav.replace('href="/map"', 'href="/map" aria-current="page"')
        search = (_OV_STATIC_DIR / 'workspace-search.html').read_text(encoding='utf-8')
        text = text.replace('</head>', '<link rel="stylesheet" href="/css/overview.css"><link rel="stylesheet" href="/css/operations.css"></head>')
        text = text.replace('<body>', '<body class="bp-operations bp-map-page">' + header + nav + search)
        text = text.replace('</body>', '<script src="/js/workspace-search.js"></script><script src="/js/map-shell.js"></script></body>')
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


DEFAULT_PORT = 8801


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dogfood desk server for BluePrint (four-lens)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--legacy-port", action="append", type=int, default=[], help="Retired local UI port to redirect to this app")
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
    Handler.change_feed = ChangeFeed(binder)

    from server.operations import set_listen_port
    from server.operations_cache import reset_operations_cache
    reset_operations_cache()
    set_listen_port(args.port)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True
    redirects = []
    try:
        from server.legacy_redirect import listener
        import threading
        for port in args.legacy_port:
            redirect = listener(args.host, port, args.port)
            redirects.append(redirect)
        for redirect in redirects:
            threading.Thread(target=redirect.serve_forever, daemon=True).start()
    except OSError:
        for redirect in redirects: redirect.server_close()
        httpd.server_close()
        raise
    where = f" · binder={binder}" if binder else ""
    print(f"bp-desk: four-lens shell on http://{args.host}:{args.port}/{where}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbp-desk: shutdown")
    finally:
        for redirect in redirects:
            redirect.shutdown()
            redirect.server_close()
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
