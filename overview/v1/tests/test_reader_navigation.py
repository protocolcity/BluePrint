"""Execute reader navigation against disposable in-memory browser fixtures."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ReaderNavigationTests(unittest.TestCase):
    def test_navigation_and_security(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        harness = Path(__file__).parent / "harness" / "reader_navigation_check.mjs"
        result = subprocess.run(
            [node, str(harness)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
