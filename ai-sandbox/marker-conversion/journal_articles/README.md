# Journal Article Conversion

Converts academic journal-article PDFs — typically short, born-digital,
publisher-rendered documents — into Markdown by reusing
[`notes/transcribe_notes.py`](../notes/)'s tiered pipeline directly, unchanged.
See the root [`journal_articles_instructions.md`](../journal_articles_instructions.md)
for the full usage guide; this file is a quick orientation.

## Key file

- `convert_journal_articles.py` — needed almost no new code: `process_pdf()`
  already does exactly what a journal article needs (tiered cost-routing,
  content-hash caching, indexing hook), so this just points it at a
  recursively-walked folder (journal articles live under thematic
  subfolders, e.g. `economics/`, that may nest further — unlike the flat,
  single-level folders the notes pipeline usually sees) with its own
  `known_doc_types={"journal_article"}`. A document over `--max-pages`
  (default 150) is flagged and **skipped entirely**, never converted — the
  GPU/Marker [`textbook/`](../textbook/) pipeline is the most expensive step
  in this whole project, and it only ever runs on files a human deliberately
  moves into `academic-hub/`'s own folder structure, never something this
  script triggers on its own.

Depends on `common/`, `indexer/`, and `notes/` (whose `process_pdf()` it calls
directly). Part of the same growing research corpus as
[`essays/`](../essays/) — see the root [`README.md`](../README.md) for the
full dependency graph.
