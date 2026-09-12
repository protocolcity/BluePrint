# Demo runbook — Map rail + theater acts (pc-471)

Parent: **pc-466**. Matrix: [`docs/specs/MAP_THEATER_MATRIX.md`](../../docs/specs/MAP_THEATER_MATRIX.md).
Register: [`docs/specs/SUITE_VOCABULARY.md`](../../docs/specs/SUITE_VOCABULARY.md) — use **project folder** (not "house"), **Agent activities** (not "agent rail"), **Work orders** (not "tickets").

## Click-through tutorial catalog

`MapTheaterDemo` ships a **12-beat catalog** of pre-scripted cinema beats — no live engine needed.
Each beat has an `id`, an `act` title shown in the step indicator, and a `look` string shown in the caption panel.

| id | Act title | What it demonstrates |
|---|---|---|
| `file` | 1 · File | Work order filed: YOU card + Work orders strip + project folder open count |
| `claim` | 2 · Claim | Agent claimed: Agent activities goes live + agent name under project folder |
| `comment` | 3 · Comment | Comment posted: Work orders rail row pulses + project folder ink mark |
| `label` | 4 · Label | Label applied: work order chip flash + label pop on project folder |
| `for_you` | 5 · For You | Gate on You: YOU badge gold + padlock badge + gold fill on project folder |
| `gate_clear` | 6 · Gate clear | Gate released: padlock releases + gold fill clears |
| `count_up` | 7 · Open count ↑ | Open count rises: project folder badge pulses |
| `close` | 8 · Close / signed | Work order closed: signed pulse on project folder + row leaves Work orders rail |
| `dispatch` | 9 · Dispatch sprint | Dispatch: Agent activities sprints + project folder green ring |
| `hire` | 10 · Hire / materialize | Agent hired: Agent activities gains row + new seat materializes on project folder |
| `fault` | 11 · Fault flash | Fault: Agent activities fault chrome + red ring on project folder |
| `leaves` | 12 · Unhire / leave | Agent removed: seat departs project folder + Agent activities row removes |

Console: `MapTheaterDemo.list()` shows all ids. `MapTheaterDemo.step("file")` runs a single beat.

The Acts below (1–6) are the **live engine demo** — you trigger real events with `wl` / MCP and the glass responds. The click-through catalog above is cinema grammar only; it does not create WorkLane tickets.

## Full cinema pause (validate) — pc-887

Before judging whether rings/rails mean the right thing, freeze motion:

1. **Click the LIVE badge** (top-right) → reads **PAUSED**
2. Or Settings · Map theater · **Pause cinema (validate)**
3. Or `?theater_pause=1` · `MapTheaterDemo.pause()`
4. Click badge again / **Resume cinema** to restore live motion

Paused holds decorative FX **and** SuiteLive thrash so the static scene is readable.

## One-click tutorial (pause → step-through)

Live engine theater can drown a walkthrough. Use **tutorial mode**:

1. Open Map at **:8801** (hard-refresh once after pull).
2. Settings · Map theater · **Run theater demo** — or
   `http://127.0.0.1:8801/workspace-map?theater=1`
3. Map **pauses live FX**, **hides the legend**, soft-zooms the target house.
4. **Your pace:** click **Next** (or the caption card, **Space**, **→**, **Enter**)
   for each beat. Click **← Back** (or **←**) to replay the previous beat.
   Use the **Beat** dropdown to jump to any scene. **Finish** after the last. **Stop** / **Esc** exits early.
5. Caption sits **under the mast (top)**. Exit restores camera + legend + live.

Timed auto (optional): `?theater_demo=1&auto=1` or `MapTheaterDemo.autoplay()`.

Console API:

```js
MapTheaterDemo.play()           // click-through (default)
MapTheaterDemo.next()           // advance one beat (or close on last)
MapTheaterDemo.prev()           // step back one beat (disabled on beat 1)
MapTheaterDemo.goto(0)          // jump to beat by 0-based index
MapTheaterDemo.goto("claim")    // jump to beat by id (starts session if cold)
MapTheaterDemo.autoplay()       // timed (~2.8s)
MapTheaterDemo.autoplay({ gapMs: 4000 })
MapTheaterDemo.step("file")     // single beat session
MapTheaterDemo.list()
MapTheaterDemo.stop()
MapTheaterDemo.pause() / .resume()
```

This is **cinema grammar only** (tutorial) — it does not invent WorkLane tickets.
For engine-truth cabling, still run Acts 2–5 via `wl` / MCP below.

## Prereqs

- Suite glass **:8801** Map open (hard-refresh once after pull)
- WorkLane + WorkForce + citylens up (`blueprint serve --with-engines`)
- At least one project with a desk store (open badges)
- Left rail visible: **YOU** · **Agent activities** · **Work orders**

## Act 1 · Clock (schedule)

| | |
|---|---|
| **Trigger** | Wait for an agent in T−3min approach (blue pill/bar) → live |
| **Look left** | Agent card: Approaching · N% → **LIVE** + work line |
| **Look map** | Blue ring → green ring; name under folder |
| **Say** | “The schedule is on the body and the ledger — same truth.” |

## Act 2 · File (human origin)

| | |
|---|---|
| **Trigger** | `wl create` / MCP create / chat file onto a product store |
| **Look left** | **YOU card pulses**; Work orders row **inserts** + flash |
| **Look map** | Project open count; short place pulse; optional slip from YOU card |
| **Say** | “Filing starts with You, lands on the work strip, then the place.” |

## Act 3 · Claim

| | |
|---|---|
| **Trigger** | MCP claim / agent claims |
| **Look left** | WO → in progress; agent card **live** |
| **Look map** | Hand under folder; green ring; co-highlight ~1s |
| **Say** | “Claim couples the order and the hand.” |

## Act 4 · For You

| | |
|---|---|
| **Trigger** | Human-gated ticket / attention tray |
| **Look left** | YOU pill count; filter **For You** gold |
| **Look map** | Gold bubble fill |
| **Say** | “What waits on the human is gold here and on the map.” |

## Act 5 · Close

| | |
|---|---|
| **Trigger** | MCP close / `wl status` |
| **Look left** | WO leaves open set |
| **Look map** | Open count drops; signed pulse if present |
| **Say** | “Close clears the ledger and the place load.” |

## Act 6 · Hire (optional)

| | |
|---|---|
| **Trigger** | `blueprint hire …` or seed-ops |
| **Look left** | Agent list gains a row |
| **Look map** | Seat / stack count; materialize if present |
| **Say** | “New hands show on the roster and the project rim.” |

## Act 7 · Expand (ops layers)

| | |
|---|---|
| **Trigger** | Click **Expand folders** (top-center FAB) |
| **Look map** | Ops minis (docs/ suite/ scripts/ …) orbit each project on the **same ring** — no scatter; "+N dig in" label for domain folders |
| **Say** | "Expand is depth-2 ops layers docked to the project ring — not a second map. Domain folders stay hidden; dig in for those." |
| **Collapse** | Click **Collapse folders** — ring clears, camera stays exactly where you left it |

## Notes

- No fake ambient crawl; approach only in T−3min window.
- If map flight fails, Act 2 still succeeds with YOU + WO alone (pc-468).
- Co-highlight (pc-470) flashes matching rail + bubble for ~1s — click WO or agent to demo.
- Fault flash (pc-472) only when health flips bad — rare in a clean demo.
- Expand camera: toggle never auto-fits; Esc does not collapse (use FAB or Reset view).
