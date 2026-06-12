"""Versioned agent prompts (markdown). Loaded as system prompts at runtime."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache
def load_prompt(name: str) -> str:
    """Load a prompt file by stem, e.g. load_prompt('trend_scout_v1')."""
    path = _DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")
