# States and terms

BluePrint projects the selected workspace's WorkLane and WorkForce evidence.
These facts remain separate; a claim is not proof that a process is running.
See [the product contract](../PRODUCT.md) and
[operations interface](OPERATIONS_EVOLUTION_2026_09.md).

## Work

| Axis | Source and meaning |
|---|---|
| Status | WorkLane lifecycle: backlog → Open, in_progress → Live, in_review → Parked, done → Done, canceled → Canceled |
| Gate | WorkLane gate fields: human, timer, deferred, tracking, or no gate; unresolved dependencies also prevent readiness |
| Assignment | Responsible registered worker from routing labels, or You, or Unassigned |
| Claim | Signed current owner, branch/workdir and start evidence; distinct from assignment |
| Kind | Work, note, todo, reminder or report from supported labels |
| For You | Derived attention, explained by a specific rule and time |

Readiness belongs to WorkLane and includes status, gates, dependencies and worker
eligibility. Ungated backlog is not sufficient. A parked implementation normally
awaits integration; it does not automatically require a human approval.

All open includes deferred and tracking work. Filters do not mutate stored status
or gates. Counts must identify unavailable stores and omitted records. Assignment,
status, gate, kind and attention filters remain independent and preserve context
through refresh and reader return. Legacy query aliases may resolve to current
filters without creating a second meaning.

## Attention

| Face | Rule |
|---|---|
| Decide | A current human decision or action with an explicit reason |
| Read | An open report requested for the person |
| Watch | Timer or qualifying lack of work updates; a reason to inspect evidence, not proof of a dead process |
| Due | The earliest valid reminder/deadline date is today or earlier on the workspace's local calendar day |

Deferred and tracking orders stay outside For You. An undated note/todo or future
date has a kind but no Due face. An agent-owned human gate stays assigned to its
agent. A parked handoff held by a registered seat does not become Watch solely
because it has been waiting for integration. Current update-age rules are in
`overview/v1/server/attention_view.py`; explain the rule rather than claiming
an agent is stalled.

Three clocks differ: a timer gate embargoes execution; a reminder/deadline label
adds a calendar date; a browser mute hides an item here temporarily. Mentioning a
date in prose does not create a deadline. Clearing a reminder must not clear a
gate. The retired attention query value `note` resolves to `due` for compatibility.

## Execution

| Term | Evidence |
|---|---|
| Seat | Registered worker allowed to claim scoped work |
| Job | Registered reporting/supervisory duty; not an implementation claim |
| Schedule | Configured trigger, separate from whether a run happened |
| Heartbeat | Daemon observation time; stale/missing stays explicit |
| Shift | Start, bounded in-flight state and terminal result from WorkForce |
| Last run | Recorded result and reason, separate from current execution |
| Provider capacity | Applicable qualification or provider evidence; installed CLI is insufficient |
| Installed build | Deployment/package receipt, verified separately from live response |

Project Running counts include verified seat execution, not jobs or GitHub events.
An old open shift is stale evidence; it does not authorize killing a process or
stealing a claim. Host-specific supervisor/integration jobs are configuration,
not automatically installed product capabilities.

## Labels and compatibility

`worker:` routes work; `you:todo`, `you:note` and legacy `you:remind` describe
personal kind; `reminder:YYYY-MM-DD` and `deadline:YYYY-MM-DD` carry dates;
`inbox-report` identifies reports; `parent:`/`slice-of:` links hierarchy.
`execution:bounded` is an eligibility convention where a runner requires it.
Other project tags do not grant authority. Historical cloud/retired-worker labels
are not installed adapters or active seats. Compatibility decision labels remain
readable but new records should use explicit current gate fields and reasons.

Status, gate, declared blockers, signed ownership and engine readiness must not
be replaced by arbitrary labels. Unassigned deferred work is intentionally
parked; it needs routing when it becomes actionable, not merely to fill a queue.
