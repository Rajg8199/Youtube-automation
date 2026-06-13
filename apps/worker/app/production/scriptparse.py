"""Pure parsing of scripts: strip/split spoken text, parse [SCENE:] markers into scenes,
and allocate per-scene durations. No I/O — unit-tested on the host.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SCENE_RE = re.compile(r"\[SCENE:\s*([^\]]+)\]")
_KNOWN_TEMPLATES = {
    "spec-card", "versus-split", "price-tracker", "news-banner",
    "broll-overlay", "chart", "talking-points", "intro",
}


@dataclass(slots=True)
class Scene:
    idx: int
    template: str
    caption: str   # short visual label from the marker (e.g. device + spec)
    text: str      # spoken text for this scene


def strip_scene_markers(text: str) -> str:
    """Remove [SCENE: ...] markers, leaving only spoken words."""
    return _SCENE_RE.sub(" ", text or "")


def _normalize_template(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    head = raw.split()[0].lower() if raw else "talking-points"
    template = head if head in _KNOWN_TEMPLATES else "talking-points"
    caption = raw[len(head):].strip() if head in _KNOWN_TEMPLATES else raw
    return template, caption


def split_segments(text: str, *, max_len: int = 240) -> list[str]:
    """Split spoken text into TTS-friendly chunks on sentence boundaries (Hindi + Latin)."""
    clean = re.sub(r"\s+", " ", strip_scene_markers(text)).strip()
    if not clean:
        return []
    # Split after sentence enders: Devanagari danda, ., !, ?
    parts = re.split(r"(?<=[।.!?])\s+", clean)
    segments: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > max_len:  # hard-wrap very long sentences
            cut = p.rfind(" ", 0, max_len)
            cut = cut if cut > 0 else max_len
            segments.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            segments.append(p)
    return segments


def parse_scenes(hook: str, body_markdown: str) -> list[Scene]:
    """Build an ordered scene list from the hook + [SCENE:]-marked body."""
    scenes: list[Scene] = [Scene(idx=0, template="intro", caption="hook", text=(hook or "").strip())]

    matches = list(_SCENE_RE.finditer(body_markdown or ""))
    if not matches:
        body = re.sub(r"\s+", " ", (body_markdown or "")).strip()
        if body:
            scenes.append(Scene(idx=1, template="talking-points", caption="", text=body))
        return [s for s in scenes if s.text]

    # Leading text before the first marker → attach to the hook scene.
    lead = body_markdown[: matches[0].start()].strip()
    if lead:
        scenes[0] = Scene(idx=0, template="intro", caption="hook",
                          text=(scenes[0].text + " " + lead).strip())

    for i, m in enumerate(matches):
        template, caption = _normalize_template(m.group(1))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_markdown)
        seg_text = re.sub(r"\s+", " ", body_markdown[m.end():end]).strip()
        scenes.append(Scene(idx=len(scenes), template=template, caption=caption, text=seg_text))

    return [s for s in scenes if s.text or s.caption]


def allocate_durations(scenes: list[Scene], total_sec: float, *, min_sec: float = 2.0) -> list[float]:
    """Distribute total voiceover seconds across scenes, weighted by spoken-text length."""
    if not scenes:
        return []
    weights = [max(1, len(s.text)) for s in scenes]
    wsum = sum(weights)
    raw = [total_sec * w / wsum for w in weights]
    return [round(max(min_sec, d), 2) for d in raw]
