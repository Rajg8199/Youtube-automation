"""Phase 4 acceptance demo (deterministic, no Google API).

Seeds a finished video (ready_for_review) with a topic + scene plan + media, runs the SEO
Optimizer, approves the publish gate, and runs the Publisher — which (with no refresh token)
builds a downloadable manual publish-kit. Asserts: rich SEO + a publish_kit.zip containing the
video and metadata. Run via `make demo-phase-4`.
"""

from __future__ import annotations

import json
import os
import sys

from .db import close_pool, cursor
from .production.media import item_dir, rel_path, store_media_asset
from .publishing.publisher import run_publisher
from .publishing.seo import run_seo_optimizer
from .state_machine import transition


def _seed() -> str:
    with cursor() as cur:
        cur.execute(
            """
            insert into topics (title, slug, category, devices, brands, summary, status)
            values ('OnePlus 14 India launch', 'op14-demo-p4', 'launch',
                    %s, %s, 'OnePlus 14 launched in India.', 'converted')
            returning id
            """,
            (["OnePlus 14"], ["OnePlus"]),
        )
        topic_id = cur.fetchone()["id"]
        cur.execute(
            """
            insert into content_items (topic_id, format, working_title, angle, status, priority)
            values (%s, 'long', %s, %s, 'ready_for_review', 80)
            returning id
            """,
            (topic_id, "OnePlus 14 India: ₹72,999 — worth it ya overpriced?",
             "Is the launch price justified for Indian buyers?"),
        )
        item_id = cur.fetchone()["id"]
        cur.execute(
            "insert into scene_plans (content_item_id, scenes) values (%s, %s)",
            (item_id, json.dumps([
                {"idx": 0, "template": "intro", "caption": "hook", "duration": 6},
                {"idx": 1, "template": "price-tracker", "caption": "₹72,999", "duration": 12},
            ])),
        )

    # Placeholder media files (real bytes so the kit zips them; not a playable video here).
    out = item_dir(item_id)
    video = os.path.join(out, "final.mp4")
    with open(video, "wb") as f:
        f.write(b"\x00FAKE-MP4-FOR-DEMO\x00")
    thumb = os.path.join(out, "thumb_A.png")
    with open(thumb, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nFAKE")

    store_media_asset(content_item_id=item_id, kind="final_video", storage_path=rel_path(video),
                      duration_sec=18)
    asset_id = store_media_asset(content_item_id=item_id, kind="thumbnail", storage_path=rel_path(thumb),
                                 meta={"variant": "A"})
    with cursor() as cur:
        cur.execute(
            "insert into thumbnails (content_item_id, variant, asset_id, concept, is_selected) "
            "values (%s, 'A', %s, 'demo', true)",
            (item_id, asset_id),
        )
    return item_id


def main() -> int:
    print(">> seeding a finished video (ready_for_review)")
    item_id = _seed()

    print(">> SEO optimizer (deterministic)")
    print("   ", run_seo_optimizer())

    print(">> approving the publish gate")
    transition(content_item_id=item_id, to_status="approved", actor="human:rj",
               detail={"gate": "publish"})
    with cursor() as cur:
        cur.execute(
            "insert into approvals (content_item_id, gate, status, decided_at) "
            "values (%s, 'publish', 'approved', now())",
            (item_id,),
        )

    print(">> publisher (no refresh token -> manual publish-kit)")
    print("   ", run_publisher())

    with cursor() as cur:
        cur.execute("select title, description, cardinality(tags) as tags, affiliate_links "
                    "from seo_metadata where content_item_id = %s", (item_id,))
        seo = cur.fetchone()
        cur.execute("select method, status from publish_jobs where content_item_id = %s", (item_id,))
        pj = cur.fetchone()
        cur.execute("select status from content_items where id = %s", (item_id,))
        status = cur.fetchone()["status"]

    kit = os.path.join(item_dir(item_id), "publish_kit.zip")
    has_affiliate = bool(seo and seo["affiliate_links"])
    kit_ok = os.path.exists(kit) and os.path.getsize(kit) > 0

    print(f"\n   SEO title:        {seo['title'] if seo else None}")
    print(f"   SEO tags:         {seo['tags'] if seo else 0}")
    print(f"   affiliate links:  {has_affiliate}")
    print(f"   publish method:   {pj['method'] if pj else None}")
    print(f"   item status:      {status}")
    print(f"   publish kit:      {'present' if kit_ok else 'MISSING'}")

    ok = (seo and seo["tags"] >= 3 and has_affiliate and pj and pj["method"] == "manual_kit"
          and kit_ok and status == "scheduled")
    print("\nPHASE 4 ACCEPTANCE:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
