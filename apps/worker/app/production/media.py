"""Shared production helpers: media paths, fonts, ffmpeg, and media_asset storage.

Files are written under <media_dir>/<content_item_id>/... and the DB stores the path
relative to media_dir (e.g. "<id>/voiceover.mp3"); the dashboard loads them from
{WORKER_URL}/media/<storage_path>.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from ..config import get_settings

# Brand kit (matches the dashboard: dark theme, orange accent).
BG = (10, 10, 10)
PANEL = (23, 23, 23)
ORANGE = (255, 106, 0)
TEXT = (240, 240, 240)
MUTED = (140, 140, 140)

VIDEO_W, VIDEO_H = 1920, 1080
THUMB_W, THUMB_H = 1280, 720

_DEVANAGARI_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]


def media_dir() -> str:
    d = get_settings().media_dir
    os.makedirs(d, exist_ok=True)
    return d


def item_dir(content_item_id: str) -> str:
    d = os.path.join(media_dir(), str(content_item_id))
    os.makedirs(d, exist_ok=True)
    return d


def rel_path(abs_path: str) -> str:
    """Path relative to media_dir, for storage + the /media URL."""
    return os.path.relpath(abs_path, media_dir())


def load_font(size: int):
    from PIL import ImageFont

    for path in _DEVANAGARI_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()[:500]}")


def probe_duration(path: str) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(proc.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def store_media_asset(
    *,
    content_item_id: str,
    kind: str,
    storage_path: str,
    duration_sec: float | None = None,
    meta: dict[str, Any] | None = None,
    cost_usd: float = 0.0,
) -> str:
    from ..db import cursor

    with cursor() as cur:
        cur.execute(
            """
            insert into media_assets
              (content_item_id, kind, storage_path, duration_sec, meta, cost_usd)
            values (%s, %s, %s, %s, %s, %s)
            returning id
            """,
            (content_item_id, kind, storage_path, duration_sec, json.dumps(meta or {}), cost_usd),
        )
        return cur.fetchone()["id"]
