# Deployment guide

## Prepare the host

Install Docker Engine and Compose v2, then create the data directories:

```bash
sudo install -d -o "$USER" -g "$(id -gn)" \
  /opt/weather/data/raw/sensors /opt/weather/data/raw/models /opt/weather/data/curated
```

Clone the repository. Optional `WXHUB_*_HOST` overrides must be absolute paths because the host
Docker daemon, not the Hub container, resolves them.

## Build, validate, and start

```bash
./scripts/validate_repo.sh
docker build -t wxhub-singleuser:latest ./image
docker compose build jupyterhub
docker compose up -d
docker compose ps
docker compose logs -f jupyterhub
```

Wait for `JupyterHub is now running` and open port 8000. Only names in
`c.Authenticator.allowed_users` can log in. Public self-signup is disabled by default; temporarily
set `WXHUB_ENABLE_SIGNUP=true` while provisioning an allowed account, then unset it and recreate
the Hub. New accounts require administrator approval unless `WXHUB_OPEN_SIGNUP=true`; avoid open
signup on an internet-facing deployment. Edit the allow-list before onboarding real users.

For internet-facing use, terminate HTTPS at a maintained reverse proxy on a trusted DNS name and
set `WXHUB_PUBLIC_HOST` to that `https://` URL. A branded login form on a raw HTTP IP address can
still trigger browser phishing protection and exposes passwords in transit.

## Acceptance checks

1. Start a user server and open JupyterLab.
2. Copy a template into `/home/jovyan/work` and run it with suitable input data.
3. Run `scripts/test_permissions.sh` from a repository copy available to the user server.
4. Restart the user server and confirm workspace persistence.
5. Restart the Hub and confirm its database and sessions persist.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `WXHUB_PORT` | `8000` | Host TCP port published for JupyterHub |
| `WXHUB_PUBLIC_HOST` | `http://localhost:8000` | Public base URL advertised by the deployment |
| `DOCKER_NOTEBOOK_IMAGE` | `wxhub-singleuser:latest` | Spawned user image |
| `WXHUB_TEMPLATES_HOST` | `${PWD}/templates` | Host template directory |
| `WXHUB_SENSORS_HOST` | `/opt/weather/data/raw/sensors` | Raw sensor directory |
| `WXHUB_MODELS_HOST` | `/opt/weather/data/raw/models` | Raw model directory |
| `WXHUB_CURATED_HOST` | `/opt/weather/data/curated` | Curated data directory |
| `WXHUB_ENABLE_SIGNUP` | `false` | Expose NativeAuthenticator self-registration; enable only during controlled provisioning |
| `WXHUB_OPEN_SIGNUP` | `false` | Authorize new registrations without administrator approval |
| `WXHUB_BRAND_NAME` | `meteo@uniparthenope WxHub` | Product name shown in Hub pages and the browser title |
| `WXHUB_BRAND_SUBTITLE` | `Weather and marine data workspace` | Short identity line in the Hub navigation |
| `WXHUB_BRAND_PRIMARY` | `#1f4e79` | Six-digit primary theme color |
| `WXHUB_BRAND_SECONDARY` | `#2a91eb` | Six-digit link and focus color |
| `WXHUB_BRAND_ACCENT` | `#181c63` | Six-digit navigation-gradient accent color |
| `WXHUB_BRAND_SITE_URL` | `https://meteo.uniparthenope.it` | Forecast-site navigation link |
| `WXHUB_BRAND_NETWORK_URL` | `https://network.meteo.uniparthenope.it` | Sensor-network navigation link |

The default palette is derived from the public meteo@uniparthenope forecast and sensor-network
sites. Override the variables in `.env`; color values must use `#RRGGBB`, and link values must be
absolute HTTP or HTTPS URLs. Recreate the Hub container after changes.

## Upgrade and rollback

Back up `jupyterhub-data` and record image IDs. Build new images with versioned tags, validate them,
then update `DOCKER_NOTEBOOK_IMAGE`. Roll back by restoring the previous tag and restarting the Hub.
Never delete per-user volumes during an upgrade.

## Release delivery

Push a semantic version tag such as `v1.0.0` after CI passes. The release workflow builds both
images and publishes tag- and commit-addressable variants to GitHub Container Registry with
provenance and SBOM attestations. Package visibility and retention are managed in the repository's
GitHub package settings.
