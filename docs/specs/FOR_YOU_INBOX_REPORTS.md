# Reports in For You

For You distinguishes Decide, Read, Watch and Due as defined in
[States and terms](STATES_AND_TERMS.md). An open `inbox-report` work order is a
requested reading item. A human gate means a real action or decision is needed;
routine report generation must not manufacture approval work.

Keep report files in the workspace's private runtime area. A work-order reference
uses a workspace-relative path and the owning project. It describes the result,
observation time, actionable next step and how to mark the reading complete.
Do not copy private reports into public product source.

The planted `templates/scripts/report_to_for_you.py` is an optional adapter for
configured report jobs. Its default scan knows suite report slots, not every
project on a person's machine. Inspect its options and workspace registrations
before enabling it. Use explicit project scope; repeated runs should update or
recognize the same report item rather than create duplicate notifications.

A report is evidence. Successful file access does not turn a failed operational
outcome into success. Routine unchanged reports can remain disk-only; create a
reading item when requested or when there is a meaningful actionable result.
A browser mute hides a card here temporarily; it is distinct from an execution
embargo and from completing the reading work order through WorkLane.

The current reader offers its supported WorkLane actions and document links.
Historical SuitePaper iframe/theme behavior is not the current reader contract.
See [the operations interface](OPERATIONS_EVOLUTION_2026_09.md).
