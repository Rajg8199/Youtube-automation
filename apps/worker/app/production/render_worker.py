"""Render Worker: assembly -> thumbnail. Pillow scene cards + FFmpeg assembly.

Renders each scene to a branded 1920x1080 PNG, concatenates them timed to the voiceover into
a 1080p MP4, and writes a sidecar .srt from the voiceover segment timing. (Remotion is the
production-grade renderer; this Pillow+FFmpeg path is the $0 local renderer — see ADR-0009.)
"""

from __future__ import annotations

import os
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .cards import render_scene_card
from .media import item_dir, probe_duration, rel_path, run_ffmpeg, store_media_asset

COMPONENT = "service:render_worker"


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title,
               sp.scenes,
               m.storage_path as vo_path, m.duration_sec as vo_duration, m.meta as vo_meta
        from content_items ci
        join lateral (
            select scenes from scene_plans p where p.content_item_id = ci.id
            order by created_at desc limit 1
        ) sp on true
        left join lateral (
            select storage_path, duration_sec, meta from media_assets ma
            where ma.content_item_id = ci.id and ma.kind = 'voiceover'
            order by created_at desc limit 1
        ) m on true
        where ci.status = 'assembly'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _srt_ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(path: str, segments: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{_srt_ts(seg['start'])} --> {_srt_ts(seg['end'])}\n{seg['text']}\n\n")


def _render_one(item: dict[str, Any]) -> dict[str, Any]:
    out = item_dir(item["content_item_id"])
    scenes = item["scenes"] or []
    if not scenes:
        raise ValueError("no scene plan")

    # 1) Render each scene card.
    list_lines = []
    for sc in scenes:
        png = os.path.join(out, f"scene_{sc['idx']:03d}.png")
        props = sc.get("props", {})
        render_scene_card(
            png, template=sc.get("template", "talking-points"),
            title=props.get("title", item["working_title"]),
            caption=props.get("caption", ""), on_screen=props.get("on_screen", sc.get("text", "")),
        )
        dur = max(2.0, float(sc.get("duration", 4.0)))
        list_lines.append(f"file '{os.path.basename(png)}'\nduration {dur}")
    # concat demuxer needs the last image repeated with no duration
    last_png = f"scene_{scenes[-1]['idx']:03d}.png"
    list_lines.append(f"file '{last_png}'")

    concat = os.path.join(out, "scenes.txt")
    with open(concat, "w", encoding="utf-8") as f:
        f.write("\n".join(list_lines) + "\n")

    # 2) Assemble video; mux voiceover if present.
    final = os.path.join(out, "final.mp4")
    media_root = os.path.dirname(out)
    vo_abs = os.path.join(media_root, item["vo_path"]) if item.get("vo_path") else None
    base = ["-f", "concat", "-safe", "0", "-i", concat]
    if vo_abs and os.path.exists(vo_abs):
        run_ffmpeg([*base, "-i", vo_abs,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", final])
    else:
        run_ffmpeg([*base, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", final])

    # 3) Sidecar subtitles from voiceover segment timing.
    sub_rel = None
    segments = (item.get("vo_meta") or {}).get("segments") if item.get("vo_meta") else None
    if segments:
        srt = os.path.join(out, "subtitles.srt")
        _write_srt(srt, segments)
        sub_rel = rel_path(srt)
        store_media_asset(content_item_id=item["content_item_id"], kind="subtitle",
                          storage_path=sub_rel)

    duration = probe_duration(final)
    store_media_asset(content_item_id=item["content_item_id"], kind="final_video",
                      storage_path=rel_path(final), duration_sec=duration,
                      meta={"scenes": len(scenes), "subtitles": sub_rel})
    return {"duration_sec": round(duration, 1), "scenes": len(scenes), "subtitles": bool(sub_rel)}


def run_render_worker(*, limit: int = 10) -> dict[str, int]:
    rendered = errors = 0
    with cursor() as cur:
        items = _fetch(cur, limit)

    for item in items:
        try:
            info = _render_one(item)
            transition(content_item_id=item["content_item_id"], to_status="thumbnail",
                       actor=COMPONENT, detail=info)
            rendered += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=COMPONENT, message="render failed",
                detail={"content_item_id": str(item["content_item_id"]), "error": str(e)},
            )

    summary = {"videos_rendered": rendered, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="render worker run complete", detail=summary)
    return summary
