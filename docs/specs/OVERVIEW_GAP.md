# Overview Gap — KEEP / REWRITE / DELETE / NEW

**Status:** DRAFT · design-first · pairs with
[`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md). Describes the gap between the
current landing surface (a wall-shaped `.html` face the desk still boots
into on the private side) and the V1 Mission Control glass this INTENT
defines. Behavior-only inventory — no personal paths, no ticket lists.

## Legend

| Verdict | Meaning |
|---|---|
| **KEEP** | Behavior belongs in V1 as-is |
| **KEEP-TRIM** | Behavior belongs in V1 but strip the Wall-era chrome around it |
| **REWRITE** | Idea is right, the current shape can't hold V1's Mission Control voice |
| **DELETE** | Not V1; the peel drops it from the landing lens for good, or files it to a non-Overview lens |
| **DEFER** | Not V1, not deleted — parked behind a flag until a Later re-add cites the INTENT invariants |
| **NEW** | V1 surface Overview does not have today |

## Current landing surface — behavior inventory

The current landing surface behaves like a Wall — a general-purpose event
board with come-back stacks, recency lists, and a mixed voice pulling from
half a dozen upstreams. Below is what it *does today*, sorted by whether
V1 wants that behavior.

### Behaviors V1 wants — keep or reshape

| Current behavior | V1 verdict | Notes |
|---|---|---|
| A landing screen exists and is what the desk boots into | **KEEP** | Overview stays the landing lens (INTENT §Four-lens spine) |
| Some form of agent presence is shown | **KEEP-TRIM** | Reduce to the four V1 states: idle · working · error · off. Drop synthesized "someone is here" affordances |
| Some form of jobs / tasks is shown | **REWRITE** | Reshape from a mixed "recent things" list to a jobs-owned surface with clear state per job. Drop generic activity rows |
| A pulse / heartbeat concept exists | **REWRITE** | Reduce to a single-glance tick — is the desk alive, when did anything last happen. Not a cinema loop |
| Empty states exist | **KEEP-TRIM** | Promote empty to a first-class state. Rewrite copy to Mission Control voice; drop placeholder cards that make it look like content is loading |

### Behaviors V1 rejects — held or deleted

| Current behavior | V1 verdict | Why held (INTENT invariant) |
|---|---|---|
| Come-back stack rendered as the hero card | **DELETE from landing** | Recency is not the hero. Agents · jobs · pulse is the hero (§V1 must-have) |
| Wall-style mixed event feed | **DELETE from landing** | Recreates the Wall rot; violates Mission Control voice |
| Synthesized / fake activity ticks to keep the surface warm | **DELETE** | Violates local-only honesty (§Invariants 3) |
| Cloud-ops summary tiles (queue depth, remote workers, ambient "cloud is busy") | **DELETE from landing** | Local-only invariant — the desk only paints what it can see on this machine |
| Fabricated collaborators / presence indicators | **DELETE** | Local-only — no simulated peers |
| Recent-files or MD reader panel duplicating Map | **DELETE from landing** | Reader lives on Map (see `MAP_V1_GLASS.md` §MD viewer). Landing lens does not embed a second reader |
| Map-lite tile — a small spatial preview of the folder | **DELETE from landing** | Second projection of the same data; if the operator wants Map, they click Map |
| Cinema / motion loop on the landing surface | **DELETE from landing** | Overview is a glass, not a screensaver |
| Gold "for you" beats sitting on top of the landing card | **DEFER** | Belongs to the For-You inbox surface, not the landing lens |
| Roster fetched from a cloud service and painted here | **DELETE from landing** | Local-only. Any roster must come from a local truth source or not paint |
| Settings-shaped controls on the landing surface (theme, prefs, workspace switch) | **DELETE from landing** | Settings is its own lens |
| Calendar-shaped rows (scheduled runs, upcoming firings) on the landing surface | **DELETE from landing** | Calendar is its own lens; Overview may quietly hand off, not host |
| LLC-era cream / oneseollc-era palette carryover | **DELETE** | PC dark theme lock (§Invariants 7). Design owns tokens |
| Mixed vocabulary (borrowing Map's `dig` / `lot` / `hub` / `fan`) | **DELETE** | Label lock (§Invariants 1–2). Mission Control voice only |

### Behaviors V1 needs that don't exist today

| New behavior | Role | Home |
|---|---|---|
| Local-only honesty banner | Permanent affordance stating: this is what *this desk* sees | Landing lens, always visible |
| Agent-state palette per agent (idle · working · error · off) | Legible state pill / dot per agent — not a mood word | Agents surface |
| Jobs surface owned by the desk's own job store | Reads the local job record; paints one row per job with a clear state | Jobs surface |
| Single-tick pulse (is the desk alive, when did anything last happen) | One glyph or line — not an animated loop | Pulse surface |
| Honest-empty copy for each of the four surfaces | Written by Product design (Writer), not filled with spinners | All four V1 surfaces |
| Quiet hand-off to Map / Calendar / Settings | Clear, minimal navigation — Overview does not embed the other lenses | Landing lens frame |

## Summary — Wall → Mission Control

The gap is not a code gap; it is a **voice and surface gap**. The current
landing behaves like a Wall trying to be everything at once. V1 makes it
the Mission Control glass: four surfaces, one voice, local-only, honestly
empty.

| Class | Rough behavior count | Fate |
|---|---|---|
| KEEP | 1 | Landing-lens role |
| KEEP-TRIM | 2 | Agent presence, empty states |
| REWRITE | 2 | Jobs, pulse |
| DELETE from landing | 10 | Wall-era rot (come-back stack, cinema, mixed feed, Map-lite, cloud tiles, second reader, fake activity, LLC palette, mixed vocabulary, settings on landing) |
| DEFER | 1 | Gold "for you" beats (lives elsewhere) |
| NEW | 6 | Local-only banner, agent-state palette, desk-local jobs, single-tick pulse, honest-empty copy, quiet hand-off |

## Ship fence (mirrors INTENT)

- No code peels in this PR. Behaviors, not files.
- No Map JS changes. No dig re-plumbing.
- Peels open only after this INTENT is accepted **and** the Design theme
  pass returns `OVERVIEW_THEME.md`.
