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

Wait for `JupyterHub is now running`, open port 8000, and register `admin`. Only names in
`c.Authenticator.allowed_users` can log in. Edit that set before onboarding real users.

## Acceptance checks

1. Start a user server and open JupyterLab.
2. Copy a template into `/home/jovyan/work` and run it with suitable input data.
3. Run `scripts/test_permissions.sh` from a repository copy available to the user server.
4. Restart the user server and confirm workspace persistence.
5. Restart the Hub and confirm its database and sessions persist.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DOCKER_NOTEBOOK_IMAGE` | `wxhub-singleuser:latest` | Spawned user image |
| `WXHUB_TEMPLATES_HOST` | `${PWD}/templates` | Host template directory |
| `WXHUB_SENSORS_HOST` | `/opt/weather/data/raw/sensors` | Raw sensor directory |
| `WXHUB_MODELS_HOST` | `/opt/weather/data/raw/models` | Raw model directory |
| `WXHUB_CURATED_HOST` | `/opt/weather/data/curated` | Curated data directory |

## Upgrade and rollback

Back up `jupyterhub-data` and record image IDs. Build new images with versioned tags, validate them,
then update `DOCKER_NOTEBOOK_IMAGE`. Roll back by restoring the previous tag and restarting the Hub.
Never delete per-user volumes during an upgrade.
