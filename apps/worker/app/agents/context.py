"""Shared agent runtime context: llm client + embedder + settings."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings, get_settings
from ..providers.embeddings import EmbeddingProvider, get_embedding_provider
from ..providers.llm import LLMClient, get_llm_client


@dataclass
class AgentContext:
    settings: Settings
    llm: LLMClient
    embedder: EmbeddingProvider


def build_context(settings: Settings | None = None) -> AgentContext:
    s = settings or get_settings()
    return AgentContext(
        settings=s,
        llm=get_llm_client(
            provider=s.llm_provider,
            use_mock=s.use_mock_providers,
            anthropic_api_key=s.anthropic_api_key,
            gemini_api_key=s.gemini_api_key,
        ),
        embedder=get_embedding_provider(s.effective_embeddings_backend),
    )
