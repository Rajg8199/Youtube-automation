"""Unit tests for the cost calculator (no DB required)."""

import math

import pytest

from app.costs import llm_cost_usd, tts_cost_usd


def test_llm_cost_sonnet():
    # 1000 in + 500 out on Sonnet 4.6: (1000/1e6)*3 + (500/1e6)*15
    cost = llm_cost_usd("claude-sonnet-4-6", 1000, 500)
    assert math.isclose(cost, 0.003 + 0.0075, rel_tol=1e-9)


def test_llm_cost_haiku_zero_tokens():
    assert llm_cost_usd("claude-haiku-4-5-20251001", 0, 0) == 0.0


def test_gemini_free_tier_is_zero_cost():
    assert llm_cost_usd("gemini-2.0-flash", 100_000, 50_000) == 0.0
    assert llm_cost_usd("gemini-2.5-flash", 100_000, 50_000) == 0.0


def test_llm_cost_unknown_model():
    with pytest.raises(ValueError):
        llm_cost_usd("gpt-nope", 10, 10)


def test_tts_edge_is_free():
    assert tts_cost_usd("edge", 5000) == 0.0


def test_tts_sarvam_per_1k():
    # 2000 chars at $0.015/1k = $0.03
    assert math.isclose(tts_cost_usd("sarvam", 2000), 0.03, rel_tol=1e-9)


def test_tts_unknown_provider():
    with pytest.raises(ValueError):
        tts_cost_usd("unknown", 100)
