# Textbook Conversion (Marker, GPU)

Converts large, figure- and math-heavy textbook PDFs into structured
Markdown using the [Marker](https://github.com/VikParuchuri/marker)
layout/OCR model, run on a spot GPU VM in Google Cloud — the most expensive
step in this whole project, so it's reserved for files that actually need
GPU-grade layout parsing (a few hundred pages, multi-column, heavy math),
not short documents. See the root [`gcp_instructions.md`](../gcp_instructions.md)
for the full step-by-step guide (one-time GCP setup, VM creation, running a
batch, troubleshooting) — this file is a quick orientation, not a
replacement for it.

## Key files

- `convert_textbook.py` — orchestrates the Marker conversion; runs on the VM.
  Loads Marker's vision models once and reuses them across every book in a
  batch. Chunk boundaries align to real chapter breaks by default (sourced
  from the PDF's embedded outline or its own printed table of contents), and
  every output page carries a `<!-- page N -->` tag plus, where derivable, a
  `<!-- folio N -->` tag (the book's own printed page number).
- `chapter_index.py` / `page_markers.py` — the chapter-boundary detection and
  page/folio tagging machinery `convert_textbook.py` builds on. Any span that
  can't be chapter-aligned falls back to a live safety probe that shifts the
  cut away from anything that looks like a mid-table or mid-formula split.
- `describe_images.py` — local-only, no GPU needed: a follow-on pass that
  filters out decorative images (covers, logos) for free using the chapter
  boundary above, then describes the rest via one combined Gemini call per
  image, writing a derived `.rag.md` file (the original conversion output is
  never touched).

Deploys alongside `common/` and `indexer/` (which it imports) to the GPU VM —
see `marker_setup.sh` and the root [`README.md`](../README.md)'s repository
layout for the full picture. Only files actually sitting in `academic-hub/`'s
own folder structure ever run through this pipeline — other subprojects
(`notes/`, `essays/`, `journal_articles/`) deliberately never auto-escalate
here.
