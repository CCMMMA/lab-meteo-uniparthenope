#!/usr/bin/env bash
# Da eseguire nel TERMINALE di JupyterLab: verifica i permessi delle aree dati (test T07-T09).
set -u
failures=0
check() {  # $1 = percorso, $2 = atteso (ro|rw)
  if [ ! -d "$1" ]; then
    printf "%-32s atteso=%s ottenuto=assente  FALLITO\n" "$1" "$2"
    failures=$((failures + 1))
    return
  fi
  f="$1/.wxhub_write_test_$$"
  if touch "$f" 2>/dev/null; then got=rw; rm -f "$f"; else got=ro; fi
  if [ "$got" = "$2" ]; then esito=SUPERATO; else esito=FALLITO; failures=$((failures + 1)); fi
  printf "%-32s atteso=%s ottenuto=%s  %s\n" "$1" "$2" "$got" "$esito"
}
check /home/jovyan/data/raw/sensors ro
check /home/jovyan/data/raw/models  ro
check /home/jovyan/data/curated     ro
check /home/jovyan/templates        ro
check /home/jovyan/work             rw
echo "--- mount effettivi ---"
grep -E '/home/jovyan/(data|templates|work)' /proc/mounts | awk '{print $2, $4}' | cut -c1-80
exit "$failures"
