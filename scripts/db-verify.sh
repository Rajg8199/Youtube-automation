#!/usr/bin/env bash
# Assert the schema is fully present: extensions, table count, key indexes, seed rows.
set -euo pipefail

COMPOSE="docker compose --env-file .env -f infra/docker-compose.yml"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-phonewala}"

q() { $COMPOSE exec -T db psql -tAX -U "$DB_USER" -d "$DB_NAME" -c "$1"; }

echo "== Extensions =="
exts=$(q "select string_agg(extname,',' order by extname) from pg_extension where extname in ('vector','pgcrypto');")
echo "  $exts"
[[ "$exts" == *vector* && "$exts" == *pgcrypto* ]] || { echo "FAIL: missing extensions"; exit 1; }

echo "== Tables =="
tables=$(q "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE';")
echo "  base tables: $tables"
[[ "$tables" -eq 30 ]] || { echo "FAIL: expected 30 tables, got $tables"; exit 1; }

echo "== HNSW vector indexes =="
hnsw=$(q "select count(*) from pg_indexes where schemaname='public' and indexdef ilike '%using hnsw%';")
echo "  hnsw indexes: $hnsw"
[[ "$hnsw" -eq 5 ]] || { echo "FAIL: expected 5 HNSW indexes, got $hnsw"; exit 1; }

echo "== Status index present =="
hasidx=$(q "select count(*) from pg_indexes where schemaname='public' and indexname='idx_content_items_status';")
[[ "$hasidx" -eq 1 ]] || { echo "FAIL: content_items(status) index missing"; exit 1; }

echo "== Seed data =="
srcs=$(q "select count(*) from sources;")
gates=$(q "select count(*) from autonomy_settings where mode='manual';")
echo "  sources: $srcs | manual gates: $gates"
[[ "$srcs" -ge 9 ]] || { echo "FAIL: expected >=9 sources, got $srcs"; exit 1; }
[[ "$gates" -eq 3 ]] || { echo "FAIL: expected 3 manual autonomy gates, got $gates"; exit 1; }

echo "ALL DB CHECKS PASSED"
