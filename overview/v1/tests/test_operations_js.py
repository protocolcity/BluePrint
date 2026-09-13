"""Regression guards on operations.js wiring for STATES_AND_TERMS.md D6-D9.

Full DOM behavior is exercised by the browser check in the ticket; these
guard the literal source so the metric definitions, the default work
filter, and the claim-aware status text cannot silently regress.
"""
import unittest
from pathlib import Path

_SRC = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'operations.js').read_text(encoding='utf-8')
_HTML = (Path(__file__).resolve().parent.parent / 'static' / 'operations.html').read_text(encoding='utf-8')


class MetricDefinitionTests(unittest.TestCase):
    def test_for_you_metric_counts_the_whole_pile_not_just_decide_and_read(self):
        self.assertIn("forYou=orders.filter(o=>o.attention_face)", _SRC.replace(' ', ''))
    def test_live_metric_requires_an_owner_marker_not_status_alone(self):
        self.assertIn("live=orders.filter(o=>o.status==='in_progress'&&o.live_with)", _SRC.replace(' ', ''))
    def test_seats_and_jobs_are_two_counts_not_one(self):
        self.assertIn("'Seats · Jobs'", _SRC)
    def test_needs_you_badge_is_reserved_for_the_decide_face(self):
        self.assertIn("order.attention_face==='decide'", _SRC)


class DefaultFilterTests(unittest.TestCase):
    def test_deferred_and_tracking_are_hidden_by_default(self):
        self.assertIn('hideParked', _SRC)
        self.assertIn("!showDeferred", _SRC)
    def test_toggle_persists_choice_in_the_url(self):
        self.assertIn("params.set('deferred','1')", _SRC.replace(' ', ''))
        self.assertIn("query.get('deferred')", _SRC)
    def test_toggle_control_exists_in_the_markup(self):
        self.assertIn('id="show-deferred"', _HTML)


class ClaimPresentationTests(unittest.TestCase):
    def test_status_text_distinguishes_live_and_parked_from_open(self):
        self.assertIn('Live with', _SRC)
        self.assertIn('Parked by', _SRC)
    def test_watch_copy_never_says_stalled(self):
        self.assertNotIn('stalled', _SRC.lower())


class AssignmentFilterTests(unittest.TestCase):
    def test_assignment_options_come_from_the_roster_not_the_data(self):
        self.assertIn("snapshot.agents.filter(a=>a.group==='seat')", _SRC)
    def test_you_never_appears_as_an_assignment_option(self):
        self.assertNotIn("new Option('You'", _SRC)
    def test_unassigned_filter_excludes_you_like_the_owner_label_does(self):
        self.assertIn("o.workers.filter(w=>w!=='you').length", _SRC.replace(' ', ''))


class BlockedFilterTests(unittest.TestCase):
    def test_blocked_status_option_matches_declared_blockers_not_a_task_status(self):
        self.assertIn("status==='blocked'?o.blockers&&o.blockers.length", _SRC.replace(' ', ''))


class LiveIndicatorTests(unittest.TestCase):
    """D2 live rendering (pc-1470): header reads Live/Reconnecting/Polling,
    never a ticking 'Updated Xs ago' counter."""

    def test_no_more_ticking_updated_ago_counter(self):
        self.assertNotIn('Updated', _SRC)
        self.assertNotIn('${Math.floor((Date.now()-lastSuccess)', _SRC.replace(' ', ''))

    def test_open_stream_reads_live_with_last_change_age(self):
        self.assertIn("streamState==='open'", _SRC)
        self.assertIn('Live · last change', _SRC)

    def test_dropped_stream_reads_reconnecting_then_polling(self):
        self.assertIn("'Reconnecting'", _SRC)
        self.assertIn("'Polling every 60 s'", _SRC)
        self.assertIn('consecutiveErrors', _SRC)

    def test_refresh_button_label_only_flips_on_a_manual_read(self):
        compact = _SRC.replace(' ', '')
        self.assertIn("if(manual){$('refresh').disabled=true", compact)
        self.assertIn('refresh(true)', _SRC)
        # The automatic call sites (stream push, fallback poll, visibility
        # resume) must not pass `true` — only the click handler does.
        auto_call_sites = _SRC.count('refresh();')
        self.assertGreaterEqual(auto_call_sites, 3)


class RowReconciliationTests(unittest.TestCase):
    """D2 live rendering (pc-1470): lists are patched in place, never
    wholesale rebuilt with replaceChildren."""

    def test_reconcile_list_imported_from_shared_module(self):
        self.assertIn("import('/js/dom-reconcile.mjs')", _SRC)

    def test_no_wholesale_replace_children_on_the_named_lists(self):
        for list_id in ('metrics', 'for-you-decide', 'work-list', 'project-summary', 'seat-list', 'job-list'):
            self.assertNotIn(f"$('{list_id}').replaceChildren", _SRC)

    def test_reconcile_list_used_for_the_named_lists(self):
        for list_id in ('metrics', 'work-list', 'seat-list', 'job-list', 'project-summary', 'projects-view', 'dated-work', 'schedule-list', 'event-list'):
            self.assertIn(f"reconcileList($('{list_id}')", _SRC)


if __name__ == '__main__':
    unittest.main()
