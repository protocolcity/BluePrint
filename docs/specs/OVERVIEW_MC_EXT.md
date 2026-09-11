# Overview Mission Control — extensions (01c · 02c · 03d)

**Status:** PEEL landing · extends sealed [`OVERVIEW_INTENT.md`](./OVERVIEW_INTENT.md) (#38) · **not a Wall restart**
**Mocks:** Brand PASS `ext-01c` · `ext-02c` · `ext-03d`
**Live base:** Overview V1 on Cellar `:8803` (`0.1.50_6`, tip `#43`)

## Label lock (unchanged)
BluePrint = desk · Overview = Mission Control glass · Map = dig. Prefer **Local desk** / **this desk**. Never `workspace` on the honesty banner. Protocol City = two words.

## Never-lie DoD (load-bearing)
- Consume ≠ MANAGED
- Private personal SoTs stay off the public install face
- No private ProtocolCity as the install face
- No fake-green theater; missing heartbeat ≠ green
- Cellar tip = brew app version only (not private city SHA)
- Cloud builders = **outbound links**, not fake local agents

## Ext-01c — Overview home (Brand PASS)
Extend live three-tile V1:

1. **Four-lens top nav** — Overview · Map · Calendar · Settings. Overview is the current lens. Bottom hand-off chips are folded away — the top nav is the single lens voice. No Dig verbs.
2. **Local desk banner** — pill affordance under the top nav that says **Local desk**. Never `workspace`. Dot uses the working-state green.
3. **Agents tile** — honest empty `No agents`; when present, one row per agent with state dot (idle · working · error · off). Under the roster, a divider then **+ Cloud builders** / **+ Remote builders** rendered as **outbound links** — never painted as local employed agents.
4. **Jobs tile** — honest `No open jobs` copy when the bucket is empty; **Waiting · Ready · Blocked** counts shown below (zeros PASS). Bucket dots are muted / working-green / error-red.
5. **Pulse tile** — named **local** heartbeats: **FS Watch · Builder · Cellar · Index · Sync** with state text and a `HH:MM:SS` last-tick. Below a divider: **Cellar tip** (brew face, e.g. `blueprint 0.1.50_6`) and **Last tick**. Missing heartbeat ≠ green — an absent row paints `off` grey, not working green.
6. **Quiet footer strip** — mirrors the pulse heartbeats in a single line (`FS Watch · Watching   Builder · Idle   Cellar · Connected …`) with an **All systems quiet** trailing label. Never lies — a missing/absent heartbeat paints muted, not green.

## Ext-02c — Project card (Brand PASS)
On project select (local desk truth):

1. **Title + path voice** — folder icon · project name; below, `Project: <slug> · Path: on this desk` (never cloud path theater, never `workspace`).
2. **Honest badges** — **Local write · Consume · Upstream · Local-only**. A badge is *lit* only when true; a badge that is off paints muted with an "off" affordance. `Consume ≠ MANAGED` — Consume is off unless the desk has an active consume lease.
3. **Charter excerpt** — pulled from `CHARTER.md` on this desk; italic quote block.
4. **Actions** — Open Charter · Plant flag · Read AGENTS.md. Local buttons; no outbound theater.

## Ext-03d — Charter + Crew (Brand PASS — no longer HOLD)
Charter drawer + Crew paint, over the Agents · Jobs · Pulse spine — the three peer tiles stay:

1. **Charter drawer** — right-side panel with operator-only voice OK (e.g. "private BluePrint cell"). Sections: **Charter for Local Desk · Purpose · Scope · Invariants**. Stranger / marketing voice stays off.
2. **Crew** — Mini WorkForce rows inside the Agents tile — one row per crew member with state dot (idle · working · error · off). Below, a **Cloud builders** group renders **only** as outbound links (never as employed local agents).
3. **Never-lie footer** — the Charter drawer closes with `Cellar app tip <version> — not private Protocol City install`. The Cellar tip is the brew face, never the private ProtocolCity SHA.
4. **Peer tiles preserved** — the drawer sits **alongside** Agents · Jobs · Pulse, never inside them. On narrow viewports the drawer stacks below, still not replacing the three-tile spine.

## Peel fence
- CLI under `~/.bots/blueprint` → `protocolcity/BluePrint` → Path B Cellar after glass DoD
- HARD HOLD `:8801` suite Map (0.1.47 pin)
- No Map JS · no Wall · no LLC cream · no sparklines · no cinema

## Soft polish (Brand)
- Outbound link voice for every cloud / remote builder
- Desk not workspace across every visible string
- One shared 2px focus ring across every interactive element

## APIs extended
Wire shape locked by this spec (extends `overview_state.py`):

| Route | Body |
|---|---|
| `GET /api/overview/agents` | `{"agents": [{name,state}], "cloud_builders": [{name,url}], "remote_builders": [{name,url}]}` |
| `GET /api/overview/jobs`   | `{"jobs": [{name,state}], "buckets": {"waiting":n,"ready":n,"blocked":n}}` |
| `GET /api/overview/pulse`  | `{"heartbeats": [{name,state,last_at}], "cellar_tip": "<brew face>", "last_at": null\|str, "ticks": [...]}` |
| `GET /api/overview/project` | `{"title","project","path_hint","badges":{local_write,consume,upstream,local_only},"charter_excerpt"}` or `{}` when nothing selected |
| `GET /api/overview/charter` | `{"title","sections":[{heading,body}],"footer"}` or `{}` when not opened |

`--cellar-tip` on `serve.py` (default `blueprint 0.1.50_6`) is the brew face injected into `/api/overview/pulse`. `--fixture` for project/charter fixtures is tests / demo only; default serve stays empty.
