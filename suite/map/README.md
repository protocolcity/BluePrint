# suite/map/ — Workspace map modules (pc-372 · pc-604)

Split from the workspace map host (`workspace_map.html`, was `skin_demo.html`) as the continuous-live grammar freezes.

## Inventory (2026-07-28)

| Module | Role | Status |
|---|---|---|
| `map-soft.js` | Structure sigs + soft lot patches (no full SVG wipe) | **shipped** |
| `map-chrome-spec.js` | `FOLDER_SEAT_SPEC` · exterior name/attention · interior seats · shape/shedding · `MAP_LEGEND_SPEC` SoT | **shipped** (pc-604 / pc-864) |
| `graph.js` | Dig tier classification, foundation dirs, children@path (`MapGraph`) | **shipped** (pc-757) |
| `live.js` | City-data overlay seam for pollLight: clone + store-overlay (`MapLive`) | **shipped** (pc-757) |
| `chrome.js` | Law mark detection, paper role classification (`MapChrome`) | **shipped** (pc-757) |
| `map-paint.js` | Static SVG (lots, sectors, papers) | residual in host |
| `map-theater.js` | Filed/claimed/signed + trucks | residual in host |
| `map-motion.js` | Walk physics / placeActors / tick | residual in host |
| `map-chrome.js` | Rails, KPIs, inspect dock | residual in host |
| `../map-searchlight.js` | Search light overlay | **shipped** (suite root) |
| Host `workspace_map.html` | ~29k lines · CSS + paint + dig-in + WO rail | still primary |

Host page: `../workspace_map.html` (loads `map-soft.js` + `map-chrome-spec.js` then page script).

Further extraction: pure functions that do not close over page `svg`/`model`
next — prefer `folderChromeLayout` / `drawOrbitCluster` / WO desk cache after
animation soak freezes. Keep theater + tick coupled until QA freezes.

## Dual projection (pc-756 · pc-844)

One workspace truth, two Map projections. The shared modules (`graph.js` /
`live.js` / `chrome.js` / **`view-state.js`**) are the seam; each projection is a
**layout-only consumer** of the same focus, expand mode, live state, and chrome.

### `MapViewState` (pc-844) — one focus + expand

| Field | Meaning |
|---|---|
| `expandLevel` | 0 = project ring · 1 = ops layers open (Map minis **and** Outline rows) |
| `dig` | `{ plotSlug, plotName, relPath, trail }` or null at workspace hub |
| `projection` | `map` \| `outline` — layout only; does **not** own expand/dig |

Expand FAB and Outline collapse/expand both write `expandLevel`. Dig enter/exit
writes `dig`. Switching projection re-applies the same expand membership.

### Projections

| Projection | Layout | Status |
|---|---|---|
| **Spatial** | Exploded bubbles — hub + project ring + dig fan | primary (existing) |
| **Outline** | Finder-like tree — managed projects stack down, rows expand inline | pc-758 |

Exploded Map is primary. Outline is a **toggle view inside Map**, not a peer
door or a separate app (no new suite port, no Explorer sibling).

### Graph focus contract

`MapGraph` owns the topology vocabulary both projections reference; **live dig
path** is mirrored in `MapViewState.dig` (pc-844).

| Term | Meaning |
|---|---|
| `plot` | A managed project node — a folder with a join marker; the unit both projections center on |
| `path` | Active dig trail — ordered slug sequence from workspace root to current dig depth |
| `trail` | Trail depth — how many levels the current focus has entered (`path.length`) |

Key helpers: `plotTopDirs(plot)` (top child dirs for dig fan, capped 12),
`mapDepthClass(n)` / `mapDepthForDigChild(trail)` / `mapDepthForExpandChild()`
(depth ladder pc-774), `folderLayerClasses(name, mapDepth, trail)` (depth + weight),
`digTierClassForDir(name, trail)` (**secondary weight only** — foundation names),
`isDigFoundationDirName(name)` (law-bearing name check).

### Depth ladder (pc-774)

Build layers from the workspace root up — one order for expand, dig, fonts, mute:

| Depth | Nodes | CSS | Color axes |
|---|---|---|---|
| **0** | Workspace hub (OneSeo) | `map-depth-0` | Hub manila / YOU |
| **1** | Managed projects | `map-depth-1` | **Work fill + ring stroke** (status) |
| **2** | Project children (expand-all + dig at project root) | `map-depth-2` | Mute manila family; optional foundation weight |
| **3+** | Deeper dig | `map-depth-3`…`4` | Quieter same family |

### Dig literacy (pc-833)

While dig-in is open, Map teaches the same objects as Outline:

| Object | Map dig | Outline |
|---|---|---|
| Child place | Orbit folder | Nested row |
| Papers | Seat stack · click → one-level `filesHere` list | Papers chip / list md |
| Open work | Tab open# face = mark+digit (`!1` Stuck · `Y1` For You) + tooltip | Work chips with words |
| Dig focus name | One step larger type | Gold row |

Dig path strip carries a short legend: orbit = folders · stack = papers · tab # = work.

**Expand membership (pc-777):** `plotExpandDirs` prefers **foundation / BluePrint
layers** (docs, suite, scripts, .agents, …) — not every top-level disk folder.
Remainder is “+N more · dig in”. Expand stems dock to **mini glyph** half-box +
project manila ray-box (not `projectNodeGeom` on child load).

**Expand polish (pc-863/864):** minis use `folderGeomAtWidth(30)` — **not**
`projectNodeGeom` minWidth floors. Packing is sibling-first soft separate →
hub repel → home-orbit snap → angular sibling spread. Mini names exterior
above their shell. Project faces keep **all chrome inside** the manila
(title · attention · stacks — pc-865).

**Folder face (pc-865/869):** name + inventory stacks + For You **count** live
**inside** the silhouette. Tab is left-only (x≈2–18, y≈5–12) —
`openBadge` sits on the **tab lip** (right end of tab, not next to the title).
Gold/red manila fill = attention state; lip digit = how many. Scale is one
system in `FOLDER_INDICATOR_SPEC` — do not ratchet down.

`dig-tier-foundation` is a **weight boost** on depth ≥2 (gold edge), not a third
palette that fights project work/ring or paints expand differently from dig.

### LiveState soft fields (MapLive)

Both projections share the same light-poll path:

1. `cloneCityForStoreOverlay(city)` — shallow folder-level clone; avoids a
   full JSON deep-copy of the ~0.3–0.8 MB city on every 2.2 s heartbeat.
2. `overlayStoresFromScene(city, scene)` — merges tp-scene store counts onto
   the clone. Sets `f._storeFromScene = true` so sticky-preserve logic never
   freezes a closed queue. Key matching via `normHubKey` (slug / name / product,
   lower-cased, underscores → hyphens).

Neither projection fetches or mutates city state directly — they receive the
overlay result from the host's `pollLight` path.

### Chrome token set (MapChrome + MapGraph)

| Token | Source | Meaning |
|---|---|---|
| `fill` | `WORK_SIGNAL_LADDER` (host) | Work state colour: Needs You · Stuck · Flowing · Queued · Starved |
| `stroke` | host people scene | Folder edge: idle · approaching · live · fault |
| `seats` | `FOLDER_SEAT_SPEC` + `classifyPaperRole` | Agents bottom-left · jobs bottom-right · papers top-right |
| `depth` | `MapGraph.mapDepthClass` | Workspace→project→child→deep ladder (primary mute / type) |
| `tiers` | `MapGraph.digTierClassForDir` | foundation weight only (secondary; not a parallel palette) |
| `weight` | Outline-only | City attachment at path: active workers + managed child count (not disk bytes) |
| `flag` | Outline-only | Adopt / instruct / automate state at path (plant flag; drives row action affordance) |

`MapChrome` classifiers (`classifyPaperRole`, `classifyProjectPaper`,
`isRequiredPaper`, `isPcLawMd`) are shared verbatim by both projections.
Outline rows consume the same paper role stack as dig-in panel; no second
paper taxonomy.

### Children (pc-756 spine)

| Ticket | Hand | Scope |
|---|---|---|
| pc-757 | tom | Extract `MapGraph` + `MapLive` + `MapChrome` from host (done — graph.js / live.js / chrome.js shipped) |
| pc-758 | vera | Outline v1: Finder-like tree toggle (same dig trail) — implement after pc-757 settles |
| pc-759 | tom | Server map-bootstrap + attention perf |
| pc-760 | vera | Dig enter ease / multi-ring pad polish |
| pc-761 | tom | Developer hardcode hygiene |

## Performance budget (pc-604)

| Metric | Target | Notes |
|---|---|---|
| Host HTML size | trend down per extract | Soft-patch must not re-grow host |
| First paint Map shell | < 2s cold local | Suite glass :8801 |
| Soft pulse (placeActors reuse) | no full wipe on poll | `data-actor-sig` / seat sig |
| Soft poll interval | existing ~2s | Do not thrash soft reseat |

Smoke: suite viewer law tests + manual Map open after each extract.

## Suite = live viewer (pc-478 / pc-519)

Map is **glass** — it projects city truth. Capture (file / claim / close /
hire) is **chat + MCP / `wl`**. No ticket CRUD forms on ship Map — including
no File rail button, dig-in “File work order” door, or empty-CTA compose
path (pc-508 regressor removed by pc-519). Setup/ops controls (Join store,
seed-ops, DISPATCH NOW) stay. Inventory: `docs/specs/SUITE_VIEWER.md`.

Machine gate: `tests/test_suite_viewer_law.py` fails if Map reintroduces
create/claim/close forms or File-from-Map empty CTAs.

Theater origin for human-authored creates: WorkLane intake author+channel
(wl-250) when present — never a suite form.

## Legend (pc-481 · folder-as-node 2026-07-28 · pc-612 · legend v2 2026-07-31 · pc-915 lockstep)

Single source: `map-chrome-spec.js` → `WORK_SIGNAL_LADDER` +
`MAP_LEGEND_SPEC`; host `projectWorkSignal()` ranks the live evidence and
`renderMapLegend()` / `legendMapSymbol()` paint the key. Stack faces call the
same `get*Glyph` helpers as seats; Settings live-apply updates legend marks
via `softRefreshSeatGlyphs` (classes `leg-you` · `leg-hand` · `leg-job` ·
`leg-work-stack` · `leg-paper` · `leg-instr`). Any ticket that changes work /
presence / stack grammar updates the **spec file** in the same slice.

**One register for Map and Outline.** Every legend row means the same thing
on both projections. Map-only paint (folder-edge stroke idle · walk · live ·
fault) is stage chrome and stays **out** of the shared legend — fab title +
this section teach that; do not re-add ring swatches as a second taxonomy.

Channel charter: **soft gold = dig focus · solid gold chip = For You work ·
badge ladder = open urgency · stack = what’s attached · green = managed ·
blue = UI only**. A detail belongs to one channel; another channel may echo
the same state at a different zoom, but may not invent a second taxonomy.

| Row | Meaning (Map = Outline) |
|---|---|
| **Folder fill** | Mini manila swatches for the **work-signal ladder colors** on the folder face (gold / red / green / cream / pale). This is what citizens see as folder state — must stay lockstep with `.work-*` CSS washes. |
| **Work** | Worst-state-wins open ladder faces: **⭐ For You** → **❗ Stuck** → **▶️ In progress** → **◻ Ready** (neutral manila — not a digit sample) → **○ Empty queue**. Same ladder as Folder fill, emoji form for Outline lockstep. Live open pile is the work **seat** (🎫 default). |
| **Stacks** | L→R seats: **You** · **Hands** (agents) · **Jobs** · **Work orders** · **Papers** (📄 handbook) · **Instructions** (📜 own seat when law exists). Order mirrors Settings Faces hierarchy (pc-1075). Empty seats leave no hole (pack present only). |
| **Papers vs Instructions (pc-924 · option D)** | **Papers** = handbook only. **Instructions** = own interior seat 📜 (not a corner hit on papers). Click → law dig + door **“All instructions on board”**. Classifier SoT unchanged. |
| **placeState** | Canonical projector: `.signal` (WORK ladder) · `.presence` (ring) · `.wo` tallies · `.motion` (schedule-walk / working / fault). Map + dig KPIs read this; not legend rows. |
| **Live / job motion** | **ring-live** = hand or job working on the folder → green perimeter **stroke breath** + soft body wash (no CSS `filter` on `#lots`). **Jobs seat** opacity-ticks while the folder is live. **ring-walk** = dashed blue approach. Intentionally not legend rows (stage chrome). |
| **Intentionally out** | Edge stroke idle/walk/live/fault · dig soft-gold · managed grey · seat count digits (`badgeR`) · transient FX/actors. Stage / view chrome only. |

Signal derivation:

- **For You** — human-gated work exists (solid gold; not the soft You-here lip).
- **Stuck** — stalled work, a worker fault, or live-open work has no routed hand.
- **In progress** — a hand is working here now.
- **Ready** — routed work is waiting normally.
- **Empty queue** — a scheduled lane hand has nothing ready; hollow zero stays visible.

Badge doors use the same signal object: For You pile; Stuck → Stalled (or Live
for no-hand routing gaps); In progress; Ready.

**Paint stack** (`ensureMapStack`, pc-842/843): links → lots (manila + work fill) →
dig-in → expand → hub → `#folder-chrome-layer` (seats + open#, **always above
gold body**) → actors. Transient FX on `#events`.

**Hard rule (pc-843):** never put CSS `filter` on manila nodes in `#lots`
(selection, dig focus, rest-lift). SVG filter stacking promotes lots over
later chrome siblings → empty folders + dead seat hover. Selection = stroke;
seat hover = hit-pad + `.is-seat-hover` on chrome only.

Build/deepen: workspace lots first; seats on top; dig deepens without burying
seats. Work color loud on **tab**, soft on **body**.

**First paint For You (pc-834):** `/api/map-bootstrap` fans attention in
parallel with city light so gold / `Y#` / You chip are truthful on first paint
(not empty until soft poll).

## Folder anatomy v2 (pc-632)

Every persistent object has one interior dock on the shared 50×40 folder
coordinate system: work badge on the tab’s left end; name in the upper body;
papers top-right; agents bottom-left; jobs bottom-right. `FOLDER_SEAT_SPEC` is
the single source. Outside the silhouette is transient space only.

**Name/papers shared edge (pc-629):** the folder name owns a bounded
upper-left lane whose right edge reserves the complete top-right paper-stack
footprint. The label ellipsizes inside that lane instead of painting under the
stack. Seat glyphs also cap their scale to the vertical row gap, so a dense
folder with papers + agents + jobs keeps daylight between the top-right and
bottom-right seats. The paper seat does not move, and zero-paper folders still
reserve the lane boundary so a later soft paint cannot create a collision.

**Work-signal altitude (pc-659):** the work-order badge exists only where a
WorkLane store can exist: the workspace hub (aggregate) and managed project
ring. Dig-in child folders and expand-all shells never paint a work badge,
including a zero badge, because those filesystem depths cannot own work
orders. They keep their truthful per-folder paper stack/count and instruction
marks.

Folder geometry is load-scaled but proportion-locked: preferred aspect 1.25,
clamped to 1.20–1.50, width 36–108 world units. Objects scale down; they never
stretch the folder. Detail sheds by rendered folder width:

| Rendered width | Detail |
|---|---|
| ≥56 px | Full interior seats |
| 34–55 px | Work badge + paper stack |
| <34 px | Work badge + fill echo |

**You are here** is an **exterior gold glow** on the host folder
(`is-you-here`) — not a person chip inside the manila. Folder faces paint
interior inventory L→R: **you · work · papers · jobs · hands** (pc-891).
You seat = `suite.youGlyph` + per-project For You count (hide when 0).
Tab lip open# digit removed (pc-892); manila fill still signals work ladder. Default host is the
workspace hub; dig-in moves the glow to the focused project; prior levels
never keep a ghost You. Left-rail You card owns face options / For You.

## Vocabulary on the Map (pc-412 — ship truth)

Do **not** use Office · City Hall · cabinet · lane (as a place) on Map chrome.

| Map word | Means | Glyph |
|---|---|---|
| **You** | Human coordinator | Left-rail face card + soft gold host-folder glow |
| **Workspace** | Found/adopted root folder | Center folder badge |
| **Hand** | Project **worker** (roster `lane` / WF `worker`) — claims work orders | **Hand** sprite + persona first name |
| **Job** | Scheduled **duty** (roster `kind=job`) — function name, does not claim | **⏰** + function id |
| **Workspace jobs** | City-wide duties on hub ⏰ (ops) | Core seed-ops: chief-of-staff · health-patrol · workspace-efficiency · plus desk seams github-desk (public issues) · ship-desk (releases) when hired |

**Operating loop:** You + preferred AI **enter** → WorkLane **queues** →
WorkForce Agents/Jobs **work** → BluePrint Map **shows**. No coordinator seat
on the ring — protocol + You + entry AI route; Jobs patrol; Agents claim.

**Create path (pc-435):** hands → `blueprint hire <persona> --workdir <project>`;
workspace jobs → `blueprint seed-ops` (or `hire … --kind job`). Reserved function
ids refuse a default lane hire so agents do not invent a “health-patrol worker.”
| **Project** | Managed top-level folder sector | Folder + open count |
| **RULES** | `.md` papers (required gold vs other) | Paper marks |
| **HANDS** | Orbit where project hands park | Outer project ring |

**Papers (pc-410 / pc-423 / pc-629):** paper grammar is self-similar at every
visible folder depth. A folder paints exactly one stack when `.md` exists at
that folder's own level; zero-paper folders paint no stack, and a parent never
inherits or counts papers from its descendants. Stack depth may hint at one /
few / many papers, but numeric paper badges never paint—numbers live in the
papers panel (**pc-880 Option A**: Map 📄 = presence only; hands/jobs/work keep
legible inventory digits; 🎫 uses ticket-umber, not agent blue). At the smallest
detail tier the pile sheds to one paper mark
rather than disappearing. **Gold fold mark** = that level includes instruction papers
(`AGENTS.md`, `PERIMETER.md`, vendor pointers). **White** = handbook/other.
Clicking any stack opens the same per-folder papers panel as clicking its
folder. `folderPaperLevelScan()` is the shared source for Map presence,
instruction marking, sidebar counts, project-root stacks, dig-in children, and
Expand-folders level-1 shells, so those surfaces cannot disagree. Dig-in lists
**Required · law**, then role stacks (Skills · Architecture · Other), then
**subfolders** (one level—click opens that folder's papers panel, not a flat
dump of every nested file).

### Home routing (critical)

Workspace ops ring **only** when:

- sector `role === "staff"`, or
- hire id is a known function (`chief-of-staff` / `health-patrol` / `workspace-efficiency` + legacy aliases), or
- workdir under `.protocolcity/ops/`

**Never** treat workplace strings `"City Hall"` / `"Office"` as ops — WorkForce
still uses those labels for the ProtocolCity *project* sector; product hands
(riley, drew, codex) home on **ProtocolCity**, not the gold belt.

## Agent activities rail (pc-529 · card meta structure)

Left rail cards share one meta stack; **idle vs live** differ only in the
work line + LIVE badge (not a second title grammar):

| Line | Content | Notes |
|---|---|---|
| **Name** | Persona first name | STAFFING §1 — never the runtime binary |
| **Role** | `product · role` (product first) | pc-527 |
| **Payroll** | `model · <pin>` | Model pin for cost/debug; **never** bare `cli · model` (pc-529 — `claude`/`grok`/`codex` misread as titles) |
| **Status meta** | walk / peek only | idle · live · due omit this line (pc-474) |
| **Work** | LIVE claim teaser only | empty when idle (pc-526) |
| **Badge** | LIVE / due / idle pill | only state that flips with motion |

Tooltip on payroll: “payroll pin — not the worker’s name”. Runtime CLI may
still sit on the soft-poll row for debug; it is not rendered on Map cards.
Roster (`roster_v1.html`) may keep its own payroll grammar until retargeted.

## Dig-in and click grammar

> **Canonical SoT:** `suite/map/map-chrome-spec.js` → `CLICK_MATRIX` (pc-1086).
> Full matrix: every clickable object (folder face/name, interior seat badges
> 👤🎫📄📜⏰✋, stacks, pulse cells, KPI chips, pile chips, doors, outline chips)
> → what opens, Scan vs Full, ⌘-click escape. This section no longer maintains
> a partial duplicate.

Key invariants that remain law here:

- **One primary click per object.** Stacks (✋ ⏰ 📄 📜) open the right-rail
  list for their kind; never a mixed default.
- **⌘-click escapes to Full page** (Finder for folders · `/person` for hands ·
  `/ticket` for tape rows).
- **Map expand is not a primary path.** List-first family only.
- Work orders are **WorkLane store records** (not `.md` files). The Map projects
  them as the tape + folder open count + project Work orders list.

### One place overview (workspace + project)

Workspace hub dig and project dig share **one** grammar:

| Layer | Role |
|---|---|
| **Place pulse** | Only summary strip · **nav** (selected cell = body slice) |
| **Body** | **One slice** at a time: act · presence · work · jobs · structure · projects |
| **Left rails** | Full agent heat + WO stream (scoped when dig open) |
| **KPI chip row** | **Retired** on place digs (was a second copy of pulse) |

**Dig opens on** (Settings → Dig-in · `suite.mapDigOpenSlice`, default **Work**):
uniform first body for every place dig — Work · For You · Structure · Presence ·
Projects · Last pulse. Not context-smart (that confused founders).

**Dig filters left rails** (no Agent Activities “Elsewhere” fold — map selection is the filter).

**Open / Pin URL** is the same chrome on workspace and project digs (`suite.placeOpen.<key>`).

**Structure pulse** counts planted AGENTS/pointers/ARCHITECTURE at that place (must match dig body list — never “plant” while files are listed).

## Hierarchy default (pc-415 · founder 2026-07-25)

- **Workspace** = Finder folder hub; stems to **project folders** (level-anchored graph)
- Hands/jobs use the fixed **interior stacks** on each project folder
- Folder work colors follow the five-state `WORK_SIGNAL_LADDER`; the edge
  independently carries hand presence.
- Project click → **Finder dig-in** (root .md + hand papers + WO door)
- In Motion side list **hidden** in hierarchy (motion is on the bubbles)
- Soft path must **not** call polar `rebuildLotByKey` in hierarchy mode

Hierarchy only (pc-663) — bullseye / `suite.mapLayout` retired.

## Motion law (pc-632)

Motion means state changed. Idle agents remain in the bottom-left interior
stack. Approaching is the dashed folder border only—there is no roaming,
orbiting, bobbing, or queue-peek loop. On live start a transient hand travels
from outside to the interior agent seat and settles; on run end it leaves.
These transitions consume the existing people/SuiteLive refresh path and add
no polling loop. You presence changes by moving the soft gold host-folder
glow; it never creates a fourth face object.

Agent Activities rail: **hard partition** by heat
(`fail → live → peek → walk → due → idle`), then remaining time within a band.
**Approaching (walk/peek) always above Due (gold countdown).** Soft-patch only
when DOM shells still match that name/band order; band moves remount the list.
Schedule progress stays textual; the map does not animate it.

**Workspace (no dig):** on-shift seats open (walk before due); idle folded by
type once each (Agents · Staff · Jobs · Show). Header census = full roster.

**Dig open:** place groups (`On this project` / `Elsewhere`); idle-tier fold
CSS must not apply (`is-dig-roster`). Header census + badge = project seats
only (tooltip carries elsewhere + workspace total).

## Rail-coupled theater matrix (pc-466 / pc-467)

**Rails are first-class stage** (YOU card · Agent activities · Work orders) —
not spectators while geometry flies alone. Full inventory of WorkLane /
WorkForce verbs → rail beat + map echo:

→ [`docs/specs/MAP_THEATER_MATRIX.md`](../../docs/specs/MAP_THEATER_MATRIX.md)

Hero implement children: file theater (pc-468) · origins (pc-469) ·
cross-highlight (pc-470) · demo runbook (pc-471) · fault flash (pc-472).

## Continuous cinema (pc-392)

The Map is the ops verification stage. **We do run continuous cinema** —
not a second database, a continuous *projection*:

| Layer | Cadence | Role |
|---|---|---|
| rAF `tick` | ~60fps | Settle fixed targets and sanctioned transitions (no network) |
| SuitePulse | ~0.9s | Generation tokens → full bootstrap when truth moves |
| SSE tape | push | WorkLane transitions (tail-from-now, not full history dump) |
| Heartbeat | ~2.2s | Light poll: tp-scene + people + attention (counts/tape) |
| Reconcile | 60s | Missed tokens + re-arm SSE |

UI badge: **LIVE · cinema**. Why it used to feel “poll-only”: pulse alone +
historical SSE dump + sticky zero counts + no heartbeat. Those are fixed.

## Interaction (pc-382)

- One close control on inspect (×); **Esc** also closes when paper drawer closed
- Paper drawer: Esc / backdrop / × (SuitePaper)
- Doors = actions only, never a second Close

## Soft-update tiers (anti dual-color flash)

Root cause of the “two circle colors / full refresh” feel: **any hands
roster change used to call `paintStatic()`**, wiping sector SVG and redrawing
washes — even when the plot pie was identical.

| Tier | When | What runs |
|---|---|---|
| 1 | Plot slugs + hands + working + queue same | Patch times / open counts / live green |
| 2 | Plot slugs same; hands or working change | `placeActors` / soft re-seat only — **no paintStatic** |
| 3 | Plot slug set changes | `paintStatic` + `placeActors` (rare) |

**pc-477 (post-refresh seat settle):** open-count soft patches **grow `bubbleR`**
and can change hierarchy **stemR** (project centers). Soft path now:

1. Soft-patch bubbles **before** `placeActors` (was after — seats stuck on old rims)
2. If stemR would move project centers → full `paintStatic` + `placeActors`
3. If only bubbleR moved a few px → `placeActors` + soft paper-stack translate
4. Does **not** wait on 60s reconcile

Sub-second soft settle after stores attach is normal; multi-tens-of-seconds
wrong seats is a bug (this fix).

**pc-763 (expand-open poll stability):** expand-all is a **density overlay on
the fixed project ring** — it never grows `stemR` or `WORLD_W`/`WORLD_H`:

- `stemR` is computed from project bubbles only; expand mini count is not a
  factor (pc-762 removed that growth path permanently).
- `pad` = `maxPackR + rimPad + 48` — project hull only, not expand shell.
- When `paintHierarchy` does run while expand is on (e.g. Tier 3 plot-set
  change), it calls `paintExpandAllChildren` from `model.lotByKey` at the end —
  minis are re-anchored to stable lot positions, not recomputed from scratch.
- `setCam()` inside `paintHierarchy` clamps the existing camera; it does not
  reset or fit-to-scene. Camera is user-owned after the expand toggle.

Result: polls while expand is open take the Tier 2 soft path; project hub
positions do not move; the ops halo re-anchors from `lotByKey` on any
full-paint without a camera punch.

Plot structure sig = **sorted slug list only** (not managed/zone/open counts).
Sector hue = **hash(name)** only — never array index.

## Work-order tape

- Sort: **latest `updated_at` / transition ts first**
- Click: `SuitePaper.openTicket(id)` (drawer on Map)
- ⌘-click: full `/ticket` page

## Theater registry — event → map animation

Truth is always engines/disk. Theater **only projects** change. Goal: every
status / write / read that users care about has a visible beat on the Map.

### Shipped (cinema v1+)

| Event / signal | Source | Animation | Hierarchy proof |
|---|---|---|---|
| Work order filed (→ backlog) | `recent_transitions` / store Δ | Slip **YOU → folder** + landing ring | `posForSlug` → bubble center (pc-444) |
| Claimed / in progress | transitions / store Δ | Slip **agent → folder** + pulse | same |
| Signed / done | transitions / store Δ | Slip **folder → YOU** | same |
| Open count ↑↓ | soft-patch counts | Folder **count bump** + color ring | soft-patch badges + count-bump **on** hierarchy (pc-444) |
| Need You appear/clear | attention feed | Gold **star** + **padlock** | 0↔gold edges only + sticky counts (pc-550); hierarchy on |
| Agent enters `in_flight` | people scene | Arrives ring at house | `lotByKey` seat |
| Agent leaves `in_flight` | people scene | Leaves ring | same |
| Hire / new roster hand | roster Δ | Moving truck to house | `posForSlug` |
| Unhire / farewell | roster Δ | Farewell walk | same |
| Job just fired | `next_fire` edge | Patrol walk | ops seats on YOU |
| Approach / peek / live | `next_fire` + working | Park → CW walk → **folder peek** → live seat | hierarchy tick |
| Tape new slip | transitions | `is-new` flash on row | chrome (layout-agnostic) |
| Comment / Owner write | `/api/activity?project=` | Ink blot YOU→folder + tape pulse | `posForSlug` |
| Shift skip/fail/ok | `last_shift` Δ | Hand outcome badge | agent seat |
| SSE status_change | `onTapeEvent` | Same-tick filed/claim/done | same as transitions |
| fire_now | `localStorage pc-map-dispatch` | Sprint + spark | `posForSlug` |
| Law paper open | `suite-paper-open` | Paper corner glow | paper marks |

### Remaining gaps

| Event / signal | Proposed theater |
|---|---|
| Label change | Chip flash on tape |
| Label change | Chip flash on tape + folder pop — **shipped** (pc-440) |
| Disk mtime / detect writes | Folder ink ripple — **shipped** (pc-442; root_mds mtime/size sig) |
| Manage / adopt materialize | Bubble materialize on adopt/join/unhide — **shipped** (pc-443); Join CTA **pc-445** |
| Survey resurvey | Soft pie reflow + HUD |

### State-change budget

Theater remains event-driven: filed, claimed, signed, hire/farewell, and real
hand run-state changes may animate. Stationary folders, You, hands, jobs, and
the LIVE badge do not pulse or bob. Stage `map-ambient-*` classes may still
describe transport activity for copy/debug; they do not authorize loops.

### Center badge (composition A · 2026-07-25)

`#workspace-badge` at `(CX,CY)`:

- `#city-folder` hit → Finder open city root
- `#map-you-card` in the left rail → `inspectYou()` / face editor
- `is-you-here` moves the soft gold glow from workspace to dig focus
- No separate YOU disk/orbit; no 12 o’clock city-folder ring seat

### MD-first inventory (2026-07-25)

- Project **`.md` only** on the **RULES** ring (`RING_PROJ_LAW`)
- **DISK** outer inventory (code/images/archives/folders piles) **retired**
- Map is an instruction viewer + ops stage, not a full Finder clone
- **Paper paint depth** (pc-663): always **all** indexed `.md` under each
  project (former `suite.mapMdDepth` selector retired). Server indexes deep
  (`hood_root_mds`, max depth 16 / 300 files, skips `workers/` / `ops/` /
  heaps); client no longer filters by user depth.



Doctrine: **no fake work**. If the engine did not change, do not invent a
slip. Prefer soft rings over full SVG rebuilds.
