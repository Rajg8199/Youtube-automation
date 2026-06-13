"""Production runner: voice -> scenes -> render -> thumbnails -> finalize.

Each sub-job is idempotent over its input status, so the pipeline is an ordered sequence
that walks a content_item from script_approved to ready_for_review.
"""

from __future__ import annotations

from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .render_worker import run_render_worker
from .thumbnail_designer import run_thumbnail_designer
from .visual_director import run_visual_director
from .voice_producer import run_voice_producer

COMPONENT = "service:finalize"


def run_finalize(*, limit: int = 10) -> dict[str, int]:
    """metadata -> ready_for_review, with a placeholder SEO row (full SEO is Phase 4)."""
    finalized = 0
    with cursor() as cur:
        cur.execute(
            "select id, working_title from content_items where status = 'metadata' "
            "order by priority desc, created_at asc limit %s",
            (limit,),
        )
        items = cur.fetchall()
    for it in items:
        with cursor() as cur:
            cur.execute(
                "insert into seo_metadata (content_item_id, title, description) values (%s, %s, %s)",
                (it["id"], (it["working_title"] or "")[:100],
                 "Auto-generated draft description. Full SEO optimization arrives in Phase 4."),
            )
        transition(content_item_id=it["id"], to_status="ready_for_review", actor=COMPONENT)
        finalized += 1
    log_system_event(severity="info", component=COMPONENT, message="finalize run complete",
                     detail={"finalized": finalized})
    return {"finalized": finalized}


def run_production_pipeline(*, limit: int = 10) -> dict[str, Any]:
    return {
        "voice": run_voice_producer(limit=limit),
        "visual": run_visual_director(limit=limit),
        "render": run_render_worker(limit=limit),
        "thumbnails": run_thumbnail_designer(limit=limit),
        "finalize": run_finalize(limit=limit),
    }
