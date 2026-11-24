#!/usr/bin/env python3
"""Offline tests for the dependency-free parts of the lab.meteo@uniparthenope Hub extension."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jupyterhub"))

from lab_ext import catalog, settings  # noqa: E402
from lab_ext.requests_store import RequestStore  # noqa: E402


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_catalog(tmp: Path) -> None:
    opendap = tmp / "opendap"
    touch(opendap / "wrf5/d03/archive/2026/11/22/wrf5_d03_20261122Z0000.nc")
    touch(opendap / "wrf5/d03/archive/2026/10/31/wrf5_d03_20261031Z0000.nc")
    touch(opendap / "wrf5/d03/history/2025/12/31/wrf5_d03_20251231Z0000.nc")
    touch(opendap / "thesis/d01/archive/2026/01/01/x.nc")  # not a model: ignored
    rows = catalog.model_inventory(str(opendap))
    assert {(r["model"], r["product"], r["latest"]) for r in rows} == {
        ("wrf5", "archive", "2026-11-22"), ("wrf5", "history", "2025-12-31")
    }, rows
    network = tmp / "network"
    for n in (2, 10, 1):
        touch(network / f"it.uniparthenope.meteo.ws{n}/2026/11/0{n % 9 + 1}/x.csv")
    touch(network / "_logos/a.png")
    stations = catalog.station_inventory(str(network))
    assert [s["number"] for s in stations] == [1, 2, 10], stations
    assert catalog.is_read_only_mount("/") in {True, False, None}


def test_store(tmp: Path) -> None:
    store = RequestStore(tmp / "requests.json")
    item = store.add("alice", "erasure", "please")
    assert store.open_for("alice")[0]["id"] == item["id"]
    assert store.close(item["id"], "admin")["status"] == "completed"
    assert store.open_for("alice") == []
    assert oct((tmp / "requests.json").stat().st_mode & 0o777) == "0o600"


def test_settings() -> None:
    os.environ.update({
        "LAB_INSTANCE": "labmeteo", "LAB_OPENDAP_HOST": "/srv/opendap",
        "LAB_NETWORK_HOST": "/srv/network", "LAB_TEMPLATES_HOST": "/srv/templates",
        "LAB_PUBLIC_HOST": "https://example.org/",
    })
    loaded = settings.load()
    assert loaded.volume_prefix == "labmeteo" and loaded.container_prefix == "labmeteo-user"
    assert loaded.https and loaded.public_host == "https://example.org"
    targets = {s.container_path for s in loaded.data_sources}
    assert {"/home/jovyan/data/opendap", "/home/jovyan/data/network"} <= targets
    os.environ["LAB_INSTANCE"] = "Bad_Name"
    try:
        settings.load()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid instance name accepted")


with tempfile.TemporaryDirectory() as directory:
    test_catalog(Path(directory))
    test_store(Path(directory))
test_settings()
print("lab.meteo@uniparthenope extension tests passed")
