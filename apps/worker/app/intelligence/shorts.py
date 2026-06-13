"""Shorts derivation: turn a published long video into a 9:16 short (WF10).

Re-frames the long's final video into a vertical 1080x1920 clip (blurred fill so captions
stay fully visible) and registers it as a derived short content_item (parent_id = the long).
A vertical-native re-edit can replace the reframe later; this gives a real short now.
"""

from __future__ import annotations

import os
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..production.media import item_dir, media_dir, probe_duration, rel_path, run_ffmpeg, store_media_asset

COMPONENT = "service:shorts"
_MAX_SECONDS = 50


def _fetch_eligible(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.topic_id, ci.working_title,
               fv.storage_path as video_path
        from content_items ci
        join lateral (
            select storage_path from media_assets m
            where m.content_item_id = ci.id and m.kind = 'final_video'
            order by created_at desc limit 1
        ) fv on true
        where ci.format = 'long'
          and not exists (
            select 1 from content_items s where s.parent_id = ci.id and s.format = 'short'
          )
        order by ci.created_at desc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _reframe_vertical(src_abs: str, out_abs: str) -> None:
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=24:4[bg];[0:v]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
    )
    run_ffmpeg(["-t", str(_MAX_SECONDS), "-i", src_abs, "-filter_complex", fc,
                "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", out_abs])


def run_shorts_derivation(*, limit: int = 5) -> dict[str, int]:
    derived = errors = 0
    with cursor() as cur:
        items = _fetch_eligible(cur, limit)

    for long in items:
        try:
            src = os.path.join(media_dir(), long["video_path"])
            if not os.path.exists(src):
                continue
            with cursor() as cur:
                cur.execute(
                    """
                    insert into content_items (topic_id, format, parent_id, working_title, status, priority)
                    values (%s, 'short', %s, %s, 'ready_for_review', 60)
                    returning id
                    """,
                    (long["topic_id"], long["content_item_id"],
                     (long["working_title"] or "")[:120] + " #Shorts"),
                )
                short_id = cur.fetchone()["id"]
            out = os.path.join(item_dir(short_id), "final.mp4")
            _reframe_vertical(src, out)
            store_media_asset(content_item_id=short_id, kind="final_video",
                              storage_path=rel_path(out), duration_sec=probe_duration(out),
                              meta={"derived_from": str(long["content_item_id"]), "aspect": "9:16"})
            derived += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(severity="error", component=COMPONENT, message="shorts derive failed",
                             detail={"content_item_id": str(long["content_item_id"]), "error": str(e)})

    summary = {"shorts_derived": derived, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="shorts derivation run complete", detail=summary)
    return summary
