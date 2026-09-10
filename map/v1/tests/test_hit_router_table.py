"""Hit-Layer SoT table lock.

The router lives in JavaScript (map-hit-router.js), so we can't easily run
the DOM classifier under Python. This test pins the *table order* by
parsing the JS module and asserting the row order the Glass spec locks:

    md-viewer → chrome → dig-in → hub → lots → empty

If someone re-orders those rows (or invents a seventh) this test fails.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROUTER = _HERE.parent / "static" / "js" / "map-hit-router.js"

EXPECTED_LAYERS = ("md-viewer", "chrome", "dig-in", "hub", "lots", "empty")

# Line comments in JS use `//` — we skip them so a comment string cannot
# accidentally satisfy the assertions.
_COMMENT_LINE = re.compile(r"^\s*//")


def _stripped_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if _COMMENT_LINE.match(line):
            continue
        out.append(line)
    return out


class HitRouterTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = _ROUTER.read_text(encoding="utf-8")
        self.code_lines = _stripped_lines(self.source)
        self.code_body = "\n".join(self.code_lines)

    def test_exported_layer_list_matches_spec(self) -> None:
        match = re.search(r"HIT_LAYERS\s*=\s*Object\.freeze\(\[([^\]]+)\]\)", self.code_body)
        self.assertIsNotNone(match, "HIT_LAYERS export missing")
        raw = match.group(1)
        names = tuple(re.findall(r"'([^']+)'", raw))
        self.assertEqual(names, EXPECTED_LAYERS)

    def test_row_order_in_classifier(self) -> None:
        # Order of the ordered checks in classifyDescriptor pins the priority
        # (md-viewer wins over chrome, chrome wins over dig-in, …).
        priority_flags = [
            "mdViewerOpen",
            "overChrome",
            "overDigIn",
            "overHub",
            "overLot",
        ]
        positions = []
        for flag in priority_flags:
            idx = self.code_body.find(f"desc.{flag}")
            self.assertNotEqual(idx, -1, f"classifyDescriptor missing check for {flag}")
            positions.append(idx)
        self.assertEqual(positions, sorted(positions), "priority flags out of order")

    def test_no_seventh_row_snuck_in(self) -> None:
        # Guard rail — if someone adds a row like fast-cover or folder-chrome
        # back into the router, this fails and forces a Glass amendment.
        forbidden = ["fast-cover", "folder-chrome", "err-veil", "outline"]
        for token in forbidden:
            self.assertNotIn(f"'{token}'", self.code_body, f"forbidden hit layer: {token}")

    def test_kind_by_layer_covers_every_row(self) -> None:
        match = re.search(r"KIND_BY_LAYER\s*=\s*Object\.freeze\(\{([^}]+)\}\)", self.code_body, re.DOTALL)
        self.assertIsNotNone(match, "KIND_BY_LAYER missing")
        body = match.group(1)
        for layer in EXPECTED_LAYERS:
            self.assertIn(layer, body, f"KIND_BY_LAYER missing '{layer}'")


if __name__ == "__main__":
    unittest.main()
