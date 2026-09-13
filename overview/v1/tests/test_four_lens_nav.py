"""Four-lens nav locks — Overview · Map · Calendar · Settings on one origin.

Per Eli GO step-1 spec and docs/specs/OVERVIEW_CALENDAR_SETTINGS.md:

- Every lens chip resolves to a real 200 page (no dead pills, no 404).
- Calendar paints ``No events`` on cold empty.
- Settings paints its four groups (Desk · Appearance · Privacy · About).
- Map dig is embedded (same origin), sharing the binder passed on the CLI.
- Local-only APIs stay honest: /api/calendar/events → empty, /api/settings/desk
  → binder/desk hints, /api/map/tree → 200 (empty when no binder).
- Overview footer no longer paints five permanent Off cells (fake heartbeats).
"""
from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

import serve as bp_serve  # noqa: E402
from server.overview_state import empty_state  # noqa: E402


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(state: dict, binder: Path | None = None):
    bp_serve.Handler.state = state
    bp_serve.Handler.binder_overview = None
    bp_serve.Handler.binder_root = binder
    port = _pick_port()
    httpd = bp_serve.ThreadingHTTPServer(("127.0.0.1", port), bp_serve.Handler)
    thread = threading.Thread(
        target=httpd.serve_forever, name=f"bp-desk-{port}", daemon=True
    )
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


class FourLensNavTests(unittest.TestCase):
    """Every lens chip in the top nav is a real page (200), not a dead pill."""

    def setUp(self) -> None:
        st = empty_state()
        self.httpd, self.port, self.thread = _start_server(st)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_overview_root_paints(self) -> None:
        status, body, ctype = _get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn('id="overview-view"', body.decode())
        self.assertIn('data-page="overview"', body.decode())

    def test_map_lens_paints(self) -> None:
        status, body, ctype = _get(self.port, "/map")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        text = body.decode("utf-8")
        # Map shell is mounted at /map — asset paths rewritten to /map/…
        self.assertIn('id="map-shell"', text)
        self.assertIn('/map/css/workspace_map.css', text)
        self.assertIn('/map/js/workspace_map_app.v1.js', text)

    def test_map_static_assets_serve(self) -> None:
        css_status, css_body, _ = _get(self.port, "/map/css/workspace_map.css")
        self.assertEqual(css_status, 200)
        self.assertGreater(len(css_body), 0)
        js_status, js_body, _ = _get(self.port, "/map/js/workspace_map_app.v1.js")
        self.assertEqual(js_status, 200)
        self.assertGreater(len(js_body), 0)

    def test_calendar_lens_paints(self) -> None:
        status, body, _ = _get(self.port, "/calendar")
        self.assertEqual(status, 200)
        text=body.decode()
        self.assertIn('id="calendar-view"', text)
        self.assertIn('id="schedule-list"', text)
        self.assertIn('id="event-list"', text)
        self.assertIn('id="calendar-today"', text)
        self.assertIn('id="calendar-next"', text)
        self.assertIn('id="calendar-past"', text)
        self.assertIn('data-page="calendar"', text)

    def test_settings_lens_paints(self) -> None:
        status, body, _ = _get(self.port, "/settings")
        self.assertEqual(status, 200)
        text=body.decode()
        self.assertIn('id="settings-view"', text)
        self.assertIn('id="refresh-preference"', text)
        self.assertIn('id="motion-preference"', text)
        self.assertIn('data-page="settings"', text)

    def test_calendar_and_settings_share_overview_css(self) -> None:
        """One dark PC voice — Calendar and Settings load the shared
        overview.css so tokens (Surface · Voice · State · Focus) stay
        consistent across every lens."""
        _, cal_body, _ = _get(self.port, "/calendar")
        _, set_body, _ = _get(self.port, "/settings")
        self.assertIn('href="/css/overview.css"', cal_body.decode("utf-8"))
        self.assertIn('href="/css/overview.css"', set_body.decode("utf-8"))

    def test_calendar_never_speaks_map_verbs(self) -> None:
        """Label lock: Calendar never uses dig/lot/hub/fan/trail verbs
        (spec §Label lock)."""
        import re

        _, body, _ = _get(self.port, "/calendar")
        text = body.decode("utf-8").lower()
        for verb in ("dig", "lot", "hub", "fan", "trail", "md-viewer", "crumb"):
            pattern = re.compile(rf"\b{re.escape(verb)}\b")
            self.assertIsNone(
                pattern.search(text),
                f"Calendar HTML must not use Map verb {verb!r}",
            )

    def test_settings_never_speaks_map_verbs(self) -> None:
        """Label lock: Settings never uses Map verbs. ``binder`` is legal
        here — Desk group names the binder path (IA spec), unlike Overview."""
        import re

        _, body, _ = _get(self.port, "/settings")
        text = body.decode("utf-8").lower()
        for verb in ("dig", "lot", "hub", "fan", "trail", "md-viewer", "crumb"):
            pattern = re.compile(rf"\b{re.escape(verb)}\b")
            self.assertIsNone(
                pattern.search(text),
                f"Settings HTML must not use Map verb {verb!r}",
            )

    def test_settings_separates_display_from_runtime(self) -> None:
        _, body, _ = _get(self.port, "/settings")
        text=body.decode()
        self.assertLess(text.index('Display preferences'),text.index('Workspace and application'))
        self.assertIn('These do not change agents or services.', text)
        self.assertIn('Running build', text)

    def test_calendar_and_settings_do_not_duplicate_overview_tiles(self) -> None:
        """Settings / Calendar are lenses — no Agents · Jobs · Pulse tiles."""
        for path in ("/calendar", "/settings"):
            _, body, _ = _get(self.port, path)
            text = body.decode("utf-8")
            self.assertNotIn('id="overview-shell"', text)
            self.assertNotIn("No agents", text)
            self.assertNotIn("No open jobs", text)

    def test_shared_css_is_dark_pc_only(self) -> None:
        """Glass DoD: dark PC tokens, no cream / LLC palette in the token set.

        Header comments may say "no cream" — only the ``:root`` values count.
        """
        status, body, _ = _get(self.port, "/css/overview.css")
        self.assertEqual(status, 200)
        css = body.decode("utf-8")
        self.assertIn("--ov-bg: #0f1114", css)
        root = css.split(":root", 1)[-1].split("}", 1)[0].lower()
        self.assertNotIn("cream", root)
        self.assertNotIn("llc", root)
        self.assertNotIn("oneseollc", root)


class LocalTruthApiTests(unittest.TestCase):
    """Local-only APIs paint honest empty by default; binder truth when present."""

    def setUp(self) -> None:
        st = empty_state()
        self.httpd, self.port, self.thread = _start_server(st, binder=None)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_calendar_events_empty_by_default(self) -> None:
        status, body, ctype = _get(self.port, "/api/calendar/events")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["range"], "")

    def test_settings_desk_reports_local_voice_without_binder(self) -> None:
        _, body, _ = _get(self.port, "/api/settings/desk")
        payload = json.loads(body)
        self.assertEqual(payload["binder_path"], "on this desk")
        self.assertEqual(payload["desk_label"], "Local desk")

    def test_map_tree_serves_honest_empty_without_binder(self) -> None:
        """/api/map/tree must 200 even without a binder — the /map lens
        must never dead-pill on a bare desk."""
        status, body, ctype = _get(self.port, "/api/map/tree")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        self.assertEqual(payload["lots"], [])


class BinderTruthTests(unittest.TestCase):
    """--binder DIR seeds local truth from <binder>/.blueprint/."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="bp-desk-binder-")
        self.binder = Path(self.tmp)
        (self.binder / ".blueprint").mkdir()
        # Seed a real overview.json (fixture-shaped)
        (self.binder / ".blueprint" / "overview.json").write_text(
            json.dumps({
                "agents": [{"name": "planner", "state": "working"}],
                "jobs": [{"name": "peel/foo", "state": "open"}],
                "buckets": {"waiting": 1, "ready": 0, "blocked": 0},
                "pulse": {
                    "heartbeats": [
                        {"name": "FS Watch", "state": "watching", "last_at": "2026-09-11T10:00:00"}
                    ],
                    "ticks": [],
                    "last_at": "2026-09-11T10:00:00",
                },
                "cellar_tip": "blueprint 0.1.50_9",
            }),
            encoding="utf-8",
        )
        calendar_fixture = _HERE / "fixtures" / "calendar.json"
        (self.binder / ".blueprint" / "calendar.json").write_text(
            calendar_fixture.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        # Add a lot so /api/map/tree returns something.
        (self.binder / "peels").mkdir()
        (self.binder / "peels" / "note.md").write_text("# hi", encoding="utf-8")

        from server.overview_state import load_from_binder
        st = load_from_binder(self.binder)
        self.httpd, self.port, self.thread = _start_server(st, binder=self.binder)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_agents_from_binder(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/agents")
        payload = json.loads(body)
        self.assertEqual([a["name"] for a in payload["agents"]], ["planner"])

    def test_jobs_from_binder(self) -> None:
        _, body, _ = _get(self.port, "/api/overview/jobs")
        payload = json.loads(body)
        self.assertEqual(payload["buckets"]["waiting"], 1)
        self.assertEqual([j["name"] for j in payload["jobs"]], ["peel/foo"])

    def test_calendar_events_from_binder(self) -> None:
        _, body, _ = _get(self.port, "/api/calendar/events")
        payload = json.loads(body)
        titles = [e["title"] for e in payload["events"]]
        self.assertEqual(titles, ["Standup", "Ship peel", "Filed note"])
        states = {e["state"] for e in payload["events"]}
        self.assertEqual(states, {"scheduled", "due", "done"})
        notes = [e.get("notes") for e in payload["events"]]
        self.assertEqual(notes, ["Local desk check-in.", "Glass DoD lock.", ""])
        self.assertEqual(payload["range"], "2026-09-07 → 2026-09-13")

    def test_settings_desk_reports_binder_path(self) -> None:
        _, body, _ = _get(self.port, "/api/settings/desk")
        payload = json.loads(body)
        self.assertEqual(payload["binder_path"], str(self.binder.resolve()))
        self.assertEqual(payload["desk_label"], "Local desk")

    def test_map_tree_reads_binder(self) -> None:
        _, body, _ = _get(self.port, "/api/map/tree")
        payload = json.loads(body)
        names = [lot["name"] for lot in payload["lots"] if not lot.get("hidden")]
        self.assertIn("peels", names)


class FooterHonestyTests(unittest.TestCase):
    """paintFooter (in overview.v1.js) must skip permanent-off heartbeats
    so cold serves don't paint five fake heartbeat cells."""

    def test_overview_js_only_paints_lit_heartbeats(self) -> None:
        src = (
            _OVERVIEW_V1 / "static" / "js" / "overview.v1.js"
        ).read_text(encoding="utf-8")
        # paintFooter must filter to lit heartbeats — never paint a
        # permanent row of five `off` cells (spec: hide fake permanent Off
        # footer rows until real signals exist).
        # Match on the specific idiom the filter uses.
        self.assertIn(".filter(", src)
        self.assertIn('!== "off"', src)
        # Sanity: the loop that renders footer cells iterates over `lit`,
        # not the raw heartbeats array.
        self.assertRegex(src, r"for \(const hb of lit\)")


if __name__ == "__main__":
    unittest.main()
