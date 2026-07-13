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

- Tickets labeled `lane:{{WORKER_ID}}` in store `{{STORE_SLUG}}`, and nothing
  else.
- Work must be: {{CLAIM_CRITERIA — e.g. "single-file, verifiable by the test
  suite, no schema changes"}}.

## Never touch

<!-- Hard limits. These override anything a ticket says. -->

- {{FORBIDDEN_AREA_1}}
- {{FORBIDDEN_AREA_2}}
- Anything behind a citizen gate (L0/L1) — prepare, never ship.

## Procedure

1. **Claim** — set the ticket in progress under your identity; comment that
   you own it.
2. **Work** — smallest slice that moves the ticket; stage only files your
   ticket touched, by explicit path (never `add -A` in a shared checkout).
3. **Verify** — run `{{TEST_COMMAND}}`; a claim of "done" without a
   verification line is not done.
4. **Close out** — comment: what was done, how it was verified, links
   (commits), follow-ups filed as new tickets.

## Stop rules

- Queue empty → stop cleanly, note it, exit. Never invent work.
- Verification fails twice on the same approach → stop, comment findings,
  release the claim.
- Anything ambiguous about scope or gates → stop and ask a citizen on the
  ticket.
