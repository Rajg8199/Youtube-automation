"""Phase 5 acceptance demo (in-container — needs ffmpeg for shorts).

Seeds published videos across two categories with different performance, then:
  - learning loop produces per-category priors (launch > explainer) that re-rank topics,
  - Growth Strategist writes a weekly report + recommendations,
  - shorts derivation turns a long video into a 9:16 short.
Run via `make demo-phase-5`.
"""

from __future__ import annotations

import os
import sys
import uuid

from .db import close_pool, cursor
from .intelligence.learning import category_priors, run_learning
from .intelligence.shorts import run_shorts_derivation
from .intelligence.strategist import run_growth_strategist
from .production.media import item_dir, rel_path, run_ffmpeg, store_media_asset


def _seed_published(category: str, n: int, views: int, avg_pct: float, make_long: bool) -> None:
    with cursor() as cur:
        cur.execute(
            "insert into topics (title, slug, category, status) values (%s, %s, %s, 'converted') returning id",
            (f"{category} video {n}", f"{category}-{uuid.uuid4().hex[:8]}", category),
        )
        topic_id = cur.fetchone()["id"]
        cur.execute(
            "insert into content_items (topic_id, format, working_title, status, priority) "
            "values (%s, 'long', %s, 'published', 70) returning id",
            (topic_id, f"{category.title()} explainer {n}"),
        )
        item_id = cur.fetchone()["id"]
        vid = f"yt_{category}_{n}_{uuid.uuid4().hex[:6]}"
        cur.execute(
            "insert into youtube_videos (content_item_id, youtube_video_id, published_at, format) "
            "values (%s, %s, now(), 'long')",
            (item_id, vid),
        )
        cur.execute(
            "insert into video_metrics_daily (youtube_video_id, date, views, avg_pct_viewed) "
            "values (%s, current_date, %s, %s)",
            (vid, views, avg_pct),
        )

    if make_long:
        out = item_dir(item_id)
        mp4 = os.path.join(out, "final.mp4")
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=0x141414:s=1920x1080:d=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4])
        store_media_asset(content_item_id=item_id, kind="final_video",
                          storage_path=rel_path(mp4), duration_sec=4)


def main() -> int:
    print(">> seeding published videos (launch=high perf, explainer=low perf)")
    _seed_published("launch", 1, views=12000, avg_pct=58, make_long=True)
    _seed_published("launch", 2, views=9000, avg_pct=55, make_long=False)
    _seed_published("explainer", 1, views=400, avg_pct=22, make_long=False)
    _seed_published("explainer", 2, views=300, avg_pct=18, make_long=False)

    print(">> learning loop")
    learn = run_learning()
    print("   ", learn)
    priors = category_priors()

    print(">> growth strategist")
    strat = run_growth_strategist()
    print("   ", strat)

    print(">> shorts derivation")
    shorts = run_shorts_derivation()
    print("   ", shorts)

    with cursor() as cur:
        cur.execute("select count(*) as n from recommendations")
        recs = cur.fetchone()["n"]
        cur.execute(
            "select count(*) as n from content_items ci "
            "join media_assets m on m.content_item_id = ci.id and m.kind='final_video' "
            "where ci.format = 'short'"
        )
        shorts_with_video = cur.fetchone()["n"]
        cur.execute("select count(*) as n from insights where scope='channel'")
        channel_insights = cur.fetchone()["n"]

    reranks = priors.get("launch", 0) > priors.get("explainer", 1)
    print(f"\n   priors: launch={priors.get('launch')} explainer={priors.get('explainer')}")
    print(f"   reranks (launch>explainer):  {reranks}")
    print(f"   channel insights:            {channel_insights}")
    print(f"   recommendations:             {recs}")
    print(f"   shorts with 9:16 video:      {shorts_with_video}")

    ok = reranks and channel_insights >= 2 and recs >= 1 and shorts_with_video >= 1
    print("\nPHASE 5 ACCEPTANCE:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
