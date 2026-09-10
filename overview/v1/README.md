# Overview V1 — Mission Control shell

> **Status:** peel shell · not wired into the pip package yet · dogfoodable
> stand-alone via `serve.py`.

Overview V1 is the **Mission Control glass for the BluePrint desk** — the
landing lens. Three equal tiles (agents · jobs · pulse), a `Local desk`
honesty banner, and quiet hand-off chips to Map · Calendar · Settings.
Honestly empty by default; every number traces to a local truth source
on this machine.

Overview is **not** Map. Overview never borrows Map's verbs (`dig`,
`lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, `crumb`). If a
proposed surface wants those words, it belongs on Map.

Design papers: [`docs/specs/OVERVIEW_INTENT.md`](../../docs/specs/OVERVIEW_INTENT.md)
· [`OVERVIEW_THEME.md`](../../docs/specs/OVERVIEW_THEME.md)
· [`OVERVIEW_GAP.md`](../../docs/specs/OVERVIEW_GAP.md)
· [`OVERVIEW_V1_GLASS.md`](../../docs/specs/OVERVIEW_V1_GLASS.md) (DoD ladder).

## What ships in this shell

| Row | V1 rule (Glass) | Module |
|---|---|---|
| 1 | landing paints three equal tiles + `Local desk` banner + hand-off chips | `static/overview.html` + `static/css/overview.css` |
| 2 | honest empty with Writer copy | `static/overview.html` (initial paint) + `paintAgents/paintJobs/paintPulse` |
| 3 | APIs return local-only JSON | `server/overview_state.py` + `serve.py` |
| 4 | focus ring + dark PC desk | `static/css/overview.css` (`--ov-focus`, `--ov-bg`) |
| 5 | no Map verbs in chrome | Locked by `tests/test_serve_api.py` |

Nothing else lives in V1. See [`docs/specs/OVERVIEW_V1_GLASS.md`](../../docs/specs/OVERVIEW_V1_GLASS.md)
§Later for the held list — every row on that list is a future peel that
only opens against a green V1 base.

## Layout

```
overview/v1/
├── README.md                  ← this file
├── RUNNING.md                 ← how to dogfood the shell
├── serve.py                   ← tiny stand-alone dogfood server
├── server/
│   ├── __init__.py
│   └── overview_state.py      ← local-only truth stubs (agents/jobs/pulse)
├── static/
│   ├── overview.html
│   ├── css/overview.css
│   └── js/overview.v1.js      ← thin host: paintAgents / paintJobs / paintPulse
└── tests/
    ├── fixtures/
    │   ├── empty.json          ← honest-empty default
    │   ├── demo_worker_only.json  ← demo-worker alone → paints `No agents`
    │   └── populated.json      ← real agents + jobs + ticks
    ├── test_overview_state.py  ← wire-shape + dogfood invariants
    └── test_serve_api.py       ← end-to-end HTTP + HTML lock
```

## Usage

```bash
# from the BluePrint repo root
python3 overview/v1/serve.py --port 8803
# → http://127.0.0.1:8803/  (overview.html)
```

Default serve is honest-empty (`No agents` · `No open jobs` · silent
pulse). That is the correct paint per
[`OVERVIEW_INTENT.md`](../../docs/specs/OVERVIEW_INTENT.md) §Dogfood note;
zeros PASS.

For tests / manual demo you can pass a fixture:

```bash
python3 overview/v1/serve.py --port 8803 --fixture overview/v1/tests/fixtures/populated.json
```

The `--fixture` flag is intentionally not part of the pip-package serve;
the default landing on Overview is empty until real local truth is wired.

## Local-only APIs

| Route | Body |
|---|---|
| `GET /api/overview/agents` | `{"agents": [{"name": "...", "state": "idle|working|error|off"}]}` |
| `GET /api/overview/jobs`   | `{"jobs": [{"name": "...", "state": "..."}]}` |
| `GET /api/overview/pulse`  | `{"ticks": [{"at": "...", "label": "..."}], "last_at": null|str}` |
| `GET /`                    | `overview.html` |
| `GET /<static>`            | `static/…` assets |

Every payload is JSON; every truth source is on this machine.

## What is NOT in this shell (say-so)

- **No workspace author.** Overview never says `workspace` — the banner
  is `Local desk`. Found / adopt / hire live in the CLI.
- **No live event bus.** No SSE, no polling loop, no fabricated pulse.
- **No come-back stack, cinema, or Wall-style feed.** V1 legibility with
  zero live inputs.
- **No Map JS changes.** This peel does not touch `map/v1/` or `:8801`.
- **No Design tokens outside the four THEME classes** (Surface · Voice ·
  State · Focus). Anything else is a spec gap back to the Design room.

## Consuming from the BluePrint pip package

When the pip package (`protocolcity-blueprint`) ships its own BFF mount
for these routes, it should:

1. Vendor `overview/v1/server/overview_state.py` (or re-implement its
   three `load_*` functions).
2. Mount three routes:
   - `GET /api/overview/agents` → `load_agents(state)`
   - `GET /api/overview/jobs` → `load_jobs(state)`
   - `GET /api/overview/pulse` → `load_pulse(state)`
3. Serve `overview/v1/static/` at `/` (matching the URL called out here).

The shell hard-codes no origin — every fetch is relative. `boot({fetcher,
endpoints})` in `static/js/overview.v1.js` is the override seam for
tests and non-standard mounts.

## Design law

- One landing lens.
- One `Local desk` banner (exact string).
- One 2px focus ring shared across every interactive element.
- Three equal tiles (agents · jobs · pulse) — no dominant tile, no
  fourth tile.
- Pulse is discrete: ticks paint once on load, never animate.
- Empty is real: Writer copy, never shimmer.
