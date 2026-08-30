# Essay (.docx) Conversion Pipeline

Companion to `notes_instructions.md`, for a simpler input format: short
prose `.docx` documents (statement-of-purpose / application essays) that
carry their own structure (headings, bold/italic, lists) in the file
format itself. No OCR, no vision model, no GCP VM, no API calls -- it's
a pure-Python conversion using [mammoth](https://github.com/mwilliamson/python-mammoth).

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
* Output: `processed_outputs/<name>.md`, one file per input `.docx` --
  a small YAML frontmatter block (`source_docx`, `word_count`,
  `conversion_warnings`) followed by the converted Markdown body, same
  `processed_outputs/`-alongside-the-input convention as the notes
  pipeline.

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

No chunking, no page markers, no indexing hook into `indexer/` --
these are short, single documents with no course/textbook metadata to
derive, so this stays a standalone converter. Feed the resulting
`.md` files into `rag/rag_agent.py` or read them directly for analysis.
