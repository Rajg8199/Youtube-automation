#!/usr/bin/env bash
# Phase 0 acceptance demo:
#   1. clean migration from scratch (db-reset)
#   2. schema verification (tables + indexes + seed)
#   3. worker /health returns 200 green
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose --env-file .env -f infra/docker-compose.yml"

# Honor WORKER_PORT from .env so the host curl matches the published port.
WORKER_PORT="$(grep -E '^WORKER_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' ')"
WORKER_PORT="${WORKER_PORT:-8000}"
HEALTH_URL="http://localhost:${WORKER_PORT}/health"

echo "############################################"
echo "# PhoneWala Gyan — Phase 0 acceptance demo #"
echo "############################################"

echo
echo ">> [1/3] Clean migration (db-reset)"
make --no-print-directory db-reset

echo
echo ">> [2/3] Schema verification"
make --no-print-directory db-verify

echo
echo ">> [3/3] Worker /health  (${HEALTH_URL})"
$COMPOSE up -d --build worker
echo "  waiting for worker..."
ok=""
for i in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/tmp/pwg_health.json 2>/dev/null; then ok=1; break; fi
  sleep 2
done
[[ -n "$ok" ]] || { echo "FAIL: worker /health never came up"; $COMPOSE logs worker | tail -30; exit 1; }
cat /tmp/pwg_health.json
echo
grep -q '"status": *"ok"' /tmp/pwg_health.json && grep -q '"db": *"up"' /tmp/pwg_health.json \
  || { echo "FAIL: worker health not green"; exit 1; }

echo
echo "PHASE 0 ACCEPTANCE: PASS ✅"
