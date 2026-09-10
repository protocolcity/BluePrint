#!/usr/bin/env python3
"""Tiny dogfood server for the Map V1 shell.

Serves the three V1 endpoints against a binder folder + the static assets:

- ``GET /api/map/tree``
- ``GET /api/map/children?relPath=…``
- ``GET /api/file?path=…&render=html``
- ``GET /``            → workspace_map.html
- ``GET /<static>``    → static/… assets

Usage::

    python3 map/v1/serve.py --binder ~/BluePrint --port 8801

The blueprint pip package can vendor ``server/map_tree.py`` and mount the
same routes in its BFF later. This module exists so the shell is
dogfoodable stand-alone against any folder on disk.
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

from server.map_tree import build_tree, children_at, render_file  # noqa: E402

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
    binder_root: Path = Path.cwd()

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
        sys.stderr.write("map-v1 %s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802 — http.server contract
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        route = parsed.path

        if route == "/api/map/tree":
            try:
                self._send_json(200, build_tree(self.binder_root))
            except Exception as exc:  # noqa: BLE001 — surface as 500
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/api/map/children":
            rel = query.get("relPath", "")
            try:
                self._send_json(200, children_at(self.binder_root, rel))
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/api/file":
            path = query.get("path", "")
            render = query.get("render", "raw")
            try:
                body, ctype = render_file(self.binder_root, path, render=render)
                self._send_text(200, body, ctype)
            except FileNotFoundError:
                self._send_text(404, "not found")
            except ValueError as exc:
                self._send_text(400, str(exc))
            return

        # Static assets under ./static
        if route == "/" or route == "/workspace-map":
            self._serve_static("workspace_map.html")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dogfood server for BluePrint Map V1")
    parser.add_argument("--binder", type=Path, required=True, help="binder folder to project")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8801)
    args = parser.parse_args(argv)
    binder = args.binder.expanduser().resolve()
    if not binder.is_dir():
        print(f"map-v1: binder is not a directory: {binder}", file=sys.stderr)
        return 2
    Handler.binder_root = binder
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"map-v1: serving {binder} → http://{args.host}:{args.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nmap-v1: shutdown")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
