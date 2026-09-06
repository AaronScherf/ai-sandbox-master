# Problem Corpus Extraction Design

Brainstormed and approved with the user 2026-09-06. First of six future
development ideas flagged in
`docs/2026-09-05-problem-generation-status.md`'s "Future development
ideas" section — the one everything else there depends on. New peer of
`problem_gen/` and `viz/`, depending on `indexer/` for file discovery
(never the reverse, matching this project's established layering: `rag/`
depends on `indexer/`; `indexer/` depends on nothing downstream).

## 1. Problem & goals

`problem_gen/generator.py` currently grounds every new problem in raw
retrieval passages, re-fetched and re-used as loose style/content
examples on every single call. The student's own problem sets and
textbooks already contain real, well-posed problems — this spec builds a
tool that extracts them into a structured, persistent corpus (topic tag,
problem text, solution text if present, course, provenance), so later
work (few-shot prompting, direct-serve matching, solution backfilling,
corpus growth, a tiered local-first pipeline — the other five ideas in
that status doc) has real structured data to build against instead of
raw passage chunks.

**A real corpus finding that shapes this design (2026-09-06):**
inspecting the actual math-camp content going in, there is no
"verified answer key" tier anywhere in the corpus. Textbook exercises
(Axler, Rudin, etc.) have no solutions at all in the converted text.
Problem sets are either solution-less (`Practice Sheet.md`, old exams —
some with a blank "Answer space" placeholder) or carry the student's own
worked attempt under an explicit `### Handwritten Solutions:` heading —
unverified, possibly wrong. **This spec never claims or stores a
`"verified"` provenance tag** — only `"student_attempt"` or no solution
at all. Backfilling real, checked solutions via Gemini is a separate,
later idea (idea #3 in the status doc), not this one.

**Goals**
- Extract every distinct problem from math-camp's problem-bearing
  content (`problem_sets`, `textbooks`, `recitation_slides` folder
  categories) into a structured, persistent JSON record: a topic tag,
  the problem text, the solution text if one exists (else `null`), the
  course, and where it came from.
- Tag solution provenance honestly: `"student_attempt"` when a solution
  was present in the source, `null` when there wasn't one. Never
  `"verified"` — that tier doesn't exist in this corpus yet.
- Re-run safely and incrementally: an unchanged file since its last
  extraction run costs nothing (no re-read, no Gemini call), matching
  `indexer/chunk_index.py`'s own content-hash-based idempotency.
- Isolate failure at both file and per-problem granularity — one bad
  file, or one bad problem within an otherwise-fine file, never costs
  the rest of a run.

**Non-goals**
- Wiring the extracted corpus into `problem_gen`'s generation prompt or
  any direct-serve matching. That's idea #2 in the status doc, built
  later against real extracted data — this subproject stops at
  producing the stored corpus (explicitly decided with the user
  2026-09-06).
- Solution backfilling via Gemini for solution-less problems (idea #3),
  corpus growth from `problem_gen`'s own generated output (idea #4), the
  tiered local-first pipeline (idea #5), or similar-problems-as-templates
  (idea #6). All five remain flagged in the status doc, unbuilt.
- Courses other than math-camp. Every other course in this corpus is
  currently empty or near-empty (confirmed during `problem_gen`'s own
  Gemini feasibility spike, which dropped econometrics for exactly this
  reason) — nothing to extract yet. The tool takes a `--course` filter
  and iterates `list_courses()` like `chunk_index.chunk()` does, so
  extending to a newly-populated course later is a config change, not a
  redesign.
- A UI or CLI for browsing the extracted corpus. It's a JSON file on
  disk, inspectable directly; a browsing/serving surface is downstream
  of idea #2.

## 2. Architecture

New sibling package `problem_corpus/`, alongside `problem_gen/`/`viz/`:

```
academic-rag-model/
  problem_corpus/
    __init__.py
    README.md
    boundaries.py    # pure: detects per-problem text spans in a file's body
    llm_extract.py   # Gemini prompt-building, call, response parsing
    store.py         # read/write <root>/.problem_corpus/<course>.json
    extractor.py     # orchestration + CLI entry point
```

Depends on `indexer/` (`index_card.list_courses()`, `load_shard()`) for
file discovery only — the same cards `chunk_index.py` already iterates,
never that module's own private chunking internals. `indexer/` gains no
new dependency in the other direction; this stays consistent with
`indexer/`'s existing role as the base layer everything else builds on.

## 3. Boundary detection (`problem_corpus/boundaries.py`)

Pure functions, no I/O, no network — fully unit-testable with plain
strings. Regex patterns and the label-extraction logic are **duplicated**
from `indexer/chunk_index.py`'s `_detect_problem_boundaries` /
`_problem_label_at` / `_PROBLEM_BOUNDARY_PATTERNS`, not imported — same
precedent as `rag/report_builder.py`'s `_slugify`, which is explicitly
duplicated from `viz/viz_agent.py` rather than imported, to avoid this
lower-level, independently-testable module reaching into another
package's underscore-prefixed internals for one piece of logic:

```python
_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),
    re.compile(r"(?m)^\*\*Practice Problem \d+"),
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same threshold and reasoning as chunk_index.py's
# own constant -- a weak/sparse match count isn't trusted as real structure.
_PROBLEM_LABEL_RE = re.compile(r"^\**\s*(?:Practice Problem|Problem|Question)?\s*(\d+)", re.IGNORECASE)


@dataclass
class ProblemSpan:
    text: str
    problem_label: str  # e.g. "Problem 1" -- falls back to the bare word
    # "Problem" (no number) if _PROBLEM_LABEL_RE finds no digit near the
    # boundary match, same as chunk_index.py's own _problem_label_at.
    # Not assumed unique within a file (two spans can both fall back to
    # "Problem") -- extractor.py's id hash (§5) includes the span's index
    # within the file specifically to stay collision-safe when that
    # happens, rather than relying on problem_label alone.


def detect_spans(body: str) -> list[ProblemSpan]:
    """Returns one span per detected problem boundary (that problem's own
    text through the start of the next one, or end of document for the
    last one), or an empty list if fewer than _MIN_PROBLEM_MATCHES
    boundaries are found -- a file whose folder_category qualifies but
    whose content isn't actually numbered problems (e.g. a mini-lecture
    chapter intro) degrades to "nothing extracted here", not an error."""
```

Frontmatter stripping also duplicates `chunk_index.py`'s
`_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.DOTALL)` as a
small private helper in `extractor.py` (where file text is first read),
for the same reason.

## 4. Structured extraction via Gemini (`problem_corpus/llm_extract.py`)

One Gemini call per detected span — narrow and cheap (the current
math-camp corpus has, by rough boundary-count, on the order of dozens to
a couple hundred spans total; at Flash-Lite pricing this is negligible,
consistent with `problem_gen`'s own measured cost). Mirrors
`problem_gen/llm_gen.py`/`viz/llm_fallback.py`'s naming and
network-call-mocked-only testing convention — no new backend toggle here
(unlike those two, this always uses Gemini; there's no equivalent
reliability concern to weigh against a local model, since this only runs
as an occasional offline batch tool, not a live per-request path):

```python
PROBLEM_CORPUS_GEMINI_MODEL = os.environ.get("PROBLEM_CORPUS_GEMINI_MODEL", "gemini-3.1-flash-lite")

@dataclass
class ExtractedRecord:
    problem_text: str
    solution_text: str | None
    topic_tag: str
    # No solution_provenance field here -- the model reports what it
    # found (solution_text or None), and extractor.py derives
    # solution_provenance deterministically when assembling the final
    # stored record ("student_attempt" if solution_text is not None,
    # else None), rather than asking the model to name it. Keeps the
    # "never verified" guarantee (§1) independent of model output.


def _build_extraction_prompt(span_text: str) -> str:
    """Asks the model to read one span (a single detected problem,
    possibly followed by the student's own worked attempt) and return
    three labeled sections: the problem statement verbatim (cleaned of
    the boundary-detection artifacts, e.g. a leading '**Practice Problem
    3.**' label), the solution verbatim if a worked attempt is present
    in the span at all (explicit instruction: if there is no solution
    attempt, respond with the literal word NONE for that section --
    never invent one), and a short, specific topic tag (e.g.
    "compactness", "diagonalizability" -- not the coarse file-level
    front-matter tags already available, which this call has no need to
    duplicate)."""


def extract_record(span_text: str, client) -> ExtractedRecord | None:
    """One Gemini call via common.gemini_utils.call_with_retries -- returns
    None (not raising) if the call fails after retries or the response
    doesn't parse into the three expected sections. A None here is a
    per-span failure, isolated from the rest of the file (§6)."""
```

## 5. Storage (`problem_corpus/store.py`)

Mirrors `indexer/chunk_index.py`'s `.index/chunks/<course>.json`
convention exactly — same directory-nesting shape, same gitignore
posture (§7):

```python
def corpus_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".problem_corpus")

def corpus_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(corpus_dir(academic_hub_root), f"{course}.json")

def load_records(academic_hub_root: str, course: str) -> list[dict]:
    """Returns [] if the file doesn't exist yet -- same as chunk_index.py's
    load_chunks()."""

def save_file_records(academic_hub_root: str, course: str, file_id: str, records: list[dict]) -> None:
    """Atomically replaces every existing record for this file_id with
    `records` (upsert-by-file_id, not upsert-by-record-id) -- loads the
    course's full record list, drops anything already tagged with this
    file_id, appends the new set, writes the whole file back. One file's
    re-extraction never touches another file's already-stored records."""
```

**Record shape** (one JSON object per extracted problem):

```json
{
  "id": "<sha256(file_id + span_index + problem_label)[:16]>",
  "course": "math-camp",
  "topic_tag": "compactness",
  "problem_text": "...",
  "solution_text": "..." ,
  "solution_provenance": "student_attempt",
  "source": {
    "file_id": "...",
    "path": "academic_notes/math-camp/problem_sets/processed_outputs/Practice Sheet.md",
    "root": "/abs/path/to/academic-hub",
    "citation": "Practice Sheet.md, Problem 1",
    "folder_category": "problem_sets"
  },
  "content_hash": "<source file's card content_hash at extraction time>",
  "extracted_at": "2026-09-06T00:00:00+00:00"
}
```

`solution_text`/`solution_provenance` are both `null` together whenever
no solution was present in the source span — never independently null
(a record is never `solution_text: "..."` with `solution_provenance:
null`, or vice versa).

## 6. Orchestration & CLI (`problem_corpus/extractor.py`)

```python
_PROBLEM_BEARING_FOLDER_CATEGORIES = ("problem_sets", "textbooks", "recitation_slides")

def extract_problems(
    academic_hub_root: str, client, course: str | None = None,
    file: str | None = None, dry_run: bool = False,
) -> dict:
    """Iterates every non-orphaned, indexed card across the given course
    (or every course via list_courses() if course is None) whose
    folder_category is problem-bearing, matching chunk_index.chunk()'s
    own iteration shape and skip conditions (orphaned/needs_indexing
    cards skipped). Per file: skip if unchanged since its last
    extraction (content_hash match against this file_id's already-stored
    records); otherwise strip frontmatter, run boundaries.detect_spans(),
    and skip (not fail) if zero spans are found. Per span, call
    llm_extract.extract_record() -- a None result skips just that one
    record, logged as a WARNING, without aborting the rest of the file.
    Assembles the file's successful records and calls
    store.save_file_records() once per file (atomic per file, per §5).
    A file-level exception (unreadable file, bad frontmatter) is caught,
    logged as a WARNING with a rerun hint (same phrasing convention as
    chunk_index.chunk()'s own "rerun `...` later to retry"), and
    processing continues to the next file -- never aborts the whole run.
    dry_run reports what WOULD be (re-)extracted (by the same
    content_hash comparison) without calling Gemini or writing anything.
    Returns {"extracted": <files with new/changed records>, "unchanged":
    <files skipped via content_hash match>, "skipped_no_problems": <files
    with zero detected spans>, "failed": <file-level exceptions>,
    "problems_extracted": <total record count written this run>}."""
```

CLI (own `main()`, mirroring `viz_agent.py`/`rag_agent.py`'s
standalone-entry-point pattern rather than a new `index_search.py`
subcommand — extraction is a `problem_gen`-adjacent subproject that
*depends on* the indexer, not an indexer-internal operation):

```powershell
python -m problem_corpus.extractor --root ../academic-hub extract --course math-camp
python -m problem_corpus.extractor --root ../academic-hub extract --course math-camp --file "Practice Sheet.md"
python -m problem_corpus.extractor --root ../academic-hub extract --dry-run
```

## 7. Storage & IP policy

`<root>/.problem_corpus/` follows the exact same posture as
`.index/`/`.viz/`/`.reports/`: gitignored by default (added to the root
`.gitignore` alongside the existing entries), since it's derived data
regenerable from the source corpus, not something to commit.

## 8. Testing

`boundaries.py` — pure function, tested directly with plain strings:
multiple numbered problems detected correctly, fewer than
`_MIN_PROBLEM_MATCHES` boundaries returns `[]`, a span runs to the start
of the next boundary or end of document for the last one, label
extraction across the three label styles (`"1. "`, `"**Practice Problem
3"`, `"Problem 4"`, `"Question 2"`).

`llm_extract.py` — prompt-building tested directly (asserts the span
text and the "respond with NONE if no solution" instruction are both
present). The actual Gemini call mocked only (established convention):
successful three-section response parses correctly, a solution-less span
correctly produces `solution_text=None`/`solution_provenance=None`
together, a malformed response returns `None`, `call_with_retries`
raising returns `None`.

`store.py` — read/write tested for real against a temp directory
(`tempfile.TemporaryDirectory()`, matching `report_builder.py`'s own
test style): round-trips a record set, `save_file_records()` replaces
only the target `file_id`'s prior records and leaves every other
`file_id`'s records untouched, `load_records()` returns `[]` for a
course with no stored file yet.

`extractor.py` — orchestration tested with `llm_extract.extract_record`
mocked and cards/files under a temp corpus tree (mirroring
`chunk_index.py`'s own test style for `chunk()`): content-hash-based
skip, file-level failure isolation (one unreadable file doesn't stop the
rest), span-level failure isolation (one `None` from `extract_record`
doesn't drop the rest of that file's spans), zero-spans-detected skip
(not counted as failed), `dry_run` makes no Gemini calls and writes
nothing, `--course`/`--file` filtering.

Real end-to-end validation (does extraction actually produce sensible
topic tags and clean problem/solution text against the real math-camp
`problem_sets` files, including the solution-less and
`### Handwritten Solutions:`-bearing cases found during this design's
own corpus inspection) happens as a one-off manual run during
implementation, written up in a new status doc — this project's
established validation convention for model-dependent capabilities
(`problem_gen`'s and `viz`'s own status docs), not asserted in a test
that would need real network access and model inference in CI.
