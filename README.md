# PhoneWala Gyan — Autonomous YouTube Content System

Semi-autonomous content pipeline for a Hindi/Hinglish smartphone channel: research →
ideate → score → script → fact-check → voice → assemble → thumbnail → optimize → publish
→ analyze → learn, with human approval gates that progressively disable ("autonomy as a
dial").

> **Status: Phases 0–1 complete.**
> - **Phase 0 (Foundations):** monorepo, DB schema + migrations, provider interfaces, cost
>   logger, docker-compose, acceptance demo.
> - **Phase 1 (Research → Scored Topics):** Trend Scout + Topic Scorer agents, BGE-M3/mock
>   embeddings, RSS/Reddit polling, WF1/WF2 n8n workflows, and the `/research` dashboard.
> - **Phase 2 (Script Factory):** Editorial Planner, Research Compiler, Script Writer, QA
>   hard-gate (+revise loop), Python state machine, and the `/scripts` dashboard + script gate.
> - **Phase 3 (Production):** Voice Producer (Edge TTS), deterministic Visual Director, Pillow
>   scene cards + FFmpeg render → 1080p MP4 + subtitles, Thumbnail Designer, and `/studio`.
>
> Phases 4–5 (publishing + analytics, learning loop) are scaffolded, not built.

## Quickstart
```bash
cp .env.example .env
make demo-phase-0     # clean migrate + verify schema + worker /health green
make demo-phase-1     # research -> >=30 deduped scored topics w/ rationale (no API keys)
```
Requires: Docker + docker compose, Node 20+ (corepack), uv (for Python tests).

## Layout
See [docs/architecture.md](docs/architecture.md). Key decisions: [docs/decisions.md](docs/decisions.md).
Operations: [docs/runbook.md](docs/runbook.md). Script voice: [docs/voice-guide.md](docs/voice-guide.md).

## Make targets
| Target | Description |
|---|---|
| `make demo-phase-0` | Phase 0 acceptance: clean migration + schema check + worker health |
| `make demo-phase-1` | Phase 1 acceptance: research → ≥30 deduped scored topics (mock providers) |
| `make demo-phase-2` | Phase 2 acceptance: greenlit topic → QA-passed Hinglish script (mock LLM) |
| `make demo-phase-3` | Phase 3 acceptance: approved script → 1080p video + thumbnails + subtitles (in-container) |
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
