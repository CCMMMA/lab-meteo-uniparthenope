# Reproducibility

## Public API demonstrations

The ten notebooks in `demos/` are generated from `scripts/build_demo_notebooks.py`. They use the
public meteo@uniparthenope API configured by `METEO_API_BASE_URL`; consequently, their numerical
results change with each forecast cycle and upstream catalog revision. The notebooks record no
transient outputs in Git and use explicit request timeouts and UTC parsing.

Regenerate and execute them in the pinned runtime with:

```bash
python3 scripts/build_demo_notebooks.py
mkdir -p /tmp/wxhub-demo-executed
docker run --rm \
  -e METEO_API_BASE_URL=https://api.meteo.uniparthenope.it \
  -v "$PWD/demos:/home/jovyan/demos:ro" \
  -v /tmp/wxhub-demo-executed:/home/jovyan/executed \
  wxhub-singleuser:check bash -lc \
  'for notebook in /home/jovyan/demos/*.ipynb; do jupyter nbconvert --execute --to notebook \
  --ExecutePreprocessor.timeout=90 --output-dir /home/jovyan/executed "$notebook"; done'
```

Executed copies are verification artifacts and must not be committed.

The anonymous environment is built from the pinned dependencies and image digests in
`demos/Dockerfile`. `docker compose build demos` generates the static JupyterLite application and
indexes the ten notebooks. In that environment, Pyodide executes Python in the browser and calls
the fixed public API URL directly; results still vary with the live forecast cycle.

## Contract

The repository fixes source code, direct and newly resolved Python dependencies, dated upstream
images, and immutable base-image digests. Given the same architecture and access to external
repositories, build inputs are repeatable. Exact output image IDs can still vary with architecture,
system package mirrors, and Docker build metadata.

The analysis also depends on a remote data service. `fetch_wrf_d03.py` writes hourly files atomically
and records SHA-256 checksums in `manifest.csv`. Preserve that manifest with published results. The
source weather data is not redistributed here.

## End-to-end procedure

1. Record `git rev-parse HEAD`, then run `./scripts/validate_repo.sh`.
2. Build both images and record their `docker image inspect` IDs.
3. Download the five-day WRF range from the README.
4. Confirm 120 available hours and no error statuses in the manifest.
5. Execute `notebooks/wrf_campania_case_study.ipynb` with Papermill or JupyterLab.
6. Preserve `results.json`, `figures/`, the Zarr store, and the source manifest.
7. Open `wrf_voila_dashboard.ipynb` against the generated Zarr store.

## Scientific derivations

- 2 m temperature: `T2 - 273.15` °C.
- 10 m wind speed: `hypot(U10, V10)`.
- Hourly rain: the difference of `RAINC + RAINNC`; after a model-cycle reset, use the current
  cumulative value.
- City series: nearest WRF grid point after a longitude cosine correction.

Expected artifacts are `manifest.csv`, `results.json`, `figures/*.png`, and
`wrf_campania_curated.zarr/`. Network availability and upstream retention are outside this project's
control. Archive the source subset under terms compatible with IODL 2.0 for durable reproduction.
