# Contributing

1. Create a focused branch from `main`.
2. Make one coherent change and update its documentation.
3. Run `./scripts/validate_repo.sh` and build affected images.
4. Execute the case study with representative data after scientific changes.
5. Commit with an imperative message and open a pull request.

Follow [AGENTS.md](../AGENTS.md). Pin every direct dependency. Rebuild and exercise the image before
refreshing `scripts/freeze_env.sh` output. Keep notebook prose in Markdown cells, code executable,
and transient output cleared. Full WRF execution is excluded from CI because input is large and
remotely hosted.

`./scripts/validate_repo.sh` also runs `scripts/test_lab_ext.py` (offline tests of the Hub
extension) and rejects any Compose mount of a `LAB_*_HOST` path without `:ro`. Changes to Hub
pages must keep the accessibility measures in [Accessibility](accessibility.md); changes that
collect or expose personal data must update [Privacy and GDPR](privacy-gdpr.md) and the notice in
`jupyterhub/templates/lab_privacy.html`. Cite only peer-reviewed sources with verified DOIs in
[Design rationale](design-rationale.md).

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main`, on pull requests, and on manual dispatch.
It runs `./scripts/validate_repo.sh`, then builds and smoke-tests the Hub and single-user images.
`.github/workflows/release.yml` publishes both images on `v*` tags. Every action is pinned to a
full commit SHA, with the release in a trailing comment; pinned actions run on the Node.js 24
runtime. To upgrade an action, resolve the new release tag to its commit, check that its
`action.yml` still accepts the inputs the workflows use, and run CI manually before merging:

```bash
gh workflow run ci.yml --ref main
```

The repository is a GitHub fork. GitHub disables workflows on new forks until a maintainer enables
them under the Actions tab; if pushes to `main` start no CI run, check that setting first.

Public demos are generated, not edited independently. Update `scripts/build_demo_notebooks.py`, run
it, and commit the resulting thirty output-free files. If the catalog size changes, update the
validator, `demos/README.md`, and the deployment acceptance count together. Branding changes must
cover `jupyterhub/templates/page.html`, `demos/build_gallery.py`, and `demos/lab.css`; bump the published stylesheet
asset name when an existing JupyterLite service-worker cache would otherwise retain old CSS.

AI demos must keep training and inference inspectable, state their intended use and limitations,
use only documented meteo@uniparthenope sources, and avoid hidden datasets, credentials, remote AI
providers, or claims of operational forecast skill without appropriate independent validation.
