# Review and publish a release

Branch publication, integration, package release, repository visibility and
runtime activation are separate actions. Follow the applicable owner/workspace
authorization. A reviewed source branch does not authorize a package upload.

## Candidate evidence

1. Verify the exact repository, branch and revision. Preserve private histories
   outside the public ancestry; do not publish an old development branch merely
   because its current files are clean.
2. Run the candidate's behavior, template, source-privacy and artifact checks.
   Review findings against the release scope rather than relying on a count.
3. Read current package names/versions/dependencies from `pyproject.toml` and
   compatibility-package metadata. Do not reuse a prior cut's hardcoded version.
4. Build wheel and source archives in a disposable output directory. Inspect
   both their contents and metadata for private runtime data, host paths,
   internal notes, credentials and unintended dependency references.
5. Install the reviewed artifacts outside the checkout and verify the documented
   first journey, diagnostics and data-preserving update/recovery behavior.
6. Record hashes, tests and known limitations. Confirm repository protection and
   secret-scanning settings with current evidence; unavailable access is unknown,
   not proof that a setting is enabled.

Use the repository's existing release-artifact checker and no-upload metadata
validation (`twine check`) where applicable. Historical cut-specific assertions
must be updated and reviewed before validating a new version; do not bypass a
failed guard or silently substitute an upload for a dry run.

## Publication and activation

Publish only the exact reviewed artifacts after release authorization, using
credentials supplied through the authorized secret mechanism. Do not put tokens
in shell arguments, logs or source. Confirm the published artifact digests match
the reviewed receipt before updating downstream installers.

Activation follows [deployment and recovery](DEPLOYMENT.md). Verify the
responding build and selected workspace after activation. Runtime data and
independent engines remain separate from BP's installed package files. Keep
host-specific receipts and operational history outside distributable source.
