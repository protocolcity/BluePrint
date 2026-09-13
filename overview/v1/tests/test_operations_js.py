"""Regression guards on operations.js wiring for STATES_AND_TERMS.md D6-D9.

Full DOM behavior is exercised by the browser check in the ticket; these
guard the literal source so the metric definitions, the default work
filter, and the claim-aware status text cannot silently regress.
"""
import json
import shutil
import subprocess
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


class ClaimPresentationTests(unittest.TestCase):
    def test_status_text_distinguishes_live_and_parked_from_open(self):
        self.assertIn('Live with', _SRC)
        self.assertIn('Parked by', _SRC)
    def test_watch_copy_never_says_stalled(self):
        self.assertNotIn('stalled', _SRC.lower())


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


class BlockedFilterTests(unittest.TestCase):
    """Blocked is a secondary filter on declared blockers, not a Status
    lifecycle word (STATES_AND_TERMS.md §5: Status holds lifecycle only)."""
    def test_blocked_filter_matches_declared_blockers_not_a_task_status(self):
        self.assertIn("!blockedOnly||(o.blockers&&o.blockers.length)", _SRC.replace(' ', ''))
    def test_blocked_is_not_a_status_option(self):
        self.assertNotIn('<option value="blocked">', _HTML)
    def test_blocked_filter_control_exists_in_the_markup(self):
        self.assertIn('id="blocked-filter"', _HTML)


class FiveAxisFilterTests(unittest.TestCase):
    """STATES_AND_TERMS.md §5 (pc-1482): Assignment, Status, Gate, Kind and
    For You are five orthogonal axes; Work composes them with search and
    project, and states the filtered/total count with a clear-all."""
    def test_status_filter_holds_only_lifecycle_words(self):
        self.assertIn('<option value="backlog">Open</option>', _HTML)
        self.assertIn('<option value="in_progress">Live</option>', _HTML)
        self.assertIn('<option value="in_review">Parked</option>', _HTML)
        self.assertNotIn('For You (any face)', _HTML.split('id="gate-filter"')[0].split('id="status-filter"')[1])
    def test_gate_filter_offers_the_five_gate_values(self):
        for value in ('none', 'human', 'timer', 'deferred', 'tracking'):
            self.assertIn(f'value="{value}"', _HTML)
    def test_attention_filter_offers_the_four_faces_and_any(self):
        for value in ('any', 'decide', 'read', 'watch', 'note'):
            self.assertIn(f'<option value="{value}">', _HTML)
    def test_filters_compose_with_and_not_or(self):
        fn = _SRC.split('function work()')[1]
        compact = fn.replace(' ', '')
        self.assertIn('selectedProject||o.project===selectedProject', compact)
        self.assertIn('selectedAssignment||matchesAssignment', compact)
        self.assertIn('status||o.status===status', compact)
        self.assertIn("gate||(gate==='none'?!o.gate_type:o.gate_type===gate)", compact)
        self.assertIn("attention||(attention==='any'?o.attention:o.attention_face===attention)", compact)
        self.assertIn('blockedOnly||(o.blockers&&o.blockers.length)', compact)
    def test_results_state_filtered_of_total(self):
        self.assertIn("`${orders.length} of ${total} matching work order", _SRC)
    def test_clear_all_resets_every_filter(self):
        fn = _SRC.split("$('clear-filters').addEventListener('click',()=>{")[1].split('});')[0]
        for control in ("$('search').value=''", "$('project-filter').value=''", "$('assignment-filter').value=''",
                        "$('status-filter').value=''", "$('gate-filter').value=''", "$('attention-filter').value=''",
                        "$('blocked-filter').checked=false"):
            self.assertIn(control, fn.replace(' ', ''))
    def test_active_filters_render_as_dismissable_chips(self):
        self.assertIn("function renderActiveFilters()", _SRC)
        self.assertIn("'bp-filter-chip'", _SRC)
        self.assertIn("$('clear-filters').hidden=!chips.length", _SRC.replace(' ', ''))


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
        for list_id in ('metrics', 'work-list', 'seat-list', 'job-list', 'project-summary', 'projects-view', 'calendar-today', 'calendar-next', 'calendar-past', 'schedule-list', 'event-list', 'engine-list', 'excluded-store-list'):
            self.assertIn(f"reconcileList($('{list_id}')", _SRC)

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
        self.assertIn('Seats claim work orders; jobs run duties. State comes from the WorkForce ledger.', _HTML)

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
        self.assertIn("timelineStep('Recovery attempts'", _SRC)
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
        self.assertIn("row.setAttribute('role','button')", fn)
        self.assertIn('row.tabIndex=1'.replace('1', '0'), fn.replace(' ', ''))
        self.assertIn("event.target.closest('button')", fn)
        self.assertIn("event.key==='Enter'", fn)

    def test_elapsed_is_a_time_budget_never_a_percent(self):
        fn = _SRC.split('function elapsedText(agent)')[1].split('function ')[0]
        self.assertIn('budget', fn)
        self.assertNotIn('%', fn)

    def test_current_work_id_is_a_usable_reader_link(self):
        fn = _SRC.split('function heldLink(agent)')[1].split('function ')[0]
        self.assertIn("readerHref('/work-order?'", fn)
        self.assertIn('workUrl(order)', fn)

    def test_timeline_covers_the_five_source_labelled_phases_in_order(self):
        fn = _SRC.split('function agentTimeline(agent)')[1].split('function agentDetail')[0]
        for phase in ('Dispatch candidate', 'Verified claim', 'Observed run start', 'Recovery attempts', 'Terminal outcome'):
            self.assertIn(f"timelineStep('{phase}'", fn)
        order = [fn.index(f"timelineStep('{phase}'") for phase in
                 ('Dispatch candidate', 'Verified claim', 'Observed run start', 'Recovery attempts', 'Terminal outcome')]
        self.assertEqual(order, sorted(order))

    def test_missing_timeline_phases_read_not_reported_not_inferred(self):
        fn = _SRC.split('function agentTimeline(agent)')[1].split('function agentDetail')[0]
        self.assertIn("'Not reported'", fn)

    def test_an_old_failure_no_longer_held_is_distinguished_from_a_current_failure(self):
        fn = _SRC.split('function agentTimeline(agent)')[1].split('function agentDetail')[0]
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


class DeliveryQuietCopyTests(unittest.TestCase):
    """pc-1466 review fix: quiet copy must follow repo.quiet only."""

    def test_quiet_copy_uses_repo_quiet_flag_only(self):
        compact = _SRC.replace(' ', '')
        self.assertIn("repo.quiet?'Quietinthelast14days.'", compact)
        self.assertNotIn("repo.quiet||repo.state==='connected'", compact)


class PersonaChipTests(unittest.TestCase):
    """pc-1473 review fix: the chip slot must print the persona text
    (Your todo / Reminder <date> / Your note) instead of "Needs routing"
    on you-qualifier rows, and still print "Needs routing" when there is
    no persona."""

    def test_persona_renders_in_the_chip_slot_before_needs_routing(self):
        self.assertIn("if(order.persona)content.append(el('span',order.persona,'bp-order-note'));", _SRC.replace(' ', ''))

    def test_needs_routing_only_renders_when_there_is_no_persona(self):
        self.assertIn("elseif(order.needs_routing)content.append(el('span','Needsrouting','bp-order-note'));", _SRC.replace(' ', ''))


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
        self.assertIn('<h2>Coverage</h2>', _HTML)
        self.assertNotIn('<h2>Seats</h2><div id="coverage-list"', _HTML)

    def test_hiring_footnote_is_present(self):
        self.assertIn('Hiring runs on this Mac through WorkForce; the desk never writes the roster.', _HTML)

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


class ConnectionsEngineTests(unittest.TestCase):
    def test_engine_list_paints_versions_reachability_and_supervisor(self):
        self.assertIn('id="engine-list"', _HTML)
        self.assertIn("function engines()", _SRC)
        self.assertIn("'WorkLane engine'", _SRC)
        self.assertIn("'WorkForce engine'", _SRC)
        self.assertIn("'WorkLane API'", _SRC)
        self.assertIn("'Supervisor last pass'", _SRC)
        self.assertIn("Source: ", _SRC)
        self.assertIn("Observed ", _SRC)


if __name__ == '__main__':
    unittest.main()
