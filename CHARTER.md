# The Protocol City Charter

**Status:** v0.1 — draft for review

Protocol City is a specification for organizing a **workspace** — any
workspace — so that humans and AI agents from any vendor can build together,
in parallel, accountably. It is paper, not software: it tells you **which
files and folders to create, what they must say, and the rules that make
them work together.** You can adopt it with nothing but a text editor; the
products that automate parts of it are optional and replaceable.

Who it's for: anyone with one or more **projects** who wants multiple agents
— Claude, Cursor, Codex, Grok, whatever comes next — doing real tasks and
builds without chaos: no lost work, no two agents trampling each other, no
"which bot did this?", no rules that live in one vendor's config format.

**Operating vocabulary (the story):**
**You → Workspace → Project → Agent · Job.** Work is filed as **work orders**.
Cross-project grants live in **Boundaries**. Binding markdown is
**instructions**. Protocol City is the product name; it is not a word you
must learn to run the system.

---

## 1. Definitions

| Term | Meaning |
|---|---|
| **Workspace** | The founded root — the folder that holds your projects, agents, and instructions. |
| **Project** | One independent folder (a repo, a product, a package) with its own lifecycle: it can ship, verify, and fail on its own. |
| **Work order** | One unit of filed work. Work moves by work order — filed, claimed, signed. Never by chat or memory. |
| **Agent** | A hired identity that claims work orders. Registered, contracted, scheduled. |
| **Job** | A scheduled duty that runs on a clock and does not claim work orders. |
| **You** | The human. Taste, gates, and the final word. |
| **Instructions** | Binding rules, always written as readable files, one owner per file. If it isn't in an `.md`, it isn't instructions. |
| **Boundaries** | The workspace-root table of cross-project grants. Empty is valid: every project is sovereign at home. |

**Historical / brand only (not operating nouns):** *city*, *neighborhood*,
*cabinet*, *citizen*, *ticket*, *desk* as a required room name. They may
appear in old papers and in code ids (`neighborhood`, `?cabinet=`). Do not
teach them. A **neighborhood** was this spec's word for a project; a
**cabinet** was Office-map furniture. Full table:
`docs/specs/SUITE_VOCABULARY.md`.

**Reserved words — one word, one meaning, workspace-wide.** Vocabulary debt
compounds: a word that means two things in the docs eventually means two
things in the code, and that rename costs a migration.

| Word | Means exactly this | Where it lives |
|---|---|---|
| **instructions** | any binding rule file | `AGENTS.md` (L0/L1) |
| **charter** | this spec | `CHARTER.md` |
| **contract** | one agent's instructions | `CONTRACT.md` (L2) |
| **prompt** | one agent's shift brief (This run) | `prompt.md` (L3) |
| **protocol** | the work-order engine's own rulebook — nothing else | the store's protocol doc |
| **blueprint** | the installable suite (map + setup) — never a single file | BluePrint |
| **agent** | an employed identity with a contract and a schedule that claims work | `CONTRACT.md` + the identity registry |
| **job** | a scheduled duty that does not claim | roster `kind=job` |
| **work order** | one unit of filed work; work moves only by work order | the store |
| **workspace** | the founded root | root `AGENTS.md` |
| **project** | one independent L1 folder | project `AGENTS.md` |

When you add a concept, give it a fresh word; never overload a reserved one.

**The legibility test — a filename says what the file is.** A stranger
navigating the tree cold can tell what a file is from its name alone. This
binds every file the protocol tells you to create and everything a founding
tool generates. Prefer plain industry words (`CONTRACT.md`,
`ARCHITECTURE.md`, `BOUNDARIES.md`) over evocative ones. Brand voice is
never a filename.

## 2. The three layers

Every piece of a working workspace belongs to exactly one layer:

| Layer | Owns | Reference implementation |
|---|---|---|
| **Store** | The work — work orders, claims, signed authors, audit trail | [WorkLane](https://github.com/protocolcity/WorkLane) |
| **Orchestrator** | The agents — identities, schedules, dispatch, budgets | [WorkForce](https://github.com/protocolcity/WorkForce) |
| **Workplace** | The code the agents act on | your repos |

The layers are substitutable — the Charter cares that each exists and keeps
its rules, not whose software fills it. None of the three is required to
comply with this spec; a text editor and a written queue are enough.

## 3. The levels of instructions

Instructions are written at four levels. Lower levels may tighten higher
ones, never loosen them. **L0–L3** are spec codes; surfaces say workspace /
project / contract / This run.

| Level | Instructions | Lives at | Binds |
|---|---|---|---|
| **L0** | Workspace instructions | `AGENTS.md` at the workspace root | every project and agent |
| **L1** | Project instructions | `AGENTS.md` at each project root | everyone working in that project |
| **L2** | Employment contract | one `CONTRACT.md` per agent | that agent, every dispatch |
| **L3** | Shift brief (This run) | one `prompt.md` per agent | that agent, this dispatch |

**The vendor-pointer rule:** the canonical instructions file is always
`AGENTS.md`. Vendor-specific files (`CLAUDE.md`, `GROK.md`, …) are
**optional** — add them only when a vendor CLI needs its own filename. When
present, they must be thin pointers, never content — e.g. `CLAUDE.md`
containing only `@AGENTS.md`, `GROK.md` as a symlink. One body of
instructions, every vendor reads it. Founding tools do not plant vendor
pointers by default.

**Boundaries:** cross-project grants live at workspace-root `BOUNDARIES.md`
(L0 only). Forever aliases still accepted if present: `PERIMETER.md`,
`OFFICE_PERIMETER.md`, `CITY_EDGES.md`. Projects (L1) use the implicit home
default; contracts (L2) and prompts (L3) may promise scope but do not own
the registry.

**The workspace of one:** a single-project workspace merges L0 and L1 — one
`AGENTS.md` serves as both workspace and project instructions until a second
project exists. Split them the day the registry gains its second row; most
workspaces start here.

**Minimum contents:**

- **L0 (workspace):** the project registry (what exists, where, its work-order
  prefix); cross-project rules (always scope work orders explicitly — "one
  work order per project" when work spans two); boundaries (which projects
  may not touch each other, and how they're allowed to talk — e.g. HTTP
  client only, never imports); what's gated to You workspace-wide.
- **L1 (project):** what this place is; how to run/test it; its work-order
  store; local boundaries and no-go zones; which agents serve it; what's
  gated to You here.
- **L2 (contract):** the agent's identity; what work it may claim (its
  assignment) and what it must never touch; its working procedure (claim →
  work → verify → close out); its stop rules.
- **L3 (This run):** the short dispatch brief — read your contract, check
  the queue, do one slice, sign your work.

## 4. The compliance test

A folder is a **project** — protocol-compliant — when three things are true:

1. **Its instructions are written.** An `AGENTS.md` at its root says what it
   is and how to work in it.
2. **Its work is tracked.** Work is filed as work orders with explicit
   scope.
3. **Its agents sign.** Every agent action — work order, comment, commit —
   carries a registered identity.

That's the whole test. A dormant repo with written instructions is
compliant; a busy repo coordinated over chat is not.

## 5. Work orders

One store per project, each with a short prefix (`app-1`, `web-42`). The
store's own protocol is instructions for work-order lifecycle — statuses,
claims, close-out contracts, comment cadence — and this Charter defers to it
rather than duplicating it (reference: WorkLane's PROTOCOL). What the Charter
itself requires: signed authorship on every work order and comment, explicit
project scope on every work order, and a close-out that states what was done
and how it was verified.

A paper workspace may track work in any written queue. WorkLane is the
optional engine that automates claim, sign, and close.

## 6. Agents and jobs

- **Identity:** every agent is registered by name in the identity registry
  before it works. No anonymous work.
- **Contract:** every agent has an L2 contract. An agent without a contract
  doesn't dispatch.
- **Agents vs jobs:** an **agent** claims work orders under its identity; a
  **job** (reports, audits, clocks) observes or runs on a schedule and never
  claims. Don't let a job mutate the queue.
- **Vendor neutrality:** an agent is a vendor CLI plus a contract plus an
  identity. Swapping the vendor doesn't change the instructions it obeys.
- **Your gates:** publishing, releases, money, permissions, and anything
  irreversible are your decisions. Agents prepare; You ship.

## 7. Founding principles

1. **Bots execute, humans govern.**
2. **Every action is signed.**
3. **Documentation is the interface.** New agent, new vendor, new person:
   read the instructions, start working.
4. **The protocol is open; the services are premium.**
5. **Every folder has a purpose.**
6. **Every path resolves.** Any path, link, or cross-reference in
   instructions, documentation, or a founding template must name a file that
   exists. A broken link in instructions is a compliance gap, not a
   documentation gap.

## 8. Founding a workspace

1. **Pick your workspace root** — the folder your projects live under.
2. **Write L0** — workspace instructions at the root: registry, scoping
   rule, boundaries.
3. **Write each project** — an L1 `AGENTS.md` per project (start with one).
   Optionally add vendor pointers if a CLI needs its own filename.
4. **Track work** — a written queue (e.g. WorkLane), one store per project,
   file your first real work orders.
5. **Hire your first agent** — one vendor CLI, one registered identity, one
   L2 contract, one L3 prompt, on whatever scheduler you have (or run it by
   hand). One agent, one assignment, small slices.
6. **Grow by evidence** — add agents when the queue demands it, instructions
   when a mistake teaches you one, projects when a folder earns one. The
   workspace is legible at every size.

The walkthrough is [FOUNDING.md](FOUNDING.md).

---

## 9. The authority tiers

*(Full doctrine: [The Covenant](COVENANT.md) — ratified 2026-07-16)*

Three tiers govern every session in a founded workspace:

| Tier | Authority | Signs as | For You relationship |
|---|---|---|---|
| **You** | The human — ultimate authority; source of all gates and final calls | Themselves | Owns For You |
| **Session (hand)** | A surface You act through; carries your full authority for the session | You (shared identity) | Never files into For You — a session IS You |
| **Agent** | An employed identity: own registered id, own L2 contract, own schedule | Its registered identity (not Yours) | Files into For You at its authority ceiling; never self-authorizes above it |

**The test:** whose authority does the session run under — not what model is
running in it.

See [The Covenant](COVENANT.md) for the full doctrine, the session shutdown
protocol, and team extension mechanics.

## 10. The five-event grammar

*(Ratified 2026-07-16)*

Exactly five events define the state space of a working workspace. All
motion on its surfaces derives from one of them; no motion is invented
outside this grammar.

| Event | Meaning |
|---|---|
| **Filed** | A work order entered the queue |
| **Claimed** | An agent took ownership of a work order |
| **Signed** | An agent closed out a work order — work verified, comment posted |
| **Agent arrives** | A scheduled agent started a shift |
| **Agent leaves** | A scheduled agent's shift ended |

**Two-motions law:** every rendered motion wears exactly one of two signals
— a receipt (it happened) or a clock (it is happening now). No motion
without a signal; no signal without a motion.

Future richer renderings of these events require no protocol-layer change.
Adding a new event requires a founding-level amendment to this section.

## 11. The truth layer

*(Ratified 2026-07-16)*

Every workspace has two layers — truth and skin — and only the truth layer
is invariant.

**Truth words** speak the filesystem and the protocol. They are the words
this Charter uses and the words surfaces must teach:

| Truth word | What it names |
|---|---|
| Workspace | The founded root — wherever L0 instructions live |
| Project | A managed folder with a governing `AGENTS.md` |
| Unmanaged folder | A folder without a governing `AGENTS.md` |
| Work order | One unit of work in the queue |
| Agent | An employed identity: registered, contracted, scheduled |
| Job | A scheduled duty that does not claim |
| You | The signed-in human — viewer-relative |
| The five events | Filed, claimed, signed, agent arrives, agent leaves |

**Skin words** are optional rendered labels. Any analogy — a city, a studio,
a lab — may wrap the default by providing a truth-to-skin mapping. The
protocol layer does not change with the skin. **Protocol City** is brand;
it does not replace workspace / project on the operating path.

**Registry keys speak truth.** A skin rename is a skin-layer change and
never requires a data migration. Legacy wire ids (`neighborhood`,
`cabinet`) may remain in code forever.

## 12. Output-landing convention

*(Ratified 2026-07-16; promoted from L1 to L0)*

Work output in any project lands in exactly one of three buckets:

| Bucket | Contents | Storage |
|---|---|---|
| **Runtime evidence** | Logs, run artifacts, generated HTML, ephemeral build output | Gitignored; never versioned. Canonical directory name: `local/` (projects may use a project-specific name). |
| **Work products** | Research, audits, doc patches, ADRs — anything You review in git history | Versioned under `docs/` |
| **Claims about work** | Close-out statements, verification notes, follow-up filings | On the work-order store (close-out comment); never a committed file |

No bucket is optional. An agent that commits a close-out statement to a
versioned file, or versions ephemeral logs, is non-compliant with this
Charter.

## 13. Optional products

The spec stands alone. Products that automate parts of it are optional and
replaceable:

| Product | What it automates |
|---|---|
| **BluePrint** | Founding tools + a visual map of the workspace |
| **WorkLane** | Work orders — local-first queue with claim, sign, and close |
| **WorkForce** | Hired agents — registered identities on schedules |

If you install BluePrint: **pages belong to the suite. Engines belong to
products.** Adding a product means adding a page in the suite, not a second
front door. Engine packages stay separate ships — standalone use, independent
export seams, separate licensing.

You can comply with this Charter without installing any of them.
