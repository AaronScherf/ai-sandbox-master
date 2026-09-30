# Problem-Set Tutor Diagnosis: Status Summary

Start here for "what happened and where do we stand" on the tutor
diagnosis extension to the RAG tutoring agent (`rag_agent.py`) -- four
new REPL commands closing the loop between grounded Q&A and the user's
actual problem-set workflow (ask an AI for an explanation, learn from
it, write a summarized solution in the course's own voice). Design
reference: `docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-27-tutor-diagnosis-plan.md`.
Builds directly on the prior RAG agent work
(`docs/status/2026-08-30-rag-agent-status.md`).

On branch `worktree-tutor-diagnosis`, PR #14 open against `main`, **not
yet merged** -- the user is testing this branch manually via the Gemini
Antigravity IDE/agent before deciding on merge.

## What shipped

Four new commands in `rag_agent.py`'s REPL, plus a per-course session
log and three new modules:

1. **`/draft`** -- after a normal question gets a grounded answer, the
   user pastes their own attempt (terminated by `/end`). `diagnose_draft()`
   (`rag/tutor_diagnosis.py`) compares it against the reference answer
   and the same retrieved passages, returning free-text feedback plus a
   **0-5 rubric** on three axes: correctness, rigor, and course-fit
   (added specifically because there was no way to compare attempts on
   a consistent basis before this -- see spec §5 for why three axes,
   not one). Also produces a short free-text `gap_tag` (not a fixed
   taxonomy) naming the single most important gap.
2. **`/hint <file> <question-ref>`** -- pulls one question's text out of
   a fresh, unsolved problem-set file (`rag/problem_set_parser.py`'s
   `extract_question()`), retrieves the normal way, and generates a
   motivating sketch of the right approach -- explicitly barred from
   stating the final answer, a verdict, or a worked derivation.
3. **`/verify`** -- re-solves the current question with an independent,
   *ungrounded* call to a stronger model (`gemini-3.6-flash`, this
   project's existing "stronger" tier), shown side by side with the
   tutor's own answer. Deliberately not shown the prior answer or any
   retrieved excerpts, so it can't just rationalize agreement with
   reasoning it's already seen. No auto-adjudication -- the user judges.
4. **`/summarize [unit]`** -- loads every event logged for a course/unit
   and generates a "what we learned" / "what to focus on" retrospective,
   plus a **computed** (not model-generated) rubric-averages line across
   that unit's `/draft` attempts.

Every REPL action (a normal answer, `/draft`, `/hint`, `/verify`) now
appends a structured `Event` to `rag/session_log.py`'s per-course,
append-only JSONL log at `<academic_hub_root>/.session_log/<course>.jsonl`
(gitignored, same IP posture as `.reports/`/`.viz/`). This also powers a
"phase 2" addition to the original `answer_question()`: it now loads
the course's recent `/draft` gap tags and folds them into the answer
prompt, so a new answer can proactively flag a question that touches a
previously-diagnosed blind spot.

Smaller refactor to the existing agent: `retrieve_passages()` extracted
from `answer_question()` for reuse by `/hint`; `AnswerResult` gained
`passages` (so `/draft` can reuse the same excerpts the reference
answer was grounded in) and `standalone_question` (the reformulated,
self-contained version of a follow-up question, so `/verify` re-solves
the actual question instead of a context-dependent raw follow-up like
"why does that hold?").

## Real-corpus validation

Confirmed live against the real Gemini API and real academic-hub
files, not just unit-tested (REPL glue stays outside pytest coverage
by this project's existing `main()` convention -- spec §12):

- **A real `/draft` diagnosis** against a deliberately wrong attempt
  ("residuals are always positive") scored it 0/5 on all three axes and
  produced the gap tag `fundamental-property-misunderstanding` --
  correctly identified and logged.
- **A real `/hint`** against the actual unsolved `homework_3.md`
  (question 1, on incomplete preference relations) produced a
  motivating sketch (construct a counterexample, think about broken
  transitivity chains) without stating a verdict or final answer.
- **A real `/verify`** produced a genuinely independent second
  solution that visibly differed from the tutor's own answer -- it
  added an intercept-term caveat the grounded answer lacked, confirming
  it isn't just echoing the same reasoning back.
- **A real `/summarize`** synthesized a session's answer/draft/verify
  history into "what we learned"/"what to focus on," correctly
  surfacing the tutor-vs-verification discrepancy on its own, plus a
  computed rubric-averages line matching the logged `/draft` scores
  exactly.
- **Retrieval returned zero passages** for `course="microecon"` in this
  dev environment throughout testing -- worth confirming the `.index/`
  is actually built for whichever course gets tested next, since this
  is an indexing/environment fact, not something this branch's code
  changed or can fix.

## Corrections made against real evidence, not assumptions

A fresh whole-branch review (a separate opus subagent, not this
session's own read of its own diff) found 2 Critical + 6 Important
issues, every one confirmed by the reviewer's own repro against real
files -- not by re-reading the plan and agreeing with it. All eight
fixed, each with its own regression test:

1. **`extract_question()` silently returned the wrong question, or a
   truncated one**, on real files like `homework_1_solutions.md` that
   put numbered sub-parts *inside* a `## Question N` heading -- the
   original dual-mode search treated every sub-part's `N. ` line as its
   own question boundary. Files with any heading now use heading-only
   start/stop; numbered-only files match top-level (unindented) items
   exclusively.
2. **`/draft`'s "blank line or `/end`" terminator** cut real
   multi-paragraph proofs short at the first blank line, and the
   remaining pasted lines spilled into the REPL as unintended
   questions -- each one a real API call plus a logged event, corrupting
   later `/summarize` averages with fragments of a still-pasting draft.
   Now terminates on `/end` only.
3. **`diagnose_draft()`'s rubric regex rejected the model's own routine
   markdown-bold formatting** (`**CORRECTNESS:** 3`) as malformed,
   raising on ordinary output, and `/draft` never caught the resulting
   error -- it crashed the whole REPL session. Regex now tolerates
   markdown emphasis and an optional `/5` suffix; `/draft` catches the
   parse error and reports it instead of crashing.
4. **Out-of-range rubric scores parsed silently** (a `CORRECTNESS: 9`
   slip would have been logged as-is, corrupting `/summarize`'s
   averages). Now raises the same `DiagnosisParseError` as a missing
   line.
5. **One corrupt session-log line broke every future answer for that
   course**, since gap-tag injection reads the log on *every*
   course-scoped question, not just `/summarize`. `load_events()` now
   skips a malformed line with a warning; `_recent_gap_tags()`
   additionally falls back to `[]` on any other read error, since it's
   optional enrichment that must never be able to take down the core
   answer path.
6. **`/draft`/`/verify` used the wrong text after a generated-practice-problem
   request** -- `/draft` compared an attempt against the problem
   statement instead of the solution, and `/verify` asked the stronger
   model to generate a new, unrelated problem instead of re-solving the
   original one. The REPL now uses `generated_problem.problem_text`/
   `solution_text` on that path.
7. **`/verify` sent the raw follow-up text** ("why does that hold?") to
   an independent, historyless model, producing a meaningless answer --
   now uses the same standalone/reformulated question
   `answer_question()` already computes for retrieval.
8. **`/hint` crashed on a mistyped path** (only `QuestionNotFoundError`
   was caught) and mis-split any file path containing spaces. Now
   catches `OSError`/`UnicodeDecodeError`, and takes the question ref as
   the last whitespace-separated token so the file path may contain
   spaces.

## Specific limitations, honestly assessed

- **No retroactive backfill of the historical `_notes`/`_guided`/`[Naive
  Gemini]` files.** Those annotation conventions differ across courses
  and files and aren't machine-clean -- deliberately deferred (spec
  §2), a manual one-off is the fallback if the fresh-data log proves
  useful enough to justify it.
- **No auto-adjudication in `/verify`.** A third model call judging
  which of two prior calls is right would be a new failure mode layered
  on the thing it's trying to catch, not a fix -- the user judges.
- **Session log and gap-tag injection are per-course only.** No
  cross-course aggregation, matching `answer_question()`'s existing
  `course` scoping.
- **Gap-tag injection only applies to `answer_question()`**, not `/hint`
  or `/draft` -- spec §10 names only the normal answer path; a plausible
  future extension, not a defect.
- **Six Minor findings deferred from the final review, none fixed**:
  an inaccurate code comment about which files use `gemini-3.6-flash`;
  duplicate gap tags not deduplicated in the injected prompt line;
  `/summarize` with no unit argument and no `--unit` set loads every
  unit for the course with a slightly confusing message; loose command
  matching (`/hints`, typos) falls through to the normal Q&A path
  instead of erroring; no notice when `--course` is omitted that
  nothing is being logged; `/draft`'s "ask a question first" message
  after a bare `/hint` doesn't explain *why* a hint doesn't count.
- **REPL glue stays outside pytest coverage**, matching every other
  `main()` in this project -- verified manually instead, both during
  initial implementation and the review fix pass.
- **Retrieval is empty for `course="microecon"` in the dev environment
  used for testing this branch** -- not yet confirmed whether the
  `.index/` simply hasn't been built for that course here, or something
  else is wrong. Worth checking before relying on retrieval-grounded
  citations during the user's own Antigravity testing.

## What's next

1. **User validation via Gemini Antigravity** -- the immediate next
   step, per the user's own plan; this doc exists to give that testing
   session (or the user directly) full context without re-deriving it.
2. **Merge PR #14** once that testing is satisfied.
3. **Confirm `.index/` build status** for whichever course gets tested,
   given the empty-retrieval observation above.
4. Revisit the six deferred Minor findings if real usage shows any of
   them actually matter (loose command matching and the no-`--course`
   silent-skip seem the likeliest candidates to bite in practice).
5. Retroactive backfill of historical files -- only if the fresh
   session log, once it accumulates real data, proves valuable enough
   to justify the one-off parsing work.

## 2026-09-27 update: Q4 retrieval failure diagnosed, textbook file-level exclusion fixed

The empty-retrieval limitation above turned out to have a second layer
once real retrieval started working: an auditing pass that reran
`/hint` against a real homework (`homework_3.md`, `microecon`, once its
chunk index was complete -- see `2026-08-29-source-indexer-status.md`'s
same-day entries) found `/hint`'s Question 4 answer talking entirely
about "contraction consistency" and consideration sets -- nothing about
the actual question (random utility, Block-Marschak inequalities, the
Luce model).

**Root cause**: `search()`'s file-level stage ranks a whole file by its
title+summary embedding (`index_card.py`'s `generate_index_card()`,
built from an LLM summary of just the document's first ~12,000
characters). For a large, topic-diverse textbook that's a poor proxy
for whether a deep, later chapter matches a specific query -- confirmed
live: ranked every one of `microecon`'s 6 textbook-tagged files (Rubinstein's
two books, Press, Ok, and two Bonus titles) *below every note and
homework file* against the real Q4 query embedding, including files on
entirely unrelated topics. Rubinstein's own textbook summary
(`"...preferences, utility, consumer choice, risk aversion, and social
choice..."`) never mentions random utility or stochastic choice at all
-- unsurprising, since that content is Chapter 8, in a 1080-page book
whose summary was written from the first 15-20 pages. With
`retrieve_passages()`'s file-level shortlist capped at 5, Rubinstein
(rank 14 of 20) never reached chunk-level ranking, so `/hint` grounded
itself in an unrelated homework's differently-numbered "Question 4"
(a consideration-sets problem) instead, and `generate_hint()` produced
a fluent, well-cited hint for the wrong question.

**Fix**: `retrieve_passages()` (`rag/rag_agent.py`) now runs a second,
`doc_type="textbook"`-scoped `search_passages()` call alongside the
general one, merges the results (deduped by `chunk_id`, re-sorted by
score) before diversifying. Textbooks now only compete against each
other for the file-level cut, so a relevant one no longer has to
out-score every short note/homework file just to be considered. Both
`answer_question()` and `/hint` share this one function, so the fix
applies to normal grounded Q&A too, not just hints. 5 new tests in
`tests/test_rag_agent.py` (the dedicated pool is queried, a
general-pool-excluded textbook passage survives, cross-pool dedup,
score re-sorting); the one existing test asserting a single
`search_passages` call was updated for the new two-call shape. Merged
to `main`.

**Verified live, and only partially fixed**: after the fix, Rubinstein's
and Press's actual Ch.8-adjacent problem chunks *are* retrieved for the
Q4 query (previously zero textbook chunks appeared at all) -- the
file-level exclusion bug is real and the fix closes it. But the specific
chunks that win chunk-level ranking are the textbook's own *practice-
problem listings* ("Problem C13 (NYU 2017)...", a lottery-prize
question), not the expository passages that actually explain
Block-Marschak or the Luce model -- plausibly because a query that is
itself a problem statement embeds more similarly to other problem
statements than to matching theory prose. With those chunks mixed into
the prompt alongside the higher-scoring wrong-topic homework passages,
`generate_hint()` still produced a hint entirely about consideration
sets for this specific example. Fixing this is a harder, chunk-level
relevance question -- separate from "can a textbook be retrieved at
all" -- and is left as a follow-up, not attempted here.

**Next steps**:
1. Investigate why chunk-level ranking favors problem-listing chunks
   over expository theory chunks for a problem-shaped query -- possibly
   worth a query reformulation step (turn the homework question into a
   more theory-shaped query before embedding) or a tier/heading-based
   preference for non-`problem_number` chunks when grounding a hint.
2. Re-run the full 4-question homework_3 comparison once that's
   addressed, to see whether Q4's hint actually becomes topically
   correct, not just better-cited.

## 2026-09-28 update: key-term weighting added; Q4's real problem was never retrieval

User's own diagnosis: dense embeddings likely under-weight a question's
rare, distinctive named terms (a theorem, a named model) relative to
its generic formal-math boilerplate -- exactly what let an unrelated
homework's differently-numbered "Question 4" outscore every real
textbook for the actual Question 4 above. Asked to identify those
terms and weight matching sources higher.

**Added**: `_extract_key_terms()` in `rag/rag_agent.py` -- a small
`GENERATION_MODEL` call, same pattern as `_reformulate_query()` --
lists a question's specific named theorems/models/inequalities (e.g.
"Block Marschak inequalities", "Luce model"), skipping generic terms
that appear in nearly every question in the field. `retrieve_passages()`
takes an optional `key_terms` param and rewards passages that literally
contain them (`_KEY_TERM_BONUS = 0.08` per matched term, tuned against
real corpus score gaps -- see the function's own docstring) before the
final diversify+cap. Deliberately opt-in, not automatic:
`retrieve_passages()` itself never calls the extractor, since
`answer_question()`'s normal Q&A path runs on every message and
shouldn't pay for a call only `/hint` benefits from. `/hint`'s own
handler extracts once, passes the terms through for the boost, and
reuses them afterward: if none of the final passages match any
extracted term, it now prints a note that the hint may not be
well-grounded, instead of silently handing over a confidently-worded
wrong-topic answer. 8 new tests in `tests/test_rag_agent.py`. Merged to
`main`.

**Also fixed, found while touching this again**: the prior
textbook-pool commit (2026-09-27) had already broken three tests that
asserted `search_passages` was called exactly once -- missed at the
time because the failures looked identical to this suite's own,
already-known, unrelated `viz`/`plotly` import failures. Verified each
failing test individually this time rather than assuming the whole
list was the same cluster; two were real regressions
(`TestAnswerQuestion::test_first_turn_skips_reformulation`,
`test_follow_up_uses_reformulated_query_for_retrieval`) plus one more
in `TestAnswerQuestionProblemGeneration`, all fixed alongside this
change.

**Verified live against the real Question 4, with the boost active**:
extraction correctly named all six distinctive terms (random utility
representation, Block Marschak inequalities, inclusion-exclusion
principle, stochastic independence of irrelevant alternatives, Luce
model, Type 1 extreme value distribution). But **zero** of the six
retrieved passages contained any of them -- confirming, independently
of the earlier corpus grep, that this specific content genuinely isn't
in the indexed corpus. The boost correctly had nothing to promote, and
the low-confidence note correctly fired. The hint text itself is still
wrong-topic for this example; that's now an honest "may not be
well-grounded" flag rather than a silent failure, which is as far as a
retrieval-side fix can take it. Closing this for real needs the
missing course material (Mark Dean's stochastic-choice lecture notes,
or equivalent) to actually exist in academic-hub -- a content gap, not
a ranking one -- left for the user to decide whether it's worth
tracking down and indexing.

## 2026-09-28 update: ungrounded fallback for the no-match case

User's call, given the above: an on-topic hint from the model's own
general knowledge beats a well-cited hint grounded in the wrong topic.
Rather than stop at the low-confidence note, `/hint` now falls back to
one when nothing retrieved matches the question's own key terms.

**Added**: `generate_ungrounded_hint()` (`rag/tutor_diagnosis.py`) --
same pedagogical constraints as `generate_hint()` (no final answer, no
verdict, no worked derivation), but no excerpts block; asks the model
to draw on its own general knowledge instead. `/hint`'s handler
branches on the same `grounded` check that already produced the
warning note: grounded uses `generate_hint()` as before; ungrounded
calls the new function, clears `hint_passages` (nothing real to cite),
and tells the student plainly the hint isn't sourced from their own
materials. `Event` gained a `grounded: bool = True` field
(`rag/session_log.py`) so a logged ungrounded hint is distinguishable
from a normal one -- defaults true so every event logged before this
field existed reads back correctly. 7 new tests across
`test_tutor_diagnosis.py` and `test_session_log.py` (including one
confirming a pre-field log line still loads without crashing).

**Verified live against the real Question 4**: the ungrounded fallback
correctly covers random utility, Block-Marschak inequalities,
inclusion-exclusion, and the Luce model/IIA equivalence -- genuinely
on-topic for the first time across every version of this hint tried
across both of today's updates. Merged to `main`.

**Known limitation, by design**: an ungrounded hint has no citations to
show and isn't checked against the course's own notation or
conventions, so it's a strictly worse hint than a real grounded one
whenever the corpus actually has the right material -- this fallback
only fires when key terms were extracted and none matched, which
should be rare outside genuine content gaps like this one. Not logged
anywhere except the `grounded: false` event field; no dashboard or
report currently surfaces "how often is /hint falling back," which
would be the natural signal for deciding whether a content gap is
worth fixing versus one-off.

## 2026-09-28 update: fallback counts surfaced in /summarize

Closed the gap named directly above, same day: the `grounded: false`
event field existed but nothing ever surfaced it, so a student
skimming `/summarize` couldn't tell a hint had quietly come from
outside knowledge instead of their own materials.

**Added**: `_format_event()` (`rag/tutor_diagnosis.py`) now appends a
note to any ungrounded hint event before it enters the summary prompt
-- a grounded hint's formatting is unchanged -- so the LLM-written
"What we learned"/"What to focus on" sections can name the gap in
their own words rather than silently treating it like normal grounded
output. `_ungrounded_fallback_line()` -- computed, not model-generated,
same reasoning as the existing rubric-averages line -- is appended
after `summarize_unit()`'s generated text: a count of how many hints
this unit fell back to outside knowledge plus a snippet of which
questions triggered it, or an explicit confirmation that all hints
were grounded when none did. 12 new tests.

**Verified live**: fed a two-hint session (one grounded, one not, the
real Question 4 case) through `summarize_unit()`. The model's own
"What to focus on" section named "reliance on external knowledge for
core topics" and "Alignment with Course Materials" as the top item
unprompted, and the computed line reported "Grounding: 1 of 2 hint(s)
this unit found nothing matching in your course materials... : ##
Question 4 Here are some questions involving classic results in
random utilit...". Both signals -- narrative and computed -- now
agree, matching the intent: the student should never have to guess
whether a hint came from their own materials.

This closes the loop `docs/status/2026-08-29-source-indexer-status.md`
started (the page-marker leak) through today's full path: chunk-level
fix -> retrieval-level fix (textbook pool, key-term weighting) ->
generation-level fallback (ungrounded hint) -> visibility (this
update). No further work queued on this thread; the remaining open
item is still the missing course material itself (Mark Dean's
stochastic-choice notes or equivalent), which is a content decision
for the user, not an engineering one.

**Checked and ruled out, so this doesn't need re-investigating later**:
whether the missing material is sitting unconverted somewhere in
academic-hub rather than genuinely absent. It isn't -- every raw PDF
under `academic_resources/microecon/professor_notes/` already has a
matching converted, chunked `.md` (no `4.*` file waiting behind
`1`/`2`/`3`); the only orphaned card in the whole `microecon` index is
a confirmed stale rename artifact (`Drawing 2026-09-07...` ->
`Microeconomics lecture 2026-09-07...`) whose original file no longer
exists on disk, not a hidden second copy; and a filename search across
all of `academic-hub` for "stochastic" or "Dean" turns up nothing
relevant. Most likely explanation: this material was never added to
academic-hub at all, or the original Antigravity hint's citation to
it was never actually grounded in a retrieved passage in the first
place. Left as a known content gap, not pursued further this session.
