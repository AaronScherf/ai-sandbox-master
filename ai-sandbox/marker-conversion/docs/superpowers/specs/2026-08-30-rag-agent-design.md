# RAG Tutoring Agent Design

Brainstormed and approved with the user 2026-08-29/30, as the direct
consumer of both prior specs: the source indexer
(`docs/superpowers/specs/2026-08-27-source-indexer-design.md`) and
passage-level embeddings
(`docs/superpowers/specs/2026-08-29-passage-embeddings-design.md`).
Original intent captured in
`ai-sandbox/personal-website/AaronScherf.github.io/content/projects/rag_analysis/index.md`
(private/local file, not itself part of this spec).

## 1. Problem & goals

An agent that answers questions grounded in the academic-hub corpus,
usable two ways: as an interactive tutor (multi-turn conversation), and
as a callable utility other code can invoke (e.g. a study-plan agent
handing it a syllabus + textbook list and getting back a grounded,
source-backed answer to build on). Both modes share one core function;
the difference is who owns the conversation history, not two separate
implementations (§3).

**Explicitly deferred, decided with the user 2026-08-29/30:**

- **Public deployment.** The corpus is copyrighted (personal PDFs, not
  licensed for redistribution); real fair-use exposure exists for a
  *public* tool that can surface substantial verbatim passages on
  demand, distinct from the personal/private use already established
  throughout this whole project (see the git-history incident below).
  This spec builds a private, local tool only. Going public is a
  separate decision requiring real legal input, not an architecture
  choice made here.
- **Local/open-weight generation (Ollama).** Investigated live: without
  a GPU, CPU-only inference for a model capable enough to tutor well is
  slow enough to hurt the actual interactive experience, and doesn't
  meaningfully save money against Gemini's actual per-query cost at
  personal-study volume (§2). Generation stays Gemini end-to-end,
  matching every other model choice in this project.
- **A vector database / orchestration framework (Chroma, FAISS,
  LangChain, LlamaIndex).** The original project-page vision named
  these, written before any of the actual indexer/chunking work
  existed. What got built instead (flat JSON, brute-force NumPy cosine
  similarity, no framework) is what this agent's retrieval reuses
  directly -- introducing a second retrieval mechanism alongside the
  one already built and validated would be net-new complexity for no
  demonstrated need.

**A real incident worth recording here, since it directly shaped "private
only" above being non-negotiable for now, not just a preference:** while
building the passage-chunking work this spec depends on, a real commit
briefly pushed passage chunks (verbatim excerpted copyrighted text plus
per-passage embeddings of that exact text) to this repo while it was
public on GitHub. Caught, untracked, and purged from git history the
same session (`git filter-repo` + force-push, scoped to the one
affected branch) -- but it's a concrete demonstration of how easily
"public" and "contains copyrighted material" collide by accident, not
just a hypothetical risk.

## 2. Cost, confirmed live (2026-08-29/30)

`gemini-embedding-001` (retrieval, already in use): $0.15/1M input
tokens. `gemini-3.6-flash` (originally chosen for generation): $0.75/1M
input, $3.75/1M output through end of 2026 (rising to $1.50/$7.50 in
2027, per Google's own pricing page). A typical tutoring exchange
(~3,000 input tokens of retrieved context + question, ~800 output
tokens) costs roughly **$0.005** -- even heavy daily personal use (50-100
exchanges/day) lands around $10-16/month. Not a reason to compromise on
model quality or to reach for local inference.

**Revised 2026-08-30 against real output (§5):** `gemini-3.6-flash` was
chosen here on an untested heuristic ("tutoring is reasoning-heavy,
step up from the cheap tier") -- a real side-by-side comparison (same
question, same retrieved passages) showed `gemini-3.1-flash-lite`
producing comparably correct, well-cited answers. `TUTOR_MODEL` is now
`gemini-3.1-flash-lite` ($0.30/1M input, $2.50/1M output) -- roughly
$0.003/exchange, cheaper still, with no observed quality loss. The
cost conclusion above (trivial either way) is unchanged; the model
choice itself was corrected.

## 3. Architecture

New module `rag_agent.py`, alongside `index_card.py`/`index_search.py`/
`retag.py`/`chunk_index.py`:

```python
import argparse
import os
from dataclasses import dataclass

from gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from index_card import GENERATION_MODEL
from index_search import PassageResult, search_passages
```

One core function, stateless per call -- conversation history is an
explicit input/output, not owned internally:

```python
@dataclass
class Turn:
    role: str  # "user" | "assistant"
    text: str


@dataclass
class Citation:
    chunk_id: str
    file_id: str
    path: str
    citation: str  # _render_citation()'s own rendering, e.g. "§3.7, p. 44"


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]  # includes this exchange, ready to pass into the next call


def answer_question(
    academic_hub_root: str, question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3,
) -> AnswerResult:
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    passages = search_passages(academic_hub_root, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
    citations = [
        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation)
        for p in passages
    ]
    updated_history = history + [Turn(role="user", text=question), Turn(role="assistant", text=answer)]
    return AnswerResult(answer=answer, citations=citations, history=updated_history)
```

**Why stateless-with-explicit-history, not an internal session object:**
the two usage modes want different ownership. A study-plan agent calling
this as a utility shouldn't need to manage a session file or clean up
state after itself -- it calls once, gets an `AnswerResult`, done (or
optionally threads `.history` into a follow-up call if it wants
continuity). A chat interface *does* want continuity across many turns
-- it just holds onto `.history` itself and passes it back in each call.
Neither mode needs the core function to own persistence; both are served
by the same function with different calling patterns. No database, no
session files, no new state-management surface in the core logic.

## 4. Retrieval

```python
_REFORMULATE_PROMPT_TEMPLATE = """Given this recent conversation and a follow-up question, rewrite \
the follow-up as a standalone question that makes sense with no other context -- preserve its \
intent exactly, just make it self-contained. Respond with ONLY the rewritten question, nothing else.

Recent conversation:
{history_block}

Follow-up question: {question}

Standalone question:"""


def _reformulate_query(question: str, history: list[Turn], client) -> str:
    """Condenses a follow-up ("explain that differently") into a
    standalone, retrievable query using recent conversation history --
    only called when history is non-empty (the first turn's question is
    already standalone, nothing to condense from). Uses
    index_card.GENERATION_MODEL (gemini-3.1-flash-lite) -- this is a
    mechanical rewrite, not a reasoning task, so it reuses this
    project's existing cheap-tier model rather than the more expensive
    tutoring-generation model (§5)."""
    recent = history[-6:]  # last 3 exchanges -- enough context to resolve most follow-ups
    history_block = "\n".join(f"{t.role}: {t.text}" for t in recent)
    prompt = _REFORMULATE_PROMPT_TEMPLATE.format(history_block=history_block, question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=GENERATION_MODEL, contents=prompt,
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    ))
    return (response.text or question).strip()


def _diversify_by_file(results: list[PassageResult], max_per_file: int) -> list[PassageResult]:
    """Caps how many of the top-ranked passages can come from the same
    file, preserving relevance order otherwise. Confirmed live this is
    a real gap, not a hypothetical one: search_passages() already
    ranks across a file shortlist, but nothing stops one dominant
    textbook from crowding out every other source -- a comparative
    question ("how do two textbooks treat this") needs material from
    multiple sources to actually be answerable as a comparison."""
    per_file_count: dict[str, int] = {}
    kept = []
    for r in results:
        if per_file_count.get(r.file_id, 0) >= max_per_file:
            continue
        per_file_count[r.file_id] = per_file_count.get(r.file_id, 0) + 1
        kept.append(r)
    return kept
```

Retrieval flow inside `answer_question()`: reformulate (if `history` is
non-empty) → `search_passages()` (already built, spec §6 of the
passage-embeddings design, unmodified) → `_diversify_by_file()` on the
results → these become the grounding context for generation.

`search_passages()` itself is **not modified** -- it stays a
general-purpose, pure-relevance search (used as-is by `query
--passages` too, where artificial diversification isn't necessarily
wanted). Diversification is this agent's own concern, applied as a
post-processing step on top of the existing function's results, not a
new parameter threaded through it.

## 5. Generation

```python
TUTOR_MODEL = "gemini-3.1-flash-lite"  # revised 2026-08-30 (§2): originally
# gemini-3.6-flash, on the untested assumption that tutoring's reasoning
# demands needed a step up from index_card.GENERATION_MODEL (this
# project's cheap/mechanical tier). A real side-by-side comparison --
# same question, same retrieved passages -- showed no meaningful
# quality or coverage difference. Switched back to the cheaper tier;
# the model this constant now equals is literally
# index_card.GENERATION_MODEL's value, kept as its own named constant
# here rather than importing that one directly, since the two are
# conceptually distinct choices that happen to currently agree, not
# the same setting reused.

_ANSWER_PROMPT_TEMPLATE = """You are tutoring a student using ONLY the excerpts below, drawn from \
their own course materials. Answer their question clearly and thoroughly, the way a good TA would \
explain it -- but do not introduce any claim, fact, or worked step that isn't supported by the \
excerpts. If the excerpts don't actually contain enough to answer the question, say so plainly \
rather than filling the gap from general knowledge.

When you use something from an excerpt, cite it inline using the citation label given with it \
(e.g. "(§3.7, p. 44)"), so the student can find it in their own materials.
{history_block}
Excerpts:
{excerpts_block}

Question: {question}

Answer:"""


def _generate_answer(question: str, history: list[Turn], passages: list[PassageResult], client) -> str:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    history_block = ""
    if history:
        recent = "\n".join(f"{t.role}: {t.text}" for t in history[-6:])
        history_block = f"\nRecent conversation, for continuity:\n{recent}\n"
    prompt = _ANSWER_PROMPT_TEMPLATE.format(
        history_block=history_block, excerpts_block=excerpts_block, question=question,
    )
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()
```

`excerpts_block` is built directly from the (diversified) retrieved
`PassageResult`s -- each one's `.text` plus its `.citation` string,
which is exactly what `index_search.py`'s existing `_render_citation()`
already produces (`"§3.7 Optimization, p. 44"` /
`"Problem 4, p. 12"` / `"p. 8"`), reused as-is, not reimplemented.
Temperature 0.2, not 0 -- unlike this project's mechanical/extraction
calls (all temperature 0, deterministic), a tutoring explanation
benefits from slight variation in phrasing across similar questions
rather than the exact same canned wording every time; still low enough
to stay close to the grounded excerpts, not open-ended creative
generation.

**Citations returned are every retrieved passage actually placed in the
prompt, not a parse of which ones the model's inline citations
reference.** Simpler and more robust than trying to regex-match citation
labels back out of free-form generated text -- every passage the model
*could* have drawn from is available to the caller as structured
grounding, which is what a calling agent building on the answer
actually needs, rather than a best-effort guess at which ones it
specifically used.

## 6. The two usage modes

**Callable utility** (already fully served by `answer_question()`
itself): `from rag_agent import answer_question` — any Python code in
this project (or anything with access to this environment) calls it
directly. No server, no new protocol. If cross-process/cross-agent
calling is ever genuinely needed (e.g. exposing this to a fully
separate agent framework), that's a thin wrapper (MCP server, HTTP
endpoint) around this same function, explicitly deferred (§8) until a
real caller needing it exists.

**Interactive chat**: `rag_agent.py`'s own `main()` — a REPL loop, not a
subcommand on `index_search.py`'s existing CLI, since a persistent
multi-turn loop is a different *kind* of interface from every other
single-shot subcommand there (`query`, `rebuild`, `retag`, `chunk` all
run once and exit). Owns the `history: list[Turn]` across iterations,
prints the answer plus a citation list after each turn.

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive tutor grounded in the academic-hub corpus.")
    parser.add_argument("--academic-hub", default=os.path.join(os.path.dirname(__file__), "..", "academic-hub"))
    parser.add_argument("--course", default=None)
    args = parser.parse_args()

    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    history: list[Turn] = []
    print("Ask a question (Ctrl+C to exit).")
    while True:
        question = input("> ").strip()
        if not question:
            continue
        result = answer_question(args.academic_hub, question, client, history=history, course=args.course)
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - {c.path} ({c.citation})")
        print()
        history = result.history
```

One additional one-shot entry point, for scripting/quick single
questions without the REPL: `index_search.py ask "question" [--course
X]` — thin CLI wiring calling `answer_question()` with `history=None`,
matching the existing subcommand pattern exactly (mirrors how `chunk`
and `retag` are wired).

## 7. Testing

`_reformulate_query()` and `_diversify_by_file()` are unit-testable the
same way everything else in this project is -- the former with a mocked
client (assert it's skipped when `history` is empty, assert it's called
with recent history when not), the latter as pure logic (a list of
`PassageResult`s in, capped-and-reordered list out, no mocking needed).
`answer_question()` itself tested end-to-end with a mocked client
covering: first-turn (no reformulation call), follow-up turn
(reformulation called, uses returned query for retrieval), citations
list matches exactly the diversified retrieved passages, `history` in
the result includes the new exchange appended to whatever was passed
in. `main()`'s REPL loop is not unit-tested (same convention as every
other `main()` in this project -- untested, thin CLI glue over tested
functions).

## 8. Explicitly not built here

- **Public deployment** (§1) -- a separate decision requiring real
  legal input on fair use, not an engineering choice.
- **Local/open-weight generation via Ollama** (§1) -- investigated and
  rejected for now on both cost and usability grounds without a GPU;
  revisit if hardware changes.
- **A vector database or orchestration framework** (§1) -- the existing
  flat-JSON + NumPy retrieval is reused as-is.
- **MCP server / HTTP API wrapper** (§6) -- `answer_question()` is
  already callable directly by anything in this environment; a network-
  facing wrapper is only worth building once a real caller needs
  cross-process access, not speculatively.
- **Persisted conversation history** (§3) -- the REPL's `history` lives
  only for that process's lifetime; nothing writes it to disk. A
  resumable chat session is a real feature that could be added on top
  of the same `history: list[Turn]` shape later, not designed for here.
- **Streaming responses.** `answer_question()` returns a complete
  answer, not a token stream -- consistent with every other Gemini call
  in this project (all synchronous, non-streaming), and not something
  the "callable utility" usage mode needs.
