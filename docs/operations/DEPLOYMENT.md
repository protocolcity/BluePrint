# BluePrint build, activate, recover

BluePrint is one application, normally on localhost:8801. Leftover split ports :8802 (old Map) and :8803 (old Overview) redirect to that origin. WorkLane and WorkForce are independent engines. Updating BP must not replace their databases, rosters, credentials, or running processes.

## Build and verify

Use Python 3.11 or later. From the canonical source checkout, create a development environment and run the Overview and Map tests. Engine integration tests write disposable stores when `BP_TEST_WORKLANE_PYTHON` explicitly names an installed WorkLane interpreter.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
PYTHONPATH=overview/v1 .venv/bin/python -m unittest discover -s overview/v1/tests
PYTHONPATH=map/v1 .venv/bin/python -m unittest discover -s map/v1/tests
.venv/bin/python tools/deploy.py stage --source "$PWD" --workspace /path/to/workspace --python "$PWD/.venv/bin/python"
```

`stage` creates an immutable release under `<workspace>/local/blueprint/releases/<version>/`, installs the wheel into its own environment, and records the wheel hash, Git head, source path, and whether uncommitted changes were included. Existing releases are not overwritten. Bump the package version before another build. Review source changes and the package contents before public distribution; a local candidate is not a published release.

## Activate

```sh
.venv/bin/python tools/deploy.py activate --workspace /path/to/workspace --release /path/to/workspace/local/blueprint/releases/VERSION --port 8801
```

Activation checks the installed app on a temporary port, replaces only BluePrint's launch agent, and verifies the running version and workspace. After restart it waits up to 60 seconds (override with `--probe-timeout`) for the service to report the expected build, distinguishing a slow start from a wrong build. Re-activating the release that is already live is a fast no-op. A failed activation restores the previous launch-agent configuration. The active receipt is `<workspace>/.blueprint/deployment.json`.

For a workspace retiring leftover split ports, specify `--legacy-port 8802 --legacy-port 8803` during the first activation, after stopping their prior listeners. Subsequent activations preserve these options. The single BP process owns the redirect listeners; they do not run additional UIs or engines. GET links redirect to the current origin; legacy writes are refused. `/desk`, `/roster`, and `/workspace-map` resolve to Work, Agents, and Map. Activation always writes `--port 8801` for the primary listener.

## Recovery and ordinary operation

Use `blueprint status --root /path/to/workspace` to check the actual responding build. `blueprint service start|restart|stop --root /path/to/workspace` controls only BP and uses bounded service calls. `blueprint serve --foreground --root /path/to/workspace` is for development. Keep it on a separate test port when the service is running.

For rollback, activate a previously verified release directory. Rollback does not restore or discard work orders, agent history, or notes. The deployment receipt and previous service configuration are diagnostic metadata; no routine copies of runtime databases are created by this process.

Homebrew can remain installed for Python and other tools. BP's application lifecycle must use this release path while source consolidation is active; do not use a Homebrew upgrade as a second BP deployment path. Independent engines retain their own upgrade procedures.

## Upgrading from the three-lane install

Older Homebrew installs ran three separate launch agents: `com.protocolcity.suite` on :8801, `com.protocolcity.blueprint-map` on :8802, and the single-page `com.protocolcity.blueprint-overview` on :8803, plus possibly the older `com.protocolcity.citylens`. `blueprint upgrade` converts a host still running any of these to the single consolidated app:

```sh
blueprint upgrade --root /path/to/workspace --dry-run   # print the plan only, write nothing
blueprint upgrade --root /path/to/workspace              # boot out legacy agents, activate the single app
```

It detects each legacy agent by plist presence and by `launchctl print`, boots out any that are found, and moves their plists to `<workspace>/local/blueprint/retired-services/<date>/` — it never deletes them. It then writes and bootstraps the single `com.protocolcity.blueprint-overview` agent for the *installed* package (no build/stage step) with `--port 8801 --legacy-port 8802 --legacy-port 8803`, and verifies the responding build on :8801 and the 307 redirects on leftover :8802 and :8803. `--quiet` suppresses output for scripted/post-install use. A second run with nothing to change reports a no-op. `<workspace>/.blueprint/` (connections, job reports) and every project's `.protocolcity/desk-join.json` are left untouched; no WorkLane store, WorkForce roster, ledger, or daemon is touched. This is macOS-only today; on other platforms it fails with a clear error instead of doing nothing silently.

## Read-only staffing audit

Run `python -m protocolcity.open_work_audit --workspace /path/to/workspace --json --feeds --process --decay` with the installed BP interpreter. An explicitly selected workspace uses its registered stores and installed WorkLane readiness policy on temporary SQLite snapshots; original stores are opened read-only. It does not fall back to another host's default desk. The current adapter supports the workspace's standard local WorkLane layout; an unavailable engine or store is reported as unknown.

Coverage distinguishes You, no worker, missing/retired workers, manual and scheduled lanes, ambiguous assignments and queue-scope mismatches. Configured coverage is not authentication, liveness or execution proof. Process checks use saved readiness and configuration; they do not certify transport. Legacy URL-only audits remain available, but cannot establish selected-workspace staffing coverage. The scheduled operations reports use the explicit workspace path and carry these limits.
