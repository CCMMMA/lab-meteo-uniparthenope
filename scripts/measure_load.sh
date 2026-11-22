#!/usr/bin/env bash
# Misura CPU/memoria dei container e il tempo di esecuzione del caso d'uso con N utenti
# che lo eseguono contemporaneamente. Da lanciare sull'HOST.
#
# Prerequisiti: server degli utenti bench01..benchNN avviati (es. dalla pagina Admin o con
#   python3 scripts/measure_spawn.py --users N --runs 1 --keep),
#   dati WRF presenti in data/raw/models/wrf5_d03 (scripts/fetch_wrf_d03.py).
# Uso: ./scripts/measure_load.sh 3        -> risultati in misure/carico_3utenti_*.csv
set -euo pipefail
N="${1:-1}"
OUTDIR="misure"; mkdir -p "$OUTDIR"
TS=$(date +%Y%m%d_%H%M%S)
STATS="$OUTDIR/carico_${N}utenti_${TS}_docker_stats.csv"
TIMES="$OUTDIR/carico_${N}utenti_${TS}_tempi.csv"

# 1) informazioni sull'hardware (da riportare nella tesi)
{ echo "# $(date)"; lscpu | grep -E 'Model name|^CPU\(s\)'; free -h | head -2; docker info --format 'Docker {{.ServerVersion}}'; } \
  > "$OUTDIR/hardware_${TS}.txt"

# 2) baseline a riposo (10 campioni)
echo "timestamp,container,cpu_perc,mem_usage,mem_perc,fase" > "$STATS"
for i in $(seq 10); do
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
    | grep -E 'jupyter-|wxhub-jupyterhub' | sed "s/^/$(date +%s),/;s/$/,riposo/" >> "$STATS"
done

# 3) campionamento in background durante il carico
( while true; do
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
      | grep -E 'jupyter-|wxhub-jupyterhub' | sed "s/^/$(date +%s),/;s/$/,carico/" >> "$STATS"
  done ) &
SAMPLER=$!

# 3b) copia del notebook nei container degli utenti di test
for i in $(seq -f "%02g" 1 "$N"); do
  docker exec "jupyter-bench$i" mkdir -p /home/jovyan/work/notebooks
  docker cp notebooks/caso_uso_wrf_campania.ipynb "jupyter-bench$i":/home/jovyan/work/notebooks/
done

# 4) esecuzione contemporanea del notebook in N container
echo "utente,tempo_s,esito" > "$TIMES"
PIDS=()
for i in $(seq -f "%02g" 1 "$N"); do
  ( t0=$(date +%s.%N)
    if docker exec "jupyter-bench$i" papermill --log-level ERROR \
         /home/jovyan/work/notebooks/caso_uso_wrf_campania.ipynb /tmp/out.ipynb \
         -p output_dir /home/jovyan/work/outputs/bench >/dev/null 2>&1; then e=ok; else e=errore; fi
    echo "bench$i,$(echo "$(date +%s.%N) - $t0" | bc),$e" >> "$TIMES" ) &
  PIDS+=($!)
done
wait "${PIDS[@]}"
kill $SAMPLER 2>/dev/null || true

echo "Tempi di esecuzione:"; column -s, -t "$TIMES"
echo "Campioni docker stats in $STATS"
