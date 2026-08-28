# Source Indexer (Core: Cards, Reconciliation, Search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core source indexer — per-file index cards generated from `transcribe_notes.py`/`convert_textbook.py`, reconciled by content hash (not path), and searchable via a two-stage embedding-similarity CLI/function — so a query like "teach me about linear algebra" returns ranked, relevant files from `academic-hub`.

**Architecture:** A new torch/marker-free module `index_card.py` owns card generation, shard I/O, and `file_id`-based reconciliation (mirroring how `chapter_index.py` is already kept free of `convert_textbook.py`'s heavy imports so it stays independently testable). A new `index_search.py` owns two-stage search and the notes-pipeline rebuild/backfill pass, plus the CLI. Both existing pipelines get a minimal hook calling into `index_card.py`.

**Tech Stack:** Python 3.13, `google-genai` 2.9.0 (already installed), `numpy` 2.5.2 (already installed), stdlib `hashlib`/`json`/`unittest`. **No new dependencies** — tag mining (which needs `rapidfuzz`) is out of scope for this plan; see Plan 2.

**Spec:** `marker-conversion/docs/superpowers/specs/2026-08-27-source-indexer-design.md`

## Global Constraints

- Generation model: `gemini-3.6-flash` (matches every existing generation call in this project — `describe_images.py`, `transcribe_notes.py`, `extract_bibliographic_info_via_llm()`).
- Embedding model: `gemini-embedding-001`, `output_dimensionality=768` — confirmed live against the real API (spec §4). Stored per-card as `embedding_model: "gemini-embedding-001:768"`. Returned vectors are **not pre-normalized** — every cosine-similarity computation must normalize itself.
- Structured-JSON generation calls use `config={"response_mime_type": "application/json", "temperature": 0, "thinking_config": {"thinking_level": "minimal"}}` — the exact pattern already established in `extract_bibliographic_info_via_llm()` (`convert_textbook.py:654`), reused rather than reinvented.
- `path`/`source_pdf_path` on every card are relative to `academic-hub/`, never absolute.
- Tests use plain `unittest` (not pytest — not installed in this environment) and are run via `cd marker-conversion && python -m unittest tests.test_<module> -v` — confirmed working against this repo's existing tests.
- `convert_textbook.py` cannot be imported in this development environment (`import torch` / `import marker` both fail — confirmed; only `chapter_index.py`'s already-established torch-free extraction pattern is testable here). Task 9 (the `convert_textbook.py` hook) is therefore verified by careful code review of the diff, not by an executable test — every other task's logic lives in `index_card.py`/`index_search.py` and is fully unit-tested.
- `rebuild` (Task 5) backfills the notes pipeline only. Backfilling the 5 already-converted textbooks is explicitly out of scope for this plan (see Task 5's note) — new textbook conversions are unaffected, since the live hook (Task 9) has no matching ambiguity.

---

## File Structure

- Create: `marker-conversion/index_card.py` — card schema, `file_id` computation, course derivation, shard I/O, card generation (LLM + embedding calls), `file_id`-based reconciliation, course-level rollup.
- Create: `marker-conversion/index_search.py` — two-stage search, notes-pipeline rebuild/backfill, CLI (`query`/`rebuild` subcommands).
- Modify: `marker-conversion/transcribe_notes.py` — replace the 4 duplicated "write markdown file" blocks in `process_pdf()` with one shared helper that writes the file and then calls into `index_card.py`.
- Modify: `marker-conversion/convert_textbook.py` — one hook call in `process_one_pdf()`, immediately after `_metadata.json` is written.
- Create: `marker-conversion/tests/test_index_card.py`
- Create: `marker-conversion/tests/test_index_search.py`
- Modify: `marker-conversion/tests/test_transcribe_notes.py` — add coverage for the new shared write-and-index helper.

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
GENERATION_MODEL = "gemini-3.6-flash"

KNOWN_DOC_TYPES = {"textbook", "problem_set", "exam", "ta_notes", "handwritten_notes"}
KNOWN_LEVELS = ("introductory", "intermediate", "advanced")


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
- Produces: `find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None`, `reconcile_and_write(academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str, content_sample: str, page_count: int, client) -> dict`. This is the **single function both pipeline hooks call** (Tasks 8 and 9) and the one Task 5 (rebuild) calls per file.

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (30 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(indexer): add file_id reconciliation across renames, moves, and course changes"
```

---

### Task 5: Rebuild / backfill pass (notes pipeline)

**Files:**
- Create: `marker-conversion/index_search.py`
- Test: `marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `compute_file_id`, `derive_course`, `reconcile_and_write`, `load_shard`, `save_shard`, `recompute_course_entry` (Task 1-4).
- Produces: `rebuild(academic_hub_root: str, client, force: bool = False, prune: bool = False) -> dict` (returns a stats dict: `{"generated": int, "updated": int, "unchanged": int, "moved": int, "orphaned": int, "pruned": int}`). Consumed by Task 7's CLI.

**Note on a smaller accuracy gap:** backfilled cards get `page_count=None`
rather than the real value, since `rebuild` doesn't parse the existing
YAML frontmatter's `total_pages` field back out of each `.md` file (no
parser for it exists yet, and the project's own `build_frontmatter()`
deliberately avoided adding PyYAML "for something this narrow" — writing
one just to extract a single integer felt like the same tradeoff). Cards
generated live by Task 8's hook are unaffected — they already receive the
real `total_pages` directly from `process_pdf()`. Worth a follow-up if
backfilled `page_count` accuracy matters in practice.

**Note on scope:** walks `academic_notes/<course>/<category>/*.pdf` only — for every such PDF, its markdown sibling is at the deterministic path `<category>/processed_outputs/<basename>.md` (matching `transcribe_notes.py`'s own `process_pdf()` convention exactly). Backfilling `academic_resources/.../textbooks-and-papers/` is **not** included: there is no reliable existing link from an already-converted `processed_outputs/<FolderName>/` output back to which of the PDFs in that folder produced it (filenames don't correspond — e.g. `Book of Proof.pdf` → `Hammack_Book_of_Proof_2025/` — and `_metadata.json` doesn't record a source filename). Guessing via fuzzy title matching risks silently attaching a card to the wrong book. This is a real, bounded gap in backfill coverage for the 5 textbooks already converted as of this writing — new textbook conversions are unaffected, since Task 9's live hook runs inside the exact conversion that produces the file, with no matching ambiguity at all.

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

import os

from index_card import (
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


def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {"generated": 0, "updated": 0, "unchanged": 0, "moved": 0, "orphaned": 0, "pruned": 0}
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

        existing = None
        for c in load_shard(academic_hub_root, course_name):
            if c.get("file_id") == file_id:
                existing = c
                break
        already_current = (
            existing is not None and not force and not existing.get("needs_indexing")
            and existing.get("path") == rel_md_path
        )
        if already_current:
            stats["unchanged"] += 1
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

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
            academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_pdf_path,
            course=course_name, folder_category=category, content_sample=content_sample,
            page_count=None, client=client,
        )
        if was_new:
            stats["generated"] += 1
        elif existing is not None and existing.get("course") != course_name:
            stats["moved"] += 1
        else:
            stats["updated"] += 1

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
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_search.py marker-conversion/tests/test_index_search.py
git commit -m "feat(indexer): add notes-pipeline rebuild/backfill with orphan flagging and prune"
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
        "has_solutions": False, "page_count": 10, "embedding": embedding,
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
            scored.append(SearchResult(
                path=card["path"], course=card["course"], doc_type=card["doc_type"],
                score=score, reason=card.get("summary", ""),
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_search -v`
Expected: PASS (16 tests)

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
Expected: PASS (20 tests)

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

### Task 9: Hook into `convert_textbook.py`

**Files:**
- Modify: `marker-conversion/convert_textbook.py`

**Interfaces:**
- Consumes: `index_card.compute_file_id`, `index_card.derive_course`, `index_card.reconcile_and_write` (Tasks 1/4).
- Produces: nothing new consumed elsewhere — this is the last integration point.

**Testing note:** per the Global Constraints, `convert_textbook.py` cannot be imported in this environment (`import torch` fails at module scope — confirmed). Every function this task calls (`compute_file_id`, `derive_course`, `reconcile_and_write`) is already fully unit-tested by Tasks 1 and 4. This task's own correctness is verified by careful review of the diff against the real function below (already read in full during planning), not by running a test here — consistent with how `chapter_index.py` was already split out of this exact file for the same reason.

- [ ] **Step 1: Add the import**

Add near the top of `marker-conversion/convert_textbook.py`, alongside its other local imports:

```python
from index_card import compute_file_id, derive_course, reconcile_and_write
```

- [ ] **Step 2: Add the hook call**

In `process_one_pdf()`, immediately after the existing metadata write (currently lines 881-888):

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

add:

```python
        try:
            from google import genai as _genai  # local import: convert_textbook.py never
            # imports google.genai at module scope (extract_bibliographic_info_via_llm()
            # imports it locally too, at line 632, for the same reason -- google-genai
            # isn't a hard dependency when --no-llm-bib is used) -- mirroring that
            # existing pattern rather than adding a new module-level import.

            academic_hub_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "academic-hub"))
            md_output_path = os.path.join(local_build_dir, f"{folder_name}.md")
            with open(md_output_path, "r", encoding="utf-8") as f:
                content_sample = f.read(12000)
            file_id = compute_file_id(input_pdf)
            rel_pdf_path = os.path.relpath(input_pdf, academic_hub_root).replace(os.sep, "/")
            course = derive_course(rel_pdf_path)
            # local_build_dir is a temp assembly directory uploaded to raw_output
            # afterward (see "Resolve Output Trajectory" below) -- the card's
            # `path` records where the file will live once uploaded, under
            # academic-hub's own processed_outputs convention, not this temp path.
            rel_md_path = (
                f"{rel_pdf_path.rsplit('/', 1)[0]}/processed_outputs/{folder_name}/{folder_name}.md"
            )
            index_client = _genai.Client(vertexai=True, project=args.llm_project, location=args.llm_location)
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

**Note on the Vertex client:** this constructs a fresh `genai.Client(vertexai=True, ...)` rather than reusing `extract_bibliographic_info_via_llm()`'s internal client, since that function doesn't expose the client it builds internally (line 650) — mirrors the same construction call already used there, including the local `from google import genai` import. If `args.llm_bib` was disabled (`--no-llm-bib`) or `args.llm_project` never resolved, this call will fail the same way the existing bibliographic-extraction call would in that case; the `try`/`except` above already treats that as non-fatal to the conversion, consistent with spec §4.2. Whether Vertex-backed `embed_content()` calls behave identically to the Developer-API-key calls this was tested against (Task 2) is a reasonable assumption from using the same SDK, not something verified in this environment (no Vertex/GCP access here) — worth confirming the first time this actually runs on the GCP VM.

- [ ] **Step 3: Manually review the diff**

Run: `cd marker-conversion && git diff convert_textbook.py`
Confirm: the added block sits after the existing metadata write, before "Resolve Output Trajectory"; no existing line was altered; indentation matches the surrounding `try:` block (this code is inside `process_one_pdf()`'s outer `try:`, same indentation level as the `master_metadata.update(...)` call above it).

- [ ] **Step 4: Commit**

```bash
git add marker-conversion/convert_textbook.py
git commit -m "feat(indexer): hook convert_textbook.py into the source indexer"
```

---

## Self-Review Notes

- **Spec coverage:** §3 (schema) → Tasks 1-3. §4 (generation, hooks, failure isolation, reconciliation) → Tasks 2, 4, 8, 9. §6 (search) → Task 6. §7 (rebuild/backfill, orphans) → Task 5 (notes-only; textbook backfill explicitly scoped out, see Task 5's note and Global Constraints). §8 (CLI) → Task 7. §5 (retag/tag mining) is **not** in this plan — it's Plan 2, since nothing here depends on `topics` being populated (search ranks purely by embedding similarity).
- **Type consistency checked:** `reconcile_and_write`'s parameter names/order match across Task 4 (definition), Task 5 (`rebuild`'s call), Task 8 (`_write_markdown_and_index`'s call), and Task 9's call — all use the same keyword arguments (`file_id`, `path`, `source_pdf_path`, `course`, `folder_category`, `content_sample`, `page_count`, `client`). `SearchResult`'s fields (`path`, `course`, `doc_type`, `score`, `reason`) match spec §6 exactly. `KNOWN_LEVELS` ordering (`introductory` < `intermediate` < `advanced`) is defined once in `index_card.py` and consumed identically by Task 6's `max_level` filter and Task 7's CLI `choices`.
- **No placeholders:** every step has runnable code; the one deliberately unbuilt piece (textbook-side `rebuild` backfill) is called out explicitly with its reason, not left as a vague TODO.
