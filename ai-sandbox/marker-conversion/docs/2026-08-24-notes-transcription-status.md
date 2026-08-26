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
| `LN_Analysis.pdf` | 155 | Hybrid (pre-dict-mode; **on hold, see below**) | 36/155 pages repaired across 22 batches, 100% first-try batch success, 0 individual-repair fallbacks. Not re-run since -- current `.md` on disk still reflects this state. |
| `LN_Linear Algebra.pdf` | 294 | Hybrid (pre-dict-mode; **on hold, see below**) | Defect detection validated (28.9% defect rate after heuristic tuning); full live repair run not separately re-confirmed after the accumulation-window change (unaffected -- hybrid tier doesn't accumulate). Not re-run since -- current `.md` on disk still reflects this state. |
| `Aug 17 Analysis.pdf` (Nebo) | 25 | Full/accumulating | First real transcription of this file; spot-checked accurate at both ends of the document |
| `Lecture_Notes_Aug_24_Probability Lecture.pdf` (OneNote) | 5 | Full/accumulating | Confirmed OneNote correctly forced to Tier 3 regardless of decent per-page local text, because local extraction silently drops all math content (see below) |
| `LN_Optimization.pdf` | 112 | Whole-document batched (2026-08-26) | 20% defect ratio crossed the 10% threshold; 10 batches, one batch (pages 1-12) came back missing pages and correctly fell back to individual per-page calls, rest succeeded first try; 112/112 pages transcribed |
| `LN_Probability.pdf` | 86 | Whole-document batched (2026-08-26) | 36% defect ratio crossed the 10% threshold; 8 batches, one batch (pages 1-12) came back missing pages and correctly fell back to individual per-page calls, rest succeeded first try; 86/86 pages transcribed |
| `Practice Sheet.pdf` | 43 | Whole-document batched, then **reclassified to Hybrid after the dict-mode fix (2026-08-26)** | Originally: 63% defect ratio crossed the 10% threshold, 4/4 batches succeeded first try, 43/43 pages transcribed, $0.024 total. After dict-mode recovered most lost exponents locally: defect ratio dropped to 5%, correctly re-routing to targeted hybrid repair (2 pages); re-run for real at zero additional cost since both defective pages were already cached |
| `Analysis_Exercises.pdf` | 11 | Hybrid (2026-08-26, dict-mode) | Predates the hybrid/local-tier feature entirely (originally 100% full-Gemini, no frontmatter). After dict-mode: defect ratio 9% (down from a hypothetical 73% under the old plain-text heuristic), correctly routes to hybrid (1 page); re-run for real at zero additional cost (already cached) -- also gained frontmatter it never had before |

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
not just the ones any one heuristic happened to flag.

*Correction (2026-08-26), caught during a completion review:* the
original version of this paragraph claimed `old_exam_2021.pdf`,
`old_exam_2025.pdf`, `old_problem_set.pdf`, and `Real Analysis Problem
Set_Solutions.pdf` were "genuinely clean (0% on every signal)" documents
demonstrating a bimodal defect-rate distribution. That was wrong, and the
error was in how the check was done: those percentages came from running
the defect regexes directly against `PyMuPDF`-extracted text in a
standalone script, without first checking whether `has_reliable_pagination()`
would even let the document reach that check in the real pipeline. Re-run
via `--dry-run` against the actual `process_pdf()` code: all four of those
files -- along with `Linear Algebra Problem Set.pdf`,
`Linear Algebra Problem Set AMS Solutions.pdf`, and all six "Part I/II"
files -- are Nebo or OneNote exports (`/Creator: Nebo` /
`Microsoft(R) OneNote(R)`), so `has_reliable_pagination()` is `False` for
every one of them; they were never candidates for local extraction or the
defect-ratio check at all, and were already fully transcribed via Tier 3
(`gemini_accumulating`) independent of anything in this section.

The real picture, as it stood before the dict-mode work below (2026-08-26
superseded this -- see that section): of the documents in this corpus,
only six are actually `reliable_pagination=True` (machine-generated,
LaTeX-sourced) at all -- `Analysis_Exercises.pdf`, `Practice Sheet.pdf`,
and the four `LN_*.pdf` lecture-note files. At that point all six crossed
the 10% threshold: `Analysis_Exercises.pdf` 73%, `Practice Sheet.pdf` 63%,
`LN_Probability.pdf` 36%, `LN_Linear Algebra.pdf` 32%,
`LN_Optimization.pdf` 20%, `LN_Analysis.pdf` 17% (these last three differ
from the 23-29% corruption-only figures reported earlier in this doc, both
because they now include the lost-exponent signal and because the PyMuPDF
extraction switch changed the corruption-only count too). The
previously-untested "too defective for hybrid" fallback branch (flagged in
an earlier version of this doc as never having been exercised live) was
exercised for real via Practice Sheet at this point.

**Status update (2026-08-26): two of the four `LN_*.pdf` files are now
processed, two remain on hold.** `LN_Probability.pdf` and
`LN_Optimization.pdf` were re-run via the whole-document-batched path --
both succeeded (see the Real-world validation table below; `LN_Probability`
exercised the individual-repair fallback for real for the first time, after
its first batch's response came back missing pages). `LN_Analysis.pdf` and
`LN_Linear Algebra.pdf` remain untouched -- deliberately put on hold
pending a final review before spending more on API calls, not because of
any known issue. See "Remaining open items."

The new path (Tier 2, whole-document batched) reuses the exact batching
machinery already built for hybrid repair (`split_run_into_batches`,
`_repair_batch`, `build_batch_transcription_prompt`) applied to every page
of the document instead of only the flagged runs -- no bookend context
(there's no "known-clean neighbor" left to borrow from) and no
accumulation (reliable_pagination still means pages are independent). This
also replaces what used to be an untested, page-by-page-only fallback
loop with something that shares real, already-validated code. New routing
value: `gemini_batched`.

## PyMuPDF dict-mode: recovering sub/superscripts locally, for free (2026-08-26)

Item 2 above ("plain-text extraction cannot represent a superscript or
subscript at all") was treated as a hard structural limit when it was
written. It isn't -- PyMuPDF's structured `"dict"` text mode exposes
per-span font size and vertical position, and a real span-level check
(`reconstruct_line_with_scripts()`) recovers the large majority of lost
exponents/subscripts locally, for zero API cost, rather than only
detecting their absence and routing to Gemini.

**Signal, confirmed on real spans from two different font families**
(Practice Sheet.pdf's Computer Modern, LN_Linear Algebra.pdf's TeXGyrePagellaX):
a genuine script span is both smaller than its line's dominant
(most-characters) size by more than `_SCRIPT_SIZE_RATIO` (0.85 -- real
cases measured ~0.73-0.77x) and vertically offset from that size's
baseline by more than `_SCRIPT_OFFSET_RATIO` (0.08 of the dominant size).
Size alone isn't sufficient: a real counter-case (`LN_Linear Algebra.pdf`,
a symbol font rendering "K" at 11.49pt against 10.91pt body text, same
baseline) confirmed a differently-sized span isn't necessarily script.
Consecutive same-direction spans group into one `^{...}`/`_{...}` run, so
a multi-character exponent doesn't come out as separate single-character
groups. Falls back to plain concatenation when no dominant size is
determinable -- can only add fidelity over the old plain-text behavior,
never regress it.

**Validated against real ground truth, not just spot-checked.** Practice
Sheet.pdf pages 1-2 and all 11 pages of `Analysis_Exercises.pdf` were
extracted via the new function and diffed against their already-correct
Gemini transcriptions (both documents' `.md` output was fully
Gemini-transcribed before this feature existed, so real ground truth was
sitting right there at zero additional cost). Every sub/superscript across
all 13 pages checked matched the ground truth in substance -- `D^5`,
`P_4`, `x^2/x^3/x^4`, `(I+D)^{-1}`, `R^n`, `x_1`, `f_x(0,0)`, `D_v f(0,0)`,
`H_f(x)`, `K_1 \supseteq K_2 \supseteq K_3` and more, across two different
documents/font families. Differences from Gemini's version are cosmetic,
not accuracy problems: no semantic LaTeX macros (`\mathbb{R}`/`\to`
instead of raw `R`/`→`), no `$...$` math-mode wrapping, no markdown
section headers -- dict mode reconstructs literal glyphs plus script
wrapping, it doesn't do semantic LaTeX translation the way Gemini does.

**A real bug found and fixed during validation:** `reconstruct_line_with_scripts()`
doesn't recursively re-nest a script inside another script -- a compound
subscript like `B_{infinity,r1}(x)` comes out as one flat group rather
than the fully-nested `B_{infinity,r_1}(x)`. This was making the residual
`_LOST_EXPONENT_OR_SUBSCRIPT_RE` check double-flag content that was
already fixed (just not maximally nested), inflating
`Analysis_Exercises.pdf`'s apparent remaining defect count from 1 page to
4. Fixed via `_has_lost_exponent_outside_scripts()`, which strips
already-produced `^{}`/`_{}` groups before that residual check runs.

**Known, accepted gap: fractions aren't recovered.** A fraction is a 2D
vertically-stacked structure spanning multiple PyMuPDF "lines" (numerator
and denominator as separate line objects), not a same-line span issue --
confirmed on Practice Sheet.pdf page 1, `v_+ = 1` / `2(v + Tv),` still
splits across lines. Not a regression: the original plain-text extraction
had this exact same problem before any of this session's changes.

**A new, previously-uncatalogued silent-corruption category found while
validating, not yet investigated further:** on `Analysis_Exercises.pdf`
page 6, a radical/square-root sign extracts as a plain ASCII `p`
(confirmed as the real codepoint, U+0070 -- not a console-rendering
artifact like the earlier em-dash false alarm). This evades all four
current `page_looks_defective()` signals: not a long run, not an
unexpected character (`p` is plain ASCII), not repeated, no adjacent
digit. A font-encoding/ToUnicode-mapping issue, predating this session's
work and not something dict-mode introduced -- it would have been present
in plain-text extraction too. Doesn't affect any real output currently
(`Analysis_Exercises.md` uses the correct cached Gemini content for that
page, unaffected). Scope/prevalence beyond this one instance not yet
investigated -- noted for the post-processing subproject (see "What's
next").

**Real effect on tier classification.** `Practice Sheet.pdf`'s defect
ratio dropped from 63% to 5%, and `Analysis_Exercises.pdf`'s from 73% to
9% -- both now correctly route to targeted hybrid repair instead of
whole-document batching. The four `LN_*.pdf` files barely moved (14-35%,
down from 17-36%), staying well over the 10% threshold, since their
defects are corruption-dominated rather than exponent-loss-dominated (on
`LN_Linear Algebra.pdf`, 70 of 93 originally-defective pages were
corruption-only, versus 13 exponent-loss-only). This confirms the 10%
threshold itself doesn't need adjusting -- the real gap between "should
stay local-ish" and "needs full Gemini" is still clean (5-9% vs. 14-35%),
just shifted from the original 5-9% vs. 17-36%.

**`Practice Sheet.pdf` and `Analysis_Exercises.pdf` were re-run for real
(local-only, zero new API calls)** to pick up the corrected tier
classification and frontmatter. One nuance worth recording: because both
files' caches already covered every page from their earlier full-Gemini
runs, the hybrid tier's `pages_text.update(cache)` step overrides the
freshly-extracted local text with the cached (already Gemini-correct)
content for every page -- so the re-run corrected the `routing`/
`pages_repaired` frontmatter to accurately reflect these are now
lightly- not heavily-defective documents, but the actual page *content*
in both files is unchanged, still sourced from the original full-Gemini
transcriptions (which are equal-or-better quality than dict-mode alone
would produce anyway, given the fraction-recovery gap above). Dict mode's
own quality is validated separately, above, via the direct
extraction-vs-ground-truth comparison.

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

- **`LN_Analysis.pdf` and `LN_Linear Algebra.pdf` need re-processing**
  (`LN_Optimization.pdf` and `LN_Probability.pdf` are done, see the table
  above) to get the whole-document-batched quality the other four
  reliably-paginated documents now have -- their current
  `processed_outputs/*.md` predate this session's PyMuPDF/dict-mode/
  threshold changes. Estimated well under $0.30 total for both combined
  (scaling from the other two files' real cost). **Deliberately on hold as
  of 2026-08-26** -- paused mid-run at the user's request pending a final
  review, not because of any known issue with either file.
- **Radical/square-root signs can silently extract as plain ASCII
  characters** (`p` observed on `Analysis_Exercises.pdf` page 6, confirmed
  as the real codepoint) -- a font-encoding/ToUnicode-mapping issue
  invisible to all four current `page_looks_defective()` signals (not a
  long run, not an unexpected character, not repeated, no adjacent digit).
  Predates this session, not a regression. Prevalence beyond this one
  instance not yet investigated. Earmarked for the post-processing
  subproject below rather than another bespoke detection regex --
  see "What's next."
- A doc-accuracy correction was needed 2026-08-26: an earlier version of
  this doc mischaracterized several Nebo/OneNote-export files as
  "genuinely clean, stays local" documents, when they're actually not
  reliably-paginated at all and were already being fully Gemini-transcribed
  via a completely different rule. See the "Correction" note above -- worth
  reading if citing this doc's numbers elsewhere.
- ~~Recovering real exponent/subscript structure... would need PyMuPDF's
  structured dict mode... Not built~~ -- **resolved 2026-08-26**: built,
  tested, and validated against real ground truth -- see "PyMuPDF
  dict-mode" above.
- ~~The Tier 3 "reliably paginated but too defective for hybrid" fallback
  branch... has never been exercised live~~ -- **resolved 2026-08-25**: that
  branch no longer exists as page-by-page transcription; it's now the
  whole-document-batched Tier 2 path, exercised live and confirmed working
  against `Practice Sheet.pdf`, `LN_Optimization.pdf`, and
  `LN_Probability.pdf`.
- The lost-exponent/subscript signal (`_LOST_EXPONENT_OR_SUBSCRIPT_RE`,
  now a residual check behind dict-mode reconstruction rather than the
  primary defense) is a known-partial proxy by design: it only catches a
  digit standing alone between word boundaries (`D5`, `R2`), not one
  sandwiched inside a longer token (`x2y` for x²y). Widening it would
  reopen the hash-string false-positive risk that motivated anchoring it
  in the first place (see above). Not planned to be fixed further --
  accepted as a known gap.
- `marker-conversion-notes-transcription` has not been merged back into
  `marker-conversion` (or `main`, which is the branch linked from the public
  website). **Deliberately held until the post-processing subproject below
  is further along** -- per-user decision 2026-08-26.
- No live quality comparison against a dedicated OCR provider (Mathpix,
  Mistral) has been run -- the cost analysis above is pricing-based, not an
  empirical accuracy comparison.

## What's next

A post-processing/error-correction subproject, scoped to notes-transcription
only (the textbook pipeline's output is expected to be meaningfully cleaner
already, given Marker's dedicated OCR and cleaner source typesetting --
though within- or across-textbook cross-validation is a real idea for
later). Motivation: several rounds of this session added increasingly
specific detection heuristics (word-boundary-anchored regexes, font-size/
baseline thresholds) each tuned against a handful of real examples --
useful, but a pattern worth stepping back from rather than continuing
indefinitely. Under discussion instead: a downstream correction pass over
already-produced `.md` output using a small text-only LLM, possibly
combining/cross-referencing multiple documents, perplexity-based
flagging of statistically anomalous passages, and using documents already
known well-transcribed (via `routing`/`pages_repaired` frontmatter) as
reference material. Brainstorming paused before a design was settled on
(scope confirmed: notes-transcription only) -- to resume on a new,
dedicated branch rather than continuing here.
