#!/usr/bin/env bash
# Import PhoneWala Gyan workflow JSONs into a running n8n instance.
#
# Usage:
#   Local CLI (n8n on the same host):   ./import.sh cli
#   REST API (set N8N_URL + N8N_API_KEY): ./import.sh api
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-cli}"
FILES=(WF*.json)

case "$MODE" in
  cli)
    for f in "${FILES[@]}"; do
      echo ">> importing $f via n8n CLI"
      n8n import:workflow --input="$f"
    done
    ;;
  api)
    : "${N8N_URL:?set N8N_URL e.g. http://localhost:5678}"
    : "${N8N_API_KEY:?set N8N_API_KEY}"
    for f in "${FILES[@]}"; do
      echo ">> POSTing $f to $N8N_URL/api/v1/workflows"
      curl -fsS -X POST "$N8N_URL/api/v1/workflows" \
        -H "X-N8N-API-KEY: $N8N_API_KEY" \
        -H "Content-Type: application/json" \
        --data-binary @"$f" >/dev/null && echo "   ok"
    done
    ;;
  *)
    echo "unknown mode: $MODE (use 'cli' or 'api')" >&2
    exit 2
    ;;
esac
echo "Done. Workflows import inactive — review and activate in the n8n UI."
