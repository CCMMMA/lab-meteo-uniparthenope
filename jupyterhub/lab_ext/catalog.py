"""Read-only inventory of the operational model archive and the weather-station network.

Expected layouts (all components are directory names):

* models:   <root>/<model>/<domain>/<history|archive>/YYYY/MM/DD/<model>_<domain>_YYYYMMDDZHHMM.nc
* stations: <root>/it.uniparthenope.meteo.wsN/YYYY/MM/DD/it.uniparthenope.meteo.wsN_YYYYMMDDZHH00.csv

The scanner only lists directories with ``os.scandir``; it never opens data files for writing,
creates files, or changes timestamps. Results are cached because the archive lives on a shared
network file system.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

MODEL_LABELS = {
    "aiq3": "AIquam (mussel-farm contamination AI)",
    "rms3": "ROMS (regional ocean model)",
    "rm3": "ROMS (regional ocean model)",
    "wrf5": "WRF (atmospheric model)",
    "ww33": "WaveWatch III (sea state)",
    "wcm3": "WaComM (water-quality community model)",
}
PRODUCT_TYPES = ("archive", "history")
STATION_PATTERN = re.compile(r"^it\.uniparthenope\.meteo\.ws(\d+)$")
_CACHE: dict[str, tuple[float, object]] = {}
_TTL_SECONDS = 600


def _dirs(path: Path, pattern: str | None = None) -> list[str]:
    try:
        with os.scandir(path) as entries:
            names = [e.name for e in entries if e.is_dir(follow_symlinks=False)]
    except OSError:
        return []
    if pattern:
        names = [n for n in names if re.fullmatch(pattern, n)]
    return sorted(names)


def latest_day(path: Path) -> str | None:
    """Return the most recent YYYY-MM-DD below ``path`` without walking the full tree."""
    for year in reversed(_dirs(path, r"\d{4}")):
        for month in reversed(_dirs(path / year, r"\d{2}")):
            days = _dirs(path / year / month, r"\d{2}")
            if days:
                return f"{year}-{month}-{days[-1]}"
    return None


def _cached(key: str, builder):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _TTL_SECONDS:
        return hit[1]
    value = builder()
    _CACHE[key] = (now, value)
    return value


def model_inventory(root: str) -> list[dict]:
    def build() -> list[dict]:
        base = Path(root)
        rows = []
        for model in _dirs(base):
            if model not in MODEL_LABELS:
                continue
            for domain in _dirs(base / model, r"d\d{2}"):
                for product in PRODUCT_TYPES:
                    product_path = base / model / domain / product
                    if not product_path.is_dir():
                        continue
                    rows.append({
                        "model": model,
                        "label": MODEL_LABELS[model],
                        "domain": domain,
                        "product": product,
                        "latest": latest_day(product_path),
                    })
        return rows

    return _cached(f"models:{root}", build)


def station_inventory(root: str) -> list[dict]:
    def build() -> list[dict]:
        base = Path(root)
        rows = []
        for name in _dirs(base):
            match = STATION_PATTERN.match(name)
            if match:
                rows.append({
                    "station": name,
                    "number": int(match.group(1)),
                    "latest": latest_day(base / name),
                })
        return sorted(rows, key=lambda row: row["number"])

    return _cached(f"stations:{root}", build)


def is_read_only_mount(path: str) -> bool | None:
    """Return True when ``path`` sits on a read-only mount in this container, None if unknown."""
    try:
        target = os.path.realpath(path)
        best: tuple[int, bool] | None = None
        with open("/proc/self/mounts", encoding="utf-8") as mounts:
            for line in mounts:
                parts = line.split()
                if len(parts) < 4:
                    continue
                mount_point = parts[1].replace("\\040", " ")
                if target == mount_point or target.startswith(mount_point.rstrip("/") + "/"):
                    if best is None or len(mount_point) > best[0]:
                        best = (len(mount_point), "ro" in parts[3].split(","))
        return None if best is None else best[1]
    except OSError:
        return None
