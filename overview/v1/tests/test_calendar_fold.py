import unittest
from suite.api.calendar import _fold_line, render_vevent
from datetime import date, datetime


def _physical_lines(folded):
    return folded.split("\r\n")


class CalendarFoldTests(unittest.TestCase):
    def assert_valid_fold(self, line):
        folded = _fold_line(line)
        for i, phys in enumerate(_physical_lines(folded)):
            self.assertLessEqual(len(phys.encode("utf-8")), 75, phys)
            if i:
                self.assertTrue(phys.startswith(" "))
        unfolded = folded.replace("\r\n ", "")
        self.assertEqual(unfolded, line)
        return folded

    def test_short_line_unchanged(self):
        self.assertEqual(_fold_line("SUMMARY:short"), "SUMMARY:short")

    def test_tail_that_is_exactly_one_multibyte_char(self):
        # pc-1462: the live failure — ellipsis as the very last character after a fold
        self.assert_valid_fold("DESCRIPTION:" + "a" * 62 + "…")
        self.assert_valid_fold("DESCRIPTION:" + "a" * 61 + "…")
        self.assert_valid_fold("DESCRIPTION:" + "a" * 63 + "—")

    def test_multibyte_across_successive_folds(self):
        line = "DESCRIPTION:" + ("word · " * 40) + "— end …"
        self.assert_valid_fold(line)
        emoji = "DESCRIPTION:" + ("🚀" * 60) + "x"
        self.assert_valid_fold(emoji)

    def test_render_vevent_with_live_shape(self):
        ev = {"uid": "osp-653", "summary": "HOST · rotate CRE SQL Server sa password",
              "description": "Remind me on 2026-08-10\nFOUNDER DECISION osp-571 (2026-08-07): rotate the CRE SQL Server `sa` password NOW (option a). This card is the execution runbook. Founder-only: the box is the legacy Win7 CRE machine; it will…",
              "dtstart": date(2026, 8, 10), "all_day": True, "url": "http://127.0.0.1:8803/work-order?project=oneseo-pos&id=653", "kind": "Hold until"}
        text = render_vevent(ev, dtstamp=datetime(2026, 9, 13))
        self.assertIn("DESCRIPTION:", text)
        for phys in text.split("\r\n"):
            self.assertLessEqual(len(phys.encode("utf-8")), 75)


if __name__ == "__main__":
    unittest.main()
