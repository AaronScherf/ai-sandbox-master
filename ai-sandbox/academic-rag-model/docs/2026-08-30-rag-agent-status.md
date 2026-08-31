# RAG Tutoring Agent: Status Summary

Start here for "what happened and where do we stand" on the RAG
tutoring agent subproject -- `rag_agent.py`, which answers questions
grounded in the academic-hub corpus via the passage-level retrieval
built on top of the source indexer. Design reference:
`docs/superpowers/specs/2026-08-30-rag-agent-design.md`; implementation
plan: `docs/superpowers/plans/2026-08-30-rag-agent.md`. Merged into
`marker-conversion` 2026-08-30.

## What shipped

One core function, `answer_question()`, deliberately stateless per call
-- conversation history is an explicit input/output the caller owns,
not internal session state. This is what lets it serve both usage
modes from the original project intent without two separate
implementations: a callable utility (`from rag_agent import
answer_question`, call once, use the result) and an interactive chat
(`rag_agent.py`'s own REPL, which threads `.history` across turns).

Pipeline inside `answer_question()`:
1. **Query reformulation** (`_reformulate_query()`) -- on any turn past
   the first, condenses a follow-up ("explain that differently") into a
   standalone, retrievable question using recent history. Skipped
   entirely on the first turn.
2. **Retrieval** -- the reformulated (or original) question goes to the
   already-shipped `search_passages()` (source-indexer subproject),
   requesting `top_k * 2` candidates.
3. **Diversification** (`_diversify_by_file()`) -- caps how many of the
   top-ranked passages can come from the same file, so a comparative
   question ("how do two textbooks treat this") actually gets material
   from multiple sources rather than one dominant file crowding out the
   rest.
4. **Generation** (`_generate_answer()`) -- prompts the model to answer
   using *only* the retrieved excerpts, citing each one inline via the
   citation label already produced by `index_search.py`'s
   `_render_citation()` (e.g. `"§7.4 Adjoints..., p. 264-266"`), and to
   say so plainly rather than filling gaps from general knowledge when
   the excerpts don't cover the question.
5. Returns the answer, a structured `Citation` list (every retrieved
   passage actually placed in the prompt -- not a parse of which ones
   the model's inline citations reference, which would be far more
   fragile), and the updated `history`.

Two entry points: `index_search.py ask "question" [--course X]` for a
single question with no memory, and `rag_agent.py`'s own `main()` for a
multi-turn REPL.

## Real-corpus validation

Confirmed live, not just unit-tested:

- **A real query end to end**, "what is the spectral theorem" --
  produced a substantive, correctly-cited, well-organized answer
  synthesizing content from two different files (`LN_Linear
  Algebra.md` and `Part I Linear Algebra 08.13 (1).md`), each citation
  a real, checkable theorem/page reference.
- **A real multi-turn exchange** -- history correctly accumulated (2
  turns → 4 entries), the second turn's reformulation call fired and
  produced an on-topic standalone question
  ("Can you explain the Spectral Theorem and its application to
  simplifying quadratic forms in simple terms suitable for a
  beginner?"), confirmed by directly inspecting the reformulated string.
- **A real model comparison** -- `gemini-3.6-flash` vs.
  `gemini-3.1-flash-lite` on the same question showed no meaningful
  quality or coverage difference (see "Corrections" below).

## Corrections made against real evidence, not assumptions

1. **`TUTOR_MODEL` was originally `gemini-3.6-flash`**, chosen on an
   untested heuristic ("tutoring needs more reasoning than this
   project's cheap tier"). A real side-by-side comparison disproved
   this -- switched to `gemini-3.1-flash-lite`, cheaper with no
   observed quality loss. Documented in the spec's §2/§5 revision notes
   and `rag_agent.py`'s own constant comment.
2. **A circular-import risk caught during planning, before it became a
   bug**: `rag_agent.py` imports from `index_search.py`
   (`search_passages`, `PassageResult`), so `index_search.py` cannot
   import `rag_agent` at module top-level the way it does for
   `chunk`/`retag` -- the `ask` subcommand uses a function-scoped
   import instead, called out explicitly in the plan so it wouldn't
   read as an oversight during review.
3. **A real retrieval/generation variance observed, not fully
   explained**: during the live multi-turn test, one specific follow-up
   run produced an answer citing files that didn't even appear in a
   direct re-run of retrieval for the same (correctly reformulated)
   query. Diagnosed as far as evidence allowed: the reformulation step
   itself was confirmed correct via direct inspection, and retrieval
   for that exact query was confirmed good via a direct re-run --
   the most likely explanation is temperature=0 not being perfectly
   deterministic server-side, especially given many real passages score
   closely together (0.68-0.74, a tight cluster where a slightly
   different reformulation phrasing could plausibly reorder results).
   Not chased further speculatively -- recorded here as a known,
   real, not-fully-explained source of run-to-run variance rather than
   quietly ignored.

## Specific limitations, honestly assessed

- **No persistent memory.** `history` lives only for one process's
  lifetime (spec §8, deliberate) -- the REPL forgets everything on
  exit, and the callable-utility mode has no built-in way to resume a
  prior conversation. Anything "context-aware" across sessions (a
  scheduled daily task that needs to know what was covered yesterday,
  for instance) needs this built first.
- **Not designed for extended or structured reports.** The current
  pipeline retrieves a small, fixed number of passages (`top_k=6` by
  default) for one question and generates a single grounded answer --
  workable for "summarize chapter 7," untested and likely too narrow
  for "summarize everything I've covered this week." Producing a
  genuinely long, structured report (multiple sections, broader
  coverage) would need a different retrieval strategy (more passages,
  probably multiple retrieval passes across sub-topics) and likely a
  different prompt shape than the single-answer template built here.
- **Not designed for generating new problem sets.** The generation
  prompt is a deliberate anti-hallucination guardrail: "do not
  introduce any claim... that isn't supported by the excerpts." Correct
  for tutoring, but it actively works against generating something
  genuinely new, since a new problem is by definition not sitting
  verbatim in retrieved passages. A real, separate task -- reusing the
  same retrieval infrastructure, but with retrieved problems used as
  style/difficulty reference rather than facts to cite, plus (per the
  user's own framing) probably wanting *both* a lookup mode (find and
  return real existing problems, some of which already have linked
  solutions in the corpus) and a generate-new mode as distinct options.
- **Not designed for study plans.** Needs broader, structural
  awareness of what exists and how to sequence it -- closer to the
  file-level `search()` and course-level tag rollups already in the
  indexer than to narrow passage-level retrieval -- plus real
  sequencing/pacing logic that doesn't exist anywhere in this project
  yet. Matches the original project page's own framing: a study-plan
  agent that *calls* this RAG agent as one building block, not
  something this RAG agent does by itself.
- **Scheduling is mechanically solved, context-awareness is not.**
  `index_search.py ask "..."` is already a plain, non-interactive
  command a scheduled job (Windows Task Scheduler) can run today for
  any *fixed* question. A scheduled task that needs to know what
  changed since last time, or what was covered in a prior session,
  needs the persistent-memory piece above first.
- **Between-course retrieval is unvalidated.** The entire corpus today
  is one course (`math-camp`) -- `search_passages()`'s course-level
  pre-filter and cross-course ranking have never been exercised against
  real data with more than one course present. Worth deliberately
  testing once a second course exists, not assuming it works.

## What's next

In rough dependency order, per discussion with the user 2026-08-30:

1. **Persistent conversation/activity history** -- the real prerequisite
   for context-aware scheduling and for anything that needs to know
   "what did I already cover." Not yet spec'd.
2. **Problem-set subsystem** -- lookup (retrieve real existing problems,
   using linked solutions where the corpus already has them) and
   generate-new (style/difficulty-matched novel problems) as distinct,
   probably separate, modes. Not yet spec'd.
3. **Extended/structured report generation** -- a genuinely different
   retrieval+generation shape than single-question tutoring. Not yet
   spec'd.
4. **Study-plan agent** -- syllabus/course-aware, likely calling this
   RAG agent (or the underlying `search()`/`search_passages()`
   directly) as one component rather than being built as an extension
   of it. Not yet spec'd.
5. **Between-course retrieval validation** -- once a second course
   enters the corpus, confirm `search_passages()`'s cross-course
   behavior against real data rather than assume it from the
   single-course design.

Explicitly still deferred (unchanged from the design spec): public
deployment (real fair-use exposure, needs real legal input, not an
engineering choice); a generation-backend swap away from the paid
Gemini key (Gemini CLI's OAuth free tier, or `claude -p` under the
user's Claude Pro subscription) -- kept as a contained, later change
via the `TUTOR_MODEL` constant, not designed around speculatively now.
