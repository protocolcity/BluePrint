"""Execute calendar agenda helpers against disposable in-memory fixtures."""
from pathlib import Path
import shutil
import subprocess
import unittest


class CalendarAgendaTests(unittest.TestCase):
    def test_merge_groups_and_clock_labels(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        harness = Path(__file__).parent / "harness" / "calendar_agenda_check.mjs"
        result = subprocess.run(
            [node, str(harness)], capture_output=True, text=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Calendar agenda:', result.stdout)
