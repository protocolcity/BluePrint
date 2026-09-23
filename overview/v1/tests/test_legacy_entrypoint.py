"""The compatibility package must not start a competing application."""
from pathlib import Path
import subprocess
import sys
import unittest


class LegacyEntrypointTests(unittest.TestCase):
    def test_historical_server_refuses_before_loading_host_configuration(self):
        root = Path(__file__).resolve().parents[3]
        result = subprocess.run([sys.executable, '-m', 'suite.serve'], cwd=root,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('blueprint serve --foreground --root WORKSPACE', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
