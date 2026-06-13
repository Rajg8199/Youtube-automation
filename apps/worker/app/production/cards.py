"""Pillow rendering of caption cards (1920x1080) and thumbnails (1280x720).

Hinglish mixes Devanagari + Latin, and no single installed font covers both well, so text is
drawn run-by-run: Devanagari runs use Noto Sans Devanagari, everything else (Latin, digits, ₹)
uses Noto Sans. Each card shows one narrated sentence large + centred (synced captions), with
a header, scene chip, and progress bar. Brand: dark + orange.
"""

from __future__ import annotations

import os
from functools import lru_cache

from .media import ORANGE, THUMB_H, THUMB_W, VIDEO_H, VIDEO_W

TEXT = (245, 245, 245)
MUTED = (150, 150, 150)
_TOP = (14, 14, 18)
_BOTTOM = (30, 18, 8)

_DEVA_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
]
_LATIN_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

_TEMPLATE_LABEL = {
    "intro": "INTRO", "spec-card": "SPECS", "versus-split": "VS", "price-tracker": "PRICE",
    "news-banner": "NEWS", "broll-overlay": "VISUAL", "chart": "DATA", "talking-points": "POINT",
}


@lru_cache(maxsize=64)
def _font(deva: bool, size: int):
    from PIL import ImageFont

    for path in (_DEVA_CANDIDATES if deva else _LATIN_CANDIDATES):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _is_deva(ch: str) -> bool:
    return 0x900 <= ord(ch) <= 0x97F


def _runs(text: str):
    """Split text into consecutive (run, is_devanagari) segments; spaces join the current run."""
    runs, cur, cur_deva = [], "", None
    for ch in text or "":
        d = _is_deva(ch)
        if ch == " " and cur_deva is not None:
            d = cur_deva
        if cur_deva is None:
            cur, cur_deva = ch, d
        elif d == cur_deva:
            cur += ch
        else:
            runs.append((cur, cur_deva))
            cur, cur_deva = ch, d
    if cur:
        runs.append((cur, cur_deva))
    return runs


def _measure(draw, text: str, size: int) -> float:
    return sum(draw.textlength(r, font=_font(d, size)) for r, d in _runs(text))


def _draw_mixed(draw, x: float, y: float, text: str, size: int, fill) -> None:
    for r, d in _runs(text):
        f = _font(d, size)
        draw.text((x, y), r, font=f, fill=fill)
        x += draw.textlength(r, font=f)


def _wrap_mixed(draw, text: str, size: int, max_w: int) -> list[str]:
    lines, cur = [], ""
    for w in (text or "").split():
        trial = (cur + " " + w).strip()
        if _measure(draw, trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _gradient(w: int, h: int):
    from PIL import Image

    base = Image.new("RGB", (w, h), _TOP)
    px = base.load()
    for y in range(h):
        t = y / max(1, h - 1)
        row = (
            int(_TOP[0] + (_BOTTOM[0] - _TOP[0]) * t),
            int(_TOP[1] + (_BOTTOM[1] - _TOP[1]) * t),
            int(_TOP[2] + (_BOTTOM[2] - _TOP[2]) * t),
        )
        for x in range(w):
            px[x, y] = row
    return base


def render_segment_card(
    path: str, *, title: str, template: str, text: str, index: int, total: int
) -> None:
    from PIL import ImageDraw

    img = _gradient(VIDEO_W, VIDEO_H)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, VIDEO_H], fill=ORANGE)

    # Header: brand + scene chip.
    _draw_mixed(d, 70, 56, "PhoneWala Gyan", 38, ORANGE)
    chip = _TEMPLATE_LABEL.get(template, "POINT")
    cw = _measure(d, chip, 30)
    d.rounded_rectangle([VIDEO_W - 90 - cw - 40, 54, VIDEO_W - 70, 104], radius=14,
                        fill=(40, 28, 14), outline=ORANGE, width=2)
    _draw_mixed(d, VIDEO_W - 90 - cw - 20, 62, chip, 30, ORANGE)

    # Context title (muted).
    for line in _wrap_mixed(d, title, 40, VIDEO_W - 160)[:1]:
        _draw_mixed(d, 70, 130, line, 40, MUTED)

    # Main spoken line — large, centred (the content).
    size = 84 if len(text) < 85 else (70 if len(text) < 150 else 58)
    lines = _wrap_mixed(d, text, size, VIDEO_W - 220)[:6]
    line_h = size + 24
    y = (VIDEO_H - len(lines) * line_h) // 2 + 20
    for line in lines:
        lw = _measure(d, line, size)
        _draw_mixed(d, (VIDEO_W - lw) / 2, y, line, size, TEXT)
        y += line_h

    # Progress bar.
    bar_y = VIDEO_H - 70
    d.rectangle([70, bar_y, VIDEO_W - 70, bar_y + 8], fill=(45, 45, 50))
    frac = (index + 1) / max(1, total)
    d.rectangle([70, bar_y, 70 + int((VIDEO_W - 140) * frac), bar_y + 8], fill=ORANGE)
    img.save(path)


def render_thumbnail(path: str, *, title: str, variant: str) -> None:
    from PIL import ImageDraw

    img = _gradient(THUMB_W, THUMB_H)
    d = ImageDraw.Draw(img)
    if variant == "A":
        d.rectangle([0, 0, 22, THUMB_H], fill=ORANGE)
        fill = TEXT
    elif variant == "B":
        d.rectangle([0, THUMB_H - 190, THUMB_W, THUMB_H], fill=(40, 28, 14))
        fill = ORANGE
    else:
        d.rounded_rectangle([14, 14, THUMB_W - 14, THUMB_H - 14], radius=20, outline=ORANGE, width=10)
        fill = TEXT

    lines = _wrap_mixed(d, title, 92, THUMB_W - 150)[:4]
    y = (THUMB_H - len(lines) * 108) // 2
    for line in lines:
        _draw_mixed(d, 64, y, line, 92, fill)
        y += 108
    _draw_mixed(d, 64, THUMB_H - 66, "PhoneWala Gyan", 38, ORANGE)
    img.save(path)
