# BluePrint operations interface — September 12 evolution

User decision: the application developed on :8803 is the forward BP baseline. The user authorizes revising its pages, navigation, density, and live behavior. This supersedes the earlier V1 limits on three equal tiles, no automatic refresh, and an inert Local desk banner. The approved dark V1 palette remains the starting design system.

## Product behavior

BluePrint provides one view into the selected workspace's projects, work orders, agents, schedules, and data sources. Overview prioritizes explicitly human-gated work and gives project context. Work provides search, project/status/assignment filters, pagination, and links to a full description/comment reader. Projects groups registered stores. Agents distinguishes registry membership from fresh runtime evidence. Calendar distinguishes WorkForce next-run reports, dates derived from work orders, and optional manually supplied events. Connections explains source availability and excluded databases. Settings contains functioning browser display preferences and running package identity.

The desk disclosure describes the selected workspace; it is not a cloud switch. GitHub delivery evidence is connected through an explicit repository allowlist on the Delivery page. Timeline joins WorkLane events, WorkForce ledger rows, supervisor passes and GitHub delivery into one source-labelled stream with honest freshness. Direct remote agent execution is not configured. A future remote adapter must carry source identity, observation time, and failure state. A local work order describing remote work is not proof of remote execution.

## Data and interaction rules

- Read only registered local project stores for operational counts. List unregistered/backup database filenames in Connections without counting their contents. No migration or deletion is implied.
- Distinguish human attention from blocked status, and preserve stored lifecycle status.
- Refresh every 15 seconds by default while visible. Allow 30-second/manual preferences. Avoid overlapping requests and rapid failure retries. Preserve last successful data when refresh fails and show its age.
- Animate only content updates and interactions. Respect reduced-motion settings.
- A roster entry does not prove an agent is running. Missing or stale heartbeat means unknown runtime state; fresh heartbeat is not a process health test.
- Display installed package metadata as the running build, not an unrelated Homebrew formula version.
- Render work titles, descriptions, comments, and calendar notes as text, never executable markup.

## Current delivery state

The application is deployed on :8803 from the canonical BluePrint source and
an isolated installed release. Build identity comes from installed package
metadata and the workspace deployment receipt. Old :8801/:8802 links redirect
in the same process; no separate preview is part of normal operation.
See [deployment and recovery](../operations/DEPLOYMENT.md).

Work-order notes, priority, hold, resume, and assignment to a registered agent
use WorkLane with an explicit project, verified store, and record-version
check. Workspace-scoped actions require WorkLane local-roster authority and never use an unrelated default WorkForce service. Assignment does not trigger a default host wake or notification. The reader displays errors and preserves the user's context. Notes
cannot smuggle lifecycle commands. Create and close use the owning engine
through the established work-order process. Agents provides manual dispatch
through WorkForce and displays refusal reasons, including an empty queue.
An assignment is not a dispatch, a dispatch acceptance is not a claim, and
a claim is not completion. Scheduled execution requires a verified schedule
and run evidence; a roster entry alone supplies neither.

Map provides both spatial navigation and a keyboard-accessible folder/paper
browser. Document readers contain untrusted text, focus the close control,
and return focus to the originating paper on dismissal. Project papers
catalog existing documents under Product, System, Operations, and Development;
this navigation does not confer public exposure or authority on a document.

GitHub PRs, checks, workflows, and releases carry repository identity and
observation state. They are delivery evidence, not agent heartbeats. Local
scheduled report jobs show actual execution receipts and are explicitly
identified as deterministic reports. They do not imply AI implementation
coverage. A future remote execution connection needs an identified runtime
and its explicit access configuration.

Verification includes isolated real-engine action tests, origin and store
refusal paths, unavailable/stale-source behavior, installed-wheel activation,
and browser navigation/readers. Host-specific test counts, versions, commits,
and remaining consolidation items live in the workspace execution report;
they are not a permanent product specification.

## Map navigation repair

The default Map shows managed projects, with names visible without hovering.
Other workspace folders are optional in View. Opening a folder replaces the
visible level rather than layering every project behind its children. Large
levels have bounded spatial pages; the folder/paper browser retains the full
readable list. Breadcrumbs and Workspace return to a parent or root. At narrow
widths the list provides the same navigation without a miniature unreadable map.
Keyboard users can activate spatial nodes with Enter or Space.

MCP mirror verification checks existing Cursor entries as well as Grok/Codex
mirrors. Synchronization updates only Cursor servers already configured there;
it does not enroll additional servers or infer session approval/authentication.
A passing mirror check and successful server handshake are evidence about MCP
server configuration only; they say nothing about whether a scheduled job is
enabled or running. The unattended local loop's own evidence is the scheduled
jobs described below.

## Scheduled local loop

Since 2026-09-14 the local loop runs unattended from three daemon-owned
WorkForce roster jobs (`kind: job`; none of the three is a seat and none
claims a work order under its own identity):

| Job | Cadence | May | May not |
|---|---|---|---|
| **bp-supervisor** | `10,30,50 * * * *`, budget 35m | Collect fresh readiness/lock/ledger state; stop without a model call when the operator stop file exists, no eligible seat has fresh ready work, or provider failures are escalated; otherwise propose and re-validate work and dispatch it onto a seat within its configured cap | Claim, sign, or close a WorkLane order itself; recover a reservation; merge, deploy or change host configuration; it does not consult `COORDINATOR.lock` and keeps firing on schedule regardless of a live coordinator session |
| **integrator** | `*/20 * * * *`, budget 50m, deterministic script, no model call | For each of its two configured stores (protocolcity and workforce), drain orders parked in_review by a registered implementation seat: suites on the seat checkout, PR open/update, reviewer dispatch, findings handling, bounded recovery rounds, merge only on green CI with no findings and a clean checkout, version bump on main, stage, then activate only when no other seat is in flight (staging always runs; a seat in flight skips only the activate step, recorded as `activate_skipped`), installed-version verification, and the PROTOCOL §5 close | Use a bypass-permission flag; act while a fresh `COORDINATOR.lock` exists (see stand-down rule below) |
| **loop-health** | `5,35 * * * *`, budget 2m, deterministic report, no model call | Read the daemon receipt, the integrator ledger and last pass output, seat locks, the coordinator lock, and the BluePrint/WorkLane HTTP endpoints; write one report line and exit non-zero on a defect so the ledger row reads ERROR and Agents shows a failed job | Dispatch, claim, merge or install anything |

The worker-config contract and README text for `bp-supervisor`
(`local/worker-config/bounded-supervisor/{README.md,workers/bp-supervisor/CONTRACT.md}`)
have been updated under wf-269 to record the `10,30,50 * * * *` cron and
that passes run unattended; they no longer say "a `manual` schedule means
nothing runs unattended".
[AGENTS_INTENT.md](AGENTS_INTENT.md)'s 2026-09-13 mockup (§"Information
hierarchy", `SUPERVISOR (bp-supervisor · manual · budget 35m)`) and its
JOBS list are earlier art from before this record and likewise predate
the cron registration; they are superseded by the table above, which
should govern a future edit to that mockup rather than the reverse.

**Stand-down rule.** Only **integrator** stands down. A live coordinator
session keeps the lock file at
`local/reports/parallel-plan-pass/uplift/COORDINATOR.lock` fresh by
rewriting its `updated_at` field (not merely by touching the file); while
`now - updated_at` is under the configured TTL (2400s / 40 minutes by
default), the integrator skips its pass entirely (logged as
`skipped_coordinator_active`) so it never acts on a checkout a live
coordinator session is using. **bp-supervisor** and **loop-health** do not
check this lock and keep firing on their own schedules even while a
coordinator session is live; a coordinator working a live implementation
checkout must rely on the reservation/lock it already holds, not on the
scheduled loop standing down around it. loop-health flags a stand-down
without a fresh lock as a defect because it reads only the last recorded
integrator outcome, not the lock's current state at check time: after a
legitimate coordinator handoff the last line can still read
`skipped_coordinator_active` for up to one integrator cadence (~20 minutes)
until the next `*/20` pass overwrites it, so a defect row here can mean
either the integrator is genuinely standing down with a stale lock or the
loop is briefly catching up to a handoff — an operator should check the
lock's own `updated_at` before treating it as an incident.

**What a person still does.** Hire or retire a seat; clear an exhausted
recovery round or an operator stop file; resolve an escalated or failed
supervisor/integrator pass through the preserved-reservation recovery
protocol, never a blind retry; and any decision, credential, publication or
host-configuration change none of the three jobs is authorized to make.

## Map context and prior FAST implementation

The active Map shares the application header, workspace search and operations projection. Folder navigation exposes project-scoped work, human attention, papers and existing instructions, plus the workspace Agents and jobs surface. Open work includes deferred/tracking orders; in-progress status is labeled as status, never live agent activity. Missing sources remain unavailable and truncated details are disclosed. The project/paper outline and breadcrumbs work independently of the SVG scene.

The prior FAST layer, theater, folder-seat stack and four-lens host are retired implementation recipes. Their useful access and truthfulness outcomes are carried by these current controls; they must not be restored as a second projection or an apparent live activity layer. This decision does not claim every optional historical visual treatment is implemented.

## Navigation acceptance

The folder browser groups projects/folders separately from papers, using restrained type icons and preserving the document's original name (including existing emoji). Breadcrumbs and canonical Map URLs preserve folder/paper context through work-order reading. Reader return targets are limited to local Work/Map routes; cold links fall back to Work. Content arrival uses a short fade/translation only when both system and saved motion preferences allow it. Camera pan/zoom remains direct, without ambient or simulated activity.
