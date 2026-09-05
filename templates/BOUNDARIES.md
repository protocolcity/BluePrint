# Boundaries — cross-project grants

<!-- Copy this file to the workspace root (next to AGENTS.md) as BOUNDARIES.md.
     Fill the registry when two projects truly share a boundary. Delete
     these guidance comments. Forever aliases still accepted if present:
     PERIMETER.md, OFFICE_PERIMETER.md, CITY_EDGES.md (workspace root only). -->

**Owner of truth:** this file (workspace root).
**Nature:** versioned instructions + machine-readable table — **not** a discovery
heuristic. The Explorer never infers edges from imports, git remotes, or the
filesystem.

**System definition:** a workspace = a folder + agents + a boundaries registry.
**Level:** L0 only — projects (L1) use the implicit home default; agent
contracts (L2) and prompts (L3) may promise scope but do not own this registry.

**Vocab:** the L1 unit is a **project**. Do not call it a "cabinet" or
"neighborhood" in install copy.

---

## THE WIDTH LAW

**Edges render only from this registry.** Every drawn connection on Explorer
cites a row here. A workspace with every possible line drawn is spaghetti;
one with only its ratified lines drawn is a map of the grants.

| Rule | Meaning |
|---|---|
| **Declare, never infer** | Do not invent connections from code, git, adjacency, or URLs. |
| **Cite the law** | Each edge carries a one-line rule and an owner path. |
| **Add a row to draw a line** | You-ratified table row — never a map-side heuristic. |
| **Skip if absent** | If a named endpoint is not on the scene, that edge is skipped silently. |

---

## THE GRANT MODEL

### THE IMPLICIT DEFAULT

**Every agent and every project reads and writes its own folder.**
That home scope needs no registry row. Registry rows are the **only**
extensions or restrictions beyond this default. An empty table below is a
valid founding: sovereign projects, no cross-grants, no drawn edges.

### Instructions, not enforcement

This file is **declared grants**. Explorer renders it; contracts promise it;
enforcement is the runner's seam (derive agent scopes from home +
registry). Until that lands, honesty holds: the map shows the grant; the
OS does not yet cut off a hand that ignores it.

### Kind → grant

| kind | read | write | via |
|---|---|---|---|
| `consumes-http` | none (no source access) | none | the target's HTTP interface only |
| `export-lane` | source | target, generated output only | the export script only — no hand edits the artifact |
| `press-pass` | everywhere | home only | direct reads; citing is governed by the home's own instructions |
| `reference-only` | inbound only | none (and never push) | findings become tickets in the consuming project |

### Worked example — ProtocolCity (suite) ↔ oneseo-pos (product)

This is **row style**, not a planted grant. Copy it into the workspace-root
registry only when that sibling product is actually on the scene. The OS
does not enforce the row; Explorer renders it and contracts promise it.

On the ProtocolCity dogfood host the pair is:

| from | to | kind | rule | owner |
|---|---|---|---|---|
| protocolcity | oneseo-pos | reference-only | Suite may cite Map prefixes and work-order vocabulary only — do not import POS app code. POS system-of-record and ops papers live in the POS repo, not city hall. | BOUNDARIES.md |

Keep Map / ticket prefixes for dogfood wiring. Do not copy POS runbooks,
host identity, or payment-provider rulings into ProtocolCity city hall.

---

## Registry (machine-readable)

Columns: `from | to | kind | rule | owner`. Parsers take data rows only;
header and separator rows are ignored. **Start empty — add a row only when
a cross-boundary rule is real.**

| from | to | kind | rule | owner |
|---|---|---|---|---|

<!-- Example row (delete or replace):
| webapp | api | consumes-http | webapp consumes the api via HTTP only — no direct imports | docs/adr/ADR-001.md |
-->
