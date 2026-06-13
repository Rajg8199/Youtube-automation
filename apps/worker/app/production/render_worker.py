"""Render Worker: assembly -> thumbnail. Moving b-roll + synced caption overlays.

Each narrated sentence becomes a clip: a free Pexels stock VIDEO plays in the background
(scaled/cropped/darkened) with a transparent caption overlay composited on top. Aspect comes
from the content item's format — 16:9 for long, 9:16 (mobile) for shorts. Falls back to a
darkened photo or gradient (with Ken Burns) when no video clip is available, so a render never
fully fails. (Remotion remains the production-grade renderer behind the interface — ADR-0009.)
"""

from __future__ import annotations

import os
from typing import Any

from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .broll import fetch_broll, fetch_broll_videos, queries_for
from .cards import _gradient, _photo_bg, render_caption_overlay
from .media import item_dir, media_dir, probe_duration, rel_path, run_ffmpeg, store_media_asset

COMPONENT = "service:render_worker"
FPS = 30


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title, ci.format,
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
    acc = 0.0
    for sc in scenes:
        acc += float(sc.get("duration", 0) or 0)
        if t <= acc:
            return sc.get("template", "talking-points")
    return scenes[-1].get("template", "talking-points") if scenes else "talking-points"


def _video_clip(bg_video: str, overlay_png: str, out: str, dur: float, w: int, h: int) -> None:
    fc = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
        f"eq=brightness=-0.20:saturation=1.05,setsar=1[bg];[bg][1:v]overlay=0:0[v]"
    )
    run_ffmpeg(["-stream_loop", "-1", "-t", f"{dur}", "-i", bg_video, "-i", overlay_png,
                "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}", "-r", str(FPS),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", out])


def _static_clip(overlay_png: str, out: str, dur: float, w: int, h: int,
                 photo: str | None, zoom_in: bool) -> None:
    """Composite the caption over a darkened photo/gradient, then a slow Ken Burns zoom."""
    from PIL import Image

    bg = None
    if photo:
        try:
            bg = _photo_bg(photo, w, h)
        except Exception:  # noqa: BLE001
            bg = None
    if bg is None:
        bg = _gradient(w, h)
    composed = bg.convert("RGBA")
    composed.alpha_composite(Image.open(overlay_png).convert("RGBA"))
    frame = out + ".png"
    composed.convert("RGB").save(frame)
    frames = max(2, int(dur * FPS))
    z = "min(zoom+0.0010,1.12)" if zoom_in else "if(eq(on,0),1.12,max(zoom-0.0010,1.0))"
    vf = (f"scale={w*2}:-1,zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":s={w}x{h}:fps={FPS}")
    try:
        run_ffmpeg(["-loop", "1", "-i", frame, "-t", f"{dur}", "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out])
    except Exception:  # noqa: BLE001
        run_ffmpeg(["-loop", "1", "-i", frame, "-t", f"{dur}", "-vf", f"scale={w}:{h},fps={FPS}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out])


def _render_one(item: dict[str, Any]) -> dict[str, Any]:
    out = item_dir(item["content_item_id"])
    scenes = item["scenes"] or []
    vo_meta = item.get("vo_meta") or {}
    segments = vo_meta.get("segments") or []
    if not segments:
        if not scenes:
            raise ValueError("no segments or scenes to render")
        segments = [{"text": sc.get("text", sc.get("caption", "")),
                     "start": 0, "end": float(sc.get("duration", 4))} for sc in scenes]

    vertical = item.get("format") == "short"
    w, h = (1080, 1920) if vertical else (1920, 1080)
    orientation = "portrait" if vertical else "landscape"

    queries = queries_for(item.get("devices") or [], item.get("brands") or [])
    clips = fetch_broll_videos(queries, out, count=min(8, len(segments)) or 1, orientation=orientation)
    photos = fetch_broll(queries, out) if not clips else []

    list_lines, total = [], len(segments)
    for i, seg in enumerate(segments):
        dur = max(1.6, float(seg.get("end", 0)) - float(seg.get("start", 0))) or 3.0
        mid = (float(seg.get("start", 0)) + float(seg.get("end", dur))) / 2
        template = _scene_template_at(scenes, mid)
        overlay = os.path.join(out, f"cap_{i:03d}.png")
        render_caption_overlay(overlay, w=w, h=h, title=item["working_title"], template=template,
                               text=seg.get("text", ""), index=i, total=total)
        clip = os.path.join(out, f"clip_{i:03d}.mp4")
        if clips:
            try:
                _video_clip(clips[i % len(clips)], overlay, clip, dur, w, h)
            except Exception:  # noqa: BLE001 - fall back to static for this scene
                _static_clip(overlay, clip, dur, w, h, None, i % 2 == 0)
        else:
            photo = photos[i % len(photos)] if photos else None
            _static_clip(overlay, clip, dur, w, h, photo, i % 2 == 0)
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
                      meta={"segments": total, "aspect": "9:16" if vertical else "16:9",
                            "bg": "video" if clips else ("photo" if photos else "gradient")})
    return {"duration_sec": round(duration, 1), "caption_cards": total,
            "bg": "video" if clips else ("photo" if photos else "gradient"),
            "aspect": "9:16" if vertical else "16:9"}


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
