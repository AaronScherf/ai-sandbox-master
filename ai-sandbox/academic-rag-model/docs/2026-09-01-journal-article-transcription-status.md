# Journal Article Transcription: Status Summary

Start here for "what happened and where do we stand" on the
journal-article subproject -- `journal_articles/convert_journal_articles.py`,
which converts academic journal-article PDFs into Markdown by reusing
`notes/transcribe_notes.py`'s tiered cost-routing pipeline wholesale.
Companion doc: `journal_articles_instructions.md`.

Journal articles are structurally the same kind of document the notes
pipeline already handles -- a PDF, usually born-digital, no table of
contents worth chapter-chunking -- just conceptually different:
published papers rather than course notes. `process_pdf()` needed no
changes to be reused here except a `known_doc_types` passthrough, the
same generalization `index_card.py`'s `generate_index_card()` already
got for `essays/convert_essays.py` (see
`docs/2026-09-01-research-notes-conversion-status.md`).

## What shipped

- **Recursive discovery** (`discover_pdf_files`, `os.walk` not a flat
  `os.listdir`): journal articles live under thematic subfolders that
  may nest further (`journal-articles/economics/development/paper.pdf`),
  unlike academic-hub's flat per-category PDF folders.
- **`known_doc_types` passthrough** on `process_pdf()`: this script
  passes its own `{"journal_article"}` set, default unchanged so the
  notes pipeline itself is unaffected.
- **Oversized-document guard** (`--max-pages`, default 150): a document
  far outside normal paper length is flagged and skipped entirely, never
  auto-converted. Confirmed real: a 402-page monograph briefly sat in
  the corpus alongside genuine ~20-page papers. This is a deliberate,
  user-driven design decision -- the GPU/Marker textbook pipeline is the
  most expensive part of this whole project, and it only ever runs on
  files a human actually moves into `academic-hub/`'s own folder
  structure, never something this script triggers on its own.
- **`has_reliable_pagination()` extended** to recognize Apache FOP and
  XEP (RenderX), two real academic-publisher PDF renderers behind 2 of
  the first 3 real papers tested. Previously only LaTeX/Word/LibreOffice
  were recognized, so genuinely clean, reliably-paginated papers from
  these renderers were routed to expensive full-page vision
  transcription for no reason. Benefits academic-hub's own notes
  pipeline too, not just this corpus.

## Real-corpus validation

Confirmed live against the real corpus, not synthetic fixtures:

- Three distinct papers converted and indexed. A fourth turned out to be
  a byte-identical duplicate under a different filename, correctly
  deduplicated by the indexer's own content-hash identity -- not a new
  bug.
- A live query for "large language models applications" correctly
  surfaced both real papers on that topic, federated in the same result
  set as the essay corpus, no separate query needed.
- 2 of the first 3 real papers came from Apache FOP/XEP renderers the
  pagination check had never seen before the fix above.

## Bugs found and fixed, in order

1. **`has_reliable_pagination()` misrouted genuinely clean PDFs**: 2 of
   the first 3 real papers came from Apache FOP/XEP, renderers the
   marker list didn't recognize, sending them to expensive page-by-page
   vision transcription for no reason. Fixed by extending the marker
   list -- a two-line fix that also benefits academic-hub's own notes
   pipeline.
2. **`known_doc_types` wasn't parameterized**: mirrored the exact fix
   `essays/convert_essays.py` needed one layer down, in
   `index_card.py`'s `generate_index_card()`.
3. **An oversized document (a 402-page monograph) sat in the corpus
   alongside genuine ~20-page papers** before the `--max-pages` guard
   existed. Fixed by flagging and skipping anything over the threshold
   entirely, rather than auto-escalating it to the GPU pipeline.

## Known, not yet fixed

- **`page_looks_defective()`'s heuristics are tuned against LaTeX-typeset
  math lecture notes, not academic-paper prose.** They flag a real,
  substantial fraction of pages in every one of the 4 real papers tested
  (32-43%), enough to push all of them into whole-document Gemini
  batching rather than the cheaper hybrid-repair tier. Likely candidates
  are citation/footnote/DOI conventions this checker has never seen.
  Not fixed: whole-document batching is still correct and still cheap
  (~$0.02/paper at real per-page rates), but this corpus isn't hitting
  the free tier as often as its clean PDF metadata alone would suggest.
- **No live transcription-quality comparison against a dedicated OCR
  provider** (Mathpix, Mistral) has ever been run -- the conclusion that
  Gemini is cheaper here is pricing-based only, not empirical accuracy.

## What's next

Both the essays and journal-article corpora are still fixed local
folders, hand-run rather than watching a live source. The plan is to
fold in a proper literature-review workflow once there are enough
papers indexed to make one worth building -- see
`docs/2026-09-01-research-notes-conversion-status.md`'s "What's next"
for the shared roadmap. A separate `journal_discovery/` subproject
(automatically finding and downloading candidate papers, rather than
hand-populating this folder) is in active development and not yet
covered by a status doc here.
