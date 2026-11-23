"""Hub pages for privacy, accessibility, personal-data self-service, and platform administration."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from jupyterhub import orm
from jupyterhub.handlers import BaseHandler
from jupyterhub.utils import maybe_future
from tornado import web
from tornado.escape import url_escape

from . import catalog
from .requests_store import REQUEST_TYPES, RequestStore
from .settings import LabMeteoSettings

# A child of JupyterHub's application logger, so audit lines reach the Hub log handlers.
_audit_logger = logging.getLogger("JupyterHub.lab.meteo.audit")


class _Audit:
    @staticmethod
    def info(message: str, *args) -> None:
        _audit_logger.info("lab.meteo.audit " + message, *args)


audit = _Audit()

# Groups that map to platform roles. Admin is JupyterHub's built-in role.
ROLE_GROUPS = {
    "students": "Student",
    "researchers": "Researcher",
    "instructors": "Instructor",
}


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.replace(microsecond=0).isoformat()


def role_label(orm_user) -> str:
    if orm_user.admin:
        return "Administrator"
    names = {group.name for group in orm_user.groups}
    for group in ("instructors", "researchers", "students"):
        if group in names:
            return ROLE_GROUPS[group]
    return "User"


def native_info(db, username: str):
    try:
        from nativeauthenticator.orm import UserInfo
    except ImportError:  # pragma: no cover - native authenticator is always installed
        return None
    try:
        return UserInfo.find(db, username)
    except Exception:  # table absent when another authenticator is configured
        db.rollback()
        return None


def docker_client():
    import docker

    return docker.from_env(timeout=15)


class LabMeteoHandler(BaseHandler):
    """Common helpers for lab.meteo@uniparthenope pages."""

    def initialize(self, wxhub: LabMeteoSettings):
        self.wxhub = wxhub
        self.store = RequestStore(wxhub.requests_file)

    def wx_namespace(self, **extra) -> dict:
        ns = {
            "wxhub_settings": self.wxhub,
            "wxhub_privacy": self.wxhub.privacy,
            "wxhub_request_types": REQUEST_TYPES,
            "wxhub_retention_days": self.wxhub.retention_days,
            "wxhub_idle_timeout": self.wxhub.idle_timeout,
        }
        ns.update(extra)
        return ns

    async def render_page(self, template: str, **extra) -> None:
        html = await self.render_template(template, **self.wx_namespace(**extra))
        self.set_header("Cache-Control", "no-store")
        self.finish(html)

    def workspace_volumes(self, user) -> list[str]:
        try:
            binds = user.spawner.volume_binds
        except Exception:
            return []
        return sorted(name for name in binds if not name.startswith("/"))


class PrivacyHandler(LabMeteoHandler):
    async def get(self):
        await self.render_page("wxhub_privacy.html")


class AccessibilityHandler(LabMeteoHandler):
    async def get(self):
        await self.render_page("wxhub_accessibility.html")


class AccountHandler(LabMeteoHandler):
    """Show, export, and raise requests about the signed-in user's personal data."""

    def personal_data(self, user) -> dict:
        orm_user = user.orm_user
        record = {
            "generated": iso(datetime.now(timezone.utc)),
            "controller": self.wxhub.privacy["controller"],
            "service": self.wxhub.brand["wxhub_brand_name"],
            "username": user.name,
            "role": role_label(orm_user),
            "administrator": bool(orm_user.admin),
            "groups": sorted(group.name for group in orm_user.groups),
            "authentication": self.wxhub.authenticator,
            "created": iso(orm_user.created),
            "last_activity": iso(orm_user.last_activity),
            "servers": {
                (name or "default"): {
                    "started": iso(spawner.started),
                    "last_activity": iso(spawner.last_activity),
                }
                for name, spawner in orm_user.orm_spawners.items()
            },
            "api_tokens": len(orm_user.api_tokens),
            "workspace_volumes": self.workspace_volumes(user),
            "privacy_requests": [r for r in self.store.all() if r["username"] == user.name],
        }
        info = native_info(self.db, user.name)
        if info is not None:
            record["local_account"] = {
                "email": info.email or None,
                "approved": bool(info.is_authorized),
                "two_factor_authentication": bool(info.has_2fa),
                "password": "stored only as a salted bcrypt hash",
            }
        return record

    @web.authenticated
    async def get(self):
        user = self.current_user
        data = self.personal_data(user)
        if self.get_argument("format", "") == "json":
            self.set_header("Content-Type", "application/json; charset=utf-8")
            self.set_header("Cache-Control", "no-store")
            self.set_header(
                "Content-Disposition", f'attachment; filename="lab-meteo-personal-data-{user.name}.json"'
            )
            self.finish(json.dumps(data, indent=2, ensure_ascii=False))
            return
        await self.render_page(
            "wxhub_account.html",
            record=data,
            open_requests=self.store.open_for(user.name),
            message=self.get_argument("message", ""),
        )

    @web.authenticated
    async def post(self):
        user = self.current_user
        kind = self.get_body_argument("type", "")
        note = self.get_body_argument("note", "").strip()
        if kind not in REQUEST_TYPES:
            raise web.HTTPError(400, "Unknown request type")
        if kind == "erasure" and self.get_body_argument("confirm", "") != "yes":
            raise web.HTTPError(400, "Erasure requests must be explicitly confirmed")
        if any(r["type"] == kind for r in self.store.open_for(user.name)):
            message = "A request of this type is already open."
        else:
            item = self.store.add(user.name, kind, note)
            audit.info("privacy-request id=%s user=%s type=%s", item["id"], user.name, kind)
            message = "Your request has been registered. An administrator will handle it."
        self.redirect(f"{self.hub.base_url}lab/account?message=" + url_escape(message))


class AdminHandler(LabMeteoHandler):
    """Platform-administration dashboard. Viewing needs ``admin-ui``; changes need admin."""

    def require_view(self):
        if self.current_user is None:
            raise web.HTTPError(403)
        if "admin-ui" not in self.parsed_scopes:
            raise web.HTTPError(403, "The platform dashboard requires an administrative role")

    def require_admin(self):
        if self.current_user is None or not self.current_user.admin:
            raise web.HTTPError(403, "Only administrators can change platform state")

    def _docker_state(self, known_volumes: set[str], data_targets: set[str]) -> dict:
        state = {"available": False, "orphans": [], "mount_violations": [], "containers": 0,
                 "error": None}
        try:
            client = docker_client()
            prefix = f"{self.wxhub.volume_prefix}-user-"
            for volume in client.volumes.list(filters={"name": prefix}):
                if volume.name.startswith(prefix) and volume.name not in known_volumes:
                    state["orphans"].append(volume.name)
            container_prefix = f"{self.wxhub.container_prefix}-"
            for container in client.containers.list(filters={"name": container_prefix}):
                if not container.name.startswith(container_prefix):
                    continue
                state["containers"] += 1
                for mount in container.attrs.get("Mounts", []):
                    if mount.get("Destination") in data_targets and mount.get("RW", True):
                        state["mount_violations"].append(
                            f"{container.name}:{mount.get('Destination')}"
                        )
            state["available"] = True
        except Exception as exc:  # Docker unavailable must not break the dashboard
            state["error"] = str(exc)
        state["orphans"].sort()
        return state

    async def collect(self) -> dict:
        users = []
        known_volumes: set[str] = set()
        for orm_user in self.db.query(orm.User).order_by(orm.User.name):
            user = self.users[orm_user]
            volumes = self.workspace_volumes(user)
            known_volumes.update(volumes)
            spawner = user.spawner
            users.append({
                "name": user.name,
                "role": role_label(orm_user),
                "admin": bool(orm_user.admin),
                "groups": sorted(g.name for g in orm_user.groups),
                "created": iso(orm_user.created),
                "last_activity": iso(orm_user.last_activity),
                "running": bool(spawner.active),
                "volumes": volumes,
            })
        pending = []
        try:
            from nativeauthenticator.orm import UserInfo

            pending = [i.username for i in self.db.query(UserInfo).filter_by(is_authorized=False)]
        except Exception:
            self.db.rollback()

        data_targets = {s.container_path for s in self.wxhub.data_sources}
        docker_state = await asyncio.to_thread(self._docker_state, known_volumes, data_targets)

        sources = []
        for source in self.wxhub.data_sources:
            entry = {"source": source, "hub_read_only": None, "inventory": None}
            if source.hub_path:
                entry["hub_read_only"] = catalog.is_read_only_mount(source.hub_path)
                if source.kind == "opendap":
                    entry["inventory"] = await asyncio.to_thread(
                        catalog.model_inventory, source.hub_path
                    )
                elif source.kind == "network":
                    entry["inventory"] = await asyncio.to_thread(
                        catalog.station_inventory, source.hub_path
                    )
            sources.append(entry)

        requests = sorted(self.store.all(), key=lambda r: (r["status"] != "open", r["created"]))
        authenticator = self.authenticator
        return {
            "users": users,
            "pending": pending,
            "requests": requests,
            "sources": sources,
            "docker": docker_state,
            "posture": {
                "authenticator": self.wxhub.authenticator,
                "signup": bool(getattr(authenticator, "enable_signup", False)),
                "open_signup": bool(getattr(authenticator, "open_signup", False)),
                "https": self.wxhub.https,
                "public_host": self.wxhub.public_host,
                "idle_timeout": self.wxhub.idle_timeout,
                "admins": sum(1 for u in users if u["admin"]),
                "running": sum(1 for u in users if u["running"]),
            },
            "role_groups": ROLE_GROUPS,
        }

    @web.authenticated
    async def get(self):
        self.require_view()
        await self.render_page(
            "wxhub_admin.html",
            dash=await self.collect(),
            message=self.get_argument("message", ""),
            can_change=bool(self.current_user.admin),
        )

    def _back(self, message: str, anchor: str = "") -> None:
        url = f"{self.hub.base_url}lab/admin?message={url_escape(message)}"
        self.redirect(url + (f"#{anchor}" if anchor else ""))

    async def _remove_volumes(self, names: list[str]) -> list[str]:
        def remove() -> list[str]:
            errors = []
            client = docker_client()
            for name in names:
                if not name.startswith(f"{self.wxhub.volume_prefix}-user-"):
                    errors.append(f"{name}: not a workspace volume")
                    continue
                try:
                    client.volumes.get(name).remove()
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
            return errors

        return await asyncio.to_thread(remove)

    async def erase_user(self, name: str) -> str:
        user = self.find_user(name)
        if user is None:
            return f"User {name} does not exist."
        if user.name == self.current_user.name:
            return "You cannot erase your own account."
        if user.running:
            await self.stop_single_user(user)
        if user.spawner._stop_pending:
            return f"The server of {name} is still stopping; retry shortly."
        volumes = self.workspace_volumes(user)
        await maybe_future(self.authenticator.delete_user(user))
        await user.delete_spawners()
        self.users.delete(user)
        errors = await self._remove_volumes(volumes)
        self.store.close_all_for(name, self.current_user.name)
        audit.info("erase-user user=%s by=%s volumes=%s errors=%s",
                   name, self.current_user.name, volumes, errors)
        if errors:
            return f"Account {name} erased; volume errors: {'; '.join(errors)}"
        return f"Account {name} and its workspace were erased."

    def set_role(self, name: str, role: str) -> str:
        user = self.find_user(name)
        if user is None:
            return f"User {name} does not exist."
        if role not in {"user", *ROLE_GROUPS}:
            raise web.HTTPError(400, "Unknown role")
        orm_user = user.orm_user
        for group_name in ROLE_GROUPS:
            group = orm.Group.find(self.db, group_name)
            if group is not None and group in orm_user.groups and group_name != role:
                orm_user.groups.remove(group)
        if role in ROLE_GROUPS:
            group = orm.Group.find(self.db, role)
            if group is None:
                group = orm.Group(name=role)
                self.db.add(group)
            if group not in orm_user.groups:
                orm_user.groups.append(group)
        self.db.commit()
        audit.info("set-role user=%s role=%s by=%s", name, role, self.current_user.name)
        return f"{name} now has the {ROLE_GROUPS.get(role, 'User')} role; it applies at next server start."

    @web.authenticated
    async def post(self):
        self.require_admin()
        action = self.get_body_argument("action", "")
        if action == "set_role":
            message = self.set_role(self.get_body_argument("username"), self.get_body_argument("role"))
            return self._back(message, "users")
        if action == "erase_user":
            name = self.get_body_argument("username")
            if self.get_body_argument("confirm", "") != name:
                return self._back("Erasure not confirmed: type the exact username.", "requests")
            return self._back(await self.erase_user(name), "requests")
        if action == "erase_volume":
            name = self.get_body_argument("volume")
            if self.get_body_argument("confirm", "") != name:
                return self._back("Volume erasure not confirmed.", "volumes")
            known = {v for u in self.db.query(orm.User) for v in self.workspace_volumes(self.users[u])}
            if name in known:
                return self._back("That volume belongs to an existing user.", "volumes")
            errors = await self._remove_volumes([name])
            audit.info("erase-volume volume=%s by=%s errors=%s", name, self.current_user.name, errors)
            return self._back("; ".join(errors) or f"Volume {name} erased.", "volumes")
        if action == "close_request":
            status = self.get_body_argument("status", "completed")
            if status not in {"completed", "rejected"}:
                raise web.HTTPError(400)
            item = self.store.close(self.get_body_argument("request_id"), self.current_user.name, status)
            audit.info("close-request id=%s status=%s by=%s",
                       item and item["id"], status, self.current_user.name)
            return self._back("Request updated." if item else "Request not found.", "requests")
        raise web.HTTPError(400, "Unknown action")


def get_handlers(wxhub: LabMeteoSettings, assets_path: str) -> list[tuple]:
    kwargs = {"wxhub": wxhub}
    return [
        (r"/lab/privacy", PrivacyHandler, kwargs),
        (r"/lab/accessibility", AccessibilityHandler, kwargs),
        (r"/lab/account", AccountHandler, kwargs),
        (r"/lab/admin", AdminHandler, kwargs),
        (r"/lab/static/(.*)", web.StaticFileHandler, {"path": assets_path}),
    ]
