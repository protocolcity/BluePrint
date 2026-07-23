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
| **Neighborhood** | One project — a repo or directory where work happens. Independent, but protocol-compliant (§4). **Surface speech (BluePrint suite, 2026-07-22):** prefer **project** for the L1 unit and **workspace** for the founded root; keep Neighborhood in this Charter as the host-neutral civic term. |
| **The work-order desk** | The ticket store. All work moves by ticket — filed, claimed, signed. Never by chat or memory. |
| **The workforce** | Your agents — any vendor. Each has a registered identity, a job description, and signs everything it does. |
| **Citizens** | The humans. Bots execute; humans govern — citizens hold the taste, the gates, and the final word. |
| **Laws** | The rules, always written as readable files, one owner per rule. If it isn't in an `.md`, it isn't law. |

**Reserved words — one word, one meaning, city-wide.** Vocabulary debt
compounds: a word that means two things in the docs eventually means two
things in the code, and that rename costs a migration. So the Charter
reserves its nouns:

| Word | Means exactly this | Where it lives |
|---|---|---|
| **law** | any binding rule file | `AGENTS.md` (L0/L1) |
| **charter** | this spec | `CHARTER.md` |
| **contract** | one worker's law | `CONTRACT.md` (L2) |
| **prompt** | one worker's shift brief | `prompt.md` (L3) |
| **protocol** | the desk's own rulebook — nothing else | the store's protocol doc |
| **blueprint** | the whole shipped kit (charter + manifesto + guides + forms + example) — never a single file | this repo |
| **worker** | an employed agent: a registered identity with a contract and a schedule | `CONTRACT.md` + the store's identity registry |
| **roster** | the registry of employed workers — who exists, their kind, their schedule | the store's identity registry |
| **ticket** | one unit of filed work; work moves only by ticket | the store |
| **dashboard** | a rendered read-only view of city state (work, workers, projects) | — (rendered from the store + roster; not a file) |

When you add a concept, give it a fresh word; never overload a reserved one.

**The legibility test — a filename says what the file is.** A stranger
navigating the tree cold can tell what a file is from its name alone. This binds
every file the protocol tells you to create and everything a founding tool
generates. Prefer plain industry words (`CONTRACT.md`, `ARCHITECTURE.md`,
`roster.json`) over evocative ones; the civic metaphor (city, neighborhood,
desk) is brand voice, never a filename.

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
| **L2** | Employment contract | one `CONTRACT.md` per worker | that worker, every dispatch |
| **L3** | Shift instructions | one `prompt.md` per worker | that worker, this dispatch |

**The vendor-pointer rule:** the canonical law file is always `AGENTS.md`.
Vendor-specific files (`CLAUDE.md`, `GROK.md`, …) are **optional** — add them
only when a vendor CLI needs its own filename. When present, they must be
thin pointers, never content — e.g. `CLAUDE.md` containing only `@AGENTS.md`,
`GROK.md` as a symlink. One law, every vendor reads it. Founding tools do
not plant vendor pointers by default.

**The perimeter registry:** cross-neighborhood grants live at city-root
`PERIMETER.md` (L0 only). Cabinets (L1) use the implicit home default;
contracts (L2) and prompts (L3) may promise scope but do not own the
registry. See WIDTH LAW prose in `docs/specs/CITY_EDGES.md`.

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
2. **Its work is ticketed.** Its work is filed at the desk; work moves by ticket
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
6. **Every path resolves.** Any path, link, or cross-reference in law,
   documentation, or a founding template must name a file that exists. A
   broken link in law is a compliance gap, not a documentation gap.

## 8. Founding a city — the new-citizen path

1. **Pick your city root** — the folder or org your projects live under.
2. **Write L0** — city law at the root: registry, scoping rule, boundaries.
3. **Charter each neighborhood** — an L1 `AGENTS.md` per project (start with
   one). Optionally add vendor pointers if a CLI needs its own filename.
4. **Stand up the desk** — install a store (e.g. WorkLane), create one
   ticket store per neighborhood, file your first real tickets.
5. **Employ your first worker** — one vendor CLI, one registered identity,
   one L2 contract, one L3 prompt, on whatever scheduler you have (or run it
   by hand). One worker, one lane, small slices.
6. **Grow by evidence** — add workers when the queue demands it, laws when a
   mistake teaches you one, neighborhoods when a project earns one. The city
   is legible at every size.

---

## 9. The authority tiers

*(Full doctrine: [The Covenant](COVENANT.md) — ratified 2026-07-16)*

Three tiers govern every session in a founded city:

| Tier | Authority | Signs as | Tray relationship |
|---|---|---|---|
| **Citizen** | The human — ultimate authority; source of all gates and final calls | Themselves | Owns the tray |
| **Hand** | A surface the citizen acts through; carries the citizen's full authority for the session | The citizen (shared identity) | Never files into the tray — a hand IS the citizen the tray waits for |
| **Worker** | An employed agent: own registered identity, own L2 contract, own schedule | Its registered identity (not the citizen's) | Files into the tray at its authority ceiling; never self-authorizes above it |

**The test:** whose authority does the session run under — not what model is
running in it.

See [The Covenant](COVENANT.md) for the full doctrine, the hand shutdown
protocol, and team extension mechanics.

## 10. The five-event grammar

*(Ratified 2026-07-16)*

Exactly five events define the state space of a working city. All motion in
a city's surfaces derives from one of them; no motion is invented outside
this grammar.

| Event | Meaning |
|---|---|
| **Filed** | A ticket entered the desk |
| **Claimed** | A worker took ownership of a ticket |
| **Signed** | A worker closed out a ticket — work verified, desk comment posted |
| **Worker arrives** | A scheduled worker started a shift |
| **Worker leaves** | A scheduled worker's shift ended |

**Two-motions law:** every rendered motion wears exactly one of two signals —
a receipt (it happened) or a clock (it is happening now). No motion without
a signal; no signal without a motion.

Future richer renderings of these events require no protocol-layer change.
Adding a new event requires a founding-level amendment to this section.

## 11. The truth layer

*(Ratified 2026-07-16)*

Every city has two layers — truth and skin — and only the truth layer is
invariant.

**Truth words** speak the filesystem and the protocol. They are the
identifiers that code, APIs, and specifications use:

| Truth word | What it names |
|---|---|
| Root folder | The city root — wherever city law lives |
| Managed folder | A folder with a governing `AGENTS.md` |
| Unmanaged folder | A folder without a governing `AGENTS.md` |
| Ticket | One unit of work at the desk |
| Worker | An employed agent: registered, contracted, scheduled |
| You | The signed-in citizen — viewer-relative |
| The five events | Filed, claimed, signed, worker arrives, worker leaves |

**Skin words** are the rendered labels a city's surfaces show to citizens.
Any analogy — a city, a studio, a lab — may replace the default skin by
providing a truth-to-skin mapping. The protocol layer does not change with
the skin.

**Registry keys speak truth.** A skin rename is a skin-layer change and
never requires a data migration.

## 12. Output-landing convention

*(Ratified 2026-07-16; promoted from L1 to L0)*

Work output in any neighborhood lands in exactly one of three buckets:

| Bucket | Contents | Storage |
|---|---|---|
| **Runtime evidence** | Logs, run artifacts, generated HTML, ephemeral build output | Gitignored; never versioned. Canonical directory name: `local/` (neighborhoods may use a project-specific name). |
| **Work products** | Research, audits, doc patches, ADRs — anything a citizen reviews in git history | Versioned under `docs/` |
| **Claims about work** | Close-out statements, verification notes, follow-up filings | On the desk (store close-out comment); never a committed file |

No bucket is optional. A worker that commits a close-out statement to a
versioned file, or versions ephemeral logs, is non-compliant with this law.

## 13. Suite architecture — pages and engines

*(Ratified 2026-07-16)*

From the citizen's seat, a founded city has one installed entry point — the
blueprint suite — and every product in the city manifests as a page within
it. Adding a product means adding a page link to the suite, not creating a
new entry point.

From the code's seat, products remain separate ships: engine packages the
suite depends on, never vendored or absorbed. This boundary carries
standalone engine use, independent export seams, and separate licensing.

**The law in two sentences: pages belong to the suite. Engines belong to
products.**
