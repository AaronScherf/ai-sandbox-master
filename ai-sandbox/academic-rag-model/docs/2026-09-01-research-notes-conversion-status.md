# Research Notes Conversion (Essays): Status Summary

Start here for "what happened and where do we stand" on the essays
subproject -- `essays/convert_essays.py`, which converts short prose
`.docx` documents (statement-of-purpose / application essays, loose
research notes) into Markdown and reconciles them into the source
indexer. Companion doc: `essays_instructions.md`.

Unlike the PDF pipelines this project started with, a `.docx` already
carries its own structure -- headings, bold/italic runs, lists -- in the
file format itself. There's no OCR problem to solve and no GPU needed:
`mammoth` (a pure-Python library, no external binary dependency) reads
that structure directly into Markdown, entirely locally. The conversion
itself makes no API calls; indexing (one Gemini generation call + one
embedding call per new/changed file) is a separate, skippable step
(`--no-index`).

## What shipped

- **`mammoth`-based conversion** (`convert_docx_to_markdown`), reading a
  `.docx`'s paragraph styles directly into Markdown, no chunking or page
  markers needed since these are short, single documents.
- **Escaping fix** (`_unescape_markdown`): mammoth's writer defensively
  backslash-escapes ordinary punctuation everywhere in the text, not
  just where it would actually be ambiguous (e.g. a literal `1.` at the
  start of a line) -- so "well-known" and "the U.S." came out as
  `well\-known`/`the U\.S\.` across every converted file. Confirmed safe
  to invert unconditionally: none of these essays have a real paragraph
  starting with a literal `1.` or `-`, the one case the escaping exists
  to protect against.
- **Source-indexer integration** (`_index_essay`), reusing
  `indexer/index_card.py`'s `reconcile_and_write()` completely
  unchanged -- it was already generic on its root-directory argument,
  not hardcoded to `academic-hub`. `course` is derived from the essay's
  path relative to `--index-root` (`derive_course()`, unmodified).
- **`known_doc_types` generalized** on `reconcile_and_write()`: the
  academic-hub corpus's own vocabulary
  (`textbook`/`problem_set`/`ta_notes`/`handwritten_notes`) was
  hardcoded into `generate_index_card()`'s prompt, so every essay got
  force-fit into `textbook` or `handwritten_notes` before this fix. This
  script now passes its own `{"personal_essay", "research_notes"}` set.
- **Multi-root query support**: `search`, `search_passages`, and the
  tutoring agent now take a list of corpus roots instead of one, so a
  query can span `academic-hub` and `research/` together. Candidates are
  tracked as `(root, course)` pairs rather than a bare course name, since
  two unrelated corpora can each have a course literally called `notes`.
- **Paragraph-tier chunking** (`_split_by_paragraphs` in
  `indexer/chunk_index.py`): the chunker's fallback tier was built
  around the PDF pipelines' `<!-- page N -->` markers, which a
  `.docx`-derived document has none of -- it was silently producing one
  giant "page" span with no page number to cite, which
  `_render_citation` then printed as an empty label. A genuine paragraph
  tier now fills that gap, numbering paragraphs 1-indexed so a citation
  reads like `¶3` or `¶2-4`. Heading-tier citations still take priority
  when a document has real structure; paragraph is specifically the
  last-resort fallback, not a length-based rule.

## Real-corpus validation

Confirmed live against the real 19-file essays/research-notes corpus
(2026-08-30), not synthetic fixtures:

- `retag` produced 5 real tags (`phd-admissions`,
  `development-economics`, `climate-adaptation`,
  `data-science-methods`, `heterodox-economics`) covering every card,
  0 fallbacks needed.
- A full re-index after the `known_doc_types` fix correctly classified
  every file as `personal_essay` or `research_notes`.
- Two genuinely different questions run against both corpora in one
  call each surfaced only the correct corpus's results -- a
  linear-algebra query stayed confined to Academic Hub, a "PhD
  statement of purpose" query stayed confined to this corpus -- real
  topic-based federation, not one root silently winning by default.
- Re-running the exact tutoring question that surfaced the empty-label
  citation bug produced well-formed `¶`-style citations across the
  board after the paragraph-tier fix shipped.

## Bugs found and fixed, in order

1. **Mammoth's defensive escaping was leaking into every converted
   file** (found before this subproject's own indexing existed): fixed
   with `_unescape_markdown`, confirmed safe against the real corpus
   (no paragraph starts with a literal `1.` or `-`).
2. **`retag`'s frontmatter write-back silently skips any file without a
   `tags:` line**: the notes pipeline's own convention (`tags: []` in
   frontmatter) had to be matched exactly, or a real essay would never
   get its mined tags patched back in.
3. **`doc_type` classification was force-fitting every essay into the
   wrong academic-hub vocabulary** (confirmed live against the real
   19-file corpus before the fix: every card landed on `textbook` or
   `handwritten_notes`) -- fixed by making `known_doc_types` a parameter
   instead of a hardcoded constant, with zero effect on Academic Hub's
   own existing behavior.
4. **A query spanning two corpora risked reading the wrong shard**:
   two unrelated corpora can each have a course literally called
   `notes`, so candidates now carry `(root, course)`, not a bare course
   name.
5. **Citations came back with an empty label for every `.docx`-derived
   document**: the chunker's page-based fallback tier assumed page
   markers that a `.docx` doesn't have. Fixed with the paragraph tier
   described above.

## What's next

Still growing, not finished: today the essays corpus is a fixed local
folder, hand-run rather than watching a live source. The plan is to
pull loose-form research-idea essays directly from Google Drive instead
of a manually-populated folder, and to fold in a proper literature-review
workflow once there are enough papers indexed (see
`docs/2026-09-01-journal-article-transcription-status.md`) to make one
worth building. The document-type vocabulary is already built to be
extended per corpus rather than shared, so whatever comes next slots in
the same way `personal_essay`/`research_notes` already did, with no
changes needed to the retrieval layer underneath.
