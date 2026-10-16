# Journal Article Conversion

Converts academic journal-article PDFs — typically short, born-digital,
publisher-rendered documents — into Markdown by reusing
[`transcribe_notes/transcribe_notes.py`](../transcribe_notes/)'s tiered pipeline directly, unchanged.

## Key file

- `convert_journal_articles.py` — needed almost no new code: `process_pdf()`
  already does exactly what a journal article needs (tiered cost-routing,
  content-hash caching, indexing hook), so this just points it at a
  recursively-walked folder (journal articles live under thematic
  subfolders, e.g. `economics/`, that may nest further — unlike the flat,
  single-level folders the notes pipeline usually sees) with its own
  `known_doc_types={"journal_article"}`. A document over `--max-pages`
  (default 150) is flagged and **skipped entirely**, never converted — the
  GPU/Marker [`convert_textbook/`](../convert_textbook/) pipeline is the most expensive step
  in this whole project, and it only ever runs on files a human deliberately
  moves into `academic-hub/`'s own folder structure, never something this
  script triggers on its own.

Depends on `core/env/`, `core/indexer/`, and `pipelines/transcribe_notes/` (whose `process_pdf()` it calls
directly). Part of the same growing research corpus as
[`convert_essays/`](../convert_essays/) — see the root [`README.md`](../../README.md) for the
full dependency graph.

## Full usage guide

Companion to [`pipelines/transcribe_notes/README.md`](../transcribe_notes/README.md), for a corpus that's structurally the
same kind of document (a PDF, usually born-digital, no table of contents
worth chapter-chunking) but conceptually different: academic journal
articles rather than course notes. `convert_journal_articles.py` reuses
`pipelines/transcribe_notes/transcribe_notes.py`'s `process_pdf()` completely unchanged -- same
tiered cost-routing (free local extraction, hybrid repair, full
Gemini-vision transcription), same caching, same indexing hook -- just
pointed at a different folder with a different `known_doc_types`.

**Default transport (2026-10-16, literature taxonomy stage 1):** transcription runs through the
Antigravity subscription as task cards, not the paid API. `--driver agent` is the default and a bare
run does nothing and exits 1; use `--driver api` for the old fully metered behaviour. Index-card
summaries and embeddings still use the Gemini API at submit time (small calls); transcription does not.

### Step 1: One-time local setup

Same dependencies as `pipelines/transcribe_notes/transcribe_notes.py` -- no new ones.

```powershell
cd academic-rag-model
pip install google-genai python-dotenv pymupdf pypdf
```

### Step 2: Run it

Recursively finds every `.pdf` under the target folder, however deep its
thematic subfolders go (`journal-articles/economics/paper.pdf`,
`journal-articles/economics/development/paper.pdf`, ...).

```powershell
# 1. Stage task cards for every paper that needs transcription (no API calls)
python -m pipelines.convert_journal_articles.convert_journal_articles --collect --run-id r1
# 2. In Antigravity, follow the contract printed by --bootstrap r1 and fill the cards
python -m pipelines.convert_journal_articles.convert_journal_articles --bootstrap r1
# 3. Validate, write and index. Clean machine-text papers have no cards and convert locally here.
python -m pipelines.convert_journal_articles.convert_journal_articles --submit r1
```

* Cards and page images live in `<index-root>/.agent_work/<run-id>/` (`research/.agent_work/` by default).
  They hold paper text, so that folder is gitignored; never commit it.
* `--submit` leaves a pending or bounced card pending. `--allow-api-fallback` is the explicit, never
  automatic opt-in to finish those via the metered API.
* `--driver api` runs the original single-step metered path. Warn before running it over a large
  batch (project rule: over $1 needs a go-ahead).
* `--backfill-identity` stamps OpenAlex id, DOI, topics and year from each paper's discovery
  `.meta.json` sidecar onto its index card. No transcription, no API calls; papers converted before
  this existed need it once. Newly converted papers are stamped automatically.
* `--dry-run` works with any driver and needs no flags.

* Defaults to `research/journal-articles` (the folder next to this
  project). Pass `--articles-dir <path>` to point at a different folder.
* Add `--file "some-paper.pdf"` to convert just one file instead of the
  whole corpus.
* Add `--dry-run` first to see which tier each paper would route to
  (and which oversized documents would get flagged) without spending
  any API calls.
* Add `--index-root <path>` to change where the source-indexer's
  `.index/` lives (default: `research/`, sibling of `academic-hub/`,
  same convention `convert_essays/convert_essays.py` uses). Course is derived
  from each paper's path relative to this root, so with the default a
  paper's thematic subfolder (`economics/`, `misc/`, ...) becomes its
  course automatically.
* Add `--max-pages <N>` to change the oversized-document threshold
  (default 150). A document over it is flagged and **skipped entirely**
  -- not converted, not indexed. This is deliberate: the GPU/Marker
  textbook pipeline is the most expensive part of this whole project,
  and it only ever runs on files actually sitting in `academic-hub/`'s
  own folder structure. A flagged file needs a human decision (move it
  into `academic-hub/` and run `convert_textbook.py` there, or leave it
  out of the indexed corpus) -- this script never makes that call for
  you. Confirmed real: a 402-page monograph briefly sat in
  `journal-articles/` alongside genuine ~20-page papers before this
  guard existed.
* Output: `processed_outputs/<name>.md` next to each source PDF (same
  `processed_outputs/`-alongside-the-input convention as the notes
  pipeline), including the `<!-- page N -->` tags and YAML frontmatter
  (`routing`, `model`, `tags: []`, ...) `transcribe_notes.py` always
  produces.

### How it works

Two small, real changes made this reuse possible, both driven by
running against the actual corpus rather than assumed upfront:

* **`known_doc_types` is now a parameter on `process_pdf()`/
  `_write_markdown_and_index()`**, not a hardcoded constant -- mirrors
  the same fix `index_card.py`'s `generate_index_card()` already got
  for `convert_essays/convert_essays.py`. Default is unchanged (academic-hub's
  own vocabulary), so the notes pipeline itself is unaffected; this
  script passes its own `{"journal_article"}` set.
* **`has_reliable_pagination()`'s marker list now recognizes Apache FOP
  and XEP** (RenderX), two real academic-publisher PDF renderers behind
  2 of the first 3 real papers in this corpus -- previously only
  LaTeX/Word/LibreOffice were recognized, so genuinely clean,
  reliably-paginated papers from these renderers were routed to
  expensive full-page vision transcription for no reason. This benefits
  `academic-hub`'s own notes pipeline too, not just this corpus.

**Defect heuristic (updated 2026-10-16):** `page_looks_defective()` was tuned against LaTeX math notes.
This converter now passes `check_math_notation=False` (a bare `R2` or `H1` in a paper is a statistic or
hypothesis label, not a lost exponent). `defect_audit.py` measures the effect per signal without printing
page text: `python -m pipelines.convert_journal_articles.defect_audit --articles-dir <dir> --no-math-notation`.
Measured result and what remains: `docs/status/convert_journal_articles/2026-10-16-stage1-driver-wiring.md`.

Original observation, before that change: `page_looks_defective()`'s
heuristics (tuned against LaTeX-typeset math lecture notes) flag a real,
substantial fraction of pages in every one of the 4 real papers tested
(32-43%) -- enough to push all of them into whole-document Gemini
batching rather than the cheaper hybrid-repair tier. Likely candidates
are citation/footnote/DOI conventions this checker has never seen, not
tuned against academic-paper prose specifically. Not fixed here --
whole-document batching is still correct and still cheap (~$0.02/paper
at real per-page rates) -- but worth knowing this corpus isn't hitting
the free tier as often as its clean PDF metadata alone would suggest.

Recursive discovery (`os.walk`, not a flat `os.listdir`) is the one other
real difference from `pipelines/transcribe_notes/transcribe_notes.py`'s own `discover_pdf_files` --
journal articles live under thematic subfolders from the start, and may
nest further, unlike academic-hub's flat per-category PDF folders.

No chunking, page markers, or indexing changes beyond `known_doc_types` --
everything downstream (`core.indexer.chunk_index`, `core.indexer.index_search`)
already works unmodified once a `journal_article`-typed card exists,
the same way it did for essays.
