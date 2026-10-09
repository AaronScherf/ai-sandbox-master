# Study Guide Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable `agent/study_guide/` pipeline (guide spec → source plan → draft → enhance) that reproduces the recovered Wald/LR/LM recipe, and extend `summary_enhance` so a guide can be rewritten or improved from a per-topic source plan.

**Architecture:** A TOML guide spec is resolved by `plan.py` into a ledger of concrete chunks per topic (pinned sections, pinned files, bounded discovery with exclusions). `draft.py` synthesizes each topic from its accepted chunks using a frozen prompt, writing a `derived_summary` that `summary_enhance` can consume. `summary_enhance` gains per-topic source subsets (`ExtraSource`) and an `improve` mode; the `study_guide enhance` command wires a plan into it. Human review of discovered candidates is an interactive Artifact (project rule), driven by review items the plan writes.

**Tech Stack:** Python 3.13, stdlib `tomllib`, pytest, `google-genai` (already installed), existing `core.indexer` and `agent.summary_enhance`.

**Spec:** `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`; recovered recipe: `docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`.

All commands run from `ai-sandbox/academic-rag-model/` inside the worktree `.worktrees/claude-study-guide-spec` (branch `claude/study-guide-spec`). Tests: `python -m pytest <file> -q`.

## Global Constraints

- `agent/rag/rag_agent.py` and `core/` are not modified.
- Guide specs are code configuration: they live in the repo under `guide_specs/<course>/<guide_id>.toml` and contain topics, instructions, section labels and source rules, never source text. Generated outputs and plans go to the vault under `<corpus>/academic_notes/<course>/`.
- Plans: `academic_notes/<course>/guide_plans/<id>.plan.json` (ids, paths, citations, scores, rules; no passage text) and `<id>.review.json` (review items for the Artifact).
- Human decisions use an interactive Artifact, never a hand-edited file: the pipeline writes review items and applies decisions; it never asks the user to edit the plan.
- Defaults: `DEFAULT_MODEL = "gemini-3.8-flash"` for both stages; section/file rule `max` default 12; discover `max` default 8 in the baseline-new-material spec but the loader default is 12; `top_k = 180`, `file_top_k = 80`; draft temperature 0.2 (via `GeminiClient`).
- Section rules build the search text as `f"{Course} textbook: {query}. {instruction}"` where `Course = spec.course.capitalize()`.
- Label matching: `heading-prefix` (default; dot-boundary prefix on any `heading_path` element's leading number, falling back to the citation substring when a chunk has no `heading_path`) or `citation-substring` (legacy).
- Outputs stay under `<corpus>/academic_notes/`; no overwrite without `--force`; no git; paid key `PAID_GEMINI_KEY` only (`--env-file` for worktrees); secrets never printed; tests make no network or paid calls.
- Draft frontmatter does not store the absolute corpus root.
- Stage files with explicit paths (never `git add -A` / `git add .`). Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Test files need unique basenames (no `__init__.py` in the test tree): `test_study_guide_*.py`. The study_guide tests share helpers through `tests/agent/study_guide/sg_helpers.py` (imported as `sg_helpers`), not through `from conftest import` (a second `conftest` module would collide with summary_enhance's).

## Rulings carried into this plan

- Spec said `summary_enhance` gains `--source-plan`. Implemented as `enhance.run(..., extra_sources=[ExtraSource, ...], mode=...)` (no study_guide import inside summary_enhance); the `--source-plan` flag lives on `python -m agent.study_guide enhance`. `summary_enhance`'s own CLI gains only `--mode`.
- `[models]` can be overridden per run with `--model` on `draft` and `enhance` (so the B1 and B2 runs share one spec).
- `run` is minimal: `plan`, then `draft --accept-unreviewed` only with `--yes`.

## Review Focus

- Label matching: `7.3` must not match `7.30`, `9.1` must not match `9.10` (heading-prefix); an unnumbered child heading under a numbered parent (`7.3.1` > "Likelihood Ratio Test") must match its parent's label (Task 2).
- A plan whose chunks vanished or whose file content changed is rejected with a clear message before any paid call (Tasks 2, 5).
- Discovered candidates are never silently used: `pending` entries block `draft` and `enhance` unless `--accept-unreviewed` (Tasks 3, 5, 8).
- `exclude_guide` pointing at a missing file or a file without a chunk list errors instead of silently excluding nothing (Task 2).
- A topic whose rules resolve to zero passages fails the plan and names the topic (Task 2).
- A topic that cites another topic's chunk is rejected in `enhance` (per-topic label sets) (Task 7).
- TOML typos (unknown keys, wrong types) are rejected, not ignored (Task 1).
- An existing output is never overwritten without `--force`, and outputs outside the vault are refused (Tasks 4, 5).

---

### Task 1: Guide spec loader

**Files:**
- Create: `agent/study_guide/__init__.py` (empty)
- Create: `agent/study_guide/spec.py`
- Create: `tests/agent/study_guide/sg_helpers.py` (stub now; filled in Task 2)
- Test: `tests/agent/study_guide/test_study_guide_spec.py`

**Interfaces:**
- Produces:
  - `SpecError(Exception)`
  - `SourceRule(kind, book="", labels=(), exclude_labels=(), file="", query="", max=12, doc_types=("textbook",), exclude_guide="", min_score=0.0, max_per_file=0)` (frozen dataclass)
  - `TopicSpec(title, instruction, sources: tuple[SourceRule, ...])`, `ComparisonSpec(title, instruction, from_topics: tuple[str, ...], take=3)`, `NoteSpec(heading, body)`
  - `GuideSpec(id, title, course, draft_model, enhance_model, prompt, label_match, top_k, file_top_k, notes, topics, comparisons, path, sha256)`
  - `DEFAULT_MODEL = "gemini-3.8-flash"`; `load_spec(path: str | Path) -> GuideSpec`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/sg_helpers.py
"""Shared helpers for the study_guide tests (imported as `sg_helpers`)."""
```

```python
# tests/agent/study_guide/test_study_guide_spec.py
import hashlib

import pytest

from agent.study_guide.spec import DEFAULT_MODEL, SpecError, load_spec

MINIMAL = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"
"""

FULL = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[models]
draft = "gemini-3.1-flash-lite"
enhance = "gemini-3.8-flash"

[draft]
prompt = "guide_v1"
label_match = "citation-substring"
top_k = 100
file_top_k = 40

[[note]]
heading = "A note"
body = "Some static text."

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.3.1", "7.3.2"]
  exclude_labels = ["7.3.5"]
  query = "wald"
  max = 5

  [[topic.source]]
  kind = "file"
  file = "class_2024/Slides/slidesASYM.md"
  query = "wald statistic"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "wald"
  doc_types = ["textbook", "ta_notes"]
  exclude_guide = "academic_notes/econ/summaries/old.md"
  max = 8
  min_score = 0.72
  max_per_file = 2

[[topic]]
title = "Topic B"
instruction = "Explain B."

  [[topic.source]]
  kind = "file"
  file = "abc123"

[[comparison]]
title = "Compare"
instruction = "Compare A and B."
from = ["Topic A", "Topic B"]
take = 2
"""


def _write(tmp_path, text):
    p = tmp_path / "g.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_minimal_spec_gets_defaults(tmp_path):
    spec = load_spec(_write(tmp_path, MINIMAL))
    assert (spec.id, spec.title, spec.course) == ("demo_guide", "Demo", "econ")
    assert spec.draft_model == spec.enhance_model == DEFAULT_MODEL == "gemini-3.8-flash"
    assert (spec.prompt, spec.label_match, spec.top_k, spec.file_top_k) == ("tutor_v1", "heading-prefix", 180, 80)
    rule = spec.topics[0].sources[0]
    assert (rule.kind, rule.book, rule.labels, rule.exclude_labels, rule.max) == ("section", "Cameron", ("7.2",), (), 12)
    assert spec.notes == () and spec.comparisons == ()


def test_sha256_and_path_recorded(tmp_path):
    p = _write(tmp_path, MINIMAL)
    spec = load_spec(p)
    assert spec.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert spec.path == str(p)


def test_full_spec_parses_every_section(tmp_path):
    spec = load_spec(_write(tmp_path, FULL))
    assert spec.draft_model == "gemini-3.1-flash-lite" and spec.enhance_model == "gemini-3.8-flash"
    assert (spec.prompt, spec.label_match, spec.top_k, spec.file_top_k) == ("guide_v1", "citation-substring", 100, 40)
    assert [(n.heading, n.body) for n in spec.notes] == [("A note", "Some static text.")]
    section, file_rule, discover = spec.topics[0].sources
    assert (section.labels, section.exclude_labels, section.max) == (("7.3.1", "7.3.2"), ("7.3.5",), 5)
    assert (file_rule.kind, file_rule.file, file_rule.query, file_rule.max) == ("file", "class_2024/Slides/slidesASYM.md", "wald statistic", 6)
    assert (discover.doc_types, discover.exclude_guide, discover.max, discover.min_score, discover.max_per_file) == (
        ("textbook", "ta_notes"), "academic_notes/econ/summaries/old.md", 8, 0.72, 2)
    assert spec.topics[1].sources[0].query == ""
    cmp_ = spec.comparisons[0]
    assert (cmp_.title, cmp_.from_topics, cmp_.take) == ("Compare", ("Topic A", "Topic B"), 2)


@pytest.mark.parametrize("old,new,fragment", [
    ('id = "demo_guide"\n', "", "missing 'id'"),
    ('id = "demo_guide"', 'id = "Bad Id"', "id"),
    ('course = "econ"', 'course = "econ"\nbogus = 1', "unknown key"),
    ('instruction = "Explain A."', 'instruction = "Explain A."\nextra = 1', "unknown key"),
    ('kind = "section"', 'kind = "weird"', "kind"),
    ('labels = ["7.2"]', "", "labels"),
    ('book = "Cameron"\n', "", "book"),
    ('query = "wald"', 'query = "wald"\nmax = 0', "max"),
    ('query = "wald"', 'query = ""', "query"),
])
def test_invalid_specs_rejected(tmp_path, old, new, fragment):
    assert old in MINIMAL
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, MINIMAL.replace(old, new)))


@pytest.mark.parametrize("extra,fragment", [
    ('\n[bogus]\nx = 1\n', "unknown"),
    ('\n[draft]\nprompt = "nope"\n', "prompt"),
    ('\n[draft]\nlabel_match = "nope"\n', "label_match"),
    ('\n[draft]\ntop_k = 0\n', "top_k"),
    ('\n[models]\ndraft = ""\n', "draft"),
    ('\n[[comparison]]\ntitle = "C"\ninstruction = "x"\nfrom = ["Nope"]\n', "Nope"),
    ('\n[[comparison]]\ntitle = "C"\ninstruction = "x"\nfrom = ["Topic A"]\ntake = 0\n', "take"),
    ('\n[[comparison]]\ntitle = "Topic A"\ninstruction = "x"\nfrom = ["Topic A"]\n', "duplicate"),
])
def test_invalid_extra_tables_rejected(tmp_path, extra, fragment):
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, MINIMAL + extra))


def test_no_topics_rejected(tmp_path):
    head = MINIMAL.split("[[topic]]")[0]
    with pytest.raises(SpecError, match="at least one topic"):
        load_spec(_write(tmp_path, head))


def test_topic_without_sources_rejected(tmp_path):
    text = MINIMAL.split("  [[topic.source]]")[0]
    with pytest.raises(SpecError, match="source"):
        load_spec(_write(tmp_path, text))


def test_duplicate_topic_titles_rejected(tmp_path):
    topic = MINIMAL.split("[[topic]]")[1]
    with pytest.raises(SpecError, match="duplicate"):
        load_spec(_write(tmp_path, MINIMAL + "\n[[topic]]" + topic))


@pytest.mark.parametrize("rule,fragment", [
    ('kind = "file"\n  query = "x"', "file"),
    ('kind = "discover"', "query"),
    ('kind = "discover"\n  query = "x"\n  min_score = 1.5', "min_score"),
    ('kind = "discover"\n  query = "x"\n  doc_types = []', "doc_types"),
    ('kind = "section"\n  book = "B"\n  labels = ["7"]\n  query = "q"\n  file = "x"', "unknown key"),
])
def test_rule_specific_validation(tmp_path, rule, fragment):
    text = MINIMAL.split("  [[topic.source]]")[0] + "  [[topic.source]]\n  " + rule + "\n"
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, text))


def test_invalid_toml_rejected(tmp_path):
    with pytest.raises(SpecError, match="TOML"):
        load_spec(_write(tmp_path, "this is = = not toml"))


def test_missing_file_rejected(tmp_path):
    with pytest.raises(SpecError, match="not found"):
        load_spec(tmp_path / "nope.toml")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_spec.py -q`
Expected: `ModuleNotFoundError: agent.study_guide` (collection error).

- [ ] **Step 3: Implement**

```python
# agent/study_guide/spec.py
"""Guide spec: the declarative description of one study guide (topics, source rules,
per-stage models, prompt). Specs are code configuration, not study content: they hold
topics, instructions and section labels, never source text. Format: TOML."""
from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
VALID_PROMPTS = ("tutor_v1", "guide_v1")
VALID_LABEL_MATCH = ("heading-prefix", "citation-substring")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")


class SpecError(Exception):
    pass


@dataclass(frozen=True)
class SourceRule:
    kind: str
    book: str = ""
    labels: tuple[str, ...] = ()
    exclude_labels: tuple[str, ...] = ()
    file: str = ""
    query: str = ""
    max: int = 12
    doc_types: tuple[str, ...] = ("textbook",)
    exclude_guide: str = ""
    min_score: float = 0.0
    max_per_file: int = 0


@dataclass(frozen=True)
class TopicSpec:
    title: str
    instruction: str
    sources: tuple[SourceRule, ...]


@dataclass(frozen=True)
class ComparisonSpec:
    title: str
    instruction: str
    from_topics: tuple[str, ...]
    take: int = 3


@dataclass(frozen=True)
class NoteSpec:
    heading: str
    body: str


@dataclass(frozen=True)
class GuideSpec:
    id: str
    title: str
    course: str
    draft_model: str
    enhance_model: str
    prompt: str
    label_match: str
    top_k: int
    file_top_k: int
    notes: tuple[NoteSpec, ...]
    topics: tuple[TopicSpec, ...]
    comparisons: tuple[ComparisonSpec, ...]
    path: str
    sha256: str


_RULE_KEYS = {
    "section": {"kind", "book", "labels", "exclude_labels", "query", "max"},
    "file": {"kind", "file", "query", "max"},
    "discover": {"kind", "query", "doc_types", "exclude_guide", "max", "min_score", "max_per_file"},
}


def _check_keys(table: dict, allowed: set[str], where: str) -> None:
    extra = set(table) - allowed
    if extra:
        raise SpecError(f"{where}: unknown key(s) {sorted(extra)}")


def _str(table: dict, key: str, where: str, default: str | None = None) -> str:
    if key not in table:
        if default is None:
            raise SpecError(f"{where}: missing '{key}'")
        return default
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{where}: '{key}' must be a non-empty string")
    return value


def _int(table: dict, key: str, where: str, default: int, minimum: int = 1) -> int:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SpecError(f"{where}: '{key}' must be an integer >= {minimum}")
    return value


def _strs(table: dict, key: str, where: str, default: tuple[str, ...] = (), required: bool = False) -> tuple[str, ...]:
    if key not in table:
        if required:
            raise SpecError(f"{where}: missing '{key}'")
        return default
    value = table[key]
    ok = isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)
    if not ok or (required and not value):
        raise SpecError(f"{where}: '{key}' must be a list of non-empty strings" + (" (at least one)" if required else ""))
    return tuple(value)


def _optional_str(table: dict, key: str, where: str) -> str:
    value = table.get(key, "")
    if not isinstance(value, str):
        raise SpecError(f"{where}: '{key}' must be a string")
    return value


def _parse_rule(raw: object, where: str) -> SourceRule:
    if not isinstance(raw, dict):
        raise SpecError(f"{where}: must be a table")
    kind = raw.get("kind")
    if kind not in _RULE_KEYS:
        raise SpecError(f"{where}: 'kind' must be one of {sorted(_RULE_KEYS)}")
    _check_keys(raw, _RULE_KEYS[kind], where)
    maximum = _int(raw, "max", where, 12)
    if kind == "section":
        return SourceRule(
            kind, book=_str(raw, "book", where), labels=_strs(raw, "labels", where, required=True),
            exclude_labels=_strs(raw, "exclude_labels", where), query=_str(raw, "query", where), max=maximum)
    if kind == "file":
        return SourceRule(kind, file=_str(raw, "file", where), query=_optional_str(raw, "query", where), max=maximum)
    min_score = raw.get("min_score", 0.0)
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)) or not 0 <= min_score <= 1:
        raise SpecError(f"{where}: 'min_score' must be a number between 0 and 1")
    doc_types = _strs(raw, "doc_types", where, default=("textbook",))
    if not doc_types:
        raise SpecError(f"{where}: 'doc_types' must not be empty")
    return SourceRule(
        kind, query=_str(raw, "query", where), doc_types=doc_types,
        exclude_guide=_optional_str(raw, "exclude_guide", where), max=maximum,
        min_score=float(min_score), max_per_file=_int(raw, "max_per_file", where, 0, minimum=0))


def load_spec(path: str | Path) -> GuideSpec:
    p = Path(path)
    if not p.is_file():
        raise SpecError(f"guide spec not found: {p}")
    raw_bytes = p.read_bytes()
    try:
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as err:
        raise SpecError(f"{p.name}: invalid TOML: {err}") from err
    _check_keys(data, {"guide", "models", "draft", "note", "topic", "comparison"}, "spec")

    guide = data.get("guide")
    if not isinstance(guide, dict):
        raise SpecError("spec: missing [guide] table")
    _check_keys(guide, {"id", "title", "course"}, "[guide]")
    guide_id = _str(guide, "id", "[guide]")
    if not _ID_RE.match(guide_id):
        raise SpecError(f"[guide]: id {guide_id!r} must be lowercase letters, digits and underscores")

    models = data.get("models", {})
    _check_keys(models, {"draft", "enhance"}, "[models]")
    draft = data.get("draft", {})
    _check_keys(draft, {"prompt", "label_match", "top_k", "file_top_k"}, "[draft]")
    prompt = _str(draft, "prompt", "[draft]", "tutor_v1")
    if prompt not in VALID_PROMPTS:
        raise SpecError(f"[draft]: prompt must be one of {VALID_PROMPTS}")
    label_match = _str(draft, "label_match", "[draft]", "heading-prefix")
    if label_match not in VALID_LABEL_MATCH:
        raise SpecError(f"[draft]: label_match must be one of {VALID_LABEL_MATCH}")

    notes = []
    for i, n in enumerate(data.get("note", []), 1):
        _check_keys(n, {"heading", "body"}, f"[[note]] {i}")
        notes.append(NoteSpec(_str(n, "heading", f"[[note]] {i}"), _str(n, "body", f"[[note]] {i}")))

    topics, seen = [], set()
    for i, t in enumerate(data.get("topic", []), 1):
        where = f"[[topic]] {i}"
        _check_keys(t, {"title", "instruction", "source"}, where)
        title = _str(t, "title", where)
        if title in seen:
            raise SpecError(f"duplicate topic title {title!r}")
        seen.add(title)
        sources = t.get("source", [])
        if not sources:
            raise SpecError(f"{where} ({title!r}): needs at least one [[topic.source]]")
        topics.append(TopicSpec(title, _str(t, "instruction", where),
                                tuple(_parse_rule(s, f"{where} source {j}") for j, s in enumerate(sources, 1))))
    if not topics:
        raise SpecError("spec needs at least one topic")

    comparisons = []
    for i, c in enumerate(data.get("comparison", []), 1):
        where = f"[[comparison]] {i}"
        _check_keys(c, {"title", "instruction", "from", "take"}, where)
        title = _str(c, "title", where)
        if title in seen:
            raise SpecError(f"duplicate title {title!r} (comparison titles must differ from topic titles)")
        seen.add(title)
        sources = _strs(c, "from", where, required=True)
        for name in sources:
            if name not in {t.title for t in topics}:
                raise SpecError(f"{where}: 'from' names unknown topic {name!r}")
        comparisons.append(ComparisonSpec(title, _str(c, "instruction", where), sources, _int(c, "take", where, 3)))

    return GuideSpec(
        id=guide_id, title=_str(guide, "title", "[guide]"), course=_str(guide, "course", "[guide]"),
        draft_model=_str(models, "draft", "[models]", DEFAULT_MODEL),
        enhance_model=_str(models, "enhance", "[models]", DEFAULT_MODEL),
        prompt=prompt, label_match=label_match, top_k=_int(draft, "top_k", "[draft]", 180),
        file_top_k=_int(draft, "file_top_k", "[draft]", 80), notes=tuple(notes), topics=tuple(topics),
        comparisons=tuple(comparisons), path=str(p), sha256=hashlib.sha256(raw_bytes).hexdigest())
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_spec.py -q`
Expected: all pass. If a parametrized `match=` fails on wording, fix the message in `spec.py` (the tests pin only the key words listed).

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/__init__.py agent/study_guide/spec.py tests/agent/study_guide/sg_helpers.py tests/agent/study_guide/test_study_guide_spec.py
git commit -m "feat(study_guide): guide spec loader (TOML) with strict validation" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Source plan core (rules, matching, ledger)

**Files:**
- Create: `agent/study_guide/plan.py`
- Modify: `tests/agent/study_guide/sg_helpers.py` (fill in), create `tests/agent/study_guide/conftest.py`
- Test: `tests/agent/study_guide/test_study_guide_plan.py`

**Interfaces:**
- Consumes: `GuideSpec`, `SourceRule`, `TopicSpec`, `load_spec` (Task 1).
- Produces (`plan.py`):
  - `PlanError(Exception)`, `PendingReviewError(PlanError)`; constants `ACCEPTED="accepted"`, `PENDING="pending"`, `DROPPED="dropped"`
  - `PlanEntry(chunk_id, file_id, path, citation, doc_type, offering, score, rule, content_hash, status="accepted")` (dataclass)
  - `TopicPlan(title, entries: list[PlanEntry])`, `Plan(spec_id, spec_file, spec_sha256, course, generated_at, topics: list[TopicPlan])`
  - `heading_numbers(heading_path: list[str]) -> list[str]`
  - `guide_chunk_ids(root: str, rel_path: str) -> set[str]`
  - `build_plan(spec, root, *, client=None, search=None, chunks=None, cards=None, now=None) -> Plan`; `search(query, *, doc_type, top_k, file_top_k) -> list` of objects with `chunk_id, file_id, path, score, citation, text`
  - `save_plan(plan, path) -> None`, `load_plan(path) -> Plan`, `plan_sha256(path) -> str`
  - `check_fresh(plan, *, chunks, cards) -> list[str]`
- Produces (`sg_helpers.py`): `CHUNKS`, `CARDS`, `cite(chunk)`, `hit(chunk_id, score)`, `StubSearch(by_doc_type)` (callable recording `.calls`), `HEADER`, `topic_toml(...)` helpers, `FakeLLM(replies)`.
- Produces (`conftest.py`): fixture `make_spec(tmp_path)` returning `make(body, header=HEADER) -> GuideSpec`; fixture `root(tmp_path)` returning the hub root string with `academic_notes/econ/summaries` created.

- [ ] **Step 1: Write helpers and the failing tests**

```python
# tests/agent/study_guide/sg_helpers.py
"""Shared helpers for the study_guide tests (imported as `sg_helpers`)."""
from __future__ import annotations

from types import SimpleNamespace

CAMERON = "academic_notes/econ/textbooks/processed_outputs/Cameron_Micro_2013/Cameron_Micro_2013.rag.md"
HANSEN = "academic_notes/econ/textbooks/processed_outputs/Hansen_Econ_2022/Hansen_Econ_2022.rag.md"
SLIDES = "academic_notes/econ/class_2024/Class Notes/Slides/processed_outputs/slidesASYM.md"
RECIT = "academic_notes/econ/class_2024/Recitations/processed_outputs/Recitation 5.md"
EMPTY = "academic_notes/econ/class_2024/Recitations/processed_outputs/Empty.md"

CHUNKS = [
    {"chunk_id": "cam-1", "file_id": "cam", "text": "Cameron: the Wald statistic.",
     "heading_path": ["Chapter 7", "**7.2.** Wald Test", "§7.2.3. Wald Test Statistic"], "page_range": [249, 249]},
    {"chunk_id": "cam-2", "file_id": "cam", "text": "Cameron: the likelihood ratio test.",
     "heading_path": ["7.3.1. Wald, Likelihood Ratio, and LM Tests", "Likelihood Ratio Test"], "page_range": [257, 257]},
    {"chunk_id": "cam-3", "file_id": "cam", "text": "Cameron: the LM test.",
     "heading_path": ["7.3.5. Interpretation and Computation of the LM test"], "page_range": [262, 262]},
    {"chunk_id": "cam-4", "file_id": "cam", "text": "Cameron: an unrelated section.",
     "heading_path": ["7.30 Something else"], "page_range": [300, 300]},
    {"chunk_id": "han-1", "file_id": "han", "text": "Hansen: Wald tests.",
     "heading_path": ["9.10 WALD TESTS"], "page_range": [268, 268]},
    {"chunk_id": "han-2", "file_id": "han", "text": "Hansen: an intro.",
     "heading_path": ["9.1 Introduction"], "page_range": [250, 250]},
    {"chunk_id": "sl-1", "file_id": "sl", "text": "Slides: first."},
    {"chunk_id": "sl-2", "file_id": "sl", "text": "Slides: second."},
    {"chunk_id": "rec-1", "file_id": "rec", "text": "Recitation: Wald of nonlinear hypothesis."},
]

CARDS = [
    {"file_id": "cam", "doc_type": "textbook", "path": CAMERON.replace(".rag.md", ".md"), "rag_md_path": CAMERON, "content_hash": "h-cam"},
    {"file_id": "han", "doc_type": "textbook", "path": HANSEN.replace(".rag.md", ".md"), "rag_md_path": HANSEN, "content_hash": "h-han"},
    {"file_id": "sl", "doc_type": "ta_notes", "path": SLIDES, "rag_md_path": None, "content_hash": "h-sl"},
    {"file_id": "rec", "doc_type": "ta_notes", "path": RECIT, "rag_md_path": None, "content_hash": "h-rec"},
    {"file_id": "empty", "doc_type": "ta_notes", "path": EMPTY, "rag_md_path": None, "content_hash": "h-empty"},
]


def cite(chunk: dict) -> str:
    hp = chunk.get("heading_path")
    if not hp:
        return chunk["chunk_id"]
    page = chunk["page_range"][0]
    return f"§{hp[-1]}, p. {page}"


def hit(chunk_id: str, score: float):
    chunk = next(c for c in CHUNKS if c["chunk_id"] == chunk_id)
    card = next(c for c in CARDS if c["file_id"] == chunk["file_id"])
    return SimpleNamespace(chunk_id=chunk_id, file_id=chunk["file_id"], path=card.get("rag_md_path") or card["path"],
                           score=score, citation=cite(chunk), text=chunk["text"])


class StubSearch:
    """Stands in for search_passages: returns canned hits per doc_type and records calls."""

    def __init__(self, by_doc_type: dict):
        self.by_doc_type = by_doc_type
        self.calls: list[dict] = []

    def __call__(self, query, *, doc_type, top_k, file_top_k):
        self.calls.append({"query": query, "doc_type": doc_type, "top_k": top_k, "file_top_k": file_top_k})
        return list(self.by_doc_type.get(doc_type, []))


HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'

WALD_TOPIC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"
"""


class FakeLLM:
    model = "fake-draft"

    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls: list[str] = []

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        reply = self.replies.pop(0) if self.replies else f"ANSWER {len(self.calls)}"
        if isinstance(reply, Exception):
            raise reply
        return reply

    def generate_structured(self, prompt, schema):
        raise AssertionError("the draft stage must not request structured output")
```

```python
# tests/agent/study_guide/conftest.py
import pytest

from agent.study_guide.spec import load_spec
from sg_helpers import HEADER


@pytest.fixture
def make_spec(tmp_path):
    def make(body, header=HEADER):
        path = tmp_path / "spec.toml"
        path.write_text(header + body, encoding="utf-8")
        return load_spec(path)
    return make


@pytest.fixture
def root(tmp_path):
    hub = tmp_path / "hub"
    (hub / "academic_notes" / "econ" / "summaries").mkdir(parents=True)
    return str(hub)
```

```python
# tests/agent/study_guide/test_study_guide_plan.py
import json

import pytest

from agent.study_guide import plan as plan_mod
from agent.study_guide.plan import (
    PlanError, build_plan, check_fresh, guide_chunk_ids, heading_numbers, load_plan, plan_sha256, save_plan,
)
from sg_helpers import CARDS, CHUNKS, WALD_TOPIC, StubSearch, hit

NOW = "2026-10-05T00:00:00+00:00"


def _topic(sources, title="Wald", instruction="Explain Wald."):
    return f'\n[[topic]]\ntitle = "{title}"\ninstruction = "{instruction}"\n' + sources


def _section(labels, book="Cameron", exclude="[]", mx=12, query="wald"):
    return (f'\n  [[topic.source]]\n  kind = "section"\n  book = "{book}"\n  labels = {json.dumps(labels)}\n'
            f'  exclude_labels = {exclude}\n  query = "{query}"\n  max = {mx}\n')


def _build(spec, root, search, **kw):
    return build_plan(spec, root, search=search, chunks=CHUNKS, cards=CARDS, now=NOW, **kw)


def _ids(plan, i=0):
    return [e.chunk_id for e in plan.topics[i].entries]


def test_heading_numbers_extracts_leading_section_numbers():
    path = ["Chapter 7", "**7.2.** Wald Test", "§7.2.3. Wald Test Statistic", "9.10 WALD TESTS", "Likelihood Ratio Test"]
    assert heading_numbers(path) == ["7.2", "7.2.3", "9.10"]


def test_section_rule_filters_by_book_and_label(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"])))
    search = StubSearch({"textbook": [hit("cam-1", .8), hit("han-1", .7), hit("cam-3", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-1"]


def test_unnumbered_child_heading_matches_its_numbered_parent(make_spec, root):
    spec = make_spec(_topic(_section(["7.3.1"])))
    search = StubSearch({"textbook": [hit("cam-2", .8), hit("cam-3", .7)]})
    assert _ids(_build(spec, root, search)) == ["cam-2"]


def test_label_prefix_stops_at_the_dot_boundary(make_spec, root):
    spec = make_spec(_topic(_section(["7.3"])))
    search = StubSearch({"textbook": [hit("cam-2", .8), hit("cam-3", .7), hit("cam-4", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-2", "cam-3"]          # not 7.30


def test_hansen_label_9_1_does_not_match_9_10_but_legacy_substring_does(make_spec, root):
    search = StubSearch({"textbook": [hit("han-1", .8), hit("han-2", .7)]})
    new = make_spec(_topic(_section(["9.1"], book="Hansen")))
    assert _ids(_build(new, root, search)) == ["han-2"]
    legacy = make_spec(_topic(_section(["9.1"], book="Hansen")), header=HEADER_LEGACY)
    assert _ids(_build(legacy, root, search)) == ["han-1", "han-2"]


HEADER_LEGACY = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n[draft]\nlabel_match = "citation-substring"\n\n'


def test_legacy_substring_misses_unnumbered_child_headings(make_spec, root):
    spec = make_spec(_topic(_section(["7.3.1"])), header=HEADER_LEGACY)
    search = StubSearch({"textbook": [hit("cam-2", .8)]})
    with pytest.raises(PlanError, match="Wald"):
        _build(spec, root, search)


def test_exclude_labels_and_max_follow_search_order(make_spec, root):
    spec = make_spec(_topic(_section(["7"], exclude='["7.3.5"]', mx=2)))
    search = StubSearch({"textbook": [hit("cam-3", .9), hit("cam-1", .8), hit("cam-2", .7), hit("cam-4", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-1", "cam-2"]


def test_section_search_text_and_parameters(make_spec, root):
    spec = make_spec(WALD_TOPIC)
    search = StubSearch({"textbook": [hit("cam-1", .8)]})
    _build(spec, root, search)
    assert search.calls == [{"query": "Econ textbook: wald. Explain Wald.", "doc_type": "textbook",
                             "top_k": 180, "file_top_k": 80}]


def _file_rule(file, query="", mx=12):
    q = f'  query = "{query}"\n' if query else ""
    return f'\n  [[topic.source]]\n  kind = "file"\n  file = "{file}"\n{q}  max = {mx}\n'


def test_file_rule_ranks_by_search_then_fills_in_document_order(make_spec, root):
    spec = make_spec(_topic(_file_rule("Slides/processed_outputs/slidesASYM.md", query="wald", mx=2)))
    search = StubSearch({"ta_notes": [hit("sl-2", .9), hit("rec-1", .8)]})
    plan = _build(spec, root, search)
    assert _ids(plan) == ["sl-2", "sl-1"]
    assert plan.topics[0].entries[0].score == .9 and plan.topics[0].entries[1].score == 0.0
    assert search.calls[0]["doc_type"] == "ta_notes" and search.calls[0]["file_top_k"] == 200


def test_file_rule_without_query_uses_document_order_and_file_id(make_spec, root):
    search = StubSearch({})
    assert _ids(_build(make_spec(_topic(_file_rule("sl"))), root, search)) == ["sl-1", "sl-2"]
    assert _ids(_build(make_spec(_topic(_file_rule("sl", mx=1))), root, search)) == ["sl-1"]
    assert search.calls == []


@pytest.mark.parametrize("ref,fragment", [("Nope/missing.md", "not found"), ("Recitations/processed_outputs/Empty.md", "chunk")])
def test_file_rule_errors(make_spec, root, ref, fragment):
    with pytest.raises(PlanError, match=fragment):
        _build(make_spec(_topic(_file_rule(ref))), root, StubSearch({}))


def _discover(extra="", query="wald", doc_types='["textbook"]', mx=8, min_score=0.72):
    return (f'\n  [[topic.source]]\n  kind = "discover"\n  query = "{query}"\n  doc_types = {doc_types}\n'
            f'  max = {mx}\n  min_score = {min_score}\n{extra}')


def test_discover_applies_threshold_pinned_exclusion_and_pending_status(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]) + _discover()))
    search = StubSearch({"textbook": [hit("cam-1", .80), hit("han-1", .76), hit("cam-3", .74), hit("han-2", .70)]})
    plan = _build(spec, root, search)
    assert _ids(plan) == ["cam-1", "han-1", "cam-3"]
    assert [e.status for e in plan.topics[0].entries] == ["accepted", "pending", "pending"]
    assert [e.rule for e in plan.topics[0].entries] == ["section", "discover", "discover"]


def test_discover_excludes_a_guides_chunks(make_spec, root, tmp_path):
    guide = tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "old.md"
    guide.write_text('---\ntitle: "Old"\nindexer_source_refs: [{"chunk_id":"han-1","file_id":"han","path":"p","citation":"c"}]\n---\n\nBody\n',
                     encoding="utf-8")
    spec = make_spec(_topic(_discover(extra='  exclude_guide = "academic_notes/econ/summaries/old.md"\n')))
    search = StubSearch({"textbook": [hit("han-1", .9), hit("cam-1", .8)]})
    assert _ids(_build(spec, root, search)) == ["cam-1"]


def test_guide_chunk_ids_reads_source_map_too(root, tmp_path):
    guide = tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "new.md"
    guide.write_text('---\nsource_map: [{"chunk_id":"a-1"},{"chunk_id":"a-2"}]\n---\n\nBody\n', encoding="utf-8")
    assert guide_chunk_ids(root, "academic_notes/econ/summaries/new.md") == {"a-1", "a-2"}


@pytest.mark.parametrize("content,fragment", [
    (None, "not readable"),
    ("no frontmatter here\n", "frontmatter"),
    ('---\ntitle: "x"\n---\n\nBody\n', "no source chunks"),
])
def test_exclude_guide_errors_are_loud(make_spec, root, tmp_path, content, fragment):
    if content is not None:
        (tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "old.md").write_text(content, encoding="utf-8")
    spec = make_spec(_topic(_discover(extra='  exclude_guide = "academic_notes/econ/summaries/old.md"\n')))
    with pytest.raises(PlanError, match=fragment):
        _build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))


def test_discover_max_per_file_and_multiple_doc_types(make_spec, root):
    spec = make_spec(_topic(_discover(doc_types='["textbook", "ta_notes"]', extra="  max_per_file = 1\n")))
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("cam-2", .85), hit("han-1", .8)],
                         "ta_notes": [hit("sl-1", .95), hit("sl-2", .9)]})
    assert _ids(_build(spec, root, search)) == ["sl-1", "cam-1", "han-1"]


def test_rule_order_is_section_then_file_then_discover(make_spec, root):
    spec = make_spec(_topic(_discover() + _file_rule("sl", mx=1) + _section(["7.2"])))
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})
    assert _ids(_build(spec, root, search)) == ["cam-1", "sl-1", "han-1"]


def test_duplicate_chunks_within_a_topic_are_kept_once(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]) + _section(["7.2"], query="wald again")))
    assert _ids(_build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))) == ["cam-1"]


def test_entry_metadata(make_spec, root, monkeypatch):
    monkeypatch.setattr(plan_mod, "_offering", lambda card, hub: "class_2024" if card["file_id"] == "sl" else "")
    spec = make_spec(_topic(_section(["7.2"]) + _file_rule("sl", mx=1)))
    plan = _build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))
    cam, sl = plan.topics[0].entries
    assert (cam.doc_type, cam.content_hash, cam.offering, cam.file_id) == ("textbook", "h-cam", "", "cam")
    assert cam.path.endswith("Cameron_Micro_2013.rag.md") and cam.citation == "§7.2.3. Wald Test Statistic, p. 249"
    assert (sl.doc_type, sl.offering, sl.citation) == ("ta_notes", "class_2024", "sl-1")
    assert (plan.spec_id, plan.course, plan.generated_at, plan.spec_sha256) == ("demo", "econ", NOW, spec.sha256)


def test_chunks_without_a_heading_path_fall_back_to_the_citation(make_spec, root):
    from types import SimpleNamespace
    chunks = CHUNKS + [{"chunk_id": "cam-5", "file_id": "cam", "text": "no heading path"}]
    result = SimpleNamespace(chunk_id="cam-5", file_id="cam", path=CARDS[0]["rag_md_path"], score=.9,
                             citation="§7.2.9 Lack of Invariance, p. 256", text="t")
    spec = make_spec(_topic(_section(["7.2"])))
    plan = build_plan(spec, root, search=StubSearch({"textbook": [result]}), chunks=chunks, cards=CARDS, now=NOW)
    assert _ids(plan) == ["cam-5"]


def test_topic_with_no_passages_fails_and_names_the_topic(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]), title="Empty Topic"))
    with pytest.raises(PlanError, match="Empty Topic"):
        _build(spec, root, StubSearch({"textbook": []}))


def test_save_load_roundtrip_and_sha(make_spec, root, tmp_path):
    plan = _build(make_spec(WALD_TOPIC), root, StubSearch({"textbook": [hit("cam-1", .8)]}))
    path = tmp_path / "out" / "demo.plan.json"
    save_plan(plan, path)
    assert load_plan(path) == plan
    assert len(plan_sha256(path)) == 64


def test_load_rejects_other_formats(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"format": 99}), encoding="utf-8")
    with pytest.raises(PlanError, match="format"):
        load_plan(path)


def test_check_fresh_detects_missing_chunks_and_changed_files(make_spec, root):
    plan = _build(make_spec(WALD_TOPIC), root, StubSearch({"textbook": [hit("cam-1", .8)]}))
    assert check_fresh(plan, chunks=CHUNKS, cards=CARDS) == []
    gone = check_fresh(plan, chunks=[c for c in CHUNKS if c["chunk_id"] != "cam-1"], cards=CARDS)
    assert len(gone) == 1 and "cam-1" in gone[0]
    changed = [dict(c, content_hash="NEW") if c["file_id"] == "cam" else c for c in CARDS]
    assert "changed" in check_fresh(plan, chunks=CHUNKS, cards=changed)[0]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_plan.py -q`
Expected: `ModuleNotFoundError: agent.study_guide.plan`.

- [ ] **Step 3: Implement**

```python
# agent/study_guide/plan.py
"""Source plan: resolves a guide spec's source rules into a concrete, ordered, de-duplicated
list of indexed passages per topic, recorded in a ledger file (ids, paths, citations, scores,
rule provenance; never passage text). Pinned rules (section, file) are accepted; discovered
candidates start pending and need a human decision (see the review functions, Task 3)."""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agent.study_guide.spec import GuideSpec, SourceRule, TopicSpec

PLAN_FORMAT = 1
ACCEPTED, PENDING, DROPPED = "accepted", "pending", "dropped"
_KIND_RANK = {"section": 0, "file": 1, "discover": 2}
_FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


class PlanError(Exception):
    pass


class PendingReviewError(PlanError):
    pass


@dataclass
class PlanEntry:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    doc_type: str
    offering: str
    score: float
    rule: str
    content_hash: str
    status: str = ACCEPTED


@dataclass
class TopicPlan:
    title: str
    entries: list[PlanEntry]


@dataclass
class Plan:
    spec_id: str
    spec_file: str
    spec_sha256: str
    course: str
    generated_at: str
    topics: list[TopicPlan]


# ---- label matching -------------------------------------------------------------------

def heading_numbers(heading_path: list[str]) -> list[str]:
    """The leading section number of each heading element, e.g. '**7.2.** Wald' -> '7.2'."""
    numbers = []
    for element in heading_path:
        m = re.match(r"(\d+(?:\.\d+)*)", re.sub(r"^[\s*#§_]+", "", element))
        if m:
            numbers.append(m.group(1))
    return numbers


def _matches(chunk: dict, citation: str, labels: tuple[str, ...], mode: str) -> bool:
    if not labels:
        return False
    heading_path = chunk.get("heading_path")
    if mode == "citation-substring" or not heading_path:
        return any(label in citation for label in labels)
    numbers = heading_numbers(heading_path)
    return any(n == label or n.startswith(label + ".") for n in numbers for label in labels)


# ---- helpers --------------------------------------------------------------------------

def _rel(root: str, path: str) -> str:
    if not os.path.isabs(path):
        return path.replace("\\", "/")
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path.replace("\\", "/")
    return path.replace("\\", "/") if rel.startswith("..") else rel.replace("\\", "/")


def _offering(card: dict, root: str) -> str:
    try:
        from core.indexer.offering_links import derive_offering_for_card
        return derive_offering_for_card(card, root) or ""
    except Exception:  # a label is optional provenance; never block planning on it
        return ""


def guide_chunk_ids(root: str, rel_path: str) -> set[str]:
    """Chunk ids a guide used, from its `indexer_source_refs` (drafts) or `source_map` (enhanced)."""
    path = Path(rel_path) if os.path.isabs(rel_path) else Path(root) / rel_path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise PlanError(f"exclude_guide not readable: {path} ({err})") from err
    match = _FRONT_RE.match(text.replace("\r\n", "\n"))
    if not match:
        raise PlanError(f"{path} has no frontmatter")
    ids: set[str] = set()
    for key in ("indexer_source_refs", "source_map"):
        m = re.search(rf"^{key}:[ \t]*(.*)$", match.group(1), re.MULTILINE)
        if not m:
            continue
        try:
            items = json.loads(m.group(1))
        except json.JSONDecodeError as err:
            raise PlanError(f"{path}: {key} is not valid JSON: {err}") from err
        ids |= {i["chunk_id"] for i in items if isinstance(i, dict) and "chunk_id" in i}
    if not ids:
        raise PlanError(f"{path} lists no source chunks (no indexer_source_refs or source_map)")
    return ids


def _find_card(cards: list[dict], ref: str) -> dict | None:
    wanted = ref.replace("\\", "/")
    for card in cards:
        if card["file_id"] == ref:
            return card
        for key in ("rag_md_path", "path"):
            value = (card.get(key) or "").replace("\\", "/")
            if value and value.endswith(wanted):
                return card
    return None


class _Context:
    def __init__(self, spec, root, search, chunks, cards):
        self.spec, self.root, self.search = spec, root, search
        self.chunks = chunks
        self.chunks_by_id = {c["chunk_id"]: c for c in chunks}
        self.cards = cards
        self.cards_by_file = {c["file_id"]: c for c in cards}

    def entry(self, result, rule: str, status: str) -> PlanEntry:
        card = self.cards_by_file.get(result.file_id, {})
        return PlanEntry(
            chunk_id=result.chunk_id, file_id=result.file_id, path=_rel(self.root, result.path),
            citation=result.citation, doc_type=card.get("doc_type", ""), offering=_offering(card, self.root) if card else "",
            score=round(float(result.score), 4), rule=rule, content_hash=card.get("content_hash", ""), status=status)


# ---- rules ----------------------------------------------------------------------------

def _resolve_section(ctx: _Context, topic: TopicSpec, rule: SourceRule) -> list[PlanEntry]:
    text = f"{ctx.spec.course.capitalize()} textbook: {rule.query}. {topic.instruction}"
    results = ctx.search(text, doc_type="textbook", top_k=ctx.spec.top_k, file_top_k=ctx.spec.file_top_k)
    picked: list[PlanEntry] = []
    for r in results:
        if rule.book not in os.path.basename(r.path):
            continue
        chunk = ctx.chunks_by_id.get(r.chunk_id, {})
        if not _matches(chunk, r.citation, rule.labels, ctx.spec.label_match):
            continue
        if _matches(chunk, r.citation, rule.exclude_labels, ctx.spec.label_match):
            continue
        picked.append(ctx.entry(r, "section", ACCEPTED))
        if len(picked) == rule.max:
            break
    return picked


def _pseudo_result(ctx: _Context, chunk: dict):
    from types import SimpleNamespace
    from core.indexer.index_search import _render_citation
    card = ctx.cards_by_file[chunk["file_id"]]
    return SimpleNamespace(chunk_id=chunk["chunk_id"], file_id=chunk["file_id"],
                           path=card.get("rag_md_path") or card["path"], score=0.0,
                           citation=_render_citation(chunk) or chunk["chunk_id"])


def _resolve_file(ctx: _Context, topic: TopicSpec, rule: SourceRule) -> list[PlanEntry]:
    card = _find_card(ctx.cards, rule.file)
    if card is None:
        raise PlanError(f"file not found in the {ctx.spec.course} index: {rule.file}")
    file_chunks = [c for c in ctx.chunks if c["file_id"] == card["file_id"]]
    if not file_chunks:
        raise PlanError(f"{rule.file} has no chunks; run the chunk step on it first")
    ranked: list = []
    if rule.query:
        results = ctx.search(f"{rule.query}. {topic.instruction}", doc_type=card.get("doc_type"),
                             top_k=3000, file_top_k=200)
        ranked = [r for r in results if r.file_id == card["file_id"]]
    have = {r.chunk_id for r in ranked}
    rest = [_pseudo_result(ctx, c) for c in file_chunks if c["chunk_id"] not in have]
    return [ctx.entry(r, "file", ACCEPTED) for r in (ranked + rest)[:rule.max]]


def _resolve_discover(ctx: _Context, topic: TopicSpec, rule: SourceRule, taken: set[str]) -> list[PlanEntry]:
    excluded = set(taken)
    if rule.exclude_guide:
        excluded |= guide_chunk_ids(ctx.root, rule.exclude_guide)
    pool: list = []
    for doc_type in rule.doc_types:
        pool += ctx.search(f"{rule.query}. {topic.instruction}", doc_type=doc_type,
                           top_k=max(60, rule.max * 8), file_top_k=40)
    pool.sort(key=lambda r: -r.score)
    per_file: Counter = Counter()
    picked: list[PlanEntry] = []
    for r in pool:
        if r.chunk_id in excluded or r.score < rule.min_score:
            continue
        if rule.max_per_file and per_file[r.file_id] >= rule.max_per_file:
            continue
        per_file[r.file_id] += 1
        excluded.add(r.chunk_id)
        picked.append(ctx.entry(r, "discover", PENDING))
        if len(picked) == rule.max:
            break
    return picked


def build_plan(spec: GuideSpec, root: str, *, client=None, search: Callable | None = None,
               chunks: list[dict] | None = None, cards: list[dict] | None = None, now: str | None = None) -> Plan:
    if search is None:
        if client is None:
            raise PlanError("a Gemini client (or an explicit search function) is required")
        from core.indexer.index_search import search_passages

        def search(query, *, doc_type, top_k, file_top_k):
            return search_passages([root], query, client, course=spec.course, top_k=top_k,
                                   file_top_k=file_top_k, doc_type=doc_type)
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    if cards is None:
        from core.indexer.index_card import load_shard
        cards = load_shard(root, spec.course)

    ctx = _Context(spec, root, search, chunks, cards)
    topics: list[TopicPlan] = []
    for topic in spec.topics:
        entries: list[PlanEntry] = []
        taken: set[str] = set()
        for rule in sorted(topic.sources, key=lambda r: _KIND_RANK[r.kind]):
            if rule.kind == "section":
                found = _resolve_section(ctx, topic, rule)
            elif rule.kind == "file":
                found = _resolve_file(ctx, topic, rule)
            else:
                found = _resolve_discover(ctx, topic, rule, taken)
            for entry in found:
                if entry.chunk_id not in taken:
                    taken.add(entry.chunk_id)
                    entries.append(entry)
        if not entries:
            raise PlanError(f"no passages resolved for topic {topic.title!r}")
        topics.append(TopicPlan(topic.title, entries))
    return Plan(spec_id=spec.id, spec_file=Path(spec.path).name, spec_sha256=spec.sha256, course=spec.course,
                generated_at=now or datetime.now(timezone.utc).isoformat(timespec="seconds"), topics=topics)


# ---- ledger ---------------------------------------------------------------------------

def save_plan(plan: Plan, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": PLAN_FORMAT, **asdict(plan)}
    tmp = p.with_name(p.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        os.replace(tmp, p)
    finally:
        tmp.unlink(missing_ok=True)


def load_plan(path: str | Path) -> Plan:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise PlanError(f"cannot read plan {path}: {err}") from err
    if data.get("format") != PLAN_FORMAT:
        raise PlanError(f"unsupported plan format {data.get('format')!r} (expected {PLAN_FORMAT})")
    try:
        return Plan(
            spec_id=data["spec_id"], spec_file=data["spec_file"], spec_sha256=data["spec_sha256"],
            course=data["course"], generated_at=data["generated_at"],
            topics=[TopicPlan(t["title"], [PlanEntry(**e) for e in t["entries"]]) for t in data["topics"]])
    except (KeyError, TypeError) as err:
        raise PlanError(f"malformed plan {path}: {err}") from err


def plan_sha256(path: str | Path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_fresh(plan: Plan, *, chunks: list[dict], cards: list[dict]) -> list[str]:
    """Problems that make a plan stale: a planned chunk is gone, or its file's content changed."""
    by_id = {c["chunk_id"]: c for c in chunks}
    hashes = {c["file_id"]: c.get("content_hash", "") for c in cards}
    problems = []
    for topic in plan.topics:
        for e in topic.entries:
            chunk = by_id.get(e.chunk_id)
            if chunk is None or chunk.get("file_id") != e.file_id:
                problems.append(f"{topic.title}: chunk {e.chunk_id} no longer exists in the index")
            elif e.content_hash and hashes.get(e.file_id) and hashes[e.file_id] != e.content_hash:
                problems.append(f"{topic.title}: {e.path} changed since the plan was built")
    return problems
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: all pass (spec and plan tests).

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/plan.py tests/agent/study_guide/sg_helpers.py tests/agent/study_guide/conftest.py tests/agent/study_guide/test_study_guide_plan.py
git commit -m "feat(study_guide): source plan - section/file/discover rules, heading-prefix matching, ledger" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Plan review (items, decisions, pending gate)

**Files:**
- Modify: `agent/study_guide/plan.py` (append)
- Test: `tests/agent/study_guide/test_study_guide_review.py`

**Interfaces:**
- Consumes: `Plan`, `TopicPlan`, `PlanEntry`, `PlanError`, `PendingReviewError`, constants (Task 2).
- Produces (`plan.py`):
  - `decision_key(topic_title: str, chunk_id: str) -> str` (`f"{topic_title}|{chunk_id}"`)
  - `review_items(plan: Plan) -> list[dict]` with keys `key, topic, chunk_id, book, citation, doc_type, offering, score, rule, status, locked`
  - `write_review_items(plan: Plan, path) -> None` (JSON list)
  - `apply_decisions(plan: Plan, decisions: dict[str, str]) -> Plan` (returns a new plan; values `"keep"`/`"drop"`; raises `PlanError` on unknown/locked keys or bad values)
  - `pending_entries(plan: Plan) -> list[tuple[str, PlanEntry]]`
  - `accepted(plan: Plan, topic_title: str, *, accept_unreviewed: bool = False) -> list[PlanEntry]` (raises `PendingReviewError` if pending and not accepted unreviewed; `PlanError` for unknown topic)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_review.py
import json

import pytest

from agent.study_guide.plan import (
    PendingReviewError, Plan, PlanEntry, PlanError, TopicPlan, accepted, apply_decisions, decision_key,
    pending_entries, review_items, write_review_items,
)


def _entry(cid, rule="section", status="accepted", **kw):
    base = dict(chunk_id=cid, file_id="f-" + cid, path=f"academic_notes/econ/{cid}.md", citation=f"c-{cid}",
                doc_type="textbook", offering="", score=0.8, rule=rule, content_hash="h", status=status)
    base.update(kw)
    return PlanEntry(**base)


@pytest.fixture
def plan():
    return Plan("demo", "demo.toml", "sha", "econ", "2026-10-05T00:00:00+00:00", [
        TopicPlan("Wald", [_entry("a"), _entry("b", "discover", "pending"), _entry("c", "discover", "pending")]),
        TopicPlan("LM", [_entry("d"), _entry("e", "discover", "pending", offering="class_2024", doc_type="ta_notes")]),
    ])


def test_decision_key():
    assert decision_key("Wald", "a") == "Wald|a"


def test_review_items_list_every_entry_with_locks(plan):
    items = review_items(plan)
    assert [i["key"] for i in items] == ["Wald|a", "Wald|b", "Wald|c", "LM|d", "LM|e"]
    first, second = items[0], items[1]
    assert first["locked"] is True and second["locked"] is False
    assert second == {"key": "Wald|b", "topic": "Wald", "chunk_id": "b", "book": "b.md", "citation": "c-b",
                      "doc_type": "textbook", "offering": "", "score": 0.8, "rule": "discover",
                      "status": "pending", "locked": False}
    assert items[4]["offering"] == "class_2024" and items[4]["doc_type"] == "ta_notes"


def test_write_review_items_is_a_json_list(plan, tmp_path):
    path = tmp_path / "x" / "demo.review.json"
    write_review_items(plan, path)
    assert [i["key"] for i in json.loads(path.read_text(encoding="utf-8"))][:2] == ["Wald|a", "Wald|b"]


def test_apply_decisions_keeps_and_drops_without_mutating_the_input(plan):
    new = apply_decisions(plan, {"Wald|b": "keep", "Wald|c": "drop", "LM|e": "keep"})
    assert [e.status for e in new.topics[0].entries] == ["accepted", "accepted", "dropped"]
    assert [e.status for e in new.topics[1].entries] == ["accepted", "accepted"]
    assert [e.status for e in plan.topics[0].entries] == ["accepted", "pending", "pending"]


@pytest.mark.parametrize("decisions,fragment", [
    ({"Wald|zzz": "keep"}, "unknown"),
    ({"Wald|a": "drop"}, "pinned"),
    ({"Wald|b": "maybe"}, "keep"),
])
def test_apply_decisions_rejects_bad_input(plan, decisions, fragment):
    with pytest.raises(PlanError, match=fragment):
        apply_decisions(plan, decisions)


def test_deciding_twice_is_rejected(plan):
    once = apply_decisions(plan, {"Wald|b": "keep"})
    with pytest.raises(PlanError, match="already decided"):
        apply_decisions(once, {"Wald|b": "drop"})


def test_pending_entries(plan):
    assert [(t, e.chunk_id) for t, e in pending_entries(plan)] == [("Wald", "b"), ("Wald", "c"), ("LM", "e")]


def test_accepted_blocks_on_pending_unless_explicitly_allowed(plan):
    with pytest.raises(PendingReviewError, match="Wald"):
        accepted(plan, "Wald")
    assert [e.chunk_id for e in accepted(plan, "Wald", accept_unreviewed=True)] == ["a", "b", "c"]


def test_accepted_excludes_dropped(plan):
    decided = apply_decisions(plan, {"Wald|b": "keep", "Wald|c": "drop"})
    assert [e.chunk_id for e in accepted(decided, "Wald")] == ["a", "b"]


def test_accepted_unknown_topic(plan):
    with pytest.raises(PlanError, match="Nope"):
        accepted(plan, "Nope")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_review.py -q`
Expected: ImportError (`cannot import name 'apply_decisions'`).

- [ ] **Step 3: Implement (append to `agent/study_guide/plan.py`)**

```python
# --- append to agent/study_guide/plan.py ---

# ---- review ---------------------------------------------------------------------------

def decision_key(topic_title: str, chunk_id: str) -> str:
    return f"{topic_title}|{chunk_id}"


def review_items(plan: Plan) -> list[dict]:
    """One item per planned passage for the review Artifact. Pinned entries are `locked`
    (shown, not decidable); discovered ones carry the decision."""
    items = []
    for topic in plan.topics:
        for e in topic.entries:
            items.append({
                "key": decision_key(topic.title, e.chunk_id), "topic": topic.title, "chunk_id": e.chunk_id,
                "book": os.path.basename(e.path), "citation": e.citation, "doc_type": e.doc_type,
                "offering": e.offering, "score": e.score, "rule": e.rule, "status": e.status,
                "locked": e.rule != "discover",
            })
    return items


def write_review_items(plan: Plan, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(review_items(plan), indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def apply_decisions(plan: Plan, decisions: dict[str, str]) -> Plan:
    """Returns a new plan with each decided pending entry set to accepted (keep) or dropped (drop)."""
    import copy
    new = copy.deepcopy(plan)
    index = {decision_key(t.title, e.chunk_id): e for t in new.topics for e in t.entries}
    for key, value in decisions.items():
        entry = index.get(key)
        if entry is None:
            raise PlanError(f"unknown decision key: {key!r}")
        if value not in ("keep", "drop"):
            raise PlanError(f"decision for {key!r} must be 'keep' or 'drop', got {value!r}")
        if entry.rule != "discover":
            raise PlanError(f"{key!r} is pinned by a section or file rule and cannot be dropped")
        if entry.status != PENDING:
            raise PlanError(f"{key!r} is already decided ({entry.status})")
        entry.status = ACCEPTED if value == "keep" else DROPPED
    return new


def pending_entries(plan: Plan) -> list[tuple[str, PlanEntry]]:
    return [(t.title, e) for t in plan.topics for e in t.entries if e.status == PENDING]


def accepted(plan: Plan, topic_title: str, *, accept_unreviewed: bool = False) -> list[PlanEntry]:
    topic = next((t for t in plan.topics if t.title == topic_title), None)
    if topic is None:
        raise PlanError(f"topic {topic_title!r} is not in the plan; re-run plan")
    pending = [e for e in topic.entries if e.status == PENDING]
    if pending and not accept_unreviewed:
        raise PendingReviewError(
            f"topic {topic_title!r} has {len(pending)} discovered passage(s) awaiting review; review them "
            "(or pass --accept-unreviewed to use them as they are)")
    return [e for e in topic.entries if e.status in (ACCEPTED, PENDING if accept_unreviewed else ACCEPTED)]
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/plan.py tests/agent/study_guide/test_study_guide_review.py
git commit -m "feat(study_guide): plan review items, decisions and the pending gate" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Prompts and the draft stage

**Files:**
- Create: `agent/study_guide/prompts.py`, `agent/study_guide/draft.py`
- Test: `tests/agent/study_guide/test_study_guide_prompts.py`, `tests/agent/study_guide/test_study_guide_draft.py`

**Interfaces:**
- Consumes: `GuideSpec`, `TopicSpec`, `ComparisonSpec`, `NoteSpec` (Task 1); `Plan`, `PlanEntry`, `accepted`, `PendingReviewError`, `PlanError` (Tasks 2-3); `summary_enhance.llm.UnusableResponse`; `FakeLLM` (sg_helpers).
- Produces (`prompts.py`): `TUTOR_V1_TEMPLATE: str` (frozen copy of the tutor's Q&A template; sha256 `e5615eb6fdbfd36db10d3ea27ab29274d817383b0fbf112e4559d0537830b0d6`, 668 characters); `tutor_v1_question(title, instruction) -> str`; `tutor_v1_prompt(question, excerpts: list[tuple[str, str]]) -> str`; `GUIDE_V1_TEMPLATE`; `guide_v1_prompt(title, instruction, excerpts) -> str`.
- Produces (`draft.py`): `DraftError(Exception)`; `output_path(root, spec, tag="") -> Path`; `draft_guide(spec, plan, *, root, llm, chunks=None, tag="", force=False, accept_unreviewed=False, plan_path="", plan_sha256="", now=None) -> Path`. `llm` needs `generate_text(prompt) -> str` and `.model`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_prompts.py
import hashlib

from agent.study_guide.prompts import (
    GUIDE_V1_TEMPLATE, TUTOR_V1_TEMPLATE, guide_v1_prompt, tutor_v1_prompt, tutor_v1_question,
)


def test_tutor_template_is_frozen():
    # A transcription guard for the copy of rag_agent._ANSWER_PROMPT_TEMPLATE taken on 2026-10-05.
    # If the tutor template is changed deliberately later, this copy stays as it is (baseline
    # reproduction); only change this hash if the frozen copy itself is meant to change.
    assert len(TUTOR_V1_TEMPLATE) == 668
    assert hashlib.sha256(TUTOR_V1_TEMPLATE.encode("utf-8")).hexdigest() == (
        "e5615eb6fdbfd36db10d3ea27ab29274d817383b0fbf112e4559d0537830b0d6")


def test_tutor_question_wording():
    assert tutor_v1_question("Wald test", "Explain it.") == (
        "Wald test. Explain it. Use only these excerpts. Cite each substantive claim by its exact source "
        "label. State plainly where the excerpts do not support an answer.")


def test_tutor_prompt_structure():
    prompt = tutor_v1_prompt("Q", [("A, p. 1", "text one"), ("B, p. 2", "text two")])
    assert prompt.startswith("You are tutoring a student using ONLY the excerpts below")
    assert "Excerpts:\n[A, p. 1]\ntext one\n\n[B, p. 2]\ntext two\n\nQuestion: Q\n\nAnswer:" in prompt
    assert "{history_block}" not in prompt and "{gap_hint_block}" not in prompt and prompt.endswith("Answer:")


def test_guide_prompt_contents():
    prompt = guide_v1_prompt("Wald test", "Cover the statistic.", [("A, p. 1", "text one")])
    assert "Section: Wald test" in prompt and "Focus: Cover the statistic." in prompt
    assert "[A, p. 1]\ntext one" in prompt and "800 words" in prompt and "###" in prompt
    assert "prefer the textbook" in prompt and prompt.endswith("Section text:")
    assert "{" not in GUIDE_V1_TEMPLATE.replace("{title}", "").replace("{instruction}", "").replace("{excerpts_block}", "")
```

```python
# tests/agent/study_guide/test_study_guide_draft.py
import json

import pytest

from agent.study_guide.draft import DraftError, draft_guide, output_path
from agent.study_guide.plan import PendingReviewError, Plan, PlanEntry, TopicPlan
from agent.summary_enhance.llm import UnusableResponse
from agent.summary_enhance.source_loader import load_guide
from sg_helpers import CHUNKS, FakeLLM

NOW = "2026-10-05T00:00:00+00:00"
TOPICS = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "file"
  file = "x"

[[topic]]
title = "LM"
instruction = "Explain LM."

  [[topic.source]]
  kind = "file"
  file = "y"

[[note]]
heading = "A static note"
body = "Note body text."

[[comparison]]
title = "Compare"
instruction = "Compare the two tests."
from = ["Wald", "LM"]
take = 1
"""


def _e(cid, status="accepted", rule="section"):
    chunk = next(c for c in CHUNKS if c["chunk_id"] == cid)
    return PlanEntry(chunk_id=cid, file_id=chunk["file_id"], path=f"academic_notes/econ/{cid}.md",
                     citation=f"cite-{cid}", doc_type="textbook", offering="", score=0.8, rule=rule,
                     content_hash="h", status=status)


def _plan(wald=("cam-1", "han-1"), lm=("cam-3", "cam-1")):
    return Plan("demo", "spec.toml", "sha", "econ", NOW, [
        TopicPlan("Wald", [_e(c) for c in wald]), TopicPlan("LM", [_e(c) for c in lm])])


@pytest.fixture
def spec(make_spec):
    return make_spec(TOPICS)


def _run(spec, root, llm=None, **kw):
    llm = llm or FakeLLM()
    kw.setdefault("plan", _plan())
    plan = kw.pop("plan")
    return draft_guide(spec, plan, root=root, llm=llm, chunks=CHUNKS, now=NOW, plan_path="p/demo.plan.json",
                       plan_sha256="planhash", **kw), llm


def test_default_output_path(spec, root):
    out, _ = _run(spec, root)
    assert out == output_path(root, spec) and out.name == "demo.md"
    assert out.parent.as_posix().endswith("academic_notes/econ/summaries")


def test_one_call_per_topic_plus_comparison(spec, root):
    _, llm = _run(spec, root)
    assert len(llm.calls) == 3


def test_topic_prompt_uses_the_frozen_tutor_wording_and_excerpts(spec, root):
    _, llm = _run(spec, root)
    p = llm.calls[0]
    assert p.startswith("You are tutoring a student using ONLY the excerpts below")
    assert "Question: Wald. Explain Wald. Use only these excerpts." in p
    assert "[cite-cam-1]\nCameron: the Wald statistic." in p and "[cite-han-1]\nHansen: Wald tests." in p


def test_comparison_uses_first_take_passages_deduplicated_and_the_bare_instruction(spec, root):
    _, llm = _run(spec, root)
    p = llm.calls[2]
    assert "Question: Compare the two tests." in p
    assert p.count("[cite-cam-1]") == 1 and "[cite-cam-3]" in p and "cite-han-1" not in p


def test_document_layout_and_frontmatter(spec, root):
    out, _ = _run(spec, root)
    text = out.read_text(encoding="utf-8")
    front, body = text.split("\n---\n\n", 1)
    fields = {line.split(": ", 1)[0]: line.split(": ", 1)[1] for line in front.splitlines()[1:]}
    assert fields["llm_generated"] == "true" and fields["content_kind"] == "derived_summary"
    assert json.loads(fields["draft_model"]) == "fake-draft" and json.loads(fields["prompt_id"]) == "tutor_v1"
    assert json.loads(fields["spec"]) == {"id": "demo", "file": "spec.toml", "sha256": spec.sha256}
    assert json.loads(fields["plan"]) == {"file": "demo.plan.json", "sha256": "planhash"}
    refs = json.loads(fields["indexer_source_refs"])
    assert [r["chunk_id"] for r in refs] == ["cam-1", "han-1", "cam-3"]
    assert set(refs[0]) == {"path", "file_id", "chunk_id", "citation"}
    assert str(root) not in text
    assert body.startswith("# Demo guide\n\nEach section below was written")
    assert "## A static note\n\nNote body text." in body
    assert "## Wald\n\nANSWER 1\n\n**Retrieved sources**\n\n- [cite-cam-1] `academic_notes/econ/cam-1.md`" in body
    assert "## Compare\n\nANSWER 3" in body and body.count("---") >= 3


def test_draft_is_loadable_by_summary_enhance(spec, root, tmp_path):
    import json as _json
    chunk_file = tmp_path / "hub" / ".index" / "chunks" / "econ.json"
    chunk_file.parent.mkdir(parents=True)
    chunk_file.write_text(_json.dumps(CHUNKS), encoding="utf-8")
    out, _ = _run(spec, root)
    guide = load_guide(out)
    assert [s.chunk_id for s in guide.sources] == ["cam-1", "han-1", "cam-3"]


def test_tag_names_the_variant_and_is_validated(spec, root):
    out, _ = _run(spec, root, tag="b2-pro")
    assert out.name == "demo.b2-pro.md"
    with pytest.raises(DraftError, match="tag"):
        _run(spec, root, tag="bad tag!")


def test_existing_output_is_not_overwritten_without_force(spec, root):
    out, _ = _run(spec, root)
    out.write_text("precious", encoding="utf-8")
    with pytest.raises(DraftError, match="exists"):
        _run(spec, root)
    assert out.read_text(encoding="utf-8") == "precious"
    _run(spec, root, force=True)
    assert "llm_generated" in out.read_text(encoding="utf-8")


def test_pending_entries_block_unless_explicitly_accepted(spec, root):
    plan = _plan()
    plan.topics[0].entries[1].status = "pending"
    with pytest.raises(PendingReviewError):
        _run(spec, root, plan=plan)
    out, llm = _run(spec, root, plan=plan, accept_unreviewed=True)
    assert "[cite-han-1]" in llm.calls[0]


def test_dropped_entries_are_left_out(spec, root):
    plan = _plan()
    plan.topics[0].entries[1].status = "dropped"
    _, llm = _run(spec, root, plan=plan)
    assert "cite-han-1" not in llm.calls[0]


def test_missing_chunk_text_is_an_error_before_any_call(spec, root):
    llm = FakeLLM()
    with pytest.raises(DraftError, match="cam-1"):
        draft_guide(spec, _plan(), root=root, llm=llm, chunks=[c for c in CHUNKS if c["chunk_id"] != "cam-1"], now=NOW)
    assert llm.calls == []


def test_guide_v1_prompt_is_used_when_selected(make_spec, root):
    guide_spec = make_spec(TOPICS, header='[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n[draft]\nprompt = "guide_v1"\n\n')
    _, llm = _run(guide_spec, root)
    assert "Section: Wald" in llm.calls[0] and "tutoring" not in llm.calls[0]


def test_unusable_response_is_retried_once_then_fails(spec, root):
    out, llm = _run(spec, root, llm=FakeLLM([UnusableResponse("truncated")]))
    assert len(llm.calls) == 4 and out.is_file()
    with pytest.raises(DraftError, match="usable"):
        _run(spec, root, llm=FakeLLM([UnusableResponse("a"), UnusableResponse("b")]), force=True)


def test_other_llm_errors_propagate_and_nothing_is_written(spec, root):
    with pytest.raises(RuntimeError):
        _run(spec, root, llm=FakeLLM([RuntimeError("503")]))
    assert not output_path(root, spec).exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_prompts.py tests/agent/study_guide/test_study_guide_draft.py -q`
Expected: `ModuleNotFoundError: agent.study_guide.prompts`.

- [ ] **Step 3: Implement**

```python
# agent/study_guide/prompts.py
"""Frozen prompt templates for the draft stage.

TUTOR_V1 is a copy of rag_agent._ANSWER_PROMPT_TEMPLATE taken on 2026-10-05 so a baseline
reproduction does not change if the tutor's prompt is edited later (see the recovered recipe in
docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md). GUIDE_V1 is a
study-guide oriented prompt for new work."""
from __future__ import annotations

TUTOR_V1_TEMPLATE = """You are tutoring a student using ONLY the excerpts below, drawn from \
their own course materials. Answer their question clearly and thoroughly, the way a good TA would \
explain it -- but do not introduce any claim, fact, or worked step that isn't supported by the \
excerpts. If the excerpts don't actually contain enough to answer the question, say so plainly \
rather than filling the gap from general knowledge.

When you use something from an excerpt, cite it inline using the citation label given with it \
(e.g. "(§3.7, p. 44)"), so the student can find it in their own materials.
{history_block}{gap_hint_block}
Excerpts:
{excerpts_block}

Question: {question}

Answer:"""

_TUTOR_V1_SUFFIX = ("Use only these excerpts. Cite each substantive claim by its exact source label. "
                    "State plainly where the excerpts do not support an answer.")

GUIDE_V1_TEMPLATE = """You are writing one section of a thorough study guide for a graduate student, \
using ONLY the excerpts below, which come from the student's own course materials (textbooks, class \
notes, slides, recitations). Do not introduce any claim, fact, or worked step that is not supported by \
the excerpts; if they do not contain enough, say so plainly instead of filling the gap from general \
knowledge.

Write at least 800 words, organized under short ### sub-headings. Build the explanation step by step: \
assumptions, the statistic and how it is computed, its distribution and the decision rule, intuition, \
when it is valid or breaks down, and common pitfalls. Where the sources use different notation or \
disagree (for example a textbook versus class notes), say so explicitly and cite both. Class notes may \
contain transcription errors; prefer the textbook where they conflict and say so.

Cite every substantive point inline with the citation label given with its excerpt, for example \
"(§3.7, p. 44)".

Section: {title}
Focus: {instruction}

Excerpts:
{excerpts_block}

Section text:"""


def _excerpts_block(excerpts: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"[{citation}]\n{text}" for citation, text in excerpts)


def tutor_v1_question(title: str, instruction: str) -> str:
    return f"{title}. {instruction} {_TUTOR_V1_SUFFIX}"


def tutor_v1_prompt(question: str, excerpts: list[tuple[str, str]]) -> str:
    return TUTOR_V1_TEMPLATE.format(
        history_block="", gap_hint_block="", excerpts_block=_excerpts_block(excerpts), question=question)


def guide_v1_prompt(title: str, instruction: str, excerpts: list[tuple[str, str]]) -> str:
    return GUIDE_V1_TEMPLATE.format(title=title, instruction=instruction, excerpts_block=_excerpts_block(excerpts))
```

```python
# agent/study_guide/draft.py
"""Draft stage: one grounded, cited synthesis per topic from the plan's accepted passages, written
as a `derived_summary` (frontmatter `indexer_source_refs`) that summary_enhance can consume."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from agent.study_guide.plan import Plan, PlanEntry, accepted
from agent.study_guide.prompts import guide_v1_prompt, tutor_v1_prompt, tutor_v1_question
from agent.study_guide.spec import GuideSpec, TopicSpec
from agent.summary_enhance.llm import UnusableResponse

GENERATED_BY = "academic-rag-model/agent/study_guide/draft.py"
INTRO = ("Each section below was written from the source passages planned for that topic; the passages "
         "retrieved for each section are listed beneath it.")
_TAG_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class DraftError(Exception):
    pass


def output_path(root: str, spec: GuideSpec, tag: str = "") -> Path:
    name = f"{spec.id}.{tag}.md" if tag else f"{spec.id}.md"
    return Path(root) / "academic_notes" / spec.course / "summaries" / name


def _excerpts(entries: list[PlanEntry], text_by_id: dict[str, str]) -> list[tuple[str, str]]:
    missing = [e.chunk_id for e in entries if e.chunk_id not in text_by_id]
    if missing:
        raise DraftError(f"passages missing from the chunk store (re-run plan): {', '.join(missing)}")
    return [(e.citation, text_by_id[e.chunk_id]) for e in entries]


def _generate(llm, prompt: str) -> str:
    for _ in range(2):
        try:
            text = (llm.generate_text(prompt) or "").strip()
        except UnusableResponse:
            continue
        if text:
            return text
    raise DraftError("the model returned no usable text twice")


def _topic_prompt(spec: GuideSpec, topic: TopicSpec, excerpts: list[tuple[str, str]]) -> str:
    if spec.prompt == "guide_v1":
        return guide_v1_prompt(topic.title, topic.instruction, excerpts)
    return tutor_v1_prompt(tutor_v1_question(topic.title, topic.instruction), excerpts)


def _section(title: str, answer: str, entries: list[PlanEntry]) -> str:
    sources = "\n".join(f"- [{e.citation}] `{e.path}`" for e in entries)
    return f"## {title}\n\n{answer}\n\n**Retrieved sources**\n\n{sources}"


def draft_guide(spec: GuideSpec, plan: Plan, *, root: str, llm, chunks: list[dict] | None = None,
                tag: str = "", force: bool = False, accept_unreviewed: bool = False,
                plan_path: str = "", plan_sha256: str = "", now: str | None = None) -> Path:
    if tag and not _TAG_RE.match(tag):
        raise DraftError(f"tag {tag!r} may contain only letters, digits, '_' and '-'")
    out = output_path(root, spec, tag)
    if out.exists() and not force:
        raise DraftError(f"{out} already exists; pass --force to replace it")
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    text_by_id = {c["chunk_id"]: c["text"] for c in chunks}

    # resolve and validate every topic's passages before spending any API call
    per_topic: dict[str, list[PlanEntry]] = {}
    for topic in spec.topics:
        per_topic[topic.title] = accepted(plan, topic.title, accept_unreviewed=accept_unreviewed)
        _excerpts(per_topic[topic.title], text_by_id)

    blocks = [f"## {n.heading}\n\n{n.body}" for n in spec.notes]
    used: dict[str, PlanEntry] = {}
    for topic in spec.topics:
        entries = per_topic[topic.title]
        answer = _generate(llm, _topic_prompt(spec, topic, _excerpts(entries, text_by_id)))
        blocks.append(_section(topic.title, answer, entries))
        for e in entries:
            used.setdefault(e.chunk_id, e)
    for cmp_ in spec.comparisons:
        chosen: list[PlanEntry] = []
        seen: set[str] = set()
        for title in cmp_.from_topics:
            for e in per_topic[title][:cmp_.take]:
                if e.chunk_id not in seen:
                    seen.add(e.chunk_id)
                    chosen.append(e)
        excerpts = _excerpts(chosen, text_by_id)
        if spec.prompt == "guide_v1":
            prompt = guide_v1_prompt(cmp_.title, cmp_.instruction, excerpts)
        else:
            prompt = tutor_v1_prompt(cmp_.instruction, excerpts)
        blocks.append(_section(cmp_.title, _generate(llm, prompt), chosen))
        for e in chosen:
            used.setdefault(e.chunk_id, e)

    refs = [{"path": e.path, "file_id": e.file_id, "chunk_id": e.chunk_id, "citation": e.citation}
            for e in used.values()]
    front = {
        "title": json.dumps(spec.title, ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "derived_summary",
        "generated_by": GENERATED_BY,
        "draft_model": json.dumps(getattr(llm, "model", spec.draft_model)),
        "prompt_id": json.dumps(spec.prompt),
        "label_match": json.dumps(spec.label_match),
        "generated_at": now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": json.dumps({"id": spec.id, "file": Path(spec.path).name, "sha256": spec.sha256}),
        "plan": json.dumps({"file": Path(plan_path).name if plan_path else "", "sha256": plan_sha256}),
        "indexer_source_refs": json.dumps(refs, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front.items()) + "---\n\n"
    document = frontmatter + f"# {spec.title}\n\n{INTRO}\n\n" + "\n\n---\n\n".join(blocks) + "\n"

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    try:
        tmp.write_text(document, encoding="utf-8", newline="\n")
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: all pass. The one-time transcription check: also run
`python -c "from agent.rag.rag_agent import _ANSWER_PROMPT_TEMPLATE as T; from agent.study_guide.prompts import TUTOR_V1_TEMPLATE as F; print(T == F)"` and expect `True`.

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/prompts.py agent/study_guide/draft.py tests/agent/study_guide/test_study_guide_prompts.py tests/agent/study_guide/test_study_guide_draft.py
git commit -m "feat(study_guide): frozen prompts and the draft stage" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: CLI (plan, apply-review, draft, run), baseline spec, README

**Files:**
- Create: `agent/study_guide/cli.py`, `agent/study_guide/__main__.py`, `agent/study_guide/README.md`
- Create: `guide_specs/README.md`, `guide_specs/econometrics/wald_lm_lr_tests.toml`
- Test: `tests/agent/study_guide/test_study_guide_cli.py`

**Interfaces:**
- Consumes: Tasks 1-4. `summary_enhance.llm.GeminiClient(client, model)`.
- Produces (`cli.py`): `default_root() -> str`; `plan_path_for(root, spec) -> Path`; `review_path_for(root, spec) -> Path`; `cmd_plan(spec_path, root, *, client=None, search=None, force=False, chunks=None, cards=None) -> int`; `cmd_apply_review(plan_path, decisions_path) -> int`; `cmd_draft(spec_path, root, *, plan_path=None, llm=None, model=None, tag="", force=False, dry_run=False, accept_unreviewed=False, env_file=None, chunks=None, cards=None) -> int`; `main(argv=None) -> int`. Exit codes: 0 ok, 1 no client, 2 input/plan/spec/draft error, 4 model call failed. (`enhance` subcommand is added in Task 8.)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_cli.py
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import (
    cmd_apply_review, cmd_draft, cmd_plan, main, plan_path_for, review_path_for,
)
from agent.study_guide.spec import load_spec
from sg_helpers import CARDS, CHUNKS, FakeLLM, StubSearch, hit

SPEC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"

  [[topic.source]]
  kind = "discover"
  query = "wald"
  min_score = 0.5
  max = 3
"""


@pytest.fixture
def spec_file(make_spec, tmp_path):
    make_spec(SPEC)
    return tmp_path / "spec.toml"


@pytest.fixture
def search():
    return StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})


def _plan(spec_file, root, search, **kw):
    return cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS, **kw)


def test_plan_writes_ledger_and_review_items(spec_file, root, search, capsys):
    assert _plan(spec_file, root, search) == 0
    spec = load_spec(spec_file)
    plan = json.loads(plan_path_for(root, spec).read_text(encoding="utf-8"))
    assert plan["spec_id"] == "demo" and plan["topics"][0]["entries"][0]["status"] == "accepted"
    items = json.loads(review_path_for(root, spec).read_text(encoding="utf-8"))
    assert [i["key"] for i in items] == ["Wald|cam-1", "Wald|han-1"]
    out = capsys.readouterr().out
    assert "1 accepted" in out and "1 pending" in out and "Wald" in out
    assert plan_path_for(root, spec).as_posix().endswith("academic_notes/econ/guide_plans/demo.plan.json")


def test_plan_refuses_to_overwrite_without_force(spec_file, root, search):
    assert _plan(spec_file, root, search) == 0
    assert _plan(spec_file, root, search) == 2
    assert _plan(spec_file, root, search, force=True) == 0


def test_plan_reports_spec_and_plan_errors_as_input_errors(tmp_path, root, search, make_spec):
    assert cmd_plan(str(tmp_path / "missing.toml"), root, search=search) == 2
    make_spec(SPEC.replace('labels = ["7.2"]', 'labels = ["99"]').replace('kind = "discover"', 'kind = "discover"\n  max_per_file = 1'))
    empty = StubSearch({"textbook": []})
    assert cmd_plan(str(tmp_path / "spec.toml"), root, search=empty, chunks=CHUNKS, cards=CARDS) == 2


def test_plan_without_a_client_or_search_is_exit_1(spec_file, root):
    assert cmd_plan(str(spec_file), root) == 1


def test_apply_review_updates_the_plan(spec_file, root, search, tmp_path, capsys):
    _plan(spec_file, root, search)
    spec = load_spec(spec_file)
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps({"Wald|han-1": "drop"}), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(decisions)) == 0
    entries = json.loads(plan_path_for(root, spec).read_text(encoding="utf-8"))["topics"][0]["entries"]
    assert [e["status"] for e in entries] == ["accepted", "dropped"]
    assert "1 dropped" in capsys.readouterr().out
    decisions.write_text(json.dumps({"Wald|nope": "keep"}), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(decisions)) == 2


def _decided(spec_file, root, search, tmp_path):
    _plan(spec_file, root, search)
    spec = load_spec(spec_file)
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"Wald|han-1": "keep"}), encoding="utf-8")
    cmd_apply_review(str(plan_path_for(root, spec)), str(d))
    return spec


def test_draft_end_to_end(spec_file, root, search, tmp_path):
    spec = _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    assert cmd_draft(str(spec_file), root, llm=llm, chunks=CHUNKS, cards=CARDS) == 0
    assert (Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md").is_file()
    assert len(llm.calls) == 1


def test_draft_blocks_on_pending_unless_accepted(spec_file, root, search):
    _plan(spec_file, root, search)
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True) == 0


def test_draft_dry_run_prints_counts_and_makes_no_call(spec_file, root, search, tmp_path, capsys):
    _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    assert cmd_draft(str(spec_file), root, llm=llm, dry_run=True, chunks=CHUNKS, cards=CARDS) == 0
    out = capsys.readouterr().out
    assert llm.calls == [] and "DRY RUN" in out and "1 call" in out and "2 passages" in out and "demo.md" in out


def test_draft_rejects_a_stale_plan_before_any_call(spec_file, root, search, tmp_path):
    _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    gone = [c for c in CHUNKS if c["chunk_id"] != "cam-1"]
    assert cmd_draft(str(spec_file), root, llm=llm, chunks=gone, cards=CARDS) == 2
    assert llm.calls == []


def test_draft_without_a_plan_file_is_an_input_error(spec_file, root):
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2


def test_draft_refuses_overwrite_and_reports_model_failures(spec_file, root, search, tmp_path):
    _decided(spec_file, root, search, tmp_path)
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 0
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2
    assert cmd_draft(str(spec_file), root, llm=FakeLLM([RuntimeError("503")]), chunks=CHUNKS, cards=CARDS, force=True) == 4


def test_draft_model_override_is_recorded(spec_file, root, search, tmp_path, monkeypatch):
    _decided(spec_file, root, search, tmp_path)
    seen = {}

    class Capturing(FakeLLM):
        def __init__(self, client, model):
            super().__init__()
            self.model = model
            seen["model"] = model

    monkeypatch.setattr(cli, "GeminiClient", Capturing)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: object())
    assert cmd_draft(str(spec_file), root, model="gemini-test", chunks=CHUNKS, cards=CARDS) == 0
    assert seen["model"] == "gemini-test"


def test_main_dispatches(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(cli, "cmd_plan", lambda spec, root, **kw: calls.setdefault("plan", (spec, kw)) and 0)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: "client")
    assert main(["plan", "s.toml", "--root", str(tmp_path), "--force"]) == 0
    spec, kw = calls["plan"]
    assert spec == "s.toml" and kw["force"] is True and kw["client"] == "client"
    monkeypatch.setattr(cli, "cmd_draft", lambda spec, root, **kw: calls.setdefault("draft", kw) and 0)
    assert main(["draft", "s.toml", "--root", str(tmp_path), "--tag", "t", "--dry-run", "--model", "m",
                 "--accept-unreviewed"]) == 0
    assert calls["draft"]["tag"] == "t" and calls["draft"]["dry_run"] and calls["draft"]["model"] == "m"
    assert calls["draft"]["accept_unreviewed"] is True


def test_run_plans_and_stops_for_review_without_yes(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "cmd_plan", lambda spec, root, **kw: seen.append("plan") or 0)
    monkeypatch.setattr(cli, "cmd_draft", lambda spec, root, **kw: seen.append("draft") or 0)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: "client")
    assert main(["run", "s.toml", "--root", str(tmp_path)]) == 0 and seen == ["plan"]
    seen.clear()
    assert main(["run", "s.toml", "--root", str(tmp_path), "--yes"]) == 0 and seen == ["plan", "draft"]


def test_baseline_spec_for_the_wald_guide_is_valid_and_matches_the_recovered_recipe():
    path = Path(__file__).resolve().parents[3] / "guide_specs" / "econometrics" / "wald_lm_lr_tests.toml"
    spec = load_spec(path)
    assert (spec.id, spec.course, spec.prompt, spec.label_match) == ("wald_lm_lr_tests", "econometrics", "tutor_v1", "citation-substring")
    assert spec.draft_model == "gemini-3.1-flash-lite" and (spec.top_k, spec.file_top_k) == (180, 80)
    assert [t.title for t in spec.topics] == [
        "Cameron & Trivedi Section 7.2: Wald test",
        "Cameron & Trivedi Section 7.3: likelihood ratio test",
        "Cameron & Trivedi Section 7.3.5: Lagrange multiplier test",
        "Hansen Section 9.10 and 9.11: Wald tests",
        "Hansen Section 9.11 reference check: likelihood ratio test",
        "Hansen Section 9.17: score (Lagrange multiplier) test",
    ]
    lr = spec.topics[1].sources[0]
    assert (lr.kind, lr.book, lr.labels, lr.exclude_labels, lr.max) == (
        "section", "Cameron_Microeconometrics", ("7.3.1", "7.3.2", "7.3.3", "7.3.4"), ("7.3.5",), 12)
    assert spec.topics[3].sources[0].labels == ("9.10", "9.11") and spec.topics[3].sources[0].book == "Hansen_ECONOMETRICS"
    assert len(spec.notes) == 1 and spec.notes[0].heading == "Source-reference discrepancy"
    comparison = spec.comparisons[0]
    assert comparison.title == "Comparing and choosing among the three tests" and comparison.take == 3
    assert comparison.from_topics == tuple(t.title for i, t in enumerate(spec.topics) if i != 4)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_cli.py -q`
Expected: `ModuleNotFoundError: agent.study_guide.cli`.

- [ ] **Step 3: Implement**

```python
# agent/study_guide/cli.py
"""Command line for the study guide pipeline.

    python -m agent.study_guide plan   <spec> [--root R] [--force] [--env-file F]
    python -m agent.study_guide apply-review <plan> --decisions <file>
    python -m agent.study_guide draft  <spec> [--root R] [--plan P] [--model M] [--tag T] [--force]
                                       [--dry-run] [--accept-unreviewed] [--env-file F]
    python -m agent.study_guide run    <spec> [--yes]         (plan; with --yes also draft)

Design: docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md. From a git
worktree pass --root <main checkout>/ai-sandbox/academic-hub and --env-file <main>/ai-sandbox/.env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from agent.study_guide.draft import DraftError, draft_guide, output_path
from agent.study_guide.plan import (
    PlanError, apply_decisions, build_plan, check_fresh, load_plan, pending_entries, plan_sha256,
    save_plan, write_review_items,
)
from agent.study_guide.spec import SpecError, load_spec
from agent.summary_enhance.llm import GeminiClient

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_LLM = 0, 1, 2, 4


def default_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


def _vault_dir(root: str, spec) -> Path:
    return Path(root) / "academic_notes" / spec.course


def plan_path_for(root: str, spec) -> Path:
    return _vault_dir(root, spec) / "guide_plans" / f"{spec.id}.plan.json"


def review_path_for(root: str, spec) -> Path:
    return _vault_dir(root, spec) / "guide_plans" / f"{spec.id}.review.json"


def _paid_client(env_file: str | None):
    from core.env.gemini_utils import get_gemini_client, load_dotenv_override
    if env_file:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
    else:
        load_dotenv_override()
    return get_gemini_client("PAID_GEMINI_KEY")


def _summary(plan) -> list[str]:
    lines = []
    for topic in plan.topics:
        counts = {s: sum(1 for e in topic.entries if e.status == s) for s in ("accepted", "pending", "dropped")}
        lines.append(f"  {topic.title}: {counts['accepted']} accepted, {counts['pending']} pending"
                     + (f", {counts['dropped']} dropped" if counts["dropped"] else ""))
    return lines


def cmd_plan(spec_path: str, root: str, *, client=None, search=None, force: bool = False,
             chunks=None, cards=None) -> int:
    try:
        spec = load_spec(spec_path)
    except SpecError as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    out = plan_path_for(root, spec)
    if out.exists() and not force:
        print(f"ERROR: {out} already exists; pass --force to replace it (this discards earlier review decisions)")
        return EXIT_INPUT
    if client is None and search is None:
        print("ERROR: no Gemini client available (PAID_GEMINI_KEY)")
        return EXIT_NO_CLIENT
    try:
        plan = build_plan(spec, root, client=client, search=search, chunks=chunks, cards=cards)
    except PlanError as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    save_plan(plan, out)
    write_review_items(plan, review_path_for(root, spec))
    print(f"Wrote {out}")
    print(f"Review items: {review_path_for(root, spec)}")
    print("\n".join(_summary(plan)))
    pending = len(pending_entries(plan))
    if pending:
        print(f"{pending} discovered passage(s) need review (publish the review Artifact, then apply-review).")
    return EXIT_OK


def cmd_apply_review(plan_path: str, decisions_path: str) -> int:
    try:
        plan = load_plan(plan_path)
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
        if not isinstance(decisions, dict):
            raise PlanError("decisions file must be a JSON object of key -> keep|drop")
        new = apply_decisions(plan, decisions)
    except (PlanError, OSError, json.JSONDecodeError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    save_plan(new, plan_path)
    print("\n".join(_summary(new)))
    return EXIT_OK


def _load_plan_for(spec, root, plan_path, chunks, cards):
    path = Path(plan_path) if plan_path else plan_path_for(root, spec)
    plan = load_plan(path)
    if plan.spec_id != spec.id:
        raise PlanError(f"plan {path.name} is for guide {plan.spec_id!r}, not {spec.id!r}")
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    if cards is None:
        from core.indexer.index_card import load_shard
        cards = load_shard(root, spec.course)
    stale = check_fresh(plan, chunks=chunks, cards=cards)
    if stale:
        raise PlanError("the plan is stale (re-run plan --force):\n  " + "\n  ".join(stale))
    return plan, path, chunks


def cmd_draft(spec_path: str, root: str, *, plan_path: str | None = None, llm=None, model: str | None = None,
              tag: str = "", force: bool = False, dry_run: bool = False, accept_unreviewed: bool = False,
              env_file: str | None = None, chunks=None, cards=None) -> int:
    try:
        spec = load_spec(spec_path)
        plan, path, chunks = _load_plan_for(spec, root, plan_path, chunks, cards)
        if dry_run:
            from agent.study_guide.plan import accepted
            counts = [len(accepted(plan, t.title, accept_unreviewed=accept_unreviewed)) for t in spec.topics]
            calls = len(spec.topics) + len(spec.comparisons)
            print(f"DRY RUN: {calls} call{'s' if calls != 1 else ''} to {model or spec.draft_model}, "
                  f"{sum(counts)} passages across {len(counts)} topics ({', '.join(map(str, counts))}), "
                  f"prompt {spec.prompt}")
            print(f"DRY RUN: would write {output_path(root, spec, tag)}")
            return EXIT_OK
        if llm is None:
            client = _paid_client(env_file)
            if client is None:
                return EXIT_NO_CLIENT
            llm = GeminiClient(client, model or spec.draft_model)
        out = draft_guide(spec, plan, root=root, llm=llm, chunks=chunks, tag=tag, force=force,
                          accept_unreviewed=accept_unreviewed, plan_path=str(path), plan_sha256=plan_sha256(path))
    except (SpecError, PlanError, DraftError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM
    print(f"Wrote {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m agent.study_guide", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, spec=True):
        if spec:
            sp.add_argument("spec", help="path to a guide spec (.toml)")
        sp.add_argument("--root", default=default_root(), help="academic-hub root (corpus)")
        sp.add_argument("--env-file", help="load PAID_GEMINI_KEY from this .env")

    sp = sub.add_parser("plan")
    common(sp)
    sp.add_argument("--force", action="store_true", help="replace an existing plan")

    sp = sub.add_parser("apply-review")
    sp.add_argument("plan")
    sp.add_argument("--decisions", required=True, help="JSON object: 'Topic|chunk_id' -> keep|drop")

    sp = sub.add_parser("draft")
    common(sp)
    sp.add_argument("--plan", help="plan file (default: the spec's plan in the vault)")
    sp.add_argument("--model", help="override [models].draft")
    sp.add_argument("--tag", default="", help="name an output variant (<id>.<tag>.md)")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--accept-unreviewed", action="store_true")

    sp = sub.add_parser("run")
    common(sp)
    sp.add_argument("--yes", action="store_true", help="after planning, draft using the plan as it is")

    args = p.parse_args(argv)
    if args.command == "apply-review":
        return cmd_apply_review(args.plan, args.decisions)
    if args.command in ("plan", "run"):
        client = _paid_client(args.env_file)
        code = cmd_plan(args.spec, args.root, client=client, force=getattr(args, "force", False))
        if args.command == "plan" or code != EXIT_OK or not args.yes:
            return code
        return cmd_draft(args.spec, args.root, accept_unreviewed=True, env_file=args.env_file)
    return cmd_draft(args.spec, args.root, plan_path=args.plan, model=args.model, tag=args.tag, force=args.force,
                     dry_run=args.dry_run, accept_unreviewed=args.accept_unreviewed, env_file=args.env_file)


if __name__ == "__main__":
    sys.exit(main())
```

```python
# agent/study_guide/__main__.py
import sys

from agent.study_guide.cli import main

sys.exit(main())
```

```toml
# guide_specs/econometrics/wald_lm_lr_tests.toml
# Baseline: reproduces the 2026-10-03 recipe that produced the first Wald/LR/LM study guide
# (recovered script: docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md).
# Same retrieval parameters, same prompt wording, same draft model, legacy label matching.

[guide]
id = "wald_lm_lr_tests"
title = "Wald, Lagrange Multiplier, and Likelihood Ratio Tests"
course = "econometrics"

[models]
draft = "gemini-3.1-flash-lite"
enhance = "gemini-3.8-flash"

[draft]
prompt = "tutor_v1"
label_match = "citation-substring"
top_k = 180
file_top_k = 80

[[note]]
heading = "Source-reference discrepancy"
body = "The course syllabus points to Hansen §§9.9, 9.11, and 9.16 for these tests. In the converted Hansen chapter, the headings identify §9.9 as *t*-ratios and the abuse of testing, §9.10 as Wald tests, §9.11 as homoskedastic Wald tests, §9.16 as Hausman tests, and §9.17 as score tests. Chapter 9 contains no section headed likelihood ratio test; the only matching phrase found in the chapter describes a criterion-based statistic as “likelihood-ratio-like.” The Hansen entries below therefore follow the actual chapter headings and preserve the syllabus mismatch rather than attributing unrelated sections to these tests."

[[topic]]
title = "Cameron & Trivedi Section 7.2: Wald test"
instruction = "Explain the Wald test: hypotheses, unrestricted estimation, statistic and covariance, asymptotic distribution, decision rule, examples, and invariance cautions."

  [[topic.source]]
  kind = "section"
  book = "Cameron_Microeconometrics"
  labels = ["7.2"]
  exclude_labels = []
  query = "Wald test linear nonlinear hypotheses covariance chi-square invariance"
  max = 12

[[topic]]
title = "Cameron & Trivedi Section 7.3: likelihood ratio test"
instruction = "Explain the likelihood ratio test: restricted/unrestricted MLE, exact statistic if given, degrees of freedom and asymptotic distribution, decision rule, assumptions, examples, and choice versus Wald/LM."

  [[topic.source]]
  kind = "section"
  book = "Cameron_Microeconometrics"
  labels = ["7.3.1", "7.3.2", "7.3.3", "7.3.4"]
  exclude_labels = ["7.3.5"]
  query = "likelihood ratio test restricted unrestricted maximum likelihood chi-square"
  max = 12

[[topic]]
title = "Cameron & Trivedi Section 7.3.5: Lagrange multiplier test"
instruction = "Explain the LM/score test: null-restricted estimator, score and scaling, statistic and asymptotic reference distribution, decision rule, computation, examples, and comparison with LR/Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron_Microeconometrics"
  labels = ["7.3.1", "7.3.3", "7.3.5"]
  exclude_labels = []
  query = "Lagrange multiplier score test restricted estimator score statistic information chi-square"
  max = 12

[[topic]]
title = "Hansen Section 9.10 and 9.11: Wald tests"
instruction = "Explain Hansen's general and homoskedastic Wald tests: hypotheses, statistic, covariance, distribution and degrees of freedom, critical-value/p-value rule, assumptions and interpretation."

  [[topic.source]]
  kind = "section"
  book = "Hansen_ECONOMETRICS"
  labels = ["9.10", "9.11"]
  exclude_labels = []
  query = "Wald tests general and homoskedastic statistics covariance chi-square F"
  max = 12

[[topic]]
title = "Hansen Section 9.11 reference check: likelihood ratio test"
instruction = "The course syllabus cites section 9.11 for a likelihood ratio test. Explain what the supplied section 9.11 excerpt actually covers and whether it provides a likelihood ratio test. Do not substitute another test or fill gaps with general knowledge; cite the evidence and state what is unavailable."

  [[topic.source]]
  kind = "section"
  book = "Hansen_ECONOMETRICS"
  labels = ["9.11"]
  exclude_labels = []
  query = "Section 9.11 likelihood ratio test compare likelihood statistic restricted unrestricted"
  max = 12

[[topic]]
title = "Hansen Section 9.17: score (Lagrange multiplier) test"
instruction = "Explain the score/LM test: restricted estimation, score and information/Hessian scaling, statistic, decision rule, relation to homoskedastic Wald/F in normal regression, and computational advantage. Cite each point and identify any details not in the excerpts."

  [[topic.source]]
  kind = "section"
  book = "Hansen_ECONOMETRICS"
  labels = ["9.17"]
  exclude_labels = []
  query = "score test restricted estimates gradient Hessian statistic chi-square normal regression"
  max = 12

[[comparison]]
title = "Comparing and choosing among the three tests"
instruction = "Compare the Wald, likelihood ratio, and Lagrange multiplier/score tests using only these selected Cameron & Trivedi and Hansen passages. Explain which estimates each requires, what each statistic measures, shared asymptotic relationships where stated, computation choices, and supported cautions. The retrieved Hansen passages do not supply a likelihood ratio section; make that limitation explicit. Cite every substantive comparison and do not fill gaps from outside knowledge."
from = [
  "Cameron & Trivedi Section 7.2: Wald test",
  "Cameron & Trivedi Section 7.3: likelihood ratio test",
  "Cameron & Trivedi Section 7.3.5: Lagrange multiplier test",
  "Hansen Section 9.10 and 9.11: Wald tests",
  "Hansen Section 9.17: score (Lagrange multiplier) test",
]
take = 3
```

```markdown
<!-- agent/study_guide/README.md -->
# study_guide

Reusable pipeline for building study guides from indexed course material: a **guide spec**
(TOML, in `guide_specs/<course>/`) is resolved to a **source plan**, which feeds a **draft**
(grounded, cited) and, optionally, an **enhance** pass (`agent.summary_enhance`).

    python -m agent.study_guide plan   guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --env-file <.env>
    python -m agent.study_guide apply-review <plan> --decisions <decisions.json>
    python -m agent.study_guide draft  guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --tag b0 --dry-run
    python -m agent.study_guide draft  <spec> --root <hub> --tag b0

- **Spec:** topics, instructions, per-topic source rules (`section` = pinned textbook sections,
  `file` = pinned class notes/slides, `discover` = bounded search that can exclude an existing
  guide's chunks), per-stage models, prompt id (`tutor_v1` reproduces the 2026-10-03 recipe).
- **Plan:** `<hub>/academic_notes/<course>/guide_plans/<id>.plan.json` (ledger, no passage text)
  and `<id>.review.json` (items for the review Artifact). Pinned passages are accepted;
  discovered ones are `pending` until reviewed (`--accept-unreviewed` overrides, explicitly).
- **Draft:** `<hub>/academic_notes/<course>/summaries/<id>[.<tag>].md`, a `derived_summary`
  whose `indexer_source_refs` lists every passage used.
- Never overwrites without `--force`, never runs git, outputs stay inside `academic_notes/`.
- Design: `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`.
  Provenance of the baseline: `docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`.
- Tests: `python -m pytest tests/agent/study_guide -q` (no network).
```

```markdown
<!-- guide_specs/README.md -->
# guide_specs

Guide specs for `python -m agent.study_guide`: configuration for the code (topics, instructions,
section labels, source rules, models). They contain no study content or source text; generated
guides live in the notes vault. One folder per course, one TOML file per guide.
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: all pass. If the spec-file test reports a TOML error, the unicode characters in the note (`§`, curly quotes) must be saved as UTF-8; `load_spec` decodes as UTF-8.

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/cli.py agent/study_guide/__main__.py agent/study_guide/README.md guide_specs/README.md guide_specs/econometrics/wald_lm_lr_tests.toml tests/agent/study_guide/test_study_guide_cli.py
git commit -m "feat(study_guide): CLI (plan, apply-review, draft, run), baseline Wald spec, README" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: summary_enhance — extra sources and source-map fields

**Files:**
- Replace: `agent/summary_enhance/source_loader.py`
- Modify: `agent/summary_enhance/render.py` (source_map entries)
- Modify: `tests/agent/summary_enhance/conftest.py` (add one chunk)
- Test: `tests/agent/summary_enhance/test_summary_enhance_extra_sources.py`

**Interfaces:**
- Consumes: existing `load_guide`, `GuideInput`, `SourceChunk`, `MissingSourcesError`, `locate_vault`.
- Produces:
  - `SourceChunk` gains `doc_type: str = ""`, `offering: str = ""`.
  - `ExtraSource(topic: str, chunk_id: str, file_id: str, path: str, citation: str, doc_type: str = "", offering: str = "")` (frozen dataclass).
  - `GuideInput` gains `topic_labels: dict[str, frozenset[str]]` (normalized topic title → labels; default `{}`) and `labels_for(title: str) -> set[str]` (that topic's labels if mapped, else every label).
  - `load_guide(guide_path, extra_sources: Sequence[ExtraSource] | None = None) -> GuideInput`: extras are appended after the guide's own refs (labels continue), de-duplicated by `chunk_id` (an extra whose chunk the guide already cites reuses that label), missing/mismatched extras raise `MissingSourcesError`.
  - `render` `source_map` entries gain `doc_type` and `offering` keys only when non-empty.

- [ ] **Step 1: Add a chunk to the conftest and write the failing tests**

In `tests/agent/summary_enhance/conftest.py`, add this entry to the `CHUNKS` list (after the `unused-1` entry):

```python
    {"chunk_id": "notes-1", "file_id": "notes", "text": "Class notes: the Wald statistic is a quadratic form."},
```

```python
# tests/agent/summary_enhance/test_summary_enhance_extra_sources.py
import json

import pytest

from agent.summary_enhance.render import render
from agent.summary_enhance.schema import Block, Enhanced, Section, Topic
from agent.summary_enhance.source_loader import ExtraSource, MissingSourcesError, load_guide


def _extra(topic, chunk_id="notes-1", file_id="notes", **kw):
    return ExtraSource(topic, chunk_id, file_id, "academic_notes/econ/class_2024/notes.md", "Notes p. 3", **kw)


def test_extras_follow_the_guides_own_refs_with_continuing_labels(vault):
    guide = load_guide(vault.guide, [_extra("Wald", doc_type="ta_notes", offering="class_2024")])
    assert [s.label for s in guide.sources] == ["S1", "S2", "S3", "S4"]
    extra = guide.sources[3]
    assert (extra.chunk_id, extra.doc_type, extra.offering, extra.citation) == ("notes-1", "ta_notes", "class_2024", "Notes p. 3")
    assert extra.text.startswith("Class notes:")


def test_extra_that_the_guide_already_cites_reuses_its_label(vault):
    guide = load_guide(vault.guide, [_extra("Wald", chunk_id="cam-1", file_id="cam")])
    assert len(guide.sources) == 3
    assert guide.labels_for("Wald") == {"S1"}


def test_topic_labels_are_per_topic_and_normalized(vault):
    guide = load_guide(vault.guide, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam"),
                                     _extra("LM", chunk_id="unused-1", file_id="cam")])
    assert guide.labels_for("wald") == {"S4"}
    assert guide.labels_for("  LM ") == {"S1", "S5"}
    assert guide.labels_for("Never mapped") == {"S1", "S2", "S3", "S4", "S5"}


def test_without_extras_every_topic_may_cite_every_source(vault):
    guide = load_guide(vault.guide)
    assert guide.topic_labels == {} and guide.labels_for("Anything") == {"S1", "S2", "S3"}


@pytest.mark.parametrize("extra", [_extra("Wald", chunk_id="gone-9"), _extra("Wald", file_id="WRONG")])
def test_missing_or_mismatched_extras_are_rejected(vault, extra):
    with pytest.raises(MissingSourcesError):
        load_guide(vault.guide, [extra])


def _enhanced():
    return Enhanced([Topic("Wald", [Section("A", [Block("grounded", "text", ["S4"])])])])


def test_source_map_carries_doc_type_and_offering_when_known(vault):
    guide = load_guide(vault.guide, [_extra("Wald", doc_type="ta_notes", offering="class_2024")])
    text = render(guide, _enhanced(), model="m", generated_at="t", worked_example=False, min_words=1)
    front = text.split("\n---\n\n", 1)[0]
    smap = json.loads(next(l for l in front.splitlines() if l.startswith("source_map: "))[len("source_map: "):])
    assert smap == [{"chunk_id": "notes-1", "file_id": "notes", "path": "academic_notes/econ/class_2024/notes.md",
                     "citation": "Notes p. 3", "doc_type": "ta_notes", "offering": "class_2024",
                     "used_in": ["Wald > A"]}]


def test_source_map_omits_empty_fields(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    text = render(guide, _enhanced(), model="m", generated_at="t", worked_example=False, min_words=1)
    entry = json.loads(next(l for l in text.splitlines() if l.startswith("source_map: "))[len("source_map: "):])[0]
    assert "doc_type" not in entry and "offering" not in entry
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_extra_sources.py -q`
Expected: ImportError (`cannot import name 'ExtraSource'`).

- [ ] **Step 3: Implement**

Replace `agent/summary_enhance/source_loader.py` entirely:

```python
# agent/summary_enhance/source_loader.py
"""Reads an existing RAG summary and resolves the exact indexer chunks it
cites. No similarity search: each `indexer_source_refs` entry is looked up
by (file_id, chunk_id) in the course's chunk store. The corpus root is
derived from the guide's own path (ancestor of academic_notes/) rather
than from the refs' stored `root`, which can be stale.

Extra sources (a study_guide source plan) can add chunks beyond the guide's own refs, each tied
to the topic that may cite it."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

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
    doc_type: str = ""
    offering: str = ""


@dataclass(frozen=True)
class ExtraSource:
    """A passage a topic may cite beyond the guide's own refs (from a study_guide source plan)."""
    topic: str
    chunk_id: str
    file_id: str
    path: str
    citation: str
    doc_type: str = ""
    offering: str = ""


def _norm_title(title: str) -> str:
    return " ".join(title.split()).casefold()


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
    topic_labels: dict[str, frozenset[str]] = field(default_factory=dict)

    def labels_for(self, title: str) -> set[str]:
        """The labels this topic may cite: its own planned set if it has one, else every label."""
        mapped = self.topic_labels.get(_norm_title(title))
        return set(mapped) if mapped is not None else {s.label for s in self.sources}


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


def load_guide(guide_path: str | Path, extra_sources: Sequence[ExtraSource] | None = None) -> GuideInput:
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

    topic_labels: dict[str, set[str]] = {}
    label_by_chunk = {s.chunk_id: s.label for s in sources}
    for extra in extra_sources or ():
        chunk = by_id.get(extra.chunk_id)
        if chunk is None or chunk.get("file_id") != extra.file_id:
            missing.append(extra.chunk_id)
            continue
        label = label_by_chunk.get(extra.chunk_id)
        if label is None:
            label = f"S{len(sources) + 1}"
            sources.append(SourceChunk(
                label=label, chunk_id=extra.chunk_id, file_id=extra.file_id, path=extra.path,
                citation=extra.citation, text=chunk["text"], doc_type=extra.doc_type, offering=extra.offering,
            ))
            label_by_chunk[extra.chunk_id] = label
        topic_labels.setdefault(_norm_title(extra.topic), set()).add(label)
    if missing:
        raise MissingSourcesError(missing)

    return GuideInput(
        path=path, root=root, course=course, title=title, body=body.strip("\n") + "\n",
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        rel_path=path.relative_to(root).as_posix(), sources=sources,
        topic_labels={k: frozenset(v) for k, v in topic_labels.items()},
    )
```

In `agent/summary_enhance/render.py`, replace the `source_map = [...]` block:

```python
    source_map = [
        {"chunk_id": s.chunk_id, "file_id": s.file_id, "path": s.path, "citation": s.citation,
         "used_in": used_in[s.label]}
        for s in guide.sources if s.label in used_in
    ]
```

with:

```python
    source_map = []
    for s in guide.sources:
        if s.label not in used_in:
            continue
        entry = {"chunk_id": s.chunk_id, "file_id": s.file_id, "path": s.path, "citation": s.citation}
        if s.doc_type:
            entry["doc_type"] = s.doc_type
        if s.offering:
            entry["offering"] = s.offering
        entry["used_in"] = used_in[s.label]
        source_map.append(entry)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance -q`
Expected: all pass (the new tests and every existing `summary_enhance` test; the extra conftest chunk does not disturb them).

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/source_loader.py agent/summary_enhance/render.py tests/agent/summary_enhance/conftest.py tests/agent/summary_enhance/test_summary_enhance_extra_sources.py
git commit -m "feat(summary_enhance): extra per-topic sources and doc_type/offering in source_map" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: summary_enhance — per-topic prompts, `improve` mode, `run` wiring

**Files:**
- Modify: `agent/summary_enhance/prompt.py`, `agent/summary_enhance/enhance.py`
- Modify: `tests/agent/summary_enhance/test_summary_enhance_prompt.py` (version assertion)
- Test: `tests/agent/summary_enhance/test_summary_enhance_improve.py`

**Interfaces:**
- Consumes: `GuideInput.labels_for`, `ExtraSource`, `SourceChunk.doc_type/offering` (Task 6); `validate_topic(topic, valid_labels, requested_title, min_words)`.
- Produces:
  - `prompt.PROMPT_VERSION = "2026-10-05.1"`
  - `prompt.build_topic_prompt(guide, topic, other_topics, min_words, errors=None, *, source_labels: set[str] | None = None, mode: str = "rewrite") -> str`
  - `enhance.run(..., mode: str = "rewrite", extra_sources: Sequence[ExtraSource] | None = None)`; `mode` must be `"rewrite"` or `"improve"` (else exit 2); `--mode` flag on `enhance.main`.
  - `enhance._synthesize(llm, guide, title, others, min_words, mode="rewrite")` uses `guide.labels_for(title)` for both the prompt's passages and validation.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/summary_enhance/test_summary_enhance_improve.py
import json

import pytest

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import run
from agent.summary_enhance.prompt import PROMPT_VERSION, build_topic_prompt
from agent.summary_enhance.source_loader import ExtraSource, load_guide
from conftest import make_topic_json


def _extra(topic, **kw):
    kw.setdefault("doc_type", "ta_notes")
    kw.setdefault("offering", "class_2024")
    return ExtraSource(topic, "notes-1", "notes", "academic_notes/econ/class_2024/notes.md", "Notes p. 3", **kw)


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def test_prompt_version_bumped():
    assert PROMPT_VERSION == "2026-10-05.1"


def test_prompt_includes_only_the_topics_labels(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    prompt = build_topic_prompt(guide, "Wald", [], 1400, source_labels={"S4"})
    assert "[S4]" in prompt and "Class notes: the Wald statistic" in prompt
    assert "Cameron: the Wald statistic" not in prompt and "[S1] §7.2.3" not in prompt


def test_prompt_without_labels_includes_everything_in_the_old_format(vault):
    guide = load_guide(vault.guide)
    prompt = build_topic_prompt(guide, "Wald", [], 1400)
    assert '[S1] §7.2.3 Wald Test Statistic, p. 249 -- academic_notes/econ/textbooks/cam.rag.md\n"""' in prompt
    assert "=== DRAFT GUIDE (not a source) ===" in prompt and "IMPROVEMENT" not in prompt


def test_improve_mode_prompt(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    prompt = build_topic_prompt(guide, "Wald", [], 1400, mode="improve")
    assert "IMPROVEMENT pass" in prompt and "BASELINE GUIDE" in prompt
    assert "[S4] (class notes/slides, class_2024 offering) Notes p. 3 -- " in prompt
    assert "prefer the textbook" in prompt and "hand-written or transcribed" in prompt
    assert "it is not a source" in prompt


def test_rewrite_mode_has_no_improve_instructions(vault):
    assert "IMPROVEMENT" not in build_topic_prompt(load_guide(vault.guide), "Wald", [], 1400, mode="rewrite")


def _go(vault, llm, extras, **kw):
    kw.setdefault("topics", ["Wald", "LM"])
    kw.setdefault("min_words", 100)
    return run(str(vault.guide), llm=llm, extra_sources=extras, **kw)


def test_extra_sources_flow_end_to_end(vault, make_llm):
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")]) == 0
    assert "Class notes: the Wald statistic" in llm.calls[0] and "Class notes" not in llm.calls[1]
    text = _out(vault).read_text(encoding="utf-8")
    front = text.split("\n---\n\n", 1)[0]
    smap = json.loads(next(l for l in front.splitlines() if l.startswith("source_map: "))[len("source_map: "):])
    assert {e["chunk_id"] for e in smap} == {"notes-1", "cam-1"}
    assert next(e for e in smap if e["chunk_id"] == "notes-1")["doc_type"] == "ta_notes"


def test_a_topic_citing_another_topics_source_is_rejected(vault, make_llm):
    # LM's own set is {S1}; citing S4 (Wald's class notes) is invalid for LM, twice -> exit 3
    bad = make_topic_json("LM", labels=("S4",))
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), bad, bad)
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")]) == 3
    assert not _out(vault).exists()
    assert "unknown label 'S4'" in llm.calls[2]


def test_improve_mode_is_passed_to_every_call(vault, make_llm):
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S4",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM")], mode="improve") == 0
    assert all("IMPROVEMENT pass" in c for c in llm.calls)


def test_unknown_mode_is_an_input_error(vault, make_llm):
    llm = make_llm()
    assert _go(vault, llm, None, mode="sideways") == 2 and llm.calls == []


def test_missing_extra_chunk_exits_before_any_call(vault, make_llm):
    llm = make_llm()
    assert _go(vault, llm, [ExtraSource("Wald", "gone-9", "notes", "p", "c")]) == 2
    assert llm.calls == []


def test_dry_run_reports_sources_and_mode(vault, make_llm, capsys):
    assert _go(vault, make_llm(), [_extra("Wald")], mode="improve", dry_run=True) == 0
    out = capsys.readouterr().out
    assert "4 chunks" in out and "mode improve" in out


def test_main_passes_mode(vault, monkeypatch):
    captured = {}
    monkeypatch.setattr(enhance, "run", lambda guide, **kw: captured.update(kw) or 0)
    enhance.main([str(vault.guide), "--mode", "improve"])
    assert captured["mode"] == "improve" and captured["extra_sources"] is None
    enhance.main([str(vault.guide)])
    assert captured["mode"] == "rewrite"
```

In `tests/agent/summary_enhance/test_summary_enhance_prompt.py`, change the version assertion:

```python
    assert PROMPT_VERSION == "2026-10-05.1"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/summary_enhance/test_summary_enhance_improve.py -q`
Expected: failures (`TypeError ... unexpected keyword 'source_labels'`, `PROMPT_VERSION` mismatch).

- [ ] **Step 3: Implement**

`agent/summary_enhance/prompt.py` edits.

1. Replace `PROMPT_VERSION = "2026-10-04.1"` with:

```python
PROMPT_VERSION = "2026-10-05.1"
```

2. Add after the `_WORKED_INSTRUCTIONS` block (before `def _passages`):

```python
_IMPROVE_INSTRUCTIONS = """\

This is an IMPROVEMENT pass. The baseline guide below was written earlier from some of these
passages. Keep what the passages support (and its good structure where it helps), correct or
tighten anything the passages do not support, and integrate the additional passages (those marked
as class notes, slides, recitations, or other textbook sections). Rules:
  * Where a textbook and class notes or slides differ in notation, assumptions or claims, say so
    plainly in a grounded block that cites both labels, and prefer the textbook.
  * Class notes and slides may be hand-written or transcribed and can contain errors; do not repeat
    a class-note claim that a textbook contradicts without saying so.
  * Do not copy asides that are not about this topic (administrative remarks, other lectures).
  * A class-notes point is grounded only if a class-notes passage supports it; your own additions
    stay "external".
"""

_KIND_TEXT = {
    "textbook": "textbook", "ta_notes": "class notes/slides", "handwritten_notes": "hand-written class notes",
    "problem_set": "problem set", "excalidraw_notes": "lecture notes",
}


def _kind(source) -> str:
    if not source.doc_type:
        return ""
    kind = _KIND_TEXT.get(source.doc_type, source.doc_type)
    return f" ({kind}, {source.offering} offering)" if source.offering else f" ({kind})"
```

3. Replace the `_passages` function with:

```python
def _passages(guide: GuideInput, labels: set[str] | None = None, mode: str = "rewrite") -> str:
    if mode == "improve":
        head = ("=== BASELINE GUIDE (existing draft; keep what the passages support, correct or extend "
                "the rest; it is not a source) ===\n")
    else:
        head = "=== DRAFT GUIDE (not a source) ===\n"
    parts = [head + guide.body, "=== TEXTBOOK PASSAGES ===" if mode != "improve" else "=== SOURCE PASSAGES ==="]
    for s in guide.sources:
        if labels is not None and s.label not in labels:
            continue
        parts.append(f"[{s.label}]{_kind(s)} {s.citation} -- {s.path}\n\"\"\"\n{s.text}\n\"\"\"")
    return "\n\n".join(parts)
```

4. Replace `build_topic_prompt` with:

```python
def build_topic_prompt(guide: GuideInput, topic: str, other_topics: list[str], min_words: int,
                       errors: list[str] | None = None, *, source_labels: set[str] | None = None,
                       mode: str = "rewrite") -> str:
    others_line = ""
    if other_topics:
        listed = ", ".join(json.dumps(t) for t in other_topics)
        others_line = (f"Other topics ({listed}) get their own sections of the finished guide; "
                       "do not duplicate their content beyond what this topic needs.\n")
    head = f"(prompt version {PROMPT_VERSION})\n\n" + _TOPIC_INSTRUCTIONS.format(
        topic=topic, others_line=others_line, target=int(min_words * _LENGTH_FACTOR),
        min_sections=MIN_SECTIONS, doubled=_DOUBLED_EXAMPLE,
        schema=json.dumps(TOPIC_SCHEMA, indent=2))
    if mode == "improve":
        head += _IMPROVE_INSTRUCTIONS
    return head + "\n" + _passages(guide, source_labels, mode) + _rejected(errors) + "\n"
```

`agent/summary_enhance/enhance.py` edits (exact replacements):

1. Import line: replace
`from agent.summary_enhance.source_loader import GuideInput, SourceError, load_guide`
with
`from agent.summary_enhance.source_loader import ExtraSource, GuideInput, SourceError, load_guide`
and add `from typing import Sequence` next to the other stdlib imports.

2. Replace `_synthesize` with:

```python
def _synthesize(llm: LLMClient, guide: GuideInput, title: str, others: list[str], min_words: int,
                mode: str = "rewrite") -> Topic:
    labels = guide.labels_for(title)

    def check(data):
        try:
            topic = parse_topic(data)
        except ValueError as err:
            return None, [f"malformed topic: {err}"]
        errors = validate_topic(topic, labels, title, min_words)
        topic.title = title  # render the requested spelling
        return topic, errors

    return _with_retry(
        lambda errs: build_topic_prompt(guide, title, others, min_words, errs, source_labels=labels, mode=mode),
        lambda p: llm.generate_structured(p, TOPIC_SCHEMA), check)
```

3. Replace the `run` signature and the first `try` block:

```python
        env_file: str | None = None, worked_example: bool = False,
        min_words: int = DEFAULT_MIN_WORDS) -> int:
    try:
        if min_words < 1:
            raise OutputError(f"--min-words must be a positive integer, got {min_words}")
        guide = load_guide(guide_path)
```

with:

```python
        env_file: str | None = None, worked_example: bool = False,
        min_words: int = DEFAULT_MIN_WORDS, mode: str = "rewrite",
        extra_sources: Sequence[ExtraSource] | None = None) -> int:
    try:
        if min_words < 1:
            raise OutputError(f"--min-words must be a positive integer, got {min_words}")
        if mode not in ("rewrite", "improve"):
            raise OutputError(f"--mode must be 'rewrite' or 'improve', got {mode!r}")
        guide = load_guide(guide_path, extra_sources)
```

4. In the dry-run print, replace
`print(f"DRY RUN: {len(guide.sources)} chunks, about {len(sample)} prompt characters per call, "`
with
`print(f"DRY RUN: {len(guide.sources)} chunks, mode {mode}, about {len(sample)} prompt characters per call, "`

5. Replace `topic = _synthesize(llm, guide, title, others, min_words)` with
`topic = _synthesize(llm, guide, title, others, min_words, mode)`.

6. In `main`, add after the `--min-words` argument:

```python
    p.add_argument("--mode", choices=("rewrite", "improve"), default="rewrite",
                   help="rewrite (default) or improve: treat the guide as a baseline to keep and extend")
```

and replace the final `return run(args.guide, ...)` call so it passes `mode=args.mode, extra_sources=None`:

```python
    return run(args.guide, topics=args.topic, output=args.output, model=args.model,
               force=args.force, dry_run=args.dry_run, env_file=args.env_file,
               worked_example=args.worked_example, min_words=args.min_words,
               mode=args.mode, extra_sources=None)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/summary_enhance tests/agent/study_guide tests/agent/rag -q`
Expected: all pass. (The `PROMPT_VERSION` assertions in `test_summary_enhance_prompt.py` and `test_summary_enhance_render.py` track the constant.)

- [ ] **Step 5: Commit**

```bash
git add agent/summary_enhance/prompt.py agent/summary_enhance/enhance.py tests/agent/summary_enhance/test_summary_enhance_prompt.py tests/agent/summary_enhance/test_summary_enhance_improve.py
git commit -m "feat(summary_enhance): per-topic source sets and improve mode" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: `study_guide enhance` command

**Files:**
- Modify: `agent/study_guide/cli.py`
- Test: `tests/agent/study_guide/test_study_guide_enhance_cmd.py`

**Interfaces:**
- Consumes: `summary_enhance.enhance.run` (imported in `cli.py` as `enhance_run`), `ExtraSource`; `accepted`, `load_plan` etc.
- Produces: `cmd_enhance(spec_path, root, *, draft_path, plan_path=None, mode="improve", worked_example=False, min_words=1400, model=None, tag="", force=False, dry_run=False, accept_unreviewed=False, env_file=None, llm=None, chunks=None, cards=None) -> int`; `main` gains the `enhance` subcommand. It passes `topics=[t.title for t in spec.topics]`, `model=model or spec.enhance_model`, `extra_sources` (one `ExtraSource` per accepted passage per topic), `output` = `<draft stem>.enhanced[.tag].md` beside the draft when `tag` is given (else `None`, letting `summary_enhance` use its default), and returns `enhance_run`'s exit code.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_enhance_cmd.py
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import cmd_apply_review, cmd_enhance, cmd_plan, main, plan_path_for
from agent.study_guide.spec import load_spec
from sg_helpers import CARDS, CHUNKS, StubSearch, hit

SPEC = """
[models]
enhance = "gemini-test-enhance"

[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"

  [[topic.source]]
  kind = "discover"
  query = "wald"
  min_score = 0.5
  max = 3

[[topic]]
title = "LM"
instruction = "Explain LM."

  [[topic.source]]
  kind = "file"
  file = "sl"
"""
HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'


@pytest.fixture
def setup(make_spec, root, tmp_path):
    make_spec(SPEC, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})
    assert cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS) == 0
    spec = load_spec(spec_file)
    draft = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    draft.write_text("---\ntitle: \"Demo\"\n---\n\nBody\n", encoding="utf-8")
    return spec_file, spec, draft


@pytest.fixture
def captured(monkeypatch):
    seen = {}

    def fake_run(guide, **kw):
        seen["guide"] = guide
        seen["kw"] = kw
        return 0

    monkeypatch.setattr(cli, "enhance_run", fake_run)
    return seen


def _decide(spec, root, tmp_path, decisions):
    d = tmp_path / "d.json"
    d.write_text(json.dumps(decisions), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(d)) == 0


def test_pending_blocks_enhance_unless_accepted(setup, root, captured):
    spec_file, spec, draft = setup
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS) == 2
    assert "kw" not in captured


def test_extra_sources_and_options_are_passed_through(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    _decide(spec, root, tmp_path, {"Wald|han-1": "keep"})
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS,
                       worked_example=True, min_words=900, force=True, dry_run=True, env_file="e.env") == 0
    kw = captured["kw"]
    assert captured["guide"] == str(draft)
    assert kw["topics"] == ["Wald", "LM"] and kw["model"] == "gemini-test-enhance"
    assert kw["mode"] == "improve" and kw["worked_example"] is True and kw["min_words"] == 900
    assert kw["force"] is True and kw["dry_run"] is True and kw["env_file"] == "e.env" and kw["output"] is None
    extras = kw["extra_sources"]
    assert [(e.topic, e.chunk_id) for e in extras] == [("Wald", "cam-1"), ("Wald", "han-1"), ("LM", "sl-1"), ("LM", "sl-2")]
    assert extras[2].doc_type == "ta_notes" and extras[0].doc_type == "textbook" and extras[0].citation


def test_dropped_passages_are_not_sent(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    _decide(spec, root, tmp_path, {"Wald|han-1": "drop"})
    cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS)
    assert [e.chunk_id for e in captured["kw"]["extra_sources"] if e.topic == "Wald"] == ["cam-1"]


def test_model_override_mode_and_tag(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True,
                model="other-model", mode="rewrite", tag="e1")
    kw = captured["kw"]
    assert kw["model"] == "other-model" and kw["mode"] == "rewrite"
    assert kw["output"] == str(draft.with_name("demo.enhanced.e1.md"))


def test_stale_plan_is_rejected(setup, root, captured):
    spec_file, spec, draft = setup
    gone = [c for c in CHUNKS if c["chunk_id"] != "cam-1"]
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=gone, cards=CARDS, accept_unreviewed=True) == 2
    assert "kw" not in captured


def test_missing_draft_is_an_input_error(setup, root, captured):
    spec_file, spec, draft = setup
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft.with_name("nope.md")), chunks=CHUNKS, cards=CARDS,
                       accept_unreviewed=True) == 2


def test_exit_code_of_the_enhance_run_is_returned(setup, root, monkeypatch):
    spec_file, spec, draft = setup
    monkeypatch.setattr(cli, "enhance_run", lambda guide, **kw: 3)
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True) == 3


def test_main_dispatches_enhance(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(cli, "cmd_enhance", lambda spec, root, **kw: calls.update(kw) or 0)
    assert main(["enhance", "s.toml", "--root", str(tmp_path), "--draft", "g.md", "--mode", "rewrite",
                 "--worked-example", "--min-words", "700", "--tag", "e1", "--model", "m", "--force",
                 "--dry-run", "--accept-unreviewed", "--plan", "p.json"]) == 0
    assert calls["draft_path"] == "g.md" and calls["mode"] == "rewrite" and calls["worked_example"] is True
    assert calls["min_words"] == 700 and calls["tag"] == "e1" and calls["model"] == "m"
    assert calls["plan_path"] == "p.json" and calls["accept_unreviewed"] is True
    main(["enhance", "s.toml", "--root", str(tmp_path), "--draft", "g.md"])
    assert calls["mode"] == "improve" and calls["min_words"] == 1400
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_enhance_cmd.py -q`
Expected: `ImportError: cannot import name 'cmd_enhance'`.

- [ ] **Step 3: Implement**

In `agent/study_guide/cli.py`:

1. Add imports near the top: `from agent.summary_enhance.enhance import DEFAULT_MIN_WORDS, run as enhance_run` and `from agent.summary_enhance.source_loader import ExtraSource`; also add `accepted` to the `from agent.study_guide.plan import (...)` list.

2. Add this function after `cmd_draft`:

```python
def cmd_enhance(spec_path: str, root: str, *, draft_path: str, plan_path: str | None = None,
                mode: str = "improve", worked_example: bool = False, min_words: int = DEFAULT_MIN_WORDS,
                model: str | None = None, tag: str = "", force: bool = False, dry_run: bool = False,
                accept_unreviewed: bool = False, env_file: str | None = None, llm=None,
                chunks=None, cards=None) -> int:
    try:
        spec = load_spec(spec_path)
        plan, _, _ = _load_plan_for(spec, root, plan_path, chunks, cards)
        if not Path(draft_path).is_file():
            raise PlanError(f"draft not found: {draft_path}")
        extras = []
        for topic in spec.topics:
            for e in accepted(plan, topic.title, accept_unreviewed=accept_unreviewed):
                extras.append(ExtraSource(topic.title, e.chunk_id, e.file_id, e.path, e.citation,
                                          e.doc_type, e.offering))
    except (SpecError, PlanError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    draft = Path(draft_path)
    output = str(draft.with_name(f"{draft.stem}.enhanced.{tag}.md")) if tag else None
    return enhance_run(
        str(draft), topics=[t.title for t in spec.topics], output=output, model=model or spec.enhance_model,
        force=force, dry_run=dry_run, llm=llm, env_file=env_file, worked_example=worked_example,
        min_words=min_words, mode=mode, extra_sources=extras)
```

3. In `main`, add the subparser before `args = p.parse_args(argv)`:

```python
    sp = sub.add_parser("enhance")
    common(sp)
    sp.add_argument("--draft", required=True, help="the guide to enhance (a derived_summary .md)")
    sp.add_argument("--plan", help="plan file (default: the spec's plan in the vault)")
    sp.add_argument("--mode", choices=("rewrite", "improve"), default="improve")
    sp.add_argument("--worked-example", action="store_true")
    sp.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)
    sp.add_argument("--model", help="override [models].enhance")
    sp.add_argument("--tag", default="", help="name an output variant (<draft>.enhanced.<tag>.md)")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--accept-unreviewed", action="store_true")
```

and dispatch it right after the `apply-review` branch:

```python
    if args.command == "enhance":
        return cmd_enhance(args.spec, args.root, draft_path=args.draft, plan_path=args.plan, mode=args.mode,
                           worked_example=args.worked_example, min_words=args.min_words, model=args.model,
                           tag=args.tag, force=args.force, dry_run=args.dry_run,
                           accept_unreviewed=args.accept_unreviewed, env_file=args.env_file)
```

4. Add the `enhance` command to the module docstring usage list and to `agent/study_guide/README.md`:
`python -m agent.study_guide enhance <spec> --draft <guide.md> [--mode improve] [--worked-example] [--tag T]`.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/study_guide tests/agent/summary_enhance tests/agent/rag -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/cli.py agent/study_guide/README.md tests/agent/study_guide/test_study_guide_enhance_cmd.py
git commit -m "feat(study_guide): enhance command wiring a plan into summary_enhance" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Real runs and comparison (manual, paid, separate from tests)

These runs make paid API calls and write into the private vault. Run each only with the user's go-ahead at that point. Use `--root <main checkout>/ai-sandbox/academic-hub` and `--env-file <main checkout>/ai-sandbox/.env`. Every output is tagged so nothing overwrites the pushed guides. Never print `.env` contents.

**Files:**
- Create: `guide_specs/econometrics/wald_lm_lr_tests_new_material.toml`
- Create (vault, local): `<hub>/academic_notes/econometrics/guide_plans/*`, `<hub>/academic_notes/econometrics/summaries/wald_lm_lr_tests*.md` variants
- Create: `docs/status/agent/<date>-study-guide-comparison-status.md` (results write-up)

- [ ] **Step 1: Plan B0 (baseline reproduction) and compare with the original guide's chunks**

```bash
python -m agent.study_guide plan guide_specs/econometrics/wald_lm_lr_tests.toml --root "<HUB>" --env-file "<ENV>"
```
Expected: per-topic counts, no pending entries (baseline has only `section` rules). Then compare the plan's chunk ids with the 16 chunks in `<HUB>/academic_notes/econometrics/summaries/wald_lm_lr_tests.md` (`indexer_source_refs`): report the overlap (the original used up to 12 per section but only 16 distinct chunks survive after the later back-fill). A large overlap confirms the recipe was recovered; list differences in the write-up. If the plan fails (`PlanError`), report the message; do not loosen matching to force it.

- [ ] **Step 2: Draft B0 (dry run, then real)**

```bash
python -m agent.study_guide draft guide_specs/econometrics/wald_lm_lr_tests.toml --root "<HUB>" --tag b0 --dry-run
python -m agent.study_guide draft guide_specs/econometrics/wald_lm_lr_tests.toml --root "<HUB>" --tag b0 --env-file "<ENV>"
```
Expected: `DRY RUN: 7 calls to gemini-3.1-flash-lite, ...` then `Wrote ...wald_lm_lr_tests.b0.md` (6 topics + 1 comparison). Skim the output for the Hansen likelihood ratio note and citations.

- [ ] **Step 3: Create the new-material spec**

Create `guide_specs/econometrics/wald_lm_lr_tests_new_material.toml` as a copy of the baseline with these changes: `id = "wald_lm_lr_new_material"`; `[draft] label_match = "heading-prefix"` (keep `prompt = "tutor_v1"` and `[models] draft = "gemini-3.1-flash-lite"` so B1 isolates the new material); replace the note body's last two sentences with: `Chapter 9 contains no section headed likelihood ratio test (Hansen section 5.13, "Likelihood Ratio Test", is included below as additional material).` and append these `[[topic.source]]` blocks to the named topics (pinned class files; the file paths are the index paths of the three files that ranked, midterm answer key excluded; discover rules exclude the original guide's chunks):

- Topics "Cameron & Trivedi Section 7.2: Wald test" and "Hansen Section 9.10 and 9.11: Wald tests":

```toml
  [[topic.source]]
  kind = "file"
  file = "class_2024/Class Notes/Slides/processed_outputs/slidesASYM.md"
  query = "Wald test statistic homoskedastic covariance chi-square"
  max = 6

  [[topic.source]]
  kind = "file"
  file = "class_2024/Recitations/processed_outputs/Recitation 5.md"
  query = "Wald test of nonlinear hypothesis delta method"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "Wald test statistic, linear and nonlinear restrictions, covariance estimator"
  doc_types = ["textbook"]
  exclude_guide = "academic_notes/econometrics/summaries/wald_lm_lr_tests.md"
  max = 8
  min_score = 0.72
  max_per_file = 4
```

- Topics "Cameron & Trivedi Section 7.3: likelihood ratio test" and "Hansen Section 9.11 reference check: likelihood ratio test":

```toml
  [[topic.source]]
  kind = "file"
  file = "class_2024/Recitations/processed_outputs/Recitation 3.md"
  query = "likelihood ratio test restricted unrestricted other approaches to testing"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "likelihood ratio test statistic restricted and unrestricted log-likelihood chi-square"
  doc_types = ["textbook"]
  exclude_guide = "academic_notes/econometrics/summaries/wald_lm_lr_tests.md"
  max = 8
  min_score = 0.72
  max_per_file = 4
```

- Topics "Cameron & Trivedi Section 7.3.5: Lagrange multiplier test" and "Hansen Section 9.17: score (Lagrange multiplier) test":

```toml
  [[topic.source]]
  kind = "file"
  file = "class_2024/Class Notes/Slides/processed_outputs/slidesASYM.md"
  query = "Lagrange multiplier score test restricted estimator statistic"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "Lagrange multiplier score test statistic computed at the restricted estimator"
  doc_types = ["textbook"]
  exclude_guide = "academic_notes/econometrics/summaries/wald_lm_lr_tests.md"
  max = 8
  min_score = 0.72
  max_per_file = 4
```

Verify with `python -c "from agent.study_guide.spec import load_spec; print(len(load_spec('guide_specs/econometrics/wald_lm_lr_tests_new_material.toml').topics))"` (expected `6`) and commit the spec file with explicit path. If a `file` path does not resolve, `plan` reports `file not found in the econometrics index`; fix the path from `python -m core.indexer.index_search` output, not by guessing.

- [ ] **Step 4: Plan B1/B2/E1 sources and run the review Artifact flow**

```bash
python -m agent.study_guide plan guide_specs/econometrics/wald_lm_lr_tests_new_material.toml --root "<HUB>" --env-file "<ENV>"
```
Expected: pinned class files accepted, discovered candidates `pending`. Then the review step (project rule: interactive Artifact, not a hand-edited file): Claude publishes a review Artifact from `<HUB>/academic_notes/econometrics/guide_plans/wald_lm_lr_new_material.review.json` (checkbox per discovered candidate showing book, section/page, score, doc type; pinned items read-only; decisions saved in the page's `db` collection, following `core/indexer/offering_links.py`'s review artifact), the user decides, Claude reads the decisions with `ArtifactData` and writes them to a temporary decisions JSON (`{"Topic|chunk_id": "keep"|"drop"}`), then:

```bash
python -m agent.study_guide apply-review "<HUB>/academic_notes/econometrics/guide_plans/wald_lm_lr_new_material.plan.json" --decisions <decisions.json>
```
Expected: counts with no `pending`. Calibrate `min_score` from the review: if most candidates were dropped (or none), note the better threshold in the write-up.

- [ ] **Step 5: Draft B1 and B2, enhance E1**

```bash
python -m agent.study_guide draft guide_specs/econometrics/wald_lm_lr_tests_new_material.toml --root "<HUB>" --tag b1 --env-file "<ENV>"
python -m agent.study_guide draft guide_specs/econometrics/wald_lm_lr_tests_new_material.toml --root "<HUB>" --tag b2 --model gemini-3.8-flash --force --env-file "<ENV>"
python -m agent.study_guide enhance guide_specs/econometrics/wald_lm_lr_tests_new_material.toml --root "<HUB>" --draft "<HUB>/academic_notes/econometrics/summaries/wald_lm_lr_tests.md" --mode improve --worked-example --tag e1 --env-file "<ENV>"
```
Use `--dry-run` first for each. B1 isolates the new material (same model as the baseline); B2 changes only the model; E1 is option 2 (improve the original guide, which is read, never modified). Optionally also run B2 with `--model gemini-3.1-pro-preview --tag b2-pro` for the model comparison.

- [ ] **Step 6: Review by hand and write up**

Compare B0, B1, B2, E1 and the original: coverage against a checklist built from the class slides (topics the slides cover that the textbook-only guide lacks), factual spot-checks of at least three claims per run against the cited passages, any class-notes errors that leaked in, structure and length, and citation traceability. Write the findings, the retrieval overlap from Step 1, the calibrated `min_score`, and cost/time per run to `docs/status/agent/<date>-study-guide-comparison-status.md`; commit it with explicit paths. Do not commit or push the vault; merging the branch is the integrator's step.
