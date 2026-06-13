"""Autonomy dial: per-gate manual | auto_with_veto | full_auto, with guardrails enforced in code.

full_auto requires the spec's earned-trust bar: >=20 published videos, >=95% QA pass rate,
and zero policy flags in the last 30 days (guardrail #1).
"""

from __future__ import annotations

from typing import Any

from ..db import cursor

GATES = ("topic_selection", "script", "publish")
MODES = ("manual", "auto_with_veto", "full_auto")

MIN_PUBLISHED = 20
MIN_QA_PASS_RATE = 0.95


def guardrail_status() -> dict[str, Any]:
    with cursor() as cur:
        cur.execute("select count(*) as n from youtube_videos")
        published = cur.fetchone()["n"]
        cur.execute("select count(*) as n, count(*) filter (where passed) as p from script_qa_reports")
        row = cur.fetchone()
        total, passed = row["n"], row["p"]
        cur.execute(
            "select count(*) as n from script_qa_reports "
            "where created_at >= now() - interval '30 days' and jsonb_array_length(policy_flags) > 0"
        )
        flags = cur.fetchone()["n"]
    qa_rate = (passed / total) if total else 1.0
    eligible = published >= MIN_PUBLISHED and qa_rate >= MIN_QA_PASS_RATE and flags == 0
    return {
        "published": published,
        "qa_pass_rate": round(qa_rate, 3),
        "policy_flags_30d": flags,
        "full_auto_eligible": eligible,
        "thresholds": {"min_published": MIN_PUBLISHED, "min_qa_pass_rate": MIN_QA_PASS_RATE},
    }


def get_autonomy() -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute("select gate, mode, updated_at from autonomy_settings order by gate")
        return cur.fetchall()


def set_autonomy(gate: str, mode: str) -> dict[str, Any]:
    if gate not in GATES:
        raise ValueError(f"unknown gate: {gate}")
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    if mode == "full_auto" and not guardrail_status()["full_auto_eligible"]:
        raise PermissionError(
            "full_auto blocked: requires >=20 published, >=95% QA pass, 0 policy flags in 30 days"
        )
    with cursor() as cur:
        cur.execute(
            """
            insert into autonomy_settings (gate, mode, updated_at) values (%s, %s, now())
            on conflict (gate) do update set mode = excluded.mode, updated_at = now()
            returning gate, mode
            """,
            (gate, mode),
        )
        return cur.fetchone()
