# Founding your city

The [Charter](CHARTER.md) is the law; this is the walkthrough. An afternoon,
a text editor, and one honest inventory of your projects is all it takes.
Nothing to install — the ["install"](templates/README.md) is copying
templates and filling them in.

**A city = a folder + a roster + an edge registry.** The folder is the city
root; the roster is who works which neighborhood; the edge registry is the
city's ACL — which cross-neighborhood permissions exist beyond the default
that every home already reads and writes only itself.

**Recursive founding:** any folder may be founded — including
folders inside an existing city; growth is founding inward. The definition
never says top-level. Unfounded depth stays paper on the map; founded depth
wears a city gate and the zoom ladder resets (see
[CITY_STORY — THE FRACTAL LAW](specs/CITY_STORY.md)). Founding remains a
citizen act, never automatic. *(The Charter's normative recursive clause
rides a later slice — this file and CITY_STORY hold the doctrine until
then.)*

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

Also declare the city's **perimeter registry** (permission grants across
cabinets) at L0. Copy [`templates/PERIMETER.md`](templates/PERIMETER.md) to
the city root as `PERIMETER.md` (next to `AGENTS.md`). The found default is
empty: every cabinet is sovereign at home — no cross-grants, no drawn edges.
When two cabinets truly share a boundary, ratify a row; the city map renders
that permission from day one. Grant-model prose (read / write / via per kind)
lives in [CITY_EDGES — THE GRANT MODEL](specs/CITY_EDGES.md) (WIDTH LAW
**spec**); the live registry is city-root `PERIMETER.md`.

## Step 2 — charter your first neighborhood (L1)

Copy [`templates/neighborhood-AGENTS.md`](templates/neighborhood-AGENTS.md) into **one** project
as `AGENTS.md`. The section that pays for itself first is **no-go zones** —
what agents must never touch. Vendor pointers are optional
([`templates/vendor-pointers.md`](templates/vendor-pointers.md)) — add them
only if a CLI needs its own filename. Don't charter everything at once; one
real neighborhood beats five hollow ones.

## Step 3 — stand up the Desk

Open a neighborhood **ledger** at the **Desk** (powered by
[WorkLane](https://github.com/protocolcity/ProtocolCity-WorkLane) — the
engine package developers install) and file your first three tickets:
real work you actually want done. From here on, work moves by ticket, not
memory.

## Step 4 — employ your first worker (L2 + L3)

Pick one vendor CLI. Create `workers/<worker-id>/` in the neighborhood and
fill in [`templates/worker-CONTRACT.md`](templates/worker-CONTRACT.md) (the
contract: lane, never-touch list, procedure, stop rules) and
[`templates/worker-prompt.md`](templates/worker-prompt.md) (the shift brief).
Register the identity at the Desk, label one ticket
`lane:<worker-id>`, and run a shift by hand — paste the prompt into the CLI
and watch it claim, work, verify, close out. Scheduling can come later;
by-hand dispatch from **Dispatch** is a legitimate first shift (no
automated workforce required on day one).

## Step 5 — check compliance

You're a city when, for each chartered neighborhood (Charter §4):

- [ ] **Law written** — `AGENTS.md` at its root
- [ ] **Work ticketed** — filed at the Desk; every change ties to a ticket
- [ ] **Workers sign** — every agent action carries a registered identity

## Step 6 — grow by evidence

Add a worker when the queue demands it, a law when a mistake teaches you
one, a neighborhood when a project earns one. A filled worked example —
city root, one neighborhood, one worker — lives in [`example/`](example/).

Founded? [RUNNING.md](RUNNING.md) is day two: the loops, the five citizen
duties, and the flywheel that keeps work moving.
