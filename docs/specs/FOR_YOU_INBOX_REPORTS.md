# For You inbox · reports (all BluePrint workspaces)

**Citizen model:** Map **For You** is the workspace **paper pile / inbox**.
**Read** face = inbox-report cards (this doc). **Decide** face = act-now
roadblocks. **Note** face = quiet Your list (not gold). Same pile, one
product name — not a second “Needs You” stamp.

**Face icons:** Decide and Read use distinct icons and pill colors
so act-now gates and read/snooze reports are visually different at a glance:
Decide = `▲` + terracotta pill (`st-decide`); Read = `📄` + steel-blue pill
(`st-read`). Watch = `⏱`/`👁` + amber. Never share the same glyph or wash.

Reports that only land under `local/reports/` are invisible. Hands and jobs
must **drop** a human-gated work order when a citizen-facing report is written.

**Canonical membership + scarcity:**
[`ALWAYS_WORK_PROCESS.md` §2i + §5](ALWAYS_WORK_PROCESS.md)
(Decide / Read / Note table). Research:
[`../research/for-you-inbox-vs-needs-you-2026-08-02.md`](../research/for-you-inbox-vs-needs-you-2026-08-02.md).

## Rules

| Rule | Detail |
|---|---|
| Gold gate | `gate_type=human` + `gate_note` act-now (not deferred/umbrella parking language) |
| Seat | `worker:you` + `you:todo` (inbox — not a hand claim queue) |
| Body | Report path + short glance + how to snooze/clear |
| Idempotent | One card per report kind per day — label `inbox-report:<project>:<key>:<date>` |
| No spam | One item per **kind**/day, not every intermediate file |

## Gold vs rollup policy

| Report kind | Default drop | Per-product gold? |
|---|---|---|
| Workspace efficiency | **Disk-only** | `--act-now` only for stuck hand / critical feed failure |
| Engine `efficiency-*` | **Disk-only** | `--act-now` only for stuck hand / critical feed failure |
| Maru desk brief (Trading) | Gold — coord skim | n/a (single product) |
| CITIZEN read packs | Gold — coord skim | n/a |
| Workspace digest | Gold — one card/day | n/a |
| Correspondent / clerk ops | Single session card | — |
| **Provider capacity thrash** (`capacity-<pool>`) | One workspace gold (`gate_type=human`) when a CLI pool is hard-blocked and seats ERROR in a streak (vendor_limit / usage 0%); idempotent label `inbox-report:workforce:capacity-<pool>:<date>`; engine:  | Not per-hand spam — ALWAYS_WORK §2d′ + §2i |

`--scan` anti-pattern: a single `--scan` run must not mint one human-gated
gold per product for efficiency. Efficiency is a workspace concern — roll up
into one card (or write to disk) unless a specific product needs act-now action.

## Dual-audience holistic brief

One gold card per project per day carries **both** sections — not two separate
golds. Workspace rollup instead when a project's output is thin.

### Product matrix

| Product | User section — what the product delivers for the citizen | Builder section — ops health for hands |
|---|---|---|
| **Trading** | Portfolio status · active plays · risk exposure · RSU window notes (when relevant) | Hands / board · deploy state · health series |
| **protocolcity** | Suite / Map state · CLI ready status · notable ship | Hands / board · build health · serve state |
| **worklane** | Board health · throughput · For You gold count | Routing audit · process metrics · feed probes |
| **workforce** | Agent outcomes · last-shift closes · empty-run signal | Runner health · feed probes · hire / retire events |
| **register** | Day close · shift sales summary · register floor floor till status | Day-close job state · transaction log health · inventory sync probes |
| **socials** | Content published · arc chapter progress · scheduled drafts ready | Mittens backlog state · deferred gate thaw signals · publish queue |
| **connector** | Integration sync status · connected product handoffs (emit when active) | Connection health · sync probes · job state — dormant: no daily report until reconnect work opens |

### Dual-audience gold rules

| Rule | Law |
|---|---|
| One card / project / day | Holistic brief — Builder + User in one body, one human-gated ticket |
| Workspace rollup | Use when a project's output is thin or all-ops — no per-product gold needed |
| Efficiency / board-validation | **Never gold by default**. Dated reports stay on disk for on-demand read. `--act-now` only for stuck hand / critical feed failure |
| Trading desk brief | Remains gold (coord skim) — carries both sections |
| CITIZEN read packs | Gold (coord skim) |
| Sparse day | Skip per-project gold; fold any signal into workspace rollup |

### Report-body structure

```
## [Product] — [date]

### Builder
[hands status · board · deploy · health]

### User
[portfolio / plays / risk / product-purpose content]

**Report:** city-rel path to full .md or .html
```

Generators that do not yet emit dual sections need child implement tickets
filed at law adoption.

## Tools

| Tool | Use |
|---|---|
| `scripts/report_to_for_you.py` | Workspace multi-project drop + `--scan` — **the For You bridge** (planted as `templates/scripts/report_to_for_you.py`) |
| `python -m core.ops.for_you_drop` (Trading) | Maru desk brief HTML + CITIZEN gold |
| **github-desk** | Public GitHub **issue intake + close** — **not** a For You drop path |

```bash
# after any report write
python3 scripts/report_to_for_you.py --workspace <ws> \
  --project trading --key maru-desk-brief \
  --title "Trading · desk brief · 2026-08-02" \
  --path Trading/local/reports/maru/2026-08-02-desk-brief.md

# catch-up all known slots for today
python3 scripts/report_to_for_you.py --workspace <ws> --scan
```

## Who drops what

| Report | Job / hand | Drop |
|---|---|---|
| Maru desk brief | maru | `for_you_drop` + optional scan |
| Trading efficiency | efficiency-pass | **Disk-only** (no gold; `--act-now` only on smell) |
| Workspace digest | digest job | auto in `protocolcity.digest` |
| Correspondent / clerk | ops jobs | `--scan` rollup |
| Engine efficiency-* | each job | **Disk-only** — write report; do not gold via `--scan` |
| workspace-efficiency | L0 job | write report; **disk-only** |
| `capacity-<pool>` alert | workforce capacity detector | Gold `gate_type=human` when pool hard-blocked; `inbox-report:workforce:capacity-<pool>:<date>`; mark read when pool clears, snooze if not blocking |

## Law

`ALWAYS_WORK_PROCESS` **§2i** (Read drop rules) + **§5** (paper-pile membership:
Decide / Read / Note; scarcity by face).  
Labels: `WORK_ORDER_LABELS` (gold = human gate for Decide + Read; Note quiet).  
Skill: `workspace-efficiency` §F.  
Collision research + target model: `docs/research/for-you-inbox-vs-needs-you-2026-08-02.md`.


## Path truth (all BluePrint projects)

Suite resolves files from the **workspace (city) root**, not a product repo
cwd. Every report path in a ticket body must be city-root-relative:

| Write | Example | Resolves |
|---|---|---|
| **City-rel (required)** | `Trading/local/reports/for-you/latest.html` | ✓ |
| Repo-rel (legacy) | `local/reports/for-you/latest.html` | Suite prefixes product folder + `/api/city-asset?project=` fallback |

| Product slug | On-disk folder |
|---|---|
| `trading` | `Trading` |
| `protocolcity` | `ProtocolCity` |
| `worklane` | `worklane` |
| `workforce` | `workforce` |
| `register` · `connector` · `gridfinity` · … | same as slug |

Drops (`for_you_drop`, `report_to_for_you`) **must** emit city-rel paths.
Suite also rewrites `local/reports/…` using the ticket product so old gold
cards still open.

## Dig-in face

Inbox-report tickets open in SuitePaper as **Inbox · {kind}**, not
**Work order · For You**. The **report file is the product** — dig loads it
inline. The ticket is only an inbox index (gold + snooze + path).

Classifier (`isInboxReport`): `inbox-report*` label · title `Inbox ·` ·
`report` + (`you:todo` | `you:host` | `for-you`) · CITIZEN/human packs with
`local/reports/` paths in the body.

| Dig-in chrome | Meaning |
|---|---|
| **Mark read** | Primary dismiss — `status=done` on report ticket, close dig, refresh For You gold |
| **Snooze 1d** | Mute gold 1 day (attention snooze); not implement cancel |
| **Report body (inline)** | Primary content — `.md` via `/api/file` + `renderMd`; `.html` auto iframe |
| **Also open** | Secondary — paper / new tab escape only |
| Path meta | City-rel path under secondary |
| Foot | “Mark read when done · not implement work” |
| Pane | Wide stage (`is-report-inbox`) — body fills sheet, not a narrow left column |

**Do not** require a second click for content. Ticket body glance is fallback
only when file fetch fails.

**Theme:** Dig-in preview injects `#suite-report-theme` so report CSS
vars (`--bg`, `--text`, …) map onto suite paper tokens for the active
light/dark resolution. Frame chrome uses suite tokens — not a fixed dark
skin. Settings appearance flips re-skin ready previews without re-fetch.
On-disk drops may still ship a dark default for raw `/api/city-asset` tabs;
prefer suite frame tokens over re-authoring every generator.

Drop bodies: `**Visual:**` / `**Report:**` + backticks, city-rel paths.
