# papers-sync — Employment Contract (L2)

Weekly workspace job that keeps neighborhood `AGENTS.md` generated blocks
in sync with the live roster and desk scene (renamed from papers-patrol).
Doctor-class: runs
`blueprint doctor --fix-papers <workspace>` and exits. No LLM, no tickets,
no KeepAlive.

## Identity

| Field | Value |
|---|---|
| Board label | **papers-sync** |
| Prior name | `papers-patrol` (alias — do not dual-hire) |
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
`.protocolcity/logs/papers-sync.out` by the LaunchAgent when installed.

## Never touch

- Tickets, roster, ledger, locks, daemon state — no TP or WorkForce writes.
- Code, contracts, prompts, or any file outside the generated AGENTS blocks.
- Host LaunchAgents folder — install is a citizen/host-ops gate.
- Do not start/restart any service or run host service load commands yourself.
- Do not create a standing ticket or claim work orders.

## Citizen gate (install)

This seat is **optional** — not part of the default seed-ops trio. Hire and
install are citizen-present actions.

### Public path (pip / brew BluePrint)

1. Copy the shipped plist template from the package:
   - `templates/host-agents/com.protocolcity.papers-sync.plist`
     (or `python -c "import protocolcity, pathlib; print(pathlib.Path(protocolcity.__file__).parent / 'templates' / 'host-agents')"`)
2. Replace every `/REPLACE/WITH/WORKSPACE` with your workspace root.
3. Point `ProgramArguments` at your `blueprint` binary if it is not
   `/usr/local/bin/blueprint` (Homebrew often uses `/opt/homebrew/bin/blueprint`).
4. Install the agent with your host's preferred mechanism (macOS example):
   copy into `~/Library/LaunchAgents/` and load it.
5. Add to WorkForce roster (`kind=job`, `schedule="0 9 * * 1"`, name
   `papers-sync`).

### Roster only (no host agent)

```text
blueprint hire papers-sync \
  --workdir <workspace>/.protocolcity/ops \
  --kind job \
  --role 'weekly AGENTS generated-block refresh' \
  --schedule '0 9 * * 1'
```

Without a host LaunchAgent, WorkForce fires the job when the suite engines
are up; the plist path is for always-on weekly refresh while the laptop is on.

## Failure posture

`blueprint doctor --fix-papers` exits non-zero if the workspace root is
missing or if a write fails. The LaunchAgent records the exit code in the log.
No retry loop — next Monday's fire is the recovery path. Do not page or
open tickets on failure.
