"""Test helpers for the revise stage: a scripted LLM and a deterministic bag-of-words embedder."""
from __future__ import annotations


class ScriptedLLM:
    model = "fake-revise"

    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls: list[str] = []
        self.kinds: list[str] = []
        self.usage = {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "cached_tokens": 0}

    def _next(self):
        self.usage["calls"] += 1
        self.usage["prompt_tokens"] += 100
        self.usage["output_tokens"] += 10
        self.usage["thinking_tokens"] += 50
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        self.kinds.append("structured")
        return self._next()

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        self.kinds.append("code" if code_execution else "text")
        return self._next()


def bag_embed(vocab):
    """Embedder: word counts over `vocab` (cosine similarity then tracks shared vocabulary)."""
    def embed(text: str) -> list[float]:
        low = text.lower()
        return [float(low.count(w)) for w in vocab]
    return embed
