---
name: code-efficiency
description: >
  Per-project code-shape / modularization pass — scan for oversized and
  god modules, propose extract-module splits, execute one split at a time.
  Use when working a product folder, after landing a feature, when files
  feel too big, modularize, split a module, god class, oversized file,
  code efficiency, or /code-efficiency. Distinct from workspace-efficiency
  (queue drain hygiene). Also the playbook for per-project efficiency-* jobs.
---

# Code efficiency (L0)

**Purpose:** Keep product code navigable. Spot oversized / god modules
**without being asked**, propose a seam, and land **one** extract-module
split at a time.

**Law:** this skill. Structural truth: the project's `ARCHITECTURE.md`.  
**Companion:** `workspace-efficiency` is **drain hygiene only** — it must
**not** refactor product trees. This skill is the code-shape counterpart.

Citizen language: **project** (one folder) · **work order** · **You**.

This skill is **scan → rank → propose → one split (or one routed WO)**.  
Scheduled **job** `efficiency-<project>` follows the same checklist under
its CONTRACT.

---

## Do not wait to be asked

Any session that opens a **project folder** for implement work loads this
skill. A dedicated ticket is **not** a prerequisite.

| Trigger | Who |
|---|---|
| Open a project for implement / review | Code lane or host session |
| After a close-out that grew a file past a band | The hand that just landed it |
| Scheduled job `efficiency-<project>` | That job (scan + file; execute only if CONTRACT allows) |
| Host chat “modularize / god file / too big / code efficiency” | Coord or lane — load this skill |
| Empty implement feed + oversized files exist | Job files **one** routed split WO (do not invent product features) |

**Not** a substitute for `workspace-efficiency` (ready-by-seat / You-starve).
**Not** a license to rewrite a tree.

---

## Thresholds (default · override in project `AGENTS.md`)

Count **physical lines** and **bytes** on source files. Bands are smells,
not automatic rewrites — a generated 2k-line file is skip, not a split.

| Band | LOC | Bytes | Action |
|---|---|---|---|
| **watch** | ≥ 400 | ≥ 24 KiB | Note in the scan. Extract only if you are already editing this file and a seam is obvious. |
| **split** | ≥ 800 | ≥ 48 KiB | File **one** routed split WO, **or** extract this pass if you own the file and tests can stay green. |
| **urgent** | ≥ 1 200 | ≥ 80 KiB | Same as split, but this file is next after the current open split closes. Do not stack WOs. |

**God-module extras** (treat as **split** even under the LOC band):

- ≥ 12 public functions / types in one file **and** ≥ 3 unrelated jobs
  (I/O + domain + UI, or parse + persist + render)
- A module that every feature must edit
- Circular imports papered over with late imports / god `utils`

**Skip (never split from this playbook):**

`node_modules` · `.git` · `dist` / `build` / `.venv` / `vendor` ·
`__pycache__` · lockfiles · `*.min.js` · `*.map` · generated protobufs /
ORM migrations you do not own · binary / data dumps · third-party trees ·
instruction papers (`AGENTS.md`, contracts, prompts)

Prefer **extract module** (new file, same package, stable imports) over
rewrite, rename-the-world, or a new framework.

---

## Preflight

1. You are in **one** project folder (its `AGENTS.md` / `ARCHITECTURE.md`).
2. Know `{{TEST_COMMAND}}` (or the project’s test line). If you cannot
   verify, **file** a split WO — do not extract blind.
3. Scan:

```bash
python3 scripts/code_size_scan.py
# from a project folder:
python3 ../scripts/code_size_scan.py --root .
# JSON for a job report:
python3 scripts/code_size_scan.py --root <project> --json
```

(If `scripts/` is missing, walk the tree by hand with the same bands.
Do not invent a second scanner.)

4. Confirm no **open** split WO already exists for this project
   (`code-split` / `efficiency-split` label, or title `Split · <path>`).
   One in flight → **do not** file another.

---

## Checklist (every pass)

### A · Scan

- [ ] Run `code_size_scan.py` (or equivalent) from the project root
- [ ] Drop skip-globs; keep only first-party source
- [ ] List watch / split / urgent with path, LOC, bytes

### B · Rank (pick one)

Prefer the file that is **over band and in active motion** (you just
touched it, or it appears in recent commits). Else the largest urgent,
then split, then a watch file you are already editing.

Do **not** pick a file because it is ugly. Pick a file because it has a
**seam**: one cohesive extract with a name you can say out loud.

### C · Propose (before any edit)

Write the seam in the WO or a ticket comment:

```markdown
## Split proposal
- Source: `path/to/god.py` (LOC · band)
- Extract: `path/to/seam.py` — one job: …
- Stays: …
- Imports to update: …
- Tests: `{{TEST_COMMAND}}` (existing + any new for the seam)
- Out of scope: rewrite, rename public API, new deps
```

If the seam is unclear → comment `Proposal: …` with two options; do **not**
gold You for ordinary extract taste. Gold only for a true gate (public API
break, migration, publish).

### D · Execute **or** file (one, not both stacks)

| You are… | Do this |
|---|---|
| Code lane, ticket **is** the split | Extract now. One seam. Tests green. Close. |
| Code lane, other implement ticket, file is **watch** and you are in it | Extract only if it unblocks *this* ticket; else finish the ticket and file a follow-up split WO. |
| Code lane, file is **split/urgent**, ticket is unrelated | **File** one routed follow-up; do not hijack the ticket into a rewrite. |
| Coord / host chat / `efficiency-*` job | **File** one routed split WO to a hired code lane. Job executes a split only when its CONTRACT says so **and** no code lane exists. |
| No hired code lane | File the WO on the best existing implement seat; if none, one gold For You: “hire a code lane or allow this job to extract.” |

**One split work order (or one split PR) at a time per project.**  
Close or park the current one before filing the next.

### E · Extract (when executing)

1. Add the new module; move **one** cohesive chunk; re-export from the old
   path if callers would otherwise churn.
2. Update imports you broke. Do not drive-by lint the city.
3. Run the project test command. Red → revert the extract or fix **this**
   seam only. Two failed approaches → stop, comment, release.
4. If layers / owners / data-flow changed → update `ARCHITECTURE.md` in
   the **same** close-out (`docs: no drift` is a lie if you added a module).
5. Stage **explicit paths** only (never `git add -A`).

### F · Report (job / coord pass)

Write (disk-only — do **not** gold For You for a routine scan):

`<project>/local/reports/code-efficiency/YYYY-MM-DD.md`  
or `.protocolcity/ops/reports/code-efficiency/<project>/YYYY-MM-DD.md`

```markdown
# Code efficiency · <project> · YYYY-MM-DD

## Summary
- scanned files · watch / split / urgent counts
- open split WO: none | <id>
- action: filed <id> | extracted <path> | quiet

## Ranked smells
| band | path | loc | bytes | seam |

## Actions
- …

## Skipped
- generated / vendor / already-open split …
```

`report_to_for_you.py --scan` must **not** gold this report (efficiency
keys stay disk-only). `--act-now` only if a split is stuck on a dead seat.

---

## Never

- Rewrite a file from scratch “while we’re here”
- Split several files in one ticket / one PR
- Cross-project moves (two WOs, one per side of the boundary)
- Touch secrets, live money paths, host services, or citizen publish gates
- Mass-rename public APIs to make the extract prettier
- File a split WO when one is already open on that project
- Treat `workspace-efficiency` findings as a license to edit product code
- Invent product features so the job has “work”
- Skip tests or claim done without a verification line

---

## Seat fit

| Project has… | Route the split WO to |
|---|---|
| A hired code / implement lane | That `worker:<id>` |
| Several lanes | The lane whose CONTRACT already owns that path |
| Only jobs / staff | Do **not** claim; gold one hire-or-allow card |
| Foreign / upstream origin | File an **upstream** issue, not a local patch (see L0 foreign-repo rule) |

---

## Done when

- Scan exists (script output or equivalent table)
- Either **quiet** (no split/urgent, or an open split already in flight)
  **or** one extract landed with tests green **or** one routed split WO filed
- No second split stacked
- Architecture paper updated if structure changed
- Console one-liner for a job ledger: `code-efficiency <project> · watch=N split=N urgent=N · filed|extracted|quiet`
