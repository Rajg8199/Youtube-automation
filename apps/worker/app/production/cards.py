"""Pillow rendering of branded scene cards (1920x1080) and thumbnails (1280x720).

Brand kit: dark background, orange accent. Hindi text uses the Noto Devanagari font
installed in the worker image.
"""

from __future__ import annotations

from .media import (
    BG, MUTED, ORANGE, PANEL, TEXT, THUMB_H, THUMB_W, VIDEO_H, VIDEO_W, load_font,
)

_TEMPLATE_LABEL = {
    "intro": "INTRO",
    "spec-card": "SPECS",
    "versus-split": "VS",
    "price-tracker": "PRICE",
    "news-banner": "NEWS",
    "broll-overlay": "B-ROLL",
    "chart": "CHART",
    "talking-points": "POINTS",
}


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_scene_card(path: str, *, template: str, title: str, caption: str, on_screen: str) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (VIDEO_W, VIDEO_H), BG)
    d = ImageDraw.Draw(img)

    # Top accent bar + template tag + channel.
    d.rectangle([0, 0, VIDEO_W, 12], fill=ORANGE)
    tag_font = load_font(34)
    d.text((80, 60), _TEMPLATE_LABEL.get(template, "POINTS"), font=tag_font, fill=ORANGE)
    d.text((VIDEO_W - 480, 60), "PhoneWala Gyan", font=tag_font, fill=MUTED)

    # Title (small, muted).
    title_font = load_font(40)
    for i, line in enumerate(_wrap(d, title, title_font, VIDEO_W - 160)[:1]):
        d.text((80, 150), line, font=title_font, fill=MUTED)

    # Caption (if present) as a highlighted panel.
    y = 280
    if caption:
        cap_font = load_font(56)
        cap_lines = _wrap(d, caption, cap_font, VIDEO_W - 200)[:2]
        d.rectangle([60, y - 20, VIDEO_W - 60, y + 40 + 70 * len(cap_lines)], fill=PANEL)
        for line in cap_lines:
            d.text((90, y), line, font=cap_font, fill=ORANGE)
            y += 70
        y += 60

    # On-screen spoken text (the main body).
    body_font = load_font(64)
    for line in _wrap(d, on_screen, body_font, VIDEO_W - 200)[:6]:
        d.text((90, y), line, font=body_font, fill=TEXT)
        y += 84

    img.save(path)


def render_thumbnail(path: str, *, title: str, variant: str) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (THUMB_W, THUMB_H), BG)
    d = ImageDraw.Draw(img)

    if variant == "A":  # bold orange band
        d.rectangle([0, 0, 24, THUMB_H], fill=ORANGE)
        text_fill, accent = TEXT, ORANGE
    elif variant == "B":  # orange panel block
        d.rectangle([0, THUMB_H - 200, THUMB_W, THUMB_H], fill=PANEL)
        text_fill, accent = ORANGE, TEXT
    else:  # C — outline/question emphasis
        d.rectangle([12, 12, THUMB_W - 12, THUMB_H - 12], outline=ORANGE, width=10)
        text_fill, accent = TEXT, ORANGE

    title_font = load_font(96)
    lines = _wrap(d, title, title_font, THUMB_W - 160)[:4]
    total_h = len(lines) * 110
    y = (THUMB_H - total_h) // 2
    for line in lines:
        d.text((70, y), line, font=title_font, fill=text_fill)
        y += 110

    brand_font = load_font(40)
    d.text((70, THUMB_H - 70), "PhoneWala Gyan", font=brand_font, fill=accent)
    img.save(path)
