from pathlib import Path
import tempfile
import unittest
from server.documents import catalog, read_document

class DocumentTests(unittest.TestCase):
    def test_existing_papers_grouped_and_arbitrary_files_refused(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root=Path(directory); project=root/'example';(project/'.protocolcity').mkdir(parents=True)
            (project/'.protocolcity/desk-join.json').write_text('{"slug":"example","display":"Example"}')
            (project/'README.md').write_text('Product <script> is text')
            (project/'docs/specs').mkdir(parents=True);(project/'docs/specs/system.md').write_text('System')
            (project/'docs/secrets').mkdir();(project/'docs/secrets/passwords.md').write_text('Excluded')
            (project/'private.key').write_text('Excluded')
            remote=Path(outside)/'external.md';remote.write_text('Excluded')
            (project/'docs/external.md').symlink_to(remote)
            papers=catalog(root,'example')['papers']
            self.assertEqual([(p['path'],p['layer']) for p in papers],[('README.md','Product'),('docs/specs/system.md','System')])
            self.assertEqual(read_document(root,'example','README.md')['content'],'Product <script> is text')
            for path in ['../private.key','private.key','docs/external.md','docs/secrets/passwords.md']:
                with self.assertRaises(FileNotFoundError):read_document(root,'example',path)
            with self.assertRaises(ValueError):catalog(root,'../example')
