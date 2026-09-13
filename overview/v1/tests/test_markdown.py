import unittest

from server.markdown import render_markdown, render_reader_content


class MarkdownTests(unittest.TestCase):
    def test_escapes_untrusted_markup(self):
        html = render_markdown('<script>alert(1)</script>\n# Title')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('<h1', html)

    def test_long_content_gets_outline_and_collapsible_sections(self):
        text = '\n'.join(['## One', 'alpha', '## Two', 'beta'] * 20)
        rendered = render_reader_content(text, collapsible_after=10)
        self.assertEqual(len(rendered['outline']), 40)
        self.assertIn('bp-md-section', rendered['html'])

    def test_collapsed_sections_keep_outline_anchor_ids(self):
        text = '\n'.join(['## First', 'body one', '## Second', 'body two'] * 20)
        rendered = render_reader_content(text, collapsible_after=10)
        for item in rendered['outline']:
            self.assertIn(f'id="{item["id"]}"', rendered['html'])
