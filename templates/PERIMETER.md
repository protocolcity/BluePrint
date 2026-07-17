# PERIMETER — cross-cabinet grants

<!-- Copy this file to the city root (next to AGENTS.md) as PERIMETER.md.
     Fill the registry when two cabinets truly share a boundary. Delete these
     guidance comments. Legacy names still accepted if present:
     OFFICE_PERIMETER.md, CITY_EDGES.md (at city root only). -->

**Owner of truth:** this file (Office / city root).
**Nature:** versioned law + machine-readable table — **not** a discovery
heuristic. The lens never infers edges from imports, git remotes, or the
filesystem.

**System definition:** an Office = a folder + a roster + a perimeter registry.
**Level:** L0 only — cabinets (L1) use the implicit home default; worker
contracts (L2) and prompts (L3) may promise scope but do not own this registry.

---

## THE WIDTH LAW

**Edges render only from this registry.** Every drawn connection on the map
cites a row of law here. An Office with every possible line drawn is
spaghetti; one with only its ratified lines drawn is a map of the law.

| Rule | Meaning |
|---|---|
| **Declare, never infer** | The lens does not invent connections from code, git, adjacency, or URLs. |
| **Cite the law** | Each edge carries a one-line rule and an owner path. |
| **Add a row to draw a line** | Citizen-ratified table row — never a map-side heuristic. |
| **Skip if absent** | If a named endpoint is not on the scene, that edge is skipped silently. |

---

## THE GRANT MODEL

### THE IMPLICIT DEFAULT

**Every worker and every cabinet reads and writes its own folder.**
That home scope needs no registry row. Registry rows are the **only**
extensions or restrictions beyond this default. An empty table below is a
valid founding: sovereign cabinets, no cross-grants, no drawn edges.

### Law, not enforcement

This file is **declared law**. The map renders it; contracts promise it;
enforcement is the runner's seam (derive worker scopes from home +
registry). Until that lands, honesty holds: the map shows the grant; the
OS does not yet cut off a hand that ignores it.

### Kind → grant

| kind | read | write | via |
|---|---|---|---|
| `consumes-http` | none (no source access) | none | the target's HTTP interface only |
| `export-lane` | source | target, generated output only | the export script only — no hand edits the artifact |
| `press-pass` | everywhere | home only | direct reads; citing is governed by the home's own law |
| `reference-only` | inbound only | none (and never push) | findings become tickets in the consuming neighborhood |

---

## Registry (machine-readable)

Columns: `from | to | kind | rule | owner`. Parsers take data rows only;
header and separator rows are ignored. **Start empty — add a row only when
a cross-boundary rule is real.**

| from | to | kind | rule | owner |
|---|---|---|---|---|

<!-- Example row (delete or replace):
| app | store | consumes-http | app consumes the store via HTTP only — no direct imports | docs/adr/ADR-001.md |
-->
