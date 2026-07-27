# Running your city

[FOUNDING.md](FOUNDING.md) is day one. This is every day after: what a
citizen actually operates once the city exists — and, just as important,
what you never have to touch because it runs itself.

## The frame: dumb loops, smart work-order ledger

Most agent systems build clever long-running loops that hold goals in
memory — and lose everything when the loop dies. A city inverts that:
**shifts are stateless, the work-order ledger is the memory.** Every dispatch
wakes up, asks WorkLane "what's ready for me?", does one slice, writes
everything back — claims, comments, close-outs, follow-ups — and exits.
Work keeps going not because anything runs forever, but because the
**ledger** persists between shifts. In the BluePrint suite you **see** that
ledger on the **Map** (open counts, tape, paper drawer) — not a separate Desk
app.

The corollary is the economics: an empty queue costs nothing (shifts skip
cleanly), and a queue that stops shrinking stops being worked (no-progress
stops prevent burn loops). A well-run city is **always ready, not always
burning.**

## The loops

Four dispatch models, in the order you'll meet them:

| Loop | What fires the shift | Where it lives |
|---|---|---|
| **Time-based** | A schedule — cron, your OS's scheduler, any clock | The workhorse. Start here: one worker, one cadence |
| **Turn-based** | The shift itself — take another pass while budget remains and the queue shrinks | Inside a shift (multi-pass with a no-progress stop) |
| **Goal-based** | The **ledger**, not the loop: a big goal decomposes into an epic → slices → follow-ups; each shift picks the next slice | In your tickets. No loop holds the goal in memory — crash-proof by construction |
| **Proactive** | An event — a ticket entering a lane triggers a dispatch instead of waiting for the clock | **Dispatch** territory (powered by WorkForce when installed); until then, clocks are plenty |

A citizen dispatching a worker by hand is also a loop — the slowest and
most legitimate one. Every city starts there.

## What you operate — five duties

Everything else in the city runs itself. You do these:

1. **The intake habit.** When you have an idea, a gripe, or a taste
   reaction, it becomes a ticket *in that moment* — not a note, not a
   memory, not a chat. This is the highest-leverage habit in the city:
   lanes can only drain what the desk holds, so the flywheel starts at
   your intake.
2. **The gate sweep.** Your inbox is two queues: tickets waiting on a
   citizen decision, and finished work in review. Sweep them when you sit
   down. Everything the workforce prepares stalls politely at your gates —
   by design, so the sweep *is* the steering wheel.
3. **The roster.** Employ, pause, and pin: which workers run, on what
   models, at what budgets. A monthly touch, not a daily one. Add a worker
   when a queue stays deep; pause one when its lane runs dry.
4. **The patrols.** Reports are instruments you read, not write: a weekly
   backlog snapshot (what's piling up), a periodic doc audit (is the law
   drifting from reality), and whatever board shows your rota's health.
   File tickets off what they show you — that's the patrol loop closing
   back into intake.
5. **The taste sessions.** Work whose deliverable is judgment — product
   decisions, design passes, anything gated — stays human, in live
   sessions. End each one by writing its state onto a ticket, so the next
   session opens where the last stopped. The mechanical backlog belongs to
   the workforce; the taste belongs to you.

## The flywheel

**You file → clocks fire → workers drain the queue and file follow-ups
(work generates work) → patrols surface the state → you sweep the gates
and re-prioritize → repeat.**

Two failure modes it survives by design: when the queues empty, the city
idles for pennies (skips are cheap); when *you* step away, nothing breaks —
prepared work stalls at your gates, shifts log clean skips, and the whole
operation waits, legible, for the next sweep.

## When a worker hits a wall — the vendor-limit playbook

Sooner or later a vendor meter runs dry mid-employment: a balance
exhausts (402), a rate window closes (429), a subscription lapses. The
machinery is built for this — the runner records a truthful failed shift
and keeps firing cheap, claims stay safe, nothing corrupts. The *account*
is yours to fix, so the playbook is a citizen duty:

1. **Read the vendor's actual words.** The worker's ledger/log holds the
   real error; the board only knows "err". Diagnose from the log, never
   from the lamp.
2. **File the decision the moment you see it**, labeled for your own
   attention — it lands in your brief and the
   incident can't get lost between sessions.
3. **Pick one of three**, in rising order of effort: **top up / wait**
   (the worker self-heals on its next fire — zero changes); **bench**
   (flip the roster schedule to an informational string so the clock
   stops firing it; relabel or hold its queue); **re-staff** (point the
   role's runtime at another installed vendor — roles are named by
   function, so the identity and its history survive the swap).
4. **Verify with one clean shift, then close with evidence.** A manual
   dispatch from the Workers dashboard beats waiting for the cron; the
   close-out cites the clean ledger line.

Prevention is staffing, not vigilance: spread roles across the vendors
you have, so one dry meter idles a lane, never the city.

## Growing pains, in order

- **Queue stays deep for weeks** → add a worker to that lane, or split the
  neighborhood's ledger.
- **Two workers touch the same files** → tighten lanes in their contracts;
  add a workspace guard to the runner.
- **You can't remember what's running** → you need the board (rota, health,
  last signed activity) — City Hall / Dispatch chrome when you have it.
  Until then, a shell script over your scheduler and ledgers is lawful.
- **The law stops matching reality** → schedule the doc-audit patrol; one
  owner per rule, demote copies to pointers.
- **A second machine or a teammate arrives** → you've outgrown this
  document; that's **Dispatch** territory (multi-machine / scheduled
  workforce), and the city's files move with you either way.
