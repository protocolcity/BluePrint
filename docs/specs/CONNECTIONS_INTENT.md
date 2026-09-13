# Connections INTENT — reachable, usable, fresh and installed as separate facts

Status: design record for pc-1490, 2026-09-13. Companion to [STATES_AND_TERMS.md](STATES_AND_TERMS.md), [SURFACES_REVIEW_2026_09.md](SURFACES_REVIEW_2026_09.md) and [OPERATIONS_EVOLUTION_2026_09.md](OPERATIONS_EVOLUTION_2026_09.md). Paint follows [OVERVIEW_THEME.md](OVERVIEW_THEME.md); no new tokens, fonts or libraries.

## One sentence

Connections says where each number on the desk comes from and how far that evidence goes: whether the origin answered, whether the payload was usable, how fresh a successful read is, what the last operational outcome was, and which build is installed — never one green badge for all of those.

## Is / Is-not

| Connections IS | Connections IS NOT |
|---|---|
| The source ledger for the selected workspace: project stores, WorkForce roster and heartbeat, calendar file, engine receipts, WorkLane API, supervisor last pass, GitHub delivery, excluded filenames | A second Overview, a process monitor, or a place that starts engines |
| Four independent facts per source: **reachable**, **usable**, **fresh** / last observation, **installed** | A single Available/healthy badge that collapses those facts |
| Honest about a 404: an HTTP responder is reachable; it is not a usable WorkLane API | A probe of an undocumented `/health` path treated as capability |
| A reader of failed evidence: a readable supervisor failure is available evidence with a failed outcome | A green pass because the report file or endpoint could be read |
| Exception-first, with one next step and raw endpoint/path/version behind a disclosure | A wall of equal rows, or a live-transport chip that hides a failed source |

## Fields

| Field | Means exactly | Must not |
|---|---|---|
| Reachable | the verified local origin (or file) answered | stand in for a usable API or a healthy daemon |
| Usable | the documented payload shape was present (WorkLane: `GET /api/admin/products` with `ok` and a `products` list) | be inferred from any HTTP status, including 404 |
| Fresh / last observation | when BluePrint last read this source | reset "last change" or the change-feed transport state |
| Last successful observation | when the last usable payload was read, even if that payload's outcome is a failure | move because a heartbeat ticked |
| Last operational outcome | the engine's own last result (supervisor `pass_outcome`, heartbeat age class) | paint as Available because the evidence was readable |
| Installed / activated | version and activation time from the workspace deployment receipt | be labelled Observed, or stand in for live daemon identity/health |
| Unknown | the engine or file could not be read | be painted as zero, idle or Available |

The header **Updates connected / Live** chip is only the change-feed transport. It never stands in for source freshness or capability. A failed, stale, partial, unreachable or merely-reachable source still appears as an exception while that chip reads Live.

## WorkLane probe

Canonical WorkLane names `GET /api/admin/products` as the health-check (README / INSTALL). `/health` is not a documented API; a 404 there only proves an HTTP responder.

| Probe result | Reachable | Usable | Badge | Next step |
|---|---|---|---|---|
| No receipt, or origin not a verified local `http://127.0.0.1\|localhost` | no | no | unavailable | Select this workspace's installation receipt; never fall back to another workspace or a default port |
| Connection error / timeout | no | no | unavailable | Start WorkLane on the verified local origin from the receipt |
| Redirect off the verified origin | no | no | unavailable | Confirm the receipt origin stays on this machine |
| HTTP reply other than a usable products list (including 404) | yes | no | reachable | Confirm `GET /api/admin/products` returns the product list; retain the HTTP status |
| HTTP 200 with `{ok: true, products: [...]}` | yes | yes | available | — |

No engine change is required for this order. If a future WorkLane `/health` capability is wanted, that is a WorkLane order, not a BluePrint one.

## Supervisor last pass

`GET /api/supervisor` on the verified WorkForce origin. A 404 is **not configured** (this engine does not report passes). A readable payload is usable evidence.

| Last `pass_outcome` | Badge | Reading |
|---|---|---|
| dispatched, proposed, no eligible ready work, stopped by operator | available | last outcome named beside the badge |
| failed, provider_failed, escalated | **failed** | available evidence, failed outcome — not an overall green pass |
| no passes yet | empty | usable endpoint, nothing recorded |

## Receipts

`local/worklane/deployment.json` and `local/workforce/deployment.json` establish **installed version** and **activated** time. They do not establish that a daemon is running or that an API is usable. Badge: **installed**. Timestamp label: **Activated**, never Observed. WorkLane API and Supervisor last pass are live probes: they belong under Engine capabilities, and in Needs attention when they are exceptions, never under Installed engines.

## Primary hierarchy

```
CONNECTIONS                         Live (transport only) · N sources need attention

  Needs attention
    WorkLane API     reachable     Reachable · health not verified · HTTP 404
      Next: Confirm GET /api/admin/products on the verified origin.
      [Endpoint, path and version]
    Supervisor last pass  failed   Last outcome provider failed · last pass 03:41
      Next: Open Agents for the pass; a readable failed report is not a green pass.
      [Endpoint, path and version]
    WorkLane stores  partial       11 readable · Unavailable: broken
      Next: Inspect the unavailable stores listed in the detail.

  Data sources                      compact healthy rows
    WorkForce roster  available
    WorkForce heartbeat  fresh     Last tick 12s ago
    Calendar          not configured

  Engine capabilities               live probes, not receipts
    WorkLane API     available     Reachable · usable
    Supervisor last pass  available  dispatched · last pass 03:41

  Installed engines                 receipts only as identity
    WorkLane   installed   0.1.7   Activated Sep 13 00:21
    WorkForce  installed   0.1.9   Activated Sep 13 08:29

  Excluded stores                   unregistered filenames, not counted
  Remote operations                 GitHub delivery evidence, not agent liveness
```

Healthy rows are compact (name + badge, one muted line, raw facts in a disclosure). Exception rows lead, carry one next step, and keep the same disclosure. On a 400px width the same fields stack; nothing is dropped. Keyboard uses native `details`/`summary`. Reduced motion (system or saved) turns the existing row transition off.

## Empty, stale, partial, unavailable

| State | When | Painted as |
|---|---|---|
| unavailable | no workspace, path outside the workspace, no receipt, no HTTP reply | error badge; never zero |
| reachable | HTTP reply, payload not usable | attention badge; HTTP status kept |
| partial | some registered stores unreadable | attention badge; readable records remain |
| stale | WorkForce heartbeat older than 120s | attention badge; not a process health check |
| unknown | heartbeat missing | unknown; never idle |
| empty | usable supervisor endpoint, no passes | empty, not available |
| not_configured | calendar file absent; supervisor 404 | not configured, not an exception |
| installed | receipt has a version | installed, not available/healthy |
| available / fresh | usable payload / heartbeat ≤ 120s | healthy compact row |

## Sources

| Fact | Source |
|---|---|
| Project stores, excluded filenames | WorkLane data directory under the selected workspace |
| Roster, heartbeat | WorkForce roster and daemon files in this workspace |
| Calendar | `.blueprint/calendar.json` |
| Installed versions | `local/worklane/deployment.json`, `local/workforce/deployment.json` |
| WorkLane API | `GET /api/admin/products` on the receipt's verified local origin |
| Supervisor last pass | `GET /api/supervisor` on the WorkForce receipt's verified local origin |
| GitHub | existing remote-activity projection |

Never probe another workspace, never default a port when the receipt is missing, never follow a redirect off the verified origin.

## Held

Starting or restarting engines; writing receipts, rosters or stores; a WorkLane `/health` route; host supervisor scope or stop-file editors (Settings already leaves those out).

## Acceptance for pc-1490

- 404 / non-products HTTP reply is reachable, not usable; HTTP status retained.
- Failed supervisor pass is failed outcome with usable evidence, not Available.
- Receipt times read Activated / installed, not Observed.
- Exceptions first, one next step, raw endpoint/path/version in a disclosure; healthy rows compact.
- Transport chip does not hide a failed source; stale/unavailable/partial/empty/unknown are distinct.
- No default-port or cross-workspace fallback.
- Disposable-fixture tests; both suites green. Installed-build/browser evidence is the integrator's close, not this seat's.
