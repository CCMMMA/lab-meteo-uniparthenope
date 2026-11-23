"""lab.meteo@uniparthenope extensions for JupyterHub.

The package adds institutional pages (privacy notice, accessibility statement, personal-data
self-service, and a platform-administration dashboard) to an unmodified JupyterHub by contributing
handlers through the configured authenticator. It intentionally avoids patching JupyterHub
internals so that upgrades remain a pinned-version change.
"""

__all__ = ["settings"]
