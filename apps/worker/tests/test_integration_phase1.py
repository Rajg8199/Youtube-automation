"""End-to-end Phase 1 flow against a live DB.

OPT-IN and DESTRUCTIVE: it truncates the pipeline tables for determinism, so it only runs
when RUN_DB_INTEGRATION=1 (and a DB is reachable). Default test runs skip it — `make
demo-phase-1` is the non-destructive end-to-end proof. Enable with:
  RUN_DB_INTEGRATION=1 DATABASE_URL=postgresql://postgres:postgres@localhost:54322/phonewala
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from app.agents.context import AgentContext
from app.agents.topic_scorer import run_topic_scorer
from app.agents.trend_scout import run_trend_scout
from app.config import get_settings
from app.providers.embeddings import get_embedding_provider
from app.providers.llm import MockLLMClient


def _db_or_skip():
    if os.environ.get("RUN_DB_INTEGRATION") != "1":
        pytest.skip("set RUN_DB_INTEGRATION=1 to run the destructive DB integration test")
    try:
        from app.db import ping

        if not ping():
            pytest.skip("DB not reachable")
    except Exception:
        pytest.skip("DB not reachable")


def _ctx() -> AgentContext:
    s = get_settings()
    llm = MockLLMClient(
        responses={
            s.model_for("classify"): json.dumps(
                {"topic_title": "", "category": "leak", "devices": [], "brands": [],
                 "summary": "test", "perishable": True, "slug": ""}
            ),
            s.model_for("script"): json.dumps(
                {"trend_velocity": 0.5, "search_demand": 0.6, "competition_gap": 0.4,
                 "monetization_potential": 0.7, "freshness": 0.8, "rationale": "test rationale"}
            ),
        }
    )
    return AgentContext(settings=s, llm=llm, embedder=get_embedding_provider("mock"))


def test_research_to_scored_topics_flow():
    _db_or_skip()
    from app.db import cursor

    tag = uuid.uuid4().hex[:8]
    titles = [
        f"[{tag}] Samsung Galaxy Z Flip leaked hinge redesign",
        f"[{tag}] OnePlus Open 2 foldable India price tip",
        f"[{tag}] Redmi K90 Pro benchmark scores appear",
    ]
    with cursor() as cur:
        # Isolate: clear the pipeline so clustering/scoring is deterministic.
        cur.execute("truncate topic_scores, topics, raw_signals restart identity cascade")
        cur.execute("select id from sources where active = true limit 1")
        src = cur.fetchone()["id"]
        for i, t in enumerate(titles):
            cur.execute(
                "insert into raw_signals (source_id, external_id, title) values (%s,%s,%s) "
                "on conflict do nothing",
                (src, f"itest-{tag}-{i}", t),
            )

    ctx = _ctx()
    scout = run_trend_scout(ctx)
    assert scout["processed"] >= 3
    scorer = run_topic_scorer(ctx)
    assert scorer["scored"] >= 1

    with cursor() as cur:
        cur.execute(
            """
            select count(*) as n from topics t
            join topic_scores s on s.topic_id = t.id
            where t.title like %s and t.status = 'scored' and s.rationale is not null
            """,
            (f"%[{tag}]%",),
        )
        assert cur.fetchone()["n"] >= 1
