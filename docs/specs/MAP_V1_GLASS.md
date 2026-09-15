# Map V1 Glass — Greenfield Spec

**Status:** HISTORICAL (2026-09-10). Superseded by
[`MAP_FOCUSED_PROJECT.md`](MAP_FOCUSED_PROJECT.md) and the Map sections of
[`OPERATIONS_EVOLUTION_2026_09.md`](OPERATIONS_EVOLUTION_2026_09.md).
Kept as the folder-glass thesis (tree + dig + reader) that focused-exploded
still sits on. **Do not implement this paper as a competing Map.**

Live code: `map/v1/`.

## One sentence

**Map is a coordination glass OVER a folder** — the workspace's file tree
(FS + git) is the truth; Map projects that truth spatially so you can dig,
read `.md`, and route work. **It is not a workspace creator.** Found / adopt /
hire live in the CLI, not in Map paint.

## Product thesis (reframe)

| Was drifting toward | V1 is |
|---|---|
| Continuous cinema over live engines (seats · trucks · pulse · gold beats) | Static-first paint of a folder tree with dig + MD reader |
| Workspace author (join / adopt / seed-ops surfaces) | Read/route glass — capture happens in chat + `wl` MCP (SUITE_VIEWER law) |
| Six inspect kinds, six left-rail modules, four projections' worth of chrome | One binder, one tree, one dig trail, one reader, one hit router |
| A layer stack fighting itself for pointer hits | One SoT that classifies every pointer hit |
| "Chrome first so it looks alive on cold boot" | "Base paints and dig works before any chrome lands" |

**Corollary:** activity flags — work-order urgency, hand presence, live badge,
motion, gold "For You", WO tape, agent activities rail, seat pack — are all
**Later**. V1 must be legible with none of them running.

## The root binder

A **binder** is a folder on disk designated as the workspace root (the folder
`blueprint found` / `adopt` wrote a marker into). Map roots on that binder
and only that binder.

| Rule | Why |
|---|---|
| Exactly one binder per Map instance | No cross-workspace stitching, no OneSeo-style meta-hub in V1 |
| Binder path is server-owned (`/api/map/snapshot` returns it) | Suite never guesses; no localStorage binder in V1 |
| Binder folder = **hub** node | Painted center; the only depth-0 lot |
| Everything else = **lot** under hub | Depth ≥1; top-level lots first, deeper lots on dig |

## Truth = filesystem + git

Map reads three things from the BFF snapshot; nothing else in V1.

| Layer | Source | Ownership |
|---|---|---|
| **Tree** | Filesystem: dir + name + `is_dir` + `has_md` | server walks; V1 caps depth 2 at cold paint, expands on dig |
| **Managed set** | `.protocolcity/` markers + `join` state | server flags each dir `managed / unmanaged / hidden` |
| **Git shape** | `git ls-tree` + `HEAD` at binder root | for filtering (`hidden` = `.gitignore` union) — not for status colors in V1 |

**Not consumed in V1:** WorkLane stores, WorkForce roster, tp-scene,
attention pulse, SSE tape, mtime, `next_fire`, city-data overlay. Those are
activity-flag inputs, deferred.

## Paint stack (one order, one owner per layer)

```
stage (SVG #world)
  ├─ #lots               ← folder silhouettes (base map)
  ├─ #hub                ← workspace binder folder (depth 0)
  ├─ #dig-in-layer       ← dig fan / child folders (only when digging)
  ├─ #md-viewer-layer    ← in-shell .md reader (overlay, dismissable)
  └─ #chrome-layer       ← HTML controls: View Options, Reset, dig trail
```

Rules:

1. `#lots` and `#hub` always paint on cold boot. If they don't paint, V1 has
   failed — no chrome tries to compensate.
2. `#dig-in-layer` is empty until a dig fires; it never pre-lays out fans.
3. `#md-viewer-layer` is `visibility: hidden` until a `.md` opens; owns hits
   only while up.
4. Chrome (HTML `<details>` / `<button>` overlays) is `pointer-events: auto`
   only where explicitly bound; the SVG never fights it for the same pixel.

No FAST porch, no folder-chrome-layer, no seat pack, no fast-cover, no
handoff dance — those are the coupling that killed dig across #13/#15/#16.

## Dig grammar

One dig verb, one back verb, one trail.

| Input | Effect |
|---|---|
| Click a lot | `MapViewState.setDig({slug, name, relPath})` → paint children in `#dig-in-layer` → update trail |
| Click a child lot (dig-in) | Same verb; trail push |
| Click hub or Reset | `clearDig()` → wipe `#dig-in-layer` → paint top-level tree |
| Click a `.md` lot | Open `#md-viewer-layer` (does not push dig) |
| Backspace / ← Up button / trail crumb | Trail pop |

Dig state has one owner (`MapViewState.dig`). No sibling `mapDigIn` global,
no host-local dig cache, no fan-sig lock. Two consumers only: `#dig-in-layer`
paint and dig trail chrome.

## MD viewer

The reader is Map's second body — it makes the folder tree instructive
instead of just spatial.

| Rule | Note |
|---|---|
| One overlay, mounted once, hidden by default | `#md-viewer-layer` — never a new page, never a suite drawer copy |
| Opens on `.md` lot click or trail-crumb `.md` | No side rail, no dig fan on `.md` |
| Content = server-rendered from `/api/file?path=…` | Markdown → HTML server-side; suite paints result |
| Closes on × / Esc / backdrop | Focus returns to prior lot |
| Does not affect `MapViewState.dig` | Reader is orthogonal to dig |

Out of V1: `.md` role classification (skills / architecture / law gold),
Required-vs-Other stack, paper glyph channel, per-folder papers panel — those
are activity flags on top of the base reader.

## Hit-Layer SoT (single router)

One classifier — `MapHitRouter` (already extracted in `map-hit-router.js`) —
returns `{kind, layer, root}` for every pointer event on stage. V1 collapses
its table down.

| Layer | Owns hits when | Verb |
|---|---|---|
| **md-viewer** | overlay open | reader-only (Esc closes) |
| **chrome** | HTML corner panels visible | own DOM listeners |
| **dig-in** | pointer over `#dig-in-layer` child | `dig` on child |
| **hub** | pointer over hub | `dig` (open workspace root) or `reset` |
| **lots** | pointer over `#lots` child | `dig` on lot |
| **empty** | none of the above | `pan` |

Everything else in the current 9-row table (err-veil, fast-cover, stage-chrome
sub-classes, outline) is chrome — comes back one row at a time only after
the six-row core holds.

## Empty pan and zoom

- Pan: pointerdown on `kind: pan` → drag pans camera; release commits.
- Zoom: wheel / pinch on `#world` → scale about pointer; clamp `k` to `[0.5, 4]`.
- Pan/zoom never fire while `md-viewer` or `chrome` own hits.
- Reset button snaps camera to a computed `fitToLots()` bound; no easing in V1.

## Out of V1 — Later (activity flags)

Everything below is **chrome** until every V1 row is green **and holds green**
across two dogfood cycles. Re-land one at a time; each re-add cites which V1
row it must not regress.

| Later — activity flags | Why held |
|---|---|
| Work-signal ladder colors on lots | Requires WorkLane store poll; not truth-of-folder |
| Interior seats (You / hands / jobs / work / papers / instr) | Seat pack collided with dig hits (#13) |
| FAST porch + fast-cover | First-paint theater that fought `#lots` for hits |
| Stems / spokes between hub and lots | Layout ornament — not required to read the tree |
| Legend | Explains chrome that isn't there yet |
| Expand FAB (top-level children of every project) | Density overlay; separate mode |
| Dig-trail glyphs / dig-tier foundation weight | Secondary palette |
| Agents Activities rail (`agents-panel.js`) | Roster stream — no truth in V1 |
| WO tape (`wo-tape.js`) | Store poll — no truth in V1 |
| Searchlight | Search over cinema — needs live index |
| Inspect-{project,person,you,workspace,orbit,shell} | Six side rails; V1 reader is the one sidebar |
| Cam / fit animations | Ease + easings — snap in V1 |
| Continuous cinema (SSE tape, pulse, heartbeat, reconcile) | The whole live loop |
| Outline projection | Ship after Map dig lives (was V1 dod3; **downgraded** — see note) |

**Note on Outline (dod3):** the INTENT V1 lock still names Outline as a V1
must-have. **This spec proposes moving Outline to Later** because a folder-tree
projection with dig + reader **is** the tree; a second row-oriented view is a
polish once the spatial view holds. Flag for Eli — this is the one place this
spec deviates from the current INTENT V1 list. If Outline stays in V1, it
becomes a projection toggle on the same `MapViewState` and reuses the same
snapshot; no second store, no second hit router.

## V1 must-have vs chrome (recap)

| Class | Members |
|---|---|
| **V1 must-have** | hub+lots paint · empty pan · zoom · dig (lot + hub + child) · MD viewer · WO-open on md-file-that-happens-to-be-a-work-order-link (see note) |
| **Held for Later** | everything under "Out of V1" above |

**WO-open (dod2) note:** in the reframe, a work order is not painted on Map
in V1 — but clicking a WO row in the reader (an `.md` that links to
`/ticket?id=…`) still opens the ticket dig-in via the standard suite router.
That closes dod2 without dragging in the WO tape module. If the operator needs
the WO tape sidebar on Map itself, it re-lands as an activity flag (Later).

## Definition of Done (DoD) — restored peel order

Peel order is **paint the base and quiet the canvas first, then dig, then
reader, then filters** — one row at a time, each verified in dogfood glass
against the live binder before the next peel opens.

| Peel | Row | Done when |
|---|---|---|
| 1 | **hub+lots paint** | Binder hub and top-level lots paint on cold boot and after Reset; no dig state sticks past Reset |
| 2 | **empty pan · zoom · reset** | Pan/zoom work on empty canvas; Reset snaps to fit; no ghost clicks on hidden chrome |
| 3 | **dig works** | Click a lot → children paint in `#dig-in-layer`; trail updates; back returns |
| 4 | **MD viewer** | Click a `.md` lot → reader opens; Esc / × / backdrop close; dig state untouched |
| 5 | **View Options filters** | Managed · Unmanaged · Hidden filter which lots paint; persists via `MapViewState`, no second store |
| 6 | **WO-open passthrough** | Clicking a WO link inside the reader opens `/ticket?id=…` in-shell |

Optional 7th (Eli call): **Outline toggle** — if kept in V1, it re-consumes
`MapViewState` and adds no new store.

All rows hold in dogfood glass before V1 is called done. A row that regresses
to make room for an activity flag fails V1.

## Non-goals (say-so)

- No workspace author (no join / adopt / seed-ops in Map paint).
- No second projection cache — one `MapViewState`, one snapshot.
- No client-side liveness (`managed / unmanaged / hidden` come from server).
- No cinema, no motion, no seats, no gold beats in V1.
- No dual hit router; `MapHitRouter` is the only classifier.
- No 28k-line host file. If the V1 host exceeds ~2k lines it has drifted.
