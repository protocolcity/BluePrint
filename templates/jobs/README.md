# Project jobs (optional paper packs)

Workspace ops (`templates/ops/`) stay at `.protocolcity/ops`. **These**
papers are hired **per project** — workdir is that project's
`.protocolcity`, not the ops kit.

| Pack | Role |
|---|---|
| [`code-efficiency`](code-efficiency/) | Scan oversized / god modules; file or land **one** extract-module split. Playbook: L0 skill `code-efficiency`. |

Not part of `blueprint seed-ops`. One command:

```text
blueprint hire efficiency-<project-slug> \
  --workdir <project>/.protocolcity \
  --kind job \
  --role 'scan oversized modules; file one split WO at a time' \
  --schedule '0 10 * * 1'
```

Copy `CONTRACT.md` + `prompt.md` into
`<project>/workers/efficiency-<project-slug>/` and fill placeholders.
Scan: `python3 scripts/code_size_scan.py --root <project>`.
Ticket shape: `templates/code-split-WO.md`.
