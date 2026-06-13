"""Produce one complete, publish-ready video from a hand-written evergreen script.

Seeds an approved script, runs the full production pipeline (Edge TTS voice + b-roll scene
cards + render + thumbnails), generates SEO metadata, and builds a manual publish-kit. The
script is an accurate, evergreen buying guide (no fabricated specs) so it's safe to publish.

Run: docker compose exec -T worker python -m app.make_video
"""

from __future__ import annotations

import json
import sys

from .db import close_pool, cursor
from .production.pipeline import run_production_pipeline
from .publishing.publisher import run_publisher
from .publishing.seo import run_seo_optimizer
from .state_machine import transition

WORKING_TITLE = "Naya Phone Kharidne Se Pehle — 7 ZAROORI Baatein (2026 Buying Guide)"
ANGLE = "A no-nonsense checklist that saves Indian buyers from overpaying or buying wrong."

HOOK = (
    "Naya phone lene ja rahe ho? Ruko! Ye 7 baatein check kiye bina paisa mat kharch karna — "
    "warna baad mein pachtaoge."
)
BODY = (
    "[SCENE: talking-points] Pehli baat — processor. Phone ka dimaag yahi hota hai. Gaming aur "
    "multitasking ke liye latest-generation chipset dekho, sirf core count pe mat jao.\n\n"
    "[SCENE: spec-card] Doosri — RAM aur storage. Aaj ke time kam se kam 8GB RAM rakho, aur "
    "storage 128GB se neeche mat jao, kyunki apps din-ba-din bhaari hote ja rahe hain.\n\n"
    "[SCENE: talking-points] Teesri — display. AMOLED panel aankhon ke liye behtar hai aur colours "
    "zyada vibrant deta hai. High refresh rate scrolling ko smooth bana deta hai.\n\n"
    "[SCENE: talking-points] Chauthi — battery aur charging. Bada battery din bhar aaram se chal "
    "jaata hai, aur fast charging ho to subah jaldi nikalna tension-free ho jaata hai.\n\n"
    "[SCENE: chart] Paanchvi — camera. Sirf megapixels ke chakkar mein mat pado. Zyada megapixel "
    "hamesha behtar nahi hota — sensor size aur software processing zyada maayne rakhte hain.\n\n"
    "[SCENE: talking-points] Chhati — software updates. Aisa brand chuno jo kam se kam teen saal ke "
    "updates de, taaki phone lambe samay tak secure aur fast bana rahe.\n\n"
    "[SCENE: price-tracker] Saatvi — after-sales aur sale timing. Service center aapke sheher mein "
    "ho ye confirm karo, aur Flipkart-Amazon ki badi sale ka wait karo — bank offers ke saath "
    "hazaaron rupaye bach sakte hain.\n\n"
    "[SCENE: talking-points] Bonus — sirf ads pe bharosa mat karo. Asli users ke reviews padho aur "
    "videos dekho, tabhi sahi tasveer milegi.\n\n"
    "[SCENE: talking-points] Yaad rakho — sabse mehnga phone zaroori nahi ki sabse achha ho. Apni "
    "zaroorat aur budget ke hisaab se smart choice karo."
)
CTA = "Tips kaam aaye to LIKE karo aur Subscribe zaroor karna. Comment mein batao — agla phone kaunsa loge?"

_WPS = 2.3


def _seed() -> str:
    wc = len((HOOK + " " + BODY).split())
    with cursor() as cur:
        cur.execute(
            "insert into topics (title, slug, category, devices, brands, summary, status) "
            "values (%s, %s, 'buying_guide', '{}', '{}', %s, 'converted') returning id",
            (WORKING_TITLE, "buying-guide-7-tips-2026", "Evergreen phone buying checklist for India."),
        )
        topic_id = cur.fetchone()["id"]
        cur.execute(
            "insert into content_items (topic_id, format, working_title, angle, status, priority) "
            "values (%s, 'long', %s, %s, 'script_approved', 95) returning id",
            (topic_id, WORKING_TITLE, ANGLE),
        )
        item_id = cur.fetchone()["id"]
        cur.execute(
            "insert into scripts (content_item_id, version, hook, body_markdown, cta, word_count, "
            "est_duration_sec, language_mix) values (%s, 1, %s, %s, %s, %s, %s, %s)",
            (item_id, HOOK, BODY, CTA, wc, int(wc / _WPS),
             json.dumps({"hindi_pct": 80, "english_pct": 20})),
        )
    return item_id


def main() -> int:
    print(">> seeding approved buying-guide script")
    item_id = _seed()

    print(">> production pipeline (Edge TTS + b-roll + render + thumbnails)")
    for stage, res in run_production_pipeline().items():
        print(f"   {stage}: {res}")

    print(">> SEO")
    print("  ", run_seo_optimizer())

    print(">> approve publish gate + publisher (manual kit)")
    transition(content_item_id=item_id, to_status="approved", actor="human:rj",
               detail={"gate": "publish"})
    with cursor() as cur:
        cur.execute(
            "insert into approvals (content_item_id, gate, status, decided_at) "
            "values (%s, 'publish', 'approved', now())",
            (item_id,),
        )
    print("  ", run_publisher())

    with cursor() as cur:
        cur.execute(
            "select storage_path, duration_sec from media_assets "
            "where content_item_id = %s and kind='final_video' order by created_at desc limit 1",
            (item_id,),
        )
        v = cur.fetchone()
        cur.execute("select title, description, tags from seo_metadata where content_item_id = %s "
                    "order by created_at desc limit 1", (item_id,))
        seo = cur.fetchone()

    print("\n===== PUBLISH-READY =====")
    print("content_item_id:", item_id)
    if v:
        print(f"video: {v['storage_path']}  ({round(v['duration_sec'] or 0)}s)")
    print(f"kit:   {item_id}/publish_kit.zip")
    if seo:
        print(f"\nTITLE: {seo['title']}")
        print(f"\nTAGS: {', '.join(seo['tags'] or [])}")
        print(f"\nDESCRIPTION:\n{seo['description']}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
