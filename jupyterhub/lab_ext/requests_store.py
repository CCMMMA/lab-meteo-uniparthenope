"""Small persistent register of data-subject requests (GDPR Articles 15-21).

The register is a JSON document in the Hub's persistent volume. It stores only what is needed to
handle and evidence a request: username, request type, timestamps, and status. Writes are atomic
and serialized inside the single Hub process.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

REQUEST_TYPES = {
    "erasure": "Erasure of account and workspace (Art. 17)",
    "restriction": "Restriction of processing (Art. 18)",
    "rectification": "Rectification of account data (Art. 16)",
}
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RequestStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".lab-requests-")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(items, handle, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def all(self) -> list[dict]:
        with _LOCK:
            return self._read()

    def open_for(self, username: str) -> list[dict]:
        return [r for r in self.all() if r["username"] == username and r["status"] == "open"]

    def add(self, username: str, kind: str, note: str = "") -> dict:
        if kind not in REQUEST_TYPES:
            raise ValueError(f"unknown request type {kind!r}")
        item = {
            "id": uuid.uuid4().hex[:12],
            "username": username,
            "type": kind,
            "note": note[:500],
            "created": _now(),
            "status": "open",
            "closed": None,
            "closed_by": None,
        }
        with _LOCK:
            items = self._read()
            items.append(item)
            self._write(items)
        return item

    def close(self, request_id: str, admin: str, status: str = "completed") -> dict | None:
        with _LOCK:
            items = self._read()
            for item in items:
                if item["id"] == request_id and item["status"] == "open":
                    item.update(status=status, closed=_now(), closed_by=admin)
                    self._write(items)
                    return item
        return None

    def close_all_for(self, username: str, admin: str) -> None:
        with _LOCK:
            items = self._read()
            for item in items:
                if item["username"] == username and item["status"] == "open":
                    item.update(status="completed", closed=_now(), closed_by=admin)
            self._write(items)
