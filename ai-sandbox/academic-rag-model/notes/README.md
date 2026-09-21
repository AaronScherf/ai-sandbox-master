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

- `transcribe_excalidraw.py` (+ `excalidraw_chunking.py`) — a separate
  pipeline for handwritten Excalidraw canvases (`.excalidraw.md` +
  its plugin-auto-exported `.png` or `.svg`), not PDFs: chunk the tall
  canvas at whitespace gaps, transcribe each chunk via Gemini vision with a
  trailing-context window, then expand the terse transcription into
  cohesive prose. Writes `<name>.excalidraw.md` (raw) +
  `<name>.excalidraw.rag.md` (expanded, the RAG-canonical artifact).

- `route_notes_transcribe.py` — a deterministic, filetype-based router
  across every course under `academic_notes/`: finds source files (`.pdf`,
  or `.excalidraw.md` + its image sibling) with no existing output yet, and
  dispatches each to the matching pipeline above by extension alone — no
  LLM decides routing, so this is safe to run unattended
  (`python -m notes.route_notes_transcribe [--course NAME] [--dry-run] [--force]`).
  Re-verifies after each call that the expected output file actually landed
  on disk rather than trusting a "no exception raised" result.
