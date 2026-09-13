# Surfaces review — September 2026 (design pass, step 2)

Status: audit for pc-1461, written 2026-09-13 against installed 0.1.47+consolidation.29. Companion records: [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md) (accepted behaviour), [OVERVIEW_INTENT.md](OVERVIEW_INTENT.md) and [OVERVIEW_THEME.md](OVERVIEW_THEME.md) (voice and paint), [SUITE_VOCABULARY.md](SUITE_VOCABULARY.md) (words), [AGENTS_INTENT.md](AGENTS_INTENT.md) and [ACTIVITY_INTENT.md](ACTIVITY_INTENT.md) (new records). This paper changes no code; it records what each surface is for, what it reads, and where it falls short, so implementation orders can be filed with acceptance.

## Design read

Product operations dashboard for one operator (You) and the agents that work for them; dark PC desk register; Mission Control voice. Dials: variance 4, density 6, motion 2. Mode: preserve and evolve. Nothing here authorises a palette, navigation-shape or type change.

## Method

Every surface was read from the running app and its source (serve routes, the JavaScript that paints it, the projection it calls). Every internal link on all nine pages was crawled: 18 unique targets, all 200 after the calendar export fix (pc-1462). Engine facts were checked against the WorkForce and WorkLane APIs directly.

## Cross-cutting findings

1. **Refresh model.** Every surface polls `/api/operations` every 15 seconds while visible (Settings lets you change the interval); Map reads once per navigation; Activity polls GitHub every two minutes through a server cache. There is no push. An engine write is visible after up to 15 seconds and never on Map without a reload. This is why the desk never feels live.
2. **Five surfaces have no design record.** Overview and Map have intent, theme and glass papers. Work, Projects, Agents, Activity and Connections were built from the operations design's one-paragraph definitions. Their gaps below are the direct result.
3. **Registry versus runtime is still blurred on the numbers.** "Agents & jobs 12" on Overview counts roster rows; Agents mixes three scheduled report jobs, six manual seats, three manual review jobs and the supervisor job in one grid with identical cards.
4. **Personal and product work share one inbox.** For You and Work interleave home-network and career items with product decisions. That is correct for one desk, but nothing lets you see one project's attention alone without leaving Overview.
5. **Deferred and tracking work dominates lists.** 88 of 126 open orders are parked or umbrellas; Work shows them in the same list as actionable orders with a thin bar label.
6. **Vocabulary is consistent** across surfaces (work order, project, Agent, Job, You, For You, Deferred). The brand skill was stale (cream register, retired seats) and has been refreshed.

## Per-surface audit

| Surface | Accepted purpose | Reads | What works | Missing or broken |
|---|---|---|---|---|
| Overview | Mission Control glass: what needs you, what is moving, what the desk can verify | `/api/operations`: orders, projects, agents, sources, work dates | Honest source status; For You with faces and mute; project cards; workspace search | "Needs you" (10) and For You (8 Decide) disagree because Read items are counted but not shown by default; "In progress 3" counts status not activity; "Agents & jobs" is a registry count; no "what changed since you last looked"; no per-project attention filter |
| Work | Find an open order, see context, read history | same snapshot; reader at `/work-order` | Search, project/assignment/status filters, pagination, reader with notes | Flat list of 126 with deferred/tracking inline; no grouping by project or face; no claim/seat state on the row (who holds it, shift open); gate note truncated with no expansion; no "updated since" ordering choice |
| Projects | Registered stores | projects summary | Twelve cards, open and attention counts, links to work and papers | No last-activity time, no seats per project, no paper count, no store health beyond available; card grid gives every project equal weight |
| Agents | Registry membership versus fresh runtime evidence | roster, daemon, ledger (open shift since pc-1458), job reports | Truthful state, shift line with candidates and lock, dispatch action, deterministic report summaries | Jobs and seats undifferentiated; no supervisor passes (`/api/supervisor` exists since WorkForce .7); no recovery attempts; last-run error has no reason link or evidence path; no operator next action; twelve identical cards with no hierarchy |
| Activity | Repository delivery evidence | GitHub open PRs, last 8 workflow runs, latest release, per allowlisted repo | Honest labelling, connected state, observed time | Named as a feed but is a CI list; merged PRs and commits invisible; quiet repos look dead; nothing from WorkLane, WorkForce or supervisor; see ACTIVITY_INTENT |
| Map | Place and inventory: projects, folders, papers, reader | map tree, projects, papers, workspace work summary | Radial layout, folder list, papers reader, breadcrumbs, search | Nodes carry no state (open, attention, working); sidebar summary is text only; no live update; radial order is arbitrary; "View" and "Workspace" controls unexplained |
| Calendar | Agent schedules and dated work with sources visible | work dates, WorkForce next runs, local calendar file | Dated work with faces, next scheduled runs, subscribe link (fixed) | Manual seats listed as "not scheduled" add nine empty rows; due and hold-until for the same order appear as two rows; no month or week view; local calendar "not configured" with no way to configure |
| Connections | Where information comes from and how current it is | sources, excluded stores, GitHub, build | Honest, complete, readable | Missing engine versions (WorkLane, WorkForce installed builds), supervisor last pass, WorkLane API reachability; excluded-store list is a wall of text |
| Settings | Browser display preferences and running build | local storage, build identity | Simple and honest | Refresh interval becomes moot with a change feed; no place for the operator stop file or supervisor scope (those are host config, so probably right to leave out) |

## The live model (decision D2)

Option A, keep polling: no change, at most 15 seconds stale, Map static.

Option B, change feed: BluePrint watches what it already reads (the twelve WorkLane store files, the WorkForce daemon file, ledger directory and supervisor reports) and publishes one server-sent event `changed` with the source and observation time when any of them changes. Pages re-read their projection on that event and keep the poll as a fallback at a long interval. Map subscribes too and repaints node state. No engine change, no orchestration, no synthetic ticks: an event is only ever emitted after a real file change. Recommended.

## Decisions for the user

- D1 Activity: rename to what it is (Delivery) now, or design the joined timeline; see ACTIVITY_INTENT.
- D2 Live: change feed (option B) or keep polling.
- D3 Work default: hide deferred and tracking by default with a visible count and toggle.
- D4 Map nodes: read-only state badges (open, needs you, working) from the same projection.
- D5 Agents: accept AGENTS_INTENT hierarchy (seats, jobs, supervisor as three groups).

## Implementation order (after decisions)

1. Change feed (D2) in BP: one endpoint, one client hook, Map included.
2. Agents per AGENTS_INTENT (D5), including supervisor panel from `/api/supervisor`.
3. Work list defaults and row state (D3), Overview count definitions.
4. Activity per D1.
5. Map node state (D4), Calendar row cleanup, Connections engine versions.

Each becomes a protocolcity order with acceptance and tests; engine-side evidence gaps found while implementing go to workforce or worklane orders.
