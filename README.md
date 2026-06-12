# PhoneWala Gyan — Autonomous YouTube Content System

Semi-autonomous content pipeline for a Hindi/Hinglish smartphone channel: research →
ideate → score → script → fact-check → voice → assemble → thumbnail → optimize → publish
→ analyze → learn, with human approval gates that progressively disable ("autonomy as a
dial").

> **Status: Phase 0 (Foundations) complete.** Monorepo, DB schema + migrations, provider
> interfaces, cost logger, local docker-compose, and the acceptance demo. Phases 1–5
> (agents, n8n workflows, Remotion, publishing, learning loop) are scaffolded but not built.

## Quickstart
```bash
cp .env.example .env
make demo-phase-0     # clean migrate + verify schema + worker /health green
```
Requires: Docker + docker compose, Node 20+ (corepack), uv (for Python tests).

## Layout
See [docs/architecture.md](docs/architecture.md). Key decisions: [docs/decisions.md](docs/decisions.md).
Operations: [docs/runbook.md](docs/runbook.md). Script voice: [docs/voice-guide.md](docs/voice-guide.md).

## Make targets
| Target | Description |
|---|---|
| `make demo-phase-0` | Phase 0 acceptance: clean migration + schema check + worker health |
| `make up` / `make down` | start / stop db + worker |
| `make db-reset` | drop public schema, re-apply all migrations in order |
| `make db-verify` | assert tables, HNSW indexes, seed data |
| `make test` | TS (vitest) + Python (pytest) unit tests |
| `make typecheck` | typecheck TS workspaces |

## Stack
n8n (orchestration) · Claude Haiku/Sonnet/Opus (LLM) · Remotion+FFmpeg (render) ·
Sarvam/ElevenLabs/Edge (TTS) · Supabase Postgres+pgvector (data) · Next.js (dashboard) ·
Python FastAPI (worker) · Graphile Worker (queue) · YouTube Data + Analytics APIs.
Toggle providers with `STACK_TIER=budget|premium`.
