"""Phase 1 acceptance demo (deterministic, no API keys).

Seeds realistic synthetic raw_signals, runs the REAL Trend Scout + Topic Scorer code
with mock LLM + mock embeddings, then asserts the Phase 1 acceptance criteria:
  - >= 30 deduped topics, all scored, each with a rationale
  - no duplicate signals (unique source_id+external_id)

Run via `make demo-phase-1` (sets DATABASE_URL to the host-published DB port).
"""

from __future__ import annotations

import json
import sys

from .agents.context import AgentContext
from .agents.topic_scorer import run_topic_scorer
from .agents.trend_scout import run_trend_scout
from .config import get_settings
from .db import close_pool, cursor
from .providers.embeddings import get_embedding_provider
from .providers.llm import MockLLMClient

# Distinct, realistic Indian smartphone signals (kept lexically distinct so the
# token-hashing mock embedder does not over-merge them).
_BRANDS_DEVICES = [
    ("Samsung", "Galaxy S26 Ultra"),
    ("Samsung", "Galaxy A56"),
    ("Samsung", "Galaxy M16"),
    ("OnePlus", "OnePlus 14"),
    ("OnePlus", "OnePlus 14R"),
    ("OnePlus", "Nord 5"),
    ("Apple", "iPhone 17 Pro"),
    ("Apple", "iPhone 17"),
    ("Xiaomi", "Redmi Note 15 Pro"),
    ("Xiaomi", "Xiaomi 16"),
    ("Xiaomi", "Poco X8"),
    ("iQOO", "iQOO 14"),
    ("iQOO", "iQOO Neo 11"),
    ("Vivo", "Vivo V60"),
    ("Vivo", "Vivo X300"),
    ("Realme", "Realme GT 8"),
    ("Realme", "Realme 14 Pro"),
    ("Motorola", "Moto Edge 70"),
    ("Nothing", "Nothing Phone 4"),
    ("Google", "Pixel 10"),
]

_ANGLES = [
    ("leak", "{d} leaked specs and India launch timeline surface"),
    ("launch", "{d} launched in India: price, variants and offers"),
    ("review", "{d} full review after three weeks of daily use"),
    ("comparison", "{d} vs rivals: which to buy under budget"),
    ("news", "{d} gets major software update with new camera features"),
]


def _seed_signals(target: int = 50) -> int:
    rows = []
    i = 0
    for brand, device in _BRANDS_DEVICES:
        for cat, tmpl in _ANGLES:
            title = tmpl.format(d=f"{device}")
            rows.append((f"seed-{i}", title, brand, device, cat))
            i += 1
            if len(rows) >= target:
                break
        if len(rows) >= target:
            break

    inserted = 0
    with cursor() as cur:
        cur.execute("select id from sources where active = true order by name limit 9")
        source_ids = [r["id"] for r in cur.fetchall()]
        for n, (ext, title, brand, device, cat) in enumerate(rows):
            src_id = source_ids[n % len(source_ids)]
            cur.execute(
                """
                insert into raw_signals (source_id, external_id, title, content, published_at)
                values (%s, %s, %s, %s, now())
                on conflict (source_id, external_id) do nothing
                """,
                (src_id, ext, title, f"{brand} {device} — {cat} coverage for India."),
            )
            inserted += cur.rowcount
        # Insert a deliberate duplicate to prove dedupe holds.
        cur.execute("select id from sources where active = true order by name limit 1")
        dup_src = cur.fetchone()["id"]
        cur.execute(
            """
            insert into raw_signals (source_id, external_id, title)
            values (%s, %s, %s) on conflict (source_id, external_id) do nothing
            """,
            (dup_src, "seed-0", "DUPLICATE that must be ignored"),
        )
    return inserted


def _mock_context() -> AgentContext:
    settings = get_settings()
    sonnet = settings.model_for("script")
    haiku = settings.model_for("classify")
    llm = MockLLMClient(
        responses={
            haiku: json.dumps(
                {
                    "topic_title": "",  # fall back to the signal title
                    "category": "news",
                    "devices": [],
                    "brands": [],
                    "summary": "Synthetic India smartphone coverage item.",
                    "perishable": True,
                    "slug": "",
                }
            ),
            sonnet: json.dumps(
                {
                    "trend_velocity": 0.62,
                    "search_demand": 0.71,
                    "competition_gap": 0.48,
                    "monetization_potential": 0.66,
                    "freshness": 0.8,
                    "rationale": "Strong Indian search interest for this device segment with "
                    "solid affiliate potential; coverage is moderately competitive.",
                }
            ),
        }
    )
    return AgentContext(
        settings=settings, llm=llm, embedder=get_embedding_provider("mock")
    )


def main() -> int:
    ctx = _mock_context()

    print(">> seeding synthetic signals")
    _seed_signals(50)

    print(">> running Trend Scout (clustering + classification)")
    scout = run_trend_scout(ctx)
    print("   ", scout)

    print(">> running Topic Scorer")
    scorer = run_topic_scorer(ctx)
    print("   ", scorer)

    with cursor() as cur:
        cur.execute("select count(*) as n from raw_signals")
        signals = cur.fetchone()["n"]
        cur.execute("select count(*) as n from topics where status = 'scored'")
        scored_topics = cur.fetchone()["n"]
        cur.execute(
            "select count(*) as n from topics t "
            "where status='scored' and not exists "
            "(select 1 from topic_scores s where s.topic_id=t.id and s.rationale is not null)"
        )
        missing_rationale = cur.fetchone()["n"]
        # Duplicate check: any (source_id, external_id) appearing more than once?
        cur.execute(
            "select count(*) as n from ("
            "  select source_id, external_id from raw_signals "
            "  group by source_id, external_id having count(*) > 1) d"
        )
        dup_groups = cur.fetchone()["n"]

    print(f"\n   signals stored:         {signals}")
    print(f"   scored topics:          {scored_topics}")
    print(f"   scored w/o rationale:   {missing_rationale}")
    print(f"   duplicate signal groups:{dup_groups}")

    ok = scored_topics >= 30 and missing_rationale == 0 and dup_groups == 0
    print("\nPHASE 1 ACCEPTANCE:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
