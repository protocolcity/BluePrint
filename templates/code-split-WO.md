# Split · `{{SOURCE_PATH}}` — {{PROJECT}}

> Instrument: code-efficiency extract (L0 skill `code-efficiency`).  
> Filed by: {{FILER}} · route `worker:{{CODE_LANE_ID}}` on create.  
> One open split WO per project — do not stack.

## Why

`{{SOURCE_PATH}}` is past the **{{BAND}}** band ({{LOC}} lines · {{BYTES}}).
It mixes more than one job. Extract **one** seam; do not rewrite the file.

## Split proposal

- **Source:** `{{SOURCE_PATH}}`
- **Extract:** `{{SEAM_PATH}}` — one job: {{SEAM_JOB}}
- **Stays** in the source: {{STAYS}}
- **Imports to update:** {{IMPORTS}}
- **Out of scope:** rewrite, public API rename, new dependencies, second file

## Verify

```
{{TEST_COMMAND}}
```

A claim of done without this line is not done. Red twice on the same
approach → stop, comment, release.

## Paper

If the extract changes layers / owners / data-flow, update
`ARCHITECTURE.md` in the **same** close-out. Else write `docs: no drift`.

## Done when

- [ ] New module exists and owns only {{SEAM_JOB}}
- [ ] Source file imports or re-exports the seam (callers keep working)
- [ ] `{{TEST_COMMAND}}` green
- [ ] Architecture paper updated or `docs: no drift`
- [ ] Follow-ups: none **or** one next-split child listed by id (do not
      file it until this ticket is done)

## Labels

`worker:{{CODE_LANE_ID}}` · `code-split` · `parent:{{PARENT_ID_OR_OMIT}}`
