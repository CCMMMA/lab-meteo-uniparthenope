#!/usr/bin/env bash
# Run in a JupyterLab terminal to verify data-area permissions (tests T07-T09).
set -u
failures=0
check() {  # $1 = path, $2 = expected mode (ro|rw)
  if [ ! -d "$1" ]; then
    printf "%-32s expected=%s actual=missing  FAILED\n" "$1" "$2"
    failures=$((failures + 1))
    return
  fi
  f="$1/.wxhub_write_test_$$"
  if touch "$f" 2>/dev/null; then got=rw; rm -f "$f"; else got=ro; fi
  if [ "$got" = "$2" ]; then result=PASSED; else result=FAILED; failures=$((failures + 1)); fi
  printf "%-32s expected=%s actual=%s  %s\n" "$1" "$2" "$got" "$result"
}
check /home/jovyan/data/raw/sensors ro
check /home/jovyan/data/raw/models  ro
check /home/jovyan/data/curated     ro
check /home/jovyan/templates        ro
check /home/jovyan/work             rw
echo "--- effective mounts ---"
grep -E '/home/jovyan/(data|templates|work)' /proc/mounts | awk '{print $2, $4}' | cut -c1-80
exit "$failures"
