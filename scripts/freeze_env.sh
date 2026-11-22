#!/usr/bin/env bash
# Congela le versioni effettive delle librerie installate nell'immagine utente.
set -euo pipefail
docker run --rm --entrypoint pip wxhub-singleuser:latest freeze > image/requirements.lock
docker image inspect wxhub-singleuser:latest --format '{{.Id}}' > image/IMAGE_ID
echo "Creati image/requirements.lock e image/IMAGE_ID"
