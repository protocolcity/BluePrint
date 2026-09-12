import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from server.workspace_search import find
from server.work_order import source_references


class WorkspaceSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        join=self.root/'product/.protocolcity/desk-join.json';join.parent.mkdir(parents=True)
        join.write_text(json.dumps({'slug':'example','prefix':'ex','display':'Example'}))
        self.db=self.root/'worklane/worklane/local/data/example.db';self.db.parent.mkdir(parents=True)
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE tasks(id INTEGER,title TEXT,status TEXT)')
            db.execute("INSERT INTO tasks VALUES(1,'Old completed work','done')")
            db.executemany("INSERT INTO tasks VALUES(?, 'New task', 'backlog')",[(i,) for i in range(2,1200)])
    def tearDown(self): self.temp.cleanup()
    def test_query_finds_old_closed_identity_and_title(self):
        for query in ('ex-1','Old completed'):
            hits=find(self.root,query)['results']
            self.assertEqual(hits[0]['identity'],'ex-1')
            self.assertIn('done',hits[0]['detail'])
    def test_results_paginate_after_matching_full_history(self):
        page=find(self.root,'New task',offset=50,limit=50)
        self.assertEqual(page['total'],1198);self.assertEqual(len(page['results']),50)
        self.assertNotEqual(page['results'][0],find(self.root,'New task')['results'][0])
    def test_nested_papers_and_folders_with_protected_sources_excluded(self):
        docs=self.root/'product/docs/deep';docs.mkdir(parents=True)
        (docs/'Guide.md').write_text('Readable')
        private=self.root/'product/local';private.mkdir();(private/'Guide.md').write_text('Private')
        with tempfile.TemporaryDirectory() as external:
            (Path(external)/'Guide.md').write_text('Foreign')
            (docs/'ForeignGuide.md').symlink_to(Path(external)/'Guide.md')
            hits=find(self.root,'Guide')['results']
        self.assertEqual([h['identity'] for h in hits],['product/docs/deep/Guide.md'])
        self.assertEqual(find(self.root,'deep')['results'][0]['kind'],'Folder')
    def test_store_failure_is_visible_while_papers_remain_searchable(self):
        self.db.write_bytes(b'broken')
        (self.root/'AGENTS.md').write_text('Workspace law')
        result=find(self.root,'AGENTS.md')
        self.assertTrue(result['issues']);self.assertEqual(result['results'][0]['identity'],'AGENTS.md')
    def test_external_store_is_never_read(self):
        with tempfile.TemporaryDirectory() as external:
            target=Path(external)/'foreign.db';self.db.rename(target);self.db.symlink_to(target)
            result=find(self.root,'Old completed')
            self.assertEqual(result['results'],[]);self.assertTrue(result['issues'])

    def test_where_links_resolve_existing_safe_paths_only(self):
        (self.root/'product/AGENTS.md').write_text('Law')
        private=self.root/'product/local';private.mkdir();(private/'private.md').write_text('Private')
        description='## Where\n`product/AGENTS.md` · product/local/private.md · missing.md · javascript:alert(1)\n## Done when\nComplete'
        refs=source_references(self.root,'example',description)
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]['action'],'Read paper')
        self.assertIn('md=product%2FAGENTS.md',refs[0]['href'])
