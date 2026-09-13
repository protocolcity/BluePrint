# BluePrint operations architecture

BluePrint is the operations interface for a selected workspace. WorkLane owns work orders and writes. WorkForce owns registered agents, schedules, execution controls, and shift history. Project applications own their business logic and data. GitHub supplies delivery evidence; it does not establish agent liveness.

## Current application

`overview/v1/serve.py` serves one origin for Overview, Work, Projects and project papers, Agents, Delivery, Timeline, Map, Calendar, Connections, and Settings. `/activity` redirects to `/delivery`. `map/v1` provides the spatial document browser and keyboard-accessible folder list. Shared recovered `protocolcity` utilities support installation, workspace bridges, and audits; `suite/api` retains compatible calendar and routing helpers. Historical suite UI specifications describe earlier implementations and do not override this application or the accepted [operations design](docs/specs/OPERATIONS_EVOLUTION_2026_09.md).

## Data and authority

The selected workspace is explicit. Registered project manifests determine which stores appear; historical/unregistered databases are excluded without deletion. Read projections use read-only SQLite connections and distinguish unavailable, empty, stale, and healthy sources. Work-order actions go through the workspace's installed WorkLane engine, with explicit project/store verification and a record-version check for changes. Browser writes require the exact local origin and an action header. Document readers restrict paths and render untrusted content as text or escaped Markdown.

WorkForce heartbeat freshness is reported evidence, not a claim that every configured agent is working. Placeholder commands are unconfigured. Deterministic scheduled reports are labeled as jobs and carry result timestamps; they do not imply AI implementation coverage. Remote execution is unconnected until a real runtime and its authority are explicitly configured. Repository delivery evidence is collected separately from an explicit GitHub allowlist.

## Source and runtime

Canonical source is protocolcity/BluePrint. Work directly in sanitized product source; do not regenerate a public checkout from a private intermediate repository. CI validates source privacy and application behavior. Former export markers and private histories are historical evidence, not an ongoing update dependency.

Build an immutable wheel/environment, verify it outside the checkout, then activate only the BP service. The selected workspace retains configuration, reports, WorkLane stores, and WorkForce state. Starting the interface never hires agents or starts other engines. Root workspace tools use the installed release; development checkouts are not an implicit runtime upgrade. See [deployment and recovery](docs/operations/DEPLOYMENT.md).
