"""Server-side tests for the Overview V1 local-only stubs.

Locks the honest-empty default and the dogfood invariants from
docs/specs/OVERVIEW_INTENT.md §Dogfood note:

- Cold serve returns empty agents / jobs / pulse.
- `demo-worker` alone on the registry paints `No agents` (empty wire), not
  a fake busy tile.
- A real `working` agent employs the desk; only then does the tile paint.

Run with:  pytest overview/v1/tests
       or:  python3 -m unittest overview.v1.tests.test_overview_state
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

from server.overview_state import (  # noqa: E402
    empty_state,
    load_agents,
    load_from_fixture,
    load_jobs,
    load_pulse,
)

FIXTURES = _HERE / "fixtures"


class EmptyStateTests(unittest.TestCase):
    def test_cold_serve_is_honest_empty(self) -> None:
        st = empty_state()
        self.assertEqual(st["agents"], [])
        self.assertEqual(st["jobs"], [])
        self.assertEqual(st["pulse"], {"ticks": [], "last_at": None})

    def test_load_agents_default(self) -> None:
        self.assertEqual(load_agents(), {"agents": []})

    def test_load_jobs_default(self) -> None:
        self.assertEqual(load_jobs(), {"jobs": []})

    def test_load_pulse_default(self) -> None:
        self.assertEqual(load_pulse(), {"ticks": [], "last_at": None})


class FixtureLoadingTests(unittest.TestCase):
    def test_empty_fixture_matches_cold_state(self) -> None:
        st = load_from_fixture(FIXTURES / "empty.json")
        self.assertEqual(st["agents"], [])
        self.assertEqual(st["jobs"], [])
        self.assertEqual(st["pulse"]["ticks"], [])
        self.assertIsNone(st["pulse"]["last_at"])

    def test_demo_worker_alone_paints_no_agents(self) -> None:
        """INTENT §Dogfood note: demo-worker on the registry with no real
        employed event still paints `No agents`."""
        st = load_from_fixture(FIXTURES / "demo_worker_only.json")
        self.assertEqual(st["agents"], [])
        self.assertEqual(load_agents(st), {"agents": []})

    def test_populated_fixture_paints_real_rows(self) -> None:
        st = load_from_fixture(FIXTURES / "populated.json")
        names = [a["name"] for a in st["agents"]]
        self.assertIn("planner", names)
        self.assertIn("reviewer", names)
        self.assertIn("runner", names)
        self.assertIn("watcher", names)
        # demo-worker never appears in the populated fixture — but if it
        # did, it would only survive because a real `working` row is also
        # present (see next test).
        self.assertNotIn("demo-worker", names)
        self.assertEqual(len(st["jobs"]), 2)
        self.assertEqual(len(st["pulse"]["ticks"]), 2)
        self.assertEqual(st["pulse"]["last_at"], "2026-09-10T09:12:00")

    def test_demo_worker_kept_when_real_working_agent_present(self) -> None:
        """If a real working agent employs the desk, demo-worker is honest
        registry content and stays."""
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


class WirePayloadShapeTests(unittest.TestCase):
    """The three endpoints must always return the V1-locked keys, even
    on cold empty. This keeps the client's honest-empty paint honest."""

    def test_agents_payload_has_agents_key(self) -> None:
        self.assertIn("agents", load_agents())

    def test_jobs_payload_has_jobs_key(self) -> None:
        self.assertIn("jobs", load_jobs())

    def test_pulse_payload_has_both_keys(self) -> None:
        payload = load_pulse()
        self.assertIn("ticks", payload)
        self.assertIn("last_at", payload)


if __name__ == "__main__":
    unittest.main()
