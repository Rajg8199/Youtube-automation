"""FastAPI internal API for the PhoneWala Gyan worker.

Phase 0:
  GET  /health
Phase 1 (research -> scored topics):
  POST /jobs/{job}            research_sweep | trend_scout | topic_scorer  (n8n calls these)
  GET  /topics/scored         scored topics + latest factor breakdown + rationale
  GET  /signals/recent        raw-signal firehose
  POST /topics/{id}/decision  greenlight | reject
Other agents still return 501 until their phase.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import __version__
from .agents.context import build_context
from .agents.trend_scout import run_trend_scout
from .agents.topic_scorer import run_topic_scorer
from .config import get_settings
from .db import cursor, ping
from .events import log_system_event
from .services.research_poll import run_research_sweep

app = FastAPI(title="PhoneWala Gyan Worker", version=__version__)

# Agents that will own /jobs endpoints across Phases 1-5 (404 vs 501 distinction).
KNOWN_AGENTS: frozenset[str] = frozenset(
    {
        "trend_scout",
        "topic_scorer",
        "editorial_planner",
        "research_compiler",
        "script_writer",
        "qa",
        "voice_producer",
        "visual_director",
        "render_worker",
        "thumbnail_designer",
        "seo_optimizer",
        "publisher",
        "analytics_analyst",
        "growth_strategist",
        "orchestrator",
    }
)

# Jobs implemented now. Each returns a JSON-serializable summary dict.
JOBS: dict[str, Callable[[], dict[str, Any]]] = {
    "research_sweep": lambda: run_research_sweep(),
    "trend_scout": lambda: run_trend_scout(build_context()),
    "topic_scorer": lambda: run_topic_scorer(build_context()),
}


@app.get("/health")
def health() -> JSONResponse:
    settings = get_settings()
    try:
        db_ok = ping()
    except Exception:  # noqa: BLE001
        db_ok = False
    code = 200 if db_ok else 503
    return JSONResponse(
        status_code=code,
        content={
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "stack_tier": settings.stack_tier,
            "db": "up" if db_ok else "down",
        },
    )


@app.post("/jobs/{job}")
def run_job(job: str) -> Any:
    if job in JOBS:
        try:
            return {"job": job, "result": JOBS[job]()}
        except Exception as e:  # noqa: BLE001
            log_system_event(
                severity="error", component=f"job:{job}", message="job failed", detail={"error": str(e)}
            )
            raise HTTPException(status_code=500, detail=f"job '{job}' failed: {e}")
    if job in KNOWN_AGENTS:
        raise HTTPException(status_code=501, detail=f"agent '{job}' not implemented yet")
    raise HTTPException(status_code=404, detail=f"unknown job: {job}")


@app.get("/topics/scored")
def topics_scored(limit: int = 100) -> dict[str, Any]:
    with cursor() as cur:
        cur.execute(
            """
            select t.id, t.title, t.category, t.devices, t.brands, t.summary,
                   t.status, t.created_at, t.expires_at,
                   cardinality(t.signal_ids) as signal_count,
                   s.composite::float8 as composite, s.rationale,
                   s.trend_velocity::float8 as trend_velocity,
                   s.search_demand::float8 as search_demand,
                   s.competition_gap::float8 as competition_gap,
                   s.channel_fit::float8 as channel_fit,
                   s.monetization_potential::float8 as monetization_potential,
                   s.freshness::float8 as freshness,
                   s.predicted_views_score::float8 as predicted_views_score,
                   s.scored_at
            from topics t
            join lateral (
                select * from topic_scores ts
                where ts.topic_id = t.id
                order by ts.scored_at desc
                limit 1
            ) s on true
            where t.status in ('scored','selected')
            order by s.composite desc
            limit %s
            """,
            (limit,),
        )
        return {"topics": cur.fetchall()}


@app.get("/signals/recent")
def signals_recent(limit: int = 100) -> dict[str, Any]:
    with cursor() as cur:
        cur.execute(
            """
            select rs.id, rs.title, rs.url, rs.published_at, rs.fetched_at,
                   rs.processed, src.name as source
            from raw_signals rs
            left join sources src on src.id = rs.source_id
            order by rs.fetched_at desc
            limit %s
            """,
            (limit,),
        )
        return {"signals": cur.fetchall()}


_DECISION_STATUS = {"greenlight": "selected", "reject": "rejected"}


@app.post("/topics/{topic_id}/decision")
def topic_decision(topic_id: str, action: str = Body(..., embed=True)) -> dict[str, Any]:
    if action not in _DECISION_STATUS:
        raise HTTPException(status_code=400, detail="action must be 'greenlight' or 'reject'")
    new_status = _DECISION_STATUS[action]
    with cursor() as cur:
        cur.execute(
            "update topics set status = %s where id = %s returning id, status",
            (new_status, topic_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return {"id": str(row["id"]), "status": row["status"]}
