# Always-work process (every BluePrint workspace)

> **Status: LIVE** — 2026-08-02 · all BluePrint installs, not host-private.  
> **Amended 2026-08-07:** shift **drain loop** is law (finish → next
> ready until empty / gated / budget / fault). Engine enforcement: ****.  
> **Amended 2026-08-08:** §9 implement backlog reconciled —  /
>  /  rows **Landed** (host residual **** stays explicit).  
> **Amended 2026-08-09:** §9 Map live-truth matrix row reconciled —
> **Landed**.  
> **Amended 2026-08-30:** §2k standing-chew rung
> (hygiene child on empty) — **superseded**.  
> **Amended 2026-09-02:** **no mill** — empty after thaw/cut **stops**
> or golds a decision. Do not file hygiene / leftover / next-knob / UNION-FF
> siblings so the next fire has work. Work orders are decided fixes and
> enhancements (You or epic-cut children), driven to conclusion on that ticket.  
> **This is the one straight process.** Other docs tighten details; they must
> not invent a second loop.  
> Companions: [`WORK_ORDER_LABELS.md`](WORK_ORDER_LABELS.md) ·
> [`../INSTRUCTION_LADDER.md`](../INSTRUCTION_LADDER.md) · FIRST_RUN
> §File, route, dispatch · WorkLane PROCESS §2–§3.9.

## One sentence

**Every open work order has a seat and a drain path; a hand drains its ready
feed inside the shift until empty, gated, budget, or fault — Map For You is
your paper pile / catch-all inbox (Decide + Read gold, Watch visible, Note
quiet); empty shifts are a signal, not a lifestyle.**

## Operating loop (the only loop)

```
You + preferred AI (entry)     ← author/intake always You
  → WorkLane (work orders)     ← history + board live here
  → route worker:<hand>        ← seat for drain (not "assigned to You")
  → WorkForce Agents / Jobs    ← claim · implement · land origin/main · close · next…
  → BluePrint Map              ← shows open / ready / For You / motion (glass = truth)
  → if true blocker            ← keep agent assignment + gate_type=human (For You)
```

**Land + glass (suite / UI products):** close-out Links cite a SHA on
`origin/main` (not only `workforce/shift/*`). On BluePrint dogfood: hard-reload
Map and confirm the surface before `done`. Dogfood vs public freeze:
[`DOGFOOD_AND_LOCAL_OPS.md`](DOGFOOD_AND_LOCAL_OPS.md) § Glass truth ·
[`../../NEXT_SHIP.md`](../../NEXT_SHIP.md).

### Shift drain loop (law · every BP city hand · )

Wake cadence (cron / Jobs schedule) is **unchanged**. What changes is the
**loop inside one shift** after a wake:

```
claim one ready WO → implement → verify → close
        ↑                                    │
        └── return to that seat's ready feed ┘
```

**Continue** until one of these **four exit conditions**:

| Exit | Meaning | Stop cleanly with |
|---|---|---|
| **1. Feed empty** | No ungated ready after §2k refill (thaw / cut). Do **not** mill a sibling WO | Empty-run note (see §4) |
| **2. Remaining gated** | Everything left is human / timer / deferred (or ice) | Why-gated one-liner; do not invent scope |
| **3. Budget / token cap** | Shift token, session, or host budget exhausted | Budget note; leftover stays ready for next wake |
| **4. Fault brake** | Consecutive verify/tool failures (runner default) | Early end + `Blocked:` note; backoff on repeat |

**Not an exit:** “I finished one ticket so the shift is done.” One close is a
**lap**, not the end of the shift. Hands **return to ready** and claim the
next ticket until an exit above fires.

| Who | Duty |
|---|---|
| **Hands (CONTRACT inherit)** | Per-hand CONTRACTs inherit this loop by **reference** to this file — no per-hand copy unless a seat deliberately opts out (e.g. manual-schedule / citizen-only seats). |
| **WorkForce engine** | Enforces multi-claim-per-shift when budget remains; records exit reason. Law and engine may land in either order — law states intent. |
| **workspace-efficiency** | Process-decay patrol: **queue nonempty + hand ended shift early without gate / budget / fault reason** is a breach (surface + file or fix). |

**Still true:** exclusive write paths per ticket; one active claim at a time;
no **silent freelance** when ready is empty — refill runway (§2k thaw / cut
from epics). Still empty → **stop** (or gold a decision). Do **not** file a
hygiene/leftover sibling to keep the shift busy. Unfiled
scope stays forbidden.
Batch same-path WOs when capacity-aware (§2d′).

| Role of **You** | When |
|---|---|
| **Author** | Always on host-chat intake — “I filed this” |
| **Quiet list (Note)** | Notes/todos/host-now (`worker:you` + you-kind, **no** human gate) |
| **Gold For You** | Paper pile needing attention *now* — **Decide** (decision / secret / publish) or **Read** (inbox-report card) |
| **Not** | Default implement seat · re-confirm after you already filed · mass For You flags for ordinary digests without a card |

- **Entry** — host chat is the front door (any vendor). Not a second queue.
- **Queue** — WorkLane is the **record and history**; file + `worker:*` on create.
  Prefer the ticket trail over re-teaching the same outcome in a new chat.
- **Work** — WorkForce drains ready seats; workspace **Jobs** (default seed:
  **chief-of-staff · health-patrol · workspace-efficiency**; optional
  github-desk · ship-desk · papers-sync) are ops, not managers. Project
  **Agents** (lanes) claim implement work.
  **github-desk** is GitHub **issue intake** (public issues → routed work
  orders). It is **not** the For You inbox bridge — reports drop via
  `scripts/report_to_for_you.py`
  ([`FOR_YOU_INBOX_REPORTS.md`](FOR_YOU_INBOX_REPORTS.md)).
- **Map/Overview** — only *show* truth; does not replace chat or engines.

**No coordinator seat.** Protocol + You + entry AI route. Optional
project `*-desk` triage agents or health-patrol jobs are **assignment /
health**, not a workspace-level manager of agents (see STAFFING.md · NO
coordinators).

## Host session open (director card)

When You (or your host AI) start a coordination session, **file or claim a
work order first** — chat is not the queue. Paste this card into the WO
Glance / first comment (or the session first message):

```
Project: protocolcity | trading | register | …
Slice: one sentence outcome
In: files / surfaces (or “find them”)
Out of scope: …
Risk: autonomous | citizen-present | human gate
Done when: 2–4 checks
Verify: command or UI look
```

**Estimate without drama:** S = one face/bug/panel · M = one dig surface or
one product path · L = split into S/M before claim. Prefer S. Do not grow
process for register (or any product) beyond this card + `worker:*` route.

BluePrint zoomed-out: **You + AI enter → WorkLane queues → WorkForce works →
Map shows.** Connect AI to the **workspace** for cross-project routing; to a
**project** folder for product depth. Map is overhead viewer, not a second desk.

### Foundation v2 (instruction model)

| Load first | Skip unless blocked |
|---|---|
| Workspace **CORE** `AGENTS.md` (≤100 lines · one loop) | Host chronicles / naming history |
| **This file** (ALWAYS_WORK — the one process) | Full WorkLane PROCESS engine bible |
| Project `AGENTS.md` + agent CONTRACT/prompt | Every `docs/specs/*` · ATLAS novel |
| Map + `wl_ready` / dig history | Re-reading dual vocabulary essays |

**Citizen test:** operating loop + one sentence + this table — the loop works. §1–9 below are reference detail; load the section matching your question.

**One flow, many pointers.** `INSTRUCTION_LADDER`, skills, and PROCESS
**detail** this loop — they must not teach a conflicting path (no Map-form
compose, no default `worker:you` for agent work, no re-seat escalate).

**Work** (WorkLane) is coordination truth **and** durable history. **CORE** is
short human law. **Inventory** (project table, agents list) should become
`<!-- bp:generated -->` blocks refreshed by doctor — not hand
essays.  
**Vocab:** citizen register only on Map surfaces —
[`SUITE_VOCABULARY.md`](SUITE_VOCABULARY.md) § Dual register
(workspace · project · work order · Agents · You).

## Product promise (humans step away)

**BluePrint workspaces keep working when You leave the chat.** Agents claim ready
work, implement, verify, and close. They **propose** ideas in comments when
uncertain; they do **not** freeze the board for every preference or design
taste. Only **true blockers** (credentials, irreversible publish, missing
law) flag For You.

| Expectation | Behavior |
|---|---|
| Queues drain | Ready + labeled work is claimed and closed — **inside the shift**, not one ticket then idle (drain loop above) |
| Can complete | Agent completes **this** WO (land origin/main on the same ticket); unfinished scope of this outcome may be a child of the epic — not a mill sibling so the next fire has work |
| Unclear preference | Comment **Proposal:** + pick a safe default and continue |
| True blocker | Stop, comment, `gate_type=human` only if You must act *now* |
| Empty feed | **No silent freelance** — **do refill runway** (§2k): thaw eligible deferred implement on that seat, or cut children from open epics. Still empty → **stop** (empty-run note). If the remaining work is a missing ruling, gold one decision. Do **not** invent related WOs so the cron is not empty |
| Early exit smell | Ready still open on that seat + shift ended with no gate/budget/fault note → process decay (efficiency patrol) |
| Duplicate imports | One canonical ticket; cancel copies with pointer |

**Not a blocker:** “which polish is prettier,” “should we rename this
string,” “confirm my plan after You already filed,” ordinary package
bumps, pure docs clarity, de-dupe of known twin tickets.

---

## 1. See all open work (citizen + coord)

| Need | How (shipped surfaces) |
|---|---|
| **City totals** | Map left Work orders header · `wl counts` / MCP `wl_counts` with `project=all` |
| **Per project open** | Map folder open# · project dig open KPI · store rollup on Map scene |
| **Live motion** | Work orders strip filter **live activity** (default) · Agent activities |
| **Ready for agents** | WO chip **ready** · `wl_ready` per project |
| **Act-now You** | Left **You** card · dig **For You** · chip **for you** (same membership) |
| **Unrouted / no seat** | Suite `GET /api/tasks/unrouted` · label `needs:routing` when pre-hire |
| **CLI audit** | `blueprint doctor` (feeds + history) · or `python …/open_work_audit.py --feeds` |
| **Cadence audit** | L0 skill `workspace-efficiency` · scheduled job `workspace-efficiency` (09:30+16:30) |

There is no separate “all tickets” product page (suite non-goal). **Map +
counts + ready/for-you doors** are the Map surface. Coord chat uses MCP with
explicit `project=` every call.

---

## 2. Always-work pipeline (product law)

```
file → route (worker:<id>) → ready drain → claim → verify → close ─┐
         ↑                              │                          │
         └── hire if no seat ───────────┘                          │
                     │              └── next ready (same shift) ───┘
                     │                   until empty | gated | budget | fault
         empty N times → surface + backoff (not silent spam)
```

1. **File = decided** — implement; do not re-ask design unless blocked.
2. **Create = route** — exactly one `worker:*` when agents are hired (hard B).
2b. **Starve rule** — `worker:you` is **not** a default implement
    seat. Cron never claims You. Bare `worker:you` is rejected when lanes are
    hired unless classified (`you:note|remind|todo|host` or citizen gate).
    Route agent work to `worker:<persona>` so queues drain while You are away.
2b′. **Assign vs escalate (do not mix)** —
    - **Assign to agent** = create with `worker:<persona>` (default for ship work).
    - **Your list** = `worker:you` + you-kind (personal / host-now only).
    - **Escalate to You** = keep the agent assignment; set `gate_type=human` or
      `Blocked:` / Next step when an agent fails or needs a decision.
    Re-labeling failed work to `worker:you` is wrong — that looks like “my
    queue” and never drains. Gold For You ≠ seat assigned to You.
2c. **Cadence validation** — run L0 skill **workspace-efficiency** (or let the
    scheduled job fire 09:30+16:30) so ready-by-seat + You-starve + **history**
    mis-assign patterns + agent config health are checked without host chat.
    Per-project `efficiency-*` jobs stay code cleanup inside one project;
    this pass is workspace **drain seating**.
2d. **Skills must load** — L0 coordination skills live on the workspace shelf
    (`.agents/skills/`). Project sessions need a **discovery bridge**
    (`ProtocolCity/scripts/skills_sync.sh` into each managed project’s
    `.claude/skills/`, plus Grok `[skills] paths`). Not a cloud skills
    marketplace — local SoT, multi-tool discovery.
2d′. **Capacity-aware coordination (every BP workspace · 2026-08-02)** — vendor
    session / weekly / credit limits are **first-class process**, not private
    host gossip.

    | When | Do |
    |---|---|
    | Hand/ledger reports `vendor_limit` / usage limit / session 100% | **Do not thrash** the same seat every 30m with no progress |
    | A pool still has **time left** (resets in N min, weekly % free) | **Leverage it** after the wall lifts — put fitting work back on that CLI |
    | One pool is hard-down (e.g. weekly 0% until a date) | **Re-pin payroll** to a healthy pool (persona unchanged); add a For You card if thrash is workspace-wide |
    | Many ready tickets share one exclusive path / surface | **Batch** — one claim/shift owns the path; group related WOs (children under one parent or claim the slice that unblocks the cluster). Do not let three agents touch the same files in parallel |
    | Shift ends mid-window with budget left | Prefer **another same-path ticket** over inventing new surfaces |

    **Wise exhaust:** use each provider’s allocation, but **group similar work**
    so token burn ships outcomes (one open path, multiple Done when bullets)
    instead of re-loading context for the same map/suite/engine slice.

    **Map surface:** capacity thrash must surface (Agents strip / For You) — see
    capacity alert jobs. Detect CLIs: `blueprint detect` · `workforce runtimes`.
    Payroll pins: STAFFING model tier law + roster only (no rename).
2e. **History** — `open_work_audit.py --history` classifies past
    `worker:you` as starve/host/list/citizen so mis-assign patterns
    surface on the workspace-efficiency cadence, not only live ready.
2f. **Queue URL = drain feed** — every `kind=lane` roster row needs
    `queue_url` …`/ready?product=<slug>&label=worker:<id>`. Wrong shape
    (`worker=` without `label=worker:`) or empty URL → silent empty shifts.
    Fix on sight; file WorkForce process if hire/doctor did not catch it
   . Efficiency cadence should probe feeds, not assume fire = work.
2g. **Mass-deferred anti-pattern** — do **not** park every implement ticket
    as `deferred` to “clean” ready metrics. **Active epics are born open** —
    chief-of-staff decomposes any open epic with zero open drainable children
    (§2j); deferred umbrella = explicit citizen park only (with thaw
    condition). **Claimable slices stay ready + `worker:`**. If `ready=0` while
    many deferred implement tickets exist, that is process failure (agents
    fire empty) — re-audit or file a board-validation WO, do not hire more
    agents. Evidence: Trading 2026-08 unlock (30 open / 0 ready).
2h. **Process smells → fix or file in parallel** — when away-work surfaces
    look off (stale health series, rotated logs, undelivered briefs, wrong
    seats), either fix the small process now or file a **routed** research/
    ops ticket the same session. Do not wait for a separate “process sprint.”
2i. **For You = paper pile / inbox** — one citizen product name on Map
    (**For You**). Not a second “Needs You” machine. Papers share the pile;
    faces sort them (Map may section Decide vs Read — ). Engine may
    keep `gate_type=human` for both Decide and Read until a softer inbox
    signal exists. Full membership + scarcity: **§5**. Inbox card rules,
    dual-audience brief structure, scarcity policy (one card per kind/day,
    workspace rollup for efficiency, capacity alerts) and drop tool:
    [`FOR_YOU_INBOX_REPORTS.md`](FOR_YOU_INBOX_REPORTS.md) ·
    `scripts/report_to_for_you.py`.
2j. **Epic decomposition (chief-of-staff duty · all stores)** — active epics
    do not stall; decomposition is agent-owned, not citizen-default.

    | Epic state | Chief-of-staff action |
    |---|---|
    | Open (ungated), zero open children | Claim as planning slice → file 3–6 routed `worker:<hand>` children from body decisions |
    | Decision missing from body | File **one** gold For You question child — do not stall the whole epic |
    | Deferred epic umbrella (explicit citizen park + thaw condition) | Leave epic parked; still **cut or thaw implement children** when ready is empty (§2k) |
    | All children done | Comment ready-to-close; epic close = all children done |

    Epic umbrella never carries implement code. Chief-of-staff sweeps
    `project=all` — workspace-wide, not per-project. Default: epics are born
    **open**; the only valid park is an explicit citizen/citizen deferral with
    a named thaw condition.

2k. **Runway refill when ready drains (away-work law · 2026-08-06)** —
    You file **long-term** work so hands always have something to chew while
    away. Empty ready is a **process signal**, not “job done, go idle.”

    | Ready state | Required action (master builder / efficiency / CoS) |
    |---|---|
    | Seat `ready == 0` (or below watermark: builder &lt; 3, specialist &lt; 2) | **Refill before next empty fire** |
    | Open ungated epic with cuttable scope | File 1–3 routed implement children |
    | Deferred **implement** on that seat (not ice) | **Thaw** up to watermark: clear `gate_type=deferred` |
    | Nothing left to thaw or cut | **Stop.** Do **not** file a hygiene / leftover / next-knob / UNION-FF child to restock the feed (mill-stop · ) |
    | Remaining work needs a ruling / credential / citizen-present | Keep the hand seat + gold one decision (`gate_type=human`) — last rung, not a mill |
    | Cuttable work returns (release landed · deferred thaw condition met · children cut) | **Clear** open decision-starved gold in the **same** refill pass — do not leave Map gold for You to notice |

    **Ice (never auto-thaw):** `needs:citizen-present` · trading-path live risk ·
    credential/host-mutation · on-glass/hardware · `gate_type=human` act-now ·
    timer not yet due · explicit citizen “not building now.”

    **Chew (auto-thaw / keep ready):** long-term implement, research, docs,
    packaging, post-northstar product pillars that are pure code, process
    maturity — anything a hand can ship without You in the room.
    **Deferred with a named thaw condition that is now true** (e.g. “after
    next release”) is **chew**, not ice — thaw and cut; do not re-gold You.

    **No mill (2026-09-02 · ; supersedes  /  chew rung):**
    empty after thaw + cut **is a stop**. Work orders are decided fixes and
    enhancements (You, or children cut from an open epic). Drive each WO to
    conclusion on **that** ticket (land `origin/main` there). If it cannot
    finish, gold a decision or blocker — do not invent the next related cell.

    1. **Do not file** a hygiene child, leftover-stamp, next-knob Zone B chew,
       UNION-FF land ticket, or “so the next fire has work” sibling.
    2. **Leftover-truth** stays on the close-out of the real WO (not a Nala /
       Pepper / Garfield leftover child per phrase or knob).
    3. **Anything larger** than the current slice → comment `Proposal:` on
       the open parent epic (or file `deferred` with a thaw note) — do not
       invent product direction.
    4. **Ice stays ice:** new product direction, hardware, credentials / keys,
       trading-path live risk, host mutation, publish — regardless of how
       empty the feed is.
    5. **Decision-starved gold** is the honest empty: no epic to cut, no
       deferred implement to thaw, remaining work needs You. One gold; do
       not mill around it.
    6. Engine empty-run SKIP / backoff **may** hide a seat whose feed is
       empty — that is correct. Do not spawn a chew pass to un-hide it.

    **Decision-starved gold lifecycle:**
    1. File/refresh **one** gold only when ready is empty **and** no cuttable
       epic/deferred-implement remains.
    2. When a later shift (or host/coord session) **refills** ready or thaws
       cuttable work → **close that gold** with evidence in the same pass.
    3. Timer gates auto-thaw at `gate_until` (engine read-time). Decision-
       starved does **not** auto-expire — hands/coord must clear it when
       the starve ends.

    **Seating (hard):** implement never parks on `worker:you`. Escalate with
    hand seat + `gate_type=human` (§2b′). Efficiency job re-labels bare You
    implement dumps every cadence.

    Cadence enforcement: L0 `workspace-efficiency` (09:30+16:30) **may thaw
    eligible deferred implement**, **must clear stale decision-starved gold**
    when ready is healthy, and re-seat You-starve — not only report.

2k′. **Entry chat maintains the board (coord hygiene · 2026-08-07 · amend 2026-08-08)** —
    Host chat is not a second archive, but it **must** keep the board
    honest while work lands — and **capture named debt** so nothing
    lives only in chat memory:

    | Session event | Required board action (same turn if tools work) |
    |---|---|
    | Ship / publish / release that satisfies a CITIZEN · publish gold | Close that gold with structured close-out |
    | Release that unlocks a deferred “after next release” ticket | Thaw parent · cut children if cuttable · clear related decision-starved gold |
    | Implement slice finished in chat | Close or land WO; never leave gold that no longer needs You |
    | **You name a debt / residual / “should…” / “file that”** (floor walk, design talk, process miss) | **File a WO same turn** (ready or `deferred` with thaw note) — brainstorm alone may stay chat-only; a **named outcome** is not brainstorm |
    | **Design / paper ticket closes** with implement residual | **On the board before `done`:** (1) ratify gold (`gate_type=human`) **or** (2) routed implement children (deferred OK). Prose-only “after ratify / later” = invalid close (PROCESS §3 rule 11) |
    | citizen already decided a deferred thaw condition | **Thaw** eligible children same turn — do not leave parked work that looks “in progress” |
    | Tools down (MCP/CLI) | Say so; file residual host heal; do not pretend For You / board is current |

    Anti-patterns: ship in chat and leave gold painted; **named debt only in
    chat transcript**; design close with residual only in `Completed:` prose;
    leave deferred implement after You already locked the thaw condition.

3. **Hire before stall** — no fit → hire, then label; do not leave
   `needs:routing` as steady state after hire.
4. **Drain (shift loop · )** — scheduled agents only claim **their**
   feed; area tags never route. After each close, **return to ready** and
   claim the next ticket until **feed empty · remaining gated · budget/token
   cap · fault brake** (see **Shift drain loop** above). One WO per claim;
   many claims per shift when the feed and budget allow. Engine: ****.
5. **Gold is the pile’s attention paint** — `gate_type=human` only (no other
   gate flags For You). Scarcity is **by face** (see §5), not “reports must
   never be For You” vs “must always be For You.” Not every question, not ordinary
   implement finish, not mass parks, not intermediate report files.
6. **Deferred** — later-track ice, not a second For You.
7. **Duplicates** — one canonical ticket per external id (e.g. GH #N); cancel
   or defer copies with a pointer comment (no silent mass cancel of real work).

---

## 3. Queue director (optional seat — not the product entry)

**Not** a second product name and **not** “the AI entry point.” Preferred
entry is still **You + host AI** filing/routing into WorkLane. A **queue
director** is only an optional **hired** seat whose job is **assignment
intelligence** (labels, de-dupe, empty-feed health) — never a people-manager
of other agents (STAFFING · NO coordinators).

| | Entry AI (You’s session) | Director seat (optional) | Lane agent |
|---|---|---|---|
| Where | Host chat | Roster `worker:…-desk` or ops job | `worker:figaro` … |
| May | File, route, decide gates | Route, re-label, de-dupe, escalate empty | Claim own feed, implement, close |
| Must not | Pretend chat is the queue | Manage other agents as reports; invent personas | Leave wrong seat on create |

**Recommended hire pattern (ship teaching):**

- **Default:** no director hire — You + entry AI + seed-ops **Jobs** (trio).
- **Workspace ops:** seed-ops diamonds (**chief-of-staff · health-patrol ·
  workspace-efficiency**). Legacy clerk / marshal / correspondent are not
  defaults; briefs fold into chief-of-staff.
- **Product projects with ≥2 implement agents:** optional
  `worker:<project>-desk` triage-only when routing load is real.
- **Solo-agent projects:** that agent is implementer + de-facto route
  discipline — prompt still says “route before inventing work.”

Cadence: slow schedule (e.g. 1–4h), not every minute. Empty director shifts
are OK if the board is clean; N empties → comment board health once, stop.

**Hire recipe (one step):**  
`blueprint hire <name>-desk --workdir <project-root> --role 'Queue director — triage and routing' --project <store-slug>`  
Names ending in `-desk` auto-plant filled director papers (`templates/director-CONTRACT.md` / `director-prompt.md`). Override with `--template worker|director`. `--dry-run` prints which template will be used. Placeholders filled: `{{WORKER_ID}}` · `{{STORE_SLUG}}` · `{{NEIGHBORHOOD_NAME}}` · `{{CLI_COMMAND}}`.

Workspace ops trio (chief-of-staff / health-patrol / workspace-efficiency) → use
`blueprint seed-ops --root <workspace>` instead (Map diamond jobs, not lane
agents).

---

## 4. Empty runs (runner + Map)

| Outcome | Meaning |
|---|---|
| Empty / no ready | Feed for that seat is empty — **often correct** (exit 1 of drain loop) |
| Gated-only remaining | Ready looks empty after human/timer/deferred filter — exit 2 |
| Budget stop | Closed ≥1 ticket then hit token/session cap — exit 3; not an empty-run |
| Fault brake | Consecutive failures → early end + Blocked note — exit 4 |
| Failed shift | Health / tool / verify failure without orderly exit — attention |
| Real close(s) | Ticket(s) moved in the shift — success; multi-close is expected when feed allows |
| Early-idle smell | Ready still open on seat + shift ended with **no** exit 2–4 reason — **process decay** |

**Policy (all BP workspaces):**

1. Empty **after the full ladder** (drain → §2k thaw / cut) is **not**
   failure — stop. Never work unfiled scope. Never mill a sibling WO so
   the shift is not empty.
2. After **N consecutive empties** (default **3**, host may pin in roster):
   surface one line on dig/Map (why empty) and **backoff** schedule if the
   runner supports it; do not thrash the ledger.
3. Map: Agent dig **Recent work** collapses empty checks; workspace wants
   **last real ticket** when that surface ships.
4. Coord: if many agents empty while ready open exists → **routing bug**, not
   “hire more.”
5. **Drain-loop enforcement:** a shift that closes one
   ticket and stops while the same seat still has ungated ready **without**
   stating budget, gate, or fault is a process-decay signal for
   `workspace-efficiency` (engine drain + early-idle patrol landed:  /
   ; host single-pass pins remain ****).

---

## 5. For You bucket (paper pile · workspace-wide)

**One product name:** **For You** (never **Needs You** as primary Map label —
see research  · stamp slice ).

**Mental model:** the You card is a **paper pile / inbox — catch-all for
everything needing your attention**. Gold paint means “needs your attention
now.” Faces are sections of the same pile, not competing products:

| Face | Membership | Primary verb | Gold? |
|---|---|---|---|
| **Decide** | `gate_type=human` act-now that is **not** an inbox-report (decision, sign-off, publish, credentials) | Open WO · clear gate / decide | **Yes** — scarce |
| **Read** | `gate_type=human` + inbox-report classifier (`inbox-report*` label · dig **Inbox · …** · `report_to_for_you` cards) | Mark read · snooze · open report body | **Yes** — scarce **by report policy** (§2i · FOR_YOU_INBOX_REPORTS) |
| **Watch** | attention `kind=stalled` or `kind=embargo` — blocked / watching items | Open WO · inspect blocker | **No** — visible in dig, not counted in pile ⭐ |
| **Note** | `worker:you` + `you:note\|todo\|remind\|host` **without** human gate | Open · complete | **No** — quiet Your list |

**Pile count (You card pill) = Decide + Read only.** Watch items appear in the
dig **and You tray** as a third band below Read but do not inflate the ⭐ count
on folders or the outline chip.

### Three clocks (do not conflate — )

| Clock | Mechanism | Citizen meaning |
|---|---|---|
| **Mute gold** | Snooze (server attention) | Hide notification; **same** gold returns; gates unchanged |
| **Timed re-entry** | `gate_type=timer` + `gate_until` | Calendar + Watch “Opens {date}”; not gold until due |
| **Quiet list** | `worker:you` + `you:note\|todo\|remind` without human gate | Note face — never gold |
| **Act-now** | `gate_type=human` | Decide or Read gold — scarce |

**Calendar** (`/calendar` · `/calendar.ics`) projects timers + `deadline:YYYY-MM-DD`
labels only — no second date store.

### In For You vs out

| In For You (dig visible) | Out of For You |
|---|---|
| **Decide** papers — human gate, non-report act-now | Ordinary backlog labeled for an agent |
| **Read** papers — human-gated inbox-report cards (daily briefs, CITIZEN packs, capacity alerts) | Disk-only reports under `local/reports/` with **no** inbox card — including all **efficiency** reports |
| **Watch** items — attention stalled/embargo kinds (not gold; dig section only) | **Note** — `worker:you` + you-kind without human gate (quiet list) |
| | Deferred / ice |
| | “Please confirm my plan” after You already filed |
| | Intermediate report artifacts, per-product efficiency spam, digests/ntfy **without** a human-gated card |

### Scarcity by sub-kind (resolves §2i ↔ older “scarce only” reading)

| Face | Scarce means |
|---|---|
| **Decide** | Only true blockers / publish / credentials — not every question, not ordinary ship finish, not mass parks |
| **Read** | One card per report **kind** per day (or workspace rollup); efficiency not per-product For You by default; see FOR_YOU_INBOX_REPORTS |
| **Watch** | Not gold — no scarcity constraint; shows all stalled/embargo in attention payload |
| **Note** | Never For You — optional Map section only |

**Engine:** Decide and Read both use `gate_type=human` and share one Map
count. Watch uses attention `kind=stalled/embargo` (already split client-side
in `slipsFromAttention`). No engine change needed for Watch band —  stays
deferred. Map may **section** Decide vs Read.

**Same membership surfaces (gold/Decide+Read only):** You card · WO **for you**
filter · folder For You. Watch visible in dig only. Dig chrome for Read:
**Inbox · {kind}** (not “Work order · For You”).

**Lenses:** Overview is distance; Map is the
full pile. Faces do not go missing — they change lens.

| Lens | Shows |
|---|---|
| **Overview For You** | Three boxes: **Decide** (gold, grouped by project — ) · **Read** (each inbox-report as a row, with project) · **Watch** (named, not gold — ; click → Map `?project=`). No Read hop. |
| **Map You tray** | Decide · Read · Watch pulses. Gold ⭐ = Decide + Read. Watch band under, not counted. Read dig `/workspace-map?you=read`. |
| **Calendar** | Dated Decide + timer Watch (same ICS; not a fourth gold face). |
| **Note** | Never gold. Quiet Your list. Optional Map section — not Overview. |

**github-desk ≠ For You bridge.** The optional github-desk job pulls public
GitHub issues into routed WorkLane tickets. It does not drop Read/Decide
cards. Inbox reports use `report_to_for_you.py` (this section +
[`FOR_YOU_INBOX_REPORTS.md`](FOR_YOU_INBOX_REPORTS.md)).

Companions: [`FOR_YOU_INBOX_REPORTS.md`](FOR_YOU_INBOX_REPORTS.md) ·
[`WORK_ORDER_LABELS.md`](WORK_ORDER_LABELS.md) ·
[`../research/for-you-inbox-vs-needs-you-2026-08-02.md`](../research/for-you-inbox-vs-needs-you-2026-08-02.md).

---

## 6. Instruction hygiene (L2 / L3 — anti-drift)

**Goal:** short law files; long truth lives in **specs and skills**, not
restated in every CONTRACT.

| File | Target length | Holds |
|---|---|---|
| `CONTRACT.md` (L2) | **≤ ~120 lines** preferred; hard smell **> 200** | Identity, lane, never-touch, procedure, stop rules |
| `prompt.md` (L3) | **≤ 1 page (~40 lines)** | Start-shift checklist; pointer to CONTRACT + AGENTS |
| Project `AGENTS.md` (L1) | Registry + how to run/test + ticket store | Not a second novel of every agent |
| Skills | Progressive disclosure | Capabilities — not employment law |

**Rules:**

1. **Reference, don’t restate** — link `docs/specs/…`, PROCESS, skills.
2. **One exclusive path story** per multi-agent project — in tickets, not
   copy-pasted into five contracts.
3. **Vendor CLI / model** = payroll pin on roster; one line in CONTRACT.
4. **History / renames** = one short “Succeeded X” note, not multi-paragraph
   genealogy every shift.
5. **Efficiency jobs** (pattern pass across code): own seat + narrow prompt;
   do not bloat implementer CONTRACTs with workspace-wide refactor doctrine.

**Hygiene pass cadence:** when empty runs spike, or after rename waves, or
monthly doc-audit — trim contracts/prompts that grew past targets.

---

## 7. Pattern efficiency (code + ops)

Across projects, prefer:

- **One helper** shared (suite Map `placeState`, WorkLane process) over
  forked copies per product.
- **Generalize then delete** — shorter code after the shared seam lands.
- **Gaps as tickets** with `worker:*` on create — not chat-only notes.

Agents that only “look for efficiency” must still **claim labeled work** and
**close with verification** — no freestyle rewrites of the workspace.

---

## 8. Acceptance (workspace is healthy)

- Open work is **visible** (Map / counts / ready).
- Almost all ready tickets have a **correct seat**.
- Agents **claim and close** when ready exists; empty runs are rare or explained.
- Agents **loop the ready feed inside a shift** until empty / gated / budget /
  fault — not one ticket then idle while ready remains.
- For You is a **catch-all inbox** (Decide + Read gold; Watch visible, not counted; Note quiet) — not a second queue of ordinary implement work.
- CONTRACTs/prompts stay **under hygiene targets** or have open trim tickets.

---

## 9. Implement backlog (product)

Not blocking this law’s status LIVE as teaching:

| Item | Intent |
|---|---|
| Director hire recipe / templates | **Landed** — `*-desk` / `--template director` plants filled director papers; §3 one-step recipe |
| Empty-run N + backoff in WorkForce runner | **Landed** — roster `empty_run_threshold` (default 3), optional `empty_run_backoff` / `empty_run_pause` / `vendor_limit_backoff`; daemon withholds cron after N consecutive queue-empty SKIPs; one WARN ledger signal; board exposes `empty_streak` for dig/Map |
| **Shift drain loop in runner** | **Landed** — engine multipass default `max_passes=0` (budget-driven drain) + stop reasons empty / gated / budget / fault / hard-cap. Host residual: seats with explicit `max_passes=1` need citizen repin (****, `you:host`). |
| Efficiency patrol: early-idle with ready open | **Landed** — engine WARN breadcrumb + `workforce doctor` Early-idle rollup when soft-ceiling stop leaves ready>0; process-decay surface without Map gold spam |
| Map “Agents · last real ticket” | **Landed** — BFF stamps `last_real_shift`/`last_real_ticket` past empty SKIP thrash; mid-shift finalize WARN no longer orphans CLAIM; Agents idle shows `Last real · id` + empty streak without gold spam |
| Map live truth matrix (Working / Holding / Idle / last real) | **Landed** — citizen matrix + animation rules + soft-poll lag: [`docs/research/map-live-truth-status-matrix-2026-08.md`](../research/map-live-truth-status-matrix-2026-08.md). Delivered: Holding density/wake/dig ≠ Idle; claim/close events soft-poll-bust sticky CLAIMED/Holding within one poll |
| `open_work_audit` in `blueprint doctor` | **Landed** — `blueprint doctor` runs feeds + history for all stores; hard fail on You-starve with hired lanes / invalid feeds |
| GH/import create always routes | **Landed** — create/import paths run `ensure_create_labels`; pre-hire stamps `needs:routing`; post-hire bare seats reject; soft path only via explicit archival restore |
