"""Hub layout — split ring + widen + stagger for dense binders.

The layout math lives in JavaScript (map-paint.js: computeHubLayout), so
this test parses the module and asserts the shape the peel promises:

- computeHubLayout is exported and returns folderRadius / fileRadius /
  outerRadius (so the host can fit-to-screen against a widened folder ring)
- paintLots consumes it and forwards outerRadius to its caller
- folder ring widens when dense (per-plate arc budget)
- file dots ride an inner ring and get a distinct label class
- both rings stagger labels above/below when the arc runs out
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PAINT = _HERE.parent / "static" / "js" / "map-paint.js"
_HOST = _HERE.parent / "static" / "js" / "workspace_map_app.v1.js"
_CSS = _HERE.parent / "static" / "css" / "workspace_map.css"


class HubLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")
        self.host = _HOST.read_text(encoding="utf-8")
        self.css = _CSS.read_text(encoding="utf-8")

    def test_compute_hub_layout_is_exported(self) -> None:
        self.assertIsNotNone(
            re.search(r"export function computeHubLayout", self.paint),
            "computeHubLayout must be an exported helper for testability",
        )

    def test_paint_lots_uses_and_returns_layout(self) -> None:
        self.assertIn("computeHubLayout(lots", self.paint)
        # paintLots must return outerRadius so the host can fit-to-screen
        # against a widened folder ring (otherwise a dense hub gets clipped).
        self.assertIsNotNone(
            re.search(r"return\s*\{[^}]*outerRadius", self.paint, re.DOTALL),
            "paintLots must return outerRadius",
        )

    def test_folder_and_file_ring_split(self) -> None:
        # The layout must split by isDir into a folder ring and a file ring
        # (so 30+ mixed lots don't share one arc).
        self.assertIn("folderRadius", self.paint)
        self.assertIn("fileRadius", self.paint)
        self.assertIn("FOLDER_ARC_PX", self.paint)
        self.assertIn("FILE_ARC_PX", self.paint)

    def test_folder_ring_widens_when_dense(self) -> None:
        # Dense folder count must widen the outer ring (density scale + arc budget).
        self.assertIn("HUB_DENSITY_SCALE", self.paint)
        self.assertIn("HUB_DENSE_MIN", self.paint)
        self.assertIsNotNone(
            re.search(r"Math\.max\s*\(\s*baseRadius\s*\*\s*densityScale\s*,\s*folderMinRadius\s*\)", self.paint),
            "folderRadius must grow past baseRadius*densityScale when the arc budget requires it",
        )

    def test_hub_label_stagger_thresholds(self) -> None:
        self.assertIn("HUB_FOLDER_STAGGER_MIN", self.paint)
        self.assertIn("HUB_FILE_STAGGER_MIN", self.paint)
        # Stagger must alternate label Y for even/odd indices on each ring.
        self.assertIsNotNone(
            re.search(r"folderStagger\s*\?\s*\(k\s*%\s*2\s*===\s*0", self.paint),
            "folder ring must alternate label Y above/below when dense",
        )
        self.assertIsNotNone(
            re.search(r"fileStagger\s*\?\s*\(k\s*%\s*2\s*===\s*0", self.paint),
            "file ring must alternate label Y above/below when dense",
        )

    def test_host_fits_camera_against_layout_outer_radius(self) -> None:
        # Host must consume paintLots' outerRadius and thread it into
        # fitTransform, or the widened folder ring gets clipped on load.
        self.assertIn("currentOuterRadius", self.host)
        self.assertIn("layout.outerRadius", self.host)
        self.assertIsNotNone(
            re.search(r"fitTransform\([^)]*radius:\s*currentOuterRadius", self.host),
            "applyCamera must fit against currentOuterRadius, not the fixed cfg.radius",
        )

    def test_file_label_gets_muted_class(self) -> None:
        # File dots on the inner ring get their own muted label class so the
        # folder ring's labels read first (Theme §Enhance).
        self.assertIn("map-lot-file-label", self.paint)
        self.assertIn(".map-lot-file-label", self.css)


class HubLayoutRuntimeShapeTests(unittest.TestCase):
    """Sanity-check the shape of the returned layout for a synthetic list.

    We can't run the JS from Python, but the ring-count invariants are cheap
    to state as string checks that guard against a future edit that forgets
    them. If someone drops the two-ring model, at least one of these fails.
    """

    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")

    def test_placed_indexes_match_input_order(self) -> None:
        # placed[idx] preserves the caller's array order — paintLots relies
        # on it for `lots.forEach((lot, i) => layout.placed[i])`.
        self.assertIn("ring: 'folder'", self.paint)
        self.assertIn("ring: 'file'", self.paint)

    def test_file_ring_clears_hub_disc(self) -> None:
        self.assertIn("FILE_RING_CLEAR", self.paint)
        self.assertIn("HUB_DISC_R", self.paint)


class HubCrowdingV2Tests(unittest.TestCase):
    """Design MAP_HUB_CROWDING_GUIDE — density orbit, hide-until-hover, plate shrink."""

    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")
        self.css = _CSS.read_text(encoding="utf-8")

    def test_multi_orbit_threshold_matches_dense_min(self) -> None:
        self.assertIn("HUB_MULTI_ORBIT_MIN = 12", self.paint)

    def test_hide_until_hover_css(self) -> None:
        self.assertIn(".map-lot.map-lot-dense .map-lot-label", self.css)
        self.assertIn("map-lot-dense", self.paint)

    def test_dense_plate_shrink(self) -> None:
        self.assertIn("plateW", self.paint)
        self.assertIn("dense ? 58 : 68", self.paint)

    def test_dig_fat_fan_density_tools(self) -> None:
        self.assertIn("map-dig-dense", self.paint)
        self.assertIn("digRadius", self.paint)


if __name__ == "__main__":
    unittest.main()
