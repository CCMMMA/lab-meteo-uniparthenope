import os
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
c.JupyterHub.template_paths = [
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/"
]

c.NativeAuthenticator.open_signup = True
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
