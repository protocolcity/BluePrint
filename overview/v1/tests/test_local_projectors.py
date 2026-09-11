"""Phase-B WorkForce / WorkLane projectors under --binder.

Locks the CoS feed contract:

- Agents from ``<binder>/.protocolcity/workforce/local/roster.json``
  (twin ``workforce/local/roster.json``). Daemon is runtime polish only.
- Jobs from ``<binder>/worklane/worklane/local/data/<slug>.db`` (Desk HTTP
  optional, short timeout, fail → SQLite / empty).
- ``overview.json`` wins when present.
- Absent / malformed → honest empty. Never invent seats or WOs.
- ``demo-worker`` alone still paints No agents.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_OVERVIEW_V1 = _HERE.parent
sys.path.insert(0, str(_OVERVIEW_V1))

from server import overview_state  # noqa: E402
from server.local_projectors import (  # noqa: E402
    classify_task,
    project_agents,
    project_jobs,
    project_local_overview,
)
from server.overview_state import (  # noqa: E402
    DEFAULT_CELLAR_TIP,
    BinderOverview,
    load_agents,
    load_from_binder,
    load_jobs,
)

FIXTURES = _HERE / "fixtures"


class ClassifyTaskTests(unittest.TestCase):
    def test_backlog_is_waiting(self) -> None:
        self.assertEqual(classify_task("backlog"), "waiting")

    def test_in_progress_is_ready(self) -> None:
        self.assertEqual(classify_task("in_progress"), "ready")

    def test_in_review_is_waiting(self) -> None:
        self.assertEqual(classify_task("in_review"), "waiting")

    def test_terminal_omitted(self) -> None:
        self.assertIsNone(classify_task("done"))
        self.assertIsNone(classify_task("canceled"))

    def test_blocked_only_when_fields_say_so(self) -> None:
        self.assertEqual(
            classify_task("backlog", gate_type="human"), "blocked"
        )
        self.assertEqual(
            classify_task("backlog", labels=["blocked"]), "blocked"
        )
        # No invent — plain backlog stays waiting.
        self.assertEqual(classify_task("backlog", labels=["worker:you"]), "waiting")


class AbsentStoresTests(unittest.TestCase):
    def test_empty_binder_projects_empty(self) -> None:
        binder = FIXTURES / "binder_absent_stores"
        binder.mkdir(exist_ok=True)
        self.assertEqual(project_agents(binder), [])
        jobs, buckets = project_jobs(binder)
        self.assertEqual(jobs, [])
        self.assertEqual(buckets, {"waiting": 0, "ready": 0, "blocked": 0})
        st = load_from_binder(binder)
        self.assertEqual(st["agents"], [])
        self.assertEqual(st["jobs"], [])
        self.assertEqual(st["buckets"], {"waiting": 0, "ready": 0, "blocked": 0})


class RosterProjectorTests(unittest.TestCase):
    def test_roster_fixture_paints_agents(self) -> None:
        binder = FIXTURES / "binder_workforce_roster"
        agents = project_agents(binder)
        names = {a["name"] for a in agents}
        self.assertIn("Planner · Desk", names)
        self.assertIn("Reviewer · Desk", names)
        self.assertIn("demo-worker", names)
        by_name = {a["name"]: a["state"] for a in agents}
        # daemon in_flight → working; others idle. Never invent.
        self.assertEqual(by_name["Planner · Desk"], "working")
        self.assertEqual(by_name["Reviewer · Desk"], "idle")

    def test_binder_overview_applies_demo_worker_filter_with_peers(self) -> None:
        """With real peers present, demo-worker may remain on the wire."""
        binder = FIXTURES / "binder_workforce_roster"
        st = load_from_binder(binder)
        names = [a["name"] for a in st["agents"]]
        self.assertIn("Planner · Desk", names)
        self.assertIn("Reviewer · Desk", names)
        # planner is working → employed → demo-worker kept.
        self.assertIn("demo-worker", names)

    def test_demo_worker_only_paints_no_agents(self) -> None:
        binder = FIXTURES / "binder_demo_worker_only"
        raw = project_agents(binder)
        self.assertEqual([a["name"] for a in raw], ["demo-worker"])
        st = load_from_binder(binder)
        self.assertEqual(st["agents"], [])
        self.assertEqual(load_agents(st)["agents"], [])


class OverviewJsonWinsTests(unittest.TestCase):
    def test_overview_json_wins_over_roster(self) -> None:
        binder = FIXTURES / "binder_overview_wins"
        st = load_from_binder(binder)
        names = [a["name"] for a in st["agents"]]
        self.assertEqual(names, ["planted-planner"])
        self.assertNotIn("roster-only-agent", names)
        self.assertEqual(st["jobs"][0]["name"], "planted-job")
        self.assertEqual(st["buckets"], {"waiting": 1, "ready": 0, "blocked": 0})


class WorkLaneSqliteTests(unittest.TestCase):
    def test_sqlite_projects_open_jobs_and_buckets(self) -> None:
        binder = FIXTURES / "binder_worklane_jobs"
        # Force SQLite path — Desk may or may not be up; mock Desk miss.
        with mock.patch(
            "server.local_projectors._project_jobs_via_desk", return_value=None
        ):
            jobs, buckets = project_jobs(binder)
        names = {j["name"] for j in jobs}
        self.assertIn("Ready-ish in progress", names)
        self.assertIn("Waiting on backlog", names)
        self.assertIn("Human gated", names)
        self.assertNotIn("Already done", names)
        self.assertNotIn("Canceled work", names)
        self.assertEqual(buckets["ready"], 1)
        self.assertEqual(buckets["waiting"], 1)
        self.assertEqual(buckets["blocked"], 1)

    def test_desk_http_failure_degrades_empty_when_no_sqlite(self) -> None:
        binder = FIXTURES / "binder_absent_stores"
        with mock.patch(
            "server.local_projectors._http_get_json", return_value=None
        ):
            jobs, buckets = project_jobs(binder)
        self.assertEqual(jobs, [])
        self.assertEqual(buckets, {"waiting": 0, "ready": 0, "blocked": 0})


class BinderOverviewLiveProjectorTests(unittest.TestCase):
    def test_roster_change_is_visible_without_bounce(self) -> None:
        tmp = tempfile.mkdtemp(prefix="bp-phaseb-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        binder = Path(tmp)
        local = binder / ".protocolcity" / "workforce" / "local"
        local.mkdir(parents=True)
        roster = local / "roster.json"
        roster.write_text(
            json.dumps({"workers": {"alpha": {"kind": "lane", "identity": "alpha"}}}),
            encoding="utf-8",
        )
        src = BinderOverview(binder, cellar_tip=DEFAULT_CELLAR_TIP)
        first = src.current()
        self.assertEqual([a["name"] for a in first["agents"]], ["alpha"])
        self.assertEqual(first["cellar_tip"], DEFAULT_CELLAR_TIP)

        roster.write_text(
            json.dumps({
                "workers": {
                    "alpha": {"kind": "lane", "identity": "alpha"},
                    "beta": {"kind": "job", "identity": "beta"},
                }
            }),
            encoding="utf-8",
        )
        second = src.current()
        self.assertEqual([a["name"] for a in second["agents"]], ["alpha", "beta"])

    def test_overview_json_appearing_takes_over(self) -> None:
        tmp = tempfile.mkdtemp(prefix="bp-phaseb-ov-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        binder = Path(tmp)
        local = binder / ".protocolcity" / "workforce" / "local"
        local.mkdir(parents=True)
        (local / "roster.json").write_text(
            json.dumps({"workers": {"alpha": {"kind": "lane", "identity": "alpha"}}}),
            encoding="utf-8",
        )
        src = BinderOverview(binder, cellar_tip=DEFAULT_CELLAR_TIP)
        self.assertEqual([a["name"] for a in src.current()["agents"]], ["alpha"])
        bp = binder / ".blueprint"
        bp.mkdir()
        (bp / "overview.json").write_text(
            json.dumps({"agents": [{"name": "planted", "state": "working"}]}),
            encoding="utf-8",
        )
        self.assertEqual([a["name"] for a in src.current()["agents"]], ["planted"])


class TwinRosterPathTests(unittest.TestCase):
    def test_workforce_local_twin_is_used(self) -> None:
        tmp = tempfile.mkdtemp(prefix="bp-phaseb-twin-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        binder = Path(tmp)
        twin = binder / "workforce" / "local"
        twin.mkdir(parents=True)
        (twin / "roster.json").write_text(
            json.dumps({"workers": {"twin-hand": {"kind": "lane", "identity": "twin-hand"}}}),
            encoding="utf-8",
        )
        agents = project_agents(binder)
        self.assertEqual([a["name"] for a in agents], ["twin-hand"])


if __name__ == "__main__":
    unittest.main()


class AgentDisplayNameTests(unittest.TestCase):
    """Design soft watch: prefer roster display over identity for paint."""

    def test_prefers_display_when_present(self) -> None:
        import tempfile, shutil, json
        from pathlib import Path
        from server.local_projectors import project_agents

        tmp = tempfile.mkdtemp(prefix="bp-display-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        roster = Path(tmp) / ".protocolcity" / "workforce" / "local"
        roster.mkdir(parents=True)
        (roster / "roster.json").write_text(json.dumps({
            "workers": {
                "chief-of-staff": {
                    "kind": "job",
                    "identity": "chief-of-staff",
                    "display": "Chief of Staff",
                }
            }
        }), encoding="utf-8")
        agents = project_agents(Path(tmp))
        self.assertEqual(agents, [{"name": "Chief of Staff", "state": "idle"}])

    def test_demo_worker_keeps_identity_wire_name(self) -> None:
        import tempfile, shutil, json
        from pathlib import Path
        from server.local_projectors import project_agents

        tmp = tempfile.mkdtemp(prefix="bp-demo-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        roster = Path(tmp) / ".protocolcity" / "workforce" / "local"
        roster.mkdir(parents=True)
        (roster / "roster.json").write_text(json.dumps({
            "workers": {
                "demo-worker": {
                    "kind": "lane",
                    "identity": "demo-worker",
                    "display": "Demo Lane",
                }
            }
        }), encoding="utf-8")
        agents = project_agents(Path(tmp))
        self.assertEqual(agents, [{"name": "demo-worker", "state": "idle"}])
