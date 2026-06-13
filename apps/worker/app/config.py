"""Worker configuration loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

StackTier = Literal["free", "budget", "premium"]
Role = Literal["classify", "script", "strategy"]

# Per-role model maps. `free` uses Google Gemini (free tier); budget/premium use Claude.
# Keep model IDs in sync with costs.py MODEL_PRICING.
# gemini-2.5-flash across roles: 2.0-flash's free-tier request quota is 0 on some
# projects/regions, whereas 2.5-flash is broadly available on the free tier.
_GEMINI_MODELS: dict[str, str] = {
    "classify": "gemini-2.5-flash",
    "script": "gemini-2.5-flash",
    "strategy": "gemini-2.5-flash",
}
_CLAUDE_MODELS: dict[str, str] = {
    "classify": "claude-haiku-4-5-20251001",
    "script": "claude-sonnet-4-6",
    "strategy": "claude-opus-4-8",
}


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
    gemini_api_key: str = ""
    # When true (tests/CI), agents use mock LLM + mock embeddings regardless of tier.
    use_mock_providers: bool = False

    # Clustering: cosine above this merges a signal into an existing topic.
    cluster_merge_threshold: float = 0.85

    # Polite polling
    http_user_agent: str = "PhoneWalaGyanBot/0.1 (+https://youtube.com/@phonewalagyan)"
    poll_timeout_sec: float = 20.0

    # ---- Phase 3: production ----
    media_dir: str = "media"  # where rendered audio/video/thumbnails are written + served
    tts_voice: str = "hi-IN-MadhurNeural"  # free Edge TTS Hindi voice
    tts_voice_female: str = "hi-IN-SwaraNeural"

    # ---- Phase 4: publish + analytics ----
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""
    youtube_privacy: str = "private"  # unverified apps lock uploads to private anyway
    youtube_daily_quota: int = 10000  # default YouTube Data API units/day
    amazon_associates_tag: str = ""
    flipkart_affiliate_id: str = ""

    @property
    def youtube_ready(self) -> bool:
        return bool(self.youtube_client_id and self.youtube_client_secret and self.youtube_refresh_token)

    @property
    def llm_provider(self) -> Literal["gemini", "anthropic"]:
        """`free` tier → Gemini (free); `budget`/`premium` → Claude."""
        return "gemini" if self.stack_tier == "free" else "anthropic"

    def model_for(self, role: Role) -> str:
        """Pick a model by role for the active tier's provider."""
        table = _GEMINI_MODELS if self.llm_provider == "gemini" else _CLAUDE_MODELS
        return table[role]

    @property
    def effective_embeddings_backend(self) -> str:
        return "mock" if self.use_mock_providers else self.embeddings_backend


@lru_cache
def get_settings() -> Settings:
    return Settings()
