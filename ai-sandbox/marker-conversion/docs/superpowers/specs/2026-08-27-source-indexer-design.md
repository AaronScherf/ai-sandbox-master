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
- Carry enough per-file metadata (§3.1: `level`, `has_solutions`,
  `page_count`) that a downstream RAG model can do more than pick sources
  by topic — e.g. avoid sourcing practice problems from a file that
  already has solutions inline, or sequence a study plan by difficulty —
  without needing a second lookup or a query-time LLM call to get that
  information.
- Stay cheap and fast as the corpus grows into the hundreds of files across
  many courses — query cost must not scale linearly with corpus size in a
  way that makes it slow or expensive.
- Index cards regenerate automatically as new files are produced by either
  pipeline (no separate manual step to remember).
- Tags (`tags`) are assigned with corpus-wide awareness, not guessed per
  file in isolation — `tags: []` has sat permanently empty in
  `transcribe_notes.py` specifically because per-file tagging without that
  awareness was rejected earlier; §5 is what it was left empty for.
- Lay groundwork (tag vocabulary, embeddings) reusable by the eventual
  RAG model and by future cross-corpus "web of knowledge" tag queries.

**Non-goals**
- No vector DB / ANN index (FAISS, Chroma, ...) — brute-force cosine
  similarity over in-memory NumPy arrays is sufficient at the target scale
  (see §6) and this can be swapped in later without touching the schema.
- No *persisted* graph structure or interactive graph traversal/query UI.
  §5 uses a similarity graph as an internal mechanism to decide which tags
  to mint, but that graph is rebuilt from scratch each `retag` run and
  discarded immediately after — only its output (tags on cards) persists.
  Querying the graph itself, or any richer tag-relationship browsing, is
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
  tags.json          # canonical tag vocabulary (flat list, grown only by retag — see §5)
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
  "tags": ["linear-algebra", "vector-spaces", "eigenvalues", "inner-product-spaces"],
  "level": "introductory",
  "has_solutions": false,
  "page_count": 404,
  "rag_md_path": null,
  "embedding": [0.0123, -0.0456, ...],
  "embedding_model": "gemini-embedding-001:768",
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
  `handwritten_notes`, or the raw `folder_category` string if the LLM's
  classification doesn't map to a known type — never fails closed.
  Exams are deliberately folded into `problem_set` rather than kept as
  their own category — confirmed against the real corpus (a live
  `rebuild` run, §7) that the LLM already classifies `old_exam_2021.md`
  and `old_exam_2025.md` as `problem_set` without being told to, and
  there isn't enough semantic difference between the two for a RAG
  consumer to warrant a separate category.
- `tags` starts as `[]` at card generation and is populated (and later
  possibly changed) **only** by the corpus-wide `retag` pass — see §5. It
  is never guessed by the per-file generation call in §4.
- `level` (`introductory` / `intermediate` / `advanced`, in that fixed
  order — what `max_level` in §6's `search()` filters against) and
  `has_solutions` (does this file contain worked solutions/answers, as
  opposed to bare problem statements or unworked exercises) are both
  inferred in the same per-file LLM call as `summary` (§4), from that
  same file's own `content_sample` — never from its filename. Unlike
  `tags`, a document's own difficulty and whether it shows its work are
  self-contained properties that don't need corpus-wide awareness to
  judge, so there's no reason to defer them to `retag`. Caveat: for the
  textbook pipeline, `content_sample` is only title/author/year + TOC
  (§4), so `has_solutions` there leans on the LLM's background knowledge
  of the named book rather than reading actual content — same tradeoff
  already accepted for `summary`/`level` on textbooks.
- `page_count` costs nothing extra to capture — both pipelines already
  compute it (`total_pages` in the notes pipeline's frontmatter,
  `total_pages_processed` in the textbook pipeline's `master_metadata`) —
  it's just never been surfaced on a searchable record before.
- `rag_md_path` (nullable, textbooks only) is set by a separate hook into
  `describe_images.py` — see §4.4 — once that script produces
  `{folder_name}.rag.md` (image descriptions inlined as text). Per-request
  decision: `.rag.md` is always preferred over `.md` when present, since
  it's identical content plus inlined descriptions, strictly more useful
  to a text-only RAG consumer — §6's search results return `rag_md_path`
  in place of `path` whenever it's set, rather than requiring a caller to
  check both fields.
- `needs_indexing: true` marks a card whose generation failed partway
  (LLM/embedding call error) — see §7 for how this gets swept up.
- `source_updated_at` is the source `.md`'s mtime at card-generation time,
  used by the rebuild pass to detect files that changed since their card
  was last generated.
- `orphaned: true` (omitted otherwise) marks a card whose `file_id` a
  rebuild sweep couldn't match to any PDF on disk — see §4.3/§7. Excluded
  from search results and from its course's centroid/tag-count rollup,
  and from tag mining, while flagged.

### 3.2 Course-level entry (one per course, in `courses.json`)

```json
{
  "course": "math-camp",
  "title": "Math Camp",
  "predominant_tags": ["linear-algebra", "real-analysis", "probability", "optimization"],
  "file_count": 14,
  "embedding": [0.0089, -0.0321, ...]
}
```

Computed **entirely from that course's own file-level cards, with no
additional LLM or embedding call**:
- `embedding` = the centroid (elementwise mean) of every file card's
  `embedding` in that course's shard.
- `predominant_tags` = the most frequent entries in the union of those
  cards' `tags`.

This is a free byproduct of writing any file card — recomputed each time a
card is added/updated in that course, and again after every `retag` run
(§5), keeping `courses.json` always in sync without a separate generation
step. Until the first `retag` run, `predominant_tags` is simply empty for
every course, since no card has any `tags` yet.

This also directly answers "identify mutually reinforcing synergies
between courses" without any further mechanism: comparing two courses'
`predominant_tags` overlap, or their centroid `embedding` similarity,
surfaces cross-course overlap (e.g. math-camp's `optimization` tag
resurfacing in an econometrics course) using data this spec already
produces as a byproduct of §5.

### 3.3 Tag vocabulary (`tags.json`)

A list of `{tag, embedding}` entries — `tag` a canonical kebab-case
string (e.g. `linear-algebra`, `eigenvalues`, `real-analysis`);
`embedding` a semantic anchor computed once, from the tag's own name +
short definition, when it's minted (see §5.1 for why this is more
stable than deriving it from whichever documents happened to found the
tag). Entries are added **only** by the `retag` pass (§5) — never
proposed per-file — which is what keeps this vocabulary free of
near-duplicate fragments (`linear-algebra` vs `Linear Algebra` vs
`lin-alg`) and keeps `tags` usable as graph edges (§9).

## 4. Card generation

New shared module, `marker-conversion/index_card.py`, called from both
pipelines rather than duplicating LLM-prompt logic in each:

```python
def generate_index_card(
    path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str,  # what the LLM sees — see below
    client,  # already constructed — see §4.1, caller-specific
) -> dict: ...

def write_card(course: str, card: dict) -> None: ...   # updates <course>.json + courses.json
```

`folder_category` (the mechanical, no-judgment path segment `derive_folder_category()`-style
logic already produces — never itself LLM-derived) is a **fallback hint passed into the
prompt**, not the card's final `doc_type`. The LLM's own classification wins whenever it maps
to a known type; `folder_category` is only used verbatim when it doesn't — content decides,
not just the folder a file happens to live in.

**`content_sample` differs by caller, deliberately kept cheap regardless of
source length:**
- Notes pipeline (`transcribe_notes.py`): the finished markdown itself —
  these documents are short (tens of pages at most), so passing the whole
  thing is cheap.
- Textbook pipeline (`convert_textbook.py`): the resolved `bib_info`
  (title/author/year — the local variable at line 844, *not*
  `master_metadata`, which only ever holds marker's structural fields
  per the comment at line 815) plus the **first ~12,000 characters of the
  finished assembled markdown** (`local_build_dir/{folder_name}.md`,
  written at line 864, already on disk by the hook point at line 881) —
  never the full text. This reuses the same "bounded prefix of the
  assembled markdown" pattern `extract_bibliographic_info_via_llm()`
  already relies on (`chunk_files[0]`, `f.read(6000)`, line 825-826) for
  the same reason: a book's front matter, including its own printed table
  of contents, is reliably near the start regardless of the book's total
  length, so this keeps card-generation cost roughly constant whether the
  book is 200 or 900 pages, without needing to plumb `chapter_index.py`'s
  internal `ChapterEntry` list out of `compute_chunk_boundaries()` (it's
  never returned past that function today — extracting it would mean
  touching several function signatures and the persisted `run_config.json`
  schema, for a signal a markdown prefix already provides more simply).

One `client.models.generate_content()` call, model `gemini-3.1-flash-lite`
— this is a pure text-in/JSON-out classification+summarization call, no
vision/multimodal input, so it uses this project's existing *cheap* text
tier (`_MODEL_TYPESET` in `transcribe_notes.py`, already used there for
exactly this kind of non-handwriting, text-only work), not the pricier
`gemini-3.6-flash` tier reserved elsewhere in this project for vision
tasks (image description, handwriting transcription). Confirmed live
against the real API that `gemini-3.1-flash-lite` supports the same
structured-JSON config used below. Via `call_with_retries()`,
`config={"response_mime_type": "application/json", "temperature": 0,
"thinking_config": {"thinking_level": "minimal"}}` (the same structured-
JSON pattern `extract_bibliographic_info_via_llm()` in
`convert_textbook.py` already uses at line 654, reused rather than
invented fresh), returns structured JSON: `{title, doc_type, summary,
level, has_solutions}` — **no `tags`**, that's §5's job, deliberately
kept separate so a single-document call is never what decides a file's
tags (`level` and `has_solutions` stay here because, unlike tags, they're
properties of the one document in front of the LLM, not something that
needs sibling files to judge correctly). `page_count` is copied from
metadata the calling pipeline already computed — no LLM involvement.

The `title+summary` text is embedded with one `client.models.embed_content()`
call, model `gemini-embedding-001` with `config=EmbedContentConfig(
output_dimensionality=768)` — confirmed live against the real API: the
model accepts and honors `output_dimensionality=768` (vs. its 3072-dim
default, unnecessarily large for this corpus's scale), and returned
vectors are **not** pre-normalized (a real call returned L2 norm ≈ 0.59,
not 1.0) — cosine similarity code anywhere in this system (§5, §6) must
normalize vectors itself, never assume unit length. `embedding_model` is
stored per-card as `"gemini-embedding-001:768"` so a future change to
either the model or the requested dimensionality is detectable rather
than silently comparing incompatible vectors. The card is written with
`tags: []`.

### 4.1 Hook insertion points

`generate_index_card()` takes an already-constructed `client` rather than
building one itself. All three pipelines that touch `index_card.py`
(`transcribe_notes.py`, `convert_textbook.py`, and `describe_images.py`
— see §4.4) use the **same** client-construction path for their indexing
calls specifically: `gemini_utils.get_gemini_client()` (Developer API key
from `.env`), matching what `describe_images.py` and `transcribe_notes.py`
already use for their own existing LLM calls today — confirmed by reading
both files.

`convert_textbook.py` runs on a GCP VM and separately builds a *different*
client, `genai.Client(vertexai=True, project=..., location=...)`, for its
own existing bibliographic-extraction call in
`extract_bibliographic_info_via_llm()` (line 650) — using Application
Default Credentials specifically so that one call doesn't need a
separately-distributed API key on the VM. That reasoning is specific to
running unattended on a VM with no interactive way to manage a secret;
the indexing hook doesn't inherit it automatically, and using the same
Developer-API-key path as every other indexing call (rather than a third
client-construction pattern) is simpler and keeps the embedding call
exercised against only the one backend it was actually verified against
live (`gemini-embedding-001` returning 3072-dim vectors, not
pre-normalized; `output_dimensionality=768` accepted and verified
working). This does mean `GEMINI_API_KEY` (or `.env`) needs to be
reachable from wherever `convert_textbook.py` actually runs — true today
for `describe_images.py`, which already depends on exactly that, so this
isn't a new requirement being introduced, just extended to a second
script. If the VM `convert_textbook.py` runs on doesn't have `.env`/the
key available when this runs, `get_gemini_client()` prints an error and
returns `None` rather than raising — the existing failure-isolation
around the indexing call (§4.2) still degrades this to a warning, never
blocking the actual textbook conversion.

- `transcribe_notes.py`, in `process_pdf()`: the frontmatter dict currently
  finalized with `"tags": []` (e.g. around the block at line 844 and its
  siblings near 904/975/1032) is a separate, optional follow-up (§9) —
  not touched by this indexer directly. `process_pdf()` has four separate
  exit points (one per routing tier), each currently ending in its own
  `with open(md_path, "w"...) as f: f.write(...)` block before an early
  `return` — the indexer hook factors that repeated block into one shared
  helper (called from all four places instead of duplicated four times)
  that writes the markdown file and then calls `generate_index_card()`
  with the finished markdown as `content_sample`, then `write_card()`.
- `convert_textbook.py`, in `process_one_pdf()`: immediately after
  `master_metadata` is finalized and `_metadata.json` is written (~line
  881-888), call `generate_index_card()` with `bib_info` (line 844) and a
  bounded prefix of the just-written `{folder_name}.md` as
  `content_sample`, then `write_card()`.

  Before that indexing call — and unconditionally, independent of whether
  it succeeds — `master_metadata` also gains two new fields written
  straight into `_metadata.json`: `source_pdf_path` (relative to
  `academic-hub/`) and `source_pdf_file_id` (the same `file_id` computed
  for the card). This is valuable bookkeeping on its own merit, not just
  indexer plumbing: it's what makes §4.4's `describe_images.py` hook able
  to find "which card does this `.rag.md` belong to" without needing to
  re-locate or re-hash a PDF from inside a different script, and it's
  what finally makes textbook backfill in §7 tractable for cards that
  predate this system — see §7's updated note. `file_id`/`rel_pdf_path`
  computation is trivial local hashing (no network call, effectively
  never fails), so writing these fields is not wrapped in the same
  try/except as the LLM/embedding-dependent indexing call below it.

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
  centroid/tag-counts for *both* the old and new course (still purely
  mechanical — no LLM or embedding call, since `summary`/`tags`/
  `embedding` don't change).
- **No match anywhere:** genuinely new content — generate a fresh card as
  in §4 (this is the only path that costs an LLM + embedding call).

This means a course-folder rename or nesting change costs exactly one
rebuild pass worth of PDF hashing (cheap — no network calls) to reconcile
every affected card in place, not a full regeneration of the corpus.

### 4.4 `describe_images.py` hook (`.rag.md` linkage)

`describe_images.py` is a third, separate script (confirmed: it already
runs locally on `gemini_utils.get_gemini_client()`, the same Developer
API key path §4.1 now uses uniformly) that produces
`{folder_name}.rag.md` from an already-converted textbook's `.md`, run
independently and later than `convert_textbook.py` — its own hook cannot
assume `.rag.md` exists at `convert_textbook.py`'s hook point (§4.1), and
doesn't need to: it adds a *second* hook of its own, in `process_book()`,
immediately after `rag_path` is written (existing code, `rag_text`
written to `rag_path`) and before the function returns:

1. Read the sibling `_metadata.json` (same `book_dir`) for
   `source_pdf_file_id` (§4.1's new field). If absent — true for any
   book converted before this change, until backfilled per §7 — log a
   warning and stop; the `.rag.md` file itself is unaffected either way,
   since this hook runs after it's already written.
2. Write `rag_md_path` (relative to `academic-hub/`) into that same
   `_metadata.json`, alongside `source_pdf_file_id` — mirroring
   `convert_textbook.py`'s own linkage fields, so `_metadata.json`
   carries the full chain (PDF → `.md` → `.rag.md`) independent of
   whether the index card update below succeeds.
3. Call a new, narrower `index_card.py` function —
   `set_rag_md_path(academic_hub_root: str, file_id: str, rag_md_path: str) -> bool`
   — that finds the card by `file_id` (§4.3's `find_card_by_file_id()`,
   reused rather than duplicated) and sets its `rag_md_path` field,
   returning `False` (logged as a warning, not raised) if no card exists
   yet for that `file_id` — e.g. the textbook hasn't been indexed yet,
   or generation failed and left a `needs_indexing` card, which still
   has a `file_id` and can still be found and updated.

Like every other indexing touchpoint, this is wrapped so a failure here
never affects the actual `.rag.md` output, which this hook only runs
after.
## 5. Tag mining (`retag` — corpus-wide, two-phase)

This is what `tags: []` was always deferred for: tags are assigned only
with visibility across the *whole* corpus, not guessed per file at
generation time (§4). Run via `index_search.py retag` (§8) — an explicit,
separate, occasionally-run pass, not part of every `rebuild`, since it's
corpus-wide rather than per-course/per-file.

Discovering *which tags should exist* and deciding *which files get a
given tag* are two different questions with two different right answers —
conflating them (tag = "you're in this cluster") is what produces at most
one tag per file, and actively wrong results for any file that
legitimately bridges two subjects: connected components are transitive,
so a file similar to both a linear-algebra cluster and a probability
cluster doesn't get two tags, it *merges the two clusters into one bad
one*. Splitting into discovery (mint new tags, conservatively) and
assignment (apply any tag in the vocabulary, liberally, to any matching
file) fixes both problems at once and is the actual algorithm:

### 5.1 Tag vocabulary now carries a real semantic anchor

`tags.json` (spec §3.3) stores `{tag, embedding}` pairs, not bare
strings — `embedding` is computed **once, when a tag is minted**, from
the tag's own name/short definition (e.g. embedding the text
"eigenvectors — eigenvectors and eigenvalues of linear operators"), not
from the mean of whichever documents happened to found it. This anchor
is durable: it's what lets `retag` compare *every* file against *every*
known tag on every run without re-embedding anything for tags that
already exist, and it's a more stable "meaning" for the tag than a
cluster centroid would be — a centroid drifts with whatever documents
happened to seed it; an embedding of the tag's own definition doesn't.
It also gets the "related words" behavior for free: an embedding of
"eigenvectors" already sits close to "eigenvalues" and "spectral
theorem" in embedding space, no manual synonym list needed.

### 5.2 Discovery — propose candidate tags holistically, validate empirically

**Revised 2026-08-28 against real data.** The original design built a
similarity graph over card embeddings and took connected components as
candidate clusters — reactively naming whatever clustering happened to
produce. Tested live against the real corpus (24 cards) and rejected:
connected components are transitive, so any document that legitimately
bridges two subjects (a mixed problem set touching both linear algebra
and real analysis) merges their clusters into one. No similarity
threshold fixed it — sweeping `0.78` through `0.90` against the real
corpus produced either one 16-of-24-card blob (low end), a cluster of 5
that grouped by **document format** (exams and problem sets) rather than
by subject (mid-range), or nothing at all (high end). Connected
components on whole-document embeddings simply don't have the
resolution to find subject boundaries at this corpus scale — confirmed,
not assumed.

**Replacement:** ask directly, once, rather than infer indirectly from a
similarity graph — the same way a person skimming a list of file titles
would recognize "there's linear algebra here, there's real analysis
there," not by computing pairwise similarity at all.

Run fresh each time (nothing here persists except its output — new
entries in `tags.json`):

1. Load every non-orphaned, embedded file card's `embedding`, `title`,
   and `summary` across all course shards.
2. **One LLM call**, holistic — not one per cluster, and no similarity
   graph involved at all — takes every card's title + summary at once
   and proposes a set of candidate subject tags that would meaningfully
   partition the corpus (broad enough to plausibly cover several
   documents, specific enough to be useful — "linear-algebra" and
   "real-analysis" as separate tags, not one tag for both or one tag per
   document). This is what avoids the transitivity problem entirely
   instead of tuning around it: the LLM sees the whole corpus at once
   and isn't constrained by pairwise-similarity chains.
3. For each candidate, fuzzy-match its proposed name against the
   existing `tags.json` vocabulary first (unchanged from before) — a
   match means nothing new is minted, `tags_reused` instead.
4. For genuinely new candidates: one embedding call over the tag's own
   name + short definition produces its anchor (§5.1, unchanged), then
   **empirically validate** it against real data before minting — count
   how many cards actually have cosine similarity above
   `TAG_ASSIGNMENT_THRESHOLD` (§5.3's threshold, reused here rather than
   a separate constant, since this is the same comparison assignment
   will make) against that anchor. Only minted (`{tag, embedding}`
   appended to `tags.json`) if at least `MIN_TAG_CLUSTER_SIZE` (starting
   default `3`, same conservative-minting principle as before) cards
   clear the bar. This is still "singleton tags aren't useful," just
   checked against real embeddings instead of a similarity-graph
   cluster's raw size — a candidate the LLM proposed but that doesn't
   actually correspond to enough real content gets rejected, not minted
   on the LLM's say-so alone.

This also fixed a second real bug found in the same live test: with the
old design, `TAG_ASSIGNMENT_THRESHOLD` defaulted to the *same* value as
the old `CLUSTER_SIMILARITY_THRESHOLD` (`0.78`) — but an anchor's
similarity to individual documents runs measurably lower than its
similarity to a cluster centroid (confirmed live: `0.82` to the
centroid, only `0.65`–`0.76` to any individual founding member, for the
same tag). A tag could be minted from real evidence and then match
*nothing*, including the very documents that inspired it. `CLUSTER_SIMILARITY_THRESHOLD`
no longer exists as a separate constant (nothing builds a similarity
graph anymore); `TAG_ASSIGNMENT_THRESHOLD`'s default is lowered to
`0.65` — the low end of the real observed range — since it's now the
only threshold in the system and is used identically at both discovery
(validating a candidate) and assignment (applying an approved tag).

**Known scaling caveat, not solved here:** step 2's holistic call puts
every card's title+summary in one prompt — fine at today's scale
(dozens of files) but will need chunking or sampling once the corpus
reaches the hundreds this project expects to grow into (§1's Goals).
Not built now — YAGNI relative to the corpus size that actually exists.

### 5.3 Assignment — apply any known tag, liberally, to any matching file

For **every** non-orphaned, embedded file card (not just cards that
happened to inspire a candidate in §5.2), independently compare its
`embedding` against every tag anchor in the (now-updated) `tags.json`
vocabulary **except tags marked `origin: "fallback"`** (§5.4 — those
describe exactly one document and are never candidates for reuse
elsewhere) — old tags and ones just minted in §5.2 alike. Above
`TAG_ASSIGNMENT_THRESHOLD` (starting default `0.65` — see §5.2 for
where that number comes from), the tag is added to that card. A card's
`tags` list is fully
**replaced** by this run's result, not appended to — this is what makes
tags non-permanent (§ below) and is also what makes back-apply correct:
a five-year-old file that was always similar to a tag that only just
crossed the minting bar gets that tag applied the same as a brand new
file would.

This is genuinely many-to-many: a file can match several tag anchors
(the actual fix for the original one-tag-per-file problem), a tag can
match files anywhere in the corpus regardless of which cluster minted it,
and — because minting (§5.2, conservative) and assignment (§5.3,
liberal) use different bars — a single relevant file can pick up an
already-established tag even though one file alone could never have
minted a brand-new one.

`courses.json`'s `predominant_tags` (§3.2's free rollup) is recomputed
for every affected course after assignment completes.

**Tags are not permanent once assigned.** Because both phases run fresh
from the current corpus every time, a later `retag` can add or drop a
tag from any file as the corpus's embeddings and the tag vocabulary
change — tags track current corpus structure, not a one-time decision.

`retag --dry-run` prints the proposed/reused/rejected candidate tags and
the full assignment result without writing anything — lets
`TAG_ASSIGNMENT_THRESHOLD` be sanity-checked against the real corpus
before trusting a run that mutates every course shard at once.

### 5.4 Minimum coverage — every file gets at least one tag

Confirmed live: 5.2's conservative minting bar (`MIN_TAG_CLUSTER_SIZE`)
correctly avoids inventing subject tags from too little real evidence,
but it also means a genuinely unique document (the only syllabus in the
corpus, a one-off course overview) can never earn a shared subject tag
on its own — 2 of 24 real cards ended up with zero tags in the same live
test that validated §5.2's redesign. An untagged file — no descriptor
at all — is a worse outcome than one single-file tag like `syllabus`
that will never clear the corpus-wide bar and isn't meant to.

After discovery (§5.2) and assignment (§5.3) complete, run one more
pass: for every card whose `tags` list is still empty, one per-file LLM
call proposes a tag specifically for *that document alone* (e.g.
`syllabus`), fuzzy-matched against the vocabulary first (§5.2's
`fuzzy_match_tag()`, reused as-is) so two similar one-off files converge
on the same tag rather than fragmenting. Unlike §5.2's candidates, a
minimum-coverage tag is **never subject to the empirical match-count
validation** — it's explicitly a single-file exception, not a claim
about corpus-wide structure, and is assigned directly to its originating
card regardless of the anchor's computed similarity to that card (the
anchor was derived to describe this exact file, so requiring it to also
clear a similarity threshold against that same file would reintroduce
§5.2's original anchor-vs-single-document gap for no reason). If a new
tag is minted this way, it's appended to `tags.json` marked
`origin: "fallback"`, and future `retag` runs' discovery-phase fuzzy
matching can still reuse it by name for another proposal that lands on
the same slug.

**Revised 2026-08-28 against real data:** this section originally said
normal §5.3 assignment could "naturally reuse" a minimum-coverage tag
too, once the corpus grew enough similar content. Confirmed live that
this was wrong: because a fallback tag's anchor was never validated
against the corpus (deliberately, per above), it's just a generic
paraphrase of one document, and in a small or topically-homogeneous
corpus that anchor can cross `TAG_ASSIGNMENT_THRESHOLD` against
completely unrelated cards — a `syllabus`-style fallback tag minted for
the corpus's one syllabus scored 0.73 similarity against an unrelated
Linear Algebra lecture-notes file, which §5.3's assignment would have
happily applied. §5.3's assignment now explicitly **excludes** any tag
with `origin: "fallback"` — a fallback tag only ever describes the
single card it was minted for, permanently, unless the corpus's content
itself changes and a *later* discovery run (§5.2) independently proposes
and empirically validates the same concept as a real corpus-wide tag
(which mints a fresh, non-fallback entry — the fallback entry is not
"promoted" in place).

This pass runs every time, not just once: a card that got a
minimum-coverage tag in an earlier run and *still* has zero tags from
discovery+assignment this run keeps getting covered; a card that now
has a real corpus-driven tag is skipped, consistent with §5.3's "tags
are not permanent."

```python
def search(
    query: str, course: str | None = None, top_k: int = 5,
    doc_type: str | None = None, has_solutions: bool | None = None,
    max_level: str | None = None,
) -> list[SearchResult]: ...
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
   that genuinely shares tags, e.g. econometrics) automatically.
3. **File filter**: load only the selected courses' shards, apply
   `doc_type`/`has_solutions`/`max_level` as hard filters over the cards
   **before** ranking, then brute-force cosine similarity over what's left
   and return the top `top_k` as `SearchResult(path, course, doc_type,
   score, reason)` — where `path` is `rag_md_path` when the card has one
   (§3.1/§4.4), falling back to `path` otherwise, so a caller never has to
   check both fields itself — and `reason` is simply that card's stored
   `summary` — no query-time LLM call needed to explain a match. Filtering
   before truncation, not after, matters: e.g. "unsolved practice problems
   on linear algebra" with `has_solutions=False` should return the best
   `k` *unsolved* matches, not whatever's left after throwing away solved
   ones from an unfiltered top `k`.

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

**Textbook backfill.** For the notes pipeline, matching a PDF to its
markdown is deterministic by construction (§4.1's fixed
`<category>/processed_outputs/<basename>.md` convention). For textbooks,
it isn't — a `processed_outputs/<FolderName>/` folder's name has no
reliable relationship to the PDF filename that produced it (e.g. `Book of
Proof.pdf` → `Hammack_Book_of_Proof_2025/`). §4.1's new
`source_pdf_path`/`source_pdf_file_id` fields in `_metadata.json` solve
this going forward — every *new* textbook conversion records its own
source unambiguously. `rebuild` reads that field back out of each book's
`_metadata.json` when present; a book folder whose `_metadata.json`
predates this change (true for the 5 converted before this spec revision)
is skipped with a clear message rather than guessed at — those 5 need
`source_pdf_path` (a plain relative-path string, not a hash — trivial to
add by hand once, since only a human who already knows which PDF matches
which folder can supply it correctly) added to their `_metadata.json`
once, after which the same `rebuild` picks them up automatically.

**Orphan handling:** a card whose `file_id` isn't matched to any PDF found
during a rebuild sweep (the source PDF was deleted, or its content was
replaced — a content change produces a different hash, which is correctly
treated as a new file rather than silently reusing the old card) is flagged
`orphaned: true` rather than deleted immediately. `rebuild --prune` removes
confirmed orphans (and rolls their old course's centroid/tag-counts back)
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

- **Document relationship/pairing detection.** Confirmed directly in the
  corpus: `Linear Algebra Problem Set.md` and
  `Linear Algebra Problem Set AMS Solutions.md` exist as two separate
  files with no link between them today, and this pattern likely repeats
  (a problem set and its solutions, or a lecture note and the textbook
  chapter it complements). `has_solutions` (§3.1) tells a RAG layer
  whether *one* file has solutions inline, but not which *other* file is
  its companion. Detecting that is a different mechanism from both §4
  (per-file, no sibling awareness) and §5 (groups by broad tag-level
  similarity via `title+summary` embeddings, not by "this is specifically
  the solved version of that") — a real, useful capability, but its own
  design pass once the base system is proven, not built here. Worth
  recording now while fresh: cluster co-membership (§5) alone won't be
  precise enough to find a specific pair, since a true pair will usually
  sit inside a cluster with several other same-tag files pulled in by
  the same broad summary similarity. A workable approach would (1) treat
  a file's similarity to a candidate partner as a *local outlier* —
  meaningfully higher than that file's similarity to every other member
  of its own cluster, not just above a fixed threshold — as a cheap
  candidate filter reusing this spec's existing shards/embeddings, then
  (2) confirm shortlisted candidates with either one LLM call comparing
  the two documents directly, or a full-text (not summary-level) embedding
  comparison limited to that shortlist — full-text embedding for the
  whole corpus would be a much larger cost than anything else in this
  spec, so it should stay scoped to confirmation, not first-pass search.
- **Prerequisite/tag ordering**, extending the tag-graph idea below
  with directionality (e.g. "eigenvalues" typically presumes
  "vector-spaces") rather than the undirected co-occurrence §5 already
  produces — useful for study-plan sequencing specifically, but ordering
  is a materially harder claim than co-occurrence and deserves its own
  validation before being trusted for that use.
- **Richer tag-graph browsing.** §5 uses a similarity graph purely as an
  internal, throwaway mechanism to decide which tags to mint — it's never
  persisted or exposed for querying. A future layer could persist
  co-occurrence structure (e.g. "eigenvalues" and "characteristic
  polynomial" co-occurring across sources even outside the same course
  folder) for actual graph browsing/traversal, directly on top of the
  normalized `tags` this spec already produces — no schema change
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
  field from the card's (post-`retag`) `tags` list, so the human-readable
  file itself carries the same tags as its index card. Not required for
  search to work (the card is the system of record), so left as a
  follow-up — and only sensible to build after `retag` exists, since
  before that the field would still just be empty.
