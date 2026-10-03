from types import SimpleNamespace

import pytest

from agent.summary_enhance.llm import DEFAULT_MODEL, GeminiClient


class StubModels:
    def __init__(self, text):
        self.text, self.kwargs = text, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text=self.text)


def _client(text):
    models = StubModels(text)
    return GeminiClient(SimpleNamespace(models=models), model="m-1"), models


def test_returns_decoded_json_and_sends_schema():
    client, models = _client('{"topics": []}')
    out = client.generate_structured("hello", {"type": "object"})
    assert out == {"topics": []}
    assert models.kwargs["model"] == "m-1"
    assert models.kwargs["contents"] == "hello"
    cfg = models.kwargs["config"]
    assert cfg["response_mime_type"] == "application/json"
    assert cfg["response_json_schema"] == {"type": "object"}


def test_strips_markdown_fences():
    client, _ = _client('```json\n{"topics": []}\n```')
    assert client.generate_structured("p", {}) == {"topics": []}


def test_non_json_raises_value_error():
    client, _ = _client("Sure! Here is your guide.")
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


def test_empty_response_raises_value_error():
    client, _ = _client(None)
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


def test_model_attribute_and_default():
    assert GeminiClient(SimpleNamespace(models=None)).model == DEFAULT_MODEL
    assert "flash" in DEFAULT_MODEL
