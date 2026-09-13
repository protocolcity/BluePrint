"""Focused exploded project — canvas/sidebar/breadcrumb wiring
(docs/specs/MAP_FOCUSED_PROJECT.md, pc-1492).

The runtime lives in JavaScript, so — matching the existing hub/dig test
style (test_hub_layout.py, test_dig_replace.py) — this pins the shape the
Done-when bullets promise by parsing the modules, rather than re-running a
browser.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PAINT = _HERE.parent / "static" / "js" / "map-paint.js"
_VIEW = _HERE.parent / "static" / "js" / "view-state.js"
_HOST = _HERE.parent / "static" / "js" / "workspace_map_app.v1.js"
_CSS = _HERE.parent / "static" / "css" / "workspace_map.css"
_HTML = _HERE.parent / "static" / "workspace_map.html"
_ROUTER = _HERE.parent / "static" / "js" / "map-hit-router.js"


class ProjectFocusPaintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paint = _PAINT.read_text(encoding="utf-8")

    def test_paint_project_focus_exported(self) -> None:
        self.assertIsNotNone(re.search(r"export function paintProjectFocus", self.paint))

    def test_only_expanded_branch_gets_items(self) -> None:
        # Items are only fanned out for the one expanded branch — collapsed
        # chips never carry an item list (Rule: "One expanded branch").
        self.assertIsNotNone(re.search(r"isExpanded\s*&&\s*branch\.items", self.paint))

    def test_long_item_lists_are_capped_with_a_labelled_count(self) -> None:
        # "long levels expose a labelled count and navigation without
        # unreadable miniatures" — the canvas caps and shows "+N more".
        self.assertIn("BRANCH_ITEM_MAX_SHOWN", self.paint)
        self.assertIn("more", self.paint)

    def test_branch_and_item_carry_named_labels_not_bare_counts(self) -> None:
        self.assertIn("branch.summary", self.paint)
        self.assertIn("branch.label", self.paint)

    def test_branch_item_entrance_is_skipped_under_reduce_motion(self) -> None:
        # cursor-reviewer (pc-1492 PR 115): the CSS opacity-0 start is scoped
        # to `prefers-reduced-motion: no-preference`, so `.bp-reduce-motion`
        # alone (transition:none only) never becomes visible again on its
        # own — the *class* itself must be skipped, not just its transition.
        self.assertIn("function prefersReducedMotion", self.paint)
        self.assertIn("bp-reduce-motion", self.paint)
        self.assertIn("reduceMotion ? '' : ' map-branch-item-enter'", self.paint)


class ViewStateFocusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.view = _VIEW.read_text(encoding="utf-8")

    def test_select_project_clears_branch_item_and_dig(self) -> None:
        self.assertIsNotNone(re.search(r"selectProject\(node\)\s*\{", self.view))
        # Selecting a new project must reset any previously expanded branch
        # or selected item — a fresh focus always starts collapsed.
        block = re.search(r"selectProject\(node\)\s*\{([\s\S]*?)\n\s*\},", self.view).group(1)
        self.assertIn("state.branch = null", block)
        self.assertIn("state.item = null", block)

    def test_set_branch_toggles_and_only_one_is_open(self) -> None:
        # Clicking the same branch again must collapse it — the ternary is
        # the "one expanded branch" invariant in code.
        self.assertIsNotNone(
            re.search(r"state\.branch\s*=\s*state\.branch\s*===\s*key\s*\?\s*null\s*:\s*key", self.view)
        )

    def test_papers_keeps_the_nested_dig_trail_other_branches_do_not(self) -> None:
        self.assertIsNotNone(re.search(r"state\.branch\s*!==\s*'papers'", self.view))

    def test_select_project_persists_has_md(self) -> None:
        # cursor-reviewer (pc-1492 PR 115): selectProject dropped `hasMd`,
        # so papersBranch always read `undefined` and reported "empty" even
        # for a project with Markdown — state.project must carry it through.
        block = re.search(r"selectProject\(node\)\s*\{([\s\S]*?)\n\s*\},", self.view).group(1)
        self.assertIn("hasMd: Boolean(node.hasMd)", block)


class HostFocusWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.host = _HOST.read_text(encoding="utf-8")

    def test_url_carries_project_branch_and_item(self) -> None:
        self.assertIn("url.searchParams.set('project'", self.host)
        self.assertIn("url.searchParams.set('branch'", self.host)
        self.assertIn("url.searchParams.set('item'", self.host)

    def test_deep_link_restores_project_branch_and_item(self) -> None:
        self.assertIn("initial.get('project')", self.host)
        self.assertIn("initial.get('branch')", self.host)
        self.assertIn("initial.get('item')", self.host)

    def test_keyboard_focus_is_preserved_across_repaint(self) -> None:
        self.assertIn("function withFocusPreserved", self.host)
        self.assertIn("document.activeElement", self.host)

    def test_item_action_returns_to_the_same_branch_and_selection(self) -> None:
        # "the reader opens from it and returns to the same branch and
        # selection" — real navigation carries return_to back to this URL.
        self.assertIn("function withReturnTo", self.host)
        self.assertIn("return_to=", self.host)

    def test_camera_is_fixed_while_a_project_is_in_focus(self) -> None:
        self.assertIn("cfg.projectFocusRadius", self.host)

    def test_opening_papers_branch_reuses_the_real_folder_tree(self) -> None:
        self.assertIn("await digInto(project, { mode: 'root' })", self.host)

    def test_focused_project_paint_keeps_the_sidebar_browser_live(self) -> None:
        # cursor-reviewer (pc-1492 PR 115): repaintInner returned early in
        # project-focus mode without calling renderBrowser(), so
        # #map-browser-list kept showing the pre-focus snapshot — including
        # at the 400px breakpoint where the canvas is hidden and the browser
        # is the only surface. Assert renderBrowser() runs before the early
        # return of the project-focus branch of repaintInner.
        match = re.search(r"function repaintInner\(\)\s*\{([\s\S]*?)\n  \}", self.host)
        self.assertIsNotNone(match)
        focus_branch = re.search(r"if \(snap\.project\)\s*\{([\s\S]*?)\n\s*return;\n\s*\}", match.group(1))
        self.assertIsNotNone(focus_branch)
        self.assertIn("renderBrowser()", focus_branch.group(1))

    def test_deep_link_project_boot_resolves_has_md_from_the_tree(self) -> None:
        # cursor-reviewer (pc-1492 PR 115): the deep-link boot only had the
        # relPath from the URL and passed no `hasMd`, so papersBranch always
        # reported "empty" on first paint even for a project with Markdown.
        self.assertIn("tree.snapshot().lots.find(lot => lot.relPath === projectPath)", self.host)
        self.assertIn("hasMd: treeLot ? treeLot.hasMd : false", self.host)


class HitRouterFocusRowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = _ROUTER.read_text(encoding="utf-8")

    def test_branch_and_branch_item_rows_exist(self) -> None:
        self.assertIn("'branch-item'", self.router)
        self.assertIn("branch: 'branch'", self.router)


class ResponsiveAndMotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.css = _CSS.read_text(encoding="utf-8")
        self.html = _HTML.read_text(encoding="utf-8")

    def test_narrow_breakpoint_collapses_to_the_stacked_list(self) -> None:
        self.assertIn("@media (max-width: 400px)", self.css)

    def test_project_panel_exists_for_the_narrow_and_sidebar_list(self) -> None:
        self.assertIn('id="map-project-panel"', self.html)
        self.assertIn('id="map-branch-buttons"', self.html)
        self.assertIn('id="map-branch-items"', self.html)
        self.assertIn('id="map-item-detail"', self.html)

    def test_branch_item_motion_honors_reduced_motion(self) -> None:
        self.assertIn(".map-branch-item-enter", self.css)
        self.assertIn(".bp-reduce-motion .map-branch-item", self.css)


if __name__ == "__main__":
    unittest.main()
