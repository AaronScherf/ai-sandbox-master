# Source Indexer (Core: Cards, Reconciliation, Search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core source indexer — per-file index cards generated from `transcribe_notes.py`/`convert_textbook.py`, linked to their `.rag.md` once `describe_images.py` produces one, reconciled by content hash (not path), and searchable via a two-stage embedding-similarity CLI/function — so a query like "teach me about linear algebra" returns ranked, relevant files from `academic-hub`.

**Architecture:** A new torch/marker-free module `index_card.py` owns card generation, shard I/O, and `file_id`-based reconciliation (mirroring how `chapter_index.py` is already kept free of `convert_textbook.py`'s heavy imports so it stays independently testable). A new `index_search.py` owns two-stage search and the rebuild/backfill pass (notes unconditionally, textbooks once `source_pdf_path` is recorded), plus the CLI. All three existing pipelines (`transcribe_notes.py`, `convert_textbook.py`, `describe_images.py`) get a minimal hook calling into `index_card.py`, all using the same Developer-API-key client construction.

**Tech Stack:** Python 3.13, `google-genai` 2.9.0 (already installed), `numpy` 2.5.2 (already installed), stdlib `hashlib`/`json`/`unittest`. **No new dependencies** — tag mining (which needs `rapidfuzz`) is out of scope for this plan; see Plan 2.

**Spec:** `marker-conversion/docs/superpowers/specs/2026-08-27-source-indexer-design.md`

## Global Constraints

- Generation model: `gemini-3.1-flash-lite` — pure text-in/JSON-out (no vision), so this uses the project's existing cheap text tier (`_MODEL_TYPESET` in `transcribe_notes.py`), not `gemini-3.6-flash` (reserved elsewhere for vision tasks). Confirmed live it supports the same structured-JSON config below.
- Embedding model: `gemini-embedding-001`, `output_dimensionality=768` — confirmed live against the real API (spec §4). Stored per-card as `embedding_model: "gemini-embedding-001:768"`. Returned vectors are **not pre-normalized** — every cosine-similarity computation must normalize itself.
- Structured-JSON generation calls use `config={"response_mime_type": "application/json", "temperature": 0, "thinking_config": {"thinking_level": "minimal"}}` — the exact pattern already established in `extract_bibliographic_info_via_llm()` (`convert_textbook.py:654`), reused rather than reinvented.
- **Client construction: `gemini_utils.get_gemini_client()` (Developer API key) uniformly, for every indexing call in all three pipelines** (`transcribe_notes.py`, `convert_textbook.py`, `describe_images.py`) — matching what `describe_images.py` and `transcribe_notes.py` already use for their own existing calls today. `convert_textbook.py` separately keeps its own Vertex-backed client for its *existing*, unrelated bibliographic-extraction call (`extract_bibliographic_info_via_llm()`) — that choice was specific to not distributing a secret to the VM for that one call, and the indexing hook doesn't inherit it. This means `.env`/`GEMINI_API_KEY` needs to be reachable wherever `convert_textbook.py` runs — already true for `describe_images.py`, so not a new requirement, just extended to a second script; if unavailable, `get_gemini_client()` returns `None` and the existing failure-isolation around the indexing call degrades that to a warning, never blocking the actual conversion.
- `path`/`source_pdf_path`/`rag_md_path` on every card are relative to `academic-hub/`, never absolute.
- Tests use plain `unittest` (not pytest — not installed in this environment) and are run via `cd marker-conversion && python -m unittest tests.test_<module> -v` — confirmed working against this repo's existing tests.
- `convert_textbook.py` cannot be imported in this development environment (`import torch` / `import marker` both fail — confirmed). Task 9 (its hook) is therefore verified by careful code review of the diff, not by an executable test. `transcribe_notes.py` and `describe_images.py` have no such dependency (both confirmed to import cleanly here) and are fully unit-tested — Tasks 8 and 10 follow normal TDD.
- `rebuild` (Task 5) backfills the notes pipeline unconditionally, and the textbook pipeline conditionally — only for book folders whose `_metadata.json` already has `source_pdf_path` (written automatically by Task 9 for every new conversion; the 5 pre-existing books need it added by hand once, a plain relative-path string, not a hash — see Task 5's note).

---

## File Structure

- Create: `marker-conversion/index_card.py` — card schema, `file_id` computation, course derivation, shard I/O, card generation (LLM + embedding calls), `file_id`-based reconciliation, course-level rollup, `rag_md_path` linkage.
- Create: `marker-conversion/index_search.py` — two-stage search, rebuild/backfill (notes unconditionally, textbooks conditionally), CLI (`query`/`rebuild` subcommands).
- Modify: `marker-conversion/transcribe_notes.py` — replace the 4 duplicated "write markdown file" blocks in `process_pdf()` with one shared helper that writes the file and then calls into `index_card.py`.
- Modify: `marker-conversion/convert_textbook.py` — write `source_pdf_path`/`source_pdf_file_id` into `_metadata.json` unconditionally, then one hook call in `process_one_pdf()`, immediately after.
- Modify: `marker-conversion/describe_images.py` — a new `link_rag_md()` helper, called once from `process_book()` immediately after `.rag.md` is written, linking it back to its card and `_metadata.json`.
- Create: `marker-conversion/tests/test_index_card.py`
- Create: `marker-conversion/tests/test_index_search.py`
- Modify: `marker-conversion/tests/test_transcribe_notes.py` — add coverage for the new shared write-and-index helper.
- Modify: `marker-conversion/tests/test_describe_images.py` — add coverage for `link_rag_md()`.

---

### Task 1: `file_id`, course derivation, and shard I/O primitives

**Files:**
- Create: `marker-conversion/index_card.py`
- Test: `marker-conversion/tests/test_index_card.py`

**Interfaces:**
- Produces: `compute_file_id(pdf_path: str) -> str`, `derive_course(relative_path: str) -> str`, `shard_path(academic_hub_root: str, course: str) -> str`, `courses_path(academic_hub_root: str) -> str`, `load_shard(academic_hub_root: str, course: str) -> list[dict]`, `save_shard(academic_hub_root: str, course: str, cards: list[dict]) -> None`, `load_courses(academic_hub_root: str) -> dict[str, dict]`, `save_courses(academic_hub_root: str, courses: dict[str, dict]) -> None`, `cosine_similarity(a: list[float], b: list[float]) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
# marker-conversion/tests/test_index_card.py
import os
import tempfile
import unittest

from index_card import (
    compute_file_id,
    derive_course,
    load_courses,
    load_shard,
    save_courses,
    save_shard,
    cosine_similarity,
)


class TestComputeFileId(unittest.TestCase):
    def test_same_bytes_produce_same_id_regardless_of_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "nested", "b.pdf")
            os.makedirs(os.path.dirname(b))
            for p in (a, b):
                with open(p, "wb") as f:
                    f.write(b"%PDF-1.4 fake content for hashing")
            self.assertEqual(compute_file_id(a), compute_file_id(b))

    def test_different_bytes_produce_different_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            with open(a, "wb") as f:
                f.write(b"content one")
            with open(b, "wb") as f:
                f.write(b"content two")
            self.assertNotEqual(compute_file_id(a), compute_file_id(b))

    def test_id_is_a_short_hex_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.pdf")
            with open(p, "wb") as f:
                f.write(b"x")
            file_id = compute_file_id(p)
            self.assertEqual(len(file_id), 16)
            int(file_id, 16)  # raises ValueError if not valid hex


class TestDeriveCourse(unittest.TestCase):
    def test_notes_path(self):
        self.assertEqual(
            derive_course("academic_notes/math-camp/ta_notes/foo.pdf"), "math-camp"
        )

    def test_resources_path(self):
        self.assertEqual(
            derive_course("academic_resources/econ-101/textbooks-and-papers/bar.pdf"),
            "econ-101",
        )

    def test_handles_backslashes(self):
        self.assertEqual(
            derive_course(r"academic_notes\math-camp\handwritten_notes\x.pdf"), "math-camp"
        )

    def test_raises_on_too_short_path(self):
        with self.assertRaises(ValueError):
            derive_course("just_a_file.pdf")


class TestShardIO(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [{"file_id": "abc", "path": "x.md"}]
            save_shard(tmp, "math-camp", cards)
            self.assertEqual(load_shard(tmp, "math-camp"), cards)

    def test_load_missing_courses_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_courses(tmp), {})

    def test_save_then_load_courses_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            courses = {"math-camp": {"course": "math-camp", "file_count": 1}}
            save_courses(tmp, courses)
            self.assertEqual(load_courses(tmp), courses)


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, places=6)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, places=6)

    def test_not_sensitive_to_magnitude(self):
        # Confirmed live against the real API that gemini-embedding-001
        # does NOT return unit-normalized vectors -- this is the case that
        # would silently break if cosine_similarity assumed unit length.
        a = [1.0, 1.0]
        b = [50.0, 50.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0, places=6)

    def test_empty_vector_scores_zero_not_a_crash(self):
        self.assertEqual(cosine_similarity([], [1.0, 2.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'index_card'`

- [ ] **Step 3: Write the implementation**

```python
# marker-conversion/index_card.py
"""
index_card.py
Per-file index card generation, file_id-based reconciliation, and shard
I/O for the academic-hub source indexer. Deliberately has no dependency
on marker/torch/surya (like chapter_index.py) so it stays testable off
the GCP VM -- convert_textbook.py imports those at module scope, which
requires CUDA to even succeed.

Spec: docs/superpowers/specs/2026-08-27-source-indexer-design.md
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONALITY = 768
EMBEDDING_MODEL_ID = f"{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONALITY}"
GENERATION_MODEL = "gemini-3.1-flash-lite"

KNOWN_DOC_TYPES = {"textbook", "problem_set", "exam", "ta_notes", "handwritten_notes"}
KNOWN_LEVELS = ("introductory", "intermediate", "advanced")

# Cap on how much of an assembled textbook markdown gets read as
# content_sample -- a book's front matter/TOC is reliably near the start
# regardless of the book's total length (spec §4), and this same constant
# is reused by both the live convert_textbook.py hook (Task 9) and
# rebuild's textbook-backfill path (Task 5) so they stay consistent.
TEXTBOOK_CONTENT_SAMPLE_CHARS = 12000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_file_id(pdf_path: str) -> str:
    """Truncated SHA-256 of the PDF's own bytes -- a card's true identity,
    independent of where the file currently lives (spec §3.1/§4.3)."""
    with open(pdf_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return digest[:16]


def derive_course(relative_path: str) -> str:
    """The course segment of a path relative to academic-hub/, e.g.
    'academic_notes/math-camp/ta_notes/foo.pdf' -> 'math-camp'. Distinct
    from folder_category (the immediate parent folder, e.g. 'ta_notes') --
    course is one segment further up."""
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        raise ValueError(f"cannot derive course from path: {relative_path!r}")
    return parts[1]


def _index_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index")


def shard_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), f"{course}.json")


def courses_path(academic_hub_root: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), "courses.json")


def load_shard(academic_hub_root: str, course: str) -> list[dict]:
    path = shard_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_shard(academic_hub_root: str, course: str, cards: list[dict]) -> None:
    path = shard_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)


def load_courses(academic_hub_root: str) -> dict[str, dict]:
    path = courses_path(academic_hub_root)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return {entry["course"]: entry for entry in entries}


def save_courses(academic_hub_root: str, courses: dict[str, dict]) -> None:
    path = courses_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(courses.values()), f, indent=2, ensure_ascii=False)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Gemini's embedding API does not return unit-normalized vectors
    (confirmed live: a real call returned L2 norm ~0.59, not 1.0) --
    this always normalizes itself rather than assuming unit length."""
    if not a or not b:
        return 0.0
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    denom = float(np.linalg.norm(arr_a) * np.linalg.norm(arr_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / denom)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(indexer): add file_id, course derivation, and shard I/O primitives"
```

---

### Task 2: Card generation (`generate_index_card`, `make_failure_card`)

**Files:**
- Modify: `marker-conversion/index_card.py`
- Test: `marker-conversion/tests/test_index_card.py`

**Interfaces:**
- Consumes: `EMBEDDING_MODEL`, `EMBEDDING_MODEL_ID`, `GENERATION_MODEL`, `KNOWN_DOC_TYPES`, `KNOWN_LEVELS`, `now_iso()` (Task 1).
- Produces: `generate_index_card(file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str, content_sample: str, page_count: int, client) -> dict`, `make_failure_card(file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str) -> dict`. Both later consumed by Task 4's `reconcile_and_write`.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_card.py
from unittest.mock import MagicMock

from index_card import generate_index_card, make_failure_card


def _fake_client(doc_type="textbook", has_solutions=False, level="introductory"):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "Linear Algebra Done Right", "doc_type": "%s", '
        '"summary": "Covers vector spaces and eigenvalues.", '
        '"level": "%s", "has_solutions": %s}'
        % (doc_type, level, str(has_solutions).lower())
    )
    client.models.generate_content.return_value = gen_response

    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2, 0.3]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestGenerateIndexCard(unittest.TestCase):
    def test_builds_a_complete_card_from_llm_and_embedding_responses(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="abc123",
            path="academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler/Axler.md",
            source_pdf_path="academic_resources/math-camp/textbooks-and-papers/Axler.pdf",
            course="math-camp",
            folder_category="textbooks-and-papers",
            content_sample="Chapter 1: Vector Spaces...",
            page_count=404,
            client=client,
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["title"], "Linear Algebra Done Right")
        self.assertEqual(card["doc_type"], "textbook")
        self.assertEqual(card["summary"], "Covers vector spaces and eigenvalues.")
        self.assertEqual(card["level"], "introductory")
        self.assertFalse(card["has_solutions"])
        self.assertEqual(card["page_count"], 404)
        self.assertEqual(card["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(card["embedding_model"], "gemini-embedding-001:768")
        self.assertEqual(card["topics"], [])
        self.assertFalse(card["needs_indexing"])
        self.assertNotIn("orphaned", card)

    def test_falls_back_to_folder_category_when_llm_doc_type_is_unrecognized(self):
        client = _fake_client(doc_type="something_weird")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["doc_type"], "ta_notes")

    def test_falls_back_to_introductory_when_llm_level_is_unrecognized(self):
        client = _fake_client(level="expert-plus")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["level"], "introductory")

    def test_embeds_title_and_summary_not_raw_content(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="a" * 50000, page_count=10, client=client,
        )
        embed_call = client.models.embed_content.call_args
        self.assertIn("Linear Algebra Done Right", embed_call.kwargs["contents"])
        self.assertIn("Covers vector spaces", embed_call.kwargs["contents"])
        self.assertNotIn("a" * 50000, embed_call.kwargs["contents"])

    def test_prompt_mentions_folder_category_as_a_hint_not_a_verdict(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="problem_sets", content_sample="text", page_count=10, client=client,
        )
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("problem_sets", prompt)


class TestMakeFailureCard(unittest.TestCase):
    def test_minimal_card_carries_enough_to_be_reconciled_later(self):
        card = make_failure_card(
            file_id="abc123", path="p.md", source_pdf_path="p.pdf",
            course="math-camp", folder_category="ta_notes",
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["path"], "p.md")
        self.assertEqual(card["source_pdf_path"], "p.pdf")
        self.assertEqual(card["course"], "math-camp")
        self.assertEqual(card["doc_type"], "ta_notes")
        self.assertTrue(card["needs_indexing"])
        self.assertEqual(card["embedding"], [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: FAIL — `ImportError: cannot import name 'generate_index_card'`

- [ ] **Step 3: Write the implementation**

```python
# append to marker-conversion/index_card.py
# (flat same-directory import, matching every other module in this
# project -- e.g. transcribe_notes.py's `from gemini_utils import ...` --
# no sys.path manipulation needed since scripts/tests both run with
# marker-conversion/ as the working directory)
from gemini_utils import call_with_retries

from google.genai import types


_PROMPT_TEMPLATE = """You are cataloging one document from a personal study corpus for a search index.

The document's containing folder is categorized as '{folder_category}', but classify based on \
the actual content below, not the folder name alone -- e.g. a file that is actually an exam \
should be classified "exam" even if it lives in a folder named for practice problem sets.

Respond with ONLY a JSON object with exactly these keys:
"title" (string, the document's own title or a short descriptive name),
"doc_type" (one of: "textbook", "problem_set", "exam", "ta_notes", "handwritten_notes"),
"summary" (2-3 sentences describing what this document covers),
"level" (one of: "introductory", "intermediate", "advanced"),
"has_solutions" (boolean -- true only if THIS document itself shows worked solutions/answers, \
not just problem statements).

--- DOCUMENT START ---
{content_sample}
--- DOCUMENT END ---"""


def generate_index_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str, page_count: int, client,
) -> dict:
    """One structured-JSON generation call plus one embedding call. Never
    proposes `topics` -- that's the corpus-wide retag pass's job (spec §5),
    kept deliberately out of scope for a single-document call."""
    prompt = _PROMPT_TEMPLATE.format(folder_category=folder_category, content_sample=content_sample)
    response = call_with_retries(lambda: client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0,
            "thinking_config": {"thinking_level": "minimal"},
        },
    ))
    parsed = json.loads(response.text)

    title = str(parsed.get("title") or "").strip()
    doc_type = parsed.get("doc_type")
    if doc_type not in KNOWN_DOC_TYPES:
        doc_type = folder_category
    summary = str(parsed.get("summary") or "").strip()
    level = parsed.get("level")
    if level not in KNOWN_LEVELS:
        level = "introductory"
    has_solutions = bool(parsed.get("has_solutions", False))

    embed_response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{title}\n\n{summary}",
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    embedding = list(embed_response.embeddings[0].values)

    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "course": course,
        "doc_type": doc_type,
        "title": title,
        "summary": summary,
        "topics": [],
        "level": level,
        "has_solutions": has_solutions,
        "page_count": page_count,
        "rag_md_path": None,
        "embedding": embedding,
        "embedding_model": EMBEDDING_MODEL_ID,
        "source_updated_at": now_iso(),
        "needs_indexing": False,
    }


def make_failure_card(file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str) -> dict:
    """Written when generate_index_card() raises -- keeps file_id/path so
    §4.3 reconciliation can find and complete this exact card on a later
    rebuild, rather than mistaking it for a new file each time."""
    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "course": course,
        "doc_type": folder_category,
        "title": "",
        "summary": "",
        "topics": [],
        "level": None,
        "has_solutions": None,
        "page_count": None,
        "rag_md_path": None,
        "embedding": [],
        "embedding_model": None,
        "source_updated_at": now_iso(),
        "needs_indexing": True,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (18 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(indexer): add per-file card generation and failure-isolation card"
```

---

### Task 3: Course-level rollup (`recompute_course_entry`)

**Files:**
- Modify: `marker-conversion/index_card.py`
- Test: `marker-conversion/tests/test_index_card.py`

**Interfaces:**
- Consumes: `load_shard`, `load_courses`, `save_courses`, `cosine_similarity`'s sibling numeric helpers (Task 1); card shape from Task 2.
- Produces: `recompute_course_entry(academic_hub_root: str, course: str) -> None`. Later called by Task 4 (`reconcile_and_write`) after every card write/move.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_card.py
from index_card import recompute_course_entry


class TestRecomputeCourseEntry(unittest.TestCase):
    def test_computes_centroid_and_file_count_from_shard_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "topics": ["linear-algebra"]},
                {"file_id": "b", "embedding": [0.0, 1.0], "topics": ["linear-algebra", "real-analysis"]},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 2)
            self.assertEqual(courses["math-camp"]["embedding"], [0.5, 0.5])
            self.assertIn("linear-algebra", courses["math-camp"]["predominant_topics"])

    def test_title_is_a_readable_form_of_the_course_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "topics": []}])
            recompute_course_entry(tmp, "math-camp")
            self.assertEqual(load_courses(tmp)["math-camp"]["title"], "Math Camp")

    def test_excludes_orphaned_cards_from_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "topics": [], "orphaned": True},
                {"file_id": "b", "embedding": [0.0, 1.0], "topics": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 1)
            self.assertEqual(courses["math-camp"]["embedding"], [0.0, 1.0])

    def test_removes_course_entry_when_shard_becomes_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "topics": []}])
            recompute_course_entry(tmp, "math-camp")
            save_shard(tmp, "math-camp", [])
            recompute_course_entry(tmp, "math-camp")
            self.assertNotIn("math-camp", load_courses(tmp))

    def test_cards_missing_topics_are_missing_from_the_embedding_but_not_a_crash(self):
        # needs_indexing cards (Task 2) have embedding: [] -- must not
        # poison the centroid computation.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [], "topics": [], "needs_indexing": True},
                {"file_id": "b", "embedding": [1.0, 0.0], "topics": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["embedding"], [1.0, 0.0])
            self.assertEqual(courses["math-camp"]["file_count"], 2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: FAIL — `ImportError: cannot import name 'recompute_course_entry'`

- [ ] **Step 3: Write the implementation**

```python
# append to marker-conversion/index_card.py
from collections import Counter  # place with other stdlib imports at top


def recompute_course_entry(academic_hub_root: str, course: str) -> None:
    """Free byproduct of writing any card in this course -- no LLM or
    embedding call (spec §3.2). Excludes orphaned and not-yet-embedded
    (needs_indexing) cards from the centroid so a failed/pending card
    can't skew course-level ranking."""
    cards = [c for c in load_shard(academic_hub_root, course) if not c.get("orphaned")]
    courses = load_courses(academic_hub_root)

    if not cards:
        courses.pop(course, None)
        save_courses(academic_hub_root, courses)
        return

    embeddings = [c["embedding"] for c in cards if c.get("embedding")]
    centroid = np.array(embeddings, dtype=float).mean(axis=0).tolist() if embeddings else []

    topic_counts: Counter[str] = Counter()
    for c in cards:
        topic_counts.update(c.get("topics") or [])
    predominant = [topic for topic, _ in topic_counts.most_common(10)]

    courses[course] = {
        "course": course,
        "title": course.replace("-", " ").title(),
        "predominant_topics": predominant,
        "file_count": len(cards),
        "embedding": centroid,
    }
    save_courses(academic_hub_root, courses)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (23 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(indexer): add free course-level centroid/topic rollup"
```

---

### Task 4: `file_id` reconciliation (`find_card_by_file_id`, `reconcile_and_write`)

**Files:**
- Modify: `marker-conversion/index_card.py`
- Test: `marker-conversion/tests/test_index_card.py`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: `find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None`, `reconcile_and_write(academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str, content_sample: str, page_count: int, client) -> dict`, `set_rag_md_path(academic_hub_root: str, file_id: str, rag_md_path: str) -> bool`. `reconcile_and_write` is the **single function both pipeline hooks call** (Tasks 8 and 9) and the one Task 5 (rebuild) calls per file; `set_rag_md_path` is the one Task 10 (`describe_images.py`'s hook) calls.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_card.py
from index_card import find_card_by_file_id, reconcile_and_write


class TestFindCardByFileId(unittest.TestCase):
    def test_finds_across_shards_not_just_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "x", "path": "a.md"}])
            save_shard(tmp, "econ-101", [{"file_id": "y", "path": "b.md"}])
            found = find_card_by_file_id(tmp, "y")
            self.assertEqual(found[0], "econ-101")
            self.assertEqual(found[1]["path"], "b.md")

    def test_returns_none_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "x", "path": "a.md"}])
            self.assertIsNone(find_card_by_file_id(tmp, "nope"))

    def test_returns_none_when_index_dir_does_not_exist_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_card_by_file_id(tmp, "x"))

    def test_ignores_courses_json_and_topics_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_courses(tmp, {"math-camp": {"course": "math-camp", "file_count": 0}})
            self.assertIsNone(find_card_by_file_id(tmp, "math-camp"))


class TestReconcileAndWrite(unittest.TestCase):
    def _card_kwargs(self, **overrides):
        kwargs = dict(
            file_id="fid1", path="a.md", source_pdf_path="a.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=5, client=_fake_client(),
        )
        kwargs.update(overrides)
        return kwargs

    def test_no_match_generates_a_fresh_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = reconcile_and_write(tmp, **self._card_kwargs())
            self.assertEqual(card["file_id"], "fid1")
            self.assertFalse(card["needs_indexing"])
            self.assertEqual(load_shard(tmp, "math-camp")[0]["file_id"], "fid1")
            self.assertEqual(load_courses(tmp)["math-camp"]["file_count"], 1)

    def test_generation_failure_writes_a_minimal_card_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_client = MagicMock()
            bad_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
            card = reconcile_and_write(tmp, **self._card_kwargs(client=bad_client))
            self.assertTrue(card["needs_indexing"])
            self.assertEqual(load_shard(tmp, "math-camp")[0]["file_id"], "fid1")

    def test_match_same_course_unchanged_path_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcile_and_write(tmp, **self._card_kwargs())
            before = load_shard(tmp, "math-camp")[0]
            reconcile_and_write(tmp, **self._card_kwargs())  # identical path/course
            after = load_shard(tmp, "math-camp")[0]
            self.assertEqual(before, after)  # no regeneration, no field churn

    def test_match_same_course_changed_path_updates_in_place_without_regenerating(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            self.assertEqual(client.models.generate_content.call_count, 1)
            reconcile_and_write(tmp, **self._card_kwargs(
                path="moved/a.md", source_pdf_path="moved/a.pdf", client=client,
            ))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still 1 -- no regen
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["path"], "moved/a.md")

    def test_match_different_course_moves_card_and_recomputes_both_rollups(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client, course="math-camp"))
            reconcile_and_write(tmp, **self._card_kwargs(
                client=client, course="econ-101", path="moved/a.md", source_pdf_path="moved/a.pdf",
            ))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            self.assertEqual(load_shard(tmp, "math-camp"), [])
            self.assertNotIn("math-camp", load_courses(tmp))
            moved_cards = load_shard(tmp, "econ-101")
            self.assertEqual(len(moved_cards), 1)
            self.assertEqual(moved_cards[0]["course"], "econ-101")
            self.assertEqual(load_courses(tmp)["econ-101"]["file_count"], 1)

    def test_reconciliation_clears_a_prior_orphaned_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            cards = load_shard(tmp, "math-camp")
            cards[0]["orphaned"] = True
            save_shard(tmp, "math-camp", cards)
            reconcile_and_write(tmp, **self._card_kwargs(client=client))
            self.assertNotIn("orphaned", load_shard(tmp, "math-camp")[0])


class TestSetRagMdPath(unittest.TestCase):
    def test_sets_rag_md_path_on_the_matching_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            reconcile_and_write(tmp, file_id="fid1", path="a.md", source_pdf_path="a.pdf",
                                 course="math-camp", folder_category="textbooks-and-papers",
                                 content_sample="text", page_count=10, client=_fake_client())
            found = set_rag_md_path(tmp, "fid1", "a.rag.md")
            self.assertTrue(found)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["rag_md_path"], "a.rag.md")

    def test_returns_false_and_writes_nothing_when_no_card_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = set_rag_md_path(tmp, "no-such-file-id", "a.rag.md")
            self.assertFalse(found)

    def test_works_on_a_needs_indexing_card_which_still_has_a_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_client = MagicMock()
            bad_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
            reconcile_and_write(tmp, file_id="fid1", path="a.md", source_pdf_path="a.pdf",
                                 course="math-camp", folder_category="textbooks-and-papers",
                                 content_sample="text", page_count=10, client=bad_client)
            found = set_rag_md_path(tmp, "fid1", "a.rag.md")
            self.assertTrue(found)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["rag_md_path"], "a.rag.md")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: FAIL — `ImportError: cannot import name 'find_card_by_file_id'`

- [ ] **Step 3: Write the implementation**

```python
# append to marker-conversion/index_card.py
def find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None:
    index_dir = _index_dir(academic_hub_root)
    if not os.path.isdir(index_dir):
        return None
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "topics.json"):
            continue
        course = name[:-len(".json")]
        for card in load_shard(academic_hub_root, course):
            if card.get("file_id") == file_id:
                return course, card
    return None


def _replace_card(cards: list[dict], file_id: str, updated: dict) -> list[dict]:
    return [updated if c.get("file_id") == file_id else c for c in cards]


def reconcile_and_write(
    academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str,
    folder_category: str, content_sample: str, page_count: int, client,
) -> dict:
    """The single entry point both pipeline hooks (and rebuild) call.
    Implements spec §4.3: never treats `path` as identity -- reconciles by
    `file_id` across every shard before ever generating anything new."""
    found = find_card_by_file_id(academic_hub_root, file_id)

    if found is not None:
        old_course, old_card = found
        changed = (
            old_card.get("path") != path
            or old_card.get("source_pdf_path") != source_pdf_path
            or old_card.get("orphaned")
        )
        updated = dict(old_card)
        updated["path"] = path
        updated["source_pdf_path"] = source_pdf_path
        updated["course"] = course
        updated.pop("orphaned", None)
        if changed:
            updated["source_updated_at"] = now_iso()

        if old_course == course:
            if changed:
                save_shard(academic_hub_root, course, _replace_card(
                    load_shard(academic_hub_root, course), file_id, updated,
                ))
                recompute_course_entry(academic_hub_root, course)
            return updated

        # Moved to a different course.
        remaining = [c for c in load_shard(academic_hub_root, old_course) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, old_course, remaining)
        new_course_cards = load_shard(academic_hub_root, course)
        new_course_cards.append(updated)
        save_shard(academic_hub_root, course, new_course_cards)
        recompute_course_entry(academic_hub_root, old_course)
        recompute_course_entry(academic_hub_root, course)
        return updated

    # No match anywhere -- genuinely new content (spec §4.3).
    try:
        card = generate_index_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path, course=course,
            folder_category=folder_category, content_sample=content_sample,
            page_count=page_count, client=client,
        )
    except Exception as err:
        print(f"WARNING: index card generation failed for {path} ({err}); writing needs_indexing card.")
        card = make_failure_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path,
            course=course, folder_category=folder_category,
        )

    cards = load_shard(academic_hub_root, course)
    cards.append(card)
    save_shard(academic_hub_root, course, cards)
    recompute_course_entry(academic_hub_root, course)
    return card


def set_rag_md_path(academic_hub_root: str, file_id: str, rag_md_path: str) -> bool:
    """Called by describe_images.py's hook (Task 10) once it produces
    .rag.md -- finds the existing card by file_id (reusing
    find_card_by_file_id rather than duplicating the shard scan) and sets
    rag_md_path on it, without touching anything else on the card (no
    regeneration). Returns False (never raises) if no card exists yet for
    this file_id -- the caller logs that as a warning, same failure-
    isolation philosophy as everywhere else in this module."""
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    course, card = found
    updated = dict(card)
    updated["rag_md_path"] = rag_md_path
    save_shard(academic_hub_root, course, _replace_card(
        load_shard(academic_hub_root, course), file_id, updated,
    ))
    return True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (33 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(indexer): add file_id reconciliation and rag_md_path linkage"
```

---

### Task 5: Rebuild / backfill pass (notes + textbook pipelines)

**Files:**
- Create: `marker-conversion/index_search.py`
- Test: `marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `compute_file_id`, `derive_course`, `reconcile_and_write`, `load_shard`, `save_shard`, `recompute_course_entry`, `TEXTBOOK_CONTENT_SAMPLE_CHARS` (Task 1-4).
- Produces: `rebuild(academic_hub_root: str, client, force: bool = False, prune: bool = False) -> dict` (returns a stats dict: `{"generated": int, "updated": int, "unchanged": int, "moved": int, "orphaned": int, "pruned": int, "skipped_no_source_pdf": int}`). Consumed by Task 7's CLI.

**Note on a smaller accuracy gap:** backfilled *notes* cards get `page_count=None`
rather than the real value, since `rebuild` doesn't parse the existing
YAML frontmatter's `total_pages` field back out of each `.md` file (no
parser for it exists yet, and the project's own `build_frontmatter()`
deliberately avoided adding PyYAML "for something this narrow" — writing
one just to extract a single integer felt like the same tradeoff). Cards
generated live by Task 8's hook are unaffected — they already receive the
real `total_pages` directly from `process_pdf()`. Worth a follow-up if
backfilled `page_count` accuracy matters in practice.

**Note on textbook backfill scope:** matching a notes PDF to its markdown
is deterministic by construction — `<category>/processed_outputs/<basename>.md`.
For textbooks it isn't — a `processed_outputs/<FolderName>/` folder's
name has no reliable relationship to the PDF filename that produced it
(e.g. `Book of Proof.pdf` → `Hammack_Book_of_Proof_2025/`). Task 9 now
writes `source_pdf_path` into every *new* textbook conversion's
`_metadata.json`, which `rebuild` reads back out to resolve this
unambiguously going forward. For the 5 textbooks converted before that
change, `_metadata.json` doesn't have it yet — `rebuild` skips such a
book folder (counted in `stats["skipped_no_source_pdf"]`, with a printed
message naming it) rather than guess via fuzzy filename matching, which
risked silently attaching a card to the wrong book. Since
`convert_textbook.py` checkpoints its work, simply **re-running it** on
those 5 PDFs is the cleanest fix — it resumes past the already-completed
marker/GPU extraction and just redoes the final assembly/metadata write,
picking up the new fields automatically; hand-editing `_metadata.json`
to add `source_pdf_path` (a plain relative-path string) is a fallback if
re-running isn't preferred.

- [ ] **Step 1: Write the failing tests**

```python
# marker-conversion/tests/test_index_search.py
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from index_card import load_courses, load_shard, save_shard
from index_search import rebuild


def _fake_client():
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "T", "doc_type": "ta_notes", "summary": "S.", '
        '"level": "introductory", "has_solutions": false}'
    )
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


def _make_notes_pdf(academic_hub_root, course, category, basename, write_markdown=True):
    pdf_dir = os.path.join(academic_hub_root, "academic_notes", course, category)
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{basename}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(f"fake pdf bytes for {basename}".encode())
    if write_markdown:
        out_dir = os.path.join(pdf_dir, "processed_outputs")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{basename}.md"), "w", encoding="utf-8") as f:
            f.write("---\ntotal_pages: 3\n---\n\nSome content.")
    return pdf_path


def _make_textbook(academic_hub_root, course, pdf_basename, folder_name, with_source_pdf_path=True):
    """Mirrors convert_textbook.py's real output layout: the PDF sits in
    textbooks-and-papers/ directly, its processed_outputs/<folder_name>/
    subfolder is NOT named after the PDF's filename (real corpus example:
    'Book of Proof.pdf' -> 'Hammack_Book_of_Proof_2025/'), and (once
    Task 9 lands) _metadata.json carries source_pdf_path back to it."""
    tp_dir = os.path.join(academic_hub_root, "academic_resources", course, "textbooks-and-papers")
    os.makedirs(tp_dir, exist_ok=True)
    pdf_path = os.path.join(tp_dir, f"{pdf_basename}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(f"fake pdf bytes for {pdf_basename}".encode())

    book_dir = os.path.join(tp_dir, "processed_outputs", folder_name)
    os.makedirs(book_dir, exist_ok=True)
    with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
        f.write("# Title\n\nChapter 1: Introduction...")

    metadata = {"total_pages_processed": 42}
    if with_source_pdf_path:
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
        metadata["source_pdf_path"] = rel_pdf_path
    with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f)
    return pdf_path


class TestRebuild(unittest.TestCase):
    def test_generates_cards_for_pdfs_with_a_markdown_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["doc_type"], "ta_notes")

    def test_skips_pdfs_with_no_markdown_output_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "not_converted_yet", write_markdown=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_second_run_with_no_changes_leaves_cards_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client=client)
            stats = rebuild(tmp, client=client)
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(client.models.generate_content.call_count, 1)  # not called again

    def test_force_regenerates_even_unchanged_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            client = _fake_client()
            rebuild(tmp, client=client)
            rebuild(tmp, client=client, force=True)
            self.assertEqual(client.models.generate_content.call_count, 2)

    def test_scoped_to_one_course_leaves_other_courses_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            _make_notes_pdf(tmp, "econ-101", "ta_notes", "Econ_Notes")
            stats = rebuild(tmp, client=_fake_client(), course="math-camp")
            self.assertEqual(stats["generated"], 1)
            self.assertEqual(load_shard(tmp, "econ-101"), [])

    def test_flags_orphaned_card_whose_pdf_disappeared(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            rebuild(tmp, client=_fake_client())
            os.remove(os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "LN_Analysis.pdf"))
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["orphaned"], 1)
            self.assertTrue(load_shard(tmp, "math-camp")[0]["orphaned"])

    def test_prune_removes_confirmed_orphans_and_rolls_back_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_notes_pdf(tmp, "math-camp", "ta_notes", "LN_Analysis")
            rebuild(tmp, client=_fake_client())
            os.remove(os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "LN_Analysis.pdf"))
            rebuild(tmp, client=_fake_client())  # flags orphan
            stats = rebuild(tmp, client=_fake_client(), prune=True)
            self.assertEqual(stats["pruned"], 1)
            self.assertEqual(load_shard(tmp, "math-camp"), [])
            self.assertNotIn("math-camp", load_courses(tmp))

    def test_generates_a_textbook_card_when_source_pdf_path_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025")
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len(cards), 1)
            self.assertTrue(cards[0]["path"].endswith("Hammack_Book_of_Proof_2025.md"))
            self.assertTrue(cards[0]["source_pdf_path"].endswith("Book of Proof.pdf"))

    def test_skips_textbook_with_no_source_pdf_path_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Book of Proof", "Hammack_Book_of_Proof_2025",
                            with_source_pdf_path=False)
            stats = rebuild(tmp, client=_fake_client())
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(stats["skipped_no_source_pdf"], 1)
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_textbook_content_sample_is_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_textbook(tmp, "math-camp", "Big Book", "BigBook_2025")
            md_path = os.path.join(tmp, "academic_resources", "math-camp", "textbooks-and-papers",
                                    "processed_outputs", "BigBook_2025", "BigBook_2025.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("x" * 50000)
            client = _fake_client()
            rebuild(tmp, client=client)
            from index_card import TEXTBOOK_CONTENT_SAMPLE_CHARS
            prompt = client.models.generate_content.call_args.kwargs["contents"]
            self.assertLessEqual(len(prompt), 50000)  # the 50000-char body did NOT go in whole
            self.assertIn("x" * TEXTBOOK_CONTENT_SAMPLE_CHARS, prompt)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'index_search'`

- [ ] **Step 3: Write the implementation**

```python
# marker-conversion/index_search.py
"""
index_search.py
Rebuild/backfill pass and (Task 6) two-stage search for the academic-hub
source indexer, plus (Task 7) its CLI.

Spec: docs/superpowers/specs/2026-08-27-source-indexer-design.md
"""
from __future__ import annotations

import json
import os

from index_card import (
    TEXTBOOK_CONTENT_SAMPLE_CHARS,
    compute_file_id,
    derive_course,
    load_shard,
    recompute_course_entry,
    reconcile_and_write,
    save_shard,
)


def _notes_pdf_paths(academic_hub_root: str, course_filter: str | None):
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            continue
        for category in sorted(os.listdir(course_dir)):
            category_dir = os.path.join(course_dir, category)
            if not os.path.isdir(category_dir):
                continue
            for name in sorted(os.listdir(category_dir)):
                if name.lower().endswith(".pdf"):
                    yield course, category, os.path.join(category_dir, name)


def _textbook_book_dirs(academic_hub_root: str, course_filter: str | None):
    resources_root = os.path.join(academic_hub_root, "academic_resources")
    if not os.path.isdir(resources_root):
        return
    for course in sorted(os.listdir(resources_root)):
        if course_filter and course != course_filter:
            continue
        processed_outputs_dir = os.path.join(
            resources_root, course, "textbooks-and-papers", "processed_outputs",
        )
        if not os.path.isdir(processed_outputs_dir):
            continue
        for folder_name in sorted(os.listdir(processed_outputs_dir)):
            book_dir = os.path.join(processed_outputs_dir, folder_name)
            if os.path.isdir(book_dir):
                yield course, folder_name, book_dir


def _reconcile_one(academic_hub_root, course_name, folder_category, file_id, rel_path,
                    rel_pdf_path, content_sample, page_count, client, force, stats):
    existing = None
    for c in load_shard(academic_hub_root, course_name):
        if c.get("file_id") == file_id:
            existing = c
            break
    already_current = (
        existing is not None and not force and not existing.get("needs_indexing")
        and existing.get("path") == rel_path
    )
    if already_current:
        stats["unchanged"] += 1
        return

    was_new = existing is None
    # force=True on an existing, otherwise-current card still needs a
    # fresh generate_index_card() call -- reconcile_and_write() only
    # regenerates on a true no-match, so force removes the old card
    # first to force that path.
    if force and existing is not None:
        remaining = [c for c in load_shard(academic_hub_root, course_name) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, course_name, remaining)
        recompute_course_entry(academic_hub_root, course_name)
        was_new = True

    reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_path, source_pdf_path=rel_pdf_path,
        course=course_name, folder_category=folder_category, content_sample=content_sample,
        page_count=page_count, client=client,
    )
    if was_new:
        stats["generated"] += 1
    elif existing is not None and existing.get("course") != course_name:
        stats["moved"] += 1
    else:
        stats["updated"] += 1


def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {
        "generated": 0, "updated": 0, "unchanged": 0, "moved": 0,
        "orphaned": 0, "pruned": 0, "skipped_no_source_pdf": 0,
    }
    seen_file_ids: set[str] = set()

    for course_name, category, pdf_path in _notes_pdf_paths(academic_hub_root, course):
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", f"{basename}.md")
        if not os.path.exists(md_path):
            continue  # not converted yet -- nothing to index

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_md_path,
                       rel_pdf_path, content_sample, None, client, force, stats)

    for course_name, folder_name, book_dir in _textbook_book_dirs(academic_hub_root, course):
        metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        source_pdf_path = metadata.get("source_pdf_path")
        if not source_pdf_path:
            print(f"WARNING: {folder_name} has no source_pdf_path in its _metadata.json yet "
                  f"(converted before this field existed) -- skipping. Re-run convert_textbook.py "
                  f"on its PDF, or add source_pdf_path by hand, then rerun rebuild.")
            stats["skipped_no_source_pdf"] += 1
            continue

        pdf_path = os.path.join(academic_hub_root, source_pdf_path)
        if not os.path.exists(pdf_path):
            print(f"WARNING: {folder_name}'s source_pdf_path ({source_pdf_path}) does not exist "
                  f"on disk -- skipping.")
            stats["skipped_no_source_pdf"] += 1
            continue

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)
        course_name = derive_course(source_pdf_path)  # trust the PDF's own path, not the folder walk

        md_path = os.path.join(book_dir, f"{folder_name}.md")
        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read(TEXTBOOK_CONTENT_SAMPLE_CHARS)

        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        page_count = metadata.get("total_pages_processed")

        _reconcile_one(academic_hub_root, course_name, "textbooks-and-papers", file_id, rel_md_path,
                       source_pdf_path, content_sample, page_count, client, force, stats)

    _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course, prune, stats)
    return stats


def _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course_filter, prune, stats):
    index_dir = os.path.join(academic_hub_root, ".index")
    if not os.path.isdir(index_dir):
        return
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "topics.json"):
            continue
        shard_course = name[:-len(".json")]
        if course_filter and shard_course != course_filter:
            continue
        cards = load_shard(academic_hub_root, shard_course)
        changed = False
        kept = []
        for card in cards:
            if card.get("file_id") in seen_file_ids:
                kept.append(card)
                continue
            if prune:
                stats["pruned"] += 1
                changed = True
                continue
            if not card.get("orphaned"):
                card["orphaned"] = True
                stats["orphaned"] += 1
                changed = True
            kept.append(card)
        if changed:
            save_shard(academic_hub_root, shard_course, kept)
            recompute_course_entry(academic_hub_root, shard_course)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_search.py marker-conversion/tests/test_index_search.py
git commit -m "feat(indexer): add notes+textbook rebuild/backfill with orphan flagging and prune"
```

---

### Task 6: Two-stage search

**Files:**
- Modify: `marker-conversion/index_search.py`
- Test: `marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `load_courses`, `load_shard`, `cosine_similarity`, `KNOWN_LEVELS` (Task 1/3).
- Produces: `SearchResult` (dataclass: `path: str`, `course: str`, `doc_type: str`, `score: float`, `reason: str`), `search(academic_hub_root: str, query: str, client, course: str | None = None, top_k: int = 5, doc_type: str | None = None, has_solutions: bool | None = None, max_level: str | None = None) -> list[SearchResult]`. Consumed by Task 7's CLI.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_search.py
from index_search import search


def _fake_query_client(query_embedding):
    client = MagicMock()
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = query_embedding
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


def _card(file_id, embedding, **overrides):
    card = {
        "file_id": file_id, "path": f"{file_id}.md", "source_pdf_path": f"{file_id}.pdf",
        "course": "math-camp", "doc_type": "textbook", "title": file_id,
        "summary": f"summary for {file_id}", "topics": [], "level": "introductory",
        "has_solutions": False, "page_count": 10, "rag_md_path": None, "embedding": embedding,
        "embedding_model": "gemini-embedding-001:768", "source_updated_at": "2026-01-01T00:00:00Z",
        "needs_indexing": False,
    }
    card.update(overrides)
    return card


class TestSearch(unittest.TestCase):
    def test_ranks_by_cosine_similarity_to_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("close", [1.0, 0.0]),
                _card("far", [0.0, 1.0]),
            ])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "linear algebra", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "close.md")
            self.assertGreater(results[0].score, results[1].score)

    def test_reason_is_the_cards_own_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].reason, "summary for x")

    def test_prefers_rag_md_path_over_path_when_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("x", [1.0, 0.0], rag_md_path="x.rag.md"),
            ])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.rag.md")

    def test_falls_back_to_path_when_rag_md_path_is_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("x", [1.0, 0.0])])  # rag_md_path defaults to None
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results[0].path, "x.md")

    def test_course_scope_skips_other_courses_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card("m", [1.0, 0.0])])
            save_shard(tmp, "spanish-101", [_card("s", [1.0, 0.0])])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            recompute_course_entry(tmp, "spanish-101")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), course="math-camp")
            self.assertEqual([r.path for r in results], ["m.md"])

    def test_top_k_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [_card(str(i), [1.0, 0.0]) for i in range(10)])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), top_k=3)
            self.assertEqual(len(results), 3)

    def test_doc_type_filter_applies_before_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [_card(f"p{i}", [1.0, 0.0], doc_type="problem_set") for i in range(5)]
            cards.append(_card("t", [0.99, 0.01], doc_type="textbook"))
            save_shard(tmp, "math-camp", cards)
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), top_k=2, doc_type="textbook")
            self.assertEqual([r.path for r in results], ["t.md"])

    def test_has_solutions_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("solved", [1.0, 0.0], has_solutions=True),
                _card("unsolved", [1.0, 0.0], has_solutions=False),
            ])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), has_solutions=False)
            self.assertEqual([r.path for r in results], ["unsolved.md"])

    def test_max_level_filter_excludes_harder_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("easy", [1.0, 0.0], level="introductory"),
                _card("hard", [1.0, 0.0], level="advanced"),
            ])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]), max_level="introductory")
            self.assertEqual([r.path for r in results], ["easy.md"])

    def test_excludes_orphaned_and_needs_indexing_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("good", [1.0, 0.0]),
                _card("orphan", [1.0, 0.0], orphaned=True),
                _card("pending", [1.0, 0.0], needs_indexing=True, embedding=[]),
            ])
            from index_card import recompute_course_entry
            recompute_course_entry(tmp, "math-camp")
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual([r.path for r in results], ["good.md"])

    def test_no_courses_indexed_yet_returns_empty_list_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = search(tmp, "q", client=_fake_query_client([1.0, 0.0]))
            self.assertEqual(results, [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: FAIL — `ImportError: cannot import name 'search'`

- [ ] **Step 3: Write the implementation**

```python
# append to marker-conversion/index_search.py
from dataclasses import dataclass

from index_card import KNOWN_LEVELS, EMBEDDING_DIMENSIONALITY, EMBEDDING_MODEL, cosine_similarity, load_courses  # noqa: E402
from google.genai import types  # noqa: E402

DEFAULT_COURSE_CANDIDATES = 3


@dataclass
class SearchResult:
    path: str
    course: str
    doc_type: str
    score: float
    reason: str


def _embed_query(query: str, client) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL, contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def _candidate_courses(academic_hub_root: str, query_embedding: list[float], course: str | None) -> list[str]:
    if course is not None:
        return [course]
    courses = load_courses(academic_hub_root)
    scored = sorted(
        courses.values(),
        key=lambda entry: cosine_similarity(query_embedding, entry.get("embedding") or []),
        reverse=True,
    )
    return [entry["course"] for entry in scored[:DEFAULT_COURSE_CANDIDATES]]


def search(
    academic_hub_root: str, query: str, client, course: str | None = None, top_k: int = 5,
    doc_type: str | None = None, has_solutions: bool | None = None, max_level: str | None = None,
) -> list[SearchResult]:
    query_embedding = _embed_query(query, client)
    candidate_courses = _candidate_courses(academic_hub_root, query_embedding, course)

    scored: list[SearchResult] = []
    for c in candidate_courses:
        for card in load_shard(academic_hub_root, c):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                continue
            if doc_type is not None and card.get("doc_type") != doc_type:
                continue
            if has_solutions is not None and card.get("has_solutions") != has_solutions:
                continue
            if max_level is not None:
                card_level = card.get("level")
                if card_level not in KNOWN_LEVELS or KNOWN_LEVELS.index(card_level) > KNOWN_LEVELS.index(max_level):
                    continue
            score = cosine_similarity(query_embedding, card["embedding"])
            # .rag.md is the same content plus inlined image descriptions --
            # strictly more useful to a text-only consumer, so always
            # preferred over the plain .md when set (spec §3.1/§4.4).
            result_path = card.get("rag_md_path") or card["path"]
            scored.append(SearchResult(
                path=result_path, course=card["course"], doc_type=card["doc_type"],
                score=score, reason=card.get("summary", ""),
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: PASS (22 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_search.py marker-conversion/tests/test_index_search.py
git commit -m "feat(indexer): add two-stage course/file search with pre-truncation filters"
```

---

### Task 7: CLI

**Files:**
- Modify: `marker-conversion/index_search.py`
- Test: `marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `search`, `rebuild` (Task 5/6); `gemini_utils.get_gemini_client`, `gemini_utils.load_dotenv_override`.
- Produces: `main()` (module `__main__` entry point), `build_arg_parser() -> argparse.ArgumentParser` (kept separate from `main()` specifically so tests can exercise argument parsing without needing a real Gemini client).

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_search.py
from index_search import build_arg_parser


class TestCLIArgParsing(unittest.TestCase):
    def test_query_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["query", "teach me linear algebra"])
        self.assertEqual(args.command, "query")
        self.assertEqual(args.query, "teach me linear algebra")
        self.assertIsNone(args.course)
        self.assertEqual(args.top_k, 5)
        self.assertIsNone(args.doc_type)
        self.assertIsNone(args.has_solutions)
        self.assertIsNone(args.max_level)

    def test_query_subcommand_with_filters(self):
        args = build_arg_parser().parse_args([
            "query", "eigenvalues", "--course", "math-camp", "--top-k", "3",
            "--doc-type", "problem_set", "--has-solutions", "false", "--max-level", "intermediate",
        ])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.top_k, 3)
        self.assertEqual(args.doc_type, "problem_set")
        self.assertFalse(args.has_solutions)
        self.assertEqual(args.max_level, "intermediate")

    def test_rebuild_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["rebuild"])
        self.assertEqual(args.command, "rebuild")
        self.assertIsNone(args.course)
        self.assertFalse(args.force)
        self.assertFalse(args.prune)

    def test_rebuild_subcommand_with_flags(self):
        args = build_arg_parser().parse_args(["rebuild", "--course", "math-camp", "--force", "--prune"])
        self.assertEqual(args.course, "math-camp")
        self.assertTrue(args.force)
        self.assertTrue(args.prune)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: FAIL — `ImportError: cannot import name 'build_arg_parser'`

- [ ] **Step 3: Write the implementation**

```python
# append to marker-conversion/index_search.py
import argparse

from gemini_utils import get_gemini_client, load_dotenv_override  # noqa: E402


def _bool_arg(value: str) -> bool:
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


def build_arg_parser() -> argparse.ArgumentParser:
    default_root = os.path.join(os.path.dirname(__file__), "..", "academic-hub")
    parser = argparse.ArgumentParser(description="Search and maintain the academic-hub source index.")
    parser.add_argument("--academic-hub", default=default_root, help="Path to the academic-hub root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Search the index for relevant sources.")
    query.add_argument("query")
    query.add_argument("--course", default=None)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--doc-type", default=None)
    query.add_argument("--has-solutions", type=_bool_arg, default=None)
    query.add_argument("--max-level", default=None, choices=list(KNOWN_LEVELS))

    rebuild_p = subparsers.add_parser("rebuild", help="Backfill/reconcile index cards for the notes pipeline.")
    rebuild_p.add_argument("--course", default=None)
    rebuild_p.add_argument("--force", action="store_true")
    rebuild_p.add_argument("--prune", action="store_true")

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "query":
        results = search(
            args.academic_hub, args.query, client, course=args.course, top_k=args.top_k,
            doc_type=args.doc_type, has_solutions=args.has_solutions, max_level=args.max_level,
        )
        for r in results:
            print(f"{r.score:.3f}  [{r.course}/{r.doc_type}]  {r.path}\n    {r.reason}")
    elif args.command == "rebuild":
        stats = rebuild(args.academic_hub, client, course=args.course, force=args.force, prune=args.prune)
        print(stats)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: PASS (26 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_search.py marker-conversion/tests/test_index_search.py
git commit -m "feat(indexer): add query/rebuild CLI"
```

---

### Task 8: Hook into `transcribe_notes.py`

**Files:**
- Modify: `marker-conversion/transcribe_notes.py`
- Test: `marker-conversion/tests/test_transcribe_notes.py`

**Interfaces:**
- Consumes: `index_card.compute_file_id`, `index_card.derive_course`, `index_card.reconcile_and_write` (Tasks 1/4).
- Produces: `_write_markdown_and_index(md_path: str, frontmatter: str, final_md: str, pdf_path: str, folder_category: str, total_pages: int, client) -> None` — the one new helper replacing all 4 duplicated write blocks in `process_pdf()`.

**Why this shape:** `process_pdf()` (line 799) has four separate exit points (Tier 1 clean/hybrid/whole-batch/accumulating), each currently ending in its own `with open(md_path, "w"...) as f: f.write(...)` block (lines ~846-847, 906-907, 977-978, 1034-1035) before an early `return`. Duplicating the indexing call four times would violate this project's own DRY convention; one shared helper, called from all four places instead, keeps the diff minimal and the tier-specific logic (and print messages) completely untouched.

- [ ] **Step 1: Write the failing test**

```python
# append to marker-conversion/tests/test_transcribe_notes.py
from unittest.mock import MagicMock, patch

# `os`, `tempfile`, `unittest` are already imported at the top of this file.
# Add `_write_markdown_and_index` to the existing
# `from transcribe_notes import (...)` block at the top of the file
# (alongside `build_frontmatter`, `derive_folder_category`, etc.) rather
# than a separate import statement here.


class TestWriteMarkdownAndIndex(unittest.TestCase):
    def test_writes_file_then_calls_reconcile_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = os.path.join(tmp, "out.md")
            pdf_path = os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "foo.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"fake pdf")

            with patch("transcribe_notes.reconcile_and_write") as mock_reconcile:
                _write_markdown_and_index(
                    md_path=md_path, frontmatter="---\nx: 1\n---\n\n", final_md="content",
                    pdf_path=pdf_path, academic_hub_root=tmp, folder_category="ta_notes",
                    total_pages=3, client=MagicMock(),
                )

            with open(md_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "---\nx: 1\n---\n\ncontent")
            self.assertEqual(mock_reconcile.call_count, 1)
            _, kwargs = mock_reconcile.call_args
            self.assertEqual(kwargs["course"], "math-camp")
            self.assertEqual(kwargs["folder_category"], "ta_notes")
            self.assertEqual(kwargs["page_count"], 3)
            self.assertEqual(kwargs["content_sample"], "content")

    def test_indexing_failure_does_not_raise_or_block_the_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = os.path.join(tmp, "out.md")
            pdf_path = os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "foo.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"fake pdf")

            with patch("transcribe_notes.reconcile_and_write", side_effect=RuntimeError("boom")):
                _write_markdown_and_index(  # must not raise
                    md_path=md_path, frontmatter="", final_md="content", pdf_path=pdf_path,
                    academic_hub_root=tmp, folder_category="ta_notes", total_pages=3, client=MagicMock(),
                )
            with open(md_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "content")  # file still written
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd marker-conversion && python -m unittest tests.test_transcribe_notes.TestWriteMarkdownAndIndex -v`
Expected: FAIL — `ImportError: cannot import name '_write_markdown_and_index'`

- [ ] **Step 3: Write the implementation**

Add near the top of `marker-conversion/transcribe_notes.py`, alongside the existing imports:

```python
from index_card import compute_file_id, derive_course, reconcile_and_write
```

Add this new function immediately before `process_pdf()` (before line 799):

```python
def _write_markdown_and_index(md_path, frontmatter, final_md, pdf_path, academic_hub_root,
                               folder_category, total_pages, client):
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + final_md)

    try:
        file_id = compute_file_id(pdf_path)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_pdf_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_pdf_path,
            course=course, folder_category=folder_category, content_sample=final_md,
            page_count=total_pages, client=client,
        )
    except Exception as err:
        # Indexing must never block or corrupt the actual transcription
        # output (spec §4.2) -- the markdown file above is already
        # written and complete regardless of what happens here.
        print(f"WARNING: source-indexer update failed for {md_path} ({err}); "
              f"rerun `python index_search.py rebuild` later to catch it up.")
```

Then replace each of the four `with open(md_path, "w", encoding="utf-8") as f: f.write(frontmatter + final_md)` blocks in `process_pdf()` with a call to this helper. `process_pdf()` needs one new parameter, `academic_hub_root` — `main()` already computes exactly this root at line 1063 (`academic_hub_dir = Path(__file__).resolve().parent.parent / "academic-hub"`, used today to build `notes_dir`), so this is threading an existing value through, not deriving a new one. Two small edits:

`process_pdf()`'s signature (line 799), from:
```python
def process_pdf(pdf_path: str, client, model_override: str | None, dry_run: bool = False) -> None:
```
to:
```python
def process_pdf(pdf_path: str, client, model_override: str | None, academic_hub_root: str, dry_run: bool = False) -> None:
```

Its call site in `main()` (line 1077), from:
```python
        process_pdf(pdf_path, client, args.model, dry_run=args.dry_run)
```
to:
```python
        process_pdf(pdf_path, client, args.model, str(academic_hub_dir), dry_run=args.dry_run)
```

Then, for example, Tier 1 (currently lines 843-847):

```python
        frontmatter = build_frontmatter({
            **base_metadata, "routing": "local", "pages_repaired": 0, "repaired_pages": [], "tags": [],
        })
        _write_markdown_and_index(
            md_path, frontmatter, final_md, pdf_path, academic_hub_root,
            folder_category, total_pages, client,
        )
```

(with the existing `print(f"[{base_name}] wrote {md_path} ...")` line immediately following, unchanged, as it already does today). Apply the same substitution at the three remaining sites (hybrid, whole-document batched, accumulating), each keeping its own existing `frontmatter = build_frontmatter({...})` call and tier-specific print message exactly as they are today — only the `with open(...) as f: f.write(...)` block itself is replaced.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_transcribe_notes -v`
Expected: PASS (all existing tests plus the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/transcribe_notes.py marker-conversion/tests/test_transcribe_notes.py
git commit -m "feat(indexer): hook transcribe_notes.py's 4 write paths into the source indexer"
```

---

### Task 9: `_metadata.json` linkage fields + hook into `convert_textbook.py`

**Files:**
- Modify: `marker-conversion/convert_textbook.py`

**Interfaces:**
- Consumes: `index_card.compute_file_id`, `index_card.derive_course`, `index_card.reconcile_and_write`, `index_card.TEXTBOOK_CONTENT_SAMPLE_CHARS` (Tasks 1/4).
- Produces: `_metadata.json` gains `source_pdf_path`/`source_pdf_file_id` — consumed by Task 5's `rebuild()` (textbook backfill) and Task 10 (`describe_images.py`'s hook).

**Testing note:** per the Global Constraints, `convert_textbook.py` cannot be imported in this environment (`import torch` fails at module scope — confirmed). Every function this task calls (`compute_file_id`, `derive_course`, `reconcile_and_write`) is already fully unit-tested by Tasks 1 and 4. This task's own correctness is verified by careful review of the diff against the real function below (already read in full during planning), not by running a test here — consistent with how `chapter_index.py` was already split out of this exact file for the same reason.

- [ ] **Step 1: Add the import**

Add near the top of `marker-conversion/convert_textbook.py`, alongside its other local imports:

```python
from index_card import TEXTBOOK_CONTENT_SAMPLE_CHARS, compute_file_id, derive_course, reconcile_and_write
from gemini_utils import get_gemini_client, load_dotenv_override
```

- [ ] **Step 2: Write the PDF linkage fields and add the hook call**

In `process_one_pdf()`, replace the existing metadata write (currently lines 881-888):

```python
        master_metadata.update({
            "total_pages_processed": total_pages,
            "processing_time_seconds": round(elapsed, 2),
            "source_pdf_document_info": source_info,
            "markdown_parsed_info": markdown_info,
        })
        with open(os.path.join(local_build_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as json_f:
            json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)
```

with:

```python
        academic_hub_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "academic-hub"))
        # Cheap local hashing, no network call -- computed and recorded
        # unconditionally, independent of whether the LLM-dependent
        # indexing call below succeeds. This is what lets rebuild()
        # (Task 5) and describe_images.py's hook (Task 10) find this
        # book's source PDF later without any filename guessing -- the
        # ambiguity that made textbook backfill unreliable before this
        # field existed (processed_outputs/<FolderName>/ folder names
        # don't correspond to their source PDF's filename).
        file_id = compute_file_id(input_pdf)
        rel_pdf_path = os.path.relpath(input_pdf, academic_hub_root).replace(os.sep, "/")

        master_metadata.update({
            "total_pages_processed": total_pages,
            "processing_time_seconds": round(elapsed, 2),
            "source_pdf_document_info": source_info,
            "markdown_parsed_info": markdown_info,
            "source_pdf_path": rel_pdf_path,
            "source_pdf_file_id": file_id,
        })
        with open(os.path.join(local_build_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as json_f:
            json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

        try:
            load_dotenv_override()
            index_client = get_gemini_client()
            if index_client is None:
                raise RuntimeError("GEMINI_API_KEY not available -- see gemini_utils.get_gemini_client()")
            md_output_path = os.path.join(local_build_dir, f"{folder_name}.md")
            with open(md_output_path, "r", encoding="utf-8") as f:
                content_sample = f.read(TEXTBOOK_CONTENT_SAMPLE_CHARS)
            course = derive_course(rel_pdf_path)
            # local_build_dir is a temp assembly directory uploaded to raw_output
            # afterward (see "Resolve Output Trajectory" below) -- the card's
            # `path` records where the file will live once uploaded, under
            # academic-hub's own processed_outputs convention, not this temp path.
            rel_md_path = (
                f"{rel_pdf_path.rsplit('/', 1)[0]}/processed_outputs/{folder_name}/{folder_name}.md"
            )
            reconcile_and_write(
                academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_pdf_path,
                course=course, folder_category="textbooks-and-papers", content_sample=content_sample,
                page_count=total_pages, client=index_client,
            )
        except Exception as index_err:
            print(f"WARNING: source-indexer update failed for {folder_name} ({index_err}); "
                  f"the converted textbook output above is unaffected -- rerun the indexer "
                  f"separately later to catch it up.")
```

**Note on the client:** uses `gemini_utils.get_gemini_client()` (Developer API key), matching every other indexing call in this plan (Global Constraints) — not the Vertex-backed client `extract_bibliographic_info_via_llm()` builds for its own, separate, existing bibliographic-extraction call. This requires `.env`/`GEMINI_API_KEY` to be reachable from wherever `convert_textbook.py` runs; if it isn't, `get_gemini_client()` returns `None`, which is turned into a `RuntimeError` and caught by the same `try`/`except` as any other indexing failure — never blocking the actual conversion, consistent with spec §4.2.

- [ ] **Step 3: Manually review the diff**

Run: `cd marker-conversion && git diff convert_textbook.py`
Confirm: `source_pdf_path`/`source_pdf_file_id` are written into `master_metadata` before the `_metadata.json` dump (so they're present even if the `try` block below fails); the indexing hook sits after that write, before "Resolve Output Trajectory"; no unrelated line was altered; indentation matches the surrounding block (this code is inside `process_one_pdf()`'s outer `try:`, same indentation level as the original `master_metadata.update(...)` call).

- [ ] **Step 4: Commit**

```bash
git add marker-conversion/convert_textbook.py
git commit -m "feat(indexer): record source PDF linkage in _metadata.json, hook into the indexer"
```

---

### Task 10: `.rag.md` linkage in `describe_images.py`

**Files:**
- Modify: `marker-conversion/describe_images.py`
- Test: `marker-conversion/tests/test_describe_images.py`

**Interfaces:**
- Consumes: `index_card.set_rag_md_path` (Task 4).
- Produces: `link_rag_md(book_dir: str, folder_name: str, rag_path: str, academic_hub_root: str) -> bool`. Called once by `process_book()`, immediately after it writes `.rag.md`. Last integration point in this plan.

**Note:** `describe_images.py` has no torch/marker dependency (confirmed: imports cleanly in this environment) and already has its own test file, unlike `convert_textbook.py` — this task follows normal TDD, not Task 9's diff-review approach. Per this module's own established pattern (small pure functions, thin `process_book()` orchestration — matching every other function already in `test_describe_images.py`), the new logic is extracted into its own testable function rather than inlined into `process_book()`.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_describe_images.py
from unittest.mock import patch

# `os`, `tempfile`, `unittest`, `json` are already imported at the top of
# this file. Add `link_rag_md` to the existing
# `from describe_images import (...)` block rather than a separate import.


class TestLinkRagMd(unittest.TestCase):
    def _book_dir_with_metadata(self, tmp, metadata):
        book_dir = os.path.join(tmp, "processed_outputs", "SomeBook_2025")
        os.makedirs(book_dir)
        with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        return book_dir

    def test_writes_rag_md_path_into_metadata_and_the_matching_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {"source_pdf_file_id": "fid1"})
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")

            with patch("describe_images.set_rag_md_path", return_value=True) as mock_set:
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)

            self.assertTrue(found)
            mock_set.assert_called_once()
            self.assertEqual(mock_set.call_args[0][0], tmp)
            self.assertEqual(mock_set.call_args[0][1], "fid1")
            self.assertEqual(mock_set.call_args[0][2], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")

            with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["rag_md_path"], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")
            self.assertEqual(metadata["source_pdf_file_id"], "fid1")  # untouched

    def test_returns_false_when_metadata_has_no_source_pdf_file_id_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {})  # predates this field
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            with patch("describe_images.set_rag_md_path") as mock_set:
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
            mock_set.assert_not_called()

    def test_returns_false_but_still_writes_metadata_when_no_card_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {"source_pdf_file_id": "fid1"})
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            with patch("describe_images.set_rag_md_path", return_value=False):
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
            with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["rag_md_path"], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")

    def test_missing_metadata_file_returns_false_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "processed_outputs", "SomeBook_2025")
            os.makedirs(book_dir)  # no _metadata.json written at all
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_describe_images -v`
Expected: FAIL — `ImportError: cannot import name 'link_rag_md'`

- [ ] **Step 3: Write the implementation**

Add near the top of `marker-conversion/describe_images.py`, alongside its other local imports:

```python
from index_card import set_rag_md_path
```

Add this new function immediately before `process_book()` (before line 223):

```python
def link_rag_md(book_dir: str, folder_name: str, rag_path: str, academic_hub_root: str) -> bool:
    """Called by process_book() right after it writes .rag.md. Records the
    linkage in _metadata.json unconditionally (independent of whether a
    matching index card exists yet), and updates the card's rag_md_path
    when one does. Never raises -- a linkage failure must not affect the
    .rag.md file this runs after, or abort process_book()'s caller's loop
    over the rest of the books being processed."""
    metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError) as err:
        print(f"WARNING: [{folder_name}] could not read {metadata_path} ({err}); "
              f"skipping .rag.md linkage.")
        return False

    file_id = metadata.get("source_pdf_file_id")
    if not file_id:
        print(f"WARNING: [{folder_name}] no source_pdf_file_id in {metadata_path} "
              f"(converted before this field existed) -- skipping .rag.md linkage. "
              f"Re-run convert_textbook.py on its PDF, or add the field by hand, "
              f"then rerun describe_images.py.")
        return False

    rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
    metadata["rag_md_path"] = rel_rag_path
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    found = set_rag_md_path(academic_hub_root, file_id, rel_rag_path)
    if not found:
        print(f"WARNING: [{folder_name}] no index card found for file_id {file_id} yet -- "
              f"_metadata.json's rag_md_path is recorded regardless; rerun "
              f"`python index_search.py rebuild` later to pick it up.")
    return found
```

Then thread `academic_hub_root` through `process_book()` and call `link_rag_md()` after the existing `.rag.md` write. `process_book()`'s signature (currently line 223-230), from:
```python
def process_book(
    book_dir: str,
    client,
    model: str,
    paragraphs_before: int = 1,
    paragraphs_after: int = 1,
    dry_run: bool = False,
) -> None:
```
to:
```python
def process_book(
    book_dir: str,
    client,
    model: str,
    academic_hub_root: str,
    paragraphs_before: int = 1,
    paragraphs_after: int = 1,
    dry_run: bool = False,
) -> None:
```

Its body (currently lines 282-285), from:
```python
    rag_text = build_rag_markdown(text, cache)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(rag_text)
    print(f"[{folder_name}] wrote {rag_path}")
```
to:
```python
    rag_text = build_rag_markdown(text, cache)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(rag_text)
    print(f"[{folder_name}] wrote {rag_path}")

    link_rag_md(book_dir, folder_name, rag_path, academic_hub_root)
```

And its call site in `main()` (currently line 324-328), from:
```python
    for book_dir in book_dirs:
        process_book(
            book_dir, client, args.model,
            args.context_paragraphs_before, args.context_paragraphs_after,
            dry_run=args.dry_run,
        )
```
to (reusing `academic_hub_dir`, already computed at line 310 for `processed_outputs_dir`):
```python
    for book_dir in book_dirs:
        process_book(
            book_dir, client, args.model, str(academic_hub_dir),
            args.context_paragraphs_before, args.context_paragraphs_after,
            dry_run=args.dry_run,
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_describe_images -v`
Expected: PASS (all existing tests plus the 4 new ones)

- [ ] **Step 5: Manually review the `process_book()`/`main()` diff**

Run: `cd marker-conversion && git diff describe_images.py`
Confirm: `academic_hub_root` is threaded through both the signature and its one call site; `link_rag_md(...)` is called after the existing `.rag.md` write and its print statement, not before; no existing line altered besides the signature/call-site edits.

- [ ] **Step 6: Commit**

```bash
git add marker-conversion/describe_images.py marker-conversion/tests/test_describe_images.py
git commit -m "feat(indexer): link .rag.md back to its index card and _metadata.json"
```

---

## Self-Review Notes

- **Spec coverage:** §3 (schema, including `rag_md_path`) → Tasks 1-3. §4 (generation, hooks, failure isolation, reconciliation) → Tasks 2, 4, 8, 9. §4.4 (`.rag.md` linkage) → Task 10. §6 (search, including `rag_md_path` preference) → Task 6. §7 (rebuild/backfill, orphans, conditional textbook backfill via `source_pdf_path`) → Task 5. §8 (CLI) → Task 7. §5 (retag/tag mining) is **not** in this plan — it's Plan 2, since nothing here depends on `topics` being populated (search ranks purely by embedding similarity).
- **Type consistency checked:** `reconcile_and_write`'s parameter names/order match across Task 4 (definition), Task 5 (`_reconcile_one`'s call, both notes and textbook paths), Task 8 (`_write_markdown_and_index`'s call), and Task 9's call — all use the same keyword arguments (`file_id`, `path`, `source_pdf_path`, `course`, `folder_category`, `content_sample`, `page_count`, `client`). `set_rag_md_path`'s signature matches between Task 4 (definition) and Task 10 (`link_rag_md`'s call). `SearchResult`'s fields (`path`, `course`, `doc_type`, `score`, `reason`) match spec §6 exactly, with `path` resolving `rag_md_path` first. `KNOWN_LEVELS` ordering (`introductory` < `intermediate` < `advanced`) is defined once in `index_card.py` and consumed identically by Task 6's `max_level` filter and Task 7's CLI `choices`. `TEXTBOOK_CONTENT_SAMPLE_CHARS` (Task 1) is the same constant used by both Task 5's textbook backfill and Task 9's live hook, so they read the same amount of content.
- **Client construction consistency:** every indexing call (Tasks 2's `generate_index_card`/`embed_content`, Task 6's query embedding) takes a caller-supplied `client`; every caller (Task 7's CLI, Task 8's `transcribe_notes.py` hook, Task 9's `convert_textbook.py` hook, Task 10 reusing `describe_images.py`'s existing `client` parameter) builds it via `gemini_utils.get_gemini_client()` — no Vertex path anywhere in this plan (Global Constraints).
- **No placeholders:** every step has runnable code; the one deliberately unbuilt piece (textbook backfill for the 5 books that predate `source_pdf_path`) is called out explicitly with its reason and its fix (re-run `convert_textbook.py`), not left as a vague TODO.
