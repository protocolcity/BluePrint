"""End-to-end tests for overview/v1/serve.py.

Boots the ThreadingHTTPServer on an ephemeral port, exercises the three
V1 endpoints + the static shell, and confirms the empty-paint invariants
from docs/specs/OVERVIEW_INTENT.md and OVERVIEW_THEME.md:

- Default serve returns honest-empty for agents · jobs · pulse.
- overview.html includes the Writer copy, the `Local desk` banner (not
  `workspace`), and the `Map` / `Calendar` / `Settings` hand-off chips.
- overview.html never contains Map's verbs (dig, lot, hub, fan, trail,
  md-viewer, binder, crumb).
- --fixture with only demo-worker still paints `No agents`.

Run with:  pytest overview/v1/tests
"""
from __future__ import annotations

import json
import re
import socket
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

import serve as overview_serve  # noqa: E402
from server.overview_state import empty_state, load_from_fixture  # noqa: E402

FIXTURES = _HERE / "fixtures"

MAP_VERBS = ("dig", "lot", "hub", "fan", "trail", "md-viewer", "binder", "crumb")


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(state: dict) -> tuple[object, int, threading.Thread]:
    overview_serve.Handler.state = state
    port = _pick_port()
    httpd = overview_serve.ThreadingHTTPServer(("127.0.0.1", port), overview_serve.Handler)
    thread = threading.Thread(target=httpd.serve_forever, name=f"ov-v1-{port}", daemon=True)
    thread.start()
    # Small settle so the socket is accepting.
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.02)
    return httpd, port, thread


def _get(port: int, path: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.status, resp.read(), resp.headers.get_content_type()


class HonestEmptyServeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.httpd, self.port, self.thread = _start_server(empty_state())

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_agents_endpoint_returns_empty_list(self) -> None:
        status, body, ctype = _get(self.port, "/api/overview/agents")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        self.assertEqual(json.loads(body), {"agents": []})

    def test_jobs_endpoint_returns_empty_list(self) -> None:
        status, body, _ = _get(self.port, "/api/overview/jobs")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"jobs": []})

    def test_pulse_endpoint_returns_empty_ticks(self) -> None:
        status, body, _ = _get(self.port, "/api/overview/pulse")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload, {"ticks": [], "last_at": None})

    def test_overview_html_paints_writer_copy(self) -> None:
        status, body, ctype = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        text = body.decode("utf-8")
        # Empty copy — Writer lock (THEME §Writer table).
        self.assertIn("No agents", text)
        self.assertIn("No open jobs", text)
        # Local-only honesty banner — the exact string, never "workspace".
        self.assertIn("Local desk", text)
        self.assertNotIn("Local workspace", text)
        self.assertNotIn("workspace", text.lower())
        # Hand-off chips — Map (not "Dig here"), Calendar, Settings.
        self.assertIn(">Map<", text)
        self.assertIn(">Calendar<", text)
        self.assertIn(">Settings<", text)
        self.assertNotIn("Dig here", text)

    def test_overview_html_never_speaks_map_verbs(self) -> None:
        """Label lock — Overview never borrows Map's vocabulary."""
        _, body, _ = _get(self.port, "/")
        text = body.decode("utf-8").lower()
        for verb in MAP_VERBS:
            pattern = re.compile(rf"\b{re.escape(verb)}\b")
            self.assertIsNone(
                pattern.search(text),
                f"Overview HTML must not use Map verb {verb!r}",
            )

    def test_static_css_serves(self) -> None:
        status, body, ctype = _get(self.port, "/css/overview.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", ctype)
        self.assertGreater(len(body), 0)

    def test_static_js_serves(self) -> None:
        status, body, ctype = _get(self.port, "/js/overview.v1.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", ctype)
        self.assertGreater(len(body), 0)

    def test_path_escape_rejected(self) -> None:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/../serve.py")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=2)
        self.assertIn(ctx.exception.code, (400, 404))


class DemoWorkerFixtureTests(unittest.TestCase):
    """`demo-worker` alone must not paint a busy Agents tile."""

    def setUp(self) -> None:
        st = load_from_fixture(FIXTURES / "demo_worker_only.json")
        self.httpd, self.port, self.thread = _start_server(st)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_agents_endpoint_stays_empty(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/agents")
        self.assertEqual(json.loads(body), {"agents": []})


class PopulatedFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        st = load_from_fixture(FIXTURES / "populated.json")
        self.httpd, self.port, self.thread = _start_server(st)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_agents_include_state_dots(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/agents")
        payload = json.loads(body)
        states = {row["state"] for row in payload["agents"]}
        # All four V1 state dots represented — idle · working · error · off.
        self.assertEqual(states, {"idle", "working", "error", "off"})

    def test_jobs_have_state(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/jobs")
        payload = json.loads(body)
        self.assertEqual(len(payload["jobs"]), 2)
        for row in payload["jobs"]:
            self.assertIn("state", row)

    def test_pulse_has_ticks_and_last_at(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/pulse")
        payload = json.loads(body)
        self.assertEqual(len(payload["ticks"]), 2)
        self.assertEqual(payload["last_at"], "2026-09-10T09:12:00")


if __name__ == "__main__":
    unittest.main()
