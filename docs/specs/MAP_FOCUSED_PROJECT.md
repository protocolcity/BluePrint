# Map — focused exploded project (approved direction, 2026-09-13)

Current surface reference. Read [the product contract](../PRODUCT.md) first.

## One sentence

Map shows one project in focus with its four direct context branches (Work, Agents, Papers, Delivery), expands exactly one branch at a time, and keeps the sidebar, canvas and breadcrumb on the same selection so a person always knows where they are and how to get back.

## Rules

- One project in focus; the other projects stay reachable in a stable sidebar. Selecting a project replaces the canvas; it never layers every project behind its children.
- Four virtual branches per project: Work, Agents, Papers, Delivery. They are context sections, not folders, and are never drawn as folders. Papers keeps the real folder/file tree with exact names; source folders (static, tests, templates) are not exposed until the person asks to browse them.
- One expanded branch. Opening a branch collapses the previously open one to its compact form. Counts on a compact branch are named ("4 open · 1 For You", "1 working"), never bare number triplets.
- One selected detail area. Selecting an item (work order, seat, paper, PR) shows its summary there with the same words the owning surface uses and a link to the original evidence; the reader opens from it and returns to the same branch and selection.
- Sidebar, canvas and breadcrumb share one selection; browser back/forward, refresh and reader return restore it (URL carries project, branch and item).
- Work counts follow STATES_AND_TERMS §5 (All open includes every gate). A WorkLane claim is "live with", never "working"; only WorkForce shift evidence paints a seat as working.
- Motion explains what opened and where it came from: a short expansion from the parent node, stable positions for everything else. A real change-feed event (WorkLane / WorkForce / supervisor file move) may flash the matching branch and tick a changed count once. No force or orbit layout, no ambient movement, no agents moving around. Reduced motion switches to immediate state changes.
- Narrow widths render the same hierarchy as an expandable list with the same selection model, not a miniature canvas.
- Text stays legible at the default zoom; large levels disclose counts and offer bounded navigation instead of shrinking labels.

## Sources

Project registry and per-project counts from the operations projection; seats from the Agents projection; papers from the documents catalog; delivery from the remote-activity cache with its observation time. Unavailable sources label the branch "unavailable", never empty.

## Validation

With real records: locate BluePrint, find its working seat and the order it holds, open an instruction paper, return to the same branch and selection, switch projects. The person should be able to explain every drawn line before the view is accepted. Record loss of orientation as a failure; visual appeal alone is not acceptance.
