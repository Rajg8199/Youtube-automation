"""Phase 2 acceptance demo (deterministic, no API keys).

Seeds a greenlit topic with a real-looking source signal, then runs the script-factory
pipeline with a prompt-routing mock LLM, and asserts the acceptance criterion:
  greenlit topic -> QA-passed Hinglish script with zero unverified claims.

The mock routes on the agent's system prompt (all four agents share one model role, so a
single keyed mock can't tell them apart). Run via `make demo-phase-2`.
"""

from __future__ import annotations

import json
import sys

from .agents.context import AgentContext
from .agents.pipeline import run_script_pipeline
from .config import get_settings
from .db import close_pool, cursor
from .providers.embeddings import get_embedding_provider
from .providers.llm import LLMResponse

_SOURCE_URL = "https://example.com/oneplus-14-india"

# Canned JSON per agent (the script only uses the one brief fact, so QA passes).
_PLAN = {
    "working_title": "OnePlus 14 India: ₹72,999 — worth it ya overpriced?",
    "angle": "Take a stance on whether the launch price is justified for Indian buyers.",
    "format": "long",
}
_BRIEF = {
    "facts": [
        {
            "claim": "India launch price",
            "value": "₹72,999 (12GB/256GB)",
            "source_url": _SOURCE_URL,
            "confidence": 1.0,
        }
    ],
    "spec_table": {"OnePlus 14": {"variant": "12GB/256GB"}},
    "price_data": {"OnePlus 14": {"amazon": None, "flipkart": None, "launch_price": "₹72,999"}},
}
_SCRIPT = {
    "hook": "OnePlus 14 India me aa gaya — lekin ₹72,999 ki keemat, kya ye justified hai?",
    "body_markdown": (
        "[SCENE: price-tracker] India me OnePlus 14 ₹72,999 se shuru hota hai, "
        "12GB/256GB variant ke liye.\n\n"
        "[SCENE: talking-points] Is price band me competition tagdi hai — mera take aage."
    ),
    "cta": "Comment me batao — lenge ya nahi? Subscribe for the full comparison.",
    "language_mix": {"hindi_pct": 70, "english_pct": 30},
}
_QA = {"claims_checked": 1, "claims_failed": [], "policy_flags": [], "readability_notes": "Tight."}


class _RoutingMockLLM:
    """Returns canned JSON based on which agent prompt is in `system`."""

    def complete(self, *, system: str, prompt: str, model: str, max_tokens: int = 2048) -> LLMResponse:
        if "Editorial Planner" in system:
            text = json.dumps(_PLAN)
        elif "Research Compiler" in system:
            text = json.dumps(_BRIEF)
        elif "Script Writer" in system:
            text = json.dumps(_SCRIPT)
        elif "Fact-Check" in system or "QA" in system:
            text = json.dumps(_QA)
        else:
            text = "{}"
        return LLMResponse(text=text, input_tokens=len(prompt) // 4 or 1,
                           output_tokens=len(text) // 4 or 1, model=model)


def _seed_greenlit_topic() -> None:
    with cursor() as cur:
        cur.execute("select id from sources where active = true limit 1")
        src = cur.fetchone()["id"]
        cur.execute(
            """
            insert into raw_signals (source_id, external_id, title, url, content, processed)
            values (%s, 'p2-demo', %s, %s, %s, true)
            returning id
            """,
            (
                src,
                "OnePlus 14 launched in India at Rs 72,999",
                _SOURCE_URL,
                "OnePlus 14 launched in India at ₹72,999 for the 12GB/256GB variant, on Amazon.in.",
            ),
        )
        signal_id = cur.fetchone()["id"]
        cur.execute(
            """
            insert into topics (title, slug, category, devices, brands, summary, signal_ids, status)
            values (%s, %s, 'launch', %s, %s, %s, %s, 'selected')
            returning id
            """,
            (
                "OnePlus 14 India launch",
                "oneplus-14-india-launch-demo",
                ["OnePlus 14"],
                ["OnePlus"],
                "OnePlus 14 launched in India.",
                [signal_id],
            ),
        )


def main() -> int:
    settings = get_settings()
    ctx = AgentContext(settings=settings, llm=_RoutingMockLLM(),
                       embedder=get_embedding_provider("mock"))

    print(">> seeding a greenlit (selected) topic with a source signal")
    _seed_greenlit_topic()

    print(">> running script pipeline (plan -> compile -> write -> QA)")
    result = run_script_pipeline(ctx)
    print("    planner:", result["editorial_planner"])
    print("    compiler:", result["research_compiler"])
    for i, r in enumerate(result["rounds"]):
        print(f"    round {i}: writer={r['writer']} qa={r['qa']}")

    with cursor() as cur:
        cur.execute("select count(*) as n from content_items where status = 'script_approved'")
        approved = cur.fetchone()["n"]
        cur.execute(
            """
            select count(*) as n from script_qa_reports r
            join scripts s on s.id = r.script_id
            join content_items ci on ci.id = s.content_item_id
            where ci.status = 'script_approved' and r.passed = true
              and jsonb_array_length(r.claims_failed) = 0
            """
        )
        clean_qa = cur.fetchone()["n"]
        cur.execute("select count(*) as n from approvals where gate='script' and status='pending'")
        pending_gate = cur.fetchone()["n"]
        cur.execute(
            "select hook from scripts s join content_items ci on ci.id=s.content_item_id "
            "where ci.status='script_approved' limit 1"
        )
        hook_row = cur.fetchone()

    print(f"\n   script_approved items:      {approved}")
    print(f"   QA-passed, 0 unverified:    {clean_qa}")
    print(f"   pending script-gate rows:   {pending_gate}")
    if hook_row:
        print(f"   sample hook:                {hook_row['hook'][:70]}")

    ok = approved >= 1 and clean_qa >= 1 and pending_gate >= 1
    print("\nPHASE 2 ACCEPTANCE:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        code = main()
    finally:
        close_pool()
    sys.exit(code)
