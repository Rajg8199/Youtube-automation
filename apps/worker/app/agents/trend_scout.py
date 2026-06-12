"""Trend Scout (Haiku): cluster unprocessed raw_signals into topics.

For each unprocessed signal:
  1. embed its title,
  2. if it is within cosine `cluster_merge_threshold` of an existing topic, merge into it,
  3. otherwise classify it with Haiku and create a new topic,
  4. mark the signal processed.

Near-duplicate detection uses pgvector cosine distance; classification (category/devices/
brands/summary) uses the LLM, which is instructed never to fabricate.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..costs import log_agent_run
from ..db import cursor, to_vector
from ..events import log_system_event
from .context import AgentContext
from .prompts import load_prompt

AGENT = "agent:trend_scout"
_PROMPT = "trend_scout_v1"
_PERISHABLE_TTL = {"leak": 14, "news": 10, "launch": 21}  # days until expiry


def _fetch_unprocessed(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select id, title, content, url
        from raw_signals
        where processed = false
        order by fetched_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _nearest_topic(cur, vec: str) -> dict[str, Any] | None:
    cur.execute(
        """
        select id, 1 - (embedding <=> %s::vector) as sim
        from topics
        where embedding is not null
        order by embedding <=> %s::vector
        limit 1
        """,
        (vec, vec),
    )
    return cur.fetchone()


def _merge_signal(cur, topic_id: str, signal_id: str) -> None:
    cur.execute(
        "update topics set signal_ids = array_append(signal_ids, %s) where id = %s",
        (signal_id, topic_id),
    )


def _unique_slug(cur, slug: str) -> str:
    base = slug or f"topic-{uuid.uuid4().hex[:8]}"
    cur.execute("select 1 from topics where slug = %s", (base,))
    if cur.fetchone() is None:
        return base
    return f"{base}-{uuid.uuid4().hex[:6]}"


def _expiry(category: str, perishable: bool) -> datetime | None:
    if not perishable:
        return None
    days = _PERISHABLE_TTL.get(category, 14)
    return datetime.now(timezone.utc) + timedelta(days=days)


def _classify(ctx: AgentContext, signal: dict[str, Any]) -> dict[str, Any]:
    model = ctx.settings.model_for("classify")
    payload = json.dumps(
        {"title": signal["title"], "content": signal.get("content"), "url": signal.get("url")}
    )
    t0 = time.time()
    resp = ctx.llm.complete(system=load_prompt(_PROMPT), prompt=payload, model=model)
    latency_ms = int((time.time() - t0) * 1000)
    log_agent_run(
        agent=AGENT,
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        latency_ms=latency_ms,
    )
    return resp.json()


def _create_topic(cur, signal: dict[str, Any], vec: str, fields: dict[str, Any]) -> str:
    category = fields.get("category")
    slug = _unique_slug(cur, fields.get("slug", ""))
    cur.execute(
        """
        insert into topics
          (title, slug, category, devices, brands, summary, signal_ids, embedding,
           status, expires_at)
        values (%s, %s, %s, %s, %s, %s, %s, %s::vector, 'new', %s)
        returning id
        """,
        (
            fields.get("topic_title") or signal["title"],
            slug,
            category,
            fields.get("devices", []),
            fields.get("brands", []),
            fields.get("summary"),
            [signal["id"]],
            vec,
            _expiry(category, bool(fields.get("perishable", True))),
        ),
    )
    return cur.fetchone()["id"]


def run_trend_scout(ctx: AgentContext, *, limit: int = 200) -> dict[str, int]:
    """Process up to `limit` unprocessed signals. Returns a run summary."""
    created = merged = processed = errors = 0
    with cursor() as cur:
        signals = _fetch_unprocessed(cur, limit)

    for signal in signals:
        text = signal["title"] + (" " + signal["content"] if signal.get("content") else "")
        try:
            vec = to_vector(ctx.embedder.embed(text))
            with cursor() as cur:
                nearest = _nearest_topic(cur, vec)
                if nearest and nearest["sim"] is not None and float(
                    nearest["sim"]
                ) >= ctx.settings.cluster_merge_threshold:
                    _merge_signal(cur, nearest["id"], signal["id"])
                    merged += 1
                else:
                    fields = _classify(ctx, signal)
                    _create_topic(cur, signal, vec, fields)
                    created += 1
                cur.execute(
                    "update raw_signals set processed = true where id = %s",
                    (signal["id"],),
                )
                processed += 1
        except Exception as e:  # noqa: BLE001 - isolate per-signal failures
            errors += 1
            log_system_event(
                severity="error",
                component=AGENT,
                message="failed to process signal",
                detail={"signal_id": str(signal["id"]), "error": str(e)},
            )

    summary = {
        "processed": processed,
        "topics_created": created,
        "topics_merged": merged,
        "errors": errors,
    }
    log_system_event(
        severity="info", component=AGENT, message="trend scout run complete", detail=summary
    )
    return summary
