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
