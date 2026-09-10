"""Smoke tests for the FS/git binder projection (map/v1/server/map_tree.py).

Run with:  python3 -m unittest map.v1.tests.test_map_tree
Or:        python3 map/v1/tests/test_map_tree.py
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


class BuildTreeTests(unittest.TestCase):
    def test_binder_descriptor(self) -> None:
        tree = build_tree(FIXTURE)
        self.assertEqual(tree["binder"]["name"], "binder-01")
        self.assertTrue(tree["binder"]["path"].endswith("binder-01"))

    def test_top_lots_include_dirs_and_root_md(self) -> None:
        tree = build_tree(FIXTURE)
        names = [lot["name"] for lot in tree["lots"]]
        self.assertIn("recipes", names)
        self.assertIn("blueprint", names)
        self.assertIn("hub.md", names)
        self.assertIn("notes", names)

    def test_hub_md_marked_has_md(self) -> None:
        tree = build_tree(FIXTURE)
        recipes = next(lot for lot in tree["lots"] if lot["name"] == "recipes")
        notes = next(lot for lot in tree["lots"] if lot["name"] == "notes")
        hub_md = next(lot for lot in tree["lots"] if lot["name"] == "hub.md")
        self.assertTrue(recipes["hasMd"], "recipes/ has README.md")
        self.assertFalse(notes["hasMd"], "notes/ has no .md file inside")
        self.assertTrue(hub_md["hasMd"], ".md files are hasMd=true")
        self.assertFalse(hub_md["isDir"])

    def test_hidden_dot_files_flagged(self) -> None:
        tmp = FIXTURE / ".hidden-note"
        tmp.write_text("hidden\n", encoding="utf-8")
        try:
            tree = build_tree(FIXTURE)
            names = [(lot["name"], lot["hidden"]) for lot in tree["lots"]]
            self.assertIn((".hidden-note", True), names)
        finally:
            tmp.unlink(missing_ok=True)


class ChildrenAtTests(unittest.TestCase):
    def test_children_of_recipes(self) -> None:
        payload = children_at(FIXTURE, "recipes")
        names = [c["name"] for c in payload["children"]]
        self.assertIn("README.md", names)

    def test_relpath_escape_rejected(self) -> None:
        with self.assertRaises(ValueError):
            children_at(FIXTURE, "../..")

    def test_absolute_relpath_rejected(self) -> None:
        with self.assertRaises(ValueError):
            children_at(FIXTURE, "/etc")

    def test_missing_directory_returns_empty(self) -> None:
        payload = children_at(FIXTURE, "does-not-exist")
        self.assertEqual(payload["children"], [])


class RenderFileTests(unittest.TestCase):
    def test_markdown_renders_html(self) -> None:
        body, ctype = render_file(FIXTURE, "hub.md", render="html")
        self.assertIn("text/html", ctype)
        self.assertIn("<h1>", body)

    def test_non_md_returns_plain(self) -> None:
        body, ctype = render_file(FIXTURE, "notes/scratch.txt", render="html")
        self.assertIn("text/plain", ctype)
        self.assertIn("non-md file", body)

    def test_escape_rejected(self) -> None:
        with self.assertRaises(ValueError):
            render_file(FIXTURE, "../secret.md")


if __name__ == "__main__":
    unittest.main()
