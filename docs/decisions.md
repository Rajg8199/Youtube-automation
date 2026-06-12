# Architecture Decision Records

Format: one ADR per decision. Status: Accepted unless noted.

---

## ADR-0001 — Budget tier is the default
**Status:** Accepted
**Context:** Spec §13 targets <$50/month. The system must run cheaply by default and only
escalate to premium providers deliberately.
**Decision:** `STACK_TIER=budget` is the default everywhere (worker config, compose, .env).
Budget = Claude Haiku/Sonnet mix, Sarvam/Edge TTS, Remotion-only, no Perplexity/gen-video.
**Consequences:** Premium adapters exist behind the same interfaces but are off unless
`STACK_TIER=premium`.

---

## ADR-0002 — Worker runtime: Python 3.11 + FastAPI
**Status:** Accepted
**Context:** Spec leaves "Python or Node — pick one, justify." Workers do research scraping,
embeddings, TTS/render orchestration, and analytics.
**Decision:** Python 3.11+ with FastAPI for the internal API and job consumers.
**Justification:** Strongest ecosystem for ML/data (embeddings, pandas, feed parsing),
clean subprocess control for FFmpeg/Remotion, mature YouTube/Google client libs. The
dashboard stays Next.js/TypeScript; shared enums are duplicated (see ADR-0006).
**Consequences:** Two languages in the repo. Cost/state-machine logic is mirrored and
kept in sync by tests.

---

## ADR-0003 — Package manager: pnpm (via corepack)
**Status:** Accepted
**Context:** Monorepo with multiple TS workspaces.
**Decision:** pnpm workspaces. Where pnpm isn't globally installed, the Makefile invokes
`corepack pnpm@9.12.0` (no global symlink needed — avoids the macOS /usr/local perms issue).
**Consequences:** Contributors need Node 20+ with corepack (bundled).

---

## ADR-0004 — Job queue: Graphile Worker (Postgres-backed)
**Status:** Accepted
**Context:** Spec says "Postgres-backed job queue (pg-boss / Graphile Worker) — no Redis."
**Decision:** Graphile Worker.
**Justification:** Pure Postgres (`LISTEN/NOTIFY`), strong typing, good operational story,
no extra infra. We already depend on Postgres heavily.
**Consequences:** Queue tasks register from the Python worker via the `graphile_worker`
schema; Phase 0 only bootstraps the schema (no tasks yet).

---

## ADR-0005 — Local DB via pgvector Docker image, not the Supabase CLI
**Status:** Accepted
**Context:** Acceptance criterion is "clean migration from scratch." The Supabase CLI was
not installed on the target machine, and it pulls a large local stack.
**Decision:** Phase 0 runs `pgvector/pgvector:pg16` in docker-compose and applies the SQL
migrations with `psql`-in-container (`make db-reset`). Production uses Supabase cloud; the
migrations are plain SQL and remain Supabase-CLI compatible (`supabase/migrations/`).
**Consequences:** `make db-reset` is the local equivalent of `supabase db reset`. When the
Supabase CLI is available, the same migration files work unchanged.

---

## ADR-0006 — Cost & state-machine logic duplicated across TS and Python
**Status:** Accepted
**Context:** Both the TS dashboard/packages and the Python worker need pricing + the content
state machine.
**Decision:** Maintain parallel implementations: `packages/shared/src/cost.ts` ↔
`apps/worker/app/costs.py`; state machine in `packages/shared/src/state-machine.ts` (Python
mirror added when the worker first needs it). Unit tests on both sides assert identical
numbers/transitions.
**Consequences:** Small duplication cost; avoids a cross-language RPC for pure functions.
If drift becomes a problem, generate one from the other.

---

## ADR-0007 — Embedding dimension fixed at 1024
**Status:** Accepted (constraint inherited from spec schema)
**Context:** All `vector` columns are `vector(1024)`.
**Decision:** Standardize on a 1024-dim embedding model (e.g. Sarvam embeddings or a
Cohere/Matryoshka model truncated to 1024). Provider stays unwired in Phase 0.
**Consequences:** Whatever embedding provider Phase 1 picks must output (or be reduced to)
exactly 1024 dims, or the migration changes.
