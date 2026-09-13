"""D2 live rendering (pc-1470): the Map sidebar summary must not rebuild
on a heartbeat-only re-fetch — see harness/map_shell_inplace_check.mjs."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

_HARNESS = Path(__file__).resolve().parent / "harness" / "map_shell_inplace_check.mjs"


class MapShellInPlaceTests(unittest.TestCase):
    def test_unchanged_snapshot_leaves_summary_nodes_untouched(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        result = subprocess.run(
            [node, str(_HARNESS)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
