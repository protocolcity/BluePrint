# Overview — operations landing

The running BluePrint app is `overview/v1/serve.py`. It serves Overview, Work,
Projects, Agents, Delivery, Timeline, Map, Calendar, Connections, and Settings
from one origin. Map modules live in `map/v1/`.

This directory still contains the earlier Mission Control peel
(`static/overview.html`, `static/js/overview.v1.js`, three equal tiles). That
shell is **not** the landing a packaged install serves. The live desk is
`static/operations.html` + `static/js/operations.js`, documented in
[OPERATIONS_EVOLUTION_2026_09.md](../../docs/specs/OPERATIONS_EVOLUTION_2026_09.md)
and [OVERVIEW_INTENT.md](../../docs/specs/OVERVIEW_INTENT.md).

## What the running desk does

- Reads the selected workspace only. Never falls back to another workspace
  or a fixed host port.
- Refreshes from `/api/operations` (15s default while visible; Settings can
  choose 30s or manual). A D2 change feed (`GET /api/changes`) pushes when
  WorkLane / WorkForce / supervisor files move; the poll is the fallback.
- Distinguishes unavailable, stale, empty, and healthy sources. GitHub
  delivery is not agent liveness. A WorkLane claim is "live with"; only a
  WorkForce shift paints a seat as working.
- Animates real content updates and interactions. Reduced motion is instant.

## Tests

```bash
PYTHONPATH=overview/v1 python -m unittest discover -s overview/v1/tests
PYTHONPATH=map/v1 python -m unittest discover -s map/v1/tests
```

## Design papers

[OVERVIEW_INTENT.md](../../docs/specs/OVERVIEW_INTENT.md) ·
[OVERVIEW_THEME.md](../../docs/specs/OVERVIEW_THEME.md) ·
[STATES_AND_TERMS.md](../../docs/specs/STATES_AND_TERMS.md) ·
[SURFACES_REVIEW_2026_09.md](../../docs/specs/SURFACES_REVIEW_2026_09.md)

Historical glass notes (`OVERVIEW_V1_GLASS.md`, three-tile peel) describe
the 2026-09 shell, not the current operations app. Do not re-implement them
as a competing landing.
