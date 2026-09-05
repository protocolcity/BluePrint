#!/usr/bin/env python3
"""Seam tests for for_you_inbox_policy + CLI re-exports. No Desk required.

  python3 templates/scripts/test_for_you_inbox_policy.py
  python3 scripts/test_for_you_inbox_policy.py   # when planted next to the CLI
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from for_you_inbox_policy import (  # noqa: E402
    _read_glance,
    _slug_key,
    canonical_report_key,
    extract_dual_sections,
    format_dual_description,
    is_always_gold_key,
    is_disk_only_efficiency_key,
    is_disk_only_scan_key,
    is_folded_into_desk_key,
    is_thin_report,
    product_display_name,
)


class SlugAndDisplay(unittest.TestCase):
    def test_slug_key(self) -> None:
        self.assertEqual(_slug_key("My Project"), "my-project")
        self.assertEqual(_slug_key(""), "report")
        self.assertEqual(_slug_key("  "), "report")
        self.assertEqual(_slug_key("A" * 80), "a" * 48)

    def test_product_display_name(self) -> None:
        self.assertEqual(product_display_name("trading"), "Trading")
        self.assertEqual(product_display_name("unknown-app"), "unknown-app")


class DualSections(unittest.TestCase):
    def test_empty_and_no_headings(self) -> None:
        self.assertEqual(extract_dual_sections(""), (None, None))
        self.assertEqual(extract_dual_sections("# Title\n\nbody\n"), (None, None))

    def test_h2_either_order(self) -> None:
        text = "## User\n\nu-body\n\n## Builder\n\nb-body\n"
        self.assertEqual(extract_dual_sections(text), ("b-body", "u-body"))

    def test_h3_accepted(self) -> None:
        text = "### Builder\n\nb3\n\n### User\n\nu3\n"
        self.assertEqual(extract_dual_sections(text), ("b3", "u3"))

    def test_prefer_h2_over_h3(self) -> None:
        text = (
            "### Builder\n\nnested\n\n## Builder\n\nouter\n\n## User\n\nuser\n"
        )
        self.assertEqual(extract_dual_sections(text), ("outer", "user"))


class KeyPolicy(unittest.TestCase):
    def test_canonical_and_fold(self) -> None:
        self.assertEqual(canonical_report_key("desk-brief"), "desk-brief")
        self.assertEqual(canonical_report_key("maru-desk-brief"), "desk-brief")
        self.assertEqual(canonical_report_key("rsu-window"), "desk-brief")
        self.assertEqual(canonical_report_key("efficiency-pass"), "efficiency-pass")
        self.assertTrue(is_folded_into_desk_key("rsu-window"))
        self.assertFalse(is_folded_into_desk_key("desk-brief"))

    def test_always_gold(self) -> None:
        self.assertTrue(is_always_gold_key("workspace-digest"))
        self.assertTrue(is_always_gold_key("correspondent-rollup"))
        self.assertFalse(is_always_gold_key("clerk-brief"))

    def test_disk_only(self) -> None:
        for key in (
            "efficiency-pass",
            "suite-efficiency",
            "workspace-efficiency",
            "code-efficiency",
            "efficiency-register",
            "code-efficiency-foo",
            "board-validation",
        ):
            self.assertTrue(is_disk_only_scan_key(key), key)
        self.assertTrue(is_disk_only_efficiency_key("efficiency-pass"))
        self.assertFalse(is_disk_only_scan_key("desk-brief"))
        self.assertFalse(is_disk_only_efficiency_key("board-validation"))


class ThinAndGlance(unittest.TestCase):
    def test_missing_file_is_thin_unless_always_gold(self) -> None:
        missing = Path("/no/such/report.md")
        self.assertTrue(is_thin_report(missing, "clerk-brief"))
        self.assertFalse(is_thin_report(missing, "desk-brief"))
        self.assertFalse(is_thin_report(missing, "efficiency-pass"))

    def test_short_file_thin_full_dual_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            short = Path(tmp) / "short.md"
            short.write_text("tiny\n", encoding="utf-8")
            self.assertTrue(is_thin_report(short, "clerk-brief"))

            full = Path(tmp) / "full.md"
            builder = "B" * 220
            user = "U" * 220
            full.write_text(
                "## Builder\n\n%s\n\n## User\n\n%s\n" % (builder, user),
                encoding="utf-8",
            )
            self.assertFalse(is_thin_report(full, "clerk-brief"))

            ops = Path(tmp) / "ops.md"
            ops.write_text("## Builder\n\n" + ("O" * 500) + "\n", encoding="utf-8")
            self.assertTrue(is_thin_report(ops, "clerk-brief"))

    def test_glance_missing_and_front_matter(self) -> None:
        missing = Path("/no/such/report.md")
        self.assertIn("not found yet", _read_glance(missing))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.md"
            p.write_text("---\n---\nHello glance\n", encoding="utf-8")
            self.assertEqual(_read_glance(p, max_lines=4), "Hello glance\n")


class FormatDual(unittest.TestCase):
    def test_synthesizes_when_no_dual_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "plain.md"
            p.write_text("plain body\n", encoding="utf-8")
            body = format_dual_description(
                project="trading",
                day="2026-09-05",
                key="desk-brief",
                rel="plain.md",
                report_path=p,
            )
            self.assertIn("## Trading — 2026-09-05", body)
            self.assertIn("### Builder", body)
            self.assertIn("### User", body)
            self.assertIn("no dual headings yet", body)
            self.assertIn("**Report:** `plain.md`", body)
            self.assertIn("**Key:** `desk-brief`", body)

    def test_uses_parsed_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dual.md"
            p.write_text("## Builder\n\nops note\n\n## User\n\nplain note\n")
            body = format_dual_description(
                project="worklane",
                day="2026-09-05",
                key="workspace-digest",
                rel="dual.md",
                report_path=p,
            )
            self.assertIn("ops note", body)
            self.assertIn("plain note", body)
            self.assertNotIn("no dual headings yet", body)


class CliReexportAndSkip(unittest.TestCase):
    def test_cli_reexports_seam(self) -> None:
        import report_to_for_you as cli

        self.assertIs(cli.canonical_report_key, canonical_report_key)
        self.assertIs(cli.is_thin_report, is_thin_report)
        self.assertIs(cli.format_dual_description, format_dual_description)

    def test_help_and_disk_only_and_folded(self) -> None:
        cli = HERE / "report_to_for_you.py"
        help_out = subprocess.run(
            [sys.executable, str(cli), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--scan", help_out.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            r = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--workspace",
                    str(ws),
                    "--project",
                    "trading",
                    "--key",
                    "efficiency-pass",
                    "--title",
                    "x",
                    "--path",
                    "missing.md",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["action"], "disk_only")

            r2 = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--workspace",
                    str(ws),
                    "--project",
                    "trading",
                    "--key",
                    "rsu-window",
                    "--title",
                    "x",
                    "--path",
                    "missing.md",
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            folded = json.loads(r2.stdout)
            self.assertEqual(folded["action"], "folded_into_desk_brief")

            scan = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--workspace",
                    str(ws),
                    "--scan",
                    "--dry-run",
                    "--json",
                    "--day",
                    "2026-09-05",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            results = json.loads(scan.stdout)["results"]
            self.assertTrue(results)
            self.assertTrue(all(row.get("skipped") for row in results))
            self.assertTrue(
                all(row.get("reason") == "no report file for day" for row in results)
            )


if __name__ == "__main__":
    unittest.main()
