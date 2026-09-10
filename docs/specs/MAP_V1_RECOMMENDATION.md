# Map V1 Recommendation — Surgical Clean vs New Map Shell

**Status:** DRAFT · CoS recommendation for Eli · design-first · pairs with
[`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md) + [`MAP_V1_GAP.md`](./MAP_V1_GAP.md).

## TL;DR

Two shapes on the table. My recommendation is **Option B — New Map Shell,
seeded from LKG `a01e29c`**, because dig has been dead through four
consecutive peels (#13 / #15 / #16 / #18) and the current 28k-line host is
where dig died. Continuing to peel on a dead surface is a fifth patch on
the same stack. The reframe (Map = glass over a folder, not a workspace
creator) also cuts ~93% of the current JS — the honest move is to build
that lean surface fresh rather than carve it out of a 46k-LOC forest.

**Effort:** M · ~4–6 focused days (design-time already spent).
**Risk:** Real, mostly around DEFERred surfaces re-attaching cleanly Later.

## The two options

### Option A — Surgical clean (peel-in-place)

Continue the existing peel cycle in `dod5 → dod6 → dod1 → dod2 → dod3 →
dod4` order per current INTENT, but scoped by [`MAP_V1_GAP.md`](./MAP_V1_GAP.md):

1. Land the doc pack (Glass + Gap + this doc) — no code
2. Peel dod5 (hubs+lots paint) inside `workspace_map_app.js`, gated by
   flag `pcMapV1=1`; keep old cinema behind the flag
3. Peel dod6 (empty pan quiet), same flag
4. Peel dod1 (dig) — the hard one; requires severing FAST / folder-chrome
   coupling without breaking the 4k-LOC WO tape and 3k inspect-project
5. Peels dod2 · dod3 · dod4

**Pros**
- Every surface stays live for operator use during the peel
- No `.js` bundle rename, no HTML preload list churn beyond deletions
- Reversible per peel; a bad peel reverts the flag

**Cons**
- Fifth peel on the same 28k host after four failures with the same shape
- Each peel must dodge four modules of coupling (FAST, folder-seats,
  view-chrome, inspect-*); the coupling itself is what killed dig
- Slowest path in raw calendar time — every peel needs a dogfood pass with
  the full activity-flag surface still hot
- Doesn't cash the reframe's simplification budget until the last peel

**Effort:** L · ~8–12 days, high uncertainty on peel 3 (dig).
**Risk:** Same rot re-emerges on peel 3; already the pattern.

### Option B — New Map Shell (greenfield host, LKG-seeded)

Cut a peel branch from **LKG `a01e29c`** (pre-#13; hubs paint AND dig
works). Rename `workspace_map_app.js` → `workspace_map_app.legacy.js` and
build `workspace_map_app.v1.js` (~800 LOC) alongside, then flip the HTML
preload / defer tags to load V1 by default and legacy behind
`?legacy=1`.

**What's imported from LKG a01e29c**
- Working dig verb (before the ring/dig split that killed it)
- Simpler hit walk (before six-layer competition)
- Base `#lots` paint before FAST porch coupling

**What's built new**
- `map-tree.js` (snapshot reader)
- `map-paint.js` (SVG paint — pure)
- `md-viewer.js` (reader overlay)
- Thin V1 host wiring HitRouter → dig / reader / pan
- New `/api/map/tree` + `/api/map/children?relPath=…` endpoints

**What's DEFERred** — 9 modules, ~11.9k LOC frozen; each re-adds later
against a green V1 base.

**Pros**
- V1 host stays under ~2k LOC; peels open on a surface small enough to
  reason about end-to-end
- Cashes the reframe budget immediately — DEFERred surfaces stop paying
  interest against every peel
- Legacy stays on disk behind `?legacy=1` for a fallback week — reversible
- Server hooks (`/api/map/tree`) can be built in parallel to the host

**Cons**
- Two hosts co-exist for one week; risk of drift if operator uses `?legacy=1`
  path meaningfully
- Re-adding DEFERred surfaces (agents rail, WO tape) is real work — each is
  a peel against V1, not a "free flip" back on
- Requires trusting LKG `a01e29c` is dig-alive; needs a bring-up smoke
  before the full V1 build starts

**Effort:** M · ~4–6 focused days.
**Risk:** Moderate. Higher variance than Option A per-day but lower total
because peel 3 stops being the death row.

## Effort honesty

Rough days assuming a single senior hand, ProtocolCity-shape days (design +
implement + dogfood the same day):

| Task | Option A | Option B |
|---|---|---|
| Doc pack (this) | 0.5 | 0.5 |
| LKG bring-up smoke | — | 0.5 |
| New endpoints (`/api/map/tree`, `/api/map/children`) | — | 1.0 |
| V1 host + paint + reader | (embedded) | 2.5 |
| dod5 hubs+lots peel | 1.0 | (in host) |
| dod6 pan/zoom peel | 0.5 | (in host) |
| dod1 dig peel | 3.0 (high var) | (in host) |
| dod2 WO-open passthrough | 0.5 | 0.25 |
| dod3 Outline (if kept) | 1.5 | 1.0 (as toggle on V1 state) |
| dod4 View Options filters | 1.0 | 0.5 |
| Dogfood + fix (per row) | 2.0 | 1.0 |
| **Total (V1 done)** | **~10 days** | **~5.5 days** |

Note the sizes assume no new surprises. Option A's dig peel has already
missed twice; the honest estimate treats it as a 3–5 day range with
tail risk to double it. Option B's tail risk is contained to the LKG
bring-up smoke (0.5 day) and one round of DEFERred-surface re-add
friction Later.

## Risks

### Both options

- **Operator-in-the-loop dogfood** — Map is the daily door; a bad peel
  bricks the door until reverted. Both options need `?legacy=1` on cold
  boot for at least a week
- **Snapshot endpoint churn** — the current `/api/map/snapshot` serves
  Overview too. Neither option should touch it in place; V1 uses new
  `/api/map/tree`

### Option A-specific

- **Same rot on dig peel** — the layer coupling that killed dig is a
  property of the 28k host; peeling in place doesn't remove it. Highest
  chance of a fifth failed peel
- **Flag debt** — `pcMapV1=1` inside a live host tends to fossilize; the
  flag rarely gets deleted after ship

### Option B-specific

- **LKG regression debt** — a01e29c predates several correctness fixes
  (empty-pan chrome eating hits, err veil z-index).
  V1 must re-apply those two fixes explicitly, not carry the LKG dig
  along with its LKG bugs. Both are one-liners and named in
  `map-hit-router.js` — cheap to re-apply
- **Two-host confusion during the week** — mitigate by having V1 own the
  default URL and legacy require `?legacy=1`

### Later-flavored risks (both)

- Re-adding activity flags one at a time is discipline work. The
  chrome-until-dig quarantine list ([`MAP_V1_GAP.md`](./MAP_V1_GAP.md)
  §Chrome-until-dig quarantine) must be honored — if the first activity
  flag re-add is "everything at once", we're back where we started
- Outline (dod3) is the one place `MAP_V1_GLASS.md` deviates from
  INTENT V1 lock. If Eli keeps it in V1, add ~1 day to Option B; it does
  not change the recommendation

## Recommendation

**Option B — New Map Shell, seeded from LKG `a01e29c`.**

Reasoning:

1. **Dig is dead.** Four consecutive peels on the current host did not
   restore it. The coupling is the surface, not the code.
2. **The reframe halves the target.** Map is glass over a folder, not
   workspace creator + cinema stage + coordination dashboard. Building
   a ~3k LOC surface is a different job than trimming a 46k LOC one.
3. **LKG is a real asset.** `a01e29c` had dig alive; that's the honest
   base to seed a V1 host from.
4. **Reversibility.** Legacy stays behind `?legacy=1` for a week; if V1
   flops we still have a working (if bloated) map.
5. **Total effort favors B.** ~5.5 days vs ~10 days; and the tail risk
   on Option A's dig peel is not bounded.

The one place Option A wins is operator continuity — no rename, no legacy
flag. That cost in Option B is one week of two-hosts and a URL flag; low.

## First step after Eli GO

The order below is deliberate — nothing peels code until the papers land
and the LKG smoke test passes.

1. **Papers land.** Commit the three docs (`MAP_V1_GLASS.md`,
   `MAP_V1_GAP.md`, `MAP_V1_RECOMMENDATION.md`) into `docs/specs/` and
   update `suite/map/INTENT.md` to reference them + record Eli's Outline
   call (V1 or Later)
2. **LKG smoke.** Cut a branch off `a01e29c`, dogfood glass: does dig
   work against the live binder? If yes, Option B is armed. If no, we
   have a bigger design conversation and this recommendation adjusts
3. **Endpoint peel #1.** Ship `/api/map/tree` behind a flag; hit it once
   from a scratch page to verify the shape. Reversible; adds no map
   surface risk
4. **V1 host peel #2.** New `workspace_map_app.v1.js` + `map-tree.js` +
   `map-paint.js` + wiring; loaded behind `?v1=1` URL param. Legacy
   still default. Dogfood dod5 + dod6 here
5. **Peel #3 — dig.** With V1 host isolated, wire dig against HitRouter
   + `MapViewState`. Dogfood dod1 in glass. This is the row that killed
   the last four peels; verify by clicking each of hub / lot / dig-in
   child / md-file lot
6. **Peel #4 — reader.** `md-viewer.js` overlay; dod2 (WO passthrough)
   falls out of reader for free
7. **Peel #5 — filters.** View Options wire dod4
8. **Peel #6 — Eli call.** Outline if kept; skip if Later
9. **Flip default.** V1 becomes the default map; legacy behind
   `?legacy=1` for one dogfood cycle; then remove
10. **Later re-add starts.** First activity flag peel opens against a
    green V1 base (candidate: WO tape · dig-split recovery)

**No peel opens on the current tip.** The doc pack is the ask. Code
follows only after Eli GO on the recommendation and on the Outline call
(step 1).
