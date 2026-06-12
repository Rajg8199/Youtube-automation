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


@lru_cache
def get_settings() -> Settings:
    return Settings()
