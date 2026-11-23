# Operations guide

## Routine commands

```bash
docker compose ps
docker compose logs --tail=200 jupyterhub
docker compose logs --tail=200 demos
docker stats
docker volume ls --filter name=jupyterhub-user-
```

Back up `jupyterhub-data`, all `jupyterhub-user-*` volumes, and host data paths from a consistent
snapshot. Restore the Hub SQLite database and cookie secret together. Never use
`docker compose down -v` during normal operations because it deletes persistent state.

## Performance measurements

```bash
export JUPYTERHUB_TOKEN='<administrator token from /hub/token>'
python3 scripts/measure_spawn.py --users 1 --runs 5
python3 scripts/measure_spawn.py --users 5 --runs 3 --keep
./scripts/measure_load.sh 5
```

Output is written under `measurements/`. Committed files are historical pilot evidence, not general
performance guarantees.

## Environment audit

After intentionally rebuilding `wxhub-singleuser:latest`, run `scripts/freeze_env.sh` and review the
diff. The snapshot may contain platform-specific base-image references. The pinned base digest and
`image/requirements.txt` are the portable build inputs.

## Troubleshooting

- **Server does not start:** inspect Hub logs; confirm the user image and `wxhub-net` exist; verify
  every configured host path exists.
- **Data is writable or missing:** run `scripts/test_permissions.sh` in the user server and compare
  `docker inspect jupyter-<username>` with [Architecture](architecture.md).
- **Benchmark returns 403:** use a token created by a member of `admin_users`.
- **Browser reports phishing:** do not bypass the warning; deploy a trusted DNS name and HTTPS as
  described in [Security](security.md). Changing colors or text cannot establish browser trust.
- **Branding is unchanged:** confirm the `jupyterhub/templates` bind mount is present, inspect the
  `WXHUB_BRAND_*` values in `docker compose config`, and recreate the Hub container.
- **Notebook lab returns 503:** confirm `wxhub-demos` is healthy enough to serve port 80, then
  check the Hub service route and `docker compose logs demos`.
- **Root URL shows the login page:** confirm `JupyterHub.default_url` is `/services/demos/` and
  recreate the Hub container. Authenticated users should use `/hub/login` directly.
- **A browser notebook reports an API error:** request the API `/version` endpoint in the same
  browser and inspect its developer console for network, TLS, or CORS errors.
- **Demo changes are missing:** run `python3 scripts/build_demo_notebooks.py`, validate that outputs
  are clear, and recreate the `demos` service.
- **Notebook fails:** confirm the requested WRF range and grid file exist, the output is writable,
  and `manifest.csv` contains no relevant download errors.
