"""Authenticator selection: local accounts or academic single sign-on.

``WXHUB_AUTHENTICATOR`` selects one of:

* ``native``  – local accounts with administrator approval (NativeAuthenticator);
* ``azuread`` – Microsoft Entra ID (Azure AD), e.g. a university Microsoft 365 tenant;
* ``google``  – Google Workspace for Education restricted to institutional hosted domains.

Every class receives the WxHub pages through ``get_handlers`` so that the extension works without
JupyterHub's deprecated ``extra_handlers`` option.
"""

from __future__ import annotations

from .handlers import get_handlers
from .settings import WxHubSettings

AUTHENTICATORS = {"native", "azuread", "google"}


def build_authenticator_class(wxhub: WxHubSettings, assets_path: str):
    kind = wxhub.authenticator
    if kind == "native":
        from nativeauthenticator import NativeAuthenticator as base
    elif kind == "azuread":
        from oauthenticator.azuread import AzureAdOAuthenticator as base
    elif kind == "google":
        from oauthenticator.google import GoogleOAuthenticator as base
    else:
        raise ValueError(f"WXHUB_AUTHENTICATOR must be one of {sorted(AUTHENTICATORS)}, got {kind!r}")

    def handlers(self, app):
        return list(base.get_handlers(self, app)) + get_handlers(wxhub, assets_path)

    return type(f"WxHub{base.__name__}", (base,), {"get_handlers": handlers})
