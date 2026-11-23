# wxhub

> A reproducible, containerized JupyterHub workspace for weather and marine-data analysis.

[![CI](https://github.com/raffmont/wxhub/actions/workflows/ci.yml/badge.svg)](https://github.com/raffmont/wxhub/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

wxhub gives every authenticated user an isolated JupyterLab server with a ready-to-use scientific
stack: Xarray, Dask, Zarr, NetCDF4, cfgrib, Cartopy, Voilà, and Papermill. Shared source data and
notebook templates are mounted read-only; each user's work lives in a persistent Docker volume.
Anonymous visitors receive a Colab-like JupyterLite workspace with thirty editable
meteo@uniparthenope notebooks. Python executes in WebAssembly inside the browser, and each visitor's
files persist only in that browser; anonymous code never runs on the deployment host.

The repository accompanies the Computer Science bachelor thesis *Development and production
deployment of an interactive environment based on Jupyter Notebook* at the University of Naples
“Parthenope” (author: Mariano Pio Stora; supervisor: Prof. Raffaele Montella).

## What you get

- Per-user, persistent JupyterLab containers managed by JupyterHub and DockerSpawner.
- A versioned scientific runtime and an auditable environment snapshot.
- Read-only shared weather data and starter notebooks.
- Thirty anonymous demonstrations: ten introductory API examples, five model analyses, five
  live-instrument analyses, and ten transparent artificial-intelligence examples.
- A reproducible WRF Campania case study with maps, time series, Zarr output, and a Voilà dashboard.
- Scripts for data acquisition, headless execution, permission checks, and performance measurements.
- Continuous validation of code, notebooks, documentation links, Compose configuration, and images.
- Tag-driven delivery of versioned Hub and single-user images to GitHub Container Registry.

## Architecture

```text
browser ──► JupyterHub :8000 ──► DockerSpawner ──► jupyter-<username>
                    │                                  │
                    ├── persistent Hub state           ├── persistent /home/jovyan/work
                    ├── Docker socket                  └── read-only data and templates
                    └── /services/demos/ ──► browser-based JupyterLite lab
```

See [Architecture](docs/architecture.md) for the complete component and storage model.

## Quick start

### Requirements

- Linux x86_64 (the production target)
- Docker Engine 24+ with Docker Compose v2
- At least 4 GB free RAM and 15 GB free disk space
- TCP port 8000 available

### Install

```bash
git clone https://github.com/raffmont/wxhub.git
cd wxhub
sudo mkdir -p /opt/weather/data/raw/sensors /opt/weather/data/raw/models /opt/weather/data/curated
sudo chown -R "$USER" /opt/weather/data
docker build -t wxhub-singleuser:latest ./image
docker compose up -d --build
docker compose logs -f jupyterhub
```

Open `http://localhost:8000`, sign up as `admin`, and start the server. The deployment intentionally
uses HTTP for a trusted pilot network; put it behind TLS before exposing it publicly.

Opening `http://localhost:8000/` sends anonymous visitors directly to the notebook gallery without
a login step. Authenticated users can sign in explicitly at `/hub/login`. The demonstrations execute
live requests against `https://api.meteo.uniparthenope.it` from a browser-isolated Pyodide kernel;
the resource-limited Nginx container serves only static files.

Host paths can be changed without editing source files:

```bash
export WXHUB_TEMPLATES_HOST="$PWD/templates"
export WXHUB_SENSORS_HOST=/srv/weather/raw/sensors
export WXHUB_MODELS_HOST=/srv/weather/raw/models
export WXHUB_CURATED_HOST=/srv/weather/curated
docker compose up -d
```

For production preparation, user management, upgrades, backups, and troubleshooting, follow the
[Deployment guide](docs/deployment.md) and [Operations guide](docs/operations.md).

## Reproduce the WRF case study

The analysis covers the 13–17 November 2026 severe-weather event in Campania using hourly WRF d03
output from the meteo@uniparthenope OPeNDAP service (~3 km resolution, IODL 2.0).

```bash
sudo docker run --rm --entrypoint python -u 1000 \
  -v /opt/weather/data/raw/models:/out -v "$PWD/scripts":/scripts:ro \
  wxhub-singleuser:latest /scripts/fetch_wrf_d03.py \
  --start 2026-11-13 --days 5 --out /out/wrf5_d03
```

Copy `notebooks/` into `~/work/notebooks` from JupyterLab, then run
`wrf_campania_case_study.ipynb`. For a headless run inside the user server:

```bash
./scripts/run_papermill.sh 2026-11-15T00 2026-11-15T23 Salerno
```

Open the dashboard at
`http://<host>:8000/user/<username>/voila/render/notebooks/wrf_voila_dashboard.ipynb`.
Data lineage, checksums, outputs, and limitations are documented in
[Reproducibility](docs/reproducibility.md).

## Repository map

| Path | Purpose |
|---|---|
| `jupyterhub/` | Hub image and DockerSpawner configuration |
| `image/` | Versioned single-user scientific image and environment snapshot |
| `notebooks/` | Executable WRF analysis and Voilà dashboard |
| `demos/` | JupyterLite image and thirty browser-executed API, model, instrument, and AI notebooks |
| `templates/` | Read-only starter notebooks |
| `scripts/` | Acquisition, validation, execution, and benchmark utilities |
| `measurements/` | Committed pilot benchmark evidence |
| `docs/` | Architecture, deployment, operations, security, and reproducibility guides |
| `.github/workflows/` | Continuous integration configuration |

Pushing a tag such as `v1.0.0` runs the release workflow and publishes versioned images as
`ghcr.io/raffmont/wxhub-jupyterhub:<tag>` and `ghcr.io/raffmont/wxhub-singleuser:<tag>` with
provenance and SBOM attestations.

## Validate a checkout

```bash
./scripts/validate_repo.sh
docker compose build jupyterhub
docker build -t wxhub-singleuser:check ./image
```

The first command is fast and offline. Image builds require network access. See
[Contributing](docs/contributing.md).

## Security scope

This is a single-host pilot. It mounts the Docker socket into the Hub, serves plain HTTP by default,
uses locally provisioned accounts from a fixed allow-list, and does not stop idle servers. Public
self-signup is disabled by default. Do not expose it directly to the internet without a trusted DNS
name and HTTPS. Review [Security](docs/security.md) first.

## License and data attribution

Source code is licensed under the [MIT License](LICENSE). WRF data is provided by
meteo@uniparthenope under the Italian Open Data License 2.0; data is not redistributed here.
