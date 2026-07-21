# 🏙️ ProtocolCity-BluePrint

> **Pre-release (0.1.x).** The roof of the **ProtocolCity** suite —
> [WorkLane](https://github.com/protocolcity/ProtocolCity-WorkLane) (desk) ·
> [WorkForce](https://github.com/protocolcity/ProtocolCity-WorkForce) (roster) ·
> this BluePrint (map + suite CLI). Expect sharp edges; file issues.

**The blueprint for running your own city of AI agents** — and the installable
suite that makes Map · Desk · Roster real on a laptop.

## Install the suite (recommended)

```bash
brew install protocolcity/tap/protocolcity
protocolcity found ~/my-city
protocolcity serve --with-engines
# → http://127.0.0.1:8801/  (Map · Desk · Roster)
```

That one formula installs the BluePrint CLI and pulls WorkLane + WorkForce
from PyPI. Product source repos stay separate; install does not require cloning
them.

Or: `pip install protocolcity protocolcity-worklane protocolcity-workforce`

## Spec + paper

Protocol City is also a **specification** for organizing a workspace so humans
and AI agents from any vendor can build together, in parallel, accountably.
You can adopt the paper path with a text editor and the templates below.

> Every bot is a worker, every `.md` is a law, and every contributor becomes
> a citizen.

## Why

Agents are brilliant and unaccountable. Every vendor wants orchestration to
live inside its own runtime, in its own config format. Decisions evaporate in
chat windows. The Blueprint is the opposite bet: coordination as a protocol —
files, tickets, and signed work — durable, auditable, human-readable, and
owned by you.

**WorkLane gives you the desk. WorkForce gives you the workforce.
The Blueprint gives you the map.**

## What's inside

| Document | What it is |
|---|---|
| [**CHARTER.md**](CHARTER.md) | The spec: definitions, the three layers, the four levels of law, the compliance test, and the founding path |
| [**MANIFESTO.md**](MANIFESTO.md) | Why the city exists — what we believe and the wager we're making |
| [**FOUNDING.md**](FOUNDING.md) | Day one: find your neighborhoods, copy the templates, pass the compliance test — an afternoon, start to finish |
| [**RUNNING.md**](RUNNING.md) | Every day after: the loops, the five citizen duties, the flywheel — and what runs itself |
| [**templates/**](templates/) | Fill-in-the-blank law files for all four levels, plus vendor pointers |
| [**example/**](example/) | Riverside — a complete minimal city (one root, one neighborhood, one worker), every template filled in |

## The short version

A **city** is your whole operation. Each project is a **neighborhood**. Work
moves only by ticket through the **work-order desk**. Your agents are the
**workforce** — any vendor, each with a registered identity that signs
everything it does. The rules are **laws**: plain markdown files at four
levels, from city-wide law down to a single worker's shift instructions.

A project is protocol-compliant when three things are true:

1. **Its law is written** — an `AGENTS.md` at its root.
2. **Its work is ticketed** — filed at the desk, explicit scope.
3. **Its workers sign** — every action carries a registered identity.

Start with one neighborhood, one worker, one law —
[FOUNDING.md](FOUNDING.md) walks you through it, and there's nothing to
install: adopting the Blueprint is copying [templates](templates/) and
filling them in.

## Status

**v0.1.x pre-release.** Install path (Homebrew / PyPI) is live. Suite UX is
still sharpening. The Blueprint is extracted from a working city: one operator,
one machine, multiple products, agents from several vendors. Expect the spec
and the shell to move quickly.

## License

[CC BY 4.0](LICENSE) — use it, adapt it, build your city on it, with
attribution.
