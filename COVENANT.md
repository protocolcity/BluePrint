# The Covenant

**Status:** RATIFIED 2026-07-16.

The Covenant is the Protocol City human-agent operating contract. It names
the three authority tiers of a founded workspace and the rules that govern
how authority moves between them. It is the practical answer to the
question every multi-agent session raises: when a decision needs a human,
which human — and by what authority?

---

## The three tiers

| Tier | Who they are | Signs as | Relationship to For You |
|---|---|---|---|
| **You** | The human of the workspace — the source of all authority, all gates, and all final calls. | Themselves (commit author, gate approver) | Owns For You; For You waits for You |
| **Session (hand)** | Any surface You act through: a terminal session, a desktop client, a browser tab. The session carries your full authority for its duration. | You (session and human share one signing identity) | Never files into For You — a session IS You |
| **Agent** | An employed identity with a registered id, an L2 CONTRACT, and a schedule. When an agent reaches its authority ceiling, it stops and files into For You rather than proceeding. | Its registered identity (never Yours) | Files into For You when authority runs out; never self-authorizes above its ceiling |

---

## The test

> **Whose authority does the session run under — not what model is running in it.**

A terminal running Grok, a Claude Desktop session, a bare `wl` command:
these are sessions when You are acting through them — live instruments,
carrying your authority. The same AI model running under a CONTRACT as a
scheduled agent is an agent. The model is incidental; the authority
structure is the distinction.

---

## The session shutdown protocol

Sessions carry your authority and never file into For You — so when a
session closes mid-work, its half-pending state is invisible to every agent
in the workspace. The shutdown norm:

1. **Commit or note before closing.** If edits are in flight, commit them.
   If a commit is not yet appropriate, drop a one-line pointer comment on
   the nearest open work order. A pointer comment ("edits in flight — [list
   files or work order]") is sufficient; it does not need to describe every
   change.
2. **Nothing staged, nothing lost.** A staged but uncommitted change is
   invisible after the session closes. The standard: leave nothing staged
   without a commit or a pointer.

**The safety net** is the interrupted-session sweep: a workspace job that
detects dirty trees, stale in-progress work orders, and orphaned staged
files, then files a pointer work order automatically. The sweep never
auto-commits, because session commits carry your authority.

**Grounding precedent (2026-07-16):** a session closed after building the
attention board, leaving uncommitted edits across three repositories. Only
a manual sweep found the state. The norm stated here is the lesson from
that incident.

---

## Team extension — more than one You

In a solo workspace, "You" in every surface refers to the single human.
When more than one human joins:

- **You remains viewer-relative.** Each human sees themselves as You.
- **Each human owns a For You pile.** Gates route to the right person by
  role.
- **Roles govern gate classes.** The workspace hat register assigns who may
  approve which gate class.
- **Agents are shared infrastructure.** Agents claim from a shared queue;
  For You routes to the human whose role owns the gate.

The multi-human onboarding mechanics are specified in
`docs/research/multi-citizen-design-2026-07.md`. The Covenant defines the
authority model; the design doc defines the join and role mechanics.

---

## Evidence from the founding session (2026-07-16)

Two incidents on the founding day grounded the Covenant in observable cost:

1. **Two sessions, one identity.** Two sessions from different clients
   committed to the same checkout within the same hour, indistinguishable in
   git history because both carried the human's author identity. This
   motivated the per-session fingerprint design.
2. **Parallel feature collision.** Two sessions independently built the same
   feature within the hour. Sessions do not coordinate through work orders
   the way agents must; the queue was the single source of truth that
   contained the collision without data loss.

Both incidents are containable costs when the authority tier of every
session is legible.

---

## Cross-references

- **[docs/CHARTER.md §9](CHARTER.md)** — Charter form of the authority tiers
  (normative; points here for full text)
