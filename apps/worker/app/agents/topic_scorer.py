"""Topic Scorer (Sonnet): score `new` topics on six factors + composite + rationale.

The LLM judges five demand/opportunity factors. `channel_fit` is computed by the system
via pgvector similarity to the channel's published winners (neutral 0.5 until there is
history — Phase 1 has none). `predicted_views_score` stays neutral until the Phase 5
learning loop. Composite is the weighted blend in scoring.composite.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from ..costs import log_agent_run
from ..db import cursor
from ..events import log_system_event
from .context import AgentContext
from .prompts import load_prompt
from .scoring import DEFAULT_WEIGHTS, FactorScores, composite

AGENT = "agent:topic_scorer"
_PROMPT = "topic_scorer_v1"


def _fetch_new_topics(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select id, title, category, devices, brands, summary, signal_ids,
               created_at, embedding
        from topics
        where status = 'new'
        order by created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _channel_fit(cur, topic_id: str) -> float:
    """Similarity of this topic to the channel's published videos. 0.5 with no history."""
    cur.execute("select count(*) as n from youtube_videos where topic_embedding is not null")
    if cur.fetchone()["n"] == 0:
        return 0.5
    cur.execute(
        """
        select max(1 - (yv.topic_embedding <=> t.embedding)) as fit
        from youtube_videos yv, topics t
        where t.id = %s and yv.topic_embedding is not null and t.embedding is not null
        """,
        (topic_id,),
    )
    row = cur.fetchone()
    return float(row["fit"]) if row and row["fit"] is not None else 0.5


def _age_hours(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    return round(max(0.0, (now - created_at).total_seconds() / 3600.0), 1)


def _score_one(ctx: AgentContext, topic: dict[str, Any]) -> dict[str, Any]:
    model = ctx.settings.model_for("script")  # Sonnet
    payload = json.dumps(
        {
            "topic_title": topic["title"],
            "category": topic["category"],
            "devices": topic.get("devices") or [],
            "brands": topic.get("brands") or [],
            "summary": topic.get("summary") or "",
            "signal_count": len(topic.get("signal_ids") or []),
            "age_hours": _age_hours(topic["created_at"]),
        }
    )
    t0 = time.time()
    resp = ctx.llm.complete(system=load_prompt(_PROMPT), prompt=payload, model=model)
    latency_ms = int((time.time() - t0) * 1000)
    log_agent_run(
        agent=AGENT,
        content_item_id=None,
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=latency_ms,
    )
    return resp.json()


def run_topic_scorer(ctx: AgentContext, *, limit: int = 200) -> dict[str, int]:
    scored = errors = 0
    with cursor() as cur:
        topics = _fetch_new_topics(cur, limit)

    for topic in topics:
        try:
            j = _score_one(ctx, topic)
            with cursor() as cur:
                fit = _channel_fit(cur, topic["id"])
                fs = FactorScores(
                    trend_velocity=float(j["trend_velocity"]),
                    search_demand=float(j["search_demand"]),
                    competition_gap=float(j["competition_gap"]),
                    channel_fit=fit,
                    monetization_potential=float(j["monetization_potential"]),
                    freshness=float(j["freshness"]),
                )
                comp = composite(fs, DEFAULT_WEIGHTS)
                d = fs.as_dict()
                cur.execute(
                    """
                    insert into topic_scores
                      (topic_id, trend_velocity, search_demand, competition_gap,
                       channel_fit, monetization_potential, freshness,
                       predicted_views_score, composite, rationale)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        topic["id"],
                        d["trend_velocity"],
                        d["search_demand"],
                        d["competition_gap"],
                        d["channel_fit"],
                        d["monetization_potential"],
                        d["freshness"],
                        d["predicted_views_score"],
                        comp,
                        j.get("rationale"),
                    ),
                )
                cur.execute(
                    "update topics set status = 'scored' where id = %s", (topic["id"],)
                )
                scored += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error",
                component=AGENT,
                message="failed to score topic",
                detail={"topic_id": str(topic["id"]), "error": str(e)},
            )

    summary = {"scored": scored, "errors": errors}
    log_system_event(
        severity="info", component=AGENT, message="topic scorer run complete", detail=summary
    )
    return summary
