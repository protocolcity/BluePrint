# Delivery and Timeline

Delivery presents allowlisted repository evidence: pull requests, checks,
merges and releases, grouped by repository and commit/PR identity. It reports
fetch time separately from event time. Failed/pending checks lead; identical
refreshes preserve expanded groups and reading position. A deployment matches a
revision only when a workspace receipt establishes that match.

Timeline joins source-labelled WorkLane history, WorkForce run events,
supervisor outcomes and GitHub delivery. Rows retain time, source, actor,
project and a link to the underlying evidence. Group only by structured identity
or revision keys; prose similarity and time proximity are insufficient.
Full comments and raw events remain reachable in disclosures.

`/activity` is a compatibility redirect to Delivery. Current sources and error
states are explained in Connections. Neither surface proves agent liveness from
GitHub activity or turns a readable failure report into a successful run.
Filters operate within the displayed loaded/time-window boundary.

Implementation: `overview/v1/server/remote_activity.py`, `timeline.py` and
`overview/v1/static/js/operations.js`. See
[the operations interface](OPERATIONS_EVOLUTION_2026_09.md).
