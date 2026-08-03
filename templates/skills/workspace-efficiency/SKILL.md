---
name: workspace-efficiency
description: >
  Workspace efficiency / drain hygiene pass — ready feeds by seat, worker:you
  starve, empty-hand vs ready mismatch, roster paper health, open-work audit,
  and process-decay patrol (law-vs-enforcement drift). Use when asked for
  efficiency pass, queue validation, "are hands draining?", starve check,
  process decay, workspace efficiency, or /workspace-efficiency. Also the
  playbook for the scheduled workspace-efficiency job.
---

# Workspace efficiency (L0)

**Purpose:** Keep work orders seated so hands drain queues while You are away.
Catch routing starve, dead hands, and empty-shift lies **on a cadence** — not
only in host chat.

**Law:** BluePrint `ALWAYS_WORK_PROCESS` (product docs) · WorkLane routing  
**Companion:** ticket-routing skill when present (create-time rules)

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

1. Desk up · suite optional · WorkForce daemon up when hands should fire.
2. Always pass the project slug on every WorkLane / `tk` call at workspace root.
3. Skills discovery bridge (L0 must load inside project sessions):

```bash
bash scripts/skills_sync.sh --check \
  || bash scripts/skills_sync.sh
```

(If this workspace keeps the monorepo layout, `ProtocolCity/scripts/skills_sync.sh`
is the same bridge.)

4. Run scene + feeds + history + process audit when the helper is planted:

```bash
python3 scripts/open_work_audit.py
python3 scripts/open_work_audit.py --feeds --history
python3 scripts/open_work_audit.py --process
python3 scripts/open_work_audit.py --decay
```

(`--process` = roster queue_url probe + deferred-pile smell per lane.
`--decay` = process-decay patrol — skills bridge, ALWAYS_WORK §9 pending,
retired seats on open work.)
Or use Map counts + `tk ready` / MCP `wl_ready` per project.

---

## Checklist (every pass)

### A · Scene (open / ready / motion)

- [ ] Ready pile with zero motion → routing / hire
- [ ] Per-project: ready ≫ 0 but no hand fire lately → inspect seat labels

### B · Ready by seat (starve detection)

For each managed project with `ready > 0`:

1. List ready work orders.
2. Histogram `worker:*` labels.
3. Flag **You-starve** (seat parked on You as if it were a hand):
   - bare `worker:you` / implement dump → **bad** (re-route to a hand)
   - `worker:you` + `you:note|todo|remind|host` → **Your list** (OK)
   - `worker:you` + human/publish gate → intentional human park (OK)
4. **Assign ≠ escalate** (do not mix):
   - **Assign to hand** = create/label `worker:<persona>` (default for ship work)
   - **Your list** = `worker:you` + you-kind (personal / host-now only)
   - **Escalate to You** = **keep the hand seat**; set `gate_type=human` or
     `Blocked:` / Next step — never re-seat failed hand work onto You
5. Flag **no seat / needs:routing** on ready when hands exist.

### C · Hand feeds

For each hired **lane** with a schedule ≠ `manual`:

1. Ready count for that hand’s label (`worker:<id>`).
2. **Probe `queue_url`** on the roster row — must be
   `.../ready?product=<slug>&label=worker:<id>` (not bare `worker=`). Missing
   or wrong URL → fix roster or file a WorkForce process WO.
3. Compare: hand fires empty while **other** seats hold ready on same product
   → re-route, do not hire more.
4. **Mass-deferred smell:** `ready≈0` but many **deferred** tickets with that
   hand’s label (or unlabeled implement ice) → board freeze, not "no work."
   File/route a validation pass; do not hire more.
5. Paper health: roster `contract` / `prompt` paths must exist.

### D · Skills leverage

L0 skills live under the **workspace** shelf. Project folders with their own
git root often **never see them** unless bridged.

| Tool | Bridge |
|---|---|
| Grok | `~/.grok/config.toml` → `[skills] paths = ["<workspace>/.agents/skills"]` |
| Claude / Cursor | `scripts/skills_sync.sh` → each managed `project/.claude/skills/` |
| SoT | Always `.agents/skills/<id>/` — never edit project copies |

Not a cloud marketplace. **Local shelf + sync** is the coordination layer.

### E · Actions

| Finding | Action |
|---|---|
| You-starve implement ready | **Re-label** to best-fit hired hand |
| Escalate confused with assign | Teach: keep hand seat + human gate |
| needs:routing + hands exist | Route to hand or hire |
| L0 skills missing in project | `scripts/skills_sync.sh` |
| Dead papers path | Plant papers or pause schedule |

**Writes allowed for scheduled job:** report file + re-label starve tickets +
file at most a few routed WOs. **Never** mass-cancel. **Never** claim lane work.

### F · Process decay (law-vs-enforcement drift)

Catch drift before a human smells smoke. Bounded: call existing tools; **never
mass-fix** from this job.

```bash
python3 scripts/open_work_audit.py --decay
# optional when planted: blueprint doctor · check_no_host_paths
```

| Check | On smell |
|---|---|
| `skills_sync.sh --check` | Heal once, or file process WO |
| ALWAYS_WORK §9 rows without **Landed** | Confirm open routed WO; else file one classed WO |
| Open tickets on retired `worker:` ids | Re-label to live hand or file process WO |

**Gold scarcity:** when decay is found, **one** workspace rollup For You card —
not one gold per finding. Detail stays in the daily report + filed WOs.

---

## Report shape

Write:

`.protocolcity/ops/reports/workspace-efficiency/YYYY-MM-DD.md`

```markdown
# Workspace efficiency · YYYY-MM-DD

## Summary
- open / ready / in_motion
- You-starve count · needs:routing count
- queue_url probe: N bad / N missing
- deferred pile smells: N
- process decay: ok | smells=N

## You-starve (re-route)
| id | project | title | → seat |

## Queue URL issues (`--process`)
| hand | project | issue |

## Deferred pile (empty-hand smell)
| hand | project | ready | deferred_count |

## Process decay
- skills_sync: ok | fail
- §9 pending: none | list
- retired seats: none | list
- rollup gold: Y/N

## Actions taken
- re-labels …
```

---

## Seat fit

Use **your** hired hands (Map / Agents roster). Prefer the product’s usual
implement seat; when unknown, leave a short report line and file a routed WO
rather than inventing a persona.

---

## Done when

- Report written for the day (or chat summary if ad-hoc)
- You-starve implement tickets re-routed **or** listed for You with reason
- No bare `worker:you` left on ready implement work when a hand fit exists
- Process decay run (`--decay`): no decay **or** smells reported with classed
  WOs / one workspace rollup (no per-item gold spam)
