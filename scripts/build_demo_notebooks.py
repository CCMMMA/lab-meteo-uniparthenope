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
}


def main() -> None:
    DEMO_DIR.mkdir(exist_ok=True)
    for filename, content in NOTEBOOKS.items():
        target = DEMO_DIR / filename
        target.write_text(json.dumps(content, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(NOTEBOOKS)} notebooks in {DEMO_DIR}")


if __name__ == "__main__":
    main()
