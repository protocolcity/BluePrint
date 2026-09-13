"""D2 review fix: Map must fall back to a 60s poll when the change feed is
down, same as Overview — see harness/map_shell_fallback_check.mjs."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

_HARNESS = Path(__file__).resolve().parent / "harness" / "map_shell_fallback_check.mjs"


class MapShellFallbackTests(unittest.TestCase):
    def test_map_shell_polls_every_60s_when_stream_unavailable(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        result = subprocess.run(
            [node, str(_HARNESS)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
