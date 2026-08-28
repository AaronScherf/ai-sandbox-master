# Source Indexer — Design Spec

Date: 2026-08-27 (revised 2026-08-28)
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
- Tags (`topics`) are assigned with corpus-wide awareness, not guessed per
  file in isolation — `tags: []` has sat permanently empty in
  `transcribe_notes.py` specifically because per-file tagging without that
  awareness was rejected earlier; §5 is what it was left empty for.
- Lay groundwork (topic vocabulary, embeddings) reusable by the eventual
  RAG model and by future cross-corpus "web of knowledge" topic queries.

**Non-goals**
- No vector DB / ANN index (FAISS, Chroma, ...) — brute-force cosine
  similarity over in-memory NumPy arrays is sufficient at the target scale
  (see §6) and this can be swapped in later without touching the schema.
- No *persisted* graph structure or interactive graph traversal/query UI.
  §5 uses a similarity graph as an internal mechanism to decide which tags
  to mint, but that graph is rebuilt from scratch each `retag` run and
  discarded immediately after — only its output (tags on cards) persists.
  Querying the graph itself, or any richer topic-relationship browsing, is
  future work (§9).
- No query-time LLM reasoning — matching (§6) is embeddings + cosine only.
- No chunk-level (paragraph/section) indexing — this indexer resolves to
  whole files; a future RAG layer does its own chunking of the files this
  indexer selects.
- No automatic reconciliation on file move — reorganizing a course folder
  is caught on the next explicit `rebuild` (§7), not instantly.

## 2. Storage layout

```
academic-hub/.index/
  topics.json          # canonical topic vocabulary (flat list, grown only by retag — see §5)
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

`path` and `source_pdf_path` are both relative to `academic-hub/` (not to
the `.index/` folder itself), so they're usable directly by anything that
treats `academic-hub/` as the corpus root:

```json
{
  "file_id": "9f2a6c1d4e8b0a3f",
  "path": "academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler_Linear_Algebra_Done_Right_2026/Axler_Linear_Algebra_Done_Right_2026.md",
  "source_pdf_path": "academic_resources/math-camp/textbooks-and-papers/Linear Algebra Done Right (4th edition) Axler.pdf",
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

- `file_id` is the true identity of a card — a truncated SHA-256 hash of
  the **original source PDF's bytes**, not derived from `path` at all. See
  §4.3: this is what makes the index robust to renaming/moving/nesting
  course folders, since `path` and `course` are free to change on an
  existing card without that card being treated as a new file. PDFs are
  confirmed to stay on disk alongside their processed outputs (checked
  directly in `academic_resources/math-camp/textbooks-and-papers/` and
  `academic_notes/math-camp/ta_notes/`), so this hash can be recomputed
  identically at any future rebuild, not just at first generation.
- `source_pdf_path` is provenance back to the original document — cheap to
  capture since the hook already has this path in hand to compute
  `file_id`. Lets a downstream consumer (human or RAG layer) jump to the
  original PDF page when a markdown transcription looks garbled or an
  image/diagram didn't survive conversion well. Never indexed/embedded
  itself — purely a backreference.
- `doc_type` is one of: `textbook`, `problem_set`, `ta_notes`,
  `handwritten_notes`, or the raw `folder_category` string if it doesn't map
  to a known type — never fails closed.
- `topics` starts as `[]` at card generation and is populated (and later
  possibly changed) **only** by the corpus-wide `retag` pass — see §5. It
  is never guessed by the per-file generation call in §4.
- `needs_indexing: true` marks a card whose generation failed partway
  (LLM/embedding call error) — see §7 for how this gets swept up.
- `source_updated_at` is the source `.md`'s mtime at card-generation time,
  used by the rebuild pass to detect files that changed since their card
  was last generated.
- `orphaned: true` (omitted otherwise) marks a card whose `file_id` a
  rebuild sweep couldn't match to any PDF on disk — see §4.3/§7. Excluded
  from search results and from its course's centroid/topic-count rollup,
  and from tag mining, while flagged.

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
card is added/updated in that course, and again after every `retag` run
(§5), keeping `courses.json` always in sync without a separate generation
step. Until the first `retag` run, `predominant_topics` is simply empty for
every course, since no card has any `topics` yet.

### 3.3 Topic vocabulary (`topics.json`)

Flat list of canonical topic strings (kebab-case, e.g. `linear-algebra`,
`eigenvalues`, `real-analysis`). Entries are added **only** by the `retag`
pass (§5) — never proposed per-file — which is what keeps this list free of
near-duplicate fragments (`linear-algebra` vs `Linear Algebra` vs
`lin-alg`) and keeps `topics` usable as graph edges (§9).

## 4. Card generation

New shared module, `marker-conversion/index_card.py`, called from both
pipelines rather than duplicating LLM-prompt logic in each:

```python
def generate_index_card(
    path: str, source_pdf_path: str, course: str, doc_type: str,
    content_sample: str,  # what the LLM sees — see below
    client,  # from gemini_utils.get_gemini_client()
) -> dict: ...

def write_card(course: str, card: dict) -> None: ...   # updates <course>.json + courses.json
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
structured JSON: `{title, doc_type, summary}` — **no `topics`**, that's
§5's job, deliberately kept separate so a single-document call is never
what decides a file's tags. The `title+summary` text is embedded with one
embedding call (same client, Gemini's embedding endpoint) to produce
`embedding`. The card is written with `topics: []`.

### 4.1 Hook insertion points

- `transcribe_notes.py`, in `process_pdf()`: the frontmatter dict currently
  finalized with `"tags": []` (e.g. around the block at line 844 and its
  siblings near 904/975/1032) is a separate, optional follow-up (§9) —
  not touched by this indexer directly. The indexer hook goes immediately
  after that frontmatter/markdown is finalized and written to disk: call
  `generate_index_card()` with the finished markdown as `content_sample`,
  then `write_card()`.
- `convert_textbook.py`, in `process_one_pdf()`: immediately after
  `master_metadata` is finalized and `_metadata.json` is written (~line
  881-888), call `generate_index_card()` with `master_metadata`'s
  title/author/year plus the chapter list, then `write_card()`.

### 4.2 Failure isolation

A card-generation failure (LLM error, embedding error, quota) must never
block, fail, or corrupt the actual conversion/transcription output — it's
caught, logged as a warning, and a minimal card is written instead: 
`file_id`/`path`/`source_pdf_path`/`course`/`doc_type` (all computed or
known before the LLM call happens, so unaffected by its failure), plus
`needs_indexing: true`, no `summary`/`embedding`. Keeping `file_id` on the
minimal card matters — it's what lets §4.3's reconciliation find and
complete this exact card on a later rebuild, rather than mistaking it for
a new file each time.

### 4.3 Reconciliation by `file_id` (robustness to folder reorganization)

Neither the hook nor the rebuild pass treats `path` as a stable identifier.
Before generating anything, both compute `file_id` from the source PDF's
bytes and look it up **across every course shard**, not just the shard for
the currently-derived `course`:

- **Match in the same course's shard, `path`/`source_pdf_path` unchanged:**
  nothing to do.
- **Match in the same course's shard, `path`/`source_pdf_path` changed:**
  the file moved within the same course (e.g. reorganized into a new
  subfolder) — update both fields plus `source_updated_at` on the existing
  card in place. No LLM or embedding call.
- **Match in a different course's shard:** the file moved to a different
  course (e.g. a folder rename that changes what `derive_folder_category`-
  style logic reads as the course, or a folder nested under a different
  course). Move the card from the old course's shard to the new one, update
  `path`/`source_pdf_path`/`course`, and recompute `courses.json`
  centroid/topic-counts for *both* the old and new course (still purely
  mechanical — no LLM or embedding call, since `summary`/`topics`/
  `embedding` don't change).
- **No match anywhere:** genuinely new content — generate a fresh card as
  in §4 (this is the only path that costs an LLM + embedding call).

This means a course-folder rename or nesting change costs exactly one
rebuild pass worth of PDF hashing (cheap — no network calls) to reconcile
every affected card in place, not a full regeneration of the corpus.

## 5. Tag mining (`retag` — corpus-wide, graph-based)

This is what `tags: []` was always deferred for: tags are assigned only
with visibility across the *whole* corpus, not guessed per file at
generation time (§4). Run via `index_search.py retag` (§8) — an explicit,
separate, occasionally-run pass, not part of every `rebuild`, since it's
corpus-wide rather than per-course/per-file.

**Algorithm**, run fresh each time (nothing about the graph itself
persists — only its output, tags on cards, does):

1. Load every non-orphaned file card's `embedding` across all course
   shards.
2. Build a similarity graph: an edge between two files if their cosine
   similarity exceeds a threshold `τ` (starting default `0.78` — a
   tunable constant expected to need empirical adjustment against the
   real corpus, same as `_CAUSAL_ZSCORE_THRESHOLD` elsewhere in this
   project; `retag` logs the resulting cluster sizes/composition so this
   can be sanity-checked rather than trusted blindly).
3. Take **connected components** as candidate tag clusters. A component
   only becomes a tag if it has at least `MIN_TAG_CLUSTER_SIZE` (starting
   default `3`) member files — this is the direct mechanism for "singleton
   tags aren't useful": a pair of similar files stays untagged until a
   third, similar enough file joins them.
4. For each qualifying cluster, **one LLM call** (not one per file) takes
   the member files' titles + summaries and proposes a canonical tag name,
   fuzzy-matched against `topics.json` (merging into an existing tag where
   appropriate, same normalization intent as before, just moved here)
   before being added as new.
5. That tag is written to **every file card in the cluster** — including
   cards that existed long before this run and never had it. This is the
   "back-apply" behavior: adding five new files about topology either
   forms a new qualifying cluster on its own, or pushes a previously
   too-small cluster of older, always-similar files over the threshold —
   either way, the tag gets minted now and applied to the old files too,
   not just the new ones.
6. `courses.json` `predominant_topics` is recomputed for every affected
   course afterward (§3.2's free rollup).

**Tags are not permanent once assigned.** Because the graph is rebuilt
from scratch each run, a later `retag` can drop a tag from a file if the
corpus's structure has shifted enough that it's no longer part of a
qualifying cluster — tags track current corpus structure, not a one-time
decision.

`retag --dry-run` prints the clusters and proposed tag names/back-apply
lists without writing anything — lets `τ` and `MIN_TAG_CLUSTER_SIZE` be
sanity-checked against the real corpus before trusting a run that mutates
every course shard at once.

## 6. Search algorithm (two-stage)

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

## 7. Backfill / rebuild

Because the 39 files that exist today predate this system, and because
hook failures leave `needs_indexing: true` stragglers, a rebuild pass walks
`academic-hub/` and, for every source PDF found, runs the §4.3 reconciliation
(hash → look up `file_id` across all shards → update-in-place, move-between-
shards, or generate fresh) — the same generation/reconciliation logic used
by the hook, invoked in bulk rather than per-file. This is also what makes
the index robust to reorganization end-to-end: renaming, moving, or nesting
a course folder doesn't break search or leave dead paths behind, it just
requires one rebuild pass to catch up. `rebuild` does not run `retag` (§5)
itself — reconciliation and tag mining are separate, explicit passes.

**Orphan handling:** a card whose `file_id` isn't matched to any PDF found
during a rebuild sweep (the source PDF was deleted, or its content was
replaced — a content change produces a different hash, which is correctly
treated as a new file rather than silently reusing the old card) is flagged
`orphaned: true` rather than deleted immediately. `rebuild --prune` removes
confirmed orphans (and rolls their old course's centroid/topic-counts back)
as an explicit, separate action — nothing disappears from the index as a
side effect of an ordinary rebuild.

## 8. CLI

`marker-conversion/index_search.py` — a thin CLI wrapper around the
importable `search()` / `rebuild()` / `retag()` functions (not CLI-only
logic), so a future RAG model can import `search()` directly:

```
python index_search.py query "teach me about linear algebra" [--course math-camp] [--top-k 5]
python index_search.py rebuild [--course math-camp] [--force] [--prune]
python index_search.py retag [--dry-run]
```

`query` prints ranked `path, course, doc_type, score, summary` rows.
`rebuild` runs §7's backfill/reconciliation pass, `--force` regenerating
even cards that look up to date, `--prune` additionally clearing confirmed
orphans. `retag` runs §5's corpus-wide tag mining pass, `--dry-run`
previewing without writing.

## 9. Future extensions (explicitly not built now)

- **Richer topic-graph browsing.** §5 uses a similarity graph purely as an
  internal, throwaway mechanism to decide which tags to mint — it's never
  persisted or exposed for querying. A future layer could persist
  co-occurrence structure (e.g. "eigenvalues" and "characteristic
  polynomial" co-occurring across sources even outside the same course
  folder) for actual graph browsing/traversal, directly on top of the
  normalized `topics` this spec already produces — no schema change
  required, just a new read path.
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
  field from the card's (post-`retag`) `topics` list, so the human-readable
  file itself carries the same tags as its index card. Not required for
  search to work (the card is the system of record), so left as a
  follow-up — and only sensible to build after `retag` exists, since
  before that the field would still just be empty.
