"""Client-side paint invariants for the Overview V1 glass.

Locks the JS-side never-lie DoD from OVERVIEW_MC_EXT.md:

- The Agents tile paints **zero builder anchors** when the wire payload
  carries no outbound URL — a hash fallback (``#cloud-builders``) is a
  fake link, and the DoD says never render one.
- Cold empty (no project title / no charter title, sections or footer)
  keeps ``[data-role="project-card"]`` and ``[data-role="charter-drawer"]``
  ``hidden`` so the shells never leak on screen.
- All-off heartbeats read as silent pulse — no orphan row list of five
  muted ``off`` rows (matches the Writer silent-pulse copy).

The paint functions run in Node against a minimal DOM harness — see
``tests/harness/dom_paint_check.mjs``. If ``node`` is not on PATH the
test skips (the JS assertions are still guarded by the string checks
in test_serve_api.py).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HARNESS = _HERE / "harness" / "dom_paint_check.mjs"


def _run_harness() -> dict:
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not available; skipping DOM paint checks")
    proc = subprocess.run(
        [node, str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"dom harness failed ({proc.returncode}):\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout)


class BuilderAnchorTests(unittest.TestCase):
    """Cloud / remote builders never render as a `#hash` fake link."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_empty_fixture_has_zero_builder_anchors(self) -> None:
        """Empty wire (no cloud/remote entries) → no anchors, links hidden."""
        c = self.cases["empty_agents_links"]
        self.assertEqual(c["anchor_count"], 0)
        self.assertEqual(c["child_count"], 0)
        self.assertTrue(c["hidden"])

    def test_hashless_builders_still_paint_zero_anchors(self) -> None:
        """Entries without a url must not become anchors — no hash fallback."""
        c = self.cases["hashless_builders"]
        self.assertEqual(c["anchor_count"], 0)
        self.assertTrue(c["hidden"])

    def test_real_outbound_url_paints_exactly_one_anchor(self) -> None:
        c = self.cases["real_cloud_only"]
        self.assertEqual(c["anchor_count"], 1)
        self.assertTrue(c["href"].startswith("http"))
        self.assertFalse(c["hidden"])


class ColdEmptyShellTests(unittest.TestCase):
    """Cold empty state keeps project card + charter drawer hidden."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_project_card_hidden_on_cold_empty(self) -> None:
        self.assertTrue(self.cases["empty_project"]["hidden"])

    def test_charter_drawer_hidden_on_cold_empty(self) -> None:
        self.assertTrue(self.cases["empty_charter"]["hidden"])


class SilentPulseTests(unittest.TestCase):
    """All-off heartbeats read as silent pulse — no row list."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_all_off_heartbeats_paint_no_row_list(self) -> None:
        c = self.cases["all_off_pulse"]
        self.assertEqual(c["ul_count"], 0)
        self.assertEqual(c["child_count"], 0)


class JsSourceGuardTests(unittest.TestCase):
    """Regression guards on the JS source — no `#hash` fallback ever."""

    def test_no_hash_fallback_in_builder_link(self) -> None:
        src = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "js"
            / "overview.v1.js"
        ).read_text(encoding="utf-8")
        # The literal template that generated `#cloud-builders` /
        # `#remote-builders` fake anchors must not return.
        self.assertNotIn("#${kind}-builders", src)
        # buildBuilderLink must be able to return null (skip append).
        self.assertIn("return null", src)


class HiddenCssRuleTests(unittest.TestCase):
    """CSS must ensure `[hidden]` collapses to `display: none` unconditionally."""

    def test_css_hides_hidden_elements_hard(self) -> None:
        css = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "css"
            / "overview.css"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"\[hidden\]\s*\{\s*display:\s*none\s*!important",
        )



class JobsCapTests(unittest.TestCase):
    """Jobs tile never walls — cap + blocked→ready→waiting + N more."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_visible_rows_capped(self) -> None:
        c = self.cases["jobs_cap"]
        self.assertLessEqual(c["row_count"], 8)
        self.assertEqual(c["row_count"], 8)
        self.assertEqual(c["more_text"], "4 more")

    def test_rank_blocked_ready_waiting(self) -> None:
        c = self.cases["jobs_rank"]
        self.assertEqual(c["visible"], 8)
        self.assertEqual(c["more"], 4)
        order = c["order"]
        self.assertEqual(order[:4], ["blocked"] * 4)
        self.assertEqual(order[4:7], ["ready"] * 3)
        self.assertEqual(order[7:], ["waiting"])

    def test_buckets_still_paint_full_counts(self) -> None:
        counts = self.cases["jobs_cap"]["bucket_counts"]
        self.assertEqual(counts, ["100", "3", "12"])


class CalendarGlassPaintTests(unittest.TestCase):
    """Calendar V1 glass DoD — empty copy + title · when · source · status."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_empty_paints_no_events(self) -> None:
        c = self.cases["calendar_empty"]
        self.assertEqual(c["empty_text"], "No events")
        self.assertEqual(c["empty_class"], "ov-empty")
        self.assertEqual(c["ul_count"], 0)
        self.assertEqual(c["child_count"], 1)
        self.assertEqual(c["range"], "")

    def test_populated_rows_show_title_when_source_status(self) -> None:
        c = self.cases["calendar_rows"]
        self.assertEqual(c["row_count"], 3)
        self.assertEqual(c["empty_count"], 0)
        self.assertEqual(c["range"], "2026-09-07 → 2026-09-13")
        classes = [f["className"] for f in c["fields"][0]]
        self.assertEqual(
            classes,
            [
                "ov-cal-event-title",
                "ov-cal-event-when",
                "ov-cal-event-source",
                "ov-cal-event-state",
            ],
        )
        titles = [row[0]["text"] for row in c["fields"]]
        self.assertEqual(titles, ["Standup", "Ship peel", "Filed note"])
        sources = [row[2]["text"] for row in c["fields"]]
        self.assertEqual(sources, ["routine", "WO", "manual"])
        states = [row[3]["text"] for row in c["fields"]]
        self.assertEqual(states, ["scheduled", "due", "done"])

    def test_unknown_source_state_fall_back(self) -> None:
        fields = self.cases["calendar_fallback"]["fields"]
        by_class = {f["className"]: f for f in fields}
        self.assertEqual(by_class["ov-cal-event-source"]["text"], "manual")
        self.assertEqual(by_class["ov-cal-event-state"]["text"], "scheduled")


class SettingsGlassPaintTests(unittest.TestCase):
    """Settings V1 glass DoD — Desk path + brew-face Cellar tip."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_desk_paints_binder_path_and_local_desk(self) -> None:
        c = self.cases["settings_desk"]
        self.assertEqual(c["binder_path"], "/tmp/local-desk")
        self.assertEqual(c["desk_label"], "Local desk")
        self.assertEqual(c["cellar_tip"], "blueprint 0.1.50_12")
        self.assertNotIn("sha", c["cellar_tip"].lower())

    def test_empty_cellar_tip_does_not_invent_a_version(self) -> None:
        c = self.cases["settings_cellar_empty"]
        self.assertEqual(c["cellar_tip"], "")


if __name__ == "__main__":
    unittest.main()
