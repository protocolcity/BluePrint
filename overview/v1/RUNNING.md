# Running the BluePrint desk — dogfood steps (four-lens shell)

The desk server is dogfoodable stand-alone before it lands in the BluePrint
pip package. One path today: **local dev tree** via the tiny server.

`overview/v1/serve.py` mounts all four lenses on one origin — Overview
(landing MC), Map V1 dig, Calendar (week list), Settings (groups). Every
lens chip in the top nav is a real page; no dead pills, no 404.

CLI session handoff: see [`docs/CLI_HANDOFF.md`](../../docs/CLI_HANDOFF.md).

## Local dev tree

```bash
# from the BluePrint repo root
python3 overview/v1/serve.py --port 8803 --binder ~/BluePrint
# → http://127.0.0.1:8803/          Overview
# → http://127.0.0.1:8803/map       Map V1 dig (same binder)
# → http://127.0.0.1:8803/calendar  Calendar week list
# → http://127.0.0.1:8803/settings  Settings groups
```

`--binder DIR` is optional. Without it the desk still boots on all four
lenses; Overview / Calendar / Map paint honest empty. With it the desk
also reads `<binder>/.blueprint/overview.json` and
`<binder>/.blueprint/calendar.json` (both optional) to seed local truth.

Both files are read live: the desk stats them per request and re-parses only
when they change, so editing `<binder>/.blueprint/overview.json` shows up on
the next refresh with no server bounce. A missing or malformed file paints
honest empty. `--fixture` stays boot-pinned (tests / demo).

Then in the browser:

1. **DoD 1 — landing paints three equal tiles + Local desk banner + hand-off
   chips.** The `Local desk` pill sits top-left. Three equal-width tiles
   (Agents · Jobs · Pulse) fill the row. The `Map` · `Calendar` · `Settings`
   chips sit at the foot. Dark PC desk background (`#0f1114` family).
2. **DoD 2 — honest empty with Writer copy.** Agents reads `No agents`. Jobs
   reads `No open jobs`. Pulse is silent (empty tick track). No shimmer, no
   spinner, no fabricated rows.
3. **DoD 3 — APIs return local-only JSON.** `curl` the three routes:
   ```bash
   curl -s http://127.0.0.1:8803/api/overview/agents  # {"agents": []}
   curl -s http://127.0.0.1:8803/api/overview/jobs    # {"jobs": []}
   curl -s http://127.0.0.1:8803/api/overview/pulse   # {"ticks": [], "last_at": null}
   ```
4. **DoD 4 — focus ring + dark desk.** Tab through the chips. Each stops
   with the same 2px yellow ring; the desk stays dark.
5. **DoD 5 — no Map verbs in chrome.** Nothing in the paint says `dig`,
   `lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, or `crumb`. The
   banner says `Local desk`, never `workspace`. The chip says `Map`,
   never `Dig here`.

## Calendar + Settings glass DoD

Against [`OVERVIEW_CALENDAR_SETTINGS.md`](../../docs/specs/OVERVIEW_CALENDAR_SETTINGS.md).
Mini dogfood uses `--binder example_user` on `:8803`. Missing
`<binder>/.blueprint/calendar.json` is the honest-empty Calendar (this desk
has no events until local truth is planted).

### Calendar — `http://127.0.0.1:8803/calendar`

1. Four-lens nav live — Calendar is the current lens (`aria-current="page"`).
2. Empty paints **`No events`**. No shimmer, no spinner, no fabricated rows.
3. Populated rows (when `calendar.json` is present) show **title · when ·
   source · status**. Source ∈ `routine` · `WO` · `manual`; status ∈
   `scheduled` · `due` · `done`. Shape: `overview/v1/tests/fixtures/calendar.json`.
4. Dark PC desk (`#0f1114` family) — no cream.
5. No Map verbs (`dig` · `lot` · `hub` · `fan` · `trail` · `md-viewer` ·
   `crumb`) and no Wall feed.

### Settings — `http://127.0.0.1:8803/settings`

1. Four-lens nav live — Settings is the current lens.
2. Four groups in order: **Desk · Appearance · Privacy/Local-only · About/Cellar**.
3. About/Cellar shows the brew-face Cellar tip (from `/api/overview/pulse`),
   never a private ProtocolCity SHA. HTML cold-empty until JS is a parked nit.
4. Dark PC only — Appearance reads **Dark PC**, no cream toggle.
5. No Overview tile duplication (no Agents · Jobs · Pulse tiles) and no Wall.

Shared pulse footer (`All systems quiet`) is desk chrome, not an Overview tile.

## Dogfood the populated fixture (tests / demo only)

The default serve is honest-empty; that's the correct paint per
[`OVERVIEW_INTENT.md`](../../docs/specs/OVERVIEW_INTENT.md) §Dogfood note.
To visualize what the tiles look like when real local truth arrives:

```bash
python3 overview/v1/serve.py --port 8803 \
    --fixture overview/v1/tests/fixtures/populated.json
```

That fixture paints four agents (idle · working · error · off), two open
jobs, and two pulse ticks with a `last_at`. Never wire a fixture into a
real serve; the pip package landing must stay empty until local truth is
wired.

## Dogfood the demo-worker-only fixture (regression pin)

```bash
python3 overview/v1/serve.py --port 8803 \
    --fixture overview/v1/tests/fixtures/demo_worker_only.json
```

Agents tile must **still** paint `No agents` — `demo-worker` on the
registry with no real employed event is not evidence the desk is
working. If a busy row appears, the peel has broken INTENT invariant #4.

## Tests

```bash
# preferred — pytest picks up both files
pytest overview/v1/tests -v

# or stdlib
python3 -m unittest discover -s overview/v1/tests -v
```

The suite runs in <2s and covers:

- Server truth stubs — honest-empty default, fixture loading, wire shape,
  the `demo-worker` invariant.
- End-to-end HTTP — the three V1 endpoints against a live
  ThreadingHTTPServer + the HTML lock (Writer copy, `Local desk`, no
  `workspace`, no Map verbs).
- Calendar + Settings glass DoD — `No events` empty, populated
  title · when · source · status, Settings group order, brew-face Cellar
  tip, no Map verbs, no Overview tile duplication.

If `test_serve_api::test_overview_html_never_speaks_map_verbs` fails, the
shell has drifted from the label lock — either fix the copy or amend
[`OVERVIEW_INTENT.md`](../../docs/specs/OVERVIEW_INTENT.md) §Label lock
and update the test.

## What to do when a peel breaks a row

1. Revert the peel; V1 rows are law until the shell is called done.
2. Open the row's DoD note in
   [`OVERVIEW_V1_GLASS.md`](../../docs/specs/OVERVIEW_V1_GLASS.md)
   §Definition of Done and confirm which row regressed.
3. Move the offending module back to §Later until the peel is
   redesigned.

## Non-goals when running

- Do **not** point the shell at a cloud-ops feed. Local-only honesty is
  load-bearing; the tiles paint what this desk sees on this machine or
  they paint empty.
- Do **not** wire in the pre-V1 landing surface (Wall-shaped `.html`
  face with come-back stacks). That surface is not in this shell; if you
  find yourself importing it you are on a different peel.
- Do **not** touch `map/v1/` (its files, tests, or the standalone `:8801`
  server) from this peel. The four-lens shell only *reads* the map
  projector and static assets — never edits them.

## Phase-B local projectors (Agents / Jobs)

When ``--binder DIR`` is set and ``<binder>/.blueprint/overview.json`` is
**absent**, Overview Agents / Jobs project from local Mini feeds:

- Agents: ``<binder>/.protocolcity/workforce/local/roster.json``
  (twin ``<binder>/workforce/local/roster.json``). Optional ``daemon.json``
  in the same dir polishes idle/working from ``in_flight`` — it never adds seats.
- Jobs: Desk HTTP ``http://127.0.0.1:8799`` (short timeout) or SQLite under
  ``<binder>/worklane/worklane/local/data/<slug>.db``.

Missing stores stay honest-empty. Planted ``overview.json`` still wins.
Cellar tip stays the boot-pinned brew face.

## LaunchAgent / always-on (macOS)

Phase-B Agents/Jobs projectors only run when the desk is started with
`--binder DIR`. A LaunchAgent (or login wrapper) that runs plain
`blueprint-overview` with **no** `--binder` will paint honest-empty Agents/Jobs
even when WorkForce/WorkLane stores exist under the binder.

Dogfood always-on Overview with local truth:

```bash
blueprint-overview --binder <your-binder-dir> --port 8803
```

Map's LaunchAgent already passes `--binder`; keep Overview's agent in the same
shape. Without `--binder`, Overview still boots (four lenses + brew Cellar tip)
— it just has no local Agents/Jobs feed to project.
