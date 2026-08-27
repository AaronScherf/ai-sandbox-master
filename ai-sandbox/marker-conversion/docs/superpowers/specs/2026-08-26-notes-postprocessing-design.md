# Local-first post-processing for notes-transcription output

**Local-inference stack: HuggingFace `transformers` (PyTorch, CPU-only).**
Ollama was the original candidate (see the project's notes-transcription
status doc for that decision) but was dropped once verified against
Ollama's own official docs that neither its native nor OpenAI-compatible
API supports scoring caller-provided text (no `echo`/prompt-logprobs mode)
-- only probabilities for tokens the model generates itself, which doesn't
support the masked/perplexity scoring this design needs. `transformers`
was confirmed to support exactly this directly (see "Real-world
validation" below).

## Problem

`transcribe_notes.py`'s local-extraction tiers -- `routing: local` documents
entirely, and the non-`repaired_pages` majority of `routing: hybrid`
documents -- are never seen by any vision-capable model at all. A page
either passes `page_looks_defective()`'s four signals (collapsed prose,
unexpected characters, repeated-character runs, a lost exponent/subscript
outside an already-reconstructed script group) or it doesn't; if it passes,
it's trusted outright.

A real example (`Analysis_Exercises.pdf` page 6) showed this heuristic set
can miss a genuine, silent error: a radical/square-root sign extracts as
plain ASCII `p` -- invisible to all four current signals (not a long run,
not an unexpected character since `p` is plain ASCII, not repeated, no
adjacent digit). Each time a new failure mode like this has surfaced this
project's response has been another bespoke, narrowly-tailored detection
regex, tuned against the one or two real examples that exposed it
(word-spacing collapse -> switched extraction libraries; lost exponents ->
`_LOST_EXPONENT_OR_SUBSCRIPT_RE`; now this). That pattern doesn't scale to
failure modes not yet observed, and is the direct motivation for this
subproject: a downstream correction pass that can catch errors *by class*
rather than by bespoke signature, accepting that upstream transcription
won't be perfect rather than chasing zero mistakes with an ever-longer
heuristic list.

## Goals

- Catch errors on local-only pages without requiring every new failure mode
  to get its own bespoke detection regex.
- Auto-correct high-confidence findings directly into the `.md` files.
- Never spam per-instance review requests; surface a review prompt only when
  a document shows a *pattern* of similar lower-confidence findings, not for
  every individual flag.
- Reuse the textbook corpus and other already-processed notes as reference
  material for extra context, without depending on the not-yet-built RAG
  Analysis project.
- Run as its own follow-on pass (matching `describe_images.py`'s precedent
  for the textbook pipeline), batchable across multiple subdirectories in
  one invocation, automatically scoped to newly-transcribed files via
  existing frontmatter conventions rather than a separate state file.

## Non-goals

- Textbook output is not a correction target in this phase -- expected to
  be materially cleaner given Marker's dedicated OCR and cleaner source
  typesetting. Within- or across-textbook cross-validation (using one
  textbook to check another, or checking a textbook's own internal
  consistency) is a real idea, explicitly deferred to a later phase.
- Not building on RAG Analysis's vector retrieval, since that project is
  still in design and has no retrieval pipeline built yet. A lightweight,
  self-contained keyword/fuzzy search is used instead. If that proves
  insufficient once exercised for real, revisit using RAG Analysis's
  retrieval once it exists -- not a blocking dependency now.
- Not committing to one single "winning" detection mechanism. The spike
  behind this spec (see below) found real, complementary signal in more
  than one approach and a real failure in at least one intuitive one
  (a "smarter" model performing *worse*) -- per direction from this
  project's owner, multiple candidate signal sources are built into the
  same pipeline and evaluated empirically against real documents in
  production, rather than one being picked a priori from spike-scale
  synthetic tests.
- Not scoring or correcting pages that already went through Gemini
  (`repaired_pages`, or any page in a `gemini_batched`/`gemini_accumulating`
  document) -- those are already model-verified against the real source
  image; this subproject's whole reason to exist is the pages that never
  were.

## Real-world validation (spike findings)

Before committing to a design, a throwaway spike (`transformers` + CPU
inference, no project code changed) tested whether small-model-based
anomaly detection actually catches the real `p`-for-`\sqrt{}` bug, and
whether refinements to the naive version hold up. Findings:

**Causal (left-to-right) perplexity, GPT-2 (124M):** the bug token `'p'`
was the single most surprising token in a short isolated passage (12.51
nats), but ranked only 6th of the full real 523-token page -- outranked by
byte-level tokenizer artifacts from legitimate Greek letters (`\xi`, `\eta`)
elsewhere on the same page. A **position confound** also showed up
directly: in a separate clean prose passage, the sentence-initial word
`'Several'` (completely correct) scored *higher* surprisal (13.76 nats)
than the actual bug, since sentence-initial tokens have no preceding
context and are inherently harder to predict -- raw surprisal isn't safely
comparable across different snippets without accounting for this.

**Allowlist-filtering the candidate list** (excluding any token whose
source-text span is already covered by this project's existing
`_ALLOWED_MATH_RANGES`/`_is_expected_char`) **completely broke the ranking**
-- zero candidates survived, because `'p'` is plain ASCII and passes the
same allowlist as everything else. This is not a bug in the filter; it's a
real, informative negative result: the allowlist is built to catch
"legitimate rare Unicode symbol looks statistically surprising," which is a
*different* false-positive class from "an ordinary ASCII character is
substituted in and looks completely normal." Applying it to *this* failure
mode throws away the exact class of error being hunted.

**Local-window z-score** (score each token relative to its own
neighborhood's mean/stdev instead of the whole page) genuinely helped:
`'p'` moved from rank 6 to rank 3 of 523 with GPT-2. A real, if modest,
improvement.

**A math/STEM-adapted model (Qwen2.5-0.5B, confirmed real and downloadable
via HuggingFace, ~0.5B params) made detection *worse*, not better** --
`'p'` dropped to rank 20 (raw) / 15 (z-score). Read: a more capable,
better-calibrated model is *less* surprised by unusual tokens in dense math
contexts generally, correct or not, diluting exactly the signal being
exploited. Bigger/more domain-adapted is not straightforwardly better for
this narrow anomaly-detection purpose -- worth remembering before reaching
for a larger model as a first instinct.

**Bidirectional masked-LM scoring (DistilBERT-base-uncased, 66M params, no
math training at all) produced by far the cleanest separation.** Masking
just the bug position in `"5. Divide by [MASK] h^2+k^2 and complete the
proof"` and reading the model's own probability for the actual token `'p'`
gave probability 0.0018 -- roughly 40x below the top candidate (`'log'` at
0.069) and rank 97 of a 30,522-token vocabulary. This makes structural
sense: the disambiguating evidence (`h^2+k^2` right after the error) is
*ahead* of the error, which a causal model can never use but a masked model
sees directly. No filtering or windowing needed to get this separation.

**But masked scoring has the identical domain blind spot**, tested
directly: masking real, correct `\xi`/`\eta` occurrences from the same page
gave probability 0.0004 (rank 72) and 0.00002 (rank 121) respectively --
*lower* than the actual bug's own 0.0018. A generic English-only model,
masked or causal, doesn't have calibrated expectations for Greek letters
regardless of architecture. Unlike the ASCII-substitution case, this
*is* the failure mode the existing allowlist is built for -- since
`\xi`/`\eta` are the correct characters and both already fall in
`_ALLOWED_MATH_RANGES` (Greek and Coptic), suppressing any candidate whose
*actual* character is already allowlisted correctly kills this false
positive without touching the `'p'` case (ordinary ASCII, never
allowlist-excluded). The two false-positive classes are complementary, not
competing, once correctly scoped.

## Design

### Candidate pool: local-only pages, derived from existing frontmatter

No new tracking needed. For each target document (see "Discovery" below),
the pages eligible for post-processing are:

| `routing` | Eligible pages |
|---|---|
| `local` | every page (0 pages ever reached a model) |
| `hybrid` | every page *except* `repaired_pages` |
| `gemini_batched` / `gemini_accumulating` | none -- already fully model-verified, skip the document entirely for detection purposes (it can still serve as a reference document, see below) |

### Discovery: recursive scan, frontmatter-driven target/reference split

A new script, `postprocess_notes.py`, alongside `transcribe_notes.py` in
`marker-conversion/`, takes a root directory (default something like
`academic-hub/academic_notes/`, or an explicit list of subdirs to scope a
run) and recursively finds every `.md` file under any `processed_outputs/`
folder beneath it -- so `problem_sets`, `ta_notes`, `handwritten_notes`, and
any future course folder are picked up in one invocation without
enumerating them by name. Matching `transcribe_notes.py`'s existing CLI
conventions: a `--dry-run` flag reports what would be flagged and
auto-fixed (with confidence and reasoning) without writing anything, since
this script edits `.md` files in place and that risk is exactly what
`--dry-run` exists to let someone inspect first; a `--file`-equivalent flag
scopes a run to one target document.

- **Correction targets**: files with a `routing` field (this project's own
  signature -- textbook output never has one) that do **not** yet carry
  `postprocessed: true` in frontmatter.
- **Reference pool**: *every* discovered `.md` file, target or not --
  already-postprocessed notes and all textbook output are equally eligible
  as reference material, just excluded from being correction targets
  themselves.
- The moment a target file's correction pass finishes, `postprocessed: true`
  is written into its frontmatter, so a subsequent run automatically skips
  it as a target while keeping it available as reference. A `--reprocess`
  flag bypasses the marker, for when the detection/correction logic itself
  improves later and a full re-run is wanted.

### Detection: three complementary signal sources, not one

Per the explicit decision to test multiple approaches in production rather
than pick one from spike-scale results, all three feed the same downstream
candidate list:

1. **Structural pre-filter (free, no model at all).** Dict-mode's span
   position data (`reconstruct_line_with_scripts`' underlying span
   geometry) already identifies isolated single-character spans standing
   alone on their own line -- structurally exactly what a stripped
   operator/delimiter glyph looks like once mis-mapped. Zero cost, directly
   targets the root cause of the one confirmed real bug rather than an
   indirect statistical proxy.
2. **Masked bidirectional LM scoring** -- small local model loaded via the
   **HuggingFace `transformers` library** (PyTorch CPU backend), the same
   stack the spike was built on. Start with `distilbert-base-cased`, not
   the `-uncased` variant the spike used: math notation is case-sensitive
   (`K` a field vs. `k` an index), and uncased scoring is blind to that
   distinction entirely; not retested in the spike, flag for verification
   during implementation. Masks each candidate token/span and reads the
   model's own probability for what's actually there.
3. **Causal local-window z-score** (kept as a secondary, cheaper-per-pass
   signal, despite masked scoring's cleaner spike results) -- a single
   forward pass scores an entire page at once, versus one pass per masked
   position for full generality, so it's worth keeping as a first coarse
   pass ahead of the more expensive masked rescan, pending a real-scale
   cost benchmark neither this spec nor the spike measured.

**Suppression layer, applied after all three signal sources, before
anything reaches verification:** drop any candidate whose *actual* text is
already covered by `_ALLOWED_MATH_RANGES`/`_is_expected_char` (reused
directly from `transcribe_notes.py`). This is the fix for the confirmed
Greek-letter false positive -- and, per the spike, must **not** be applied
to ordinary-ASCII candidates, since that class of error (a plausible wrong
letter substituted for a symbol) is exactly what the allowlist can't
distinguish and would otherwise suppress along with the false positives.

### Verification: re-check against the real source, not against text alone

For each surviving candidate, confidence doesn't come from a model's
self-reported score on text alone -- it comes from re-checking against the
actual source PDF page, reusing this project's own already-validated repair
machinery (`render_page_to_image_bytes`, the `_repair_page_individually`/
`_repair_batch` call pattern, `gemini-3.1-flash-lite` to match the rest of
the pipeline). The candidate's surrounding context, plus any cross-reference
hits (below), get passed alongside the re-rendered page image. This is also
where the multi-signal detection step above earns its keep cheaply: local
detection is free/near-free, so it can be generous about what it flags,
because the real cost (one Gemini call) only happens after a candidate has
already survived detection and suppression.

- **High confidence** (the re-check clearly confirms a different reading
  than what's currently on record) -> auto-apply the fix, log it.
- **Low confidence** (image genuinely ambiguous, or the re-check agrees
  with the existing text) -> don't touch it; feed into pattern aggregation
  instead of a per-instance prompt.

### Cross-referencing: lightweight keyword/fuzzy search, self-contained

For a flagged span, search other reference-pool `.md` files (other notes,
and textbooks) for similar surrounding text/terminology -- no vector
embeddings, no new infrastructure, just text search over already-discovered
files. Two uses: confirming domain terminology the judge might not
otherwise recognize, and as an independent signal when the *same* term
reads differently across documents covering the same material. Explicitly
not a dependency on RAG Analysis (not built); if plain keyword/fuzzy search
proves too weak once exercised on real documents, that project's retrieval
is the natural upgrade path -- noted here, not built against yet.

### Correction application: in-place edits, with a changelog

High-confidence fixes are written directly into the target `.md` file (this
is meant to be *the* trustworthy RAG-ready file, not a parallel derived
artifact like `describe_images.py`'s additive `.rag.md` -- a third file
variant per document would just create ambiguity about which one is
canonical). Every applied fix is logged to a companion file,
`<name>_postprocess_log.json`, mirroring the existing `_pages_cache.json`
convention: what changed, why (which signal(s) flagged it, the judge's
reasoning), and the page it was re-verified against -- so nothing is
silently altered without a record, and a full run's changes are auditable
after the fact even with no per-fix human review.

### Pattern-level aggregation and review trigger

Low-confidence findings are grouped by a rough signature (e.g. same
character substitution, same document, same detection source) across a
run. A review prompt is only surfaced when a document crosses some minimum
count of similar findings -- treated as a real threshold to tune once real
corpus behavior is visible, not fixed here. Below that bar, findings are
logged (in the same `_postprocess_log.json`) but never interrupt.

## Edge cases

| Situation | Behavior |
|---|---|
| Document is `gemini_batched`/`gemini_accumulating` | Skipped as a correction target entirely (no local-only pages exist); still usable as a reference document. |
| A candidate's re-verification against the source image is itself ambiguous (genuinely hard to read) | Treated as low confidence, not auto-applied, folded into pattern aggregation like any other unresolved flag. |
| The same page is flagged by more than one detection signal | Still one verification call per page, not one per signal -- signals only contribute to the candidate list, not to call volume. |
| A target document's PDF is missing/moved since transcription | Detection (text-only) still runs; verification (needs the source image) fails gracefully and that candidate is logged as unverifiable, not silently dropped or auto-applied. |
| `--reprocess` run against an already-`postprocessed: true` file | Marker bypassed for that run only; a fresh `postprocessed: true` (and log) is written on completion, same as a first-time run. |
| Cross-reference search finds conflicting readings across multiple reference documents | Passed to the verification step as-is (multiple candidate readings); the source-image re-check is still the deciding signal, not a vote across references. |

## Testing

Following this project's established split: pure logic gets real unit
tests; anything touching PyMuPDF, a local model, or the network doesn't.

**Unit-testable (pure Python, no model/PDF/network I/O):**
- Candidate-pool derivation from frontmatter (`routing`/`repaired_pages` ->
  eligible page list) -- pure function over parsed frontmatter dicts.
- Discovery/target-vs-reference classification (`routing` field presence,
  `postprocessed` marker) -- pure function over a list of frontmatter dicts
  and file paths, no real filesystem walk needed for the logic itself.
- The suppression layer (allowlist check against a candidate list) --
  directly reuses `_is_expected_char`, already tested.
- Pattern-aggregation grouping/threshold logic -- pure function over a list
  of finding records.
- Changelog record shape/serialization.

**Not unit-testable here (needs a real model, PDF, or network call):**
- The masked-LM and causal-z-score scoring functions themselves (model
  inference).
- The structural pre-filter's actual dict-mode span walk (PyMuPDF).
- Verification (Gemini network call, reusing already-tested
  `_repair_page_individually`/`_repair_batch` machinery).
- Cross-reference search quality against real reference documents.

These get validated the way this project has consistently validated
everything else: real documents, spot-checked results, logged reasoning --
not synthetic fixtures standing in for the parts that can't be unit tested.

## Open questions, deliberately left open

- **Exact weighting/interaction of the three detection signals** is not
  decided here -- per direction to test them in production, initial
  implementation should keep them as independent contributors to one
  candidate list (already reflected above) and let real corpus results
  inform whether any should be dropped, weighted, or gated behind another.
- **Masked-LM scan granularity and cost at real scale** -- the spike tested
  short synthetic sentences and one real page; scanning every candidate
  position exhaustively needs one forward pass per position, and neither
  the spike nor this spec has benchmarked that against a real multi-hundred-
  page corpus. Worth an early implementation-time check before assuming
  it's fast enough, similar in spirit to the VM-validation gap this
  project has hit before with untestable-locally code paths.
- **Cased vs. uncased masked model** -- flagged above as a real gap (the
  spike only tested uncased); needs verifying that a cased variant doesn't
  regress the demonstrated signal before committing to it.
- **Pattern-aggregation review threshold** -- "a consistent pattern," not
  every instance, was the explicit requirement; the actual count/shape of
  that threshold isn't set here, since it depends on what real low-
  confidence-finding volume looks like once this runs against real
  documents.
