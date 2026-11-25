"""Colab-style notebook workflows: new notebook, open from GitHub, upload, recent files, runtime.

Google Colaboratory lets a user open any public notebook through a predictable URL
(``/github/<owner>/<repo>/blob/<ref>/<path>.ipynb``), create a notebook with one click, upload
a notebook from the local disk, and connect, restart, or delete the runtime. These handlers give
lab.meteo@uniparthenope the same behaviour on top of JupyterHub:

* the Hub starts the user's server when needed, then writes the notebook into ``~/work`` through
  the Jupyter Server contents API, using a short-lived token restricted to that user's server;
* notebooks open in the Jupyter Notebook 7 single-document interface, the closest open-source
  counterpart of the Colab editor; JupyterLab stays one click away;
* only ``raw.githubusercontent.com`` is contacted, with validated path components and no
  redirects, so the import cannot be used to reach internal hosts.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

from jupyterhub import orm
from jupyterhub.utils import url_path_join
from tornado import web
from tornado.escape import url_escape
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest

from .handlers import LabMeteoHandler, audit

MAX_NOTEBOOK_BYTES = 25 * 1024 * 1024
NAME = r"[A-Za-z0-9_.-]{1,100}"
SEGMENT = re.compile(r"^[A-Za-z0-9_.()+,@ -]{1,200}$")
GITHUB_PATH = re.compile(rf"^(?P<owner>{NAME})/(?P<repo>{NAME})/blob/(?P<ref>{NAME})/(?P<path>.+\.ipynb)$")


def empty_notebook() -> dict:
    """The notebook a user gets from *New notebook*: one empty code cell, as in Colab."""
    return {
        "cells": [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": []}],
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def safe_segments(path: str) -> list[str]:
    """Split a relative path, rejecting traversal, hidden names, and unexpected characters."""
    parts = [part for part in path.split("/") if part]
    if not parts:
        raise web.HTTPError(400, "Empty path")
    for part in parts:
        if part in {".", ".."} or part.startswith(".") or not SEGMENT.match(part):
            raise web.HTTPError(400, f"Unsupported path component: {part!r}")
    return parts


def validate_notebook(raw: bytes) -> dict:
    if len(raw) > MAX_NOTEBOOK_BYTES:
        raise web.HTTPError(413, "Notebooks larger than 25 MB are not imported")
    try:
        notebook = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise web.HTTPError(400, "The file is not a valid Jupyter notebook (JSON expected)") from None
    if not (
        isinstance(notebook, dict)
        and isinstance(notebook.get("cells"), list)
        and isinstance(notebook.get("nbformat"), int)
        and notebook["nbformat"] >= 4
    ):
        raise web.HTTPError(400, "The file is not a Jupyter notebook in format 4 or later")
    return notebook


def parse_github_url(url: str) -> str:
    """Translate a github.com or raw.githubusercontent.com URL to the Colab-style route."""
    parsed = urlparse(url.strip())
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"}:
        raise web.HTTPError(400, "Enter a GitHub URL starting with https://")
    if parsed.netloc == "github.com" and len(parts) >= 5 and parts[2] == "blob":
        route = "/".join(parts)
    elif parsed.netloc == "raw.githubusercontent.com" and len(parts) >= 4:
        route = "/".join(parts[:2] + ["blob"] + parts[2:])
    else:
        raise web.HTTPError(400, "Use a link to a notebook file, e.g. https://github.com/<owner>/<repo>/blob/<branch>/<file>.ipynb")
    if not GITHUB_PATH.match(route):
        raise web.HTTPError(400, "The link does not point to an .ipynb file on a branch or tag")
    return route


class WorkspaceHandler(LabMeteoHandler):
    """Talks to the signed-in user's own server with a short-lived, narrowly scoped token."""

    def runtime_ready(self, user) -> bool:
        return bool(user.spawner.ready)

    def redirect_to_spawn(self, user) -> None:
        target = url_path_join(self.hub.base_url, "spawn", user.name)
        self.redirect(f"{target}?next={url_escape(self.request.uri)}")

    async def server_api(self, user, method: str, path: str, body: dict | None = None, query: str = ""):
        token = user.new_api_token(
            note="lab.meteo workspace action", expires_in=300, scopes=[f"access:servers!user={user.name}"]
        )
        try:
            base = user.spawner.server.url
            request = HTTPRequest(
                url_path_join(base, "api/contents", quote(path)) + (f"?{query}" if query else ""),
                method=method,
                headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
                body=json.dumps(body) if body is not None else None,
                request_timeout=60,
                follow_redirects=False,
            )
            try:
                response = await AsyncHTTPClient().fetch(request)
            except HTTPClientError as error:
                if error.code == 404:
                    return None
                raise web.HTTPError(502, f"Your server refused the request ({error.code})") from None
            return json.loads(response.body or b"null")
        finally:
            record = orm.APIToken.find(self.db, token)
            if record is not None:
                self.db.delete(record)
                self.db.commit()

    async def ensure_dirs(self, user, parts: list[str]) -> None:
        for depth in range(1, len(parts) + 1):
            path = "/".join(parts[:depth])
            if await self.server_api(user, "GET", path, query="content=0") is None:
                await self.server_api(user, "PUT", path, {"type": "directory"})

    async def free_name(self, user, folder: list[str], stem: str, suffix: str = ".ipynb") -> str:
        for index in range(0, 500):
            name = f"{stem}{suffix}" if index == 0 else f"{stem}{index}{suffix}"
            if await self.server_api(user, "GET", "/".join(folder + [name]), query="content=0") is None:
                return name
        raise web.HTTPError(409, "Too many notebooks with this name")

    async def save_notebook(self, user, parts: list[str], notebook: dict) -> None:
        if len(parts) > 1:
            await self.ensure_dirs(user, parts[:-1])
        await self.server_api(user, "PUT", "/".join(parts), {"type": "notebook", "format": "json", "content": notebook})

    def open_notebook(self, user, parts: list[str]) -> None:
        self.redirect(url_path_join(user.url, "notebooks", *[quote(part) for part in parts]))


class NewNotebookHandler(WorkspaceHandler):
    """``/new``: create ``~/work/UntitledN.ipynb`` and open it, like *File → New notebook* in Colab."""

    @web.authenticated
    async def get(self):
        user = self.current_user
        if not self.runtime_ready(user):
            return self.redirect_to_spawn(user)
        name = await self.free_name(user, [], "Untitled")
        await self.save_notebook(user, [name], empty_notebook())
        audit.info("user=%s created notebook %s", user.name, name)
        self.open_notebook(user, [name])


class GitHubHandler(WorkspaceHandler):
    """``/github/<owner>/<repo>/blob/<ref>/<path>.ipynb``: the Colab URL scheme for public notebooks.

    The notebook is copied to ``~/work/github/<owner>/<repo>/<path>``. An existing copy is opened
    unchanged so that the user's edits are never overwritten; ``?copy=1`` fetches a fresh copy
    under a new name.
    """

    @web.authenticated
    async def get(self, route: str):
        match = GITHUB_PATH.match(route)
        if not match:
            raise web.HTTPError(404, "Use /github/<owner>/<repo>/blob/<branch>/<path>.ipynb")
        owner, repo, ref = match["owner"], match["repo"], match["ref"]
        file_parts = safe_segments(match["path"])
        user = self.current_user
        if not self.runtime_ready(user):
            return self.redirect_to_spawn(user)

        folder = ["github", owner, repo] + file_parts[:-1]
        target = folder + [file_parts[-1]]
        fresh = self.get_argument("copy", "") == "1"
        exists = await self.server_api(user, "GET", "/".join(target), query="content=0") is not None
        if exists and not fresh:
            return self.open_notebook(user, target)

        raw_url = "https://raw.githubusercontent.com/" + "/".join(
            quote(part) for part in [owner, repo, ref, *file_parts]
        )
        try:
            response = await AsyncHTTPClient().fetch(
                HTTPRequest(raw_url, request_timeout=30, follow_redirects=False,
                            headers={"User-Agent": "lab.meteo-notebook-import"})
            )
        except HTTPClientError as error:
            raise web.HTTPError(404 if error.code in (301, 302, 404) else 502,
                                f"GitHub returned {error.code} for {owner}/{repo}/{ref}") from None
        notebook = validate_notebook(response.body)
        if exists:
            stem = file_parts[-1][: -len(".ipynb")]
            target = folder + [await self.free_name(user, folder, f"{stem}-copy")]
        await self.save_notebook(user, target, notebook)
        audit.info("user=%s imported github:%s/%s@%s/%s", user.name, owner, repo, ref, "/".join(file_parts))
        self.open_notebook(user, target)


class OpenUrlHandler(WorkspaceHandler):
    """``/open?url=…``: accept a pasted GitHub link and forward to the Colab-style route."""

    @web.authenticated
    async def get(self):
        url = self.get_argument("url", "")
        if not url:
            return self.redirect(url_path_join(self.hub.base_url, "home"))
        self.redirect(url_path_join(self.hub.base_url, "github", parse_github_url(url)))


class UploadHandler(WorkspaceHandler):
    """``POST /upload``: store an uploaded notebook in ``~/work/uploads`` and open it."""

    @web.authenticated
    async def post(self):
        user = self.current_user
        if not self.runtime_ready(user):
            raise web.HTTPError(409, "Connect your runtime before uploading a notebook")
        files = self.request.files.get("notebook") or []
        if not files:
            raise web.HTTPError(400, "Choose an .ipynb file to upload")
        upload = files[0]
        filename = upload["filename"].replace("\\", "/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".ipynb"):
            raise web.HTTPError(400, "Only .ipynb notebooks can be uploaded")
        stem = re.sub(r"[^A-Za-z0-9_.()+,@ -]", "_", filename[: -len(".ipynb")]).strip(" .") or "notebook"
        notebook = validate_notebook(upload["body"])
        name = await self.free_name(user, ["uploads"], stem[:150])
        await self.save_notebook(user, ["uploads", name], notebook)
        audit.info("user=%s uploaded notebook uploads/%s", user.name, name)
        self.open_notebook(user, ["uploads", name])


class RecentHandler(WorkspaceHandler):
    """``GET /recent``: JSON list of the most recently modified notebooks in ``~/work``."""

    @web.authenticated
    async def get(self):
        user = self.current_user
        self.set_header("Content-Type", "application/json")
        self.set_header("Cache-Control", "no-store")
        if not self.runtime_ready(user):
            return self.finish(json.dumps({"running": False, "notebooks": []}))
        found: list[dict] = []

        async def scan(path: str, depth: int) -> None:
            listing = await self.server_api(user, "GET", (path or ""), query="content=1")
            for item in (listing or {}).get("content") or []:
                if item["type"] == "notebook":
                    found.append({"path": item["path"], "name": item["name"], "modified": item["last_modified"]})
                elif item["type"] == "directory" and depth < 6 and not item["name"].startswith("."):
                    await scan(item["path"], depth + 1)
                if len(found) > 400:
                    return

        await scan("", 0)
        found.sort(key=lambda item: item["modified"], reverse=True)
        for item in found:
            item["url"] = url_path_join(user.url, "notebooks", *[quote(p) for p in item["path"].split("/")])
        self.finish(json.dumps({"running": True, "notebooks": found[:15]}))


class RuntimeHandler(WorkspaceHandler):
    """``POST /runtime``: *Restart runtime* and *Disconnect and delete runtime*, as in Colab.

    The container is removed on stop; files in ``~/work`` live in a persistent volume and stay.
    """

    @web.authenticated
    async def post(self):
        user = self.current_user
        action = self.get_body_argument("action", "")
        if action not in {"restart", "delete"}:
            raise web.HTTPError(400, "Unknown runtime action")
        if user.spawner.active:
            await self.stop_single_user(user)
        audit.info("user=%s runtime %s at %s", user.name, action, datetime.now(timezone.utc).isoformat())
        if action == "restart":
            return self.redirect(url_path_join(self.hub.base_url, "spawn", user.name))
        self.redirect(url_path_join(self.hub.base_url, "home") + "?runtime=deleted")


def get_workspace_handlers(lab) -> list[tuple]:
    kwargs = {"lab": lab}
    return [
        (r"/new", NewNotebookHandler, kwargs),
        (r"/github/(.+)", GitHubHandler, kwargs),
        (r"/open", OpenUrlHandler, kwargs),
        (r"/upload", UploadHandler, kwargs),
        (r"/recent", RecentHandler, kwargs),
        (r"/runtime", RuntimeHandler, kwargs),
    ]
