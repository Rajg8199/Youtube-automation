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

## ADR-0007 — Embeddings: BGE-M3 self-hosted (1024-dim)
**Status:** Accepted (supersedes the Phase 0 placeholder)
**Context:** All `vector` columns are `vector(1024)`. We needed an Indic/Hindi-capable
1024-dim embedder that fits the budget tier. **Sarvam was the first choice but has no
embeddings API** — its endpoints are chat, translation, STT, TTS, transliteration, and
language ID only (verified: https://docs.sarvam.ai/api-reference-docs/introduction).
**Decision:** Use **BGE-M3** (BAAI), self-hosted in the worker via sentence-transformers.
1024-dim native, strong multilingual incl. Hindi, MIT-licensed, **zero per-call cost**.
**Justification:** Keeps the budget tier genuinely cheap (no embedding line item), India-
capable, and removes an external dependency/key from the hot path. Premium tier may later
swap in Cohere `embed-multilingual-v3.0` (also 1024-dim native) behind the same interface.
**Consequences:** The worker image gains a model download (~2GB) and CPU/torch deps; we add
an `EmbeddingProvider` interface (mock + bge-m3 adapter) so the model is swappable and tests
run without it. If RAM on the Oracle ARM VM is tight, run embeddings as a separate small
service (documented in the runbook when Phase 1 deploys).

---

## ADR-0008 — `free` tier: Gemini (free) LLM for a $0/month pipeline
**Status:** Accepted
**Context:** Every component except the LLM is already free in the budget tier (BGE-M3
embeddings, Edge TTS, Remotion render, RSS/Reddit research, Supabase/Oracle/Vercel free
tiers, YouTube API). The LLM was the only real cost. User asked for a zero-spend option.
**Decision:** Add a third tier `STACK_TIER=free` that routes all agents to **Google Gemini**
free tier (`gemini-2.0-flash` for classify, `gemini-2.5-flash` for scoring/scripts/strategy)
via the official `google-genai` SDK, behind the existing `LLMClient` protocol. `budget`/
`premium` stay on Claude. Selection is `Settings.llm_provider` (free→gemini, else→anthropic)
and a tier-aware `model_for(role)`.
**Justification:** Gemini Flash has a genuinely usable free quota (well above 5 long + 10
shorts/week) and strong Hindi/Hinglish. It is the best quality-per-$0 for this channel.
**Non-Claude note:** per the claude-api skill, `GeminiClient` is plain provider code (the
Google SDK), not Anthropic SDK code — a deliberate, user-requested non-Claude implementation.
**Consequences:** Free-tier rate limits and weaker output on the hardest task (Hinglish
*script writing*, Phase 2) — a Claude-for-scripts hybrid (~$2–5/mo) is the documented
fallback. `google-genai` is an optional extra (`uv sync --extra gemini`), lazy-imported so
tests/default install don't need it. Gemini model IDs are priced at $0 in the cost calculator
(free within quota); review Google's free-tier terms (rate limits, data-use, commercial use).
