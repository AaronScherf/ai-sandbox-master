# Source Indexer Tag Mining (`retag`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `retag` — the corpus-wide, two-phase tag mining pass (spec §5) that mines and assigns `tags` on every card, the one piece of the source indexer Plan 1 deliberately left out (`tags: []` has sat empty since Plan 1 shipped; search itself never needed it).

**Architecture:** A new module `retag.py` owns the two-phase algorithm — **discovery** (connected components over the corpus's card embeddings → clusters ≥ a minimum size mint new tags, each anchored to an embedding of its own name/definition, never a cluster centroid) and **assignment** (every card independently checked against every tag anchor in the vocabulary — no cluster-membership restriction, which is what makes this genuinely many-to-many instead of one-tag-per-file). `index_card.py` gains the small storage primitives (`tags.json` I/O, a shared course-listing helper) both `retag.py` and Plan 1's existing `find_card_by_file_id()` need. `index_search.py` gains the `retag` CLI subcommand the Plan 1 spec already documented but never wired up.

**Tech Stack:** Python 3.13, `google-genai` 2.9.0, `numpy` 2.5.2 (both already installed), **`rapidfuzz`, the one new dependency Plan 1 explicitly deferred** (confirmed not currently installed in `marker-conversion/.venv`) — needed for fuzzy-matching a proposed tag name against the existing vocabulary so `linear-algebra`/`Linear Algebra`/`lin-alg` don't fragment into separate tags.

**Spec:** `marker-conversion/docs/superpowers/specs/2026-08-27-source-indexer-design.md`, §3.3 and §5 specifically (both revised same day as this plan — the tag vocabulary now stores `{tag, embedding}` pairs, and mining is two-phase, not single-pass clustering).

## Global Constraints

- Generation model: `gemini-3.1-flash-lite`, same as every other indexing call (Plan 1's Global Constraints) — cluster naming is pure text-in/JSON-out, no vision.
- Embedding model: `gemini-embedding-001`, `output_dimensionality=768`, same as every other embedding call — a tag's anchor embedding must live in the same vector space as card embeddings for cosine similarity between them to mean anything.
- Client construction: `gemini_utils.get_gemini_client()` (Developer API key), same as Plan 1 — `retag` is invoked from the CLI (`index_search.py`), which already builds this client the same way for `query`/`rebuild`.
- Structured-JSON generation calls use the same `config={"response_mime_type": "application/json", "temperature": 0, "thinking_config": {"thinking_level": "minimal"}}` pattern as every other generation call in this project.
- `CLUSTER_SIMILARITY_THRESHOLD` (discovery), `TAG_ASSIGNMENT_THRESHOLD` (assignment), `MIN_TAG_CLUSTER_SIZE`, and `TAG_FUZZY_MATCH_THRESHOLD` are all tunable constants expected to need empirical adjustment against the real corpus (spec §5.2) — not something this plan claims to get exactly right on the first pass. `retag --dry-run` (Task 3) exists specifically so these can be sanity-checked before a run that mutates every course shard.
- `retag.py` has no torch/marker dependency (like `index_card.py`/`index_search.py`) and is fully unit-testable in this environment.
- Tests use plain `unittest`, run via `cd marker-conversion && python -m unittest tests.test_<module> -v` (confirmed working convention from Plan 1).

---

## File Structure

- Modify: `marker-conversion/index_card.py` — add `list_courses()` (extracted from `find_card_by_file_id()`'s existing shard-enumeration logic, reused by both), `tags_path()`, `load_tags()`, `save_tags()`.
- Create: `marker-conversion/retag.py` — discovery (clustering, naming, minting), assignment (many-to-many tagging), the `retag()` orchestration function.
- Modify: `marker-conversion/index_search.py` — add the `retag` CLI subcommand (the spec's §8 already documents this command; Plan 1 never wired it up since `retag()` didn't exist yet).
- Create: `marker-conversion/tests/test_retag.py`.
- Modify: `marker-conversion/tests/test_index_card.py` — add coverage for `list_courses()`/`load_tags()`/`save_tags()`.

---

### Task 1: Tag vocabulary I/O + shared course-listing helper

**Files:**
- Modify: `marker-conversion/index_card.py`
- Test: `marker-conversion/tests/test_index_card.py`

**Interfaces:**
- Consumes: `_index_dir()`, `load_shard()` (already in `index_card.py`).
- Produces: `list_courses(academic_hub_root: str) -> list[str]`, `tags_path(academic_hub_root: str) -> str`, `load_tags(academic_hub_root: str) -> list[dict]`, `save_tags(academic_hub_root: str, tags: list[dict]) -> None`. `list_courses()`/`load_tags()`/`save_tags()` are consumed by Task 2/3 (`retag.py`); `list_courses()` also replaces `find_card_by_file_id()`'s inline shard-enumeration loop.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_index_card.py
from index_card import list_courses, load_tags, save_tags


class TestListCourses(unittest.TestCase):
    def test_lists_course_shards_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a"}])
            save_shard(tmp, "econ-101", [{"file_id": "b"}])
            save_courses(tmp, {"math-camp": {"course": "math-camp", "file_count": 1}})
            save_tags(tmp, [{"tag": "linear-algebra", "embedding": [1.0]}])
            self.assertEqual(sorted(list_courses(tmp)), ["econ-101", "math-camp"])

    def test_empty_when_no_index_dir_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list_courses(tmp), [])


class TestTagVocabularyIO(unittest.TestCase):
    def test_load_missing_tags_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_tags(tmp), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            tags = [{"tag": "linear-algebra", "embedding": [0.1, 0.2]}]
            save_tags(tmp, tags)
            self.assertEqual(load_tags(tmp), tags)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: FAIL — `ImportError: cannot import name 'list_courses'`

- [ ] **Step 3: Write the implementation**

Add to `marker-conversion/index_card.py`, near the other storage primitives (`courses_path`/`load_courses`/`save_courses`):

```python
def list_courses(academic_hub_root: str) -> list[str]:
    index_dir = _index_dir(academic_hub_root)
    if not os.path.isdir(index_dir):
        return []
    return [
        name[:-len(".json")]
        for name in sorted(os.listdir(index_dir))
        if name.endswith(".json") and name not in ("courses.json", "tags.json")
    ]


def tags_path(academic_hub_root: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), "tags.json")


def load_tags(academic_hub_root: str) -> list[dict]:
    path = tags_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tags(academic_hub_root: str, tags: list[dict]) -> None:
    path = tags_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=2, ensure_ascii=False)
```

Then refactor `find_card_by_file_id()` to reuse `list_courses()` instead of its own inline enumeration loop — from:
```python
def find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None:
    index_dir = _index_dir(academic_hub_root)
    if not os.path.isdir(index_dir):
        return None
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "tags.json"):
            continue
        course = name[:-len(".json")]
        for card in load_shard(academic_hub_root, course):
            if card.get("file_id") == file_id:
                return course, card
    return None
```
to:
```python
def find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None:
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("file_id") == file_id:
                return course, card
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_index_card -v`
Expected: PASS (39 tests — the existing 35 plus 4 new). Also confirms the `find_card_by_file_id()` refactor didn't break any of its existing tests.

- [ ] **Step 5: Commit**

```bash
git add marker-conversion/index_card.py marker-conversion/tests/test_index_card.py
git commit -m "feat(retag): add tags.json I/O and a shared course-listing helper"
```

---

### Task 2: Discovery — clustering, fuzzy tag matching, minting

**Files:**
- Create: `marker-conversion/retag.py`
- Test: `marker-conversion/tests/test_retag.py`

**Interfaces:**
- Consumes: `cosine_similarity`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONALITY`, `GENERATION_MODEL` (Task 1 / Plan 1's `index_card.py`).
- Produces: `build_clusters(embeddings: list[list[float]], threshold: float) -> list[list[int]]`, `fuzzy_match_tag(proposed: str, known_tags: list[dict]) -> dict | None`, `discover_tags(all_cards: list[tuple[str, dict]], known_tags: list[dict], client, threshold: float = CLUSTER_SIMILARITY_THRESHOLD, min_cluster_size: int = MIN_TAG_CLUSTER_SIZE) -> tuple[list[dict], dict]`. Consumed by Task 3's `retag()` orchestration.

- [ ] **Step 1: Install the new dependency**

```bash
cd marker-conversion && ./.venv/Scripts/python.exe -m pip install rapidfuzz
```

Confirm: `./.venv/Scripts/python.exe -c "import rapidfuzz; print(rapidfuzz.__version__)"` prints a version, no `ModuleNotFoundError`.

- [ ] **Step 2: Write the failing tests**

```python
# marker-conversion/tests/test_retag.py
import unittest
from unittest.mock import MagicMock

from retag import build_clusters, fuzzy_match_tag, discover_tags


class TestBuildClusters(unittest.TestCase):
    def test_two_disjoint_similar_groups_become_two_clusters(self):
        embeddings = [
            [1.0, 0.0], [0.99, 0.01], [0.98, 0.02],   # group A -- mutually similar
            [0.0, 1.0], [0.01, 0.99], [0.02, 0.98],   # group B -- mutually similar, unlike A
        ]
        clusters = build_clusters(embeddings, threshold=0.9)
        self.assertEqual(len(clusters), 2)
        sizes = sorted(len(c) for c in clusters)
        self.assertEqual(sizes, [3, 3])

    def test_dissimilar_singletons_stay_separate(self):
        embeddings = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]]
        clusters = build_clusters(embeddings, threshold=0.9)
        self.assertEqual(len(clusters), 3)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(build_clusters([], threshold=0.9), [])

    def test_transitive_bridge_merges_into_one_component(self):
        # A-B similar, B-C similar, A-C NOT similar -- still one component,
        # because connected components are transitive. This is exactly the
        # failure mode spec §5 motivates splitting discovery from
        # assignment over: a file bridging two topics merges their
        # clusters rather than getting two tags.
        embeddings = [[1.0, 0.0], [0.7, 0.7], [0.0, 1.0]]
        clusters = build_clusters(embeddings, threshold=0.5)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(sorted(clusters[0]), [0, 1, 2])


class TestFuzzyMatchTag(unittest.TestCase):
    def test_exact_match_reused(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("linear-algebra", known)
        self.assertEqual(result["tag"], "linear-algebra")

    def test_close_variant_reused(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("Linear Algebra", known)
        self.assertEqual(result["tag"], "linear-algebra")

    def test_unrelated_tag_not_matched(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("real-analysis", known)
        self.assertIsNone(result)

    def test_empty_vocabulary_never_matches(self):
        self.assertIsNone(fuzzy_match_tag("anything", []))


def _fake_naming_client(tag="linear-algebra", definition="Linear algebra: vector spaces and linear maps."):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = '{"tag": "%s", "definition": "%s"}' % (tag, definition)
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.5, 0.5]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestDiscoverTags(unittest.TestCase):
    def _cards(self, n, embedding):
        return [
            ("math-camp", {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}", "embedding": embedding})
            for i in range(n)
        ]

    def test_no_cards_mints_nothing(self):
        updated, stats = discover_tags([], [], client=MagicMock())
        self.assertEqual(updated, [])
        self.assertEqual(stats["clusters_found"], 0)
        self.assertEqual(stats["tags_minted"], 0)

    def test_cluster_below_min_size_mints_nothing(self):
        cards = self._cards(2, [1.0, 0.0])  # below default MIN_TAG_CLUSTER_SIZE=3
        client = _fake_naming_client()
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(updated, [])
        client.models.generate_content.assert_not_called()

    def test_qualifying_cluster_mints_a_new_tag_with_anchor_embedding(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_naming_client(tag="linear-algebra")
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["clusters_found"], 1)
        self.assertEqual(stats["tags_minted"], 1)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["tag"], "linear-algebra")
        self.assertEqual(updated[0]["embedding"], [0.5, 0.5])

    def test_qualifying_cluster_matching_existing_vocabulary_reuses_not_mints(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_naming_client(tag="Linear Algebra")  # fuzzy-matches existing
        known = [{"tag": "linear-algebra", "embedding": [0.9, 0.1]}]
        updated, stats = discover_tags(cards, known, client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(stats["tags_reused"], 1)
        self.assertEqual(updated, known)  # unchanged -- no new embedding call needed
        client.models.embed_content.assert_not_called()

    def test_two_disjoint_qualifying_clusters_mint_two_tags(self):
        cards_a = self._cards(3, [1.0, 0.0])
        cards_b = [
            ("math-camp", {"file_id": f"g{i}", "title": f"T{i}", "summary": f"S{i}", "embedding": [0.0, 1.0]})
            for i in range(3)
        ]
        client = MagicMock()
        responses = [
            '{"tag": "linear-algebra", "definition": "d1"}',
            '{"tag": "real-analysis", "definition": "d2"}',
        ]
        gen_response = MagicMock()
        gen_response.text = responses[0]
        embed_response = MagicMock()
        embedding = MagicMock()
        embedding.values = [0.5, 0.5]
        embed_response.embeddings = [embedding]

        def _side_effect(*args, **kwargs):
            gen_response.text = responses.pop(0)
            return gen_response

        client.models.generate_content.side_effect = _side_effect
        client.models.embed_content.return_value = embed_response

        updated, stats = discover_tags(cards_a + cards_b, [], client)
        self.assertEqual(stats["clusters_found"], 2)
        self.assertEqual(stats["tags_minted"], 2)
        self.assertEqual(sorted(t["tag"] for t in updated), ["linear-algebra", "real-analysis"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_retag -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'retag'`

- [ ] **Step 4: Write the implementation**

```python
# marker-conversion/retag.py
"""
retag.py
Corpus-wide, two-phase tag mining for the academic-hub source indexer
(spec §5): discovery (mint new tags, conservatively, via connected
components over the corpus's card embeddings) and assignment (apply any
tag in the vocabulary to any matching file, independently -- no
cluster-membership restriction, which is what makes this genuinely
many-to-many instead of one-tag-per-file; see spec §5 for why plain
connected-components alone actively merges clusters for any file that
bridges two subjects, rather than just under-tagging it).

Deliberately separate from index_card.py (per-file generation) and
index_search.py (query-time search/rebuild) -- tag mining looks at the
whole corpus at once, on its own explicit schedule, never per-file.
"""
from __future__ import annotations

import json

from rapidfuzz import fuzz
from google.genai import types

from gemini_utils import call_with_retries
from index_card import EMBEDDING_DIMENSIONALITY, EMBEDDING_MODEL, GENERATION_MODEL, cosine_similarity

CLUSTER_SIMILARITY_THRESHOLD = 0.78
MIN_TAG_CLUSTER_SIZE = 3
TAG_FUZZY_MATCH_THRESHOLD = 85  # rapidfuzz token_sort_ratio, 0-100


def build_clusters(embeddings: list[list[float]], threshold: float) -> list[list[int]]:
    """Connected components over a similarity graph -- index i adjacent to
    j if cosine_similarity(embeddings[i], embeddings[j]) > threshold."""
    n = len(embeddings)
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if cosine_similarity(embeddings[i], embeddings[j]) > threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)

    visited = [False] * n
    clusters: list[list[int]] = []
    for start in range(n):
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        clusters.append(component)
    return clusters


def fuzzy_match_tag(proposed: str, known_tags: list[dict]) -> dict | None:
    """Returns the existing tag entry whose name is closest to `proposed`
    (rapidfuzz token_sort_ratio), if that score is >= TAG_FUZZY_MATCH_THRESHOLD
    -- None means `proposed` is genuinely new, not a near-duplicate of
    something already in the vocabulary (spec §5.2)."""
    slug = proposed.strip().lower().replace(" ", "-")
    best_entry = None
    best_score = 0.0
    for entry in known_tags:
        score = fuzz.token_sort_ratio(slug, entry["tag"])
        if score > best_score:
            best_score = score
            best_entry = entry
    if best_entry is not None and best_score >= TAG_FUZZY_MATCH_THRESHOLD:
        return best_entry
    return None


_TAG_NAMING_PROMPT = """You are naming a topic tag shared by {n} related documents from a personal \
study corpus. Below is each document's title and summary.

Respond with ONLY a JSON object with exactly two keys:
"tag" (a short, kebab-case tag name, e.g. "linear-algebra" or "real-analysis"),
"definition" (one sentence defining what this tag means, for use as its own semantic anchor).

{documents}"""


def _name_cluster(cards: list[dict], client) -> tuple[str, str]:
    documents = "\n\n".join(f"- {c.get('title', '')}: {c.get('summary', '')}" for c in cards)
    prompt = _TAG_NAMING_PROMPT.format(n=len(cards), documents=documents)
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
    tag = str(parsed.get("tag") or "").strip().lower().replace(" ", "-")
    definition = str(parsed.get("definition") or "").strip()
    return tag, definition


def _embed_tag(tag: str, definition: str, client) -> list[float]:
    """The tag's semantic anchor -- an embedding of its own name+definition,
    not the mean of whichever cards happened to found it (spec §5.1): a
    stable meaning that doesn't drift with the founding cluster, and gets
    related terms (eigenvalues near eigenvectors) for free."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{tag}: {definition}",
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def discover_tags(
    all_cards: list[tuple[str, dict]], known_tags: list[dict], client,
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD, min_cluster_size: int = MIN_TAG_CLUSTER_SIZE,
) -> tuple[list[dict], dict]:
    """Phase 1 (spec §5.2): mints new tags from qualifying clusters,
    conservatively. Pure function -- does not read or write any files,
    does not mutate `known_tags` in place. Returns (updated_known_tags,
    stats); the caller (retag(), Task 3) is responsible for persisting."""
    stats = {"clusters_found": 0, "tags_minted": 0, "tags_reused": 0}
    if not all_cards:
        return list(known_tags), stats

    cards_only = [c for _, c in all_cards]
    embeddings = [c["embedding"] for c in cards_only]
    clusters = build_clusters(embeddings, threshold)

    updated_tags = list(known_tags)
    for cluster_indices in clusters:
        if len(cluster_indices) < min_cluster_size:
            continue
        stats["clusters_found"] += 1
        cluster_cards = [cards_only[i] for i in cluster_indices]

        proposed_tag, definition = _name_cluster(cluster_cards, client)
        existing = fuzzy_match_tag(proposed_tag, updated_tags)
        if existing is not None:
            stats["tags_reused"] += 1
            continue

        embedding = _embed_tag(proposed_tag, definition, client)
        updated_tags.append({"tag": proposed_tag, "embedding": embedding})
        stats["tags_minted"] += 1

    return updated_tags, stats
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_retag -v`
Expected: PASS (12 tests)

- [ ] **Step 6: Commit**

```bash
git add marker-conversion/retag.py marker-conversion/tests/test_retag.py
git commit -m "feat(retag): add discovery -- clustering, fuzzy tag matching, minting"
```

---

### Task 3: Assignment, `retag()` orchestration, and the CLI subcommand

**Files:**
- Modify: `marker-conversion/retag.py`
- Modify: `marker-conversion/index_search.py`
- Test: `marker-conversion/tests/test_retag.py`

**Interfaces:**
- Consumes: `list_courses`, `load_shard`, `save_shard`, `load_tags`, `save_tags`, `recompute_course_entry` (Task 1); `discover_tags` (Task 2).
- Produces: `assign_tags(academic_hub_root: str, all_cards: list[tuple[str, dict]], known_tags: list[dict], threshold: float = TAG_ASSIGNMENT_THRESHOLD, dry_run: bool = False) -> dict`, `retag(academic_hub_root: str, client, dry_run: bool = False, cluster_threshold: float = CLUSTER_SIMILARITY_THRESHOLD, assignment_threshold: float = TAG_ASSIGNMENT_THRESHOLD, min_cluster_size: int = MIN_TAG_CLUSTER_SIZE) -> dict`. `retag()` is consumed by the CLI (this task) and is the function a future RAG model or any other caller would import directly, matching Plan 1's `search()`/`rebuild()` convention.

- [ ] **Step 1: Write the failing tests**

```python
# append to marker-conversion/tests/test_retag.py
import tempfile

from index_card import load_shard, load_tags, save_shard, save_tags
from retag import assign_tags, retag


class TestAssignTags(unittest.TestCase):
    def test_card_matching_one_tag_gets_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["linear-algebra"])

    def test_card_matching_multiple_tags_gets_all_of_them(self):
        # The actual fix for one-tag-per-file: a card similar to two
        # unrelated tag anchors gets both, with no cluster-membership
        # restriction at all (spec §5.3).
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [0.7, 0.7], "tags": []}])
            known = [
                {"tag": "linear-algebra", "embedding": [1.0, 0.0]},
                {"tag": "probability", "embedding": [0.0, 1.0]},
            ]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [0.7, 0.7]})]
            assign_tags(tmp, all_cards, known, threshold=0.5)
            self.assertEqual(
                sorted(load_shard(tmp, "math-camp")[0]["tags"]), ["linear-algebra", "probability"],
            )

    def test_card_matching_no_tags_gets_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": ["stale"]}])
            known = [{"tag": "real-analysis", "embedding": [0.0, 1.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])

    def test_tags_are_replaced_not_appended(self):
        # spec §5.3: a card's tags list is fully replaced each run, not
        # accumulated -- this is what makes tags non-permanent.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "tags": ["old-unrelated-tag"]},
            ])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["linear-algebra"])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            stats = assign_tags(tmp, all_cards, known, dry_run=True)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])  # unchanged
            self.assertIn("preview", stats)
            self.assertEqual(stats["preview"]["math-camp"]["a"], ["linear-algebra"])


class TestRetag(unittest.TestCase):
    def test_end_to_end_mints_and_assigns(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [
                {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}",
                 "embedding": [1.0, 0.0], "tags": []}
                for i in range(3)
            ]
            save_shard(tmp, "math-camp", cards)
            client = _fake_naming_client(tag="linear-algebra")

            stats = retag(tmp, client)

            self.assertEqual(stats["tags_minted"], 1)
            self.assertEqual(stats["cards_tagged"], 3)
            tags_on_disk = load_tags(tmp)
            self.assertEqual(len(tags_on_disk), 1)
            self.assertEqual(tags_on_disk[0]["tag"], "linear-algebra")
            for card in load_shard(tmp, "math-camp"):
                self.assertEqual(card["tags"], ["linear-algebra"])

    def test_dry_run_mints_nothing_persisted_and_writes_no_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [
                {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}",
                 "embedding": [1.0, 0.0], "tags": []}
                for i in range(3)
            ]
            save_shard(tmp, "math-camp", cards)
            client = _fake_naming_client(tag="linear-algebra")

            stats = retag(tmp, client, dry_run=True)

            self.assertEqual(stats["tags_minted"], 1)  # discovery still ran/reported
            self.assertEqual(load_tags(tmp), [])        # but nothing persisted
            for card in load_shard(tmp, "math-camp"):
                self.assertEqual(card["tags"], [])       # cards untouched
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd marker-conversion && python -m unittest tests.test_retag -v`
Expected: FAIL — `ImportError: cannot import name 'assign_tags'`

- [ ] **Step 3: Write the implementation**

Add to `marker-conversion/retag.py` (update its `index_card` import line first):

```python
from index_card import (
    EMBEDDING_DIMENSIONALITY,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    cosine_similarity,
    list_courses,
    load_shard,
    load_tags,
    recompute_course_entry,
    save_shard,
    save_tags,
)

TAG_ASSIGNMENT_THRESHOLD = 0.78
```

then:

```python
def assign_tags(
    academic_hub_root: str, all_cards: list[tuple[str, dict]], known_tags: list[dict],
    threshold: float = TAG_ASSIGNMENT_THRESHOLD, dry_run: bool = False,
) -> dict:
    """Phase 2 (spec §5.3): for every card, independently checks every tag
    anchor and replaces the card's tags list with this run's fresh
    result. Many-to-many by construction -- no cluster-membership
    restriction at all, which is the actual fix for one-tag-per-file."""
    stats = {"cards_tagged": 0, "tag_assignments": 0}
    by_course: dict[str, dict[str, list[str]]] = {}

    for course, card in all_cards:
        matched = [
            entry["tag"] for entry in known_tags
            if cosine_similarity(card["embedding"], entry["embedding"]) > threshold
        ]
        if matched:
            stats["cards_tagged"] += 1
            stats["tag_assignments"] += len(matched)
        by_course.setdefault(course, {})[card["file_id"]] = matched

    if dry_run:
        return stats | {"preview": by_course}

    for course, file_tag_map in by_course.items():
        cards = load_shard(academic_hub_root, course)
        changed = False
        for card in cards:
            fid = card.get("file_id")
            if fid in file_tag_map and card.get("tags") != file_tag_map[fid]:
                card["tags"] = file_tag_map[fid]
                changed = True
        if changed:
            save_shard(academic_hub_root, course, cards)
            recompute_course_entry(academic_hub_root, course)

    return stats


def _load_all_cards(academic_hub_root: str) -> list[tuple[str, dict]]:
    """(course, card) for every non-orphaned, embedded card across all
    shards -- what both discovery and assignment operate over."""
    result = []
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                continue
            result.append((course, card))
    return result


def retag(
    academic_hub_root: str, client, dry_run: bool = False,
    cluster_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
    assignment_threshold: float = TAG_ASSIGNMENT_THRESHOLD,
    min_cluster_size: int = MIN_TAG_CLUSTER_SIZE,
) -> dict:
    all_cards = _load_all_cards(academic_hub_root)
    known_tags = load_tags(academic_hub_root)

    updated_tags, discovery_stats = discover_tags(
        all_cards, known_tags, client, threshold=cluster_threshold, min_cluster_size=min_cluster_size,
    )
    assignment_stats = assign_tags(
        academic_hub_root, all_cards, updated_tags, threshold=assignment_threshold, dry_run=dry_run,
    )

    if not dry_run:
        save_tags(academic_hub_root, updated_tags)

    return discovery_stats | assignment_stats
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd marker-conversion && python -m unittest tests.test_retag -v`
Expected: PASS (19 tests)

- [ ] **Step 5: Wire up the CLI subcommand**

In `marker-conversion/index_search.py`, add the import:

```python
from retag import retag
```

(no alias needed — `args.command == "retag"` compares a string against `main()`'s parsed CLI argument, which doesn't collide with a local name `retag` bound to the imported function; the same pattern `rebuild`/`search` already use as both a function name and a subcommand string.)

Add to `build_arg_parser()`, alongside the existing `query`/`rebuild` subparsers:

```python
    retag_p = subparsers.add_parser("retag", help="Mine and apply tags across the whole corpus.")
    retag_p.add_argument("--dry-run", action="store_true")
```

Add to `main()`'s branching, alongside the existing `query`/`rebuild` handling:

```python
    elif args.command == "retag":
        stats = retag(args.academic_hub, client, dry_run=args.dry_run)
        print(stats)
```

- [ ] **Step 6: Add CLI parsing tests**

```python
# append to marker-conversion/tests/test_index_search.py
class TestRetagCLIArgParsing(unittest.TestCase):
    def test_retag_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["retag"])
        self.assertEqual(args.command, "retag")
        self.assertFalse(args.dry_run)

    def test_retag_subcommand_with_dry_run(self):
        args = build_arg_parser().parse_args(["retag", "--dry-run"])
        self.assertTrue(args.dry_run)
```

- [ ] **Step 7: Run the full test suite**

Run: `cd marker-conversion && python -m unittest discover -s tests -v`
Expected: PASS (all tests — Plan 1's 273 plus Task 1-3's new ones)

- [ ] **Step 8: Smoke-test the CLI**

Run: `cd marker-conversion && ./.venv/Scripts/python.exe index_search.py retag --help`
Confirm: prints usage with `--dry-run`, no errors.

- [ ] **Step 9: Commit**

```bash
git add marker-conversion/retag.py marker-conversion/index_search.py marker-conversion/tests/test_retag.py marker-conversion/tests/test_index_search.py
git commit -m "feat(retag): add many-to-many assignment, retag() orchestration, and CLI subcommand"
```

---

## Self-Review Notes

- **Spec coverage:** §3.3 (`{tag, embedding}` vocabulary) → Task 1. §5.1 (tag anchor embedding) → Task 2's `_embed_tag`. §5.2 (discovery: clustering, min size, fuzzy match, minting) → Task 2. §5.3 (assignment: many-to-many, replace-not-append) → Task 3. §8 (`retag` CLI, `--dry-run`) → Task 3.
- **Type consistency checked:** `discover_tags()`'s return type (`tuple[list[dict], dict]`) matches how `retag()` (Task 3) unpacks it. `assign_tags()`'s `all_cards`/`known_tags` parameter shapes match exactly what `discover_tags()` consumes and produces, so `retag()` can pass `updated_tags` straight through. `TAG_ASSIGNMENT_THRESHOLD` is defined once in `retag.py` (Task 3) and consumed by both `assign_tags()`'s default and `retag()`'s default, not duplicated. `list_courses()` (Task 1) is used identically by `find_card_by_file_id()` (Plan 1, refactored) and `retag.py`'s `_load_all_cards()` (Task 3) — one enumeration rule, not two.
- **The core design fix is directly tested:** `test_card_matching_multiple_tags_gets_all_of_them` (Task 3) and `test_transitive_bridge_merges_into_one_component` (Task 2) together demonstrate exactly the problem (connected components merge bridging files into one cluster) and its fix (assignment checks every tag independently, unrestricted by cluster membership) — this is the single most important behavior in this plan, not left as an assumption.
- **No placeholders:** every step has runnable code. `CLUSTER_SIMILARITY_THRESHOLD`/`TAG_ASSIGNMENT_THRESHOLD`/`MIN_TAG_CLUSTER_SIZE`/`TAG_FUZZY_MATCH_THRESHOLD` are explicitly flagged (Global Constraints) as starting values expected to need real-corpus tuning, not asserted as correct.
