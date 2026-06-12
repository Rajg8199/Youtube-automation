# Runbook

## Local quickstart
```bash
cp .env.example .env          # already done if .env exists
make demo-phase-0             # clean migrate + verify schema + worker /health
make demo-phase-1             # research -> >=30 deduped scored topics (mock providers)
```

## Phase 1 — research → scored topics
Run the pipeline live (worker on :8008, mock providers by default in `.env`):
```bash
make up
curl -X POST localhost:8008/jobs/research_sweep   # poll RSS/Reddit -> raw_signals
curl -X POST localhost:8008/jobs/trend_scout      # cluster -> topics (needs LLM to classify)
curl -X POST localhost:8008/jobs/topic_scorer     # score topics (needs LLM)
```
Dashboard Research Queue: `WORKER_URL=http://localhost:8008 pnpm --filter @pwg/dashboard dev`
then open `/research` (greenlight/reject, factor breakdown, signal firehose).

**Provider modes** (`.env`): keyless dev uses `USE_MOCK_PROVIDERS=true` + `EMBEDDINGS_BACKEND=mock`.
Production: set `USE_MOCK_PROVIDERS=false`, `EMBEDDINGS_BACKEND=bge-m3`, and `ANTHROPIC_API_KEY`.
With mock LLM, `trend_scout` still creates topics but `topic_scorer` needs a real key (the
mock returns no factor scores) — use `make demo-phase-1` for the deterministic full-path proof.

### Known limitation — Reddit sources 403
Reddit blocks the generic bot User-Agent on `*/new.json` (returns 403); the 3 Reddit
sources fail gracefully (logged as `warn` in `system_events`) while the 6 RSS sources work.
Fix in a later pass: Reddit OAuth app credentials or a compliant UA + backoff.

### Dashboard gotcha
Do NOT inline `WORKER_URL` via `next.config.mjs` `env` — that bakes a build-time constant.
Server components read `process.env.WORKER_URL` at runtime (`apps/dashboard/lib/worker.ts`).
Postgres `numeric` serializes as a JSON string; the API casts score columns to `float8`.
Individual targets:
```bash
make up         # start db + worker
make db-reset   # drop public schema, re-apply all migrations in order
make db-verify  # assert tables/indexes/seed
make test       # TS + Python unit tests
make down       # stop everything
```

## Failure recovery (Phase 0 scope)

| Symptom | Likely cause | Fix |
|---|---|---|
| `make db-reset` hangs on "Waiting for Postgres" | db container slow/unhealthy | `docker compose -f infra/docker-compose.yml logs db`; ensure port `${DB_PORT}` free |
| `psql: could not connect` | db not up | `make db-up` first; check `docker ps` |
| worker `/health` returns 503, `db: down` | worker can't reach Postgres | confirm `DATABASE_URL` uses host `db` inside compose; restart worker |
| HNSW index errors on migrate | pgvector missing/old | image must be `pgvector/pgvector:pg16`; 0001 must run first |
| pnpm not found | no global pnpm | Makefile falls back to `corepack pnpm@9.12.0`; ensure Node 20+ |

## Secret rotation
Secrets live only in `.env` (gitignored). To rotate: update the value, restart the worker
(`docker compose ... up -d worker`). Cloud secrets (Supabase, YouTube refresh token) rotate
in their respective consoles; update `.env` and redeploy. Nightly `pg_dump` → Oracle Object
Storage (`infra/backup/pg_dump.sh`, wired in Phase 4 deploy).

## Kill switch
Phase 5 adds the global automation kill switch (pauses n8n schedules + job consumers).
Until then, `make down` stops the worker and DB.
