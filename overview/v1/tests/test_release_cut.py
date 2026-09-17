"""Public cut 0.1.50 — metadata and artifact hygiene (pc-1468 / #145)."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
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

    def test_planted_host_mcp_json_is_excluded_from_wheel(self):
        """*.json package-data must not ship a planted host .mcp.json."""
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / 'candidate'
            shutil.copytree(ROOT / 'protocolcity', candidate / 'protocolcity',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for name in ('pyproject.toml', 'README.md', 'MANIFEST.in'):
                src = ROOT / name
                if src.is_file():
                    shutil.copy2(src, candidate / name)
            planted = candidate / 'protocolcity' / '.mcp.json'
            # Build the forbidden host token at runtime so this test file
            # itself never stores a personal-path fingerprint.
            fingerprint = '/'.join(('', 'Users', 'someone', ''))
            planted.write_text('{"mcpServers":{"host":{"command":"%sbin/python"}}}' % fingerprint)
            dist = Path(tmp) / 'dist'
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                 '--wheel-dir', str(dist), str(candidate)],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wheel = next(dist.glob('*.whl'))
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                self.assertFalse(any(Path(name).name == '.mcp.json' for name in names), names)
                for name in names:
                    if name.endswith(('.json', '.py', '.md', '.toml')):
                        body = archive.read(name).decode('utf-8', errors='replace')
                        self.assertNotIn(fingerprint, body, name)
