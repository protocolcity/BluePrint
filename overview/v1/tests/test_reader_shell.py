"""Reader shell parity — pc-1491 shared navigation and Delivery naming."""
from __future__ import annotations

import socket
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

import serve as overview_serve  # noqa: E402
from server.overview_state import empty_state  # noqa: E402


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server():
    from server.operations_cache import reset_operations_cache
    reset_operations_cache()
    overview_serve.Handler.state = empty_state()
    overview_serve.Handler.binder_overview = None
    overview_serve.Handler.binder_root = None
    overview_serve.Handler.change_feed = None
    port = _pick_port()
    httpd = overview_serve.ThreadingHTTPServer(("127.0.0.1", port), overview_serve.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.02)
    return httpd, port


class ReaderShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.httpd, self.port = _start_server()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def _get(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=2) as resp:
            return resp.read().decode()

    def test_work_order_shell_uses_delivery_nav_and_desk_scope(self) -> None:
        body = self._get("/work-order")
        self.assertIn('href="/delivery"', body)
        self.assertIn('href="/timeline"', body)
        self.assertNotIn('>Activity</a>', body)
        self.assertIn('id="desk-scope"', body)
        self.assertIn('id="facts"', body)
        self.assertIn('/js/reader-shell.js', body)

    def test_documents_shell_matches_operations_destinations(self) -> None:
        body = self._get("/documents")
        self.assertIn('href="/delivery"', body)
        self.assertIn('id="reader-back"', body)
        self.assertIn('class="bp-md', body)
