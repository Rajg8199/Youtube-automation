"""Research Compiler: idea -> researched. Builds a verified fact brief from the topic's
clustered raw_signals. NO fact enters the pipeline except through this brief.
"""

from __future__ import annotations

import json
import time
from typing import Any

from ..costs import log_agent_run
from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .context import AgentContext
from .prompts import load_prompt

AGENT = "agent:research_compiler"
_PROMPT = "research_compiler_v1"


def _fetch_idea_items(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id, ci.topic_id, t.title, t.devices, t.brands, t.signal_ids
        from content_items ci
        join topics t on t.id = ci.topic_id
        where ci.status = 'idea'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _fetch_sources(cur, signal_ids: list[str]) -> list[dict[str, Any]]:
    if not signal_ids:
        return []
    cur.execute(
        "select url, title, content from raw_signals where id = any(%s)",
        (signal_ids,),
    )
    return cur.fetchall()


def _compile(ctx: AgentContext, item: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
    model = ctx.settings.model_for("script")
    payload = json.dumps(
        {
            "topic_title": item["title"],
            "devices": item.get("devices") or [],
            "brands": item.get("brands") or [],
            "sources": [
                {"url": s.get("url"), "title": s["title"], "content": (s.get("content") or "")[:2000]}
                for s in sources
            ],
        }
    )
    t0 = time.time()
    resp = ctx.llm.complete(system=load_prompt(_PROMPT), prompt=payload, model=model)
    log_agent_run(
        agent=AGENT,
        content_item_id=item["id"],
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=int((time.time() - t0) * 1000),
    )
    return resp.json()


def run_research_compiler(ctx: AgentContext, *, limit: int = 50) -> dict[str, int]:
    compiled = errors = 0
    with cursor() as cur:
        items = _fetch_idea_items(cur, limit)

    for item in items:
        try:
            with cursor() as cur:
                sources = _fetch_sources(cur, item.get("signal_ids") or [])
            brief = _compile(ctx, item, sources)
            with cursor() as cur:
                cur.execute(
                    """
                    insert into research_briefs
                      (content_item_id, facts, spec_table, price_data, competitor_videos)
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        item["id"],
                        json.dumps(brief.get("facts", [])),
                        json.dumps(brief.get("spec_table", {})),
                        json.dumps(brief.get("price_data", {})),
                        json.dumps([]),
                    ),
                )
            transition(
                content_item_id=item["id"],
                to_status="researched",
                actor=AGENT,
                detail={"fact_count": len(brief.get("facts", []))},
            )
            compiled += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error",
                component=AGENT,
                message="failed to compile research",
                detail={"content_item_id": str(item["id"]), "error": str(e)},
            )

    summary = {"briefs_compiled": compiled, "errors": errors}
    log_system_event(
        severity="info", component=AGENT, message="research compiler run complete", detail=summary
    )
    return summary
