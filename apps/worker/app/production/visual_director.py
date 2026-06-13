"""Visual Director (deterministic): voiceover -> assembly.

Parses the script's [SCENE:] markers into an ordered scene plan and allocates each scene a
slice of the voiceover duration proportional to its spoken text. No LLM — so it costs $0 and
never touches the Gemini quota.
"""

from __future__ import annotations

import json
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .scriptparse import allocate_durations, parse_scenes

COMPONENT = "service:visual_director"


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title,
               s.hook, s.body_markdown,
               va.duration_sec as vo_duration
        from content_items ci
        join lateral (
            select * from scripts sc where sc.content_item_id = ci.id
            order by sc.version desc limit 1
        ) s on true
        left join lateral (
            select duration_sec from media_assets m
            where m.content_item_id = ci.id and m.kind = 'voiceover'
            order by created_at desc limit 1
        ) va on true
        where ci.status = 'voiceover'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _plan_one(cur, item: dict[str, Any]) -> int:
    scenes = parse_scenes(item["hook"] or "", item["body_markdown"] or "")
    total = float(item["vo_duration"] or max(8.0, len(scenes) * 4.0))
    durations = allocate_durations(scenes, total)

    scene_json = [
        {
            "idx": s.idx,
            "template": s.template,
            "caption": s.caption,
            "text": s.text,
            "duration": d,
            "props": {"title": item["working_title"], "caption": s.caption,
                      "on_screen": s.text[:160]},
        }
        for s, d in zip(scenes, durations)
    ]
    cur.execute(
        "insert into scene_plans (content_item_id, scenes) values (%s, %s)",
        (item["content_item_id"], json.dumps(scene_json)),
    )
    return len(scene_json)


def run_visual_director(*, limit: int = 20) -> dict[str, int]:
    planned = errors = 0
    with cursor() as cur:
        items = _fetch(cur, limit)

    for item in items:
        try:
            with cursor() as cur:
                n = _plan_one(cur, item)
            transition(content_item_id=item["content_item_id"], to_status="assembly",
                       actor=COMPONENT, detail={"scenes": n})
            planned += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=COMPONENT, message="scene plan failed",
                detail={"content_item_id": str(item["content_item_id"]), "error": str(e)},
            )

    summary = {"scene_plans": planned, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="visual director run complete", detail=summary)
    return summary
