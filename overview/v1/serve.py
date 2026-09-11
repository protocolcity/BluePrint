#!/usr/bin/env python3
"""Tiny dogfood server for the Overview V1 Mission Control shell.

Serves the V1 endpoints + static assets:

- ``GET /api/overview/agents``   (with cloud / remote builder links)
- ``GET /api/overview/jobs``     (with Waiting · Ready · Blocked buckets)
- ``GET /api/overview/pulse``    (named heartbeats + Cellar tip + last tick)
- ``GET /api/overview/project``  (project card or ``{}``)
- ``GET /api/overview/charter``  (charter drawer or ``{}``)
- ``GET /``                      → overview.html
- ``GET /<static>``              → static/… assets

Usage::

    python3 overview/v1/serve.py --port 8803
    python3 overview/v1/serve.py --port 8803 --fixture path/to/state.json
    python3 overview/v1/serve.py --port 8803 --cellar-tip "blueprint 0.1.50_6"

The default serve returns honest-empty (``No agents`` · ``No open jobs`` ·
silent pulse) — that is the correct paint per
``docs/specs/OVERVIEW_INTENT.md`` §Dogfood note. ``--fixture`` is for tests
and manual demos only; it never lands in the pip package.

``--cellar-tip`` overrides the brew face injected into
``/api/overview/pulse`` — never a private ProtocolCity SHA (``OVERVIEW_MC_EXT.md``
never-lie DoD).

Sibling of ``map/v1/serve.py``; the BluePrint pip package can vendor
``server/overview_state.py`` and mount the same routes in its BFF later.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from server.overview_state import (  # noqa: E402
    DEFAULT_CELLAR_TIP,
    empty_state,
    load_agents,
    load_charter,
    load_from_fixture,
    load_jobs,
    load_project,
    load_pulse,
)

_STATIC_DIR = _HERE / "static"

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


class Handler(BaseHTTPRequestHandler):
    state: dict = empty_state()

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

    def _send_text(self, code: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        self._send_bytes(code, text.encode("utf-8"), content_type)

    def log_message(self, fmt: str, *args) -> None:  # keep output quiet
        sys.stderr.write("overview-v1 %s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        route = urlparse(self.path).path

        if route == "/api/overview/agents":
            self._send_json(200, load_agents(self.state))
            return
        if route == "/api/overview/jobs":
            self._send_json(200, load_jobs(self.state))
            return
        if route == "/api/overview/pulse":
            self._send_json(200, load_pulse(self.state))
            return
        if route == "/api/overview/project":
            self._send_json(200, load_project(self.state))
            return
        if route == "/api/overview/charter":
            self._send_json(200, load_charter(self.state))
            return

        if route == "/" or route == "/overview":
            self._serve_static("overview.html")
            return
        if route.startswith("/"):
            self._serve_static(route.lstrip("/"))
            return
        self._send_text(404, "not found")

    def _serve_static(self, rel: str) -> None:
        candidate = (_STATIC_DIR / rel).resolve()
        try:
            candidate.relative_to(_STATIC_DIR)
        except ValueError:
            self._send_text(400, "path escape")
            return
        if not candidate.is_file():
            self._send_text(404, "not found")
            return
        ctype = _MIME_BY_SUFFIX.get(candidate.suffix.lower(), "application/octet-stream")
        self._send_bytes(200, candidate.read_bytes(), ctype)


def _apply_cellar_tip(state: dict, cellar_tip: str) -> dict:
    """Overlay the brew-face Cellar tip onto the loaded state.

    Never a private ProtocolCity SHA. ``--cellar-tip`` on the CLI is the
    single voice for the version string the pulse tile paints.
    """
    tip = (cellar_tip or "").strip() or DEFAULT_CELLAR_TIP
    state["cellar_tip"] = tip
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dogfood server for BluePrint Overview V1")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8803)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="JSON fixture of local truth (tests / demo only — default serve stays empty)",
    )
    parser.add_argument(
        "--cellar-tip",
        default=DEFAULT_CELLAR_TIP,
        help=(
            "Brew-face Cellar tip painted by /api/overview/pulse "
            f"(default: {DEFAULT_CELLAR_TIP!r}). Never a private ProtocolCity SHA."
        ),
    )
    args = parser.parse_args(argv)

    if args.fixture is not None:
        try:
            state = load_from_fixture(args.fixture)
        except (FileNotFoundError, ValueError) as exc:
            print(f"overview-v1: fixture error: {exc}", file=sys.stderr)
            return 2
        print(f"overview-v1: loaded fixture {args.fixture}", file=sys.stderr)
    else:
        state = empty_state()

    Handler.state = _apply_cellar_tip(state, args.cellar_tip)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"overview-v1: Mission Control on http://{args.host}:{args.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\noverview-v1: shutdown")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
