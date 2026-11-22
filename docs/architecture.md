# Architecture

wxhub is a single-host JupyterHub deployment for a controlled teaching or research pilot.

## Components

| Component | Responsibility |
|---|---|
| JupyterHub | Authentication, routing, lifecycle, and Hub database |
| NativeAuthenticator | Local signup and passwords for the configured allow-list |
| DockerSpawner | One isolated single-user container per account |
| Single-user image | JupyterLab and the weather-analysis Python stack |
| ConfigurableHTTPProxy | Routes `/user/<username>/` to its container |
| Docker volumes | Persist Hub state and each user's workspace |
| Host bind mounts | Expose templates and weather data read-only |
| Custom Hub template | Applies configurable meteo@uniparthenope identity and colors |

All containers join `wxhub-net`. JupyterHub is reachable as `jupyterhub` on that network, and
DockerSpawner uses internal container addresses.

## Storage model

| Data | Source | Container destination | Access |
|---|---|---|---|
| User workspace | `jupyterhub-user-{username}` | `/home/jovyan/work` | read/write |
| Templates | `WXHUB_TEMPLATES_HOST` | `/home/jovyan/templates` | read-only |
| Raw sensors | `WXHUB_SENSORS_HOST` | `/home/jovyan/data/raw/sensors` | read-only |
| Raw models | `WXHUB_MODELS_HOST` | `/home/jovyan/data/raw/models` | read-only |
| Curated data | `WXHUB_CURATED_HOST` | `/home/jovyan/data/curated` | read-only |
| Hub state | `jupyterhub-data` | `/srv/jupyterhub/data` | Hub-only |

Compose mounts are not inherited by spawned containers. DockerSpawner receives absolute host paths
through environment variables and asks the host Docker daemon to mount them directly.

Each user server is limited to 4 GB RAM and 2 CPU cores. These are limits, not reservations. The Hub
controls the host Docker daemon through its socket; user containers do not receive the socket. See
[Security](security.md) for the resulting trust boundary.
