# Architecture

## Monorepo map
```
apps/
  dashboard/   Next.js 14 control plane (Phase 0: /system only)
  worker/      FastAPI internal API + job consumers (Python 3.11)
packages/
  db/          SQL migrations (supabase/migrations) + table constants
  agents/      LLM agents + versioned prompts (Phase 1+)
  providers/   tts/ video/ research/ publish/ adapter interfaces + mocks
  remotion/    video compositions + brand kit (Phase 3)
  shared/      types, zod schemas, constants, cost + state-machine
n8n/           workflow JSON exports (Phase 1+)
infra/         docker-compose, Dockerfiles, backups
docs/          decisions (ADRs), runbook, architecture, voice guide
```

## Data flow (target, full system)
```
sources ──poll──> raw_signals ──cluster──> topics ──score──> topic_scores
   │                                                              │
   └────────────────────── Editorial Planner ◄───────────────────┘
                                  │
                          content_items (state machine)
   research_briefs → scripts → script_qa_reports → media_assets/scene_plans
        → thumbnails → seo_metadata → publish_jobs → youtube_videos
        → video_metrics_daily / retention_curves → insights → recommendations
```

## Phase 0 runtime
```
docker compose:  db (pgvector) ──> worker (FastAPI :8000 /health, /jobs/{agent})
Vercel-bound:    dashboard (Next.js) ──fetch──> worker /health  (/system page)
```

## n8n boundary
Workflows are thin (schedule/webhook/branch/notify). All business logic lives behind the
worker's `POST /jobs/{agent}` endpoints so it is testable outside n8n. The 15 agents and
10 workflows are specified in the master prompt §6/§7 and built Phases 1–5.

## State machine
`content_items.status` has 19 states. Legal transitions are enforced in
`packages/shared/src/state-machine.ts` (single source of truth) and mirror the DB CHECK
constraint in `0003_pipeline.sql`. Every transition writes a `pipeline_events` row.
```
