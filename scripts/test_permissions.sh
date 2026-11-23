#!/usr/bin/env bash
# Run in a JupyterLab terminal to verify data-area permissions (tests T07-T09).
# Shared archives and templates must be read-only; only ~/work may be writable.
set -u
failures=0
check() {  # $1 = path, $2 = expected mode (ro|rw), $3 = optional (1 = skip when absent)
  if [ ! -d "$1" ]; then
    if [ "${3:-0}" = 1 ]; then
      printf "%-32s expected=%s actual=absent   SKIPPED\n" "$1" "$2"
      return
    fi
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
check /home/jovyan/data/opendap     ro 1
check /home/jovyan/data/network     ro 1
check /home/jovyan/templates        ro
check /home/jovyan/work             rw
echo "--- effective mounts ---"
grep -E '/home/jovyan/(data|templates|work)' /proc/mounts | awk '{print $2, $4}' | cut -c1-80
echo "--- privilege escalation ---"
if grep -q '^NoNewPrivs:[[:space:]]*1' /proc/self/status; then
  echo "no-new-privileges          PASSED"
else
  echo "no-new-privileges          FAILED"; failures=$((failures + 1))
fi
if grep -q '^CapEff:[[:space:]]*0000000000000000' /proc/self/status; then
  echo "no effective capabilities  PASSED"
else
  echo "no effective capabilities  FAILED"; failures=$((failures + 1))
fi
exit "$failures"
