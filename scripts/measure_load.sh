#!/usr/bin/env bash
# Measure container CPU/memory and case-study execution time for N concurrent users.
# Run this script on the HOST.
#
# Prerequisites: bench01..benchNN servers are running (from the Admin page or with
#   python3 scripts/measure_spawn.py --users N --runs 1 --keep), and WRF data exists
#   under data/raw/models/wrf5_d03 (see scripts/fetch_wrf_d03.py).
# Usage: ./scripts/measure_load.sh 3      -> results under measurements/load_3users_*.csv
set -euo pipefail
N="${1:-1}"
if ! [[ "$N" =~ ^[1-9][0-9]*$ ]]; then
  echo "Usage: $0 <positive-user-count>" >&2
  exit 2
fi
OUTDIR="measurements"; mkdir -p "$OUTDIR"
TS=$(date +%Y%m%d_%H%M%S)
STATS="$OUTDIR/load_${N}users_${TS}_docker_stats.csv"
TIMES="$OUTDIR/load_${N}users_${TS}_times.csv"

# 1) Record hardware information.
{ echo "# $(date)"; lscpu | grep -E 'Model name|^CPU\(s\)'; free -h | head -2; docker info --format 'Docker {{.ServerVersion}}'; } \
  > "$OUTDIR/hardware_${TS}.txt"

# 2) Idle baseline (10 samples).
echo "timestamp,container,cpu_percent,memory_usage,memory_percent,phase" > "$STATS"
for i in $(seq 10); do
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
    | grep -E 'jupyter-|lab-jupyterhub' | sed "s/^/$(date +%s),/;s/$/,idle/" >> "$STATS"
done

# 3) Sample in the background during the load test.
( while true; do
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
      | grep -E 'jupyter-|lab-jupyterhub' | sed "s/^/$(date +%s),/;s/$/,load/" >> "$STATS"
  done ) &
SAMPLER=$!
trap 'kill "$SAMPLER" 2>/dev/null || true' EXIT INT TERM

# 3b) Copy the notebook into each test user's container.
for i in $(seq -f "%02g" 1 "$N"); do
  docker exec "jupyter-bench$i" mkdir -p /home/jovyan/work/notebooks
  docker cp notebooks/wrf_campania_case_study.ipynb "jupyter-bench$i":/home/jovyan/work/notebooks/
done

# 4) Run the notebook concurrently in N containers.
echo "user,elapsed_seconds,status" > "$TIMES"
PIDS=()
for i in $(seq -f "%02g" 1 "$N"); do
  ( t0=$(date +%s.%N)
    if docker exec "jupyter-bench$i" papermill --log-level ERROR \
         /home/jovyan/work/notebooks/wrf_campania_case_study.ipynb /tmp/out.ipynb \
         -p output_dir /home/jovyan/work/outputs/bench >/dev/null 2>&1; then e=ok; else e=error; fi
    echo "bench$i,$(echo "$(date +%s.%N) - $t0" | bc),$e" >> "$TIMES" ) &
  PIDS+=("$!")
done
wait "${PIDS[@]}"
kill "$SAMPLER" 2>/dev/null || true
trap - EXIT INT TERM

echo "Execution times:"; column -s, -t "$TIMES"
echo "Docker statistics written to $STATS"
