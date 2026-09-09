# Problem Generation Sub-Agent

Generates a new practice problem plus a worked solution — styled after
the student's own problem sets and past exams, grounded in their own
textbooks. Generation itself uses Gemini by default (the same
`GEMINI_API_KEY` this project already requires for retrieval
embeddings — no separate setup), with local Ollama available as an
opt-in, fully free/private alternative
(`PROBLEMGEN_BACKEND=ollama`). 2026-09-06, defaulted to Gemini after a
real feasibility spike (see
`../docs/status/2026-09-05-problem-generation-status.md`): local
`qwen2-math:7b` never once produced an accepted result across two
independent real trials on a technique-constrained request, while
`gemini-3.1-flash-lite` passed 9/9 across three different topics in
the same testing, at negligible real cost (well under a cent per
problem) and dramatically faster (seconds per call, vs 10–50 minutes
per local attempt).

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
- `llm_gen.py` — sends the topic plus both retrieved pools to the
  configured backend (`PROBLEMGEN_BACKEND`, default `"gemini"`), extracts
  the generated problem and worked solution, then sends the pair back
  a second time to verify — as two independently-judged lines,
  `TECHNIQUE: YES/NO` and `CORRECTNESS: VALID/INVALID: <reason>`, not
  one combined verdict (a combined check let an easy correctness call
  paper over an unaddressed technique mismatch — see the status doc's
  2026-09-06 entry) — retrying with the specific failure fed back up to
  `MAX_ATTEMPTS = 5` before giving up.
  - **Gemini (default)**: model `gemini-3.1-flash-lite`, override with
    `PROBLEMGEN_GEMINI_MODEL`. Uses the same `GEMINI_API_KEY` as
    retrieval — no extra setup. Real spike testing: 9/9 trials passed
    across three topics, each completing in seconds.
  - **Ollama (opt-in via `PROBLEMGEN_BACKEND=ollama`)**: model
    `qwen2-math:7b`, override with `PROBLEMGEN_OLLAMA_MODEL`. Requires
    Ollama running locally (`ollama serve`) with the model pulled
    (`ollama pull qwen2-math:7b`). On CPU-only Ollama, expect single
    requests to take several minutes, up to ~30 minutes in the worst
    case (retries × two model calls each) — and per real testing,
    unreliable at actually honoring an explicit technique constraint
    (0/2 real trials succeeded on a technique-constrained request, even
    with a working technique-check and 5 attempts). Kept available for
    fully free/private generation, not as the recommended default.
  - Either backend degrades to returning `None` with a printed warning
    if unreachable — see `../docs/status/2026-09-05-problem-generation-status.md`
    for the full real-corpus validation history of both paths.

Nothing is written to disk — every request generates a fresh problem,
deliberately uncached (a repeated "give me another" should be a
genuinely different problem, not a cache hit).

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-03-problem-generation-design.md`.
