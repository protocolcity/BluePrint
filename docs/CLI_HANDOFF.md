# CLI session handoff — BluePrint desk

One pasteable session law so a Claude / Grok CLI session on the Mini can keep
building the cleaned four-lens desk (Overview MC · Map V1 · Calendar · Settings)
without a Grok Bot relay in the middle.

---

## 0. Read this first

This file is **session law for a builder CLI**. Paste it (or point the session at
it) at the top of a session, then follow the read order in §2 before touching a
single file. Everything below is a lock, not a suggestion.

---

## 1. Repo — source of truth

| Thing | Value |
|---|---|
| SoT repo | **`protocolcity/BluePrint`** (Path B — public repo is the law) |
| Checkout on the Mini | **`~/OneSeo/ProtocolCity-BluePrint`** |
| Isolated agent HOME | **`~/.bots/blueprint`** — prefer it **when present** |
| Workspace / binder | **`~/OneSeo`** |

**Rule:** if `~/.bots/blueprint` exists, run the session under that isolated HOME.
Otherwise just open the checkout at `~/OneSeo/ProtocolCity-BluePrint` directly.
Either way, the code and the Specs you edit live in that checkout — never in a
scratch copy, never in the binder.

`protocolcity/BluePrint` is the only repo that carries this desk. Private
ProtocolCity work is **not** in scope for a builder session and its SHAs never
appear here (see §6).

---

## 2. Spec-first read order

Specs are law. Read them in this order, top to bottom, before proposing a peel.
Links are relative to this file (`docs/CLI_HANDOFF.md`).

1. [`specs/ALWAYS_WORK_PROCESS.md`](specs/ALWAYS_WORK_PROCESS.md) — the one
   straight loop. No second loop, no mill, no hygiene siblings.
2. [`specs/OVERVIEW_INTENT.md`](specs/OVERVIEW_INTENT.md) +
   [`specs/OVERVIEW_THEME.md`](specs/OVERVIEW_THEME.md) +
   [`specs/OVERVIEW_V1_GLASS.md`](specs/OVERVIEW_V1_GLASS.md) — what Mission
   Control *is*, what it looks like, and the glass DoD it must pass.
3. [`specs/OVERVIEW_MC_EXT.md`](specs/OVERVIEW_MC_EXT.md) — the MC extension
   surface (Agents · Jobs · Pulse projectors).
4. [`specs/OVERVIEW_CALENDAR_SETTINGS.md`](specs/OVERVIEW_CALENDAR_SETTINGS.md)
   — the Calendar + Settings lens IA. **This is the next legal deepen** (§5).
5. [`specs/MAP_V1_GLASS.md`](specs/MAP_V1_GLASS.md) +
   [`specs/MAP_HUB_CROWDING_GUIDE.md`](specs/MAP_HUB_CROWDING_GUIDE.md) — Map
   dig glass and the hub density stack (orbit · multi · hide labels).
6. [`specs/FINISHED_PRODUCT_INVENTORY.md`](specs/FINISHED_PRODUCT_INVENTORY.md)
   — what is already finished. Check here before you "build" anything.
7. [`../overview/v1/RUNNING.md`](../overview/v1/RUNNING.md) +
   [`../map/v1/RUNNING.md`](../map/v1/RUNNING.md) — how to actually run each
   lens and what the DoD checks look like in a browser.

If a Spec and live code disagree, the Spec wins and the gap is the work order.

---

## 3. Lane locks (ports)

| Port | Lane | Lock |
|---|---|---|
| **:8801** | suite Map (`blueprint serve`) | **HARD HOLD at PyPI 0.1.47.** No suite Map peels. Do not touch `map/v1/` shipping behaviour on this lane. |
| **:8802** | `blueprint-map` | V1 Map shell against the binder. |
| **:8803** | `blueprint-overview` | Four-lens desk. **MUST keep `--binder ~/OneSeo`.** |

**The `--binder` lock matters.** Without `--binder`, Overview still boots all
four lenses but Agents / Jobs paint honest-empty forever — it reads
`<binder>/.blueprint/overview.json` and `<binder>/.blueprint/calendar.json` live.
A LaunchAgent or login wrapper that runs plain `blueprint-overview` with no
`--binder` is a bug, not a config choice. Map's LaunchAgent already passes
`--binder`; keep Overview's in the same shape.

:8801 being held at 0.1.47 is why Map work happens on :8802. Do not "fix" :8801
to match — that is a separate, currently-frozen lane.

---

## 4. Sealed Cellar

**Sealed: `0.1.50_12` @ tip `4cc69b3e`** — covers PRs **#50–#55**.

Soft nits still **parked** against that seal (not this Map peel):

- Calendar lead-flex
- Settings cold tip

Map nits **dig-fan** and **md-clip** land on Path B `main` after the crowding
follow-up peel; Cellar still shows them until the next drink.

Parked means *do not re-open them as drive-by fixes*. They are known, they are
written down, and they wait for their own work order.

---

## 5. Next legal deepen

**Calendar + Settings V1**, built against
[`specs/OVERVIEW_CALENDAR_SETTINGS.md`](specs/OVERVIEW_CALENDAR_SETTINGS.md), in
this order:

1. **Honest empty** — the lens paints truthfully with no data. No shimmer, no
   spinner, no fabricated rows.
2. **Local truth** — read the binder's local files; still honest when they're
   missing or malformed.
3. **Design glass DoD** — pass the glass checks in the Spec and in
   [`../overview/v1/RUNNING.md`](../overview/v1/RUNNING.md).
4. **Cellar tip bump** — via **Github Coordinator / homebrew-tap**, only after
   the glass DoD is green.

The **only** other legal option is inventory **RESTORE** — and only *after* V1
stays green. Not instead of it, not alongside it.

Calendar and Settings are **lenses**, not Overview embeds. Overview never hosts a
Calendar feed or a Settings panel.

---

## 6. Fence — do not cross

- **No Wall.**
- **No LLC cream.** Protocol City (two words) is the brand. Not an LLC, not a POS
  product name.
- **No private ProtocolCity SHA as a Cellar tip.** The sealed tip is `4cc69b3e`
  and it is public.
- **No Map verbs on Overview.** `dig` · `lot` · `hub` · `fan` · `trail` ·
  `md-viewer` stay off Overview, Calendar, and Settings chrome.
- **No inventing peels.** If it isn't in a Spec, it isn't work. Check
  [`specs/FINISHED_PRODUCT_INVENTORY.md`](specs/FINISHED_PRODUCT_INVENTORY.md)
  first.
- **No blueprint service start/stop on the Mini.** `bootout` / `bootstrap` only.

---

## 7. Ship

- Open a **PR to `protocolcity/BluePrint`**.
- In the PR body, report **which Spec rows closed** — by name, not by vibe.
- **Glass DoD before Cellar drink.** The tip does not move until the glass is
  green.

---

## 8. Workspace law vs builder law

`~/OneSeo/AGENTS.md` is **consume-only operator law** — it governs how the
workspace is operated, and a builder session reads it without editing it.

**Builder sessions take their law from the Specs in the BluePrint checkout**
(`docs/specs/`). When operator law and Spec disagree about what to *build*, the
Spec wins; when they disagree about how to *operate the Mini*, operator law wins.

---

## 9. How to start a session

```bash
# 1. Prefer the isolated agent HOME when it exists
[ -d ~/.bots/blueprint ] && export HOME=~/.bots/blueprint

# 2. Open the checkout (this is the SoT working tree)
cd ~/OneSeo/ProtocolCity-BluePrint
git status                       # expect clean before you start

# 3. Read the Specs in order (§2) before touching anything
ls docs/specs/
#   ALWAYS_WORK_PROCESS → OVERVIEW_INTENT + OVERVIEW_THEME + OVERVIEW_V1_GLASS
#   → OVERVIEW_MC_EXT → OVERVIEW_CALENDAR_SETTINGS
#   → MAP_V1_GLASS + MAP_HUB_CROWDING_GUIDE → FINISHED_PRODUCT_INVENTORY
#   → overview/v1/RUNNING.md + map/v1/RUNNING.md

# 4. Serve the four-lens desk — --binder is NOT optional on this lane
python3 overview/v1/serve.py --port 8803 --binder ~/OneSeo
# → http://127.0.0.1:8803/          Overview (Mission Control)
# → http://127.0.0.1:8803/map       Map V1 dig
# → http://127.0.0.1:8803/calendar  Calendar week list
# → http://127.0.0.1:8803/settings  Settings groups

# 5. Map V1 shell on its own lane (separate terminal)
python3 map/v1/serve.py --binder ~/OneSeo --port 8802

# :8801 is the suite Map lane — HARD HOLD at PyPI 0.1.47. Leave it alone.
```

Installed-CLI shape, same locks:

```bash
blueprint-overview --binder ~/OneSeo --port 8803
blueprint-map      --binder ~/OneSeo --port 8802
```

Then read the DoD steps in [`../overview/v1/RUNNING.md`](../overview/v1/RUNNING.md)
and check them in the browser before you call anything done.
