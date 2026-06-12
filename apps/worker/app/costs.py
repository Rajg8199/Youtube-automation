"""Cost logger + calculator.

Every agent run, TTS call, render, and API call logs its cost to the `costs` table.
Pricing here MUST stay in sync with packages/shared/src/cost.ts (see docs/decisions.md
ADR-0006 on the deliberate duplication across runtimes).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .db import cursor

CostCategory = Literal["llm", "tts", "video_gen", "render", "storage", "api", "infra"]

# ---- Claude API pricing (USD per 1M tokens), Jan 2026 list prices ----
# Keep in sync with packages/shared/src/cost.ts MODEL_PRICING.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # model_id: (input_per_mtok, output_per_mtok)
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
}

# ---- TTS pricing (USD per 1k characters) ----
TTS_PRICING_PER_1K_CHARS: dict[str, float] = {
    "sarvam": 0.015,
    "elevenlabs": 0.30,
    "google": 0.016,
    "edge": 0.0,  # free fallback
}


def llm_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in MODEL_PRICING:
        raise ValueError(f"unknown model for pricing: {model}")
    in_rate, out_rate = MODEL_PRICING[model]
    return (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate


def tts_cost_usd(provider: str, chars: int) -> float:
    rate = TTS_PRICING_PER_1K_CHARS.get(provider)
    if rate is None:
        raise ValueError(f"unknown TTS provider for pricing: {provider}")
    return (chars / 1000) * rate


@dataclass(slots=True)
class CostEntry:
    category: CostCategory
    amount_usd: float
    content_item_id: str | None = None
    detail: dict[str, Any] | None = None


def log_cost(entry: CostEntry) -> None:
    """Insert a row into `costs`."""
    with cursor() as cur:
        cur.execute(
            """
            insert into costs (category, content_item_id, amount_usd, detail)
            values (%s, %s, %s, %s)
            """,
            (
                entry.category,
                entry.content_item_id,
                entry.amount_usd,
                json.dumps(entry.detail or {}),
            ),
        )


def log_agent_run(
    *,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    status: Literal["ok", "error", "retried"] = "ok",
    content_item_id: str | None = None,
    error: str | None = None,
) -> float:
    """Record an LLM agent run in `agent_runs` and mirror its cost in `costs`.

    Returns the computed cost in USD.
    """
    cost = llm_cost_usd(model, input_tokens, output_tokens)
    with cursor() as cur:
        cur.execute(
            """
            insert into agent_runs
              (agent, content_item_id, model, input_tokens, output_tokens,
               cost_usd, latency_ms, status, error)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                agent,
                content_item_id,
                model,
                input_tokens,
                output_tokens,
                cost,
                latency_ms,
                status,
                error,
            ),
        )
    log_cost(
        CostEntry(
            category="llm",
            amount_usd=cost,
            content_item_id=content_item_id,
            detail={"agent": agent, "model": model},
        )
    )
    return cost
