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

import os

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agents.context import build_context
from .agents.editorial_planner import run_editorial_planner
from .agents.pipeline import run_script_pipeline
from .agents.qa import run_qa
from .agents.research_compiler import run_research_compiler
from .agents.script_writer import run_script_writer
from .agents.trend_scout import run_trend_scout
from .agents.topic_scorer import run_topic_scorer
from .config import get_settings
from .db import cursor, ping
from .events import log_pipeline_event, log_system_event
from .production.pipeline import run_finalize, run_production_pipeline
from .production.render_worker import run_render_worker
from .production.thumbnail_designer import run_thumbnail_designer
from .production.visual_director import run_visual_director
from .production.voice_producer import run_voice_producer
from .intelligence import autonomy
from .intelligence.learning import run_learning
from .intelligence.shorts import run_shorts_derivation
from .intelligence.strategist import run_growth_strategist
from .publishing import quota
from .publishing.analytics import run_analytics_analyst
from .publishing.publisher import run_publisher
from .publishing.seo import run_seo_optimizer
from .services.research_poll import run_research_sweep
from .state_machine import transition

app = FastAPI(title="PhoneWala Gyan Worker", version=__version__)

# Serve rendered media (voiceover, scene cards, thumbnails, final video) for the dashboard.
_media_dir = get_settings().media_dir
os.makedirs(_media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_dir), name="media")

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

# Jobs implemented now. Each takes an optional `limit` and returns a summary dict.
# `limit` caps how many items an LLM-backed job processes — useful to stay under
# free-tier rate limits on a manual run.
JOBS: dict[str, Callable[[int], dict[str, Any]]] = {
    # Phase 1
    "research_sweep": lambda limit: run_research_sweep(),
    "trend_scout": lambda limit: run_trend_scout(build_context(), limit=limit),
    "topic_scorer": lambda limit: run_topic_scorer(build_context(), limit=limit),
    # Phase 2 — script factory
    "editorial_planner": lambda limit: run_editorial_planner(build_context(), limit=limit),
    "research_compiler": lambda limit: run_research_compiler(build_context(), limit=limit),
    "script_writer": lambda limit: run_script_writer(build_context(), limit=limit),
    "qa": lambda limit: run_qa(build_context(), limit=limit),
    "script_pipeline": lambda limit: run_script_pipeline(build_context(), limit=limit),
    # Phase 3 — production (no LLM)
    "voice_producer": lambda limit: run_voice_producer(limit=limit),
    "visual_director": lambda limit: run_visual_director(limit=limit),
    "render_worker": lambda limit: run_render_worker(limit=limit),
    "thumbnail_designer": lambda limit: run_thumbnail_designer(limit=limit),
    "finalize": lambda limit: run_finalize(limit=limit),
    "production_pipeline": lambda limit: run_production_pipeline(limit=limit),
    # Phase 4 — publish + analytics
    "seo_optimizer": lambda limit: run_seo_optimizer(limit=limit),
    "publisher": lambda limit: run_publisher(limit=limit),
    "analytics_analyst": lambda limit: run_analytics_analyst(limit=limit),
    # Phase 5 — intelligence
    "learning": lambda limit: run_learning(limit=limit),
    "growth_strategist": lambda limit: run_growth_strategist(limit=limit),
    "shorts_derive": lambda limit: run_shorts_derivation(limit=limit),
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
def run_job(job: str, limit: int = 200) -> Any:
    if job in JOBS:
        try:
            return {"job": job, "result": JOBS[job](limit)}
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


# ---- Phase 2: script factory ----

_SCRIPT_STAGE = ("scripting", "script_qa", "qa_failed", "script_approved")


@app.get("/scripts")
def scripts(limit: int = 100) -> dict[str, Any]:
    """Content items in the script stage with their latest script + QA report."""
    with cursor() as cur:
        cur.execute(
            """
            select ci.id, ci.working_title, ci.angle, ci.format, ci.status, ci.priority,
                   s.version, s.hook, s.body_markdown, s.cta,
                   s.word_count, s.est_duration_sec, s.language_mix,
                   q.passed, q.claims_checked, q.claims_failed, q.policy_flags,
                   q.readability_notes,
                   (select status from approvals a
                      where a.content_item_id = ci.id and a.gate = 'script'
                      order by created_at desc limit 1) as approval_status
            from content_items ci
            left join lateral (
                select * from scripts sc where sc.content_item_id = ci.id
                order by sc.version desc limit 1
            ) s on true
            left join lateral (
                select * from script_qa_reports r where r.script_id = s.id
                order by r.created_at desc limit 1
            ) q on true
            where ci.status = any(%s)
            order by ci.priority desc, ci.created_at asc
            limit %s
            """,
            (list(_SCRIPT_STAGE), limit),
        )
        return {"scripts": cur.fetchall()}


@app.post("/content/{content_id}/script-decision")
def script_decision(
    content_id: str,
    action: str = Body(..., embed=True),
    note: str | None = Body(None, embed=True),
) -> dict[str, Any]:
    """Human script gate: approve a QA-passed script, send it back, or reject it."""
    if action not in ("approve", "request_changes", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve|request_changes|reject")

    with cursor() as cur:
        cur.execute("select status from content_items where id = %s", (content_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="content item not found")
    status = row["status"]

    def _decide(decision: str) -> None:
        with cursor() as cur:
            cur.execute(
                """
                update approvals set status = %s, reviewer_note = %s, decided_at = now()
                where id = (select id from approvals where content_item_id = %s and gate = 'script'
                            order by created_at desc limit 1)
                """,
                (decision, note, content_id),
            )

    if action == "approve":
        if status != "script_approved":
            raise HTTPException(status_code=409, detail="only a script_approved item can be approved")
        _decide("approved")
        log_pipeline_event(content_item_id=content_id, from_status=status, to_status=status,
                           actor="human:rj", detail={"gate": "script", "decision": "approved"})
        return {"id": content_id, "status": status, "approval": "approved"}

    if action == "reject":
        transition(content_item_id=content_id, to_status="rejected", actor="human:rj",
                   detail={"gate": "script", "note": note})
        _decide("rejected")
        return {"id": content_id, "status": "rejected", "approval": "rejected"}

    # request_changes: record human note as a failed QA report, bounce to qa_failed for revision.
    if status not in ("script_approved", "qa_failed"):
        raise HTTPException(status_code=409, detail="cannot request changes from this status")
    with cursor() as cur:
        cur.execute(
            "select id from scripts where content_item_id = %s order by version desc limit 1",
            (content_id,),
        )
        srow = cur.fetchone()
        if srow:
            cur.execute(
                """
                insert into script_qa_reports
                  (script_id, passed, claims_checked, claims_failed, policy_flags, readability_notes)
                values (%s, false, 0, '[]', '[]', %s)
                """,
                (srow["id"], note or "Human requested changes."),
            )
    if status == "script_approved":
        transition(content_item_id=content_id, to_status="qa_failed", actor="human:rj",
                   detail={"gate": "script", "note": note})
    _decide("changes_requested")
    return {"id": content_id, "status": "qa_failed", "approval": "changes_requested"}


# ---- Phase 3: production / Studio ----

_STUDIO_STAGE = ("script_approved", "voiceover", "assembly", "thumbnail", "metadata", "ready_for_review")


@app.get("/studio")
def studio(limit: int = 50) -> dict[str, Any]:
    """Content items in the production stage with their media artifacts for the Studio view."""
    with cursor() as cur:
        cur.execute(
            """
            select ci.id, ci.working_title, ci.format, ci.status, ci.priority,
                   vo.storage_path as voiceover_path, vo.duration_sec::float8 as voiceover_duration,
                   fv.storage_path as video_path, fv.duration_sec::float8 as video_duration,
                   sp.scenes,
                   (select json_agg(json_build_object(
                              'variant', t.variant, 'path', m.storage_path,
                              'selected', t.is_selected, 'concept', t.concept)
                            order by t.variant)
                      from thumbnails t join media_assets m on m.id = t.asset_id
                      where t.content_item_id = ci.id) as thumbnails
            from content_items ci
            left join lateral (
                select storage_path, duration_sec from media_assets
                where content_item_id = ci.id and kind = 'voiceover'
                order by created_at desc limit 1
            ) vo on true
            left join lateral (
                select storage_path, duration_sec from media_assets
                where content_item_id = ci.id and kind = 'final_video'
                order by created_at desc limit 1
            ) fv on true
            left join lateral (
                select scenes from scene_plans where content_item_id = ci.id
                order by created_at desc limit 1
            ) sp on true
            where ci.status = any(%s)
            order by ci.priority desc, ci.created_at asc
            limit %s
            """,
            (list(_STUDIO_STAGE), limit),
        )
        return {"studio": cur.fetchall()}


# ---- Phase 4: publish + analytics ----

_PUBLISH_STAGE = ("ready_for_review", "approved", "scheduled", "publishing", "published")


@app.get("/publish")
def publish_queue(limit: int = 50) -> dict[str, Any]:
    settings = get_settings()
    with cursor() as cur:
        cur.execute(
            """
            select ci.id, ci.working_title, ci.status, ci.priority,
                   se.title, cardinality(se.tags) as tag_count,
                   (select storage_path from media_assets where content_item_id = ci.id
                      and kind = 'final_video' order by created_at desc limit 1) as video_path,
                   pj.method, pj.status as publish_status, pj.youtube_video_id, pj.error as publish_note,
                   (select status from approvals a where a.content_item_id = ci.id and a.gate = 'publish'
                      order by created_at desc limit 1) as approval_status
            from content_items ci
            left join lateral (
                select title, tags from seo_metadata where content_item_id = ci.id
                order by created_at desc limit 1
            ) se on true
            left join lateral (
                select method, status, youtube_video_id, error from publish_jobs
                where content_item_id = ci.id order by id desc limit 1
            ) pj on true
            where ci.status = any(%s)
            order by ci.priority desc, ci.created_at asc
            limit %s
            """,
            (list(_PUBLISH_STAGE), limit),
        )
        rows = cur.fetchall()
    for r in rows:
        r["kit_path"] = f"{r['id']}/publish_kit.zip" if r.get("method") == "manual_kit" else None
    return {
        "quota": {
            "used": quota.units_used_today(),
            "remaining": quota.remaining(),
            "daily": settings.youtube_daily_quota,
            "youtube_ready": settings.youtube_ready,
        },
        "items": rows,
    }


@app.post("/content/{content_id}/publish-decision")
def publish_decision(content_id: str, action: str = Body(..., embed=True),
                     note: str | None = Body(None, embed=True)) -> dict[str, Any]:
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve|reject")
    with cursor() as cur:
        cur.execute("select status from content_items where id = %s", (content_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="content item not found")
    if row["status"] != "ready_for_review":
        raise HTTPException(status_code=409, detail="only a ready_for_review item can be decided")

    if action == "approve":
        transition(content_item_id=content_id, to_status="approved", actor="human:rj",
                   detail={"gate": "publish"})
        with cursor() as cur:
            cur.execute(
                "insert into approvals (content_item_id, gate, status, reviewer_note, decided_at) "
                "values (%s, 'publish', 'approved', %s, now())",
                (content_id, note),
            )
        return {"id": content_id, "status": "approved", "approval": "approved"}

    transition(content_item_id=content_id, to_status="rejected", actor="human:rj",
               detail={"gate": "publish", "note": note})
    with cursor() as cur:
        cur.execute(
            "insert into approvals (content_item_id, gate, status, reviewer_note, decided_at) "
            "values (%s, 'publish', 'rejected', %s, now())",
            (content_id, note),
        )
    return {"id": content_id, "status": "rejected", "approval": "rejected"}


@app.get("/videos")
def videos(limit: int = 50) -> dict[str, Any]:
    with cursor() as cur:
        cur.execute(
            """
            select yv.youtube_video_id, yv.published_at, yv.format,
                   ci.working_title,
                   m.views, m.watch_time_min, m.avg_pct_viewed::float8 as avg_pct_viewed,
                   m.likes, m.comments, m.date as metrics_date
            from youtube_videos yv
            left join content_items ci on ci.id = yv.content_item_id
            left join lateral (
                select * from video_metrics_daily d where d.youtube_video_id = yv.youtube_video_id
                order by date desc limit 1
            ) m on true
            order by yv.published_at desc nulls last
            limit %s
            """,
            (limit,),
        )
        return {"videos": cur.fetchall()}


# ---- Phase 5: intelligence + autonomy ----


@app.get("/insights")
def insights(limit: int = 50) -> dict[str, Any]:
    with cursor() as cur:
        cur.execute(
            "select id, scope, ref_id, insight, confidence, applied, created_at "
            "from insights order by created_at desc limit %s",
            (limit,),
        )
        ins = cur.fetchall()
        cur.execute(
            "select id, type, title, detail, expected_impact, status, created_at "
            "from recommendations order by created_at desc limit %s",
            (limit,),
        )
        recs = cur.fetchall()
    return {"insights": ins, "recommendations": recs}


@app.get("/autonomy")
def autonomy_get() -> dict[str, Any]:
    return {"gates": autonomy.get_autonomy(), "guardrails": autonomy.guardrail_status()}


@app.post("/autonomy")
def autonomy_set(gate: str = Body(..., embed=True), mode: str = Body(..., embed=True)) -> dict[str, Any]:
    try:
        row = autonomy.set_autonomy(gate, mode)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"gate": row["gate"], "mode": row["mode"]}
