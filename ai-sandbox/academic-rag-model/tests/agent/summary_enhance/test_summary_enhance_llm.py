# tests/agent/summary_enhance/test_summary_enhance_llm.py
from types import SimpleNamespace

import pytest

from agent.summary_enhance.llm import DEFAULT_MODEL, MAX_OUTPUT_TOKENS, GeminiClient


class StubModels:
    def __init__(self, text, finish=None):
        self.text, self.finish, self.kwargs = text, finish, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        resp = SimpleNamespace(text=self.text)
        if self.finish is not None:
            resp.candidates = [SimpleNamespace(finish_reason=self.finish)]
        return resp


def _client(text, finish=None):
    models = StubModels(text, finish)
    return GeminiClient(SimpleNamespace(models=models), model="m-1"), models


def test_structured_returns_decoded_json_and_sends_schema_and_token_limit():
    client, models = _client('{"topics": []}')
    assert client.generate_structured("hello", {"type": "object"}) == {"topics": []}
    assert models.kwargs["model"] == "m-1" and models.kwargs["contents"] == "hello"
    cfg = models.kwargs["config"]
    assert cfg["response_mime_type"] == "application/json"
    assert cfg["response_json_schema"] == {"type": "object"}
    assert cfg["max_output_tokens"] == MAX_OUTPUT_TOKENS == 32768


def test_structured_strips_markdown_fences():
    client, _ = _client('```json\n{"topics": []}\n```')
    assert client.generate_structured("p", {}) == {"topics": []}


def test_structured_non_json_raises_value_error():
    client, _ = _client("Sure! Here is your guide.")
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


@pytest.mark.parametrize("text", [None, ""])
def test_empty_response_raises_value_error(text):
    client, _ = _client(text)
    with pytest.raises(ValueError):
        client.generate_structured("p", {})
    with pytest.raises(ValueError):
        client.generate_text("p")


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "FinishReason.MAX_TOKENS", SimpleNamespace(name="MAX_TOKENS")])
def test_truncated_response_raises_value_error(finish):
    client, _ = _client('{"topics": []}', finish=finish)
    with pytest.raises(ValueError, match="truncated"):
        client.generate_structured("p", {})
    with pytest.raises(ValueError, match="truncated"):
        client.generate_text("p")


def test_normal_finish_reason_is_fine():
    client, _ = _client('{"a": 1}', finish="STOP")
    assert client.generate_structured("p", {}) == {"a": 1}


def test_generate_text_plain():
    client, models = _client("  hello  ")
    assert client.generate_text("p") == "hello"
    cfg = models.kwargs["config"]
    assert "tools" not in cfg and "response_mime_type" not in cfg
    assert cfg["max_output_tokens"] == MAX_OUTPUT_TOKENS


def test_generate_text_with_code_execution_enables_the_tool():
    client, models = _client("42")
    assert client.generate_text("p", code_execution=True) == "42"
    tools = models.kwargs["config"]["tools"]
    assert len(tools) == 1 and tools[0].code_execution is not None


def test_model_attribute_and_default():
    assert GeminiClient(SimpleNamespace(models=None)).model == DEFAULT_MODEL
    assert "flash" in DEFAULT_MODEL


def test_unusable_responses_raise_the_dedicated_subclass():
    from agent.summary_enhance.llm import UnusableResponse
    assert issubclass(UnusableResponse, ValueError)
    for text, finish in [(None, None), ("not json", None), ('{"a": 1}', "MAX_TOKENS")]:
        client, _ = _client(text, finish)
        with pytest.raises(UnusableResponse):
            client.generate_structured("p", {})


def test_usage_is_accumulated_across_calls():
    class UsageModels(StubModels):
        def generate_content(self, **kwargs):
            resp = super().generate_content(**kwargs)
            resp.usage_metadata = SimpleNamespace(prompt_token_count=1000, candidates_token_count=300,
                                                  thoughts_token_count=50, total_token_count=1350)
            return resp

    client = GeminiClient(SimpleNamespace(models=UsageModels("ok")), model="m-1")
    assert client.usage == {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}
    client.generate_text("a")
    client.generate_text("b")
    assert client.usage == {"calls": 2, "prompt_tokens": 2000, "output_tokens": 600, "thinking_tokens": 100}


def test_usage_tolerates_a_response_without_metadata():
    client, _ = _client("ok")
    client.generate_text("a")
    assert client.usage["calls"] == 1 and client.usage["prompt_tokens"] == 0
