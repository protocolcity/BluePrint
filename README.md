# BluePrint

**A window into your work across projects and AI providers.**

BluePrint shows what needs your attention, who is responsible, what execution
has actually happened, and the evidence behind the result. Work stays connected
to its project and instructions instead of disappearing into separate chats.

BluePrint is the operations interface. [WorkLane](https://github.com/protocolcity/WorkLane)
owns work orders, claims and history. [WorkForce](https://github.com/protocolcity/WorkForce)
owns registered executors, provider adapters and runs. Each component remains
independently usable. Starting BP does not hire agents or start the engines.

The 0.1.x series is pre-release. Read the [product contract](docs/PRODUCT.md)
for current capabilities and the boundary between supported behavior and future
provider/host continuation.

## Start

Install the published package in an isolated environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install protocolcity protocolcity-worklane protocolcity-workforce
blueprint setup ~/my-workspace --create --yes
blueprint serve --foreground --root ~/my-workspace --port 8803
```

Open `http://127.0.0.1:8803`. The port above is explicit; use the selected
workspace's deployment receipt to identify an existing service. A source checkout
can contain newer features than the published package. Verify your installation
with `blueprint --version` and `blueprint status --root ~/my-workspace`.

See [running BP](RUNNING.md), [deployment and recovery](docs/operations/DEPLOYMENT.md)
and [Windows status](WINDOWS_FIRST_USER.md) before installing a persistent
service. Keep tests and previews on a separate port from a running workspace.

## First useful journey

1. Select your workspace and inspect Connections. Missing engines should appear
   unavailable; an empty count is not a substitute for a failed connection.
2. Register a real project and its instructions. Projects provides its scope,
   work and papers; Map offers another way to navigate that same information.
3. Capture a scoped work order through WorkLane. Choose a registered executor
   with the required project access and tools. Assignment is not dispatch.
4. Use Agents to inspect configured capacity and actual execution evidence.
   A roster entry alone does not prove that a provider is authenticated or busy.
5. Review artifacts and verification on the work order. Continue or hand off
   only through mechanisms supported by the installed engines.

## How the desk works

| Surface | Question it answers |
|---|---|
| Overview | What needs my attention, and what is the workspace doing? |
| Work | What is the objective, owner, state, evidence and next action? |
| Projects | What belongs to this project, and which instructions apply? |
| Agents | What is configured, what ran, and why did execution stop? |
| Delivery and Timeline | What delivery and execution evidence was observed? |
| Map | Where are this workspace's projects, instructions and papers? |
| Calendar | What is scheduled, dated or embargoed? |
| Connections and Settings | Which sources are available, and what build/preferences are active? |

The interface distinguishes unavailable, stale, empty and healthy sources.
GitHub events are delivery evidence, not agent liveness. Human attention,
reminder dates and execution embargoes have separate meanings.

## Providers and continuation

Codex, Claude, Cursor and Grok can participate through configured WorkForce
adapters and WorkLane tools. Provider, model, worker identity, account quota and
execution host are distinct configuration. Verify their actual availability;
BP does not infer quota or reset times from a configured CLI.

The goal is durable work that can continue across providers. Checkpoint and
safe-handoff support depends on the installed WorkLane/WorkForce versions;
BP does not claim universal chat-session migration or remote/cloud dispatch.
A remote adapter needs explicit host identity, scope, authentication and
observed execution evidence. See the [capability matrix](docs/PRODUCT.md#capabilities).

## Develop and troubleshoot

Start with [AGENTS.md](AGENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
Run behavior tests against disposable workspaces, inspect built artifacts, and
verify the installed build before calling a UI fix complete. Doctor is one
layer of diagnostics, not proof that every feature works.

Keep runtime configuration, credentials and private work history outside
product source. Report bugs using the repository issue templates with a
sanitized version, reproduction and diagnostic result. Component-specific
issues belong to their owning repository.

## License

See [LICENSE](LICENSE).
