"""Learning loop: turn published performance into per-category priors that re-rank new topics.

`category_priors()` is read live by the Topic Scorer (predicted_views_score), so as videos
publish and gather metrics, the scorer demonstrably re-ranks. `run_learning()` is the periodic
job that snapshots those priors as insights for visibility.
"""

from __future__ import annotations

from typing import Any

from ..db import cursor
from ..events import log_system_event

COMPONENT = "service:learning"


def category_priors() -> dict[str, float]:
    """Per-category performance prior in [0,1] from published videos' latest metrics.

    Blend of average % viewed (retention) and views (reach), normalized across categories.
    Empty until there are published videos with metrics.
    """
    with cursor() as cur:
        cur.execute(
            """
            select t.category,
                   avg(coalesce(m.avg_pct_viewed, 0)) as ap,
                   avg(coalesce(m.views, 0)) as v,
                   count(*) as n
            from youtube_videos yv
            join content_items ci on ci.id = yv.content_item_id
            join topics t on t.id = ci.topic_id
            left join lateral (
                select * from video_metrics_daily d
                where d.youtube_video_id = yv.youtube_video_id
                order by date desc limit 1
            ) m on true
            where t.category is not null
            group by t.category
            """
        )
        rows = cur.fetchall()
    if not rows:
        return {}
    max_v = max((float(r["v"] or 0) for r in rows), default=0) or 1.0
    priors: dict[str, float] = {}
    for r in rows:
        ap = min(1.0, float(r["ap"] or 0) / 100.0)   # avg_pct_viewed is 0..100
        vn = float(r["v"] or 0) / max_v               # views normalized 0..1
        priors[r["category"]] = round(0.6 * ap + 0.4 * vn, 3)
    return priors


def run_learning(*, limit: int = 0) -> dict[str, Any]:  # limit unused; uniform job signature
    priors = category_priors()
    if not priors:
        return {"categories": 0, "note": "no published videos with metrics yet"}

    with cursor() as cur:
        # Refresh channel-scope category insights.
        cur.execute("delete from insights where scope = 'channel' and ref_id like 'category:%'")
        for cat, score in sorted(priors.items(), key=lambda kv: -kv[1]):
            cur.execute(
                """
                insert into insights (scope, ref_id, insight, evidence, confidence, actionable)
                values ('channel', %s, %s, %s, %s, true)
                """,
                (f"category:{cat}",
                 f"'{cat}' videos perform at {score:.0%} (blended retention+reach prior).",
                 f'{{"category": "{cat}", "prior": {score}}}', min(1.0, 0.4 + score / 2)),
            )
    summary = {"categories": len(priors), "priors": priors}
    log_system_event(severity="info", component=COMPONENT, message="learning run complete", detail=summary)
    return summary
