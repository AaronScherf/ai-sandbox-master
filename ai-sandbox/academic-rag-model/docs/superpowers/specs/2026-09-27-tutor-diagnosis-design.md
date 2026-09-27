# Problem-Set Tutor Diagnosis Design

Brainstormed and approved with the user 2026-09-26/27, as a direct
extension of the RAG tutoring agent
(`docs/superpowers/specs/2026-08-30-rag-agent-design.md`, `rag/rag_agent.py`).
That spec built grounded Q&A, problem generation, and visualization.
This one closes the loop between that Q&A and the user's actual
problem-set workflow: ask an AI for an explanation, learn from it, then
write a summarized solution that fits the course's own notation and
framing.

## 1. Problem & goals

Auditing `academic-hub/academic_notes/{econometrics,microecon}/problem_sets/`
surfaced two patterns:

- **microecon**: `homework_1_solutions.md` (clean, submitted) vs.
  `homework_1_solutions_notes.md` (the same problems annotated with
  `[First Attempt]`, `[Wait, what if...]`, `[Corrected with proper
  induction]`) -- a preserved record of exactly where the user's own
  reasoning went wrong before self-correcting.
- **econometrics**: `problem_set_1_gemini_solutions.md` embeds a
  deliberate `[Naive Gemini]` (subtly flawed) proof next to a
  `[Correct Gemini]` one with a "Where the Flaw Lies" section -- using
  the AI to manufacture contrast cases, not just get one answer.

Both patterns are the same underlying need: the user's individual
error patterns are the highest-value tutoring signal available, but
today capturing and reconciling them is entirely manual. This spec
adds four REPL capabilities on top of `answer_question()`'s existing
retrieval and generation:

1. **`/hint`** -- guidance before an attempt exists, grounded in the
   corpus, without giving away the answer.
2. **`/draft`** -- reconciling a finished attempt against a grounded
   reference answer, producing a diagnosis instead of just a verdict.
3. **`/verify`** -- an independent, ungrounded cross-check against a
   stronger model, since grounding in retrieved excerpts doesn't by
   itself guarantee a correct derivation.
4. **`/summarize`** -- a unit-level (e.g. one problem set) retrospective
   over everything the session produced, once the user is done and
   reviewing.

All four log structured events to a per-course session log, which also
lets `answer_question()` (phase 2, §10) proactively surface the user's
own recurring gaps in future answers.

## 2. Scope / non-goals

- **Retroactively parsing the existing `_notes`/`_guided`/`[Naive
  Gemini]` files** to backfill the session log. Those annotation
  conventions differ across courses and files and aren't machine-clean
  (see §6's parser scope). Worth a manual/semi-automated one-off later
  if the log proves useful with fresh data; not built here.
- **Auto-adjudicating `/verify`'s two solutions.** A third model call
  judging which of two prior calls is right is a new failure mode
  layered on the thing it's trying to catch, not a fix. `/verify`
  displays both; the user judges.
- **Cross-course aggregation.** The session log and gap-tag injection
  are scoped per course, matching how `answer_question()` is already
  scoped (`course: str | None`).
- **Public deployment, local/open-weight generation, a vector DB.**
  Unchanged from the rag-agent spec's own deferrals (§1 there) -- this
  extension doesn't revisit them.

## 3. Shared retrieval refactor

`answer_question()` currently inlines retrieval:

```python
passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
passages = _diversify_by_file(passages, max_per_file)[:top_k]
```

Pulled out into a reusable function (renamed without the leading
underscore, since it's now called from another module):

```python
def retrieve_passages(
    roots: list[str], query: str, client,
    course: str | None = None, top_k: int = 6, max_per_file: int = 3,
) -> list[PassageResult]:
    passages = search_passages(roots, query, client, course=course, top_k=top_k * 2)
    return _diversify_by_file(passages, max_per_file)[:top_k]
```

`answer_question()` calls this instead of the inlined version
(behavior-identical). `/hint` (§6) calls it directly for its own
retrieval. `/draft` and `/verify` do **not** call it: `/draft` reuses
whatever passages the most recent normal answer already retrieved
(§5), and `/verify` is deliberately ungrounded (§7).

## 4. New module layout

Three new files under `rag/`, kept separate from `rag_agent.py` for
the same isolation reason `viz/` and `problem_gen/` are their own
packages -- each is independently testable and has one job:

- **`rag/session_log.py`** -- `Event` dataclass, `append_event()`,
  `load_events()`. Pure JSON I/O, no LLM calls, no mocking needed to
  test.
- **`rag/problem_set_parser.py`** -- `extract_question()`. Pure text
  parsing, no LLM calls.
- **`rag/tutor_diagnosis.py`** -- `diagnose_draft()`, `generate_hint()`,
  `generate_verification()`, `summarize_unit()`. Four thin
  prompt-template-and-generate functions, mirroring
  `rag_agent._generate_answer()`'s existing pattern (build prompt,
  `call_with_retries`, return text).

## 5. `/draft` -- reconciling an attempt against the reference

Usage: after a normal question gets a grounded answer (unchanged
flow), the user types `/draft`, then pastes their own attempt
(terminated by a blank line). The REPL calls:

```python
def diagnose_draft(
    question: str, reference_answer: str, passages: list[PassageResult],
    draft: str, client,
) -> Diagnosis:
    ...
```

```python
@dataclass
class Diagnosis:
    text: str      # what the draft covered correctly, what's missing or
                    # wrong -- each claim grounded back to a cited excerpt,
                    # same discipline as _ANSWER_PROMPT_TEMPLATE
    gap_tag: str    # short free-text label, e.g. "vacuous-case-overlooked"
```

The prompt instructs the model to end its response with a line
`GAP_TAG: <short-kebab-label>`, parsed out with a regex (same
"respond with ONLY X" convention `_REFORMULATE_PROMPT_TEMPLATE`
already uses for a single-line constrained output). `gap_tag` is
free text, not a fixed taxonomy -- it should name whatever's actually
true of this attempt, not be forced into predefined buckets.

The REPL prints `diagnosis.text`, then appends a `"draft"` event to
the session log (§8) with the diagnosis text, gap tag, and the
reference answer's citations.

**Revisions**: running `/draft` again on the same question with an
updated attempt is just another event -- the append-only log
preserves the sequence of attempts naturally, which is what makes
`/summarize` (§9) able to show "first attempt" through "revision."

## 6. `/hint <file> <question-ref>` -- guidance before an attempt exists

```python
def extract_question(file_path: str, question_ref: str) -> str:
    ...
```

Matches `question_ref` against `## Question N` headings or top-level
numbered items (`N.`) in the target file. **Scoped to fresh, unsolved
files** (e.g. `homework_3.md`, where the structure is clean) --
matches §2's exclusion of the historical `_notes`/`_guided` files,
which mix questions and solutions in ways this parser isn't built to
separate. Raises a clear error if `question_ref` isn't found rather
than guessing.

The extracted question text is retrieved the normal way
(`retrieve_passages()`, §3), but generation uses a prompt explicitly
barred from stating the final answer, verdict, or worked derivation --
only a motivating sketch of the right technique or theorem to reach
for, plus which excerpts to look at:

```python
def generate_hint(question: str, passages: list[PassageResult], client) -> str:
    ...
```

The REPL prints the hint plus the citation list (same `Citation`
construction `answer_question()` already does from `passages`), and
appends a `"hint"` event to the session log.

## 7. `/verify` -- independent cross-check

Re-solves whichever question most recently produced output in the
REPL (any of a normal answer, `/hint`, or `/draft` -- tracked in a
`last_question: str | None` REPL-local variable, updated by all three).

```python
VERIFY_MODEL = "gemini-3.6-flash"  # this project's existing "stronger"
# tier (already used for textbook conversion and transcription,
# indexer/index_card.py and textbook/convert_textbook.py) -- chosen over
# TUTOR_MODEL specifically because this call exists to catch reasoning
# errors the cheap tier makes; checking a cheap model's output with the
# same cheap model is weak evidence. Opt-in and per-question, not run on
# every query, so the cost difference doesn't compound the way it would
# if this were the default generation path.

def generate_verification(question: str, client) -> str:
    ...
```

Deliberately **not** grounded in retrieved excerpts and **not** shown
the tutor's own prior answer -- an independent solve from the
question text alone, so it can't just rationalize agreement with
reasoning it's already seen. The REPL prints both outputs side by
side and appends a `"verify"` event to the session log. No
auto-adjudication (§2).

## 8. Session log -- schema & storage

**Location**: `<academic_hub_root>/.session_log/<course>.jsonl`, i.e.
`roots[0]/.session_log/<course>.jsonl` -- matching where
`.reports/`, `.viz/`, and `.problem_corpus/` already live (derived,
corpus-grounded content rooted alongside the corpus itself, not under
`academic-rag-model/`), per `rag/report_builder.py`'s existing
`report_path()` convention. JSON Lines, not a single JSON array, so
each event is an independent append (`open(path, "a")`) rather than a
read-modify-write-whole-file on every action.

**Gitignore**: add `**/.session_log/` to the root `.gitignore`,
alongside the existing `**/.reports/`, `**/.viz/`,
`**/.problem_corpus/` entries -- same IP posture, since event text
embeds excerpt citations and quoted corpus content the same way
reports and problem-corpus extracts already do.

```python
@dataclass
class Event:
    type: str              # "answer" | "draft" | "hint" | "verify"
    course: str
    unit: str | None       # e.g. "homework_3" -- see below
    question: str
    text: str               # the generated output: answer / diagnosis / hint / verify text
    citations: list[Citation]
    timestamp: str          # ISO 8601
    gap_tag: str | None = None  # set only for type == "draft"


def append_event(roots: list[str], event: Event) -> None: ...
def load_events(roots: list[str], course: str, unit: str | None = None) -> list[Event]: ...
```

**Tagging events to a unit**: rather than passing a unit on every
command, the REPL accepts an optional `--unit` at startup (e.g.
`rag_agent.py --course microecon --unit homework_3`), stamped on
every event for that session. A normal answered question also
appends an `"answer"` event now (previously it only lived in the
in-memory `history: list[Turn]`) -- needed so `/summarize` (§9) can
see "the back and forth," not just diagnoses.

## 9. `/summarize [unit]` -- unit-level retrospective

```python
def summarize_unit(events: list[Event], client) -> str:
    ...
```

Loads every event for `(course, unit)` (defaulting to the REPL's
`--unit` if the argument is omitted) via `load_events()`, and
generates two sections:

- **What we learned** -- synthesized from the `answer`/`draft`/`verify`
  events, citing the same excerpt citations already attached to each
  event.
- **What to focus on** -- the recurring `gap_tag`s across `draft`
  events and any unresolved `verify` discrepancies, prioritized.

Pure aggregation over already-grounded events -- no new retrieval, so
every claim in the summary traces back to a citation the user already
saw during the session. Event text is included in full (not
truncated to the most-recent-N the way conversational `history` is
capped elsewhere in this project) since this is a retrospective over
the *whole* unit, not a continuity aid for an ongoing exchange.

## 10. Phase 2 -- gap-tag context injection

`answer_question()` gains an optional step: before generating a new
answer, load the course's recent `draft`-type events from the session
log and fold their `gap_tag`s into `_ANSWER_PROMPT_TEMPLATE` as a
short "the student has previously struggled with: X, Y" line -- so a
new answer can proactively flag when it touches a known blind spot,
without the user having to remember their own history of mistakes.
Filters the same `Event` stream `/summarize` reads (§9), not a
separate store.

## 11. REPL integration summary

New state in `main()`'s loop, alongside the existing
`history: list[Turn]`:

- `last_question: str | None` -- updated by a normal answer, `/hint`,
  and `/draft`; read by `/verify`.
- `last_answer` / `last_passages` -- the most recent normal answer's
  output and retrieved passages; read by `/draft`.
- `unit: str | None` -- set once from `--unit` at startup; stamped on
  every event.

New commands: `/draft` (multi-line paste, blank line or `/end`
terminates), `/hint <file> <question-ref>`, `/verify`, `/summarize
[unit]`.

## 12. Testing

- `retrieve_passages()`: gets its own test once split out of
  `answer_question()`, replacing the retrieval assertions currently
  folded into that function's tests.
- `extract_question()`: tested against real fixture files -- numeric
  ref, heading match, not-found case.
- `diagnose_draft()`, `generate_hint()`, `generate_verification()`,
  `summarize_unit()`: mocked-client tests mirroring
  `_generate_answer()`'s existing pattern.
- `append_event()` / `load_events()`: pure I/O, tested against a temp
  directory without mocking -- append then load round-trips, unit
  filtering excludes other units/courses.
- REPL glue (`main()`'s new command branches): untested, same
  convention as every other `main()` in this project.

## 13. Explicitly not built here

- Retroactive parsing of historical `_notes`/`_guided`/`[Naive
  Gemini]` files into the session log (§2) -- fragile given
  inconsistent conventions across files; a manual backfill is the
  fallback if this becomes worth doing.
- Auto-adjudication of `/verify`'s two outputs (§2) -- a new failure
  mode, not a fix.
- Cross-course gap aggregation (§2) -- session log and gap-tag
  injection stay per-course, matching `answer_question()`'s existing
  `course` scoping.
- Public deployment / local generation / vector DB -- unchanged from
  the rag-agent spec's own deferrals.
