# Runbook

## Local quickstart
```bash
cp .env.example .env          # already done if .env exists
make demo-phase-0             # clean migrate + verify schema + worker /health
```
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
