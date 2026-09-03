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

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_URL = "http://localhost:11434/api/embeddings"

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


@dataclass
class ExampleRecord:
    concept: str
    context: str
    keywords: list[str]
    embedding: list[float]
    script: str
    created_at: str  # ISO 8601, UTC


def _store_path(store_dir: str) -> str:
    return os.path.join(store_dir, "examples.json")


def _embed(text: str) -> list[float] | None:
    """POSTs to Ollama's local embeddings endpoint. Returns None on any
    network/HTTP failure (logged as a WARNING) -- never raises, mirroring
    llm_fallback.py's _call_ollama."""
    payload = json.dumps({"model": EMBEDDING_MODEL, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        EMBEDDING_URL, data=payload, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("embedding")
    except Exception as err:
        print(f"WARNING: Ollama embedding call failed ({err}) -- is `ollama serve` running "
              f"and has `ollama pull {EMBEDDING_MODEL}` been run?")
        return None


def _load(store_dir: str) -> list[ExampleRecord]:
    path = _store_path(store_dir)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [ExampleRecord(**entry) for entry in raw]
    except Exception as err:
        print(f"WARNING: example store at {path} is unreadable ({err}) -- treating as empty")
        return []


def _write(store_dir: str, records: list[ExampleRecord]) -> None:
    path = _store_path(store_dir)
    os.makedirs(store_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2, ensure_ascii=False)


EXAMPLE_SIMILARITY_THRESHOLD = 0.85  # deliberately high -- a related-but-distinct
    # topic (e.g. "eigenvalues" vs. "singular values") surfacing as a worked
    # example is worse than showing none at all
MAX_EXAMPLES = 2


def find_examples(concept: str, context: str, store_dir: str) -> list[ExampleRecord]:
    """Returns up to MAX_EXAMPLES past successful generations relevant to
    (concept, context): embedding similarity >= EXAMPLE_SIMILARITY_THRESHOLD
    if any clear it, else keyword-overlap fallback, else []. Never raises --
    any failure degrades to "no examples available" (spec §4)."""
    try:
        records = _load(store_dir)
        if not records:
            return []
        query_text = f"{concept}\n{context}"
        query_embedding = _embed(query_text)
        if query_embedding is not None:
            scored = [(_cosine_similarity(query_embedding, r.embedding), r) for r in records]
            above_threshold = [(score, r) for score, r in scored if score >= EXAMPLE_SIMILARITY_THRESHOLD]
            if above_threshold:
                above_threshold.sort(key=lambda pair: pair[0], reverse=True)
                return [r for _, r in above_threshold[:MAX_EXAMPLES]]
        query_words = _derive_keywords(query_text)
        overlapping = [
            (len(query_words & set(r.keywords)), i, r)
            for i, r in enumerate(records)
            if query_words & set(r.keywords)
        ]
        if overlapping:
            overlapping.sort(key=lambda triple: (-triple[0], triple[1]))
            return [r for _, _, r in overlapping[:MAX_EXAMPLES]]
        return []
    except Exception as err:
        print(f"WARNING: example lookup failed unexpectedly ({err}) -- proceeding without examples")
        return []


def save(concept: str, context: str, script: str, store_dir: str) -> None:
    """Appends a validated (concept, context, script) triple to the
    example store. Never raises -- a failure to save is logged as a
    WARNING and otherwise ignored; it must never turn a successful
    generation into a failed generate_via_llm() call (spec §2)."""
    try:
        query_text = f"{concept}\n{context}"
        embedding = _embed(query_text)
        if embedding is None:
            print("WARNING: could not save example -- embedding unavailable")
            return
        record = ExampleRecord(
            concept=concept, context=context,
            keywords=sorted(_derive_keywords(query_text)),
            embedding=embedding, script=script,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        records = _load(store_dir)
        records.append(record)
        _write(store_dir, records)
    except Exception as err:
        print(f"WARNING: failed to save example ({err})")
