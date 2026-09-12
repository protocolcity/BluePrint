# BluePrint operations interface — September 12 evolution

User decision: the application developed on :8803 is the forward BP baseline. The user authorizes revising its pages, navigation, density, and live behavior. This supersedes the earlier V1 limits on three equal tiles, no automatic refresh, and an inert Local desk banner. The approved dark V1 palette remains the starting design system.

## Product behavior

BluePrint provides one view into the selected workspace's projects, work orders, agents, schedules, and data sources. Overview prioritizes explicitly human-gated work and gives project context. Work provides search, project/status filters, pagination, and links to a full description/comment reader. Projects groups registered stores. Agents distinguishes registry membership from fresh runtime evidence. Calendar separates WorkForce next-run reports from manually supplied calendar events. Connections explains source availability and excluded databases. Settings contains functioning browser display preferences and running package identity.

The desk disclosure describes the selected workspace; it is not a cloud switch. Remote operations are explicitly not connected. A future remote adapter must carry source identity, observation time, and failure state. A local work order describing remote work is not proof of remote execution.

## Data and interaction rules

- Read only registered local project stores for operational counts. List unregistered/backup database filenames in Connections without counting their contents. No migration or deletion is implied.
- Distinguish human attention from blocked status, and preserve stored lifecycle status.
- Refresh every 15 seconds by default while visible. Allow 30-second/manual preferences. Avoid overlapping requests and rapid failure retries. Preserve last successful data when refresh fails and show its age.
- Animate only content updates and interactions. Respect reduced-motion settings.
- A roster entry does not prove an agent is running. Missing or stale heartbeat means unknown runtime state; fresh heartbeat is not a process health test.
- Display installed package metadata as the running build, not an unrelated Homebrew formula version.
- Render work titles, descriptions, comments, and calendar notes as text, never executable markup.

## Delivery state

Implemented in isolated blueprint-consolidation candidate, package 0.1.47+consolidation.2. 129 Overview tests and 44 Map tests pass. Installed-wheel route/data smoke test passes. Browser checks cover search → detail, real comment trail, desk disclosure, calendar schedules, Map navigation, and a 375px work-list layout.

Production deployment, remote adapters, work-order write/dispatch controls, and broader Map information-density improvements remain. Existing V1 assets and APIs are retained for compatibility; live operation routes use the new shell. This candidate has not been published or installed into the production service.

## Note action extension

Candidate .3 adds ordinary notes through the workspace-installed WorkLane handler, using its author identity and lifecycle validation. The bridge validates the registered project and resolved tracker path before writing. Lifecycle command markers are blocked in this note-only form. Dedicated approve/close/assign/dispatch actions remain unimplemented. Notes may now be written from the reader; other data views stay read-only. 134 Overview tests pass, including isolated real-engine and local-origin tests. Browser persistence/error tests used disposable records only.
