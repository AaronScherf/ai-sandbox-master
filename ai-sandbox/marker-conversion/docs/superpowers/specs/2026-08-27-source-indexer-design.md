# Source Indexer — Design Spec

Date: 2026-08-27
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

`academic-hub` holds markdown converted from math (and other course) PDFs by
two pipelines in this folder: `transcribe_notes.py` (notes, problem sets, TA
notes, handwritten notes) and `convert_textbook.py` (full textbooks, via
marker). Both already emit some metadata (YAML frontmatter with an always-
empty `tags: []` for the notes pipeline; a sparse `_metadata.json` sidecar
for the textbook pipeline), but nothing today lets a query like "teach me
about linear algebra" cheaply identify which of the (currently 39, expected
to grow into the hundreds) files are relevant.

This spec designs a **source indexer**: a component that, given a natural-
language query, returns a ranked list of relevant source files with a short
reason each — intended as ground-truth source selection for a future RAG
model, not the RAG model itself. Generating summaries, problem sets, or
tutoring content from the selected sources is explicitly out of scope here.

**Goals**
- Given a query, return ranked `(path, course, doc_type, score, reason)`
  results, scanning all courses by default, scopable to one course.
- Stay cheap and fast as the corpus grows into the hundreds of files across
  many courses — query cost must not scale linearly with corpus size in a
  way that makes it slow or expensive.
- Index cards regenerate automatically as new files are produced by either
  pipeline (no separate manual step to remember).
- Lay groundwork (topic vocabulary, embeddings) reusable by the eventual
  RAG model and by future cross-corpus "web of knowledge" topic queries,
  without building either of those now.

**Non-goals**
- No vector DB / ANN index (FAISS, Chroma, ...) — brute-force cosine
  similarity over in-memory NumPy arrays is sufficient at the target scale
  (see §5) and this can be swapped in later without touching the schema.
- No knowledge-graph traversal UI or logic — only the topic normalization
  that would make one possible later.
- No query-time LLM reasoning — matching is embeddings + cosine only.
- No chunk-level (paragraph/section) indexing — this indexer resolves to
  whole files; a future RAG layer does its own chunking of the files this
  indexer selects.

## 2. Storage layout

```
academic-hub/.index/
  topics.json          # canonical topic vocabulary (flat list, grows incrementally)
  courses.json          # one entry per course (see §3.2)
  math-camp.json         # one entry per file in that course (see §3.1)
  econ-101.json
  env-101.json
  ...
```

One shard per course, not one global file and not one file per source
directory — matches how material actually gets added (one course, one file,
at a time) and keeps hook-triggered updates cheap: writing a new card
touches exactly one course shard plus `courses.json`, never a full-corpus
rewrite. `course` is derived the same way `derive_folder_category()` already
derives `folder_category` in `transcribe_notes.py`: the relevant path
segment under `academic_notes/<course>/...` or
`academic_resources/<course>/...`.

Shards live in a dedicated `.index/` folder, not inside the content
directories — keeps them out of the way of the human-facing corpus, but
still plain JSON, git-trackable, and directly greppable/readable without
running any search code.

## 3. Data model

### 3.1 File-level index card (one entry per source file, in its course shard)

`path` is relative to `academic-hub/` (not to the `.index/` folder itself),
so it's usable directly by anything that treats `academic-hub/` as the
corpus root:

```json
{
  "path": "academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler_Linear_Algebra_Done_Right_2026/Axler_Linear_Algebra_Done_Right_2026.md",
  "course": "math-camp",
  "doc_type": "textbook",
  "title": "Linear Algebra Done Right",
  "summary": "Undergraduate linear algebra textbook covering vector spaces, linear maps, eigenvalues, inner product spaces, and spectral theory, with an emphasis on basis-free proofs.",
  "topics": ["linear-algebra", "vector-spaces", "eigenvalues", "inner-product-spaces"],
  "embedding": [0.0123, -0.0456, ...],
  "embedding_model": "<gemini embedding model id, pinned>",
  "source_updated_at": "2026-08-27T00:00:00Z",
  "needs_indexing": false
}
```

- `doc_type` is one of: `textbook`, `problem_set`, `ta_notes`,
  `handwritten_notes`, or the raw `folder_category` string if it doesn't map
  to a known type — never fails closed.
- `topics` are drawn from `topics.json` (see §4); always normalized, never
  raw free text.
- `needs_indexing: true` marks a card whose generation failed partway
  (LLM/embedding call error) — see §6 for how this gets swept up.
- `source_updated_at` is the source `.md`'s mtime at card-generation time,
  used by the rebuild pass to detect files that changed since their card
  was last generated.

### 3.2 Course-level entry (one per course, in `courses.json`)

```json
{
  "course": "math-camp",
  "title": "Math Camp",
  "predominant_topics": ["linear-algebra", "real-analysis", "probability", "optimization"],
  "file_count": 14,
  "embedding": [0.0089, -0.0321, ...]
}
```

Computed **entirely from that course's own file-level cards, with no
additional LLM or embedding call**:
- `embedding` = the centroid (elementwise mean) of every file card's
  `embedding` in that course's shard.
- `predominant_topics` = the most frequent entries in the union of those
  cards' `topics`.

This is a free byproduct of writing any file card — recomputed each time a
card is added/updated in that course, keeping `courses.json` always in sync
without a separate generation step.

### 3.3 Topic vocabulary (`topics.json`)

Flat list of canonical topic strings (kebab-case, e.g. `linear-algebra`,
`eigenvalues`, `real-analysis`). When card generation proposes a topic
string, it's fuzzy-matched (e.g. via `rapidfuzz`, a new small dependency)
against this list first; only added as new if nothing sufficiently close
exists. This is what keeps `topics` usable as graph edges later (§7)
instead of fragmenting into near-duplicate strings.

## 4. Card generation

New shared module, `marker-conversion/index_card.py`, called from both
pipelines rather than duplicating LLM-prompt and normalization logic
in each:

```python
def generate_index_card(
    path: str, course: str, doc_type: str,
    content_sample: str,  # what the LLM sees — see below
    client,  # from gemini_utils.get_gemini_client()
) -> dict: ...

def write_card(course: str, card: dict) -> None: ...   # updates <course>.json + courses.json
def normalize_topics(proposed: list[str]) -> list[str]: ...  # match/extend topics.json
```

**`content_sample` differs by caller, deliberately kept cheap regardless of
source length:**
- Notes pipeline (`transcribe_notes.py`): the finished markdown itself —
  these documents are short (tens of pages at most), so passing the whole
  thing is cheap.
- Textbook pipeline (`convert_textbook.py`): **only** the title/author/year
  already in `master_metadata` plus the chapter/TOC entries
  `chapter_index.py` extracts during `compute_chunk_boundaries()` — never
  the full text. A 900-page book doesn't need to be read for a summary; an
  LLM's own knowledge of a named textbook plus its real chapter list is
  enough, and this keeps card-generation cost roughly constant regardless
  of book length.

One `client.models.generate_content()` call (reusing
`gemini_utils.get_gemini_client()` / `call_with_retries()`) returns
structured JSON: `{title, doc_type, summary, topics}`. `topics` then goes
through `normalize_topics()`. The `title+summary+topics` text is embedded
with one embedding call (same client, Gemini's embedding endpoint) to
produce `embedding`.

### 4.1 Hook insertion points

- `transcribe_notes.py`, in `process_pdf()`: the frontmatter dict currently
  finalized with `"tags": []` (e.g. around the block at line 844 and its
  siblings near 904/975/1032) is where the real `topics` list eventually
  wants to live too — but that's a **separate, optional follow-up**
  (backfilling `tags` in the frontmatter itself is not required for the
  indexer to work, since the card is the system of record for search). The
  indexer hook itself goes immediately after that frontmatter/markdown is
  finalized and written to disk: call `generate_index_card()` with the
  finished markdown as `content_sample`, then `write_card()`.
- `convert_textbook.py`, in `process_one_pdf()`: immediately after
  `master_metadata` is finalized and `_metadata.json` is written (~line
  881-888), call `generate_index_card()` with `master_metadata`'s
  title/author/year plus the chapter list, then `write_card()`.

### 4.2 Failure isolation

A card-generation failure (LLM error, embedding error, quota) must never
block, fail, or corrupt the actual conversion/transcription output — it's
caught, logged as a warning, and a minimal card with `needs_indexing: true`
(path/course/doc_type only, no summary/topics/embedding) is written instead,
so the file is at least known to exist and picked up by the rebuild pass.

## 5. Search algorithm (two-stage)

```python
def search(query: str, course: str | None = None, top_k: int = 5) -> list[SearchResult]: ...
```

1. Embed `query` once (same embedding model as card generation — the model
   id is pinned and stored per-card in `embedding_model` so a future model
   change can be detected rather than silently comparing incompatible
   vectors).
2. **Course filter** (skipped if `course` is passed explicitly): cosine
   similarity between the query embedding and every entry in
   `courses.json` (a handful of entries — trivial cost). Select courses
   above a similarity threshold (or top-N courses), not a hardcoded
   include/exclude list — this is what makes "linear algebra" score a
   Spanish course near zero and pull in math-camp (and any other course
   that genuinely shares topics, e.g. econometrics) automatically.
3. **File filter**: load only the selected courses' shards, brute-force
   cosine similarity against every file card's `embedding`, return the
   top `top_k` as `SearchResult(path, course, doc_type, score, reason)`
   where `reason` is simply that card's stored `summary` — no query-time
   LLM call needed to explain a match.

No persistent ANN/vector-DB structure — the scan itself is the query. At
the target scale (hundreds of files, low thousands of vectors) a NumPy
brute-force scan is single-digit milliseconds. If the corpus ever reaches
tens of thousands of files, the upgrade path is swapping the scan for an
ANN library (e.g. FAISS) without changing the card schema, shard format, or
the two-stage structure — not needed now (YAGNI).

## 6. Backfill / rebuild

Because the 39 files that exist today predate this system, and because
hook failures leave `needs_indexing: true` stragglers, a rebuild pass walks
`academic-hub/` and calls the same `generate_index_card()` /
`write_card()` path in bulk for any file that has no card, has
`needs_indexing: true`, or whose source `.md` mtime is newer than its
card's `source_updated_at`. This is not a second mechanism competing with
the hook — it's the same generation logic, invoked in bulk, used for
initial backfill and for recovering from any failed hook calls.

## 7. CLI

`marker-conversion/index_search.py` — a thin CLI wrapper around the
importable `search()` / rebuild functions (not CLI-only logic), so a
future RAG model can import `search()` directly:

```
python index_search.py query "teach me about linear algebra" [--course math-camp] [--top-k 5]
python index_search.py rebuild [--course math-camp] [--force]
```

`query` prints ranked `path, course, doc_type, score, summary` rows.
`rebuild` runs §6's backfill pass, `--force` regenerating even cards that
look up to date.

## 8. Future extensions (explicitly not built now)

- **Cross-corpus topic graph.** Because `topics` are normalized against a
  shared vocabulary (§3.3) rather than left as free text, a `topic → [file
  cards]` inverted index and topic co-occurrence graph (e.g. "eigenvalues"
  and "characteristic polynomial" co-occurring across sources even outside
  the same course folder) are cheap to build later directly from the
  existing shards — no schema change required.
- **Chunk-level embeddings for the actual RAG retrieval step.** The
  embedding infrastructure built here (client setup, embedding calls,
  cosine similarity search) is directly reusable for embedding
  paragraph/section-level chunks once the RAG model itself is being built —
  this indexer's file-level embeddings are not throwaway work relative to
  that.
- **Retrieval-conditioned scoring for the notes post-processing precision
  problem.** Noted previously (see project memory
  `project_notes_postprocessing_paused`) as a specific interest once a
  retrieval layer exists over the combined corpus: scoring a flagged
  transcription candidate against retrieved, validated-similar passages
  rather than broad domain fine-tuning. This indexer is a prerequisite for
  that direction, not a part of this spec's scope.
- Optional: backfilling the notes pipeline's own frontmatter `tags: []`
  field from the normalized `topics` list, so the human-readable file
  itself carries the same tags as its index card. Not required for search
  to work (the card is the system of record), so left as a follow-up.
