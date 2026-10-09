# tests/agent/summary_enhance/test_summary_enhance_cache.py
"""Prompt layout for implicit caching (shared material first, topic last) and cached-token usage."""
from types import SimpleNamespace

from agent.summary_enhance.llm import GeminiClient
from agent.summary_enhance.prompt import build_topic_prompt
from agent.summary_enhance.source_loader import load_guide

TASK = "=== TASK ==="


def _split(prompt):
    head, _, task = prompt.partition(TASK)
    return head, task


def test_two_topics_share_everything_before_the_task_block(vault):
    guide = load_guide(vault.guide)
    a = build_topic_prompt(guide, "Wald test", ["LM test"], 1400, mode="improve")
    b = build_topic_prompt(guide, "LM test", ["Wald test"], 2000, mode="improve")
    (head_a, task_a), (head_b, task_b) = _split(a), _split(b)
    assert head_a == head_b and len(head_a) > 500
    assert '"Wald test"' in task_a and '"LM test"' in task_b


def test_task_block_carries_the_topic_the_other_topics_and_the_target(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", ["LM test", "LR test"], 1400)
    head, task = _split(prompt)
    assert '"Wald test"' not in head and "1680 words" not in head and "Other topics" not in head
    assert '"Wald test"' in task and "1680 words" in task and "LM test" in task and "LR test" in task


def test_retry_errors_come_after_the_task_block(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400, errors=["too short"])
    assert prompt.index(TASK) < prompt.index("REJECTED") < prompt.index("too short")


def test_baseline_and_passages_precede_the_task_block(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400, baseline_body="BASELINE-X")
    head, _ = _split(prompt)
    assert "BASELINE-X" in head and "=== TEXTBOOK PASSAGES ===" in head and "[S1]" in head


def _client(meta):
    class Models:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text="ok", candidates=[SimpleNamespace(finish_reason=None)], usage_metadata=meta)

    return GeminiClient(SimpleNamespace(models=Models()), model="m-1")


def test_cached_prompt_tokens_are_accumulated():
    meta = SimpleNamespace(prompt_token_count=5000, candidates_token_count=10, thoughts_token_count=0,
                           cached_content_token_count=4000)
    client = _client(meta)
    assert client.usage["cached_tokens"] == 0
    client.generate_text("a")
    client.generate_text("b")
    assert client.usage["cached_tokens"] == 8000 and client.usage["prompt_tokens"] == 10000


def test_missing_cached_count_counts_as_zero():
    client = _client(SimpleNamespace(prompt_token_count=100, candidates_token_count=1, thoughts_token_count=0))
    client.generate_text("a")
    assert client.usage["cached_tokens"] == 0


def test_usage_line_mentions_cached_tokens_only_when_there_are_some():
    from agent.summary_enhance.llm import usage_line
    base = {"calls": 2, "prompt_tokens": 9000, "output_tokens": 500, "thinking_tokens": 7}
    assert usage_line(base) == ("Token usage: 2 calls, 9000 prompt tokens, 500 output tokens, 7 thinking tokens")
    assert usage_line({**base, "cached_tokens": 0}) == usage_line(base)
    assert usage_line({**base, "cached_tokens": 6000}).endswith(", 6000 of the prompt tokens cached")
