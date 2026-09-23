# BluePrint product development

BluePrint is the operations interface; WorkLane owns work-order state and WorkForce owns agent execution. Independent products keep their own business logic, data, and interfaces. Do not embed their runtime internals here.

The active application is `overview/v1/serve.py`, with shared Map modules in `map/v1/`. The historical `suite/` and recovered `protocolcity/` runtime remain during consolidation; avoid starting competing UI services. Product definition: `docs/PRODUCT.md`. Current operations design: `docs/specs/OPERATIONS_EVOLUTION_2026_09.md`.

## Implementation and verification

- Read from the explicitly selected workspace. Never fall back to another workspace's data or a fixed host port.
- Route writes through the owning engine with explicit project and verified store identity.
- Distinguish unavailable, stale, empty, and healthy data. GitHub evidence does not establish agent liveness.
- Keep source safe for distribution. Credentials, customer data, host connections, and internal operational history belong outside the product source.
- Test meaningful behavior with disposable workspaces. Package and verify outside the checkout before replacing a running release.
- Tests: `PYTHONPATH=overview/v1 python -m unittest discover -s overview/v1/tests`; `PYTHONPATH=map/v1 python -m unittest discover -s map/v1/tests`.
- Runtime data must survive updates. Source changes are not deployed until the installed build is identified and verified.
