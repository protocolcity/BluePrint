# MC full glass — gap vs live :8803 (peel landing)

**Date:** 2026-09-11 · **Gate:** Brand PASS on **01c · 02c · 03d** — full glass peel opens
**Live:** Cellar `0.1.50_6` `blueprint-overview` · BluePrint tip `c35db4f5` (#42+#43)
**Mocks:** Brand-PASS `ext-01c` · `ext-02c` · `ext-03d`

## Live before this peel
- Local desk banner · three equal tiles Agents/Jobs/Pulse · honest empties
- Hand-off chips Map · Calendar · Settings (bottom)
- Focusable tile bodies + hide empty pulse track (#43)
- Stub APIs `/api/overview/{agents,jobs,pulse}` — empty by default
- No four-lens top nav · no project card · no Charter drawer · no Crew · no honesty badges · no Cellar tip footer

## Peel landing — full glass (this PR)
Extend `#38` (`overview/v1/`) without breaking V1 DoD (`OVERVIEW_V1_GLASS.md` rows 1–5):

| Wanted | Was | Now |
|---|---|---|
| Four-lens top nav Overview·Map·Calendar·Settings | Bottom chips only | Top nav row (Overview current) |
| Local desk pill under nav (never `workspace`) | Banner pill in-flow | Pill under top nav, working-green dot |
| Agents rows + state dots; cloud/remote builders as **links** | Empty only | `paintAgents` renders rows + link group |
| Jobs Waiting/Ready/Blocked counts (zeros OK) | Empty copy only | `paintJobs` renders honest bucket counts |
| Pulse named local heartbeats (FS/Builder/Cellar/Index/Sync) + Cellar tip line | Silent tick | `paintPulse` renders heartbeat rows + `Cellar tip` + `Last tick` |
| Footer "systems quiet" strip | Absent | `paintFooter` mirrors heartbeats + never-lie |
| Project card (title + honest badges + Charter excerpt) | Absent | `paintProject` shows when server returns a project |
| Charter drawer + Crew (03d) | Absent | `paintCharter` renders drawer alongside peer tiles |
| Never-lie Cellar tip (brew face, not private SHA) | Absent | `--cellar-tip` server flag; drawer footer says "not private Protocol City install" |

## Never-lie fences held
- Consume ≠ MANAGED (badge lit only when a lease is live)
- No example_user as OneSeoPOS peel SoT
- No private ProtocolCity as install face
- Missing heartbeat paints muted, never green
- Cellar tip = brew app version (e.g. `blueprint 0.1.50_6`)
- Cloud/remote builders = outbound links, never local agents
- Charter drawer stays alongside (never replaces) Agents · Jobs · Pulse peer tiles

## Non-goals (still)
- No Wall restart · no Map-as-home · no sparklines · no `:8801` suite Map peels · no SaaS chrome · no cinema / continuous animation

## Peel order (this PR bundles)
1. Spec addendum — [`OVERVIEW_MC_EXT.md`](./OVERVIEW_MC_EXT.md) covering **01c · 02c · 03d**
2. Four-lens chrome + Jobs buckets + Pulse local heartbeats + Cellar tip (never-lie)
3. Project card + honesty badges
4. Charter drawer + Crew (03d)
5. Cellar tip bump → Local dogfood DoD
