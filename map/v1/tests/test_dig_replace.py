"""Dig grammar: REPLACE on sibling, PUSH on nested — the peel's DoD.

Bug: clicking folder B after folder A used to layer/stack dig rings and
push both onto the trail (as if B were A's child). Fix pins:

  digInto(A: root)  → trail=[A], dig=A, fan=A's children
  digInto(B: root)  → trail=[B], dig=B, fan=B's children  (SIBLING SWAP)
  digInto(C: nest)  → trail=[B, C], dig=C, fan=C's children (nested push)

The runtime lives in JavaScript so we string-parse the modules and assert
the shape the peel promises. This is cheap regression coverage, not a
JS-runtime integration test — enough to trip if a future peel drops the
mode arg or reverts to the always-push semantics.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOST = _HERE.parent / "static" / "js" / "workspace_map_app.v1.js"
_VIEW = _HERE.parent / "static" / "js" / "view-state.js"
_PAINT = _HERE.parent / "static" / "js" / "map-paint.js"


class DigReplaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.host = _HOST.read_text(encoding="utf-8")
        self.view = _VIEW.read_text(encoding="utf-8")
        self.paint = _PAINT.read_text(encoding="utf-8")

    def test_view_state_exposes_replace_dig(self) -> None:
        # Root-ring clicks must swap the trail, not push. That needs a
        # first-class store verb — pushing then popping in the host would
        # emit two intermediate frames and re-introduce the layering bug.
        self.assertIsNotNone(
            re.search(r"replaceDig\s*\(node\)\s*\{", self.view),
            "view-state must expose replaceDig for root-level sibling swap",
        )
        # replaceDig collapses the trail down to just this node.
        self.assertIsNotNone(
            re.search(r"state\.trail\s*=\s*\[\s*entry\s*\]", self.view),
            "replaceDig must set trail = [entry], not push",
        )

    def test_dig_into_takes_mode(self) -> None:
        # digInto(node, {mode}) — 'root' replaces, 'nest' pushes.
        self.assertIsNotNone(
            re.search(r"async function digInto\(node,\s*\{\s*mode\s*=\s*'root'", self.host),
            "digInto must accept a mode arg with 'root' as default",
        )
        self.assertIn("viewState.replaceDig(node)", self.host)
        self.assertIn("viewState.setDig(node)", self.host)

    def test_click_handler_routes_mode_by_hit_layer(self) -> None:
        # 'lots' click → root; 'dig-in' click → nest. The mode is derived
        # from hit.layer, the only reliable signal for sibling vs child.
        self.assertIsNotNone(
            re.search(
                r"hit\.layer\s*===\s*'dig-in'\s*\?\s*'nest'\s*:\s*'root'",
                self.host,
            ),
            "click handler must map 'dig-in' → 'nest' and 'lots' → 'root'",
        )

    def test_dig_layer_cleared_before_every_paint(self) -> None:
        # Belt-and-braces: even though paintDigIn calls replaceChildren, the
        # host clears the layer at each call site so a racing second click
        # cannot leave A's ring layered under B's.
        clear_before_paint = re.findall(
            r"clearDigIn\(world\)[\s\S]{0,200}?paintDigIn\(world,",
            self.host,
        )
        # digInto, trail-crumb click, and backspace all repaint the fan —
        # each site must clear first.
        self.assertGreaterEqual(
            len(clear_before_paint), 3,
            "clearDigIn(world) must precede paintDigIn(world, …) at every call site",
        )


class HubCrowdingFollowupTests(unittest.TestCase):
    """Priority 2 follow-up: more radius scaling, tighter label handling."""

    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")

    def test_multi_orbit_when_dense(self) -> None:
        # N > 16 top-level folders spreads onto two concentric orbits so
        # every label doesn't share one arc.
        self.assertIn("HUB_MULTI_ORBIT_MIN", self.paint)
        self.assertIn("HUB_INNER_ORBIT_RATIO", self.paint)
        self.assertIn("folderInnerRadius", self.paint)
        self.assertIsNotNone(
            re.search(r"multiOrbit\s*=\s*folderCount\s*>=\s*HUB_MULTI_ORBIT_MIN", self.paint),
            "multiOrbit must trigger on folderCount >= HUB_MULTI_ORBIT_MIN",
        )

    def test_folder_arc_budget_widened(self) -> None:
        # PR#40 landed FOLDER_ARC_PX=95; this peel widens it so dense
        # binders get more radius per plate on the outer orbit.
        match = re.search(r"FOLDER_ARC_PX\s*=\s*(\d+)", self.paint)
        self.assertIsNotNone(match)
        self.assertGreater(int(match.group(1)), 95,
                           "FOLDER_ARC_PX must widen past the PR#40 baseline (95)")

    def test_stagger_thresholds_tightened(self) -> None:
        # Stagger triggers earlier so 10–15-lot hubs also get relief.
        m_folder = re.search(r"HUB_FOLDER_STAGGER_MIN\s*=\s*(\d+)", self.paint)
        m_file = re.search(r"HUB_FILE_STAGGER_MIN\s*=\s*(\d+)", self.paint)
        self.assertIsNotNone(m_folder)
        self.assertIsNotNone(m_file)
        self.assertLess(int(m_folder.group(1)), 8,
                        "folder stagger threshold must drop below the PR#40 baseline (8)")
        self.assertLess(int(m_file.group(1)), 12,
                        "file stagger threshold must drop below the PR#40 baseline (12)")

    def test_lot_labels_truncate_with_title(self) -> None:
        # Long folder names must clip with an ellipsis and keep the full
        # name reachable via an SVG <title> tooltip.
        self.assertIn("LOT_FOLDER_LABEL_MAX", self.paint)
        self.assertIn("truncateLotLabel", self.paint)
        # Always attach <title> so hover works even when rest labels are hidden.
        self.assertIn("label.appendChild(el('title'", self.paint)


if __name__ == "__main__":
    unittest.main()
