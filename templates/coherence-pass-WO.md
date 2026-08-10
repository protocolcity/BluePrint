# Coherence-pass work order — {{PROJECT}} · {{LAW_CHANGE_ID}}

> Instrument: architecture-first companion (ALWAYS_WORK §2l).  
> Filed by: {{FILER}} as follow-up to {{LAW_CHANGE_WO}}.  
> Early instances: POS · trading · BP suite architecture passes.

## Why

{{LAW_CHANGE_WO}} landed a binding law change:

> {{ONE-LINE SUMMARY OF THE LAW CHANGE}}

Surfaces built before this rule may not comply. This pass audits every surface
the new law touches, ranks drift by severity, and routes children.

## As-built map

| Surface | File:line | Law rule | Compliant? |
|---|---|---|---|
| … | `…:…` | … | yes / no / partial |

Fill one row per surface the new law touches. "Surface" = a module, route,
template, or doc that must satisfy the law's invariant. File:line is the
narrowest citation that anchors the assessment.

## Drift register

| # | Surface | File:line | Severity | Note |
|---|---|---|---|---|
| 1 | … | `…:…` | critical / major / minor | … |

**Severity key:**

| Severity | Meaning | Action |
|---|---|---|
| **critical** | Live invariant violated; breaks the law's hard guarantee | Fix before next release; child WO this wave |
| **major** | Law intent violated; no hard break but drift accumulates | Child WO this wave |
| **minor** | Law direction not followed; low risk now | File child or defer with explicit thaw condition |

## Child WOs

Filed as follow-ups from this ticket (log ids in a comment here):

| Child WO | Seat | Severity class | Surface |
|---|---|---|---|
| {{child-id}} | `worker:{{hand}}` | critical / major | … |

**Child rules:**
- One WO per critical/major drift item.
- Route `worker:<hand>` on create; do not leave unrouted.
- Attach `parent:{{THIS-WO}}` label on each child.
- Log all child ids in a comment on this ticket immediately after filing.
- Children drain under runway rules — no forced serialization.
- Minor items: file a deferred child or add a thaw note here; do not silently drop.

## Sequencing

1. File this WO in the same `follow_ups:` field as {{LAW_CHANGE_WO}}'s close-out.
2. Fill the as-built map before claiming any children.
3. Children drain in normal seat order; no single-path lock unless surfaces collide.
4. Close this ticket when: all critical children closed + law doc updated.

## Paper update (same close-out)

When this pass closes, update the law doc ({{LAW_DOC}}) in the same commit:

- Add `Status: LIVE · coherence pass: {{THIS-WO}}` to the header.
- Add `Register: {{THIS-WO}} ({{DATE}})` line citing the drift register.
- Add ATLAS row if a new governance file was created.

## Done when

- [ ] As-built map complete — file:line for every surface the law touches
- [ ] Drift register ranked — all critical/major items filed as children
- [ ] Minor items filed or explicitly deferred with thaw condition
- [ ] Law doc updated with `Status: LIVE` and `Register:` pointer in same commit
- [ ] ATLAS row added (if a new governance file was created)
- [ ] Child ids logged in a comment on this ticket
