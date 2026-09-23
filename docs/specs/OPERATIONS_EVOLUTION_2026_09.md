# BluePrint operations interface

Status: current operations design. [The product contract](../PRODUCT.md) owns
positioning and capability boundaries; [architecture](../../ARCHITECTURE.md)
owns component responsibilities. Earlier Map-only interaction recipes are
historical references, not current restrictions.

## Information and actions

The application presents the explicitly selected workspace's projects, work
orders, instructions, agents, schedules and sources in one origin. Overview
prioritizes human attention. Work provides scoped search/filtering and a reader
with description, comments, evidence and supported actions. Projects groups
registered projects and papers. Agents separates registration, dispatch, claim
and observed execution. Delivery and Timeline label their evidence sources.
Calendar distinguishes scheduled runs, work dates and optional supplied events.
Connections explains missing sources and excluded stores. Settings exposes
working display preferences and responding build identity.

WorkLane owns writes; actions require explicit project/store identity and record
version. WorkForce owns dispatch and refusal reasons. An assignment is not a
run; accepted dispatch is not a claim; claimed work is not a completed or
installed result. Current remote execution is unconnected. The workspace
disclosure is not a switch that grants cloud access.

## State and interaction

- Count registered stores only. Explain excluded/unavailable sources without
  reading another workspace, treating failure as empty, or deleting data.
- Distinguish unavailable, stale, empty and healthy observations. Preserve last
  successful data and its age when a refresh fails.
- Refresh while visible according to the saved interval/manual preference;
  avoid overlapping requests and rapid failure retries.
- Keep human decisions, requested reading, watch items and personal notes
  distinct. Timer gates are embargoes; reminder dates and browser-local mutes
  do not change ownership or execution authority.
- Render work and document content as untrusted text or escaped Markdown.
  Browser writes retain local-origin and action-header protections.
- Preserve project, filters and reader context after actions and errors. Respect
  reduced motion; animate interactions and content arrival without synthetic
  agent activity.

## Map and papers

Map and the keyboard-accessible folder/paper list address the same projects and
instructions. Opening a folder replaces the visible level; breadcrumbs return
to the parent. Bounded spatial pages retain the complete readable list, including
at narrow widths. Labels remain visible, and keyboard activation works without
hover. Readers focus the close control and restore originating focus.

Project papers are grouped by Product, System, Operations and Development.
Navigation does not confer authority or public exposure. Preserve original
paper names and keep cold reader links useful through a local fallback route.
Historical theater and parallel projections must not be restored as apparent
live execution.

## Execution and operation

Schedules and automation exist only where an installation explicitly configures
and verifies them in WorkForce. BP ships no claim that a private host's
supervisor, integrator or reporting job is installed everywhere. Each configured
job supplies identity, trigger, scope, budget and dated execution evidence.
Empty queues stop. Failed runs retain their reason and artifacts.

Build identity comes from the responding installed package and deployment
receipt. Ports and service configuration belong to that installation. Source
changes are not deployed results. See [deployment and recovery](../operations/DEPLOYMENT.md)
for staging, activation and data preservation. Starting BP never hires workers
or upgrades independent business runtimes.

## Verification

Use disposable workspaces for engine action/origin/store refusal tests, browser
navigation/readers, unavailable/stale-source behavior and install/upgrade/recovery
checks. Use fake providers in ordinary CI and bounded live qualification
separately. A passing mirror check verifies configuration parity, not provider
capacity or unattended execution. Host receipts and private test histories stay
outside distributable product documents.
