"""Publisher: approved -> published (YouTube Data API) or a manual publish-kit fallback.

API path (when YOUTUBE_REFRESH_TOKEN is set and quota allows): resumable videos.insert +
thumbnail set, recorded against the quota ledger. Otherwise it builds a downloadable kit
(video + thumbnail + metadata.txt) so you can upload by hand until the Google API audit is
approved. Either way it writes publish_jobs (+ youtube_videos on a real upload).
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from typing import Any

from ..config import get_settings
from ..db import cursor
from ..events import log_system_event
from ..production.media import item_dir, media_dir, rel_path
from ..state_machine import transition
from . import YOUTUBE_SCOPES
from .quota import COST_THUMBNAIL_SET, COST_VIDEOS_INSERT, can_spend, record_units

COMPONENT = "service:publisher"
_CATEGORY_SCIENCE_TECH = "28"


def _fetch_approved(cur, limit: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        select ci.id as content_item_id, ci.working_title,
               fv.storage_path as video_path,
               se.title, se.description, se.tags,
               (select m.storage_path from thumbnails th join media_assets m on m.id = th.asset_id
                 where th.content_item_id = ci.id order by th.is_selected desc, th.variant asc limit 1)
                 as thumb_path
        from content_items ci
        left join lateral (
            select storage_path from media_assets where content_item_id = ci.id and kind = 'final_video'
            order by created_at desc limit 1
        ) fv on true
        left join lateral (
            select title, description, tags from seo_metadata where content_item_id = ci.id
            order by created_at desc limit 1
        ) se on true
        where ci.status = 'approved'
        order by ci.priority desc, ci.created_at asc
        limit %s
        """,
        (limit,),
    )
    return cur.fetchall()


def _abs(rel: str | None) -> str | None:
    return os.path.join(media_dir(), rel) if rel else None


def _api_upload(item: dict[str, Any], video_abs: str, thumb_abs: str | None) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    s = get_settings()
    creds = Credentials(
        None, refresh_token=s.youtube_refresh_token, client_id=s.youtube_client_id,
        client_secret=s.youtube_client_secret, token_uri="https://oauth2.googleapis.com/token",
        scopes=YOUTUBE_SCOPES,
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": (item.get("title") or item["working_title"])[:100],
            "description": item.get("description") or "",
            "tags": item.get("tags") or [],
            "categoryId": _CATEGORY_SCIENCE_TECH,
        },
        "status": {"privacyStatus": s.youtube_privacy, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(video_abs, resumable=True, chunksize=-1),
    )
    response = None
    while response is None:
        _, response = req.next_chunk()
    video_id = response["id"]
    if thumb_abs and os.path.exists(thumb_abs):
        try:
            yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_abs)).execute()
            record_units(COST_THUMBNAIL_SET)
        except Exception as e:  # noqa: BLE001 - custom thumbnails need a verified channel
            log_system_event(severity="warn", component=COMPONENT,
                             message="thumbnail set failed (channel may be unverified)",
                             detail={"video_id": video_id, "error": str(e)})
    record_units(COST_VIDEOS_INSERT)
    return video_id


def _build_kit(item: dict[str, Any], video_abs: str, thumb_abs: str | None) -> str:
    out = item_dir(item["content_item_id"])
    kit_path = os.path.join(out, "publish_kit.zip")
    meta = (
        f"TITLE:\n{item.get('title') or item['working_title']}\n\n"
        f"DESCRIPTION:\n{item.get('description') or ''}\n\n"
        f"TAGS:\n{', '.join(item.get('tags') or [])}\n\n"
        f"CATEGORY: Science & Technology (28)\n"
        f"PRIVACY: {get_settings().youtube_privacy}\n"
        f"DISCLOSURE: altered/AI-assisted content — enable the disclosure on upload.\n"
    )
    with zipfile.ZipFile(kit_path, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.exists(video_abs):
            z.write(video_abs, "video.mp4")
        if thumb_abs and os.path.exists(thumb_abs):
            z.write(thumb_abs, "thumbnail.png")
        z.writestr("metadata.txt", meta)
    return kit_path


def run_publisher(*, limit: int = 5) -> dict[str, Any]:
    s = get_settings()
    published = kits = errors = 0
    with cursor() as cur:
        items = _fetch_approved(cur, limit)

    for item in items:
        cid = item["content_item_id"]
        video_abs = _abs(item.get("video_path"))
        thumb_abs = _abs(item.get("thumb_path"))
        if not video_abs or not os.path.exists(video_abs):
            errors += 1
            log_system_event(severity="error", component=COMPONENT, message="no final video",
                             detail={"content_item_id": str(cid)})
            continue
        try:
            transition(content_item_id=cid, to_status="scheduled", actor=COMPONENT)
            use_api = s.youtube_ready and can_spend(COST_VIDEOS_INSERT + COST_THUMBNAIL_SET)

            if use_api:
                transition(content_item_id=cid, to_status="publishing", actor=COMPONENT)
                video_id = _api_upload(item, video_abs, thumb_abs)
                with cursor() as cur:
                    cur.execute(
                        "insert into publish_jobs (content_item_id, method, status, youtube_video_id, quota_cost) "
                        "values (%s, 'api', 'done', %s, %s)",
                        (cid, video_id, COST_VIDEOS_INSERT + COST_THUMBNAIL_SET),
                    )
                    cur.execute(
                        "insert into youtube_videos (content_item_id, youtube_video_id, published_at, format) "
                        "values (%s, %s, now(), 'long') on conflict (youtube_video_id) do nothing",
                        (cid, video_id),
                    )
                transition(content_item_id=cid, to_status="published", actor=COMPONENT,
                           detail={"youtube_video_id": video_id, "privacy": s.youtube_privacy})
                published += 1
            else:
                kit = _build_kit(item, video_abs, thumb_abs)
                reason = "quota_blocked" if s.youtube_ready else "no_refresh_token"
                with cursor() as cur:
                    cur.execute(
                        "insert into publish_jobs (content_item_id, method, status, error) "
                        "values (%s, 'manual_kit', 'done', %s)",
                        (cid, reason),
                    )
                # Stay at 'scheduled' — kit is ready for manual upload.
                kits += 1
                log_system_event(severity="info", component=COMPONENT,
                                 message=f"manual kit built ({reason})",
                                 detail={"content_item_id": str(cid), "kit": rel_path(kit)})
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(severity="error", component=COMPONENT, message="publish failed",
                             detail={"content_item_id": str(cid), "error": str(e)})

    summary = {"published": published, "kits": kits, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="publisher run complete", detail=summary)
    return summary
