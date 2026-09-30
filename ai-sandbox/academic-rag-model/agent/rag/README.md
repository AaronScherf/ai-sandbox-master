# RAG Tutoring Agent

A grounded question-answering agent that retrieves and cites real passages
from whatever's been converted and indexed — textbooks, notes, essays,
journal articles — usable directly as a multi-turn chat, or as a stateless
function other code can call.

Run as a module from the `academic-rag-model/` root:

```powershell
python -m rag.rag_agent --root ../academic-hub
```

`--root` is repeatable (`--root academic-hub --root research`), so one
conversation can be grounded in passages from more than one corpus at once —
see the [Source Indexer](../indexer/)'s multi-root search this builds on.

## Key file

- `rag_agent.py` — one core function, `answer_question()`, deliberately
  stateless per call: conversation history is an explicit input/output the
  caller owns, not internal session state. That's what lets it serve both
  usage modes (the interactive REPL in `main()`, and a plain callable) without
  two separate implementations. Inside a call: a follow-up question is first
  condensed into a standalone, retrievable query using recent history (skipped
  on the first turn), the reformulated question goes to the indexer's
  passage-level search, a diversification step caps how many top-ranked
  passages can come from a single file (so a comparative question actually
  pulls from multiple sources), and generation is prompted to answer using
  *only* the retrieved excerpts — citing each one inline, and saying so
  plainly when the excerpts don't cover the question.

Retrieval itself isn't new machinery — it's the [Source Indexer](../indexer/)'s
`search_passages()`, reused as-is. Depends on `indexer/`; see the root
[`README.md`](../README.md) for the full dependency graph.

## `--visualize`

```powershell
python -m rag.rag_agent --root ../academic-hub --visualize
```

Opt-in flag (`answer_question(..., visualize=True)` underneath) that also
generates an interactive Plotly HTML visualization for each question's
concept via the [Visualization Sub-Agent](../viz/) — off by default, so
nothing about a plain question-answering call changes unless you ask for it.
It tries a small keyword-matched template library first (near-instant, no
paid API call); when no template matches, it falls back to an LLM, Gemini
(`gemini-3.1-flash-lite`) by default as of 2026-09-06 — the same
`GEMINI_API_KEY` this project already requires for retrieval, no extra
setup. Local Ollama generation is still available as an opt-in
(`VIZ_BACKEND=ollama`), which adds up to ~1 minute of local generation time
on CPU (~68s observed for a real, unmatched concept) and requires Ollama
running locally with a model pulled — see the
[Visualization Sub-Agent's own README](../viz/README.md) for setup and the
full Gemini-vs-Ollama comparison
([`../docs/status/2026-09-02-visualization-agent-status.md`](../docs/status/2026-09-02-visualization-agent-status.md)).
Either way, a missing visualization is a normal outcome (e.g. the backend
unreachable, or it produced a broken script) — `result.visualization` is
just `None`, never a hard failure of the question-answering call itself.

## Practice problems

Unlike `--visualize`, this is **automatic — no flag required**. A cheap
regex intent check runs against every question's raw text (phrases like
"give me a practice problem on...", "quiz me on...", "another exercise");
a match routes the question to the [Problem Generation Sub-Agent](../problem_gen/)
instead of the normal retrieval-and-answer flow, generating a new practice
problem plus a worked solution grounded in the student's own problem sets
and textbooks rather than answering the question as asked.

Generation defaults to Gemini (`gemini-3.1-flash-lite`) — the same
`GEMINI_API_KEY` this project already requires for retrieval, no extra
setup, and fast: real spike testing (9 trials across 3 topics, all
passed) completed in seconds per call. 2026-09-06, defaulted to Gemini
after that spike found it dramatically more reliable at honoring an
explicit technique constraint than the original local-only design —
see
[`../docs/status/2026-09-05-problem-generation-status.md`](../docs/status/2026-09-05-problem-generation-status.md)
for the full real-corpus comparison.

Local Ollama generation is still available as an opt-in
(`PROBLEMGEN_BACKEND=ollama` — set it up the same way as
`--visualize`'s Ollama dependency, but pull the different model this
sub-agent needs: `ollama pull qwen2-math:7b`) for fully free/private
generation. Expect this path to be much slower than `--visualize`'s
~1 minute: on CPU-only Ollama, a single request took **9–23 minutes**
across real end-to-end trials (up to `MAX_ATTEMPTS=5` retries, each
attempt making up to 2 model calls — one to generate, one to verify),
worst case up to **~50 minutes** — and per that same real testing,
it never once succeeded on a technique-constrained request even with a
working technique-check, so it's kept available but not recommended as
a default.

Generation is never a hard dependency: when there are no style examples
for the resolved topic/course, the configured backend is unreachable,
or verification never passes within the retry budget, the sub-agent
returns `None` and the tutor falls back to answering the same question
normally — a normal, expected outcome, not an error, exactly like
`--visualize`'s own graceful degradation above.

**Visualizing a generated problem:** since problem generation has no flag
of its own to combine with `--visualize`, a visualization here is
triggered by an explicit in-text request instead — phrases like
"visualize this", "make a graph", "show me a diagram" — checked the same
way the problem-request intent itself is (a cheap regex, not an LLM
call). The existing `visualize=True` flag still works too (e.g. a
`--visualize` CLI caller), so either the flag or the phrase turns it on.
The visualization is grounded in the newly generated problem and
solution text (not the corpus passages, since a fresh problem has no
retrieved passages of its own) via the same
[Visualization Sub-Agent](../viz/) used on the normal Q&A path, with the
same graceful degradation — a missing visualization is `None`, never a
hard failure of the generated problem itself.

**Combined reports** (`report=True`) also work on a generated problem,
same as the normal Q&A path — the report additionally includes the
worked solution as its own section, not just the problem statement.
This was a real integration gap until 2026-09-06: the problem-generation
branch didn't call the report builder at all regardless of `report=True`,
the same kind of gap `--visualize` had until its own fix above.
