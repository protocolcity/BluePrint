# Boundaries — cross-project grants

<!-- Copy to the workspace root as BOUNDARIES.md. Fill only actual grants. -->

This registry describes authorized relationships between projects. Each project
works within its own authorized scope. An empty registry is valid. Instruction
files do not enforce a sandbox: credentials, runner tools and operating-system
controls determine actual access.

The optional BP Map may render declared relationships. It must not infer a grant
from a link, adjacent folder, import or repository remote. A displayed edge is a
declaration, not proof that enforcement exists.

## Kinds

| kind | Meaning |
|---|---|
| `consumes-http` | Use the target's authorized HTTP interface; no direct source or database access |
| `export-lane` | Write generated output through the declared export process only |
| `press-pass` | Read the declared scope; write only in the home project |
| `reference-only` | Consult the target as reference; no writes or publication to it |

## Registry (machine-readable)

Use the columns below. Each owner is an existing instruction or decision path.
Add a row only within authorization for both owning products. Legacy filenames
may remain as aliases; keep a single canonical registry.

| from | to | kind | rule | owner |
|---|---|---|---|---|

<!-- Synthetic example; replace before adopting:
| webapp | api | consumes-http | webapp uses the authorized API; no direct database access | BOUNDARIES.md |
-->
