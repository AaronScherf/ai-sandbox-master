# Essay Conversion

Converts short prose `.docx` documents — statement-of-purpose / PhD
application essays, loose research notes — straight to Markdown. Unlike the
PDF pipelines elsewhere in this repo, a `.docx` already carries its own
structure (headings, bold/italic, lists) in the file format itself, so
there's no OCR problem to solve: no vision model, no GPU, entirely local. See
the root [`essays_instructions.md`](../essays_instructions.md) for the full
usage guide; this file is a quick orientation.

## Key file

- `convert_essays.py` — reads each `.docx` via
  [`mammoth`](https://github.com/mwilliamson/python-mammoth) and inverts its
  writer's defensive backslash-escaping (`well\-known` → `well-known`) so the
  output reads as plain prose. Indexing is a live hook per file (mirroring
  `notes/transcribe_notes.py`'s own), reusing the
  [Source Indexer](../indexer/)'s `reconcile_and_write()` completely
  unmodified except for its own `known_doc_types` vocabulary
  (`personal_essay`, `research_notes`) — that reuse is what proved the
  indexer's design generalizes past the one corpus (`academic-hub`) it was
  originally built for.

Depends on `common/` and `indexer/`. Part of a small, growing personal
research corpus alongside [`journal_articles/`](../journal_articles/) — see
the root [`README.md`](../README.md) for the full dependency graph.
