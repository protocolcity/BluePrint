"""Cut upgrade paths: brew HARD HOLD 0.1.47 → 0.1.50 and pip 0.1.49 → 0.1.50.

These do not talk to Homebrew or PyPI. They prove `blueprint update` would
ask each channel to move from the pre-cut drift faces onto this cut.
"""
import unittest
from unittest.mock import patch

from protocolcity import update as update_mod


CUT = '0.1.50'
BREW_HOLD = '0.1.47'
PIP_DRIFT = '0.1.49'


class CutUpgradePathTests(unittest.TestCase):
    def test_brew_hold_047_upgrades_to_cut(self):
        def fake_run(cmd, **kwargs):
            joined = ' '.join(cmd)
            if 'upgrade' in joined:
                return 0, 'Upgrading blueprint 0.1.47 -> 0.1.50', ''
            return 0, '', ''

        with patch.object(update_mod, '_suite_version', return_value=BREW_HOLD), \
                patch.object(update_mod, '_suite_version_fresh', return_value=CUT), \
                patch.object(update_mod, '_brew_formula', return_value='protocolcity/tap/blueprint'), \
                patch.object(update_mod.shutil, 'which', return_value='/usr/bin/brew'), \
                patch.object(update_mod, '_run', side_effect=fake_run):
            result = update_mod.upgrade_package(method='brew')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['method'], 'brew')
        self.assertEqual(result['before'], BREW_HOLD)
        self.assertEqual(result['after'], CUT)
        self.assertEqual(result['formula'], 'protocolcity/tap/blueprint')
        self.assertIn('upgrade', ' '.join(result['cmd']))

    def test_pip_049_upgrades_to_cut_with_engines_extra(self):
        versions = iter([PIP_DRIFT, CUT])

        def fake_run(cmd, **kwargs):
            joined = ' '.join(cmd)
            self.assertIn('protocolcity-blueprint[engines]', joined)
            return 0, 'Successfully installed protocolcity-blueprint-0.1.50', ''

        with patch.object(update_mod, '_suite_version', side_effect=lambda: next(versions)), \
                patch.object(update_mod, '_run', side_effect=fake_run):
            result = update_mod.upgrade_package(method='pip')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['method'], 'pip')
        self.assertEqual(result['before'], PIP_DRIFT)
        self.assertEqual(result['after'], CUT)
        self.assertIn('protocolcity-blueprint[engines]', ' '.join(result['cmd']))
