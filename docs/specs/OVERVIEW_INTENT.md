# Overview INTENT — Mission Control Glass

**Status:** DRAFT · Product design room (Brand · Designer · Writer) + Eli
review · **spec-first**, code peels do not open until this INTENT lands **and**
the Design theme pass returns [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md).
Sibling of [`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md) — same shape, different lens.

## Label lock (do not swap)

The desk has one shared vocabulary. Every surface of every peel that lands
against this spec must use these names and only these names:

| Label | Means |
|---|---|
| **BluePrint** | The desk — the shell the operator sits at |
| **Overview** | The Mission Control glass — the landing lens on the desk |
| **Map** | Dig — the glass over a folder (spatial folder projection) |

Overview is **not** Map. Overview is **not** dig. Overview is **not** a
spatial folder glass. Overview never borrows Map's verbs. If a proposed
Overview element wants to say `dig`, `lot`, `hub`, `md-viewer`, `fan`, or
`trail`, it belongs on Map instead — reject the paint and file it to the
Map track.

The brand is **PC** (Protocol City). No LLC surface, no legacy oneseollc
carryover, no cream palette — this is the dark PC desk.

## One sentence

**Overview is the Mission Control glass for the BluePrint desk** — a
system summary of **agents · jobs · pulse** at this desk, spoken in a
local-only voice. It is the lens the operator lands on; it never
pretends work is happening in the cloud.

## Four-lens spine (reminder)

BluePrint has four lenses on the same desk. Overview is the landing lens.

| Lens | Role |
|---|---|
| **Overview** | Mission Control glass — agents · jobs · pulse (this spec) |
| **Map** | Dig — glass over a folder (see `MAP_V1_GLASS.md`) |
| **Calendar** | Time lens — scheduled routines, planned work (later spec) |
| **Settings** | Desk configuration lens (later spec) |

Overview is **the landing lens**: the operator arrives here first. Every
other lens is one click away, but Overview is the surface that sets the
tone for the desk.

## Is / Is-not

| Overview IS | Overview IS NOT |
|---|---|
| Mission Control glass — system summary at a glance | Map, dig, or any spatial folder projection |
| Voice-of-the-desk: what agents are doing, what jobs exist, what the pulse looks like | A come-back stack, an activity feed, or a "recent things" wall |
| Local-only honesty — reports only what this desk can see on this machine | A cloud-ops theater — no fake in-flight indicators for work the desk didn't launch |
| Honestly empty when nothing is running | Padded with placeholder cards, motion, or synthetic activity to look busy |
| Aware of its neighbors — a quiet hand-off to Map / Calendar / Settings | A dashboard that tries to *be* Map or Calendar inside itself |
| Dark PC desk — one theme, keyed to [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md) | Cream, LLC-era palette, or any legacy brand carryover |

## V1 must-have chrome

Four surfaces. Nothing else lands in V1.

| Surface | What it says | Truth source (local-only) |
|---|---|---|
| **Agents** | Which agents this desk knows about and what state they're in (idle · working · error · off) | Local agent registry / running-process view — no roster fetched from a cloud service |
| **Jobs** | Jobs the desk has launched or is tracking, with status | Local job store on this machine — the desk's own record |
| **Pulse** | A single-glance heartbeat — is the desk alive, when did anything last happen | Local event tick; never a synthesized "someone is doing something right now" |
| **Local-only honesty banner** | A small, permanent affordance that says: this is what *this desk* sees | Constant — not a toast, not a modal |

Each surface must read as legible with **zero** entries. Honest empty is a
first-class state, not a fallback.

### Dogfood note — empty is truth

Recorded from a Local + Eli pass on **this desk · Protocol City**:
Workspace·Agents rendered **empty** (`people.staff = 0`, `workers = [demo-worker]`,
`live = 0`). This is the intentional state after an agent reset / consume cut —
**not a hang, not a missing-roster bug, not a wiring gap.**

Rules that fall out of this evidence — a peel that breaks any of them fails V1:

- Empty Agents is a **valid honesty state** under local-only. Do not imply a
  missing roster; do not invent demo agents as chrome to fill the tile.
- V1 wiring for **agents · jobs · pulse** paints **real desk truth** — including
  zeros. Never fake activity, never fabricate an employed count, never
  synthesize a heartbeat to make the tile look occupied.
- **`demo-worker` alone ≠ employed pulse.** A placeholder worker on the
  registry is not evidence the desk is working; the pulse tile stays quiet
  until a real event ticks.
- The Writer empties in [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md) (`No agents`
  · `No open jobs` · pulse silent or `No pulse yet`) are the **PASS** copy for
  this dogfood state, not a fallback for a broken read.

## Later — chrome held (activity flags)

Everything below is the rot that Overview inherited from the prior wall
surface. Each row is a re-add candidate for a future peel, but only after
V1 has held green across two dogfood cycles and only if it does not
regress the "Mission Control voice" rule.

| Held — activity flag / chrome | Why held |
|---|---|
| Come-back stack as hero | Turns Overview into a recency wall; buries agents · jobs · pulse |
| Fake / synthetic activity ticks | Cloud-ops theater — violates local-only honesty |
| Wall-style event feed | Re-creates the Wall rot the reframe is peeling away |
| Any Map verb on Overview (`dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`) | Label lock — those verbs belong to Map |
| LLC cream palette / oneseollc carryover | Brand lock — PC dark desk only |
| Second landing surface (competing "home" card) | One landing lens; Overview is it |
| "Recent files" panel that duplicates Map's reader | Reader lives on Map, not here |
| Motion / cinema / continuous animation | Overview is a glass, not a screensaver |
| Fabricated collaborators / presence indicators | Local-only — no simulated peers |
| Gold "for you" beats / attention pulse | Belongs to the For-You inbox, not the landing lens |
| Cloud-ops summary tiles (queue depth, remote workers) | Cloud is not truth for this desk |
| Second projection of the same data (Map-lite tile) | If it wants to be Map, click Map |

## Invariants

Rules a peel cannot break without failing V1.

1. **Voice.** Mission Control voice only. Overview never speaks in Map
   verbs (`dig`, `lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`,
   `crumb`). If a component wants those words, it belongs on Map.
2. **Label lock.** BluePrint = desk · Overview = Mission Control glass ·
   Map = dig. No swap, no synonym, no "just this once."
3. **Local-only.** Every number Overview paints traces to a truth source
   on this machine. No "somewhere in the cloud, something is happening"
   surfaces. If the truth source is not local, the surface does not paint.
4. **Honest empty.** Agents · jobs · pulse each render legibly with zero
   entries. Empty is copy, not a spinner. Zeros **PASS** dogfood — the
   Dogfood note above is the reference case: `people.staff = 0` +
   `workers = [demo-worker]` + `live = 0` paints `No agents`, not a
   synthetic employed count.
5. **Landing.** Overview is the landing lens. It hands off to Map,
   Calendar, Settings — it does not try to be them.
6. **No rot re-entry.** The Later list is the rot ledger. A peel that
   re-lands any Later row must cite this section and prove it does not
   regress an invariant.
7. **PC dark theme.** No cream. No LLC-era palette. Tokens come from
   [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md) (see next).
8. **One landing lens.** Overview is the only surface with landing-lens
   behavior. Neither Map, Calendar, nor Settings competes for that role.

## Theme — hand off to Product design

This spec **does not invent Design tokens**. It names the need and hands it
to the Design room:

- Overview needs an [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md) companion
  (dark PC desk) that enumerates **keep · enhance · drop** decisions
  against the current landing surface's token set — the same shape Map
  is getting.
- Points Design at three token classes explicitly:
  1. **Surface** — the desk glass background, the Mission Control tile
     background, the honest-empty state background.
  2. **Voice** — the type ramp and weights for the four V1 surfaces
     (agents · jobs · pulse · local-only banner). Mission Control voice
     is quiet, not loud.
  3. **State** — the agent-state palette (idle · working · error · off)
     and the pulse tick. Must survive light/dark parity checks once dark
     is locked.
- Any Design token needed to paint V1 that is *not* named in the theme
  companion is a **spec gap**, not a peel decision. File it back to the
  Design room; do not invent one in code.

## Non-goals (say-so)

- Overview is **not a workspace author** — no join / adopt / seed-ops.
- Overview is **not a router** — it hands off to Map / Calendar /
  Settings; it does not embed them.
- Overview is **not a live event bus** — no SSE tape, no heartbeat that
  fabricates activity.
- Overview is **not a come-back stack** — recency is not the hero. The
  hero is agents · jobs · pulse.
- Overview is **not multi-workspace** in V1 — one desk, one Overview.
- Overview is **not a settings panel** — desk configuration lives in
  Settings.
- Overview is **not a cloud dashboard** — local-only is a load-bearing
  claim, not a decoration.

## Ship fence (for the peel that follows this spec)

For the record, so a future peel knows the frame it lands into:

- V1 Mission Control surface = **agents · jobs · pulse · local-only**.
  Nothing else.
- Peels open only **after** this INTENT is accepted **and** the Design
  theme pass returns [`OVERVIEW_THEME.md`](./OVERVIEW_THEME.md).
- Peel order will be published as a separate `OVERVIEW_V1_GLASS.md`
  (paint-and-quiet order first, then jobs · pulse, then filters), mirror
  of the Map DoD ladder.
- No Map JS changes. No dig re-plumbing. This is a landing-lens peel,
  not a Map peel.
