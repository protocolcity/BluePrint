# BluePrint build, activate, recover

BluePrint is one application, normally on localhost:8803. WorkLane and WorkForce are independent engines. Updating BP must not replace their databases, rosters, credentials, or running processes.

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
.venv/bin/python tools/deploy.py activate --workspace /path/to/workspace --release /path/to/workspace/local/blueprint/releases/VERSION
```

Activation checks the installed app on a temporary port, replaces only BluePrint's launch agent, and verifies the running version and workspace. A failed activation restores the previous launch-agent configuration. The active receipt is `<workspace>/.blueprint/deployment.json`.

For a workspace retiring older UI ports, specify `--legacy-port 8801 --legacy-port 8802` during the first activation, after stopping their prior listeners. Subsequent activations preserve these options. The single BP process owns the redirect listeners; they do not run additional UIs or engines. GET links redirect to the current origin; legacy writes are refused. `/desk`, `/roster`, and `/workspace-map` resolve to Work, Agents, and Map.

## Recovery and ordinary operation

Use `blueprint status --root /path/to/workspace` to check the actual responding build. `blueprint service start|restart|stop --root /path/to/workspace` controls only BP and uses bounded service calls. `blueprint serve --foreground --root /path/to/workspace` is for development. Keep it on a separate test port when the service is running.

For rollback, activate a previously verified release directory. Rollback does not restore or discard work orders, agent history, or notes. The deployment receipt and previous service configuration are diagnostic metadata; no routine copies of runtime databases are created by this process.

Homebrew can remain installed for Python and other tools. BP's application lifecycle must use this release path while source consolidation is active; do not use a Homebrew upgrade as a second BP deployment path. Independent engines retain their own upgrade procedures.

## Read-only staffing audit

Run `python -m protocolcity.open_work_audit --workspace /path/to/workspace --json --feeds --process --decay` with the installed BP interpreter. An explicitly selected workspace uses its registered stores and installed WorkLane readiness policy on temporary SQLite snapshots; original stores are opened read-only. It does not fall back to another host's default desk. The current adapter supports the workspace's standard local WorkLane layout; an unavailable engine or store is reported as unknown.

Coverage distinguishes You, no worker, missing/retired workers, manual and scheduled lanes, ambiguous assignments and queue-scope mismatches. Configured coverage is not authentication, liveness or execution proof. Process checks use saved readiness and configuration; they do not certify transport. Legacy URL-only audits remain available, but cannot establish selected-workspace staffing coverage. The scheduled operations reports use the explicit workspace path and carry these limits.
