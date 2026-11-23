#!/usr/bin/env python3
"""Generate the public, output-free meteo@uniparthenope demo notebooks."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demos"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str, *, tags: list[str] | None = None) -> dict:
    metadata = {"tags": tags} if tags else {}
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": metadata,
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


INTRO = """This live demonstration uses public meteo@uniparthenope data. Values are generated
automatically and are intended for research, education, and general information—not for official
warnings, navigation, or safety-critical decisions. Times are UTC. Run and edit the cells in this
browser-based workspace; your changes stay in your browser unless you download the notebook."""


SETUP = '''import json
import os
import sys
from urllib.parse import urlencode
from datetime import datetime

if sys.platform == "emscripten":
    import piplite
    await piplite.install("ipywidgets")

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML, clear_output, display

API_BASE = "https://api.meteo.uniparthenope.it" if sys.platform == "emscripten" else os.environ.get(
    "METEO_API_BASE_URL", "https://api.meteo.uniparthenope.it"
).rstrip("/")
BRAND = "#1f4e79"
ACCENT = "#2a91eb"

def api_json(path, params=None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urlencode(params)}"
    if sys.platform == "emscripten":
        from pyodide.http import open_url
        return json.load(open_url(url))
    import requests
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()

def forecast_frame(place):
    payload = api_json(f"products/wrf5/timeseries/{place}")
    if payload.get("result") != "ok":
        raise ValueError(f"No WRF forecast is available for {place}")
    frame = pd.DataFrame(payload["timeseries"])
    frame["time"] = pd.to_datetime(frame["dateTime"], format="%Y%m%dZ%H%M", utc=True)
    return frame.set_index("time")

def records_frame(payload):
    """Normalize common API list, GeoJSON, and envelope responses."""
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("features"), list):
        records = []
        for feature in payload["features"]:
            record = dict(feature.get("properties", {}))
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) >= 2:
                record.update(longitude=coordinates[0], latitude=coordinates[1])
            records.append(record)
    elif isinstance(payload, dict):
        records = next((payload[key] for key in ("weatherreports", "reports", "data", "results", "items")
                        if isinstance(payload.get(key), list)), [payload])
    else:
        records = []
    return pd.json_normalize(records)

def numeric_snapshot(payload):
    """Return scalar numeric values without assuming a product-specific schema."""
    frame = records_frame(payload)
    if frame.empty:
        return frame
    numeric = frame.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    return numeric

PLACES = {"Gulf of Naples": "ca001", "Gulf of Salerno": "ca002", "Cilento": "ca003"}
'''


def notebook(title: str, purpose: str, body: str, *, parameters: str = "") -> dict:
    cells = [
        markdown(f"# {title}\n\n{purpose}\n\n{INTRO}\n"),
        code(SETUP),
    ]
    if parameters:
        cells.append(code(parameters, tags=["parameters"]))
    cells.append(code(body))
    for index, cell in enumerate(cells):
        identity = f"{title}\0{index}\0{cell['cell_type']}\0{''.join(cell['source'])}"
        cell["id"] = hashlib.sha256(identity.encode()).hexdigest()[:12]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python"},
            "language_info": {"name": "python", "version": "3.13"},
            "voila": {"strip_sources": True, "theme": "light"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


NOTEBOOKS = {
    "01_api_catalog.ipynb": notebook(
        "API and model catalog",
        "Inspect the live service version and compare the atmospheric, marine, wave, water-quality, and AI products published by meteo@uniparthenope.",
        '''output = widgets.Output()
refresh = widgets.Button(description="Refresh catalog", button_style="primary", icon="refresh")

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            version = api_json("version")
            products = api_json("products")["products"]
            rows = []
            for key, product in products.items():
                rows.append({
                    "code": key,
                    "description": product.get("desc", {}).get("en-US", ""),
                    "fields": len(product.get("fields", {})),
                    "outputs": len(product.get("outputs", {})),
                    "forecast steps": product.get("steps"),
                })
            display(HTML(f"<h3>API {version['version']} <small>({version['environment']})</small></h3>"))
            display(pd.DataFrame(rows).sort_values("code").reset_index(drop=True))
        except Exception as exc:
            display(HTML(f"<b>API request failed:</b> {exc}"))

refresh.on_click(render)
display(widgets.VBox([refresh, output]))
render()
''',
    ),
    "02_place_finder.ipynb": notebook(
        "Place finder",
        "Search the geographic catalog, inspect identifiers used by forecast endpoints, and map the matching locations.",
        '''query = widgets.Text(value="Napoli", description="Search:", continuous_update=False)
search = widgets.Button(description="Find places", button_style="primary", icon="search")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            places = api_json(f"places/search/byname/{query.value.strip()}")
            rows = []
            for item in places[:50]:
                lon, lat = item.get("pos", {}).get("coordinates", [np.nan, np.nan])
                name = item.get("long_name", {}).get("it") or item.get("name", {}).get("it", "")
                rows.append({"identifier": item.get("id"), "name": name, "longitude": lon, "latitude": lat})
            frame = pd.DataFrame(rows).dropna(subset=["longitude", "latitude"])
            display(frame)
            if not frame.empty:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.scatter(frame.longitude, frame.latitude, color=ACCENT, edgecolor=BRAND)
                for row in frame.head(12).itertuples():
                    ax.annotate(row.identifier, (row.longitude, row.latitude), xytext=(4, 4), textcoords="offset points")
                ax.set(xlabel="Longitude", ylabel="Latitude", title=f"Matches for {query.value!r}")
                ax.grid(alpha=.25)
                plt.show()
        except Exception as exc:
            display(HTML(f"<b>Search failed:</b> {exc}"))

search.on_click(render)
query.on_submit(render)
display(widgets.VBox([widgets.HBox([query, search]), output]))
render()
''',
    ),
    "03_current_conditions.ipynb": notebook(
        "Current model conditions",
        "Build a compact conditions card from the latest WRF forecast for three Campania coastal domains.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
refresh = widgets.Button(description="Refresh", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            data = api_json(f"products/wrf5/forecast/{place.value}")
            when = pd.to_datetime(data["dateTime"], format="%Y%m%dZ%H%M", utc=True)
            sky = data.get("text", {}).get("en-US", "Unknown")
            html = f"""<div style='border-left:6px solid {ACCENT};padding:1rem;background:#f4f7fa'>
            <h2>{place.label}</h2><p><b>{when:%Y-%m-%d %H:%M UTC}</b> · {sky}</p>
            <p style='font-size:1.35rem'>🌡️ {data['t2c']} °C &nbsp; 💧 {data['rh2']}% &nbsp;
            🌬️ {data['ws10']} m/s {data['winds']} &nbsp; ⏱️ {data['slp']} hPa</p>
            <p>Hourly rain: {data['crh']} mm · Cloud fraction: {data['clf']:.0%} · MCAPE: {data['mcape']} J/kg</p></div>"""
            display(HTML(html))
        except Exception as exc:
            display(HTML(f"<b>Forecast request failed:</b> {exc}"))

place.observe(render, names="value")
refresh.on_click(render)
display(widgets.VBox([widgets.HBox([place, refresh]), output]))
render()
''',
    ),
    "04_temperature_humidity.ipynb": notebook(
        "Temperature and humidity forecast",
        "Explore the hourly WRF near-surface temperature and relative-humidity forecast as a synchronized two-axis time series.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
hours = widgets.IntSlider(value=72, min=24, max=168, step=24, description="Hours:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = forecast_frame(place.value).head(hours.value)
            fig, ax = plt.subplots(figsize=(10, 4.8))
            ax.plot(frame.index, frame.t2c, color="#d95f02", lw=2, label="Temperature")
            ax.set_ylabel("Temperature (°C)", color="#d95f02")
            other = ax.twinx()
            other.plot(frame.index, frame.rh2, color=ACCENT, lw=1.8, label="Relative humidity")
            other.set_ylabel("Relative humidity (%)", color=ACCENT)
            ax.set_title(f"{place.label}: WRF near-surface forecast")
            ax.grid(alpha=.25)
            fig.autofmt_xdate()
            plt.show()
        except Exception as exc:
            display(HTML(f"<b>Forecast request failed:</b> {exc}"))

place.observe(render, names="value")
hours.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, hours]), output]))
render()
''',
    ),
    "05_wind_forecast.ipynb": notebook(
        "Wind forecast explorer",
        "Analyze forecast wind speed and direction, including a polar view that makes direction shifts and stronger periods easy to identify.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
hours = widgets.IntSlider(value=48, min=12, max=168, step=12, description="Hours:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = forecast_frame(place.value).head(hours.value)
            theta = np.deg2rad(frame.wd10.astype(float))
            speed = frame.ws10.astype(float)
            fig = plt.figure(figsize=(9, 5.2))
            polar = fig.add_subplot(121, projection="polar")
            polar.set_theta_zero_location("N")
            polar.set_theta_direction(-1)
            points = polar.scatter(theta, speed, c=np.arange(len(frame)), cmap="viridis", s=35)
            polar.set_title("Direction and speed")
            timeline = fig.add_subplot(122)
            timeline.plot(frame.index, speed, color=BRAND, lw=2)
            timeline.set(ylabel="Wind speed (m/s)", title=place.label)
            timeline.grid(alpha=.25)
            fig.colorbar(points, ax=polar, pad=.12, label="Forecast step")
            fig.autofmt_xdate()
            plt.show()
        except Exception as exc:
            display(HTML(f"<b>Forecast request failed:</b> {exc}"))

place.observe(render, names="value")
hours.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, hours]), output]))
render()
''',
    ),
    "06_rain_clouds.ipynb": notebook(
        "Rain and cloud timeline",
        "Inspect hourly precipitation together with total cloud fraction and summarize wet forecast periods.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
rain_threshold = widgets.FloatSlider(value=1.0, min=0, max=10, step=.5, description="Wet ≥ mm:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = forecast_frame(place.value)
            fig, ax = plt.subplots(figsize=(10, 4.8))
            ax.bar(frame.index, frame.crh, width=.03, color=ACCENT, label="Hourly rain")
            ax.set_ylabel("Rain (mm/hour)")
            cloud = ax.twinx()
            cloud.plot(frame.index, frame.clf * 100, color="#607486", lw=1.5, label="Cloud")
            cloud.set_ylabel("Cloud fraction (%)")
            ax.axhline(rain_threshold.value, color="#d95f02", ls="--", lw=1)
            wet = frame[frame.crh >= rain_threshold.value]
            ax.set_title(f"{place.label}: {len(wet)} forecast hours at or above threshold")
            ax.grid(axis="y", alpha=.25)
            fig.autofmt_xdate()
            plt.show()
            display(wet[["crh", "clf", "t2c", "ws10"]].head(20).rename(columns={"crh": "rain_mm", "clf": "cloud_fraction"}))
        except Exception as exc:
            display(HTML(f"<b>Forecast request failed:</b> {exc}"))

place.observe(render, names="value")
rain_threshold.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, rain_threshold]), output]))
render()
''',
    ),
    "07_upper_air_profile.ipynb": notebook(
        "Forecast upper-air profile",
        "Plot the latest WRF temperature and relative-humidity values on standard pressure levels to examine atmospheric structure.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            data = api_json(f"products/wrf5/forecast/{place.value}")
            levels = np.array([1000, 975, 950, 925, 850, 700, 500, 300])
            temp = np.array([data[f"tc{level}"] for level in levels])
            humidity = np.array([data[f"rh{level}"] for level in levels])
            fig, ax = plt.subplots(figsize=(8, 5.5))
            ax.plot(temp, levels, "o-", color="#d95f02", label="Temperature")
            ax.set(xlabel="Temperature (°C)", ylabel="Pressure (hPa)", title=f"{place.label}: forecast vertical profile")
            ax.set_yscale("log")
            ax.set_yticks(levels, labels=levels)
            ax.invert_yaxis()
            ax.grid(alpha=.25)
            other = ax.twiny()
            other.plot(humidity, levels, "s--", color=ACCENT, label="Relative humidity")
            other.set_xlabel("Relative humidity (%)")
            ax.legend(loc="lower left")
            other.legend(loc="lower right")
            plt.show()
        except Exception as exc:
            display(HTML(f"<b>Profile request failed:</b> {exc}"))

place.observe(render, names="value")
display(widgets.VBox([place, output]))
render()
''',
    ),
    "08_product_field_dictionary.ipynb": notebook(
        "Product field dictionary",
        "Browse the metadata that defines model variables, units, labels, transformations, and aggregation methods.",
        '''product = widgets.Dropdown(options=["wrf5", "ww33", "rm3", "wcm3", "aiq3"], description="Product:")
needle = widgets.Text(description="Filter:", placeholder="temperature, wind, rain…", continuous_update=False)
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            fields = api_json(f"products/{product.value}/fields")["fields"]
            rows = []
            for key, item in fields.items():
                rows.append({
                    "field": key,
                    "title": item.get("title", {}).get("en-US", ""),
                    "label": item.get("label", {}).get("en-US", ""),
                    "unit": item.get("unit", ""),
                    "source variable": item.get("var", ""),
                    "aggregations": ", ".join(item.get("aggregate", [])),
                })
            frame = pd.DataFrame(rows)
            if needle.value.strip():
                mask = frame.astype(str).apply(lambda col: col.str.contains(needle.value, case=False, na=False)).any(axis=1)
                frame = frame[mask]
            display(HTML(f"<h3>{product.value}: {len(frame)} matching fields</h3>"))
            display(frame.reset_index(drop=True))
        except Exception as exc:
            display(HTML(f"<b>Metadata request failed:</b> {exc}"))

product.observe(render, names="value")
needle.on_submit(render)
display(widgets.VBox([widgets.HBox([product, needle]), output]))
render()
''',
    ),
    "09_map_layer_catalog.ipynb": notebook(
        "Interactive-map layer catalog",
        "Inspect the public map-layer configuration, including WMS sources and rendering parameters used by meteo@uniparthenope applications.",
        '''layer = widgets.Dropdown(description="Layer:")
output = widgets.Output()
catalog = {}

def load_catalog():
    global catalog
    catalog = api_json("v2/layers")
    layer.options = sorted(catalog)
    layer.value = layer.options[0]

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            item = catalog[layer.value]
            name = item.get("name", {}).get("en-US", layer.value)
            display(HTML(f"<h2>{name}</h2><p><code>{item.get('type', '')}</code></p>"))
            display(HTML(f"<p style='overflow-wrap:anywhere'><b>Service template:</b> {item.get('url', 'n/a')}</p>"))
            extras = item.get("extras", {})
            display(pd.DataFrame([{"parameter": key, "value": value} for key, value in extras.items()]))
        except Exception as exc:
            display(HTML(f"<b>Layer request failed:</b> {exc}"))

try:
    load_catalog()
    layer.observe(render, names="value")
    display(widgets.VBox([layer, output]))
    render()
except Exception as exc:
    display(HTML(f"<b>Catalog request failed:</b> {exc}"))
''',
    ),
    "10_coastal_area_comparison.ipynb": notebook(
        "Campania coastal forecast comparison",
        "Compare current WRF conditions for the gulfs of Naples and Salerno and the Cilento coast, following the reference use case’s reproducible indicator-and-figure pattern.",
        '''refresh = widgets.Button(description="Compare areas", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            rows = []
            for label, identifier in PLACES.items():
                data = api_json(f"products/wrf5/forecast/{identifier}")
                rows.append({
                    "area": label,
                    "time": pd.to_datetime(data["dateTime"], format="%Y%m%dZ%H%M", utc=True),
                    "temperature_C": data["t2c"],
                    "humidity_pct": data["rh2"],
                    "wind_ms": data["ws10"],
                    "rain_mm": data["crh"],
                    "pressure_hPa": data["slp"],
                })
            frame = pd.DataFrame(rows).set_index("area")
            display(frame)
            axes = frame[["temperature_C", "humidity_pct", "wind_ms", "rain_mm"]].plot.bar(
                subplots=True, layout=(2, 2), figsize=(10, 7), legend=False, color=[BRAND, ACCENT, "#181c63"]
            )
            plt.suptitle("Current WRF indicators across Campania coastal areas")
            plt.tight_layout()
            plt.show()
        except Exception as exc:
            display(HTML(f"<b>Comparison failed:</b> {exc}"))

refresh.on_click(render)
display(widgets.VBox([refresh, output]))
render()
''',
    ),
    "11_model_cycle_inventory.ipynb": notebook(
        "Model cycle inventory",
        "Compare the currently published atmospheric, wave, ocean, water-quality, and AI model products and their forecast horizons.",
        '''refresh = widgets.Button(description="Refresh models", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            products = api_json("products")["products"]
            rows = []
            for code, item in products.items():
                rows.append({"model": code, "description": item.get("desc", {}).get("en-US", ""),
                             "forecast_steps": item.get("steps"), "fields": len(item.get("fields", {})),
                             "map_outputs": len(item.get("outputs", {}))})
            frame = pd.DataFrame(rows).sort_values("model")
            display(frame)
            frame.set_index("model")[["fields", "map_outputs"]].plot.bar(figsize=(9, 4), color=[BRAND, ACCENT])
            plt.title("Published model capabilities"); plt.ylabel("Count"); plt.xticks(rotation=0); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Model catalog temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "12_wrf_heat_stress.ipynb": notebook(
        "WRF heat-stress indicators",
        "Derive humidex-like apparent temperature from the WRF temperature and humidity forecast for a selected Campania coastal area.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
hours = widgets.IntSlider(value=72, min=24, max=168, step=24, description="Hours:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = forecast_frame(place.value).head(hours.value).copy()
            vapor = 6.112 * np.exp((17.67 * frame.t2c) / (frame.t2c + 243.5)) * frame.rh2 / 100
            frame["apparent_C"] = frame.t2c + 0.5555 * (vapor - 10)
            frame[["t2c", "apparent_C"]].plot(figsize=(10, 4.5), color=[BRAND, "#d95f02"])
            plt.title(f"{place.label}: WRF thermal comfort"); plt.ylabel("°C"); plt.grid(alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>WRF forecast temporarily unavailable:</b> {exc}"))

place.observe(render, names="value"); hours.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, hours]), output])); render()
'''),
    "13_wavewatch_snapshot.ipynb": notebook(
        "WaveWatch III model snapshot",
        "Inspect the latest WaveWatch III forecast payload and visualize every numeric sea-state variable returned for the selected coastal area.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            payload = api_json(f"products/ww33/forecast/{place.value}")
            numeric = numeric_snapshot(payload)
            display(pd.DataFrame(records_frame(payload).iloc[:1].T, columns=["value"]))
            if not numeric.empty:
                numeric.iloc[0].dropna().head(16).plot.bar(figsize=(10, 4), color=ACCENT)
                plt.title(f"{place.label}: WaveWatch III numeric fields"); plt.grid(axis="y", alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Wave model temporarily unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "14_roms_ocean_snapshot.ipynb": notebook(
        "ROMS ocean model snapshot",
        "Explore the latest ROMS coastal-dynamics forecast returned by the public API without assuming a fixed variable schema.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            payload = api_json(f"products/rms3/forecast/{place.value}")
            frame = records_frame(payload)
            display(HTML(f"<h3>{place.label} · ROMS coastal dynamics</h3>")); display(frame.T.rename(columns={0: "value"}))
            numeric = numeric_snapshot(payload)
            if not numeric.empty:
                numeric.iloc[0].dropna().head(16).plot.bar(figsize=(10, 4), color=BRAND)
                plt.ylabel("Reported value"); plt.grid(axis="y", alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>ROMS model temporarily unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "15_wacomm_water_quality.ipynb": notebook(
        "WaComM water-quality snapshot",
        "Inspect the latest WaComM inert-tracer transport and diffusion forecast for a Campania coastal area.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            payload = api_json(f"products/wcm3/forecast/{place.value}")
            frame = records_frame(payload)
            display(HTML(f"<h3>{place.label} · WaComM</h3>")); display(frame.T.rename(columns={0: "value"}))
            numeric = numeric_snapshot(payload)
            if not numeric.empty:
                numeric.iloc[0].dropna().head(16).plot.bar(figsize=(10, 4), color="#2a9d8f")
                plt.ylabel("Reported value"); plt.grid(axis="y", alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Water-quality model temporarily unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "16_live_instrument_map.ipynb": notebook(
        "Live instrument network map",
        "Load the latest official weather reports and map instruments whenever the API supplies geographic coordinates.",
        '''refresh = widgets.Button(description="Refresh instruments", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/json"))
            display(HTML(f"<h3>{len(frame)} latest instrument reports</h3>")); display(frame.head(30))
            lon = next((c for c in frame if c.lower() in ("lon", "longitude", "lng")), None)
            lat = next((c for c in frame if c.lower() in ("lat", "latitude")), None)
            if lon and lat:
                plt.figure(figsize=(8, 5)); plt.scatter(frame[lon], frame[lat], c=ACCENT, edgecolor=BRAND)
                plt.xlabel("Longitude"); plt.ylabel("Latitude"); plt.title("Live meteo@uniparthenope instruments"); plt.grid(alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Live instrument service temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "17_live_air_temperature.ipynb": notebook(
        "Live air-temperature observations",
        "Retrieve the newest air-temperature field reported by the meteo@uniparthenope instrument network.",
        '''refresh = widgets.Button(description="Refresh temperature", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/t2c/json"))
            display(frame)
            numeric = numeric_snapshot(frame.to_dict("records"))
            if not numeric.empty: numeric.iloc[:, -1].dropna().plot.hist(bins=15, color="#d95f02", edgecolor="white", title="Latest air-temperature distribution")
            plt.xlabel("Reported value"); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Live temperature temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "18_live_wind.ipynb": notebook(
        "Live wind observations",
        "Refresh the latest wind-speed reports from the official live-instrument endpoint and compare reporting stations.",
        '''refresh = widgets.Button(description="Refresh wind", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/ws10/json"))
            display(frame)
            numeric = numeric_snapshot(frame.to_dict("records"))
            if not numeric.empty: numeric.iloc[:, -1].dropna().head(30).plot.bar(figsize=(10, 4), color=ACCENT, title="Latest wind-speed reports")
            plt.ylabel("Reported value"); plt.grid(axis="y", alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Live wind temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "19_live_pressure.ipynb": notebook(
        "Live atmospheric-pressure observations",
        "Inspect the most recent sea-level pressure observations published by live instruments.",
        '''refresh = widgets.Button(description="Refresh pressure", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/slp/json"))
            display(frame)
            numeric = numeric_snapshot(frame.to_dict("records"))
            if not numeric.empty: numeric.iloc[:, -1].dropna().head(30).plot(marker="o", figsize=(10, 4), color=BRAND, title="Latest pressure reports")
            plt.ylabel("Reported value"); plt.grid(alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Live pressure temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "20_live_instrument_quality.ipynb": notebook(
        "Live instrument freshness and completeness",
        "Audit the newest weather reports for timestamp freshness, missing values, and field completeness.",
        '''refresh = widgets.Button(description="Run quality audit", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/json"))
            summary = pd.DataFrame({"non_null": frame.notna().sum(), "missing": frame.isna().sum(), "coverage_pct": (100 * frame.notna().mean()).round(1)})
            display(HTML(f"<h3>Quality audit · {len(frame)} live reports</h3>")); display(summary.sort_values("coverage_pct"))
            summary.coverage_pct.sort_values().tail(25).plot.barh(figsize=(8, 6), color=ACCENT)
            plt.xlabel("Coverage (%)"); plt.xlim(0, 100); plt.grid(axis="x", alpha=.25); plt.show()
        except Exception as exc:
            display(HTML(f"<b>Live quality audit temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "21_aiq_mussel_intelligence.ipynb": notebook(
        "AIQ mussel-contamination intelligence",
        "Inspect the official AIQ3 machine-learning product, its prediction fields, units, aggregation rules, and published outputs.",
        '''refresh = widgets.Button(description="Inspect AIQ3", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            product = api_json("products")["products"]["aiq3"]
            fields = product.get("fields", {})
            rows = [{"field": key, "label": item.get("label", {}).get("en-US", ""),
                     "unit": item.get("unit", ""), "source": item.get("var", ""),
                     "aggregation": ", ".join(item.get("aggregate", []))}
                    for key, item in fields.items()]
            display(HTML(f"<h3>{product['desc']['en-US']}</h3>")); display(pd.DataFrame(rows))
            display(pd.DataFrame([{"output": key, "configuration": str(value)[:180]}
                                  for key, value in product.get("outputs", {}).items()]))
        except Exception as exc:
            display(HTML(f"<b>AIQ3 metadata temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
    "22_ai_temperature_regression.ipynb": notebook(
        "AI temperature regression",
        "Train and evaluate a transparent linear regression on the live WRF forecast, using forecast hour to estimate near-surface temperature.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = forecast_frame(place.value).dropna(subset=["t2c"]).head(168)
            x = np.arange(len(frame), dtype=float); y = frame.t2c.to_numpy(float)
            split = max(12, int(len(y) * .75)); coef = np.polyfit(x[:split], y[:split], 1)
            prediction = np.polyval(coef, x); rmse = np.sqrt(np.mean((y[split:] - prediction[split:]) ** 2))
            display(pd.DataFrame([{"slope_C_per_hour": coef[0], "intercept_C": coef[1], "test_RMSE_C": rmse}]))
            plt.figure(figsize=(10, 4)); plt.plot(frame.index, y, label="WRF"); plt.plot(frame.index, prediction, label="linear AI model")
            plt.axvline(frame.index[split], color="grey", ls="--", label="test split"); plt.legend(); plt.grid(alpha=.25); plt.title(place.label); plt.show()
        except Exception as exc: display(HTML(f"<b>Regression unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "23_ai_weather_regimes.ipynb": notebook(
        "Unsupervised weather regimes",
        "Use deterministic k-means clustering to discover recurring WRF weather regimes from temperature, humidity, wind, pressure, rain, and cloud cover.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
clusters = widgets.IntSlider(value=3, min=2, max=6, description="Regimes:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            cols = ["t2c", "rh2", "ws10", "slp", "crh", "clf"]
            frame = forecast_frame(place.value)[cols].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            x = (frame - frame.mean()) / frame.std().replace(0, 1); values = x.to_numpy()
            centers = values[np.linspace(0, len(values)-1, clusters.value, dtype=int)]
            for _ in range(30):
                labels = ((values[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
                updated = np.array([values[labels == k].mean(axis=0) if np.any(labels == k) else centers[k] for k in range(clusters.value)])
                if np.allclose(updated, centers): break
                centers = updated
            display(pd.DataFrame(centers, columns=cols).rename_axis("regime").round(2))
            plt.figure(figsize=(10, 3)); plt.scatter(frame.index, frame.t2c, c=labels, cmap="viridis"); plt.ylabel("Temperature (°C)"); plt.title(f"{place.label}: learned weather regimes"); plt.show()
        except Exception as exc: display(HTML(f"<b>Clustering unavailable:</b> {exc}"))

place.observe(render, names="value"); clusters.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, clusters]), output])); render()
'''),
    "24_ai_forecast_anomalies.ipynb": notebook(
        "Multivariate forecast anomaly detection",
        "Detect unusual WRF forecast hours with a robust median absolute-deviation score across key atmospheric variables.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
sensitivity = widgets.FloatSlider(value=3.5, min=2, max=6, step=.5, description="Threshold:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            cols = ["t2c", "rh2", "ws10", "slp", "crh", "clf"]
            frame = forecast_frame(place.value)[cols].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            median = frame.median(); mad = (frame - median).abs().median().replace(0, 1)
            score = ((frame - median).abs() / (1.4826 * mad)).max(axis=1)
            result = frame.assign(anomaly_score=score, anomalous=score >= sensitivity.value)
            display(result.nlargest(12, "anomaly_score"))
            score.plot(figsize=(10, 3.5), color=BRAND); plt.axhline(sensitivity.value, color="#d95f02", ls="--"); plt.ylabel("Robust anomaly score"); plt.grid(alpha=.25); plt.show()
        except Exception as exc: display(HTML(f"<b>Anomaly detection unavailable:</b> {exc}"))

place.observe(render, names="value"); sensitivity.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, sensitivity]), output])); render()
'''),
    "25_ai_pca_weather_space.ipynb": notebook(
        "PCA weather-space explorer",
        "Apply principal component analysis to compress the live WRF forecast and visualize its dominant atmospheric patterns.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            cols = ["t2c", "rh2", "ws10", "slp", "crh", "clf"]
            frame = forecast_frame(place.value)[cols].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            z = ((frame - frame.mean()) / frame.std().replace(0, 1)).to_numpy()
            _, singular, vectors = np.linalg.svd(z, full_matrices=False); projected = z @ vectors[:2].T
            explained = singular ** 2 / np.sum(singular ** 2)
            display(pd.DataFrame(vectors[:2].T, index=cols, columns=["PC1 loading", "PC2 loading"]).round(3))
            display(HTML(f"<b>Explained variance:</b> PC1 {explained[0]:.1%}, PC2 {explained[1]:.1%}"))
            plt.figure(figsize=(7, 5)); plt.scatter(projected[:,0], projected[:,1], c=np.arange(len(frame)), cmap="plasma"); plt.xlabel("PC1"); plt.ylabel("PC2"); plt.title(place.label); plt.colorbar(label="Forecast hour"); plt.show()
        except Exception as exc: display(HTML(f"<b>PCA unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "26_ai_rain_classifier.ipynb": notebook(
        "Rain-event classifier",
        "Train a logistic classifier on WRF humidity, cloud fraction, pressure, and wind to estimate the probability of hourly rain.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
threshold = widgets.FloatSlider(value=.2, min=.05, max=2, step=.05, description="Rain mm:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            cols = ["rh2", "clf", "slp", "ws10"]
            frame = forecast_frame(place.value)[cols + ["crh"]].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            x = ((frame[cols] - frame[cols].mean()) / frame[cols].std().replace(0, 1)).to_numpy(); x = np.c_[np.ones(len(x)), x]
            y = (frame.crh.to_numpy() >= threshold.value).astype(float); weights = np.zeros(x.shape[1])
            for _ in range(600):
                probability = 1 / (1 + np.exp(-np.clip(x @ weights, -30, 30)))
                weights -= .08 * (x.T @ (probability - y) / len(y))
            prediction = probability >= .5; accuracy = np.mean(prediction == y)
            display(pd.DataFrame({"feature": ["intercept"] + cols, "weight": weights.round(3)})); display(HTML(f"<b>Training accuracy:</b> {accuracy:.1%}"))
            pd.Series(probability, index=frame.index).plot(figsize=(10, 3.5), color=ACCENT); plt.ylabel("Rain probability"); plt.ylim(0,1); plt.grid(alpha=.25); plt.show()
        except Exception as exc: display(HTML(f"<b>Rain classifier unavailable:</b> {exc}"))

place.observe(render, names="value"); threshold.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, threshold]), output])); render()
'''),
    "27_ai_analog_forecast.ipynb": notebook(
        "Nearest-neighbor analog forecast",
        "Find forecast hours with the most similar multivariate weather state and present them as explainable analog evidence.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
analogs = widgets.IntSlider(value=5, min=2, max=12, description="Neighbors:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            cols = ["t2c", "rh2", "ws10", "slp", "clf"]
            frame = forecast_frame(place.value)[cols].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            z = ((frame - frame.mean()) / frame.std().replace(0, 1)).to_numpy(); target = z[-1]
            distance = np.sqrt(((z[:-1] - target) ** 2).sum(axis=1)); selected = np.argsort(distance)[:analogs.value]
            table = frame.iloc[selected].copy(); table["distance"] = distance[selected]
            display(HTML(f"<h3>Analogs for {frame.index[-1]}</h3>")); display(table)
            table[cols].plot.bar(subplots=True, layout=(3,2), figsize=(10,8), legend=False); plt.tight_layout(); plt.show()
        except Exception as exc: display(HTML(f"<b>Analog forecast unavailable:</b> {exc}"))

place.observe(render, names="value"); analogs.observe(render, names="value")
display(widgets.VBox([widgets.HBox([place, analogs]), output])); render()
'''),
    "28_ai_svd_sensor_quality.ipynb": notebook(
        "AI-assisted instrument quality control",
        "Use low-rank SVD reconstruction to identify observation fields that behave differently from the dominant live-instrument data structure.",
        '''rank = widgets.IntSlider(value=2, min=1, max=5, description="SVD rank:")
refresh = widgets.Button(description="Audit live reports", button_style="primary", icon="refresh")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            frame = records_frame(api_json("v2/weatherreports/latest/json")); numeric = frame.apply(pd.to_numeric, errors="coerce").dropna(axis=1, thresh=max(2, len(frame)//2))
            filled = numeric.fillna(numeric.median()); z = ((filled - filled.mean()) / filled.std().replace(0,1)).to_numpy()
            u, s, vt = np.linalg.svd(z, full_matrices=False); keep = min(rank.value, len(s)); reconstruction = (u[:,:keep] * s[:keep]) @ vt[:keep]
            error = np.sqrt(((z - reconstruction) ** 2).mean(axis=0)); result = pd.Series(error, index=filled.columns, name="reconstruction_error").sort_values(ascending=False)
            display(result.to_frame()); result.head(20).sort_values().plot.barh(figsize=(8,5), color=ACCENT); plt.title("Fields requiring quality review"); plt.show()
        except Exception as exc: display(HTML(f"<b>Live quality model temporarily unavailable:</b> {exc}"))

rank.observe(render, names="value"); refresh.on_click(render); display(widgets.VBox([widgets.HBox([rank, refresh]), output])); render()
'''),
    "29_ai_forecast_explainability.ipynb": notebook(
        "Explainable temperature model",
        "Fit a multivariate linear model for WRF temperature and rank standardized feature contributions for an interpretable AI baseline.",
        '''place = widgets.Dropdown(options=PLACES, description="Area:")
output = widgets.Output()

def render(*_):
    with output:
        clear_output(wait=True)
        try:
            features = ["rh2", "ws10", "slp", "crh", "clf"]
            frame = forecast_frame(place.value)[features + ["t2c"]].apply(pd.to_numeric, errors="coerce").dropna().head(168)
            xframe = (frame[features] - frame[features].mean()) / frame[features].std().replace(0,1); y = (frame.t2c - frame.t2c.mean()) / frame.t2c.std()
            x = np.c_[np.ones(len(xframe)), xframe.to_numpy()]; weights = np.linalg.pinv(x) @ y.to_numpy(); prediction = x @ weights
            r2 = 1 - np.sum((y - prediction)**2) / np.sum((y - y.mean())**2)
            importance = pd.Series(np.abs(weights[1:]), index=features, name="absolute standardized weight").sort_values()
            display(HTML(f"<b>Training R²:</b> {r2:.3f}")); display(importance.sort_values(ascending=False).to_frame())
            importance.plot.barh(figsize=(8,4), color=BRAND); plt.title("Explainable feature importance"); plt.show()
        except Exception as exc: display(HTML(f"<b>Explainability model unavailable:</b> {exc}"))

place.observe(render, names="value"); display(widgets.VBox([place, output])); render()
'''),
    "30_ai_model_card.ipynb": notebook(
        "AI model card and responsible-use checklist",
        "Generate a reproducible model card for the notebook AI demonstrations using live API provenance, assumptions, limitations, and safety constraints.",
        '''refresh = widgets.Button(description="Generate model card", button_style="primary", icon="refresh")
output = widgets.Output()

def render(_=None):
    with output:
        clear_output(wait=True)
        try:
            version = api_json("version"); products = api_json("products")["products"]
            card = pd.DataFrame([
                ("API provenance", f"meteo@uniparthenope API {version['version']} ({version['environment']})"),
                ("Models represented", ", ".join(sorted(products))),
                ("AI methods", "linear/logistic regression, k-means, robust anomalies, PCA/SVD, nearest neighbors"),
                ("Training scope", "Current forecast cycle or latest public observations; no hidden training corpus"),
                ("Intended use", "Education, research exploration, and method demonstration"),
                ("Prohibited use", "Official warnings, navigation, emergency response, or automated safety decisions"),
                ("Known limitations", "Small non-independent samples, forecast bias, missing observations, concept drift, upstream outages"),
                ("Privacy", "Public environmental data only; browser-local execution; no user data transmitted"),
                ("Reproducibility", "Notebook source is versioned; live results vary by API cycle and observation availability"),
            ], columns=["model-card field", "statement"])
            display(HTML("<h2>Responsible AI model card</h2>")); display(card)
        except Exception as exc: display(HTML(f"<b>Model card provenance temporarily unavailable:</b> {exc}"))

refresh.on_click(render); display(widgets.VBox([refresh, output])); render()
'''),
}


def main() -> None:
    DEMO_DIR.mkdir(exist_ok=True)
    for filename, content in NOTEBOOKS.items():
        target = DEMO_DIR / filename
        target.write_text(json.dumps(content, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(NOTEBOOKS)} notebooks in {DEMO_DIR}")


if __name__ == "__main__":
    main()
