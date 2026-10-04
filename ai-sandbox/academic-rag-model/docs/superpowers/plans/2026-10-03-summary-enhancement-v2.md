# Summary Enhancement v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework `agent/summary_enhance/` so the enhanced guide reads as a clean standalone study document (no inline citations, display math for long formulas, light external-context tags), is much longer per topic, and optionally includes computed worked examples.

**Architecture:** One synthesis call per topic (optional planning call first; optional code-execution worked-example call per topic) returning a sections/blocks schema; a pure `mathfmt` module and a rewritten renderer produce the body; provenance moves to a frontmatter `source_map`.

**Tech Stack:** Python 3.13, pytest, `google-genai` 2.9 (already installed; `types.ToolCodeExecution` and `max_output_tokens` verified present).

**Spec:** `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-v2-design.md` (amends `2026-10-03-summary-enhancement-design.md`).

All commands run from `ai-sandbox/academic-rag-model/` inside the worktree `.worktrees/claude-summary-enhance-v2` (branch `claude/summary-enhance-v2`). Tests: `python -m pytest <file> -q`.

**Suite state during execution:** Tasks 1-6 are a deliberate rewrite. `render.py`, `prompt.py`, `llm.py`, `enhance.py` and their tests import names that Task 1 removes from `schema.py`, so until each is replaced the full suite is red. Run only the task's own test file(s) for Tasks 1-5. The full suite (`tests/agent/summary_enhance` and `tests/agent/rag`) must be green at the end of Task 6.

## Global Constraints

- No change to `core/` or `agent/rag/rag_agent.py`.
- Unchanged from v1: `source_loader.py`, output guards, `--dry-run`, atomic write plus recovery copy, exit codes (0 ok, 1 no client, 2 input, 3 invalid after retry, 4 LLM failure, 5 write failure), `--env-file`, `PAID_GEMINI_KEY`, never run git, original guide never overwritten.
- Retain every v1 text check: control characters, label markers (tolerant regex), forged structure, newline inside inline math.
- Rendered body: no `[S#...]`, no Sources section, no HTML comments, no `Not from the textbooks` banners.
- Tags (exact strings): external paragraphs start with `*(External context)*`; worked example starts with `*(Worked example — illustrative data, not from the textbooks)*`.
- Display-math threshold: an inline `$...$` span with **more than 10** symbols becomes a `$$` block. Symbol count: each `\command` is 1; every other non-whitespace character except `{` and `}` is 1.
- Defaults: `DEFAULT_MIN_WORDS = 1400`; `MIN_SECTIONS = 3`; grounded share >= 50% of words; plan must have 3-8 topics; worked example >= 150 words and contains `$`.
- `PROMPT_VERSION = "2026-10-03.2"`; `format_version: 2` in frontmatter.
- Tests make no network or paid calls. Stage explicit paths only (never `git add -A` / `git add .`). Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Test files need unique basenames (no `__init__.py` in the test tree).

## Review Focus

- Model returns a topic title differing from the requested one only by case/spacing: accepted, and the requested spelling is rendered (Task 6).
- Math splitting must not touch `$` inside list items, table rows, blockquotes, fenced code, or existing `$$` blocks, and must be idempotent (Task 2).
- An external paragraph that starts with math, a list, or a table gets its tag on its own line, not glued to the structure (Task 3).
- Truncated response (`MAX_TOKENS`) or invalid JSON is retried and reported as an unusable response, not "model call failed" (Tasks 5, 6).
- Planning call returns duplicates, too few, or too many topics: rejected, retried once, then abort with nothing written (Tasks 1, 6).
- `--min-words 0` or negative: clear input error, no API call (Task 6).
- The v1 prompt's backslash-doubling example was itself a single-backslash string (Python escape); the v2 prompt must show two real backslashes (Task 4).

## Rulings carried into this plan

- `indexer_source_refs` and the absolute corpus `root` are no longer written (spec v2); `source_map` entries use the vault-relative `path`.
- The prompt-example backslash bug above is fixed here with a test.

---

### Task 1: Schema v2, validation v2, test fixtures

**Files:**
- Replace: `agent/summary_enhance/schema.py`
- Replace: `agent/summary_enhance/validate.py`
- Replace: `tests/agent/summary_enhance/conftest.py`
- Replace: `tests/agent/summary_enhance/test_summary_enhance_validate.py`

**Interfaces:**
- Produces (`schema.py`):
  - `BLOCK_TYPES = ("grounded", "external")`
  - dataclasses `Block(type: str, text: str, sources: list[str])`, `Section(heading: str, blocks: list[Block])`, `Topic(title: str, sections: list[Section], worked_example: str | None = None)`, `Enhanced(topics: list[Topic])`
  - `TOPIC_SCHEMA: dict`, `PLAN_SCHEMA: dict`
  - `parse_topic(data: object) -> Topic` and `parse_plan(data: object) -> list[str]` (both raise `ValueError`)
- Produces (`validate.py`):
  - constants `MIN_SECTIONS = 3`, `GROUNDED_SHARE = 0.5`, `MIN_WORKED_WORDS = 150`, `PLAN_MIN = 3`, `PLAN_MAX = 8`
  - `validate_topic(topic: Topic, valid_labels: set[str], requested_title: str, min_words: int) -> list[str]`
  - `validate_plan(titles: list[str]) -> list[str]`
  - `validate_worked_example(text: str) -> list[str]` (empty list = valid)
- Produces (`conftest.py`): helper `words(n) -> str`; `make_topic_json(title, labels=("S1",), per_section=40, sections=3, external_words=10) -> dict`; constants `WORKED_TEXT` (180 words, contains `$t=2$`), `PLAN_JSON`; function `write_guide(...)` (unchanged); fixtures `vault`, `make_llm`; class `FakeLLM` with `.model == "fake-model"`, `.calls: list[str]` (every prompt, both methods), `.kinds: list[str]` (`"structured"`/`"text"`), `.code_execution: list[bool]` (one entry per text call). Responses are consumed in call order from one queue; an `Exception` item is raised.

- [ ] **Step 1: Replace conftest and write the failing tests**

```python
# tests/agent/summary_enhance/conftest.py
import copy
import json
from types import SimpleNamespace

import pytest

CHUNKS = [
    {"chunk_id": "cam-1", "file_id": "cam", "text": "Cameron: the Wald statistic uses the unrestricted estimator."},
    {"chunk_id": "cam-2", "file_id": "cam", "text": "Cameron: the LM test uses the restricted estimator."},
    {"chunk_id": "han-1", "file_id": "han", "text": "Hansen: a Wald test of H0 uses the covariance estimator."},
    {"chunk_id": "unused-1", "file_id": "cam", "text": "Cameron: unrelated passage, not cited by the guide."},
]

REFS = [
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/cam.rag.md", "file_id": "cam",
     "chunk_id": "cam-1", "citation": "§7.2.3 Wald Test Statistic, p. 249"},
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/cam.rag.md", "file_id": "cam",
     "chunk_id": "cam-2", "citation": "§7.3.5 LM test, p. 262"},
    {"root": "STALE-ROOT", "path": "academic_notes/econ/textbooks/han.rag.md", "file_id": "han",
     "chunk_id": "han-1", "citation": "§9.10 WALD TESTS, p. 268"},
]

PLAN_JSON = {"topics": ["Wald test", "Likelihood ratio test", "LM test"]}
WORKED_TEXT = " ".join(["Compute $t=2$ here."] * 60)  # 180 words (3 per repeat), has inline math


def words(n):
    return " ".join(["word"] * n)


def make_topic_json(title, labels=("S1",), per_section=40, sections=3, external_words=10):
    secs = [{"heading": f"{title} part {i + 1}",
             "blocks": [{"type": "grounded", "text": words(per_section), "sources": list(labels)}]}
            for i in range(sections)]
    if external_words:
        secs[-1]["blocks"].append({"type": "external", "text": words(external_words), "sources": []})
    return {"title": title, "sections": secs}


def write_guide(path, refs, newline="\n"):
    front = ["---", 'title: "Wald and LM tests"', "llm_generated: true",
             "content_kind: derived_summary"]
    if refs is not None:
        front.append("indexer_source_refs: " + (refs if isinstance(refs, str)
                     else json.dumps(refs, separators=(",", ":"))))
    front.append("---")
    text = newline.join(front) + newline + newline + "# Wald and LM tests" + newline + newline + "Body text." + newline
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "hub"
    course = "econ"
    chunks_file = root / ".index" / "chunks" / f"{course}.json"
    chunks_file.parent.mkdir(parents=True)
    chunks_file.write_text(json.dumps(CHUNKS), encoding="utf-8")
    guide = root / "academic_notes" / course / "summaries" / "guide.md"
    refs = copy.deepcopy(REFS)
    write_guide(guide, refs)
    return SimpleNamespace(root=root, guide=guide, course=course, refs=refs)


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.kinds = []
        self.code_execution = []

    def _next(self):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        self.kinds.append("structured")
        return self._next()

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        self.kinds.append("text")
        self.code_execution.append(code_execution)
        return self._next()


@pytest.fixture
def make_llm():
    return lambda *responses: FakeLLM(responses)
```

```python
# tests/agent/summary_enhance/test_summary_enhance_validate.py
import pytest

from agent.summary_enhance.schema import Block, Section, Topic, parse_plan, parse_topic
from agent.summary_enhance.validate import (
    MIN_SECTIONS, validate_plan, validate_topic, validate_worked_example,
)
from conftest import WORKED_TEXT, words

LABELS = {"S1", "S2", "S3"}


def _topic(title="Wald test", g_words=40, e_words=10, sections=3, sources=("S1",), heading="Part"):
    secs = [Section(f"{heading} {i}", [Block("grounded", words(g_words), list(sources))])
            for i in range(sections)]
    if e_words:
        secs[-1].blocks.append(Block("external", words(e_words), []))
    return Topic(title, secs)


def _check(topic, min_words=100, requested="Wald test"):
    return validate_topic(topic, LABELS, requested, min_words)


def _with_text(text, kind="grounded"):
    sources = ["S1"] if kind == "grounded" else []
    return Topic("Wald test", [
        Section("A", [Block(kind, text, sources)]),
        Section("B", [Block("grounded", words(60), ["S1"])]),
        Section("C", [Block("grounded", words(60), ["S1"])]),
    ])


def test_valid_topic_passes():
    assert _check(_topic()) == []


def test_min_sections_constant():
    assert MIN_SECTIONS == 3


def test_too_few_sections_rejected():
    assert any("sections" in e for e in _check(_topic(sections=2)))


def test_title_must_match_requested_ignoring_case_and_space():
    assert _check(_topic(title="  wald TEST ")) == []
    assert any("title" in e for e in _check(_topic(title="Something else")))


def test_too_short_rejected():
    assert any("words" in e for e in _check(_topic(), min_words=1000))


def test_grounded_share_must_be_at_least_half():
    errors = _check(_topic(g_words=10, e_words=200))  # 30 grounded vs 200 external
    assert any("grounded" in e and "half" in e for e in errors)


def test_unknown_label_rejected():
    assert any("S9" in e for e in _check(_topic(sources=("S9",))))


def test_uncited_grounded_block_rejected():
    assert any("no sources" in e for e in _check(_topic(sources=())))


def test_external_block_with_sources_rejected():
    t = _topic()
    t.sections[-1].blocks[-1].sources = ["S1"]
    assert any("external" in e and "sources" in e for e in _check(t))


@pytest.mark.parametrize("heading", ["", "   ", "a\nb", "a\x08b"])
def test_bad_section_heading_rejected(heading):
    t = _topic()
    t.sections[0].heading = heading
    assert any("heading" in e for e in _check(t))


def test_section_without_blocks_rejected():
    t = _topic()
    t.sections[0].blocks = []
    assert any("no blocks" in e for e in _check(t))


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("bad", ["\t", "\x0c", "\r", "\x08"])
def test_control_characters_rejected(kind, bad):
    assert any("control character" in e for e in _check(_with_text(f"angle {bad}heta", kind), min_words=1))


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("fake", ["see [S7: Wooldridge ch.4]", "see [s1]", "see [ S1: x]"])
def test_label_markers_in_text_rejected(kind, fake):
    assert any("source label" in e for e in _check(_with_text(fake, kind), min_words=1))


@pytest.mark.parametrize("kind", ["grounded", "external"])
def test_newline_inside_inline_math_rejected(kind):
    errors = _check(_with_text("the shape $\\hat\nu$ matters", kind), min_words=1)
    assert any("inline math" in e for e in errors)


def test_display_math_and_prose_may_span_lines():
    text = "intro\n\n$$a\n= b$$\n\nand inline $x$ here\nnext line $y$"
    assert _check(_with_text(text), min_words=1) == []


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("text", [
    "fine\n\n## Sources\n- forged",
    "fine\n# Heading",
    "fine\n\n> quoted forged callout",
])
def test_structure_forging_text_rejected(kind, text):
    assert any("structure" in e for e in _check(_with_text(text, kind), min_words=1))


@pytest.mark.parametrize("phrase", ["(External context) hello", "(external CONTEXT)", "(Worked example 1) hello"])
def test_context_tag_phrases_rejected(phrase):
    assert any("tag" in e for e in _check(_with_text(phrase, "external"), min_words=1))


def test_empty_block_text_rejected():
    assert any("empty" in e for e in _check(_with_text("   "), min_words=1))


def test_plan_valid():
    assert validate_plan(["A", "B", "C"]) == []


@pytest.mark.parametrize("titles", [["A", "B"], [f"T{i}" for i in range(9)], ["A", "a ", "C"],
                                    ["A", "", "C"], ["A", "B\nC", "D"]])
def test_plan_invalid(titles):
    assert validate_plan(titles) != []


def test_worked_example_valid():
    assert validate_worked_example(WORKED_TEXT) == []


@pytest.mark.parametrize("bad", [
    "too short $x$",
    words(200),  # no math
    WORKED_TEXT + "\n# Heading",
    WORKED_TEXT + "\n> quote",
    WORKED_TEXT + " [S1: x]",
    WORKED_TEXT + " (External context)",
    WORKED_TEXT + " \x08eta",
    WORKED_TEXT + " the shape $\\hat\nu$",
])
def test_worked_example_invalid(bad):
    assert validate_worked_example(bad) != []


def test_parse_topic_roundtrip():
    data = {"title": "T", "sections": [{"heading": "H", "blocks": [
        {"type": "grounded", "text": "a", "sources": ["S1"]},
        {"type": "external", "text": "b", "sources": []}]}]}
    topic = parse_topic(data)
    assert topic.title == "T" and topic.worked_example is None
    assert topic.sections[0].blocks[0].sources == ["S1"]
    assert topic.sections[0].blocks[1].type == "external"


@pytest.mark.parametrize("bad", [
    None, [], {"title": "T"}, {"title": 1, "sections": []},
    {"title": "T", "sections": [{"heading": "H"}]},
    {"title": "T", "sections": [{"heading": "H", "blocks": [{"type": "weird", "text": "a", "sources": []}]}]},
    {"title": "T", "sections": [{"heading": "H", "blocks": [{"type": "grounded", "text": "a"}]}]},
])
def test_parse_topic_bad_shape_raises(bad):
    with pytest.raises(ValueError):
        parse_topic(bad)


def test_parse_plan():
    assert parse_plan({"topics": ["A", "B"]}) == ["A", "B"]
    for bad in (None, {"topics": "x"}, {"topics": [1]}):
        with pytest.raises(ValueError):
            parse_plan(bad)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_validate.py -q`
Expected: ImportError (`cannot import name 'Block'` / `validate_topic`).

- [ ] **Step 3: Replace the implementation**

```python
# agent/summary_enhance/schema.py
"""Typed shape of the enhancement model's JSON responses. The grounded /
external split is the whole point: grounded blocks must cite passage labels,
external blocks can never cite and are always rendered with an
(External context) tag (see render.py)."""
from __future__ import annotations

from dataclasses import dataclass

BLOCK_TYPES = ("grounded", "external")


@dataclass
class Block:
    type: str
    text: str
    sources: list[str]


@dataclass
class Section:
    heading: str
    blocks: list[Block]


@dataclass
class Topic:
    title: str
    sections: list[Section]
    worked_example: str | None = None


@dataclass
class Enhanced:
    topics: list[Topic]


TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": list(BLOCK_TYPES)},
                                "text": {"type": "string"},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["type", "text", "sources"],
                        },
                    },
                },
                "required": ["heading", "blocks"],
            },
        },
    },
    "required": ["title", "sections"],
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"topics": {"type": "array", "items": {"type": "string"}}},
    "required": ["topics"],
}


def parse_topic(data: object) -> Topic:
    """Converts one decoded topic response into dataclasses. Raises ValueError
    on any structural problem (wrong type, missing key, unknown block type)."""
    if (not isinstance(data, dict) or not isinstance(data.get("title"), str)
            or not isinstance(data.get("sections"), list)):
        raise ValueError("topic must be an object with a string 'title' and a 'sections' list")
    sections = []
    for s in data["sections"]:
        if (not isinstance(s, dict) or not isinstance(s.get("heading"), str)
                or not isinstance(s.get("blocks"), list)):
            raise ValueError("each section needs a string 'heading' and a 'blocks' list")
        blocks = []
        for b in s["blocks"]:
            if (not isinstance(b, dict) or b.get("type") not in BLOCK_TYPES
                    or not isinstance(b.get("text"), str) or not isinstance(b.get("sources"), list)
                    or not all(isinstance(x, str) for x in b["sources"])):
                raise ValueError(f"section {s['heading']!r}: malformed block")
            blocks.append(Block(b["type"], b["text"], list(b["sources"])))
        sections.append(Section(s["heading"], blocks))
    return Topic(data["title"], sections)


def parse_plan(data: object) -> list[str]:
    if (not isinstance(data, dict) or not isinstance(data.get("topics"), list)
            or not all(isinstance(t, str) for t in data["topics"])):
        raise ValueError("plan must be an object with a list of string 'topics'")
    return list(data["topics"])
```

```python
# agent/summary_enhance/validate.py
"""Checks parsed model output against the grounding and formatting contract.
Proves a cited label exists, NOT that the passage entails the claim (known
limitation, spec 'Grounding boundary')."""
from __future__ import annotations

import re

from agent.summary_enhance.schema import Topic

MIN_SECTIONS = 3
GROUNDED_SHARE = 0.5
MIN_WORKED_WORDS = 150
PLAN_MIN, PLAN_MAX = 3, 8

# Label-like marker in free text, tolerant of case/space: "[S7", "[s1", "[ S1".
# Labels belong only in a block's `sources`; a marker inside text would be a forged citation.
_LABEL_MARKER_RE = re.compile(r"\[\s*S\s*\d+", re.IGNORECASE)
# Every control character except newline (\x0a). A LaTeX command written with a
# single backslash in the model's JSON (\beta, \theta, \rho, \frac) is decoded by
# json.loads as a control character (backspace, tab, CR, form feed) followed by the
# rest of the word, silently corrupting the math (real finding, first live run,
# 2026-10-03).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x09\x0b-\x1f]")
_CONTROL_CHAR_HINT = "contains a control character (a LaTeX backslash was not doubled in the JSON)"
# \nu, \neq, \nabla ... with one backslash decode to a newline + "u"/"eq"/...;
# inline $...$ math never legitimately spans lines ($$...$$ display math may).
_INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)([^$]+?)(?<!\$)\$(?!\$)")
# A line that starts a heading or blockquote would forge document structure.
_FORGED_LINE_RE = re.compile(r"^[ \t]*[#>]", re.MULTILINE)
# The renderer adds these tags itself; model text must not contain them.
_TAG_PHRASES = ("(external context)", "(worked example")


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def _single_line(text: str) -> bool:
    return bool(text.strip()) and not re.search(r"[\x00-\x1f]", text)


def _text_errors(text: str, where: str, kind: str) -> list[str]:
    errors = []
    if not text.strip():
        errors.append(f"{where} is empty")
    if _CONTROL_CHAR_RE.search(text):
        errors.append(f"{where} {_CONTROL_CHAR_HINT}")
    if _LABEL_MARKER_RE.search(text):
        errors.append(f"{where} contains a source label in its text; "
                      + ("labels go only in 'sources'" if kind == "grounded"
                         else "external text must not cite the textbooks"))
    if any("\n" in m.group(1) for m in _INLINE_MATH_RE.finditer(text)):
        errors.append(f"{where} has a line break inside inline math "
                      "(a single-backslash \\nu, \\neq or \\nabla was decoded as a newline)")
    if _FORGED_LINE_RE.search(text):
        errors.append(f"{where} would break the document structure (a line starting with # or >)")
    low = text.lower()
    if any(p in low for p in _TAG_PHRASES):
        errors.append(f"{where} contains a context tag; the renderer adds those")
    return errors


def validate_topic(topic: Topic, valid_labels: set[str], requested_title: str, min_words: int) -> list[str]:
    errors: list[str] = []
    name = requested_title
    if _norm(topic.title) != _norm(requested_title):
        errors.append(f"topic title {topic.title!r} does not match the requested {requested_title!r}")
    if len(topic.sections) < MIN_SECTIONS:
        errors.append(f"topic {name!r} has {len(topic.sections)} sections; at least {MIN_SECTIONS} are required")
    total = grounded = 0
    for si, section in enumerate(topic.sections, 1):
        where_s = f"topic {name!r} section {si}"
        if not _single_line(section.heading):
            errors.append(f"{where_s} heading {section.heading!r} is empty or contains a line break/control character")
        if not section.blocks:
            errors.append(f"{where_s} has no blocks")
        for bi, block in enumerate(section.blocks, 1):
            where = f"{where_s} block {bi}"
            errors.extend(_text_errors(block.text, where, block.type))
            n = len(block.text.split())
            total += n
            if block.type == "grounded":
                grounded += n
                if not block.sources:
                    errors.append(f"{where} has no sources")
                for label in block.sources:
                    if label not in valid_labels:
                        errors.append(f"{where} cites unknown label {label!r}")
            elif block.sources:
                errors.append(f"{where} is external but lists sources")
    if total < min_words:
        errors.append(f"topic {name!r} has {total} words; at least {min_words} are required")
    if total and grounded < GROUNDED_SHARE * total:
        errors.append(f"topic {name!r}: at least half of the words must be in grounded blocks "
                      f"({grounded} of {total})")
    return errors


def validate_plan(titles: list[str]) -> list[str]:
    errors: list[str] = []
    if not PLAN_MIN <= len(titles) <= PLAN_MAX:
        errors.append(f"plan has {len(titles)} topics; it must have {PLAN_MIN} to {PLAN_MAX}")
    seen: set[str] = set()
    for title in titles:
        if not _single_line(title):
            errors.append(f"topic title {title!r} is empty or contains a line break/control character")
            continue
        key = _norm(title)
        if key in seen:
            errors.append(f"duplicate topic title {title!r}")
        seen.add(key)
    return errors


def validate_worked_example(text: str) -> list[str]:
    errors = _text_errors(text, "worked example", "worked")
    if len(text.split()) < MIN_WORKED_WORDS:
        errors.append(f"worked example has {len(text.split())} words; at least {MIN_WORKED_WORDS} are required")
    if "$" not in text:
        errors.append("worked example contains no math ($...$)")
    return errors
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_validate.py tests/agent/summary_enhance/test_summary_enhance_source_loader.py -q`
Expected: all pass (the loader tests still pass because `conftest.py`'s `vault` and `write_guide` are unchanged in behavior).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/schema.py agent/summary_enhance/validate.py tests/agent/summary_enhance/conftest.py tests/agent/summary_enhance/test_summary_enhance_validate.py
git commit -m "feat(summary_enhance): v2 sections/blocks schema and validation" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Display-math formatter

**Files:**
- Create: `agent/summary_enhance/mathfmt.py`
- Test: `tests/agent/summary_enhance/test_summary_enhance_mathfmt.py`

**Interfaces:**
- Produces: `SYMBOL_LIMIT = 10`; `symbol_count(formula: str) -> int`; `split_display_math(text: str) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_mathfmt.py
import pytest

from agent.summary_enhance.mathfmt import SYMBOL_LIMIT, split_display_math, symbol_count


def test_limit_constant():
    assert SYMBOL_LIMIT == 10


def test_symbol_count_commands_chars_and_braces():
    assert symbol_count(r"\hat\theta") == 2
    assert symbol_count(r"x_{1}+y") == 5
    assert symbol_count(r"\frac{a}{b}") == 3
    assert symbol_count(r"a \, b") == 3
    assert symbol_count("  a  b ") == 2


@pytest.mark.parametrize("formula,converted", [("ab+cd+ef+g", False), ("ab+cd+ef+gh", True)])
def test_threshold_is_more_than_ten(formula, converted):
    text = f"Value ${formula}$ here."
    out = split_display_math(text)
    assert (out != text) is converted


def test_long_inline_becomes_display_block():
    out = split_display_math("The statistic is $ab+cd+ef+gh$ here.")
    assert out == "The statistic is\n\n$$\nab+cd+ef+gh\n$$\n\nhere."


def test_trailing_punctuation_moves_inside_the_block():
    out = split_display_math("We get $ab+cd+ef+gh$.")
    assert out == "We get\n\n$$\nab+cd+ef+gh.\n$$"


def test_formula_at_start_has_no_leading_blank():
    out = split_display_math("$ab+cd+ef+gh$ is the statistic.")
    assert out == "$$\nab+cd+ef+gh\n$$\n\nis the statistic."


def test_two_formulas_in_one_line():
    out = split_display_math("A $ab+cd+ef+gh$ and $ij+kl+mn+op$ end.")
    assert out == "A\n\n$$\nab+cd+ef+gh\n$$\n\nand\n\n$$\nij+kl+mn+op\n$$\n\nend."


def test_short_formulas_stay_inline_in_same_line_as_long_one():
    out = split_display_math("Let $x$ be $ab+cd+ef+gh$ today.")
    assert out == "Let $x$ be\n\n$$\nab+cd+ef+gh\n$$\n\ntoday."


def test_trailing_newline_preserved_only_if_present():
    assert split_display_math("a $ab+cd+ef+gh$\n").endswith("\n")
    assert not split_display_math("a $ab+cd+ef+gh$").endswith("\n")


def test_existing_display_math_untouched():
    text = "Before\n\n$$\\sum_{i=1}^{n} x_i + y_i + z_i$$\n\nAfter\n\n$$\na = b\n$$"
    assert split_display_math(text) == text


@pytest.mark.parametrize("line", [
    "- item $ab+cd+ef+gh$",
    "* item $ab+cd+ef+gh$",
    "1. item $ab+cd+ef+gh$",
    "2) item $ab+cd+ef+gh$",
    "| a | $ab+cd+ef+gh$ |",
    "> quote $ab+cd+ef+gh$",
])
def test_list_table_blockquote_lines_untouched(line):
    assert split_display_math(line) == line


def test_fenced_code_untouched():
    text = "```\nx = '$ab+cd+ef+gh$'\n```\n\nand $ab+cd+ef+gh$ outside"
    out = split_display_math(text)
    assert "x = '$ab+cd+ef+gh$'" in out
    assert out.endswith("$$\nab+cd+ef+gh\n$$\n\noutside")


def test_idempotent():
    once = split_display_math("A $ab+cd+ef+gh$ and $ij+kl+mn+op$, end.")
    assert split_display_math(once) == once


def test_plain_text_unchanged():
    text = "No math here.\n\nSecond paragraph with $x$ only."
    assert split_display_math(text) == text
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_mathfmt.py -q`
Expected: `ModuleNotFoundError: agent.summary_enhance.mathfmt`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/mathfmt.py
"""Moves long inline formulas onto their own display-math block.

Done in the renderer (not left to the model) so the reading experience does not
depend on the model following a style instruction."""
from __future__ import annotations

import re

SYMBOL_LIMIT = 10

_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)(?<!\$)\$(?!\$)([.,;:]?)")
_SKIP_LINE_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||>)")
_FENCE_RE = re.compile(r"^\s*```")


def symbol_count(formula: str) -> int:
    """Each \\command is one symbol; so is each other non-space character except braces."""
    f = re.sub(r"\\[A-Za-z]+", "X", formula)
    f = re.sub(r"\\.", "X", f)
    return len(re.sub(r"[\s{}]", "", f))


def _convert_line(line: str) -> str:
    def repl(m: re.Match) -> str:
        formula = m.group(1).strip()
        if symbol_count(formula) <= SYMBOL_LIMIT:
            return m.group(0)
        return f"\n\n$$\n{formula}{m.group(2)}\n$$\n\n"

    return _INLINE_RE.sub(repl, line)


def split_display_math(text: str) -> str:
    out: list[str] = []
    in_fence = in_display = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        toggles = line.count("$$") % 2 == 1
        if in_display or toggles or _SKIP_LINE_RE.match(line):
            out.append(line)
            if toggles:
                in_display = not in_display
            continue
        out.append(_convert_line(line))
    result = "\n".join(out)
    result = re.sub(r"[ \t]+\n\n", "\n\n", result)
    result = re.sub(r"\n\n[ \t]+", "\n\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    if not text.endswith("\n"):
        result = result.rstrip("\n")
    if not text.startswith("\n"):
        result = result.lstrip("\n")
    return result
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_mathfmt.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/mathfmt.py tests/agent/summary_enhance/test_summary_enhance_mathfmt.py
git commit -m "feat(summary_enhance): display-math formatter for long inline formulas" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Renderer v2

**Files:**
- Replace: `agent/summary_enhance/render.py`
- Delete: `tests/agent/summary_enhance/test_summary_enhance_prompt_render.py` (via `git rm`; its prompt tests are rewritten in Task 4)
- Test: `tests/agent/summary_enhance/test_summary_enhance_render.py`

**Interfaces:**
- Consumes: `GuideInput`, `SourceChunk` (source_loader, unchanged); `Enhanced`, `Topic`, `Section`, `Block` (Task 1); `split_display_math` (Task 2); `PROMPT_VERSION` from `prompt.py` — **Task 4 replaces `prompt.py`; until then `prompt.PROMPT_VERSION` is `"2026-10-03.1"`.** To avoid an ordering dependency, `render.py` imports `PROMPT_VERSION` lazily inside `render()` and the test asserts only that `prompt_version:` is present and equals `agent.summary_enhance.prompt.PROMPT_VERSION`.
- Produces: `GENERATED_BY: str`; `EXTERNAL_TAG = "*(External context)*"`; `WORKED_TAG = "*(Worked example — illustrative data, not from the textbooks)*"`; `render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str, worked_example: bool, min_words: int) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_render.py
import json

from agent.summary_enhance.prompt import PROMPT_VERSION
from agent.summary_enhance.render import EXTERNAL_TAG, WORKED_TAG, render
from agent.summary_enhance.schema import Block, Enhanced, Section, Topic
from agent.summary_enhance.source_loader import load_guide

INTRO = ("*Study guide synthesized from the course textbooks. Passages marked (External context) "
         "or (Worked example) come from outside the textbooks.*")


def _enhanced(worked=None):
    return Enhanced([Topic("Wald test", [
        Section("Setup", [
            Block("grounded", "The Wald statistic uses the unrestricted fit.", ["S1", "S3"]),
            Block("external", "Think of it as a distance.", []),
        ]),
        Section("Statistic", [Block("grounded", "See the formula $ab+cd+ef+gh$ below.", ["S2"])]),
    ], worked_example=worked)])


def _render(vault, enhanced, **kw):
    guide = load_guide(vault.guide)
    args = dict(model="fake-model", generated_at="2026-10-03T12:00:00+00:00", worked_example=False, min_words=1400)
    args.update(kw)
    return guide, render(guide, enhanced, **args)


def _front(text):
    front, body = text.split("\n---\n\n", 1)
    return front, body


def _field(front, key):
    line = next(l for l in front.splitlines() if l.startswith(f"{key}: "))
    return line[len(key) + 2:]


def test_body_exact(vault):
    _, text = _render(vault, _enhanced(worked="We draw data. $t=2$."), worked_example=True)
    _, body = _front(text)
    assert body == (
        "# Wald and LM tests (enhanced)\n\n"
        f"{INTRO}\n\n"
        "## Wald test\n\n"
        "### Setup\n\n"
        "The Wald statistic uses the unrestricted fit.\n\n"
        "*(External context)* Think of it as a distance.\n\n"
        "### Statistic\n\n"
        "See the formula\n\n$$\nab+cd+ef+gh\n$$\n\nbelow.\n\n"
        "### Worked example\n\n"
        "*(Worked example — illustrative data, not from the textbooks)*\n\n"
        "We draw data. $t=2$.\n"
    )


def test_body_has_no_citation_machinery(vault):
    _, text = _render(vault, _enhanced())
    _, body = _front(text)
    assert "[S" not in body and "Sources" not in body and "<!--" not in body
    assert "Not from the textbooks" not in body
    assert "Worked example" not in body.split("## Wald test", 1)[1]  # no worked example requested


def test_frontmatter_fields(vault):
    guide, text = _render(vault, _enhanced())
    front, _ = _front(text)
    assert front.startswith("---\ntitle:")
    assert "llm_generated: true" in front and "content_kind: enhanced_summary" in front
    assert "format_version: 2" in front
    assert _field(front, "enhancement_model") == '"fake-model"'
    assert _field(front, "prompt_version") == json.dumps(PROMPT_VERSION)
    assert _field(front, "generated_at") == "2026-10-03T12:00:00+00:00"
    assert json.loads(_field(front, "source_summary")) == {
        "path": "academic_notes/econ/summaries/guide.md", "sha256": guide.sha256}
    assert json.loads(_field(front, "topics")) == ["Wald test"]
    assert json.loads(_field(front, "options")) == {"worked_example": False, "min_words": 1400}
    assert json.loads(_field(front, "external_context_marker")) == "(External context)"
    assert "indexer_source_refs" not in front


def test_source_map_lists_cited_chunks_with_sections(vault):
    guide, text = _render(vault, _enhanced())
    front, _ = _front(text)
    smap = json.loads(_field(front, "source_map"))
    assert [e["chunk_id"] for e in smap] == ["cam-1", "cam-2", "han-1"]
    assert smap[0] == {"chunk_id": "cam-1", "file_id": "cam",
                       "path": "academic_notes/econ/textbooks/cam.rag.md",
                       "citation": "§7.2.3 Wald Test Statistic, p. 249",
                       "used_in": ["Wald test > Setup"]}
    assert smap[1]["used_in"] == ["Wald test > Statistic"]
    assert smap[2]["used_in"] == ["Wald test > Setup"]
    assert str(guide.root) not in text  # no absolute local path anywhere


def test_source_map_only_cited_and_no_duplicate_sections(vault):
    enhanced = Enhanced([Topic("Wald test", [
        Section("A", [Block("grounded", "x", ["S2"]), Block("grounded", "y", ["S2"])]),
        Section("B", [Block("external", "z", [])]),
    ])])
    _, text = _render(vault, enhanced)
    smap = json.loads(_field(_front(text)[0], "source_map"))
    assert [e["chunk_id"] for e in smap] == ["cam-2"]
    assert smap[0]["used_in"] == ["Wald test > A"]


def test_external_tag_on_every_paragraph(vault):
    enhanced = Enhanced([Topic("T", [Section("A", [Block("external", "First.\n\nSecond.", [])])])])
    _, body = _front(_render(vault, enhanced)[1])
    assert f"{EXTERNAL_TAG} First.\n\n{EXTERNAL_TAG} Second." in body


def test_external_tag_goes_on_own_line_before_structure(vault):
    enhanced = Enhanced([Topic("T", [Section("A", [
        Block("external", "$$x+y$$ is the form", []),
        Block("external", "- a\n- b", []),
        Block("external", "| a | b |\n|---|---|\n| 1 | 2 |", []),
    ])])])
    _, body = _front(_render(vault, enhanced)[1])
    assert f"{EXTERNAL_TAG}\n\n$$x+y$$ is the form" in body
    assert f"{EXTERNAL_TAG}\n\n- a\n- b" in body
    assert f"{EXTERNAL_TAG}\n\n| a | b |" in body


def test_worked_example_options_recorded(vault):
    _, text = _render(vault, _enhanced(worked="Data."), worked_example=True, min_words=900)
    assert json.loads(_field(_front(text)[0], "options")) == {"worked_example": True, "min_words": 900}


def test_tags_constants():
    assert EXTERNAL_TAG == "*(External context)*"
    assert WORKED_TAG == "*(Worked example — illustrative data, not from the textbooks)*"
```

- [ ] **Step 2: Run to verify failure**

Run: `git rm -q tests/agent/summary_enhance/test_summary_enhance_prompt_render.py && python -m pytest tests/agent/summary_enhance/test_summary_enhance_render.py -q`
Expected: ImportError (`cannot import name 'EXTERNAL_TAG'`).

- [ ] **Step 3: Replace the implementation**

```python
# agent/summary_enhance/render.py
"""Deterministic Markdown rendering of validated enhancement output.

The body is a clean study document: no citation markers, no Sources list, no
comments. Provenance lives in the frontmatter `source_map` (chunk -> sections
that rely on it). External paragraphs carry a light (External context) tag."""
from __future__ import annotations

import json
import re

from agent.summary_enhance.mathfmt import split_display_math
from agent.summary_enhance.schema import Block, Enhanced
from agent.summary_enhance.source_loader import GuideInput

GENERATED_BY = "academic-rag-model/agent/summary_enhance/enhance.py"
EXTERNAL_TAG = "*(External context)*"
WORKED_TAG = "*(Worked example — illustrative data, not from the textbooks)*"
EXTERNAL_MARKER = "(External context)"
_INTRO = ("*Study guide synthesized from the course textbooks. Passages marked (External context) "
          "or (Worked example) come from outside the textbooks.*")
_STRUCTURE_START_RE = re.compile(r"^\s*(?:\$|[-*+]\s|\d+[.)]\s|\||>)")


def _tag_external(text: str) -> str:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    tagged = []
    for p in paragraphs:
        if _STRUCTURE_START_RE.match(p):
            tagged.append(f"{EXTERNAL_TAG}\n\n{p}")
        else:
            tagged.append(f"{EXTERNAL_TAG} {p}")
    return "\n\n".join(tagged)


def _block_text(block: Block) -> str:
    return block.text.strip() if block.type == "grounded" else _tag_external(block.text)


def render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str,
           worked_example: bool, min_words: int) -> str:
    from agent.summary_enhance.prompt import PROMPT_VERSION

    used_in: dict[str, list[str]] = {}
    for topic in enhanced.topics:
        for section in topic.sections:
            where = f"{topic.title} > {section.heading}"
            for block in section.blocks:
                if block.type != "grounded":
                    continue
                for label in block.sources:
                    places = used_in.setdefault(label, [])
                    if where not in places:
                        places.append(where)
    source_map = [
        {"chunk_id": s.chunk_id, "file_id": s.file_id, "path": s.path, "citation": s.citation,
         "used_in": used_in[s.label]}
        for s in guide.sources if s.label in used_in
    ]

    front_fields = {
        "title": json.dumps(f"{guide.title} (enhanced)", ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "enhanced_summary",
        "format_version": "2",
        "generated_by": GENERATED_BY,
        "enhancement_model": json.dumps(model),
        "prompt_version": json.dumps(PROMPT_VERSION),
        "generated_at": generated_at,
        "source_summary": json.dumps({"path": guide.rel_path, "sha256": guide.sha256}),
        "topics": json.dumps([t.title for t in enhanced.topics], ensure_ascii=False),
        "options": json.dumps({"worked_example": worked_example, "min_words": min_words}),
        "external_context_marker": json.dumps(EXTERNAL_MARKER),
        "source_map": json.dumps(source_map, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front_fields.items()) + "---\n\n"

    parts = [f"# {guide.title} (enhanced)", _INTRO]
    for topic in enhanced.topics:
        parts.append(f"## {topic.title}")
        for section in topic.sections:
            parts.append(f"### {section.heading}")
            parts.extend(_block_text(b) for b in section.blocks)
        if topic.worked_example:
            parts.append("### Worked example")
            parts.append(WORKED_TAG)
            parts.append(topic.worked_example.strip())
    body = "\n\n".join(parts) + "\n"
    return frontmatter + split_display_math(body)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_render.py tests/agent/summary_enhance/test_summary_enhance_mathfmt.py -q`
Expected: all pass. (`render.py` imports `prompt.PROMPT_VERSION` lazily; `prompt.py` is still the v1 file here and exports `PROMPT_VERSION`, so the test's comparison holds in both v1 and v2.)

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/render.py tests/agent/summary_enhance/test_summary_enhance_render.py
git commit -m "feat(summary_enhance): clean-body renderer with frontmatter source_map and external tags" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

(`git rm` in Step 2 already staged the deletion of the old prompt/render test file.)

---

### Task 4: Prompts v2

**Files:**
- Replace: `agent/summary_enhance/prompt.py`
- Test: `tests/agent/summary_enhance/test_summary_enhance_prompt.py`

**Interfaces:**
- Consumes: `GuideInput`/`SourceChunk` (source_loader); `TOPIC_SCHEMA`, `PLAN_SCHEMA` (Task 1); `MIN_SECTIONS` (Task 1 validate).
- Produces: `PROMPT_VERSION = "2026-10-03.2"`; `build_plan_prompt(guide, errors: list[str] | None = None) -> str`; `build_topic_prompt(guide, topic: str, other_topics: list[str], min_words: int, errors: list[str] | None = None) -> str`; `build_worked_example_prompt(topic_title: str, grounded_text: str, errors: list[str] | None = None) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_prompt.py
from agent.summary_enhance.prompt import (
    PROMPT_VERSION, build_plan_prompt, build_topic_prompt, build_worked_example_prompt,
)
from agent.summary_enhance.source_loader import load_guide


def test_version():
    assert PROMPT_VERSION == "2026-10-03.2"


def test_topic_prompt_contents(vault):
    guide = load_guide(vault.guide)
    prompt = build_topic_prompt(guide, "Wald test", ["LM test", "Likelihood ratio test"], 1400)
    for s in guide.sources:
        assert f"[{s.label}]" in prompt and s.text in prompt and s.citation in prompt
    assert "Body text." in prompt                      # draft guide included
    assert '"Wald test"' in prompt
    assert "LM test" in prompt and "Likelihood ratio test" in prompt   # other topics named
    assert PROMPT_VERSION in prompt
    assert '"sections"' in prompt                      # schema embedded
    assert "at least 3 sections" in prompt
    assert "1680 words" in prompt                      # 1400 * 1.2 target
    assert "half" in prompt                            # grounded share rule
    assert "ten symbols" in prompt                     # display-math instruction
    assert "(External context)" in prompt              # told not to write it


def test_topic_prompt_shows_doubled_backslashes_literally(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400)
    assert '"\\\\beta"' in prompt      # runtime text is "\\beta": two real backslashes


def test_topic_prompt_without_other_topics(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400)
    assert "Other topics" not in prompt


def test_topic_prompt_includes_retry_errors(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400,
                                errors=["topic has 900 words; at least 1400 are required"])
    assert "REJECTED" in prompt and "900 words" in prompt


def test_plan_prompt(vault):
    guide = load_guide(vault.guide)
    prompt = build_plan_prompt(guide)
    assert "3 to 8" in prompt and "Body text." in prompt and '"topics"' in prompt
    assert "REJECTED" in build_plan_prompt(guide, errors=["duplicate"])


def test_worked_example_prompt():
    prompt = build_worked_example_prompt("Wald test", "W = (r - t)' V^-1 (r - t)")
    assert '"Wald test"' in prompt and "V^-1" in prompt
    assert "code execution" in prompt and "illustrative" in prompt.lower()
    assert "REJECTED" in build_worked_example_prompt("T", "x", errors=["no math"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_prompt.py -q`
Expected: ImportError (`build_plan_prompt`) / version assertion fails.

- [ ] **Step 3: Replace the implementation**

```python
# agent/summary_enhance/prompt.py
"""Prompts for the enhancement pipeline. The contract here (grounded vs. external
blocks, formatting rules) is mirrored by schema.py/validate.py, which enforce it."""
from __future__ import annotations

import json

from agent.summary_enhance.schema import PLAN_SCHEMA, TOPIC_SCHEMA
from agent.summary_enhance.source_loader import GuideInput
from agent.summary_enhance.validate import MIN_SECTIONS, PLAN_MAX, PLAN_MIN

PROMPT_VERSION = "2026-10-03.2"

# Runtime text: "\\beta", "\\frac" (two real backslashes). A plain "\beta" here would
# teach the model the exact mistake we are warning about.
_DOUBLED_EXAMPLE = '"\\\\beta", "\\\\frac"'
_LENGTH_FACTOR = 1.2

_TOPIC_INSTRUCTIONS = """\
You are writing one topic of a thorough, standalone study guide for a graduate student.
You are given (1) an existing LLM-generated draft guide and (2) the exact textbook passages
it was built from, each tagged with a label such as [S1]. Write the topic "{topic}".
{others_line}
Length and structure
  * Write at least {target} words in total across all blocks (several pages). Depth matters
    more than brevity: state the assumptions, build the derivation step by step, explain what
    each term in the statistic measures, give the decision rule, say when the test is valid or
    breaks down, compare how the different textbooks present it, and list common pitfalls.
  * Organize the topic into at least {min_sections} sections. Each section has a short
    descriptive "heading" (one line, plain words, no markdown symbols) and ordered "blocks".
    A block is one or more paragraphs.

Two block types
  * "grounded": synthesis the textbooks support. List in "sources" the labels of every passage
    the block relies on. Merge the sources into one coherent explanation instead of summarizing
    each book in turn. Use ONLY what the passages state or directly imply. The draft guide is
    not a source: leave out of grounded blocks anything the passages do not support. Where the
    sources differ (notation, assumptions, scope) or one is silent, say so plainly. At least
    half of all your words must be in grounded blocks.
  * "external": your own additions that help a student (intuition, examples, general
    background) that the textbooks do not support. "sources" must be empty. Do not write
    "(External context)" or any tag yourself; the document adds a marker.

Text rules
  * Never write [S#] markers or any citation inside "text".
  * Do not use markdown headings (#) or blockquotes (>) in "text", and do not write the phrases
    "(External context)" or "(Worked example". Lists and tables are fine.
  * Math is LaTeX in $...$ (inline) or $$...$$ (display). Put any formula longer than about ten
    symbols in its own $$...$$ block; keep short symbols inline. This is JSON, so every LaTeX
    backslash must be doubled ({doubled}); a single backslash before b, t, f, r or n silently
    corrupts the formula.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""

_PLAN_INSTRUCTIONS = """\
Read the draft study guide and the textbook passages below. List the {lo} to {hi} distinct
topics a student should have a dedicated section on, in a sensible teaching order. Titles are
short, unique, single-line phrases.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""

_WORKED_INSTRUCTIONS = """\
Below are the explanation and formulas for the topic "{title}" from a study guide. Write a
worked numeric example showing how to compute the test statistic, apply its decision rule, and
reach a conclusion.
  * Invent a small, simple dataset (a few observations or a small table) and state it
    explicitly. Call it illustrative.
  * Use the code execution tool to do ALL the arithmetic; report only numbers you computed.
    Show each intermediate quantity (estimates, variance pieces, the statistic, the critical
    value or p-value, the decision) with a short step-by-step explanation.
  * Use the same notation as the explanation below.
  * Plain Markdown paragraphs, lists and tables only. LaTeX math in $...$ or $$...$$; put any
    formula longer than about ten symbols in its own $$...$$ block.
  * No headings (#), no blockquotes (>), no citations, and do not write the phrases
    "(External context)" or "(Worked example".
  * At least 200 words. Return only the example.

=== EXPLANATION ===
{grounded}
"""


def _passages(guide: GuideInput) -> str:
    parts = ["=== DRAFT GUIDE (not a source) ===\n" + guide.body, "=== TEXTBOOK PASSAGES ==="]
    for s in guide.sources:
        parts.append(f"[{s.label}] {s.citation} -- {s.path}\n\"\"\"\n{s.text}\n\"\"\"")
    return "\n\n".join(parts)


def _rejected(errors: list[str] | None) -> str:
    if not errors:
        return ""
    bullet = "\n".join(f"  - {e}" for e in errors)
    return "\n\n=== YOUR PREVIOUS ANSWER WAS REJECTED ===\nFix these problems and answer again:\n" + bullet


def build_plan_prompt(guide: GuideInput, errors: list[str] | None = None) -> str:
    head = f"(prompt version {PROMPT_VERSION})\n\n" + _PLAN_INSTRUCTIONS.format(
        lo=PLAN_MIN, hi=PLAN_MAX, schema=json.dumps(PLAN_SCHEMA, indent=2))
    return head + "\n" + _passages(guide) + _rejected(errors) + "\n"


def build_topic_prompt(guide: GuideInput, topic: str, other_topics: list[str], min_words: int,
                       errors: list[str] | None = None) -> str:
    others_line = ""
    if other_topics:
        listed = ", ".join(json.dumps(t) for t in other_topics)
        others_line = (f"Other topics ({listed}) get their own sections of the finished guide; "
                       "do not duplicate their content beyond what this topic needs.\n")
    head = f"(prompt version {PROMPT_VERSION})\n\n" + _TOPIC_INSTRUCTIONS.format(
        topic=topic, others_line=others_line, target=int(min_words * _LENGTH_FACTOR),
        min_sections=MIN_SECTIONS, doubled=_DOUBLED_EXAMPLE,
        schema=json.dumps(TOPIC_SCHEMA, indent=2))
    return head + "\n" + _passages(guide) + _rejected(errors) + "\n"


def build_worked_example_prompt(topic_title: str, grounded_text: str, errors: list[str] | None = None) -> str:
    return (f"(prompt version {PROMPT_VERSION})\n\n"
            + _WORKED_INSTRUCTIONS.format(title=topic_title, grounded=grounded_text)
            + _rejected(errors) + "\n")
```

Note: the test asserts `"Other topics" not in prompt` when none are given, and the template text contains `Other topics (` only inside `others_line`, so the assertion holds. The test also asserts `"at least 3 sections"`; the template line is `Organize the topic into at least {min_sections} sections`, which renders `at least 3 sections`. The assertion `"(External context)" in prompt` holds because the instructions mention it in quotes.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_prompt.py tests/agent/summary_enhance/test_summary_enhance_render.py -q`
Expected: all pass (render's `PROMPT_VERSION` assertion compares against the new constant).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/prompt.py tests/agent/summary_enhance/test_summary_enhance_prompt.py
git commit -m "feat(summary_enhance): v2 prompts (per-topic synthesis, planning, worked example) and backslash-example fix" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: LLM client v2

**Files:**
- Replace: `agent/summary_enhance/llm.py`
- Replace: `tests/agent/summary_enhance/test_summary_enhance_llm.py`

**Interfaces:**
- Consumes: `core.env.gemini_utils.call_with_retries`.
- Produces: `DEFAULT_MODEL = "gemini-3.8-flash"`; `MAX_OUTPUT_TOKENS = 32768`; `LLMClient` protocol with `model`, `generate_structured(prompt, schema) -> dict`, `generate_text(prompt, *, code_execution=False) -> str`; `GeminiClient(client, model=DEFAULT_MODEL)`. Both methods raise `ValueError` on empty, truncated (`MAX_TOKENS`), or (structured only) non-JSON output.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_llm.py
from types import SimpleNamespace

import pytest

from agent.summary_enhance.llm import DEFAULT_MODEL, MAX_OUTPUT_TOKENS, GeminiClient


class StubModels:
    def __init__(self, text, finish=None):
        self.text, self.finish, self.kwargs = text, finish, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        resp = SimpleNamespace(text=self.text)
        if self.finish is not None:
            resp.candidates = [SimpleNamespace(finish_reason=self.finish)]
        return resp


def _client(text, finish=None):
    models = StubModels(text, finish)
    return GeminiClient(SimpleNamespace(models=models), model="m-1"), models


def test_structured_returns_decoded_json_and_sends_schema_and_token_limit():
    client, models = _client('{"topics": []}')
    assert client.generate_structured("hello", {"type": "object"}) == {"topics": []}
    assert models.kwargs["model"] == "m-1" and models.kwargs["contents"] == "hello"
    cfg = models.kwargs["config"]
    assert cfg["response_mime_type"] == "application/json"
    assert cfg["response_json_schema"] == {"type": "object"}
    assert cfg["max_output_tokens"] == MAX_OUTPUT_TOKENS == 32768


def test_structured_strips_markdown_fences():
    client, _ = _client('```json\n{"topics": []}\n```')
    assert client.generate_structured("p", {}) == {"topics": []}


def test_structured_non_json_raises_value_error():
    client, _ = _client("Sure! Here is your guide.")
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


@pytest.mark.parametrize("text", [None, ""])
def test_empty_response_raises_value_error(text):
    client, _ = _client(text)
    with pytest.raises(ValueError):
        client.generate_structured("p", {})
    with pytest.raises(ValueError):
        client.generate_text("p")


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "FinishReason.MAX_TOKENS", SimpleNamespace(name="MAX_TOKENS")])
def test_truncated_response_raises_value_error(finish):
    client, _ = _client('{"topics": []}', finish=finish)
    with pytest.raises(ValueError, match="truncated"):
        client.generate_structured("p", {})
    with pytest.raises(ValueError, match="truncated"):
        client.generate_text("p")


def test_normal_finish_reason_is_fine():
    client, _ = _client('{"a": 1}', finish="STOP")
    assert client.generate_structured("p", {}) == {"a": 1}


def test_generate_text_plain():
    client, models = _client("  hello  ")
    assert client.generate_text("p") == "hello"
    cfg = models.kwargs["config"]
    assert "tools" not in cfg and "response_mime_type" not in cfg
    assert cfg["max_output_tokens"] == MAX_OUTPUT_TOKENS


def test_generate_text_with_code_execution_enables_the_tool():
    client, models = _client("42")
    assert client.generate_text("p", code_execution=True) == "42"
    tools = models.kwargs["config"]["tools"]
    assert len(tools) == 1 and tools[0].code_execution is not None


def test_model_attribute_and_default():
    assert GeminiClient(SimpleNamespace(models=None)).model == DEFAULT_MODEL
    assert "flash" in DEFAULT_MODEL
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_llm.py -q`
Expected: ImportError (`MAX_OUTPUT_TOKENS`).

- [ ] **Step 3: Replace the implementation**

```python
# agent/summary_enhance/llm.py
"""LLM boundary for the enhancement pipeline. Only GeminiClient touches the
network; everything else (and every test) depends on the LLMClient protocol."""
from __future__ import annotations

import json
import re
from typing import Protocol

from core.env.gemini_utils import call_with_retries

# Verified present on the paid key's model list 2026-10-03. Newest flash tier:
# one step above the tutor's gemini-3.6-flash, flash-priced.
DEFAULT_MODEL = "gemini-3.8-flash"
MAX_OUTPUT_TOKENS = 32768


class LLMClient(Protocol):
    model: str

    def generate_structured(self, prompt: str, schema: dict) -> dict: ...

    def generate_text(self, prompt: str, *, code_execution: bool = False) -> str: ...


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t.strip()


def _truncated(response) -> bool:
    for cand in getattr(response, "candidates", None) or []:
        reason = getattr(cand, "finish_reason", None)
        name = getattr(reason, "name", None) or str(reason or "")
        if "MAX_TOKENS" in name:
            return True
    return False


class GeminiClient:
    def __init__(self, client, model: str = DEFAULT_MODEL):
        self._client = client
        self.model = model

    def _generate(self, prompt: str, config: dict) -> str:
        response = call_with_retries(lambda: self._client.models.generate_content(
            model=self.model, contents=prompt, config=config))
        if _truncated(response):
            raise ValueError("response truncated (hit the output token limit)")
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("model returned an empty response")
        return text

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        text = self._generate(prompt, {
            "temperature": 0.2,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        })
        try:
            return json.loads(_strip_fences(text))
        except json.JSONDecodeError as err:
            raise ValueError(f"model response was not valid JSON: {err}") from err

    def generate_text(self, prompt: str, *, code_execution: bool = False) -> str:
        config: dict = {"temperature": 0.2, "max_output_tokens": MAX_OUTPUT_TOKENS}
        if code_execution:
            from google.genai import types
            config["tools"] = [types.Tool(code_execution=types.ToolCodeExecution())]
        return self._generate(prompt, config).strip()
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_llm.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/llm.py tests/agent/summary_enhance/test_summary_enhance_llm.py
git commit -m "feat(summary_enhance): text generation with code execution, token limit, truncation detection" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Orchestration, CLI, README

**Files:**
- Replace: `agent/summary_enhance/enhance.py`
- Replace: `tests/agent/summary_enhance/test_summary_enhance_cli.py`
- Modify: `agent/summary_enhance/README.md`

**Interfaces:**
- Consumes: everything from Tasks 1-5. `build_plan_prompt(guide, errors)`, `build_topic_prompt(guide, topic, other_topics, min_words, errors)`, `build_worked_example_prompt(title, grounded_text, errors)`; `validate_plan/validate_topic/validate_worked_example`; `parse_plan/parse_topic`; `PLAN_SCHEMA/TOPIC_SCHEMA`; `render(guide, enhanced, *, model, generated_at, worked_example, min_words)`; `LLMClient.generate_structured / generate_text`.
- Produces: `DEFAULT_MIN_WORDS = 1400`; `GenerationFailed(Exception)` with `.errors: list[str]`; `run(guide_path, *, topics, output=None, model=None, force=False, dry_run=False, llm=None, env_file=None, worked_example=False, min_words=DEFAULT_MIN_WORDS) -> int`; `main(argv=None) -> int` with new flags `--worked-example`, `--min-words N`. `resolve_output`, `OutputError` unchanged from v1.

Call order for `run`: `[plan]` (only if no `topics`), then for each topic in order: synthesis, then (if `worked_example`) its worked-example call. `FakeLLM` consumes responses in exactly that order.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_cli.py
import os

import pytest

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import DEFAULT_MIN_WORDS, run
from conftest import PLAN_JSON, WORKED_TEXT, make_topic_json, write_guide

TOPICS = ["Wald test", "LM test"]
MIN = 100  # words; make_topic_json defaults produce 130 words per topic


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def _topic(title, **kw):
    return make_topic_json(title, **kw)


def _go(vault, llm, **kw):
    kw.setdefault("topics", TOPICS)
    kw.setdefault("min_words", MIN)
    return run(str(vault.guide), llm=llm, **kw)


def test_default_min_words():
    assert DEFAULT_MIN_WORDS == 1400


def test_happy_path_one_call_per_topic_and_clean_output(vault, make_llm):
    original = vault.guide.read_bytes()
    llm = make_llm(_topic("Wald test", labels=("S1", "S3")), _topic("LM test", labels=("S2",)))
    assert _go(vault, llm) == 0
    assert llm.kinds == ["structured", "structured"]
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Wald test" in text and "## LM test" in text
    assert "format_version: 2" in text and "source_map:" in text and 'enhancement_model: "fake-model"' in text
    body = text.split("\n---\n\n", 1)[1]
    assert "[S" not in body and "Sources" not in body
    assert "*(External context)*" in body
    assert vault.guide.read_bytes() == original


def test_each_topic_prompt_names_the_other_topics(vault, make_llm):
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert '"Wald test"' in llm.calls[0] and "LM test" in llm.calls[0]
    assert '"LM test"' in llm.calls[1] and "Wald test" in llm.calls[1]


def test_no_topics_triggers_one_planning_call_first(vault, make_llm):
    llm = make_llm(PLAN_JSON, _topic("Wald test"), _topic("Likelihood ratio test"), _topic("LM test"))
    assert _go(vault, llm, topics=[]) == 0
    assert llm.kinds == ["structured"] * 4
    assert "3 to 8" in llm.calls[0]  # the planning prompt
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Likelihood ratio test" in text


def test_bad_plan_is_retried_then_aborts(vault, make_llm):
    llm = make_llm({"topics": ["A", "B"]}, {"topics": ["A", "B"]})
    assert _go(vault, llm, topics=[]) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_requested_title_spelling_is_rendered(vault, make_llm):
    llm = make_llm(_topic("  wald TEST "), _topic("LM test"))
    assert _go(vault, llm) == 0
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Wald test" in text and "wald TEST" not in text


def test_worked_example_off_makes_no_text_calls(vault, make_llm):
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert llm.code_execution == []
    assert "Worked example" not in _out(vault).read_text(encoding="utf-8")


def test_worked_example_on_adds_one_code_execution_call_per_topic(vault, make_llm):
    llm = make_llm(_topic("Wald test"), WORKED_TEXT, _topic("LM test"), WORKED_TEXT)
    assert _go(vault, llm, worked_example=True) == 0
    assert llm.kinds == ["structured", "text", "structured", "text"]
    assert llm.code_execution == [True, True]
    assert "Wald test" in llm.calls[1]
    text = _out(vault).read_text(encoding="utf-8")
    assert text.count("### Worked example") == 2
    assert text.count("*(Worked example — illustrative data, not from the textbooks)*") == 2
    assert '"worked_example": true' in text


def test_bad_worked_example_is_retried(vault, make_llm):
    llm = make_llm(_topic("Wald test"), "too short $x$", WORKED_TEXT, _topic("LM test"), WORKED_TEXT)
    assert _go(vault, llm, worked_example=True) == 0
    assert llm.kinds.count("text") == 3 and "REJECTED" in llm.calls[2]


def test_too_short_topic_is_retried_with_the_errors(vault, make_llm):
    short = _topic("Wald test", per_section=5)
    llm = make_llm(short, _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert len(llm.calls) == 3
    assert "REJECTED" in llm.calls[1] and "words" in llm.calls[1]


def test_persistent_validation_failure_writes_nothing(vault, make_llm):
    short = _topic("Wald test", per_section=5)
    llm = make_llm(short, short)
    assert _go(vault, llm) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_truncated_or_invalid_response_is_retried_as_unusable(vault, make_llm):
    llm = make_llm(ValueError("response truncated (hit the output token limit)"),
                   _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert "REJECTED" in llm.calls[1] and "unusable" in llm.calls[1]


def test_malformed_shape_is_retried(vault, make_llm):
    llm = make_llm({"nope": 1}, _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert len(llm.calls) == 3


def test_llm_exception_writes_nothing(vault, make_llm):
    llm = make_llm(RuntimeError("503"))
    assert _go(vault, llm) == 4
    assert not _out(vault).exists()


@pytest.mark.parametrize("bad", [0, -5])
def test_min_words_must_be_positive(vault, make_llm, bad):
    llm = make_llm()
    assert _go(vault, llm, min_words=bad) == 2
    assert llm.calls == []


def test_explicit_output_path(vault, make_llm):
    target = vault.guide.parent / "custom.md"
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test")), output=str(target)) == 0
    assert target.is_file() and not _out(vault).exists()


def test_refuses_to_overwrite_without_force(vault, make_llm):
    _out(vault).write_text("precious", encoding="utf-8")
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 2
    assert _out(vault).read_text(encoding="utf-8") == "precious" and llm.calls == []
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test")), force=True) == 0
    assert "enhanced_summary" in _out(vault).read_text(encoding="utf-8")


def test_refuses_output_equal_to_input_even_with_different_spelling(vault, make_llm):
    spelled = vault.guide.parent / ".." / "summaries" / "guide.md"
    llm = make_llm()
    assert _go(vault, llm, output=str(spelled), force=True) == 2
    assert llm.calls == []


def test_refuses_output_outside_vault(vault, tmp_path, make_llm):
    llm = make_llm()
    assert _go(vault, llm, output=str(tmp_path / "leak.md")) == 2
    assert not (tmp_path / "leak.md").exists() and llm.calls == []


def test_refuses_non_markdown_output(vault, make_llm):
    assert _go(vault, make_llm(), output=str(vault.guide.parent / "x.txt")) == 2


def test_dry_run_reports_call_count_and_makes_no_call(vault, make_llm, capsys):
    llm = make_llm()
    assert _go(vault, llm, dry_run=True) == 0
    assert llm.calls == [] and not _out(vault).exists()
    printed = capsys.readouterr().out
    assert "3 chunks" in printed and "guide.enhanced.md" in printed and "2 calls" in printed
    assert _go(vault, llm, dry_run=True, worked_example=True) == 0
    assert "4 calls" in capsys.readouterr().out
    assert _go(vault, llm, dry_run=True, topics=[]) == 0
    assert "planning call" in capsys.readouterr().out


def test_dry_run_does_not_require_an_api_key(vault, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not build a client in dry-run")
    monkeypatch.setattr(enhance, "get_gemini_client", boom)
    assert run(str(vault.guide), topics=TOPICS, dry_run=True) == 0


def test_missing_chunks_exit_before_any_llm_call(vault, make_llm):
    write_guide(vault.guide, vault.refs + [{**vault.refs[0], "chunk_id": "gone"}])
    llm = make_llm()
    assert _go(vault, llm) == 2
    assert llm.calls == []


def test_write_failure_after_paid_calls_saves_a_recovery_copy_and_no_tmp(vault, make_llm, monkeypatch):
    def locked(src, dst):
        raise PermissionError("file is open in another program")

    monkeypatch.setattr(enhance.os, "replace", locked)
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test"))) == 5
    folder = vault.guide.parent
    assert not _out(vault).exists() and not list(folder.glob("*.tmp"))
    recovered = folder / "guide.enhanced.recovered.md"
    assert recovered.is_file() and "## Wald test" in recovered.read_text(encoding="utf-8")


def test_missing_api_key_returns_1(vault, monkeypatch):
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(enhance, "get_gemini_client", lambda key_env_var="": None)
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN) == 1
    assert not _out(vault).exists()


def test_paid_key_is_the_one_requested(vault, monkeypatch):
    seen = {}
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)

    def fake_client(key_env_var="GEMINI_API_KEY"):
        seen["k"] = key_env_var
        return None

    monkeypatch.setattr(enhance, "get_gemini_client", fake_client)
    run(str(vault.guide), topics=TOPICS, min_words=MIN)
    assert seen["k"] == "PAID_GEMINI_KEY"


def test_env_file_is_loaded_for_the_paid_key(vault, tmp_path, monkeypatch):
    env_file = tmp_path / "main.env"
    env_file.write_text("PAID_GEMINI_KEY=from-env-file\n", encoding="utf-8")
    monkeypatch.delenv("PAID_GEMINI_KEY", raising=False)
    seen = {}

    def fake_client(key_env_var="GEMINI_API_KEY"):
        seen["value"] = os.environ.get(key_env_var)
        return None

    monkeypatch.setattr(enhance, "get_gemini_client", fake_client)
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN, env_file=str(env_file)) == 1
    assert seen["value"] == "from-env-file"
    monkeypatch.delenv("PAID_GEMINI_KEY", raising=False)  # dotenv wrote os.environ directly


def test_missing_env_file_is_an_input_error(vault, tmp_path):
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN, env_file=str(tmp_path / "nope.env")) == 2


def test_main_parses_args(vault, monkeypatch):
    captured = {}

    def fake_run(guide, **kw):
        captured.update(guide=guide, **kw)
        return 0

    monkeypatch.setattr(enhance, "run", fake_run)
    rc = enhance.main([str(vault.guide), "--topic", "A", "--topic", "B", "--dry-run", "--force",
                       "--output", "o.md", "--model", "m", "--env-file", "e.env",
                       "--worked-example", "--min-words", "900"])
    assert rc == 0
    assert captured["topics"] == ["A", "B"] and captured["dry_run"] and captured["force"]
    assert captured["output"] == "o.md" and captured["model"] == "m" and captured["env_file"] == "e.env"
    assert captured["worked_example"] is True and captured["min_words"] == 900


def test_main_defaults(vault, monkeypatch):
    captured = {}
    monkeypatch.setattr(enhance, "run", lambda guide, **kw: captured.update(kw) or 0)
    enhance.main([str(vault.guide)])
    assert captured["worked_example"] is False and captured["min_words"] == DEFAULT_MIN_WORDS
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_cli.py -q`
Expected: ImportError (`cannot import name 'DEFAULT_MIN_WORDS'`) or failures from the v1 `enhance.py`.

- [ ] **Step 3: Replace the implementation**

```python
# agent/summary_enhance/enhance.py
"""CLI/orchestration for the optional summary-enhancement pipeline (v2).

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" \
        --topic "Likelihood ratio test" [--worked-example] [--min-words N] \
        [--output PATH] [--model M] [--env-file PATH] [--force] [--dry-run]

Per run: an optional planning call (no --topic), one synthesis call per topic, and
(with --worked-example) one code-execution call per topic. Writes one enhanced
Markdown file next to the guide (never over the guide, never outside
<corpus>/academic_notes/). Never runs git. Specs:
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md (v1) and
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-v2-design.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from agent.summary_enhance.llm import DEFAULT_MODEL, GeminiClient, LLMClient
from agent.summary_enhance.prompt import (
    build_plan_prompt, build_topic_prompt, build_worked_example_prompt,
)
from agent.summary_enhance.render import render
from agent.summary_enhance.schema import (
    PLAN_SCHEMA, TOPIC_SCHEMA, Enhanced, Topic, parse_plan, parse_topic,
)
from agent.summary_enhance.source_loader import GuideInput, SourceError, load_guide
from agent.summary_enhance.validate import validate_plan, validate_topic, validate_worked_example
from core.env.gemini_utils import get_gemini_client, load_dotenv_override

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_INVALID, EXIT_LLM, EXIT_WRITE = 0, 1, 2, 3, 4, 5
DEFAULT_MIN_WORDS = 1400


class OutputError(Exception):
    pass


class GenerationFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def resolve_output(guide: GuideInput, output: str | None, force: bool) -> Path:
    default = guide.path.with_name(f"{guide.path.stem}.enhanced.md")
    out = Path(output).resolve() if output else default
    vault = (guide.root / "academic_notes").resolve()
    if out.suffix.lower() != ".md":
        raise OutputError(f"output must be a .md file: {out}")
    if not out.is_relative_to(vault):
        raise OutputError(f"output must be inside {vault} (generated guides stay in the private notes vault): {out}")
    if out == guide.path:
        raise OutputError("output would overwrite the original guide")
    if out.exists() and not force:
        raise OutputError(f"{out} already exists; pass --force to replace it")
    return out


def _with_retry(make_prompt, call, check):
    """Up to two attempts; the second prompt carries the first attempt's errors.
    make_prompt(errors|None) -> str; call(prompt) -> raw; check(raw) -> (result, errors).
    A ValueError from the client (truncated, empty, not JSON) counts as an unusable
    response and is retried; any other exception propagates."""
    errors: list[str] | None = None
    for _ in range(2):
        try:
            raw = call(make_prompt(errors))
        except ValueError as err:
            errors = [f"model response unusable: {err}"]
            continue
        result, errors = check(raw)
        if not errors:
            return result
    raise GenerationFailed(errors or ["no attempt succeeded"])


def _plan_topics(llm: LLMClient, guide: GuideInput) -> list[str]:
    def check(data):
        try:
            titles = parse_plan(data)
        except ValueError as err:
            return None, [f"malformed plan: {err}"]
        return titles, validate_plan(titles)

    return _with_retry(lambda errs: build_plan_prompt(guide, errs),
                       lambda p: llm.generate_structured(p, PLAN_SCHEMA), check)


def _synthesize(llm: LLMClient, guide: GuideInput, title: str, others: list[str], min_words: int) -> Topic:
    labels = {s.label for s in guide.sources}

    def check(data):
        try:
            topic = parse_topic(data)
        except ValueError as err:
            return None, [f"malformed topic: {err}"]
        errors = validate_topic(topic, labels, title, min_words)
        topic.title = title  # render the requested spelling
        return topic, errors

    return _with_retry(lambda errs: build_topic_prompt(guide, title, others, min_words, errs),
                       lambda p: llm.generate_structured(p, TOPIC_SCHEMA), check)


def _grounded_text(topic: Topic) -> str:
    return "\n\n".join(b.text.strip() for s in topic.sections for b in s.blocks if b.type == "grounded")


def _worked_example(llm: LLMClient, topic: Topic) -> str:
    grounded = _grounded_text(topic)

    def check(text):
        text = text.strip()
        return text, validate_worked_example(text)

    return _with_retry(lambda errs: build_worked_example_prompt(topic.title, grounded, errs),
                       lambda p: llm.generate_text(p, code_execution=True), check)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _save_recovery(out: Path, enhanced: Enhanced, text: str | None) -> None:
    """The paid calls already succeeded; keep their result (inside the vault, next to the
    intended output) when the final write fails, e.g. Obsidian/sync holds the file open."""
    try:
        if text is not None:
            rec = out.with_name(out.stem + ".recovered.md")
            rec.write_text(text, encoding="utf-8", newline="\n")
        else:
            rec = out.with_name(out.stem + ".recovered.json")
            rec.write_text(json.dumps(asdict(enhanced), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"The model result was saved to {rec}")
    except Exception as err:
        print(f"WARNING: could not save a recovery copy either: {err}")


def _load_env(env_file: str | None) -> None:
    """Default: ai-sandbox/.env relative to the code. A worktree has no .env
    (it is git-ignored), so --env-file lets it inherit the main checkout's."""
    if env_file is None:
        load_dotenv_override()
        return
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)


def _planned_calls(topics: list[str], worked_example: bool) -> str:
    if topics:
        n = len(topics) * (2 if worked_example else 1)
        return f"{n} calls ({len(topics)} topics{', each with a worked example' if worked_example else ''})"
    extra = " + 1 worked-example call per topic" if worked_example else ""
    return f"1 planning call + 1 call per planned topic (3-8){extra}"


def run(guide_path: str, *, topics: list[str], output: str | None = None, model: str | None = None,
        force: bool = False, dry_run: bool = False, llm: LLMClient | None = None,
        env_file: str | None = None, worked_example: bool = False,
        min_words: int = DEFAULT_MIN_WORDS) -> int:
    try:
        if min_words < 1:
            raise OutputError(f"--min-words must be a positive integer, got {min_words}")
        guide = load_guide(guide_path)
        out = resolve_output(guide, output, force)
        if env_file is not None and not Path(env_file).is_file():
            raise OutputError(f"--env-file not found: {env_file}")
    except (SourceError, OutputError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT

    if dry_run:
        sample = (build_topic_prompt(guide, topics[0], topics[1:], min_words) if topics
                  else build_plan_prompt(guide))
        print(f"DRY RUN: {len(guide.sources)} chunks, about {len(sample)} prompt characters per call, "
              f"model {model or DEFAULT_MODEL}, {_planned_calls(topics, worked_example)}, "
              f"topics {topics or '(model-chosen)'}, min {min_words} words per topic")
        print(f"DRY RUN: would write {out}")
        return EXIT_OK

    if llm is None:
        _load_env(env_file)
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return EXIT_NO_CLIENT
        llm = GeminiClient(client, model or DEFAULT_MODEL)

    try:
        titles = list(topics) or _plan_topics(llm, guide)
        done: list[Topic] = []
        for i, title in enumerate(titles):
            others = [t for j, t in enumerate(titles) if j != i]
            topic = _synthesize(llm, guide, title, others, min_words)
            if worked_example:
                topic.worked_example = _worked_example(llm, topic)
            done.append(topic)
    except GenerationFailed as err:
        print("ERROR: model output failed validation twice; nothing written:")
        for e in err.errors:
            print(f"  - {e}")
        return EXIT_INVALID
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM

    enhanced = Enhanced(done)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    text: str | None = None
    try:
        text = render(guide, enhanced, model=llm.model, generated_at=generated_at,
                      worked_example=worked_example, min_words=min_words)
        _atomic_write(out, text)
    except Exception as err:
        print(f"ERROR: could not write {out}: {err}")
        _save_recovery(out, enhanced, text)
        return EXIT_WRITE
    print(f"Wrote {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guide", help="path to an existing RAG-generated summary (.md)")
    p.add_argument("--topic", action="append", default=[],
                   help="section title; repeat per topic (omit to let the model plan the topics)")
    p.add_argument("--worked-example", action="store_true",
                   help="add a computed worked example per topic (code-execution call)")
    p.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS,
                   help=f"minimum words per topic (default {DEFAULT_MIN_WORDS})")
    p.add_argument("--output", help="explicit output .md path (must be inside academic_notes/)")
    p.add_argument("--model", help=f"Gemini model id (default {DEFAULT_MODEL})")
    p.add_argument("--env-file", help="load PAID_GEMINI_KEY from this .env (e.g. the main checkout's) "
                                      "instead of ai-sandbox/.env next to the code")
    p.add_argument("--force", action="store_true", help="replace an existing enhanced file")
    p.add_argument("--dry-run", action="store_true", help="show size/destination/call count; no API call")
    args = p.parse_args(argv)
    return run(args.guide, topics=args.topic, output=args.output, model=args.model,
               force=args.force, dry_run=args.dry_run, env_file=args.env_file,
               worked_example=args.worked_example, min_words=args.min_words)


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- replace the body of agent/summary_enhance/README.md with: -->
# summary_enhance

Optional follow-up to the RAG tutor. Takes an existing RAG-generated summary, loads the exact
indexed chunks listed in its `indexer_source_refs`, and asks a Gemini model (paid key) to write
a thorough standalone study guide: one section per topic, several sub-sections each.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --dry-run
    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --worked-example

- **Clean body, provenance in frontmatter.** No inline citations or Sources list. The frontmatter
  `source_map` lists each cited chunk (`chunk_id`, `file_id`, `path`, `citation`) with `used_in`
  (the `Topic > Section` headings that rely on it).
- **External context.** Paragraphs the textbooks do not support start with `*(External context)*`.
  Worked examples start with `*(Worked example — illustrative data, not from the textbooks)*`.
- **Display math.** Inline formulas longer than 10 symbols are moved to their own `$$` block.
- **Depth.** One synthesis call per topic; `--min-words` (default 1400) per topic, at least 3
  sections, at least half the words textbook-grounded. With no `--topic`, one planning call picks 3-8 topics.
- **Worked examples (`--worked-example`).** One extra call per topic with Gemini's code-execution
  tool, so the arithmetic is computed, not guessed.
- Output: `<guide-stem>.enhanced.md` beside the guide; `--output` to choose a path (must be under
  `<corpus>/academic_notes/`); `--force` to replace.
- Model: `gemini-3.8-flash` by default (`--model` to override). Uses `PAID_GEMINI_KEY`; from a git
  worktree (no `.env`), pass `--env-file <main checkout>/ai-sandbox/.env`.
- Never runs git. Keep outputs in the private notes vault.
- Validation checks that cited labels exist, not that a passage entails the claim, and code execution
  makes worked-example numbers real but not the prose around them: spot-check both.
- Specs: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md` (v1) and
  `...-v2-design.md`. Tests: `python -m pytest tests/agent/summary_enhance -q` (no network).
```

- [ ] **Step 4: Run to verify pass, then the whole affected suite**

Run: `python -m pytest tests/agent/summary_enhance -q`
Expected: all pass.
Run: `python -m pytest tests/agent/rag -q`
Expected: pass (unchanged code).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/enhance.py agent/summary_enhance/README.md tests/agent/summary_enhance/test_summary_enhance_cli.py
git commit -m "feat(summary_enhance): per-topic synthesis, planning, worked examples, --min-words" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Real run (manual, paid, separate from tests)

Makes paid API calls and writes a **new** file into the live private vault. Run only with the user's go-ahead for that moment. Do not overwrite the already-pushed `wald_lm_lr_tests.enhanced.md`. Never print `.env` contents.

**Files:**
- Modify only if a check below requires it: `agent/summary_enhance/llm.py`
- Create (live vault, local only): `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\econometrics\summaries\wald_lm_lr_tests.enhanced.v2.md`

- [ ] **Step 1: Availability check (code execution and token limit) on the default model**

```bash
python - <<'EOF'
from dotenv import load_dotenv
load_dotenv(r"C:\Users\theaa\ai-sandbox-master\ai-sandbox\.env", override=True)
from core.env.gemini_utils import get_gemini_client
from agent.summary_enhance.llm import GeminiClient
g = GeminiClient(get_gemini_client("PAID_GEMINI_KEY"))
print(repr(g.generate_text("Use code execution to compute 17*23 and reply with only the number.", code_execution=True)))
print(g.generate_structured('Return {"ok": true} as JSON.', {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}))
EOF
```
Expected: `'391'` and `{'ok': True}`. If the first call fails because code execution is unsupported on `gemini-3.8-flash`, or `max_output_tokens=32768` is rejected: STOP and ask the user before choosing another model or limit (the model is a user decision).

- [ ] **Step 2: Dry run**

```bash
python -m agent.summary_enhance.enhance "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\econometrics\summaries\wald_lm_lr_tests.md" --topic "Wald test" --topic "Likelihood ratio test" --topic "Lagrange multiplier (score) test" --worked-example --output "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\econometrics\summaries\wald_lm_lr_tests.enhanced.v2.md" --dry-run
```
Expected: `DRY RUN: 16 chunks, ... 6 calls (3 topics, each with a worked example) ...` and the `.v2.md` destination.

- [ ] **Step 3: Real run**

Same command without `--dry-run`, plus `--env-file "C:\Users\theaa\ai-sandbox-master\ai-sandbox\.env"`. Expected: `Wrote ...enhanced.v2.md`. Exit 3 means a call failed validation twice (nothing written): report the printed errors; do not loosen the validator to make it pass. Exit 5 means the write failed and a `.recovered.md` was saved.

- [ ] **Step 4: Review by hand and report**

Open the output. Check: about 1400+ words per topic and at least three `###` sub-sections each; no `[S`, no Sources section, no `<!--` in the body; `source_map` in the frontmatter is correct against the cited chunks (spot-check two entries' `used_in`); long formulas appear as `$$` blocks and no inline formula exceeds 10 symbols; `*(External context)*` tags are sparse and attached to genuinely external paragraphs; each worked example's numbers are independently re-computed (e.g. a quick Python re-calculation of the statistic from the stated data) and the decision follows from them; the Hansen LR gap and Cameron/Hansen differences are still called out. Report findings; any prompt tweak is a proposal (bump `PROMPT_VERSION`).

- [ ] **Step 5: Hand off**

Do not commit or push the vault from this task. Tell the user the output path, that the v1 file is untouched, and that replacing it and committing/pushing to the private vault repo are their calls. Commit any `llm.py` or prompt changes in the worktree with explicit paths. Merging `claude/summary-enhance-v2` into main is the integrator's step per `docs/WORKTREE_WORKFLOW.md`.
