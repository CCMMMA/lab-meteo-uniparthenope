# Public notebook demonstrations

These thirty output-free notebooks are published in an anonymous JupyterLite workspace. Visitors
arrive at a Colab-style gallery (`/services/demos/`) generated at image build time by
`build_gallery.py` from each notebook's first Markdown cell; every card opens its notebook in the
lab through `lab/index.html?path=<file>`. The gallery is written to `gallery.html` because
JupyterLite reads its configuration from the root `index.html`.

 Visitors can
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
| `11_model_cycle_inventory.ipynb` | Published model capabilities and horizons |
| `12_wrf_heat_stress.ipynb` | WRF apparent-temperature indicators |
| `13_wavewatch_snapshot.ipynb` | WaveWatch III sea-state snapshot |
| `14_roms_ocean_snapshot.ipynb` | ROMS coastal-dynamics snapshot |
| `15_wacomm_water_quality.ipynb` | WaComM tracer and water-quality snapshot |
| `16_live_instrument_map.ipynb` | Latest instrument reports and map |
| `17_live_air_temperature.ipynb` | Live air-temperature observations |
| `18_live_wind.ipynb` | Live wind observations |
| `19_live_pressure.ipynb` | Live atmospheric-pressure observations |
| `20_live_instrument_quality.ipynb` | Observation freshness and completeness audit |
| `21_aiq_mussel_intelligence.ipynb` | Official AIQ3 mussel-contamination product metadata |
| `22_ai_temperature_regression.ipynb` | Linear temperature regression and holdout error |
| `23_ai_weather_regimes.ipynb` | Unsupervised k-means weather regimes |
| `24_ai_forecast_anomalies.ipynb` | Robust multivariate forecast anomalies |
| `25_ai_pca_weather_space.ipynb` | PCA compression and weather-space exploration |
| `26_ai_rain_classifier.ipynb` | Logistic rain-event classification |
| `27_ai_analog_forecast.ipynb` | Nearest-neighbor analog forecasting |
| `28_ai_svd_sensor_quality.ipynb` | SVD-assisted live-instrument quality control |
| `29_ai_forecast_explainability.ipynb` | Interpretable feature importance |
| `30_ai_model_card.ipynb` | Responsible-use model card and provenance |

Notebooks 16–20 use the official live weather-report endpoints. They display a clear temporary
unavailability message when the upstream observation service is slow or offline.

Notebooks 21–30 demonstrate artificial-intelligence methods over public meteo@uniparthenope data.
They implement compact NumPy/Pandas baselines directly in the notebook so learners can inspect every
training and inference step. They are educational models, not operational forecasts or warning
systems, and they do not call a generative-AI service or use a hidden training dataset.

Forecasts and derived values are automatically generated and are not official warnings or
navigation guidance. All times are UTC.
