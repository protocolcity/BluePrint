# BluePrint operations interface — September 12 evolution

User decision: the application developed on :8803 is the forward BP baseline. The user authorizes revising its pages, navigation, density, and live behavior. This supersedes the earlier V1 limits on three equal tiles, no automatic refresh, and an inert Local desk banner. The approved dark V1 palette remains the starting design system.

## Product behavior

BluePrint provides one view into the selected workspace's projects, work orders, agents, schedules, and data sources. Overview prioritizes explicitly human-gated work and gives project context. Work provides search, project/status filters, pagination, and links to a full description/comment reader. Projects groups registered stores. Agents distinguishes registry membership from fresh runtime evidence. Calendar distinguishes WorkForce next-run reports, dates derived from work orders, and optional manually supplied events. Connections explains source availability and excluded databases. Settings contains functioning browser display preferences and running package identity.

The desk disclosure describes the selected workspace; it is not a cloud switch. GitHub delivery activity is connected through an explicit repository allowlist. Direct remote agent execution is not configured. A future remote adapter must carry source identity, observation time, and failure state. A local work order describing remote work is not proof of remote execution.

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
check. The reader displays errors and preserves the user's context. Notes
cannot smuggle lifecycle commands. Create, close, and agent-dispatch forms
are not currently implemented in BP; those operations use their owning
engines through the established work-order process.

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
