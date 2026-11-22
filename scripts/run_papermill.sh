#!/usr/bin/env bash
# Esecuzione non interattiva e parametrizzata del caso d'uso WRF (da terminale JupyterLab).
# Esempio: ./run_papermill.sh 2026-11-15T00 2026-11-15T23 Salerno
set -euo pipefail
START="${1:-2026-11-13T00}"; END="${2:-2026-11-17T23}"; CITY="${3:-Positano}"
OUT="$HOME/work/outputs/wrf_${START%%T*}_${CITY,,}"
mkdir -p "$OUT"
papermill "$HOME/work/notebooks/caso_uso_wrf_campania.ipynb" "$OUT/eseguito.ipynb" \
  -p start "$START" -p end "$END" -p focus_city "$CITY" -p output_dir "$OUT"
echo "Risultati in $OUT (risultati.json, figure/, *.zarr)"
