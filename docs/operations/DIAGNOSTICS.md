# Workspace diagnostics

`blueprint doctor --root WORKSPACE` reads only the selected workspace. It checks
instructions, project/store registration, read-only SQLite integrity, component
receipts and roster readability. It does not run workspace scripts, probe fixed
host ports, modify records or infer provider capacity from a binary.

```sh
blueprint doctor --root /path/to/workspace --json
blueprint doctor --root /path/to/workspace --probe
blueprint doctor --root /path/to/workspace --support-bundle /path/to/new-report.json
```

Every finding has a stable code, severity, state, source, observation time and
next step. Exit 1 means a diagnostic error; exit 2 means an invalid request or
failed report/repair operation. Missing optional components remain explicit.
A readable receipt is installation evidence, not proof of a healthy process.

`--probe` uses only local origins recorded in this workspace's receipts, refuses
redirects and never substitutes a default port. BP must report the same workspace
and build. A usable WorkLane read endpoint does not prove write authority.
WorkForce process/heartbeat and provider qualification require their own evidence.

Support JSON includes only allowlisted diagnostic fields. It omits source paths,
project/worker names, runtime configuration, credentials, raw logs and work text.
An existing report is never overwritten. A bundle is not an automatic upload.

`--repair vendor-pointers` plants missing CLAUDE.md/GROK.md pointers to an existing
workspace AGENTS.md. It preserves existing files, including divergent pointers.
There is no blanket automatic repair; inspect and back up records before any
separate store/roster repair. Historical doctor internals remain compatibility
helpers for older adoption code, not the public diagnostic entrypoint.

Doctor, behavioral tests, browser journeys and installed-build smoke checks
supply different evidence. See [verification](VERIFICATION.md) and
[recovery](DEPLOYMENT.md). No check certifies the absence of every bug.
