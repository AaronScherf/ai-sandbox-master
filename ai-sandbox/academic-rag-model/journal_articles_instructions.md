# Journal Article Conversion Pipeline

Companion to `notes_instructions.md`, for a corpus that's structurally the
same kind of document (a PDF, usually born-digital, no table of contents
worth chapter-chunking) but conceptually different: academic journal
articles rather than course notes. `convert_journal_articles.py` reuses
`notes/transcribe_notes.py`'s `process_pdf()` completely unchanged -- same
tiered cost-routing (free local extraction, hybrid repair, full
Gemini-vision transcription), same caching, same indexing hook -- just
pointed at a different folder with a different `known_doc_types`.

## Step 1: One-time local setup

Same dependencies as `notes/transcribe_notes.py` -- no new ones.

```powershell
cd academic-rag-model
pip install google-genai python-dotenv pymupdf pypdf
```

## Step 2: Run it

Recursively finds every `.pdf` under the target folder, however deep its
thematic subfolders go (`journal-articles/economics/paper.pdf`,
`journal-articles/economics/development/paper.pdf`, ...).

```powershell
python -m journal_articles.convert_journal_articles
```

* Defaults to `research/journal-articles` (the folder next to this
  project). Pass `--articles-dir <path>` to point at a different folder.
* Add `--file "some-paper.pdf"` to convert just one file instead of the
  whole corpus.
* Add `--dry-run` first to see which tier each paper would route to
  (and which oversized documents would get flagged) without spending
  any API calls.
* Add `--index-root <path>` to change where the source-indexer's
  `.index/` lives (default: `research/`, sibling of `academic-hub/`,
  same convention `essays/convert_essays.py` uses). Course is derived
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

## How it works

Two small, real changes made this reuse possible, both driven by
running against the actual corpus rather than assumed upfront:

* **`known_doc_types` is now a parameter on `process_pdf()`/
  `_write_markdown_and_index()`**, not a hardcoded constant -- mirrors
  the same fix `index_card.py`'s `generate_index_card()` already got
  for `essays/convert_essays.py`. Default is unchanged (academic-hub's
  own vocabulary), so the notes pipeline itself is unaffected; this
  script passes its own `{"journal_article"}` set.
* **`has_reliable_pagination()`'s marker list now recognizes Apache FOP
  and XEP** (RenderX), two real academic-publisher PDF renderers behind
  2 of the first 3 real papers in this corpus -- previously only
  LaTeX/Word/LibreOffice were recognized, so genuinely clean,
  reliably-paginated papers from these renderers were routed to
  expensive full-page vision transcription for no reason. This benefits
  `academic-hub`'s own notes pipeline too, not just this corpus.

One thing confirmed live but *not* changed: `page_looks_defective()`'s
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
real difference from `notes/transcribe_notes.py`'s own `discover_pdf_files` --
journal articles live under thematic subfolders from the start, and may
nest further, unlike academic-hub's flat per-category PDF folders.

No chunking, page markers, or indexing changes beyond `known_doc_types` --
everything downstream (`indexer.chunk_index`, `indexer.index_search`)
already works unmodified once a `journal_article`-typed card exists,
the same way it did for essays.
