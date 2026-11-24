#!/usr/bin/env bash
# Record the effective package versions and image identifier for audit purposes.
set -euo pipefail
docker run --rm --entrypoint pip lab-singleuser:latest freeze > image/requirements.lock
docker image inspect lab-singleuser:latest --format '{{.Id}}' > image/IMAGE_ID
echo "Created image/requirements.lock and image/IMAGE_ID"
