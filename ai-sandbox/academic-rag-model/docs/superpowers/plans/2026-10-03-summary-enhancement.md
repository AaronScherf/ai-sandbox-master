# Summary Enhancement Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `agent/summary_enhance/` pipeline that turns an existing RAG summary plus its exact cited indexer chunks into one enhanced, per-topic study guide, with textbook-grounded synthesis structurally separated from labeled LLM elaboration.

**Architecture:** Pure, separately testable units (loader, prompt, schema/validate, render) around a tiny `LLMClient` protocol. `GeminiClient` (paid key) is the only network-touching unit; every test uses a fake. The CLI orchestrates load → guards → (dry-run | generate → validate → one retry) → render → atomic write.

**Tech Stack:** Python 3.13, pytest, `google-genai` 2.9 (already installed), stdlib only otherwise.

**Spec:** `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md`

All commands run from `ai-sandbox/academic-rag-model/` inside the worktree `.worktrees/claude-summary-enhance` (branch `claude/summary-enhance`). Tests: `python -m pytest <file> -q` (system Python 3.13 already has pytest and google-genai; no venv needed).

## Global Constraints

- No change to `core/` or `agent/rag/rag_agent.py`.
- Chunks resolved by `(file_id, chunk_id)` from `indexer_source_refs` via `core.indexer.chunk_index.load_chunks`; no similarity search.
- One enhanced `.md` per run, one `##` section per topic.
- Default output `<guide-stem>.enhanced.md` beside the guide; never overwrite the original; never overwrite an existing output without `--force`; output must lie inside `<root>/academic_notes/`.
- Real runs use `get_gemini_client("PAID_GEMINI_KEY")` from `core.env.gemini_utils`; never print `.env` contents.
- Tests make no network or paid calls.
- The tool never runs git; stage explicit paths only; never `git add -A` / `git add .`.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Test files need unique basenames (the test tree has no `__init__.py` files): use `test_summary_enhance_*.py`.

**Deviation from spec (deliberate):** the corpus root is derived from the guide's own path (the ancestor of the `academic_notes/` segment), not from each ref's stored `root`, because stored roots can be stale (e.g. recorded from a different checkout). The ref's `path`, `file_id`, `chunk_id`, `citation` are still used verbatim.

## Review Focus

- Guide with missing, empty, or malformed `indexer_source_refs` → clear error, exit before any API call (Task 2).
- Guide located outside any `academic_notes/<course>/` tree → clear error, no guessing a root (Task 2).
- Guide saved with CRLF line endings (Windows/Obsidian) still parses; `sha256` is of the raw bytes (Task 2).
- Model returns JSON wrapped in markdown fences, non-JSON, or cites a label that doesn't exist / puts `[S#]` markers inside elaboration → rejected, retried once, never written (Tasks 1, 4, 5).
- Requested topic title differing from the model's only by case/whitespace is accepted; a missing topic is not (Task 1).
- Output path equal to the input under a different spelling (case, `..`) or outside the vault → refused (Task 5).

---

### Task 1: Response schema and validation

**Files:**
- Create: `agent/summary_enhance/__init__.py` (empty)
- Create: `agent/summary_enhance/schema.py`
- Create: `agent/summary_enhance/validate.py`
- Test: `tests/agent/summary_enhance/test_summary_enhance_validate.py`

**Interfaces:**
- Produces:
  - `schema.ELABORATION_KINDS: tuple[str, ...]` = `("intuition", "example", "background")`
  - `schema.GroundedBlock(text: str, sources: list[str])`, `schema.ElaborationBlock(kind: str, text: str)`, `schema.Topic(title: str, grounded: list[GroundedBlock], elaboration: list[ElaborationBlock])`, `schema.Enhanced(topics: list[Topic])` (dataclasses)
  - `schema.RESPONSE_SCHEMA: dict` (JSON schema)
  - `schema.parse_enhanced(data: object) -> Enhanced` (raises `ValueError` on bad shape)
  - `validate.validate(enhanced: Enhanced, valid_labels: set[str], requested_topics: list[str]) -> list[str]` (empty list = valid)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_validate.py
import pytest

from agent.summary_enhance.schema import (
    ElaborationBlock, Enhanced, GroundedBlock, Topic, parse_enhanced,
)
from agent.summary_enhance.validate import validate

LABELS = {"S1", "S2", "S3"}


def _topic(title="Wald test", sources=("S1",), grounded_text="g", elab=None):
    return Topic(
        title=title,
        grounded=[GroundedBlock(grounded_text, list(sources))],
        elaboration=elab if elab is not None else [ElaborationBlock("intuition", "e")],
    )


def test_valid_passes():
    assert validate(Enhanced([_topic()]), LABELS, ["Wald test"]) == []


def test_unknown_label_rejected():
    errors = validate(Enhanced([_topic(sources=("S9",))]), LABELS, [])
    assert any("S9" in e for e in errors)


def test_uncited_grounded_block_rejected():
    errors = validate(Enhanced([_topic(sources=())]), LABELS, [])
    assert any("no sources" in e for e in errors)


def test_empty_grounded_rejected():
    t = Topic("Wald test", [], [])
    assert any("grounded" in e for e in validate(Enhanced([t]), LABELS, []))


def test_missing_requested_topic_rejected():
    errors = validate(Enhanced([_topic()]), LABELS, ["Wald test", "LM test"])
    assert any("LM test" in e for e in errors)


def test_topic_match_ignores_case_and_whitespace():
    t = _topic(title="  wald TEST ")
    assert validate(Enhanced([t]), LABELS, ["Wald test"]) == []


def test_no_topics_rejected_even_when_none_requested():
    assert validate(Enhanced([]), LABELS, []) != []


def test_label_marker_inside_elaboration_rejected():
    t = _topic(elab=[ElaborationBlock("example", "see [S1] for details")])
    assert any("elaboration" in e for e in validate(Enhanced([t]), LABELS, []))


def test_bad_elaboration_kind_rejected():
    t = _topic(elab=[ElaborationBlock("trivia", "x")])
    assert any("kind" in e for e in validate(Enhanced([t]), LABELS, []))


def test_empty_text_rejected():
    errors = validate(Enhanced([_topic(grounded_text="  ")]), LABELS, [])
    assert any("empty" in e for e in errors)


def test_parse_enhanced_roundtrip():
    data = {"topics": [{"title": "T", "grounded": [{"text": "a", "sources": ["S1"]}],
                        "elaboration": [{"kind": "intuition", "text": "b"}]}]}
    parsed = parse_enhanced(data)
    assert parsed.topics[0].grounded[0].sources == ["S1"]
    assert parsed.topics[0].elaboration[0].kind == "intuition"


@pytest.mark.parametrize("bad", [None, [], {"topics": "x"}, {"topics": [{"title": "T"}]},
                                 {"topics": [{"title": "T", "grounded": [{"text": "a"}], "elaboration": []}]}])
def test_parse_enhanced_bad_shape_raises(bad):
    with pytest.raises(ValueError):
        parse_enhanced(bad)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_validate.py -q`
Expected: collection error / `ModuleNotFoundError: agent.summary_enhance`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/schema.py
"""Typed shape of the enhancement model's JSON response. The grounded /
elaboration split is the whole point: grounded blocks must cite passage
labels, elaboration blocks can never cite and are always rendered under
a "Not from the textbooks" callout (see render.py)."""
from __future__ import annotations

from dataclasses import dataclass, field

ELABORATION_KINDS = ("intuition", "example", "background")


@dataclass
class GroundedBlock:
    text: str
    sources: list[str]


@dataclass
class ElaborationBlock:
    kind: str
    text: str


@dataclass
class Topic:
    title: str
    grounded: list[GroundedBlock] = field(default_factory=list)
    elaboration: list[ElaborationBlock] = field(default_factory=list)


@dataclass
class Enhanced:
    topics: list[Topic]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "grounded": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "sources"],
                        },
                    },
                    "elaboration": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "string", "enum": list(ELABORATION_KINDS)},
                                "text": {"type": "string"},
                            },
                            "required": ["kind", "text"],
                        },
                    },
                },
                "required": ["title", "grounded", "elaboration"],
            },
        }
    },
    "required": ["topics"],
}


def parse_enhanced(data: object) -> Enhanced:
    """Converts the model's decoded JSON into dataclasses. Raises
    ValueError on any structural problem (wrong type, missing key)."""
    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        raise ValueError("response must be an object with a 'topics' list")
    topics = []
    for t in data["topics"]:
        if not isinstance(t, dict) or not isinstance(t.get("title"), str):
            raise ValueError("each topic needs a string 'title'")
        grounded_raw, elab_raw = t.get("grounded"), t.get("elaboration")
        if not isinstance(grounded_raw, list) or not isinstance(elab_raw, list):
            raise ValueError(f"topic {t['title']!r} needs 'grounded' and 'elaboration' lists")
        grounded = []
        for g in grounded_raw:
            if (not isinstance(g, dict) or not isinstance(g.get("text"), str)
                    or not isinstance(g.get("sources"), list)
                    or not all(isinstance(s, str) for s in g["sources"])):
                raise ValueError(f"topic {t['title']!r}: malformed grounded block")
            grounded.append(GroundedBlock(g["text"], list(g["sources"])))
        elaboration = []
        for e in elab_raw:
            if (not isinstance(e, dict) or not isinstance(e.get("kind"), str)
                    or not isinstance(e.get("text"), str)):
                raise ValueError(f"topic {t['title']!r}: malformed elaboration block")
            elaboration.append(ElaborationBlock(e["kind"], e["text"]))
        topics.append(Topic(t["title"], grounded, elaboration))
    return Enhanced(topics)
```

```python
# agent/summary_enhance/validate.py
"""Checks a parsed model response against the grounding contract. Proves
a cited label exists, NOT that the passage entails the claim (known
limitation, spec 'Grounding boundary')."""
from __future__ import annotations

import re

from agent.summary_enhance.schema import ELABORATION_KINDS, Enhanced

_LABEL_MARKER_RE = re.compile(r"\[S\d+")


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def validate(enhanced: Enhanced, valid_labels: set[str], requested_topics: list[str]) -> list[str]:
    errors: list[str] = []
    if not enhanced.topics:
        errors.append("response contains no topics")
    present = {_norm(t.title) for t in enhanced.topics}
    for requested in requested_topics:
        if _norm(requested) not in present:
            errors.append(f"requested topic missing: {requested!r}")
    for topic in enhanced.topics:
        name = topic.title
        if not topic.grounded:
            errors.append(f"topic {name!r} has no grounded blocks")
        for i, block in enumerate(topic.grounded, 1):
            if not block.text.strip():
                errors.append(f"topic {name!r} grounded block {i} is empty")
            if not block.sources:
                errors.append(f"topic {name!r} grounded block {i} has no sources")
            for label in block.sources:
                if label not in valid_labels:
                    errors.append(f"topic {name!r} grounded block {i} cites unknown label {label!r}")
        for i, block in enumerate(topic.elaboration, 1):
            if block.kind not in ELABORATION_KINDS:
                errors.append(f"topic {name!r} elaboration block {i} has bad kind {block.kind!r}")
            if not block.text.strip():
                errors.append(f"topic {name!r} elaboration block {i} is empty")
            if _LABEL_MARKER_RE.search(block.text):
                errors.append(f"topic {name!r} elaboration block {i} contains a source label; "
                              "elaboration must not cite the textbooks")
    return errors
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_validate.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/__init__.py agent/summary_enhance/schema.py agent/summary_enhance/validate.py tests/agent/summary_enhance/test_summary_enhance_validate.py
git commit -m "feat(summary_enhance): response schema and grounding validation" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Source loader (guide → exact chunks)

**Files:**
- Create: `agent/summary_enhance/source_loader.py`
- Create: `tests/agent/summary_enhance/conftest.py` (shared fixtures, reused by Tasks 3–5)
- Test: `tests/agent/summary_enhance/test_summary_enhance_source_loader.py`

**Interfaces:**
- Consumes: `core.indexer.chunk_index.load_chunks(academic_hub_root: str, course: str) -> list[dict]` (chunk dicts have `chunk_id`, `file_id`, `text`).
- Produces:
  - `SourceError(Exception)`; `MissingSourcesError(SourceError)` with attribute `.missing: list[str]`
  - `SourceChunk(label: str, chunk_id: str, file_id: str, path: str, citation: str, text: str)` (frozen dataclass)
  - `GuideInput(path: Path, root: Path, course: str, title: str, body: str, sha256: str, rel_path: str, sources: list[SourceChunk])` (dataclass; `rel_path` is posix path relative to `root`)
  - `load_guide(guide_path: str | Path) -> GuideInput`
  - `locate_vault(guide_path: Path) -> tuple[Path, str]` → `(root, course)`
- Fixtures (conftest): `vault` → `SimpleNamespace(root: Path, guide: Path, course: str, refs: list[dict])`; `good_response` → dict valid for topics `"Wald test"` and `"LM test"`; `make_llm` → factory `make_llm(*responses) -> FakeLLM` (`.model == "fake-model"`, `.calls: list[str]` prompts; each response is a dict returned, or an `Exception` raised).

- [ ] **Step 1: Write conftest and failing tests**

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


def write_guide(path, refs, newline="\n", extra_front=""):
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


@pytest.fixture
def good_response():
    return {"topics": [
        {"title": "Wald test",
         "grounded": [{"text": "Both books define the Wald statistic from the unrestricted fit.",
                       "sources": ["S1", "S3"]}],
         "elaboration": [{"kind": "intuition", "text": "Think of it as a distance in estimate space."}]},
        {"title": "LM test",
         "grounded": [{"text": "The LM test needs only the restricted estimator.", "sources": ["S2"]}],
         "elaboration": []},
    ]}


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)


@pytest.fixture
def make_llm():
    return lambda *responses: FakeLLM(responses)
```

```python
# tests/agent/summary_enhance/test_summary_enhance_source_loader.py
import hashlib

import pytest

from agent.summary_enhance.source_loader import (
    MissingSourcesError, SourceError, load_guide, locate_vault,
)
from conftest import write_guide


def test_loads_chunks_in_ref_order_with_labels(vault):
    guide = load_guide(vault.guide)
    assert [s.label for s in guide.sources] == ["S1", "S2", "S3"]
    assert [s.chunk_id for s in guide.sources] == ["cam-1", "cam-2", "han-1"]
    assert guide.sources[0].text.startswith("Cameron: the Wald")
    assert guide.sources[0].citation == "§7.2.3 Wald Test Statistic, p. 249"
    assert guide.sources[2].path.endswith("han.rag.md")


def test_unreferenced_chunks_are_not_loaded(vault):
    guide = load_guide(vault.guide)
    assert "unused-1" not in {s.chunk_id for s in guide.sources}


def test_root_course_title_body_rel_path(vault):
    guide = load_guide(vault.guide)
    assert guide.root == vault.root.resolve()
    assert guide.course == "econ"
    assert guide.title == "Wald and LM tests"
    assert "Body text." in guide.body and "indexer_source_refs" not in guide.body
    assert guide.rel_path == "academic_notes/econ/summaries/guide.md"


def test_stale_ref_root_is_ignored(vault):
    # refs carry root "STALE-ROOT"; loading must still work off the guide's own path
    assert load_guide(vault.guide).sources


def test_duplicate_refs_deduped(vault):
    write_guide(vault.guide, vault.refs + [vault.refs[0]])
    assert len(load_guide(vault.guide).sources) == 3


def test_missing_chunks_all_listed(vault):
    refs = vault.refs + [{**vault.refs[0], "chunk_id": "gone-1"}, {**vault.refs[0], "chunk_id": "gone-2"}]
    write_guide(vault.guide, refs)
    with pytest.raises(MissingSourcesError) as err:
        load_guide(vault.guide)
    assert err.value.missing == ["gone-1", "gone-2"]


def test_file_id_mismatch_counts_as_missing(vault):
    refs = [{**vault.refs[0], "file_id": "WRONG"}]
    write_guide(vault.guide, refs)
    with pytest.raises(MissingSourcesError):
        load_guide(vault.guide)


@pytest.mark.parametrize("refs", [None, "[]", "not json", '{"a": 1}', '[{"chunk_id": "x"}]'])
def test_bad_refs_raise_source_error(vault, refs):
    write_guide(vault.guide, refs)
    with pytest.raises(SourceError):
        load_guide(vault.guide)


def test_no_frontmatter_raises(vault):
    vault.guide.write_text("# just a heading\n", encoding="utf-8")
    with pytest.raises(SourceError):
        load_guide(vault.guide)


def test_guide_outside_academic_notes_raises(tmp_path):
    stray = tmp_path / "scratch" / "guide.md"
    write_guide(stray, [])
    with pytest.raises(SourceError):
        load_guide(stray)


def test_locate_vault_requires_course_dir(tmp_path):
    with pytest.raises(SourceError):
        locate_vault(tmp_path / "academic_notes" / "guide.md")


def test_crlf_guide_parses_and_hash_is_raw_bytes(vault):
    write_guide(vault.guide, vault.refs, newline="\r\n")
    guide = load_guide(vault.guide)
    assert len(guide.sources) == 3
    assert guide.sha256 == hashlib.sha256(vault.guide.read_bytes()).hexdigest()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_source_loader.py -q`
Expected: `ModuleNotFoundError: agent.summary_enhance.source_loader`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/source_loader.py
"""Reads an existing RAG summary and resolves the exact indexer chunks it
cites. No similarity search: each `indexer_source_refs` entry is looked up
by (file_id, chunk_id) in the course's chunk store. The corpus root is
derived from the guide's own path (ancestor of academic_notes/) rather
than from the refs' stored `root`, which can be stale."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.indexer.chunk_index import load_chunks

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n\n?", re.DOTALL)


class SourceError(Exception):
    pass


class MissingSourcesError(SourceError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(
            "indexed chunks referenced by the guide were not found (stale index or "
            f"wrong file_id): {', '.join(missing)}"
        )


@dataclass(frozen=True)
class SourceChunk:
    label: str
    chunk_id: str
    file_id: str
    path: str
    citation: str
    text: str


@dataclass
class GuideInput:
    path: Path
    root: Path
    course: str
    title: str
    body: str
    sha256: str
    rel_path: str
    sources: list[SourceChunk]


def locate_vault(guide_path: Path) -> tuple[Path, str]:
    """Returns (corpus root, course) from .../<root>/academic_notes/<course>/.../guide.md."""
    parts = guide_path.parts
    idxs = [i for i, p in enumerate(parts) if p.lower() == "academic_notes"]
    if not idxs or len(parts) - idxs[-1] < 3:
        raise SourceError(
            f"{guide_path} is not inside <corpus>/academic_notes/<course>/; cannot locate the corpus root"
        )
    i = idxs[-1]
    return Path(*parts[:i]), parts[i + 1]


def _field(front: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*?)[ \t]*$", front, re.MULTILINE)
    return m.group(1) if m else None


def _parse_refs(raw: str | None) -> list[dict]:
    if raw is None:
        raise SourceError("guide frontmatter has no indexer_source_refs; it was not produced by the RAG report writer")
    try:
        refs = json.loads(raw)
    except json.JSONDecodeError as err:
        raise SourceError(f"indexer_source_refs is not valid JSON: {err}") from err
    if not isinstance(refs, list) or not refs:
        raise SourceError("indexer_source_refs must be a non-empty JSON list")
    for ref in refs:
        if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k]
                                               for k in ("file_id", "chunk_id", "path")):
            raise SourceError("each indexer_source_refs entry needs string file_id, chunk_id and path")
    return refs


def load_guide(guide_path: str | Path) -> GuideInput:
    path = Path(guide_path).resolve()
    if not path.is_file():
        raise SourceError(f"guide not found: {path}")
    raw_bytes = path.read_bytes()
    text = path.read_text(encoding="utf-8")  # universal newlines: CRLF -> LF
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SourceError("guide has no YAML frontmatter")
    front, body = match.group(1), text[match.end():]

    refs = _parse_refs(_field(front, "indexer_source_refs"))
    root, course = locate_vault(path)

    title_raw = _field(front, "title")
    title = path.stem
    if title_raw:
        try:
            decoded = json.loads(title_raw)
            title = decoded if isinstance(decoded, str) and decoded else title
        except json.JSONDecodeError:
            title = title_raw

    by_id = {c["chunk_id"]: c for c in load_chunks(str(root), course)}
    sources: list[SourceChunk] = []
    missing: list[str] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        key = (ref["file_id"], ref["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        chunk = by_id.get(ref["chunk_id"])
        if chunk is None or chunk.get("file_id") != ref["file_id"]:
            missing.append(ref["chunk_id"])
            continue
        sources.append(SourceChunk(
            label=f"S{len(sources) + 1}", chunk_id=ref["chunk_id"], file_id=ref["file_id"],
            path=ref["path"], citation=str(ref.get("citation", "")), text=chunk["text"],
        ))
    if missing:
        raise MissingSourcesError(missing)

    return GuideInput(
        path=path, root=root, course=course, title=title, body=body.strip("\n") + "\n",
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        rel_path=path.relative_to(root).as_posix(), sources=sources,
    )
```

Note: `label` numbering uses `len(sources) + 1`, so labels stay contiguous even though missing refs abort the run anyway.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_source_loader.py -q`
Expected: all pass. If `from conftest import write_guide` fails, the repo-root `conftest.py` puts the repo root on `sys.path`, not the test dir; fix by importing `from tests.agent.summary_enhance.conftest import write_guide` only if `tests` is importable, otherwise move `write_guide` into a `helpers.py` beside the tests and add `sys.path.insert(0, os.path.dirname(__file__))` at the top of `conftest.py` (pytest's default `prepend` import mode already inserts the test dir for rootless test modules, so the plain `conftest` import normally works).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/source_loader.py tests/agent/summary_enhance/conftest.py tests/agent/summary_enhance/test_summary_enhance_source_loader.py
git commit -m "feat(summary_enhance): resolve a guide's exact indexed chunks by chunk_id" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Prompt builder and Markdown renderer

**Files:**
- Create: `agent/summary_enhance/prompt.py`
- Create: `agent/summary_enhance/render.py`
- Test: `tests/agent/summary_enhance/test_summary_enhance_prompt_render.py`

**Interfaces:**
- Consumes: `GuideInput`, `SourceChunk` (Task 2); `Enhanced`, `RESPONSE_SCHEMA` (Task 1).
- Produces:
  - `prompt.PROMPT_VERSION: str` = `"2026-10-03.1"`
  - `prompt.build_prompt(guide: GuideInput, topics: list[str], errors: list[str] | None = None) -> str`
  - `render.GENERATED_BY: str` = `"academic-rag-model/agent/summary_enhance/enhance.py"`
  - `render.render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_prompt_render.py
import json

from agent.summary_enhance.prompt import PROMPT_VERSION, build_prompt
from agent.summary_enhance.render import render
from agent.summary_enhance.schema import parse_enhanced
from agent.summary_enhance.source_loader import load_guide


def test_prompt_contains_labels_texts_topics_version_and_schema(vault):
    guide = load_guide(vault.guide)
    prompt = build_prompt(guide, ["Wald test", "LM test"])
    for s in guide.sources:
        assert f"[{s.label}]" in prompt and s.text in prompt and s.citation in prompt
    assert "Body text." in prompt
    assert '"Wald test"' in prompt and '"LM test"' in prompt
    assert PROMPT_VERSION in prompt
    assert '"grounded"' in prompt  # schema embedded
    assert "Not from the textbooks" in prompt


def test_prompt_without_topics_asks_model_to_choose(vault):
    prompt = build_prompt(load_guide(vault.guide), [])
    assert "choose" in prompt.lower()


def test_prompt_includes_retry_errors(vault):
    prompt = build_prompt(load_guide(vault.guide), [], errors=["cites unknown label 'S9'"])
    assert "cites unknown label 'S9'" in prompt


def test_render_frontmatter_and_body(vault, good_response):
    guide = load_guide(vault.guide)
    text = render(guide, parse_enhanced(good_response), model="fake-model",
                  generated_at="2026-10-03T12:00:00+00:00")
    front, body = text.split("\n---\n\n", 1)
    assert front.startswith("---\ntitle:")
    assert "llm_generated: true" in front
    assert "content_kind: enhanced_summary" in front
    assert 'enhancement_model: "fake-model"' in front
    assert "prompt_version:" in front and "generated_at: 2026-10-03T12:00:00+00:00" in front
    src = json.loads(next(l for l in front.splitlines() if l.startswith("source_summary: "))[len("source_summary: "):])
    assert src == {"path": "academic_notes/econ/summaries/guide.md", "sha256": guide.sha256}
    refs = json.loads(next(l for l in front.splitlines() if l.startswith("indexer_source_refs: "))[len("indexer_source_refs: "):])
    assert [r["chunk_id"] for r in refs] == ["cam-1", "cam-2", "han-1"]
    assert set(refs[0]) == {"root", "path", "file_id", "chunk_id", "citation"}
    assert refs[0]["root"] == str(guide.root)
    assert json.loads(next(l for l in front.splitlines() if l.startswith("topics: "))[len("topics: "):]) == ["Wald test", "LM test"]

    expected_body = (
        "# Wald and LM tests (enhanced)\n\n"
        "> Generated by `fake-model` from the RAG summary `academic_notes/econ/summaries/guide.md`. "
        "Source-grounded text carries `[S#: citation]` markers; every callout labeled "
        "\"Not from the textbooks\" is LLM elaboration that the textbooks do not support. "
        "Check grounded claims against the cited passages.\n\n"
        "## Wald test\n\n"
        "Both books define the Wald statistic from the unrestricted fit. "
        "[S1: §7.2.3 Wald Test Statistic, p. 249; S3: §9.10 WALD TESTS, p. 268]\n\n"
        "> **Not from the textbooks — LLM elaboration (intuition):** Think of it as a distance in estimate space.\n\n"
        "## LM test\n\n"
        "The LM test needs only the restricted estimator. [S2: §7.3.5 LM test, p. 262]\n\n"
        "## Sources\n\n"
        "- S1: `academic_notes/econ/textbooks/cam.rag.md` (§7.2.3 Wald Test Statistic, p. 249; file_id: `cam`; chunk_id: `cam-1`; corpus: `{root}`)\n"
        "- S2: `academic_notes/econ/textbooks/cam.rag.md` (§7.3.5 LM test, p. 262; file_id: `cam`; chunk_id: `cam-2`; corpus: `{root}`)\n"
        "- S3: `academic_notes/econ/textbooks/han.rag.md` (§9.10 WALD TESTS, p. 268; file_id: `han`; chunk_id: `han-1`; corpus: `{root}`)\n"
    ).replace("{root}", str(guide.root))
    assert body == expected_body


def test_render_lists_only_cited_chunks(vault, good_response):
    good_response["topics"] = good_response["topics"][1:]  # only S2 cited
    guide = load_guide(vault.guide)
    text = render(guide, parse_enhanced(good_response), model="m", generated_at="t")
    assert "chunk_id: `cam-2`" in text
    assert "cam-1" not in text and "han-1" not in text


def test_render_multiline_elaboration_stays_inside_callout(vault, good_response):
    good_response["topics"][0]["elaboration"] = [
        {"kind": "example", "text": "Line one.\n\nLine three."}]
    guide = load_guide(vault.guide)
    text = render(guide, parse_enhanced(good_response), model="m", generated_at="t")
    assert ("> **Not from the textbooks — LLM elaboration (example):** Line one.\n"
            ">\n> Line three.\n") in text
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_prompt_render.py -q`
Expected: `ModuleNotFoundError: agent.summary_enhance.prompt`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/prompt.py
"""Builds the enhancement prompt. The contract here (grounded vs.
elaboration) is mirrored by schema.py/validate.py, which enforce it."""
from __future__ import annotations

import json

from agent.summary_enhance.schema import ELABORATION_KINDS, RESPONSE_SCHEMA
from agent.summary_enhance.source_loader import GuideInput

PROMPT_VERSION = "2026-10-03.1"

_INSTRUCTIONS = """\
You are improving a student's study guide. Below are (1) an existing LLM-generated
draft guide and (2) the exact textbook passages it was built from, each tagged
with a label like [S1]. Produce one coherent guide with one section per topic.

For each topic, return two separate arrays:

"grounded" -- synthesis the textbooks support.
  * Merge what the different sources say about the topic into one clear explanation;
    do not just summarize each book in turn.
  * Every block must list, in "sources", the labels of the passages it relies on.
  * Use ONLY what the passages state or directly imply. The draft guide is not a
    source: if a claim in it is not supported by a passage, leave it out of "grounded".
  * Where the sources differ (notation, assumptions, scope) or one is silent on
    something, say so plainly instead of papering over it.
  * Keep math in LaTeX with $...$ / $$...$$ delimiters.
  * Do NOT write [S#] markers inside "text"; put labels only in "sources".

"elaboration" -- your own additions that help a student: intuition, worked
examples, general background. These are NOT supported by the textbooks.
  * "kind" must be one of: {kinds}.
  * Never cite labels or attribute elaboration to the textbooks.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""


def build_prompt(guide: GuideInput, topics: list[str], errors: list[str] | None = None) -> str:
    parts = [f"(prompt version {PROMPT_VERSION})\n"]
    parts.append(_INSTRUCTIONS.format(
        kinds=", ".join(ELABORATION_KINDS), schema=json.dumps(RESPONSE_SCHEMA, indent=2)))
    if topics:
        listed = "\n".join(f"  - {json.dumps(t)}" for t in topics)
        parts.append(f"Topics (use exactly these titles, in this order, one section each):\n{listed}\n")
    else:
        parts.append("Topics: choose the natural topics covered by the draft and passages, "
                     "one section each.\n")
    parts.append("=== DRAFT GUIDE (not a source) ===\n" + guide.body)
    parts.append("=== TEXTBOOK PASSAGES ===")
    for s in guide.sources:
        parts.append(f"[{s.label}] {s.citation} -- {s.path}\n\"\"\"\n{s.text}\n\"\"\"")
    if errors:
        bullet = "\n".join(f"  - {e}" for e in errors)
        parts.append("=== YOUR PREVIOUS ANSWER WAS REJECTED ===\nFix these problems and answer again:\n" + bullet)
    return "\n\n".join(parts) + "\n"
```

```python
# agent/summary_enhance/render.py
"""Deterministic Markdown rendering of a validated Enhanced response.
Elaboration is ALWAYS rendered in a 'Not from the textbooks' callout;
the Sources list and indexer_source_refs contain only chunks actually cited."""
from __future__ import annotations

import json

from agent.summary_enhance.prompt import PROMPT_VERSION
from agent.summary_enhance.schema import ElaborationBlock, Enhanced
from agent.summary_enhance.source_loader import GuideInput

GENERATED_BY = "academic-rag-model/agent/summary_enhance/enhance.py"


def _callout(block: ElaborationBlock) -> str:
    lines = block.text.strip().splitlines() or [""]
    head = f"> **Not from the textbooks — LLM elaboration ({block.kind}):** {lines[0]}"
    rest = [f"> {line}" if line.strip() else ">" for line in lines[1:]]
    return "\n".join([head, *rest])


def render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str) -> str:
    by_label = {s.label: s for s in guide.sources}
    cited: set[str] = {lbl for t in enhanced.topics for g in t.grounded for lbl in g.sources}
    cited_sources = [s for s in guide.sources if s.label in cited]

    refs = [{"root": str(guide.root), "path": s.path, "file_id": s.file_id,
             "chunk_id": s.chunk_id, "citation": s.citation} for s in cited_sources]
    front_fields = {
        "title": json.dumps(f"{guide.title} (enhanced)", ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "enhanced_summary",
        "generated_by": GENERATED_BY,
        "enhancement_model": json.dumps(model),
        "prompt_version": json.dumps(PROMPT_VERSION),
        "generated_at": generated_at,
        "source_summary": json.dumps({"path": guide.rel_path, "sha256": guide.sha256}),
        "topics": json.dumps([t.title for t in enhanced.topics], ensure_ascii=False),
        "indexer_source_refs": json.dumps(refs, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front_fields.items()) + "---\n\n"

    out = [
        f"# {guide.title} (enhanced)",
        f"> Generated by `{model}` from the RAG summary `{guide.rel_path}`. "
        "Source-grounded text carries `[S#: citation]` markers; every callout labeled "
        "\"Not from the textbooks\" is LLM elaboration that the textbooks do not support. "
        "Check grounded claims against the cited passages.",
    ]
    for topic in enhanced.topics:
        out.append(f"## {topic.title}")
        for block in topic.grounded:
            marks = "; ".join(f"{lbl}: {by_label[lbl].citation}" for lbl in block.sources)
            out.append(f"{block.text.strip()} [{marks}]")
        for block in topic.elaboration:
            out.append(_callout(block))
    source_lines = [
        f"- {s.label}: `{s.path}` ({s.citation}; file_id: `{s.file_id}`; "
        f"chunk_id: `{s.chunk_id}`; corpus: `{guide.root}`)" for s in cited_sources
    ]
    out.append("## Sources\n\n" + "\n".join(source_lines))
    return frontmatter + "\n\n".join(out) + "\n"
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_prompt_render.py -q`
Expected: all pass. (If the exact-body test fails, diff the two strings; the renderer is the source of truth only where the spec agrees — fix the code, not the expected text, unless the expected text contradicts the spec.)

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/prompt.py agent/summary_enhance/render.py tests/agent/summary_enhance/test_summary_enhance_prompt_render.py
git commit -m "feat(summary_enhance): prompt builder and grounded/elaboration renderer" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: LLM client (Gemini, paid key)

**Files:**
- Create: `agent/summary_enhance/llm.py`
- Test: `tests/agent/summary_enhance/test_summary_enhance_llm.py`

**Interfaces:**
- Consumes: `core.env.gemini_utils.call_with_retries(fn)`; `RESPONSE_SCHEMA` shape (passed in by caller).
- Produces:
  - `llm.DEFAULT_MODEL: str` = `"gemini-3.6-pro"` (**unverified**; Task 6 step 1 confirms against the live model list before any real run, and this constant is edited then if needed)
  - `llm.LLMClient` (Protocol): attribute `model: str`; `generate_structured(prompt: str, schema: dict) -> dict`
  - `llm.GeminiClient(client, model: str = DEFAULT_MODEL)` implementing it; raises `ValueError` on non-JSON output

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_llm.py
from types import SimpleNamespace

import pytest

from agent.summary_enhance.llm import DEFAULT_MODEL, GeminiClient


class StubModels:
    def __init__(self, text):
        self.text, self.kwargs = text, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text=self.text)


def _client(text):
    models = StubModels(text)
    return GeminiClient(SimpleNamespace(models=models), model="m-1"), models


def test_returns_decoded_json_and_sends_schema():
    client, models = _client('{"topics": []}')
    out = client.generate_structured("hello", {"type": "object"})
    assert out == {"topics": []}
    assert models.kwargs["model"] == "m-1"
    assert models.kwargs["contents"] == "hello"
    cfg = models.kwargs["config"]
    assert cfg["response_mime_type"] == "application/json"
    assert cfg["response_json_schema"] == {"type": "object"}


def test_strips_markdown_fences():
    client, _ = _client('```json\n{"topics": []}\n```')
    assert client.generate_structured("p", {}) == {"topics": []}


def test_non_json_raises_value_error():
    client, _ = _client("Sure! Here is your guide.")
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


def test_empty_response_raises_value_error():
    client, _ = _client(None)
    with pytest.raises(ValueError):
        client.generate_structured("p", {})


def test_model_attribute_and_default():
    assert GeminiClient(SimpleNamespace(models=None)).model == DEFAULT_MODEL
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_llm.py -q`
Expected: `ModuleNotFoundError: agent.summary_enhance.llm`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/llm.py
"""LLM boundary for the enhancement pipeline. Only GeminiClient touches the
network; everything else (and every test) depends on the LLMClient protocol."""
from __future__ import annotations

import json
import re
from typing import Protocol

from core.env.gemini_utils import call_with_retries

# Unverified default -- confirm against the live model list before a real run
# (docs/superpowers/plans/2026-10-03-summary-enhancement.md, Task 6 step 1).
DEFAULT_MODEL = "gemini-3.6-pro"


class LLMClient(Protocol):
    model: str

    def generate_structured(self, prompt: str, schema: dict) -> dict: ...


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t.strip()


class GeminiClient:
    def __init__(self, client, model: str = DEFAULT_MODEL):
        self._client = client
        self.model = model

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        response = call_with_retries(lambda: self._client.models.generate_content(
            model=self.model, contents=prompt,
            config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        ))
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("model returned an empty response")
        try:
            return json.loads(_strip_fences(text))
        except json.JSONDecodeError as err:
            raise ValueError(f"model response was not valid JSON: {err}") from err
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_llm.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/llm.py tests/agent/summary_enhance/test_summary_enhance_llm.py
git commit -m "feat(summary_enhance): LLMClient protocol and Gemini implementation" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: CLI orchestration, output guards, README

**Files:**
- Create: `agent/summary_enhance/enhance.py`
- Create: `agent/summary_enhance/README.md`
- Test: `tests/agent/summary_enhance/test_summary_enhance_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4; `core.env.gemini_utils.load_dotenv_override()`, `get_gemini_client("PAID_GEMINI_KEY")` (returns `None` on missing key/SDK, after printing its own error).
- Produces:
  - `enhance.OutputError(Exception)`
  - `enhance.resolve_output(guide: GuideInput, output: str | None, force: bool) -> Path`
  - `enhance.run(guide_path: str, *, topics: list[str], output: str | None = None, model: str | None = None, force: bool = False, dry_run: bool = False, llm: LLMClient | None = None) -> int`
  - Exit codes: `0` ok; `1` no API client; `2` source/guard error; `3` validation failed after retry; `4` LLM call failed
  - `enhance.main(argv: list[str] | None = None) -> int` (argparse: positional `guide`; `--topic` repeatable; `--output`; `--model`; `--force`; `--dry-run`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_cli.py
import json

import pytest

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import run

TOPICS = ["Wald test", "LM test"]


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def test_happy_path_writes_default_output_and_leaves_original(vault, make_llm, good_response):
    original = vault.guide.read_bytes()
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    out = _out(vault)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "content_kind: enhanced_summary" in text and 'enhancement_model: "fake-model"' in text
    assert "## Wald test" in text and "## LM test" in text
    assert vault.guide.read_bytes() == original
    assert len(llm.calls) == 1


def test_explicit_output_path(vault, make_llm, good_response):
    target = vault.guide.parent / "custom.md"
    assert run(str(vault.guide), topics=TOPICS, output=str(target), llm=make_llm(good_response)) == 0
    assert target.is_file() and not _out(vault).exists()


def test_refuses_to_overwrite_without_force(vault, make_llm, good_response):
    _out(vault).write_text("precious", encoding="utf-8")
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 2
    assert _out(vault).read_text(encoding="utf-8") == "precious" and llm.calls == []
    assert run(str(vault.guide), topics=TOPICS, force=True, llm=make_llm(good_response)) == 0
    assert "enhanced_summary" in _out(vault).read_text(encoding="utf-8")


def test_refuses_output_equal_to_input_even_with_different_spelling(vault, make_llm, good_response):
    spelled = vault.guide.parent / ".." / "summaries" / "guide.md"
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, output=str(spelled), force=True, llm=llm) == 2
    assert llm.calls == []


def test_refuses_output_outside_vault(vault, tmp_path, make_llm, good_response):
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, output=str(tmp_path / "leak.md"), llm=llm) == 2
    assert not (tmp_path / "leak.md").exists() and llm.calls == []


def test_refuses_non_markdown_output(vault, make_llm, good_response):
    out = vault.guide.parent / "x.txt"
    assert run(str(vault.guide), topics=TOPICS, output=str(out), llm=make_llm(good_response)) == 2


def test_dry_run_makes_no_llm_call_and_writes_nothing(vault, make_llm, capsys):
    llm = make_llm()
    assert run(str(vault.guide), topics=TOPICS, dry_run=True, llm=llm) == 0
    assert llm.calls == [] and not _out(vault).exists()
    printed = capsys.readouterr().out
    assert "3 chunks" in printed and "guide.enhanced.md" in printed


def test_dry_run_does_not_require_an_api_key(vault, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not build a client in dry-run")
    monkeypatch.setattr(enhance, "get_gemini_client", boom)
    assert run(str(vault.guide), topics=TOPICS, dry_run=True) == 0


def test_missing_chunks_exit_before_any_llm_call(vault, make_llm):
    from conftest import write_guide
    write_guide(vault.guide, vault.refs + [{**vault.refs[0], "chunk_id": "gone"}])
    llm = make_llm()
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 2
    assert llm.calls == []


def test_retry_once_then_succeed(vault, make_llm, good_response):
    bad = {"topics": [{"title": "Wald test",
                       "grounded": [{"text": "x", "sources": ["S9"]}], "elaboration": []}]}
    llm = make_llm(bad, good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    assert len(llm.calls) == 2 and "unknown label 'S9'" in llm.calls[1]


def test_persistent_validation_failure_writes_nothing(vault, make_llm):
    bad = {"topics": [{"title": "Wald test",
                       "grounded": [{"text": "x", "sources": []}], "elaboration": []}]}
    llm = make_llm(bad, bad)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_unparseable_response_is_retried(vault, make_llm, good_response):
    llm = make_llm({"nope": 1}, good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    assert len(llm.calls) == 2


def test_llm_exception_writes_nothing(vault, make_llm):
    llm = make_llm(RuntimeError("503"))
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 4
    assert not _out(vault).exists()


def test_missing_api_key_returns_1(vault, monkeypatch):
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(enhance, "get_gemini_client", lambda key_env_var="": None)
    assert run(str(vault.guide), topics=TOPICS) == 1
    assert not _out(vault).exists()


def test_paid_key_is_the_one_requested(vault, monkeypatch):
    seen = {}
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(enhance, "get_gemini_client",
                        lambda key_env_var="GEMINI_API_KEY": seen.setdefault("k", key_env_var) and None)
    run(str(vault.guide), topics=TOPICS)
    assert seen["k"] == "PAID_GEMINI_KEY"


def test_main_parses_args(vault, make_llm, good_response, monkeypatch):
    captured = {}

    def fake_run(guide, **kw):
        captured.update(guide=guide, **kw)
        return 0

    monkeypatch.setattr(enhance, "run", fake_run)
    rc = enhance.main([str(vault.guide), "--topic", "A", "--topic", "B", "--dry-run", "--force",
                       "--output", "o.md", "--model", "m"])
    assert rc == 0
    assert captured["topics"] == ["A", "B"] and captured["dry_run"] and captured["force"]
    assert captured["output"] == "o.md" and captured["model"] == "m"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_cli.py -q`
Expected: `ModuleNotFoundError: agent.summary_enhance.enhance`

- [ ] **Step 3: Implement**

```python
# agent/summary_enhance/enhance.py
"""CLI/orchestration for the optional summary-enhancement pipeline.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" \
        --topic "Likelihood ratio test" [--output PATH] [--model M] [--force] [--dry-run]

Writes one enhanced Markdown file next to the guide (never over the guide,
never outside <corpus>/academic_notes/). Never runs git. Spec:
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent.summary_enhance.llm import DEFAULT_MODEL, GeminiClient, LLMClient
from agent.summary_enhance.prompt import build_prompt
from agent.summary_enhance.render import render
from agent.summary_enhance.schema import RESPONSE_SCHEMA, Enhanced, parse_enhanced
from agent.summary_enhance.source_loader import GuideInput, SourceError, load_guide
from agent.summary_enhance.validate import validate
from core.env.gemini_utils import get_gemini_client, load_dotenv_override

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_INVALID, EXIT_LLM = 0, 1, 2, 3, 4


class OutputError(Exception):
    pass


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


def _generate(llm: LLMClient, guide: GuideInput, topics: list[str]) -> tuple[Enhanced | None, list[str]]:
    """Up to two attempts; the second prompt carries the first attempt's errors.
    Returns (enhanced, []) on success or (None, errors) after the retry fails.
    LLM exceptions propagate."""
    valid_labels = {s.label for s in guide.sources}
    errors: list[str] = []
    for attempt in range(2):
        prompt = build_prompt(guide, topics, errors=errors or None)
        data = llm.generate_structured(prompt, RESPONSE_SCHEMA)
        try:
            enhanced = parse_enhanced(data)
        except ValueError as err:
            errors = [f"malformed response: {err}"]
            continue
        errors = validate(enhanced, valid_labels, topics)
        if not errors:
            return enhanced, []
    return None, errors


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def run(guide_path: str, *, topics: list[str], output: str | None = None, model: str | None = None,
        force: bool = False, dry_run: bool = False, llm: LLMClient | None = None) -> int:
    try:
        guide = load_guide(guide_path)
        out = resolve_output(guide, output, force)
    except (SourceError, OutputError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT

    if dry_run:
        prompt = build_prompt(guide, topics)
        print(f"DRY RUN: {len(guide.sources)} chunks, prompt {len(prompt)} characters, "
              f"model {model or DEFAULT_MODEL}, topics {topics or '(model-chosen)'}")
        print(f"DRY RUN: would write {out}")
        return EXIT_OK

    if llm is None:
        load_dotenv_override()
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return EXIT_NO_CLIENT
        llm = GeminiClient(client, model or DEFAULT_MODEL)

    try:
        enhanced, errors = _generate(llm, guide, topics)
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM
    if enhanced is None:
        print("ERROR: model output failed validation twice; nothing written:")
        for e in errors:
            print(f"  - {e}")
        return EXIT_INVALID

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write(out, render(guide, enhanced, model=llm.model, generated_at=generated_at))
    print(f"Wrote {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guide", help="path to an existing RAG-generated summary (.md)")
    p.add_argument("--topic", action="append", default=[], help="section title; repeat per topic")
    p.add_argument("--output", help="explicit output .md path (must be inside academic_notes/)")
    p.add_argument("--model", help=f"Gemini model id (default {DEFAULT_MODEL})")
    p.add_argument("--force", action="store_true", help="replace an existing enhanced file")
    p.add_argument("--dry-run", action="store_true", help="show size/destination; no API call")
    args = p.parse_args(argv)
    return run(args.guide, topics=args.topic, output=args.output, model=args.model,
               force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- agent/summary_enhance/README.md -->
# summary_enhance

Optional follow-up to the RAG tutor. Takes an existing RAG-generated summary,
loads the exact indexed chunks listed in its `indexer_source_refs`, and asks a
stronger Gemini model (paid key) to rewrite it as one guide with a section per
topic. Textbook-grounded synthesis (cited as `[S#: citation]`) is kept separate
from LLM elaboration, which is always rendered in a
"Not from the textbooks" callout.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --dry-run
    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test"

- Output: `<guide-stem>.enhanced.md` beside the guide; `--output` to choose a path
  (must be under `<corpus>/academic_notes/`); `--force` to replace.
- Records `enhancement_model`, `prompt_version`, `source_summary` (path + sha256),
  and exactly the cited chunks in `indexer_source_refs`.
- Never runs git. Keep outputs in the private notes vault.
- Validation checks that cited labels exist, not that a passage entails the claim:
  spot-check grounded text against the sources.
- Spec: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md`.
- Tests: `python -m pytest tests/agent/summary_enhance -q` (no network).
```

- [ ] **Step 4: Run to verify pass, then the whole new test directory**

Run: `python -m pytest tests/agent/summary_enhance -q`
Expected: all pass.

Also run the existing neighbours to confirm nothing else moved: `python -m pytest tests/agent/rag -q` (expected pass; we changed nothing there).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/enhance.py agent/summary_enhance/README.md tests/agent/summary_enhance/test_summary_enhance_cli.py
git commit -m "feat(summary_enhance): CLI orchestration with output guards and retry" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Real run on `wald_lm_lr_tests.md` (manual, separate from tests)

This task makes paid API calls and writes into the live private vault. Run it only with the user's go-ahead for that moment. The prompt is about 16 chunks plus the guide (small).

**Files:**
- Modify (only if the model check below requires it): `agent/summary_enhance/llm.py` (`DEFAULT_MODEL`)
- Create (live vault, local only): `ai-sandbox/academic-hub/academic_notes/econometrics/summaries/wald_lm_lr_tests.enhanced.md`

The live vault lives in the **original checkout**, not this worktree (it is a separate nested repo). Run the CLI from this worktree's `academic-rag-model/` but pass the guide's absolute path in the original checkout: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\econometrics\summaries\wald_lm_lr_tests.md`. The worktree has no `ai-sandbox/.env`; `load_dotenv_override()` reads `ai-sandbox/.env` relative to the code, so first confirm a key is reachable (step 1) without printing it. If it is not, ask the user how to provision it (e.g. a copy of the ignored `.env` into the worktree), do not print or commit it.

- [ ] **Step 1: Confirm the key is reachable and pick the model (no content printed)**

```bash
python - <<'EOF'
from core.env.gemini_utils import load_dotenv_override, get_gemini_client
import os
load_dotenv_override()
print("PAID_GEMINI_KEY set:", bool(os.environ.get("PAID_GEMINI_KEY")))
c = get_gemini_client("PAID_GEMINI_KEY")
if c:
    names = sorted(m.name for m in c.models.list() if "gemini" in m.name and "generateContent" in (m.supported_actions or []))
    print("\n".join(names))
EOF
```
Expected: `PAID_GEMINI_KEY set: True` and a list of model ids. Choose the strongest Pro-tier id from the list; if it differs from `DEFAULT_MODEL`, either pass `--model <id>` or update the constant, and re-run `python -m pytest tests/agent/summary_enhance/test_summary_enhance_llm.py -q`.

- [ ] **Step 2: Tiny availability call**

```bash
python - <<'EOF'
from core.env.gemini_utils import load_dotenv_override, get_gemini_client
from agent.summary_enhance.llm import GeminiClient
load_dotenv_override()
g = GeminiClient(get_gemini_client("PAID_GEMINI_KEY"), model="<chosen-id>")
print(g.generate_structured('Return {"ok": true} as JSON.', {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}))
EOF
```
Expected: `{'ok': True}`. This also confirms `response_json_schema` is accepted by the API.

- [ ] **Step 3: Dry run on the real guide**

```bash
python -m agent.summary_enhance.enhance "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub\academic_notes\econometrics\summaries\wald_lm_lr_tests.md" --topic "Wald test" --topic "Likelihood ratio test" --topic "Lagrange multiplier (score) test" --dry-run
```
Expected: `DRY RUN: 16 chunks, prompt <N> characters, ...` and the `.enhanced.md` destination. If it reports missing chunks, the index is stale for those IDs; stop and report the IDs.

- [ ] **Step 4: Real run**

Same command without `--dry-run` (add `--model <chosen-id>` if not editing the constant).
Expected: `Wrote ...wald_lm_lr_tests.enhanced.md`. Exit code 3 means validation failed twice (nothing written): report the printed errors rather than loosening the validator.

- [ ] **Step 5: Review by hand and report**

Open the output (not in terminal scrollback beyond a skim) and check: three `##` topic sections; every grounded paragraph ends with `[S#: citation]`; spot-check at least one claim per topic against the cited chunk text; elaboration appears only in "Not from the textbooks" callouts; Cameron vs. Hansen differences and the known Hansen LR gap are called out rather than filled; frontmatter has model, prompt version, sha256, and only the cited chunk refs. Report findings and any prompt tweaks as proposals (changing `PROMPT_VERSION` if the prompt changes).

- [ ] **Step 6: Hand off**

Do not commit or push the vault from this task. Tell the user the output path and that committing/pushing to the private vault repo is their call. Commit any `DEFAULT_MODEL`/prompt changes in the worktree with explicit paths. Final integration of `claude/summary-enhance` into `main` is the integrator's step per `docs/WORKTREE_WORKFLOW.md`.
