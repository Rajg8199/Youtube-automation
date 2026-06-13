# n8n workflows

Thin schedulers: each workflow is a cron/interval trigger → HTTP POST to the worker's
`/jobs/{name}` endpoint. All business logic lives in the worker (testable outside n8n).
Because the worker's jobs are idempotent batch jobs over content statuses, the whole pipeline
runs by polling on a schedule.

## Run n8n

```bash
docker compose -f infra/docker-compose.yml up -d n8n      # http://localhost:5678
```

n8n reaches the worker at `http://worker:8000` on the compose network (set via `WORKER_URL`).

## Import + activate

```bash
cd n8n
N8N_URL=http://localhost:5678 N8N_API_KEY=<key from n8n UI: Settings → API> ./import.sh api
# or, with the n8n CLI available on the host:
./import.sh cli
```

Workflows import **inactive**. Open each in the n8n UI and toggle **Active** to start its
schedule. (Activate WF4 Gate Router only once you've set the autonomy gates the way you want —
see the dashboard `/insights` dial; on `manual` it no-ops and humans approve in the dashboard.)

## The workflows

| File | Trigger | Worker jobs (in order) |
|---|---|---|
| WF1 Research Sweep      | every 2h        | `research_sweep` → `trend_scout` |
| WF2 Score & Plan        | 06:00 IST daily | `topic_scorer` → `editorial_planner` |
| WF3 Production Line      | every 20 min    | `research_compiler` → `script_pipeline` → `production_pipeline` → `seo_optimizer` |
| WF4 Gate Router          | every 10 min    | `gate_router` (auto-advances script/publish gates per the autonomy dial) |
| WF5 Publish             | every 30 min    | `publisher` (API upload or manual kit) |
| WF6 Analytics Ingest    | 09:00 IST daily | `analytics_analyst` → `learning` |
| WF7 Weekly Strategy     | Sun 10:00 IST   | `growth_strategist` |
| WF8 Health & Costs      | hourly          | `GET /health` (monitor) |
| WF10 Shorts Derivation  | every 6h        | `shorts_derive` (9:16) |

**WF9 Competitor Watch** is intentionally not shipped — the competitor-uploads ingest agent
isn't built yet (the `competitors` / `competitor_videos` tables exist for it). Add the
`competitor_watch` worker job first, then a WF9 JSON mirroring this pattern.

## How autonomy interacts

- Gates default to **manual**: WF3 produces up to a script, then waits — a human approves on
  `/scripts` (script gate) and `/publish` (publish gate).
- Set a gate to **auto_with_veto** / **full_auto** on `/insights`, and WF4 advances it
  automatically, so WF3 → WF5 flow end-to-end without clicks. `full_auto` is guardrail-gated
  (≥20 published, ≥95% QA pass, 0 policy flags/30d).
