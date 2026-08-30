# Essay (.docx) Conversion Pipeline

Companion to `notes_instructions.md`, for a simpler input format: short
prose `.docx` documents (statement-of-purpose / application essays) that
carry their own structure (headings, bold/italic, lists) in the file
format itself. No OCR, no vision model, no GCP VM -- it's a pure-Python
conversion using [mammoth](https://github.com/mwilliamson/python-mammoth).
The conversion itself makes no API calls; by default each converted
file is *also* reconciled into its own source-indexer card (one Gemini
generation call + one embedding call per new/changed file -- pass
`--no-index` to skip this and stay fully local/free).

## Step 1: One-time local setup

```powershell
cd marker-conversion
pip install mammoth
```

## Step 2: Run it

Batches over every `.docx` found directly under the target folder.

```powershell
python -m essays.convert_essays
```

* Defaults to `research/independent-research/notes/application_essays`
  (the folder next to this project). Pass `--essays-dir <path>` to
  point at a different folder.
* Add `--file "Statement of Purpose - Harvard.docx"` to convert just one
  file instead of the whole folder.
* Add `--dry-run` to see which files would be converted without writing
  anything.
* Add `--output-dir <path>` to write output somewhere other than
  `<essays-dir>/processed_outputs` -- useful for consolidating several
  `--essays-dir` subfolders (e.g. `application_essays/` and other
  folders under a shared `notes/` parent) into one output location.
* Output: `processed_outputs/<name>.md` (or `--output-dir`), one file per input `.docx` --
  a small YAML frontmatter block (`source_docx`, `word_count`,
  `conversion_warnings`, `tags`) followed by the converted Markdown
  body, same `processed_outputs/`-alongside-the-input convention as the
  notes pipeline. `tags: []` matches the notes pipeline's own
  convention so `retag`'s frontmatter write-back (see below) can patch
  it in place.
* Add `--index-root <path>` to change where the source-indexer's
  `.index/` lives (default: `research/`, sibling of `academic-hub/`).
  Add `--no-index` to skip indexing entirely (no Gemini calls, no
  `.index/` writes) -- just convert.

## How it works

`mammoth.convert_to_markdown()` reads the `.docx`'s own paragraph
styles (Heading 1/2/..., bold/italic runs, bulleted/numbered lists)
directly into Markdown. Its writer also defensively backslash-escapes
punctuation like `.`/`-`/`(` everywhere in ordinary text (not just
where it would actually be ambiguous, e.g. a literal `1.` at the start
of a line) -- `convert_docx_to_markdown` inverts that escaping
afterward (`_unescape_markdown`) so the output reads as plain prose,
confirmed safe against this corpus since none of these essays have a
real paragraph starting with a literal `1.` or `-` (the case the
escaping exists to protect against).

No chunking or page markers -- these are short, single documents, no
need for `textbook/`'s chapter-boundary machinery. Indexing reuses
`indexer/index_card.py`'s `reconcile_and_write()` completely unchanged
(it's already generic on its root-directory argument, not hardcoded to
`academic-hub`) -- `_index_essay()` in `convert_essays.py` is a ~15-line
hook mirroring `notes/transcribe_notes.py`'s own `_write_markdown_and_index`,
called live per file rather than needing a separate `rebuild` backfill
pass (this converter already visits every file itself). `course` is
derived from the essay's path relative to `--index-root`
(`derive_course()`, unmodified) -- with the default `research/` root,
everything under `independent-research/notes/**` resolves to course
`notes`, regardless of nesting.

Once indexed, `python -m indexer.index_search --academic-hub research
{query,retag,chunk,ask}` all work unmodified against this corpus (that
flag is just a root path, not literally tied to the academic-hub
folder). Confirmed live against the full 19-file real corpus
(2026-08-30): `retag` produced 5 real tags (`phd-admissions`,
`development-economics`, `climate-adaptation`, `data-science-methods`,
`heterodox-economics`) covering every card with 0 fallbacks, and
`query` returns sensible semantic matches. One known rough edge:
`generate_index_card()`'s prompt constrains `doc_type` to
`{textbook, problem_set, ta_notes, handwritten_notes}` -- an
academic-hub-specific enum with no "personal essay" option, so every
essay gets force-fit into one of those (cosmetically wrong, doesn't
affect search/tags since those key off the embedding, not `doc_type`).
`rebuild` was *not* generalized -- its directory-walk
(`_notes_pdf_paths`/`_textbook_book_dirs`) is still hardcoded to the
`academic_notes/`/`academic_resources/` layout and won't discover this
corpus; not needed as long as the live hook covers every conversion.
