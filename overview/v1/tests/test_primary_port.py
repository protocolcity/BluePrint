"""Primary listen port defaults to :8801; leftover split ports are :8802/:8803."""
import unittest

import serve as overview_serve
from protocolcity import deploy as deploy_mod
from protocolcity import operations_cli


class PrimaryPortDefaultsTests(unittest.TestCase):
    def test_named_defaults_are_8801(self):
        self.assertEqual(overview_serve.DEFAULT_PORT, 8801)
        self.assertEqual(operations_cli.DEFAULT_PORT, 8801)
        self.assertEqual(deploy_mod.DEFAULT_PORT, 8801)
        self.assertEqual(deploy_mod.DEFAULT_LEGACY_PORTS, (8802, 8803))
        self.assertNotIn(8801, deploy_mod.DEFAULT_LEGACY_PORTS)


if __name__ == '__main__':
    unittest.main()
