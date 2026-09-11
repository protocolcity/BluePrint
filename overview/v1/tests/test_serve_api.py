"""End-to-end tests for overview/v1/serve.py (full glass ext-01c/02c/03d).

Boots the ThreadingHTTPServer on an ephemeral port, exercises the five
V1 endpoints + the static shell, and confirms the empty-paint invariants
from docs/specs/OVERVIEW_INTENT.md · OVERVIEW_THEME.md · OVERVIEW_MC_EXT.md:

- Default serve returns honest-empty for agents · jobs · pulse (+ five
  named heartbeats stamped ``off``).
- overview.html includes the four-lens top nav, the `Local desk` banner
  (not `workspace`), Writer copy, and Charter drawer / Project card
  hosts. It never contains Map's verbs (dig, lot, hub, fan, trail,
  md-viewer, binder, crumb).
- --fixture with only demo-worker still paints `No agents`.
- Cloud / remote builders come back in their own arrays, never mixed
  into the agents roster.
- Full-glass fixture surfaces the Charter drawer + Project card
  alongside the peer tiles.
- Cellar tip = brew face (never a private ProtocolCity SHA).

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
from server.overview_state import (  # noqa: E402
    DEFAULT_CELLAR_TIP,
    HEARTBEAT_NAMES,
    empty_state,
    load_from_fixture,
)

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
        st = empty_state()
        self.httpd, self.port, self.thread = _start_server(st)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_agents_endpoint_returns_empty_lists(self) -> None:
        status, body, ctype = _get(self.port, "/api/overview/agents")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["agents"], [])
        self.assertEqual(payload["cloud_builders"], [])
        self.assertEqual(payload["remote_builders"], [])

    def test_jobs_endpoint_returns_zero_buckets(self) -> None:
        status, body, _ = _get(self.port, "/api/overview/jobs")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["jobs"], [])
        self.assertEqual(
            payload["buckets"], {"waiting": 0, "ready": 0, "blocked": 0}
        )

    def test_pulse_endpoint_names_five_local_heartbeats(self) -> None:
        status, body, _ = _get(self.port, "/api/overview/pulse")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        names = [hb["name"] for hb in payload["heartbeats"]]
        self.assertEqual(list(HEARTBEAT_NAMES), names)
        for hb in payload["heartbeats"]:
            # Missing heartbeat ≠ green — cold serve paints every row muted.
            self.assertEqual(hb["state"], "off")
        self.assertEqual(payload["cellar_tip"], DEFAULT_CELLAR_TIP)
        self.assertEqual(payload["ticks"], [])
        self.assertIsNone(payload["last_at"])

    def test_project_endpoint_returns_empty_object(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/project")
        self.assertEqual(json.loads(body), {})

    def test_charter_endpoint_returns_empty_object(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/charter")
        self.assertEqual(json.loads(body), {})

    def test_overview_html_paints_full_glass_hosts(self) -> None:
        status, body, ctype = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        text = body.decode("utf-8")
        # Writer lock — Agents / Jobs empty copy verbatim.
        self.assertIn("No agents", text)
        self.assertIn("No open jobs", text)
        # Local-only honesty banner — the exact string, never `workspace`.
        self.assertIn("Local desk", text)
        self.assertNotIn("Local workspace", text)
        # Case-insensitive `workspace` guard — no theme carryover.
        self.assertNotIn("workspace", text.lower())
        # Four-lens top nav — Overview is the current lens.
        self.assertIn('data-lens="overview"', text)
        self.assertIn('data-lens="map"', text)
        self.assertIn('data-lens="calendar"', text)
        self.assertIn('data-lens="settings"', text)
        self.assertIn('aria-current="page"', text)
        # Chip verbs — Map, never `Dig here`.
        self.assertNotIn("Dig here", text)
        # Peer tile hosts + drawer + project card + footer roles present.
        for role in (
            "agents-body", "jobs-body", "pulse-body",
            "agents-links", "jobs-buckets", "pulse-meta",
            "project-card", "project-badges", "project-excerpt",
            "charter-drawer", "charter-body", "charter-footer",
            "footer-row", "footer-quiet",
        ):
            self.assertIn(f'data-role="{role}"', text, f"missing role {role!r}")

    def test_overview_tile_bodies_are_keyboard_focusable(self) -> None:
        _, body, _ = _get(self.port, "/")
        text = body.decode("utf-8")
        for role in ("agents-body", "jobs-body", "pulse-body"):
            self.assertRegex(
                text,
                rf'data-role="{role}"[^>]*tabindex="0"',
                f"Overview tile body {role!r} must be focusable",
            )

    def test_overview_html_hides_project_and_charter_by_default(self) -> None:
        """Honest default — no project card, no charter drawer until state
        says otherwise. The elements exist as hosts but stay hidden."""
        _, body, _ = _get(self.port, "/")
        text = body.decode("utf-8")
        self.assertRegex(
            text,
            r'data-role="project-card"[^>]*hidden',
            "Project card must be hidden by default",
        )
        self.assertRegex(
            text,
            r'data-role="charter-drawer"[^>]*hidden',
            "Charter drawer must be hidden by default",
        )

    def test_overview_css_shares_focus_ring_across_interactive_elements(self) -> None:
        _, body, _ = _get(self.port, "/css/overview.css")
        css = body.decode("utf-8")
        self.assertIn(".ov-tile-body:focus-visible", css)
        self.assertIn(".ov-lens:focus-visible", css)
        self.assertIn(".ov-link-row:focus-visible", css)
        self.assertIn(".ov-project-action:focus-visible", css)

    def test_overview_html_never_speaks_map_verbs(self) -> None:
        _, body, _ = _get(self.port, "/")
        # HTML lens chip mentions `data-lens="map"` — that's the lens name,
        # not the verb `Map` in prose. The Map verbs guarded here are the
        # dig-family words (dig, lot, hub, fan, trail, md-viewer, binder,
        # crumb) — the lens name `Map` is allowed as a chip label.
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
        payload = json.loads(body)
        self.assertEqual(payload["agents"], [])


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
        self.assertEqual(states, {"idle", "working", "error", "off"})

    def test_cloud_builders_are_links_not_agents(self) -> None:
        """Links ≠ agents — cloud/remote builders never appear in the
        `agents` array. They come back in their own outbound-link array."""
        _, body, _ = _get(self.port, "/api/overview/agents")
        payload = json.loads(body)
        agent_names = {row["name"] for row in payload["agents"]}
        cloud_names = {row["name"] for row in payload["cloud_builders"]}
        remote_names = {row["name"] for row in payload["remote_builders"]}
        self.assertGreater(len(cloud_names) + len(remote_names), 0)
        # No overlap — a builder is a link, never a local agent row.
        self.assertEqual(agent_names & cloud_names, set())
        self.assertEqual(agent_names & remote_names, set())
        # Every builder row carries a url (outbound).
        for row in payload["cloud_builders"] + payload["remote_builders"]:
            self.assertTrue(row["url"].startswith("http"))

    def test_jobs_have_buckets(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/jobs")
        payload = json.loads(body)
        self.assertEqual(payload["buckets"], {"waiting": 1, "ready": 2, "blocked": 0})

    def test_pulse_has_named_heartbeats_and_cellar_tip(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/pulse")
        payload = json.loads(body)
        names = [hb["name"] for hb in payload["heartbeats"]]
        self.assertEqual(list(HEARTBEAT_NAMES), names)
        # No private ProtocolCity SHA — the tip is the brew face.
        self.assertEqual(payload["cellar_tip"], "blueprint 0.1.50_6")
        self.assertNotIn("protocolcity", payload["cellar_tip"].lower())
        self.assertEqual(payload["last_at"], "2026-09-11T10:21:34")


class FullGlassFixtureTests(unittest.TestCase):
    """Full-glass fixture: project card + charter drawer + peer tiles."""

    def setUp(self) -> None:
        st = load_from_fixture(FIXTURES / "full_glass.json")
        self.httpd, self.port, self.thread = _start_server(st)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_project_card_is_present(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/project")
        payload = json.loads(body)
        self.assertEqual(payload["title"], "Protocol City")
        # On this desk — path voice never says `workspace`, never cloud.
        self.assertEqual(payload["path_hint"], "on this desk")
        self.assertNotIn("workspace", json.dumps(payload).lower())

    def test_project_badges_are_honest(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/project")
        payload = json.loads(body)
        badges = payload["badges"]
        self.assertTrue(badges["local_write"])
        # Consume ≠ MANAGED — badge off unless a lease is live.
        self.assertFalse(badges["consume"])
        self.assertTrue(badges["upstream"])
        self.assertTrue(badges["local_only"])

    def test_charter_drawer_carries_never_lie_footer(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/charter")
        payload = json.loads(body)
        self.assertIn("Cellar app tip", payload["footer"])
        self.assertIn("not private Protocol City install", payload["footer"])
        headings = [s["heading"] for s in payload["sections"]]
        self.assertIn("Purpose", headings)
        self.assertIn("Scope", headings)
        self.assertIn("Invariants", headings)

    def test_peer_tiles_preserved_alongside_drawer(self) -> None:
        """The Charter drawer sits alongside the three peer tiles — it
        never replaces the spine. Agents/Jobs/Pulse all keep their own
        endpoints and payload shape."""
        _, agents_body, _ = _get(self.port, "/api/overview/agents")
        _, jobs_body, _ = _get(self.port, "/api/overview/jobs")
        _, pulse_body, _ = _get(self.port, "/api/overview/pulse")
        agents = json.loads(agents_body)
        jobs = json.loads(jobs_body)
        pulse = json.loads(pulse_body)
        self.assertGreater(len(agents["agents"]), 0)
        self.assertIn("buckets", jobs)
        self.assertGreater(len(pulse["heartbeats"]), 0)


class CellarTipInjectionTests(unittest.TestCase):
    """--cellar-tip on serve.py is the single voice for the brew face."""

    def test_apply_cellar_tip_overrides_state(self) -> None:
        st = empty_state()
        overview_serve._apply_cellar_tip(st, "blueprint 0.1.50_7")
        self.assertEqual(st["cellar_tip"], "blueprint 0.1.50_7")

    def test_apply_cellar_tip_defaults_when_empty(self) -> None:
        st = empty_state()
        overview_serve._apply_cellar_tip(st, "")
        self.assertEqual(st["cellar_tip"], DEFAULT_CELLAR_TIP)


if __name__ == "__main__":
    unittest.main()
