"""Analytics Analyst: ingest per-video metrics + retention via the YouTube Analytics API,
and map retention cliffs to script segments (the killer insight).

Live data needs a real published video + at least a day of viewing, so every call is
defensive: with no refresh token or no published videos it returns a no-op summary.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from ..config import get_settings
from ..db import cursor
from ..events import log_system_event
from . import YOUTUBE_SCOPES

COMPONENT = "service:analytics_analyst"
_METRICS = "views,estimatedMinutesWatched,averageViewPercentage,likes,comments,shares,subscribersGained,subscribersLost"


def _client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    s = get_settings()
    creds = Credentials(
        None, refresh_token=s.youtube_refresh_token, client_id=s.youtube_client_id,
        client_secret=s.youtube_client_secret, token_uri="https://oauth2.googleapis.com/token",
        scopes=YOUTUBE_SCOPES,
    )
    return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def _published_videos(cur) -> list[dict[str, Any]]:
    cur.execute("select content_item_id, youtube_video_id from youtube_videos")
    return cur.fetchall()


def _segment_at(cur, content_item_id: str, position_pct: float) -> str | None:
    """Map a 0..1 retention position to the spoken script segment playing then."""
    cur.execute(
        "select duration_sec, meta from media_assets where content_item_id = %s and kind='voiceover' "
        "order by created_at desc limit 1",
        (content_item_id,),
    )
    row = cur.fetchone()
    if not row or not row["meta"]:
        return None
    total = float(row["duration_sec"] or 0)
    segs = (row["meta"] or {}).get("segments") or []
    if total <= 0 or not segs:
        return None
    t = position_pct * total
    for seg in segs:
        if seg["start"] <= t <= seg["end"]:
            return seg["text"][:160]
    return segs[-1]["text"][:160]


def _ingest_metrics(client, cur, vid: str) -> int:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=7)
    resp = client.reports().query(
        ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
        metrics=_METRICS, dimensions="day", filters=f"video=={vid}",
    ).execute()
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = resp.get("rows", [])
    for r in rows:
        rec = dict(zip(cols, r))
        cur.execute(
            """
            insert into video_metrics_daily
              (youtube_video_id, date, views, watch_time_min, avg_pct_viewed,
               likes, comments, shares, subs_gained, subs_lost)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (youtube_video_id, date) do update set
              views=excluded.views, watch_time_min=excluded.watch_time_min,
              avg_pct_viewed=excluded.avg_pct_viewed, likes=excluded.likes,
              comments=excluded.comments, shares=excluded.shares,
              subs_gained=excluded.subs_gained, subs_lost=excluded.subs_lost
            """,
            (vid, rec.get("day"), rec.get("views"), rec.get("estimatedMinutesWatched"),
             rec.get("averageViewPercentage"), rec.get("likes"), rec.get("comments"),
             rec.get("shares"), rec.get("subscribersGained"), rec.get("subscribersLost")),
        )
    return len(rows)


def _ingest_retention(client, cur, content_item_id: str, vid: str) -> None:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=30)
    resp = client.reports().query(
        ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
        metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
        filters=f"video=={vid}",
    ).execute()
    rows = resp.get("rows", [])
    if not rows:
        return
    curve = [{"pct_position": float(p), "audience_retention": float(r)} for p, r in rows]
    cur.execute(
        "insert into retention_curves (youtube_video_id, curve) values (%s, %s)",
        (vid, json.dumps(curve)),
    )
    # Biggest consecutive drop = the cliff; map it to the script segment.
    worst_drop, worst_pos = 0.0, None
    for a, b in zip(curve, curve[1:]):
        drop = a["audience_retention"] - b["audience_retention"]
        if drop > worst_drop:
            worst_drop, worst_pos = drop, b["pct_position"]
    if worst_pos is not None and worst_drop > 0.05:
        seg = _segment_at(cur, content_item_id, worst_pos)
        cur.execute(
            """
            insert into insights (scope, ref_id, insight, evidence, confidence)
            values ('hook', %s, %s, %s, %s)
            """,
            (vid, f"Retention cliff (~{int(worst_pos*100)}%): {worst_drop:.0%} drop. Segment: {seg}",
             json.dumps({"position": worst_pos, "drop": worst_drop, "segment": seg}),
             min(1.0, worst_drop * 3)),
        )


def run_analytics_analyst(*, limit: int = 50) -> dict[str, Any]:
    s = get_settings()
    if not s.youtube_ready:
        return {"ingested": 0, "note": "no YOUTUBE_REFRESH_TOKEN — run `make youtube-auth`"}
    with cursor() as cur:
        videos = _published_videos(cur)
    if not videos:
        return {"ingested": 0, "note": "no published videos yet"}

    ingested = errors = 0
    try:
        client = _client()
    except Exception as e:  # noqa: BLE001
        log_system_event(severity="error", component=COMPONENT, message="analytics client failed",
                         detail={"error": str(e)})
        return {"ingested": 0, "error": str(e)}

    for v in videos[:limit]:
        try:
            with cursor() as cur:
                n = _ingest_metrics(client, cur, v["youtube_video_id"])
                _ingest_retention(client, cur, v["content_item_id"], v["youtube_video_id"])
            ingested += 1 if n else 0
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_system_event(severity="error", component=COMPONENT, message="ingest failed",
                             detail={"video": v["youtube_video_id"], "error": str(e)})

    summary = {"ingested": ingested, "errors": errors}
    log_system_event(severity="info", component=COMPONENT, message="analytics run complete", detail=summary)
    return summary
