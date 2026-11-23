# wxhub

> A reproducible, containerized JupyterHub workspace for weather and marine-data analysis.

[![CI](https://github.com/raffmont/wxhub/actions/workflows/ci.yml/badge.svg)](https://github.com/raffmont/wxhub/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

wxhub follows a Colab-style, two-tier model. Anonymous visitors land on a gallery of thirty
meteo@uniparthenope notebooks and run them with one click in a JupyterLite lab whose Python kernel
executes in WebAssembly inside the browser; their code never runs on the deployment host. Signed-in
members connect to a persistent, isolated JupyterLab server with Xarray, Dask, Zarr, NetCDF4,
cfgrib, Cartopy, Voilà, and Papermill, and with **strictly read-only** access to the operational
model archive (WRF, ROMS, WaveWatch III, WaComM, AIquam) and the weather-station network.

The interface follows the visual identity of [meteo.uniparthenope.it](https://meteo.uniparthenope.it)
and [network.meteo.uniparthenope.it](https://network.meteo.uniparthenope.it). The service is designed
for GDPR compliance and WCAG 2.1 AA accessibility, supports academic single sign-on (Microsoft Entra
ID or Google Workspace) besides approval-gated local accounts, and provides roles (administrator,
instructor, researcher, user, student) with an administration dashboard.

The repository accompanies the Computer Science bachelor thesis *Development and production
deployment of an interactive environment based on Jupyter Notebook* at the University of Naples
“Parthenope” (author: Mariano Pio Stora; supervisor: Prof. Raffaele Montella).

## What you get

- A public notebook gallery and browser lab that need no account.
- Per-user, persistent JupyterLab containers managed by JupyterHub and DockerSpawner, hardened with
  no capabilities, `no-new-privileges`, and a spawn-time check that every shared mount is read-only.
- Roles with resource tiers, local accounts or academic SSO, and a platform dashboard for accounts,
  data-mount audit, archive freshness, privacy requests, and security posture.
- Privacy notice, *My data* self-service export and requests, and an accessibility statement.
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
browser ──► JupyterHub :WXHUB_PORT ──► DockerSpawner ──► <instance>-user-<username>
                    │                                      │
                    ├── Hub state, roles, wxhub_ext pages  ├── persistent ~/work
                    ├── Docker socket                      ├── read-only ~/data/opendap, ~/data/network
                    └── /services/demos/ ──► gallery + browser-based JupyterLite lab
```

See [Architecture](docs/architecture.md) for components and storage, and
[Design rationale](docs/design-rationale.md) for the scientific and engineering reasoning with
references.

## Quick start

### Requirements

- Linux x86_64 (the production target)
- Docker Engine 24+ with Docker Compose v2
- At least 4 GB free RAM and 15 GB free disk space
- TCP port 8000 available

### Install

```bash
git clone https://github.com/CCMMMA/lab-meteo-uniparthenope.git
cd lab-meteo-uniparthenope
sudo mkdir -p /opt/weather/data/raw/sensors /opt/weather/data/raw/models /opt/weather/data/curated
sudo chown -R "$USER" /opt/weather/data
docker compose --profile images build singleuser
docker compose up -d --build
docker compose logs -f jupyterhub
```

Create the administrator account (the password is read from standard input):

```bash
read -rs PASSWORD
printf '%s\n' "$PASSWORD" | docker compose exec -T jupyterhub \
  python -m wxhub_ext.manage_users create admin --role admin
```

Open `http://localhost:8000/` for the public gallery and *Sign in* for your server. Point
`WXHUB_OPENDAP_HOST` and `WXHUB_NETWORK_HOST` at the operational archives to expose them read-only.
The deployment uses HTTP for a trusted pilot network; put it behind TLS before exposing it publicly.

Configuration lives in an untracked `.env` file; see the [Deployment guide](docs/deployment.md)
for every variable, [Identity and roles](docs/identity-and-roles.md) for accounts and SSO, and the
[Operations guide](docs/operations.md) for backups, duties, and troubleshooting.

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
| `jupyterhub/` | Hub image, DockerSpawner configuration, templates, and logo |
| `jupyterhub/wxhub_ext/` | Hub extension: settings, SSO selection, admin/privacy/account pages, user CLI |
| `image/` | Versioned single-user scientific image and environment snapshot |
| `notebooks/` | Executable WRF analysis and Voilà dashboard |
| `demos/` | Gallery generator, JupyterLite image, and thirty browser-executed notebooks |
| `templates/` | Read-only starter notebooks, including local archive access |
| `scripts/` | Acquisition, validation, execution, and benchmark utilities |
| `measurements/` | Committed pilot benchmark evidence |
| `docs/` | Architecture, rationale, deployment, operations, identity, security, privacy, accessibility, and reproducibility |
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

## Security, privacy, and accessibility

This is a single-host service. The Hub holds the Docker socket and serves plain HTTP unless a TLS
proxy is added; user servers are unprivileged, idle servers are culled, and shared data is
read-only by construction. Public self-signup is disabled by default. Do not expose the service to
the internet without a trusted DNS name and HTTPS. Review [Security](docs/security.md),
[Privacy and GDPR](docs/privacy-gdpr.md), and [Accessibility](docs/accessibility.md).

## License and data attribution

Source code is licensed under the [MIT License](LICENSE). WRF data is provided by
meteo@uniparthenope under the Italian Open Data License 2.0; data is not redistributed here.
