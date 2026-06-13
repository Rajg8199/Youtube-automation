"""Voice Producer: script_approved -> voiceover. Free Edge TTS (Hindi neural voice).

Splits the latest script into segments, synthesizes each to mp3, concatenates, normalizes
loudness to ~-14 LUFS, and records per-segment timing (for subtitles) on the media asset.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from ..config import get_settings
from ..db import cursor
from ..events import log_system_event
from ..state_machine import transition
from .media import item_dir, probe_duration, rel_path, run_ffmpeg, store_media_asset
from .scriptparse import split_segments, strip_scene_markers

COMPONENT = "service:voice_producer"


def _fetch(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, s.hook, s.body_markdown
        from content_items ci
        join lateral (
            select * from scripts sc where sc.content_item_id = ci.id
            order by sc.version desc limit 1
        ) s on true
        where ci.status = 'script_approved'
          and (
            coalesce((select mode from autonomy_settings where gate = 'script'), 'manual') <> 'manual'
            or exists (select 1 from approvals a
                       where a.content_item_id = ci.id and a.gate = 'script' and a.status = 'approved')
          )
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


async def _synthesize(segments: list[str], voice: str, out_dir: str) -> list[str]:
    import edge_tts

    paths: list[str] = []
    for i, seg in enumerate(segments):
        path = os.path.join(out_dir, f"seg_{i:03d}.mp3")
        await edge_tts.Communicate(seg, voice).save(path)
        paths.append(path)
    return paths


def _produce_one(item: dict[str, Any], voice: str) -> dict[str, Any]:
    out = item_dir(item["content_item_id"])
    full_text = (item["hook"] or "") + "\n" + strip_scene_markers(item["body_markdown"] or "")
    segments = split_segments(full_text)
    if not segments:
        raise ValueError("no spoken text to synthesize")

    seg_paths = asyncio.run(_synthesize(segments, voice, out))

    # Concat segments, then loudness-normalize.
    list_file = os.path.join(out, "segments.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in seg_paths:
            f.write(f"file '{os.path.basename(p)}'\n")
    raw = os.path.join(out, "voiceover_raw.mp3")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", raw])
    final = os.path.join(out, "voiceover.mp3")
    run_ffmpeg(["-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "24000", final])

    # Per-segment timing for subtitles.
    timings, cursor_t = [], 0.0
    for seg, p in zip(segments, seg_paths):
        d = probe_duration(p)
        timings.append({"text": seg, "start": round(cursor_t, 2), "end": round(cursor_t + d, 2)})
        cursor_t += d

    duration = probe_duration(final)
    store_media_asset(
        content_item_id=item["content_item_id"], kind="voiceover",
        storage_path=rel_path(final), duration_sec=duration,
        meta={"voice": voice, "segments": timings, "segment_count": len(segments)},
    )
    return {"duration_sec": round(duration, 1), "segments": len(segments)}


def run_voice_producer(*, limit: int = 20) -> dict[str, int]:
    voice = get_settings().tts_voice
    produced = errors = 0
    with cursor() as cur:
        items = _fetch(cur, limit)

    for item in items:
        try:
            info = _produce_one(item, voice)
            transition(content_item_id=item["content_item_id"], to_status="voiceover",
                       actor=COMPONENT, detail=info)
            produced += 1
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(
                severity="error", component=COMPONENT, message="voiceover failed",
                detail={"content_item_id": str(item["content_item_id"]), "error": str(e)},
            )

    summary = {"voiceovers": produced, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="voice producer run complete", detail=summary)
    return summary
