---
name: workspace-efficiency
description: >
  Workspace efficiency / drain hygiene pass — ready feeds by seat, worker:you
  starve, empty-agent vs ready mismatch, roster paper health, open-work audit,
  and process-decay patrol (law-vs-enforcement drift). Use when asked for
  efficiency pass, queue validation, "are hands draining?", starve check,
  process decay, workspace efficiency, or /workspace-efficiency. Also the
  playbook for the scheduled workspace-efficiency job.
---

# Workspace efficiency (L0)

**Purpose:** Keep work orders seated so agents process queues while You are away.
Catch routing starve, idle agents, and empty-shift lies **on a cadence** — not
only in host chat.

**Law:** [`ProtocolCity/docs/specs/ALWAYS_WORK_PROCESS.md`](../../../ProtocolCity/docs/specs/ALWAYS_WORK_PROCESS.md)  
**Engine starve guard:** WorkLane `routing_labels` (wl-315)  
**Companion skill:** `ticket-routing` (create-time rules)

This skill is **read → report → re-route (coord only) → file**.  
Scheduled **job** runs report + optional re-route under CONTRACT limits.

Citizen language: **workspace** (not “city”). Product glass is Map / Desk /
Agents over *your* workspace folder.

---

## When to run

| Trigger | Who |
|---|---|
| Scheduled job `workspace-efficiency` | WorkForce cron (default 09:30 + 16:30) |
| Host chat “efficiency pass / validate queues” | Coord session loads this skill |
| After reboot / mass hire / process change | You or coord once |

**Not** a substitute for per-project `efficiency-*` code jobs (those clean
code inside one project folder). This pass is **workspace drain + seating**.

---

## Preflight

1. Desk up (`:8799`) · suite optional (`:8801`) · WorkForce daemon up (`:8797`).
2. Always `project=` on every WorkLane call (workspace-root session).
3. Skills discovery bridge (L0 must load inside project sessions):

```bash
bash scripts/skills_sync.sh --check \
  || bash scripts/skills_sync.sh
# monorepo host fallback:
# bash ProtocolCity/scripts/skills_sync.sh --check
```

4. Run scene + feeds + history + process audit:

```bash
python3 scripts/open_work_audit.py
python3 scripts/open_work_audit.py --feeds --history
python3 scripts/open_work_audit.py --process
python3 scripts/open_work_audit.py --decay
python3 scripts/open_work_audit.py --json --feeds --history --process --decay
# monorepo host fallback: ProtocolCity/scripts/open_work_audit.py
```

(`--feeds` = ready-by-seat + You-starve. `--history` = open+recent done
worker:you mixup classes: starve / host / list / You-park.
`--process` = roster queue_url probe + deferred-pile smell per lane.
`--decay` = process-decay patrol — skills bridge, ALWAYS_WORK §9 pending,
retired seats on open work.)

---

## Checklist (every pass)

### A · Scene (open / ready / motion)

- [ ] `total_ready` vs `total_in_motion` — ready pile with zero motion → routing
- [ ] Per-project: ready ≫ 0 but no agent fire in last 2h → investigate seat labels

### B · Ready by seat (starve detection)

For each managed project with `ready > 0`:

1. List ready tickets (`GET /api/admin/tasks/ready?product=<slug>` or suite proxy).
2. Histogram `worker:*` labels.
3. Flag **You-starve** (seat parked on You as if it were an agent):
   - bare `worker:you` / implement dump → **bad** (re-route to a hand)
   - `worker:you` + `you:note|todo|remind` → **Your list** (OK — not a hand queue)
   - `worker:you` + publish / You-present gate → intentional human park (OK)
4. Do **not** treat “needs You” the same as “assigned to You”:
   - **Escalate to You** = hand seat kept + `gate_type=human` / Blocked: (gold)
   - **Assigned to You** = `worker:you` (Your list; no cron drain)
5. Flag **no seat / needs:routing** on ready when hands exist.
6. Flag **wrong product** seats (wl-296) if known.

### C · Agent feeds (empty-shift truth)

For each hired **lane** with a schedule ≠ `manual`:

1. Query ready with that hand’s label (`worker:<id>`).
2. **Probe `queue_url`** on the roster row — must be
   `.../ready?product=<slug>&label=worker:<id>` (not bare `worker=`). Missing
   or wrong URL → fix roster or file WorkForce process WO.
3. Compare: hand fires empty while **other** seats hold ready on same product
   → re-route, do not hire more.
4. **Mass-deferred smell:** `ready≈0` but many **deferred** tickets with that
   hand’s label (or unlabeled implement ice) → board freeze, not “no work.”
   **Thaw eligible chew** (§C′′); do not hire more.
5. Config health: roster `contract` / `prompt` paths must exist.

### C′ · Runway-refill breach (ALWAYS_WORK §2k)

For each project with hired hands:

1. Check `ready == 0` (or below watermark: master-builder < 3, specialist < 2)
   for any seat.
2. Query open ungated epics (`status=backlog`, no `gate_type=deferred`) in that
   project — does any hold non-shipped scope not already cut into open children?
3. If **yes to both** → flag **runway-refill law breach**:
   the project's master-builder seat should have cut new children at last shift start.
   Report line: `BREACH: <project> runway starved — <seat> feed empty while <N> epic(s) hold cuttable scope`
4. If `ready == 0` and **no epics on the board** → try **auto-thaw** (§C′′) first;
   only then note legitimate quiet if only ice remains.
5. If a breach exists and the master-builder ran a compliant cut that found
   nothing cuttable → a For You gold should be present; check for it; if absent
   flag the missing gate as a secondary smell.
6. **Stale decision-starved gold:** if open gold titled/note `decision-starved`
   exists **and** ready ≥ watermark (or cuttable children were just filed/thawed),
   **clear it** (`gate_type=""` + `done` + evidence comment) in this pass —
   ALWAYS_WORK §2k. Report line: `CLEARED: <id> decision-starved — ready refilled`.

Add to report:
```
## Runway breach
| project | seat | ready | open-epics-with-scope | verdict |
```

### C′′ · Auto-thaw when ready drains (ALWAYS_WORK §2k · 2026-08-06)

Long-term work You filed is **chew**, not permanent ice. When a seat’s ready
feed is empty or below watermark:

1. List deferred tickets with `worker:<that-seat>` (same product).
2. **Skip ice:** `needs:you-present` · trading-path · credential/host ·
   on-glass/hardware · `gate_type=human` · timer not due · epic/umbrella
   tracking-only · explicit “not building now.”
3. **Thaw chew:** clear `gate_type=deferred` (and empty gate_note) on up to
   **watermark − ready** implement/research/docs tickets (priority order).
4. Comment: `Runway thaw · empty feed · <date> · workspace-efficiency`.
5. Prefer thaw over filing duplicate children when the deferred ticket is
   already a concrete implement slice.
6. **Never** re-seat implement to `worker:you`. Escalate = hand seat + human.

| Finding | Action |
|---|---|
| ready=0 + deferred implement (chew) | **Thaw** up to watermark; clear stale decision-starved gold if any |
| ready=0 + only ice | Report; gold only if decision-starved (one; refresh, don't stack) |
| ready=0 + open epic, no children | File 1–3 children **or** thaw existing deferred children; then clear decision-starved gold |
| ready healthy + open decision-starved gold | **Clear gold** — starve ended |
| deferred “after next release” and release shipped | Treat as **chew** — thaw + cut; not ice |
### D · Provider / roster smoke (light)

- [ ] Lane models non-empty (except intentional script jobs)
- [ ] CLI on PATH for the host service runner (`claude` / `codex` / `grok` / `cursor-agent`)
- [ ] Recent ledger: not all `ERROR` / `rc=1` for scheduled lanes

### E · Skills leverage (why local skills “don’t fire”)

L0 skills live under the **workspace** shelf. Project folders with their own
git root often **never see them** unless bridged.

| Tool | Bridge |
|---|---|
| Grok | `~/.grok/config.toml` → `[skills] paths = ["~/OneSeo/.agents/skills"]` |
| Claude / Cursor | `skills_sync.sh` symlinks L0 into each managed `project/.claude/skills/` |
| SoT | Always `.agents/skills/<id>/` — never edit project copies |

Not a cloud marketplace (skillsgate / skills.sh). **Local shelf + sync** is the
coordination layer. Overlap skills (routing, efficiency, brand, levels) stay
L0; product-only skills stay L1 under the project.

### F · Report inbox (For You)

Citizen briefs (desk brief, digest, You read packs) must appear on Map
**For You**. Efficiency reports stay **on disk**.

```bash
# briefs / digest — not efficiency gold
python3 scripts/report_to_for_you.py --workspace "$WS" --scan
# product-local For You drop when that product ships one:
# ( cd <product> && python -m <module>.for_you_drop )
```

If a **brief** exists for today but For You has no matching `Inbox · …` card
→ run `--scan` (or file process WO). Missing efficiency gold is expected.

**Efficiency For You rule:** `--scan` must not gold efficiency. Write the
dated report; leave it on disk. Gold only with `--act-now` when a product
has a stuck hand or critical feed failure. Desk brief / You read packs
remain For You cards. See [`FOR_YOU_INBOX_REPORTS.md`](../../../ProtocolCity/docs/specs/FOR_YOU_INBOX_REPORTS.md) §Gold vs rollup policy.

### G · Actions

| Finding | Action |
|---|---|
| You-starve implement ready | **Re-label** to best-fit hired agent (coord / this job if CONTRACT allows) |
| Bare `worker:you` implement (no you:kind / not true host-now) | **Re-seat to hand**; if needs You decision, keep hand + `gate_type=human` |
| Escalate parked on You (credential gold on worker:you) | **Hand seat + human gate** — never leave escalate as assign-to-You |
| History starve/host dumps | Report pattern; re-label open ones only |
| Escalate confused with assign | Teach: keep hand seat + human gate — never re-seat to You |
| ready=0 + deferred chew on seat | **Auto-thaw** (§C′′) up to watermark |
| needs:routing + hands exist | Route to hand or hire |
| Report on disk, missing For You | Efficiency: expected (disk-only). Other briefs: `--scan` or `for_you_drop` |
| L0 skills missing in project | `skills_sync.sh` |
| Dead papers path | Plant papers or pause schedule |
| Code drift inside one project | File to that project’s `efficiency-*` or code lane |
| Consecutive capacity fails, hand re-fired | Comment on the ledger WO; hand must not re-fire before limit resets |
| Hard-down pool, no For You gold | `python3 -m workforce capacity --live` or `report_to_for_you.py --project workforce --key capacity-<pool> --path <report>` |

**Writes allowed for scheduled job:** report file + re-label starve tickets +
**thaw eligible deferred implement** (clear gate only) + **close stale
decision-starved gold** when ready is healthy + For You report drops +
file at most a few routed WOs. **Never** mass-cancel. **Never** claim lane
work. **Never** create bare `worker:you` implement.

### H · Capacity thrash (provider / session limits)

- [ ] Recent ledger: any scheduled lane shows consecutive `vendor_limit` /
  `usage_limit` events? Confirm the hand **stopped** (did not re-fire within
  the blocked window). Re-fire within a limit window = **capacity thrash**.
- [ ] Hard-down pool today (weekly 0% / usage 0%): check For You for an
  `inbox-report:workforce:capacity-<pool>:<date>` gold. If absent, the
  capacity detector should drop it automatically:
  ```bash
  python3 -m workforce capacity --live   #  (wired to cadence by )
  # manual fallback:
  python3 scripts/report_to_for_you.py \
    --project workforce --key capacity-<pool> --path <report>
  ```
- [ ] Workspace-wide thrash (multiple pools blocked same hour): **one** workspace
  rollup gold — not one per-hand gold. See ALWAYS_WORK §2d′ + §2i.

### I · Process decay (law-vs-enforcement drift)

Catch drift **before** a human smells smoke. Bounded: **call existing tools**,
report + file classed tickets — **never mass-fix** from this job.

```bash
python3 scripts/open_work_audit.py --decay
# optional identity/path classes when planted:
# blueprint doctor
# python3 scripts/check_no_host_paths.py --check
```

| Check | Source | On smell |
|---|---|---|
| Skills bridge | `skills_sync.sh --check` (also inside `--decay`) | Heal once with `skills_sync.sh`, or file process WO if unhealable |
| ALWAYS_WORK §9 pending | `--decay` parses §9 table; rows without **Landed** | Confirm open routed WO exists; if missing, file **one** classed WO to the right seat |
| Retired seats | open tickets on succession ids (`ring`/`stock` → `pepper`/`binx`; `trinity` → `blossom`) | Re-label to live hand **or** file process WO — do not leave drain on a dead id |
| Doctor / host paths | `blueprint doctor` · `check_no_host_paths` when available | Report + file classed WO (do not mass-edit configs) |

**Gold scarcity (ALWAYS_WORK §2i):** when decay is found, mint **one** workspace
rollup For You card (efficiency / process-decay kind) — **not** one gold per
finding. Per-item detail stays in the daily report + filed WOs.

| Finding | Action |
|---|---|
| skills_sync fail | heal once, else file WO |
| §9 row without open ticket | file one routed WO to best-fit seat |
| retired `worker:` on open work | re-label to current hand or file WO |
| many smells same pass | report section + **one** workspace rollup gold |

### J · Zero-child parked epics (stall signal)

For every **deferred** ticket labeled `epic` or `umbrella` in each project:

1. Query open tickets with `parent:<epic-id>` label for that project.
2. If **zero** open children found → flag: "epic parked, nothing drainable."
   - Distinguish: children all `done` (epic closeable, child-coverage satisfied) vs
     children never filed (no drainable implement work exists yet).
3. Report line per flagged epic: `<id> · <title> — zero open children (file a child or cancel)`
4. **Do not** auto-cancel or auto-route; surface to the digest only.

| Finding | Action |
|---|---|
| Deferred epic, 0 open children, none ever filed | Report: suggest file implement child or cancel epic |
| Deferred epic, all children done | Report: epic may be closeable — child-coverage satisfied |

### K · Closed-but-unverified You checks (evaporated You-actions)

Scan tickets closed `done` in the last **7 days** whose `Done-when` or
`Verification` field (or any close-out comment body) contains any of:
`You re-check` · `You verify` · `You check` · `taste-check` ·
`re-check on live` · `host re-check` · `host verify`

For each match, scan the comment trail for a recorded **You confirmation**
after the close-out (a comment from author=you, or close text containing
`Confirmed:` / `Verified by:` / `You: ok`). If absent → collect into digest.

Digest entry per ticket: `<id> · <title> · residual action: <quoted text>`

**Gold scarcity:** all matches append to the single efficiency inbox report —
never mint one gold per finding.

| Finding | Action |
|---|---|
| Closed ticket, unverified You check | Append to efficiency digest; do not re-open unilaterally |

### L · Quickfire For You batch (deferred <5-min You-actions)

For each **deferred** ticket (any project) whose `gate_note` describes a short
You-action. Keywords: `scan` · `reboot` · `tap` · `check screen` · `plug in` ·
`confirm` · `look at` · `swipe` · `re-check` — or any note that reads as a
single physical or browser action under five minutes.

1. Collect: `<id>` + exact `gate_note` action text + project.
2. Render as **one** Quickfire batch block in the efficiency report:

```markdown
### Quickfire For You batch (clear these in one sitting)
| id | project | action |
|---|---|---|
| <id> | <project> | You re-check on live screen |
```

3. The block lands in the efficiency inbox report card (worker:you + you:note),
   **not** as N separate human-gate golds.
4. After You drains a batch, gate owner should close or cancel the ticket.

| Finding | Action |
|---|---|
| Deferred, gate_note = short You-action | Collect into one quickfire batch block in report |
| Batch > 10 items | Still one block — list all; do not paginate into multiple golds |

---

## Report shape

Write:

`OneSeo/.protocolcity/ops/reports/workspace-efficiency/YYYY-MM-DD.md`

```markdown
# Workspace efficiency · YYYY-MM-DD

## Summary
- open / ready / in_motion
- You-starve count · needs:routing count
- agents with ready>0 / empty feeds
- queue_url probe: N bad / N missing
- deferred pile smells: N
- capacity: pools hard-down · thrash events · For You gold Y/N
- process decay: ok | smells=N (skills_sync · §9 pending · retired seats)

## Scene table
…

## You-starve (re-route)
| id | project | title | → seat |

## Agent feeds
| hand | project | ready | last fire |

## Queue URL issues (`--process`)
| hand | project | issue |

## Deferred pile (empty-hand smell)
| hand | project | ready | deferred_count |

## Process decay
- skills_sync: ok | fail (detail)
- §9 pending: none | list (WOs filed / already open)
- retired seats on open work: none | list
- rollup gold: Y/N

## Actions taken
- re-labels …
- WOs filed …

## Zero-child parked epics (J)
| id | project | title | children status |

## Closed-unverified You checks (K)
| id | project | title | residual action |

## Quickfire For You batch (L)
| id | project | action |

## Skipped (intentional You parks)
- Publish / You · notes …
```

---

## Seat fit cheat-sheet (example workspace)

| Project | Typical implement seats |
|---|---|
| protocolcity | suite lane · code lane · quality lane · docs lane · brand |
| oneseo-pos | POS/till · inventory/catalog |
| trading | visual · execution · research seats (see that product's AGENTS) |
| worklane | engine lane |
| workforce | employment lane |
| socials | drafts lane |
| connector | design lane |
| presentations | talks lane |
| gridfinity | workshop lane |
| career | personal project lane |

**Dogfood density:** a host may run many hands by design. Shipped BluePrint seed is the ops trio only — do not treat a fat dogfood roster as the product package.

---

## Done when

- Report written for the day (or chat summary if ad-hoc)
- You-starve implement tickets re-routed **or** listed for You with reason
- No bare `worker:you` left on ready implement work when a hand fit exists
- Capacity thrash events noted; hard-down pools have a For You gold (or / queued)
- Process decay run (`--decay`): either **no decay** or smells reported with
  classed WOs / one workspace rollup (no per-item gold spam)
- Zero-child parked epics (J): flagged or confirmed none
- Closed-unverified You checks (K): digest entries collected or confirmed none (last 7 days)
- Quickfire For You batch (L): batch block rendered in report or confirmed none
- Console one-liner for WorkForce ledger
