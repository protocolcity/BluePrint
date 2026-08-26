# {{CITY_NAME}} — Workspace instructions (L0 CORE)

<!-- Copy this file to your WORKSPACE ROOT as AGENTS.md (the folder that holds
     all projects). Fill every {{PLACEHOLDER}}, delete these guidance comments.
     Keep this file short (target ≤100 lines). Host chronicles belong in a
     separate registry doc, not here. Law you don't enforce is worse than no law.
     Citizen vocab: workspace · project · work order · Agents · You
     (see BluePrint SUITE_VOCABULARY dual register). -->

This folder is the **workspace** root. Sessions opened here are
**cross-project**. Deep work: open a project folder so its L1 `AGENTS.md` loads.

## One loop (read this first)

```
You + entry AI (author = you)
  → file work order (route worker:<hand> on create)
  → Agents drain that seat on a clock
  → Map shows live truth
  → true blocker → keep hand seat + gold For You (gate_type=human)
  → close on the ticket (history) — do not re-file from chat memory
```

| Stamp | Meaning |
|---|---|
| **Author** | You filed it (host chat intake) |
| **Seat** | `worker:<hand>` implements while you step away |
| **For You** | Only when the hand needs your decision / credential / publish |

**Load order:** this CORE → product always-work process (if installed) →
project `AGENTS.md` → hand CONTRACT/prompt. Skip long engine bibles unless
blocked.

## Project registry

<!-- One row per project. Single-project workspace: merge into that project's
     AGENTS.md until a second project exists. -->

| Folder | What it is | Work orders (prefix) | Status |
|---|---|---|---|
| `{{FOLDER_1}}/` | {{WHAT_IT_IS}} | `{{PREFIX_1}}-*` | {{live / drafting / dormant}} |
| `{{FOLDER_2}}/` | {{WHAT_IT_IS}} | `{{PREFIX_2}}-*` | {{...}} |

## Cross-project rules

- **Scope every work order explicitly.** At workspace root, never rely on a
  default project — pass the project's slug on every call (MCP).
- **Work spanning two projects = two work orders**, one per project,
  each scoped to its side of the boundary.

## Coordination (You in chat — any vendor)

BluePrint is vendor-neutral: pick any chat host + WorkLane MCP for capture, any
CLI for hired hands, suite as **glass**.

- **Capture** = chat + MCP (`wl_create`) — not suite Map forms. Never `tk`.
- **File = decided.** When You file a work order, hands work it — they do not
  re-ask for permission. Route with `worker:<id>` on create.
- **Hands** drain only tickets labeled `worker:<id>`
- **Assign ≠ escalate.** Assign = `worker:<hand>` on create. Escalate to You =
  keep the hand seat + `gate_type=human` / Blocked — never re-seat failed work
  to `worker:you` (that parks implement work where cron never drains).
- **Tag You only when needed.** Author is always You; gold For You is scarce
  (true blocker). Ordinary finish stays closed by the hand without re-asking.
- **History on the board.** Work orders + comments are the archive. Prefer
  dig-in / done trail over re-teaching the same outcome in a new chat.
- **For You** = roadblocks only (true decisions / sign-off) — not FYI, not
  “confirm this plan” after You already filed
- **Coord sessions** file / label / dispatch / escalate — they do **not** claim
  `worker:*` work when a hand runtime exists
- **Identity** default wire id: **`you`** (UI shows **You**)
- **Skills** live on **local disk** under `.agents/skills/` (preferred) and
  `.claude/skills/` — L0 always-on toolkit; L1 under each project. Not cloud.
  L0 must still load in **project** sessions (`scripts/skills_sync.sh` + Grok
  `[skills] paths` — see `.claude/skills/README.md` and `FIRST_RUN.md`).
- **Drain hygiene:** L0 skill + job `workspace-efficiency` (seeded by
  `blueprint seed-ops`) — ready-by-seat / You-starve on a cadence.
- **Capacity-aware:** vendor session / weekly limits are first-class process
  (ALWAYS_WORK §2d′). Do not thrash a capped seat; batch same-path tickets;
  re-pin payroll when a pool is hard-down. Glass: `capacity-<pool>` kind in
  For You (`workforce capacity` — ; wired to cadence by ).
- Full ladder: product docs `INSTRUCTION_LADDER.md` + `SUITE_VIEWER.md` when
  present in your BluePrint install

## Creating workers and work orders

When the citizen asks to create something, route by shape:

| Ask shape | Right move | Never |
|---|---|---|
| One-off outcome | File a **work order** | Create a new worker |
| Recurring fixed duty (report, sync, release) | **Job** (`kind=job`, function-named) | Give it a persona |
| Open-ended claiming worker for a project | **Agent hire** (`kind=lane`; persona optional) | Make it a staff seat |
| Coordination / triage powers needed | Point at the shipped **chief-of-staff** | Invent a second coordinator |

**Naming law:** Jobs and staff are function-named — the name states the duty
(`weekly-report`, `health-patrol`, not a person's name). Lane ids are
lowercase-kebab and stable forever — the id is a contract with the
work-order board.

```shell
# Seed the shipped ops trio (chief-of-staff, health-patrol, workspace-efficiency):
blueprint seed-ops --root <workspace>

# Hire an agent for a project:
blueprint hire <id> --workdir <project>/.protocolcity --kind lane

# Hire a recurring job:
blueprint hire <function-name> --workdir <workspace>/.protocolcity/ops --kind job
```

## Truth upkeep (board + papers — every project)

The work-order board is shared memory. **Closing a ticket hides the work.**

- **Sticky residual.** If work remains at close: keep the parent open, **or**
  file child tickets first and list those ids under `Follow-ups:`.  
  **`Follow-ups: none` means none** — not “tabled in the close comment.”
- **Docs drift.** If the change altered structural truth (entrypoints, process,
  public install lines, decision checklists / ADRs, architecture), update those
  papers **in the same close-out commit**. Name the doc updates under
  `Completed:` (or write `docs: no drift`). Stale truth files are invisible work.
- **Decisions with checklists.** When a later release lands a checklist item,
  tick the decision paper in that same slice — do not leave ratified ADRs
  half-checked forever.

WorkLane’s PROTOCOL (PROCESS) carries the full close-out rules; this section is
the short city-root reminder every neighborhood inherits.

## Boundaries

<!-- How projects are allowed to talk to each other. The strongest
     version names the mechanism and bans the rest, e.g.:
     "app consumes the store via HTTP only; importing its code is an
      automatic reject." -->

- {{PROJECT_A}} talks to {{PROJECT_B}} via {{MECHANISM}} only.

## Gates that need You (workspace-wide)

Anything below is prepared by workers but shipped only by a citizen:

- Publishing or making anything public
- Releases and version tags
- Money, credentials, and permissions
- Deleting anything that can't be regenerated
<!-- Add your own. Err on the side of gating; ungate by evidence. -->

## Vendor pointers (optional)

The canonical law file at every level is `AGENTS.md`. Vendor files are
optional thin pointers when a CLI needs its own filename — see
`templates/vendor-pointers.md`.
