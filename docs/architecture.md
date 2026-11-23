# Architecture

lab.meteo@uniparthenope is a single-host JupyterHub deployment for teaching and research at meteo@uniparthenope.
The reasoning behind each choice is in [Design rationale](design-rationale.md).

## Components

| Component | Responsibility |
|---|---|
| JupyterHub 5 | Authentication, RBAC, routing, server lifecycle, Hub database |
| Authenticator | Local accounts (NativeAuthenticator) or academic SSO (Microsoft Entra ID, Google) |
| `wxhub_ext` Hub extension | Privacy notice, accessibility statement, *My data* page, platform dashboard |
| DockerSpawner | One isolated, unprivileged container per user |
| Single-user image | JupyterLab and the weather-analysis Python stack |
| Idle culler | Stops servers idle longer than `WXHUB_IDLE_TIMEOUT` |
| Public gallery and lab | Static Nginx service: notebook gallery plus JupyterLite with a Pyodide kernel |
| ConfigurableHTTPProxy | Routes `/user/<username>/` and `/services/demos/` |
| Docker volumes | Persist Hub state and each user's workspace |
| Host bind mounts | Expose templates, operational archives, and station data read-only |
| Custom Hub templates | meteo@uniparthenope identity, accessible layout, sign-in, runtime page |

The extension contributes its pages through the authenticator's `get_handlers` hook, so JupyterHub
itself is not patched and upgrades remain a pinned-version change.

```text
browser ──► :WXHUB_PORT ──► proxy ──┬─► /hub/…            JupyterHub + wxhub_ext pages
                                    ├─► /services/demos/  gallery + JupyterLite (static, browser kernel)
                                    └─► /user/<name>/     <instance>-user-<name> container
                                                           ├─ ~/work            read/write volume
                                                           ├─ ~/data/opendap    read-only model archive
                                                           ├─ ~/data/network    read-only station data
                                                           └─ ~/templates, ~/data/raw, ~/data/curated  read-only
```

## Instances

`WXHUB_INSTANCE` scopes every Docker object so that several deployments can share a host:

| Object | Default instance `wxhub` | Other instance, e.g. `labmeteo` |
|---|---|---|
| Hub / gallery containers | `wxhub-jupyterhub`, `wxhub-demos` | `labmeteo-jupyterhub`, `labmeteo-demos` |
| Network | `wxhub-net` | `labmeteo-net` |
| User containers | `jupyter-<user>` | `labmeteo-user-<user>` |
| User volumes | `jupyterhub-user-<user>` | `labmeteo-user-<user>` |
| Images | `wxhub-demos`, `WXHUB_SINGLEUSER_IMAGE` | `labmeteo-demos`, `WXHUB_SINGLEUSER_IMAGE` |

The default instance keeps the historical names so that existing volumes survive upgrades.

## Storage model

| Data | Host source | Container destination | Access |
|---|---|---|---|
| User workspace | `<prefix>-user-{username}` volume | `/home/jovyan/work` | read/write |
| Templates | `WXHUB_TEMPLATES_HOST` | `/home/jovyan/templates` | read-only |
| Operational model archive | `WXHUB_OPENDAP_HOST` | `/home/jovyan/data/opendap` | read-only |
| Weather-station network | `WXHUB_NETWORK_HOST` | `/home/jovyan/data/network` | read-only |
| Raw sensor mirror | `WXHUB_SENSORS_HOST` | `/home/jovyan/data/raw/sensors` | read-only |
| Raw model mirror | `WXHUB_MODELS_HOST` | `/home/jovyan/data/raw/models` | read-only |
| Curated data | `WXHUB_CURATED_HOST` | `/home/jovyan/data/curated` | read-only |
| Hub state | `jupyterhub-data` | `/srv/jupyterhub/data` | Hub only |

The archive layouts are kept unchanged:

```text
opendap/<model>/<domain>/<archive|history>/YYYY/MM/DD/<model>_<domain>_YYYYMMDDZHHMM.nc
network/it.uniparthenope.meteo.wsN/YYYY/MM/DD/it.uniparthenope.meteo.wsN_YYYYMMDDZHH00.csv
```

Models are `wrf5` (WRF), `rms3` (ROMS), `ww33` (WaveWatch III), `wcm3` (WaComM), and `aiq3`
(AIquam); domains are `d01`, `d02`, `d03`, …; `archive` holds normalized products ready for
plotting and `history` the raw model output.

Compose mounts are not inherited by spawned containers. DockerSpawner receives absolute host paths
through environment variables and asks the host Docker daemon to bind them as `read_only_volumes`.
The Hub also mounts the archive and station roots read-only, solely to report their freshness on
the platform dashboard.

## Roles and resources

| Role | Source | Resource tier | Extra permissions |
|---|---|---|---|
| Administrator | `WXHUB_ADMIN_USERS` or the control panel | researcher (8 GB, 4 CPU) | everything |
| Researcher | group `researchers` | 8 GB, 4 CPU | — |
| Instructor | group `instructors` | 4 GB, 2 CPU | view users and activity, start/stop student servers |
| User | approved account without a role group | 4 GB, 2 CPU | — |
| Student | group `students` | 2 GB, 1 CPU | — |

Limits are configurable (see [Deployment](deployment.md)) and are applied by the Hub's
`pre_spawn_hook` at each server start. See [Identity and roles](identity-and-roles.md).

## Public tier

The gallery at `/services/demos/` is a generated static page that lists the thirty bundled
notebooks and opens each in JupyterLite (`lab/index.html?path=…`). The Nginx container has a
read-only root filesystem and 256 MB / 0.5 CPU / 64-process limits. Notebook execution and uploads
remain in the visitor's browser; the service cannot reach the host, the Docker socket, user volumes,
or the data mounts.
