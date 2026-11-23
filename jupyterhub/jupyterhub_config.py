"""JupyterHub configuration for the meteo@uniparthenope WxHub single-host deployment."""

import os
import sys

sys.path.insert(0, "/srv/jupyterhub")

from dockerspawner import DockerSpawner  # noqa: E402
import nativeauthenticator  # noqa: E402

from wxhub_ext import settings as wxsettings  # noqa: E402
from wxhub_ext.auth import build_authenticator_class  # noqa: E402

c = get_config()  # noqa: F821

WX = wxsettings.load()
ASSETS = "/srv/jupyterhub/assets"

#------------------------------------------------------------------------------
# Core Hub settings
#------------------------------------------------------------------------------
c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = os.environ.get("HUB_IP", "jupyterhub")
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"
# Keep the cookie secret in persistent storage so sessions survive Hub restarts.
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/data/jupyterhub_cookie_secret"
c.JupyterHub.logo_file = f"{ASSETS}/logo.png"
c.JupyterHub.default_url = "/services/demos/"
c.JupyterHub.cookie_max_age_days = wxsettings.env_int("WXHUB_COOKIE_MAX_AGE_DAYS", 7, minimum=1)

# Security headers for every Hub page. Hub pages load no third-party resources.
security_headers = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self'; "
        "frame-ancestors 'self'; base-uri 'self'; form-action 'self' https:"
    ),
}
if WX.https:
    security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
c.JupyterHub.tornado_settings = {
    "headers": security_headers,
    "cookie_options": {"SameSite": "Lax", "Secure": WX.https},
}

c.JupyterHub.services = [
    {"name": "demos", "url": f"http://{WX.instance}-demos:80", "display": True},
]
c.JupyterHub.load_roles = []

if WX.idle_timeout > 0:
    c.JupyterHub.services.append({
        "name": "idle-culler",
        "command": [
            sys.executable, "-m", "jupyterhub_idle_culler",
            f"--timeout={WX.idle_timeout}", "--cull-every=300",
        ],
    })
    c.JupyterHub.load_roles.append({
        "name": "idle-culler",
        "description": "Stop servers that have been idle longer than WXHUB_IDLE_TIMEOUT",
        "scopes": ["list:users", "read:users:activity", "read:servers", "delete:servers"],
        "services": ["idle-culler"],
    })

#------------------------------------------------------------------------------
# Roles and groups
#
# administrator – JupyterHub's built-in admin role (WXHUB_ADMIN_USERS)
# instructor    – group "instructors": read-only user oversight and start/stop of student servers
# researcher    – group "researchers": larger resource tier
# student       – group "students": standard teaching tier
# user          – any approved account without a group
#------------------------------------------------------------------------------
c.JupyterHub.load_roles.append({
    "name": "wxhub-instructor",
    "description": "Teaching staff: view users and activity, start and stop student servers",
    "scopes": [
        "self", "admin-ui", "list:users", "read:users", "read:users:activity",
        "read:servers", "list:groups", "read:groups", "servers!group=students",
    ],
    "groups": ["instructors"],
})
c.JupyterHub.load_groups = {
    "students": {"users": wxsettings.env_list("WXHUB_STUDENTS")},
    "researchers": {"users": wxsettings.env_list("WXHUB_RESEARCHERS")},
    "instructors": {"users": wxsettings.env_list("WXHUB_INSTRUCTORS")},
}

RESOURCE_TIERS = {
    "researcher": (os.environ.get("WXHUB_RESEARCHER_MEM_LIMIT", "8G"),
                   float(os.environ.get("WXHUB_RESEARCHER_CPU_LIMIT", "4"))),
    "instructor": (os.environ.get("WXHUB_MEM_LIMIT", "4G"),
                   float(os.environ.get("WXHUB_CPU_LIMIT", "2"))),
    "user": (os.environ.get("WXHUB_MEM_LIMIT", "4G"),
             float(os.environ.get("WXHUB_CPU_LIMIT", "2"))),
    "student": (os.environ.get("WXHUB_STUDENT_MEM_LIMIT", "2G"),
                float(os.environ.get("WXHUB_STUDENT_CPU_LIMIT", "1"))),
}

#------------------------------------------------------------------------------
# Authentication: local accounts or academic single sign-on
#------------------------------------------------------------------------------
c.JupyterHub.authenticator_class = build_authenticator_class(WX, ASSETS)
c.Authenticator.admin_users = set(wxsettings.env_list("WXHUB_ADMIN_USERS") or ["admin"])
explicit_allow = set(wxsettings.env_list("WXHUB_ALLOWED_USERS"))
if explicit_allow:
    c.Authenticator.allowed_users = explicit_allow | c.Authenticator.admin_users
    c.Authenticator.allow_existing_users = True

if WX.authenticator == "native":
    # Accounts are gated by administrator approval (or by `manage_users create`), so every
    # approved local account may log in.
    if not explicit_allow:
        c.Authenticator.allow_all = True
    c.NativeAuthenticator.enable_signup = wxsettings.env_bool("WXHUB_ENABLE_SIGNUP")
    c.NativeAuthenticator.open_signup = wxsettings.env_bool("WXHUB_OPEN_SIGNUP")
    c.NativeAuthenticator.minimum_password_length = 12
    c.NativeAuthenticator.check_common_password = True
    c.NativeAuthenticator.allowed_failed_logins = 5
    c.NativeAuthenticator.seconds_before_next_try = 600
    # Data minimisation: do not collect e-mail addresses at signup.
    c.NativeAuthenticator.ask_email_on_signup = False
else:
    oauth = c.AzureAdOAuthenticator if WX.authenticator == "azuread" else c.GoogleOAuthenticator
    oauth.client_id = wxsettings.env_str("WXHUB_OAUTH_CLIENT_ID")
    oauth.client_secret = wxsettings.env_str("WXHUB_OAUTH_CLIENT_SECRET")
    oauth.oauth_callback_url = f"{WX.public_host}/hub/oauth_callback"
    if not (oauth.client_id and oauth.client_secret):
        raise ValueError("WXHUB_OAUTH_CLIENT_ID and WXHUB_OAUTH_CLIENT_SECRET are required for SSO")
    if WX.authenticator == "azuread":
        tenant = wxsettings.env_str("WXHUB_OAUTH_TENANT_ID")
        if not tenant or tenant in {"common", "organizations", "consumers"}:
            raise ValueError("WXHUB_OAUTH_TENANT_ID must name the university's Entra ID tenant")
        c.AzureAdOAuthenticator.tenant_id = tenant
        c.AzureAdOAuthenticator.username_claim = wxsettings.env_str(
            "WXHUB_OAUTH_USERNAME_CLAIM", "upn"
        )
        c.AzureAdOAuthenticator.login_service = "Microsoft (university account)"
    else:
        domains = wxsettings.env_list("WXHUB_OAUTH_HOSTED_DOMAINS")
        if not domains:
            raise ValueError("WXHUB_OAUTH_HOSTED_DOMAINS is required for Google sign-in")
        c.GoogleOAuthenticator.hosted_domain = domains
        c.GoogleOAuthenticator.login_service = "Google (university account)"
    # The identity provider restricts sign-in to the institution's tenant or hosted domains.
    if not explicit_allow:
        oauth.allow_all = wxsettings.env_bool("WXHUB_OAUTH_ALLOW_ALL", True)

#------------------------------------------------------------------------------
# Templates and branding
#------------------------------------------------------------------------------
c.JupyterHub.template_paths = [
    "/srv/jupyterhub/templates",
    f"{os.path.dirname(nativeauthenticator.__file__)}/templates/",
]
c.JupyterHub.template_vars = {
    **WX.brand,
    "announcement_login": "",
    "wxhub_authenticator": WX.authenticator,
    "wxhub_https": WX.https,
    "wxhub_cookie_days": c.JupyterHub.cookie_max_age_days,
}

#------------------------------------------------------------------------------
# Spawner
#------------------------------------------------------------------------------
c.JupyterHub.spawner_class = DockerSpawner
c.DockerSpawner.image = os.environ["DOCKER_NOTEBOOK_IMAGE"]
c.DockerSpawner.network_name = f"{WX.instance}-net"
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True
c.DockerSpawner.prefix = WX.container_prefix
c.Spawner.default_url = "/lab"
c.Spawner.cmd = ["jupyterhub-singleuser"]
c.Spawner.http_timeout = 120
c.Spawner.start_timeout = 300

notebook_dir = "/home/jovyan/work"
c.DockerSpawner.notebook_dir = notebook_dir

# Keys are paths on the Docker HOST because the host engine creates these mounts. The only
# writable mount is the user's own named volume; every shared source is bound read-only.
c.DockerSpawner.volumes = {f"{WX.volume_prefix}-user-{{username}}": notebook_dir}
c.DockerSpawner.read_only_volumes = {s.host_path: s.container_path for s in WX.data_sources}
READ_ONLY_TARGETS = {s.container_path for s in WX.data_sources}

# Defence in depth: user containers cannot gain privileges, so a read-only bind cannot be
# remounted read-write, and process counts are bounded.
c.DockerSpawner.extra_host_config = {
    "cap_drop": ["ALL"],
    "security_opt": ["no-new-privileges:true"],
    "pids_limit": 1024,
    "log_config": {"type": "json-file", "config": {"max-size": "10m", "max-file": "3"}},
}

c.Spawner.environment = {
    "JUPYTERHUB_SINGLEUSER_APP": "jupyter_server.serverapp.ServerApp",
    "METEO_API_BASE_URL": os.environ.get(
        "METEO_API_BASE_URL", "https://api.meteo.uniparthenope.it"
    ),
    "WXHUB_OPENDAP_DIR": "/home/jovyan/data/opendap",
    "WXHUB_NETWORK_DIR": "/home/jovyan/data/network",
}


def resource_tier(user) -> str:
    groups = {group.name for group in user.groups}
    if user.admin or "researchers" in groups:
        return "researcher"
    if "instructors" in groups:
        return "instructor"
    if "students" in groups:
        return "student"
    return "user"


def pre_spawn_hook(spawner):
    """Apply the role's resource tier and refuse to start with any writable shared mount."""
    tier = resource_tier(spawner.user)
    spawner.mem_limit, spawner.cpu_limit = RESOURCE_TIERS[tier]
    spawner.environment = {**spawner.environment, "WXHUB_ROLE": tier}
    for host_path, spec in spawner.volume_binds.items():
        if spec["bind"] in READ_ONLY_TARGETS and spec["mode"] != "ro":
            raise RuntimeError(f"refusing to spawn: {spec['bind']} would be writable")
        if spec["bind"] != notebook_dir and spec["bind"] not in READ_ONLY_TARGETS:
            raise RuntimeError(f"refusing to spawn: unexpected mount {spec['bind']}")


c.Spawner.pre_spawn_hook = pre_spawn_hook
