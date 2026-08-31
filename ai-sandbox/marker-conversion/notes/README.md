# Notes Transcription Pipeline

A cost-routed pipeline that turns short, unstructured academic PDFs — TA
notes, problem sets, exams, handwritten scans, and (via
[`journal_articles/`](../journal_articles/), which reuses this unchanged)
journal articles — into clean, LLM-ready Markdown. Runs entirely locally, no
GPU or VM needed. See the root [`notes_instructions.md`](../notes_instructions.md)
for the full usage guide; this file is a quick orientation.

## Key file

- `transcribe_notes.py` — `process_pdf()` is a three-tier router instead of
  always calling the API: a reliably-paginated, machine-generated document
  (LaTeX, Word, LibreOffice, or an academic-publisher renderer like Apache
  FOP/XEP) with a clean local text layer gets extracted for free, zero API
  calls; if some pages are defective, only those get batched to Gemini for
  repair using surrounding clean pages as context; and a genuinely messy or
  handwritten document goes through full vision transcription, page-by-page
  with a small sliding window of already-transcribed pages as context.
  `known_doc_types` is a parameter here (default: `academic-hub`'s own
  vocabulary), so a different corpus can classify into its own document
  types without forking this function — see `journal_articles/convert_journal_articles.py`
  for the one other real caller.

Depends on `common/` and `indexer/` (for its per-file indexing hook, via
`_write_markdown_and_index`). `postprocessing/postprocess_notes.py` is a
downstream correction pass over this pipeline's own output — see the root
[`README.md`](../README.md) for the full dependency graph.
