# Map V1 — thin glass shell

> **Status:** peel shell · not wired into the pip package yet · dogfoodable
> stand-alone via `serve.py`.

Map V1 is a **coordination glass over a folder**. The workspace's file tree
(filesystem + git) is the truth; the shell projects that truth spatially so
you can dig into folders, read `.md` files, and route work. It is **not** a
workspace creator — found / adopt / hire live in the CLI, not in Map paint.

Design papers: [`docs/specs/MAP_V1_GLASS.md`](../../docs/specs/MAP_V1_GLASS.md)
· [`MAP_V1_GAP.md`](../../docs/specs/MAP_V1_GAP.md)
· [`MAP_V1_RECOMMENDATION.md`](../../docs/specs/MAP_V1_RECOMMENDATION.md).

## What ships in this shell

| Row | V1 rule (Glass) | Module |
|---|---|---|
| 1 | hub + top-level lots paint on cold boot | `static/js/map-paint.js` + `server/map_tree.py` |
| 2 | empty pan · zoom · reset (snap, no easing) | `static/js/workspace_map_app.v1.js` |
| 3 | dig on lot / hub / dig-in child | `workspace_map_app.v1.js` + `map-tree.js` |
| 4 | in-shell `.md` reader overlay | `static/js/md-viewer.js` + `server/map_tree.render_file` |
| 5 | View Options filter (managed · unmanaged · hidden) | `static/js/view-state.js` |
| 6 | Hit-Layer SoT (one router, six rows) | `static/js/map-hit-router.js` |

Nothing else lives in V1. See [MAP_V1_GAP.md §Chrome-until-dig quarantine](../../docs/specs/MAP_V1_GAP.md#chrome-until-dig-quarantine-list)
for the full DEFERred list — every row on that list is a Later peel that only
opens against a green V1 base.

## Layout

```
map/v1/
├── README.md                  ← this file
├── RUNNING.md                 ← how to dogfood the shell
├── serve.py                   ← tiny stand-alone dogfood server
├── server/
│   ├── __init__.py
│   └── map_tree.py            ← FS/git binder projection + reader render
├── static/
│   ├── workspace_map.html
│   ├── css/workspace_map.css
│   └── js/
│       ├── workspace_map_app.v1.js    ← thin host (~250 LOC)
│       ├── map-tree.js                ← snapshot reader (client)
│       ├── map-paint.js               ← pure SVG paint
│       ├── map-hit-router.js          ← Hit-Layer SoT
│       ├── md-viewer.js               ← reader overlay
│       └── view-state.js              ← MapViewState (single store)
└── tests/
    ├── fixtures/binder-01/            ← smoke fixture (hub.md + 3 lots)
    ├── test_map_tree.py               ← server projection tests
    ├── test_hit_router_table.py       ← locks 6-row hit order in JS
    └── test_dig_smoke.py              ← DoD 1-4 smoke against fixture
```

## What is NOT in this shell (say-so)

- **No workspace author.** Found / adopt / seed-ops stay in the CLI.
- **No 28k-line host.** The V1 host is ~250 LOC; if it climbs past ~2k it
  has drifted.
- **No FAST porch, folder seats, agents rail, WO tape, inspect-\*, city
  overlay.** All DEFERred. Each re-add is a peel that must cite which V1
  row it must not regress.
- **No second projection (Outline).** Deviates from earlier V1 intent (see
  the Glass doc's §Note on Outline). If Outline stays in V1 it becomes a
  toggle on the same `MapViewState`, not a second store.

## Consuming from the BluePrint pip package

`serve.py` is the standalone dogfood path. When the BluePrint pip package
(`protocolcity-blueprint`) is ready to serve the shell, it should:

1. Vendor `map/v1/server/map_tree.py` (or re-implement its four functions
   in the BluePrint BFF).
2. Mount three routes:
   - `GET /api/map/tree` → `build_tree(binder_root)`
   - `GET /api/map/children?relPath=…` → `children_at(binder_root, relPath)`
   - `GET /api/file?path=…&render=html` → `render_file(binder_root, path)`
3. Serve `map/v1/static/` at `/workspace-map` (matching the URL called out
   in `README.md`).

The shell hard-codes no origin — every fetch is relative. Overriding
endpoints or the fetcher is supported via the `boot({fetcher, endpoints})`
arg for tests and non-standard mounts.

## Design law

- One binder per Map instance.
- One `MapViewState` store.
- One hit router (six rows, in the fixed order tested by
  `tests/test_hit_router_table.py`).
- Paint stack in the fixed order: `lots · hub · dig-in-layer ·
  md-viewer-layer · chrome-layer`.
- No cinema, no live loop, no seat pack, no gold beats in V1.
