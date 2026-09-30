# Viz Local Example Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Ollama fallback (`viz/llm_fallback.py`) a local, free memory of its own past successful generations, injected as few-shot examples into future prompts for similar concepts.

**Architecture:** A new sibling module, `viz/example_store.py`, persists validated `(concept, context, script)` triples to a flat JSON file and retrieves the most relevant ones for a new concept via local-Ollama embedding similarity (high threshold), falling back to auto-derived-keyword overlap, falling back to nothing. `viz/llm_fallback.py` calls `find_examples()` once per `generate_via_llm()` call (before the retry loop) and `save()` once, only on the attempt that actually succeeds.

**Tech Stack:** Python 3, stdlib only (`json`, `urllib.request`, `dataclasses`, `re`, `datetime`) — no new pip dependency. Ollama's `/api/embeddings` endpoint with the `nomic-embed-text` model (separate pull from the existing `qwen2.5-coder:7b` generation model).

**Spec:** `docs/superpowers/specs/2026-09-03-viz-example-store-design.md`

## Global Constraints

- Embeddings come from local Ollama (`nomic-embed-text` @ `http://localhost:11434/api/embeddings`) — never the project's paid Gemini embedding API. This tier stays free of paid calls, matching the existing fallback tier's own principle.
- `EXAMPLE_SIMILARITY_THRESHOLD = 0.85` — deliberately high; a related-but-distinct topic must not surface as an example.
- `MAX_EXAMPLES = 2`.
- Storage is a single flat JSON file at `<academic_hub_root>/.viz/.examples/examples.json` — already covered by the repo's existing `**/.viz/` gitignore pattern, no gitignore change needed.
- `find_examples()` and `save()` must never raise past their caller — any failure (Ollama unreachable, corrupt store file) is caught, logged as a `WARNING: ...` printed line, and degrades to "no examples available" / "example not saved", never blocks or fails a generation.
- The example store is the **unverified** tier (only bar: "it executed successfully") and stays structurally separate from `viz/templates/*.py`, the **verified** tier (hand-written, reviewed). Examples are only ever injected as prompt text — never rendered, never added to `TEMPLATE_REGISTRY`, never returned directly from `generate_via_llm()`.
- `find_examples()` is called exactly once per `generate_via_llm()` call (before the attempt loop starts), not once per attempt. `save()` is called exactly once, only for the code that actually succeeded — an intermediate failed attempt is never saved.
- Test runner: `./.venv/Scripts/python.exe -m unittest discover -s tests`, run from `ai-sandbox/academic-rag-model/`.

---

### Task 1: Pure matching helpers — `_derive_keywords`, `_cosine_similarity`

**Files:**
- Create: `viz/example_store.py`
- Test: `tests/test_example_store.py`

**Interfaces:**
- Produces: `_derive_keywords(text: str) -> set[str]`, `_cosine_similarity(a: list[float], b: list[float]) -> float`. Both pure, no I/O — later tasks depend on these exact names and signatures.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_example_store.py`:

```python
import unittest

from viz.example_store import _cosine_similarity, _derive_keywords


class TestDeriveKeywords(unittest.TestCase):
    def test_drops_short_words_and_stopwords(self):
        result = _derive_keywords("The eigenvectors and eigenvalues of a symmetric matrix")
        self.assertEqual(result, {"eigenvectors", "eigenvalues", "symmetric", "matrix"})

    def test_lowercases_and_splits_on_non_alphanumeric(self):
        result = _derive_keywords("Gradient-Descent: Convergence!")
        self.assertEqual(result, {"gradient", "descent", "convergence"})

    def test_empty_text_returns_empty_set(self):
        self.assertEqual(_derive_keywords(""), set())


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_similarity_is_one(self):
        self.assertAlmostEqual(_cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_similarity_is_zero(self):
        self.assertAlmostEqual(_cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_empty_vector_returns_zero(self):
        self.assertEqual(_cosine_similarity([], [1.0, 0.0]), 0.0)

    def test_mismatched_length_returns_zero(self):
        self.assertEqual(_cosine_similarity([1.0], [1.0, 0.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v` (from `ai-sandbox/academic-rag-model/`)
Expected: `ModuleNotFoundError: No module named 'viz.example_store'`

- [ ] **Step 3: Write minimal implementation**

Create `viz/example_store.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: all `TestDeriveKeywords` and `TestCosineSimilarity` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add viz/example_store.py tests/test_example_store.py
git commit -m "feat(viz): add pure matching helpers for example store"
```

---

### Task 2: `ExampleRecord`, JSON storage (`_load`/`_write`), and `_embed`

**Files:**
- Modify: `viz/example_store.py`
- Test: `tests/test_example_store.py`

**Interfaces:**
- Consumes: nothing from Task 1 directly (this task's functions are independent), but shares the module.
- Produces: `ExampleRecord` dataclass (fields: `concept: str`, `context: str`, `keywords: list[str]`, `embedding: list[float]`, `script: str`, `created_at: str`), `_store_path(store_dir: str) -> str`, `_load(store_dir: str) -> list[ExampleRecord]`, `_write(store_dir: str, records: list[ExampleRecord]) -> None`, `_embed(text: str) -> list[float] | None`. Later tasks (3, 4) call all of these.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_example_store.py` (below the existing imports, add `json`, `os`, `tempfile`, and `unittest.mock`):

```python
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from viz.example_store import ExampleRecord, _embed, _load, _store_path, _write
```

Add these test classes:

```python
class TestEmbed(unittest.TestCase):
    @patch("viz.example_store.urllib.request.urlopen")
    def test_returns_embedding_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = _embed("eigenvalues")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("viz.example_store.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(_embed("eigenvalues"))


class TestLoadWriteRoundTrip(unittest.TestCase):
    def test_write_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as store_dir:
            record = ExampleRecord(
                concept="spectral decomposition", context="some passage text",
                keywords=["spectral", "decomposition"], embedding=[0.1, 0.2],
                script="fig = go.Figure()", created_at="2026-09-03T00:00:00+00:00",
            )
            _write(store_dir, [record])
            loaded = _load(store_dir)
            self.assertEqual(loaded, [record])

    def test_load_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            self.assertEqual(_load(store_dir), [])

    def test_load_corrupt_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            path = _store_path(store_dir)
            with open(path, "w", encoding="utf-8") as f:
                f.write("not valid json{{{")
            self.assertEqual(_load(store_dir), [])

    def test_write_creates_store_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_dir = os.path.join(tmp, "nested", ".examples")
            record = ExampleRecord(
                concept="c", context="", keywords=[], embedding=[0.1],
                script="fig = go.Figure()", created_at="2026-09-03T00:00:00+00:00",
            )
            _write(store_dir, [record])
            self.assertTrue(os.path.exists(_store_path(store_dir)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: `ImportError: cannot import name 'ExampleRecord' from 'viz.example_store'`

- [ ] **Step 3: Write minimal implementation**

Add to `viz/example_store.py` (below the existing imports, add `json`, `os`, `urllib.error`, `urllib.request`, and `dataclasses`):

```python
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_URL = "http://localhost:11434/api/embeddings"


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: all tests in `TestEmbed` and `TestLoadWriteRoundTrip` PASS (plus Task 1's tests still passing).

- [ ] **Step 5: Commit**

```bash
git add viz/example_store.py tests/test_example_store.py
git commit -m "feat(viz): add ExampleRecord storage and local Ollama embedding call"
```

---

### Task 3: `find_examples` — the selection cascade

**Files:**
- Modify: `viz/example_store.py`
- Test: `tests/test_example_store.py`

**Interfaces:**
- Consumes: `ExampleRecord`, `_embed`, `_load`, `_write`, `_derive_keywords`, `_cosine_similarity` (all from Tasks 1-2).
- Produces: `find_examples(concept: str, context: str, store_dir: str) -> list[ExampleRecord]`, plus module constants `EXAMPLE_SIMILARITY_THRESHOLD = 0.85` and `MAX_EXAMPLES = 2`. Task 5 calls `find_examples` by this exact name and signature.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_example_store.py`:

```python
from viz.example_store import EXAMPLE_SIMILARITY_THRESHOLD, MAX_EXAMPLES, find_examples


def _record(concept, keywords, embedding, script="fig = go.Figure()"):
    return ExampleRecord(
        concept=concept, context="", keywords=keywords, embedding=embedding,
        script=script, created_at="2026-09-03T00:00:00+00:00",
    )


class TestFindExamples(unittest.TestCase):
    def test_empty_store_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as store_dir:
            self.assertEqual(find_examples("eigenvalues", "", store_dir), [])

    @patch("viz.example_store._embed")
    def test_returns_matches_above_threshold_highest_first(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            best_match = _record("eigenvectors basics", ["eigenvectors"], [1.0, 0.0])
            second_match = _record("spectral decomposition", ["spectral", "decomposition"], [0.99, 0.01])
            below_threshold = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [second_match, best_match, below_threshold])
            mock_embed.return_value = [1.0, 0.0]
            result = find_examples("eigenvalues", "", store_dir)
            self.assertEqual(result, [best_match, second_match])

    @patch("viz.example_store._embed")
    def test_falls_back_to_keywords_when_nothing_above_threshold(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent optimization", ["gradient", "descent", "optimization"], [0.0, 1.0])
            _write(store_dir, [record])
            mock_embed.return_value = [1.0, 0.0]  # orthogonal -- similarity 0.0, below threshold
            result = find_examples("gradient descent for neural networks", "", store_dir)
            self.assertEqual(result, [record])

    @patch("viz.example_store._embed")
    def test_returns_empty_when_neither_embedding_nor_keywords_match(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            mock_embed.return_value = [1.0, 0.0]
            result = find_examples("totally unrelated topic", "", store_dir)
            self.assertEqual(result, [])

    @patch("viz.example_store._embed", return_value=None)
    def test_embedding_failure_falls_back_to_keywords(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            result = find_examples("gradient descent basics", "", store_dir)
            self.assertEqual(result, [record])

    @patch("viz.example_store._embed", return_value=None)
    def test_embedding_and_keyword_both_fail_returns_empty(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            record = _record("gradient descent", ["gradient", "descent"], [0.0, 1.0])
            _write(store_dir, [record])
            result = find_examples("totally unrelated", "", store_dir)
            self.assertEqual(result, [])

    def test_caps_at_max_examples(self):
        with tempfile.TemporaryDirectory() as store_dir:
            records = [_record(f"concept {i}", ["shared"], [1.0, 0.0]) for i in range(5)]
            _write(store_dir, records)
            with patch("viz.example_store._embed", return_value=[1.0, 0.0]):
                result = find_examples("shared topic", "", store_dir)
            self.assertEqual(len(result), MAX_EXAMPLES)

    def test_keyword_fallback_ties_broken_by_insertion_order(self):
        with tempfile.TemporaryDirectory() as store_dir:
            first = _record("first concept", ["shared", "gradient"], [0.0, 1.0])
            second = _record("second concept", ["shared", "gradient"], [0.0, 1.0])
            third = _record("third concept", ["shared"], [0.0, 1.0])
            _write(store_dir, [first, second, third])
            with patch("viz.example_store._embed", return_value=None):
                result = find_examples("shared gradient topic", "", store_dir)
            # first and second both overlap on {"shared", "gradient"} (2 words, tied) --
            # insertion order breaks the tie, so first comes before second; third
            # overlaps on only {"shared"} (1 word) and loses to both on overlap count.
            self.assertEqual(result, [first, second])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: `ImportError: cannot import name 'find_examples' from 'viz.example_store'`

- [ ] **Step 3: Write minimal implementation**

Add to `viz/example_store.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: all `TestFindExamples` tests PASS (plus all earlier tests still passing).

- [ ] **Step 5: Commit**

```bash
git add viz/example_store.py tests/test_example_store.py
git commit -m "feat(viz): add find_examples selection cascade (embedding -> keyword -> none)"
```

---

### Task 4: `save`

**Files:**
- Modify: `viz/example_store.py`
- Test: `tests/test_example_store.py`

**Interfaces:**
- Consumes: `_embed`, `_load`, `_write`, `_derive_keywords`, `ExampleRecord` (Tasks 1-2).
- Produces: `save(concept: str, context: str, script: str, store_dir: str) -> None`. Task 5 calls `save` by this exact name and signature.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_example_store.py`:

```python
from viz.example_store import save


class TestSave(unittest.TestCase):
    @patch("viz.example_store._embed", return_value=[0.1, 0.2, 0.3])
    def test_appends_new_record(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            save("eigenvalues", "some context", "fig = go.Figure()", store_dir)
            records = _load(store_dir)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].concept, "eigenvalues")
            self.assertEqual(records[0].context, "some context")
            self.assertEqual(records[0].script, "fig = go.Figure()")
            self.assertEqual(records[0].embedding, [0.1, 0.2, 0.3])
            self.assertIn("eigenvalues", records[0].keywords)

    @patch("viz.example_store._embed", return_value=[0.1, 0.2, 0.3])
    def test_appends_to_existing_records(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            save("eigenvalues", "", "fig = go.Figure()", store_dir)
            save("gradient descent", "", "fig = go.Figure()", store_dir)
            records = _load(store_dir)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[1].concept, "gradient descent")

    @patch("viz.example_store._embed", return_value=None)
    def test_does_not_save_when_embedding_unavailable(self, mock_embed):
        with tempfile.TemporaryDirectory() as store_dir:
            save("eigenvalues", "", "fig = go.Figure()", store_dir)
            self.assertEqual(_load(store_dir), [])

    def test_never_raises_on_unexpected_error(self):
        with tempfile.TemporaryDirectory() as store_dir:
            with patch("viz.example_store._embed", side_effect=RuntimeError("boom")):
                save("eigenvalues", "", "fig = go.Figure()", store_dir)  # must not raise
            self.assertEqual(_load(store_dir), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: `ImportError: cannot import name 'save' from 'viz.example_store'`

- [ ] **Step 3: Write minimal implementation**

Add to `viz/example_store.py` (add `from datetime import datetime, timezone` to the imports):

```python
from datetime import datetime, timezone


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_example_store -v`
Expected: all `TestSave` tests PASS (plus every earlier test in the file still passing — run the full file, not just this class).

- [ ] **Step 5: Commit**

```bash
git add viz/example_store.py tests/test_example_store.py
git commit -m "feat(viz): add save() to persist validated examples"
```

---

### Task 5: Wire the example store into `llm_fallback.py`

**Files:**
- Modify: `viz/llm_fallback.py`
- Modify: `tests/test_llm_fallback.py`

**Interfaces:**
- Consumes: `viz.example_store.find_examples(concept, context, store_dir) -> list[ExampleRecord]`, `viz.example_store.save(concept, context, script, store_dir) -> None`, `viz.example_store.ExampleRecord` (Tasks 2-4).
- Produces: `_build_prompt(concept, context, previous_code=None, previous_error=None, examples=None) -> str` (new `examples` param), `generate_via_llm(concept, context, output_path, cache_dir, examples_dir) -> VizResult | None` (new `examples_dir` param, 5th positional argument). Task 6 calls `generate_via_llm` with this exact 5-argument signature.

- [ ] **Step 1: Write the failing tests**

In `tests/test_llm_fallback.py`, add to the import block at the top:

```python
from viz.example_store import ExampleRecord
```

Add these test methods to `TestBuildPrompt`:

```python
    def test_examples_block_included_when_examples_given(self):
        example = ExampleRecord(
            concept="spectral decomposition", context="", keywords=["spectral"],
            embedding=[0.1], script="fig = go.Figure()  # prior success",
            created_at="2026-09-03T00:00:00+00:00",
        )
        prompt = _build_prompt("eigenvalues", "", examples=[example])
        self.assertIn("fig = go.Figure()  # prior success", prompt)
        self.assertIn("spectral decomposition", prompt)
        self.assertIn("successfully", prompt)

    def test_examples_block_absent_when_examples_none(self):
        prompt = _build_prompt("eigenvalues", "", examples=None)
        self.assertNotIn("generated successfully", prompt)

    def test_examples_block_absent_when_examples_empty_list(self):
        prompt = _build_prompt("eigenvalues", "", examples=[])
        self.assertNotIn("generated successfully", prompt)
```

Replace every existing call to `generate_via_llm(...)` in `TestGenerateViaLlm` to add a 5th `examples_dir` argument, and mock `viz.llm_fallback.example_store.find_examples`/`.save` in every test (so no real network call happens). Replace the entire `TestGenerateViaLlm` class with:

```python
class TestGenerateViaLlm(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value=None) as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying (spec §4)

    def test_returns_none_when_no_code_block_extracted_after_exhausting_all_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="no code here") as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, MAX_GENERATION_ATTEMPTS)

    def test_retries_after_ollama_timeout_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch(
                    "viz.llm_fallback._call_ollama",
                    side_effect=[_OLLAMA_TIMEOUT, "```python\nfig = go.Figure()\n```"],
                 ) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertEqual(mock_call.call_count, 2)
            second_prompt = mock_call.call_args_list[1].args[0]
            self.assertIn("timed out", second_prompt)

    def test_returns_none_when_ollama_times_out_on_every_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value=_OLLAMA_TIMEOUT) as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, MAX_GENERATION_ATTEMPTS)

    def test_success_copies_cached_file_to_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "course", "concept.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="```python\nfig = go.Figure()\n```"), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))

    def test_cache_hit_skips_ollama_call_and_example_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            os.makedirs(cache_dir)
            key = _cache_key("concept", "")
            with open(os.path.join(cache_dir, f"{key}.html"), "w", encoding="utf-8") as f:
                f.write("<html>cached</html>")
            output_path = os.path.join(tmp, "out.html")

            with patch("viz.llm_fallback.example_store.find_examples") as mock_find, \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama") as mock_call:
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            mock_call.assert_not_called()
            mock_find.assert_not_called()
            mock_save.assert_not_called()
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))

    def test_recovers_after_one_failed_attempt_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",  # attempt 1: bad property
                "```python\nfig = go.Figure()\n```",                        # attempt 2: fixed
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertEqual(mock_call.call_count, 2)
            second_prompt = mock_call.call_args_list[1].args[0]
            self.assertIn("Bad property path", second_prompt)
            self.assertIn("bold=True", second_prompt)

    def test_only_the_successful_attempt_is_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    self.assertFalse(os.path.exists(path))  # nothing cached from the failed attempt
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            cache_key = _cache_key("concept", "")
            cached_path = os.path.join(cache_dir, f"{cache_key}.html")
            self.assertTrue(os.path.exists(cached_path))
            with open(cached_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "<html>fake</html>")

    def test_examples_are_injected_into_the_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            example = ExampleRecord(
                concept="spectral decomposition", context="", keywords=["spectral"],
                embedding=[0.1], script="fig = go.Figure()  # prior success",
                created_at="2026-09-03T00:00:00+00:00",
            )

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[example]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="```python\nfig = go.Figure()\n```") as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            prompt = mock_call.call_args_list[0].args[0]
            self.assertIn("fig = go.Figure()  # prior success", prompt)

    def test_find_examples_called_once_across_multiple_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]) as mock_find, \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertEqual(mock_find.call_count, 1)

    def test_save_called_once_with_final_successful_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            mock_save.assert_called_once_with("concept", "", "fig = go.Figure()", examples_dir)

    def test_save_not_called_when_every_attempt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama", return_value="no code here"):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_llm_fallback -v`
Expected: `TypeError: _build_prompt() got an unexpected keyword argument 'examples'` (and, once that's temporarily worked around, `TypeError: generate_via_llm() missing 1 required positional argument: 'examples_dir'`) — confirms the tests exercise the not-yet-added parameters.

- [ ] **Step 3: Write minimal implementation**

In `viz/llm_fallback.py`, add the import (below the existing `from viz.viz_agent import VizResult` line):

```python
from viz import example_store
from viz.example_store import ExampleRecord
```

Replace the `_PROMPT_TEMPLATE` constant with:

```python
_PROMPT_TEMPLATE = """Write a single self-contained Python script that uses the `plotly` and \
`numpy` libraries to create an interactive visualization illustrating this concept: {concept}

{context_block}
{examples_block}
Requirements:
- Assign the finished figure to a variable named exactly `fig` (a plotly.graph_objects.Figure).
- Do not call fig.show(), fig.write_html(), or write any file yourself -- the caller handles that.
- Do not import anything other than plotly (as go or px) and numpy.
- Prefer simple, well-documented trace types: go.Scatter, go.Bar, go.Contour, go.Surface. Stick to
  basic layout options: fig.update_layout(title=...), axis labels via xaxis_title/yaxis_title.
- Do NOT use speculative or exotic Plotly properties you are not certain exist (e.g. text styling
  properties like "bold", or a "z" property on a trace type that does not support one). If unsure
  whether a property exists, leave it out rather than guessing.
- Respond with ONLY one fenced ```python code block, nothing else.
"""
```

Add this new function above `_build_prompt`:

```python
def _build_examples_block(examples: list[ExampleRecord] | None) -> str:
    if not examples:
        return ""
    parts = [
        "Here are examples of visualizations you generated successfully for related "
        "concepts -- follow similar patterns (trace types, layout options) where they "
        "fit this new concept:\n"
    ]
    for i, example in enumerate(examples, start=1):
        parts.append(f'Example {i} (concept: "{example.concept}"):\n```python\n{example.script}\n```\n')
    return "\n".join(parts) + "\n"
```

Replace `_build_prompt`'s signature and its first two lines:

```python
def _build_prompt(
    concept: str, context: str,
    previous_code: str | None = None, previous_error: str | None = None,
    examples: list[ExampleRecord] | None = None,
) -> str:
    """Composes the prompt sent to Ollama. First attempt (previous_error
    is None): the base concept+context+examples prompt. Retry attempt
    (previous_error set): the same base prompt plus the previous
    attempt's code (if any -- omitted when extraction itself failed,
    since there's no code to show) and the exact error it produced,
    asking for a corrected script (spec:
    docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md
    §3). `examples`, when given, are past successful generations for a
    similar concept (spec:
    docs/superpowers/specs/2026-09-03-viz-example-store-design.md §5) --
    included on every attempt of a call, not just the first."""
    context_block = f"Background from the student's own course materials:\n{context}\n" if context else ""
    examples_block = _build_examples_block(examples)
    base = _PROMPT_TEMPLATE.format(concept=concept, context_block=context_block, examples_block=examples_block)
    if previous_error is None:
        return base
```

(The rest of `_build_prompt`, from `previous_code_block = (...)` onward, is unchanged.)

Replace `generate_via_llm`:

```python
def generate_via_llm(concept: str, context: str, output_path: str, cache_dir: str, examples_dir: str) -> VizResult | None:
    """Generates a visualization via the local Ollama fallback, retrying
    up to MAX_GENERATION_ATTEMPTS times with the previous failure fed
    back to the model as a corrective prompt, or returns None on any
    failure -- never raises past its caller (spec §4, hardened per
    docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md
    §2/§4). Looks up past successful examples once per call (not once per
    attempt) via example_store.find_examples(), and saves the final
    successful attempt's code via example_store.save() (spec:
    docs/superpowers/specs/2026-09-03-viz-example-store-design.md §5) --
    both of those calls are skipped entirely on a cache hit, since no
    Ollama call happens in that case either."""
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cached_path = os.path.join(cache_dir, f"{_cache_key(concept, context)}.html")

        if not os.path.exists(cached_path):
            examples = example_store.find_examples(concept, context, examples_dir)
            previous_code, previous_error = None, None
            succeeded = False
            final_code = None
            for _ in range(MAX_GENERATION_ATTEMPTS):
                prompt = _build_prompt(concept, context, previous_code, previous_error, examples)
                response_text = _call_ollama(prompt)
                if response_text is None:
                    return None  # Ollama unreachable -- not worth retrying (spec §4)
                if response_text is _OLLAMA_TIMEOUT:
                    # A live-but-slow Ollama call is plausibly worth a retry, unlike a
                    # genuinely unreachable server -- see _OllamaTimeout's own docstring.
                    previous_code, previous_error = None, (
                        f"the request to Ollama itself timed out after "
                        f"{OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- the model may just be slow; "
                        f"try to respond more concisely"
                    )
                    continue
                code = _extract_code(response_text)
                if code is None:
                    previous_code, previous_error = None, "the response contained no ```python code block"
                    continue
                success, error = _run_generated_code(code, cached_path)
                if success:
                    succeeded = True
                    final_code = code
                    break
                previous_code, previous_error = code, error
            if not succeeded:
                return None
            example_store.save(concept, context, final_code, examples_dir)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copyfile(cached_path, output_path)
        return VizResult(html_path=output_path, title=concept, source="llm_fallback")
    except Exception as err:
        print(f"WARNING: LLM fallback failed unexpectedly ({err})")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_llm_fallback -v`
Expected: every test in the file PASSes, including the new `TestBuildPrompt` examples-block tests and the new/updated `TestGenerateViaLlm` tests.

Then run the full suite to confirm no regressions elsewhere:

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add viz/llm_fallback.py tests/test_llm_fallback.py
git commit -m "feat(viz): inject few-shot examples into Ollama prompt, save on success"
```

---

### Task 6: Wire up `viz_agent.py` and update documentation

**Files:**
- Modify: `viz/viz_agent.py:55-59`
- Modify: `viz/README.md`
- Modify: `viz/templates/__init__.py` (docstring only)

**Interfaces:**
- Consumes: `generate_via_llm(concept, context, output_path, cache_dir, examples_dir)` (Task 5's new 5-argument signature).
- Produces: nothing new — this task is the production call site + docs, no new testable behavior beyond what Tasks 1-5 already verify. Verified by re-running the full suite and a manual dry run (Step 4).

- [ ] **Step 1: Update the production call site**

In `viz/viz_agent.py`, replace the final two lines (currently):

```python
    from viz.llm_fallback import generate_via_llm  # function-scoped: keeps the Ollama/
    # subprocess-dependent module out of the import path for callers that only ever hit
    # the template path (e.g. plain-Q&A callers of answer_question() that never set
    # visualize=True at all -- see Task 9)
    return generate_via_llm(concept, context, output_path, os.path.join(viz_root, ".cache"))
```

with:

```python
    from viz.llm_fallback import generate_via_llm  # function-scoped: keeps the Ollama/
    # subprocess-dependent module out of the import path for callers that only ever hit
    # the template path (e.g. plain-Q&A callers of answer_question() that never set
    # visualize=True at all -- see Task 9)
    return generate_via_llm(
        concept, context, output_path,
        os.path.join(viz_root, ".cache"), os.path.join(viz_root, ".examples"),
    )
```

- [ ] **Step 2: Add a one-line trust-tier note to the templates registry docstring**

In `viz/templates/__init__.py`, in the module docstring, add one sentence after the existing description (the docstring currently ends `"...no separate registration step to remember."`) — append:

```
This is the VERIFIED tier (hand-written, human-reviewed); see
viz/example_store.py for the separate UNVERIFIED tier of auto-generated
examples, which never populates this registry.
```

- [ ] **Step 3: Update `viz/README.md`**

Replace the "Key files" list's `llm_fallback.py` bullet (the one ending `"...degrades to returning None with a printed warning if it isn't."`) by appending, after that sentence, a new bullet:

```markdown
- `example_store.py` — a local, free memory of past successful `llm_fallback.py`
  generations, used for few-shot prompting only (never rendered or matched
  directly). Before each Ollama call, looks up up to 2 past successes for a
  similar concept — via local embedding similarity (`nomic-embed-text`, high
  threshold) falling back to auto-derived-keyword overlap — and injects them
  into the prompt as worked examples. Every genuinely successful generation is
  appended to the store afterward. This is the **unverified** tier (only bar:
  "it ran without error") — deliberately kept separate from `templates/`'s
  **verified**, human-reviewed tier. Storage: a flat JSON file at
  `<root>/.viz/.examples/examples.json`, same gitignore posture as the cache.
  Requires a second local Ollama model (`ollama pull nomic-embed-text`),
  independent of the generation model.
```

- [ ] **Step 4: Run the full suite and a manual dry run**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests` (from `ai-sandbox/academic-rag-model/`)
Expected: all tests PASS.

Run (requires `ollama serve` running, `qwen2.5-coder:7b` and `nomic-embed-text` both pulled):

```powershell
.\.venv\Scripts\python.exe -c "from viz.viz_agent import generate_visualization; print(generate_visualization('a topic with no matching template', academic_hub_root='../academic-hub', course='math-camp'))"
```

Expected: a `VizResult(source='llm_fallback')` is printed, and `../academic-hub/.viz/.examples/examples.json` now contains one record. This is a manual real-environment check, not asserted in CI — same convention as the original spec's own real-corpus validation.

- [ ] **Step 5: Commit**

```bash
git add viz/viz_agent.py viz/templates/__init__.py viz/README.md
git commit -m "feat(viz): wire example store into the production call site, document it"
```
