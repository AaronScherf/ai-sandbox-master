# Question Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A manual command that answers each `[Question]` tag in the Excalidraw notes (grounded in the course corpus when possible, labeled when not), stores the answers in a per-note sidecar, and marks each tag in the `.rag.md` so readers and agents see the question is resolved and where.

**Architecture:** Pure logic (tag discovery, ids, sidecar I/O, marker application) lives in `core/indexer/questions.py` so both the transcriber hook and the resolver import it without a layering cycle. A new shared module `core/env/excalidraw_text.py` holds the one definition of the `[Question]` tag and the `[Slide]`/`[Handwritten]` segment splitter, replacing the copies in `transcribe_excalidraw.py` and `related.py`. `agent/rag/resolve_questions.py` reuses the `/hint` grounding pattern (key terms, `retrieve_passages`, grounded check) and owns the CLI. The sidecar is indexed through `rebuild` under a stable derived id.

**Tech Stack:** Python 3.13, pytest, existing `core.env.frontmatter`, `core.indexer.index_card`/`index_search`, `agent.rag.rag_agent` helpers, Gemini via the existing client.

**Spec:** `docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md`

**Working directory for every command:** the worktree's `ai-sandbox/academic-rag-model/` (branch `claude/question-resolver`, worktree `.worktrees/claude-question-resolver`). Use the main checkout's venv: `/c/Users/theaa/ai-sandbox-master/ai-sandbox/academic-rag-model/.venv/Scripts/python`, written as `$PY`. Stage explicit paths only; never `git add -A`. Files in this repo may have CRLF line endings: if the Edit tool reports no match on a block you can see, do the same replacement with a short Python script that opens with `newline=""`.

## Global Constraints

- Sidecar name: `<base>.excalidraw.questions.md`, in the same folder as the raw transcript `<base>.excalidraw.md` and the `.rag.md` (`<base>.excalidraw.rag.md`). All three paths derive from the raw transcript's path.
- Question id: `q<ordinal>-<8 hex>`; ordinal is 1-based among the **raw transcript's** tags; the hex is the first 8 characters of SHA-256 of the lowercased, whitespace-collapsed question text. Ids are never derived from the `.rag.md`.
- Question text: text after the tag up to and including the next `?`; if the rest of the line has no `?`, the rest of the line; if that is blank, the next non-blank line; whitespace-collapsed; capped at 200 characters.
- Marker formats (ASCII only): open `[Question]`; grounded `[Question: answered -> <sidecar basename>#<qid>]`; ungrounded `[Question: answered (ungrounded) -> <sidecar basename>#<qid>]`. Only the tag token is rewritten; the question text stays.
- Tag regex everywhere: `\[Question(?::[^\]]*)?\]` (matches open and resolved tags).
- `apply_markers` makes no model call and writes the `.rag.md` only when its text changes.
- Sidecar writes are atomic (temp file in the same folder, then `os.replace`; temp file removed on failure).
- Default resolver model `gemini-3.6-flash`; temperature 0.2 for answers; API key via `get_gemini_client("PAID_GEMINI_KEY")`.
- Grounded means: at least one retrieved passage survives own-note exclusion **and** (no key terms were extracted **or** some passage mentions a key term).
- A failed question writes nothing for that question and is retried on the next run.
- Notes whose index card has `subset_of` are skipped by the CLI.
- `core/indexer` and `core/env` are shared: the full suite (1939+ tests) must pass after the last task.
- Commits end with: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Never print or commit API keys. The real-data task runs `--dry-run` first and runs the paid resolver only with the user's go-ahead.

## Review Focus

- Mid-sentence tag (e.g. "...the distance [Question] what is furthest you can get from A while in B? and d_B as...") must yield the question text up to the first `?`, and the marker must replace only the tag token. (Tasks 2 and 4.)
- A regenerated `.rag.md` that rewords a question or changes the tag count must pair by position when counts match and by text similarity when they don't; unmatched tags stay open and their sidecar entries are flagged `stale`. (Task 4.)
- A question must never be "grounded" in its own note's `.rag.md` or sidecar. (Task 5.)
- Rewriting the sidecar must update, never duplicate, its index card (stable id). (Task 8.)
- One question failing (error or empty answer) must not abort the others or leave a partial entry, and a rerun must retry only the failed one. (Task 6.)
- An answer containing `## ` heading lines must not split or corrupt sidecar parsing. (Task 3.)

## File Structure

- Create `core/env/excalidraw_text.py` — one definition of the tag constants/regex and `split_labeled_segments`.
- Create `core/indexer/questions.py` — tags, ids, sidecar model and I/O, marker application. No network.
- Create `agent/rag/resolve_questions.py` — context extraction, prompts, per-question resolution, note orchestration, discovery, CLI.
- Modify `pipelines/transcribe_notes/transcribe_excalidraw.py` — import shared definitions; call `apply_markers` in `write_outputs`.
- Modify `core/indexer/related.py` — import shared regexes.
- Modify `core/indexer/index_card.py` — `EXCALIDRAW_QUESTION_DOC_TYPES`.
- Modify `core/indexer/index_search.py` — index the sidecar in `rebuild`.
- Create tests: `tests/core/env/test_excalidraw_text.py`, `tests/core/indexer/test_questions.py`, `tests/agent/rag/test_resolve_questions.py`; modify `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`, `tests/core/indexer/test_index_search.py`, `tests/core/indexer/test_chunk_index.py`.
- Modify `agent/rag/README.md`, `core/indexer/README.md`, and the spec (two clarifications).

---

### Task 1: Shared tag and segment definitions (resolves the two open plan items)

**Files:**
- Create: `core/env/excalidraw_text.py`
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (lines ~11-30 imports, ~102, ~265-293)
- Modify: `core/indexer/related.py` (lines ~20-31)
- Test: `tests/core/env/test_excalidraw_text.py`

**Interfaces:**
- Produces (used by every later task):
  - `QUESTION_TAG: str = "[Question]"`
  - `QUESTION_TAG_RE: re.Pattern` matching `\[Question(?::[^\]]*)?\]`
  - `SEGMENT_LABEL_RE`, `CHUNK_MARKER_RE: re.Pattern`
  - `split_labeled_segments(raw_markdown: str) -> list[tuple[str, str]]` (label is `"Slide"` or `"Handwritten"`; chunk markers dropped; leading unlabeled text is `"Handwritten"`).

- [ ] **Step 1: Write the failing tests**

Create `tests/core/env/test_excalidraw_text.py`:

```python
from core.env import excalidraw_text as et
from core.env.excalidraw_text import QUESTION_TAG, QUESTION_TAG_RE, split_labeled_segments


def test_question_tag_constant():
    assert QUESTION_TAG == "[Question]"


def test_tag_regex_matches_open_and_resolved_markers_only():
    text = (
        "a [Question] b [Question: answered -> f.md#q1-ab] c "
        "[Question: answered (ungrounded) -> f.md#q2-cd] d [Questions] e [Question2]"
    )
    assert [m.group(0) for m in QUESTION_TAG_RE.finditer(text)] == [
        "[Question]",
        "[Question: answered -> f.md#q1-ab]",
        "[Question: answered (ungrounded) -> f.md#q2-cd]",
    ]


def test_split_labeled_segments_orders_labels_and_strips_chunk_markers():
    raw = (
        "<!-- chunk 1 -->\n\n**[Handwritten]**\nnote a\n\n**[Slide]**\n* Slide one\n\n"
        "<!-- chunk 2 -->\n\n**[Handwritten]**\nnote b\n"
    )
    segments = split_labeled_segments(raw)
    assert [label for label, _ in segments] == ["Handwritten", "Slide", "Handwritten"]
    assert all("<!-- chunk" not in text for _, text in segments)
    assert segments[1][1] == "* Slide one"


def test_split_labeled_segments_treats_leading_unlabeled_text_as_handwritten():
    assert split_labeled_segments("stray words\n\n**[Slide]**\n* s\n")[0] == ("Handwritten", "stray words")


def test_every_module_uses_the_one_shared_definition():
    from core.indexer import related
    from pipelines.transcribe_notes import transcribe_excalidraw as te

    assert te.split_labeled_segments is split_labeled_segments
    assert te._SEGMENT_LABEL_RE is et.SEGMENT_LABEL_RE
    assert te._CHUNK_MARKER_RE is et.CHUNK_MARKER_RE
    assert te._QUESTION_TAG == QUESTION_TAG
    assert related._LABEL_RE is et.SEGMENT_LABEL_RE
    assert related._CHUNK_MARKER_RE is et.CHUNK_MARKER_RE
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/env/test_excalidraw_text.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'core.env.excalidraw_text'`.

- [ ] **Step 3: Create the shared module**

Create `core/env/excalidraw_text.py`:

```python
"""
excalidraw_text.py
The one definition of the text conventions the Excalidraw notes pipeline,
the subset linker, and the question resolver all parse: the `[Question]`
tag (open, or already rewritten into a resolved marker) and the
`**[Slide]**` / `**[Handwritten]**` block labels of a slide-aware raw
transcript. No network, no filesystem.
"""
from __future__ import annotations

import re

QUESTION_TAG = "[Question]"
# Matches an open tag and a resolved marker such as
# "[Question: answered -> <sidecar>#<qid>]" (see core.indexer.questions).
QUESTION_TAG_RE = re.compile(r"\[Question(?::[^\]]*)?\]")

SEGMENT_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)


def split_labeled_segments(raw_markdown: str) -> list[tuple[str, str]]:
    """Splits a slide-aware raw transcript into ordered (label, text) blocks,
    label being 'Slide' or 'Handwritten'. Chunk markers are dropped (a block
    can straddle a chunk boundary; they are transcription bookkeeping, not
    content). Text before the first label is treated as handwriting -- the
    safe default, since handwriting is the part that gets rewritten and the
    fallback on any failure is to keep it verbatim."""
    text = CHUNK_MARKER_RE.sub("", raw_markdown)
    matches = list(SEGMENT_LABEL_RE.finditer(text))
    pieces: list[tuple[str, str]] = []
    first_start = matches[0].start() if matches else len(text)
    if text[:first_start].strip():
        pieces.append(("Handwritten", text[:first_start].strip()))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            pieces.append((m.group(1), body))
    return pieces
```

- [ ] **Step 4: Rewire `transcribe_excalidraw.py`**

(a) In the import block, after `from core.env.academic_hub_paths import resolve_output_dir, to_resources_root`, add:

```python
from core.env.excalidraw_text import (
    CHUNK_MARKER_RE as _CHUNK_MARKER_RE,
    QUESTION_TAG as _QUESTION_TAG,
    SEGMENT_LABEL_RE as _SEGMENT_LABEL_RE,
    split_labeled_segments,
)
```

(b) Delete the line `_QUESTION_TAG = "[Question]"` (and the blank line after it).

(c) Delete these definitions, keeping the line `_SLIDE_CONTEXT_CHARS = 3000  # per neighboring slide, keeps each handwriting call small` in place:

```python
_SEGMENT_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
_CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)
```

and the whole `def split_labeled_segments(raw_markdown: str) -> list[tuple[str, str]]:` function (from `def` through `return pieces`). The aliased imports keep every other reference in the file working unchanged.

- [ ] **Step 5: Rewire `related.py`**

Replace these two lines:

```python
_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
_CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)
```

with nothing, and add to its import block (after `from core.env.frontmatter import parse_frontmatter`):

```python
from core.env.excalidraw_text import CHUNK_MARKER_RE as _CHUNK_MARKER_RE, SEGMENT_LABEL_RE as _LABEL_RE
```

- [ ] **Step 6: Run to verify pass, then the affected suites**

Run: `$PY -m pytest tests/core/env tests/core/indexer/test_related.py tests/pipelines/transcribe_notes -q`
Expected: all pass (existing slide/related tests unchanged, new tests green).

- [ ] **Step 7: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/env/excalidraw_text.py ai-sandbox/academic-rag-model/tests/core/env/test_excalidraw_text.py ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_excalidraw.py ai-sandbox/academic-rag-model/core/indexer/related.py
git commit -m "refactor: one shared definition of the [Question] tag and slide segment splitter"
```

---

### Task 2: Tag discovery and question ids

**Files:**
- Create: `core/indexer/questions.py`
- Test: `tests/core/indexer/test_questions.py`

**Interfaces:**
- Consumes (Task 1): `QUESTION_TAG_RE`.
- Produces (used by Tasks 3-8):
  - `@dataclass(frozen=True) Tag(ordinal: int, qid: str, text: str, start: int, end: int)` (`start`/`end` span the whole tag token in the scanned text)
  - `normalize(text: str) -> str`
  - `question_id(ordinal: int, text: str) -> str`
  - `question_text_after(text: str, tag_end: int) -> str`
  - `find_tags(markdown: str) -> list[Tag]`
  - `raw_tags(raw_text: str) -> list[Tag]` (frontmatter stripped first)

- [ ] **Step 1: Write the failing tests**

Create `tests/core/indexer/test_questions.py`:

```python
from core.indexer.questions import find_tags, normalize, question_id, raw_tags


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Why   NOT\nreflexivity? ") == "why not reflexivity?"


def test_line_start_tag_text_runs_to_the_question_mark():
    tags = find_tags("intro\n[Question] why not reflexivity? and then more words\nnext")
    assert [t.text for t in tags] == ["why not reflexivity?"]


def test_mid_sentence_tag_text_is_cut_at_the_next_question_mark():
    text = "We define d_A as the distance [Question] what is furthest you can get from A while in B? and d_B as the distance"
    assert find_tags(text)[0].text == "what is furthest you can get from A while in B?"


def test_tag_alone_on_its_line_takes_the_next_non_blank_line():
    assert find_tags("[Question]\n\nWhat if X is not finite?\nx")[0].text == "What if X is not finite?"


def test_text_without_a_question_mark_runs_to_end_of_line():
    assert find_tags("[Question] explain the proof\nnext line")[0].text == "explain the proof"


def test_text_is_capped_and_whitespace_collapsed():
    text = find_tags("[Question] " + "word  " * 100)[0].text
    assert len(text) <= 200 and "  " not in text


def test_ordinals_are_one_based_in_document_order_and_embedded_in_ids():
    tags = find_tags("[Question] a?\n[Question] b?")
    assert [t.ordinal for t in tags] == [1, 2]
    assert tags[0].qid.startswith("q1-") and tags[1].qid.startswith("q2-")


def test_question_id_ignores_case_and_whitespace_but_not_text_or_ordinal():
    assert question_id(1, "Why not   reflexivity?") == question_id(1, "why not reflexivity?")
    assert question_id(1, "why not reflexivity?") != question_id(1, "why not symmetry?")
    assert question_id(1, "x?") != question_id(2, "x?")
    assert len(question_id(1, "x?").split("-")[1]) == 8


def test_resolved_markers_count_as_tags_and_the_span_covers_the_whole_marker():
    marker = "[Question: answered -> f.questions.md#q1-ab12cd34]"
    tags = find_tags(marker + " why not reflexivity?")
    assert len(tags) == 1 and tags[0].text == "why not reflexivity?"
    assert tags[0].end - tags[0].start == len(marker)


def test_raw_tags_ignores_frontmatter():
    raw = "---\nnote: [Question] fake?\n---\n\n[Question] real?\n"
    assert [t.text for t in raw_tags(raw)] == ["real?"]
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'core.indexer.questions'`.

- [ ] **Step 3: Implement**

Create `core/indexer/questions.py`:

```python
"""
questions.py
Pure logic (no network) for resolving the `[Question]` tags in Excalidraw
notes: tag discovery and stable ids, the per-note sidecar of answers, and the
deterministic step that rewrites tags in the `.rag.md` into "resolved" markers.
The resolver itself (retrieval + generation + CLI) is agent/rag/resolve_questions.py.

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from core.env.excalidraw_text import QUESTION_TAG_RE
from core.env.frontmatter import parse_frontmatter

_QUESTION_TEXT_CAP = 200
_WS_RE = re.compile(r"\s+")


def _collapse(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def normalize(text: str) -> str:
    return _collapse(text).lower()


def question_id(ordinal: int, text: str) -> str:
    digest = hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:8]
    return f"q{ordinal}-{digest}"


def question_text_after(text: str, tag_end: int) -> str:
    """The question a tag asks: the rest of the tag's line up to and including
    the first '?', else the whole line; if that line is blank, the next
    non-blank line. Whitespace-collapsed and capped."""
    for line in text[tag_end:].split("\n"):
        collapsed = _collapse(line)
        if collapsed:
            mark = collapsed.find("?")
            if mark != -1:
                collapsed = collapsed[: mark + 1]
            return collapsed[:_QUESTION_TEXT_CAP]
    return ""


@dataclass(frozen=True)
class Tag:
    ordinal: int  # 1-based, document order
    qid: str
    text: str
    start: int  # span of the whole tag token (open tag or resolved marker)
    end: int


def find_tags(markdown: str) -> list[Tag]:
    tags = []
    for ordinal, match in enumerate(QUESTION_TAG_RE.finditer(markdown), start=1):
        text = question_text_after(markdown, match.end())
        tags.append(Tag(ordinal, question_id(ordinal, text), text, match.start(), match.end()))
    return tags


def raw_tags(raw_text: str) -> list[Tag]:
    """Tags of a raw transcript, the stable source of ids (the .rag.md is
    regenerated and its wording can change; the raw transcript cannot)."""
    return find_tags(parse_frontmatter(raw_text)[1])
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/questions.py ai-sandbox/academic-rag-model/tests/core/indexer/test_questions.py
git commit -m "feat(indexer): [Question] tag discovery and stable question ids"
```

---

### Task 3: Sidecar model and atomic I/O

**Files:**
- Modify: `core/indexer/questions.py`
- Test: `tests/core/indexer/test_questions.py`

**Interfaces:**
- Consumes (Task 2): `_collapse` (module-private).
- Produces (used by Tasks 4, 6, 7):
  - `SIDECAR_SUFFIX = ".excalidraw.questions.md"`
  - `sidecar_path_for(raw_path: str) -> str`, `rag_path_for(raw_path: str) -> str` (raise `ValueError` if `raw_path` does not end in `.excalidraw.md`)
  - `@dataclass Entry(qid: str, question: str, grounded: bool, model: str, resolved_at: str, stale: bool = False, context: str = "", answer: str = "", sources: list[str] = [])`
  - `render_entry(e: Entry) -> str`, `parse_entries(body: str) -> list[Entry]`
  - `read_sidecar(path: str) -> tuple[dict, list[Entry]]` (`({}, [])` if missing)
  - `write_sidecar(path: str, fields: dict, entries: list[Entry]) -> None` (atomic)

- [ ] **Step 1: Write the failing tests**

Append to `tests/core/indexer/test_questions.py`:

```python
import os
from unittest.mock import patch

import pytest

from core.indexer.questions import (
    SIDECAR_SUFFIX,
    Entry,
    parse_entries,
    rag_path_for,
    read_sidecar,
    render_entry,
    sidecar_path_for,
    write_sidecar,
)


def _entry(**kw):
    base = dict(
        qid="q1-1a2b3c4d", question="why not reflexivity?", grounded=True, model="gemini-3.6-flash",
        resolved_at="2026-10-03T12:00:00+00:00", stale=False, context="x succsim y",
        answer="Because $x$ is related.\n\n$$u(x) \\geq u(y)$$\n\nSecond paragraph.",
        sources=["a/b.md (p. 3)", "c/d.md (section 2)"],
    )
    base.update(kw)
    return Entry(**base)


def test_paths_derive_from_the_raw_transcript_path():
    raw = "a/processed_outputs/N 2026-09-15.excalidraw.md"
    assert sidecar_path_for(raw) == "a/processed_outputs/N 2026-09-15" + SIDECAR_SUFFIX
    assert rag_path_for(raw) == "a/processed_outputs/N 2026-09-15.excalidraw.rag.md"
    with pytest.raises(ValueError):
        sidecar_path_for("a/b.md")
    with pytest.raises(ValueError):
        rag_path_for("a/b.md")


def test_entry_round_trips_grounded_with_sources():
    entry = _entry()
    assert parse_entries(render_entry(entry)) == [entry]


def test_entry_round_trips_ungrounded_with_no_sources():
    entry = _entry(grounded=False, sources=[])
    rendered = render_entry(entry)
    assert "not sourced from your course materials" in rendered
    assert parse_entries(rendered) == [entry]


def test_stale_flag_round_trips():
    assert parse_entries(render_entry(_entry(stale=True)))[0].stale is True


def test_answer_headings_cannot_split_an_entry():
    entry = _entry(answer="## Heading in answer\ntext")
    parsed = parse_entries(render_entry(entry) + "\n" + render_entry(_entry(qid="q2-aaaaaaaa")))
    assert [p.qid for p in parsed] == ["q1-1a2b3c4d", "q2-aaaaaaaa"]
    assert parsed[0].answer.startswith("### Heading in answer")


def test_write_then_read_sidecar_keeps_frontmatter_and_entries(tmp_path):
    path = str(tmp_path / ("N" + SIDECAR_SUFFIX))
    fields = {"source_excalidraw": "a/N.excalidraw.md", "questions": "2"}
    entries = [_entry(), _entry(qid="q2-bbbbbbbb", question="what if X is infinite?")]
    write_sidecar(path, fields, entries)
    got_fields, got_entries = read_sidecar(path)
    assert got_fields == fields and got_entries == entries
    assert not os.path.exists(path + ".tmp")


def test_read_sidecar_of_a_missing_file_is_empty(tmp_path):
    assert read_sidecar(str(tmp_path / "none.md")) == ({}, [])


def test_failed_write_keeps_the_existing_sidecar_and_removes_the_temp_file(tmp_path):
    path = str(tmp_path / ("N" + SIDECAR_SUFFIX))
    write_sidecar(path, {"questions": "1"}, [_entry()])
    before = open(path, encoding="utf-8").read()
    with patch("core.indexer.questions.os.replace", side_effect=OSError("disk")):
        with pytest.raises(OSError):
            write_sidecar(path, {"questions": "2"}, [_entry(), _entry(qid="q2-bbbbbbbb")])
    assert open(path, encoding="utf-8").read() == before
    assert not os.path.exists(path + ".tmp")
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: collection error `ImportError: cannot import name 'SIDECAR_SUFFIX'` (or similar).

- [ ] **Step 3: Implement**

In `core/indexer/questions.py` change the imports to:

```python
import hashlib
import os
import re
from dataclasses import dataclass, field

from core.env.excalidraw_text import QUESTION_TAG_RE
from core.env.frontmatter import parse_frontmatter, render_frontmatter
```

and append:

```python
SIDECAR_SUFFIX = ".excalidraw.questions.md"
_RAW_SUFFIX = ".excalidraw.md"
_RAG_SUFFIX = ".excalidraw.rag.md"


def sidecar_path_for(raw_path: str) -> str:
    if not raw_path.endswith(_RAW_SUFFIX):
        raise ValueError(f"not a raw Excalidraw transcript path: {raw_path!r}")
    return raw_path[: -len(_RAW_SUFFIX)] + SIDECAR_SUFFIX


def rag_path_for(raw_path: str) -> str:
    if not raw_path.endswith(_RAW_SUFFIX):
        raise ValueError(f"not a raw Excalidraw transcript path: {raw_path!r}")
    return raw_path[: -len(_RAW_SUFFIX)] + _RAG_SUFFIX


@dataclass
class Entry:
    qid: str
    question: str
    grounded: bool
    model: str
    resolved_at: str
    stale: bool = False
    context: str = ""
    answer: str = ""
    sources: list[str] = field(default_factory=list)


_NO_SOURCES = "none -- not sourced from your course materials."
_META_RE = re.compile(
    r"<!--\s*qid:\s*(?P<qid>[^;]+?);\s*grounded:\s*(?P<grounded>true|false);\s*model:\s*(?P<model>[^;]+?);\s*"
    r"resolved_at:\s*(?P<at>[^;]+?);\s*stale:\s*(?P<stale>true|false)\s*-->"
)
_SECTION_SPLIT_RE = re.compile(r"(?m)^## ")
_CONTEXT_RE = re.compile(r"\*\*Context:\*\*[ \t]*(.*)")


def render_entry(entry: Entry) -> str:
    # A line starting with "## " inside the answer would read as a new entry.
    answer = re.sub(r"(?m)^## ", "### ", entry.answer.strip())
    if entry.sources:
        sources = "**Sources:**\n" + "\n".join(f"- {s}" for s in entry.sources)
    else:
        sources = f"**Sources:** {_NO_SOURCES}"
    meta = (
        f"<!-- qid: {entry.qid}; grounded: {'true' if entry.grounded else 'false'}; model: {entry.model}; "
        f"resolved_at: {entry.resolved_at}; stale: {'true' if entry.stale else 'false'} -->"
    )
    return (
        f"## {entry.qid} - {_collapse(entry.question)}\n{meta}\n\n"
        f"**Context:** {_collapse(entry.context)}\n\n{answer}\n\n{sources}\n"
    )


def parse_entries(body: str) -> list[Entry]:
    """Reads entries back from the metadata comment and section boundaries
    only, so a user's prose edits inside an answer survive."""
    entries = []
    for section in _SECTION_SPLIT_RE.split(body)[1:]:
        heading, _, rest = section.partition("\n")
        meta = _META_RE.search(rest)
        if meta is None:
            continue
        question = heading.split(" - ", 1)[1].strip() if " - " in heading else ""
        after_meta = rest[meta.end():]
        sources_at = after_meta.rfind("**Sources:**")
        main_part = after_meta if sources_at == -1 else after_meta[:sources_at]
        sources_part = "" if sources_at == -1 else after_meta[sources_at + len("**Sources:**"):]
        context, answer = "", main_part
        context_match = _CONTEXT_RE.search(main_part)
        if context_match:
            context = context_match.group(1).strip()
            answer = main_part[context_match.end():]
        entries.append(Entry(
            qid=meta["qid"].strip(), question=question, grounded=meta["grounded"] == "true",
            model=meta["model"].strip(), resolved_at=meta["at"].strip(), stale=meta["stale"] == "true",
            context=context, answer=answer.strip(),
            sources=[ln[2:].strip() for ln in sources_part.splitlines() if ln.startswith("- ")],
        ))
    return entries


def read_sidecar(path: str) -> tuple[dict, list[Entry]]:
    if not os.path.exists(path):
        return {}, []
    with open(path, encoding="utf-8") as f:
        fields, body = parse_frontmatter(f.read())
    return fields, parse_entries(body)


def write_sidecar(path: str, fields: dict, entries: list[Entry]) -> None:
    """Atomic: the temp file is in the same folder so os.replace is a rename."""
    text = render_frontmatter(fields) + "\n".join(render_entry(e) for e in entries)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/questions.py ai-sandbox/academic-rag-model/tests/core/indexer/test_questions.py
git commit -m "feat(indexer): question sidecar model with atomic read/write"
```

---

### Task 4: Marker application (`apply_markers`)

**Files:**
- Modify: `core/indexer/questions.py`
- Test: `tests/core/indexer/test_questions.py`

**Interfaces:**
- Consumes (Tasks 2-3): `raw_tags`, `find_tags`, `normalize`, `Entry`, `read_sidecar`, `write_sidecar`, `sidecar_path_for`.
- Produces (used by Tasks 6, 7):
  - `marker_for(entry: Entry, sidecar_filename: str) -> str`
  - `apply_markers(raw_path: str, rag_path: str) -> bool` — `True` if the `.rag.md` or the sidecar's stale flags changed. The sidecar path is `sidecar_path_for(raw_path)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/core/indexer/test_questions.py`:

```python
from core.indexer.questions import apply_markers, marker_for

RAW = (
    "---\nchunks: 1\n---\n\n**[Handwritten]**\n"
    "[Question] Is IIA nec. & sufficient?\nother\n[Question] why not reflexivity?\n"
)
RAG = (
    "---\nx: y\n---\n\nProse. [Question] Is IIA necessary and sufficient?\n\n"
    "More. [Question] why not reflexivity?\n"
)


def _entry_for(tag, grounded=True):
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model="m", resolved_at="t",
        answer="ans", sources=["s"] if grounded else [],
    )


def _setup(tmp_path, raw=RAW, rag=RAG, entry_indexes=(0, 1), grounded=True):
    raw_path = str(tmp_path / "N.excalidraw.md")
    rag_path = rag_path_for(raw_path)
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(rag)
    tags = raw_tags(raw)
    entries = [_entry_for(tags[i], grounded) for i in entry_indexes]
    if entries:
        write_sidecar(sidecar_path_for(raw_path), {"questions": str(len(entries))}, entries)
    return raw_path, rag_path, tags


def _read(path):
    return open(path, encoding="utf-8").read()


def test_marker_text_for_grounded_and_ungrounded_entries():
    grounded = Entry(qid="q1-ab12cd34", question="q?", grounded=True, model="m", resolved_at="t")
    ungrounded = Entry(qid="q1-ab12cd34", question="q?", grounded=False, model="m", resolved_at="t")
    assert marker_for(grounded, "N.excalidraw.questions.md") == "[Question: answered -> N.excalidraw.questions.md#q1-ab12cd34]"
    assert marker_for(ungrounded, "N.excalidraw.questions.md") == (
        "[Question: answered (ungrounded) -> N.excalidraw.questions.md#q1-ab12cd34]"
    )


def test_markers_are_applied_by_position_when_tag_counts_match_and_wording_differs(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path)
    assert apply_markers(raw_path, rag_path) is True
    text = _read(rag_path)
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[0].qid}] Is IIA necessary and sufficient?" in text
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[1].qid}] why not reflexivity?" in text


def test_ungrounded_entries_get_the_ungrounded_marker(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path, grounded=False)
    apply_markers(raw_path, rag_path)
    assert f"[Question: answered (ungrounded) -> N.excalidraw.questions.md#{tags[0].qid}]" in _read(rag_path)


def test_a_tag_without_a_sidecar_entry_stays_open(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path, entry_indexes=(1,))
    apply_markers(raw_path, rag_path)
    text = _read(rag_path)
    assert "Prose. [Question] Is IIA necessary and sufficient?" in text
    assert f"#{tags[1].qid}]" in text


def test_second_application_changes_nothing(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path)
    apply_markers(raw_path, rag_path)
    after_first = _read(rag_path)
    assert apply_markers(raw_path, rag_path) is False
    assert _read(rag_path) == after_first


def test_when_counts_differ_tags_pair_by_text_similarity_and_unmatched_entries_go_stale(tmp_path):
    rag_one_tag = "---\nx: y\n---\n\nOnly. [Question] Why not reflexivity?\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag_one_tag)
    apply_markers(raw_path, rag_path)
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[1].qid}] Why not reflexivity?" in _read(rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    stale = {e.qid: e.stale for e in entries}
    assert stale == {tags[0].qid: True, tags[1].qid: False}


def test_a_dissimilar_tag_is_left_open_when_counts_differ(tmp_path):
    rag = "---\nx: y\n---\n\nOnly. [Question] something entirely unrelated to either\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag)
    apply_markers(raw_path, rag_path)
    assert "[Question] something entirely unrelated to either" in _read(rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert all(e.stale for e in entries)


def test_stale_entries_recover_when_the_tags_match_again(tmp_path):
    rag_one_tag = "---\nx: y\n---\n\nOnly. [Question] Why not reflexivity?\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag_one_tag)
    apply_markers(raw_path, rag_path)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(RAG)
    apply_markers(raw_path, rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert not any(e.stale for e in entries)


def test_a_marker_reverts_to_open_when_its_sidecar_entry_is_removed(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path)
    apply_markers(raw_path, rag_path)
    write_sidecar(sidecar_path_for(raw_path), {"questions": "1"}, [_entry_for(tags[1])])
    apply_markers(raw_path, rag_path)
    text = _read(rag_path)
    assert "Prose. [Question] Is IIA necessary and sufficient?" in text
    assert f"#{tags[1].qid}]" in text


def test_no_sidecar_leaves_open_tags_untouched(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path, entry_indexes=())
    assert apply_markers(raw_path, rag_path) is False
    assert _read(rag_path) == RAG


def test_missing_rag_file_is_a_noop(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path)
    os.remove(rag_path)
    assert apply_markers(raw_path, rag_path) is False
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: collection error `ImportError: cannot import name 'apply_markers'`.

- [ ] **Step 3: Implement**

Add `import difflib` to the imports of `core/indexer/questions.py`, and append:

```python
_PAIR_SIMILARITY_MIN = 0.8


def marker_for(entry: Entry, sidecar_filename: str) -> str:
    label = "answered" if entry.grounded else "answered (ungrounded)"
    return f"[Question: {label} -> {sidecar_filename}#{entry.qid}]"


def _pair_tags(raw: list[Tag], rag: list[Tag]) -> dict[int, int]:
    """raw index -> rag index. By position when the counts agree (the
    expansion reworded the text but kept the tags); otherwise greedily by
    text similarity, leaving anything below the threshold unpaired."""
    if len(raw) == len(rag):
        return {i: i for i in range(len(raw))}
    pairs: dict[int, int] = {}
    used: set[int] = set()
    for i, raw_tag in enumerate(raw):
        best, best_ratio = None, 0.0
        for j, rag_tag in enumerate(rag):
            if j in used:
                continue
            ratio = difflib.SequenceMatcher(None, normalize(raw_tag.text), normalize(rag_tag.text)).ratio()
            if ratio > best_ratio:
                best, best_ratio = j, ratio
        if best is not None and best_ratio >= _PAIR_SIMILARITY_MIN:
            pairs[i] = best
            used.add(best)
    return pairs


def apply_markers(raw_path: str, rag_path: str) -> bool:
    """Makes every tag in the .rag.md reflect the sidecar: an answered
    question gets its resolved marker, anything else is (re)set to an open
    `[Question]`. Deterministic, no model call, idempotent. Also flags sidecar
    entries stale when their raw tag has no counterpart in the .rag.md, and
    clears the flag when one is found again. Returns True if either file
    changed."""
    if not os.path.exists(rag_path):
        return False
    sidecar = sidecar_path_for(raw_path)
    with open(raw_path, encoding="utf-8") as f:
        raw = raw_tags(f.read())
    with open(rag_path, encoding="utf-8") as f:
        rag_text = f.read()
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}

    rag = find_tags(rag_text)
    replacement = {j: "[Question]" for j in range(len(rag))}
    matched: set[str] = set()
    for i, j in _pair_tags(raw, rag).items():
        entry = by_id.get(raw[i].qid)
        if entry is not None:
            replacement[j] = marker_for(entry, os.path.basename(sidecar))
            matched.add(entry.qid)

    new_text = rag_text
    for j in range(len(rag) - 1, -1, -1):
        new_text = new_text[: rag[j].start] + replacement[j] + new_text[rag[j].end:]
    changed = new_text != rag_text
    if changed:
        with open(rag_path, "w", encoding="utf-8") as f:
            f.write(new_text)

    stale_changed = False
    for entry in entries:
        should_be_stale = entry.qid not in matched
        if entry.stale != should_be_stale:
            entry.stale = should_be_stale
            stale_changed = True
    if stale_changed:
        write_sidecar(sidecar, fields, entries)
    return changed or stale_changed
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer/test_questions.py -q`
Expected: 29 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/questions.py ai-sandbox/academic-rag-model/tests/core/indexer/test_questions.py
git commit -m "feat(indexer): apply resolved-question markers to the .rag.md deterministically"
```

---

### Task 5: Resolver core (context, prompts, grounding)

**Files:**
- Create: `agent/rag/resolve_questions.py`
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Consumes: Task 1 `QUESTION_TAG_RE`, `split_labeled_segments`; Task 2 `Tag`, `_collapse` is private (do not import); Task 3 `Entry`; existing `agent.rag.rag_agent._extract_key_terms(question, client)`, `_term_match_count(text, key_terms)`, `retrieve_passages(roots, query, client, course=, key_terms=)`; `core.indexer.index_search.PassageResult` (`.text`, `.path`, `.citation`).
- Produces (used by Task 6):
  - `RESOLVER_MODEL = "gemini-3.6-flash"`
  - `question_context(raw_body: str, ordinal: int) -> tuple[str, list[str]]` — (excerpt around the ordinal-th tag, neighboring `Slide` blocks)
  - `build_answer_prompt(question: str, context: str, neighbor_slides: list[str], passages: list | None) -> str` (`passages=None` means ungrounded)
  - `resolve_question(tag, context, neighbors, *, client, roots, course, model, exclude_basenames, retrieve=retrieve_passages, extract=_extract_key_terms) -> Entry`

- [ ] **Step 1: Write the failing tests**

Create `tests/agent/rag/test_resolve_questions.py`:

```python
from unittest.mock import MagicMock

import pytest

from agent.rag.resolve_questions import (
    RESOLVER_MODEL,
    build_answer_prompt,
    question_context,
    resolve_question,
)
from core.indexer.index_search import PassageResult
from core.indexer.questions import find_tags

BODY = (
    "**[Slide]**\nSlide A text about completeness\n\n"
    "**[Handwritten]**\nnotes [Question] why not reflexivity?\nmore\n\n"
    "**[Slide]**\nSlide B text\n\n"
    "**[Handwritten]**\n[Question] what if X is infinite?\n"
)


def test_default_model_is_the_stronger_tier():
    assert RESOLVER_MODEL == "gemini-3.6-flash"


def test_context_for_the_first_tag_includes_both_adjacent_slides():
    excerpt, neighbors = question_context(BODY, 1)
    assert "why not reflexivity?" in excerpt
    assert neighbors == ["Slide A text about completeness", "Slide B text"]


def test_context_for_the_last_tag_has_only_the_preceding_slide():
    excerpt, neighbors = question_context(BODY, 2)
    assert "what if X is infinite?" in excerpt
    assert neighbors == ["Slide B text"]


def test_context_for_an_unknown_ordinal_is_empty():
    assert question_context(BODY, 3) == ("", [])


def test_context_excerpt_is_windowed_and_slides_are_truncated():
    body = "**[Slide]**\n" + "s" * 2000 + "\n\n**[Handwritten]**\n" + "a " * 2000 + "[Question] why? " + "b " * 2000
    excerpt, neighbors = question_context(body, 1)
    assert "[Question] why?" in excerpt
    assert len(excerpt) <= 1600
    assert len(neighbors[0]) == 800


def test_grounded_prompt_carries_question_context_slides_and_excerpts():
    passage = PassageResult(chunk_id="c", file_id="f", path="book.md", course="c", score=0.9,
                            text="EXCERPT TEXT", citation="p. 3", root="/r")
    prompt = build_answer_prompt("why not reflexivity?", "my notes", ["Slide B text"], [passage])
    for needle in ("why not reflexivity?", "my notes", "Slide B text", "EXCERPT TEXT", "p. 3"):
        assert needle in prompt


def test_ungrounded_prompt_has_no_excerpts_and_asks_for_general_knowledge():
    prompt = build_answer_prompt("why not reflexivity?", "my notes", [], None)
    assert "general knowledge" in prompt
    assert "EXCERPT" not in prompt


def _client(text="An explanation."):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


def _passage(text, path="book.md", citation="p. 3"):
    return PassageResult(chunk_id="c1", file_id="f1", path=path, course="c", score=0.9,
                         text=text, citation=citation, root="/r")


def _resolve(client, passages, key_terms, exclude=()):
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    return resolve_question(
        tag, "ctx text", ["Slide text"], client=client, roots=["/r"], course="c", model="m",
        exclude_basenames=set(exclude), retrieve=lambda *a, **k: passages, extract=lambda q, c: key_terms,
    )


def test_grounded_when_a_passage_mentions_a_key_term():
    client = _client()
    entry = _resolve(client, [_passage("The Hausdorff metric is defined as ...")], ["Hausdorff"])
    assert entry.grounded is True
    assert entry.sources == ["book.md (p. 3)"]
    assert entry.answer == "An explanation."
    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == "m" and "The Hausdorff metric is defined" in call["contents"]


def test_ungrounded_when_no_passage_mentions_any_key_term():
    client = _client()
    entry = _resolve(client, [_passage("Completely unrelated passage")], ["Hausdorff"])
    assert entry.grounded is False and entry.sources == []
    assert "Completely unrelated passage" not in client.models.generate_content.call_args.kwargs["contents"]


def test_ungrounded_when_nothing_was_retrieved_even_with_no_key_terms():
    assert _resolve(_client(), [], []).grounded is False


def test_grounded_when_there_are_no_key_terms_but_passages_exist():
    assert _resolve(_client(), [_passage("some passage")], []).grounded is True


def test_the_notes_own_files_are_excluded_from_grounding():
    own = _passage("The Hausdorff metric is defined as ...", path="lecture/N.excalidraw.rag.md")
    entry = _resolve(_client(), [own], ["Hausdorff"], exclude={"N.excalidraw.rag.md"})
    assert entry.grounded is False and entry.sources == []


def test_empty_model_answer_raises_so_no_partial_entry_is_recorded():
    with pytest.raises(ValueError):
        _resolve(_client(text="  "), [_passage("Hausdorff")], ["Hausdorff"])


def test_entry_records_identity_model_and_context():
    entry = _resolve(_client(), [_passage("Hausdorff")], ["Hausdorff"])
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    assert entry.qid == tag.qid and entry.question == tag.text
    assert entry.model == "m" and entry.resolved_at and entry.stale is False
    assert entry.context == "ctx text"
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/agent/rag/test_resolve_questions.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'agent.rag.resolve_questions'`.

- [ ] **Step 3: Implement**

Create `agent/rag/resolve_questions.py`:

```python
"""
resolve_questions.py
Answers the `[Question]` tags in Excalidraw notes: grounded in the course
corpus when it can be (the same key-term + retrieval + grounded check /hint
uses), clearly labeled when it can't. Answers go to a per-note sidecar; the
.rag.md gets resolved markers (core/indexer/questions.py).

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from agent.rag.rag_agent import _extract_key_terms, _term_match_count, retrieve_passages
from core.env.excalidraw_text import QUESTION_TAG_RE, split_labeled_segments
from core.env.gemini_utils import call_with_retries
from core.indexer.questions import Entry, Tag

RESOLVER_MODEL = "gemini-3.6-flash"  # the stronger tier: answers are persisted and indexed
_CONTEXT_CHARS = 1500
_NEIGHBOR_CHARS = 800
_STORED_CONTEXT_CHARS = 600

_ANSWER_PROMPT_TEMPLATE = """A student wrote this open question in the margin of their lecture notes. \
Explain the answer so the student can understand it, with the reasoning spelled out. Use LaTeX \
($...$ / $$...$$) for math.

The student's handwriting around the question:
{context}

{slides_block}{excerpts_block}Open question: {question}

{grounding_instruction}
Respond with ONLY the explanation in markdown -- no preamble, no code fence."""

_GROUNDED_INSTRUCTION = (
    "Base the explanation on the course excerpts above and do not claim anything they contradict."
)
_UNGROUNDED_INSTRUCTION = (
    "No course material supports this question. Answer from general knowledge and say plainly "
    "where you are unsure."
)


def question_context(raw_body: str, ordinal: int) -> tuple[str, list[str]]:
    """The text around the ordinal-th tag of a raw transcript body (frontmatter
    already stripped): a window of its own block, plus the adjacent slide
    blocks. Splitting preserves tag order, so counting tags across segments in
    order finds the same tag the sidecar's ordinal refers to."""
    segments = split_labeled_segments(raw_body)
    seen = 0
    for idx, (_label, text) in enumerate(segments):
        matches = list(QUESTION_TAG_RE.finditer(text))
        if seen + len(matches) >= ordinal:
            match = matches[ordinal - seen - 1]
            half = _CONTEXT_CHARS // 2
            excerpt = text[max(0, match.start() - half): min(len(text), match.end() + half)].strip()
            neighbors = [
                segments[j][1][:_NEIGHBOR_CHARS]
                for j in (idx - 1, idx + 1)
                if 0 <= j < len(segments) and segments[j][0] == "Slide"
            ]
            return excerpt, neighbors
        seen += len(matches)
    return "", []


def build_answer_prompt(question: str, context: str, neighbor_slides: list[str], passages: list | None) -> str:
    slides_block = ""
    if neighbor_slides:
        slides_block = "Lecture slide content beside the question:\n" + "\n\n---\n\n".join(neighbor_slides) + "\n\n"
    excerpts_block = ""
    if passages:
        excerpts = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
        excerpts_block = f"Course excerpts:\n{excerpts}\n\n"
    return _ANSWER_PROMPT_TEMPLATE.format(
        context=context, slides_block=slides_block, excerpts_block=excerpts_block, question=question,
        grounding_instruction=_GROUNDED_INSTRUCTION if passages else _UNGROUNDED_INSTRUCTION,
    )


def resolve_question(
    tag: Tag, context: str, neighbors: list[str], *, client, roots: list[str], course: str | None,
    model: str, exclude_basenames: set[str], retrieve=retrieve_passages, extract=_extract_key_terms,
) -> Entry:
    """One question -> one Entry. Raises on any failure (including an empty
    answer) so the caller records nothing for it. Grounded means a passage
    survived own-note exclusion and (no key terms, or one mentions a key
    term) -- /hint's check, plus a guard so an empty retrieval can never count
    as grounded."""
    key_terms = extract(f"{tag.text}\n{context}", client)
    found = retrieve(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    passages = [p for p in found if os.path.basename(p.path) not in exclude_basenames]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    response = call_with_retries(lambda: client.models.generate_content(
        model=model, contents=prompt, config={"temperature": 0.2},
    ))
    answer = (response.text or "").strip()
    if not answer:
        raise ValueError(f"model returned an empty answer for {tag.qid}")
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model=model,
        resolved_at=datetime.now(timezone.utc).isoformat(),
        context=" ".join(context.split())[:_STORED_CONTEXT_CHARS], answer=answer,
        sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/agent/rag/test_resolve_questions.py -q`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/rag/resolve_questions.py ai-sandbox/academic-rag-model/tests/agent/rag/test_resolve_questions.py
git commit -m "feat(rag): resolve a single [Question] with grounded or labeled-ungrounded answers"
```

---

### Task 6: Note orchestration, discovery, and CLI

**Files:**
- Modify: `agent/rag/resolve_questions.py`
- Test: `tests/agent/rag/test_resolve_questions.py`

**Interfaces:**
- Consumes (Tasks 2-5): `find_tags`, `raw_tags` (use `find_tags(parse_frontmatter(text)[1])` where you also need the body), `read_sidecar`, `write_sidecar`, `sidecar_path_for`, `rag_path_for`, `apply_markers`, `Entry`, `Tag`, `question_context`, `resolve_question`, `RESOLVER_MODEL`; existing `core.env.frontmatter.parse_frontmatter`, `core.indexer.index_card.derive_course`, `load_shard`, `core.env.gemini_utils.get_gemini_client`, `load_dotenv_override`.
- Produces: `NoteResult(resolved: int, skipped: int, failed: list[str])`, `discover_notes(hub, course=None, note=None) -> list[str]`, `resolve_note(raw_path, hub, client, roots, model=RESOLVER_MODEL, redo=False, budget=None, retrieve=..., extract=...) -> NoteResult`, `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent/rag/test_resolve_questions.py`:

```python
import os
from unittest.mock import patch

from agent.rag import resolve_questions as rq
from agent.rag.resolve_questions import discover_notes, resolve_note
from core.indexer.index_card import save_shard
from core.indexer.questions import Entry, read_sidecar, rag_path_for, sidecar_path_for

RAW_FM = "---\nchunks: 1\nembedded_slides: true\n---\n\n"
RAG_TEXT = "---\nx: y\n---\n\nProse [Question] why not reflexivity?\n\nMore [Question] what if X is infinite?\n"


def _hub(tmp_path, course="microecon", raw_body=BODY, name="N 2026-09-15"):
    hub = tmp_path / "hub"
    out = hub / "academic_notes" / course / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True)
    raw = out / f"{name}.excalidraw.md"
    raw.write_text(RAW_FM + raw_body, encoding="utf-8")
    (out / f"{name}.excalidraw.rag.md").write_text(RAG_TEXT, encoding="utf-8")
    return str(hub), str(raw)


def _fake_resolve(failing_ordinals=()):
    def fake(tag, context, neighbors, **kwargs):
        if tag.ordinal in failing_ordinals:
            raise RuntimeError("boom")
        return Entry(qid=tag.qid, question=tag.text, grounded=True, model=kwargs["model"],
                     resolved_at="t", answer="A", sources=["s"])
    return fake


def test_resolve_note_writes_the_sidecar_and_marks_the_rag(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        result = resolve_note(raw, hub, client=object(), roots=[hub])
    assert (result.resolved, result.skipped, result.failed) == (2, 0, [])
    _, entries = read_sidecar(sidecar_path_for(raw))
    assert [e.question for e in entries] == ["why not reflexivity?", "what if X is infinite?"]
    rag = open(rag_path_for(raw), encoding="utf-8").read()
    assert rag.count("[Question: answered ->") == 2


def test_second_run_skips_answered_questions_and_redo_redoes_them(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        resolve_note(raw, hub, client=object(), roots=[hub])
        assert mock.call_count == 2
        again = resolve_note(raw, hub, client=object(), roots=[hub])
        assert mock.call_count == 2 and (again.resolved, again.skipped) == (0, 2)
        resolve_note(raw, hub, client=object(), roots=[hub], redo=True)
        assert mock.call_count == 4


def test_one_failing_question_does_not_stop_the_others_and_is_retried_alone(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve(failing_ordinals={1})):
        result = resolve_note(raw, hub, client=object(), roots=[hub])
    assert result.resolved == 1 and len(result.failed) == 1 and result.failed[0].startswith("q1-")
    _, entries = read_sidecar(sidecar_path_for(raw))
    assert [e.question for e in entries] == ["what if X is infinite?"]
    rag = open(rag_path_for(raw), encoding="utf-8").read()
    assert rag.count("[Question: answered ->") == 1 and "[Question] why not reflexivity?" in rag
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        retry = resolve_note(raw, hub, client=object(), roots=[hub])
    assert mock.call_count == 1 and retry.resolved == 1 and retry.failed == []


def test_budget_caps_the_number_of_questions_resolved(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        result = resolve_note(raw, hub, client=object(), roots=[hub], budget=1)
    assert result.resolved == 1
    assert len(read_sidecar(sidecar_path_for(raw))[1]) == 1


def test_discover_notes_finds_only_raw_transcripts_that_have_tags(tmp_path):
    hub, raw = _hub(tmp_path)
    out = os.path.dirname(raw)
    open(os.path.join(out, "Plain 2026-09-16.excalidraw.md"), "w", encoding="utf-8").write(RAW_FM + "no tags here")
    open(os.path.join(out, "Plain 2026-09-16.excalidraw.rag.md"), "w", encoding="utf-8").write("[Question] x?")
    open(os.path.join(out, "N 2026-09-15.excalidraw.questions.md"), "w", encoding="utf-8").write("[Question] x?")
    assert discover_notes(hub) == [raw]
    assert discover_notes(hub, course="other") == []
    assert discover_notes(hub, note="2026-09-15") == [raw]
    assert discover_notes(hub, note="nomatch") == []


def test_cli_dry_run_lists_questions_without_any_api_call(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "get_gemini_client", side_effect=AssertionError("no client in dry-run")), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("no resolve in dry-run")):
        assert rq.main(["--root", hub, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "2 question(s)" in out and "why not reflexivity?" in out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_skips_notes_that_are_a_subset_of_another(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    rel_rag = os.path.relpath(rag_path_for(raw), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "x", "path": rel_rag, "subset_of": "y"}])
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("subset must be skipped")):
        assert rq.main(["--root", hub]) == 0
    assert "subset" in capsys.readouterr().out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_full_run_returns_zero_and_nonzero_on_failure(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        assert rq.main(["--root", hub]) == 0
    os.remove(sidecar_path_for(raw))
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve(failing_ordinals={1})):
        assert rq.main(["--root", hub]) == 1


def test_cli_max_questions_stops_after_the_budget(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        rq.main(["--root", hub, "--max-questions", "1"])
    assert mock.call_count == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/agent/rag/test_resolve_questions.py -q`
Expected: failures/errors `ImportError: cannot import name 'discover_notes'` (or `AttributeError` on `rq.main`).

- [ ] **Step 3: Implement**

In `agent/rag/resolve_questions.py` replace the import block at the top with:

```python
import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent.rag.rag_agent import _extract_key_terms, _term_match_count, retrieve_passages
from core.env.excalidraw_text import QUESTION_TAG_RE, split_labeled_segments
from core.env.frontmatter import parse_frontmatter
from core.env.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from core.indexer.index_card import derive_course, load_shard
from core.indexer.questions import (
    Entry,
    Tag,
    apply_markers,
    find_tags,
    rag_path_for,
    read_sidecar,
    sidecar_path_for,
    write_sidecar,
)
```

and append:

```python
_DEFAULT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


@dataclass
class NoteResult:
    resolved: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)


def _read_body(raw_path: str) -> str:
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def _rel(hub: str, path: str) -> str:
    return os.path.relpath(path, hub).replace(os.sep, "/")


def _note_card(hub: str, raw_path: str) -> dict | None:
    rel_rag = _rel(hub, rag_path_for(raw_path))
    for card in load_shard(hub, derive_course(rel_rag)):
        if card.get("path") == rel_rag:
            return card
    return None


def discover_notes(hub: str, course: str | None = None, note: str | None = None) -> list[str]:
    """Raw transcripts (`processed_outputs/*.excalidraw.md`) under academic_notes/
    that contain at least one tag, optionally limited to a course or to
    filenames containing `note`."""
    found = []
    for dirpath, _dirs, files in os.walk(os.path.join(hub, "academic_notes")):
        if os.path.basename(dirpath) != "processed_outputs":
            continue
        if course and derive_course(_rel(hub, dirpath)) != course:
            continue
        for name in sorted(files):
            if not name.endswith(".excalidraw.md") or (note and note not in name):
                continue
            raw_path = os.path.join(dirpath, name)
            if find_tags(_read_body(raw_path)):
                found.append(raw_path)
    return sorted(found)


def resolve_note(
    raw_path: str, hub: str, client, roots: list[str], model: str = RESOLVER_MODEL, redo: bool = False,
    budget: int | None = None, retrieve=retrieve_passages, extract=_extract_key_terms,
) -> NoteResult:
    """Resolves a note's unanswered questions into its sidecar, then applies
    markers. A question that fails records nothing and is retried next run."""
    body = _read_body(raw_path)
    tags = find_tags(body)
    sidecar = sidecar_path_for(raw_path)
    rag_path = rag_path_for(raw_path)
    fields, entries = read_sidecar(sidecar)
    by_id = {e.qid: e for e in entries}
    card = _note_card(hub, raw_path)
    course = derive_course(_rel(hub, raw_path))
    exclude = {os.path.basename(rag_path), os.path.basename(sidecar)}

    result = NoteResult()
    for tag in tags:
        if tag.qid in by_id and not redo:
            result.skipped += 1
            continue
        if budget is not None and result.resolved >= budget:
            break
        context, neighbors = question_context(body, tag.ordinal)
        try:
            by_id[tag.qid] = resolve_question(
                tag, context, neighbors, client=client, roots=roots, course=course, model=model,
                exclude_basenames=exclude, retrieve=retrieve, extract=extract,
            )
            result.resolved += 1
        except Exception as err:
            print(f"WARNING: {tag.qid} ({tag.text[:60]!r}) failed: {err}")
            result.failed.append(tag.qid)

    if result.resolved:
        in_order = [by_id[t.qid] for t in tags if t.qid in by_id]
        leftover = [e for qid, e in by_id.items() if qid not in {t.qid for t in tags}]
        ordered = in_order + leftover
        fields = {
            **fields,
            "source_excalidraw": _rel(hub, raw_path),
            "source_note_file_id": card["file_id"] if card else "",
            "resolver_model": model,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "questions": str(len(ordered)),
        }
        write_sidecar(sidecar, fields, ordered)
    apply_markers(raw_path, rag_path)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer the [Question] tags in Excalidraw notes.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None)
    parser.add_argument("--note", default=None, help="Only raw transcripts whose filename contains this text.")
    parser.add_argument("--dry-run", action="store_true", help="List questions; no API calls, no writes.")
    parser.add_argument("--redo", action="store_true", help="Re-answer questions that already have an entry.")
    parser.add_argument("--model", default=RESOLVER_MODEL)
    parser.add_argument("--max-questions", type=int, default=None)
    args = parser.parse_args(argv)

    hub = os.path.abspath(args.root)
    jobs = []
    for raw_path in discover_notes(hub, args.course, args.note):
        card = _note_card(hub, raw_path)
        if card and card.get("subset_of"):
            print(f"skip (subset of another note): {os.path.basename(raw_path)}")
            continue
        answered = {e.qid for e in read_sidecar(sidecar_path_for(raw_path))[1]}
        pending = [t for t in find_tags(_read_body(raw_path)) if args.redo or t.qid not in answered]
        jobs.append((raw_path, pending))

    total = sum(len(p) for _, p in jobs)
    print(f"{len(jobs)} note(s) with [Question] tags, {total} question(s) to resolve")
    if args.dry_run:
        for raw_path, pending in jobs:
            print(f"  {os.path.basename(raw_path)}")
            for tag in pending:
                print(f"    {tag.qid}: {tag.text}")
        return 0
    if total == 0:
        return 0

    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        return 1
    remaining = args.max_questions
    failed: list[str] = []
    for raw_path, _pending in jobs:
        if remaining is not None and remaining <= 0:
            print("stopping: --max-questions budget used")
            break
        print(f"Resolving {os.path.basename(raw_path)}...")
        result = resolve_note(
            raw_path, hub, client, [hub], model=args.model, redo=args.redo, budget=remaining,
        )
        failed.extend(result.failed)
        if remaining is not None:
            remaining -= result.resolved
    print(f"done; failed: {failed or 'none'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/agent/rag/test_resolve_questions.py -q`
Expected: all pass (Task 5's 14 plus 9 new).

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/agent/rag/resolve_questions.py ai-sandbox/academic-rag-model/tests/agent/rag/test_resolve_questions.py
git commit -m "feat(rag): resolve_questions CLI with discovery, idempotence, and failure isolation"
```

---

### Task 7: Re-apply markers when a note is regenerated (`write_outputs`)

**Files:**
- Modify: `pipelines/transcribe_notes/transcribe_excalidraw.py` (`write_outputs`)
- Test: `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes (Task 4): `apply_markers(raw_path, rag_path) -> bool`.
- Produces: none (side effect: a regenerated `.rag.md` regains its markers before it is indexed).

- [ ] **Step 1: Write the failing tests**

Append to `tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py` (it already imports `os`, `patch`, `write_outputs`, and defines `_write_outputs_kwargs`):

```python
def test_write_outputs_reapplies_markers_from_an_existing_sidecar(tmp_path):
    from core.env.academic_hub_paths import resolve_output_dir
    from core.indexer.questions import Entry, find_tags, sidecar_path_for, write_sidecar

    kwargs = _write_outputs_kwargs(tmp_path)
    kwargs["raw_markdown"] = "**[Handwritten]**\n[Question] why not reflexivity?\n"
    kwargs["expanded_markdown"] = "Prose. [Question] why not reflexivity?\n"
    out_dir = resolve_output_dir(kwargs["excalidraw_md_path"])
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "Drawing 2026-09-08.excalidraw.md")
    tag = find_tags(kwargs["raw_markdown"])[0]
    write_sidecar(sidecar_path_for(raw_path), {"questions": "1"}, [Entry(
        qid=tag.qid, question=tag.text, grounded=True, model="m", resolved_at="t", answer="A", sources=["s"],
    )])
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        _raw, rag_path = write_outputs(**kwargs)
    text = open(rag_path, encoding="utf-8").read()
    assert f"[Question: answered -> Drawing 2026-09-08.excalidraw.questions.md#{tag.qid}] why not reflexivity?" in text


def test_write_outputs_applies_markers_before_indexing(tmp_path):
    order = []
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.apply_markers", side_effect=lambda *a: order.append("markers")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write", side_effect=lambda *a, **k: order.append("index")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        write_outputs(**kwargs)
    assert order == ["markers", "index"]


def test_write_outputs_survives_a_marker_failure_and_still_indexes(tmp_path, capsys):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.apply_markers", side_effect=RuntimeError("boom")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write") as mock_index, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        _raw, rag_path = write_outputs(**kwargs)
    assert os.path.exists(rag_path)
    mock_index.assert_called_once()
    assert "WARNING" in capsys.readouterr().out
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py -k "markers" -q`
Expected: failures (`AttributeError: ... transcribe_excalidraw has no attribute 'apply_markers'`).

- [ ] **Step 3: Implement**

In `pipelines/transcribe_notes/transcribe_excalidraw.py`:

(a) Add to the imports, after `from core.indexer.related import link_subsets`:

```python
from core.indexer.questions import apply_markers
```

(b) In `write_outputs`, directly after the `.rag.md` write block and before the indexing `try:` (i.e. after `f.write(build_frontmatter(rag_meta) + expanded_markdown)`), insert:

```python
    try:
        apply_markers(raw_path, rag_path)
    except Exception as err:
        print(f"WARNING: could not re-apply question markers to {rag_path} ({err}).")
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/pipelines/transcribe_notes -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_excalidraw.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git commit -m "feat(transcribe): re-apply question markers after regenerating a .rag.md, before indexing"
```

---

### Task 8: Index the sidecar

**Files:**
- Modify: `core/indexer/index_card.py` (constant), `core/indexer/index_search.py` (`rebuild`, imports)
- Test: `tests/core/indexer/test_index_search.py`, `tests/core/indexer/test_chunk_index.py`

**Interfaces:**
- Consumes: existing `compute_id_from_parts(parts: list[str]) -> str`, `compute_file_id(path)`, `compute_content_hash(path)`, `_reconcile_one(...)`.
- Produces: `EXCALIDRAW_QUESTION_DOC_TYPES = frozenset({"excalidraw_questions"})`; `rebuild` indexes `<base>.excalidraw.questions.md` with `file_id = compute_id_from_parts(["excalidraw_questions", <source note's file_id>])`.

- [ ] **Step 1: Write the failing tests**

(a) In `tests/core/indexer/test_index_search.py`, add `compute_id_from_parts` to the existing `from core.indexer.index_card import (...)` list. Then add this class **above** the final `if __name__ == "__main__":` block:

```python
class TestRebuildExcalidrawQuestionSidecar(unittest.TestCase):
    def _sidecar(self, md_path, text):
        base = os.path.basename(md_path)[: -len(".excalidraw.md")]
        path = os.path.join(os.path.dirname(md_path), "processed_outputs", f"{base}.excalidraw.questions.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_sidecar_is_indexed_under_a_stable_derived_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path, _ = _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            self._sidecar(md_path, "## q1-aaaaaaaa - Why?\nanswer one\n")
            rebuild(tmp, client=_fake_client())
            expected_id = compute_id_from_parts(["excalidraw_questions", compute_file_id(md_path)])
            cards = [c for c in load_shard(tmp, "math-camp") if c["file_id"] == expected_id]
            self.assertEqual(len(cards), 1)
            self.assertTrue(cards[0]["path"].endswith("Drawing 2026-09-08.excalidraw.questions.md"))
            self.assertFalse(cards[0].get("orphaned"))

    def test_rewriting_the_sidecar_updates_instead_of_duplicating_the_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path, _ = _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            self._sidecar(md_path, "## q1-aaaaaaaa - Why?\nanswer one\n")
            rebuild(tmp, client=_fake_client())
            self._sidecar(md_path, "## q1-aaaaaaaa - Why?\na much longer, rewritten answer\n")
            rebuild(tmp, client=_fake_client())
            expected_id = compute_id_from_parts(["excalidraw_questions", compute_file_id(md_path)])
            cards = load_shard(tmp, "math-camp")
            self.assertEqual(len([c for c in cards if c["file_id"] == expected_id]), 1)
            self.assertEqual(len(cards), 2)  # the note's own card + the sidecar's

    def test_no_sidecar_means_no_extra_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "math-camp", "lecture_notes", "Drawing 2026-09-08")
            rebuild(tmp, client=_fake_client())
            self.assertEqual(len(load_shard(tmp, "math-camp")), 1)
```

(b) In `tests/core/indexer/test_chunk_index.py`, add above the final `if __name__ == "__main__":` block:

```python
class TestQuestionSidecarChunking(unittest.TestCase):
    def test_one_heading_chunk_per_question(self):
        from core.indexer.chunk_index import chunk_file
        text = (
            "---\nresolver_model: m\n---\n\n"
            "## q1-aaaaaaaa - Why not reflexivity?\n<!-- qid: q1-aaaaaaaa; grounded: true -->\n\n"
            "**Context:** ctx\n\nAnswer one is short.\n\n**Sources:** a\n\n"
            "## q2-bbbbbbbb - What if X is not finite?\n<!-- qid: q2-bbbbbbbb; grounded: false -->\n\n"
            "**Context:** ctx2\n\nAnswer two is short.\n\n**Sources:** none\n"
        )
        chunks = chunk_file(text, "excalidraw_questions", "lecture_notes")
        self.assertEqual(
            [c["heading_path"] for c in chunks],
            [["q1-aaaaaaaa - Why not reflexivity?"], ["q2-bbbbbbbb - What if X is not finite?"]],
        )
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m pytest tests/core/indexer/test_index_search.py -k QuestionSidecar -q; $PY -m pytest tests/core/indexer/test_chunk_index.py -k QuestionSidecar -q`
Expected: the `rebuild` tests fail (no card for the sidecar id: `AssertionError: 0 != 1`); the chunking test already passes (the chunker needs no change; it pins the behavior the design relies on).

- [ ] **Step 3: Implement**

(a) In `core/indexer/index_card.py`, directly after `EXCALIDRAW_DOC_TYPES = frozenset({"excalidraw_notes"})`, add:

```python
# The question resolver's per-note sidecar of answers
# (core/indexer/questions.py), indexed as its own card so retrieval can find
# resolved answers.
EXCALIDRAW_QUESTION_DOC_TYPES = frozenset({"excalidraw_questions"})
```

(b) In `core/indexer/index_search.py`, add `EXCALIDRAW_QUESTION_DOC_TYPES,` to the `from core.indexer.index_card import (...)` list (after `EXCALIDRAW_DOC_TYPES,`).

(c) In `rebuild()`'s Excalidraw loop, directly after the existing `_reconcile_one(... known_doc_types=EXCALIDRAW_DOC_TYPES, source_asset_path=rel_image_path)` call and before `_flag_or_prune_orphans`, add (inside the loop, same indentation as that call):

```python
        sidecar_path = os.path.join(os.path.dirname(rag_path), f"{base_name}.excalidraw.questions.md")
        if os.path.exists(sidecar_path) and os.path.getsize(sidecar_path) > 0:
            # Identity derives from the source note, not the sidecar's own bytes:
            # the sidecar is rewritten on every resolver run, and a bytes-based id
            # would mint a new card each time.
            sidecar_id = compute_id_from_parts(["excalidraw_questions", file_id])
            seen_file_ids.add(sidecar_id)
            with open(sidecar_path, "r", encoding="utf-8") as f:
                sidecar_text = f.read()
            _reconcile_one(academic_hub_root, course_name, category, sidecar_id,
                           os.path.relpath(sidecar_path, academic_hub_root).replace(os.sep, "/"),
                           rel_md_path, sidecar_text, None, client, force, stats,
                           source_mtime=os.path.getmtime(sidecar_path),
                           content_hash=compute_content_hash(sidecar_path),
                           known_doc_types=EXCALIDRAW_QUESTION_DOC_TYPES, source_asset_path=rel_image_path)
```

- [ ] **Step 4: Run to verify pass**

Run: `$PY -m pytest tests/core/indexer -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/index_card.py ai-sandbox/academic-rag-model/core/indexer/index_search.py ai-sandbox/academic-rag-model/tests/core/indexer/test_index_search.py ai-sandbox/academic-rag-model/tests/core/indexer/test_chunk_index.py
git commit -m "feat(indexer): index the question sidecar under a stable derived id"
```

---

### Task 9: Docs, spec clarifications, regression, and real-data dry run

**Files:**
- Modify: `agent/rag/README.md`, `core/indexer/README.md`, `docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md`

**Interfaces:** none.

- [ ] **Step 1: Spec clarifications (two, both discovered while planning)**

In the spec:
1. Change the status line to `**Status:** approved; implemented per docs/superpowers/plans/agent/rag/2026-10-03-question-resolver.md.`
2. In "Resolution flow" step 4, replace the grounded definition with: `**Grounded?** at least one retrieved passage survives own-note exclusion and (no key terms were extracted, or some passage mentions a key term). This is /hint's check plus a guard so an empty retrieval never counts as grounded.`
3. Replace the whole "Open questions for the implementation plan" section's first two bullets with: `Resolved in the plan: the shared segment helper and the shared tag regex now live in core/env/excalidraw_text.py, imported by transcribe_excalidraw.py, related.py, questions.py and resolve_questions.py.` (keep the prompt-wording bullet).

- [ ] **Step 2: Document the feature**

In `agent/rag/README.md` add a section:

```markdown
## Resolving `[Question]` tags (`resolve_questions.py`)

`python -m agent.rag.resolve_questions [--root R] [--course C] [--note TEXT] [--dry-run] [--redo] [--model M] [--max-questions N]`
answers the open questions the Excalidraw pipeline tags as `[Question]`. For each unanswered tag it extracts key terms,
retrieves course passages (`retrieve_passages`), and answers: grounded in the retrieved excerpts when a passage mentions a
key term, otherwise from general knowledge and labeled ungrounded. Answers go to `<name>.excalidraw.questions.md` beside the
note (atomic writes, one `## q<n>-<hash>` section per question); the `.rag.md` tag becomes
`[Question: answered -> <sidecar>#<id>]` (or `answered (ungrounded)`). Idempotent: answered ids are skipped unless `--redo`;
a failing question writes nothing and is retried next run; notes that are a `subset_of` another note are skipped.
`--dry-run` makes no API calls. Uses `PAID_GEMINI_KEY`. Markers are re-applied automatically whenever a note is
regenerated (`transcribe_excalidraw.write_outputs`, `--reexpand`).
```

In `core/indexer/README.md`, after the `related.py` bullet, add:

```markdown
- `questions.py` (2026-10-03) — pure logic for the `[Question]` resolver (`agent/rag/resolve_questions.py`):
  tag discovery and stable ids (`q<ordinal>-<hash>`, from the raw transcript so regeneration can't change them),
  the per-note sidecar (`<name>.excalidraw.questions.md`) with atomic I/O, and `apply_markers`, the deterministic
  step that rewrites `.rag.md` tags into resolved markers (by position when tag counts match, by text similarity
  otherwise; unmatched entries are flagged stale). `rebuild` indexes each sidecar as its own `excalidraw_questions`
  card under `compute_id_from_parts(["excalidraw_questions", <note file_id>])` so rewrites update one card.
```

- [ ] **Step 3: Full regression**

Run: `$PY -W error::SyntaxWarning -m pytest tests -q -p no:cacheprovider`
Expected: all pass (1939 before this work plus the new tests); no `SyntaxWarning`s.

- [ ] **Step 4: Real-data dry run (read-only, no API calls)**

```bash
PYTHONPATH="$(pwd -W)" $PY -m agent.rag.resolve_questions --root "C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-hub" --course microecon --dry-run
```

Expected: `4 note(s) with [Question] tags, 7 question(s) to resolve`, listing the 09-07 (1), 09-10 (1), 09-17 (1) and 09-22 (4) notes, each question with its `q<n>-<hash>` id. If the counts differ, stop and report; do not adjust the code to match.

- [ ] **Step 5: Commit, then ask before the paid run**

```bash
git add ai-sandbox/academic-rag-model/agent/rag/README.md ai-sandbox/academic-rag-model/core/indexer/README.md ai-sandbox/academic-rag-model/docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
git commit -m "docs: document the question resolver; clarify grounded check and shared helper in the spec"
```

The real run (about 14-21 paid model calls, writes four sidecars and markers into the main checkout's vault) happens only with the user's go-ahead: `PYTHONPATH="$(pwd -W)" $PY -m agent.rag.resolve_questions --root <hub> --course microecon`, then `python -m core.indexer.index_search --root <hub> rebuild --course microecon` to index the sidecars, and a `query` to confirm a resolved answer is retrievable and the `.rag.md` shows markers.
