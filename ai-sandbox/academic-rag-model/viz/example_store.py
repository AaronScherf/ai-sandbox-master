"""
viz/example_store.py
Local example store for the Ollama fallback's few-shot prompting (spec:
docs/superpowers/specs/2026-09-03-viz-example-store-design.md). Persists
validated (concept, context, script) triples from successful
viz/llm_fallback.py generations and retrieves the most relevant past
successes for a new concept, to inject into the fallback's prompt as
worked examples.

UNVERIFIED tier -- "ran successfully" is the only bar, not "correct" or
"reviewed". Deliberately separate from the hand-written, human-reviewed
viz/templates/*.py registry (the VERIFIED tier): examples here are only
ever used as prompt context, never rendered or returned directly.
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your",
    "you", "are", "was", "were", "has", "have", "not", "but", "can",
    "will", "its",
}
_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _derive_keywords(text: str) -> set[str]:
    """Lowercases, splits on non-alphanumeric characters, and drops
    short (<3 char) and stopword tokens -- an auto-derived stand-in for
    the hand-curated keyword lists viz/templates/*.py uses, needed here
    because examples are saved automatically with no human to write a
    keyword list."""
    words = _WORD_PATTERN.findall(text.lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
