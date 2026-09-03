# Problem Generation Sub-Agent Design

Brainstormed and approved with the user 2026-09-03. Direct consumer of
the source indexer's retrieval (`indexer/index_search.py`'s
`search_passages()`) and a new peer of the RAG tutoring agent
(`rag/rag_agent.py`, `docs/superpowers/specs/2026-08-30-rag-agent-design.md`)
and the visualization sub-agent (`viz/`,
`docs/superpowers/specs/2026-09-02-visualization-agent-design.md`), whose
structure this design deliberately mirrors.

## 1. Problem & goals

The tutor (`answer_question()`) answers questions grounded in retrieved
passages, but it has no way to *generate new practice material*. The
student's math-camp corpus already contains real problem sets and past
exams (2017–2025, several with worked solutions) and five processed
textbooks — enough raw material to draw both style and content from.
This spec builds a **problem generation sub-agent**: given a topic
implied by the student's question, it produces a new practice problem
(not copied from the corpus) plus a worked solution, styled after the
student's own problem sets and grounded in their own textbooks.

**Explicit constraint carried through every decision below, set by the
user 2026-09-03:** generation itself uses a local Ollama model only, no
paid API call — same posture as `viz/`'s LLM fallback, for the same
reason (call volume/prompt size here is driven by however often a
student asks for practice, not a fixed-shape single call). Retrieval
still uses the Gemini client `rag_agent` already holds for embeddings —
that is an existing dependency of every retrieval call in this project,
not new spend introduced by this subproject.

**Goals**
- Given a topic (the student's question) and a course, retrieve the
  student's own real problems on that topic (style/difficulty anchor)
  and their own textbook content on that topic (correctness anchor),
  then generate a new problem plus a worked solution via a local model.
- Self-verify the generated solution actually solves the generated
  problem before returning it; retry with the failure fed back to the
  model, rather than silently returning a wrong or ill-posed problem.
- Integrate into `rag_agent.answer_question()` via automatic intent
  detection on the question text — a student doesn't need special
  syntax to ask for a practice problem.
- Degrade gracefully at every failure point (Ollama not running,
  verification never passes, no style examples on the topic) by falling
  back to the tutor's normal Q&A behavior — never a hard failure of the
  question-answering call itself.

**Non-goals**
- A difficulty parameter/slider. Difficulty is implicit — inferred by
  the model from the retrieved style examples and the student's own
  phrasing ("an easy problem on...", "a hard one on..."). Revisit only
  if real usage shows this isn't good enough (this project's established
  evidence-driven pattern, per the status docs).
- Multiple problems per request. One problem per call; "give me
  another" is simply another call — see §4's no-caching decision, which
  is what makes repeated requests actually return different problems.
- A paid-API fallback if Ollama is unavailable. Per the user's explicit
  choice this is local-only; unlike `viz/`, there is no secondary paid
  tier here — unavailability degrades to falling back to normal Q&A
  (§6), not to spending money to guarantee an answer.
- Content-pool retrieval beyond `doc_type="textbook"` (e.g. also
  pulling from `ta_notes`/`handwritten_notes`). `search_passages()`
  takes one `doc_type` value (§3); a course whose textbook coverage
  turns out too thin to ground problems well is a real-evidence-driven
  reason to extend that later, not a speculative one built now.
- Tracking conversation state to resolve a bare follow-up like "give me
  another one" that drops the word "problem" entirely. The intent
  heuristic (§5) matches on the literal question text only; this is a
  known limitation, not solved here.

## 2. Architecture

New package `problem_gen/`, alongside `viz/`/`rag/`/`indexer/` —
matching this project's existing per-subproject package convention.

```
academic-rag-model/
  problem_gen/
    __init__.py
    README.md
    generator.py    # generate_problem(), the one public entry point
    llm_gen.py       # Ollama prompt-building, extraction, generate+verify+retry loop
  common/
    ollama_utils.py  # NEW: shared Ollama HTTP-call helper, extracted from viz/llm_fallback.py
```

`common/ollama_utils.py` is a small, targeted refactor alongside this
work, not a separate project: `viz/llm_fallback.py`'s `_call_ollama` and
its `_OllamaTimeout` sentinel (a live-but-slow call is worth retrying;
a genuinely unreachable server isn't — see that module's own docstring)
are exactly the logic `problem_gen/llm_gen.py` also needs. Duplicating
~30 lines of HTTP-call/timeout-distinction code across two subprojects
the same day this second one is built is the kind of problem the
brainstorming process asks to fix inline rather than copy — so
`viz/llm_fallback.py` is refactored to import this shared helper too,
with no behavior change (existing viz tests continue to pass, updated
only to mock the shared call site instead of the old private one).

```python
# common/ollama_utils.py
class OllamaTimeout:
    """Sentinel distinguishing a live-but-slow call from a genuinely
    unreachable server (see viz/llm_fallback.py's original docstring)."""

OLLAMA_TIMEOUT = OllamaTimeout()

def call_ollama(prompt: str, model: str, request_timeout: int) -> str | None | OllamaTimeout:
    """POSTs to Ollama's local HTTP API. Returns the response text, None
    if the server is unreachable, or OLLAMA_TIMEOUT if the request
    itself timed out. Never raises."""
```

One public function, `problem_gen/generator.py`:

```python
from dataclasses import dataclass

@dataclass
class ProblemSource:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    root: str
    role: str  # "style" | "content"

@dataclass
class GeneratedProblem:
    problem_text: str
    solution_text: str
    sources: list[ProblemSource]

def generate_problem(
    query: str, roots: list[str], client, course: str | None = None,
    style_top_k: int = 3, content_top_k: int = 4,
) -> GeneratedProblem | None:
    """Returns None if there are no style examples to ground a new
    problem on this topic/course, or if generation+verification never
    succeeds (e.g. Ollama not running) -- callers must handle this
    being unavailable and fall back to normal Q&A, never treat problem
    generation as a hard dependency (§6)."""
```

`ProblemSource` deliberately doesn't reuse `rag_agent.Citation` — that
would make this lower-level package depend on its own consumer.
`rag_agent.py` converts `ProblemSource` into its own `Citation` at the
integration point (§6), dropping the `role` field that only this
subproject's retrieval strategy needs.

## 3. Retrieval: two pools, one small indexer extension

`indexer.index_search.search_passages()` currently takes no `doc_type`
filter, even though the file-level `search()` it wraps already has one.
This is a one-line extension, not a new capability — thread the
existing parameter through:

```python
def search_passages(
    roots: list[str], query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5, doc_type: str | None = None,
) -> list[PassageResult]:
    file_results = search(roots, query, client, course=course, top_k=file_top_k, doc_type=doc_type)
    ...
```

`generate_problem()` then makes two calls:

1. **Style pool** — `doc_type="problem_set"`, `top_k=style_top_k`. The
   indexer already chunks problem sets one-problem-per-chunk (numbered-
   problem detection, `chunk_index.py`'s `problem_label` tier), so these
   passages are real individual problems from the student's own sets
   and past exams — the phrasing, notation, and difficulty anchor. **If
   this pool comes back empty, `generate_problem()` returns `None`
   immediately** — there's nothing to style a new problem after, and
   generating one ungrounded would defeat the point of this subproject.
2. **Content pool** — `doc_type="textbook"`, `top_k=content_top_k`. Real
   definitions/theorems/examples from the actual textbooks (Rudin,
   Axler, Simon, Sydsæter, Blume), grounding the generated problem's
   math in real content rather than the local model's own possibly-
   incorrect recollection. **If this pool is empty** (no indexed
   textbook for this course), generation proceeds on the style pool
   alone — not a hard failure, since a topic can plausibly be generated
   correctly from good style examples even without textbook grounding.

Both calls reuse the raw `query` (the student's question, or the
reformulated standalone version on a follow-up turn — same string
`rag_agent.answer_question()` already computes) as the search string,
the same choice `viz/`'s integration made for template matching (spec
§6 there): no separate LLM call to isolate a clean topic phrase out of
the full sentence.

## 4. Generation + self-verification (local Ollama, no sandboxing)

Simpler than `viz/llm_fallback.py` by design: output here is text (a
problem statement and a worked solution), not executable code, so there
is no subprocess execution or restricted-import concern at all — the
generated text is just returned, never run.

Default model: `qwen2.5-math:7b` — math-tuned, unlike `viz/`'s
code-tuned `qwen2.5-coder:7b`, since this generates mathematical
reasoning, not code. Overridable via `PROBLEMGEN_OLLAMA_MODEL`, matching
`VIZ_OLLAMA_MODEL`'s existing convention. Requires `ollama pull
qwen2.5-math:7b` as a one-time setup step (documented in this
subproject's README, same as `viz/`'s).

**Generation prompt** asks for a *new* problem (explicitly: not a copy
of the given examples) on the given topic, in the same notation/style as
the style examples, grounded in the content excerpts where relevant,
formatted as two labeled sections so extraction is unambiguous:

```
## Problem
<problem statement>

## Solution
<full worked solution>
```

**Verification prompt** (a second, separate call) gives the model back
its own `problem_text` and `solution_text` and asks it to check whether
the solution is actually correct and complete for the stated problem,
responding with exactly `VALID` or `INVALID: <short reason>`.

**Retry loop**, capped at `MAX_ATTEMPTS = 3`, mirroring `viz/`'s
retry-hardening pattern
(`docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`):
on any failure — extraction fails (no `## Problem`/`## Solution`
sections found), or verification returns `INVALID: <reason>` — the
specific failure is fed back into the next attempt's prompt asking for
a corrected problem/solution. On `call_ollama` returning `None` (server
unreachable), stop immediately without retrying — not worth retrying a
genuinely-down server. On `OLLAMA_TIMEOUT` (server live but slow),
retry — a live-but-slow call is plausibly worth another attempt, per
`OllamaTimeout`'s own rationale (§2). Exhausting `MAX_ATTEMPTS` without
a `VALID` verification returns `None`.

```python
def generate_and_verify(
    topic: str, style_examples: list[str], content_excerpts: list[str],
) -> tuple[str, str] | None:
    """Returns (problem_text, solution_text) once verification confirms
    the solution is correct, or None if Ollama is unreachable or
    verification never passes within MAX_ATTEMPTS. Never raises."""
```

Any exception anywhere in this path is caught and logged as a warning,
returning `None` — same failure-isolation convention as `viz/`'s
`generate_via_llm` and `index_card.py`'s minimal-card fallback.

## 5. Intent detection in the tutor

A cheap regex/keyword check, `_looks_like_problem_request()`, added as
a private helper in `rag/rag_agent.py` (alongside its existing private
helpers `_diversify_by_file`/`_reformulate_query`) — not part of
`problem_gen`'s own public surface, since deciding *when* to generate a
problem is the tutor's routing decision, not this subproject's
capability:

```python
_PROBLEM_REQUEST_PATTERNS = [
    re.compile(r"\bpractice problem", re.IGNORECASE),
    re.compile(r"\bgive me a problem", re.IGNORECASE),
    re.compile(r"\bquiz me", re.IGNORECASE),
    re.compile(r"\banother (?:problem|exercise|question)\b", re.IGNORECASE),
    re.compile(r"\b(?:example|practice) (?:problem|question|exercise)", re.IGNORECASE),
    re.compile(r"\btest my (?:understanding|knowledge)", re.IGNORECASE),
]

def _looks_like_problem_request(question: str) -> bool:
    return any(p.search(question) for p in _PROBLEM_REQUEST_PATTERNS)
```

Checked against the raw `question` as typed (before follow-up
reformulation) — reformulation exists to make a retrieval query
standalone, which is orthogonal to classifying the student's literal
intent.

## 6. Integration with the tutor

`rag_agent.answer_question()` checks intent before doing its normal
retrieval-and-answer flow:

```python
def answer_question(
    roots: list[str], question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3, visualize: bool = False,
) -> AnswerResult:
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    if _looks_like_problem_request(question):
        from problem_gen.generator import generate_problem  # function-scoped import,
        # same circular-import-avoidance / dependency-isolation pattern as viz's own
        # integration (spec §6 there) -- keeps this package's Ollama dependency out of
        # every plain Q&A caller's import path.
        generated = generate_problem(retrieval_query, roots, client, course=course)
        if generated is not None:
            citations = [
                Citation(chunk_id=s.chunk_id, file_id=s.file_id, path=s.path, citation=s.citation, root=s.root)
                for s in generated.sources
            ]
            updated_history = history + [
                Turn(role="user", text=question), Turn(role="assistant", text=generated.problem_text),
            ]
            return AnswerResult(
                answer=generated.problem_text, citations=citations,
                history=updated_history, generated_problem=generated,
            )
        # generated is None (no style examples on this topic, or Ollama unavailable/never
        # verified) -- fall through to the normal Q&A path below on this same question,
        # same graceful-degradation principle as viz's visualization=None.

    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]
    answer = _generate_answer(question, history, passages, client)
    ...
```

`AnswerResult` gains one new field, `generated_problem: GeneratedProblem
| None = None` (same pattern as `visualization: VizResult | None`) —
`answer` is set to the problem text itself so the REPL's existing
`print(result.answer)` naturally shows the problem, while
`generated_problem.solution_text` is kept separate so a future caller
(or the REPL) can withhold the solution until the student asks for it,
rather than always printing question and answer together.

`main()`'s REPL prints the solution after the citation list when
present:

```python
if result.generated_problem:
    print(f"\n--- Solution ---\n{result.generated_problem.solution_text}\n")
```

## 7. Storage & IP policy

Nothing is written to disk. Per the user's explicit no-caching decision
(§1), every request generates fresh — there is no output file, no
`.problem_gen/` cache directory, and therefore no new IP-policy surface
to reason about at all (a strictly smaller footprint than `viz/`'s
`.viz/` output, which does persist HTML to disk).

## 8. Testing

`common/ollama_utils.py`'s `call_ollama` — the one network-touching
function in this design, tested with the HTTP call mocked (asserting
the right request is built; a non-2xx/connection error returns `None`;
a socket timeout returns `OLLAMA_TIMEOUT`) — same convention as this
project's other network-dependent code. `viz/llm_fallback.py`'s
existing tests for `_call_ollama` are updated to mock this shared call
site instead.

`problem_gen/llm_gen.py` — prompt-building and section extraction
(`## Problem`/`## Solution` parsing, verdict parsing) are pure logic,
tested directly with table-driven cases (well-formed response, missing
solution section, extra prose around the fenced sections, `VALID` vs
`INVALID: <reason>` verdicts). `generate_and_verify`'s orchestration is
tested with `call_ollama` mocked, covering: unreachable → `None`
immediately with no retry; timeout → retried; extraction failure →
retried with the error fed back; `INVALID` verdict → retried with the
reason fed back; success on a later attempt; `MAX_ATTEMPTS` exhausted →
`None`.

`problem_gen/generator.py` — tested with `search_passages` and
`generate_and_verify` both mocked: asserts `doc_type="problem_set"` is
requested for the style pool and `doc_type="textbook"` for the content
pool; an empty style pool returns `None` without calling generation at
all; sources come back tagged `role="style"`/`role="content"`
correctly.

`rag_agent.answer_question()` — `_looks_like_problem_request` gets a
table of trigger/non-trigger phrases (including near-misses that
shouldn't fire, mirroring `viz/`'s own keyword-matcher test approach).
With `generate_problem` mocked: a matching question routes to it and
returns its result as `AnswerResult`, a non-matching question never
imports/calls it, and a matching question where `generate_problem`
returns `None` falls through to the normal retrieval-and-answer path
unchanged.

Real end-to-end validation (does `qwen2.5-math:7b` actually produce a
correct, well-posed new problem for a handful of real math-camp
topics, and does the verification pass genuinely distinguish
correct from broken solutions) happens as a one-off manual check
during implementation, recorded in a status doc — this project's
established validation convention for model-dependent capabilities
(per `viz/`'s own testing section), not asserted in a test that would
need network access and real model inference in CI.
