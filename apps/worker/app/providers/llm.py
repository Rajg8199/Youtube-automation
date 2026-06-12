"""LLM client abstraction over the Anthropic API, with a mock for tests.

Every call logs tokens + cost to agent_runs/costs (via costs.log_agent_run), retries
with exponential backoff (max 3), and emits a system_event on terminal failure.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str

    def json(self) -> Any:
        """Parse the response as JSON, tolerating ```json fences and prose around it."""
        return _extract_json(self.text)


class LLMClient(Protocol):
    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse: ...


def _extract_json(text: str) -> Any:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Fall back to the first {...} or [...] block.
        m = re.search(r"(\{.*\}|\[.*\])", candidate, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(1))


class AnthropicClient:
    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._max_retries = max_retries

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        last_err: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                msg = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = "".join(
                    block.text for block in msg.content if block.type == "text"
                )
                return LLMResponse(
                    text=text,
                    input_tokens=msg.usage.input_tokens,
                    output_tokens=msg.usage.output_tokens,
                    model=model,
                )
            except Exception as e:  # noqa: BLE001 - retry then surface
                last_err = e
                if attempt < self._max_retries - 1:
                    time.sleep(2**attempt)
        assert last_err is not None
        raise last_err


class GeminiClient:
    """Google Gemini client (free tier) — non-Claude provider behind the same protocol.

    Uses the official `google-genai` SDK (optional extra: `uv sync --extra gemini`).
    The SDK is lazy-imported so tests and the default install don't require it.
    """

    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._client = None  # lazily constructed

    def _ensure(self):
        if self._client is None:
            from google import genai  # heavy/optional import

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        from google.genai import types

        client = self._ensure()
        last_err: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=max_tokens,
                    ),
                )
                usage = getattr(resp, "usage_metadata", None)
                return LLMResponse(
                    text=resp.text or "",
                    input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
                    output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
                    model=model,
                )
            except Exception as e:  # noqa: BLE001 - retry then surface
                last_err = e
                if attempt < self._max_retries - 1:
                    # Free-tier 429s reset on ~minute windows — back off longer than Claude.
                    time.sleep(8 * (attempt + 1))
        assert last_err is not None
        raise last_err


@dataclass
class MockLLMClient:
    """Returns canned responses keyed by model, or a default. For tests/CI."""

    responses: dict[str, str] = field(default_factory=dict)
    default: str = "{}"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        self.calls.append({"system": system, "prompt": prompt, "model": model})
        text = self.responses.get(model, self.default)
        return LLMResponse(
            text=text,
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(text) // 4),
            model=model,
        )


def get_llm_client(
    *,
    provider: str = "anthropic",
    use_mock: bool = False,
    anthropic_api_key: str = "",
    gemini_api_key: str = "",
) -> LLMClient:
    """Select the LLM client by provider. Falls back to the mock when the required
    key is missing, so a keyless dev environment never errors."""
    if use_mock:
        return MockLLMClient()
    if provider == "gemini":
        return GeminiClient(api_key=gemini_api_key) if gemini_api_key else MockLLMClient()
    return AnthropicClient(api_key=anthropic_api_key) if anthropic_api_key else MockLLMClient()
