# Public notebook demonstrations

These ten output-free notebooks are published in an anonymous JupyterLite workspace. Visitors can
open, edit, execute, upload, download, and save notebook copies in browser-local storage, much like
a lightweight Colab session. Python runs in a Pyodide WebAssembly kernel inside the visitor's
browser, never in the deployment container. The public meteo@uniparthenope API supports the live
examples through CORS.

The notebooks follow the reference use-case pattern: parameters and controls, explicit provenance,
live data acquisition, derived indicators, visual results, and stated limitations. Run
`python3 scripts/build_demo_notebooks.py` after changing their source definitions.

| Notebook | Demonstration |
|---|---|
| `01_api_catalog.ipynb` | API version and model-product inventory |
| `02_place_finder.ipynb` | Geographic catalog search and location plot |
| `03_current_conditions.ipynb` | Latest WRF conditions card |
| `04_temperature_humidity.ipynb` | Temperature and humidity forecast |
| `05_wind_forecast.ipynb` | Wind speed and polar direction analysis |
| `06_rain_clouds.ipynb` | Rain threshold and cloud timeline |
| `07_upper_air_profile.ipynb` | Standard-pressure-level profile |
| `08_product_field_dictionary.ipynb` | Model field, unit, and aggregation metadata |
| `09_map_layer_catalog.ipynb` | WMS layer and rendering configuration |
| `10_coastal_area_comparison.ipynb` | Naples, Salerno, and Cilento comparison |

Forecasts and derived values are automatically generated and are not official warnings or
navigation guidance. All times are UTC.
