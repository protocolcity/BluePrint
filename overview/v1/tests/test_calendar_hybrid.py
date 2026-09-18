"""pc-1563: Calendar Hybrid soft-conflict marks + outbound honesty."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


class CalendarHybridHarnessTests(unittest.TestCase):
    def test_locked_scenes_honesty_weight_and_day_cap(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        harness = Path(__file__).parent / "harness" / "calendar_hybrid_check.mjs"
        result = subprocess.run(
            [node, str(harness)],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "TZ": "America/Chicago"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scenes"], ["A", "B2", "C1", "D1"])
        self.assertEqual(payload["chips"]["B2"], ["You win"])
        self.assertEqual(payload["day_cap"]["remainder"], 2)
        self.assertTrue(all("honesty" in chip for chip in payload["outbound"]))
