# Finished Product Inventory — KEEP / RESTORE / DROP / NET-NEW

**Status:** DRAFT · Eli / CoS + Product design room accept · **addendum**, not a
new peel. Siblings: [`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md) ·
[`MAP_V1_GLASS.md`](./MAP_V1_GLASS.md) · `MAP_V1_THEME.md` (Design room —
forthcoming).

## Purpose

Every prior BluePrint surface, one ledger. Which behaviors are in V1 now,
which come back Later, which never come back, and which are net-new folds from
the Product design room (Brand · Designer · Writer). One place so no future
peel accidentally re-lands rot or re-invents a fold that already has a home.

## Label lock (say-so, so this doc doesn't drift)

**BluePrint** = the desk. **Overview** = the Mission Control glass (landing
lens). **Map** = dig (glass over a folder). Brand is **Protocol City** (PC
as acronym elsewhere in this doc). Overview never borrows Map verbs (`dig`,
`lot`, `hub`, `fan`, `trail`, `md-viewer`, `binder`, `crumb`) and Map never
borrows Overview verbs (`agents`, `jobs`, `pulse`). No LLC / cream /
stranger-marketing carryover.

---

## 1) KEEP in V1 now

The four-lens spine, the Map surfaces that already shipped green, and the
Overview surfaces the INTENT spec locks. Nothing else is V1.

| Surface | Row | Source of truth |
|---|---|---|
| **BluePrint chrome** — four-lens spine (Overview · Map · Calendar · Settings) | Suite nav | Lens registry |
| **Map** — hub + lots paint | `MAP_V1_GLASS.md` DoD 1 | `/api/map/tree` (binder + top-level lots) |
| **Map** — empty pan · zoom · reset | DoD 2 | `MapViewState` |
| **Map** — dig (lot · hub · child) with one trail | DoD 3 | `MapViewState.dig` |
| **Map** — MD viewer overlay (open on `.md`, Esc / × / backdrop close) | DoD 4 | `/api/file?render=html` |
| **Map** — View Options filters (Managed · Unmanaged · Hidden) | DoD 5 | Server managed/hidden state (Cellar dig 0.1.50 includes VO; wired in `workspace_map_app.v1.js`) |
| **Map polish (shipped)** — focus ring, hub label contrast, dense dig fan, md-viewer wrap | Post-shell polish | In-file CSS |
| **Overview** — Agents surface (idle · working · error · off) | `OVERVIEW_INTENT.md` V1 | Local agent registry / running-process view |
| **Overview** — Jobs surface (launched · tracked · status) | INTENT V1 | Local job store |
| **Overview** — Pulse (single-glance heartbeat) | INTENT V1 | Local event tick |
| **Overview** — Local-only honesty banner | INTENT V1 | Constant affordance |
| **Calendar** — week list + honest empty `No events` + event rows (title · when · source · status) + detail sheet (title · time · notes) | `OVERVIEW_CALENDAR_SETTINGS.md` V1 | `/api/calendar/events` ← `<binder>/.blueprint/calendar.json` |
| **Settings** — Desk · Appearance · Privacy/Local-only · About/Cellar (brew tip) | `OVERVIEW_CALENDAR_SETTINGS.md` Glass DoD | `/api/settings/desk` + `/api/overview/pulse` cellar_tip |

Everything on this list must read legible with **zero** entries. Honest empty
is first-class.

---

## 2) RESTORE Later — activity flags

The prior BluePrint surfaces that have a real home once V1 holds green across
two dogfood cycles. Held, not deleted. Re-add is one row at a time, each
citing which V1 invariant it must not regress.

| Prior surface | Home lens | Why held |
|---|---|---|
| FAST porch + fast-cover | Map | First-paint theater; collided with `#lots` for hits |
| Folder interior seats (You · hands · jobs · work · papers · instr) | Map | Seat pack collided with dig hits |
| Stems / spokes between hub and lots | Map | Layout ornament — dig reads without it |
| Legend | Map | Explains chrome not yet present |
| Expand FAB (top-level children everywhere) | Map | Density mode — separate |
| Dig-trail glyphs · dig-tier foundation weight | Map | Secondary palette |
| Agents Activities rail (map side) | Map (Later) | Roster stream — Overview already owns "agents" voice; Map version is a live badge, deferred |
| Map — WO-open passthrough (reader → `/ticket?id=…`) | Map (Later) | Option B Map V1 did not ship WO-open; suite router hop is a separate peel |
| WO tape · WO buckets · folder papers panel | Map | Store poll; not truth-of-folder |
| Searchlight | Map | Search over cinema; needs live index |
| Six `inspect-*` sidebars (project · person · you · workspace · orbit · shell) | Split — see below | Reader is V1's only sidebar |
| Cam / fit animations | Map | Ease + easings; V1 snaps |
| SSE tape · pulse · heartbeat · reconcile (map live loop) | Map (Later) | Continuous cinema over live engines |
| Outline projection | Map | Second row-oriented view; polish once dig holds |
| Theater demo dialog | Map | Demo scaffolding |
| Skills library corner panel | Map / Overview | First-class **AGENTS.md / skills / PROGRAMS** re-lands as a Map surface (see NET-NEW) |
| Landing surface: for-you / comeback stacks | **Not restored on Overview** — see DROP row | For-you inbox is a separate lens candidate |
| Wall — project filter · density · notices · WO search · face boxes · note · regroup · parked hop · since-window | **Not restored as Overview** — parked | If any row returns it lands on its own lens, not on the landing glass |

Split of the six inspects: **person → `/person` route** (already separate); 
**you → Overview voice** (already there in Agents + Pulse); **project ·
workspace · orbit · shell → do not restore** (superseded by Map reader +
Overview spine).

---

## 3) DROP / never return

Union of the Product design room's DROP calls (Brand + Designer + Writer) plus
the rot the reframe named. If a future peel proposes any of these, this row
is the veto.

| Dropped surface / behavior | Room | Why never |
|---|---|---|
| Map-as-ticket-database | Brand | Map is a glass over a folder; tickets live in `/ticket` |
| Workspace creator on Map (join / adopt / seed-ops paint) | Brand + Writer | Found / adopt / hire live in CLI + `wl` MCP; Map is read/route only |
| Outline as a tree that competes with dig | Brand + Writer | Two projections of the same data; dig wins |
| LLC cream palette / oneseollc carryover | Brand + Designer + Writer | Dark PC desk only |
| Stranger marketing surfaces on the desk | Brand | Desk is for the operator, not a landing page |
| Map painted to look like Mission Control | Designer | Label lock — Map is dig, not MC |
| Overview painting lots / borrowing Map verbs | Designer | Label lock — MC voice only |
| Activity to "compensate" for a slow base paint | Designer | Base paints and dig work before any chrome lands |
| Fake / synthetic "N agents busy" tickers | Writer | Local-only honesty — no fabricated presence |
| Fabricated collaborators / presence indicators | Writer | Same rule; there are no simulated peers |
| Cloud-ops summary tiles (remote queue depth · remote workers) | Writer | Cloud is not truth for this desk |
| Come-back stack as landing hero | (reframe) | Turns Overview into a recency wall; buries agents · jobs · pulse |
| Gold "For You" beats on the landing lens | (reframe) | Belongs to the For-You inbox, not Overview |
| Wall-style event feed as Overview | (reframe) | Re-creates the Wall rot |
| Second landing surface (competing "home" card) | (reframe) | One landing lens; Overview is it |
| "Recent files" panel on Overview | (reframe) | Reader lives on Map |
| Continuous cinema on cold boot | (reframe) | V1 legibility with zero live inputs |
| 28k-line Map host | (reframe) | If the V1 host exceeds ~2k lines it has drifted |
| Second hit router · sibling dig cache · fan-sig locks | (reframe) | One `MapHitRouter`, one `MapViewState.dig` |

---

## 4) NET-NEW — Product design room folds

Brand · Designer · Writer already delivered NET-NEW surfaces in the Product
design room. Folded here so both lenses can see what's coming and Design can
mark which need `OVERVIEW_THEME.md` / `MAP_V1_THEME.md` before a peel opens.

Legend for **Theme?**: **Y** = needs a Design token pass before peel · **N** =
paints inside the surfaces already themed.

| # | NET-NEW | Overview column | Map column | Theme? |
|---|---|---|---|---|
| 1 | WO counts by state (Waiting on you · Ready · Blocked · Employed · Idle) | Card on the Jobs surface — labels are the copy | — | **Y** (state palette must survive light/dark parity) |
| 2 | WorkForce pulse — Employed / Idle / Blocked | Sub-band under Agents | — | **Y** (agent-state palette shared with #1) |
| 3 | Next-action strip — one verb + one object | Below the Jobs card ("plant a flag", "read `AGENTS.md`", "open the ticket") | — | **N** (uses body type ramp) |
| 4 | Plant-a-flag CTA → Map | Route chip on the Next-action strip; hands off, does not embed Map | Companion — the flag lands on a lot | **Y** (chip token — quiet accent, not a marketing button) |
| 5 | Cellar / brew version + SoT footer | Quiet footer: `BluePrint 0.x · Cellar` + SoT honesty line | — | **N** (footer voice — muted) |
| 6 | City heartbeat — quiet last-plant / dig / merge | Pulse tick; only when a real event fired | — | **N** (uses pulse token from INTENT) |
| 7 | Empty copy — "None waiting" (not a spinner) | Every V1 surface honest-empty state | — | **N** (voice, not tokens) |
| 8 | Flag plant / adopt on a lot | — | On a selected lot; not a Map-paint mode | **Y** (selected-lot ring + flag glyph) |
| 9 | FS + git badges — Dirty · Clean · Untracked | — | Small badge on lot; hidden until the snapshot returns git shape | **Y** (badge palette — three states, dark PC) |
| 10 | Selected-lot sheet — **Open WO · Plant flag · Read `.md`** | — | Small side sheet on selected lot; hands off, not a rail | **Y** (sheet chrome — matches MD viewer weight) |
| 11 | First-class **AGENTS.md · skills · PROGRAMS** | Named in Agents / Jobs voice | Reader recognizes them as first-class `.md` targets (no role classifier in V1 — file names carry) | **N** (voice) |
| 12 | Quiet last-agent-touch — only when real | — | Optional badge on lot; hidden by default | **Y** (share agent-state palette from #2) |
| 13 | Dig trail = crumbs only (path) | — | Trail chrome; no glyphs, no tier weight | **N** (uses chrome text) |
| 14 | Contracts named by filename (not by ticket schema) | Copy rule everywhere | Copy rule everywhere | **N** (voice) |

**Theme dependency:** rows marked **Y** are peel blockers until Design returns
the relevant `*_THEME.md`. Rows marked **N** paint inside surfaces already
themed by V1 tokens.

**Cross-lens rule (say-so):** the CTA on row 4 is a **route chip**, not an
embed. Overview hands off to Map. Overview does not paint lots. Map does not
paint agents · jobs · pulse. Every NET-NEW row lives on exactly one lens.

---

## Invariants this addendum locks

1. **One inventory.** This doc is the single ledger for KEEP / RESTORE / DROP
   / NET-NEW across BluePrint. A peel that proposes a re-add must cite the
   row it's re-landing.
2. **Restore rate.** One RESTORE row per peel, only after V1 has held green
   across two dogfood cycles. Never bundle a re-add with another peel.
3. **DROP is durable.** A dropped row does not come back with a rename. If the
   need it addressed is real, it lands as a NET-NEW row here first.
4. **NET-NEW needs Theme.** Rows in section 4 marked **Y** wait for the
   `OVERVIEW_THEME.md` / `MAP_V1_THEME.md` companion before a peel opens.
5. **Label lock stands.** BluePrint = desk · Overview = MC glass · Map = dig.
   PC dark only.

## Non-goals (say-so)

- This addendum does not open a peel. It ratifies which peels are legal.
- This addendum does not invent Design tokens. It names which NET-NEW rows
  need them and where they belong.
- This addendum does not add a fifth lens, a second landing, or a shared
  vocabulary between Overview and Map beyond what the two INTENT specs
  already lock.
