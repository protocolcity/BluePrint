# Verification tiers

BluePrint source validation is layered. Use one entrypoint locally; CI runs the
matching tiers on pull requests and release candidates.

## Entrypoint

From the repository root (development checkout or prepared task branch):

```bash
python scripts/verify.py --tier edit    # while editing
python scripts/verify.py --tier pr      # before opening a review PR
python scripts/verify.py --tier release # before a package/release candidate
python scripts/verify.py --tier installed --root /path/to/workspace --expected-version VERSION
```

Set `BP_VERIFY_PYTHON` to pin the interpreter (for example the project venv).
Browser journeys require test-only dependencies:

```bash
python -m pip install -r browser-tests/requirements-dev.lock
python -m playwright install chromium
# Required for real, disposable engine actions (never point this at source-editable code):
export BP_TEST_WORKLANE_PYTHON=/path/to/installed-worklane/venv/bin/python
```

Failure artifacts (traces, screenshots) land under `browser-tests/artifacts/`
with retain-on-failure tracing. They are local-only and must not contain live
workspace paths or private desk data — fixtures are synthetic.

## CI mapping

| Tier | When | Evidence |
| --- | --- | --- |
| **edit** | Active implementation | Overview + Map `unittest` suites on the candidate revision |
| **pr** | Every integration PR | edit + skip audit + Playwright journeys on disposable binders |
| **release** | Pre-release cut | pr + template mirror, source privacy, host-path scrub, artifact dry-run |
| **installed** | After authorized activation | Deployment receipt, `/api/operations` build identity, automated read-only critical-route smoke plus separate changed-action acceptance |

GitHub workflow `Source validation` runs component suites and packaging checks.
The `Browser journeys` job runs the Playwright suite when browser dependencies
are installed in CI.

## Acceptance mapping

| Acceptance | Automated evidence | Known gap |
| --- | --- | --- |
| Local entrypoint + tier docs | `scripts/verify.py`, this file | Installed smoke requires explicit workspace and expected version |
| Preserve unit/integration/privacy checks | Existing suites unchanged; `scripts/audit_test_skips.py` lists explicit skips | `BP_TEST_WORKLANE_PYTHON` integration runs only when set |
| Browser journeys (real note/priority writes, reader return, search, keyboard/narrow, empty/partial/stale/failure) | `browser-tests/test_journeys.py` | Stale heartbeat, failed refresh and failed write/draft preservation are covered |
| Synthetic fixtures, failure traces | `browser-tests/support/*`, pytest retain-on-failure | No unlimited retries — failures fail the job |
| Map criteria to tests | Table above | Coverage is journey-based, not a percentage score |

Reproduced product bugs should add a failing-then-passing regression in the
suite that owns the behavior (component unittest or browser journey).

Traces use the [official pytest plugin options](https://playwright.dev/python/docs/test-runners). CI retains synthetic failure evidence for seven days, with no automatic retries. Missing the installed WorkLane dependency fails the write journey rather than silently skipping it.
