# Map V1 Gap — KEEP / REWRITE / DELETE / NEW

**Status:** DRAFT · design-first · pairs with [`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md).
Inventory reflects `suite/map/` at tip (49c1591; dogfood glass = FAIL for
dig / WO / Outline) and its thin server hooks.

## Legend

| Verdict | Meaning |
|---|---|
| **KEEP** | Ship as-is in V1 with no functional change |
| **KEEP-TRIM** | Ship in V1 but strip surfaces / branches that only serve activity flags |
| **REWRITE** | Concept is right; current implementation is too coupled to fix in place |
| **DELETE** | Not in V1; module comes back Later (activity flags) or never |
| **DEFER** | Not deleted, not touched; parked behind a build flag until re-add |
| **NEW** | Module V1 needs that doesn't exist yet |

Two orthogonal peels here: the JS surface (`suite/map/`) and the thin BFF /
host hooks it depends on. Neither can be touched today per the READ-only
guard on this branch — this doc is design; peels open only after Eli GO.

## `suite/map/*` inventory

Numbers are current LOC (`wc -l`, 2026-09-10). "V1 role" is the row from
`MAP_V1_GLASS.md` the module maps to.

### Base map / paint

| File | LOC | Current role | V1 role | Verdict | Notes |
|---|---|---|---|---|---|
| `map-stack.js` | 98 | SVG layer order (`ensureMapStack`) | Paint stack order (§Paint stack) | **KEEP-TRIM** | Reduce `MAP_STACK_IDS` to `lots · hub · dig-in-layer · md-viewer-layer · chrome-layer` (drop fast-cover, folder-chrome, events, actors, links) |
| `map-soft.js` | 215 | Structure sigs + soft lot patches | Snapshot diff → repaint sig | **KEEP-TRIM** | Only paths + `is_dir` + `has_md` are load-bearing in V1; drop store overlay branches |
| `map-chrome-spec.js` | 854 | `FOLDER_SEAT_SPEC` · `WORK_SIGNAL_LADDER` · `CLICK_MATRIX` · `MAP_LEGEND_SPEC` | Just `CLICK_MATRIX` (single verb per object) | **REWRITE** | Split the spec: keep click intents, quarantine seat/legend/work-signal spec behind a flag |
| `map-fast.js` | 1492 | First-paint FAST porch + fast-cover | **out of V1** | **DEFER** | Coupling source for #13/#15/#16; do not delete yet (has performance work) |
| `map-folder-seats.js` | 638 | Interior seats on FAST ring | **out of V1** | **DEFER** | Later, first activity-flag re-add candidate |
| `map-view-chrome.js` | 792 | Legend · View options · Expand · Reset · Map\|Outline · dig trail | View options + Reset + dig trail only | **KEEP-TRIM** | Strip Legend, Expand FAB, projection toggle, showKind → LS complexity |

### Dig / projection / state

| File | LOC | Current role | V1 role | Verdict | Notes |
|---|---|---|---|---|---|
| `view-state.js` | 250 | `MapViewState` — one focus, expand, projection, custom order | Same, minus projection + custom order + layout API | **KEEP-TRIM** | Drop `setProjection` / order-persist fetch to `/api/map/layout` in V1 (comes back with Outline / Later) |
| `graph.js` | 215 | Dig tier classification, foundation dirs, `plotTopDirs`, depth ladder | `plotChildren(path)` — children under path | **REWRITE** | Reduce to two helpers: `topLots(binder)` and `childrenAt(relPath)` |
| `map-hit-router.js` | 398 | Hit-Layer SoT — 9 layers, 4 kinds | 6-row table (md-viewer · chrome · dig-in · hub · lots · empty) | **KEEP-TRIM** | Cut fast-cover / folder-chrome rows; simplify `classify` sweeps |
| `chrome.js` | 388 | Paper role classifier + law mark detection | **out of V1** | **DEFER** | Comes back with paper stack / instruction glyphs (Later) |

### Body panels / rails (all six inspects)

| File | LOC | V1 role | Verdict | Notes |
|---|---|---|---|---|
| `inspect-project.js` | 3423 | none | **DELETE** | Reader (`#md-viewer-layer`) is V1's only sidebar |
| `inspect-person.js` | 1131 | none | **DELETE** | Person page is a separate route (`/person`) |
| `inspect-you.js` | 1696 | none | **DELETE** | You card belongs to Overview lens, not Map |
| `inspect-workspace.js` | 751 | none | **DELETE** | Workspace inspect is Overview / Settings |
| `inspect-orbit.js` | 440 | none | **DELETE** | Orbit view is expand chrome |
| `inspect-shell.js` | 444 | none | **DELETE** | Shell scaffold for the above five |

**Total inspect LOC deleted: ~7,885** — bulk of the current map bundle.

### Activity streams (agents / WO / notices / live)

| File | LOC | V1 role | Verdict | Notes |
|---|---|---|---|---|
| `agents-panel.js` | 2912 | none | **DEFER** | Agent activities rail — first Later re-add |
| `wo-tape.js` | 4323 | none | **DEFER** | WO tape — second Later re-add |
| `wo-buckets.js` | 313 | none | **DEFER** | Shared bucket math for tape + folder counts |
| `folder-list.js` | 2538 | none | **DEFER** | Per-folder papers panel + hood list; supersedes reader in Later |
| `map-notices.js` | 163 | none | **DEFER** | Toast rail for tape events |
| `live.js` | 83 | none | **DELETE** | City-data overlay seam; no city-data poll in V1 |

### Host + CSS

| File | LOC | Verdict | Notes |
|---|---|---|---|
| `workspace_map_app.js` | 28485 | **REWRITE** | New V1 host ≤2k lines wiring snapshot → paint → dig → reader → HitRouter. The 28k host is where dig died at #13; a peel-in-place is a fifth stacked patch on a dead surface |
| `workspace_map.css` | 7426 | **KEEP-TRIM** | Preserve `#world` · `#lots` · `.map-hit` · corner-panel classes; delete `.map-tape*`, `.map-agents*`, `.map-wo-*`, seat classes; strip roughly 40% |
| `workspace_map.html` | 472 | **KEEP-TRIM** | Delete rail sections (`#map-mod-agents`, `#map-mod-wo`, `#map-outline`, `#map-skills`, theater demo dialog); drop half the preload / defer tags to match trimmed JS set |

### New files V1 needs

| File | Role | LOC est. |
|---|---|---|
| `map-tree.js` | Reads snapshot, returns `{binder, topLots, expandableAt(relPath)}` — replaces graph.js + parts of the host | ~200 |
| `map-paint.js` | Owns SVG paint: `paintHub`, `paintLots`, `paintDigIn`, `paintReset`. Pure — no state, no polling | ~500 |
| `md-viewer.js` | Overlay reader: mount, open(path), close, hit ownership | ~250 |
| `workspace_map_app.v1.js` | Thin host: boots snapshot fetch, mounts paint, wires HitRouter → dig / reader / pan | ~800 |

**Estimated V1 JS surface:** ~2.5k LOC hand-written + ~600 LOC KEEP-TRIM
of existing modules ≈ **3.1k LOC total**, vs 45.7k in shipped `suite/map/*.js`
today. Roughly a **93% cut**.

## Thin host / BFF hooks

Endpoints Map V1 needs from the server. Some exist; some need a lean new
endpoint that returns exactly what V1 paints (avoids trimming huge legacy
payloads client-side).

| Endpoint | Status today | V1 verdict | V1 shape |
|---|---|---|---|
| `/api/map/snapshot` | Exists — full snapshot with stores + scene + attention | **REWRITE** | Return only `{binder: {path, name}, lots: [{relPath, name, isDir, hasMd, managed, hidden}]}` for cold boot |
| `/api/city?light=1` | Exists — city with stores, roster, WO shape | **DELETE from Map** | Belongs to Overview; V1 must not fetch it |
| `/api/people?light=1` | Exists — roster | **DELETE from Map** | Overview / Agents rail (Later) |
| `/api/tp-scene` | Exists — WorkLane scene | **DELETE from Map** | WO tape (Later) |
| `/api/file?path=…` | Exists — file read | **KEEP** | Reader source; needs a `?render=html` mode for MD in V1 |
| `/api/ground?scope=…` | Exists — file listing | **REWRITE** | Rename / narrow to `/api/map/children?relPath=…` for dig fan |
| `/api/manage` · `/api/hidden` | Exists — write managed/hidden state | **KEEP** | View Options filter → server persist (V1 uses them via existing wire) |
| `/api/open` | Exists — Finder open | **KEEP** | ⌘-click escape hatch |
| `/api/map/layout` | Exists — custom ring order | **DEFER** | Layout customization comes back with density polish |
| `/api/seed-ops` · `/api/skip/*` · `/api/task/*` · `/api/stores/prefixes` · `/api/survey` | Exists | **DELETE from Map** | Not Map's job |

**Two new endpoints proposed** (each is a peel, not a slam):

| New endpoint | Shape | Replaces |
|---|---|---|
| `GET /api/map/tree` | `{binder, lots, git: {head, dirty}}` — depth-2, no city / no stores | fat `/api/map/snapshot` for V1 cold boot |
| `GET /api/map/children?relPath=…` | `{relPath, children: [{name, isDir, hasMd}]}` | client-side walk of `/api/ground` results |

Server work needed: ~a day per endpoint if the file walk already exists
(it does — `hood_root_mds`, `plotTopDirs` server variants).

## Chrome-until-dig quarantine list

These stay on disk during V1 (`DEFER`) but are wired **off** on cold boot.
Re-add is a flag flip + a peel per surface. Naming them here so no future
peel accidentally re-lands one before the six V1 rows hold green.

- FAST porch (`map-fast.js`)
- Folder interior seats (`map-folder-seats.js`)
- Interior seat spec, work signal ladder, legend spec (`map-chrome-spec.js` — split)
- Legend fab
- Expand FAB
- Dig-trail glyphs
- Outline projection (unless Eli overrides §Note in Glass doc)
- All six `inspect-*.js` sidebars
- Agents Activities rail (`agents-panel.js`)
- WO tape (`wo-tape.js`, `wo-buckets.js`, `folder-list.js`)
- City-data live overlay (`live.js`)
- Map notices toasts (`map-notices.js`)
- Searchlight (`map-searchlight.js` — suite root)
- Theater demo dialog (HTML block in `workspace_map.html`)
- Skills library corner panel (`#map-skills`)
- Cam / fit animations (host's `fitDigInCamera` easings)
- SSE tape · pulse · heartbeat · reconcile (host's live loop)

Each row on this list is a re-add candidate for a future peel — but only
after the six V1 rows have held green across two consecutive dogfood cycles.

## Summary counts

| Verdict | Files | LOC affected |
|---|---|---|
| KEEP | 1 | 388 (chrome.js — no, that's DEFER; actual KEEPs: /api/file, /api/manage, /api/hidden, /api/open — endpoints, not files) |
| KEEP-TRIM | 6 | ~9,700 → ~2,500 |
| REWRITE | 4 | ~30,000 → ~1,700 |
| DELETE | 7 | ~7,970 |
| DEFER | 9 | ~11,900 (frozen) |
| NEW | 4 | 0 → ~1,750 |

Net V1 JS surface ≈ **~6 KEEP-TRIM + 4 NEW modules, ~3k LOC**, down from
**24 shipped modules and ~46k LOC**.
