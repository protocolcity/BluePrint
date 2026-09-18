"""Issue #156 — Map paint hosts apply motion stroke; doors stay; no n8n canvas."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PAINT = _HERE.parent / "static" / "js" / "map-paint.js"
_HOST = _HERE.parent / "static" / "js" / "workspace_map_app.v1.js"
_MOTION = _HERE.parent / "static" / "js" / "map-motion.js"
_CSS = _HERE.parent / "static" / "css" / "workspace_map.css"
_HTML = _HERE.parent / "static" / "workspace_map.html"
_HARNESS = _HERE / "harness" / "map_motion_check.mjs"


class MapMotionPaintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")
        self.host = _HOST.read_text(encoding="utf-8")
        self.motion = _MOTION.read_text(encoding="utf-8")
        self.css = _CSS.read_text(encoding="utf-8")
        self.html = _HTML.read_text(encoding="utf-8")

    def test_classifier_is_pure_and_honest(self) -> None:
        self.assertIn("export function classifyNodeMotion", self.motion)
        self.assertIn("export function indexNodeState", self.motion)
        self.assertIn("stroke: 'none'", self.motion)
        self.assertIn("!== 'available'", self.motion)

    def test_lots_and_dig_and_focus_apply_stroke_class(self) -> None:
        self.assertIn("motionClassName(motion)", self.paint)
        self.assertIn("data-motion", self.paint)
        self.assertIn("motionClassName", self.paint)
        self.assertIn("nodeState", self.paint.split("export function paintDigIn")[1][:400])
        self.assertIn("motion = null", self.paint.split("export function paintProjectFocus")[1][:240])

    def test_host_indexes_portfolio_motion_from_operations(self) -> None:
        self.assertIn("indexNodeState(detail.projects, detail.portfolio)", self.host)
        self.assertIn("motion:nodeState[snap.project.relPath]", self.host.replace(" ", ""))
        self.assertIn("nodeState", self.host)
        self.assertIn("motionClassName(state.motion)", self.host)

    def test_css_paints_stroke_not_a_chart_or_canvas(self) -> None:
        self.assertIn(".map-lot.map-motion-live .map-lot-plate", self.css)
        self.assertIn(".map-lot.map-motion-recent .map-lot-plate", self.css)
        self.assertIn(".map-lot.map-motion-unavailable .map-lot-plate", self.css)
        self.assertIn("stroke-dasharray: 3 3", self.css)
        self.assertIn("#map-browser-list button.map-motion-live", self.css)
        self.assertNotIn("n8n", self.css.lower())
        self.assertNotIn("histogram", self.css.lower())

    def test_doors_and_ten_page_shell_stay(self) -> None:
        self.assertIn('id="map-browser-list"', self.html)
        self.assertIn('id="map-project-panel"', self.html)
        self.assertIn('id="map-dig-trail"', self.html)
        self.assertIn("createHitRouter", self.host)
        self.assertNotIn("n8n", self.html.lower())
        self.assertNotIn("WORKFLOWS", self.html)
        self.assertNotIn("drag-wire", self.host)
        self.assertNotIn("node graph", self.host.lower())

    def test_classifier_harness(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        result = subprocess.run(
            [node, str(_HARNESS)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Pc1561MapMotionVerifyTests(unittest.TestCase):
    """pc-1561 — Map motion verify Cap. Stroke stays the live pulse."""

    def setUp(self) -> None:
        self.html = _HTML.read_text(encoding="utf-8")
        self.css = _CSS.read_text(encoding="utf-8")
        self.paint = _PAINT.read_text(encoding="utf-8")
        self.host = _HOST.read_text(encoding="utf-8")
        self.motion = _MOTION.read_text(encoding="utf-8")

    def test_stroke_still_reads_as_activity_not_static_chrome(self) -> None:
        self.assertIn("pc-1561", self.css)
        self.assertIn(".map-lot.map-motion-live .map-lot-plate", self.css)
        self.assertIn("stroke-width: 1.5", self.css)
        self.assertIn(".map-lot-plate { fill: var(--map-lot); stroke: #1e2128; stroke-width: 1; }", self.css)
        self.assertIn("classifyNodeMotion", self.motion)
        self.assertIn("LIVE_MOTION = 3", self.motion)

    def test_map_shell_has_no_wo_wall(self) -> None:
        html = self.html
        css = self.css
        self.assertIn("no wo-tape", css)
        for leak in (
            'id="wo-tape"',
            'id="work-list"',
            'id="work-band-act-now"',
            'id="work-band-my-todos"',
            'id="work-band-seat-backlog"',
            'id="work-flow"',
            'id="for-you-decide"',
            ".wo-tape",
            "#work-list",
            "#work-flow",
        ):
            self.assertNotIn(leak, html)
            self.assertNotIn(leak, css)
            self.assertNotIn(leak, self.paint)
            self.assertNotIn(leak, self.host)

    def test_map_shell_has_no_overview_dump(self) -> None:
        html = self.html
        for leak in (
            'id="overview-throughput"',
            'id="overview-face-chips"',
            'id="overview-exec"',
            'id="overview-unrouted"',
            'id="metrics"',
            "Act now",
        ):
            self.assertNotIn(leak, html)
            self.assertNotIn(leak, self.paint)
            self.assertNotIn(leak, self.host)

    def test_does_not_invent_density_overlay_or_steal_pos(self) -> None:
        blob = self.html + self.css + self.paint + self.host + self.motion
        self.assertNotIn("density-overlay", blob.lower())
        self.assertNotIn("heatmap", blob.lower())
        self.assertNotIn("histogram", self.css.lower())
        self.assertNotIn("n8n", blob.lower())
        self.assertNotIn("POS", blob)
        self.assertNotIn("point-of-sale", blob.lower())

    def test_ten_map_a_pages_stay_frozen(self) -> None:
        self.assertIn('id="map-browser-list"', self.html)
        self.assertIn('id="map-project-panel"', self.html)
        self.assertIn('id="map-dig-trail"', self.html)
        self.assertIn('id="map-view-options"', self.html)
        self.assertNotIn("id=\"map-density\"", self.html)
        self.assertNotIn("id=\"map-overlay\"", self.html)
        self.assertNotIn("WORKFLOWS", self.html)


if __name__ == "__main__":
    unittest.main()
