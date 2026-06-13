"""Produce one native 9:16 YouTube Short (mobile format) end-to-end.

Seeds a short (format='short') approved script, runs the full production pipeline — which
renders vertical 1080x1920 with moving Pexels b-roll + synced captions — then SEO + publish
(auto-uploads if a YouTube token is set, else builds a publish-kit).

Run: docker compose exec -T worker python -m app.make_short
"""

from __future__ import annotations

import json
import sys
import uuid

from .db import close_pool, cursor
from .production.pipeline import run_production_pipeline
from .publishing.publisher import run_publisher
from .publishing.seo import run_seo_optimizer
from .state_machine import transition

WORKING_TITLE = "Naya phone? Ye 3 galtiyan mat karna! #Shorts"
HOOK = "Naya phone le rahe ho? Ye 3 galtiyan mat karna — warna paisa barbaad!"
BODY = (
    "[SCENE: talking-points] Pehli galti — sirf megapixels dekhke camera judge karna. "
    "Sensor aur software zyada matter karte hain.\n\n"
    "[SCENE: spec-card] Doosri — kam storage lena. 128GB se neeche aaj ke time mat jao, "
    "warna 6 mahine mein bhar jayega.\n\n"
    "[SCENE: price-tracker] Teesri — full price pe kharidna. Sale aur bank offers ka wait karo, "
    "hazaaron rupaye bach jayenge."
)
CTA = "Aur aise tips ke liye PhoneWala Gyan ko follow karo!"
_WPS = 2.3


def _seed() -> str:
    wc = len((HOOK + " " + BODY).split())
    with cursor() as cur:
        cur.execute(
            "insert into topics (title, slug, category, devices, brands, summary, status) "
            "values (%s, %s, 'buying_guide', '{}', '{}', %s, 'converted') returning id",
            (WORKING_TITLE, f"short-3-mistakes-{uuid.uuid4().hex[:8]}", "Quick phone-buying mistakes."),
        )
        topic_id = cur.fetchone()["id"]
        cur.execute(
            "insert into content_items (topic_id, format, working_title, angle, status, priority) "
            "values (%s, 'short', %s, %s, 'script_approved', 95) returning id",
            (topic_id, WORKING_TITLE, "Three quick buying mistakes — punchy vertical short."),
        )
        item_id = cur.fetchone()["id"]
        cur.execute(
            "insert into scripts (content_item_id, version, hook, body_markdown, cta, word_count, "
            "est_duration_sec, language_mix) values (%s, 1, %s, %s, %s, %s, %s, %s)",
            (item_id, HOOK, BODY, CTA, wc, int(wc / _WPS),
             json.dumps({"hindi_pct": 85, "english_pct": 15})),
        )
    return item_id


def main() -> int:
    print(">> seeding approved SHORT script (9:16)")
    item_id = _seed()
    print(">> production pipeline (vertical render + video b-roll)")
    for stage, res in run_production_pipeline().items():
        print(f"   {stage}: {res}")
    print(">> SEO"); print("  ", run_seo_optimizer())
    transition(content_item_id=item_id, to_status="approved", actor="human:rj", detail={"gate": "publish"})
    with cursor() as cur:
        cur.execute("insert into approvals (content_item_id, gate, status, decided_at) "
                    "values (%s, 'publish', 'approved', now())", (item_id,))
    print(">> publisher"); print("  ", run_publisher())

    with cursor() as cur:
        cur.execute("select storage_path, duration_sec, meta from media_assets "
                    "where content_item_id=%s and kind='final_video' order by created_at desc limit 1",
                    (item_id,))
        v = cur.fetchone()
    print("\n===== SHORT READY =====")
    print("content_item_id:", item_id)
    if v:
        print(f"video: {v['storage_path']}  ({round(v['duration_sec'] or 0)}s, {v['meta'].get('aspect')}, bg={v['meta'].get('bg')})")
    print(f"kit:   {item_id}/publish_kit.zip")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
