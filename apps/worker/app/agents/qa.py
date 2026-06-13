"""Fact-Check / QA hard gate: script_qa -> script_approved | qa_failed.

Verifies every concrete claim against the research brief. Pass requires zero unverified
claims; on pass a pending `script` approval is created for the human gate. On fail the item
goes to qa_failed (the Script Writer revises; the runner caps revisions).
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

AGENT = "agent:qa"
_PROMPT = "qa_v1"


def _fetch_for_qa(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, s.id as script_id, s.hook, s.body_markdown
        from content_items ci
        join lateral (
            select * from scripts sc where sc.content_item_id = ci.id
            order by sc.version desc limit 1
        ) s on true
        where ci.status = 'script_qa'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _brief(cur, item_id: str) -> dict[str, Any]:
    cur.execute(
        "select facts, spec_table, price_data from research_briefs "
        "where content_item_id = %s order by created_at desc limit 1",
        (item_id,),
    )
    row = cur.fetchone()
    if not row:
        return {"facts": [], "spec_table": {}, "price_data": {}}
    return {"facts": row["facts"], "spec_table": row["spec_table"], "price_data": row["price_data"]}


def _check(ctx: AgentContext, item: dict[str, Any], brief: dict) -> dict[str, Any]:
    model = ctx.settings.model_for("script")
    payload = json.dumps(
        {"hook": item["hook"], "body_markdown": item["body_markdown"], "research_brief": brief}
    )
    t0 = time.time()
    resp = ctx.llm.complete(system=load_prompt(_PROMPT), prompt=payload, model=model)
    log_agent_run(
        agent=AGENT,
        content_item_id=item["content_item_id"],
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=int((time.time() - t0) * 1000),
    )
    return resp.json()


def run_qa(ctx: AgentContext, *, limit: int = 50) -> dict[str, int]:
    passed = failed = errors = 0
    with cursor() as cur:
        items = _fetch_for_qa(cur, limit)

    for item in items:
        try:
            with cursor() as cur:
                brief = _brief(cur, item["content_item_id"])
            report = _check(ctx, item, brief)
            claims_failed = report.get("claims_failed", []) or []
            policy_flags = report.get("policy_flags", []) or []
            # Hard gate: zero unverified claims to pass.
            ok = len(claims_failed) == 0

            with cursor() as cur:
                cur.execute(
                    """
                    insert into script_qa_reports
                      (script_id, passed, claims_checked, claims_failed, policy_flags, readability_notes)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item["script_id"], ok, int(report.get("claims_checked", 0) or 0),
                        json.dumps(claims_failed), json.dumps(policy_flags),
                        report.get("readability_notes"),
                    ),
                )

            if ok:
                transition(content_item_id=item["content_item_id"], to_status="script_approved",
                           actor=AGENT, detail={"claims_checked": report.get("claims_checked", 0)})
                with cursor() as cur:
                    cur.execute(
                        "insert into approvals (content_item_id, gate, status) "
                        "values (%s, 'script', 'pending')",
                        (item["content_item_id"],),
                    )
                passed += 1
            else:
                transition(content_item_id=item["content_item_id"], to_status="qa_failed",
                           actor=AGENT, detail={"claims_failed": len(claims_failed)})
                failed += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=AGENT, message="failed to QA script",
                detail={"content_item_id": str(item["content_item_id"]), "error": str(e)},
            )

    summary = {"passed": passed, "failed": failed, "errors": errors}
    log_system_event(
        severity="info", component=AGENT, message="qa run complete", detail=summary
    )
    return summary
