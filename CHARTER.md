# The Protocol City Charter

**Status:** v0.1 — draft for review

Protocol City is a specification for organizing a workspace — any workspace —
so that humans and AI agents from any vendor can build together, in parallel,
accountably. It is paper, not software: it tells you **which files and folders
to create, what they must say, and the rules that make them work together.**
You can adopt it with nothing but a text editor; the products that automate
parts of it are optional and replaceable.

Who it's for: anyone with one or more projects who wants multiple agents —
Claude, Cursor, Codex, Grok, whatever comes next — doing real tasks and builds
without chaos: no lost work, no two agents trampling each other, no "which bot
did this?", no rules that live in one vendor's config format.

---

## 1. Definitions

| Term | Meaning |
|---|---|
| **The city** | Your whole operation: every project, agent, human, and rule under one set of laws. Its root is wherever you keep your projects — a folder, a monorepo, a GitHub org. |
| **City hall** | The place city-wide law and records live: the root of the city. |
| **Neighborhood** | One project — a repo or directory where work happens. Independent, but protocol-compliant (§4). |
| **The work-order desk** | The ticket store. All work moves by ticket — filed, claimed, signed. Never by chat or memory. |
| **The workforce** | Your agents — any vendor. Each has a registered identity, a job description, and signs everything it does. |
| **Citizens** | The humans. Bots execute; humans govern — citizens hold the taste, the gates, and the final word. |
| **Laws** | The rules, always written as readable files, one owner per rule. If it isn't in an `.md`, it isn't law. |

## 2. The three layers

Every piece of a working city belongs to exactly one layer:

| Layer | Owns | Reference implementation |
|---|---|---|
| **Store** | The work — tickets, claims, signed authors, audit trail | [WorkLane](https://github.com/protocolcity/ProtocolCity-WorkLane) |
| **Orchestrator** | The workers — identities, schedules, dispatch, budgets | *(spec forthcoming; today: your scheduler + §6)* |
| **Workplace** | The code the workers act on | your repos |

The layers are substitutable — the Charter cares that each exists and keeps
its rules, not whose software fills it.

## 3. The levels of law

Law is written at four levels. Lower levels may tighten higher ones, never
loosen them.

| Level | Law | Lives at | Binds |
|---|---|---|---|
| **L0** | City law | `AGENTS.md` at the city root | every neighborhood and worker |
| **L1** | Neighborhood law | `AGENTS.md` at each neighborhood root | everyone working in that neighborhood |
| **L2** | Employment contract | one `PROTOCOL.md` per worker | that worker, every dispatch |
| **L3** | Shift instructions | one `prompt.md` per worker | that worker, this dispatch |

**The vendor-pointer rule:** the canonical law file is always `AGENTS.md`.
Vendor-specific files are pointers, never content — e.g. `CLAUDE.md`
containing only `@AGENTS.md`, `GROK.md` as a symlink. One law, every vendor
reads it.

**The city of one:** a single-project city merges L0 and L1 — one
`AGENTS.md` serves as both city and neighborhood law until a second
neighborhood exists. Split them the day the registry gains its second row;
most cities start here.

**Minimum contents:**

- **L0 (city law):** the neighborhood registry (what exists, where, its ticket
  prefix); cross-neighborhood rules (always scope tickets explicitly — "one
  ticket per neighborhood" when work spans two); boundaries (which
  neighborhoods may not touch each other, and how they're allowed to talk —
  e.g. HTTP client only, never imports); what's citizen-gated city-wide.
- **L1 (neighborhood law):** what this place is; how to run/test it; its
  ticket store; local boundaries and no-go zones; which workers serve it;
  what's citizen-gated here.
- **L2 (employment contract):** the worker's identity; what work it may claim
  (its lane) and what it must never touch; its working procedure (claim →
  work → verify → close out); its stop rules.
- **L3 (shift instructions):** the short dispatch brief — read your contract,
  check the queue, do one slice, sign your work.

## 4. The compliance test

A project is a neighborhood — protocol-compliant — when three things are true:

1. **Its law is written.** An `AGENTS.md` at its root says what it is and how
   to work in it.
2. **Its work is ticketed.** It has a store at the desk; work moves by ticket
   with explicit scope.
3. **Its workers sign.** Every agent action — ticket, comment, commit —
   carries a registered identity.

That's the whole test. A dormant repo with written law is compliant; a busy
repo coordinated over chat is not.

## 5. The desk

One store per neighborhood, each with a short prefix (`app-1`, `web-42`).
The store's own protocol is law for ticket lifecycle — statuses, claims,
close-out contracts, comment cadence — and this Charter defers to it rather
than duplicating it (reference: WorkLane's PROTOCOL). What the Charter itself
requires: signed authorship on every ticket and comment, explicit
neighborhood scope on every ticket, and a close-out that states what was done
and how it was verified.

## 6. The workforce

- **Identity:** every worker is registered by name in the store's identity
  registry before it works. No anonymous work.
- **Contract:** every worker has an L2 contract. A worker without a contract
  doesn't dispatch.
- **Lanes vs jobs:** a **lane** claims tickets under its identity; a **job**
  (reports, audits) observes and never claims. Don't let a job mutate work.
- **Vendor neutrality:** a worker is a vendor CLI plus a contract plus an
  identity. Swapping the vendor doesn't change the law it obeys.
- **Citizen gates:** publishing, releases, money, permissions, and anything
  irreversible are citizen decisions. Workers prepare; citizens ship.

## 7. Founding principles

1. **Bots execute, humans govern.**
2. **Every action is signed.**
3. **Documentation is the interface.** New agent, new vendor, new person:
   read the law, start working.
4. **The protocol is open; the services are premium.**
5. **Every folder has a purpose.**

## 8. Founding a city — the new-citizen path

1. **Pick your city root** — the folder or org your projects live under.
2. **Write L0** — city law at the root: registry, scoping rule, boundaries.
3. **Charter each neighborhood** — an L1 `AGENTS.md` per project (start with
   one). Add vendor pointers.
4. **Stand up the desk** — install a store (e.g. WorkLane), create one
   ticket store per neighborhood, file your first real tickets.
5. **Employ your first worker** — one vendor CLI, one registered identity,
   one L2 contract, one L3 prompt, on whatever scheduler you have (or run it
   by hand). One worker, one lane, small slices.
6. **Grow by evidence** — add workers when the queue demands it, laws when a
   mistake teaches you one, neighborhoods when a project earns one. The city
   is legible at every size.
