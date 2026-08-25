# Notes Transcription: Status Summary

Start here for "what happened and where do we stand" on the notes-transcription
subproject -- `transcribe_notes.py`, which converts short, non-textbook academic
PDFs (problem sets, TA lecture notes, recitation slides, syllabi, handwritten
notes) into RAG-ready markdown. Sibling to `convert_textbook.py` (Marker-based,
tuned for printed-text OCR at textbook scale) and `describe_images.py` (see
`docs/2026-08-23-image-description-status.md`), but architecturally distinct:
this renders each page to an image and asks a vision-capable Gemini model to
transcribe it directly, since these documents have no table of contents, are
often too short to need chapter-aware chunking, and frequently mix typed and
handwritten content on the same page.

## What this project built

A three-tier router in `process_pdf()` that picks the cheapest approach a
document's actual content will support, decided per-document from PDF
metadata and (where safe) per-page local text extraction -- never a blanket
"always call the API" or "always try local first":

- **Tier 1 -- pure local extraction, 0 API calls.** Reliably-paginated
  (LaTeX/Word/LibreOffice), machine-generated, and every page's local
  `pypdf` text scores as clean. The PDF's own embedded text layer is trusted
  outright.
- **Tier 2 -- hybrid batched repair.** Reliably paginated, but some pages'
  local text is corrupted (garbled ligatures, dropped glyphs from large
  delimiter symbols, etc.) -- up to 35% of the document
  (`_MAX_DEFECT_RATIO_FOR_HYBRID`). Only the defective pages are sent to
  Gemini, grouped into contiguous runs and batched (up to 12 pages per call,
  `_MAX_BATCH_SIZE`) with bookend context from the surrounding clean pages,
  so a single document never needs more than a handful of API calls
  regardless of page count.
- **Tier 3 -- full Gemini transcription.** Either not reliably paginated
  (handwritten/messy exports: Nebo, MyScript, OneNote) or reliably paginated
  but too defective for hybrid repair to be worth it. Handwritten/messy
  documents use `gemini-3.6-flash` at 200 DPI with a sliding accumulating
  context window (see below); the too-defective-typeset case uses
  `gemini-3.1-flash-lite` at 150 DPI with no accumulation, since each page is
  independent once it's known to be machine-generated.

Every tier writes a YAML frontmatter block (`source_pdf`, `folder_category`,
`total_pages`, `routing`, `model`, `pages_repaired`/`repaired_pages`, a `tags:
[]` placeholder left for a future indexing pass) ahead of the markdown body,
so a downstream RAG indexer can filter or weight documents by how they were
produced without re-deriving that from content.

Everything except PyMuPDF page rendering, the Gemini network calls, and the
CLI driver is pure Python and independently unit-tested
(`tests/test_transcribe_notes.py`) -- 147 tests across the whole project as
of this writing, all passing.

## How the routing decision actually gets made

- **`has_reliable_pagination(metadata)`**: checks a messy-export denylist
  first and unconditionally (`nebo`, `myscript`, `onenote` in
  Producer/Creator) -- if any hit, the document is Tier 3 regardless of
  anything else. Only if that denylist misses does it check for positive
  evidence of normal pagination (`latex`, `pdftex`, `word`, `libreoffice`,
  `openoffice`).
- **`page_looks_defective(text)`**: three independent signals over a page's
  local-extracted text -- a run of 25+ pure-ASCII-alphabetic characters with
  no separators (collapsed prose, not legitimate dense math notation, which
  mixes in symbols/non-ASCII even when unspaced); more than 3 characters
  outside an allowlist covering ASCII plus the Unicode ranges real math
  notation actually uses (Mathematical Alphanumeric Symbols, Operators,
  Letterlike Symbols, Arrows, Greek and Coptic, ligatures, etc.); or the same
  non-alphanumeric, non-"legitimate-repeatable" character (`.-=_*#·` excluded)
  repeated 3+ times in a row.
- Both were tuned against real documents, not synthetic fixtures -- see
  Errors and fixes below.

## The sliding-window accumulation fix (this session's headline change)

Full accumulation -- every already-transcribed page resent as context on
every subsequent call -- is necessary for messy exports specifically because
a page's internal layout window can split a paragraph non-adjacently rather
than at a clean page boundary (confirmed against real OneNote exports).
But resending the *entire* document's transcript on every call means input
tokens grow with page count, confirmed on a real 25-page Nebo file
(`Aug 17 Analysis.pdf`): per-call input tokens climbed from 1,817 on page 1
toward 7,000+ by page 5 under full accumulation, on a trajectory toward
500K+ accumulated input tokens by page 25.

Since the paragraph-splitting behavior only ever spans adjacent pages, a
trailing window of the last `_ACCUMULATION_WINDOW = 3` transcribed pages
(instead of the whole document) preserves the same continuity. Confirmed
live on the same 25-page file: per-call input tokens now stay flat
(~1,300-2,700 across the whole document) instead of growing unbounded --
total 54,674 input + 7,408 output tokens for the full file (~$0.069 at
`gemini-3.6-flash` rates), versus a full-accumulation trajectory that would
have landed well over 3x higher on a document this length, and worse on
longer ones (the old cost curve was quadratic in page count; the new one is
linear).

Accuracy was verified two ways before trusting this: diffing a 5-page file's
output against its pre-change full-accumulation baseline (no content lost,
only cosmetic markdown-style variance between runs); and, on the 25-page
file, directly rendering a page well past where the window had dropped early
pages from context and confirming byte-for-byte-faithful transcription
against the actual page image (including one unusual page that turned out to
be a screenshot of a pasted AI-tutor explanation, transcribed verbatim).

Also added in this pass: real per-call token-usage logging
(`_log_token_usage`), since no part of the pipeline previously captured
`usage_metadata` at all -- prior cost figures were character-count guesses.

## Real-world validation

| Document | Pages | Tier | Result |
|---|---:|---|---|
| `LN_Analysis.pdf` | 155 | Hybrid | 36/155 pages repaired across 22 batches, 100% first-try batch success, 0 individual-repair fallbacks |
| `LN_Optimization.pdf` | 112 | Hybrid | 31/112 pages repaired across 21 batches, 100% first-try batch success, 0 individual-repair fallbacks |
| `LN_Linear Algebra.pdf` | 294 | Hybrid | Defect detection validated (28.9% defect rate after heuristic tuning); full live repair run not separately re-confirmed after the accumulation-window change (unaffected -- hybrid tier doesn't accumulate) |
| `Aug 17 Analysis.pdf` (Nebo) | 25 | Full/accumulating | First real transcription of this file; spot-checked accurate at both ends of the document |
| `Lecture_Notes_Aug_24_Probability Lecture.pdf` (OneNote) | 5 | Full/accumulating | Confirmed OneNote correctly forced to Tier 3 regardless of decent per-page local text, because local extraction silently drops all math content (see below) |

Content quality spot-checks across these runs found correct LaTeX
reconstruction of summations, multi-index Taylor's theorem, Lagrangian and
envelope-theorem notation, and matrices; the model has also spontaneously
described figures inline during repair calls without being asked to.

## A real finding that shaped the design: local text isn't uniformly useful

Investigated whether handwritten-note files could be split page-by-page into
"cheap to extract locally" vs. "needs the API," the same way typeset
documents are. Checked real Nebo/MyScript exports directly: every page's
local text is Nebo's *own* on-device handwriting-recognition guess embedded
as a hidden layer, not human-typed source -- already garbled
(`"1141, = Sup 1144111"`), worse than no context if used as free continuity
context, and pages with no recognized ink return 0 characters rather than
signaling "clean." No exploitable free tier exists in this file type.

OneNote exports are different again: prose paragraphs extract as genuinely
readable, correct text, but equation regions extract as *nothing at all* --
not garbled, silently blank. This matters because `page_looks_defective()`
can only detect corruption signals (garbled/unexpected characters,
collapsed runs); it has no way to detect content that's silently missing.
Confirmed directly: on a real OneNote file, 3 of 5 pages with entirely
missing math scored as "not defective." A hybrid approach applied to this
file type wouldn't just be less accurate -- it would confidently ship pages
with whole equations missing and no warning. This is why the messy-export
denylist in `has_reliable_pagination()` forces Tier 3 unconditionally,
rather than attempting per-page classification within these documents.

## Cost research: is a dedicated math-OCR API cheaper?

Investigated Mathpix Convert API ($0.005/page, or $0.0035/page at volume)
and Mistral OCR 4 ($0.004/page, $0.002/page with the batch discount) against
this project's actual Gemini-based cost. Working from real captured token
counts and confirmed `gemini-3.1-flash-lite` pricing ($0.25/M input, $1.50/M
output), the hybrid tier's per-repaired-page cost comes out to roughly
$0.0012-0.0013/page -- cheaper than both dedicated OCR providers, before
even counting that the hybrid design already restricts API calls to the
~23-35% of pages that actually need them, which a dedicated OCR provider
would need the same kind of pre-filter bolted on to match. Conclusion:
switching providers wouldn't reduce cost here; the batching + lite-model +
defective-pages-only design already captures more savings than a per-page
rate difference would buy back. No live quality test against a dedicated OCR
provider was run (would require a real signup/setup fee), so this
conclusion is on cost, not transcription quality, specifically.

Image-figure extraction (the `convert_textbook.py`/`describe_images.py`
pattern) was considered and not built for this pipeline: there's no
structured layout detection here to hang it off of, and figure descriptions
are already emerging for free, inline, as part of normal transcription (the
model has spontaneously captioned diagrams during repair calls).

## Key errors encountered and overcome

Roughly in the order they were hit:

1. **Sparse-sampling false negatives** (two real cases: a Nebo file with
   mostly-blank spacer pages, and unlucky evenly-spaced samples on
   `LN_Analysis`) -- both passed a 5-page sample check while real corruption
   existed elsewhere. Fixed by scanning every page (confirmed cheap, under
   10s even for 294 pages) and removing sampling entirely.
2. **`_RELIABLE_PAGINATION_MARKERS` too broad.** A bare `"microsoft"`
   matched `"Microsoft® OneNote®"`, misclassifying the canonical
   messy-export case as reliably paginated. Fixed with an explicit
   denylist checked first.
3. **Defect-detection allowlist far too narrow.** Initially flagged
   148/294 real `LN_Linear Algebra` pages as defective -- missing Greek
   letters, angle brackets, primes, dagger, and treating single-occurrence
   ligatures (`ﬁ` in "significant") as corruption. Fixed by adding the
   correct Unicode ranges and separating "one occurrence is normal
   typography" from "a repeated run is corruption."
4. **Long-word check flagged legitimate dense equations** -- real,
   confirmed-clean content
   (`𝑓(𝑎+ℎ)=𝑓(𝑎)+∇𝑓(𝑎)·ℎ+𝑜(∥ℎ∥)`) was flagged as collapsed prose. Fixed
   by requiring the long run to be pure ASCII letters, since real math
   notation mixes in symbols even when unspaced.
5. **Repeated-char-run check flagged page numbers and roman numerals**
   (`"111"`, `"III"`). Fixed by excluding ASCII alphanumerics from that
   specific check.
6. **A stale cache silently produced a false-negative "success."** An
   earlier pre-refactor cache file already had every page cached, so a
   "successful" hybrid run made zero real API calls and validated nothing.
   Diagnosed by the absence of any "repaired via batch" log lines; fixed by
   renaming the stale cache aside and re-running.
7. **`gemini-3.6-flash-lite` doesn't exist** -- a real 404, confirmed via
   both the live API and a web search; Google's lite tier stayed at 3.1
   while the main Flash line moved to 3.6. Corrected the constant.
8. **A "Unicode corruption" that was never real.** `�` appeared in printed
   console output at three points across two documents and was assumed to
   be U+FFFD replacement-character corruption; a fix
   (`text.replace("�", "—")`) was written and committed before
   directly checking the actual codepoint, which turned out to be a
   completely correct U+2014 em-dash every time -- a console-rendering
   artifact, not data corruption. No file was ever damaged (the "cleanup"
   script's own search-and-replace correctly found zero real matches each
   time). The fix was left in place as a harmless no-op rather than
   reverted, since it does target genuine U+FFFD and costs nothing.
9. **Full-accumulation quadratic cost growth** (this session, see above) --
   fixed via the sliding context window.

## Remaining open items

- The Tier 3 "reliably paginated but too defective for hybrid" fallback
  branch (`defect_ratio > _MAX_DEFECT_RATIO_FOR_HYBRID`) is unit-tested but
  has never been exercised live -- no real document tested so far has
  exceeded ~29% defective.
- `marker-conversion-notes-transcription` has not been merged back into
  `marker-conversion` (or `main`, which is the branch linked from the public
  website). As of this writing the branch also has one local commit (the
  sliding-window change) not yet pushed to its remote.
- No live quality comparison against a dedicated OCR provider (Mathpix,
  Mistral) has been run -- the cost analysis above is pricing-based, not an
  empirical accuracy comparison.
