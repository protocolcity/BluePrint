# BluePrint PyPI publish checklist

Authorized humans only. Delivery lands source. **Twine upload is a
separate action.** Agents and CI on this repository must not upload.

No API tokens belong in git, CI logs, release notes, or PR bodies.

## Org / repo gate — secret scanning (pc-1517)

GitHub **secret_scanning** and **push_protection** are a required org/repo
gate **before public publish**. A pull request cannot enable them.

| Check | Status for this cut |
|---|---|
| secret_scanning + push_protection | **FAIL until a human confirms they are enabled** on `protocolcity/BluePrint` (Settings → Code security). Delivery agents see `security_and_analysis: null` and cannot flip the toggle. |
| In-repo scrub CI (`public-cut`) | Required and shipping — does **not** replace the org gate. |
| Twine / PyPI | **FAIL / not publish-ready** until the org gate is confirmed **and** an authorized human uploads. No agent twine. |

A later land-bar may claim the org toggle was enabled. Treat that as
unverified here until a person with repo admin opens the security page
and records the enablement. Until then this cut stays **FAIL** on the
org gate and must not be called publish-ready.

## Packages

| Distro | Path | Version | Engines extra |
|---|---|---|---|
| `protocolcity-blueprint` (preferred) | repo root `pyproject.toml` | 0.1.50 | `protocolcity-worklane==0.1.9`, `protocolcity-workforce==0.1.9` |
| `protocolcity` (compat alias) | `packaging/pypi/protocolcity/pyproject.toml` | 0.1.50 | same pins, plus `protocolcity-blueprint[engines]==0.1.50` |

Build both. Upload both, preferred first.

## Dry-run / receipt (required before any upload)

Work in a disposable directory outside the checkout.

```sh
python3.11 -m venv /tmp/bp-cut-venv
/tmp/bp-cut-venv/bin/python -m pip install -U pip build twine
cd /path/to/BluePrint
/tmp/bp-cut-venv/bin/python -m build --sdist --wheel --outdir /tmp/bp-cut-dist
/tmp/bp-cut-venv/bin/python -m build --sdist --wheel --outdir /tmp/bp-cut-dist \
  packaging/pypi/protocolcity
/tmp/bp-cut-venv/bin/python scripts/check_release_artifacts.py
# No-upload validation. Do not print artifact bodies (secrets stay out of logs).
/tmp/bp-cut-venv/bin/python -m twine check /tmp/bp-cut-dist/*
# Optional extra dry-run when twine supports it. If the flag is unknown, stop.
# Never drop --dry-run and rerun. Never pass a token on the command line.
/tmp/bp-cut-venv/bin/python -m twine upload --help | grep -q -- '--dry-run' \
  && /tmp/bp-cut-venv/bin/python -m twine upload --repository pypi \
       --non-interactive --dry-run /tmp/bp-cut-dist/*
```

`twine check` is the required no-upload dry-run. A live `twine upload`
without an authorized human is forbidden. If `--dry-run` is missing from
your twine, do not invent a substitute upload.

Record a receipt (hashes only):

```sh
(cd /tmp/bp-cut-dist && shasum -a 256 * > /tmp/bp-cut-receipt.sha256)
cat /tmp/bp-cut-receipt.sha256
```

Confirm the receipt names:

- `protocolcity_blueprint-0.1.50.tar.gz`
- `protocolcity_blueprint-0.1.50-py3-none-any.whl`
- `protocolcity-0.1.50.tar.gz`
- `protocolcity-0.1.50-py3-none-any.whl`

and that `scripts/check_release_artifacts.py` printed clean.

## Live upload (human, after dry-run receipt)

Only after the dry-run receipt is filed and a person with PyPI ownership
authorizes the cut:

```sh
# Human terminal. Token via keyring / prompt — never echo, never commit.
/tmp/bp-cut-venv/bin/python -m twine upload --repository pypi /tmp/bp-cut-dist/*
```

Then poll `https://pypi.org/pypi/protocolcity-blueprint/json` until
`releases["0.1.50"]` lists the sdist. Confirm sha256 matches the receipt
exactly. Repeat for `protocolcity`. If the uploaded digest differs, do
not update Homebrew — rebuild was not the receipt artifact.

Homebrew tap formula URL/sha is filled **after** this confirmation.
See protocolcity/homebrew-tap (companion formula bump).
