# Overview THEME — Mission Control Glass (dark PC desk)

**Status:** DRAFT · Product design room (Brand · Designer · Writer) PASS on
label lock + Mission Control voice, nits applied. Companion to
[`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md) — INTENT names the surface, this
theme names the paint. Sibling shape to [`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md).

This doc is a **decision spec**, not a token registry. It records the Design
room's keep · enhance · drop calls against the landing surface and hands
Writer's empty copy to the peel. No exact token values live here; the paint
layer owns those, gated by these decisions.

## One sentence

**Overview is painted as a quiet, dark PC desk** — four surfaces at rest
(agents · jobs · pulse · local-only banner), honest empty by default,
Mission Control voice throughout. It never looks busy to look alive.

## Label lock (reminder)

Same vocabulary as INTENT. **BluePrint** = the desk. **Overview** =
Mission Control glass. **Map** = dig. The brand is **PC** (Protocol City).
No LLC surface, no legacy oneseollc carryover, no cream palette.

## Keep · Enhance · Drop

### Keep

The Design room accepts these — they carry forward from the current landing
surface into V1 without modification.

| Keep | Why |
|---|---|
| Dark PC desk (near-black, `#0f1114` family — not cream) | Brand lock; the landing lens is the desk's first breath, and the desk is dark |
| Four-surface spine — **agents · jobs · pulse · local-only banner** | The V1 surfaces named by INTENT; nothing else lands |
| Honest empty as a first-class state | INTENT invariant #4; empty is copy, not a spinner |
| Quiet desk density type — read at rest, not from across the room | Mission Control voice; the glass whispers, not shouts |
| One landing lens with quiet hand-offs to **Map · Calendar · Settings** | INTENT invariant #5 + #8; Overview hands off, it does not embed |

### Enhance

The Design room accepts the surface but sharpens the paint. These are
deltas against today's landing pattern, not new surfaces.

| Enhance | Delta |
|---|---|
| Banner → **three equal tiles** (agents · jobs · pulse) | Replace the single hero band with a three-tile row; each tile owns one V1 surface, equal weight, no dominant tile |
| No hero come-back | Recency does not get its own tile; if it re-appears Later, it lives inside jobs |
| **State dots** for agents — idle · working · error · off | Four-state palette; one dot per agent row; the dot is the state, not a label next to it |
| Shared **2px focus** ring across all interactive elements | One focus voice across tiles, hand-off chips, and the banner — no per-component focus styling |
| **Pulse = one quiet tick line**, never a loop | Single horizontal tick track; ticks land as events land; no continuous animation, no easing loop, no shimmer |
| Empty = **Writer copy** (or a silent Design spacer), not skeleton shimmer | Skeleton shimmer implies "loading — real content coming"; V1 empty is real content |

### Drop

The Design room drops these outright. Any peel proposing to re-land one
must cite this section and prove it does not regress an INTENT invariant.

| Drop | Why |
|---|---|
| Map-lite tile or any dig verb on Overview | Label lock — `dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, `crumb` belong to Map |
| Wall-style feed or cinema | Recreates the Wall rot the reframe is peeling away; Overview is a glass, not a screensaver |
| Cream / LLC-era palette | Brand lock — PC dark desk only |
| Fake / synthetic activity indicators | Local-only honesty; no fabricated pulse, no simulated peers, no cloud-ops theater |
| A second `.md` reader on Overview | Reader lives on Map |
| Settings panel on the landing lens | Settings is its own lens; Overview hands off to it |
| Competing "home" card | One landing lens; Overview is it |

## Writer — empty copy (V1 lock)

Every surface must read as legible with **zero** entries. These are the
strings Writer signed off on; the peel uses them verbatim. Zeros **PASS**
dogfood — see the Dogfood note in [`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md):
`No agents` is the correct paint when the desk truthfully has none, not a
fallback for a broken read.

| Surface | Empty copy |
|---|---|
| Agents | `No agents` |
| Jobs | `No open jobs` |
| Pulse | silent — or `No pulse yet` if a string is required |
| Local-only banner | `Local desk` — **never** the word `workspace` |
| Hand-off chips | `Map` · `Calendar` · `Settings` — the Map chip says `Map`, **never** `Dig here` |

Rules on the copy:

1. **`Local desk`, not `Local workspace`.** The banner speaks the desk's
   name; `workspace` is a legacy surface word we do not carry forward.
2. **`Map`, not `Dig here`.** The hand-off chip is a lens name, not a
   verb. Verbs belong on Map, not on the chip that points at Map.
3. **Pulse may be silent.** If nothing has ticked, the tick line paints
   empty; a string is optional, not required.
4. **No punctuation drift.** No trailing periods on empty strings, no
   ellipses, no "…yet" softeners beyond the one Writer already approved
   for Pulse.

## Token classes (named, not enumerated)

The paint layer owns exact values. These are the classes the peel is
allowed to reach for; anything outside is a **spec gap** back to the
Design room, not a peel decision.

| Class | Covers | Notes |
|---|---|---|
| **Surface** | Desk glass background · tile background · honest-empty background | Dark PC desk family; one background voice across all three tiles, no per-tile tint |
| **Voice** | Type ramp + weights for the four V1 surfaces (agents · jobs · pulse · banner) | Quiet; read at rest; no display-weight hero type on the landing lens |
| **State** | Agent-state palette (idle · working · error · off) + pulse tick color | Four dot colors + one tick color; must survive a light/dark parity check when a light variant is proposed Later |
| **Focus** | The shared 2px focus ring | One focus voice; same ring on tiles, chips, banner |

Values live in the paint layer. This spec names the classes and the
decisions; it does not print the values.

## Invariants (theme-side)

These sit under the INTENT invariants and cannot be broken without failing
the theme pass.

1. **Dark only.** No cream, no LLC-era palette, no light-mode variant in
   V1. A light variant is a Later spec, not a V1 flip.
2. **Three equal tiles.** No dominant tile, no hero band, no come-back
   surface competing with agents · jobs · pulse.
3. **Pulse is discrete.** Ticks are events, not motion. No continuous
   animation on the landing lens.
4. **Empty is real.** Empty states use Writer copy or a Design spacer.
   Never skeleton shimmer — shimmer lies about a loading state that
   isn't happening. A `demo-worker` on the local registry does **not**
   paint a busy tile — it paints `No agents` until a real event ticks.
5. **One focus voice.** The 2px ring is shared across every interactive
   element. No per-component focus experiments in V1.
6. **Copy lock.** The strings in the Writer table above are exact. A
   peel that reworders them fails the theme pass.

## Later — theme held (activity flags)

Mirrors INTENT's Later list, theme-side. Each is a re-add candidate for
a future peel; none paint in V1.

| Held — theme surface | Why held |
|---|---|
| Light-mode palette | V1 is dark-only; parity check happens against a proposed light spec, not by inference |
| Motion / cinema / continuous animation on any surface | Pulse invariant #3; the glass is not a screensaver |
| Skeleton shimmer as an empty state | Empty-is-real invariant #4 |
| A fourth tile of any kind | Three-equal-tiles invariant #2 |
| Per-tile background tints or per-agent color chips | One surface voice; agent state lives in the dot, not the row |
| Focus ring experiments per surface | One focus voice invariant #5 |

## Hand-off to the peel

For the record, so the peel that follows this spec knows the frame:

- The peel paints against **Keep** as-is, applies **Enhance** as the
  delta, and rejects **Drop** on sight.
- Writer copy in the empty table is verbatim; the peel does not
  reword.
- Token values live in the paint layer, gated by the four classes above.
  A missing class is a spec gap back to the Design room, not a peel call.
- The peel order is published separately in `OVERVIEW_V1_GLASS.md`
  (see INTENT's ship fence).
