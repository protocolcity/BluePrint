# Running the BluePrint desk — dogfood steps (four-lens shell)

The desk server is dogfoodable stand-alone before it lands in the BluePrint
pip package. One path today: **local dev tree** via the tiny server.

`overview/v1/serve.py` mounts all four lenses on one origin — Overview
(landing MC), Map V1 dig, Calendar (week list), Settings (groups). Every
lens chip in the top nav is a real page; no dead pills, no 404.

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
