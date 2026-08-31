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
