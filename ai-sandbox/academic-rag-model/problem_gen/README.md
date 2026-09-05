# Problem Generation Sub-Agent

Generates a new practice problem plus a worked solution — styled after
the student's own problem sets and past exams, grounded in their own
textbooks. A local Ollama model does the generation itself; no paid
API call for that part (retrieval still uses the existing Gemini
client for embeddings, same as every other retrieval call in this
project).

Run directly:

```powershell
.\.venv\Scripts\python.exe -c "from problem_gen.generator import generate_problem; from common.gemini_utils import get_gemini_client, load_dotenv_override; load_dotenv_override(); print(generate_problem('a problem on eigenvalues', ['../academic-hub'], get_gemini_client(), course='math-camp'))"
```

Or via the tutor's own automatic intent detection — see
[`../rag/README.md`](../rag/README.md): asking the tutor something that
reads like a request for practice ("give me a practice problem on...",
"quiz me on...") routes to this sub-agent automatically, no flag
needed.

## Key files

- `generator.py` — the one public entry point, `generate_problem()`.
  Retrieves the student's own real problems on the topic
  (`doc_type="problem_set"`, the style/difficulty anchor) and, if
  available, their own textbook content on the topic
  (`doc_type="textbook"`, the correctness anchor) via the
  [Source Indexer](../indexer/)'s `search_passages()`, resolving which
  course to search by matching the question text against the corpus's
  known course names when a course isn't given explicitly. Returns
  `None` (no hard failure) when there are no style examples on this
  topic/course, or when generation never produces a verified problem.
- `llm_gen.py` — sends the topic plus both retrieved pools to a local
  Ollama model (`qwen2.5-math:7b` by default, override with
  `PROBLEMGEN_OLLAMA_MODEL`), extracts the generated problem and worked
  solution, then sends the pair back to the model a second time to
  verify the solution is actually correct — retrying with the specific
  failure fed back (an extraction failure or an `INVALID` verdict) up
  to 3 attempts before giving up. Requires Ollama running locally
  (`ollama serve`) with the model pulled
  (`ollama pull qwen2.5-math:7b`) — degrades to returning `None` with a
  printed warning if it isn't.

Nothing is written to disk — every request generates a fresh problem,
deliberately uncached (a repeated "give me another" should be a
genuinely different problem, not a cache hit).

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-03-problem-generation-design.md`.
