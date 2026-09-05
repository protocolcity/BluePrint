# Founding your workspace

The [Charter](CHARTER.md) is the spec; this is the walkthrough. An afternoon,
a text editor, and one honest inventory of your projects is all it takes.
Nothing to install — the ["install"](templates/README.md) is copying
templates and filling them in.

**A workspace = a folder + agents + a boundaries registry.** The folder is
the workspace root; agents are who works which project; Boundaries is the
ACL — which cross-project permissions exist beyond the default that every
home already reads and writes only itself.

**The story:** You → Workspace → Project → Agent · Job. Work is **work
orders**. Binding files are **instructions**.

## Step 0 — find your projects

A **project** is one thing with an **independent lifecycle**: it ships,
verifies, and fails on its own. Two questions sort any folder:

1. *Could this have its own work-order queue without half the cards really
   belonging somewhere else?*
2. *Does it deploy, release, or get verified on its own?*

Two yeses → project. Common shapes:

| Your setup | Your workspace |
|---|---|
| **Several repos** in one folder | The folder is the workspace root; each repo a project |
| **A monorepo** | The repo is the workspace root; apps/packages with independent lifecycles are projects |
| **One project** | A **workspace of one** — the project is root and project at once; one `AGENTS.md` serves as both L0 and L1 until a second project exists (Charter §3) |
| **Client work** | Each engagement a project; your folder the workspace root |

Not projects: a library folder inside an app, your notes, backups, scratch
dirs — no independent lifecycle, no queue of their own. When in doubt, don't
found it; projects are earned (Charter §8).

## Step 1 — write workspace instructions (L0)

Copy [`templates/city-AGENTS.md`](templates/city-AGENTS.md) to your
workspace root as `AGENTS.md`. The registry table — every project, its
folder, its work-order prefix — is the heart of it. *(Workspace of one: skip
to Step 2; your one file carries both levels.)*

Also declare **Boundaries** at L0. Copy
[`templates/BOUNDARIES.md`](templates/BOUNDARIES.md) to the workspace
root as `BOUNDARIES.md` (next to `AGENTS.md`). The found default is empty:
every project is sovereign at home — no cross-grants, no drawn edges. When
two projects truly share a boundary, add a row.

## Step 2 — write your first project (L1)

Copy [`templates/project-AGENTS.md`](templates/project-AGENTS.md) into
**one** project as `AGENTS.md`. The section that pays for itself first is
**no-go zones** — what agents must never touch. Vendor pointers are optional
([`templates/vendor-pointers.md`](templates/vendor-pointers.md)) — add
them only if a CLI needs its own filename. Don't found everything at once;
one real project beats five hollow ones.

## Step 3 — track work

File your first three work orders: real work you actually want done. From
here on, work moves by work order, not memory. A paper list is enough. The
optional engine is
[WorkLane](https://github.com/protocolcity/WorkLane).

## Step 4 — hire your first agent (L2 + L3)

Pick one vendor CLI. Create `workers/<agent-id>/` in the project and fill in
[`templates/worker-CONTRACT.md`](templates/worker-CONTRACT.md) (the
contract: assignment, never-touch list, procedure, stop rules) and
[`templates/worker-prompt.md`](templates/worker-prompt.md) (This run).
Register the identity, label one work order `worker:<agent-id>`, and run a
shift by hand — paste the prompt into the CLI and watch it claim, work,
verify, close out. Scheduling can come later; by-hand dispatch is a
legitimate first shift.

## Step 5 — check compliance

You're a founded workspace when, for each project (Charter §4):

- [ ] **Instructions written** — `AGENTS.md` at its root
- [ ] **Work tracked** — filed as work orders; every change ties to one
- [ ] **Agents sign** — every agent action carries a registered identity

## Step 6 — grow by evidence

Add an agent when the queue demands it, an instruction when a mistake
teaches you one, a project when a folder earns one. When a product file
crosses the **code-efficiency** bands (watch 400 LOC · split 800 · urgent
1 200), agents extract **one** seam or file one routed split work order —
they do not wait to be asked. A filled worked example — workspace root,
one project, one agent — lives in
[`example/`](example/).

Founded and want the optional suite? Start at
[BluePrint](https://github.com/protocolcity/BluePrint).
Day two on the suite is
[RUNNING.md](RUNNING.md).
