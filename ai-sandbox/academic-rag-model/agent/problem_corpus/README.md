# Problem Corpus Extraction

Builds a persistent corpus of practice problems from indexed problem sets,
textbooks, and recitation slides. Each record contains a topic tag, problem
text, any student solution attempt, course, and source citation. Solutions are
never marked verified; `solution_provenance` is `student_attempt` or `null`.
The corpus is stored at `<root>/.problem_corpus/<course>.json`.

The default route uses subscription agent task cards. From
`ai-sandbox/academic-rag-model/`:

```powershell
python -m agent.problem_corpus.extractor --root ../academic-hub collect --course math-camp
python -m agent.problem_corpus.extractor --root ../academic-hub bootstrap <run-id>
python -m agent.problem_corpus.extractor --root ../academic-hub submit <run-id>
python -m agent.problem_corpus.extractor --root ../academic-hub status
```

`collect` makes one card per eligible, changed source file and prints its run
ID. It makes no API calls and writes no corpus records. The cards and worklist
live in `<root>/.agent_work/<run-id>/`, a private, ignored directory. Give the
agent the `bootstrap` contract, have it fill the YAML result blocks in the
cards, then run `submit`. Invalid answers bounce with specific reasons; correct
those blocks and submit again. Applied cards are never reapplied. `collect`
accepts `--file`, `--run-id`, and `--redo` as well as `--course`.

The API backup is **explicit opt-in** on a collected run:

```powershell
python -m agent.problem_corpus.extractor --root ../academic-hub api <run-id> --approve-cost 1.00
```

It uses `PAID_GEMINI_KEY` and the `core.agent_tasks` cost gate. Without
`--approve-cost`, estimates over $1 are refused before any card is sent. The
API result passes through the same validation and storage path as a filled
subscription card. The old `extract_problems()` Python function remains for
existing callers, but the CLI no longer offers an implicit API `extract`
command.

`boundaries.py` detects the same numbered spans as the original pipeline.
`stage.py` collects cards, checks that the source and index are still current,
validates one answer per span, and assembles records. `store.py` retains the
course-scoped file layout and replacement by source file ID. Unchanged files
are skipped unless `--redo` is given. Files without detected spans are
reported as skipped.

This package stops at producing stored records. Using them in `problem_gen`
is a separate project; see
[`docs/status/agent/problem_gen/2026-09-05-problem-generation-status.md`](../../docs/status/agent/problem_gen/2026-09-05-problem-generation-status.md).
