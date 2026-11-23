# Architecture

wxhub is a single-host JupyterHub deployment for a controlled teaching or research pilot.

## Components

| Component | Responsibility |
|---|---|
| JupyterHub | Authentication, routing, lifecycle, and Hub database |
| NativeAuthenticator | Local signup and passwords for the configured allow-list |
| DockerSpawner | One isolated single-user container per account |
| Single-user image | JupyterLab and the weather-analysis Python stack |
| Anonymous notebook lab | Serves JupyterLite and a Pyodide browser kernel |
| ConfigurableHTTPProxy | Routes `/user/<username>/` to its container |
| Docker volumes | Persist Hub state and each user's workspace |
| Host bind mounts | Expose templates and weather data read-only |
| Custom Hub template | Applies configurable meteo@uniparthenope identity and colors |

All containers join `wxhub-net`. JupyterHub is reachable as `jupyterhub` on that network, and
DockerSpawner uses internal container addresses. The Hub proxy routes `/services/demos/` to the
static JupyterLite service. Anonymous visitors get a JupyterLab-style editor, file browser, uploads,
downloads, and a Pyodide Python kernel without creating a Hub user.

The service container is only an Nginx static-file server with a read-only root filesystem, 256 MB
RAM, 0.5 CPU, and 64-process limits. Notebook execution and uploaded files remain in the visitor's
browser. Browser code can call the public meteo API because it permits cross-origin requests, but
cannot access the host, Docker socket, authenticated user volumes, or server-side data mounts.
The anonymous lab injects the same WxHub palette, typography, and gradient navigation used by the
Hub login page. Its thirty bundled notebooks cover API discovery, forecasts, model products, live
instrument observations, and transparent artificial-intelligence methods.

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
