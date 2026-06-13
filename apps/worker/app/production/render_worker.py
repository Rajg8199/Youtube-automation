"""Render Worker: assembly -> thumbnail. Sentence-synced caption cards + Ken Burns motion.

The video is driven by the voiceover's spoken segments: one caption card per narrated
sentence (synced to its timing), each turned into a short clip with a slow zoom (Ken Burns),
concatenated and muxed with the voiceover. A sidecar .srt is also written. Per-clip motion
falls back to a static clip if ffmpeg's zoompan errors, so a render never fully fails.
(Remotion stays the production-grade renderer behind the VideoRenderer interface — ADR-0009.)
"""

from __future__ import annotations

import os
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .broll import fetch_broll, queries_for
from .cards import render_segment_card
from .media import item_dir, media_dir, probe_duration, rel_path, run_ffmpeg, store_media_asset

COMPONENT = "service:render_worker"
FPS = 30


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title,
               t.devices, t.brands,
               sp.scenes,
               m.storage_path as vo_path, m.duration_sec as vo_duration, m.meta as vo_meta
        from content_items ci
        left join topics t on t.id = ci.topic_id
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


def _scene_template_at(scenes: list[dict], t: float) -> str:
    """Which scene template is on screen at time t (by cumulative scene durations)."""
    acc = 0.0
    for sc in scenes:
        acc += float(sc.get("duration", 0) or 0)
        if t <= acc:
            return sc.get("template", "talking-points")
    return scenes[-1].get("template", "talking-points") if scenes else "talking-points"


def _kenburns_clip(png: str, out_mp4: str, dur: float, zoom_in: bool) -> None:
    frames = max(2, int(dur * FPS))
    if zoom_in:
        z = "min(zoom+0.0010,1.14)"
    else:
        z = "if(eq(on,0),1.14,max(zoom-0.0010,1.0))"
    vf = (
        f"scale=2400:-1,zoompan=z='{z}':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={FPS}"
    )
    try:
        run_ffmpeg(["-loop", "1", "-i", png, "-t", f"{dur}", "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out_mp4])
    except Exception:  # noqa: BLE001 - fall back to a static clip
        run_ffmpeg(["-loop", "1", "-i", png, "-t", f"{dur}",
                    "-vf", f"scale=1920:1080,fps={FPS}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out_mp4])


def _render_one(item: dict[str, Any]) -> dict[str, Any]:
    out = item_dir(item["content_item_id"])
    scenes = item["scenes"] or []
    vo_meta = item.get("vo_meta") or {}
    segments = vo_meta.get("segments") or []

    # Fall back to scene text if there are no voiceover segments.
    if not segments:
        if not scenes:
            raise ValueError("no segments or scenes to render")
        segments = [{"text": sc.get("text", sc.get("caption", "")),
                     "start": 0, "end": float(sc.get("duration", 4))} for sc in scenes]

    # Optional Pexels b-roll pool (empty list if no PEXELS_API_KEY -> gradient fallback).
    broll = fetch_broll(queries_for(item.get("devices") or [], item.get("brands") or []), out)

    clips, list_lines = [], []
    total = len(segments)
    for i, seg in enumerate(segments):
        dur = max(1.6, float(seg.get("end", 0)) - float(seg.get("start", 0))) or 3.0
        mid = (float(seg.get("start", 0)) + float(seg.get("end", dur))) / 2
        template = _scene_template_at(scenes, mid)
        bg = broll[i % len(broll)] if broll else None
        png = os.path.join(out, f"cap_{i:03d}.png")
        render_segment_card(png, title=item["working_title"], template=template,
                            text=seg.get("text", ""), index=i, total=total, bg_image=bg)
        clip = os.path.join(out, f"clip_{i:03d}.mp4")
        _kenburns_clip(png, clip, dur, zoom_in=(i % 2 == 0))
        clips.append(clip)
        list_lines.append(f"file '{os.path.basename(clip)}'")

    concat = os.path.join(out, "clips.txt")
    with open(concat, "w", encoding="utf-8") as f:
        f.write("\n".join(list_lines) + "\n")
    silent = os.path.join(out, "silent.mp4")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", silent])

    final = os.path.join(out, "final.mp4")
    vo_abs = os.path.join(media_dir(), item["vo_path"]) if item.get("vo_path") else None
    if vo_abs and os.path.exists(vo_abs):
        run_ffmpeg(["-i", silent, "-i", vo_abs, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", final])
    else:
        run_ffmpeg(["-i", silent, "-c", "copy", final])

    sub_rel = None
    if vo_meta.get("segments"):
        srt = os.path.join(out, "subtitles.srt")
        _write_srt(srt, vo_meta["segments"])
        sub_rel = rel_path(srt)
        store_media_asset(content_item_id=item["content_item_id"], kind="subtitle", storage_path=sub_rel)

    duration = probe_duration(final)
    store_media_asset(content_item_id=item["content_item_id"], kind="final_video",
                      storage_path=rel_path(final), duration_sec=duration,
                      meta={"segments": total, "subtitles": sub_rel})
    return {"duration_sec": round(duration, 1), "caption_cards": total, "subtitles": bool(sub_rel)}


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
            log_system_event(severity="error", component=COMPONENT, message="render failed",
                             detail={"content_item_id": str(item["content_item_id"]), "error": str(e)})

    summary = {"videos_rendered": rendered, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="render worker run complete", detail=summary)
    return summary
