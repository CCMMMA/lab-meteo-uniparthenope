"""Environment-driven lab.meteo@uniparthenope settings shared by the Hub configuration and the extension handlers."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    return env_str(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = env_str(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def env_list(name: str) -> list[str]:
    return [item.strip() for item in env_str(name).split(",") if item.strip()]


def env_color(name: str, default: str) -> str:
    value = env_str(name, default)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(f"{name} must be a six-digit hexadecimal color")
    return value


def env_http_url(name: str, default: str) -> str:
    value = env_str(name, default)
    if not re.fullmatch(r"https?://[^\s]+", value):
        raise ValueError(f"{name} must be an HTTP or HTTPS URL")
    return value


def env_instance() -> str:
    value = env_str("WXHUB_INSTANCE", "wxhub")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", value):
        raise ValueError("WXHUB_INSTANCE must be 2-31 lowercase letters, digits, or hyphens")
    return value


@dataclass(frozen=True)
class DataSource:
    """A host directory exposed read-only to every user server."""

    key: str
    label: str
    host_path: str
    container_path: str
    hub_path: str | None = None
    kind: str = "generic"


@dataclass(frozen=True)
class LabMeteoSettings:
    instance: str
    public_host: str
    authenticator: str
    brand: dict
    privacy: dict
    data_sources: tuple[DataSource, ...]
    volume_prefix: str
    container_prefix: str
    requests_file: Path
    idle_timeout: int
    retention_days: int
    extra: dict = field(default_factory=dict)

    @property
    def https(self) -> bool:
        return self.public_host.startswith("https://")


def load() -> LabMeteoSettings:
    instance = env_instance()
    # Keep historical Docker object names for the default instance so that existing
    # deployments retain their per-user volumes after an upgrade.
    legacy = instance == "wxhub"
    sources: list[DataSource] = [
        DataSource("templates", "Starter notebooks", env_str("WXHUB_TEMPLATES_HOST"),
                   "/home/jovyan/templates", kind="templates"),
        DataSource("sensors", "Raw sensor mirror", env_str("WXHUB_SENSORS_HOST"),
                   "/home/jovyan/data/raw/sensors"),
        DataSource("models", "Raw model mirror", env_str("WXHUB_MODELS_HOST"),
                   "/home/jovyan/data/raw/models"),
        DataSource("curated", "Curated products", env_str("WXHUB_CURATED_HOST"),
                   "/home/jovyan/data/curated"),
    ]
    if env_str("WXHUB_OPENDAP_HOST"):
        sources.append(DataSource(
            "opendap", "Operational model archive", env_str("WXHUB_OPENDAP_HOST"),
            "/home/jovyan/data/opendap", "/srv/data/opendap", kind="opendap",
        ))
    if env_str("WXHUB_NETWORK_HOST"):
        sources.append(DataSource(
            "network", "Weather-station network", env_str("WXHUB_NETWORK_HOST"),
            "/home/jovyan/data/network", "/srv/data/network", kind="network",
        ))
    for source in sources:
        if source.host_path and not source.host_path.startswith("/"):
            raise ValueError(f"host path for {source.key} must be absolute: {source.host_path}")

    brand = {
        "wxhub_brand_name": env_str("WXHUB_BRAND_NAME", "lab.meteo@uniparthenope"),
        "wxhub_brand_subtitle": env_str("WXHUB_BRAND_SUBTITLE", "Weather and marine data workspace"),
        "wxhub_brand_primary": env_color("WXHUB_BRAND_PRIMARY", "#1f4e79"),
        "wxhub_brand_secondary": env_color("WXHUB_BRAND_SECONDARY", "#2a91eb"),
        "wxhub_brand_accent": env_color("WXHUB_BRAND_ACCENT", "#181c63"),
        "wxhub_brand_site_url": env_http_url("WXHUB_BRAND_SITE_URL", "https://meteo.uniparthenope.it"),
        "wxhub_brand_network_url": env_http_url(
            "WXHUB_BRAND_NETWORK_URL", "https://network.meteo.uniparthenope.it"
        ),
    }
    privacy = {
        "controller": env_str(
            "WXHUB_PRIVACY_CONTROLLER", "University of Naples “Parthenope”"
        ),
        "contact": env_str("WXHUB_PRIVACY_CONTACT", "privacy@uniparthenope.it, privacy@pec.uniparthenope.it (University Privacy Office)"),
        "dpo_contact": env_str("WXHUB_DPO_CONTACT", "dpo.privacy@uniparthenope.it"),
        "accessibility_contact": env_str("WXHUB_ACCESSIBILITY_CONTACT",
                                       "meteo@uniparthenope.it or the University accessibility page https://www.uniparthenope.it/Portale-Ateneo/accessibilita"),
    }
    return LabMeteoSettings(
        instance=instance,
        public_host=env_str("WXHUB_PUBLIC_HOST", "http://localhost:8000").rstrip("/"),
        authenticator=env_str("WXHUB_AUTHENTICATOR", "native").lower(),
        brand=brand,
        privacy=privacy,
        data_sources=tuple(s for s in sources if s.host_path),
        volume_prefix="jupyterhub" if legacy else instance,
        container_prefix="jupyter" if legacy else f"{instance}-user",
        requests_file=Path("/srv/jupyterhub/data/wxhub_privacy_requests.json"),
        idle_timeout=env_int("WXHUB_IDLE_TIMEOUT", 3600),
        retention_days=env_int("WXHUB_RETENTION_DAYS", 365, minimum=1),
    )
