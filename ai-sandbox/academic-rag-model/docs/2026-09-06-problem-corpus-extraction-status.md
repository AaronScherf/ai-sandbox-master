# Problem Corpus Extraction: Real Validation

Spec: `docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`
Plan: `docs/superpowers/plans/2026-09-06-problem-corpus-extraction.md`

## Real run results

**Dry run, before any real extraction:**
```
{'extracted': 12, 'unchanged': 0, 'skipped_no_problems': 0, 'failed': 0, 'problems_extracted': 0}
```
12 problem-bearing cards found under `math-camp` (8 `problem_sets` files, 4
`recitation_slides` files) — the 5 textbook cards weren't visible yet, see
the folder-alias finding below.

**Real run #1** (`extract --course math-camp`):
```
{'extracted': 8, 'unchanged': 0, 'skipped_no_problems': 4, 'failed': 0, 'problems_extracted': 196}
```
All 8 `problem_sets` files extracted successfully (196 problems total); the
4 `recitation_slides` files produced zero detected spans each (correctly
skipped, not failed — recitation slides don't have `_MIN_PROBLEM_MATCHES`
numbered-problem boundaries). Wall-clock: several minutes, dominated by
Gemini free-tier rate-limit backoff (see below), not the extraction logic
itself.

**Real finding mid-run: hit Gemini's free-tier rate limit hard.** The
196-call run repeatedly hit `429 RESOURCE_EXHAUSTED` (`gemini-3.1-flash-lite`
free tier: 15 requests/minute) — a pattern this project's smaller-scale
spikes (`problem_gen`'s 18-call feasibility spike, `viz`'s single-digit
real trials) never triggered, simply because this tool makes far more
calls in a tight loop (one per detected problem span across an entire
file, not one per user request). `common.gemini_utils.call_with_retries`
handled every one of these correctly — it reads the API's own suggested
`retryDelay` (up to ~60s here) and waits that long before retrying,
rather than the fixed exponential-backoff schedule it falls back to
without that hint. Every call eventually succeeded: **0 span-level
failures from rate limiting** across the whole run. Cost is still
negligible at Flash-Lite pricing (196 calls, well under a cent total),
but a full-corpus extraction run realistically takes several minutes on
the free tier due to this throttling, not because the work itself is slow.

**Real finding: a stale index path silently hid all 5 textbook files.**
Inspecting the actual `math-camp` index card shard found all 5 textbook
cards (Axler, Hammack, Rudin, Simon, Sydsæter) still carry the path
segment `academic_resources/math-camp/textbooks-and-papers/...`, even
though that folder was renamed to `academic_resources/math-camp/textbooks/`
on disk at some point (per the root `.gitignore`'s own comment history —
math-camp was renamed, several other courses were not). This repo's own
`_PROBLEM_BEARING_FOLDER_CATEGORIES` tuple only recognized `"textbooks"`,
so these 5 cards were silently filtered out before `extract_problems()`
ever tried to open them — no warning, no failure count, just invisible.

**Fix:** widened `_PROBLEM_BEARING_FOLDER_CATEGORIES` to also recognize
`"textbooks-and-papers"`, matching the root `.gitignore`'s own explicit
dual-naming handling for exactly this situation. Added a regression test
(`test_textbooks_and_papers_alias_is_not_filtered_out`). Full suite:
`1009 tests, OK`.

**Dry run after the fix:**
```
{'extracted': 9, 'unchanged': 8, 'skipped_no_problems': 0, 'failed': 0, 'problems_extracted': 0}
```
17 problem-bearing cards now visible (12 original + 5 textbook cards).

**Real run #2, after the fix:**
```
{'extracted': 0, 'unchanged': 8, 'skipped_no_problems': 4, 'failed': 5, 'problems_extracted': 0}
```
The 5 textbook cards now correctly surface as **failed** — the widened
filter lets them reach the file-level `try`/`except`, which reports
`[Errno 2] No such file or directory: '...textbooks-and-papers/...'` and
the standard rerun hint, exactly as designed. This is strictly better
than the pre-fix silent drop: the tool now honestly reports "5 files
couldn't be read" instead of implying "nothing to extract here." **No
textbook content has actually been extracted yet** — that requires
`python index_search.py rebuild` to reconcile the stale index cards
first, which is a pre-existing indexer issue, out of scope for this
subproject to fix.

**Idempotency confirmed** by real run #2 itself: all 8 already-extracted
`problem_sets` files reported `unchanged` with zero new Gemini calls —
content-hash-based skip works correctly on real data, not just the
mocked orchestration tests.

**Final corpus state:** `.problem_corpus/math-camp.json` holds 196
records from 8 files:

| File | Records | With solution |
|---|---|---|
| Linear Algebra Problem Set AMS Solutions.md | 10 | 5 |
| Linear Algebra Problem Set.md | 8 | 3 |
| old_problem_set.md | 30 | 14 |
| Analysis_Exercises.md | 5 | 0 |
| Practice Sheet.md | 42 | 0 |
| Real Analysis Problem Set_Solutions.md | 79 | 15 |
| old_exam_2021.md | 8 | 1 |
| old_exam_2025.md | 14 | 7 |

## Findings

**Core extraction quality is genuinely good on clean, problem-only
files.** `Practice Sheet.md`'s 42 records: 0 duplicate-labeled citations,
every `topic_tag` specific and accurate (`"diagonalizability"`,
`"nilpotent operators"`, `"compactness"`), every `problem_text` correctly
stripped of its boundary-detection artifact (0/196 records anywhere in
the corpus still start with a raw `"Problem N."`/`"**Practice Problem
N"`/bare digit prefix) and matching the source content verbatim.

**Real limitation found: `old_problem_set.md`'s numbering isn't flat,
and the corpus has genuinely duplicate/fragmented records because of
it.** 10 of its 30 records share a citation label with another record
in the same file (`"old_problem_set.md, Problem 9"` appears 5 times).
Inspecting these by hand found two distinct causes, not one:
1. **Numbered true/false sub-statements inside a single problem** (e.g.
   "state whether each of the following statements is true or false")
   match the same `^\d+\.\s` boundary pattern as a top-level problem
   number, so the boundary detector splits one logical problem into
   several fragments, each mislabeled with the same "Problem N" (the
   number it happened to detect nearest). This is an inherent limitation
   of the regex duplicated from `indexer/chunk_index.py`, not something
   this subproject's own code introduced — the same simple-numbering
   assumption underlies both.
2. Two of "Problem 9"'s five records are **exact duplicates of the same
   content** — the boundary detector found two boundary matches close
   together (likely a re-stated problem number, or the same numeral
   appearing twice in the source text) and produced two spans covering
   overlapping content.

Other files with duplicate-labeled citations (`Linear Algebra Problem
Set AMS Solutions.md`: 2/10, `Linear Algebra Problem Set.md`: 2/8, `Real
Analysis Problem Set_Solutions.md`: 6/79, `old_exam_2021.md`: 2/8,
`old_exam_2025.md`: 2/14) show the same pattern at a lower rate — these
files' guided-walkthrough/mini-lecture sections embed their own numbered
steps, which the same regex can't distinguish from a new problem's start.

**This does not violate any of this subproject's hard guarantees**: every
record still gets a unique, collision-safe `id` (the span-index
component of the hash was specifically designed for this), and
`solution_text`/`solution_provenance` are still correctly paired in every
record inspected. It's a data-quality gap in the human-readable
`citation` label and in how many genuinely-distinct "problems" get
recorded from a file whose structure doesn't match the simple
"top-level numbered problems only" assumption — worth a future pass at
`boundaries.py`'s detection logic if this corpus is used for anything
where fragment-vs-whole-problem quality matters (e.g. few-shot examples,
idea #1/#2 in the problem-generation status doc), but not a blocker for
this subproject's own stated goal of getting a structured corpus
started.

## Known limitations

- ~~No textbook content extracted yet~~ — **fixed 2026-09-06, see below.**
- **Boundary detection over-splits on numbered content embedded inside
  a problem's own body** (numbered sub-statements, guided-walkthrough
  steps) — see the Findings section above. Affects 6 of 8 real files
  extracted so far, at rates from 2/8 to 10/30 duplicate-labeled records.
- Only math-camp is covered; other courses are empty or near-empty in
  this corpus right now (per this project's own earlier finding during
  `problem_gen`'s Gemini feasibility spike).
- No verified-solution tier exists anywhere in this corpus — see the
  spec's own Section 1 finding. Confirmed again by this real run: every
  one of the 45 records with a solution is tagged `"student_attempt"`,
  never `"verified"`.
- Real extraction runs hit Gemini's free-tier rate limit heavily (15
  req/min) on a full-corpus pass — `call_with_retries` handles it
  correctly, but a full run realistically takes several minutes on the
  free tier, dominated by rate-limit backoff rather than extraction work.
- This subproject stops at the stored corpus; nothing yet consumes
  `.problem_corpus/<course>.json` (see the five other future-development
  ideas flagged in `docs/2026-09-05-problem-generation-status.md`).

## 2026-09-06 (continued): fixed the actual indexer bug behind the stale path

The "out of scope, run `index_search.py rebuild`" note above turned out
to be wrong on inspection: **running `rebuild` alone would not have
fixed anything.** The real root cause was in the indexer itself, not
just stale data.

`indexer/index_search.py`'s `_textbook_book_dirs()` hardcoded the folder
name it walks under `academic_resources/<course>/` to the literal string
`"textbooks-and-papers"`. Math-camp's folder was renamed to `textbooks/`
on disk at some point; every other course (`econometrics`, `env-science`,
`interm_spanish`, `intro_spanish`) still uses `textbooks-and-papers/`.
Because the walk only recognized the old name, it silently produced zero
book directories for math-camp — `rebuild()` never saw these 5 textbooks
to reconcile, no matter how many times it ran, with no warning at all.
This is the same shape of bug as the `_PROBLEM_BEARING_FOLDER_CATEGORIES`
fix documented above, one layer deeper: that fix let `problem_corpus`
correctly *notice* the folder-alias mismatch and report `failed: 5`;
this fix addresses why the underlying index cards were stale in the
first place.

**Fix:** widened `_textbook_book_dirs()` to check both
`_TEXTBOOK_FOLDER_NAMES = ("textbooks", "textbooks-and-papers")` and
yield which alias matched, threading that real folder name into
`rebuild()`'s `_reconcile_one(...)` call in place of the old hardcoded
literal (`indexer/index_search.py`). Added two regression tests
(`test_generates_a_textbook_card_under_the_textbooks_folder_alias`,
`test_both_textbook_folder_aliases_are_picked_up_in_the_same_course`).
Full suite: `1011 tests, OK`.

**Real validation.** Running `index_search.py rebuild --course math-camp`
after the code fix found the 5 book directories, but surfaced a second,
independent staleness problem: each textbook's own
`processed_outputs/<book>/<book>_metadata.json` — the durable record
`rebuild()` trusts for `source_pdf_path` and `rag_md_path` — still
pointed at the old `textbooks-and-papers/` location for both fields,
left over from before the on-disk rename. `rebuild` correctly reported
this as `skipped_no_source_pdf: 5` with an explicit "does not exist on
disk" warning per file, rather than failing silently. Fixed by
correcting `source_pdf_path`/`rag_md_path` in all 5 metadata.json files
to the current `textbooks/` location (each verified to exist on disk
before writing). Re-running `rebuild --course math-camp` then reported
`{'updated': 5, 'orphaned': 0, 'skipped_no_source_pdf': 0}` — all 5
cards now carry correct, current paths.

`problem_corpus.extractor extract --course math-camp --dry-run`
afterward reported `{'extracted': 15, 'unchanged': 0, 'failed': 0}` —
zero failures, up from the prior `failed: 5`. A real (non-dry-run)
extraction scoped to one textbook (`Hammack_Book_of_Proof_2025.md`)
produced 62 real records with correct citations and honest
`solution_provenance: null` throughout — confirming the whole pipeline
now works for textbook content, not just problem sets.

**New finding, not fixed (out of scope for this bug fix):** a quick
inspection of the Book of Proof records found several with thin
problem_text (e.g. a single `$$\phi$$`) — `boundaries.py`'s
numbered-list detector is tuned for problem-set-style "Problem N."
prose and appears to also catch textbook end-of-chapter exercise lists
that are more terse/symbolic. This is a boundary-detection precision
question specific to textbook content, distinct from both the path bug
fixed here and the fragmentation limitation documented above — worth a
closer look before textbook records are trusted for downstream use
(e.g. few-shot examples), but not a blocker for the bug this session
targeted.
