# Deployment guide

## Prepare the host

Install Docker Engine 24+ and Compose v2 on Linux x86_64. Decide the instance name, published
port, and data paths, and write them to an untracked `.env` file next to `docker-compose.yml`:

```bash
umask 077
cat > .env <<'EOF'
WXHUB_INSTANCE=labmeteo
WXHUB_PORT=8290
WXHUB_PUBLIC_HOST=http://<host>:8290
WXHUB_SINGLEUSER_IMAGE=labmeteo-singleuser:latest
WXHUB_TEMPLATES_HOST=/home/<user>/devel/lab-meteo-uniparthenope/templates
WXHUB_OPENDAP_HOST=/storage/ccmmma/prometeo/data/opendap
WXHUB_NETWORK_HOST=/storage/ccmmma/prometeo/data/network
WXHUB_SENSORS_HOST=/home/<user>/devel/lab-meteo-uniparthenope-data/raw/sensors
WXHUB_MODELS_HOST=/home/<user>/devel/lab-meteo-uniparthenope-data/raw/models
WXHUB_CURATED_HOST=/home/<user>/devel/lab-meteo-uniparthenope-data/curated
WXHUB_ADMIN_USERS=admin
EOF
```

Every `*_HOST` value must be an absolute, existing path: the host Docker daemon resolves it, and a
missing path would be created empty by Docker. Create the local mirror directories first. Choose a
`WXHUB_INSTANCE` that no other deployment on the host uses; it scopes container, network, volume,
and image names (see [Architecture](architecture.md#instances)).

## Build, validate, and start

```bash
./scripts/validate_repo.sh
docker compose --profile images build singleuser
docker compose build jupyterhub demos
docker compose up -d
docker compose ps
docker compose logs -f jupyterhub
```

Wait for `JupyterHub is now running`. Never run `docker compose down -v`: it deletes the Hub
database and cookie secret.

## Provision the first accounts

With local accounts (the default), create the administrator and any initial users from the host.
Generate passwords, store them only in a mode-600 file outside Git, and hand them over through a
secure channel:

```bash
mkdir -p .secrets && chmod 700 .secrets
PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')
printf '%s\n' "$PASSWORD" | docker compose exec -T jupyterhub \
  python -m wxhub_ext.manage_users create admin --role admin
printf 'admin %s\n' "$PASSWORD" >> .secrets/credentials.txt && chmod 600 .secrets/credentials.txt
```

Repeat with `--role user|student|researcher|instructor` for other accounts. Ask every user to change
the initial password at `/change-password`. For Microsoft or Google sign-in, follow
[Identity and roles](identity-and-roles.md) instead.

## Acceptance checks

1. `/` sends anonymous visitors to the gallery at `/services/demos/`, which lists thirty notebooks
   in four sections; a card opens its notebook in the lab and a Pyodide kernel starts.
2. `/login` shows the branded sign-in card; signing in as a regular user reaches *My runtime*.
3. Start a server, open a terminal, and run `scripts/test_permissions.sh`: every shared path must
   report `ro`, `~/work` `rw`, and both privilege checks `PASSED`.
4. Run `templates/local_archives.ipynb` (copied to `~/work`): it reads a WRF file and a station CSV
   and reports that the archive is read-only.
5. As administrator, open `/dashboard`: the live audit reports no writable shared mount and
   the archive tables show recent days. A regular user receives HTTP 403 there.
6. Restart the user server and the Hub; confirm workspace files and sessions persist.
7. Open `/privacy` and `/accessibility` without signing in.
8. Old links such as `/hub/login` redirect to `/login`; no page shows a `/hub/` URL, and a user
   server opens at `/user/<name>/lab` with working kernels (see [Architecture](architecture.md#clean-urls-and-the-front-proxy)).
9. Run one model, one live-instrument, and one AI notebook in the gallery; an explicit upstream
   timeout message is acceptable, an unhandled traceback is not.

For internet-facing use, terminate HTTPS at a maintained reverse proxy, set `WXHUB_PUBLIC_HOST` to
the `https://` URL, and set `WXHUB_BIND_ADDRESS=127.0.0.1`. See [Security](security.md).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `WXHUB_INSTANCE` | `wxhub` | Prefix for containers, network, user containers/volumes, and the gallery image |
| `WXHUB_PORT` | `8000` | Host TCP port of the front proxy (`web`), the only published port |
| `WXHUB_BIND_ADDRESS` | `0.0.0.0` | Host address the port binds to; use `127.0.0.1` behind an HTTPS proxy |
| `WXHUB_PUBLIC_HOST` | `http://localhost:8000` | Public base URL; `https://` enables secure cookies, HSTS, and SSO callbacks |
| `WXHUB_SINGLEUSER_IMAGE` | `wxhub-singleuser:latest` | Image spawned for users |
| `WXHUB_TEMPLATES_HOST` | `${PWD}/templates` | Starter notebooks (read-only) |
| `WXHUB_OPENDAP_HOST` | empty | Operational model archive root (read-only); omitted when empty |
| `WXHUB_NETWORK_HOST` | empty | Weather-station network root (read-only); omitted when empty |
| `WXHUB_SENSORS_HOST` | `/opt/weather/data/raw/sensors` | Raw sensor mirror (read-only) |
| `WXHUB_MODELS_HOST` | `/opt/weather/data/raw/models` | Raw model mirror used by the WRF case study (read-only) |
| `WXHUB_CURATED_HOST` | `/opt/weather/data/curated` | Curated products (read-only) |
| `WXHUB_AUTHENTICATOR` | `native` | `native`, `azuread`, or `google` |
| `WXHUB_ADMIN_USERS` | `admin` | Comma-separated administrators |
| `WXHUB_ALLOWED_USERS` | empty | Optional explicit allow-list (otherwise approval or IdP restriction applies) |
| `WXHUB_STUDENTS`, `WXHUB_RESEARCHERS`, `WXHUB_INSTRUCTORS` | empty | Seed role groups at start-up |
| `WXHUB_ENABLE_SIGNUP` | `false` | Expose the local sign-up form (requests need approval) |
| `WXHUB_OPEN_SIGNUP` | `false` | Approve sign-ups automatically; avoid on reachable hosts |
| `WXHUB_OAUTH_CLIENT_ID`, `WXHUB_OAUTH_CLIENT_SECRET` | empty | SSO application credentials |
| `WXHUB_OAUTH_TENANT_ID` | empty | Entra ID tenant (required for `azuread`) |
| `WXHUB_OAUTH_USERNAME_CLAIM` | `upn` | Entra ID claim used as username |
| `WXHUB_OAUTH_HOSTED_DOMAINS` | empty | Google Workspace domains (required for `google`) |
| `WXHUB_OAUTH_ALLOW_ALL` | `true` | Allow every member of the tenant/domain |
| `WXHUB_MEM_LIMIT`, `WXHUB_CPU_LIMIT` | `4G`, `2` | User and instructor tier |
| `WXHUB_STUDENT_MEM_LIMIT`, `WXHUB_STUDENT_CPU_LIMIT` | `2G`, `1` | Student tier |
| `WXHUB_RESEARCHER_MEM_LIMIT`, `WXHUB_RESEARCHER_CPU_LIMIT` | `8G`, `4` | Researcher and administrator tier |
| `WXHUB_IDLE_TIMEOUT` | `3600` | Seconds before idle servers stop; `0` disables culling |
| `WXHUB_COOKIE_MAX_AGE_DAYS` | `7` | Session cookie lifetime |
| `WXHUB_RETENTION_DAYS` | `365` | Inactivity period after which accounts are reviewed |
| `WXHUB_PRIVACY_CONTROLLER` | University of Naples “Parthenope” | Controller named in the privacy notice |
| `WXHUB_PRIVACY_CONTACT` | privacy@uniparthenope.it, privacy@pec.uniparthenope.it (University Privacy Office) | Privacy contact in the notice |
| `WXHUB_DPO_CONTACT` | dpo.privacy@uniparthenope.it | University DPO in the notice |
| `WXHUB_ACCESSIBILITY_CONTACT` | meteo@uniparthenope.it or the University accessibility page https://www.uniparthenope.it/Portale-Ateneo/accessibilita | Feedback channel in the accessibility statement |
| `WXHUB_BRAND_NAME`, `WXHUB_BRAND_SUBTITLE` | lab.meteo@uniparthenope; Weather and marine data workspace | Identity text |
| `WXHUB_BRAND_PRIMARY`, `WXHUB_BRAND_SECONDARY`, `WXHUB_BRAND_ACCENT` | `#1f4e79`, `#2a91eb`, `#181c63` | Palette shared with the meteo@uniparthenope portals |
| `WXHUB_BRAND_SITE_URL`, `WXHUB_BRAND_NETWORK_URL` | meteo and network portal URLs | Navigation links |
| `METEO_API_BASE_URL` | `https://api.meteo.uniparthenope.it` | API base URL passed to user servers |

Colours must use `#RRGGBB`; the light-mode link colour is the primary colour so that link text
keeps at least 4.5:1 contrast. The gallery and lab share the default palette through
`demos/wxhub.css` (published as `lab-meteo-v4.css`; bump the name when changing it so that browser
service-worker caches refresh). Recreate the affected containers after configuration changes.

## Upgrade and rollback

Back up `jupyterhub-data` and record image IDs. Build new images with versioned tags, validate them,
then update `WXHUB_SINGLEUSER_IMAGE` and recreate the Hub. Roll back by restoring the previous tag.
Never delete per-user volumes during an upgrade. Changing `WXHUB_INSTANCE` on an existing deployment
changes volume names; migrate volumes first.

## Release delivery

Push a semantic version tag such as `v1.0.0` after CI passes. The release workflow builds both
images and publishes tag- and commit-addressable variants to GitHub Container Registry with
provenance and SBOM attestations.
