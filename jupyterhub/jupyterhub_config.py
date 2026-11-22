import os
import re
from dockerspawner import DockerSpawner
import nativeauthenticator

c = get_config()

#------------------------------------------------------------------------------
# Core Hub settings
#-----------------------------------------------------------------------------
c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = os.environ.get("HUB_IP", "jupyterhub")
c.JupyterHub.db_url = "sqlite:///data/jupyterhub.sqlite"
# Keep the cookie secret in persistent storage so sessions survive Hub restarts.
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/data/jupyterhub_cookie_secret"

#-----------------------------------------------------------------------------
# Authentication
#------------------------------------------------------------------------------
c.JupyterHub.authenticator_class = "native"


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_color(name, default):
    value = os.environ.get(name, default).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(f"{name} must be a six-digit hexadecimal color")
    return value


def env_http_url(name, default):
    value = os.environ.get(name, default).strip()
    if not re.fullmatch(r"https?://[^\s]+", value):
        raise ValueError(f"{name} must be an HTTP or HTTPS URL")
    return value


c.JupyterHub.template_paths = [
    "/srv/jupyterhub/templates",
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"
]
c.JupyterHub.template_vars = {
    "wxhub_brand_name": os.environ.get("WXHUB_BRAND_NAME", "meteo@uniparthenope WxHub"),
    "wxhub_brand_subtitle": os.environ.get(
        "WXHUB_BRAND_SUBTITLE", "Weather and marine data workspace"
    ),
    "wxhub_brand_primary": env_color("WXHUB_BRAND_PRIMARY", "#1f4e79"),
    "wxhub_brand_secondary": env_color("WXHUB_BRAND_SECONDARY", "#2a91eb"),
    "wxhub_brand_accent": env_color("WXHUB_BRAND_ACCENT", "#181c63"),
    "wxhub_brand_site_url": env_http_url(
        "WXHUB_BRAND_SITE_URL", "https://meteo.uniparthenope.it"
    ),
    "wxhub_brand_network_url": env_http_url(
        "WXHUB_BRAND_NETWORK_URL", "https://network.meteo.uniparthenope.it"
    ),
}

c.NativeAuthenticator.open_signup = env_bool("WXHUB_OPEN_SIGNUP")
c.Authenticator.admin_users = {"admin"}

# Pilot users used by the acceptance and load tests.
c.Authenticator.allowed_users = {'admin', 'aulainfo', 'user1', 'user2'}

#----------------------------------------------------------------------------------
# Spawner
#----------------------------------------------------------------------------------

c.JupyterHub.spawner_class = DockerSpawner

c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]
c.DockerSpawner.network_name = "wxhub-net"
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True

#Jupyterlab as default UI
c.Spawner.default_url = "/lab"

#Resource hints for the pilot
c.Spawner.mem_limit = "4G"
c.Spawner.cpu_limit = 2.0

#Container command suitable for Jupyterhub single-user containers
c.Spawner.cmd = ["jupyterhub-singleuser"]

#Per-user persistent workspace
notebook_dir = "/home/jovyan/work"
c.DockerSpawner.notebook_dir = notebook_dir

# Keys are paths on the Docker HOST because the host engine creates these mounts.
# Compose passes them as environment variables to keep the setup host-independent.
# Shared areas are read-only ("mode": "ro").
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": "/home/jovyan/work",
    os.environ["WXHUB_TEMPLATES_HOST"]: {"bind": "/home/jovyan/templates", "mode": "ro"},
    os.environ["WXHUB_SENSORS_HOST"]: {"bind": "/home/jovyan/data/raw/sensors", "mode": "ro"},
    os.environ["WXHUB_MODELS_HOST"]: {"bind": "/home/jovyan/data/raw/models", "mode": "ro"},
    os.environ["WXHUB_CURATED_HOST"]: {"bind": "/home/jovyan/data/curated", "mode": "ro"},
}

#Useful environment variables inside user servers
c.Spawner.environment = {
    "JUPYTERHUB_SINGLEUSER_APP": "jupyter_server.serverapp.ServerApp",
    "PREFERED_URL_SCHEME": "http",
}

#-------------------------------------------------------------------------------
#User experience
#----------------------------------------------------------------------------------
c.JupyterHub.default_url = "/hub/home"

#------------------------------------------------------------------------------
#Idle cleanup left out for Phase 1 to keep the pilot simple
#---------------------------------------------------------------------------------
