# Founding your city

The [Charter](CHARTER.md) is the law; this is the walkthrough. An afternoon,
a text editor, and one honest inventory of your projects is all it takes.
Nothing to install — the ["install"](templates/README.md) is copying
templates and filling them in.

## Step 0 — find your neighborhoods

A **neighborhood** is one thing with an **independent lifecycle**: it ships,
verifies, and fails on its own. Two questions sort any folder:

1. *Could this have its own ticket queue without half the tickets really
   belonging somewhere else?*
2. *Does it deploy, release, or get verified on its own?*

Two yeses → neighborhood. Common shapes:

| Your setup | Your city |
|---|---|
| **Several repos** in one folder | The folder is the city root; each repo a neighborhood |
| **A monorepo** | The repo is the city root; apps/packages with independent lifecycles are neighborhoods |
| **One project** | A **city of one** — the project is root and neighborhood at once; one `AGENTS.md` serves as both L0 and L1 until a second neighborhood exists (Charter §3) |
| **Client work** | Each engagement a neighborhood; your workspace the city root |

Not neighborhoods: a library folder inside an app, your notes, backups,
scratch dirs — no independent lifecycle, no queue of their own. When in
doubt, don't charter it; neighborhoods are earned (Charter §8.6).

## Step 1 — write city law (L0)

Copy [`templates/city-AGENTS.md`](templates/city-AGENTS.md) to your city root as
`AGENTS.md`. The registry table — every neighborhood, its folder, its ticket
prefix — is the heart of it. *(City of one: skip to Step 2; your one file
carries both levels.)*

## Step 2 — charter your first neighborhood (L1)

Copy [`templates/neighborhood-AGENTS.md`](templates/neighborhood-AGENTS.md) into **one** project
as `AGENTS.md`. The section that pays for itself first is **no-go zones** —
what agents must never touch. Add the vendor pointers
([`templates/vendor-pointers.md`](templates/vendor-pointers.md)). Don't
charter everything at once; one real neighborhood beats five hollow ones.

## Step 3 — stand up the desk

Install a ticket store — [WorkLane](https://github.com/protocolcity/ProtocolCity-WorkLane)
is the reference — create one store for the neighborhood, and file your
first three tickets: real work you actually want done. From here on, work
moves by ticket, not memory.

## Step 4 — employ your first worker (L2 + L3)

Pick one vendor CLI. Create `workers/<worker-id>/` in the neighborhood and
fill in [`templates/worker-CONTRACT.md`](templates/worker-CONTRACT.md) (the
contract: lane, never-touch list, procedure, stop rules) and
[`templates/worker-prompt.md`](templates/worker-prompt.md) (the shift brief).
Register the identity at the desk, label one ticket `lane:<worker-id>`, and
run a shift by hand — paste the prompt into the CLI and watch it claim,
work, verify, close out. Scheduling can come later; by-hand dispatch is a
legitimate orchestrator.

## Step 5 — check compliance

You're a city when, for each chartered neighborhood (Charter §4):

- [ ] **Law written** — `AGENTS.md` at its root
- [ ] **Work ticketed** — a store at the desk; every change ties to a ticket
- [ ] **Workers sign** — every agent action carries a registered identity

## Step 6 — grow by evidence

Add a worker when the queue demands it, a law when a mistake teaches you
one, a neighborhood when a project earns one. A filled worked example —
city root, one neighborhood, one worker — lives in [`example/`](example/).

Founded? [RUNNING.md](RUNNING.md) is day two: the loops, the five citizen
duties, and the flywheel that keeps work moving.
