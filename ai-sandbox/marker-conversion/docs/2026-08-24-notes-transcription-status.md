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
  (LaTeX/Word/LibreOffice), machine-generated, and every page's local text
  scores as clean. The PDF's own embedded text layer is trusted outright.
  As of 2026-08-25, local extraction goes through PyMuPDF rather than
  pypdf -- see "Local extraction fidelity" below.
- **Tier 2 -- hybrid batched repair, or whole-document batching.** Reliably
  paginated, but some pages' local text is defective (garbled ligatures,
  dropped glyphs from large delimiter symbols, or -- as of 2026-08-25 -- a
  lost exponent/subscript no plain-text extraction can represent). Up to
  `_MAX_DEFECT_RATIO_FOR_HYBRID` (10% as of 2026-08-25, was 35%) of the
  document, only the defective pages are batched to Gemini (up to 12 pages
  per call, `_MAX_BATCH_SIZE`) with bookend context from the surrounding
  clean pages. Over that threshold, the whole document is batched through
  Gemini instead -- see "Local extraction fidelity" below for why.
- **Tier 3 -- full Gemini transcription, accumulating context.** Not
  reliably paginated (handwritten/messy exports: Nebo, MyScript, OneNote).
  Uses `gemini-3.6-flash` at 200 DPI with a sliding accumulating context
  window (see below). As of 2026-08-25 this tier is exclusively the
  messy-export case -- the reliably-paginated-but-too-defective case that
  used to fall through to here (page-by-page, no accumulation) now has its
  own whole-document-batched Tier 2 path instead.

Every tier writes a YAML frontmatter block (`source_pdf`, `folder_category`,
`total_pages`, `routing`, `model`, `pages_repaired`/`repaired_pages`, a `tags:
[]` placeholder left for a future indexing pass) ahead of the markdown body,
so a downstream RAG indexer can filter or weight documents by how they were
produced without re-deriving that from content.

Everything except the PyMuPDF calls (page rendering and, as of 2026-08-25,
local text extraction -- see below), the Gemini network calls, and the CLI
driver is pure Python and independently unit-tested
(`tests/test_transcribe_notes.py`) -- 150 tests across the whole project as
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
| `Practice Sheet.pdf` | 43 | Whole-document batched (2026-08-25) | 63% defect ratio (2 corruption + 27 lost-exponent) crossed the new 10% threshold; 4/4 batches succeeded first try, 43/43 pages transcribed, $0.024 total (48,527 input + 7,613 output tokens) |

Content quality spot-checks across these runs found correct LaTeX
reconstruction of summations, multi-index Taylor's theorem, Lagrangian and
envelope-theorem notation, and matrices; the model has also spontaneously
described figures inline during repair calls without being asked to.

## Local extraction fidelity: PyMuPDF, a fourth defect signal, and whole-document batching (2026-08-25)

Manually reviewing `Practice Sheet.pdf`'s Tier 2 (hybrid) output surfaced
two separate, real quality problems with what the local-extraction tiers
had been shipping as "clean" text -- neither was a false negative in the
sense of prior bugs (garbled/wrong output that should have been caught);
both were content that read as perfectly normal prose but was silently
worse than it should have been.

**1. pypdf collapses inter-word spacing that PyMuPDF preserves.** Confirmed
directly: pypdf's `PdfReader.extract_text()` on `Practice Sheet.pdf` page 1
produced `"LetVbe a finite-dimensional real vector space and letT:V->Vsatisfy"`
-- every space between certain word/symbol boundaries silently dropped.
PyMuPDF's `page.get_text()` on the identical page produced the correct
`"Let V be a finite-dimensional real vector space and let T : V ->V satisfy"`.
Measured across ~1,150 real pages spanning 10 documents (this project's
own problem sets and LaTeX-sourced lecture notes): PyMuPDF was **never**
worse than pypdf, and recovered the bug entirely on documents where pypdf
had it badly (88->0 hits on Practice Sheet, 152->0 on `LN_Linear Algebra.pdf`,
77->2 on `LN_Analysis.pdf`, using a `[a-z]{2,}[A-Z]` collapsed-boundary
proxy check). The two residual "ties" found (`dimG`, `imA`) are identical
in both extractions -- the PDF itself never encodes a space there at all,
so no text-extraction library can recover it locally. Local extraction
(Tier 1/2, and Tier 3's per-page hint) now goes through PyMuPDF instead of
pypdf; pypdf stays in use only for page count and metadata
(`has_reliable_pagination`). See `extract_all_page_texts`/`extract_page_text`.

**2. Plain-text extraction cannot represent a superscript or subscript at
all**, regardless of which library does the extracting -- this is a
structural limitation, not a bug either library could fix. `D^5` and `R^2`
both extract as bare `D5`/`R2`; the vertical-offset/font-size information
that would distinguish an exponent from ordinary adjacent characters
simply isn't in plain-text output. A regex proxy for this
(`\b[A-Za-z]\d\b`, word-boundary-anchored on both ends) was tuned against
real documents before shipping: a looser, unanchored version
(`[A-Za-z]\d`) was confirmed to false-positive constantly against embedded
comment/hyperlink hash IDs in `Real Analysis Problem Set_Solutions.pdf`
(e.g. `...app/06b7ab97dac5cbbb>`, which alternates letters and digits with
no boundary anywhere inside the run) -- inflating that file's apparent
defect rate from a true 0% to a spurious 50%. The word-boundary-anchored
version eliminated that false positive entirely while still catching every
real case checked by hand (`x2`->x², `D5`->D^5, `R2`->R^2, `P4`->P₄, `K2`->K₂).
Known, accepted gap: it only catches a digit standing alone between
boundaries, not one sandwiched inside a longer token (`x2y` for x²y) --
widening it to catch that case would reopen the same hash-string
false-positive risk. Added as a fourth signal in `page_looks_defective()`
(alongside the three existing corruption checks), via
`_LOST_EXPONENT_OR_SUBSCRIPT_RE`.

**3. `_MAX_DEFECT_RATIO_FOR_HYBRID` lowered from 0.35 to 0.10, and the
"too defective for hybrid" fallback now batches the whole document instead
of looping page-by-page.** Reasoning: with real per-page cost measured at
~$0.0007/page (`gemini-3.1-flash-lite`), fully transcribing a ~40-page
document costs a few cents regardless -- there's little to gain from
preserving free local extraction on a document that's already shown real
defects, since any confirmed defect is evidence about that specific PDF's
own production quirks (font encoding, or the same kind of intrinsic
notation loss item 2 describes) that plausibly affects other pages too,
not just the ones any one heuristic happened to flag. Checked against
real per-document defect rates before picking 10%: the distribution is
sharply bimodal, not a continuum needing a finely-tuned cutoff -- documents
are either genuinely clean (0% on every signal: `old_exam_2021.pdf`,
`old_exam_2025.pdf`, `old_problem_set.pdf`, `Real Analysis Problem
Set_Solutions.pdf`) or clearly over any reasonable threshold (23-29%
corruption-only on all three already-hybrid-repaired `LN_*.pdf` lecture
files, even before counting the new lost-exponent signal; 63% on Practice
Sheet once it's counted). At 10%, all three `LN_*.pdf` files and Practice
Sheet now escalate to whole-document batching; the previously-untested
"too defective for hybrid" fallback branch (flagged in the prior version
of this doc as never having been exercised live) is now exercised for
real, via Practice Sheet.

The new path (Tier 2, whole-document batched) reuses the exact batching
machinery already built for hybrid repair (`split_run_into_batches`,
`_repair_batch`, `build_batch_transcription_prompt`) applied to every page
of the document instead of only the flagged runs -- no bookend context
(there's no "known-clean neighbor" left to borrow from) and no
accumulation (reliable_pagination still means pages are independent). This
also replaces what used to be an untested, page-by-page-only fallback
loop with something that shares real, already-validated code. New routing
value: `gemini_batched`.

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

- ~~The Tier 3 "reliably paginated but too defective for hybrid" fallback
  branch... has never been exercised live~~ -- **resolved 2026-08-25**: that
  branch no longer exists as page-by-page transcription; it's now the
  whole-document-batched Tier 2 path, exercised live and confirmed working
  against `Practice Sheet.pdf` (see above).
- The lost-exponent/subscript signal (`_LOST_EXPONENT_OR_SUBSCRIPT_RE`) is a
  known-partial proxy by design: it only catches a digit standing alone
  between word boundaries (`D5`, `R2`), not one sandwiched inside a longer
  token (`x2y` for x²y). Widening it would reopen the hash-string
  false-positive risk that motivated anchoring it in the first place (see
  above). Not planned to be fixed further -- accepted as a known gap.
- Recovering real exponent/subscript structure (rather than just detecting
  its absence) would need PyMuPDF's structured (`"dict"`/`"rawdict"`) text
  mode, which exposes per-span font size and baseline position -- a
  genuinely local, free fix, but a substantially bigger feature than the
  detection heuristic above. Not built; flagged here as a real option if
  the Gemini-routing approach ever needs to be cheaper still.
- `marker-conversion-notes-transcription` has not been merged back into
  `marker-conversion` (or `main`, which is the branch linked from the public
  website).
- No live quality comparison against a dedicated OCR provider (Mathpix,
  Mistral) has been run -- the cost analysis above is pricing-based, not an
  empirical accuracy comparison.
