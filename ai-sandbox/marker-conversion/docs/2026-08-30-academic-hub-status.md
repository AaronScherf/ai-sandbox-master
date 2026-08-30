# Academic Hub: Project-Wide Status Summary

Start here for "where does the whole project stand" -- a synthesis across
every subproject's own status doc, not a replacement for any of them. Read
the linked doc for a given piece's full history; this page is the map.

**Subproject docs, in build order:**
1. `docs/2026-08-22-chapter-aware-chunking-status.md` -- textbook chunking/page tracking
2. `docs/2026-08-23-image-description-status.md` -- textbook figure descriptions
3. `docs/2026-08-24-notes-transcription-status.md` -- non-textbook PDF transcription
4. `docs/2026-08-27-notes-postprocessing-status.md` -- downstream transcription correction (in progress, paused)
5. `docs/2026-08-29-source-indexer-status.md` -- tags, cards, file-level search
6. `docs/2026-08-30-rag-agent-status.md` -- passage retrieval + tutoring agent
7. `docs/2026-08-28-known-errors-todo.md` -- cross-cutting bug tracker

## The pipeline, end to end

```
PDFs (textbooks, problem sets, exams, notes)
  |
  |-- convert_textbook.py  (Marker + chapter-aware chunking + page/folio tags)
  |     -> describe_images.py  (figure descriptions, .rag.md)
  |
  |-- transcribe_notes.py  (3-tier router: local / hybrid-batch / full-Gemini)
  |     -> postprocess_notes.py  (downstream correction pass, IN PROGRESS)
  |
  v
Source indexer (index_card.py / index_search.py / retag.py / chunk_index.py)
  - per-file cards (file_id, doc_type, tags, embeddings)
  - corpus-wide tag vocabulary (retag)
  - file-level two-stage search
  - passage-level chunks + embeddings (chunk_index.py)
  |
  v
rag_agent.py -- multi-turn tutoring, grounded citations, no persistent memory
```

**Repository layout (as of 2026-08-30):** the scripts above now live in
per-subproject packages -- `common/`, `indexer/`, `textbook/`, `notes/`,
`postprocessing/`, `rag/` -- run via `python -m <package>.<module>`, e.g.
`python -m notes.transcribe_notes`, `python -m indexer.index_search query
"..."`. Previously a flat folder of ~15 top-level scripts. See
`README.md`'s "Repository layout" section for the full breakdown; the VM
deployment step in `gcp_instructions.md` was updated to match (a
`--recurse` copy of `common/`+`indexer/`+`textbook/` instead of
cherry-picked flat files, which also fixed a real pre-existing gap where
`index_card.py`/`gemini_utils.py` were never actually deployed to the VM).

Every stage after the raw PDF is markdown-first: each pipeline stage reads
the previous stage's `.md`/`.rag.md` output and its own YAML frontmatter or
JSON sidecar state, never re-parses the PDF. This is why re-running any one
stage after a fix (e.g. re-transcribing after the Nebo-guard fix, or
re-tagging after the fallback-leak fix) has consistently been cheap and
safe throughout the project -- each stage's output is a stable, inspectable
artifact, not a black box.

## Real-corpus state today (2026-08-30)

One course in the corpus so far, `math-camp`:
- **30 index cards**, all healthy: 0 orphaned, 0 `needs_indexing`, 0
  untagged, 30/30 have `content_hash`, 5/5 textbooks linked to their
  `.rag.md`.
- **14 tags** in the corpus-wide vocabulary (10 corpus-validated, 4
  single-document fallback tags, all correctly isolated from cross-leak).
- **5 textbooks** fully chapter-chunked, page/folio-tagged, and
  image-described (793 candidate figures, 764 described, 29 correctly
  skipped as decorative).
- **~15 notes/problem-set documents** transcribed via the 3-tier router;
  the 6 that were stale pre-fix artifacts have been re-transcribed for
  real.
- **Passage-level chunks + embeddings** generated for the full corpus
  (`.index/chunks/math-camp.json`, gitignored -- see "IP and security
  posture" below).
- **RAG tutor** validated against real multi-turn queries on this corpus.

Everything above is one course. Nothing about cross-course behavior (tag
vocabulary scaling, cross-course retrieval ranking, whether one course's
fallback tags could drift toward relevance in another) has been exercised
against real data yet -- see "Between-course retrieval" below.

## Cross-cutting patterns worth carrying forward

These showed up independently across nearly every subproject and are worth
treating as house style, not one-off lessons:

- **Real-evidence-driven correction over untested heuristics.** Threshold
  values (repetition-loop regex, causal z-score, defect ratio), model
  choices (`TUTOR_MODEL`, image-description model), and even whole
  detection approaches (tag clustering, causal-only vs. causal+masked
  scoring) were repeatedly set on a first-pass heuristic, then measured
  against real corpus data, then corrected when the evidence disagreed.
  Several of these corrections were prompted by the user directly
  questioning an unvalidated assumption ("why are we using a 3.6 gemini?").
  Default to testing before asserting a quality/capability claim.
- **Dependency-free core modules.** `chapter_index.py`, `page_markers.py`,
  `describe_images.py`'s parsing/caching logic, `chunk_index.py`, and most
  of `rag_agent.py` deliberately avoid importing `torch`/`marker` (GPU-only
  deps) or making network calls at module scope, so the logic is unit
  testable on a plain machine. `convert_textbook.py` itself is the
  exception (GPU-bound, VM-only) -- everything downstream of it was
  designed not to inherit that constraint.
- **Two-stage bugs: real ones, and stale artifacts mistaken for real
  ones.** More than once (the 6 zero-byte `.md` files, the mtime-reset
  false "14 cards updated") the investigation had to distinguish "this is
  a live bug" from "this is leftover state from before a fix shipped."
  Confirming via commit timestamps and direct re-runs, rather than
  patching defensively, kept the fix count honest.
- **A cross-stage bug class: state written but never reconciled onto the
  card that's supposed to reflect it.** `rag_md_path` (image-description ->
  index card) and `content_hash`/`needs_indexing` (retag/rebuild
  interactions) both had this shape -- one stage's sidecar JSON updates
  correctly, but the index card that's supposed to summarize it doesn't
  get told. Worth checking for this shape specifically if a future stage
  adds its own sidecar state.

## IP and security posture (load-bearing, do not relax silently)

The GitHub repo `AaronScherf/ai-sandbox-master` is **public**. The corpus
contains copyrighted PDFs/textbooks. Current policy, enforced via a
deny-list `.gitignore` (not a blanket directory ignore):
- Source PDFs, converted `.md`/`.rag.md`, `images/`, page caches, and raw
  OneNote exports are all gitignored under `academic-hub/**`.
- `.index/chunks/` (passage text + embeddings) is gitignored -- added after
  a real incident where verbatim chunk text and embeddings of that exact
  text were briefly pushed public, then purged via a scoped
  `git filter-repo` history rewrite.
- File-level index **cards** (`doc_type`, LLM-authored title/summary,
  tags) are treated as genuinely derivative and are not gitignored --
  the distinction that matters is verbatim-reproduction risk (chunk text,
  embeddings of chunk text) vs. LLM-authored description of a document.

Any future subproject that stores or transmits corpus text more granular
than a card-level summary (new problem-set text, journal-article chunks,
YouTube transcript excerpts) needs this same check before its first commit,
not after.

## Where each subproject stands

- **Chapter-aware chunking**: shipped, VM-validated across 3+ books. A
  handful of low-stakes deferred items (stale docstring, minor off-by-ones)
  remain, explicitly non-blocking.
- **Image description**: shipped, validated against all 5 real textbooks
  (764/793 figures described, spot-checked accurate). No open blockers.
- **Notes transcription**: shipped, 3-tier router validated against the
  real corpus including a full repetition-loop defense system added this
  session. No open blockers on the transcription pipeline itself.
- **Notes post-processing**: **in progress, explicitly paused.** Built,
  unit-tested, and validated against one real reproduced bug (the
  radical-as-`p` case) and a broader corpus run that fixed a real
  word-spacing extraction bug. Left open: the causal z-score signal still
  has an unresolved precision problem on math-heavy prose (mitigated
  ~62% via a threshold raise, not solved) -- see
  `docs/2026-08-27-notes-postprocessing-status.md` and the
  `project_notes_postprocessing_paused` memory. The most promising
  unpursued direction is conditioning detection on retrieved,
  validated-similar passages -- which now has a real prerequisite in
  place (passage embeddings exist), making this a plausible thing to
  revisit rather than a purely speculative future idea.
- **Source indexer**: shipped (core + retag + passage chunking), real
  corpus healthy per the snapshot above. No open blockers.
- **RAG tutoring agent**: shipped, validated against real multi-turn
  queries. Explicit, honestly-scoped limitations -- see
  `docs/2026-08-30-rag-agent-status.md` in full; summarized in "What's
  next" below since they're this project's most immediate next steps.

## Outstanding TODOs and known bugs, consolidated

Every documented, not-yet-fixed item found across all subproject docs, so
nothing gets lost between them. None of these are blocking current use of
the pipeline -- if they were, they'd be in "Where each subproject stands"
above instead. Pulled from each doc's own "Remaining open items"/"What's
next"/checklist sections on 2026-08-30; add new ones here going forward
rather than letting them live only in a subproject doc no one revisits.

**Tracked publicly as GitHub issues** (`AaronScherf/ai-sandbox-master`,
issues #1-13, filed 2026-08-30) -- each bullet below links its issue.
Two items were deliberately **not** filed as issues: the lost-exponent
regex gap under notes-transcription (explicitly not-planned-to-fix, listed
here only for completeness) and the branch-state housekeeping note under
notes-postprocessing (already resolved, nothing to track).

**Chapter-aware chunking** (`docs/2026-08-22-chapter-aware-chunking-status.md`,
`docs/superpowers/plans/2026-08-20-vm-validation-checklist.md`):
- [#1](https://github.com/AaronScherf/ai-sandbox-master/issues/1)
  `parse_printed_toc` extracts one spurious entry from Hammack's front
  matter (`folio=2, title='='`) -- harmless today (fails to fuzzy-match,
  silently dropped) but never actually fixed.
- [#2](https://github.com/AaronScherf/ai-sandbox-master/issues/2)
  `README.md` and `convert_textbook.py`'s own module docstring still
  describe fixed-interval chunking and never mention the `<!-- page N -->`
  / `<!-- folio N -->` tag output -- the most user-visible change of that
  whole feature is undocumented in the two places a new reader would look.
- [#3](https://github.com/AaronScherf/ai-sandbox-master/issues/3) A
  corrupt/truncated `run_config.json` (possible since the write isn't
  atomic) hits the same silent-`pass` exception handler as the
  already-fixed old-format case, but does **not** get the stale-chunk-
  clearing treatment -- worth closing (atomic write, or extend the
  clearing fix to this exception path) before a real interrupted run hits
  it, since the failure mode is a silent duplicate-content merge.
- [#4](https://github.com/AaronScherf/ai-sandbox-master/issues/4) A
  cluster of lower-stakes VM-checklist items, none independently
  confirmed to matter in practice: an off-by-one letting the boundary-shift
  probe shift one page past its configured cap; `_boundary_bootstrap_images`
  never cleaned up, accumulating on VM disk across a batch; two
  `process_page_range` bootstrap calls inside `compute_chunk_boundaries`
  ignore the user's `--chunk-timeout`/`--page-timeout` overrides
  (hardcoded 1800s/240s).

**Image description** (`docs/2026-08-23-image-description-status.md`):
- [#5](https://github.com/AaronScherf/ai-sandbox-master/issues/5) The
  front-matter filter only excludes images *before* the first real
  chapter -- back matter (index, appendix, bibliography) isn't specifically
  filtered, left entirely to the per-image LLM skip decision instead. Not
  shown to be a real problem in the 5-book validation, so not prioritized,
  but untested against a book with a large back-matter image section.

**Notes transcription** (`docs/2026-08-24-notes-transcription-status.md`):
- [#6](https://github.com/AaronScherf/ai-sandbox-master/issues/6)
  **`LN_Analysis.pdf` and `LN_Linear Algebra.pdf` still need
  re-processing** through the whole-document-batched path the other four
  reliably-paginated documents already have -- deliberately paused
  2026-08-26 pending a final review, not blocked on anything technical.
  Estimated well under $0.30 total for both. This is the single most
  concrete "just go run it" item in the whole project.
- [#7](https://github.com/AaronScherf/ai-sandbox-master/issues/7)
  **Radical/square-root signs can silently extract as plain ASCII**
  (confirmed real: `Analysis_Exercises.pdf` page 6, a `√` extracting as
  literal `p`) -- invisible to all four `page_looks_defective()` signals.
  Doesn't affect current output (that page's cached Gemini transcription is
  correct), but prevalence beyond this one instance was never investigated.
  This is the motivating bug for the post-processing subproject below, not
  a transcription-pipeline fix in its own right.
- [#8](https://github.com/AaronScherf/ai-sandbox-master/issues/8) No live
  transcription-quality comparison against a dedicated OCR provider
  (Mathpix, Mistral) has ever been run -- the conclusion that Gemini is
  cheaper is pricing-based only, not empirical accuracy.
- Not filed as an issue -- accepted, not-planned-to-fix gap: the
  lost-exponent/subscript regex only catches a digit standing alone
  between word boundaries (`D5`), not one embedded in a longer token
  (`x2y`) -- widening it would reopen a real false-positive risk against
  embedded hash IDs, already hit once.

**Notes post-processing** (`docs/2026-08-27-notes-postprocessing-status.md`,
still the project's one **paused, in-progress** subsystem -- see
`[[project_notes_postprocessing_paused]]` memory):
- [#9](https://github.com/AaronScherf/ai-sandbox-master/issues/9)
  **The causal z-score precision problem is the headline open item.**
  Raising the threshold to 5.0 cut false-positive noise ~62% but did not
  eliminate it -- no threshold in a reasonable range fully separates
  correct terse math vocabulary from real anomalies. `_MASKED_PROBABILITY_THRESHOLD`
  (0.01) hasn't been data-driven the same way yet either. Most promising
  unpursued direction: condition detection on retrieved, validated-similar
  passages instead of a fixed threshold -- now newly *possible* since
  passage embeddings exist (they didn't when this was last worked), not
  yet attempted.
- [#10](https://github.com/AaronScherf/ai-sandbox-master/issues/10) No
  real (non-dry-run, API-spending) pass has been run against the broader
  `ta_notes`/`problem_sets` corpora -- a real pass against `Practice
  Sheet.md` today would trigger on the order of 22 pages' worth of
  verification calls at current noise levels. Blocked on #9 first.
- [#11](https://github.com/AaronScherf/ai-sandbox-master/issues/11) Three
  grouped "implemented but never observed live" gaps: never exercised
  across multiple `--root` directories in one invocation; the
  pattern-review threshold (5+ similar low-confidence findings) has never
  actually fired in any real run; cross-reference search's real-world
  value-add is unverified (wasn't the deciding factor in the one real fix
  made so far).
- Not filed as an issue -- already resolved: this doc's own "not yet
  pushed" / "held pending post-processing" branch notes turned out to be
  stale. `origin/marker-conversion-notes-transcription` has zero commits
  not already in `marker-conversion` (confirmed via `git log
  marker-conversion..origin/marker-conversion-notes-transcription`), and
  neither `marker-conversion-notes-transcription` nor
  `marker-conversion-post-processing` exist as local branches anymore --
  this session's `transcription-fix` branch superseded and merged that
  work already. No action needed beyond deleting the stale remote branch
  ref at some point.

**Source indexer** (`docs/2026-08-29-source-indexer-status.md`, its own
"What's next"):
- [#12](https://github.com/AaronScherf/ai-sandbox-master/issues/12)
  **Document-pairing detection is a confirmed real gap**, not just
  deferred scope -- `Linear Algebra Problem Set.md` and `...AMS
  Solutions.md` have no link today despite being an obvious pair. Flagged
  by the user as worth keeping in mind, not urgent. Directly relevant to
  the problem-set subsystem's lookup mode below.
- [#13](https://github.com/AaronScherf/ai-sandbox-master/issues/13)
  Tag-graph browsing (persisting the co-occurrence structure `retag`'s
  discovery phase already computes and discards) is cheap to build but
  parked as a low-priority navigation aid, not something that moves any
  current goal forward.

### Priority and sequencing (decided 2026-08-30)

Before any new subsystem work starts. Grouped by effort/risk/dependency,
not strictly by issue number:

1. **Tier 0 -- trivial, do first:** #6 (finish LN_* reprocessing -- just
   run it, <$0.30, zero code risk -- still open), ~~#2~~ (stale
   README/docstring, 5-min doc fix -- **fixed** `826703a`).
2. **Tier 1 -- cheap, real fixes:** ~~#3~~ (`run_config.json` atomicity --
   genuine data-integrity risk, small fix -- **fixed** `826703a`), ~~#1~~
   (Hammack TOC parser bug, trivial -- **fixed** `826703a`), ~~#4~~ (minor
   VM-pipeline cluster -- **fixed** `826703a`).

   **#1-#4 fixed 2026-08-30**, commit `826703a` on `marker-conversion`
   (local, not yet pushed) -- 425 tests pass (was 417; added
   `tests/test_convert_textbook.py`, the first local test coverage for
   `convert_textbook.py`, made possible by stubbing the `marker` submodules
   in `sys.modules` before import so its pure-logic functions -- no
   Marker/GPU call of their own -- can be exercised without a VM). GitHub
   issue comments were attempted but rejected (403, token lacks comment
   permission on this repo) -- issues #1-#4 are not yet marked closed on
   GitHub; close manually or re-run once the branch is pushed and the
   token's permissions allow it.
3. **Tier 2 -- the actual blocker, real effort:** #9 (causal z-score
   precision). This is the one that determines whether notes-postprocessing
   can resume at all -- worth a dedicated spike on retrieval-conditioned
   scoring (now possible since passage embeddings exist) before touching
   #10/#11.
4. **Tier 3 -- depends on #9, batch together once unblocked:** #10, #11.
5. **Tier 4 -- low priority, no urgency:** #5, #7 (likely subsumed once
   #9/#10 land), #8.
6. **Tier 5 -- defer to when the relevant new subsystem starts:** #12 (do
   right before/during problem-set subsystem work), #13 (parked
   indefinitely).

## What's next

In two groups: the extensions to the *existing* RAG agent already
identified in its own status doc, and the three new project ideas raised
alongside this stocktaking. None of these are spec'd yet -- this section
is goals/ordering, not a plan.

### Extending the RAG agent (carried over from its status doc)

1. **Persistent conversation/activity history.** The real prerequisite for
   everything context-aware below -- scheduled tasks that need to know
   "what did I already cover," multi-day study continuity. Not yet spec'd.
2. **Problem-set subsystem**, as two distinct modes per the user's own
   framing: a **lookup** mode (retrieve real existing problems, using
   linked solutions where the corpus already has them -- note
   document-pairing detection, e.g. linking `Linear Algebra Problem
   Set.md` to `...AMS Solutions.md`, is a confirmed real gap today, listed
   in the source-indexer status doc as unbuilt) and a **generate-new** mode
   (style/difficulty-matched novel problems, which needs a different
   prompt shape than the tutor's own -- the tutor's anti-hallucination
   guardrail actively works against generating anything novel by design).
3. **Extended/structured report generation.** A different retrieval+
   generation shape than single-question tutoring -- more passages, likely
   multiple retrieval passes across sub-topics, a multi-section prompt
   template. "Summarize chapter 7" is probably already workable today;
   "summarize everything I've covered this week" is not, and also depends
   on persistent history (#1) to know what "this week" covered.
4. **Study-plan agent.** Needs course-level structural awareness (closer
   to the indexer's file-level `search()` and course rollups than to
   passage retrieval) plus real sequencing/pacing logic that doesn't exist
   anywhere yet, and something like a syllabus or target timeline as
   input. Matches the original project framing: a study-plan agent that
   *calls* the RAG agent as one building block, not an extension of it.
5. **Between-course retrieval validation.** Deferred until a second course
   actually enters the corpus (see below) -- `search_passages()`'s
   course-level pre-filter and cross-course ranking are implemented but
   have literally never run against more than one course's data.
6. **Scheduling.** Mechanically solved today for any fixed, non-contextual
   question (`index_search.py ask "..."` is already a plain
   non-interactive CLI command a scheduled job can run) -- what's missing
   is exclusively the context-awareness that #1 unlocks, not scheduling
   infrastructure itself.

### New corpus growth: additional courses

The corpus has only ever contained `math-camp`. Adding new courses is a
stated near-term plan, not a new subsystem -- it should mostly exercise
existing infrastructure (transcription/conversion pipelines, retag's
corpus-wide tag mining, course-level search) rather than requiring new
code, but it's the first real test of a few things designed for multi-course
use and never yet observed: `retag`'s tag vocabulary at a larger, more
topically diverse scale (does the 0.65 assignment threshold still isolate
cleanly, or was it implicitly tuned against a topically homogeneous single
course?), and #5 above.

### New project idea: journal-article transcription

Framed by the user as needing something structurally *between* the
textbook and notes pipelines: journal articles share the textbook
pipeline's printed-text reliability and citation/reference-heavy structure
(so likely closer to `convert_textbook.py`'s Marker-based OCR than
`transcribe_notes.py`'s per-page vision transcription), but lack chapter
structure entirely and are short enough that the chapter-aware chunking
machinery (built specifically for 300-600-page books) is probably
unnecessary overhead. Likely candidate shape: single-chunk (or
section-heading-based, reusing `chunk_index.py`'s existing heading-split
tier rather than `chapter_index.py`'s book-oriented one) conversion with
citation/reference-list-aware structure the existing pipelines don't need
to think about. Not yet brainstormed in any depth -- this is a starting
hypothesis, not a design.

### New project idea: YouTube lecture summarization

Pull lecture video links, send them to a Gemini API (which has native
video/audio understanding for YouTube URLs) to generate content summaries.
Structurally the most self-contained of the three new ideas -- no PDF
involved, no dependency on the chunking/indexing pipeline's assumptions
about document structure, plausibly a fairly short subproject (fetch link
-> Gemini call -> structured summary -> index as a new `doc_type` alongside
existing ones so it's searchable/citable the same way). The main open
questions are probably about output shape (summary granularity,
timestamp-linked notes vs. a single rollup) and whether/how a video-derived
summary should be treated differently from a source's own text for the
verbatim-content IP policy above (a Gemini-authored summary of a lecture is
likely in the same "derivative, not verbatim" bucket as an index card, not
the chunk-text bucket -- but worth confirming explicitly when this is
actually designed, not assumed).

### New project idea: literature review / gap analysis / research ideation

Uses the journal-article corpus (once it exists) to do literature review,
identify gaps, and brainstorm new research directions. The most
architecturally novel of the three -- unlike the RAG tutor (answer a
question from existing material) or a study-plan agent (sequence existing
material), this one's job is synthesizing *across* many articles and
producing genuinely novel output (a gap, a research idea) that by
definition isn't sitting in any single retrieved passage. Closest existing
precedent in this project is the RAG agent's own "not designed for
generating new problem sets" limitation -- the same tension (grounded
citation vs. novel generation) applies here at a larger scale, and
whatever prompt/retrieval shape ends up solving problem-set generation is
worth revisiting as a starting point for this, rather than solving the
grounded-vs-novel tension twice independently. Depends on the
journal-article pipeline existing first.

## Explicitly not re-litigated here

Backend/hosting choices (paid Gemini key, kept for now; Gemini CLI OAuth
free tier and `claude -p` under Claude Pro noted as viable later swaps via
the `TUTOR_MODEL` constant) and public-deployment fair-use questions (real
legal question, not an engineering one) are covered in full in
`docs/2026-08-30-rag-agent-status.md` and not repeated here.
