# Features — {{PROJECT_NAME}}

<!-- Copy to the project as docs/FEATURES.md (or the project root next to
     AGENTS.md when the project has no docs/). One table of citizen-named
     surfaces. Fill every {{PLACEHOLDER}}, delete the guidance comments. -->

{{ONE_LINE: the product's named surfaces — one row each, glass-checkable.}}

The named surfaces of this product: the words You and chat actually say
("For You", "the tape", "back-ops") tied to where each one lives and how a
hand checks it on live glass. Not [`PROGRAMS.md`](PROGRAMS.md) (named tracks
of work). Not the route inventory (pages/routes have their own table, e.g.
`SUITE_PAGES.md` / `PAGE_INVENTORY.md`). Hands use this table two ways:
**verify** the full set still works after a change, and **propose**
enhancements against a named row instead of a vague area.

| Feature | Where (route / surface) | Verify (how an agent checks) | Notes |
|---|---|---|---|
| {{FEATURE_1}} | {{WHERE_1}} | {{VERIFY_1}} | {{NOTES_1}} |
| {{FEATURE_2}} | {{WHERE_2}} | {{VERIFY_2}} | {{NOTES_2}} |
| {{FEATURE_3}} | {{WHERE_3}} | {{VERIFY_3}} | {{NOTES_3}} |

Rules:

- Citizen words win the **Feature** column — the name You says out loud,
  not the module name. Internals stay in `ARCHITECTURE.md`.
- One row per surface a citizen can point at. Sub-parts share the parent
  row's Notes until they earn their own name.
- **Verify** is something an agent can run or look at (a route + element,
  a command, a file that must exist) — never "should work".
- Update the row in the same slice that changes the surface.
