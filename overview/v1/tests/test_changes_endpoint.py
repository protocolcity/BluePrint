"""GET /api/changes — SSE wiring for the D2 change feed.

Boots the real ThreadingHTTPServer and drives it over a socket (urlopen
buffers the whole body, which never arrives on an SSE stream) to confirm:
the response is ``text/event-stream``; a real stat change on a watched
file arrives as a ``changed`` event within the poll interval; the
endpoint refuses a client past the shared cap; disconnecting one client
frees a slot for the next.
"""
from __future__ import annotations

import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

import serve as overview_serve  # noqa: E402
from server.change_feed import ChangeFeed, MAX_CLIENTS  # noqa: E402
from server.overview_state import empty_state  # noqa: E402


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(root: Path, poll_interval: float = 0.05):
    from server.operations import set_listen_port
    from server.operations_cache import reset_operations_cache
    reset_operations_cache()
    overview_serve.Handler.state = empty_state()
    overview_serve.Handler.binder_overview = None
    overview_serve.Handler.binder_root = root
    overview_serve.Handler.change_feed = ChangeFeed(root, poll_interval=poll_interval)
    port = _pick_port()
    set_listen_port(port)
    httpd = overview_serve.ThreadingHTTPServer(("127.0.0.1", port), overview_serve.Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, name=f"ov-changes-{port}", daemon=True)
    thread.start()
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.02)
    return httpd, port


def _open_stream(port: int) -> socket.socket:
    sock = socket.create_connection(("127.0.0.1", port), timeout=2)
    sock.sendall(b"GET /api/changes HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n")
    return sock


def _read_headers(sock: socket.socket) -> bytes:
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += sock.recv(4096)
    return buf


def _read_until_event(sock: socket.socket, timeout: float = 3.0) -> str:
    sock.settimeout(timeout)
    buf = b""
    while b"\n\n" not in buf:
        buf += sock.recv(4096)
    return buf.decode("utf-8", errors="replace")


class ChangesEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "worklane" / "worklane" / "local" / "data").mkdir(parents=True)
        self.httpd, self.port = _start_server(self.root)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_stream_content_type_is_event_stream(self) -> None:
        sock = _open_stream(self.port)
        try:
            head = _read_headers(sock)
            self.assertIn(b"200", head.split(b"\r\n", 1)[0])
            self.assertIn(b"text/event-stream", head)
        finally:
            sock.close()

    def test_store_change_arrives_as_changed_event(self) -> None:
        sock = _open_stream(self.port)
        try:
            _read_headers(sock)
            db = self.root / "worklane" / "worklane" / "local" / "data" / "acme.db"
            db.write_bytes(b"x")
            body = _read_until_event(sock)
            self.assertIn("event: changed", body)
            self.assertIn('"source": "worklane"', body)
            self.assertIn('"path": "acme.db"', body)
            self.assertNotIn(str(self.root), body)
        finally:
            sock.close()

    def test_client_cap_and_release(self) -> None:
        sockets = [_open_stream(self.port) for _ in range(MAX_CLIENTS)]
        try:
            for sock in sockets:
                _read_headers(sock)
            overflow = _open_stream(self.port)
            try:
                head = _read_headers(overflow)
                self.assertIn(b"503", head.split(b"\r\n", 1)[0])
            finally:
                overflow.close()
            sockets[0].close()
            db = self.root / "worklane" / "worklane" / "local" / "data" / "acme.db"
            for _ in range(50):
                db.write_bytes(str(time.time()).encode())
                if self.httpd.RequestHandlerClass.change_feed.client_count() < MAX_CLIENTS:
                    break
                time.sleep(0.05)
            reconnect = _open_stream(self.port)
            try:
                head = _read_headers(reconnect)
                self.assertIn(b"200", head.split(b"\r\n", 1)[0])
            finally:
                reconnect.close()
        finally:
            for sock in sockets[1:]:
                sock.close()


if __name__ == "__main__":
    unittest.main()
