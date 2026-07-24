# ProtocolCity-BluePrint

> **Pre-release (0.1.x).** Installable suite for coordinating AI agents with
> plain files you own — [WorkLane](https://github.com/protocolcity/ProtocolCity-WorkLane)
> (work orders) · [WorkForce](https://github.com/protocolcity/ProtocolCity-WorkForce)
> (agents) · this BluePrint (map + CLI). Expect sharp edges; file issues.

**A map of the AI instructions already living in your project folders.**  
It does not replace Claude, Cursor, or Grok — it shows what those agents are
supposed to follow, who is hired, and which work orders are still open.

> Every agent has instructions. Every job is a file. Every work order closes the loop.

## Install the suite (recommended)

```bash
brew install protocolcity/tap/protocolcity
# Pick *your* folder name (Developer, notes, work, … — no forced default).
protocolcity setup ~/my-workspace
protocolcity serve --root ~/my-workspace --with-engines
# → http://127.0.0.1:8801/  (Overview; Map digs in)
```

That one formula installs the BluePrint CLI and pulls WorkLane + WorkForce
from PyPI. Product source repos stay separate; install does not require cloning
them.

Or: `pip install protocolcity protocolcity-worklane protocolcity-workforce`

### What to clone vs install

| You want… | Do this |
|---|---|
| **Run the suite** (Overview · Map · agents · work orders) | **Homebrew** (above) or the three PyPI packages |
| **Read the papers** (Charter, templates, example) | Browse/clone [ProtocolCity-BluePrint](https://github.com/protocolcity/ProtocolCity-BluePrint) — docs only |
| **Contribute to an engine** | Clone WorkLane / WorkForce source repos (developer path) |

Cloning BluePrint alone does **not** install a runnable Map/Desk/Roster.

## What you see

Open the suite → **Overview** (system summary). Click **Map** to dig in —
then click a project folder to see:

| Layer | What it is | Typical files |
|---|---|---|
| **You** | Human decisions and gates | (you, in the loop) |
| **Workspace** | Rules for the whole folder | root `AGENTS.md`, boundaries |
| **Project** | One app or repo under the workspace | project `AGENTS.md` |
| **Agent** | A hired AI worker | `workers/<id>/CONTRACT.md` |
| **Job / this run** | What to do on this shift | `workers/<id>/prompt.md` |
| **Work orders** | Tracked tickets until done | WorkLane desk |

Nobody has to learn a “city” metaphor to run the system. Optional deeper docs
(Charter, Manifesto) keep the brand story for people who want it.

## Why

Agents are brilliant and unaccountable. Every vendor wants orchestration to
live inside its own runtime, in its own config format. Decisions evaporate in
chat windows. BluePrint is the opposite bet: coordination as **files you can
read**, work orders you can audit, and agents that **sign** what they do —
owned by you.

**WorkLane** tracks work orders. **WorkForce** runs hired agents.  
**BluePrint** is the map that ties the folder, the instructions, and the loop together.

## What's inside

Papers live on GitHub (links work from PyPI too):

| Document | What it is |
|---|---|
| [**CHARTER.md**](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/CHARTER.md) | Full protocol spec (advanced / optional depth) |
| [**MANIFESTO.md**](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/MANIFESTO.md) | Why we built this — brand voice |
| [**FOUNDING.md**](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/FOUNDING.md) | Paper path: templates + compliance (no install) |
| [**RUNNING.md**](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/RUNNING.md) | Day-to-day loops after setup |
| [**templates/**](https://github.com/protocolcity/ProtocolCity-BluePrint/tree/main/templates) | Fill-in-the-blank instruction files |
| [**example/**](https://github.com/protocolcity/ProtocolCity-BluePrint/tree/main/example) | Minimal workspace (one root, one project, one agent) |

## The short version

A **workspace** is one root folder. Each **project** is a subfolder with
instructions agents must follow (`AGENTS.md`). Work moves as **work orders**.
Your **agents** are any vendor, each with a registered identity that signs
what it does. **Boundaries** say what agents may not touch.

A project is set up well when three things are true:

1. **Instructions exist** — an `AGENTS.md` at its root.
2. **Work is tracked** — a work order with clear scope.
3. **Agents sign** — every action carries a registered identity.

Start with one project, one agent, one instruction file —
[FOUNDING.md](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/FOUNDING.md)
walks the paper path; the install path above opens the **map** so you can see
the same structure visually.

## Report a bug

1. On the machine that broke, run (local only — nothing is uploaded):

   ```bash
   protocolcity feedback
   # or: protocolcity feedback ~/my-workspace
   ```

2. Paste the markdown into a new issue:
   [ProtocolCity-BluePrint issues](https://github.com/protocolcity/ProtocolCity-BluePrint/issues/new/choose)

Include versions from that block. Rough routing:

| Symptom | Board |
|---|---|
| Overview / Map / setup / serve shell | [BluePrint issues](https://github.com/protocolcity/ProtocolCity-BluePrint/issues) |
| Work orders / `tk` / desk stores | [WorkLane issues](https://github.com/protocolcity/ProtocolCity-WorkLane/issues) |
| Hire / roster / agent daemon | [WorkForce issues](https://github.com/protocolcity/ProtocolCity-WorkForce/issues) |
| Formula only | [homebrew-tap](https://github.com/protocolcity/homebrew-tap/issues) |

## Status

**v0.1.x pre-release.** Install path (Homebrew / PyPI) is live. Suite UX is
map-first and still sharpening. Expect the shell and ship words to move
quickly as first-user feedback lands.

## License

[CC BY 4.0](https://github.com/protocolcity/ProtocolCity-BluePrint/blob/main/LICENSE) — use it, adapt it, build on it, with attribution.
