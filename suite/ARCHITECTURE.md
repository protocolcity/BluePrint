> Historical suite design. The current application authority is [../ARCHITECTURE.md](../ARCHITECTURE.md); retained rules below apply only where compatible with the current architecture.

# suite/ — Client Architecture (L2 binding law)

> **Binding law** — pc-1088 · 2026-08-04 · blossom
> Promoted from: `docs/research/bp-suite-production-architecture-2026-07.md`
> Supersedes: pc-706 (EXPLORE Map live-projection architecture) — see §Supersedes.
> **Close-out rule (§5):** any Map/suite ticket that changes structural behavior must
> update this paper in the same close-out.

---

## 1. Layer doctrine

The suite is a **thin client** over disk-truth engines. Three layers, one direction.

| Layer | Owns | Rule |
|---|---|---|
| **Truth** | Files + WorkLane SQLite + WorkForce roster/ledger | No browser source-of-truth |
| **Projection** | Engines — citylens :8796, WorkLane :8799, WorkForce :8797 | APIs, scene models, generation tokens |
| **View** | Suite :8801 — `serve.py` BFF + `suite/` JS | Thin client: compose + cache + pulse only |

Citizen entry is **:8801 only** (ONE DOOR — pc-277). Engines are API-only from the
citizen's perspective; their own HTML surfaces are lumber.

---

## 2. Data-flow contract

**Five invariants.** Every structural ticket must leave all five intact.

### 2.1 One snapshot + one delta stream

The BFF exposes one composed scene per surface (e.g., `GET /api/map/snapshot`). The
client requests it on first paint and after a full cache miss. All subsequent updates
arrive via **one delta bus: `GET /api/pulse`**. When pulse tokens move the client
requests only the affected scope — it does not maintain a second poll, SSE connection,
or interval loop for the same data.

Current delta bus: `suite/suite-pulse.js` · `suite/map/live.js`.

### 2.2 One client store per panel

Each Map panel (left rail, work-order tape, folder list) owns its own state slice.
State does not bleed between panels via module-scope globals or `window.*` flags. A
panel renders what it receives; it does not read another panel's cache to infer state.

Canonical panel boundary: `suite/map/workspace_map_app.js` — its render functions are
the unit of migration in the strangler order (§4). Extracted: `suite/map/agents-panel.js`
(Phase 3-A) · `suite/map/wo-tape.js` (Phase 3-B) · `suite/map/folder-list.js` (Phase 3-C)
· `suite/map/inspect-project.js` (pc-1395 — project inspect overview / Finder / house /
open-pile door; host keeps thin wrappers) · `suite/map/inspect-person.js` (pc-1401 —
hand / job inspect + person-dig body; host keeps thin wrappers) · `suite/map/inspect-you.js` (pc-1405 —
You / For You inspect + snooze/toolbar/face-query; host keeps thin wrappers) · `suite/map/inspect-workspace.js` (pc-1408 —
workspace inspect / place pulse; host keeps a thin `showWorkspaceDetail` wrapper) · `suite/map/inspect-orbit.js` (pc-1414 —
inspect orbit list / KPI chips / Previous-panel button; host keeps thin wrappers) · `suite/map/inspect-shell.js` (pc-1415 —
inspect rail shell: open / history / toolbar / close; host keeps thin wrappers).

### 2.3 One vocabulary module, shared client and server

WO bucket thresholds, gate names, status labels, and `live`/`open`/`in-pile`
vocabulary have **one source of truth: `suite/map/wo-buckets.js`** (pc-1084/1085/1086).
No panel, render helper, or BFF route may inline these definitions.

### 2.4 Liveness computed server-side

Which workers are live, which work orders are active, and what counts as "in-pile" are
decisions the **BFF or engine API makes before the response leaves the server**. The
client renders the verdict it receives. No client-side liveness heuristics (e.g., "if
`last_seen` > 30s, mark grey").

### 2.5 View state as one persisted object

All expand/focus/dig-in state lives in **`suite/map/view-state.js` (`MapViewState`,
pc-844)**. No competing `localStorage` keys, URL-fragment shadow copies, or `window.*`
expand flags.

---

## 3. Structural diagnosis (2026-08-04 investigation)

The following structural problems were confirmed during the founder's 2026-08-04
investigation. They are the root cause of the grey-Agent-Activities, duplicate-sidebar,
seat-overlap, and view-option domino bugs. They are recorded here so future tickets do
not re-diagnose the same causes.

| # | Problem | Observed evidence |
|---|---|---|
| D1 | ~285 module-scope globals in `suite/map/workspace_map_app.js` | State changes cascade unpredictably across render paths |
| D2 | 9+ copies of work-order state (inline fetch · SWR cache · left-rail copy · tape copy · folder copy · global map · SSE patch object · pulse patch object · view-state ref) | An update in one layer does not reach others; stale UI persists even after pulse tick |
| D3 | Two rail renderers negotiating via 9 `window.*` flags | Rail rebuild triggers full re-render; no declared render contract between them |
| D4 | Four incoherent cache layers (SWR sessionStorage · BFF process-local TTL · SuiteLive SSE patch · SuitePulse token) | Cache invalidation is per-symptom, not per-rule; invalidating one leaves others stale |
| D5 | Three unreconciled liveness clocks (WorkForce poll · SuiteLive heartbeat · SuitePulse generation token) | Liveness decisions differ per surface; grey seats appear at different rates than stale WO tape |

These problems trace to no enforced architecture binding suite work: the correct
layering existed in the vault note since 2026-07-21 but nothing required code to follow
it. The strangler order (§4) is the repair sequence.

---

## 4. Strangler order

Phases are sequential for structural work. Point fixes (styling, label copy, link
targets) may proceed in any phase. A phase is "open" while it has any unclosed
structural ticket. Phase N+1 structural tickets must not land while phase N structural
tickets are open.

| Phase | Scope | Done when | Anchor tickets |
|---|---|---|---|
| **1 — Vocabulary collapse** | All WO bucket thresholds, gate names, status labels, and live/open/in-pile tests import from `suite/map/wo-buckets.js`; no inline copies remain in `workspace_map_app.js` or any rail/tape renderer | Zero inline definitions found by grep; `wo-buckets.js` is the only SoT | pc-1084 · pc-1085 · pc-1086 ✓ in flight |
| **2 — Snapshot / delta endpoints** | BFF exposes `GET /api/map/snapshot` (full composed scene); clients rely on `GET /api/pulse` for delta tokens; ad-hoc sub-interval poll loops removed | No interval < pulse frequency remains for structural data; snapshot round-trip < 250ms | pc-1122 ✓ |
| **3 — Per-panel store migration** | Left rail first: extract its state slice + render loop from `workspace_map_app.js` into a dedicated module with no shared globals; then WO tape; then folder list | `workspace_map_app.js` module-scope mutable globals < 20; each panel's module boundary is explicit | pc-1130 ✓ Phase 3-A agents panel (`suite/map/agents-panel.js`) · pc-1248 ✓ Phase 3-B WO tape (`suite/map/wo-tape.js`; host wrappers for `rowMatchesWoFilter` / folder heat / `repaintWoInsights`) · pc-1260 ✓ Phase 3-C folder list (`suite/map/folder-list.js`; host wrappers for Outline expand/render / `outlineRevealPlot`) · **pc-1395 ✓** project inspect renderer (`suite/map/inspect-project.js`; host wrappers for `showProjectDetail` / `inspectProjectFinder` / `inspectHouse` / `openProjectWorkOrders`) · **pc-1401 ✓** person inspect renderer (`suite/map/inspect-person.js`; host wrappers for `inspectPerson` / `paintPersonDigIn`) · **pc-1405 ✓** You inspect renderer (`suite/map/inspect-you.js`; host wrappers for `inspectYou` / `fillYouForYouPanel` / `bindYouSnoozeBar` / `applyYouFaceQuery`) · **pc-1408 ✓** workspace inspect renderer (`suite/map/inspect-workspace.js`; host wrapper for `showWorkspaceDetail`) · **pc-1414 ✓** inspect orbit chrome (`suite/map/inspect-orbit.js`; host wrappers for `inspectOrbitGroup` / `paintInspectKpis` / `paintInspectBackBtn`) · **pc-1415 ✓** inspect rail shell (`suite/map/inspect-shell.js`; host wrappers for `openInspect` / `closeInspect` / `ensureInspectToolbar` / `inspectBack`). First-paint incidents: **pc-1292 ✓** (profile + snapshot preload / defer panels — not a mega-split). Phase 3 panels extracted; globals-count done-when still open (Phase 4 / residual host state). Host slim continues (pc-1395 standing 34k → ≤33k; pc-1401 ≤31.4k; pc-1405 ≤30k; pc-1408 ≤29.6k; pc-1414 ≤29.4k; pc-1415 ≤29.1k). |
| **4 — Delete dead code** | Remove `suite/map/map-fast.js`, v1 HTML pages (post-302 redirect confirmed), legacy route handlers in `serve.py`, all `window.*` negotiation flags | `map-fast.js` deleted; zero dead routes in `serve.py`; zero `window.*` render flags | TBD — after phase 3 complete |

**pc-1292 first-paint profile** (founder host, 2026-08-19 — do not mega-split the host IIFE):

| Clock | What | This host |
|---|---|---|
| Time-to-skeleton | HTML + CSS (shell already has “Building workspace map…”) | ~instant after HTML/CSS (gzip HTML ~5 KiB) |
| Time-to-folder-ring | map-fast paints managed ring **under** the skeleton after snapshot | Snapshot cold ~1 s / warm ~23 ms. Ring stays covered until host handoff (pc-973) or 4 s failsafe |
| Host parse vs bootstrap | `workspace_map_app.js` 1.18 MB / ~305 KiB gzip | `node --check` parse ~29 ms — **not** the long wait. Bootstrap 302 `/api/map-bootstrap` → `/api/map/snapshot` discarded the fetch preload; two **sync** panel scripts (~242 KB) blocked the deferred host tag |

Bounded land: preload + prefetch **`/api/map/snapshot`** (no 302); preload `map-fast.js`; **defer** `agents-panel.js` + `wo-tape.js` so document parse reaches the host `defer` tag after map-fast only. Console `[pc-1292] first-paint` marks shell→ring / host-exec / reveal.

When a child ticket lands for a phase-2/3/4 slice, add it to the anchor-tickets column
and update the "done when" count if the scope changes.

---

## 5. Close-out rule (binding)

> **Any Map or suite ticket that changes structural behavior — adds or removes a state
> store, introduces a new data-fetch path, changes how a panel receives its data, adds or
> removes a shared module, or changes the liveness decision boundary — must update this
> paper in the same close-out commit.**

"Update this paper" means one or more of:
- Revise the affected row in §2 Data-flow contract.
- Add or remove a row in the Structural diagnosis if a new problem is confirmed or a
  listed problem is resolved.
- Advance the Phase row in §4 Strangler order (mark a phase done, or add a child ticket
  anchor).
- Add or remove a Target violation in §6 if a new invariant applies.

A close-out that touches structure but skips this update is **incomplete** and should
not be merged without a follow-up ticket explicitly scoped to the paper update.

---

## 6. Target violations

Agents building against this paper must not:

1. Add a new module-scope mutable variable that holds work-order or worker state in
   `workspace_map_app.js` or any panel module.
2. Add a second `setInterval`, `SuiteLive`, `EventSource`, or `SuitePulse` instance to
   obtain data already available via the existing pulse/SSE bus.
3. Inline WO status labels, bucket thresholds, or gate names — import from
   `suite/map/wo-buckets.js`.
4. Add a client-side liveness heuristic (time-since-last-seen → visual state) — that
   decision belongs server-side.
5. Store view state in `localStorage` outside `MapViewState` (`suite/map/view-state.js`).
6. Add a `window.*` flag to communicate state between rail renderers.
7. Close a structural ticket without updating this paper (§5 close-out rule).
8. Point Map **behavior** greps at `workspace_map.html` (299-line shell). Assert
   functions / paint / filters against `workspace_map_app.js` or the extracted
   module; script-tag and first-paint skeleton checks may stay on the HTML.
   (pc-1249 / RC-08 · pc-1248 wo-tape.js · pc-1260 folder-list.js).

---

## 7. Supersedes

**pc-706** (EXPLORE: Map live-projection architecture vs map-first simplicity) required
a short research note in `docs/research/` capturing the target live model. This paper
is that deliverable, promoted to binding law. pc-706 is closed with a pointer here.

The source vault note
(`docs/research/bp-suite-production-architecture-2026-07.md`) remains the record of
the July system architecture, performance bottlenecks, component structure, and
WorkLane split design — it is not superseded, only supplemented by this binding paper.
Figaro's deferred/umbrella note on pc-706 (2026-08-01) correctly identified the
research note as docs-lane work; this close-out fulfills that routing.
