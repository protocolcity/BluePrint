"""Public cut 0.1.50 — metadata and artifact hygiene (pc-1468 / #145)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        'check_release_artifacts', ROOT / 'scripts' / 'check_release_artifacts.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicCutMetadataTests(unittest.TestCase):
    def setUp(self):
        self.check = _load_checker()

    def test_both_packages_declare_cut_and_engine_pins(self):
        failures = self.check.check_metadata()
        self.assertEqual(failures, [])

    def test_release_notes_have_no_secrets_or_host_paths(self):
        self.assertEqual(self.check.scan_release_notes(), [])

    def test_public_tests_have_no_host_path_fingerprints(self):
        self.assertEqual(self.check.scan_public_tests(), [])

    def test_templates_use_workspace_root_token(self):
        self.assertEqual(self.check.scan_source_templates(), [])


class PublicCutArtifactTests(unittest.TestCase):
    def test_sdist_and_wheel_exclude_host_mcp_runtime_and_paths(self):
        check = _load_checker()
        self.assertEqual(check.main([]), 0, 'sdist/wheel dry-run must stay public-clean')
