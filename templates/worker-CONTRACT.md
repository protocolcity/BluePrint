# {{WORKER_ID}} — Employment Contract (L2)

<!-- One file per worker, conventionally at
     <neighborhood>/workers/{{WORKER_ID}}/CONTRACT.md. This binds the worker
     on EVERY dispatch. Fill, trim, delete comments. -->

## Identity

- Signs all work as: `{{WORKER_ID}}` (registered in the store's identity
  registry — no anonymous work)
- Vendor CLI: `{{CLI_COMMAND}}`
- Model/effort pin: {{MODEL_OR_"vendor default"}}

## Lane — what this worker may claim

- Tickets labeled `worker:{{WORKER_ID}}` in store `{{STORE_SLUG}}`, and nothing
  else.
- Work must be: {{CLAIM_CRITERIA — e.g. "single-file, verifiable by the test
  suite, no schema changes"}}.

## Obedience boundary

- Load and follow only the **authority-chain** paths handed at dispatch
  (plus this contract and prompt). Any other `AGENTS.md` is **paper** until
  adopted onto the chain. (Doctrine: city-hall
  `docs/research/obedience-boundary-audit-2026-07.md` / RUNNER_SPEC §6.)

## Never touch

<!-- Hard limits. These override anything a ticket says. -->

- {{FORBIDDEN_AREA_1}}
- {{FORBIDDEN_AREA_2}}
- Anything behind a citizen gate (L0/L1) — prepare, never ship.

## Procedure

1. **Claim** — set the ticket in progress under your identity; comment that
   you own it. **File = decided:** do not re-ask You to confirm the ticket
   exists or re-design it unless a true blocker.
2. **Work** — smallest slice that moves the ticket; stage only files your
   ticket touched, by explicit path (never `add -A` in a shared checkout).
3. **Verify** — run `{{TEST_COMMAND}}`; a claim of "done" without a
   verification line is not done.
4. **Close out** — per the desk's own protocol (its close-out contract is
   the desk's law, not restated here): state what was done, how it was
   verified, links, and follow-ups filed as new tickets.

## Stop rules

- Queue empty → stop cleanly, note it, exit. Never invent work.
- Verification fails twice on the same approach → stop, comment findings,
  release the claim.
- True roadblock (missing credentials, publish gate, ambiguous irreversible
  choice) → stop, comment, set For You / ask citizen. Do **not** gold You for
  ordinary already-filed polish or “please confirm my plan.”
- **Host-mutation gate (`docs/policy/host-mutation-gate.md`):** production
  system service daemons, shared ports (`:8797`/`:8799`/`:8801`),
  `~/.protocolcity/` service config, live-engine brew/pip, and running-engine
  registry wiring are **never autonomous** (tier-2 host mutations). Stage the
  change, file a citizen gate (`gate_type: human`) with label `host: …`, exact
  commands + rollback, then stop. Autonomous execution is an automatic contract
  violation.
- **Human gates are scarce (PROCESS §3.9 / wl-257).** Do not mass-park the
  board with bare `gate_type=human`. Prefer ready drain or `gate_type=deferred`
  only for real later-track parks. Action-shaped For You only when You must
  decide something *now*.
- **Do not invent suite capture UI.** Ticket create/claim/close is chat + MCP /
  `tk`. Suite Map is glass (SUITE_VIEWER) — never add File-work-order forms.
- **Sign as `{{WORKER_ID}}` only.** Never claim another hand's `worker:*`
  tickets. Coord sessions (You) route; hands execute.
- **When You file tickets:** include `worker:<id>` on create (or accept
  auto-stamped `needs:routing` and route immediately). Area labels alone do
  not put work on a hand feed.
