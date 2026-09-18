"""Regression guards on operations.js wiring for STATES_AND_TERMS.md D6-D9.

Full DOM behavior is exercised by the browser check in the ticket; these
guard the literal source so the metric definitions, the default work
filter, and the claim-aware status text cannot silently regress.
"""
import json
import shutil
import subprocess
import re
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
    """STATES_AND_TERMS.md §5 (pc-1482): All open is complete by default;
    deferred/tracking are never hidden behind a second checkbox, and Gate
    is its own filter with no default exclusion."""
    def test_deferred_and_tracking_are_never_hidden_by_default(self):
        self.assertNotIn('hideParked', _SRC)
        self.assertNotIn('showDeferred', _SRC)
    def test_show_deferred_toggle_control_is_removed_from_the_markup(self):
        self.assertNotIn('id="show-deferred"', _HTML)
        self.assertNotIn('id="deferred-toggle"', _HTML)
    def test_gate_is_its_own_filter_with_no_default_exclusion(self):
        self.assertIn('id="gate-filter"', _HTML)
        self.assertIn("gate=$('gate-filter').value", _SRC.replace(' ', ''))
    def test_old_deferred_and_gate_status_links_map_to_the_gate_filter(self):
        self.assertIn("statusParam.startsWith('gate:')", _SRC)
        self.assertIn("statusParam === 'deferred'", _SRC)
    def test_old_attention_status_links_map_to_the_attention_filter(self):
        self.assertIn("statusParam === 'attention'", _SRC)
        self.assertIn("statusParam.startsWith('face:')", _SRC)
    def test_old_deferred_equals_1_link_maps_to_the_gate_filter(self):
        """Review finding (pc-1482): the legacy checkbox link /work?deferred=1
        must also map onto gate=deferred, same as status=deferred/gate:*."""
        self.assertIn("query.get('deferred') === '1'", _SRC)
        self.assertIn("gateParam = gateParam || 'deferred'", _SRC)
    def test_legacy_link_is_canonicalised_on_first_paint(self):
        """Review finding (pc-1482): once a legacy param is remapped, the
        address bar must be rewritten to the canonical params on load (not
        only inside updateFilters) so chips, counts and the URL agree from
        the first paint."""
        self.assertIn('legacyParam', _SRC)
        self.assertIn('if (legacyParam)', _SRC)
    def test_old_attention_equals_note_link_maps_to_the_due_face(self):
        """Review finding (pc-1494 recovery): the retired Note face value
        must not silently yield an empty list; ?attention=note resolves to
        Due and is canonicalised like every other legacy param."""
        self.assertIn("attentionParam === 'note'", _SRC)
        self.assertIn("attentionParam = 'due'", _SRC)


class ClaimPresentationTests(unittest.TestCase):
    def test_status_text_distinguishes_live_and_parked_from_open(self):
        self.assertIn('Live with', _SRC)
        self.assertIn('Parked by', _SRC)
    def test_watch_copy_never_says_stalled(self):
        # Watch copy stays evidence language; Stalled is a Status badge (pc-1510).
        watch = _SRC.split('function nextActionText(order)')[1].split('function orderDetailBody')[0]
        self.assertNotIn('stalled', watch.lower())
        self.assertIn("Check for new evidence", watch)


class AssignmentFilterTests(unittest.TestCase):
    """STATES_AND_TERMS.md §5 (pc-1482): You returns to Assignment beside the
    registered seats and Unassigned; persona items and human-owned decisions
    match You, never Unassigned."""
    def test_assignment_options_come_from_the_roster_not_the_data(self):
        self.assertIn("snapshot.agents.filter(a=>a.group==='seat')", _SRC)
    def test_you_is_an_assignment_option(self):
        self.assertIn("newOption('You','you')", _SRC.replace(' ', ''))
    def test_unassigned_filter_excludes_you_and_persona_items(self):
        self.assertIn("if(value==='unassigned')return!order.assigned_you&&!order.workers.filter(w=>w!=='you').length", _SRC.replace(' ', ''))
    def test_you_filter_matches_the_assigned_you_fact(self):
        self.assertIn("if(value==='you')returnorder.assigned_you", _SRC.replace(' ', ''))


class GateBlockedFilterTests(unittest.TestCase):
    """Declared blockers are a Gate value, not a checkbox or Status word
    (STATES_AND_TERMS.md §5, pc-1493)."""
    def test_blocked_is_a_gate_filter_value_not_a_status_option(self):
        self.assertIn('<option value="blocked">Blocked on another order</option>', _HTML)
        status_section = _HTML.split('id="status-filter"')[1].split('</select>')[0]
        self.assertNotIn('value="blocked"', status_section)
    def test_blocked_filter_control_is_removed_from_the_markup(self):
        self.assertNotIn('id="blocked-filter"', _HTML)
    def test_gate_filter_matches_open_blockers_via_blocked_on(self):
        self.assertIn("if(value==='blocked')returnorder.blocked_on==='open'||order.blocked_on==='unknown'", _SRC.replace(' ', ''))
    def test_ungated_excludes_orders_with_open_blockers(self):
        self.assertIn("if(value==='none')return!order.gate_type&&order.blocked_on==='clear'", _SRC.replace(' ', ''))
    def test_gate_label_surfaces_blocked_on_another_order(self):
        self.assertIn("if(order.blocked_on==='open'||order.blocked_on==='unknown')return'Blockedonanotherorder'", _SRC.replace(' ', ''))
    def test_unknown_blocker_note_surfaces_in_reader_text(self):
        self.assertIn("if(order.blocked_on==='unknown'&&order.blocked_note)returnorder.blocked_note", _SRC.replace(' ', ''))
    def test_legacy_blocked_param_maps_to_gate_blocked(self):
        self.assertIn("query.get('blocked') === '1'", _SRC)
        self.assertIn("gateParam = gateParam || 'blocked'", _SRC)
    def test_legacy_status_blocked_maps_to_gate_blocked(self):
        self.assertIn("statusParam === 'blocked'", _SRC)


class FiveAxisFilterTests(unittest.TestCase):
    """STATES_AND_TERMS.md §5 (pc-1482): Assignment, Status, Gate, Kind and
    For You are five orthogonal axes; Work composes them with search and
    project, and states the filtered/total count with a clear-all."""
    def test_status_filter_holds_only_lifecycle_words(self):
        status = _HTML.split('id="status-filter"')[1].split('</select>')[0]
        for value in ('Open', 'Ready', 'Live', 'Review', 'Deferred', 'Stalled', 'Done'):
            self.assertIn(f'value="{value}"', status)
        self.assertNotIn('For You (any face)', status)
        self.assertNotIn('value="backlog"', status)
    def test_gate_filter_offers_the_gate_values_including_blocked(self):
        for value in ('none', 'human', 'timer', 'deferred', 'tracking', 'blocked'):
            self.assertIn(f'value="{value}"', _HTML)
    def test_attention_filter_offers_the_board_bands(self):
        attention = _HTML.split('id="attention-filter"')[1].split('</select>')[0]
        self.assertIn('>Any</option>', attention)
        for value in ('act_now', 'my_todos', 'seat'):
            self.assertIn(f'value="{value}"', attention)
    def test_kind_filter_offers_the_five_kinds(self):
        """STATES_AND_TERMS.md §5 (D16): Work gains a Kind filter separate
        from For You so the item type axis stops overloading the faces."""
        self.assertIn('id="kind-filter"', _HTML)
        for value in ('work', 'todo', 'note', 'reminder', 'report'):
            self.assertIn(f'<option value="{value}">', _HTML)
        self.assertIn("kind=$('kind-filter').value", _SRC.replace(' ', ''))
        self.assertIn("kind||o.kind===kind", _SRC.replace(' ', ''))
    def test_filters_compose_with_and_not_or(self):
        fn = _SRC.split('function matchingWorkOrders()')[1].split('function workHasMatchingFilter')[0]
        compact = fn.replace(' ', '')
        self.assertIn('selectedProject||o.project===selectedProject', compact)
        self.assertIn('selectedAssignment||matchesAssignment', compact)
        self.assertIn('matchesStatusFacet(o,status)', compact)
        self.assertIn('gate||matchesGate(o,gate)', compact)
        self.assertIn('matchesAttentionFacet(o,attention)', compact)
        work_fn = _SRC.split('function work()')[1].split('function agentAction')[0]
        self.assertIn('matchingWorkOrders()', work_fn)
    def test_results_state_filtered_of_total(self):
        self.assertIn("`${orders.length} of ${total} matching work order", _SRC)
    def test_clear_all_resets_every_filter(self):
        fn = _SRC.split("$('clear-filters').addEventListener('click',()=>{")[1].split('});')[0]
        for control in ("$('search').value=''", "$('project-filter').value=''", "$('assignment-filter').value=''",
                        "$('status-filter').value=''", "$('gate-filter').value=''", "$('kind-filter').value=''",
                        "$('attention-filter').value=''"):
            self.assertIn(control, fn.replace(' ', ''))
    def test_active_filters_render_as_dismissable_chips(self):
        self.assertIn("function renderActiveFilters()", _SRC)
        self.assertIn("'bp-filter-chip'", _SRC)
        self.assertIn("$('clear-filters').hidden=!chips.length", _SRC.replace(' ', ''))


class LiveIndicatorTests(unittest.TestCase):
    """pc-1483: the freshness line separates three independent clocks —
    transport (Updates connected/reconnecting/polling/paused), last
    successful source read/age, and last meaningful content change — never
    one ambiguous word. Supersedes pc-1470's ban on a ticking 'Updated Xs
    ago' counter: that decision was about conflating read time with content
    change into a single label; these are three distinct, self-explanatory
    clauses instead (STATES_AND_TERMS.md, OPERATIONS_EVOLUTION_2026_09.md)."""

    def test_transport_state_is_its_own_clause(self):
        self.assertIn("'Updates connected'", _SRC)
        self.assertIn("'Updates reconnecting'", _SRC)
        self.assertIn("'Updates polling every 60 s'", _SRC)
        self.assertIn("'Updates paused'", _SRC)
        self.assertIn('consecutiveErrors', _SRC)

    def test_last_read_age_is_its_own_clause(self):
        self.assertIn('last read ${readAge}s ago', _SRC)

    def test_last_change_age_is_its_own_clause_and_never_a_bare_read(self):
        self.assertIn('last change ${Math.floor((Date.now()-lastChangeAt)/1000)}s ago', _SRC)
        self.assertIn('no change observed yet', _SRC)

    def test_refresh_button_label_only_flips_on_a_manual_read(self):
        compact = _SRC.replace(' ', '')
        self.assertIn("if(manual){$('refresh').disabled=true", compact)
        self.assertIn('refresh(true)', _SRC)
        # The automatic call sites (stream push, fallback poll, visibility
        # resume) must not pass `true` — only the click handler does.
        auto_call_sites = _SRC.count('refresh();')
        self.assertGreaterEqual(auto_call_sites, 3)


class ContentFingerprintTests(unittest.TestCase):
    """pc-1483: a fingerprint used to decide whether the content actually
    changed must not include pure read-time/heartbeat-tick fields, or a
    silent identical re-read repaints and bumps 'last change' every poll."""

    def test_content_key_strips_heartbeat_tick_and_probe_read_time(self):
        fn = _SRC.split('function contentKey(next)')[1].split('async function refresh(')[0]
        self.assertIn('last_at', fn)
        self.assertIn("worklane_api", fn)
        self.assertIn('stripProbeTimes', fn)
        self.assertIn('supervisor', fn)
        helper = _SRC.split('function stripProbeTimes(engine)')[1].split('function contentKey(next)')[0]
        self.assertIn('observed_at', helper)
        self.assertIn('last_success_at', helper)

    def test_content_key_strips_shift_age_seconds(self):
        """Review finding (pc-1483 recovery 2): an agent's open-shift
        age_seconds is recomputed from the wall clock on every read, so two
        otherwise-identical snapshots that only differ there must fingerprint
        the same — the prior fix stripped last_at from agents/supervisor but
        kept the full shift object, which still carried age_seconds."""
        fn = _SRC.split('function contentKey(next)')[1].split('async function refresh(')[0]
        self.assertIn('stripShiftAge', fn)
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping contentKey behavioral check')
        harness = Path(__file__).resolve().parent / 'harness' / 'content_key_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'content key harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertTrue(result['same_key_for_different_age_seconds'])
        self.assertTrue(result['different_key_for_different_started_at'])
        self.assertTrue(result['same_key_for_probe_timestamps'])
        self.assertTrue(result['different_key_for_capability_state'])

    def test_refresh_uses_content_key_not_a_raw_json_stringify(self):
        fn = _SRC.split('async function refresh(manual)')[1].split('function updateFilters()')[0]
        self.assertIn('contentKey(next)', fn)

    def test_timeline_change_clock_ignores_an_identical_successful_read(self):
        """refreshTimeline() must not stamp lastChangeAt on every successful
        read (STATES_AND_TERMS.md/pc-1483: 'Timeline successful identical
        reads must not reset last meaningful change')."""
        fn = _SRC.split('async function refreshTimeline(')[1].split('async function refreshRemote(')[0]
        self.assertNotIn('lastChangeAt = Date.now();\n  } catch (error) {', fn)
        self.assertIn('timelineFingerprint', fn)
        self.assertIn('timelineKey!==timelineFingerprint', fn.replace(' ', ''))

    def test_manual_refresh_forces_a_full_timeline_reload(self):
        """Review finding (pc-1483 recovery 2): after Load more sets
        timelineExpanded, refreshTimeline(false) alone takes the background
        path (only toggling the new-events affordance), so the explicit
        Refresh button did nothing visible. The click handler must pass
        {force: true} so a manual refresh always reloads the list, the same
        way the new-events affordance click already does."""
        handler = _SRC.split("$('refresh').addEventListener('click',")[1].split(');\n')[0]
        compact = handler.replace(' ', '')
        self.assertIn('refreshTimeline(false,{force:true})', compact)


class RowReconciliationTests(unittest.TestCase):
    """D2 live rendering (pc-1470): lists are patched in place, never
    wholesale rebuilt with replaceChildren."""

    def test_reconcile_list_imported_from_shared_module(self):
        self.assertIn("import('/js/dom-reconcile.mjs')", _SRC)

    def test_no_wholesale_replace_children_on_the_named_lists(self):
        for list_id in ('metrics', 'for-you-decide', 'work-act-now', 'work-my-todos', 'work-seat-backlog', 'project-summary', 'seat-list', 'job-list'):
            self.assertNotIn(f"$('{list_id}').replaceChildren", _SRC)

    def test_reconcile_list_used_for_the_named_lists(self):
        for list_id in ('overview-executions', 'metrics', 'seat-list', 'job-list', 'projects-list', 'calendar-today', 'calendar-next', 'calendar-past', 'schedule-list', 'event-list', 'engine-list', 'capability-list', 'excluded-store-list', 'remote-repositories', 'connection-exceptions'):
            self.assertIn(f"reconcileList($('{list_id}')", _SRC)
        self.assertIn("reconcileList(host, visible", _SRC)
        self.assertIn("reconcileList(host, preview", _SRC)

    def test_delivery_no_longer_replaces_all_repository_children(self):
        """pc-1483/pc-1487: delivery painting must reconcile repository and
        group sections by key instead of tearing the whole list down."""
        fn = _SRC.split('function paintDelivery(')[1].split('function remoteStatusText')[0]
        self.assertNotIn("container.replaceChildren()", fn)
        self.assertIn("reconcileList($('remote-repositories')", fn)
        self.assertIn('.bp-delivery-groups', fn)

    def test_excluded_stores_are_a_reconciled_list_not_a_joined_note(self):
        self.assertIn("reconcileList($('excluded-store-list')", _SRC)
        self.assertIn('id="excluded-store-list"', _HTML)
        self.assertNotIn("Excluded unregistered databases:", _SRC)
        self.assertNotIn("$('connection-list').append(el('p','Excluded", _SRC)


class AgentCardBodyTests(unittest.TestCase):
    """pc-1472: lean card body, dropped daemon heartbeat row, dropped
    pre-design intro copy, vocabulary fixes (SUITE_VOCABULARY.md)."""

    def test_identity_type_configuration_rows_are_dropped(self):
        for label in ('Identity', 'Type', 'Configuration', 'Scheduler heartbeat'):
            self.assertNotIn(f"['{label}',", _SRC)

    def test_pre_design_intro_copy_is_gone(self):
        self.assertNotIn('These are registered local agents', _HTML)
        self.assertNotIn('Runtime state is unknown when the heartbeat', _HTML)

    def test_intro_copy_matches_agents_intent_ruling(self):
        legend = _HTML.split('id="agents-legend"')[1].split('</p>')[0]
        self.assertIn('Seats claim work orders', legend)
        self.assertIn('Jobs never claim', legend)
        self.assertIn('Supervisor dispatches seats', legend)
        self.assertIn('Coverage shows hired vs missing', legend)
        self.assertIn('2 implementation seats', legend)
        self.assertIn('WorkForce ledger', legend)

    def test_group_headings_drop_the_parenthetical(self):
        self.assertIn('<h2>Seats</h2>', _HTML)
        self.assertIn('<h2>Jobs</h2>', _HTML)
        self.assertNotIn('implementation lanes', _HTML)
        self.assertNotIn('scheduled duties', _HTML)

    def test_daemon_heartbeat_is_one_line_in_the_page_header_not_per_card(self):
        self.assertIn('id="agents-heartbeat"', _HTML)
        self.assertIn('function heartbeatLine()', _SRC)
        self.assertIn("'WorkForce daemon: not reachable'", _SRC)
        self.assertIn('WorkForce daemon: seen', _SRC)

    def test_find_assigned_work_is_seat_only(self):
        """pc-1485: the link moved into the seat-only inspector panel;
        jobRow never renders it."""
        self.assertIn("container.append(link('Find assigned work'", _SRC)
        self.assertNotIn("Find assigned work", _SRC.split('function jobRow')[1].split('function ')[0])

    def test_recovery_attempts_is_seat_only(self):
        """pc-1485: recovery attempts moved into the seat-only run timeline;
        jobRow never references it."""
        self.assertIn("'Recovery attempts'", _SRC.split('function agentTimelineValues')[1].split('function ')[0])
        self.assertNotIn('recovery_attempts', _SRC.split('function jobRow')[1].split('function ')[0])


class AgentCompactRowAndInspectorTests(unittest.TestCase):
    """pc-1485: compact comparable seat rows plus a selected-run inspector
    with a source-labelled timeline; jobs stay a compact schedule/report
    line with no timeline."""

    def test_seat_and_job_lists_use_compact_rows_not_the_old_card_grid(self):
        self.assertIn('id="seat-list" class="bp-agent-rows"', _HTML)
        self.assertIn('id="job-list" class="bp-agent-rows"', _HTML)
        self.assertNotIn('bp-agent-grid', _HTML)
        self.assertNotIn('bp-agent-grid', _SRC)

    def test_agent_detail_panel_exists_and_starts_hidden(self):
        self.assertIn('id="agent-detail"', _HTML)
        self.assertIn('id="agent-detail" class="bp-panel bp-agent-detail" hidden', _HTML)

    def test_seat_row_carries_project_state_work_elapsed_update_and_one_action(self):
        fn = _SRC.split('function agentRow(agent)')[1].split('function jobRow')[0]
        self.assertIn("agent.project_name || 'No project queue'", fn)
        self.assertIn('badge(agent.state,agent.badge)', fn)
        self.assertIn('heldLink(agent)', fn)
        self.assertIn('elapsedText(agent)', fn)
        self.assertIn('lastUpdateText(agent)', fn)
        self.assertIn('agentAction(agent)', fn)

    def test_selecting_a_row_toggles_selection_and_repaints(self):
        self.assertIn('function selectAgent(id)', _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn("selectedAgentId=selectedAgentId===id?'':id", compact)
        self.assertIn('agents();', _SRC.split('function selectAgent(id)')[1].split('}')[0] + '}')

    def test_row_is_keyboard_operable_without_reactivating_on_button_or_link_clicks(self):
        fn = _SRC.split('function agentRow(agent)')[1].split('function jobRow')[0]
        self.assertIn("select.setAttribute('role','button')", fn)
        self.assertIn('select.tabIndex=1'.replace('1', '0'), fn.replace(' ', ''))
        self.assertIn("event.target.closest('a')", fn)
        self.assertIn("event.key==='Enter'", fn)

    def test_action_cell_is_not_inside_the_selectable_region(self):
        """pc-1485 review fix: the action cell (a real button/link) must
        not be nested inside the role=button selectable region — it is a
        sibling of it on the row."""
        fn = _SRC.split('function agentRow(agent)')[1].split('function jobRow')[0]
        select_body = fn.split('row.append(select);')[0]
        self.assertNotIn('bp-agent-action', select_body)
        self.assertIn("row.append(select);", fn)
        self.assertIn("row.append(actionCell);", fn.split('row.append(select);')[1])

    def test_elapsed_is_a_time_budget_never_a_percent(self):
        fn = _SRC.split('function elapsedText(agent)')[1].split('function ')[0]
        self.assertIn('budget', fn)
        self.assertNotIn('%', fn)

    def test_current_work_id_is_a_usable_reader_link(self):
        fn = _SRC.split('function heldLink(agent)')[1].split('function ')[0]
        self.assertIn("readerHref('/work-order?'", fn)
        self.assertIn('workUrl(order)', fn)

    def test_timeline_covers_the_five_source_labelled_phases_in_order(self):
        fn = _SRC.split('function agentTimelineValues(agent)')[1].split('function agentTimeline(agent)')[0]
        for phase in ('Dispatch candidate', 'Verified claim', 'Observed run start', 'Recovery attempts', 'Terminal outcome'):
            self.assertIn(f"'{phase}'", fn)
        order = [fn.index(f"'{phase}'") for phase in
                 ('Dispatch candidate', 'Verified claim', 'Observed run start', 'Recovery attempts', 'Terminal outcome')]
        self.assertEqual(order, sorted(order))

    def test_missing_timeline_phases_read_not_reported_not_inferred(self):
        fn = _SRC.split('function agentTimelineValues(agent)')[1].split('function agentTimeline(agent)')[0]
        self.assertIn("'Not reported'", fn)

    def test_an_old_failure_no_longer_held_is_distinguished_from_a_current_failure(self):
        fn = _SRC.split('function agentTimelineValues(agent)')[1].split('function agentTimeline(agent)')[0]
        self.assertIn("state==='last_run_failed'", fn)
        self.assertIn('resolved by another provider', fn)

    def test_job_row_is_a_compact_schedule_report_line_with_no_timeline(self):
        fn = _SRC.split('function jobRow(agent)')[1].split('function timelineStep')[0]
        self.assertIn('scheduleLabel(agent.schedule)', fn)
        self.assertIn('agent.report', fn)
        self.assertNotIn('agentTimeline', fn)
        self.assertNotIn('heldLink', fn)

    def test_inspector_action_is_seat_only_and_hides_when_nothing_selected(self):
        fn = _SRC.split('function agentDetail()')[1].split('})();')[0]
        self.assertIn("a.group==='seat'", fn)
        self.assertIn('container.hidden=true', fn)

    def test_inspector_reconciliation_escape_and_row_control_split(self):
        """pc-1485 review recovery 1: DOM-behavioral guards a source-string
        check cannot make honest — (1) an identical repaint of the selected
        agent leaves every inspector node untouched and a single changed
        field updates only that field; (2) Escape clears the seat selection,
        hides the inspector, and returns focus to the row; (3) the action
        cell is never nested inside the role=button selectable region."""
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping agent inspector harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'agent_inspector_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'agent inspector harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertTrue(result['identical_repaint_stable'])
        self.assertTrue(result['changed_phase_isolated'])
        self.assertTrue(result['escape_clears_selection'])
        self.assertTrue(result['escape_hides_inspector'])
        self.assertTrue(result['escape_returns_focus'])
        self.assertTrue(result['action_cell_outside_select_region'])


class DeliveryQuietCopyTests(unittest.TestCase):
    """pc-1466 review fix: quiet copy must follow repo.quiet only."""

    def test_quiet_copy_uses_repo_quiet_flag_only(self):
        compact = _SRC.replace(' ', '')
        self.assertIn("repo.quiet?'Quietinthelast14days.'", compact)
        self.assertNotIn("repo.quiet||repo.state==='connected'", compact)


class PersonaChipTests(unittest.TestCase):
    """pc-1484: persona and needs-routing move into the expandable detail body."""

    def test_persona_renders_in_the_detail_body_before_needs_routing(self):
        fn = _SRC.split('function orderDetailBody(order, content)')[1].split('function orderHasDetail')[0]
        compact = fn.replace(' ', '')
        self.assertIn("if(order.persona)content.append(el('p',order.persona,'bp-order-note'));", compact)
        self.assertLess(compact.index('if(order.persona)'), compact.index('elseif(order.needs_routing)'))

    def test_needs_routing_only_renders_in_detail_when_there_is_no_persona(self):
        fn = _SRC.split('function orderDetailBody(order, content)')[1].split('function orderHasDetail')[0]
        self.assertIn("elseif(order.needs_routing)content.append(el('p','Needsrouting','bp-order-note'));", fn.replace(' ', ''))


class CompactRowTests(unittest.TestCase):
    """pc-1484: compact Overview and Work rows with progressive disclosure."""

    def test_work_row_uses_one_line_title_not_a_tall_body(self):
        fn = _SRC.split('function workBoardRow(order')[1].split('function orderRow')[0]
        compact = fn.replace(' ', '')
        self.assertIn("el('strong',order.title)", compact)
        self.assertIn('relativeAge(order.updated_at)', compact)
        self.assertIn('seatChipForOrder(order)', compact)
        self.assertNotIn('compactMetaLine(order)', compact)
        self.assertNotIn('Mute 24h', fn)
        self.assertNotIn("el('summary','More')", fn)

    def test_assignment_summary_never_prefixes_assigned_to(self):
        self.assertIn('function assignmentSummary(order)', _SRC)
        self.assertNotIn("'Assigned to'", _SRC.split('function assignmentSummary')[1].split('function orderUpdatedAt')[0])

    def test_boilerplate_notes_are_filtered_from_summary_and_detail_gate(self):
        self.assertIn('function isBoilerplateNote(note)', _SRC)
        self.assertIn('Intake:', _SRC)
        self.assertIn('!isBoilerplateNote(order.last_note)', _SRC.replace(' ', ''))

    def test_overview_starts_with_current_execution_before_metrics(self):
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        compact = fn.replace(' ', '')
        self.assertLess(compact.index("reconcileList($('overview-executions')"), compact.index("reconcileList($('metrics')"))

    def test_work_has_three_density_bands(self):
        self.assertIn('id="overview-executions"', _HTML)
        self.assertIn('id="work-act-now"', _HTML)
        self.assertIn('id="work-my-todos"', _HTML)
        self.assertIn('id="work-seat-backlog"', _HTML)
        self.assertNotIn('id="overview-recent"', _HTML)
        self.assertNotIn('id="work-recent"', _HTML)

    def test_for_you_uses_overview_face_row_not_full_order_row(self):
        self.assertIn('function overviewFaceRow(order)', _SRC)
        self.assertIn('overviewFaceRow(order)', _SRC.split('function faceEntry')[1].split('function faceHeading')[0])

    def test_running_and_claimed_metrics_are_distinct(self):
        self.assertIn("'Running'", _SRC)
        self.assertIn("'Claimed'", _SRC)

    def test_overview_execution_uses_running_seats_only(self):
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        compact = fn.replace(' ', '')
        self.assertIn("snapshot.agents.filter(a=>a.group==='seat'&&a.state==='working')", compact)
        self.assertIn("reconcileList($('overview-executions'),running.length", compact)
        self.assertIn('overviewExecutionSummary', compact)
        self.assertNotIn('executionRow', compact)

    def test_overview_execution_empty_is_honest_when_no_running_seats(self):
        self.assertIn('function overviewExecutionEmpty()', _SRC)
        self.assertIn('No seats report an open shift right now.', _SRC)

    def test_overview_execution_empty_text_only_when_no_running_seats(self):
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        compact = fn.replace(' ', '')
        self.assertIn('running.length?{}:{emptyText:overviewExecutionEmpty()}', compact)


class UnroutedOverviewTests(unittest.TestCase):
    """pc-1507: Unrouted is a read-only rollup beside metrics, not a sixth KPI
    or a For You inflation. The Work link uses the same isUnrouted predicate
    via /work?unrouted=1."""

    def test_overview_unrouted_line_is_under_metrics_not_in_the_tile_row(self):
        self.assertIn('id="overview-unrouted"', _HTML)
        metrics_pos = _HTML.index('id="metrics"')
        spark_pos = _HTML.index('id="overview-throughput"')
        unrouted_pos = _HTML.index('id="overview-unrouted"')
        for_you_pos = _HTML.index('id="for-you-decide"')
        self.assertLess(metrics_pos, spark_pos)
        self.assertLess(spark_pos, unrouted_pos)
        self.assertLess(unrouted_pos, for_you_pos)

    def test_unrouted_matches_open_backlog_needs_routing_chip(self):
        self.assertIn("function isUnrouted(order)", _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn("returnorder.status==='backlog'&&Boolean(order.needs_routing)", compact)

    def test_face_heading_updates_summary_not_retired_heading_ids(self):
        fn = _SRC.split('function faceHeading(')[1].split('function bindForYouFaceToggle')[0]
        compact = fn.replace(' ', '')
        self.assertIn("faceHost(label.toLowerCase(),'summary')", compact)
        self.assertNotIn('-heading', fn)
        self.assertIn('summary.textContent=text', compact)

    def test_unrouted_link_opens_work_with_the_same_predicate_as_the_count(self):
        self.assertIn("UNROUTED_WORK_HREF='/work?unrouted=1'", _SRC.replace(' ', ''))
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        self.assertIn("orders.filter(isUnrouted)", fn)
        self.assertIn("link(String(unrouted.length),UNROUTED_WORK_HREF)", fn.replace(' ', ''))
        work_fn = _SRC.split('function matchingWorkOrders()')[1].split('function workHasMatchingFilter')[0]
        self.assertIn('(!unroutedOnly||isUnrouted(o))', work_fn.replace(' ', ''))

    def test_unrouted_zero_renders_quiet_text_not_hidden(self):
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        self.assertIn("' — none right now'", fn)

    def test_for_you_metric_is_unchanged(self):
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        compact = fn.replace(' ', '')
        self.assertIn("forYou=orders.filter(o=>o.attention_face)", compact)
        self.assertIn("['ForYou',forYou.length,'/work?attention=any']", compact)

    def test_overview_unrouted_styles_exist_for_narrow_viewports(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-overview-unrouted', css)
        self.assertIn('@media(max-width:560px)', css)


class SlimOverviewTests(unittest.TestCase):
    """pc-1508: Overview = Now — short queues, no project grid, compact sources."""

    def test_across_your_projects_section_removed_from_overview(self):
        self.assertNotIn('Across your projects', _HTML)
        self.assertNotIn('id="project-summary"', _HTML)
        fn = _SRC.split('function overview()')[1].split('function filterOptions')[0]
        self.assertNotIn("reconcileList($('project-summary')", fn)

    def test_decide_act_now_is_capped_at_five_one_line_rows(self):
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        compact = fn.replace(' ', '').replace('\n', '')
        self.assertIn('OVERVIEW_DECIDE_LIMIT=5', _SRC.replace(' ', ''))
        self.assertIn('.slice(0,OVERVIEW_DECIDE_LIMIT)', compact)
        self.assertIn('overviewDecideRow', compact)
        self.assertIn("emptyText:'Nothing for You'", fn)
        self.assertNotIn('faceEntry', compact)

    def test_recent_changes_stay_off_overview(self):
        overview_fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertNotIn("reconcileList($('overview-recent')", overview_fn)
        self.assertNotIn('Recent changes', _HTML.split('id="overview-view"')[1].split('id="work-view"')[0])
        self.assertNotIn('id="work-recent"', _HTML)

    def test_source_status_is_one_compact_line_not_a_source_list(self):
        self.assertIn('id="overview-source-line"', _HTML)
        self.assertNotIn('id="source-list"', _HTML.split('id="overview-view"')[1].split('id="work-view"')[0])
        self.assertIn('function overviewSourceLine()', _SRC)
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertIn('overviewSourceLine()', fn)
        self.assertNotIn("sources($('source-list')", fn)

    def test_read_and_watch_are_count_chips_to_work(self):
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        compact = fn.replace(' ', '')
        self.assertIn("['Read','read'],['Watch','watch'],['Due','due']", compact)
        self.assertIn('overviewFaceChip', compact)
        self.assertIn("'/work?attention='+face", compact)
        self.assertIn('calendarDoorsFromSnapshot()', fn)
        self.assertIn('doors.due_count', compact)
        self.assertIn('doors.due_href', compact)
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertIn('id="overview-face-chips"', overview)
        self.assertNotIn('id="for-you-read"', overview)
        self.assertNotIn('id="for-you-watch"', overview)


class SlimOverviewReviewFixTests(unittest.TestCase):
    """pc-1508 recovery 1: source status is a compact line, not a hollow panel;
    five KPI tiles wrap before narrow mobile."""

    def test_source_line_is_outside_for_you_panel_not_a_grid_aside(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertNotIn('class="bp-overview-grid"', overview)
        self.assertNotIn('bp-overview-source-aside', overview)
        source_pos = overview.index('id="overview-source-line"')
        for_you_pos = overview.index('id="for-you-decide"')
        self.assertLess(source_pos, for_you_pos)

    def test_five_metric_tiles_have_a_mid_width_breakpoint(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        compact = css.replace(' ', '')
        self.assertIn('grid-template-columns:repeat(5,minmax(0,1fr))', compact)
        self.assertIn('@media(max-width:900px){.bp-metrics{grid-template-columns:repeat(3,minmax(0,1fr));}', compact)


class CompactRowReviewFixTests(unittest.TestCase):
    """pc-1484 review recovery 1: recent changes sort, More outside the link,
    assignment summary from server owner."""

    def test_closed_orders_stay_out_of_work_bands(self):
        self.assertIn('function orderUpdatedAt(order)', _SRC)
        self.assertIn('function isClosedOrder(order)', _SRC)
        compact = _SRC.split('function isSeatBacklog(order)')[1].split('function boardBand')[0].replace(' ', '')
        self.assertIn('if(isClosedOrder(order)||isActNow(order)||isMyTodo(order))returnfalse', compact)

    def test_more_disclosure_is_outside_the_row_link(self):
        fn = _SRC.split('function overviewFaceRow(order')[1].split('function ')[0]
        compact = fn.replace(' ', '')
        self.assertIn('anchor.append(content)', compact)
        self.assertNotIn('anchor.append(details)', compact)
        self.assertIn('row.append(details)', compact)
        self.assertLess(fn.index('row.append(anchor'), fn.index('row.append(details)'))
        work = _SRC.split('function workBoardRow(order')[1].split('function orderRow')[0]
        self.assertNotIn("el('summary','More')", work)
        self.assertNotIn('bp-order-detail', work)

    def test_assignment_summary_uses_server_owner_field(self):
        fn = _SRC.split('function assignmentSummary(order)')[1].split('function orderUpdatedAt')[0]
        compact = fn.replace(' ', '')
        self.assertIn('order.owner', fn)
        self.assertNotIn('order.assigned_you', compact)
        self.assertNotIn('order.workers', compact)

    def test_compact_row_dom_behavior(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping compact row harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'compact_row_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'compact row harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertTrue(result['persona_owner_shows_you'])
        self.assertTrue(result['recent_sorts_by_real_time'])
        self.assertTrue(result['done_order_excluded'])
        self.assertTrue(result['one_line_title'])
        self.assertFalse(result['has_more'])
        self.assertFalse(result['has_mute'])


class SeatCoverageTests(unittest.TestCase):
    """AGENT_ADOPTION.md D15 (pc-1480): compact coverage panel after seats and
    jobs, hire commands behind a disclosure, no classifier caveat."""

    def test_agents_paints_seats_before_coverage(self):
        agents_fn = _SRC.split('function agents()')[1].split('function timelineRow')[0]
        compact = agents_fn.replace(' ', '')
        self.assertLess(compact.index("reconcileList($('seat-list')"), compact.index('renderCoverage()'))

    def test_coverage_uses_a_compact_line_not_the_server_text_blob(self):
        self.assertIn('coverageCompactLine(row)', _SRC)
        self.assertNotIn('card.append(el(\'p\',row.text));', _SRC)

    def test_unstaffed_projects_collapse_into_one_disclosure(self):
        self.assertIn('bp-coverage-collapsed', _SRC)
        self.assertIn('unstaffed (', _SRC)

    def test_hire_button_copies_the_command_and_never_dispatches_it(self):
        self.assertNotIn("fetch('/api/agents/hire'", _SRC)
        self.assertIn('navigator.clipboard.writeText(command)', _SRC)

    def test_hire_commands_stay_behind_a_disclosure(self):
        self.assertIn("el('summary','Hire…')", _SRC)

    def test_classifier_jargon_is_removed(self):
        self.assertNotIn('classifier', _SRC.lower())

    def test_not_configured_providers_show_their_install_hint(self):
        self.assertIn('row.install_hints[p]', _SRC)

    def test_coverage_panel_is_separate_from_seats(self):
        self.assertIn('id="agents-coverage-door"', _HTML)
        self.assertIn('id="agents-coverage-summary"', _HTML)
        self.assertIn('id="coverage-list"', _HTML)
        self.assertNotIn('<h2>Coverage</h2>', _HTML)
        self.assertNotIn('<h2>Seats</h2><div id="coverage-list"', _HTML)

    def test_hiring_footnote_is_present(self):
        self.assertIn('Hiring runs on this Mac through WorkForce; the desk never writes the roster.', _HTML)
        self.assertIn('not a hire-now list', _HTML)
        self.assertIn('not For You work', _HTML)

    def test_old_agents_subtitle_is_removed(self):
        self.assertNotIn('Registered local agents, schedules, and reported runtime state.', _HTML)
        self.assertNotIn('Registered local agents, schedules, and reported runtime state.', _SRC)


class SeatCoverageReviewFixTests(unittest.TestCase):
    """pc-1480 review fixes: reconcile coverage rows, lazy hire bodies,
    unknown project stores stay active."""

    def test_render_coverage_reconciles_rows_instead_of_replacing_children(self):
        fn = _SRC.split('function renderCoverage()')[1].split('function agents()')[0]
        self.assertIn('reconcileList($(\'coverage-list\')', fn)
        self.assertNotIn('container.replaceChildren()', fn)

    def test_hire_commands_populate_only_when_disclosure_opens(self):
        self.assertIn('paintCoverageHireBody(hire, row)', _SRC)
        self.assertIn("container.addEventListener('toggle'", _SRC)
        self.assertNotIn('coverageHireBlock(row)', _SRC)

    def test_hire_toggle_listener_uses_capture_phase(self):
        fn = _SRC.split('function ensureCoverageHireDelegation()')[1].split('function renderCoverage()')[0]
        self.assertRegex(fn, r"addEventListener\('toggle'[\s\S]*,\s*true\)")

    def test_unavailable_project_store_is_not_treated_as_zero_open(self):
        self.assertIn('function projectStoreState(slug)', _SRC)
        self.assertIn('function coverageIsActive(row)', _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn("if(projectStoreState(row.project)!=='available')returntrue", compact)
        self.assertIn("'Store unavailable'", _SRC)

    def test_open_hire_disclosures_repaint_after_reconcile(self):
        self.assertIn('refreshCoverageHireBodies($(\'coverage-list\'))', _SRC)


class AgentsCoverageHarnessTests(unittest.TestCase):
    """pc-1480: live-shaped fixture proves seat-first order, one collapsed
    unstaffed line, and hire commands hidden until disclosure opens."""

    _HARNESS = Path(__file__).resolve().parent / 'harness' / 'agents_coverage_check.mjs'

    @classmethod
    def setUpClass(cls) -> None:
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping agents coverage harness')
        proc = subprocess.run([node, str(cls._HARNESS)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'agents coverage harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        cls.result = json.loads(proc.stdout)

    def test_seat_cards_render_before_coverage(self) -> None:
        self.assertGreater(self.result['seat_count'], 0)

    def test_exactly_one_collapsed_unstaffed_line(self) -> None:
        self.assertRegex(self.result['collapsed_summary'], r'\d+ projects unstaffed')

    def test_hire_commands_hidden_until_disclosure_opens(self) -> None:
        self.assertTrue(self.result['hire_hidden_until_open'])

    def test_no_classifier_text_in_the_dom(self) -> None:
        self.assertTrue(self.result['no_classifier'])

    def test_hire_disclosure_stays_open_across_repaint(self) -> None:
        self.assertTrue(self.result['hire_open_survives_repaint'])

    def test_unavailable_store_renders_active_not_collapsed(self) -> None:
        self.assertTrue(self.result['unavailable_store_active'])

    def test_closed_rows_have_no_hire_command_nodes(self) -> None:
        self.assertTrue(self.result['no_hire_nodes_while_closed'])


class RefreshTimelinePositionHarnessTests(unittest.TestCase):
    """pc-1488 cursor-reviewer finding #2: a background poll on the default
    first page (no Load more used) must keep the reader's scroll position
    and surface a new-events count, anchored on scroll depth — not only
    after timelineExpanded is set by Load more."""

    _HARNESS = Path(__file__).resolve().parent / 'harness' / 'refresh_timeline_check.mjs'

    @classmethod
    def setUpClass(cls) -> None:
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping refreshTimeline harness')
        proc = subprocess.run([node, str(cls._HARNESS)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'refreshTimeline harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        cls.result = json.loads(proc.stdout)

    def test_position_kept_while_scrolled_on_default_first_page(self) -> None:
        self.assertTrue(self.result['kept_position_while_scrolled'])

    def test_new_events_count_shown_without_load_more(self) -> None:
        self.assertRegex(self.result['new_events_count_shown_on_first_page'], r'1 new event')

    def test_poll_at_top_may_still_bring_in_newest_rows(self) -> None:
        self.assertEqual(self.result['replaced_rows_when_at_top'], ['r5', 'r4', 'r3', 'r2', 'r1'])


class SeatHeaderProjectNameTests(unittest.TestCase):
    """pc-1474 scope addition: seat headers always name their project from
    the queue, not just held seats — 'No project queue' replaces the old
    always-'Unassigned' text."""

    def test_seat_header_uses_project_name_not_held_only(self):
        self.assertIn("agent.project_name || 'No project queue'", _SRC)

    def test_unassigned_literal_is_gone_from_the_seat_header(self):
        self.assertNotIn("agent.held ? agent.held.project : 'Unassigned'", _SRC)


class CalendarRowTests(unittest.TestCase):
    def test_manual_seats_collapse_behind_on_demand_line(self):
        self.assertIn("function onDemandSeat(agent)", _SRC)
        self.assertIn("On demand seats: ", _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn("agent.group==='seat'", compact)
        self.assertIn("agent.schedule==='manual'", compact)
        self.assertIn("agent.schedule==='Notscheduled'", compact)
        self.assertIn("'No next run'", _SRC)
        self.assertIn("Last run: ", _SRC)

    def test_due_hold_reminder_and_mentioned_merge_on_the_same_row(self):
        self.assertIn("function mergeDatedWork(items)", _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn("event.kind!=='deadline'&&event.kind!=='timer'&&event.kind!=='reminder'&&event.kind!=='mentioned'", compact)
        self.assertIn("row.due=", compact)
        self.assertIn("row.hold=", compact)
        self.assertIn("row.reminder=", compact)
        self.assertIn("row.mentioned=", compact)
        self.assertIn("'Due'", _SRC)
        self.assertIn("'Hold until'", _SRC)
        self.assertIn("'Expired hold'", _SRC)
        self.assertIn("'Mentioned date'", _SRC)
        self.assertIn("'Reminder'", _SRC)

    def test_agenda_centres_today_and_collapses_past(self):
        self.assertIn("function agendaGroup(row, origin)", _SRC)
        self.assertIn("id=\"calendar-today\"", _HTML)
        self.assertIn("id=\"calendar-next\"", _HTML)
        self.assertIn("id=\"calendar-past\"", _HTML)
        self.assertIn("Past and overdue", _SRC)
        self.assertIn("id=\"calendar-prev-week\"", _HTML)
        self.assertIn("id=\"calendar-today-btn\"", _HTML)

    def test_agenda_group_buckets_per_clock_so_overdue_beats_a_later_reminder(self):
        fn = _SRC.split('function agendaGroup(row, origin)')[1].split('function ')[0]
        compact = fn.replace(' ', '')
        self.assertIn('days.some(day=>day===origin)', compact)
        self.assertIn('days.some(day=>day<origin)', compact)
        self.assertNotIn('days.some(day=>day>origin)', compact)

    def test_needs_you_on_calendar_is_decide_only(self):
        self.assertIn("event.attention_face==='decide'", _SRC)
        self.assertIn("decide?'Needs you'", _SRC)

    def test_calendar_links_go_through_the_reader_return(self):
        self.assertIn("function datedHref(event)", _SRC)
        self.assertIn("readerHref('/work-order?'", _SRC)

    def test_missing_calendar_file_is_not_configured(self):
        self.assertIn("No local calendar file. Agent schedules above are independent of a calendar file.", _SRC)
        self.assertIn("No next run reported", _SRC)


class ActivityCueTests(unittest.TestCase):
    """pc-1483/pc-1485: elapsed feedback on a seat row is restrained and
    evidence-bound — read only from the server-reported shift.age_seconds
    on each real refresh, never a local per-second ticking animation, and
    always a time budget, never a fake percent-complete value."""

    def test_elapsed_is_read_from_server_shift_evidence_not_a_local_timer(self):
        fn = _SRC.split('function elapsedText(agent)')[1].split('\nfunction ')[0]
        self.assertIn('agent.shift.age_seconds', fn)
        self.assertNotIn('setInterval', fn)
        self.assertNotIn('Date.now()', fn)

    def test_elapsed_text_is_a_real_duration_not_a_fake_progress_value(self):
        self.assertIn('function elapsedText(agent)', _SRC)
        fn = _SRC.split('function elapsedText(agent)')[1].split('\n}')[0]
        ret = [line for line in fn.splitlines() if 'return' in line]
        self.assertTrue(ret)
        self.assertFalse(any('%' in line for line in ret))
        self.assertIn('budget', fn)


class NewEventsAffordanceTests(unittest.TestCase):
    """pc-1483: a background Timeline refresh while the reader has loaded
    older pages must not silently move the reading position — it shows an
    affordance instead."""

    def test_new_events_control_exists_in_the_markup(self):
        self.assertIn('id="timeline-new-events"', _HTML)

    def test_background_refresh_does_not_replace_an_expanded_reading_position(self):
        fn = _SRC.split('async function refreshTimeline(')[1].split('async function refreshRemote(')[0]
        self.assertIn('timelineExpanded', fn)

    def test_loading_more_marks_the_reader_as_expanded(self):
        self.assertIn('timelineExpanded = true', _SRC.replace(' ', '') and _SRC)
        self.assertIn('timelineExpanded=true', _SRC.replace(' ', ''))


class ProjectsSurfaceTests(unittest.TestCase):
    """pc-1486 / PROJECTS_INTENT: comparison rows, activity ordering,
    quiet collapse, unavailable/partial honesty, and scoped go links."""

    def test_projects_page_uses_a_comparison_table_not_card_grid(self):
        self.assertIn('id="projects-list"', _HTML)
        self.assertIn('bp-projects-row', _HTML)
        self.assertIn("function projects()", _SRC)
        self.assertIn("function projectComparisonRow(", _SRC)

    def test_activity_ordering_prefers_running_then_attention_then_open(self):
        self.assertIn('function projectActivitySort(a,b)', _SRC)
        compact = _SRC.replace(' ', '')
        self.assertIn('if(project.running)return0', compact)
        self.assertIn('if(project.claimed)return1', compact)
        self.assertIn('if(project.attention)return2', compact)

    def test_quiet_projects_collapse_into_one_disclosure(self):
        self.assertIn('bp-projects-collapsed', _SRC)
        self.assertIn('Quiet projects (no open work, no seats)', _SRC)

    def test_unavailable_store_never_paints_zero_open(self):
        self.assertIn("project.state!=='available'", _SRC)
        self.assertIn("'Store unavailable'", _SRC)
        self.assertIn('partial (limited to 2,000)', _SRC)

    def test_last_change_reads_from_server_not_read_time(self):
        self.assertIn('project.last_change', _SRC)
        self.assertIn("'no activity recorded'", _SRC)

    def test_go_links_carry_the_project_id(self):
        compact = _SRC.replace(' ', '')
        self.assertIn('params=id=>newURLSearchParams({project:id})', compact)
        self.assertIn("newURLSearchParams({project:project.id,attention:'any'})", compact)
        self.assertIn("'/map?project='+encodeURIComponent(project.id)", compact)

    def test_go_links_include_scoped_agents_and_delivery_with_reader_return(self):
        compact = _SRC.replace(' ', '')
        self.assertIn("link('Agents','/agents?'+retained)", compact)
        self.assertIn("link('Delivery','/delivery?'+retained)", compact)
        self.assertIn('return_to:projectReturnTo()', compact)

    def test_agents_now_merges_live_seats_with_coverage_not_roster_labels(self):
        compact = _SRC.replace(' ', '')
        self.assertIn('functionprojectLiveSeats(project)', compact)
        self.assertIn("order.status!=='in_progress'", compact)
        self.assertIn('!order.live_with', compact)
        self.assertIn('functionprojectCoverageLists(row)', compact)
        agents_fn = _SRC.split('function projectAgentsNowText(project)')[1].split('function projectReturnTo')[0]
        self.assertIn('projectCoverageStaffedText(project,{skipProviders:liveProviders})', compact.replace(' ', ''))
        self.assertIn('seatProviderFromId(id)', agents_fn)
        self.assertNotIn("a.group==='seat'", agents_fn)
        quiet_fn = _SRC.split('function projectIsQuiet(project)')[1].split('function projectActivityRank')[0]
        self.assertIn('projectHasRegisteredSeats(project)', quiet_fn)
        self.assertNotIn("a.group==='seat'", quiet_fn)

    def test_scan_derived_counts_carry_partial_marker_when_store_is_truncated(self):
        self.assertIn("projectCountCell(project,'deferred')", _SRC)
        live_fn = _SRC.split('function projectLiveParkedText(project)')[1].split('function projectLiveSeats')[0]
        self.assertIn('project.partial', live_fn)
        self.assertIn('partial (limited to 2,000)', live_fn)

    def test_breakdown_is_keyboard_reachable(self):
        self.assertIn('bp-projects-detail', _SRC)
        self.assertIn("el('summary','Breakdown')", _SRC)


class ProjectsSurfaceHarnessTests(unittest.TestCase):
    """pc-1486: live-shaped fixture proves comparison rows, quiet collapse,
    unavailable honesty, and project-scoped links."""

    _HARNESS = Path(__file__).resolve().parent / 'harness' / 'projects_surface_check.mjs'

    @classmethod
    def setUpClass(cls) -> None:
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping projects surface harness')
        proc = subprocess.run([node, str(cls._HARNESS)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'projects surface harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        cls.result = json.loads(proc.stdout)

    def test_comparison_rows_render_for_active_projects(self) -> None:
        self.assertGreater(self.result['active_row_count'], 0)

    def test_quiet_projects_collapse_to_one_line(self) -> None:
        self.assertRegex(self.result['quiet_summary'], r'Quiet projects')

    def test_unavailable_store_is_not_zero_open(self) -> None:
        self.assertTrue(self.result['unavailable_honest'])

    def test_go_links_include_project_query(self) -> None:
        self.assertTrue(self.result['links_carry_project'])

    def test_agents_and_delivery_links_reader_return_to_projects(self) -> None:
        self.assertTrue(self.result['agents_delivery_return'])

    def test_live_claim_still_shows_idle_hired_coverage(self) -> None:
        self.assertTrue(self.result['live_merges_idle_coverage'])

    def test_roster_seat_without_live_order_reads_hired_coverage(self) -> None:
        self.assertTrue(self.result['roster_reads_coverage'])

    def test_unregistered_project_reads_none_staffed(self) -> None:
        self.assertTrue(self.result['unregistered_none_staffed'])

    def test_partial_scan_counts_carry_limit_marker(self) -> None:
        self.assertTrue(self.result['partial_counts_marked'])

    def test_breakdown_disclosure_is_present(self) -> None:
        self.assertTrue(self.result['breakdown_present'])

    def test_portfolio_spark_marks_hot_store(self) -> None:
        self.assertTrue(self.result['spark_hot'])

    def test_compare_bars_door_open_work_and_skip_quiet(self) -> None:
        self.assertGreaterEqual(self.result['compare_rows'], 4)
        self.assertTrue(self.result['compare_has_work_door'])
        self.assertTrue(self.result['compare_skips_quiet'])


class ConnectionsEngineTests(unittest.TestCase):
    def test_engine_list_paints_versions_reachability_and_supervisor(self):
        self.assertIn('id="engine-list"', _HTML)
        self.assertIn('id="capability-list"', _HTML)
        self.assertIn('id="connection-exceptions"', _HTML)
        self.assertIn("function engines()", _SRC)
        self.assertIn("function capabilities()", _SRC)
        self.assertIn("'WorkLane engine'", _SRC)
        self.assertIn("'WorkForce engine'", _SRC)
        self.assertIn("'WorkLane API'", _SRC)
        self.assertIn("'Supervisor last pass'", _SRC)
        self.assertIn("function connectionExceptions()", _SRC)
        self.assertIn("'Activated '", _SRC)
        self.assertIn("'Last observation '", _SRC)
        self.assertIn("'Last outcome '", _SRC)
        self.assertIn("'Next: '", _SRC)
        self.assertIn("'Endpoint, path and version'", _SRC)
        self.assertNotIn("'Observed '", _SRC)

    def test_installed_engines_panel_is_receipts_only(self):
        engines_fn = _SRC.split('function engines()')[1].split('function excludedStores()')[0]
        self.assertIn('receiptEngineRows()', engines_fn)
        self.assertNotIn('capabilityEngineRows()', engines_fn)
        self.assertNotIn("'WorkLane API'", engines_fn)
        self.assertNotIn("'Supervisor last pass'", engines_fn)
        self.assertIn("reconcileList($('engine-list')", engines_fn)
        self.assertIn('Engine capabilities', _HTML)
        caps_fn = _SRC.split('function capabilities()')[1].split('function engines()')[0]
        self.assertIn('capabilityEngineRows()', caps_fn)
        self.assertIn("reconcileList($('capability-list')", caps_fn)

    def test_receipt_timestamp_is_activated_not_observed(self):
        self.assertIn("record.activated_at", _SRC)
        self.assertIn("'Activated '", _SRC)
        self.assertNotIn("'Observed '", _SRC)

    def test_failed_supervisor_is_not_painted_available(self):
        self.assertIn("EXCEPTION_STATES", _SRC)
        self.assertIn("'failed'", _SRC)
        self.assertIn("item.usable===false", _SRC.replace(' ', ''))

    def test_transport_warning_includes_engine_exceptions(self):
        self.assertIn("engineRows().filter(([,engine])=>isException(engine))", _SRC.replace(' ', ''))
        self.assertIn("The live indicator is only the update transport.", _HTML)


class SeatParkedClaimRowTests(unittest.TestCase):
    """pc-1495: seat rows show finishing and parked handoff copy."""

    def test_held_link_prefers_live_claim_then_finishing_then_parked(self):
        fn = _SRC.split('function heldLink(agent)')[1].split('function elapsedText')[0]
        compact = fn.replace(' ', '')
        self.assertLess(compact.index('currentOrderFor(agent)'), compact.index('agent.finishing'))
        self.assertLess(compact.index('agent.finishing'), compact.index('parkedIds.length'))
        self.assertIn('Finishing·parked', compact.replace(' ', ''))
        self.assertIn('Parked:', fn)
        self.assertIn('awaiting integration', fn)

    def test_timeline_uses_parked_time_when_no_live_claim(self):
        fn = _SRC.split('function agentTimelineValues(agent)')[1].split('function agentTimeline(agent)')[0]
        self.assertIn('agent.parked', fn)
        self.assertIn('p.verified', fn)
        self.assertIn('latestParkedSince(agent)', fn)
        self.assertIn('currentShiftParkedIds(agent)', _SRC)

class TimelineClearResetsPeriodTests(unittest.TestCase):
    """pc-1488 browser check on .58: Clear reset the period select but left
    ?period= in the URL because clearTimelineFilters never cleared the
    client-side timelinePeriod that timelineFilterParams() serialises."""

    def test_clear_timeline_filters_clears_period_state(self):
        source = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'operations.js').read_text()
        start = source.index('function clearTimelineFilters()')
        body = source[start:source.index('\n}\n', start)]
        self.assertIn("timelinePeriod = ''", body)
        self.assertLess(body.index("timelinePeriod = ''"), body.index('updateTimelineFilters()'))


class TimelineActivityChartTests(unittest.TestCase):
    """Issue 142: day/week activity histogram lives on Timeline only."""

    def test_timeline_view_hosts_the_activity_chart(self):
        self.assertIn('id="timeline-activity"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertIn('id="timeline-activity-summary"', _HTML)
        view = _HTML.split('id="timeline-view"', 1)[1].split('id="connections-view"', 1)[0]
        self.assertIn('id="timeline-activity"', view)
        self.assertNotIn('id="timeline-activity"', _HTML.split('id="timeline-view"', 1)[0])

    def test_timeline_paints_activity_from_the_spine(self):
        fn = _SRC.split('function timeline()')[1].split('function timelineFilterParams')[0]
        self.assertIn('paintTimelineActivity()', fn)
        self.assertIn('paintTimelineDoors()', fn)
        self.assertIn("'Quiet in this window.'", _SRC)
        self.assertIn('timelineData.activity', _SRC)
        self.assertIn('activity.day', _SRC)
        self.assertIn('activity.week', _SRC)
        self.assertIn('activity.window', _SRC)

    def test_period_selects_day_or_week_grain(self):
        fn = _SRC.split('function timelineActivitySeries()')[1].split('function timelineWorkHref')[0]
        self.assertIn("timelinePeriod === '1'", fn)
        self.assertIn("timelinePeriod === '3'", fn)
        self.assertIn("timelinePeriod === '7'", fn)
        self.assertIn("grain: 'hour'", fn)
        self.assertIn("grain: 'day'", fn)
        self.assertIn('activity.three', fn)

    def test_activity_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping timeline activity harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'timeline_activity_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'timeline activity harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        result = json.loads(proc.stdout)
        self.assertEqual(result['default_summary'], '5 events · last 14 days · by day')
        self.assertEqual(result['default_bars'], 14)
        self.assertEqual(result['day_summary'], '3 events · last day · by hour')
        self.assertEqual(result['day_bars'], 24)
        self.assertEqual(result['week_bars'], 7)
        self.assertEqual(result['quiet_summary'], 'Quiet in this window.')
        self.assertTrue(result['quiet_chart_hidden'])
        self.assertTrue(result['unavailable_hidden'])
        self.assertEqual(result['kinds'], ['work', 'delivery'])
        self.assertEqual(result['healthy_work'], 'Work2 eventsWorkLane firings')
        self.assertEqual(result['healthy_delivery'], 'Delivery3 eventsGitHub firings')
        self.assertEqual(result['work_href'], '/work')
        self.assertEqual(result['delivery_href'], '/delivery')
        self.assertTrue(result['has_line'])
        self.assertEqual(result['hist_counts'], 4)
        self.assertEqual(result['day_count'], 2)
        self.assertTrue(result['has_rail'])
        self.assertEqual(result['event_times'], 2)
        self.assertEqual(result['source_labels'], 2)
        self.assertEqual(result['quiet_work'], 'WorknoneWorkLane firings')
        self.assertEqual(result['quiet_delivery'], 'DeliverynoneGitHub firings')
        self.assertEqual(result['quiet_stream'], 'No timeline rows in the readable window.')
        self.assertEqual(result['unavailable_doors'], ['Workunavailable', 'Deliveryunavailable'])


class TimelineHeroTests(unittest.TestCase):
    """pc-1544 / CAP_ACQUAINTANCE_052 C5: histogram/line is the Timeline
    activity hero. Doors go to Work and Delivery. Timeline stays in the
    acquaintance bar — not deferred, not a new page."""

    def test_hero_sits_on_timeline_above_filters_and_the_event_list(self):
        timeline = _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        delivery = _HTML.split('id="delivery-view"')[1].split('id="timeline-view"')[0]
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        self.assertIn('id="timeline-hero"', timeline)
        self.assertIn('Timeline time spine', timeline)
        self.assertIn('>Firings<', timeline)
        self.assertIn('id="timeline-doors"', timeline)
        self.assertIn('id="timeline-activity"', timeline)
        self.assertIn('id="timeline-activity-chart"', timeline)
        self.assertIn('bp-timeline-facets', timeline)
        self.assertIn('bp-timeline-stream', timeline)
        self.assertLess(timeline.index('id="timeline-hero"'), timeline.index('id="timeline-filters"'))
        self.assertLess(timeline.index('id="timeline-doors"'), timeline.index('id="timeline-activity"'))
        self.assertLess(timeline.index('id="timeline-activity"'), timeline.index('id="timeline-filters"'))
        self.assertLess(timeline.index('id="timeline-filters"'), timeline.index('id="timeline-list"'))
        self.assertLess(timeline.index('id="timeline-list"'), timeline.index('id="timeline-source-strip"'))
        self.assertEqual(_HTML.count('id="timeline-hero"'), 1)
        self.assertEqual(_HTML.count('id="timeline-doors"'), 1)
        self.assertNotIn('id="timeline-hero"', overview)
        self.assertNotIn('id="timeline-hero"', work)
        self.assertNotIn('id="timeline-hero"', agents)
        self.assertNotIn('id="timeline-hero"', delivery)
        self.assertNotIn('id="timeline-hero"', calendar)
        self.assertNotIn('id="timeline-doors"', delivery)
        self.assertNotIn('id="delivery-hero"', timeline)
        self.assertNotIn('id="work-flow"', timeline)
        self.assertNotIn('id="calendar-load"', timeline)

    def test_paint_uses_work_and_delivery_doors_not_neighbor_heroes(self):
        self.assertIn('function paintTimelineDoors(', _SRC)
        self.assertIn('function timelineDoorChip(', _SRC)
        self.assertIn('function paintTimelineActivityLine(', _SRC)
        paint = _SRC.split('function paintTimelineDoors(')[1].split('function paintTimelineActivityLine(')[0]
        compact = paint.replace(' ', '')
        self.assertIn("'Work'", paint)
        self.assertIn("'Delivery'", paint)
        self.assertIn("'WorkLane firings'", paint)
        self.assertIn("'GitHub firings'", paint)
        self.assertIn("timelineWorkHref()", compact)
        self.assertIn("'/delivery'", paint)
        self.assertIn('unavailable', paint)
        self.assertIn("'none'", paint)
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('Decide', paint)
        self.assertNotIn('For You', paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('POS', paint)
        timeline = _SRC.split('function timeline()')[1].split('function timelineFilterParams')[0]
        self.assertIn('paintTimelineDoors()', timeline)
        self.assertIn('paintTimelineActivity()', timeline)
        self.assertLess(timeline.index('paintTimelineDoors'), timeline.index('paintTimelineActivity'))
        line = _SRC.split('function paintTimelineActivityLine(')[1].split('function paintTimelineActivity(')[0]
        self.assertIn('bp-timeline-hist-line', line)
        self.assertIn('polyline', line)

    def test_hero_weight_beats_filter_mast_and_holds_neighbors(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-timeline-hero', css)
        self.assertIn('.bp-timeline-doors', css)
        self.assertIn('.bp-timeline-hist-line', css)
        self.assertIn('.bp-timeline-hist-count', css)
        self.assertIn('.bp-timeline-stream', css)
        self.assertIn('#timeline-view .bp-filters', css)
        primary = css.split('.bp-timeline-door-primary')[1].split('}')[0]
        self.assertIn('font-size: 20px', primary)
        filters = css.split('#timeline-view .bp-filters input')[1].split('}')[0]
        self.assertIn('min-height: 28px', filters)
        self.assertIn('id="delivery-hero"', _HTML)
        self.assertIn('id="delivery-ci-spark"', _HTML)
        self.assertIn('id="overview-face-chips"', _HTML)
        self.assertIn('id="agents-canvas"', _HTML)
        self.assertIn('id="calendar-load"', _HTML)
        self.assertIn('id="calendar-doors"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertIn('href="/timeline"', nav)
        self.assertIn('data-page="timeline"', nav)

    def test_timeline_stays_in_the_acquaintance_bar(self):
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        pages = re.findall(r'data-page="([^"]+)"', nav)
        self.assertEqual(
            pages,
            ['overview', 'work', 'projects', 'agents', 'delivery', 'timeline',
             'calendar', 'connections', 'settings'],
        )
        self.assertIn('href="/map"', nav)
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('deferred', nav.lower())
        self.assertNotIn('later', nav.lower())


class TimelineTimeSpineVisualFinishTests(unittest.TestCase):
    """Timeline time-spine mock-parity: firings histogram + line is the
    first-read hero. Stream is events by time. Not a quiet list."""

    def test_first_read_is_time_spine_hero_not_a_quiet_list(self):
        timeline = _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0]
        self.assertIn('Timeline time spine', timeline)
        self.assertIn('>Firings<', timeline)
        self.assertIn('id="timeline-activity-chart"', timeline)
        self.assertIn('bp-timeline-facets', timeline)
        self.assertIn('bp-timeline-stream', timeline)
        self.assertIn('id="timeline-note"', timeline)
        self.assertLess(timeline.index('id="timeline-hero"'), timeline.index('id="timeline-filters"'))
        self.assertLess(timeline.index('id="timeline-filters"'), timeline.index('id="timeline-list"'))
        self.assertLess(timeline.index('id="timeline-activity"'), timeline.index('id="timeline-list"'))
        self.assertLess(timeline.index('id="timeline-list"'), timeline.index('id="timeline-stream-more"'))
        self.assertLess(timeline.index('id="timeline-stream-more"'), timeline.index('id="timeline-source-strip"'))
        self.assertNotIn('id="work-band-act-now"', timeline)
        self.assertNotIn('id="for-you-decide"', timeline)
        self.assertNotIn('wo-tile', timeline)
        self.assertNotIn('Act now', timeline)

    def test_css_weights_firings_hero_over_quiet_filters_and_stream(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-timeline-hero', css)
        self.assertIn('.bp-timeline-hist-count', css)
        self.assertIn('.bp-timeline-facets', css)
        self.assertIn('.bp-timeline-stream', css)
        self.assertIn('.bp-timeline-rail', css)
        self.assertIn('.bp-timeline-event', css)
        hero = css.split('.bp-timeline-door-primary')[1].split('}')[0]
        self.assertIn('font-size: 20px', hero)
        hist = css.split('.bp-timeline-hist {')[1].split('}')[0]
        self.assertIn('height: 176px', hist)
        filters = css.split('#timeline-view .bp-filters input')[1].split('}')[0]
        self.assertIn('min-height: 28px', filters)

    def test_paint_keeps_c5_doors_and_groups_the_stream_by_time(self):
        self.assertIn('function paintTimelineDoors(', _SRC)
        self.assertIn('function paintTimelineActivityLine(', _SRC)
        self.assertIn('function buildTimelineDays(', _SRC)
        self.assertIn('function timelineDayNode(', _SRC)
        self.assertIn('function timelineClock(', _SRC)
        self.assertIn("'WorkLane firings'", _SRC)
        self.assertIn("'GitHub firings'", _SRC)
        self.assertIn('bp-timeline-event', _SRC)
        self.assertIn('Quiet in this window.', _SRC)
        self.assertIn('Timeline is unavailable right now.', _SRC)
        self.assertIn('No timeline rows in the readable window.', _SRC)
        paint = _SRC.split('function paintTimelineDoors(')[1].split('function paintTimelineActivityLine(')[0]
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('For You', paint)
        timeline = _SRC.split('function timeline()')[1].split('function timelineFilterParams')[0]
        self.assertIn('buildTimelineDays(', timeline)
        self.assertLess(timeline.index('paintTimelineDoors'), timeline.index('paintTimelineActivity'))

    def test_does_not_regress_neighbor_surfaces(self):
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="delivery-hero"', _HTML)
        self.assertIn('id="calendar-hero"', _HTML)
        self.assertIn('id="delivery-ci-spark"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('POS', _HTML)


class TimelineDensityCapTests(unittest.TestCase):
    """pc-1560 WANT residual: Firings hist+line keeps first-read hero weight;
    the event stream is capped with a visible +N remainder door. Compose
    with #190 time-spine — elevate density, do not thrash neighbors."""

    def test_stream_host_and_remainder_door_sit_under_the_hero(self):
        timeline = _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0]
        self.assertIn('id="timeline-hero"', timeline)
        self.assertIn('id="timeline-activity-chart"', timeline)
        self.assertIn('id="timeline-stream-more"', timeline)
        self.assertIn('bp-timeline-more', timeline)
        self.assertLess(timeline.index('id="timeline-hero"'), timeline.index('id="timeline-filters"'))
        self.assertLess(timeline.index('id="timeline-activity"'), timeline.index('id="timeline-list"'))
        self.assertLess(timeline.index('id="timeline-list"'), timeline.index('id="timeline-stream-more"'))
        self.assertLess(timeline.index('id="timeline-stream-more"'), timeline.index('id="timeline-more"'))
        self.assertEqual(_HTML.count('id="timeline-stream-more"'), 1)
        self.assertNotIn('id="timeline-stream-more"', _HTML.split('id="timeline-view"')[0])
        self.assertNotIn('id="work-flow"', timeline)
        self.assertNotIn('id="calendar-load"', timeline)

    def test_paint_caps_the_stream_and_exposes_remainder(self):
        compact = _SRC.replace(' ', '')
        self.assertIn('TIMELINE_STREAM_LIMIT=8', compact)
        self.assertIn('function capTimelineDays(', _SRC)
        self.assertIn('function paintTimelineRemainder(', _SRC)
        self.assertIn('function expandTimelineStream(', _SRC)
        self.assertIn("'+'+remainder+' more'", compact)
        self.assertIn('bp-timeline-remainder', _SRC)
        timeline = _SRC.split('function timeline()')[1].split('function timelineFilterParams')[0]
        self.assertIn('capTimelineDays(', timeline)
        self.assertIn('paintTimelineRemainder(', timeline)
        self.assertIn('timelineMore && capped.remainder === 0', timeline.replace(' ', ''))
        self.assertIn('resetTimelineStreamWindow()', _SRC)
        paint = _SRC.split('function paintTimelineDoors(')[1].split('function paintTimelineActivityLine(')[0]
        self.assertIn("'WorkLane firings'", paint)
        self.assertIn("'GitHub firings'", paint)
        self.assertIn("'none'", paint)
        self.assertIn('unavailable', paint)
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('For You', paint)

    def test_css_keeps_hist_line_louder_than_the_capped_stream(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('pc-1560', css)
        hist = css.split('.bp-timeline-hist {')[1].split('}')[0]
        self.assertIn('height: 176px', hist)
        activity = css.split('.bp-timeline-activity h2 {')[1].split('}')[0]
        self.assertIn('font-size: 22px', activity)
        stream = css.split('.bp-timeline-stream {')[1].split('}')[0]
        self.assertIn('padding: 8px 12px', stream)
        filters = css.split('#timeline-view .bp-filters input')[1].split('}')[0]
        self.assertIn('min-height: 28px', filters)
        self.assertIn('.bp-timeline-remainder', css)
        calendar = css.split('#calendar-view .ov-cal-load-chart {')[1].split('}')[0]
        self.assertIn('height: 128px', calendar)

    def test_density_harness_caps_and_keeps_honest_empty(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping timeline density harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'timeline_activity_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'timeline density harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        result = json.loads(proc.stdout)
        self.assertEqual(result['stream_cap'], 8)
        self.assertEqual(result['dense_events'], 8)
        self.assertEqual(result['dense_remainder'], '+2 more')
        self.assertEqual(result['expanded_events'], 10)
        self.assertEqual(result['expanded_remainder'], '')
        self.assertEqual(result['quiet_remainder'], '')
        self.assertEqual(result['quiet_stream'], 'No timeline rows in the readable window.')
        self.assertEqual(result['quiet_work'], 'WorknoneWorkLane firings')
        self.assertEqual(result['unavailable_doors'], ['Workunavailable', 'Deliveryunavailable'])
        self.assertTrue(result['has_line'])
        self.assertEqual(result['healthy_work'], 'Work2 eventsWorkLane firings')

    def test_does_not_regress_neighbors_or_held_surfaces(self):
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="agents-canvas"', _HTML)
        self.assertIn('id="delivery-hero"', _HTML)
        self.assertIn('id="calendar-hero"', _HTML)
        self.assertIn('id="calendar-load"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('POS', _HTML)
        self.assertNotIn('point of sale', _HTML.lower())
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertIn('href="/timeline"', nav)


class ProjectsReturnAndFinishingTests(unittest.TestCase):
    """pc-1486 second pass: /projects is a valid reader return, and a seat
    finishing parked work in a project keeps that project out of Quiet."""

    def test_projects_is_an_allowed_reader_return(self):
        source = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'reader-navigation.mjs').read_text()
        self.assertIn("'/projects'", source)
        self.assertRegex(source, r"work\|map\|calendar\|timeline\|projects")

    def test_finishing_seat_counts_as_live_for_the_project(self):
        source = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'operations.js').read_text()
        start = source.index('function projectLiveSeats(')
        body = source[start:source.index('\n}\n', start)]
        self.assertIn('agent.finishing', body)
        self.assertIn("p.project===project.id", body)

class ReaderNavAndOutlineTests(unittest.TestCase):
    """pc-1491 second pass: nav scroll falls back to scrollLeft, and outline or
    fragment navigation opens the targeted collapsed section."""

    def test_nav_scroll_has_a_scroll_left_fallback(self):
        src = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'nav-shell.mjs').read_text()
        fn = src.split('export function ensureActiveNavVisible(')[1].split('export function')[0]
        self.assertIn("typeof nav.scrollTo === 'function'", fn)
        self.assertIn('catch { nav.scrollLeft = next; }', fn)

    def test_hash_navigation_opens_the_collapsed_section(self):
        src = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'nav-shell.mjs').read_text()
        self.assertIn('export function revealHashSection(', src)
        self.assertIn("node.tagName === 'DETAILS') node.open = true", src)
        self.assertIn("addEventListener?.('hashchange'", src)
        for name in ('work-order.js', 'documents.js'):
            reader = (Path(__file__).resolve().parents[1] / 'static' / 'js' / name).read_text()
            self.assertIn('bindHashReveal(document)', reader)
            # The reader imports nav-shell dynamically; the helper must be part of
            # that destructuring or the paint aborts after the outline (.63 defect).
            self.assertRegex(reader, r"const \{[^}]*bindHashReveal[^}]*\} = await import\('/js/nav-shell.mjs'\)")


class DeliverySurfaceTests(unittest.TestCase):
    """pc-1487: exception-first delivery rollups with filters and honest badges."""

    def test_delivery_filters_and_boundary_controls_exist(self):
        self.assertIn('id="delivery-filters"', _HTML)
        self.assertIn('id="delivery-boundary"', _HTML)
        self.assertIn('id="delivery-repo"', _HTML)
        self.assertIn('id="delivery-type"', _HTML)
        self.assertIn('id="delivery-period"', _HTML)

    def test_delivery_uses_one_collapsible_source_label(self):
        self.assertIn('bp-delivery-note', _HTML)
        self.assertNotIn('These records do not prove an agent is currently running.', _HTML)

    def test_merged_pull_requests_badge_event_not_closed_state(self):
        fn = _SRC.split('function deliveryEvidenceRow(')[1].split('function deliveryGroupRow')[0]
        self.assertIn('deliveryPullEvent(item)', fn)
        self.assertNotIn('badge(item.state)', fn)

    def test_delivery_receipt_match_uses_installed_wording(self):
        badge_fn = _SRC.split('function deliveryBadgeState(')[1].split('function deliveryPeriodCutoff')[0]
        self.assertIn("'deployed'", badge_fn)
        self.assertIn('`Activated ${when}`', badge_fn)
        # Activated only with a time; without one the badge reads Installed
        # (pc-1487 second pass: never overclaim activation).
        self.assertNotIn("'Activated'", badge_fn)
        self.assertIn('`Installed${version}`', badge_fn)
        self.assertIn("'version_note'", badge_fn)
        self.assertNotIn("'Deployed'", badge_fn)
        self.assertNotIn("'Released'", badge_fn)
        summary_fn = _SRC.split('function deliverySummaryLine(')[1].split('function deliveryEvidenceRow')[0]
        self.assertIn('`Activated ${activated}`', summary_fn)
        self.assertIn('`Version note ${repo.deployment.version}`', summary_fn)
        self.assertNotIn("'Running'", summary_fn)
        self.assertNotIn("'Receipt'", summary_fn)

    def test_delivery_pull_event_prefers_merged_before_state(self):
        fn = _SRC.split('function deliveryPullEvent(')[1].split('function deliveryBadgeState')[0]
        self.assertIn('merged_at', fn)
        self.assertIn('merged', fn)
        self.assertLess(fn.index('merged_at'), fn.index('pr_event'))

    def test_delivery_status_reports_cache_age_separately(self):
        fn = _SRC.split('function remoteStatusText(')[1].split('async function refreshRemote')[0]
        self.assertIn('cache_age_seconds', fn)
        self.assertIn('fetched_at', fn)

    def test_delivery_groups_expand_with_event_time_labels(self):
        self.assertIn('bp-delivery-group', _SRC)
        self.assertIn('Event ${date', _SRC)
        self.assertIn('Fetched ${date', _SRC)

    def test_clear_delivery_filters_resets_period_from_url(self):
        body = _SRC.split('function clearDeliveryFilters()')[1].split('function paintDelivery')[0]
        self.assertIn("deliveryPeriod=''", body)
        self.assertIn("deliveryRepo=''", body)


class ChangeFeedLiveCueTests(unittest.TestCase):
    """Change-feed events flash Current execution once (MAP_FOCUSED_PROJECT
    / OPERATIONS_EVOLUTION: one-shot on a real source event, never ambient).
    connectChanges() keeps the harness bootMarker shape — payload is read
    from the document event change-feed.mjs already dispatches."""

    def test_note_live_source_writes_the_cue_and_flashes(self):
        self.assertIn('function noteLiveSource(change)', _SRC)
        fn = _SRC.split('function noteLiveSource(change)')[1].split('function overview()')[0]
        self.assertIn("change.source!=='workforce'", fn.replace(' ', ''))
        self.assertIn("host.dataset.liveSource=change.source", fn.replace(' ', ''))
        self.assertIn("$('overview-exec-cue')", fn)
        self.assertIn('bp-live-flash', fn)

    def test_reduced_motion_skips_the_flash(self):
        fn = _SRC.split('function noteLiveSource(change)')[1].split('function overview()')[0]
        self.assertIn("document.body.classList.contains('bp-reduce-motion')", fn)
        self.assertIn('return;', fn)

    def test_desk_changed_listener_feeds_note_live_source(self):
        self.assertIn("document.addEventListener('bp:desk-changed',event=>{noteLiveSource(event.detail);});", _SRC)

    def test_exec_cue_exists_in_markup(self):
        self.assertIn('id="overview-exec-cue"', _HTML)

    def test_connect_changes_callback_keeps_the_harness_boot_marker(self):
        self.assertIn('connectChanges(()=>{if(!document.hidden){refresh();', _SRC)

    def test_change_feed_parses_the_payload_and_dispatches_desk_changed(self):
        feed = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'change-feed.mjs').read_text(encoding='utf-8')
        self.assertIn('JSON.parse(ev.data)', feed)
        self.assertIn("new CustomEvent('bp:desk-changed'", feed)
        self.assertIn('onChanged(payload || {})', feed)

    def test_new_rows_enter_with_a_one_shot_class(self):
        reconcile = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'dom-reconcile.mjs').read_text(encoding='utf-8')
        self.assertIn("enterClass = 'bp-row-enter'", reconcile)

    def test_live_flash_css_is_one_shot_not_infinite(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('@keyframes bp-live-flash', css)
        self.assertIn('.bp-live-flash { animation: bp-live-flash 400ms ease-out; }', css)
        self.assertNotIn('infinite', css.split('@keyframes bp-live-flash')[1].split('@keyframes')[0])
        self.assertIn('.bp-reduce-motion * { animation: none !important;', css)


class OverviewForYouChromeTests(unittest.TestCase):
    """pc-1506 / pc-1510: Work is the three-band board; Overview keeps
    Decide rows plus Read/Watch count chips and five KPI tiles."""

    def test_work_paints_three_bands_with_counts(self):
        for band in ('act-now', 'my-todos', 'seat-backlog'):
            self.assertIn(f'id="work-band-{band}"', _HTML)
            self.assertIn(f'id="work-{band}"', _HTML)
            self.assertIn(f'id="work-{band}-count"', _HTML)

    def test_work_attention_facet_is_orthogonal_to_status(self):
        self.assertIn('id="status-filter"', _HTML)
        self.assertIn('id="attention-filter"', _HTML)
        self.assertIn('function matchesStatusFacet', _SRC)
        self.assertIn('function matchesAttentionFacet', _SRC)
        update = _SRC.split('function updateFilters()')[1].split('function updateWorkFilters')[0]
        self.assertIn("params.set('status'", update)
        self.assertIn("params.set('attention'", update)

    def test_kpi_grid_is_five_columns_on_desktop(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('grid-template-columns: repeat(5,minmax(0,1fr))', css)
        self.assertNotIn('grid-template-columns: repeat(4,1fr)', css)


class SlimOverviewHarnessTests(unittest.TestCase):
    """pc-1509 / pc-1511: live-shaped paint — Overview chips + five Decide
    rows and an honest remainder door; Work keeps full For You, Mute, More,
    and Recent."""

    _HARNESS = Path(__file__).resolve().parent / 'harness' / 'overview_slim_check.mjs'

    @classmethod
    def setUpClass(cls) -> None:
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping overview slim harness')
        proc = subprocess.run([node, str(cls._HARNESS)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'overview slim harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        cls.result = json.loads(proc.stdout)

    def test_overview_decide_is_five_one_line_rows_without_mute_or_more(self):
        self.assertEqual(self.result['decide_rows'], 5)
        self.assertFalse(self.result['overview_has_mute'])
        self.assertFalse(self.result['overview_has_more'])
        self.assertEqual(self.result['decide_more'], '+1 more on Work')
        self.assertEqual(self.result['decide_more_href'], '/work?attention=decide')
        self.assertEqual(self.result['for_you_kpi'], 10)
        self.assertEqual(self.result['exec_line'], '1 seat on shift')
        self.assertFalse(self.result['exec_has_inspect'])
        self.assertFalse(self.result['exec_has_open_order'])

    def test_read_watch_due_are_count_chips_to_work(self):
        self.assertEqual(self.result['chips'], ['Read · 2', 'Watch · 1', 'Due · 1'])
        self.assertEqual(self.result['chip_hrefs'], [
            '/work?attention=read', '/work?attention=watch', '/work?attention=due',
        ])

    def test_due_chip_is_calendar_fed_not_an_attention_face_count(self):
        self.assertEqual(self.result['event_due_chip'], 'Due · 1')
        self.assertEqual(self.result['event_due_href'], '/calendar')
        self.assertEqual(self.result['zero_due_chips'], ['Read · 2', 'Watch · 1', 'Due · 0'])
        self.assertRegex(self.result['next_fire'], r'Next fire · loop-health in \d+m')
        self.assertEqual(self.result['helper_due_count'], 1)
        self.assertEqual(self.result['helper_next_fire'], 'Next fire · loop-health in 12m')

    def test_fifteen_decide_keeps_five_rows_and_true_remainder_door(self):
        self.assertEqual(self.result['overflow_rows'], 5)
        self.assertEqual(self.result['overflow_more'], '+10 more on Work')
        self.assertEqual(self.result['overflow_kpi'], 19)
        self.assertEqual(self.result['overflow_chips'], ['Read · 2', 'Watch · 1', 'Due · 1'])

    def test_zero_decide_is_nothing_for_you_without_remainder_door(self):
        self.assertEqual(self.result['empty_decide_text'], 'Nothing for You')
        self.assertFalse(self.result['empty_decide_more'])
        self.assertEqual(self.result['empty_kpi'], 4)
        self.assertEqual(self.result['empty_chips'], ['Read · 2', 'Watch · 1', 'Due · 1'])

    def test_work_keeps_three_bands_dual_badges_without_mute(self):
        self.assertEqual(self.result['work_act_now'], 8)
        self.assertEqual(self.result['work_my_todos'], 1)
        self.assertGreaterEqual(self.result['work_seat'], 1)
        self.assertEqual(self.result['work_mutes'], 0)
        self.assertEqual(self.result['work_more'], 0)
        self.assertTrue(self.result['work_dual_badges'])
        self.assertFalse(self.result['work_needs_you'])

    def test_unrouted_kpis_and_source_line_still_paint(self):
        self.assertIn('Unrouted', self.result['unrouted'])
        self.assertIn('2 sources', self.result['source_line'])
        self.assertEqual(self.result['kpis'], 5)
        self.assertEqual(self.result['throughput'], '3 closes · last 24h')
        self.assertEqual(self.result['throughput_href'], '/timeline?period=1')
        self.assertEqual(self.result['throughput_empty'], 'No closes in the last 24h')
        self.assertEqual(self.result['throughput_unavailable'], 'Throughput unavailable')
        self.assertIn('pepper', self.result['work_flow'])
        self.assertIn('lili', self.result['work_flow'])
        self.assertIn('Open 1 → Ready 1 → Live 2 → Done 0', self.result['work_flow'])
        self.assertEqual(self.result['work_flow_seats'], ['lili', 'pepper'])
        self.assertEqual(self.result['work_flow_empty'], 'No seat drain right now')
        self.assertEqual(self.result['work_flow_unavailable'], 'Seat load unavailable')


class SlimOverviewFollowThroughTests(unittest.TestCase):
    """pc-1509: Overview is Now — Decide Act-now only; Read/Watch chips;
    Mute/More/Recent live on Work."""

    def test_overview_does_not_paint_mute_or_more(self):
        overview_html = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        overview_fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertNotIn('id="mute-status"', overview_html)
        self.assertNotIn('id="restore-muted"', overview_html)
        self.assertNotIn('Mute 24h', overview_fn)
        self.assertNotIn("el('summary','More')", overview_fn)
        self.assertNotIn('faceEntry', overview_fn)
        decide = _SRC.split('function overviewDecideRow(order)')[1].split('function overviewFaceChip')[0]
        self.assertNotIn("el('summary','More')", decide)
        self.assertNotIn('Mute', decide)

    def test_work_owns_the_three_bands_without_mute_more(self):
        work_html = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertNotIn('id="mute-status"', work_html)
        self.assertNotIn('id="restore-muted"', work_html)
        self.assertIn('id="work-act-now"', work_html)
        self.assertIn('id="work-my-todos"', work_html)
        self.assertIn('id="work-seat-backlog"', work_html)
        work_row = _SRC.split('function workBoardRow')[1].split('function orderRow')[0]
        self.assertNotIn('Mute 24h', work_row)
        self.assertNotIn("el('summary','More')", work_row)
        self.assertIn('WORK_BAND_LIMIT=8', _SRC.replace(' ', ''))

    def test_overview_keeps_unrouted_execution_kpis_and_source_line(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertIn('id="overview-executions"', overview)
        self.assertIn('id="metrics"', overview)
        self.assertIn('id="overview-throughput"', overview)
        self.assertIn('id="overview-unrouted"', overview)
        self.assertIn('id="overview-source-line"', overview)
        self.assertNotIn('Across your projects', _HTML)
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertIn('orders.filter(isUnrouted)', fn)
        self.assertIn('UNROUTED_WORK_HREF', fn)
        self.assertIn('overviewSourceLine()', fn)

    def test_face_chips_and_decide_rows_wrap_on_narrow_viewports(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        compact = css.replace(' ', '')
        self.assertIn('.bp-overview-face-chips{display:flex;flex-wrap:wrap;', compact)
        self.assertIn('@media(max-width:900px){.bp-metrics{grid-template-columns:repeat(3,minmax(0,1fr));}', compact)
        self.assertIn('@media(max-width:560px)', css)
        self.assertIn('grid-template-columns:repeat(5,minmax(0,1fr))', compact)


class OverviewHonestyTests(unittest.TestCase):
    """pc-1511 / pc-1512: true For You count, ≤5 Act-now rows, remainder
    door, Read/Watch doors to Work, Due chip fed by Calendar."""

    def test_for_you_kpi_stays_the_true_attention_count(self):
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        compact = fn.replace(' ', '')
        self.assertIn("['ForYou',forYou.length,'/work?attention=any']", compact)

    def test_decide_remainder_door_uses_true_remainder_and_work_act_now(self):
        self.assertIn("DECIDE_WORK_HREF='/work?attention=decide'", _SRC.replace(' ', ''))
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        compact = fn.replace(' ', '')
        self.assertIn("remainder=decide.length-decideVisible.length", compact)
        self.assertIn("'+'+remainder+'moreonWork'", compact)
        self.assertIn('DECIDE_WORK_HREF', fn)
        self.assertIn("emptyText:'Nothing for You'", fn)
        self.assertIn('decideMore.hidden=true', compact)
        self.assertNotIn('muted[muteKey', fn)

    def test_remainder_door_host_sits_after_decide_rows(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        decide_pos = overview.index('id="for-you-decide"')
        more_pos = overview.index('id="overview-decide-more"')
        self.assertLess(decide_pos, more_pos)
        self.assertNotIn('Needs you', overview)
        self.assertNotIn('id="needs-you"', _HTML)

    def test_decide_row_is_title_project_and_face_badge(self):
        fn = _SRC.split('function overviewDecideRow(order)')[1].split('function overviewFaceChip')[0]
        compact = fn.replace(' ', '')
        self.assertIn("[order.title,order.project_name]", compact)
        self.assertIn("join(' · ')", fn)
        self.assertIn("badge('attention','Needsyou')", compact)

    def test_ten_pages_stay_and_across_your_projects_stays_gone(self):
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('Across your projects', _HTML)
        self.assertNotIn('id="project-summary"', _HTML)

    def test_remainder_door_reuses_existing_type_tokens(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-overview-decide-more', css)
        self.assertIn('font-variant-numeric: tabular-nums', css.split('.bp-overview-decide-more')[1].split('}')[0])


class OverviewNowPaintTests(unittest.TestCase):
    """pc-1541 / CAP_ACQUAINTANCE_052 C3: overnight paint parity on Now.
    Option D membership stays: ≤5 Decide rows, +N remainder door, Read /
    Watch / Due chips. Paint only — no membership reopen."""

    def test_due_and_decide_chips_carry_face_tokens(self):
        chip = _SRC.split('function overviewFaceChip(')[1].split('function faceHost')[0]
        compact = chip.replace(' ', '')
        self.assertIn('chip.dataset.face=face', compact)
        fn = _SRC.split('function overview()')[1].split('function remainderLabel')[0]
        compact = fn.replace(' ', '')
        self.assertIn("overviewFaceChip(label,doors.due_count,doors.due_href||'/calendar',face)", compact)
        self.assertIn("'/work?attention='+face,face)", compact)
        self.assertIn("door.dataset.face='decide'", compact)
        self.assertIn("'bp-filter-chip bp-face-chip'", fn)

    def test_now_hides_tall_mute_and_more_bodies(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        hide = css.split('#overview-view .bp-face-entry')[1].split('#overview-view .bp-face-chip')[0]
        self.assertIn('.bp-face-mute', hide)
        self.assertIn('.bp-order-detail', hide)
        self.assertIn('display: none !important', hide)
        overview_fn = _SRC.split('function overview()')[1].split('function remainderLabel')[0]
        self.assertNotIn('Mute 24h', overview_fn)
        self.assertNotIn("el('summary','More')", overview_fn)
        self.assertNotIn('faceEntry', overview_fn)

    def test_decide_rows_stay_one_line_on_narrow(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        compact = css.replace(' ', '')
        self.assertIn('.bp-overview-decide{padding:5px0;align-items:center;gap:8px;grid-template-columns:minmax(0,1fr)auto;}', compact)
        narrow = css.split('@media(max-width:560px)')[1]
        self.assertIn('#overview-view .bp-overview-decide { grid-template-columns: minmax(0,1fr) auto', narrow)
        self.assertIn('#overview-view .bp-overview-decide .bp-badge { justify-self: end; }', narrow)

    def test_due_chip_uses_quiet_gold_not_alarm_red(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        due = css.split('.bp-face-chip[data-face="due"]')[1].split('}')[0]
        self.assertIn('var(--ov-state-scanning)', due)
        self.assertIn('var(--ov-badge-lit-border)', due)
        self.assertNotIn('var(--ov-state-error)', due)
        decide = css.split('.bp-face-chip[data-face="decide"]')[1].split('}')[0]
        self.assertIn('var(--ov-focus)', decide)
        self.assertIn('OVERVIEW_DECIDE_LIMIT = 5', _SRC)
        self.assertIn("'+'+remainder+' more on Work'", _SRC)
        self.assertIn('id="overview-decide-more"', _HTML)
        self.assertIn('id="overview-face-chips"', _HTML)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)


class OverviewNowParityTests(unittest.TestCase):
    """pc-1549 / Visual-finish MUST #1: Now matches end-01 look-fors.
    Option D membership stays — paint + stack only."""

    def test_now_stack_is_kpis_chips_compact_exec_then_decide(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        metrics_pos = overview.index('id="metrics"')
        chips_pos = overview.index('id="overview-face-chips"')
        exec_pos = overview.index('id="overview-executions"')
        decide_pos = overview.index('id="for-you-decide"')
        more_pos = overview.index('id="overview-decide-more"')
        self.assertLess(metrics_pos, chips_pos)
        self.assertLess(chips_pos, exec_pos)
        self.assertLess(exec_pos, decide_pos)
        self.assertLess(decide_pos, more_pos)
        self.assertIn('id="overview-due-fed"', overview)
        self.assertIn('Due fed by Calendar', overview)
        self.assertIn('href="/agents"', overview)
        self.assertIn('All agents', overview)
        self.assertNotIn('Mute 24h', overview)
        self.assertNotIn('View all', overview)
        self.assertNotIn('Inspect seat', overview)
        self.assertNotIn('Seats with an open WorkForce shift', overview)

    def test_current_execution_is_a_count_door_not_seat_rows(self):
        fn = _SRC.split('function overview()')[1].split('function remainderLabel')[0]
        compact = fn.replace(' ', '')
        summary = _SRC.split('function overviewExecutionSummary(item)')[1].split('function overviewSourceLine')[0].replace(' ', '')
        self.assertIn('function overviewExecutionSummary(item)', _SRC)
        self.assertIn("n===1?'1seatonshift':n+'seatsonshift'", summary)
        self.assertIn("running.length?[{id:'shift',n:running.length}]:[]", compact)
        self.assertNotIn('Inspect seat', fn)
        self.assertNotIn('Open order', fn)
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-overview-exec', css)
        hide = css.split('#overview-view .bp-face-entry')[1].split('#overview-view .bp-face-chip')[0]
        self.assertIn('.bp-execution-row', hide)
        self.assertIn('.bp-execution-actions', hide)

    def test_for_you_panel_chrome_is_gone(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertIn('class="bp-overview-act"', overview)
        self.assertIn('id="for-you-decide-heading">Act now<', overview)
        self.assertNotIn('<h2>For You</h2>', overview)
        self.assertNotIn('Act-now decisions here', overview)
        self.assertNotIn('class="bp-panel', overview)


class CalendarDoorsTests(unittest.TestCase):
    """pc-1512: thin Calendar doors on Overview and Agents only."""

    def test_due_chip_reads_calendar_doors_not_attention_face(self):
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertIn('calendarDoorsFromSnapshot()', fn)
        self.assertIn('doors.due_count', fn.replace(' ', ''))
        self.assertIn("if(face==='due')", fn.replace(' ', ''))

    def test_agents_paints_next_fire_one_liner_to_calendar(self):
        self.assertIn('id="agents-next-fire"', _HTML)
        self.assertIn('function paintAgentsNextFire()', _SRC)
        self.assertIn('function nextScheduleFire(', _SRC)
        agents = _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0]
        self.assertIn('paintAgentsNextFire()', agents)
        self.assertIn("link(doors.next_fire_line", _SRC.replace(' ', ''))
        self.assertIn("'/calendar'", _SRC.split('function paintAgentsNextFire()')[1].split('function scheduleDoorRow')[0])

    def test_work_calendar_doors_are_not_a_second_calendar(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertIn('id="work-calendar-doors"', work)
        self.assertNotIn('id="work-calendar-today"', _HTML)
        self.assertNotIn('week-grid', _HTML)
        self.assertNotIn('isometric', _SRC)
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        self.assertNotIn('wo-tile', calendar)

    def test_ten_pages_unchanged(self):
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)


class AgentsLiveFloorTests(unittest.TestCase):
    """pc-1513: live floor pulse on Agents, not a dead Off wall."""

    def test_pulse_strip_and_quiet_disclosure_are_on_agents_only(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="agents-pulse"', agents)
        self.assertIn('id="agents-quiet"', agents)
        self.assertIn('id="agents-quiet-list"', agents)
        self.assertIn('id="agents-floor-empty"', agents)
        self.assertIn('id="agents-next-fire"', agents)
        self.assertIn('id="agents-floor-spark"', agents)
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertNotIn('id="agents-pulse"', work)
        self.assertNotIn('id="agents-floor-spark"', work)

    def test_agents_paints_pulse_then_reuses_calendar_next_fire(self):
        agents = _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0]
        self.assertIn('paintAgentsPulse()', agents)
        self.assertIn('paintAgentsFloorSpark()', agents)
        self.assertIn('paintAgentsNextFire()', agents)
        self.assertLess(agents.index('paintAgentsPulse()'), agents.index('paintAgentsFloorSpark()'))
        self.assertLess(agents.index('paintAgentsFloorSpark()'), agents.index('paintAgentsNextFire()'))
        self.assertIn("floorBucket(a)!=='quiet'", agents.replace(' ', ''))
        self.assertIn('Quiet ·', agents)

    def test_pulse_counts_come_from_state_not_roster_length(self):
        fn = _SRC.split('function floorBucket(agent)')[1].split('function buildAgentsFloor')[0]
        self.assertIn("state==='working'", fn.replace(' ', ''))
        self.assertIn("state==='last_run_failed'", fn.replace(' ', ''))
        self.assertIn("state==='idle'", fn.replace(' ', ''))
        self.assertIn("return 'quiet'", fn)
        self.assertNotIn('agents.length', _SRC.split('function buildAgentsFloor')[1].split('function agentsFloorFromSnapshot')[0])

    def test_off_is_not_painted_as_idle_and_failed_stays_error(self):
        self.assertIn("['Error',floor.error,'last_run_failed']", _SRC.replace(' ', ''))
        self.assertIn("['Idle',floor.idle,'idle']", _SRC.replace(' ', ''))
        remainder = _SRC.split('function paintAgentsPulse()')[1].split('function paintAgentsNextFire()')[0]
        self.assertIn('stale shift', remainder)
        self.assertIn('off or unknown', remainder)
        self.assertIn('No seats working right now.', remainder)

    def test_working_rows_keep_claim_and_live_cue(self):
        row = _SRC.split('function agentRow(agent)')[1].split('function jobRow(agent)')[0]
        self.assertIn('heldLink(agent)', row)
        self.assertIn('bp-shift-cue', row)
        self.assertIn("agent.state==='working'", row.replace(' ', ''))
        self.assertIn('agentRowClass(agent)', row)

    def test_ten_pages_and_no_invented_nav(self):
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('EXECUTIONS', _HTML)
        self.assertIn('n8n-style factory', _SRC.lower())
        self.assertNotIn('n8n editor', _SRC.lower())
        # Activity histogram is native on Timeline only (representation brief §6).
        overview = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        work = _SRC.split('function work()')[1].split('function agentAction')[0]
        agents = _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0]
        self.assertNotIn('paintTimelineActivity', overview)
        self.assertNotIn('paintTimelineActivity', work)
        self.assertNotIn('paintTimelineActivity', agents)
        self.assertNotIn('histogram', overview.lower())
        self.assertNotIn('histogram', work.lower())
        self.assertNotIn('histogram', agents.lower())

    def test_live_floor_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping agents floor harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'agents_floor_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'agents floor harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertEqual(result['pulse'], ['1Working', '2Idle', '1Error'])
        self.assertEqual(result['live_seats'], ['working-seat'])
        self.assertEqual(result['quiet_seats'], ['off-seat'])
        self.assertTrue(result['working_has_claim'])
        self.assertTrue(result['working_has_cue'])
        self.assertEqual(result['empty_when_quiet'], 'No seats working right now.')
        self.assertIn('Next fire ·', result['next_fire'])
        self.assertEqual(result['working_spark'], '2 runs')
        self.assertEqual(result['failed_spark'], '1 run · 1 fail (100%)')
        self.assertEqual(result['idle_spark'], '')
        self.assertEqual(result['quiet_spark'], '')
        self.assertIn('4 runs · last 24h', result['floor_spark'])
        self.assertIn('1 fail (25%)', result['floor_spark'])
        self.assertEqual(result['floor_spark_when_quiet'], '')
        self.assertEqual(result['dispatch_secondary'], 'Dispatch now')
        self.assertFalse(result['coverage_door_open'])
        self.assertEqual(result['coverage_door'], 'Coverage · 1 project')
        self.assertFalse(result['coverage_door_bulletin'])
        self.assertEqual(result['coverage_door_empty'], 'Coverage · none reported')


class AgentsFloorSparkPaintTests(unittest.TestCase):
    """Issue #140: seat throughput / fail-rate sparks. Pulse chrome stays."""

    def test_spark_host_sits_under_pulse_not_inside_the_tiles(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="agents-floor-spark"', agents)
        self.assertLess(agents.index('id="agents-pulse"'), agents.index('id="agents-floor-spark"'))
        self.assertLess(agents.index('id="agents-floor-spark"'), agents.index('id="agents-next-fire"'))
        self.assertEqual(_HTML.count('id="agents-floor-spark"'), 1)
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertNotIn('id="agents-floor-spark"', overview)
        self.assertIn('id="overview-throughput"', overview)

    def test_rows_paint_spark_without_redoing_claim_or_pulse(self):
        row = _SRC.split('function agentRow(agent)')[1].split('function jobRow(agent)')[0]
        self.assertIn('seatSparkCell(agent)', row)
        self.assertIn('heldLink(agent)', row)
        self.assertIn('bp-shift-cue', row)
        pulse = _SRC.split('function paintAgentsPulse()')[1].split('function paintAgentsNextFire()')[0]
        self.assertIn("['Working',floor.working,'working']", pulse.replace(' ', ''))
        self.assertIn("['Idle',floor.idle,'idle']", pulse.replace(' ', ''))
        self.assertIn("['Error',floor.error,'last_run_failed']", pulse.replace(' ', ''))
        self.assertNotIn('seatSparkCell', pulse)

    def test_quiet_and_empty_stay_honest_and_timeline_keeps_the_histogram(self):
        spark = _SRC.split('function seatSparkCell(agent)')[1].split('function floorThroughputFromSnapshot()')[0]
        self.assertIn("bucket==='quiet'", spark.replace(' ', ''))
        self.assertIn('Runs unavailable', spark)
        self.assertIn('failBits(', spark)
        self.assertIn('bp-agent-spark-fail', spark)
        floor = _SRC.split('function paintAgentsFloorSpark()')[1].split('function paintAgentsPulse()')[0]
        self.assertIn('No seat runs in the last 24h', floor)
        self.assertIn("floorBucket(agent)!=='quiet'", floor.replace(' ', ''))
        self.assertIn('/timeline?period=1', floor)
        self.assertIn('bp-agents-floor-fail', floor)
        self.assertIn('failBits(', floor)
        self.assertNotIn('n8n', floor.lower())
        self.assertNotIn('histogram', floor.lower())
        self.assertIn('function paintTimelineActivity(', _SRC)
        self.assertIn('id="timeline-activity-chart"', _HTML)

    def test_fail_rate_is_glanceable_and_mixed_fail_does_not_paint_the_strip_error(self):
        self.assertIn('function failRateText(', _SRC)
        self.assertIn('function failBits(', _SRC)
        self.assertIn('function sparkTone(', _SRC)
        self.assertIn('function floorThroughputFromSnapshot()', _SRC)
        tone = _SRC.split('function sparkTone(data, fallback)')[1].split('function seatSparkLabel')[0]
        self.assertIn('data.errors>=data.runs', tone.replace(' ', ''))
        bits = _SRC.split('function failBits(errors, rate)')[1].split('function sparkTone')[0]
        self.assertIn('1 fail', bits)
        self.assertIn('failRateText(rate)', bits)
        pulse = _SRC.split('function paintAgentsPulse()')[1].split('function paintAgentsNextFire()')[0]
        self.assertIn("['Working',floor.working,'working']", pulse.replace(' ', ''))
        self.assertIn("['Idle',floor.idle,'idle']", pulse.replace(' ', ''))
        self.assertIn("['Error',floor.error,'last_run_failed']", pulse.replace(' ', ''))
        work = _SRC.split('function paintWorkFlow()')[1].split('function isUnrouted')[0]
        self.assertIn('bp-work-seat-chip', work)
        self.assertIn('bp-work-flow-strip', work)
        self.assertNotIn('failRateText', work)
        self.assertNotIn('agents_floor', work)

    def test_spark_css_does_not_add_a_fourth_pulse_tile(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-agents-floor-spark', css)
        self.assertIn('.bp-agent-spark-line', css)
        self.assertIn('.bp-agents-floor-fail', css)
        self.assertIn('.bp-agent-spark-fail', css)
        self.assertIn('grid-template-columns: repeat(3, minmax(0, 1fr))', css)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('EXECUTIONS', _HTML)


class OverviewThroughputTests(unittest.TestCase):
    """Issue #141: quiet last-24h closes spark under KPIs. Door, not a
    sixth tile or an n8n canvas. Honesty / Work / Calendar / Agents stay."""

    def test_spark_host_sits_under_kpis_not_inside_the_tile_row(self):
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        metrics_pos = overview.index('id="metrics"')
        spark_pos = overview.index('id="overview-throughput"')
        unrouted_pos = overview.index('id="overview-unrouted"')
        decide_pos = overview.index('id="for-you-decide"')
        self.assertLess(metrics_pos, spark_pos)
        self.assertLess(spark_pos, unrouted_pos)
        self.assertLess(unrouted_pos, decide_pos)
        self.assertEqual(_HTML.count('id="overview-throughput"'), 1)
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertNotIn('id="overview-throughput"', work)

    def test_paint_uses_snapshot_ticks_and_honest_empty(self):
        self.assertIn('function paintOverviewThroughput()', _SRC)
        self.assertIn('function throughputSpark(', _SRC)
        fn = _SRC.split('function overview()')[1].split('function renderWorkInbox')[0]
        self.assertIn('paintOverviewThroughput()', fn)
        paint = _SRC.split('function paintOverviewThroughput()')[1].split('function isUnrouted')[0]
        self.assertIn('No closes in the last 24h', paint)
        self.assertIn('Throughput unavailable', paint)
        self.assertIn('closes · last 24h', paint)
        self.assertIn('THROUGHPUT_HREF', paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('histogram', paint.lower())

    def test_spark_is_not_a_sixth_kpi_and_keeps_option_d(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-overview-throughput', css)
        self.assertIn('.bp-overview-spark', css)
        self.assertIn('grid-template-columns: repeat(5,minmax(0,1fr))', css)
        self.assertIn('OVERVIEW_DECIDE_LIMIT = 5', _SRC)
        self.assertIn("'+'+remainder+' more on Work'", _SRC)
        self.assertIn('id="work-band-act-now"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('function calendarDoorsFromSnapshot', _SRC)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())


class WorkDensityTests(unittest.TestCase):
    """pc-1510: live board — three bands, dual badges, orthogonal facets."""

    def test_work_rows_use_dual_face_and_status_badges(self):
        fn = _SRC.split('function orderBadges(order)')[1].split('function workBoardRow')[0]
        compact = fn.replace(' ', '')
        self.assertIn("dataset.kind='face'", compact)
        self.assertIn("dataset.kind='status'", compact)
        self.assertNotIn('Needs you', fn)
        self.assertNotIn("'attention'", fn)

    def test_comfortable_cap_is_eight_plus_remainder(self):
        self.assertIn('WORK_BAND_LIMIT=8', _SRC.replace(' ', ''))
        self.assertIn("'+'+remainder", _SRC)
        self.assertIn('more in Act now', _SRC)
        self.assertIn('more · My todos', _SRC)
        self.assertIn('more · filter by seat', _SRC)
        self.assertIn('function renderComfortBand', _SRC)
        self.assertIn('function renderSeatBacklog', _SRC)
        self.assertIn('bp-work-seat-virt', _HTML)
        self.assertIn('SEAT_PREVIEW_SEATS=3', _SRC.replace(' ', ''))
        self.assertIn('SEAT_PREVIEW_PER_SEAT=3', _SRC.replace(' ', ''))
        self.assertNotIn('SEAT_WINDOW=40', _SRC.replace(' ', ''))

    def test_honest_empty_copy_is_per_band(self):
        self.assertIn("'Nothing for You'", _SRC)
        self.assertIn("'Your list is clear'", _SRC)
        self.assertIn("'No seat backlog'", _SRC)

    def test_legacy_work_links_still_resolve(self):
        self.assertIn("statusLegacy[statusParam]", _SRC)
        self.assertIn("attentionParam === 'note'", _SRC)
        self.assertIn("DECIDE_WORK_HREF='/work?attention=decide'", _SRC.replace(' ', ''))

    def test_work_css_stays_on_dark_pc_tokens(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-work-seat-virt', css)
        self.assertIn('.bp-order-badges', css)
        self.assertNotIn('#fff', css.split('.bp-work-seat-virt')[1].split('}')[0])


class WorkFlowStripTests(unittest.TestCase):
    """Issue #160 / #166: Work hero paint — colored flow + chips above facets."""

    def test_strip_host_sits_on_work_above_the_bands_only(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        self.assertIn('id="work-flow"', work)
        self.assertLess(work.index('id="work-flow"'), work.index('id="filters"'))
        self.assertLess(work.index('id="filters"'), work.index('id="work-band-act-now"'))
        self.assertLess(work.index('id="work-band-act-now"'), work.index('id="work-band-my-todos"'))
        self.assertLess(work.index('id="work-band-my-todos"'), work.index('id="work-band-seat-backlog"'))
        self.assertEqual(_HTML.count('id="work-flow"'), 1)
        self.assertNotIn('id="work-flow"', overview)
        self.assertNotIn('id="work-flow"', _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0])
        self.assertNotIn('id="work-flow"', _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0])
        self.assertNotIn('id="work-flow"', _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0])

    def test_paint_uses_ready_stalled_chips_and_flow_companion(self):
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn('function buildWorkFlow(', _SRC)
        work_fn = _SRC.split('function work()')[1].split('function agentAction')[0]
        self.assertIn('paintWorkFlow()', work_fn)
        self.assertIn('matchingWorkOrders()', work_fn)
        paint = _SRC.split('function paintWorkFlow()')[1].split('function isUnrouted')[0]
        self.assertIn('Seat load unavailable', paint)
        self.assertIn('No seat drain right now', paint)
        self.assertIn('bp-work-seat-chip', paint)
        self.assertIn(' ready', paint)
        self.assertIn(' stalled', paint)
        self.assertIn('scopeSeatLoad', paint)
        self.assertIn('bp-work-flow-strip', paint)
        self.assertIn('bp-work-flow-ticks', paint)
        self.assertIn('bp-work-flow-label', paint)
        self.assertIn('bp-work-flow-count', paint)
        self.assertIn('FLOW_STAGES', paint)
        self.assertIn('data.flow', paint)
        self.assertNotIn('bp-work-flow-bar', paint)
        self.assertNotIn('flow-pipeline', paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('histogram', paint.lower())
        self.assertNotIn('Needs you', paint)

    def test_work_view_keeps_seat_load_and_paints_flow_counts(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertIn('function flowStage', _SRC)
        self.assertIn("const FLOW_STAGES = ['Open','Ready','Live','Done']", _SRC)
        self.assertNotIn('bp-work-flow-pipeline', _SRC)
        self.assertNotIn('bp-work-flow-bar', _SRC)
        self.assertIn('aria-label="Seat load"', work)
        self.assertIn('bp-work-seat-chip', _SRC)
        paint = _SRC.split('function paintWorkFlow()')[1].split('function isUnrouted')[0]
        self.assertIn("aria-label','Flow'", paint.replace(' ', ''))
        self.assertNotIn('Held', paint)

    def test_strip_does_not_retouch_density_or_neighbor_doors(self):
        self.assertIn("dataset.kind='face'", _SRC)
        self.assertIn("dataset.kind='status'", _SRC)
        self.assertIn('function matchesStatusFacet', _SRC)
        self.assertIn('function matchesAttentionFacet', _SRC)
        self.assertIn('id="work-band-act-now"', _HTML)
        self.assertIn('id="work-calendar-doors"', _HTML)
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="timeline-activity"', _HTML)
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-work-flow', css)
        self.assertIn('.bp-work-seat-load', css)
        self.assertIn('.bp-work-flow-strip', css)
        self.assertNotIn('#fff', css.split('.bp-work-flow')[1].split('.bp-badge')[0])
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('point of sale', _HTML.lower())


class WorkVisualFinishTests(unittest.TestCase):
    """Issue #166: paint-only Work hero — dots, chip cards, order, band scarcity."""

    def test_hero_sits_above_the_filter_mast(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertLess(work.index('id="work-flow"'), work.index('id="filters"'))
        self.assertLess(work.index('id="filters"'), work.index('id="work-band-act-now"'))
        self.assertIn('bp-work-facets', work)
        self.assertIn('bp-work-facet-status', work)

    def test_css_paints_stage_dots_chip_cards_and_band_weight(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        work = css[css.index('#work-view {'):css.index('.bp-work-row {')]
        self.assertIn('.bp-work-flow-stage::before', work)
        self.assertIn('[data-stage="Open"]', work)
        self.assertIn('[data-stage="Ready"]', work)
        self.assertIn('[data-stage="Live"]', work)
        self.assertIn('[data-stage="Done"]', work)
        self.assertIn('.bp-work-flow-ticks', work)
        self.assertIn('.bp-work-flow-tick', work)
        self.assertIn('border-radius: 8px', work)
        self.assertIn('.bp-work-seat-chip-ready { color: var(--ov-link);', work)
        self.assertIn('.bp-work-seat-chip-stalled { color: var(--ov-state-error);', work)
        self.assertIn('font-weight: 600', work)
        self.assertIn('.bp-work-band-act-now', work)
        self.assertIn('var(--ov-state-scanning)', work)
        self.assertIn('.bp-work-band-my-todos', work)
        self.assertIn('.bp-work-band-seat-backlog', work)
        self.assertIn('#work-view .bp-work-facets', work)
        self.assertNotIn('#fff', work)
        self.assertNotIn('bp-work-flow-bar', work)
        self.assertNotIn('n8n', work.lower())

    def test_paint_does_not_reopen_caps_or_membership(self):
        self.assertIn('WORK_BAND_LIMIT=8', _SRC.replace(' ', ''))
        self.assertIn('SEAT_PREVIEW_SEATS=3', _SRC.replace(' ', ''))
        self.assertIn('SEAT_PREVIEW_PER_SEAT=3', _SRC.replace(' ', ''))
        self.assertNotIn('SEAT_WINDOW=40', _SRC.replace(' ', ''))
        self.assertNotIn('bp-work-flow-pipeline', _SRC)
        self.assertNotIn('bp-work-flow-bar', _SRC)


class WorkScarcityMockCloseTests(unittest.TestCase):
    """pc-1558 residual mock-close: hero scarcity wins vs filter wall / ticket wall."""

    def test_title_hero_filter_door_then_bands(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertLess(work.index('id="work-flow"'), work.index('id="filters"'))
        self.assertLess(work.index('id="search"'), work.index('id="work-facet-door"'))
        self.assertLess(work.index('id="work-facet-door"'), work.index('id="project-filter"'))
        self.assertLess(work.index('id="filters"'), work.index('id="work-band-act-now"'))
        self.assertLess(work.index('id="work-band-act-now"'), work.index('id="work-band-my-todos"'))
        self.assertLess(work.index('id="work-band-my-todos"'), work.index('id="work-band-seat-backlog"'))
        self.assertIn('bp-work-facet-door', work)
        self.assertIn('id="work-facet-door-summary"', work)
        self.assertNotIn('<details class="bp-work-facet-door" id="work-facet-door" open', work)
        self.assertIn('document.body.dataset.page = page', _SRC)
        self.assertIn('function syncWorkFacetDoor()', _SRC)
        work_fn = _SRC.split('function work()')[1].split('function agentAction')[0]
        self.assertIn('renderActiveFilters()', work_fn)
        door = _SRC.split('function syncWorkFacetDoor()')[1].split('function renderActiveFilters')[0]
        self.assertIn("'Filters · '", door)
        self.assertIn("door.open=true", door.replace(' ', ''))

    def test_css_elevates_hero_and_scarcity_over_filter_wall(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('pc-1558', css)
        work = css[css.index('#work-view {'):css.index('.bp-work-row {')]
        self.assertIn('font-size: 28px', work)
        self.assertIn('grid-template-areas: "dot label" "count count" "ticks ticks"', work)
        self.assertIn('.bp-work-facet-door', work)
        self.assertIn('#work-view .bp-work-band .bp-section-head .bp-muted { display: none; }', work)
        self.assertIn('border-left: 4px solid var(--ov-state-scanning)', work)
        self.assertIn('.bp-work-band-my-todos', work)
        self.assertIn('background: transparent', work)
        self.assertIn('.bp-work-band-seat-backlog', work)
        self.assertIn('.bp-operations[data-page="work"] #page-description { display: none; }', work)
        self.assertIn('.bp-work-seat-chip-ready { color: var(--ov-link);', work)
        self.assertIn('.bp-work-seat-chip-stalled { color: var(--ov-state-error);', work)
        self.assertNotIn('#fff', work)
        self.assertNotIn('bp-work-flow-bar', work)
        self.assertNotIn('n8n', work.lower())
        self.assertIn('#work-view .bp-work-row { grid-template-columns: auto minmax(0,1fr) auto', css)

    def test_caps_membership_and_neighbors_stay_frozen(self):
        self.assertIn('WORK_BAND_LIMIT=8', _SRC.replace(' ', ''))
        self.assertIn('SEAT_PREVIEW_SEATS=3', _SRC.replace(' ', ''))
        self.assertIn('SEAT_PREVIEW_PER_SEAT=3', _SRC.replace(' ', ''))
        self.assertNotIn('SEAT_WINDOW=40', _SRC.replace(' ', ''))
        self.assertNotIn('bp-work-flow-pipeline', _SRC)
        self.assertNotIn('bp-work-flow-bar', _SRC)
        self.assertIn('id="agents-hero"', _HTML)
        self.assertIn('id="timeline-hero"', _HTML)
        self.assertIn('id="calendar-hero"', _HTML)
        self.assertIn('id="delivery-hero"', _HTML)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('point of sale', _HTML.lower())


class WorkRepresentationV2Tests(unittest.TestCase):
    """Issue #158 / #160: seat-load chips + thin flow companion, hard caps, +N doors."""

    def test_work_html_keeps_one_hero_host_above_the_bands(self):
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertIn('aria-label="Seat load"', work)
        self.assertNotIn('Seat load and flow', work)
        self.assertNotIn('id="mute-status"', work)
        self.assertIn('bp-work-band-act-now', work)

    def test_desk_like_counts_cap_and_doors(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping work v2 harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'work_v2_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=20, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'work v2 harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertEqual(result['act_now_total'], '9')
        self.assertEqual(result['act_now_visible_default'], 8)
        self.assertEqual(result['act_now_more'], '+1 more in Act now')
        self.assertEqual(result['my_todos_total'], '31')
        self.assertEqual(result['my_todos_visible_default'], 8)
        self.assertEqual(result['my_todos_more'], '+23 more · My todos')
        self.assertEqual(result['seat_total'], '78')
        self.assertEqual(result['seat_visible_default'], 9)
        self.assertEqual(result['seat_more'], '+69 more · filter by seat')
        self.assertFalse(result['hero_has_flow_bar'])
        self.assertTrue(result['hero_has_flow_strip'])
        self.assertIn('Open', result['hero_flow'])
        self.assertIn('Ready', result['hero_flow'])
        self.assertIn('Live', result['hero_flow'])
        self.assertIn('Done', result['hero_flow'])
        self.assertIn('pepper', result['hero_chips'])
        self.assertEqual(result['mute_on_rows'], 0)
        self.assertEqual(result['more_on_rows'], 0)
        self.assertEqual(result['door_sets_attention'], 'act_now')
        self.assertEqual(result['chip_sets_seat'], 'worker:pepper')


class ProjectsPortfolioSparkTests(unittest.TestCase):
    """Issue #150: per-card open/For You sparks and workspace compare bars."""

    def test_hosts_live_on_projects_view_only(self):
        projects = _HTML.split('id="projects-view"')[1].split('id="agents-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="projects-compare"', projects)
        self.assertIn('id="projects-compare-summary"', projects)
        self.assertLess(projects.index('id="projects-summary"'), projects.index('id="projects-compare"'))
        self.assertLess(projects.index('id="projects-compare"'), projects.index('id="projects-list"'))
        self.assertEqual(_HTML.count('id="projects-compare"'), 1)
        self.assertNotIn('id="projects-compare"', work)
        self.assertNotIn('id="projects-compare"', overview)
        self.assertNotIn('id="projects-compare"', agents)

    def test_paint_uses_stacked_open_for_you_and_work_map_doors(self):
        self.assertIn('function paintProjectsCompare()', _SRC)
        self.assertIn('function projectSparkCell(', _SRC)
        self.assertIn('function stackedOpenBar(', _SRC)
        fn = _SRC.split('function projects()')[1].split('function overviewDecideRow')[0]
        self.assertIn('paintProjectsCompare()', fn)
        paint = _SRC.split('function paintProjectsCompare()')[1].split('function projectComparisonRow')[0]
        self.assertIn("row.pulse!=='quiet'", paint.replace(' ', ''))
        self.assertIn('pulseRank', paint)
        self.assertIn('For You', paint)
        self.assertIn('Map', paint)
        self.assertIn('/work?project=', paint)
        self.assertNotIn('/delivery', paint)
        self.assertNotIn("link('Agents'", paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('histogram', paint.lower())
        row = _SRC.split('function projectComparisonRow(project)')[1].split('function projectIsQuiet')[0]
        self.assertIn('projectSparkCell(project)', row)

    def test_does_not_regress_other_map_a_surfaces(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-projects-compare', css)
        self.assertIn('.bp-projects-stack', css)
        self.assertIn('.bp-projects-spark', css)
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="agents-floor-spark"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertIn('id="work-band-act-now"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="work-calendar-doors"', _HTML)
        self.assertIn('function paintOverviewThroughput()', _SRC)
        self.assertIn('function paintAgentsFloorSpark()', _SRC)
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn('function paintTimelineActivity()', _SRC)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)


class DeliveryCiSparkTests(unittest.TestCase):
    """Issue #152: CI pass/fail spark (optional merge cadence) on Delivery."""

    def test_spark_host_sits_on_delivery_under_status_only(self):
        delivery = _HTML.split('id="delivery-view"')[1].split('id="timeline-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        projects = _HTML.split('id="projects-view"')[1].split('id="agents-view"')[0]
        timeline = _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0]
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        hero = delivery.split('id="delivery-hero"')[1].split('id="delivery-filters"')[0]
        self.assertIn('id="delivery-ci-spark"', delivery)
        self.assertIn('id="delivery-ci-spark"', hero)
        self.assertLess(delivery.index('id="delivery-hero-chips"'), delivery.index('id="delivery-ci-spark"'))
        self.assertLess(delivery.index('id="delivery-ci-spark"'), delivery.index('id="remote-status"'))
        self.assertLess(delivery.index('id="delivery-ci-spark"'), delivery.index('id="delivery-filters"'))
        self.assertLess(delivery.index('id="delivery-ci-spark"'), delivery.index('id="remote-repositories"'))
        self.assertEqual(_HTML.count('id="delivery-ci-spark"'), 1)
        self.assertNotIn('id="delivery-ci-spark"', overview)
        self.assertNotIn('id="delivery-ci-spark"', work)
        self.assertNotIn('id="delivery-ci-spark"', agents)
        self.assertNotIn('id="delivery-ci-spark"', projects)
        self.assertNotIn('id="delivery-ci-spark"', timeline)
        self.assertNotIn('id="delivery-ci-spark"', calendar)

    def test_paint_uses_pass_fail_and_repo_pr_doors(self):
        self.assertIn('function paintDeliverySpark(', _SRC)
        self.assertIn('function deliverySparkFromRemote(', _SRC)
        paint = _SRC.split('function paintDeliverySpark(')[1].split('function paintDelivery(')[0]
        self.assertIn('CI not configured', paint)
        self.assertIn('CI unavailable', paint)
        self.assertIn('No CI runs in the ', paint)
        self.assertIn('checks · ', paint)
        self.assertIn('deliverySparkHref(\'workflow\')', paint.replace(' ', ''))
        self.assertIn('deliverySparkHref(\'pull_request\')', paint.replace(' ', ''))
        self.assertIn("target='_blank'", paint)
        self.assertIn('Open failing check', paint)
        self.assertIn('Open repository', paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('histogram', paint.lower())
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('seat', paint.lower())
        delivery = _SRC.split('function paintDelivery(')[1].split('function remoteStatusText')[0]
        self.assertIn('paintDeliverySpark(data)', delivery)

    def test_does_not_regress_other_map_a_surfaces(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-delivery-ci-spark', css)
        self.assertIn('.bp-delivery-ci-spark-line', css)
        self.assertIn('.bp-delivery-ci-spark-bars', css)
        self.assertIn('.bp-delivery-ci-spark-bar', css)
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="agents-floor-spark"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="projects-compare"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertIn('id="work-band-act-now"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="work-calendar-doors"', _HTML)
        self.assertIn('id="calendar-load"', _HTML)
        self.assertIn('function paintOverviewThroughput()', _SRC)
        self.assertIn('function paintAgentsFloorSpark()', _SRC)
        self.assertIn('function paintProjectsCompare()', _SRC)
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn('function paintTimelineActivity()', _SRC)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)

    def test_delivery_spark_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping delivery spark harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'delivery_spark_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'delivery spark harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertIn('8 checks · last 14 days', result['healthy'])
        self.assertIn('2 fails', result['healthy'])
        self.assertIn('3 merges', result['healthy'])
        self.assertEqual(result['healthy_href'], '/delivery?type=workflow')
        self.assertEqual(result['merge_href'], '/delivery?type=pull_request')
        self.assertEqual(result['out_href'], 'https://github.com/org/repo/actions/runs/9')
        self.assertEqual(result['out_label'], 'Open failing check')
        self.assertTrue(result['has_glyphs'])
        self.assertTrue(result['has_bars'])
        self.assertEqual(result['empty'], 'No CI runs in the last 14 days')
        self.assertEqual(result['unavailable'], 'CI unavailable')
        self.assertEqual(result['not_configured'], 'CI not configured')
        self.assertIn('No CI runs in the last 14 days', result['merges_only'])
        self.assertIn('1 merge', result['merges_only'])


class DeliveryHeroTests(unittest.TestCase):
    """pc-1542 / CAP_ACQUAINTANCE_052 C4: PR · CI · Remote is the Delivery
    hero (git ledger). Optional CI spark stays. Not WorkLane triage."""

    def test_hero_sits_on_delivery_above_status_spark_and_filters(self):
        delivery = _HTML.split('id="delivery-view"')[1].split('id="timeline-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        projects = _HTML.split('id="projects-view"')[1].split('id="agents-view"')[0]
        timeline = _HTML.split('id="timeline-view"')[1].split('id="connections-view"')[0]
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        self.assertIn('id="delivery-hero"', delivery)
        self.assertIn('id="delivery-hero-chips"', delivery)
        self.assertIn('id="delivery-ci-spark"', delivery)
        self.assertIn('Delivery git evidence', delivery)
        self.assertIn('bp-delivery-facets', delivery)
        self.assertIn('bp-delivery-ledger', delivery)
        hero = delivery.split('id="delivery-hero"')[1].split('id="delivery-filters"')[0]
        self.assertIn('id="delivery-ci-spark"', hero)
        self.assertIn('id="remote-status"', hero)
        self.assertLess(delivery.index('id="delivery-hero"'), delivery.index('id="remote-status"'))
        self.assertLess(delivery.index('id="delivery-hero-chips"'), delivery.index('id="delivery-ci-spark"'))
        self.assertLess(delivery.index('id="delivery-ci-spark"'), delivery.index('id="remote-status"'))
        self.assertLess(delivery.index('id="delivery-ci-spark"'), delivery.index('id="delivery-filters"'))
        self.assertLess(delivery.index('id="delivery-filters"'), delivery.index('id="remote-repositories"'))
        self.assertEqual(_HTML.count('id="delivery-hero"'), 1)
        self.assertNotIn('id="delivery-hero"', overview)
        self.assertNotIn('id="delivery-hero"', work)
        self.assertNotIn('id="delivery-hero"', agents)
        self.assertNotIn('id="delivery-hero"', projects)
        self.assertNotIn('id="delivery-hero"', timeline)
        self.assertNotIn('id="delivery-hero"', calendar)
        self.assertNotIn('wo-tile', delivery)
        self.assertNotIn('id="work-band-act-now"', delivery)
        self.assertNotIn('id="for-you-decide"', delivery)

    def test_paint_uses_pr_ci_remote_doors_not_worklane_triage(self):
        self.assertIn('function paintDeliveryHero(', _SRC)
        self.assertIn('function deliveryHeroFromRemote(', _SRC)
        self.assertIn('function deliveryHeroBranch(', _SRC)
        self.assertIn('function deliveryRemoteSecondary(', _SRC)
        self.assertIn('function deliverySparkBars(', _SRC)
        chip = _SRC.split('function deliveryHeroChip(')[1].split('function paintDeliveryHero(')[0]
        self.assertIn('node.dataset.kind=kind', chip.replace(' ', ''))
        paint = _SRC.split('function paintDeliveryHero(')[1].split('function paintDeliverySpark(')[0]
        compact = paint.replace(' ', '')
        self.assertIn("deliverySparkHref('pull_request')", compact)
        self.assertIn("deliverySparkHref('workflow')", compact)
        self.assertIn("'/connections'", paint)
        self.assertIn("'PR'", paint)
        self.assertIn("'CI'", paint)
        self.assertIn("'Remote'", paint)
        self.assertIn('not configured', paint)
        self.assertIn('unavailable', paint)
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('Decide', paint)
        self.assertNotIn('For You', paint)
        self.assertNotIn('seat', paint.lower())
        self.assertNotIn('n8n', paint.lower())
        delivery = _SRC.split('function paintDelivery(')[1].split('function remoteStatusText')[0]
        self.assertIn('paintDeliveryHero(data)', delivery)
        self.assertIn('paintDeliverySpark(data)', delivery)
        self.assertLess(delivery.index('paintDeliveryHero'), delivery.index('paintDeliverySpark'))

    def test_hero_weight_beats_filter_mast_and_holds_neighbors(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-delivery-hero', css)
        self.assertIn('.bp-delivery-hero-chip', css)
        self.assertIn('#delivery-view .bp-filters', css)
        hero = css.split('.bp-delivery-hero-chip-primary')[1].split('}')[0]
        self.assertIn('font-size: 20px', hero)
        filters = css.split('#delivery-view .bp-filters input')[1].split('}')[0]
        self.assertIn('min-height: 32px', filters)
        self.assertIn('id="overview-face-chips"', _HTML)
        self.assertIn('id="overview-decide-more"', _HTML)
        self.assertIn('id="agents-canvas"', _HTML)
        self.assertIn('id="calendar-load"', _HTML)
        self.assertIn('id="calendar-doors"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)

    def test_delivery_hero_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping delivery hero harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'delivery_hero_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'delivery hero harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertEqual(result['kinds'], ['pr', 'ci', 'remote'])
        self.assertEqual(result['healthy_pr'], 'PR2 open3 merged')
        self.assertEqual(result['healthy_ci'], 'CI8 checks2 fails')
        self.assertEqual(result['healthy_remote'], 'Remoteconnectedmain')
        self.assertEqual(result['pr_href'], '/delivery?type=pull_request')
        self.assertEqual(result['ci_href'], '/delivery?type=workflow')
        self.assertEqual(result['remote_href'], '/connections')
        self.assertEqual(result['empty_pr'], 'PRnone')
        self.assertEqual(result['unavailable'], ['PRunavailable', 'CIunavailable', 'Remoteunavailable'])
        self.assertEqual(result['not_configured'], ['PRnot configured', 'CInot configured', 'Remotenot configured'])
        self.assertEqual(result['branch'], 'main')
        self.assertEqual(result['empty_remote'], 'Remoteconnected0 remotes')


class DeliveryGitEvidenceVisualFinishTests(unittest.TestCase):
    """Delivery git-evidence mock-parity: PR/CI/remote chips + thin CI spark
    are the first-read hero. Not a WorkLane triage dump."""

    def test_first_read_is_git_evidence_hero_not_worklane_dump(self):
        delivery = _HTML.split('id="delivery-view"')[1].split('id="timeline-view"')[0]
        self.assertIn('Delivery git evidence', delivery)
        self.assertIn('id="delivery-hero-chips"', delivery)
        self.assertIn('id="delivery-ci-spark"', delivery)
        self.assertIn('bp-delivery-facets', delivery)
        self.assertIn('bp-delivery-ledger', delivery)
        self.assertLess(delivery.index('id="delivery-hero"'), delivery.index('id="delivery-filters"'))
        self.assertLess(delivery.index('id="delivery-filters"'), delivery.index('id="remote-repositories"'))
        self.assertNotIn('id="work-band-act-now"', delivery)
        self.assertNotIn('id="for-you-decide"', delivery)
        self.assertNotIn('wo-tile', delivery)
        self.assertNotIn('Act now', delivery)

    def test_css_weights_hero_over_quiet_filters_and_ledger(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-delivery-hero', css)
        self.assertIn('.bp-delivery-ci-spark-bars', css)
        self.assertIn('.bp-delivery-facets', css)
        self.assertIn('.bp-delivery-ledger', css)
        self.assertIn('#delivery-view .bp-delivery-repo', css)
        hero = css.split('.bp-delivery-hero-chip-primary')[1].split('}')[0]
        self.assertIn('font-size: 20px', hero)
        filters = css.split('#delivery-view .bp-filters input')[1].split('}')[0]
        self.assertIn('min-height: 32px', filters)

    def test_paint_keeps_spark_peels_and_branch_honesty(self):
        self.assertIn('function paintDeliverySpark(', _SRC)
        self.assertIn('function deliverySparkBars(', _SRC)
        self.assertIn('function deliveryHeroBranch(', _SRC)
        self.assertIn('function deliveryRemoteSecondary(', _SRC)
        self.assertIn('No CI runs in the ', _SRC)
        self.assertIn('CI unavailable', _SRC)
        self.assertIn('CI not configured', _SRC)
        paint = _SRC.split('function paintDeliveryHero(')[1].split('function paintDeliverySpark(')[0]
        self.assertNotIn('Needs you', paint)
        self.assertNotIn('Act now', paint)
        self.assertNotIn('For You', paint)
        self.assertNotIn('seat', paint.lower())

    def test_does_not_regress_neighbor_surfaces(self):
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="calendar-hero"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('POS', _HTML)


class CalendarLoadBarTests(unittest.TestCase):
    """Issue #153: load-by-day bars on Calendar. Doors stay; no WO dump."""

    def test_hosts_live_on_calendar_view_only(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        delivery = _HTML.split('id="delivery-view"')[1].split('id="timeline-view"')[0]
        self.assertIn('id="calendar-load"', calendar)
        self.assertIn('id="calendar-load-chart"', calendar)
        self.assertIn('id="calendar-load-summary"', calendar)
        self.assertIn('id="calendar-doors"', calendar)
        self.assertLess(calendar.index('id="calendar-doors"'), calendar.index('id="calendar-load"'))
        self.assertLess(calendar.index('id="calendar-load"'), calendar.index('id="schedule-list"'))
        self.assertEqual(_HTML.count('id="calendar-load"'), 1)
        self.assertNotIn('id="calendar-load"', overview)
        self.assertNotIn('id="calendar-load"', work)
        self.assertNotIn('id="calendar-load"', agents)
        self.assertNotIn('id="calendar-load"', delivery)
        self.assertNotIn('wo-tile', calendar)
        self.assertNotIn('id="agents-pulse"', calendar)
        self.assertNotIn('week-grid', calendar)

    def test_paint_uses_calendar_v1_host_and_keeps_doors(self):
        self.assertIn("await import('/js/calendar.v1.js')", _SRC)
        self.assertIn('function paintCalendarSchedule()', _SRC)
        fn = _SRC.split('function calendar()')[1].split('function capabilities()')[0]
        self.assertIn('paintCalendarSchedule()', fn)
        paint = _SRC.split('function paintCalendarSchedule()')[1].split('function calendar()')[0]
        self.assertIn('buildLoadByDay(', paint)
        self.assertIn('paintLoad(', paint)
        self.assertIn('paintDoors(', paint)
        self.assertIn('calendarDoorsFromSnapshot()', paint)
        self.assertNotIn('n8n', paint.lower())
        self.assertNotIn('histogram', paint.lower())
        self.assertNotIn('wo-tile', paint)

    def test_does_not_regress_neighbor_map_a_surfaces(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-calendar-load', css)
        self.assertIn('.bp-calendar-doors', css)
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-floor-spark"', _HTML)
        self.assertIn('id="agents-next-fire"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertIn('id="projects-compare"', _HTML)
        self.assertIn('id="work-calendar-doors"', _HTML)
        self.assertIn('id="delivery-ci-spark"', _HTML)
        self.assertIn('function paintOverviewThroughput()', _SRC)
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn('function paintAgentsFloorSpark()', _SRC)
        self.assertIn('function paintTimelineActivity()', _SRC)
        self.assertIn('function paintProjectsCompare()', _SRC)
        self.assertIn('function paintDeliverySpark(', _SRC)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)

    def test_load_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping calendar load harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'calendar_load_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'calendar load harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        result = json.loads(proc.stdout)
        self.assertEqual(result['origin'], '2026-09-14')
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['counts'], [0, 0, 1, 1, 3, 0, 0])
        self.assertEqual(result['summary'], '5 scheduled · this week')
        self.assertEqual(result['bars'], 7)
        self.assertTrue(result['quiet_hidden'])
        self.assertEqual(result['unavailable'], 'Schedule load unavailable')
        self.assertEqual(result['due_door'], 'Due · 2')
        self.assertEqual(result['fire_door'], '/agents')


class CalendarHybridHonestyStripTests(unittest.TestCase):
    """pc-1540 / Cap C2: reserved Hybrid source + outbound strips, and the
    write door, stay honest — no fake MCP/Connector/Apple/Outlook live
    state, and no write UI until the fabric exists."""

    def test_source_and_outbound_strips_live_on_calendar_view_only(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertIn('data-role="cal-sources"', calendar)
        self.assertIn('data-role="cal-outbound"', calendar)
        self.assertIn('id="calendar-write-door"', calendar)
        self.assertIn('id="calendar-local-line"', calendar)
        self.assertIn('id="calendar-app-facet"', calendar)
        self.assertNotIn('data-role="cal-sources"', overview)
        self.assertNotIn('data-role="cal-sources"', work)
        self.assertLess(calendar.index('data-role="cal-sources"'), calendar.index('id="calendar-load"'))
        self.assertLess(calendar.index('id="calendar-local-line"'), calendar.index('id="calendar-load"'))

    def test_write_door_is_reserved_and_hidden(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        write_door = calendar.split('id="calendar-write-door"')[1].split('>')[0]
        self.assertIn('hidden', write_door)
        self.assertIn('disabled', write_door)
        self.assertIn('aria-disabled="true"', write_door)

    def test_paint_calendar_schedule_paints_both_strips(self):
        paint = _SRC.split('function paintCalendarSchedule()')[1].split('function calendar()')[0]
        self.assertIn('paintSourceStrip(', paint)
        self.assertIn('paintOutboundStrip(', paint)
        self.assertIn('paintCalendarLocalLine(', paint)
        self.assertIn('bindCalendarClock(', paint)
        import_line = _SRC.split("await import('/js/calendar.v1.js')")[0].splitlines()[-1]
        self.assertIn('paintSourceStrip', import_line)
        self.assertIn('paintOutboundStrip', import_line)

    def test_source_strip_reads_worklane_from_sources_state_not_a_fake_mcp(self):
        paint = _SRC.split('function paintCalendarSchedule()')[1].split('function calendar()')[0]
        self.assertIn("source.name==='WorkLane'", paint)
        self.assertIn("workLane: workLaneSource?.state==='available'", paint)
        self.assertNotIn('mcp: true', _SRC.lower())
        self.assertNotIn('connector: true', _SRC.lower())

    def test_css_dims_reserved_chips(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-cal-chip[data-state="reserved"]', css)
        self.assertIn('.bp-cal-write-door[hidden]', css)

    def test_load_harness_covers_strips(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping calendar load harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'calendar_load_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(
                f'calendar load harness failed ({proc.returncode}):\n'
                f'stdout={proc.stdout}\nstderr={proc.stderr}'
            )
        result = json.loads(proc.stdout)
        self.assertEqual(result['source_states'], ['live', 'reserved', 'reserved'])
        self.assertEqual(result['source_states_no_worklane'], ['unavailable', 'reserved', 'reserved'])
        self.assertEqual(result['outbound_states'], ['reserved', 'reserved'])


class CalendarOneAgendaVisualFinishTests(unittest.TestCase):
    """Calendar One Agenda mock-parity: factory clock, not a quiet list."""

    def test_hero_clock_and_one_agenda_are_first_read(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        self.assertIn('id="calendar-hero"', calendar)
        self.assertIn('One Agenda factory clock', calendar)
        self.assertIn('>One Agenda<', calendar)
        self.assertIn('id="calendar-app-facet"', calendar)
        self.assertIn('BluePrint · SoT', calendar)
        self.assertLess(calendar.index('id="calendar-hero"'), calendar.index('id="calendar-doors"'))
        self.assertLess(calendar.index('id="calendar-doors"'), calendar.index('id="calendar-load"'))
        self.assertLess(calendar.index('id="calendar-load"'), calendar.index('id="calendar-filters"'))
        self.assertLess(calendar.index('id="calendar-filters"'), calendar.index('id="dated-work"'))
        self.assertLess(calendar.index('id="dated-work"'), calendar.index('id="schedule-list"'))
        self.assertLess(calendar.index('id="schedule-list"'), calendar.index('id="event-list"'))

    def test_facets_do_not_open_a_second_list(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        self.assertIn('bp-cal-facets', calendar)
        self.assertIn('id="calendar-project"', calendar)
        self.assertIn('id="calendar-app-facet"', calendar)
        self.assertNotIn('id="apple-events"', calendar)
        self.assertNotIn('id="outlook-events"', calendar)
        self.assertNotIn('id="mcp-events"', calendar)
        self.assertEqual(calendar.count('id="dated-work"'), 1)
        self.assertNotIn('Google', calendar)
        self.assertNotIn('google', calendar)

    def test_write_door_stays_reserved_and_copy_never_implies_mcp_write(self):
        calendar = _HTML.split('id="calendar-view"')[1].split('id="settings-view"')[0]
        write_door = calendar.split('id="calendar-write-door"')[1].split('>')[0]
        self.assertIn('hidden', write_door)
        self.assertIn('disabled', write_door)
        self.assertNotIn('mcp write', calendar.lower())
        self.assertNotIn('publish to apple', calendar.lower())

    def test_css_weights_doors_and_week_strip(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-calendar-hero', css)
        self.assertIn('.bp-cal-door-primary', css)
        self.assertIn('#calendar-view .ov-cal-load-chart', css)
        self.assertIn('.bp-cal-app-facet', css)
        self.assertIn('.bp-calendar-agenda', css)

    def test_operations_paints_local_line_and_selectable_clock(self):
        self.assertIn('function paintCalendarLocalLine(', _SRC)
        self.assertIn('Local schedule · WorkLane clocks on this desk.', _SRC)
        self.assertIn('Local schedule · no dated clocks this week.', _SRC)
        self.assertNotIn('Google', _SRC)
        self.assertIn("calendarDay=col.dataset.day", _SRC.replace(' ', ''))
        self.assertIn('One Agenda — the factory clock', _SRC)

    def test_does_not_regress_neighbor_surfaces(self):
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="delivery-hero"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('POS', _HTML)


class MapNodeMotionLeakTests(unittest.TestCase):
    """Issue #156: Map motion stroke stays on Map. Neighbor peels untouched."""

    def test_operations_pages_do_not_host_map_motion_paint(self):
        self.assertNotIn('map-motion-live', _HTML)
        self.assertNotIn('map-motion-recent', _HTML)
        self.assertNotIn('map-motion-unavailable', _HTML)
        self.assertNotIn('classifyNodeMotion', _SRC)
        self.assertNotIn('indexNodeState', _SRC)
        self.assertNotIn('data-motion', _SRC)
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertNotIn('.map-motion-live', css)
        self.assertNotIn('.map-lot.map-motion', css)

    def test_neighbor_peels_stay_on_their_pages(self):
        self.assertIn('id="overview-throughput"', _HTML)
        self.assertIn('id="work-flow"', _HTML)
        self.assertIn('id="agents-floor-spark"', _HTML)
        self.assertIn('id="agents-pulse"', _HTML)
        self.assertIn('id="projects-compare"', _HTML)
        self.assertIn('id="delivery-ci-spark"', _HTML)
        self.assertIn('id="timeline-activity-chart"', _HTML)
        self.assertIn('id="calendar-load"', _HTML)
        self.assertIn('id="calendar-doors"', _HTML)
        self.assertIn('function paintOverviewThroughput()', _SRC)
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn('function paintAgentsFloorSpark()', _SRC)
        self.assertIn('function paintProjectsCompare()', _SRC)
        self.assertIn('function paintDeliverySpark(', _SRC)
        self.assertIn('function paintTimelineActivity()', _SRC)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('POS', _HTML)


class AgentsCanvasPeelTests(unittest.TestCase):
    """pc-1534 / issue #168: Floor | Canvas toggle. Read-only spatial twin."""

    def test_toggle_and_canvas_host_live_on_agents_only(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertIn('id="agents-face"', agents)
        self.assertIn('id="agents-face-floor"', agents)
        self.assertIn('id="agents-face-canvas"', agents)
        self.assertIn('>Floor<', agents)
        self.assertIn('>Canvas<', agents)
        self.assertIn('id="agents-canvas"', agents)
        self.assertIn('id="agents-canvas-empty"', agents)
        self.assertIn('id="agents-canvas-empty-teach"', agents)
        self.assertIn('id="agents-canvas-tour"', agents)
        self.assertIn('id="agents-canvas-tour-start"', agents)
        self.assertIn('id="agents-canvas-legend"', agents)
        self.assertIn('Claim edge', agents)
        self.assertIn('Next-fire edge', agents)
        self.assertIn('id="agents-floor-lists"', agents)
        self.assertLess(agents.index('id="agents-floor-spark"'), agents.index('id="agents-face"'))
        self.assertLess(agents.index('id="agents-face"'), agents.index('id="agents-next-fire"'))
        self.assertLess(agents.index('id="agents-floor-lists"'), agents.index('id="agents-canvas-wrap"'))
        self.assertLess(agents.index('id="agents-canvas-wrap"'), agents.index('id="agent-detail"'))
        self.assertEqual(_HTML.count('id="agents-canvas"'), 1)
        self.assertNotIn('id="agents-canvas"', overview)
        self.assertNotIn('id="agents-canvas"', work)
        self.assertNotIn('id="agents-canvas-tour"', overview)
        self.assertNotIn('id="agents-canvas-tour"', work)
        self.assertNotIn('id="agents-face"', overview)
        self.assertNotIn('id="agents-face"', work)
        self.assertIn('id="agents-pulse"', agents)
        self.assertIn('id="agents-floor-spark"', agents)
        self.assertIn('Working / Idle / Error counts this floor', agents)
        self.assertIn('A seat or job would sit here', agents)
        self.assertIn('Work or Timeline opens from a node', agents)
        self.assertLess(agents.index('id="agents-canvas-empty"'), agents.index('id="agents-canvas-empty-teach"'))
        self.assertLess(agents.index('id="agents-canvas-empty-teach"'), agents.index('id="agents-canvas-tour"'))
        self.assertLess(agents.index('id="agents-canvas-tour"'), agents.index('id="agents-canvas"'))

    def test_paint_reuses_floor_truth_and_has_doors_not_an_editor(self):
        agents = _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0]
        self.assertIn('paintAgentsPulse()', agents)
        self.assertIn('paintAgentsFloorSpark()', agents)
        self.assertIn('paintAgentsNextFire()', agents)
        self.assertIn('syncAgentsFace()', agents)
        self.assertIn('paintAgentsCanvas()', agents)
        self.assertIn('maybeStartAgentsTour()', agents)
        self.assertLess(agents.index('paintAgentsPulse()'), agents.index('paintAgentsCanvas()'))
        self.assertLess(agents.index('paintAgentsCanvas()'), agents.index('maybeStartAgentsTour()'))
        paint = _SRC.split('function paintAgentsCanvas()')[1].split('function timelineActionLabel')[0]
        self.assertIn('agentsCanvasFromSnapshot()', paint)
        self.assertIn('No seats or jobs on this roster.', paint)
        self.assertIn('agents-canvas-empty-teach', paint)
        self.assertIn('maybeStartAgentsTour', paint)
        self.assertIn("id:'strip'", paint.replace(' ', ''))
        self.assertIn("id:'node'", paint.replace(' ', ''))
        self.assertIn("id:'door'", paint.replace(' ', ''))
        self.assertIn('bp-agents-canvas-tour', paint)
        self.assertNotIn('draggable', paint)
        self.assertNotIn('dragstart', paint)
        self.assertNotIn('rewire', paint)
        self.assertNotIn('line.className', _SRC)
        edges = _SRC.split('function paintAgentsCanvasEdges')[1].split('function paintAgentsCanvas()')[0]
        self.assertIn("setAttribute('class','bp-agents-canvas-edge')", edges.replace(' ', ''))
        self.assertNotIn('.className', edges)
        builder = _SRC.split('function buildAgentsCanvas(agents, now)')[1].split('function agentsCanvasFromSnapshot')[0]
        self.assertIn('floorBucket(agent)', builder)
        self.assertIn("group==='seat'", builder.replace(' ', ''))
        self.assertIn('agent.held', builder)
        self.assertIn('next_fire', builder)
        self.assertIn("kind:'claim'", builder.replace(' ', ''))
        self.assertIn("kind:'last_run'", builder.replace(' ', ''))
        self.assertIn("kind:'next_fire'", builder.replace(' ', ''))
        self.assertIn('lastRunTarget(agent)', builder)
        node = _SRC.split('function paintAgentsCanvasNode(node)')[1].split('function paintAgentsCanvasEdges')[0]
        self.assertIn('selectAgent(node.id)', node.replace(' ', ''))
        self.assertIn('work_href', node)
        self.assertIn("door==='ticket'", node.replace(' ', ''))
        self.assertIn('readerHref(', node)
        self.assertIn("'/calendar'", node)
        self.assertIn('node.fire', node)
        self.assertIn('paintAgentsFireChip(node.fire)', node.replace(' ', ''))
        self.assertIn("kind==='fire'", node.replace(' ', ''))
        edges = _SRC.split('function paintAgentsCanvasEdges')[1].split('function paintAgentsCanvas()')[0]
        self.assertIn("dataset.motion='pulse'", edges.replace(' ', ''))
        self.assertIn('dataset.tone', edges)
        self.assertIn('function paintAgentsFireTicks()', _SRC)
        self.assertIn('n8n-style factory', _SRC.lower())
        self.assertNotIn('n8n editor', _SRC.lower())
        self.assertNotIn('histogram', paint.lower())

    def test_does_not_add_a_page_or_regress_floor_and_work(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-agents-face', css)
        self.assertIn('.bp-agents-canvas-node', css)
        self.assertIn('.bp-agents-canvas-edge', css)
        self.assertIn('.bp-agents-canvas-edge[data-kind="claim"]', css)
        self.assertIn('bp-canvas-claim-pulse', css)
        self.assertIn('bp-canvas-claim-flow', css)
        self.assertIn('.bp-agents-canvas-fire', css)
        self.assertIn('.bp-agents-canvas-tick', css)
        self.assertIn('.bp-agents-tour', css)
        self.assertIn('[data-tour-focus="true"]', css)
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('WORKFLOWS', _HTML)
        self.assertNotIn('EXECUTIONS', _HTML)
        self.assertNotIn('id="work-canvas"', _HTML)
        self.assertNotIn('id="overview-canvas"', _HTML)
        work = _SRC.split('function work()')[1].split('function agentAction')[0]
        self.assertIn('paintWorkFlow()', work)
        self.assertNotIn('paintAgentsCanvas', work)
        self.assertIn('function paintAgentsFloorSpark()', _SRC)
        self.assertIn('function paintWorkFlow()', _SRC)
        self.assertIn("['Working',floor.working,'working']", _SRC.replace(' ', ''))

    def test_canvas_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping agents canvas harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'agents_canvas_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'agents canvas harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertEqual(result['pulse'], ['1Working', '2Idle', '1Error'])
        self.assertTrue(result['floor_lists_visible'])
        self.assertTrue(result['canvas_hidden_on_floor'])
        self.assertTrue(result['canvas_visible'])
        self.assertTrue(result['floor_lists_hidden_on_canvas'])
        self.assertEqual(result['seat_ids'], ['working-seat', 'idle-seat', 'failed-seat', 'off-seat'])
        self.assertEqual(result['job_ids'], ['loop-health'])
        self.assertEqual(result['working_bucket'], 'working')
        self.assertTrue(result['has_claim_edge'])
        self.assertTrue(result['has_next_fire_edge'])
        self.assertTrue(result['work_chip'])
        self.assertTrue(result['ticket_door'])
        self.assertEqual(result['empty_roster'], 'No seats or jobs on this roster.')
        self.assertTrue(result['empty_teaches_floor'])
        self.assertEqual(result['tour_steps'], ['strip', 'node', 'door'])
        self.assertEqual(result['tour_seen'], 'seen')
        self.assertTrue(result['floor_back'])
        self.assertTrue(result['claim_pulse'])
        self.assertTrue(result['fire_on_job'])
        self.assertTrue(result['last_run_error_tone'])
        self.assertTrue(result['floor_hero'])
        self.assertTrue(result['coverage_door_closed'])
        self.assertEqual(result['soft_poll_pulse'], ['0Working', '1Idle', '0Error'])


class AgentsFloorFirstGlanceTests(unittest.TestCase):
    """pc-1559 Agents Floor first-glance (end-03): live strip hero only, no ops bulletin."""

    def test_live_strip_and_spark_are_the_only_hero(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        hero = agents.split('id="agents-hero"', 1)[1].split('id="agents-face"', 1)[0]
        self.assertIn('class="bp-agents-hero"', agents)
        self.assertIn('id="agents-pulse"', hero)
        self.assertIn('id="agents-floor-spark"', hero)
        self.assertNotIn('bp-muted bp-agents-floor-spark', hero)
        self.assertNotIn('id="agents-coverage-door"', hero)
        self.assertNotIn('id="coverage-list"', hero)
        self.assertNotIn('id="agents-legend"', hero)
        self.assertNotIn('Hire…', hero)
        self.assertLess(agents.index('id="agents-hero"'), agents.index('id="agents-pulse"'))
        self.assertLess(agents.index('id="agents-pulse"'), agents.index('id="agents-floor-spark"'))
        self.assertLess(agents.index('id="agents-floor-spark"'), agents.index('id="agents-face"'))
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('pc-1559', css)
        self.assertIn('.bp-agents-hero .bp-agents-floor-spark', css)
        self.assertIn('font-size: 32px', css)
        hero_css = css[css.index('.bp-agents-hero {'):css.index('.bp-agents-meta')]
        self.assertIn('border: 1px solid var(--ov-tile-border-strong)', hero_css)
        self.assertIn('font-size: 15px', hero_css)
        self.assertNotIn('#fff', hero_css)

    def test_coverage_hire_and_legend_stay_behind_closed_door(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        door = agents.split('id="agents-coverage-door"', 1)[1]
        self.assertIn('class="bp-agents-door"', agents)
        door_tag = re.search(r'<details[^>]*id="agents-coverage-door"[^>]*>', agents)
        self.assertIsNotNone(door_tag)
        self.assertNotIn(' open', door_tag.group(0))
        self.assertIn('id="agents-coverage-summary"', door)
        self.assertIn('id="coverage-list"', door)
        self.assertIn('id="agents-legend"', door)
        self.assertIn('not a hire-now list', door)
        self.assertNotIn('<h2>Coverage</h2>', agents)
        paint = _SRC.split('function paintCoverageDoor(')[1].split('function renderCoverage(')[0]
        assigned = [line for line in paint.splitlines() if 'textContent' in line]
        self.assertTrue(assigned)
        self.assertIn('Coverage · none reported', paint)
        self.assertIn('Coverage · 1 project', paint)
        self.assertTrue(all('missing staff' not in line and 'Hire' not in line for line in assigned))
        self.assertIn('pc-1559', paint)

    def test_dispatch_stays_quiet_and_floor_canvas_caps_stay(self):
        action = _SRC.split('function agentAction(agent, dispatchLabel)')[1].split('function currentOrderFor')[0]
        self.assertIn("'bp-quiet-action'", action)
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="agents-face-floor"', agents)
        self.assertIn('id="agents-face-canvas"', agents)
        self.assertIn('id="agents-canvas"', agents)
        self.assertIn('id="agents-canvas-tour"', agents)
        self.assertIn("kind:'claim'", _SRC.replace(' ', ''))
        self.assertIn("kind:'next_fire'", _SRC.replace(' ', ''))
        self.assertIn('maybeStartAgentsTour()', _SRC)
        self.assertNotIn('draggable', _SRC.split('function paintAgentsCanvas()')[1].split('function timelineActionLabel')[0])
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('point of sale', _HTML.lower())


class AgentsFloorScarcityTests(unittest.TestCase):
    """Agents Floor scarcity / visual-finish: factory hero first, coverage door, dispatch secondary."""

    def test_hero_band_is_first_read_and_holds_pulse_plus_spark(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="agents-hero"', agents)
        self.assertIn('class="bp-agents-hero"', agents)
        self.assertLess(agents.index('id="agents-hero"'), agents.index('id="agents-pulse"'))
        self.assertLess(agents.index('id="agents-pulse"'), agents.index('id="agents-floor-spark"'))
        self.assertLess(agents.index('id="agents-floor-spark"'), agents.index('id="agents-face"'))
        self.assertLess(agents.index('id="agents-face"'), agents.index('id="agents-next-fire"'))
        self.assertLess(agents.index('id="agents-next-fire"'), agents.index('id="agents-floor-lists"'))
        pulse_close = agents.index('id="agents-pulse"')
        spark_at = agents.index('id="agents-floor-spark"')
        hero_close = agents.index('id="agents-face"')
        self.assertLess(pulse_close, spark_at)
        self.assertLess(spark_at, hero_close)
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertNotIn('id="agents-hero"', overview)
        self.assertNotIn('id="agents-hero"', work)
        self.assertNotIn('id="agents-coverage-door"', overview)

    def test_coverage_hire_and_legend_sit_behind_a_closed_door(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        door = agents.split('id="agents-coverage-door"', 1)[1]
        self.assertIn('class="bp-agents-door"', agents)
        self.assertIn('id="agents-coverage-summary"', door)
        self.assertIn('id="coverage-list"', door)
        self.assertIn('id="agents-legend"', door)
        self.assertIn('not a hire-now list', door)
        self.assertLess(agents.index('id="seat-list"'), agents.index('id="agents-coverage-door"'))
        self.assertLess(agents.index('id="job-list"'), agents.index('id="agents-coverage-door"'))
        self.assertLess(agents.index('id="supervisor-panel"'), agents.index('id="agents-coverage-door"'))
        self.assertNotIn('<h2>Coverage</h2>', agents)
        self.assertNotIn('class="bp-panel"><h2>Coverage</h2>', _HTML)
        self.assertIn('function paintCoverageDoor(', _SRC)
        self.assertIn('Coverage · none reported', _SRC)
        self.assertIn("renderCoverage()", _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0])

    def test_dispatch_controls_are_secondary_not_twin_hero(self):
        action = _SRC.split('function agentAction(agent, dispatchLabel)')[1].split('function currentOrderFor')[0]
        self.assertIn("'bp-quiet-action'", action)
        self.assertIn("el('button',agent.action==='recover'", action.replace(' ', ''))
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-agents-hero', css)
        self.assertIn('#agents-floor-lists .bp-quiet-action', css)
        self.assertIn('font-size: 32px', css)
        hero = css[css.index('.bp-agents-hero {'):css.index('.bp-agents-meta')]
        self.assertIn('border: 1px solid var(--ov-tile-border-strong)', hero)
        self.assertNotIn('#fff', hero)
        self.assertIn('.bp-agents-door', css)
        self.assertLess(css.index('.bp-agents-hero'), css.index('.bp-agents-door'))

    def test_floor_canvas_toggle_and_canvas_caps_stay(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('id="agents-face-floor"', agents)
        self.assertIn('id="agents-face-canvas"', agents)
        self.assertIn('id="agents-canvas"', agents)
        self.assertIn('id="agents-canvas-tour"', agents)
        self.assertIn('Working / Idle / Error counts this floor', agents)
        self.assertIn("kind:'claim'", _SRC.replace(' ', ''))
        self.assertIn("kind:'last_run'", _SRC.replace(' ', ''))
        self.assertIn("kind:'next_fire'", _SRC.replace(' ', ''))
        self.assertIn('maybeStartAgentsTour()', _SRC)
        self.assertNotIn('draggable', _SRC.split('function paintAgentsCanvas()')[1].split('function timelineActionLabel')[0])
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)
        self.assertNotIn('n8n', _HTML.lower())
        self.assertNotIn('point of sale', _HTML.lower())


class AgentsCanvasMotionTests(unittest.TestCase):
    """Agents Canvas motion / visual-finish MUST — C1 claim pulse + C6 next-fire ticks."""

    def test_claim_edges_pulse_and_claimed_wo_stays_on_the_node(self):
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        claim = css[css.index('.bp-agents-canvas-edge[data-kind="claim"]'):css.index('.bp-agents-canvas-edge[data-kind="next_fire"]')]
        self.assertIn('bp-canvas-claim-pulse', claim)
        self.assertIn('bp-canvas-claim-flow', claim)
        self.assertIn('stroke-dasharray', claim)
        self.assertIn('var(--ov-state-working)', claim)
        self.assertIn('@keyframes bp-canvas-claim-flow', css)
        self.assertIn('.bp-agents-canvas-claim', css)
        self.assertIn('font-weight: 600', css[css.index('.bp-agents-canvas-claim'):css.index('.bp-agents-canvas-fire {')])
        node = _SRC.split('function paintAgentsCanvasNode(node)')[1].split('function paintAgentsCanvasEdges')[0]
        self.assertIn('bp-agents-canvas-claim', node)
        edges = _SRC.split('function paintAgentsCanvasEdges')[1].split('function paintAgentsCanvas()')[0]
        self.assertIn("dataset.motion='pulse'", edges.replace(' ', ''))

    def test_next_fire_ticks_sit_on_jobs_and_seats(self):
        builder = _SRC.split('function buildAgentsCanvas(agents, now)')[1].split('function agentsCanvasFromSnapshot')[0]
        self.assertIn('actor.fire=', builder.replace(' ', ''))
        self.assertIn('countdownWords(seconds)', builder.replace(' ', ''))
        node = _SRC.split('function paintAgentsCanvasNode(node)')[1].split('function paintAgentsCanvasEdges')[0]
        self.assertIn('paintAgentsFireChip(node.fire)', node.replace(' ', ''))
        self.assertIn("kind==='fire'", node.replace(' ', ''))
        self.assertIn('paintAgentsFireTicks()', node)
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-agents-canvas-ticks', css)
        self.assertIn('.bp-agents-canvas-tick', css)
        self.assertIn('var(--ov-state-scanning)', css[css.index('.bp-agents-canvas-edge[data-kind="next_fire"]'):css.index('.bp-agents-canvas-edge[data-kind="last_run"]')])
        self.assertIn('Live factory window of this floor', _HTML)
        self.assertIn('Next-fire ticks sit on the job or seat', _HTML)
        self.assertIn('this is not an editor', _HTML)

    def test_soft_poll_and_tour_and_floor_scarcity_stay(self):
        agents = _SRC.split('function agents()')[1].split('const SOURCE_LABEL')[0]
        self.assertLess(agents.index('paintAgentsPulse()'), agents.index('paintAgentsCanvas()'))
        self.assertIn('maybeStartAgentsTour()', agents)
        self.assertIn('id="agents-hero"', _HTML)
        self.assertIn('id="agents-coverage-door"', _HTML)
        self.assertIn('id="agents-face-floor"', _HTML)
        self.assertIn('id="agents-canvas-tour"', _HTML)
        self.assertIn("id:'strip'", _SRC.replace(' ', ''))
        self.assertIn("id:'node'", _SRC.replace(' ', ''))
        self.assertIn("id:'door'", _SRC.replace(' ', ''))
        self.assertNotIn('draggable', _SRC.split('function paintAgentsCanvas()')[1].split('function timelineActionLabel')[0])
        nav = _HTML.split('class="bp-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertEqual(len(re.findall(r'<a href=', nav)), 10)


class AgentsCanvasCap1Tests(unittest.TestCase):
    """pc-1564 Cap 1 — n8n-feel acquaintance canvas. Read-only factory window."""

    def test_full_bleed_stage_legend_and_distinct_shapes(self):
        agents = _HTML.split('id="agents-view"')[1].split('id="delivery-view"')[0]
        self.assertIn('class="bp-agents-canvas-stage"', agents)
        self.assertIn('id="agents-canvas-legend"', agents)
        self.assertLess(agents.index('id="agents-canvas-legend"'), agents.index('id="agents-canvas"'))
        self.assertIn('>Working<', agents.split('id="agents-canvas-legend"', 1)[1])
        self.assertIn('>Idle<', agents.split('id="agents-canvas-legend"', 1)[1])
        self.assertIn('>Error<', agents.split('id="agents-canvas-legend"', 1)[1])
        self.assertIn('Claim edge', agents.split('id="agents-canvas-legend"', 1)[1])
        self.assertIn('Next-fire edge', agents.split('id="agents-canvas-legend"', 1)[1])
        self.assertIn('Live factory window of this floor', agents)
        self.assertIn('this is not an editor', agents)
        self.assertIn('This factory window is not an editor', agents)
        css = (Path(__file__).resolve().parent.parent / 'static' / 'css' / 'operations.css').read_text(encoding='utf-8')
        self.assertIn('.bp-agents-canvas-stage', css)
        self.assertIn('min-height: min(70vh, 780px)', css)
        self.assertIn('.bp-agents-canvas-node[data-kind="seat"]', css)
        self.assertIn('.bp-agents-canvas-node[data-kind="job"]', css)
        self.assertIn('clip-path: polygon(', css)
        self.assertIn('.bp-agents-canvas-legend', css)
        self.assertNotIn('resize: both', css[css.index('.bp-agents-canvas-node {'):css.index('.bp-agents-canvas-person')])

    def test_face_deep_link_and_tour_name_the_factory_not_an_editor(self):
        self.assertIn("query.get('face')==='canvas'", _SRC.replace(' ', ''))
        self.assertIn("params.set('face','canvas')", _SRC.replace(' ', ''))
        self.assertIn("params.delete('view')", _SRC.replace(' ', ''))
        self.assertIn('n8n-style factory', _SRC)
        self.assertIn('property inspector', _SRC)
        self.assertNotIn('n8n editor', _SRC.lower())
        node = _SRC.split('function paintAgentsCanvasNode(node)')[1].split('function paintAgentsCanvasEdges')[0]
        self.assertIn('dataset.shape', node)
        self.assertIn('bp-agents-canvas-project', node)
        self.assertIn('paintAgentsCanvasSpark(node.id)', node.replace(' ', ''))
        self.assertIn('selectAgent(node.id)', node.replace(' ', ''))
        self.assertNotIn('draggable', node)
        self.assertNotIn('addNode', node)
        overview = _HTML.split('id="overview-view"')[1].split('id="work-view"')[0]
        work = _HTML.split('id="work-view"')[1].split('id="projects-view"')[0]
        self.assertNotIn('id="agents-canvas-legend"', overview)
        self.assertNotIn('id="agents-canvas-legend"', work)
        self.assertNotIn('id="agents-canvas"', overview)
        self.assertNotIn('id="agents-canvas"', work)
        self.assertLess(
            _HTML.split('id="agents-view"')[1].index('id="agents-coverage-door"'),
            _HTML.split('id="agents-view"')[1].index('id="agents-canvas-wrap"'),
        )
        door = _HTML.split('id="agents-coverage-door"', 1)[1].split('id="agents-canvas-wrap"', 1)[0]
        self.assertIn('id="coverage-list"', door)

    def test_canvas_cap1_harness(self):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not available; skipping agents canvas harness')
        harness = Path(__file__).resolve().parent / 'harness' / 'agents_canvas_check.mjs'
        proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=15, check=False)
        if proc.returncode != 0:
            raise AssertionError(f'agents canvas harness failed ({proc.returncode}):\nstdout={proc.stdout}\nstderr={proc.stderr}')
        result = json.loads(proc.stdout)
        self.assertEqual(result['working_shape'], 'rounded')
        self.assertEqual(result['job_shape'], 'diamond')
        self.assertTrue(result['has_legend'])
        self.assertTrue(result['has_project_label'])
        self.assertTrue(result['has_optional_spark'])
        self.assertIn('face=canvas', result['canvas_href'])
        self.assertNotIn('view=canvas', result['canvas_href'])
        self.assertTrue(result['person_sheet'])
        self.assertIn('n8n-style factory', result['tour_factory'])


if __name__ == '__main__':
    unittest.main()
