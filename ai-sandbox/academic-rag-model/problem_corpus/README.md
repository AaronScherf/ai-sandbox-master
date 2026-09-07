# Problem Corpus Extraction

Extracts a structured, persistent corpus of practice problems (topic
tag, problem text, solution text if present, course, provenance) from
math-camp's own problem sets, textbooks, and recitation slides. First
of six future-development ideas flagged in
[`../docs/2026-09-05-problem-generation-status.md`](../docs/2026-09-05-problem-generation-status.md)'s
"Future development ideas" section — the one everything else there
depends on.

**No `"verified"` solutions here.** Inspecting the actual corpus found
no answer-key tier at all: textbook exercises have no solutions in the
converted text, and problem sets are either solution-less or carry the
student's own worked attempt under an explicit `### Handwritten
Solutions:` heading — unverified, possibly wrong. Every extracted
record's `solution_provenance` is either `"student_attempt"` or
`null`, never `"verified"`.

**This subproject stops at producing the stored corpus.** Wiring it
into `problem_gen`'s generation prompt or any direct-serve matching is
a separate, later idea — see the status doc above.

Run directly:

```powershell
python -m problem_corpus.extractor --root ../academic-hub extract --course math-camp
python -m problem_corpus.extractor --root ../academic-hub extract --dry-run
```

Uses the same `GEMINI_API_KEY` this project already requires for
retrieval — no extra setup. One Gemini call (`gemini-3.1-flash-lite` by
default, override with `PROBLEM_CORPUS_GEMINI_MODEL`) per detected
problem span.

## Key files

- `extractor.py` — the one public entry point, `extract_problems()`,
  plus this subproject's own CLI (`main()`). Iterates indexed cards via
  [`../indexer/`](../indexer/)'s `index_card.load_shard()`/
  `list_courses()` — the same public interface
  `indexer/chunk_index.py`'s own `chunk()` already uses — filtered to
  problem-bearing folder categories (`problem_sets`, `textbooks`,
  `recitation_slides`). Content-hash-based incremental extraction: an
  unchanged file since its last run costs nothing (no re-read, no
  Gemini call), mirroring `chunk_index.py`'s own idempotency. Failure
  is isolated at both file granularity (one unreadable file doesn't
  stop the rest of a run) and per-problem granularity (one failed
  extraction within an otherwise-fine file doesn't drop its other
  problems).
- `boundaries.py` — pure, no-I/O detection of per-problem text spans.
  Regex patterns duplicated from `indexer/chunk_index.py`'s own
  proven problem-boundary detection, not imported (avoids reaching
  into another package's private internals for one piece of logic).
- `llm_extract.py` — one Gemini call per detected span, turning its raw
  text into a structured record (cleaned problem statement, solution
  verbatim if present, a short topic tag).
- `store.py` — read/write for `<root>/.problem_corpus/<course>.json`,
  mirroring `indexer/chunk_index.py`'s `.index/chunks/<course>.json`
  convention exactly.

Output goes to `<root>/.problem_corpus/<course>.json`, gitignored by
default (see the root `.gitignore`) — same IP posture as
`.index/chunks/`, since extracted problem text is pulled directly from
the corpus rather than being an LLM-authored summary of it.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`.
