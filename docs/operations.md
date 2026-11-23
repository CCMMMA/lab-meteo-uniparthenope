# Operations guide

## Routine commands

```bash
docker compose ps
docker compose logs --tail=200 jupyterhub
docker compose logs --tail=200 demos
docker stats
docker volume ls --filter name=-user-
docker compose exec -T jupyterhub python -m wxhub_ext.manage_users list
docker compose logs jupyterhub | grep wxhub.audit
```

The platform dashboard (`/hub/wxhub/admin`) is the first place to look: it summarises accounts,
running servers, pending sign-ups, open privacy requests, archive freshness, a live read-only mount
audit, orphaned workspaces, and the security posture.

Back up `jupyterhub-data` (database, cookie secret, privacy-request register), all user workspace
volumes, and the curated data path from a consistent snapshot. The operational archives are owned
by the production chain and are not modified by WxHub. Restore the Hub SQLite database and cookie secret together. Never use
`docker compose down -v` during normal operations because it deletes persistent state.

## Recurring duties

- **Weekly:** review pending sign-ups and open privacy requests; requests must be answered within
  one month (see [Privacy and GDPR](privacy-gdpr.md)).
- **Monthly:** review accounts inactive for longer than `WXHUB_RETENTION_DAYS`, the administrator
  list, and orphaned workspaces.
- **Each release:** run the acceptance checks in [Deployment](deployment.md) and the accessibility
  checks in [Accessibility](accessibility.md).

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
  `docker inspect <instance>-user-<username>` (or `jupyter-<username>` for the default instance)
  with [Architecture](architecture.md). A server whose mount plan would be writable is refused by
  the Hub with `refusing to spawn` in its log.
- **Archive tables on the dashboard are empty:** check `WXHUB_OPENDAP_HOST` and
  `WXHUB_NETWORK_HOST` in `docker compose config` and that the network file system is mounted on
  the host; the inventory is cached for ten minutes.
- **SSO login fails with a redirect error:** the callback URL registered with the identity
  provider must equal `${WXHUB_PUBLIC_HOST}/hub/oauth_callback` and use HTTPS.
- **A user is locked out:** wait ten minutes after five failed attempts, or reset the password with
  `manage_users create <name> --update`.
- **Gallery opens but the lab stays blank:** the JupyterLite root `index.html` must remain the
  generated file; the gallery is published separately as `gallery.html`.
- **Benchmark returns 403:** use a token created by a member of `admin_users`.
- **Browser reports phishing:** do not bypass the warning; deploy a trusted DNS name and HTTPS as
  described in [Security](security.md). Changing colors or text cannot establish browser trust.
- **Branding is unchanged:** confirm the `jupyterhub/templates` bind mount is present, inspect the
  `WXHUB_BRAND_*` values in `docker compose config`, and recreate the Hub container.
- **Notebook lab returns 503:** confirm `wxhub-demos` is healthy enough to serve port 80, then
  check the Hub service route and `docker compose logs demos`.
- **Root URL shows the login page:** confirm `JupyterHub.default_url` is `/services/demos/` and
  recreate the Hub container. Authenticated users use *Sign in* or `/hub/login` directly.
- **A browser notebook reports an API error:** request the API `/version` endpoint in the same
  browser and inspect its developer console for network, TLS, or CORS errors.
- **A live-instrument notebook reports temporary unavailability:** check the public API
  `/v2/weatherreports/latest/json` endpoint. Upstream timeouts do not indicate a JupyterLite
  container failure and the notebook never substitutes a different observation source.
- **An AI notebook has too few samples or constant features:** check its source API response and
  selected area. The notebook intentionally reports data limitations instead of downloading a
  different training dataset or calling an external AI service.
- **Demo changes are missing:** run `python3 scripts/build_demo_notebooks.py`, validate that outputs
  are clear, and recreate the `demos` service.
- **Notebook fails:** confirm the requested WRF range and grid file exist, the output is writable,
  and `manifest.csv` contains no relevant download errors.
