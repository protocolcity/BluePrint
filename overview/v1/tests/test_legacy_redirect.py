import unittest
from server.legacy_redirect import target
class RedirectTests(unittest.TestCase):
    def test_old_entrypoints_keep_query_and_point_to_current_surfaces(self):
        self.assertEqual(target('/desk?project=example'),'/work?project=example')
        self.assertEqual(target('/roster'),'/agents')
        self.assertEqual(target('/workspace-map/'),'/map')
        self.assertEqual(target('/api/operations'),'/api/operations')
        self.assertEqual(target('https://external.example/desk'),'/work')
