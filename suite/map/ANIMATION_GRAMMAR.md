# Map + rail animation grammar (pc-942)

Research + ship notes · 2026-08-02 · calm professional glass (no playful bounce).

## Channels (do not double-code)

| Channel | Carrier | Meaning |
|---|---|---|
| **Work ladder** | Manila **fill** (`.work-*`) + Work legend emoji | Open urgency: For You → Stuck → In progress → Ready → Empty |
| **Presence** | Manila **edge stroke** (`.ring-*`) | Hand motion: idle · approaching · live · fault |
| **You dig** | Exterior gold SVG halo (`syncYouHereHalo`) | Current dig leaf only — not For You work |
| **Stacks** | Interior seats | Inventory: You · WO · Papers · Jobs · Hands (+ 📜 instr hit) |
| **Rails** | Left-rail cards / tape beats | Same states at list scale; claim/file/close theater |

One state may **echo** across channels (e.g. live hand → green edge + green fill when flowing), but must not invent a second taxonomy.

## State → visual matrix

| State | Static | Motion | Duration | Reduced motion |
|---|---|---|---|---|
| Idle | Neutral cream manila, thin ink stroke | none | — | same |
| Approaching | Blue dashed perimeter | `map-ring-walk-dash` dash offset | 2.4s linear loop | static dash, no anim |
| On-shift / live | Solid green perimeter | **stroke-width breath** `map-ring-live-pulse` + body fill wash `map-ring-live-body` | ~1.65s ease-in-out | solid thick green stroke |
| Live + jobs seat | Jobs ⏰ present | opacity tick `map-job-live-tick` | ~1.1s | solid |
| For You | Gold tab/body wash | none (urgency is color, not pulse) | — | same |
| Stuck | Red tab/body wash | none | — | same |
| Empty queue | Pale manila | none (edge may still approach) | — | same |
| You presence | Soft gold silhouette under face | static wash (SVG clone) | — | same |
| Fault | Red solid perimeter | none (flash via rail / cross-hl) | — | same |
| Claim / file / close | Tape row beats | rail-only (`map-feed-*`) | <1s once | skip |
| Theater pause | — | freezes walk/live/job/rail FX | while paused | — |

## Missing beats fixed this slice

1. **Live glow was filter-based** on `.hier-folder-node` inside `#lots` → violated pc-843 (filter stacking covers seats) and looked “unwired.” Replaced with stroke + fill pulse only.
2. **Legend lied about folder states** — Work row was emoji-only; manila colors not shown. Added **Folder fill** mini-manila swatches.
3. **Job executing on a folder** — previously only ring-live edge; no stack cue. Jobs seat now opacity-ticks while folder is `ring-live`.

## Papers vs Instructions (pc-924)

Already shipped option D: handbook 📄 seat · 📜 corner hit / law-only face · board “All instructions on board.” Legend **Law** band owns 📜. Not mixed into Papers default dig.

## Seat rings retired (2026-08-03)

Interior stack faces are **bare emoji only** (pc-853). No `cluster-hit-ring`,
no gold disc on corner 📜, no permanent ring on `is-instr-only`. Invisible
`cluster-hit-pad` remains for hit-testing only.

**Not retired:** manila **edge** presence classes (`.ring-idle` / `.ring-walk` /
`.ring-live` / `.ring-fault`) — those are folder work-signal grammar, not seat
chrome. Class names keep `ring-*` for historical CSS; they paint the manila
stroke, not a glyph halo.

## Recommended implement children (residual)

1. ~~Live green pulse wired without filter~~ — **landed with this research**
2. ~~Folder fill legend truthful~~ — **landed**
3. Theater Back / jump-select residual UX polish (stash has prior work; merge when dogfooding)
4. Soft-patch SVG live wash under face (optional parity with You halo) if stroke breath still too quiet at zoom-out
5. Agents strip pulse/WF failure paint (pc-943)
6. Empty-queue pause surface visibility (wf-125 family) — process, not Map FX

## Verify

Hard-reload Map (suite sync). On a project with a live hand:

- Green perimeter **thickens/thins** (not a soft drop-shadow blob)
- Jobs ⏰ gently ticks if the jobs seat is painted
- Legend shows **Folder fill** mini manilas + Work faces + Stacks + Law
- Theater pause freezes the pulse
