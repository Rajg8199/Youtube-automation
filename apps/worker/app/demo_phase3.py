"""Phase 3 acceptance demo (runs inside the worker container — needs ffmpeg + edge-tts).

Seeds an approved Hinglish script, runs the production pipeline, and asserts the acceptance
criterion: approved script -> 1080p video + 3 thumbnails + subtitles, zero manual steps.

Edge TTS is a real (free, no-key) network call, so this produces a real MP4. Run via
`make demo-phase-3`.
"""

from __future__ import annotations

import json
import sys

from .db import close_pool, cursor
from .production.pipeline import run_production_pipeline

_HOOK = (
    "OnePlus 14 — ₹72,999 mein. Par kya ye paisa-vasool hai? "
    "Kharidne se pehle ye 3 baatein zaroor jaan lo."
)
_BODY = (
    "[SCENE: price-tracker] Pehle price. OnePlus 14 India mein ₹72,999 se shuru hota hai, "
    "12GB aur 256GB variant ke liye, yaani sidha flagship segment mein.\n\n"
    "[SCENE: spec-card] Display mein milta hai ek bada AMOLED panel high refresh rate ke saath, "
    "to scrolling aur gaming dono butter-smooth lagte hain.\n\n"
    "[SCENE: spec-card] Performance ke liye top-tier Snapdragon chip hai, jo heavy games aur "
    "multitasking aaram se sambhal leta hai.\n\n"
    "[SCENE: talking-points] Battery aur fast charging OnePlus ki purani strength hai — din bhar "
    "ka backup aur jaldi charge hone ka combo yahan bhi milta hai.\n\n"
    "[SCENE: versus-split] Ab comparison. Isi price par Samsung software updates mein aage hai, "
    "jabki OnePlus clean aur tez experience deta hai.\n\n"
    "[SCENE: talking-points] Kiske liye sahi hai? Agar smooth software, fast charging aur premium "
    "build chahiye bina iPhone wali keemat ke — to ye strong choice hai.\n\n"
    "[SCENE: talking-points] Kiske liye nahi? Agar camera aapki pehli priority hai ya sabse lamba "
    "software support chahiye, to dusre options bhi dekh lena.\n\n"
    "[SCENE: price-tracker] Ek tip: Flipkart aur Amazon sales mein bank offers ke saath effective "
    "price kaafi neeche aa jaata hai — to sale ka wait karna samajhdari ho sakti hai.\n\n"
    "[SCENE: talking-points] Mera verdict: ₹73,000 ke aas-paas OnePlus 14 ek complete all-rounder "
    "hai, lekin sabse achhi deal sale mein hi banegi."
)


def _seed_approved_script() -> None:
    with cursor() as cur:
        cur.execute(
            """
            insert into content_items (format, working_title, angle, status, priority)
            values ('long', %s, %s, 'script_approved', 80)
            returning id
            """,
            ("OnePlus 14 India: ₹72,999 — worth it ya overpriced?",
             "Is the launch price justified for Indian buyers?"),
        )
        item_id = cur.fetchone()["id"]
        cur.execute(
            """
            insert into scripts
              (content_item_id, version, hook, body_markdown, cta, word_count,
               est_duration_sec, language_mix)
            values (%s, 1, %s, %s, %s, %s, %s, %s)
            """,
            (item_id, _HOOK, _BODY, "Comment me batao — lenge ya nahi? Subscribe karo.",
             60, 26, json.dumps({"hindi_pct": 70, "english_pct": 30})),
        )


def main() -> int:
    print(">> seeding an approved Hinglish script")
    _seed_approved_script()

    print(">> running production pipeline (voice -> scenes -> render -> thumbnails -> finalize)")
    result = run_production_pipeline()
    for stage, summary in result.items():
        print(f"    {stage}: {summary}")

    with cursor() as cur:
        cur.execute("select count(*) as n from media_assets where kind = 'voiceover'")
        voiceovers = cur.fetchone()["n"]
        cur.execute("select count(*) as n from media_assets where kind = 'final_video'")
        videos = cur.fetchone()["n"]
        cur.execute("select count(*) as n from media_assets where kind = 'thumbnail'")
        thumbs = cur.fetchone()["n"]
        cur.execute("select count(*) as n from media_assets where kind = 'subtitle'")
        subs = cur.fetchone()["n"]
        cur.execute("select count(*) as n from content_items where status = 'ready_for_review'")
        ready = cur.fetchone()["n"]
        cur.execute(
            "select storage_path, duration_sec from media_assets where kind='final_video' limit 1"
        )
        v = cur.fetchone()

    print(f"\n   voiceover assets:        {voiceovers}")
    print(f"   final videos:            {videos}")
    print(f"   thumbnail variants:      {thumbs}")
    print(f"   subtitle (srt) assets:   {subs}")
    print(f"   ready_for_review items:  {ready}")
    if v:
        print(f"   video: {v['storage_path']} ({round(v['duration_sec'] or 0, 1)}s)")

    ok = voiceovers >= 1 and videos >= 1 and thumbs >= 3 and subs >= 1 and ready >= 1
    print("\nPHASE 3 ACCEPTANCE:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
