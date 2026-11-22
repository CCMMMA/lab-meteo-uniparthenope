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
# [NUOVO] segreto dei cookie nel volume persistente: le sessioni sopravvivono al riavvio
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

# [MODIFICATO] aggiunti due utenti di prova per i test T02 e T16
c.Authenticator.allowed_users = {'admin', 'aulainfo', 'utente1', 'utente2'}

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

# I percorsi a sinistra sono percorsi dell'HOST (la VM), perché i mount
# li esegue il Docker Engine dell'host, non il container dell'Hub. Sono passati
# da Compose per evitare di legare la configurazione a uno specifico utente host.
# Le aree condivise sono in sola lettura ("mode": "ro").
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
