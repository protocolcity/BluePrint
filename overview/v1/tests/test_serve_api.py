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
import shutil
import re
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

import serve as overview_serve  # noqa: E402
from server.overview_state import (  # noqa: E402
    BinderOverview,
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


def _start_server(
    state: dict,
    *,
    binder_overview=None,
    binder_root: Path | None = None,
    change_feed=None,
) -> tuple[object, int, threading.Thread]:
    # Handler carries truth on the class — reset each knob on every boot so
    # one test class can't leak a binder into the next.
    overview_serve.Handler.state = state
    overview_serve.Handler.binder_overview = binder_overview
    overview_serve.Handler.binder_root = binder_root
    overview_serve.Handler.change_feed = change_feed
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

    def test_overview_html_paints_operations_shell(self) -> None:
        status, body, ctype = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        text = body.decode()
        for name in ("overview", "work", "projects", "agents", "connections", "calendar", "settings"):
            self.assertIn(f'id="{name}-view"', text)
        self.assertIn('/js/operations.js', text)
        self.assertIn('id="source-warning"', text)

    def test_operations_controls_use_native_keyboard_elements(self) -> None:
        _, body, _ = _get(self.port, "/")
        text = body.decode()
        self.assertIn('<details id="desk-scope">', text)
        self.assertIn('<input id="search" type="search"', text)
        self.assertIn('<select id="project-filter">', text)
        self.assertIn('href="#content"', text)

    def test_operations_cold_state_does_not_claim_healthy_sources(self) -> None:
        _, body, _ = _get(self.port, "/")
        text = body.decode()
        self.assertIn('Waiting for source data', text)
        self.assertNotIn('All systems quiet', text)
        _, body, _ = _get(self.port, "/api/operations")
        payload = json.loads(body)
        self.assertEqual(payload['sources'][0]['state'], 'unavailable')
        self.assertEqual(payload['orders'], [])
        self.assertEqual(payload['throughput']['state'], 'unavailable')
        self.assertEqual(payload['throughput']['closes'], 0)
        self.assertEqual(payload['work_flow']['state'], 'unavailable')
        self.assertEqual(payload['work_flow']['seats'], [])
        self.assertEqual(payload['calendar_load']['state'], 'unavailable')
        self.assertEqual(payload['calendar_load']['days'], [])

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
        self.assertEqual(payload["cellar_tip"], "blueprint 0.1.50_9")
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




class BinderLiveReadTests(unittest.TestCase):
    """Binder truth is re-read per request, like calendar.json.

    Before this peel Agents / Jobs / Pulse were boot-pinned: a desk started
    cold stayed cold until it was bounced.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="bp-desk-live-")
        self.binder = Path(self.tmp)
        (self.binder / ".blueprint").mkdir()
        self.marker = self.binder / ".blueprint" / "overview.json"
        self.source = BinderOverview(self.binder, cellar_tip=DEFAULT_CELLAR_TIP)
        self.httpd, self.port, self.thread = _start_server(
            self.source.current(),
            binder_overview=self.source,
            binder_root=self.binder,
        )

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_marker(self, payload: dict) -> None:
        self.marker.write_text(json.dumps(payload), encoding="utf-8")

    def _agents(self) -> list:
        return json.loads(_get(self.port, "/api/overview/agents")[1])["agents"]

    def test_binder_without_overview_json_is_honest_empty(self) -> None:
        self.assertEqual(self._agents(), [])
        jobs = json.loads(_get(self.port, "/api/overview/jobs")[1])
        self.assertEqual(jobs["jobs"], [])
        self.assertEqual(jobs["buckets"], {"waiting": 0, "ready": 0, "blocked": 0})
        pulse = json.loads(_get(self.port, "/api/overview/pulse")[1])
        self.assertEqual([hb["name"] for hb in pulse["heartbeats"]], list(HEARTBEAT_NAMES))
        self.assertEqual({hb["state"] for hb in pulse["heartbeats"]}, {"off"})
        self.assertEqual(json.loads(_get(self.port, "/api/overview/project")[1]), {})
        self.assertEqual(json.loads(_get(self.port, "/api/overview/charter")[1]), {})

    def test_marker_written_mid_serve_paints_on_next_get(self) -> None:
        self.assertEqual(self._agents(), [])
        self._write_marker({
            "agents": [{"name": "planner", "state": "working"}],
            "jobs": [{"name": "peel-overview-agents-jobs", "state": "open"}],
            "buckets": {"waiting": 1, "ready": 2, "blocked": 0},
            "pulse": {
                "heartbeats": [
                    {"name": "FS Watch", "state": "watching", "last_at": "2026-09-11T10:00:00"}
                ],
                "ticks": [],
                "last_at": "2026-09-11T10:00:00",
            },
        })
        self.assertEqual([a["name"] for a in self._agents()], ["planner"])
        jobs = json.loads(_get(self.port, "/api/overview/jobs")[1])
        self.assertEqual(jobs["buckets"], {"waiting": 1, "ready": 2, "blocked": 0})
        pulse = json.loads(_get(self.port, "/api/overview/pulse")[1])
        by_name = {hb["name"]: hb["state"] for hb in pulse["heartbeats"]}
        self.assertEqual(by_name["FS Watch"], "watching")
        self.assertEqual(by_name["Builder"], "off")

    def test_marker_mutation_is_visible_without_a_bounce(self) -> None:
        self._write_marker({"agents": [{"name": "planner", "state": "working"}]})
        self.assertEqual([a["name"] for a in self._agents()], ["planner"])
        self._write_marker({"agents": [
            {"name": "planner", "state": "idle"},
            {"name": "builder-2", "state": "working"},
        ]})
        self.assertEqual([a["name"] for a in self._agents()], ["planner", "builder-2"])

    def test_marker_removal_returns_to_honest_empty(self) -> None:
        self._write_marker({"agents": [{"name": "planner", "state": "working"}]})
        self.assertEqual(len(self._agents()), 1)
        self.marker.unlink()
        self.assertEqual(self._agents(), [])

    def test_malformed_marker_is_honest_empty_not_500(self) -> None:
        self.marker.write_text("{ not json", encoding="utf-8")
        status, body, _ = _get(self.port, "/api/overview/agents")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["agents"], [])

    def test_demo_worker_alone_still_paints_no_agents(self) -> None:
        self._write_marker({"agents": [{"name": "demo-worker", "state": "working"}]})
        self.assertEqual(self._agents(), [])

    def test_cellar_tip_stays_the_pinned_brew_face(self) -> None:
        """A binder file can't re-voice the Cellar tip."""
        self._write_marker({"cellar_tip": "protocolcity deadbeef"})
        pulse = json.loads(_get(self.port, "/api/overview/pulse")[1])
        self.assertEqual(pulse["cellar_tip"], DEFAULT_CELLAR_TIP)
        self.assertNotIn("protocolcity", pulse["cellar_tip"].lower())


class CellarTipInjectionTests(unittest.TestCase):
    """--cellar-tip is the single voice; omitted, the tip comes from brew."""

    def test_apply_cellar_tip_overrides_state(self) -> None:
        st = empty_state()
        with mock.patch.object(overview_serve, "detect_cellar_tip") as detect:
            overview_serve._apply_cellar_tip(st, "blueprint 0.1.50_7")
        self.assertEqual(st["cellar_tip"], "blueprint 0.1.50_7")
        detect.assert_not_called()

    def test_apply_cellar_tip_detects_when_empty(self) -> None:
        st = empty_state()
        with mock.patch.object(overview_serve, "detect_cellar_tip",
                               return_value="blueprint 0.1.50_9"):
            overview_serve._apply_cellar_tip(st, "")
        self.assertEqual(st["cellar_tip"], "blueprint 0.1.50_9")

    def test_apply_cellar_tip_defaults_when_brew_is_absent(self) -> None:
        st = empty_state()
        with mock.patch("server.overview_state.subprocess.run",
                        side_effect=FileNotFoundError("brew")):
            overview_serve._apply_cellar_tip(st, "")
        self.assertEqual(st["cellar_tip"], DEFAULT_CELLAR_TIP)
        self.assertNotIn("protocolcity", st["cellar_tip"].lower())


class DisposableDeskThroughputSmokeTests(unittest.TestCase):
    """Issue #141: serve a throwaway binder and read the spark through HTTP."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='bp-throughput-')
        self.root = Path(self.temp.name)
        manifest = self.root / 'product' / '.protocolcity' / 'desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'product', 'prefix': 'pc', 'display': 'Product'}))
        data = self.root / 'worklane' / 'worklane' / 'local' / 'data'
        data.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with sqlite3.connect(data / 'product.db') as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, '
                'priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
            )
            conn.execute("INSERT INTO tasks VALUES(1,NULL,'Live','in_progress',1,?,?,'human','Decide')",
                         (recent, json.dumps(['worker:agent'])))
            conn.execute("INSERT INTO tasks VALUES(2,NULL,'Closed','done',1,?,'[]',NULL,NULL)", (recent,))
            conn.execute("INSERT INTO task_events VALUES(1,2,'status_change','done','seat',?)", (recent,))
            conn.execute("INSERT INTO task_comments VALUES(1,2,'Completed: done','seat',?)", (recent,))
        self.httpd, self.port, self.thread = _start_server(empty_state(), binder_root=self.root)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp.cleanup()

    def test_operations_html_hosts_the_spark_under_kpis(self) -> None:
        status, body, _ = _get(self.port, '/')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('id="overview-throughput"', text)
        self.assertLess(text.index('id="metrics"'), text.index('id="overview-throughput"'))
        self.assertLess(text.index('id="overview-throughput"'), text.index('id="overview-unrouted"'))
        self.assertIn('id="for-you-decide"', text)
        self.assertIn('id="overview-decide-more"', text)

    def test_operations_api_returns_last_24h_closes(self) -> None:
        status, body, ctype = _get(self.port, '/api/operations')
        self.assertEqual(status, 200)
        self.assertIn('application/json', ctype)
        payload = json.loads(body)
        self.assertEqual(payload['throughput']['closes'], 1)
        self.assertEqual(payload['throughput']['state'], 'healthy')
        self.assertEqual(payload['throughput']['href'], '/timeline?period=1')
        self.assertEqual(sum(payload['throughput']['hours']), 1)
        self.assertEqual([order['id'] for order in payload['orders']], ['pc-1'])

    def test_operations_html_hosts_portfolio_sparks_on_projects_only(self) -> None:
        status, body, _ = _get(self.port, '/')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('id="projects-compare"', text)
        self.assertIn('id="projects-compare-summary"', text)
        projects = text.split('id="projects-view"', 1)[1].split('id="agents-view"', 1)[0]
        work = text.split('id="work-view"', 1)[1].split('id="projects-view"', 1)[0]
        self.assertIn('id="projects-compare"', projects)
        self.assertNotIn('id="projects-compare"', work)
        self.assertIn('id="overview-throughput"', text)
        self.assertIn('id="agents-floor-spark"', text)
        self.assertIn('id="timeline-activity-chart"', text)
        self.assertIn('id="work-band-act-now"', text)
        self.assertIn('id="calendar-load"', text)
        self.assertIn('id="calendar-doors"', text)
        calendar = text.split('id="calendar-view"', 1)[1].split('id="settings-view"', 1)[0]
        self.assertIn('id="calendar-load"', calendar)
        self.assertNotIn('id="calendar-load"', work)

    def test_operations_api_returns_portfolio_pulse(self) -> None:
        status, body, ctype = _get(self.port, '/api/operations')
        self.assertEqual(status, 200)
        self.assertIn('application/json', ctype)
        payload = json.loads(body)
        portfolio = payload['portfolio']
        self.assertEqual(portfolio['state'], 'healthy')
        row = next(item for item in portfolio['projects'] if item['id'] == 'product')
        self.assertEqual(row['pulse'], 'hot')
        self.assertEqual(row['href'], '/work?project=product')
        self.assertEqual(row['attention_href'], '/work?project=product&attention=any')
        self.assertEqual(row['map_href'], '/map?project=product')
        self.assertGreaterEqual(row['motion'], 1)
        self.assertGreaterEqual(sum(row['hours']), 1)
        self.assertNotIn('/delivery', row['href'])


class DisposableDeskAgentsSparkSmokeTests(unittest.TestCase):
    """Issue #140: serve a throwaway binder and read seat sparks through HTTP."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='bp-agents-spark-')
        self.root = Path(self.temp.name)
        runtime = self.root / 'workforce' / 'local'
        runtime.mkdir(parents=True)
        (runtime / 'ledger').mkdir()
        (runtime / 'roster.json').write_text(json.dumps({
            'workers': {
                'seat': {'display': 'Seat', 'command': ['example-agent'], 'identity': 'seat', 'kind': 'lane'},
                'off-seat': {'display': 'Off', 'command': ['example-agent'], 'identity': 'off-seat', 'kind': 'lane', 'enabled': False},
            }
        }))
        now = datetime.now(timezone.utc)
        (runtime / 'daemon.json').write_text(json.dumps({
            'last_tick': now.isoformat(), 'in_flight': [],
        }))
        stopped = (now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        failed = (now - timedelta(minutes=40)).strftime('%Y-%m-%dT%H:%M:%SZ')
        (runtime / 'ledger' / 'seat.log').write_text(
            f'{stopped} START identity=seat kind=lane budget_secs=1500\n'
            f'{stopped} DONE rc=0\n'
            f'{stopped} STOP reason="single-pass complete"\n'
            f'{failed} START identity=seat kind=lane budget_secs=1500\n'
            f'{failed} ERROR reason="agent exit" rc=1\n'
        )
        self.httpd, self.port, self.thread = _start_server(empty_state(), binder_root=self.root)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp.cleanup()

    def test_operations_html_hosts_the_floor_spark_under_pulse(self) -> None:
        status, body, _ = _get(self.port, '/')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('id="agents-view"', text)
        self.assertIn('id="agents-pulse"', text)
        self.assertIn('id="agents-floor-spark"', text)
        self.assertLess(text.index('id="agents-pulse"'), text.index('id="agents-floor-spark"'))
        self.assertLess(text.index('id="agents-floor-spark"'), text.index('id="agents-next-fire"'))
        self.assertIn('id="overview-throughput"', text)
        self.assertIn('id="timeline-activity-chart"', text)

    def test_operations_api_returns_seat_run_and_fail_sparks(self) -> None:
        status, body, ctype = _get(self.port, '/api/operations')
        self.assertEqual(status, 200)
        self.assertIn('application/json', ctype)
        payload = json.loads(body)
        spark = payload['agents_floor']['sparks']['seat']
        self.assertEqual(spark['runs'], 2)
        self.assertEqual(spark['errors'], 1)
        self.assertEqual(spark['fail_rate'], 0.5)
        self.assertEqual(spark['state'], 'healthy')
        self.assertEqual(sum(spark['hours']), 2)
        self.assertEqual(payload['agents_floor']['error'], 1)
        self.assertEqual(payload['agents_floor']['quiet'], 1)
        off = payload['agents_floor']['sparks']['off-seat']
        self.assertEqual(off['state'], 'empty')
        self.assertEqual(off['runs'], 0)


class DisposableDeskWorkFlowSmokeTests(unittest.TestCase):
    """Issue #147: serve a throwaway binder and read the Work strip."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='bp-workflow-')
        self.root = Path(self.temp.name)
        manifest = self.root / 'product' / '.protocolcity' / 'desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'product', 'prefix': 'pc', 'display': 'Product'}))
        data = self.root / 'worklane' / 'worklane' / 'local' / 'data'
        data.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with sqlite3.connect(data / 'product.db') as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, '
                'priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
            )
            conn.execute(
                "INSERT INTO tasks VALUES(1,NULL,'Ready peel','backlog',1,?,?,'','')",
                (recent, json.dumps(['worker:pepper'])),
            )
            conn.execute(
                "INSERT INTO tasks VALUES(2,NULL,'Live peel','in_progress',1,?,?,'','')",
                (recent, json.dumps(['worker:lili'])),
            )
        roster = self.root / 'workforce' / 'local' / 'roster.json'
        roster.parent.mkdir(parents=True)
        roster.write_text(json.dumps({
            'workers': {
                'pepper': {'kind': 'lane', 'display': 'pepper', 'command': ['true']},
                'lili': {'kind': 'lane', 'display': 'lili', 'command': ['true']},
            }
        }))
        self.httpd, self.port, self.thread = _start_server(empty_state(), binder_root=self.root)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp.cleanup()

    def test_work_html_hosts_the_strip_above_the_bands(self) -> None:
        status, body, _ = _get(self.port, '/work')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('id="work-flow"', text)
        self.assertLess(text.index('id="work-flow"'), text.index('id="work-band-act-now"'))
        self.assertIn('id="work-band-act-now"', text)
        self.assertIn('id="work-band-my-todos"', text)
        self.assertIn('id="work-band-seat-backlog"', text)
        self.assertIn('id="work-calendar-doors"', text)
        self.assertNotIn('n8n', text.lower())

    def test_operations_api_returns_seat_load_and_flow(self) -> None:
        status, body, ctype = _get(self.port, '/api/operations')
        self.assertEqual(status, 200)
        self.assertIn('application/json', ctype)
        payload = json.loads(body)
        flow = payload['work_flow']
        self.assertEqual(flow['state'], 'healthy')
        self.assertGreaterEqual(flow['flow']['Ready'], 1)
        self.assertGreaterEqual(flow['flow']['Live'], 1)
        by_id = {seat['id']: seat for seat in flow['seats']}
        self.assertEqual(by_id['pepper']['ready'], 1)
        self.assertEqual(by_id['pepper']['name'], 'pepper')
        self.assertEqual(by_id['lili']['claimed'], 1)
        self.assertEqual({order['row_status'] for order in payload['orders']}, {'Ready', 'Live'})
        self.assertTrue(all(order.get('board_band') == 'seat_backlog' for order in payload['orders']))


class DisposableDeskMapMotionSmokeTests(unittest.TestCase):
    """Issue #156: Map motion paint on a throwaway desk; neighbor pages stay clean."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='bp-map-motion-')
        self.root = Path(self.temp.name)
        manifest = self.root / 'product' / '.protocolcity' / 'desk-join.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'slug': 'product', 'prefix': 'pc', 'display': 'Product'}))
        data = self.root / 'worklane' / 'worklane' / 'local' / 'data'
        data.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        with sqlite3.connect(data / 'product.db') as conn:
            conn.executescript(
                'CREATE TABLE tasks(id INTEGER, ext_id TEXT, title TEXT, status TEXT, '
                'priority INTEGER, updated_at TEXT, labels TEXT, gate_type TEXT, gate_note TEXT);'
                'CREATE TABLE task_comments(id INTEGER, task_id INTEGER, body TEXT, author TEXT, created_at TEXT);'
                'CREATE TABLE task_events(id INTEGER, task_id INTEGER, event_type TEXT, status TEXT, actor TEXT, created_at TEXT);'
            )
            conn.execute("INSERT INTO tasks VALUES(1,NULL,'Live','in_progress',1,?,?,'human','Decide')",
                         (recent, json.dumps(['worker:agent'])))
            conn.execute("INSERT INTO task_events VALUES(1,1,'status_change','in_progress','seat',?)", (recent,))
            conn.execute("INSERT INTO task_comments VALUES(1,1,'Working: peel','seat',?)", (recent,))
        (self.root / 'product' / 'note.md').write_text('# paper\n')
        self.httpd, self.port, self.thread = _start_server(empty_state(), binder_root=self.root)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp.cleanup()

    def test_map_shell_hosts_motion_stroke_and_doors(self) -> None:
        status, body, _ = _get(self.port, '/map')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertIn('id="map-shell"', text)
        self.assertIn('id="map-browser-list"', text)
        self.assertIn('id="map-project-panel"', text)
        self.assertIn('id="map-dig-trail"', text)
        self.assertIn('/map/css/workspace_map.css', text)
        self.assertIn('/map/js/workspace_map_app.v1.js', text)
        css_status, css_body, _ = _get(self.port, '/map/css/workspace_map.css')
        css = css_body.decode()
        self.assertEqual(css_status, 200)
        self.assertIn('.map-lot.map-motion-live .map-lot-plate', css)
        self.assertIn('.map-lot.map-motion-recent .map-lot-plate', css)
        self.assertIn('.map-lot.map-motion-unavailable .map-lot-plate', css)
        self.assertNotIn('n8n', css.lower())
        js_status, js_body, _ = _get(self.port, '/map/js/map-motion.js')
        self.assertEqual(js_status, 200)
        self.assertIn('classifyNodeMotion', js_body.decode())

    def test_operations_pages_do_not_receive_map_motion(self) -> None:
        status, body, _ = _get(self.port, '/')
        text = body.decode()
        self.assertEqual(status, 200)
        self.assertNotIn('map-motion-live', text)
        self.assertNotIn('id="map-shell"', text)
        self.assertIn('id="overview-throughput"', text)
        self.assertIn('id="work-flow"', text)
        self.assertIn('id="agents-floor-spark"', text)
        self.assertIn('id="projects-compare"', text)
        self.assertIn('id="delivery-ci-spark"', text)
        self.assertIn('id="timeline-activity-chart"', text)
        self.assertIn('id="calendar-load"', text)
        self.assertIn('id="calendar-doors"', text)
        nav = text.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)

    def test_operations_api_still_exposes_truthful_motion_signals(self) -> None:
        status, body, ctype = _get(self.port, '/api/operations')
        self.assertEqual(status, 200)
        self.assertIn('application/json', ctype)
        payload = json.loads(body)
        row = next(item for item in payload['portfolio']['projects'] if item['id'] == 'product')
        self.assertGreaterEqual(row['motion'], 1)
        project = next(item for item in payload['projects'] if item['id'] == 'product')
        self.assertEqual(project['state'], 'available')
        self.assertIsNotNone(project['last_change'])
        self.assertIsNotNone(project['last_change']['at'])
        self.assertNotEqual(row['pulse'], 'unavailable')


if __name__ == "__main__":
    unittest.main()

