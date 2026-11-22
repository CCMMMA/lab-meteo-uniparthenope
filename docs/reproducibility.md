# Reproducibility

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
