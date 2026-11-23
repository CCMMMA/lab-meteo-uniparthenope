#!/usr/bin/env bash
# Run fast, offline repository checks before committing.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

python3 -m py_compile scripts/*.py demos/build_gallery.py jupyterhub/jupyterhub_config.py \
  jupyterhub/wxhub_ext/*.py
bash -n scripts/*.sh
python3 scripts/validate_repo.py
python3 scripts/test_wxhub_ext.py
git diff --check

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh
else
  echo "SKIP: shellcheck is unavailable"
fi
