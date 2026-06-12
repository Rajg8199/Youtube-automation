"""Worker configuration loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

StackTier = Literal["budget", "premium"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:54322/phonewala"
    stack_tier: StackTier = "budget"

    # Cost guardrails (USD). Enforced in later phases; surfaced here in Phase 0.
    monthly_cost_cap_usd: float = 50.0
    per_video_cost_cap_usd: float = 1.0

    # ---- Phase 1: research → scored topics ----
    embeddings_backend: Literal["mock", "bge-m3"] = "bge-m3"
    anthropic_api_key: str = ""
    # When true (tests/CI), agents use mock LLM + mock embeddings regardless of tier.
    use_mock_providers: bool = False

    # Clustering: cosine above this merges a signal into an existing topic.
    cluster_merge_threshold: float = 0.85

    # Polite polling
    http_user_agent: str = "PhoneWalaGyanBot/0.1 (+https://youtube.com/@phonewalagyan)"
    poll_timeout_sec: float = 20.0

    def model_for(self, role: Literal["classify", "script", "strategy"]) -> str:
        """Pick a Claude model by role, honoring budget vs premium tier."""
        if role == "classify":
            return "claude-haiku-4-5-20251001"
        if role == "strategy":
            return "claude-opus-4-8"
        return "claude-sonnet-4-6"

    @property
    def effective_embeddings_backend(self) -> str:
        return "mock" if self.use_mock_providers else self.embeddings_backend


@lru_cache
def get_settings() -> Settings:
    return Settings()
