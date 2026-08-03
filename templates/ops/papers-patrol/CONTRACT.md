# papers-patrol — Employment Contract (L2)

Weekly workspace job that keeps neighborhood `AGENTS.md` generated blocks
in sync with the live roster and desk scene. Doctor-class: runs
`blueprint doctor --fix-papers <workspace>` and exits. No LLM, no tickets,
no KeepAlive.

## Identity

| Field | Value |
|---|---|
| Board label | **papers-patrol** |
| Kind | `job` |
| Assignment | City-wide workspace job; fires weekly |
| Vendor | n/a — CLI only, no model pin |
| Schedule | `0 9 * * 1` (Monday 09:00 local) |
| Signs as | n/a — no TP writes |

## What this job does

Exactly one action per fire:

```
blueprint doctor --fix-papers <workspace>
```

`fix_papers()` rewrites only the `<!-- bp:generated:... -->` marker
blocks inside each neighborhood `AGENTS.md`. It is idempotent: a second run
with no roster/scene change is always a no-op. Output (stdout) is appended to
`.protocolcity/logs/papers-patrol.out` by the LaunchAgent.

## Never touch

- Tickets, roster, ledger, locks, daemon state — no TP or WorkForce writes.
- Code, contracts, prompts, or any file outside the generated AGENTS blocks.
- `~/Library/LaunchAgents/` — install is a citizen/host-ops gate.
- Do not start/restart any service or run `launchctl`.
- Do not create a standing ticket or claim work orders.

## Citizen gate (install)

Hire and install are citizen-present actions:

1. Create `~/Library/LaunchAgents/com.protocolcity.papers-patrol.plist` — a
   LaunchAgent that runs `blueprint doctor --fix-papers` on the weekly
   schedule, with your workspace root as the working directory.
2. Add to WorkForce roster (`kind=job`, `schedule="0 9 * * 1"`).
3. `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.protocolcity.papers-patrol.plist`

## Failure posture

`blueprint doctor --fix-papers` exits non-zero if the workspace root is
missing or if a write fails. The LaunchAgent records the exit code in the log.
No retry loop — next Monday's fire is the recovery path. Do not page or
open tickets on failure.
