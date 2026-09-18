"""pc-1554: /api/operations stays responsive under concurrent desk clients.

Reproduces the dogfood hang: a slow engine probe plus open /api/changes
streams must not leave GET /api/operations at 0 bytes past the browser
abort, and a receipt pointed at this process must not nest a probe.
"""
from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

import serve as overview_serve  # noqa: E402
from server.change_feed import ChangeFeed  # noqa: E402
from server.operations import PROBE_TIMEOUT_SECS, set_listen_port  # noqa: E402
from server.operations_cache import reset_operations_cache  # noqa: E402
from server.overview_state import empty_state  # noqa: E402


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _start_server(root: Path | None = None):
    reset_operations_cache()
    set_listen_port(None)
    overview_serve.Handler.state = empty_state()
    overview_serve.Handler.binder_overview = None
    overview_serve.Handler.binder_root = root
    overview_serve.Handler.change_feed = ChangeFeed(root, poll_interval=0.05)
    port = _pick_port()
    set_listen_port(port)
    httpd = overview_serve.ThreadingHTTPServer(('127.0.0.1', port), overview_serve.Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, name=f'ov-hang-{port}', daemon=True)
    thread.start()
    for _ in range(50):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.02)
    return httpd, port


def _open_changes(port: int) -> socket.socket:
    sock = socket.create_connection(('127.0.0.1', port), timeout=2)
    sock.sendall(b'GET /api/changes HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n')
    buf = b''
    while b'\r\n\r\n' not in buf:
        buf += sock.recv(4096)
    return sock


def _get(port: int, path: str, timeout: float = 4.0) -> tuple[int, bytes]:
    sock = socket.create_connection(('127.0.0.1', port), timeout=timeout)
    try:
        sock.settimeout(timeout)
        sock.sendall(f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n'.encode())
        buf = b''
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        sock.close()
    head, _, body = buf.partition(b'\r\n\r\n')
    status = int(head.split(b' ', 2)[1])
    return status, body


class OperationsHangTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.httpd = None

    def tearDown(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        reset_operations_cache()
        set_listen_port(None)
        self.temp.cleanup()

    def test_probe_timeout_is_under_browser_abort(self) -> None:
        self.assertLessEqual(PROBE_TIMEOUT_SECS, 1.0)

    def test_three_clients_share_one_slow_snapshot(self) -> None:
        calls = []

        def slow_snapshot(binder):
            calls.append(binder)
            time.sleep(0.35)
            return {
                'observed_at': '2026-09-18T00:00:00+00:00',
                'build': 'test',
                'workspace': {'name': self.root.name, 'path': str(self.root)},
                'orders': [], 'projects': [], 'agents': [], 'sources': [],
                'calendar_doors': {'due_count': 0, 'items': []},
            }

        self.httpd, port = _start_server(self.root)
        streams = [_open_changes(port) for _ in range(2)]
        try:
            with patch('server.operations.operations_snapshot', side_effect=slow_snapshot):
                results = []
                errors = []

                def worker():
                    try:
                        results.append(_get(port, '/api/operations', timeout=3.0))
                    except Exception as exc:  # noqa: BLE001 — collect for the assertion
                        errors.append(exc)

                threads = [threading.Thread(target=worker) for _ in range(3)]
                started = time.monotonic()
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(4.0)
                    self.assertFalse(thread.is_alive())
                elapsed = time.monotonic() - started
            self.assertEqual(errors, [])
            self.assertEqual(len(results), 3)
            for status, body in results:
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertEqual(json.loads(body)['build'], 'test')
            self.assertEqual(len(calls), 1)
            self.assertLess(elapsed, 1.5)
            pulse_status, pulse_body = _get(port, '/api/overview/pulse', timeout=2.0)
            self.assertEqual(pulse_status, 200)
            self.assertTrue(pulse_body)
        finally:
            for sock in streams:
                sock.close()

    def test_self_origin_receipt_does_not_nest_a_probe(self) -> None:
        (self.root / 'local' / 'worklane').mkdir(parents=True)
        self.httpd, port = _start_server(self.root)
        (self.root / 'local' / 'worklane' / 'deployment.json').write_text(json.dumps({
            'version': '0.1.7+test', 'port': port,
        }))
        started = time.monotonic()
        status, body = _get(port, '/api/operations', timeout=3.0)
        elapsed = time.monotonic() - started
        self.assertEqual(status, 200)
        payload = json.loads(body)
        api = payload['engines']['worklane_api']
        self.assertEqual(api['state'], 'unavailable')
        self.assertIn('listen port', api['detail'].lower())
        self.assertLess(elapsed, 2.0)


if __name__ == '__main__':
    unittest.main()
