"""End-to-end smoke: cold boot → paint hub+lots → dig into a lot → children.

Simulates what the JS host does at boot by driving the Python server
directly. If this test regresses, the shell has drifted (a peel accidentally
touched the tree contract) and the six V1 DoD rows are at risk.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MAP_V1 = _HERE.parent
sys.path.insert(0, str(_MAP_V1))

from server.map_tree import build_tree, children_at, render_file  # noqa: E402

FIXTURE = _HERE / "fixtures" / "binder-01"


class ColdBootDigSmoke(unittest.TestCase):
    def test_dod5_hub_and_lots_paint(self) -> None:
        # DoD 1 — hub + top-level lots come back on cold boot.
        tree = build_tree(FIXTURE)
        self.assertEqual(tree["binder"]["name"], "binder-01")
        self.assertGreaterEqual(len(tree["lots"]), 3, "at least recipes / blueprint / hub.md")

    def test_dod1_dig_into_lot(self) -> None:
        # DoD 3 — click on recipes lot returns its children.
        payload = children_at(FIXTURE, "recipes")
        self.assertEqual(payload["relPath"], "recipes")
        names = [c["name"] for c in payload["children"]]
        self.assertIn("README.md", names)

    def test_dod2_md_open_from_reader(self) -> None:
        # DoD 4 — reader opens an md file server-rendered.
        html, ctype = render_file(FIXTURE, "recipes/README.md", render="html")
        self.assertIn("<h1>", html)
        self.assertIn("recipes", html.lower())
        self.assertIn("text/html", ctype)

    def test_dig_trail_is_linear(self) -> None:
        # Digging further into a subfolder returns its subfolder listing.
        payload = children_at(FIXTURE, "blueprint")
        names = [c["name"] for c in payload["children"]]
        self.assertIn("CHARTER.md", names)


if __name__ == "__main__":
    unittest.main()
