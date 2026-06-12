# n8n workflows

Exported workflow JSONs land here (Phase 1+). Workflows are **thin**: scheduling,
webhooks, branching, notifications. Business logic lives behind the worker's
`POST /jobs/{agent}` endpoints so it stays testable outside n8n.

Planned (master spec §7):

| File | Trigger | Purpose |
|---|---|---|
| WF1_research_sweep.json    | every 2h        | poll sources → Trend Scout → cluster topics |
| WF2_score_and_plan.json    | 06:00 IST daily | Topic Scorer → Editorial Planner → slate |
| WF3_production_line.json   | status webhook  | research→script→QA→voice→scenes→render→thumb→SEO |
| WF4_approval_router.json   | approval webhook| route approve / changes_requested |
| WF5_publish.json           | scheduler+quota | Publisher → verify |
| WF6_analytics_ingest.json  | 09:00 IST daily | metrics + retention + comments → insights |
| WF7_weekly_strategy.json   | Sun 10:00 IST   | Growth Strategist → report → recommendations |
| WF8_health_costs.json      | hourly          | Orchestrator checks → alerts |
| WF9_competitor_watch.json  | every 6h        | competitor uploads → gap analysis |
| WF10_shorts_derivation.json| on long publish | derive 9:16 shorts |

Import script (`n8n/import.sh`) added when the first workflow is exported.
