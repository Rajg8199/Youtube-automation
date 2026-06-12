"""Tier-aware model + provider selection."""

from app.config import Settings


def _settings(**kw) -> Settings:
    # Construct without reading the ambient .env so tier is deterministic.
    return Settings(_env_file=None, **kw)


def test_free_tier_uses_gemini():
    s = _settings(stack_tier="free")
    assert s.llm_provider == "gemini"
    assert s.model_for("classify") == "gemini-2.5-flash"
    assert s.model_for("script") == "gemini-2.5-flash"


def test_budget_tier_uses_claude():
    s = _settings(stack_tier="budget")
    assert s.llm_provider == "anthropic"
    assert s.model_for("classify") == "claude-haiku-4-5-20251001"
    assert s.model_for("script") == "claude-sonnet-4-6"


def test_premium_tier_uses_claude():
    s = _settings(stack_tier="premium")
    assert s.llm_provider == "anthropic"
    assert s.model_for("strategy") == "claude-opus-4-8"
