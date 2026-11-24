# Contributor and agent guide

## Scope

These instructions apply to the entire repository.

## Project conventions

- Write source code, comments, documentation, notebook text, UI labels, filenames, and generated
  schema headers in English.
- Preserve the single-host Docker Compose architecture unless explicitly changing orchestrators.
- Never commit credentials, tokens, secrets, downloaded weather data, workspaces, or generated output.
- Keep shared data and templates read-only in spawned user containers.
- Keep host paths configurable through the `LAB_*_HOST` environment variables.
- Pin container bases by tag and digest and pin direct Python dependencies.
- Treat `image/requirements.lock` and `image/IMAGE_ID` as audit snapshots, not portable installers.

## Required validation

Run before every commit:

```bash
./scripts/validate_repo.sh
```

When Dockerfiles, dependencies, or Hub configuration change, also run:

```bash
docker compose build jupyterhub
docker build -t lab-singleuser:check ./image
```

When the WRF workflow changes and data is available, execute it through Papermill and verify
`results.json`, figures, and the Zarr store.

## Documentation and safety

- Update `docs/` with every behavior, configuration, security, or operations change.
- Keep `README.md` task-oriented and place operational detail in `docs/`.
- Keep notebook prose in Markdown cells and clear transient outputs.
- Preserve user volumes and measurement evidence.
- Never run `docker compose down -v` during validation; it destroys persistent state.
- Do not silently change the data source, geographic domain, or scientific derivation.
- Never push a `v*` tag casually: release tags publish both container images to GHCR.
