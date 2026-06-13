"""Thumbnail Designer: thumbnail -> metadata. 3 brand-kit variants via Pillow."""

from __future__ import annotations

import os
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .cards import render_thumbnail
from .media import item_dir, rel_path, store_media_asset

COMPONENT = "service:thumbnail_designer"
_VARIANTS = [
    ("A", "Bold orange band, full title"),
    ("B", "Title over an orange panel block"),
    ("C", "Outlined frame, question emphasis"),
]


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select id as content_item_id, working_title
        from content_items where status = 'thumbnail'
        order by priority desc, created_at asc limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _design_one(cur, item: dict[str, Any]) -> int:
    out = item_dir(item["content_item_id"])
    for variant, concept in _VARIANTS:
        png = os.path.join(out, f"thumb_{variant}.png")
        render_thumbnail(png, title=item["working_title"], variant=variant)
        asset_id = store_media_asset(content_item_id=item["content_item_id"], kind="thumbnail",
                                     storage_path=rel_path(png), meta={"variant": variant})
        cur.execute(
            """
            insert into thumbnails (content_item_id, variant, asset_id, concept, is_selected)
            values (%s, %s, %s, %s, %s)
            """,
            (item["content_item_id"], variant, asset_id, concept, variant == "A"),
        )
    return len(_VARIANTS)


def run_thumbnail_designer(*, limit: int = 10) -> dict[str, int]:
    designed = errors = 0
    with cursor() as cur:
        items = _fetch(cur, limit)

    for item in items:
        try:
            with cursor() as cur:
                n = _design_one(cur, item)
            transition(content_item_id=item["content_item_id"], to_status="metadata",
                       actor=COMPONENT, detail={"variants": n})
            designed += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=COMPONENT, message="thumbnail failed",
                detail={"content_item_id": str(item["content_item_id"]), "error": str(e)},
            )

    summary = {"thumbnail_sets": designed, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="thumbnail designer run complete", detail=summary)
    return summary
