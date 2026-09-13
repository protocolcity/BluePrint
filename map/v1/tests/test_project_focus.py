"""Focused exploded project — branch composition (MAP_FOCUSED_PROJECT.md,
pc-1492). project-focus.js is pure data composition (no DOM), so it is
exercised directly under Node — see harness/project_focus_check.mjs for the
realistic busy / empty / unavailable / stale fixtures.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

_HARNESS = Path(__file__).resolve().parent / "harness" / "project_focus_check.mjs"


class ProjectFocusCompositionTests(unittest.TestCase):
    def test_branch_composition_matches_sources_contract(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        result = subprocess.run(
            [node, str(_HARNESS)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
