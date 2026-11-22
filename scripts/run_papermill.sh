#!/usr/bin/env bash
# Non-interactive, parameterized WRF case-study run from a JupyterLab terminal.
# Example: ./run_papermill.sh 2026-11-15T00 2026-11-15T23 Salerno
set -euo pipefail
START="${1:-2026-11-13T00}"; END="${2:-2026-11-17T23}"; CITY="${3:-Positano}"
OUT="$HOME/work/outputs/wrf_${START%%T*}_${CITY,,}"
mkdir -p "$OUT"
papermill "$HOME/work/notebooks/wrf_campania_case_study.ipynb" "$OUT/executed.ipynb" \
  -p start "$START" -p end "$END" -p focus_city "$CITY" -p output_dir "$OUT"
echo "Results written to $OUT (results.json, figures/, *.zarr)"
