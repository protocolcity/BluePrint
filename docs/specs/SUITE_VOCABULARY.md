# Suite vocabulary (current register)

Status: current, 2026-09-13. Supersedes the dual-register paper kept in the private aside folder; civic nouns (city, neighborhood, citizen, hand) are historical brand only and are not taught on any surface. Principle: nobody has to learn the history to run the system.

| Concept | Word on every surface | Wire / code (fine in code, never as chrome) |
|---|---|---|
| Founded root | **Workspace** | `workspace`, binder |
| Folder with its own store | **Project** | store slug, `desk-join.json` |
| Filed work | **Work order** | `task`, `wl-*` ids |
| Everything registered in the roster (the page) | **Agents** | roster, `/agents` |
| Roster row that claims work orders under its own identity | **Seat** | `kind=lane` (never say lane in chrome) |
| Roster row that runs a duty on a schedule or on demand and never claims | **Job** | `kind=job` |
| The person | **You** | `author=you`, `worker:you` |
| Act-now attention | **For You** with faces Decide · Read · Watch · Note | `gate_type=human`, reminders, timers |
| Parked on purpose | **Deferred** · **Tracking** (structural umbrella) | `gate_type=deferred`, `gate_type=tracking` |
| Binding instructions | **Instructions** | `AGENTS.md` |
| Scope file | **Boundaries** | `BOUNDARIES.md` (aliases `PERIMETER.md`) |
| Work engine | **WorkLane** | `:8799` API, `wl_*` tools |
| Execution engine | **WorkForce** | `:8797` API, roster, ledger, supervisor |
| The interface | **BluePrint** | `blueprint-overview`, `protocolcity` package |
| A worker's run | **Shift** (open · stale · last run) | ledger START/STOP/ERROR rows |
| A coordination pass | **Supervisor pass** | `/api/supervisor` evidence |
| Delivery evidence | **Repository activity** (GitHub) | Activity surface |

Hierarchy: You → Workspace → Project → Agent · Job. Operating loop: You and an entry AI file a work order → WorkLane queues it → WorkForce seats work it → BluePrint shows verified state and routes supported actions to the owning engine.

Surfaces: Overview · Work · Projects · Agents · Activity · Map · Calendar · Connections · Settings. Their definitions are in [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md).
