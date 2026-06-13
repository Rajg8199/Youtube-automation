"""Script Writer: researched -> script_qa (write v1), and qa_failed -> script_qa (revise).

Hinglish, hook-first, fact-constrained to the research brief. Revisions read the latest QA
report and fix exactly the flagged issues.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from ..costs import log_agent_run
from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .context import AgentContext
from .prompts import load_prompt

AGENT = "agent:script_writer"
_PROMPT = "script_writer_v1"
_WORDS_PER_SEC = 2.3  # ~140 wpm Hinglish narration


def _fetch_writable(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select id, status, format, working_title, angle
        from content_items
        where status in ('researched', 'qa_failed')
        order by priority desc, created_at asc
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


def _revision_feedback(cur, item_id: str) -> dict[str, Any] | None:
    cur.execute(
        """
        select r.claims_failed, r.policy_flags, r.readability_notes
        from script_qa_reports r
        join scripts s on s.id = r.script_id
        where s.content_item_id = %s
        order by r.created_at desc limit 1
        """,
        (item_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "claims_failed": row["claims_failed"],
        "policy_flags": row["policy_flags"],
        "readability_notes": row["readability_notes"],
    }


def _next_version(cur, item_id: str) -> int:
    cur.execute(
        "select coalesce(max(version), 0) + 1 as v from scripts where content_item_id = %s",
        (item_id,),
    )
    return cur.fetchone()["v"]


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _write(ctx: AgentContext, item: dict[str, Any], brief: dict, feedback: dict | None) -> dict[str, Any]:
    model = ctx.settings.model_for("script")
    payload = json.dumps(
        {
            "working_title": item["working_title"],
            "angle": item.get("angle"),
            "format": item["format"],
            "research_brief": brief,
            "revision_feedback": feedback,
        }
    )
    t0 = time.time()
    resp = ctx.llm.complete(
        system=load_prompt(_PROMPT), prompt=payload, model=model, max_tokens=4096
    )
    log_agent_run(
        agent=AGENT,
        content_item_id=item["id"],
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=int((time.time() - t0) * 1000),
    )
    return resp.json()


def run_script_writer(ctx: AgentContext, *, limit: int = 50) -> dict[str, int]:
    written = errors = 0
    with cursor() as cur:
        items = _fetch_writable(cur, limit)

    for item in items:
        try:
            with cursor() as cur:
                brief = _brief(cur, item["id"])
                feedback = _revision_feedback(cur, item["id"]) if item["status"] == "qa_failed" else None
                version = _next_version(cur, item["id"])

            transition(content_item_id=item["id"], to_status="scripting", actor=AGENT,
                       detail={"version": version, "revision": feedback is not None})

            script = _write(ctx, item, brief, feedback)
            hook = (script.get("hook") or "").strip()
            body = script.get("body_markdown") or ""
            wc = _word_count(hook + " " + body)

            with cursor() as cur:
                cur.execute(
                    """
                    insert into scripts
                      (content_item_id, version, hook, body_markdown, cta,
                       word_count, est_duration_sec, language_mix)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item["id"], version, hook or "(missing hook)", body,
                        script.get("cta"), wc, int(wc / _WORDS_PER_SEC),
                        json.dumps(script.get("language_mix", {})),
                    ),
                )
            transition(content_item_id=item["id"], to_status="script_qa", actor=AGENT,
                       detail={"version": version, "word_count": wc})
            written += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=AGENT, message="failed to write script",
                detail={"content_item_id": str(item["id"]), "error": str(e)},
            )

    summary = {"scripts_written": written, "errors": errors}
    log_system_event(
        severity="info", component=AGENT, message="script writer run complete", detail=summary
    )
    return summary
