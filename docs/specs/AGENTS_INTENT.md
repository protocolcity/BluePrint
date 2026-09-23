# Agents

Status: current intent. [Agent configuration](AGENT_ADOPTION.md) defines scope
and qualification; [states and terms](STATES_AND_TERMS.md) defines evidence.

Agents explains which executors are configured, what they last did, what is
observed now, and why work stopped. Keep implementation seats, scheduled jobs
and supervision evidence distinguishable; none implies the others are installed.

A seat claims work under its identity. A job performs the duty defined by its
contract. A supervisor pass is an observed coordination action, not another
running implementation worker. Display configuration beside evidence instead of
inferring liveness from a roster row or a repository event.

Show observation time and source for heartbeat, run start/stop, lock, budget,
last outcome and refusal. A stale heartbeat is unknown health. Missing sources
remain unavailable. Expose supported WorkForce actions with explicit scope and
useful refusal messages; assignment alone does not dispatch.

A provider is not a worker, a model is not an account budget, and an execution
host is not a model provider. Qualify these separately. Current dispatch is
local; remote execution needs a real adapter and its own authority/evidence.

Validate empty/held/unavailable/stale/failed states, safe dispatch refusal,
keyboard access, narrow layouts and preservation of the current project/reader.
Do not hardcode a private installation's worker names or job schedules.
