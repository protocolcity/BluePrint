# Overview V1 Glass — Mission Control Shell DoD Ladder

**Status:** DRAFT · peel companion to [`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md)
and [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md). Mirror shape of
[`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md), Mission Control voice throughout.
Names the peel order for the shell that dogfoods against `overview/v1/`.

## One sentence

**Overview V1 paints the landing lens as a quiet, dark PC desk** — three
equal tiles (agents · jobs · pulse), a `Local desk` honesty banner, and
three quiet hand-off chips (Map · Calendar · Settings). Honestly empty
by default; every number traces to a local truth source on this machine.

## Label lock (reminder)

Same vocabulary as INTENT · THEME. Overview never borrows Map's verbs
(`dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, `crumb`).
The banner says `Local desk`, **never** `workspace`. The chip says
`Map`, **never** `Dig here`.

## Paint surfaces (V1 lock)

Nothing else lands in V1.

| Surface | Owner (module) | Truth source |
|---|---|---|
| **Local-only honesty banner** — `Local desk` | `static/overview.html` (permanent header) | Constant affordance |
| **Agents tile** — state dots (idle · working · error · off) | `static/js/overview.v1.js paintAgents()` | `GET /api/overview/agents` |
| **Jobs tile** — one row per open job | `paintJobs()` | `GET /api/overview/jobs` |
| **Pulse tile** — one quiet tick line | `paintPulse()` | `GET /api/overview/pulse` |
| **Hand-off chips** — `Map` · `Calendar` · `Settings` | `static/overview.html` (footer nav) | Static links |

## Definition of Done (DoD)

Peel order is **land the landing first, quiet the empty, then wire the
APIs, then ring the focus, then guard the vocabulary** — one row at a
time, each verified before the next opens.

| Peel | Row | Done when |
|---|---|---|
| 1 | **Landing paints three equal tiles + Local desk banner + hand-off chips** | Cold boot renders the banner, three equal-width tiles, and the three chips on a dark PC desk (`#0f1114` family). No dominant tile, no fourth tile, no come-back stack. |
| 2 | **Honest empty with Writer copy** | Each tile paints its exact Writer string on empty: `No agents` · `No open jobs` · silent pulse (or `No pulse yet` if a string is required). No shimmer, no spinner, no synthesized rows. |
| 3 | **APIs return local-only JSON** | `GET /api/overview/{agents,jobs,pulse}` respond `200 application/json` with the V1-locked keys. Default serve is empty; `demo-worker` alone still paints `No agents`. |
| 4 | **Focus ring + dark desk** | Every interactive element (chips, banner, focusable tiles) shares one 2px focus ring (`--ov-focus`). No cream palette, no light-mode variant. |
| 5 | **No Map verbs in chrome** | HTML, CSS, JS, and any strings the shell paints contain zero occurrences of `dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, `crumb`. The chip says `Map`, never `Dig here`. |

All five rows hold before Overview V1 is called done. A row that regresses
to make room for an activity flag (come-back stack, cinema, fake pulse,
Map-lite tile, cloud-ops summary) fails V1 — file the flag under §Later.

## Later — held (mirror INTENT · THEME)

Each row is a re-add candidate for a future peel, only after V1 has held
green across two dogfood cycles and only if it does not regress an
invariant.

| Held | Where it belongs |
|---|---|
| Come-back stack, Wall-style feed, cinema | Not Overview — for-you inbox is a separate lens candidate |
| Fake / synthesized activity ticks | Never — local-only honesty is load-bearing |
| Map-lite tile · any dig verb on Overview | Map — see [`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md) |
| Roster fetched from a cloud service | Never — local truth source or no paint |
| Gold "for you" beats on the landing lens | For-you inbox (later lens candidate) |
| Light-mode palette | Later spec, not a V1 flip |
| Per-tile background tints, per-component focus experiments | Never — one Surface voice, one Focus voice |

## Non-goals (say-so)

- Overview V1 is not a router — the chips hand off, they do not embed
  Map / Calendar / Settings.
- Overview V1 is not a live event bus — no SSE, no polling loop, no
  heartbeat that fabricates activity.
- Overview V1 does not touch `map/v1/`. This peel is landing-lens only.
- Overview V1 does not invent Design tokens outside the four THEME
  classes (Surface · Voice · State · Focus). A missing token is a spec
  gap back to the Design room.

## Ship fence

- Peels open only against green V1 rows. A DoD row that regresses fails V1.
- No Cursor cloud agents; the shell is Claude CLI dogfood.
- The pip package (`protocolcity-blueprint`) vendors
  `overview/v1/server/overview_state.py` when its BFF mounts the three
  V1 routes; until then `overview/v1/serve.py` is the dogfood path.
