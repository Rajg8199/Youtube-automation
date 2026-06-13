"""Editorial Planner: greenlit (selected) topics -> content_items with a distinctive angle."""

from __future__ import annotations

import json
import time
from typing import Any

from ..costs import log_agent_run
from ..db import cursor
from ..events import log_pipeline_event, log_system_event
from .context import AgentContext
from .prompts import load_prompt

AGENT = "agent:editorial_planner"
_PROMPT = "editorial_planner_v1"


def _fetch_selected(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select t.id, t.title, t.category, t.devices, t.brands, t.summary,
               coalesce(s.composite, 0.5) as composite
        from topics t
        left join lateral (
            select composite from topic_scores ts
            where ts.topic_id = t.id order by ts.scored_at desc limit 1
        ) s on true
        where t.status = 'selected'
        order by s.composite desc nulls last
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _plan(ctx: AgentContext, topic: dict[str, Any]) -> dict[str, Any]:
    model = ctx.settings.model_for("script")
    payload = json.dumps(
        {
            "title": topic["title"],
            "category": topic["category"],
            "devices": topic.get("devices") or [],
            "brands": topic.get("brands") or [],
            "summary": topic.get("summary") or "",
        }
    )
    t0 = time.time()
    resp = ctx.llm.complete(system=load_prompt(_PROMPT), prompt=payload, model=model)
    log_agent_run(
        agent=AGENT,
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=int((time.time() - t0) * 1000),
    )
    return resp.json()


def run_editorial_planner(ctx: AgentContext, *, limit: int = 50) -> dict[str, int]:
    created = errors = 0
    with cursor() as cur:
        topics = _fetch_selected(cur, limit)

    for topic in topics:
        try:
            plan = _plan(ctx, topic)
            fmt = "short" if plan.get("format") == "short" else "long"
            priority = int(round(float(topic["composite"]) * 100))
            with cursor() as cur:
                cur.execute(
                    """
                    insert into content_items
                      (topic_id, format, working_title, angle, status, priority)
                    values (%s, %s, %s, %s, 'idea', %s)
                    returning id
                    """,
                    (
                        topic["id"],
                        fmt,
                        plan.get("working_title") or topic["title"],
                        plan.get("angle"),
                        priority,
                    ),
                )
                item_id = cur.fetchone()["id"]
                cur.execute(
                    "update topics set status = 'converted' where id = %s", (topic["id"],)
                )
            log_pipeline_event(
                content_item_id=item_id,
                from_status=None,
                to_status="idea",
                actor=AGENT,
                detail={"topic_id": str(topic["id"]), "format": fmt},
            )
            created += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error",
                component=AGENT,
                message="failed to plan topic",
                detail={"topic_id": str(topic["id"]), "error": str(e)},
            )

    summary = {"content_items_created": created, "errors": errors}
    log_system_event(
        severity="info", component=AGENT, message="editorial planner run complete", detail=summary
    )
    return summary
