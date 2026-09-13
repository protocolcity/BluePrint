"""Exercise the authoring mirror and actual wheel planting without engines."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]


class TemplatePackagingTests(unittest.TestCase):
    def test_mirror_matches_authoring_tree(self):
        source = ROOT / 'templates'
        mirror = ROOT / 'protocolcity/templates'
        expected = {p.relative_to(source): p.read_bytes()
                    for p in source.rglob('*') if p.is_file()}
        actual = {p.relative_to(mirror): p.read_bytes()
                  for p in mirror.rglob('*') if p.is_file()}
        self.assertEqual(expected.keys(), actual.keys())
        for name in expected:
            with self.subTest(template=str(name)):
                self.assertEqual(expected[name], actual[name])

    def test_sync_detects_repairs_and_preserves_unrecognized_files(self):
        spec = importlib.util.spec_from_file_location('template_sync', ROOT / 'scripts/templates_sync.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            source, mirror = Path(tmp) / 'source', Path(tmp) / 'mirror'
            source.mkdir(); mirror.mkdir()
            (source / 'worker.md').write_text('current bounded process')
            (mirror / 'worker.md').write_text('stale refill instructions')
            self.assertFalse(module.sync(source, mirror, check=True))
            self.assertEqual((mirror / 'worker.md').read_text(), 'stale refill instructions')
            self.assertTrue(module.sync(source, mirror))
            self.assertTrue(module.sync(source, mirror, check=True))
            (mirror / 'unique.md').write_text('preserve me')
            self.assertFalse(module.sync(source, mirror))
            self.assertEqual((mirror / 'unique.md').read_text(), 'preserve me')

    def test_wheel_plants_current_papers_without_source_or_engines(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = base / 'candidate'
            candidate.mkdir()
            # Build outside the checkout. Only package source and build inputs;
            # no repository, runtime data or source-template fallback is present.
            shutil.copytree(ROOT / 'protocolcity', candidate / 'protocolcity',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for name in ('pyproject.toml', 'README.md'):
                shutil.copy2(ROOT / name, candidate / name)
            dist = base / 'dist'
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                 '--wheel-dir', str(dist), str(candidate)],
                cwd=base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            installed = base / 'installed'
            with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel:
                wheel.extractall(installed)
            expected = {str(p.relative_to(ROOT / 'templates')): p.read_text()
                        for p in (ROOT / 'templates').rglob('*.md')}
            (base / 'expected.json').write_text(json.dumps(expected))
            env = dict(os.environ, PYTHONPATH=str(installed),
                       WORKSPACE_ROOT=str(base / 'workspace'),
                       BLUEPRINT_WORKSPACE=str(base / 'workspace'))
            # Deny network and SQLite access before importing any product module.
            # Plant through the same functions used by found/hire/seed, with no
            # engine calls, source tree fallback or dependency on the host roster.
            program = r'''
import json, socket, sqlite3
from pathlib import Path

def deny(*args, **kwargs):
    raise AssertionError('planting attempted engine/network access')
socket.socket.connect = deny
socket.create_connection = deny
sqlite3.connect = deny
from protocolcity import found, seed_ops
from protocolcity.cli import plant_hire_papers, _fill_hire_placeholders
base = Path.cwd()
expected = json.loads((base / 'expected.json').read_text())
assert found._templates_dir() == base / 'installed/protocolcity/templates'
assert seed_ops._templates_dir() == found._templates_dir()
for name, text in expected.items():
    assert found._template(name).read_text() == text, name
workspace = base / 'workspace'
workspace.mkdir()
project = workspace / 'sample'
project.mkdir()
for kind in ('worker', 'director'):
    contract, prompt, _ = plant_hire_papers(str(project), 'sample-' + kind,
                                           template=kind, store='sample')
    for path, suffix in ((contract, 'CONTRACT.md'), (prompt, 'prompt.md')):
        body = Path(path).read_text()
        assert 'sample-' + kind in body
        assert 'project=sample' in body or suffix == 'prompt.md'
        assert '{{WORKER_ID}}' not in body
        assert body == _fill_hire_placeholders(expected[kind + '-' + suffix], {
            'WORKER_ID': 'sample-' + kind, 'slug': 'sample-' + kind,
            'STORE_SLUG': 'sample', 'store': 'sample',
            'NEIGHBORHOOD_NAME': 'sample', 'neighborhood': 'sample',
            'CLI_COMMAND': 'claude', 'MODEL_OR_"vendor default"': 'vendor default',
            'CLAIM_CRITERIA — e.g. "single-file, verifiable by the test suite, no schema changes"': 'work assigned to this cabinet',
            'FORBIDDEN_AREA_1': 'local/ employment records (roster, ledger locks)',
            'FORBIDDEN_AREA_2': "other cabinets' workers/ trees",
        })
    Path(contract).write_text('local customization')
    plant_hire_papers(str(project), 'sample-' + kind, template=kind, store='sample')
    assert Path(contract).read_text() == 'local customization'
seed_ops.plant_efficiency_kit(workspace, quiet=True)
skill = workspace / '.agents/skills/workspace-efficiency/SKILL.md'
assert skill.read_text() == expected['skills/workspace-efficiency/SKILL.md']
assert (workspace / '.claude/skills/workspace-efficiency/SKILL.md').read_text() == skill.read_text()
skill.write_text('local skill')
seed_ops.plant_efficiency_kit(workspace, quiet=True)
assert skill.read_text() == 'local skill'
for name in ('chief-of-staff', 'health-patrol', 'workspace-efficiency', 'papers-sync'):
    receipt = seed_ops.plant_ops_seat_papers(workspace, name)
    assert receipt['ok'], name
    for path in receipt['files']:
        assert (workspace / path).read_text() == (found._templates_dir() / 'ops' / name / Path(path).name).read_text()
founded = base / 'new-workspace'
found.found(founded, city_name='Example', neighborhood='sample-product',
            with_desk=False, sample_ticket=False)
for filename in ('CONTRACT.md', 'prompt.md'):
    body = (founded / 'sample-product/workers/demo-worker' / filename).read_text()
    assert 'worker:(fill me)' not in body
    assert 'project=(fill me)' not in body
    assert 'demo-worker' in body
    assert 'project=sample-product' in body
contract = founded / 'sample-product/workers/demo-worker/CONTRACT.md'
assert 'Vendor CLI: `(fill me)`' in contract.read_text()
assert not list(founded.rglob('roster.json'))
assert not list(workspace.rglob('*.db'))
assert not list(workspace.rglob('roster.json'))
print('wheel planting: worker, director, efficiency skill, four ops packs; no engines')
'''
            result = subprocess.run([sys.executable, '-c', program], cwd=base,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
