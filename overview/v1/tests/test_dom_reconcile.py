"""Keyed list reconciliation invariants (Live rendering, pc-1470).

``dom-reconcile.mjs`` is the shared patch used by every list on the
Operations glass (metrics, For You, project cards, work list, agent
cards, calendar rows): rows are matched by key and patched in place —
never a wholesale ``replaceChildren`` of the list. Locks the DoD from
the ticket: an unchanged snapshot leaves the DOM identical (same node
identities, no highlight), a changed row is patched without touching
its siblings, reordering preserves node identity, a focused control in
an untouched row is never disturbed, ``open`` on a details row survives
a patch, and the empty state does not repaint itself when nothing
changed. Runs in Node against a hand-rolled but DOM-spec-faithful
harness — see ``tests/harness/dom_reconcile_check.mjs``. If ``node`` is
not on PATH the test skips.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HARNESS = _HERE / "harness" / "dom_reconcile_check.mjs"


def _run_harness() -> dict:
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not available; skipping DOM reconcile checks")
    proc = subprocess.run(
        [node, str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"dom reconcile harness failed ({proc.returncode}):\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout)


class ReconcileListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = _run_harness()

    def test_unchanged_snapshot_leaves_dom_identical(self) -> None:
        c = self.cases["unchanged_same_identity"]
        self.assertTrue(c["sameLength"])
        self.assertTrue(c["sameNodes"])
        self.assertTrue(c["noHighlight"])

    def test_changed_row_is_patched_without_rebuilding_siblings(self) -> None:
        c = self.cases["changed_row_patched"]
        self.assertTrue(c["siblingsUntouched"])
        self.assertTrue(c["patchedInPlace"])
        self.assertEqual(c["newText"], "Beta CHANGED")
        self.assertTrue(c["highlighted"])
        self.assertTrue(c["siblingsNotHighlighted"])

    def test_added_and_removed_keys(self) -> None:
        c = self.cases["add_remove"]
        self.assertEqual(c["keys"], ["b", "c"])
        self.assertEqual(c["count"], 2)

    def test_reordering_preserves_node_identity(self) -> None:
        c = self.cases["reorder_preserves_identity"]
        self.assertEqual(c["order"], ["c", "a", "b"])
        self.assertTrue(c["sameNodes"])

    def test_focused_control_in_unchanged_row_is_undisturbed(self) -> None:
        c = self.cases["focus_preserved_on_unchanged_row"]
        self.assertTrue(c["sameButtonNode"])
        self.assertTrue(c["stillFocusedFlagUntouched"])

    def test_open_details_survive_a_patch(self) -> None:
        c = self.cases["open_state_preserved"]
        self.assertTrue(c["stillOpen"])
        self.assertEqual(c["textUpdated"], "Note changed")

    def test_empty_state_does_not_repaint_when_unchanged(self) -> None:
        c = self.cases["empty_state_stable"]
        self.assertEqual(c["childCount"], 1)
        self.assertEqual(c["text"], "Nothing here")
        self.assertTrue(c["sameNode"])


if __name__ == "__main__":
    unittest.main()
