#!/usr/bin/env bash
# Nightly logical backup → Oracle Object Storage (wired in Phase 4 deploy).
# Phase 0: local dump to ./backups for verification.
set -euo pipefail

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$OUT_DIR"

: "${DATABASE_URL:?set DATABASE_URL}"
pg_dump "$DATABASE_URL" -Fc -f "${OUT_DIR}/phonewala_${STAMP}.dump"
echo "wrote ${OUT_DIR}/phonewala_${STAMP}.dump"

# TODO(Phase 4): upload to Oracle Object Storage, prune local copies > 14d.
