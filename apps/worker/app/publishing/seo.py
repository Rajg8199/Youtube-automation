"""SEO Optimizer (deterministic, no LLM): title, description with chapters + disclosure +
affiliate links, tags/hashtags. Writes seo_metadata. Avoids the Gemini quota entirely.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus

from ..config import get_settings
from ..db import cursor
from ..events import log_system_event

COMPONENT = "service:seo_optimizer"
_DISCLOSURE = "Note: This video uses AI-assisted narration and graphics."


def _affiliate_links(devices: list[str]) -> list[dict[str, str]]:
    s = get_settings()
    links = []
    for d in devices:
        q = quote_plus(d)
        amazon = f"https://www.amazon.in/s?k={q}"
        if s.amazon_associates_tag:
            amazon += f"&tag={s.amazon_associates_tag}"
        flipkart = f"https://www.flipkart.com/search?q={q}"
        if s.flipkart_affiliate_id:
            flipkart += f"&affid={s.flipkart_affiliate_id}"
        links.append({"device": d, "amazon_url": amazon, "flipkart_url": flipkart})
    return links


def _chapters_from_scenes(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chapters, t = [], 0.0
    for sc in scenes:
        mm, ss = divmod(int(t), 60)
        label = (sc.get("caption") or sc.get("template") or "Section").strip()[:40]
        chapters.append({"time": f"{mm}:{ss:02d}", "label": label})
        t += float(sc.get("duration", 0) or 0)
    return chapters


def _build(item: dict[str, Any]) -> dict[str, Any]:
    devices = item.get("devices") or []
    brands = item.get("brands") or []
    affiliates = _affiliate_links(devices)
    scenes = item.get("scenes") or []
    chapters = _chapters_from_scenes(scenes)

    title = (item["working_title"] or "")[:100]
    parts = [item.get("angle") or "", ""]
    if chapters:
        parts.append("⏱️ Chapters:")
        parts += [f"{c['time']} {c['label']}" for c in chapters]
        parts.append("")
    if affiliates:
        parts.append("🛒 Buy / check price (affiliate):")
        for a in affiliates:
            parts.append(f"{a['device']} — Amazon: {a['amazon_url']} | Flipkart: {a['flipkart_url']}")
        parts.append("")
    parts.append(_DISCLOSURE)
    description = "\n".join(p for p in parts if p is not None)[:5000]

    tags = list(dict.fromkeys(
        [*devices, *brands, "smartphone", "tech", "hindi tech", "PhoneWala Gyan"]
    ))[:25]
    hashtags = ["#" + b.replace(" ", "") for b in brands][:3] + ["#PhoneWalaGyan", "#tech"]
    return {
        "title": title, "description": description, "tags": tags,
        "hashtags": hashtags, "affiliate_links": affiliates, "chapters": chapters,
    }


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title, ci.angle,
               t.devices, t.brands,
               sp.scenes
        from content_items ci
        left join topics t on t.id = ci.topic_id
        left join lateral (
            select scenes from scene_plans p where p.content_item_id = ci.id
            order by created_at desc limit 1
        ) sp on true
        where ci.status = 'ready_for_review'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def run_seo_optimizer(*, limit: int = 20) -> dict[str, int]:
    optimized = errors = 0
    with cursor() as cur:
        items = _fetch(cur, limit)
    for item in items:
        try:
            meta = _build(item)
            with cursor() as cur:
                # Replace the placeholder row created at finalize, if any.
                cur.execute("delete from seo_metadata where content_item_id = %s",
                            (item["content_item_id"],))
                cur.execute(
                    """
                    insert into seo_metadata
                      (content_item_id, title, description, tags, hashtags,
                       affiliate_links, chapters)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (item["content_item_id"], meta["title"], meta["description"],
                     meta["tags"], meta["hashtags"],
                     json.dumps(meta["affiliate_links"]), json.dumps(meta["chapters"])),
                )
            optimized += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(severity="error", component=COMPONENT, message="seo failed",
                             detail={"content_item_id": str(item["content_item_id"]), "error": str(e)})
    summary = {"optimized": optimized, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="seo optimizer run complete", detail=summary)
    return summary
