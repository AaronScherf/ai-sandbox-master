# Notes Post-Processing: Status Summary

**Status: in progress.** The pipeline is built, unit-tested, and validated
end-to-end against one real, reproduced bug -- but only against one small
document so far. This doc will be updated once a broader corpus run
(multiple subdirectories, the longer `LN_*.pdf`-scale documents) has
happened; see "Remaining open items" for exactly what that's expected to
tell us.

Start here for "what happened and where do we stand" on the post-processing
subproject -- `postprocess_notes.py`, a downstream correction pass over
`transcribe_notes.py`'s already-produced `.md` output. Sibling to
`docs/2026-08-24-notes-transcription-status.md` (that pipeline's own status
doc) and directly motivated by a gap found while writing it: local-only
pages (pages that never reached a vision model, either because a whole
document was `routing: local` or because a page fell outside a hybrid
document's `repaired_pages`) can carry silent errors invisible to
`page_looks_defective()`'s four existing signals. The motivating case: a
radical/square-root sign on `Analysis_Exercises.pdf` page 6 extracting as
plain ASCII `p` -- not a long run, not an unexpected character, not
repeated, no adjacent digit, so nothing in the existing heuristic set ever
had a chance of catching it.

## Why a different approach this time

Several rounds of the notes-transcription work added increasingly specific
detection heuristics (word-boundary-anchored regexes, font-size/baseline
thresholds), each tuned against a handful of real examples that exposed a
gap. Useful, but recognized as a pattern not worth continuing indefinitely
-- this subproject deliberately shifts from "detect every failure mode we
can think of" to a general downstream correction pass, accepting that
transcription won't be perfect rather than chasing zero mistakes upstream.
Full design reasoning and the spike behind it:
`docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md`.
Implementation plan: `docs/superpowers/plans/2026-08-26-notes-postprocessing.md`.

## What this project built

A pipeline with three stages, wired together in `postprocess_notes.py`:

1. **Discovery and candidate-pool scoping** (`postprocess_discovery.py`).
   Recursively finds every `.md` file under any `processed_outputs/` folder
   beneath one or more root directories. A document is a **correction
   target** if it has a `routing` field (this project's own signature --
   textbook output never has one) and isn't already marked
   `postprocessed: true`; every discovered file, target or not, is fair
   game as **reference material**. Eligible pages within a target are
   derived straight from existing frontmatter -- no new state file: every
   page for `routing: local`, every page except `repaired_pages` for
   `routing: hybrid`, nothing at all for `gemini_batched`/
   `gemini_accumulating` (already fully model-verified).
2. **Layered detection** (`postprocess_findings.py` + `local_model_scoring.py`).
   A free structural pre-filter (an isolated single-character span
   standing alone on its own line -- the exact shape of the confirmed real
   bug) runs independently. Separately, a cheap causal-LM pass (GPT-2, one
   forward pass per page) narrows candidate positions by local z-score,
   and only that narrowed set gets the more expensive masked-LM
   confirmation pass (DistilBERT-cased, one forward pass per candidate).
   A suppression layer removes any *non-ASCII* candidate already covered
   by `transcribe_notes.py`'s own math-symbol allowlist (Greek letters,
   etc.) -- deliberately scoped to non-ASCII only; see "Key errors" below
   for why applying it to ASCII candidates was a real bug, not a design
   choice.
3. **Verification and correction.** Every surviving candidate is
   re-checked against its actual source PDF page, reusing
   `transcribe_notes.py`'s existing, already-validated repair machinery
   (`repair_page_individually`, `gemini-3.1-flash-lite`) rather than
   trusting any model's self-reported confidence on text alone. A page
   whose re-check differs from the current text is corrected in place; one
   that matches is left untouched. Every decision -- applied fix, confirmed
   -no-change, or unverifiable -- is logged to `<name>_postprocess_log.json`,
   mirroring the `_pages_cache.json` convention. Low-confidence findings
   are grouped by document + flagged text; a review prompt only surfaces
   once a document crosses a repeat-count threshold (default 5), never per
   instance.

Four `transcribe_notes.py` helpers (`is_expected_char`, `ALLOWED_MATH_RANGES`,
`repair_batch`, `repair_page_individually`) were renamed from private to
public first, since they're now a real cross-module interface -- pure
rename, verified zero behavior change against the full existing suite.

**Stack note:** local model inference uses HuggingFace `transformers`
(PyTorch, CPU-only), not Ollama. Ollama was the original candidate but was
dropped after checking its own official docs directly: neither its native
nor OpenAI-compatible API supports scoring caller-provided text (no
echo/prompt-logprobs mode) -- only probabilities for tokens the model
generates itself, which doesn't support the masked-scoring this design
needs.

Everything except the PyMuPDF/`transformers`/network-touching pieces is
pure Python and independently unit-tested -- 197 tests across the whole
project as of this writing (37 new: 17 in `test_postprocess_discovery.py`,
20 in `test_postprocess_findings.py`), all passing.

## The design spike, briefly

Before writing any implementation code, a throwaway spike (`transformers`,
CPU inference) tested detection approaches against the real bug:

- **Causal (left-to-right) perplexity (GPT-2)** found the bug but was
  outranked by legitimate Greek-letter tokenizer artifacts on the full real
  page -- a position/domain-mismatch confound, not just noise.
- **A math-adapted model (Qwen2.5-0.5B) made detection *worse*, not
  better** -- a more capable, better-calibrated model is less surprised by
  unusual tokens in dense math contexts generally, correct or not,
  diluting the exact signal being exploited. Worth remembering before
  reaching for a "smarter" model as a first instinct.
- **Bidirectional masked-LM scoring (DistilBERT) produced by far the
  cleanest separation** -- the disambiguating evidence (`h^2+k^2` right
  after the error) sits *after* the error, which only a masked model can
  use. But it shares the identical domain blind spot on legitimate Greek
  letters, confirming the allowlist-suppression layer is still needed --
  just scoped correctly (see below).

Full numbers and reasoning: the design spec linked above.

## Real-world validation

| Document | What happened |
|---|---|
| `Practice Sheet.md` (dry-run, 41 eligible pages, already known-clean) | Before fixing the detection layering: 28 of 41 pages flagged, all from unnarrowed causal z-score alone -- false positives on an already-verified-correct document. After layering causal z-score as a narrowing pass ahead of masked-LM confirmation (matching the design spec's actual intent, which the first implementation had deviated from): 0 pages flagged. Also ~10x+ faster -- caching model loads and narrowing the masked-LM candidate set both mattered. |
| `Analysis_Exercises.md` (real run, page 6's cache entry cleared to force the real bug to reproduce from fresh local extraction) | Found and correctly fixed the actual radical-as-`p` bug (`page 6` now reads `$$\sqrt{h^2 + k^2}$$`, re-verified against the source image). 9 other flagged candidates across the same document were independently re-verified and correctly left untouched (source-image check matched existing text). 10 real Gemini verification calls total, well under a cent. |

## Key errors encountered and overcome

Found during the two runs above, all before any code was considered done --
none caught by the 37 new unit tests, since all four are integration-level
(exactly why the plan's final task ends in a real run, not just green
tests):

1. **`--dry-run` never actually stopped the real verification call** -- it
   only gated the final file write. Every dry-run candidate hit the
   network with a `None` client, retried twice with 5s/10s backoff, then
   failed. Fixed: `dry_run` now reports candidates without ever calling
   the network, matching `transcribe_notes.py`'s own established
   `--dry-run` convention.
2. **Both local models reloaded from scratch on every single call** (once
   per page) -- dominated real end-to-end runtime far more than the
   scoring work itself. Fixed via `functools.lru_cache` in
   `local_model_scoring.py`.
3. **Masked-LM scoring ran on every non-whitespace character
   unconditionally** -- both far too slow (thousands of forward passes per
   document) and far too noisy (the 28-page false-positive result above).
   This was a real deviation from the design spec's own stated intent
   ("causal z-score as a first coarse pass ahead of the more expensive
   masked rescan") that the first implementation pass missed. Fixed by
   actually layering the two signals as designed.
4. **The suppression layer accidentally suppressed the real bug itself.**
   `is_allowlisted_span()` is `True` for *any* ASCII text (inherited from
   `is_expected_char`'s original corruption-detection semantics: ASCII is
   never "exotic-looking"), not just legitimate math-range Unicode. The
   first implementation applied it as a blanket filter over every
   candidate regardless of source -- which silently removed the
   structural candidate for the real `p` bug, since `p` is ordinary ASCII.
   This is exactly the ASCII-substitution class `postprocess_findings.py`'s
   own `is_allowlisted_span` test docstring already said this layer
   couldn't help with (written *before* this bug was hit) -- the lesson
   was documented and then violated anyway during integration. Fixed:
   only non-ASCII allowlisted candidates are suppressed now.
5. **DistilBERT crashed on a longer page** -- 554 tokens vs. its fixed
   512-token position-embedding limit. Fixed by scoring each masked
   candidate against a local text window (200 chars each side) rather than
   the full page, which also keeps every call fast regardless of page
   length and matches the design spike's own finding that nearby context
   carries the signal, not the whole page.

## Remaining open items

- **Only validated against one small (11-page) document.** The
  `_MASKED_PROBABILITY_THRESHOLD` (0.01) and `_CAUSAL_ZSCORE_THRESHOLD`
  (3.0) constants in `postprocess_notes.py` are still first-guess
  defaults, not yet exercised against a longer or more diverse document
  (e.g. the 100+ page `LN_*.pdf` lecture-note files). A broader run is the
  natural next step before trusting these at scale.
- **Never run across multiple subdirectories in one invocation** (e.g.
  `problem_sets` + `ta_notes` + `handwritten_notes` together) -- the
  mechanism supports it (`--root` is repeatable), just not exercised for
  real yet.
- **The pattern-review threshold (5+ similar low-confidence findings
  in one document) has never actually fired** -- logic is unit-tested,
  but no real run so far has produced enough low-confidence volume to
  trigger it.
- **Cross-reference search's real-world impact is unverified.** It's
  wired into the verification hint and unit-tested in isolation, but
  wasn't the deciding factor in the one real fix made so far (the
  source-image check was) -- its actual value-add hasn't been specifically
  observed yet.
- **`LN_Analysis.pdf` and `LN_Linear Algebra.pdf` remain on hold** from the
  notes-transcription subproject (see that doc) -- unrelated to
  post-processing directly, but still an open item in the same corpus.
- `marker-conversion-post-processing` has been merged locally into
  `marker-conversion-notes-transcription` (fast-forward, tests green) but
  not yet pushed to `origin`. `marker-conversion-notes-transcription`
  itself remains unmerged into `marker-conversion`/`main` -- a separate,
  still-pending decision.
