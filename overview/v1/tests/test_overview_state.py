"""Server-side tests for the Overview V1 local-only stubs.

Locks the honest-empty default and the dogfood invariants from
docs/specs/OVERVIEW_INTENT.md §Dogfood note + the full-glass extensions
(01c · 02c · 03d) from docs/specs/OVERVIEW_MC_EXT.md:

- Cold serve returns empty agents / jobs / pulse with honest defaults.
- `demo-worker` alone on the registry paints `No agents` (empty wire).
- Cloud / remote builders come back in their own arrays, never as agents.
- Jobs carry Waiting · Ready · Blocked buckets; zeros PASS.
- Pulse carries named local heartbeats (missing → `off`, never green).
- Cellar tip is the brew face; project + charter default to `{}`.

Run with:  pytest overview/v1/tests
       or:  python3 -m unittest overview.v1.tests.test_overview_state
"""
from __future__ import annotations

import sys
import subprocess
import unittest
from unittest import mock
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

from server import overview_state  # noqa: E402
from server.overview_state import (  # noqa: E402
    DEFAULT_CELLAR_TIP,
    HEARTBEAT_NAMES,
    empty_state,
    load_agents,
    load_charter,
    load_from_fixture,
    load_jobs,
    load_project,
    load_pulse,
)

FIXTURES = _HERE / "fixtures"


class EmptyStateTests(unittest.TestCase):
    def test_cold_serve_is_honest_empty(self) -> None:
        st = empty_state()
        self.assertEqual(st["agents"], [])
        self.assertEqual(st["cloud_builders"], [])
        self.assertEqual(st["remote_builders"], [])
        self.assertEqual(st["jobs"], [])
        self.assertEqual(st["buckets"], {"waiting": 0, "ready": 0, "blocked": 0})
        self.assertEqual(st["pulse"], {"heartbeats": [], "ticks": [], "last_at": None})
        self.assertEqual(st["cellar_tip"], DEFAULT_CELLAR_TIP)
        self.assertEqual(st["project"], {})
        self.assertEqual(st["charter"], {})

    def test_load_agents_default_has_link_keys(self) -> None:
        payload = load_agents()
        self.assertEqual(payload["agents"], [])
        self.assertEqual(payload["cloud_builders"], [])
        self.assertEqual(payload["remote_builders"], [])

    def test_load_jobs_default_buckets_zero(self) -> None:
        payload = load_jobs()
        self.assertEqual(payload["jobs"], [])
        self.assertEqual(payload["buckets"], {"waiting": 0, "ready": 0, "blocked": 0})

    def test_load_pulse_default_names_five_local_heartbeats(self) -> None:
        payload = load_pulse()
        names = [hb["name"] for hb in payload["heartbeats"]]
        # Every named local heartbeat renders — a missing heartbeat paints
        # ``off`` (muted), never working green.
        self.assertEqual(list(HEARTBEAT_NAMES), names)
        for hb in payload["heartbeats"]:
            self.assertEqual(hb["state"], "off")
            self.assertIsNone(hb["last_at"])
        self.assertEqual(payload["cellar_tip"], DEFAULT_CELLAR_TIP)
        self.assertIsNone(payload["last_at"])
        self.assertEqual(payload["ticks"], [])

    def test_load_project_default_empty(self) -> None:
        self.assertEqual(load_project(), {})

    def test_load_charter_default_empty(self) -> None:
        self.assertEqual(load_charter(), {})


class FixtureLoadingTests(unittest.TestCase):
    def test_empty_fixture_matches_cold_state(self) -> None:
        st = load_from_fixture(FIXTURES / "empty.json")
        self.assertEqual(st["agents"], [])
        self.assertEqual(st["cloud_builders"], [])
        self.assertEqual(st["jobs"], [])
        self.assertEqual(st["buckets"], {"waiting": 0, "ready": 0, "blocked": 0})
        self.assertEqual(st["pulse"]["ticks"], [])
        self.assertEqual(st["pulse"]["heartbeats"], [])
        self.assertIsNone(st["pulse"]["last_at"])
        self.assertEqual(st["project"], {})
        self.assertEqual(st["charter"], {})

    def test_demo_worker_alone_paints_no_agents(self) -> None:
        """INTENT §Dogfood note: demo-worker on the registry with no real
        employed event still paints `No agents`."""
        st = load_from_fixture(FIXTURES / "demo_worker_only.json")
        self.assertEqual(st["agents"], [])
        self.assertEqual(load_agents(st)["agents"], [])

    def test_populated_fixture_paints_real_rows(self) -> None:
        st = load_from_fixture(FIXTURES / "populated.json")
        names = [a["name"] for a in st["agents"]]
        self.assertIn("planner", names)
        self.assertIn("reviewer", names)
        self.assertIn("runner", names)
        self.assertIn("watcher", names)
        self.assertNotIn("demo-worker", names)
        # Cloud + remote come back in their own arrays — links, not agents.
        self.assertEqual(len(st["cloud_builders"]), 1)
        self.assertEqual(len(st["remote_builders"]), 1)
        self.assertNotIn("Packet Foundry", names)
        self.assertNotIn("Mesh Warden", names)
        self.assertEqual(st["buckets"], {"waiting": 1, "ready": 2, "blocked": 0})
        self.assertEqual(len(st["pulse"]["heartbeats"]), 5)
        self.assertEqual(len(st["jobs"]), 2)
        self.assertEqual(st["pulse"]["last_at"], "2026-09-11T10:21:34")

    def test_full_glass_fixture_carries_project_and_charter(self) -> None:
        st = load_from_fixture(FIXTURES / "full_glass.json")
        # Peer tiles preserved — agents present alongside the drawer.
        self.assertEqual(len(st["agents"]), 4)
        # Cloud builders live as outbound links, never mixed into agents.
        cloud_names = [b["name"] for b in st["cloud_builders"]]
        self.assertIn("Packet Foundry", cloud_names)
        self.assertIn("Mesh Warden", cloud_names)
        self.assertIn("Stack Relay", cloud_names)
        agent_names = [a["name"] for a in st["agents"]]
        for cloud in cloud_names:
            self.assertNotIn(cloud, agent_names)
        # Project card: on this desk voice, honest badges (Consume off).
        project = st["project"]
        self.assertEqual(project["title"], "Protocol City")
        self.assertEqual(project["path_hint"], "on this desk")
        self.assertTrue(project["badges"]["local_write"])
        self.assertFalse(project["badges"]["consume"])
        self.assertTrue(project["badges"]["upstream"])
        self.assertTrue(project["badges"]["local_only"])
        # Charter drawer sections + never-lie footer.
        charter = st["charter"]
        headings = [s["heading"] for s in charter["sections"]]
        self.assertIn("Purpose", headings)
        self.assertIn("Scope", headings)
        self.assertIn("Invariants", headings)
        self.assertIn("not private Protocol City install", charter["footer"])

    def test_demo_worker_kept_when_real_working_agent_present(self) -> None:
        import json
        import tempfile

        payload = {
            "agents": [
                {"name": "demo-worker", "state": "idle"},
                {"name": "planner", "state": "working"},
            ],
            "jobs": [],
            "pulse": {"ticks": [], "last_at": None},
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(payload, fh)
            path = Path(fh.name)
        try:
            st = load_from_fixture(path)
            names = [a["name"] for a in st["agents"]]
            self.assertIn("demo-worker", names)
            self.assertIn("planner", names)
        finally:
            path.unlink(missing_ok=True)

    def test_unknown_agent_state_coerced_to_idle(self) -> None:
        import json
        import tempfile

        payload = {
            "agents": [{"name": "mystery", "state": "confused"}],
            "jobs": [],
            "pulse": {"ticks": [], "last_at": None},
        }
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(payload, fh)
            path = Path(fh.name)
        try:
            st = load_from_fixture(path)
            self.assertEqual(st["agents"][0]["state"], "idle")
        finally:
            path.unlink(missing_ok=True)

    def test_missing_fixture_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_from_fixture(FIXTURES / "does-not-exist.json")


class HeartbeatHonestyTests(unittest.TestCase):
    def test_partial_heartbeats_fill_missing_with_off(self) -> None:
        state = empty_state()
        state["pulse"]["heartbeats"] = [
            {"name": "FS Watch", "state": "watching", "last_at": "2026-09-11T10:00:00"},
        ]
        payload = load_pulse(state)
        by_name = {hb["name"]: hb for hb in payload["heartbeats"]}
        self.assertEqual(by_name["FS Watch"]["state"], "watching")
        for absent in ("Builder", "Cellar", "Index", "Sync"):
            self.assertEqual(by_name[absent]["state"], "off")
            self.assertIsNone(by_name[absent]["last_at"])

    def test_unknown_heartbeat_state_coerced_to_off(self) -> None:
        state = empty_state()
        state["pulse"]["heartbeats"] = [
            {"name": "Cellar", "state": "green-because-i-said-so"},
        ]
        payload = load_pulse(state)
        cellar = next(hb for hb in payload["heartbeats"] if hb["name"] == "Cellar")
        self.assertEqual(cellar["state"], "off")

    def test_cellar_tip_never_reads_from_pulse_rows(self) -> None:
        """Cellar tip is a top-level state field — never smuggled from a
        heartbeat row masquerading as a version string."""
        state = empty_state()
        state["cellar_tip"] = "blueprint 0.1.50_9"
        payload = load_pulse(state)
        self.assertEqual(payload["cellar_tip"], "blueprint 0.1.50_9")


class ProjectHonestyTests(unittest.TestCase):
    def test_project_path_hint_defaults_to_on_this_desk(self) -> None:
        state = empty_state()
        state["project"] = {"title": "Foo", "project": "foo"}
        payload = load_project(state)
        self.assertEqual(payload["path_hint"], "on this desk")

    def test_project_badges_default_to_off(self) -> None:
        state = empty_state()
        state["project"] = {"title": "Foo"}
        payload = load_project(state)
        self.assertEqual(
            payload["badges"],
            {
                "local_write": False,
                "consume": False,
                "upstream": False,
                "local_only": False,
            },
        )

    def test_consume_badge_is_off_by_default(self) -> None:
        """Consume ≠ MANAGED — the badge is lit only when the fixture says so."""
        state = empty_state()
        state["project"] = {"title": "Foo", "badges": {"local_write": True}}
        payload = load_project(state)
        self.assertFalse(payload["badges"]["consume"])


class WirePayloadShapeTests(unittest.TestCase):
    def test_agents_payload_keys(self) -> None:
        payload = load_agents()
        self.assertIn("agents", payload)
        self.assertIn("cloud_builders", payload)
        self.assertIn("remote_builders", payload)

    def test_jobs_payload_keys(self) -> None:
        payload = load_jobs()
        self.assertIn("jobs", payload)
        self.assertIn("buckets", payload)
        for key in ("waiting", "ready", "blocked"):
            self.assertIn(key, payload["buckets"])

    def test_pulse_payload_keys(self) -> None:
        payload = load_pulse()
        for key in ("heartbeats", "ticks", "last_at", "cellar_tip"):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()


def _completed(returncode: int, stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["brew", "list", "--versions", "blueprint"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class CellarTipDetectTests(unittest.TestCase):
    """Brew face detection — brew is never required for the suite to pass."""

    def test_detect_falls_back_when_brew_is_missing(self) -> None:
        with mock.patch("server.overview_state.subprocess.run",
                        side_effect=FileNotFoundError("brew")):
            self.assertEqual(overview_state.detect_cellar_tip(), DEFAULT_CELLAR_TIP)

    def test_detect_falls_back_when_brew_exits_nonzero(self) -> None:
        with mock.patch("server.overview_state.subprocess.run",
                        return_value=_completed(1, "")):
            self.assertEqual(overview_state.detect_cellar_tip(), DEFAULT_CELLAR_TIP)

    def test_detect_falls_back_on_timeout(self) -> None:
        with mock.patch("server.overview_state.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("brew", 2.0)):
            self.assertEqual(overview_state.detect_cellar_tip(), DEFAULT_CELLAR_TIP)

    def test_detect_parses_brew_list_versions(self) -> None:
        with mock.patch("server.overview_state.subprocess.run",
                        return_value=_completed(0, "blueprint 0.1.50_9\n")):
            self.assertEqual(overview_state.detect_cellar_tip(), "blueprint 0.1.50_9")

    def test_detect_takes_the_newest_keg(self) -> None:
        with mock.patch("server.overview_state.subprocess.run",
                        return_value=_completed(0, "blueprint 0.1.50_8 0.1.50_9\n")):
            self.assertEqual(overview_state.detect_cellar_tip(), "blueprint 0.1.50_9")

    def test_detect_never_paints_a_private_sha(self) -> None:
        """A SHA-shaped token is refused — the tip stays the brew face."""
        with mock.patch("server.overview_state.subprocess.run",
                        return_value=_completed(0, "blueprint c35db4f5\n")):
            tip = overview_state.detect_cellar_tip()
        self.assertEqual(tip, DEFAULT_CELLAR_TIP)
        self.assertNotIn("protocolcity", tip.lower())

