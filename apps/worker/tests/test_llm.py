"""LLM client: JSON extraction robustness + mock behavior."""

import pytest

from app.providers.llm import LLMResponse, MockLLMClient, get_llm_client


def _resp(text: str) -> LLMResponse:
    return LLMResponse(text=text, input_tokens=1, output_tokens=1, model="m")


def test_json_plain():
    assert _resp('{"a": 1}').json() == {"a": 1}


def test_json_fenced():
    assert _resp('```json\n{"a": 2}\n```').json() == {"a": 2}


def test_json_with_prose():
    text = 'Here is the result:\n{"category": "leak", "score": 0.9}\nThanks!'
    assert _resp(text).json()["category"] == "leak"


def test_json_array():
    assert _resp("[1, 2, 3]").json() == [1, 2, 3]


def test_json_invalid_raises():
    with pytest.raises(Exception):
        _resp("not json at all").json()


def test_mock_client_records_calls_and_routes_by_model():
    client = MockLLMClient(responses={"haiku": '{"ok": true}'}, default="{}")
    r = client.complete(system="s", prompt="p", model="haiku")
    assert r.json() == {"ok": True}
    assert client.calls[0]["model"] == "haiku"
    # unknown model -> default
    assert client.complete(system="s", prompt="p", model="other").json() == {}


def test_get_llm_client_falls_back_to_mock_without_key():
    assert isinstance(get_llm_client(use_mock=False, api_key=""), MockLLMClient)
    assert isinstance(get_llm_client(use_mock=True, api_key="sk-x"), MockLLMClient)
