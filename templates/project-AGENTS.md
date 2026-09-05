# {{PROJECT_NAME}} — Project instructions (L1)

<!-- Copy this file to the PROJECT ROOT (the project's repo/folder) as
     AGENTS.md. Fill every {{PLACEHOLDER}}, delete these comments. This is
     the first thing any agent reads before touching your project — write
     it for a competent stranger. -->

## What this place is

{{ONE_PARAGRAPH: what the project does, who it's for, and anything an agent
must know before acting — e.g. "handles real customer data", "deploys
automatically on push", "prototype, nothing depends on it".}}

## Architecture

**Read [`ARCHITECTURE.md`](ARCHITECTURE.md) before structural work.** Layers,
sources of truth, data-flow direction, and invariants live there — not only
in vault research notes. Any structural change updates that paper in the same
close-out.

## Papers and exports

Human+AI editable papers are **Markdown**. Derived files (pptx, PDF, HTML
renders) are **exports**, not the paper. Named lines of work live in
[`PROGRAMS.md`](PROGRAMS.md) (3–5; twigs stay off the Wall). The product's
named surfaces — what each feature is called, where it lives, and how a hand
verifies it — live in `docs/FEATURES.md` (template: `FEATURES.md`).

Exceptions — do not convert these to Markdown: **code**, **databases**,
**secrets**, **binary assets**.

## How to run and test it

```
{{RUN_COMMAND}}
{{TEST_COMMAND}}
```

<!-- If verification is more than one command, link a doc. An agent that
     can't verify its work must stop and say so, not guess. -->

## The desk

- Ticket store: `{{STORE_SLUG}}` (work orders `{{PREFIX}}-*`)
- Every change ties to a ticket; every ticket close-out states what was done
  and how it was verified. Residual work stays on the board (child tickets or
  open parent) — not only in a `Follow-ups:` prose note. If you changed
  structural truth (process, public install, decision checklists), update
  those papers in the same close-out.
- **File** work via chat + WorkLane MCP (any vendor). The suite Map is a live
  viewer — not a ticket compose form.
- **Route** each ready ticket to a hand: label `worker:<id>` (or it stays
  visible as needs routing but no schedule drains it).

## Boundaries and no-go zones

<!-- The most valuable section. Name what agents must never touch and why,
     e.g. payment code, production configs, migration files, another
     project's internals. -->

- {{NO_GO_1}} — {{WHY}}
- {{NO_GO_2}} — {{WHY}}

## Code shape (proactive)

Do **not** wait to be asked. When working this folder, load L0 skill
`code-efficiency` (workspace `.agents/skills/code-efficiency/`) and keep
modules extractable.

Default bands (override here if this tree is generated-heavy): **watch**
≥ 400 LOC / 24 KiB · **split** ≥ 800 / 48 KiB · **urgent** ≥ 1 200 / 80 KiB.
Prefer extract-module over rewrite. Keep `{{TEST_COMMAND}}` green. **One**
split work order (or PR) at a time.

```
python3 scripts/code_size_scan.py --root .
# planted script lives at the workspace root when found from BluePrint:
# python3 ../scripts/code_size_scan.py --root .
```

Optional cadence job (papers: BluePrint `templates/jobs/code-efficiency/`):

```
blueprint hire efficiency-{{STORE_SLUG}} \
  --workdir <this-project>/.protocolcity \
  --kind job \
  --role 'scan oversized modules; file one split WO at a time' \
  --schedule '0 10 * * 1'
```

Foreign / upstream origin: file an upstream issue, not a local split
patch (workspace foreign-repo rule).

## The agents here

<!-- Who is hired on this project (optional at found). -->

- {{AGENT_1}} — {{ROLE}}
