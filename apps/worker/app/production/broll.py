"""Pexels b-roll: fetch a small pool of relevant stock photos to use as caption backgrounds.

Free Pexels API (needs PEXELS_API_KEY). Without a key this returns [] and the renderer falls
back to the gradient cards — so production never breaks on a missing key. License: Pexels is
free to use; we tag each asset's source for the licensing guardrail.
"""

from __future__ import annotations

import os

import httpx

from ..config import get_settings
from ..events import log_system_event

COMPONENT = "service:broll"
_SEARCH = "https://api.pexels.com/v1/search"
_VIDEO_SEARCH = "https://api.pexels.com/videos/search"


def fetch_broll_videos(queries: list[str], dest_dir: str, *, count: int = 8,
                       orientation: str = "landscape") -> list[str]:
    """Download up to `count` free Pexels STOCK VIDEO clips for the queries (moving b-roll).
    Returns local mp4 paths. Empty list if no PEXELS_API_KEY."""
    key = get_settings().pexels_api_key
    if not key:
        return []
    os.makedirs(dest_dir, exist_ok=True)
    paths: list[str] = []
    headers = {"Authorization": key}
    try:
        with httpx.Client(timeout=40.0, headers=headers) as client:
            per = max(1, count // max(1, len(queries)))
            for q in queries:
                if len(paths) >= count:
                    break
                resp = client.get(_VIDEO_SEARCH, params={
                    "query": q, "per_page": per, "orientation": orientation, "size": "medium"})
                if resp.status_code != 200:
                    continue
                for vid in resp.json().get("videos", []):
                    files = vid.get("video_files", [])
                    # pick an HD-ish mp4 not larger than ~1280 wide to keep downloads small
                    cand = sorted(
                        [f for f in files if f.get("file_type") == "video/mp4" and f.get("width")],
                        key=lambda f: abs((f.get("width") or 0) - 1280),
                    )
                    if not cand:
                        continue
                    url = cand[0]["link"]
                    r = client.get(url)
                    if r.status_code != 200:
                        continue
                    p = os.path.join(dest_dir, f"clip_{len(paths):02d}.mp4")
                    with open(p, "wb") as f:
                        f.write(r.content)
                    paths.append(p)
                    if len(paths) >= count:
                        break
    except Exception as e:  # noqa: BLE001 - best-effort; fall back to photos/gradient
        log_system_event(severity="warn", component=COMPONENT, message="pexels video fetch failed",
                         detail={"error": str(e)})
        return paths
    return paths


def fetch_broll(queries: list[str], dest_dir: str, *, count: int = 6) -> list[str]:
    """Download up to `count` landscape photos for the given queries. Returns local paths."""
    key = get_settings().pexels_api_key
    if not key:
        return []
    os.makedirs(dest_dir, exist_ok=True)
    paths: list[str] = []
    headers = {"Authorization": key}
    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            per = max(1, count // max(1, len(queries)))
            for q in queries:
                if len(paths) >= count:
                    break
                resp = client.get(_SEARCH, params={"query": q, "per_page": per,
                                                   "orientation": "landscape", "size": "large"})
                if resp.status_code != 200:
                    continue
                for photo in resp.json().get("photos", []):
                    url = photo.get("src", {}).get("landscape") or photo.get("src", {}).get("large")
                    if not url:
                        continue
                    img = client.get(url)
                    if img.status_code != 200:
                        continue
                    p = os.path.join(dest_dir, f"broll_{len(paths):02d}.jpg")
                    with open(p, "wb") as f:
                        f.write(img.content)
                    paths.append(p)
                    if len(paths) >= count:
                        break
    except Exception as e:  # noqa: BLE001 - b-roll is best-effort; fall back to gradient
        log_system_event(severity="warn", component=COMPONENT, message="pexels fetch failed",
                         detail={"error": str(e)})
        return paths
    return paths


def queries_for(devices: list[str], brands: list[str]) -> list[str]:
    qs = [f"{d} smartphone" for d in (devices or [])[:2]]
    qs += [f"{b} phone" for b in (brands or [])[:1]]
    qs += ["smartphone closeup", "technology gadget", "mobile phone hand"]
    seen, out = set(), []
    for q in qs:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:5]
