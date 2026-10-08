# Guide Revise Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `revise` stage to `agent/study_guide` that refines a large study guide against four criteria (relevance weighted by exams and problem sets, deduplication, correctness, organization) by producing a reviewed edit list and applying the accepted edits deterministically.

**Architecture:** The guide is segmented into heading-delimited blocks with stable ids. Four stages each propose typed edits (relevance and dedup use embeddings; dedup, correctness and organization add model calls scoped to one cluster, one section or the outline). Proposals merge into one edit report; the owner accepts or rejects each edit in an interactive Artifact; a model-free `apply-revise` applies the accepted edits and checks post-conditions before writing.

**Tech Stack:** Python 3.13, stdlib `tomllib`/`json`/`re`/`hashlib`, pytest, existing `agent.study_guide` (plan, spec, cli), `agent.summary_enhance.llm.GeminiClient`, `core.indexer` embeddings.

**Spec:** `docs/superpowers/specs/agent/2026-10-08-guide-revise-pipeline-design.md`.

All commands run from `ai-sandbox/academic-rag-model/` inside the worktree `.worktrees/claude-study-guide-spec` (branch `claude/study-guide-spec`). Tests: `python -m pytest <file> -q`.

## Global Constraints

- The code lives in the new package `agent/study_guide/revise/`; it reads `agent/study_guide/{spec,plan}.py` and `agent/summary_enhance/llm.py` but changes only `spec.py` (the `[revise]` table) and `cli.py` (two subcommands) outside the package.
- Revise never adds a claim: replacement text comes from the model only for `fix`/`link`/`merge`/`shrink`/`retitle` edits that the owner reviews; `apply-revise` calls no model.
- A revise run never makes the guide longer: accepted edits may not raise the total word count except by the words of accepted `fix` replacements.
- Output files: report `academic_notes/<course>/guide_plans/<guide-stem>[.<tag>].revise.json`, review items `...revise.review.json`, revised guide next to the input `<guide-stem>.revised[.<tag>].md` and `...revised[.<tag>].changelog.md`. No overwrite without `--force`.
- Human decisions use an interactive Artifact; the pipeline writes review items and reads the decisions file, and never asks the owner to edit the report by hand. Undecided edits count as rejected.
- Paid calls use `PAID_GEMINI_KEY` through `GeminiClient` (`--env-file` for worktrees). Tests make no network or paid calls: a scripted fake LLM, a bag-of-words fake embedder, and stub search.
- Stage files with explicit paths (never `git add -A`). Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Test files need unique basenames (no `__init__.py` in the test tree): `test_study_guide_revise_*.py`. Shared helpers: `tests/agent/study_guide/rv_helpers.py` (imported as `rv_helpers`), alongside `sg_helpers`.
- On this harness, heredocs halve backslashes: write code containing regexes through the Write/Edit tools, not `cat <<EOF`.

## Rulings carried into this plan

- The spec's LLM judge for borderline relevance is deferred: the relevance stage proposes `delete` only below `relevance_low`, and the review Artifact shows the nearest evidence so the owner judges. Cost if wrong: some borderline blocks get no proposal.
- New edit type `note` (advisory, cannot be applied) so a finding without a safe replacement still reaches the owner. Accepted `note` edits appear in the changelog and change nothing.
- Edit `fix` may carry `quote`: the exact text replaced inside `targets[0]` (must occur exactly once); without `quote`, the whole block is replaced.
- `apply-revise` works on the body after the frontmatter and writes two extra frontmatter fields (`revised_from`, `revise_edits_applied`); the input guide is never modified.
- Evidence rules reuse `build_plan` (one synthetic topic per rule), so file, section and discover rules behave exactly as in a guide plan.

## Review Focus

- A no-op apply (nothing accepted) returns the body byte-for-byte (Task 3).
- A report built for a different version of the guide is refused (Tasks 3, 9).
- Two accepted edits touching the same block are refused, not silently merged (Task 3).
- Undecided edits are rejected; a protected edit is applied only on an explicit accept (Task 5).
- An audit finding whose quote is absent or ambiguous in its block yields a reported problem and no edit (Task 7).
- The relevance stage with no evidence resolved is an error, not a silent skip (Task 4).
- Post-conditions: words not increased, no new page citations, no new heading problems (Task 3).

---

### Task 1: Segmenting the guide into blocks

**Files:**
- Create: `agent/study_guide/revise/__init__.py` (empty)
- Create: `agent/study_guide/revise/segment.py`
- Create: `tests/agent/study_guide/rv_helpers.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_segment.py`

**Interfaces:**
- Produces:
  - `Block(id, heading_path: tuple[str, ...], level: int, start: int, end: int, text: str, words: int, equations: int, constructed: bool)` (frozen dataclass; `start`/`end` are line indexes into `body.split("\n")`, `end` exclusive; `level` 0 means text before the first heading)
  - `split_frontmatter(markdown) -> tuple[str, str]` (frontmatter including its fences and one trailing blank line, body)
  - `segment(body) -> list[Block]`, `check_headings(body) -> list[str]`, `CONSTRUCTED`
  - test helpers `ScriptedLLM(replies)` (`generate_structured`, `generate_text`, `.calls`, `.kinds`) and `bag_embed(vocab)` (a deterministic embedder)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_segment.py
from agent.study_guide.revise.segment import check_headings, segment, split_frontmatter

BODY = ("# T\n\nintro text\n\n## A\n\nalpha\n\n### A1\n\n$$\nx=1\n$$\n\n"
        "**Constructed example (not from the sources)** n=3 and more words here\n\n## B\n\nbeta\n")


def test_split_frontmatter():
    assert split_frontmatter("---\ntitle: x\n---\n\n# T\n") == ("---\ntitle: x\n---\n\n", "# T\n")
    assert split_frontmatter("# T\n") == ("", "# T\n")


def test_blocks_follow_headings_with_paths_and_counts():
    blocks = segment(BODY)
    assert [b.heading_path for b in blocks] == [("T",), ("T", "A"), ("T", "A", "A1"), ("T", "B")]
    assert [b.level for b in blocks] == [1, 2, 3, 2]
    a1 = blocks[2]
    assert a1.equations == 1 and a1.constructed is True and a1.words > 8
    assert blocks[1].equations == 0 and blocks[1].constructed is False


def test_text_before_the_first_heading_is_a_level_zero_block():
    blocks = segment("preface words\n\n# T\n\nbody\n")
    assert blocks[0].level == 0 and blocks[0].heading_path == () and "preface" in blocks[0].text


def test_ids_are_stable_when_other_blocks_change():
    before, after = segment(BODY), segment(BODY.replace("beta", "gamma changed"))
    assert [b.id for b in before[:3]] == [b.id for b in after[:3]] and before[3].id != after[3].id


def test_identical_blocks_get_distinct_ids():
    blocks = segment("# T\n\n## A\n\nsame\n\n## A\n\nsame\n")
    assert len({b.id for b in blocks}) == len(blocks)


def test_headings_inside_code_fences_are_ignored():
    blocks = segment("# T\n\n```\n# not a heading\n```\n\n## A\n\nx\n")
    assert [b.heading_path for b in blocks] == [("T",), ("T", "A")]


def test_start_and_end_index_the_original_lines():
    lines = BODY.split("\n")
    for b in segment(BODY):
        assert "\n".join(lines[b.start:b.end]).rstrip("\n") == b.text


def test_check_headings():
    assert check_headings(BODY) == []
    assert any("extra H1" in p for p in check_headings("# T\n\n# U\n"))
    assert any("jumps" in p for p in check_headings("# T\n\n#### Deep\n"))
    assert any("duplicate" in p for p in check_headings("# T\n\n## A\n\n## a\n"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_segment.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.study_guide.revise`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/segment.py
"""Split a guide into heading-delimited blocks with stable ids, and check heading hygiene."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FRONT_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.S)
CONSTRUCTED = "constructed example (not from the sources)"


@dataclass(frozen=True)
class Block:
    id: str
    heading_path: tuple[str, ...]
    level: int
    start: int
    end: int
    text: str
    words: int
    equations: int
    constructed: bool


def split_frontmatter(markdown: str) -> tuple[str, str]:
    m = _FRONT_RE.match(markdown)
    return (markdown[:m.end()], markdown[m.end():]) if m else ("", markdown)


def segment(body: str) -> list[Block]:
    lines = body.split("\n")
    marks, fenced = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else _HEADING_RE.match(line)
        if m:
            marks.append((i, len(m.group(1)), m.group(2)))
    spans = []
    first = marks[0][0] if marks else len(lines)
    if first > 0 and "\n".join(lines[:first]).strip():
        spans.append((0, first, 0, ""))
    for k, (i, level, title) in enumerate(marks):
        spans.append((i, marks[k + 1][0] if k + 1 < len(marks) else len(lines), level, title))
    blocks, stack, seen = [], [], {}
    for start, end, level, title in spans:
        if level:
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        path = tuple(t for _, t in stack) if level else ()
        text = "\n".join(lines[start:end]).rstrip("\n")
        digest = hashlib.sha1((" > ".join(path) + "\n" + text[:200]).encode("utf-8")).hexdigest()[:10]
        seen[digest] = seen.get(digest, 0) + 1
        bid = "b" + digest + ("" if seen[digest] == 1 else f"-{seen[digest]}")
        blocks.append(Block(bid, path, level, start, end, text, len(text.split()), text.count("$$") // 2,
                            CONSTRUCTED in text.lower()))
    return blocks


def check_headings(body: str) -> list[str]:
    problems, prev, h1s = [], 0, 0
    siblings: dict[tuple, set[str]] = {}
    for b in segment(body):
        if not b.level:
            continue
        title = b.heading_path[-1]
        if b.level == 1:
            h1s += 1
            if h1s > 1:
                problems.append(f"extra H1: {title!r}")
        if prev and b.level > prev + 1:
            problems.append(f"heading level jumps from H{prev} to H{b.level}: {title!r}")
        prev = b.level
        seen = siblings.setdefault(b.heading_path[:-1] + (b.level,), set())
        if title.casefold() in seen:
            problems.append(f"duplicate heading under {' > '.join(b.heading_path[:-1]) or 'top'}: {title!r}")
        seen.add(title.casefold())
        if not title.strip():
            problems.append("empty heading")
    return problems
```

```python
# tests/agent/study_guide/rv_helpers.py
"""Test helpers for the revise stage: a scripted LLM and a deterministic bag-of-words embedder."""
from __future__ import annotations


class ScriptedLLM:
    model = "fake-revise"

    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls: list[str] = []
        self.kinds: list[str] = []

    def _next(self):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def generate_structured(self, prompt, schema):
        self.calls.append(prompt)
        self.kinds.append("structured")
        return self._next()

    def generate_text(self, prompt, *, code_execution=False):
        self.calls.append(prompt)
        self.kinds.append("code" if code_execution else "text")
        return self._next()


def bag_embed(vocab):
    """Embedder: word counts over `vocab` (cosine similarity then tracks shared vocabulary)."""
    def embed(text: str) -> list[float]:
        low = text.lower()
        return [float(low.count(w)) for w in vocab]
    return embed
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_segment.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/__init__.py agent/study_guide/revise/segment.py tests/agent/study_guide/rv_helpers.py tests/agent/study_guide/test_study_guide_revise_segment.py
git commit -m "revise: segment a guide into blocks with stable ids; heading checks"
```

---

### Task 2: The `[revise]` table in the guide spec

**Files:**
- Modify: `agent/study_guide/spec.py` (new dataclasses, `_parse_revise`, `load_spec`, `GuideSpec.revise`)
- Test: `tests/agent/study_guide/test_study_guide_revise_spec.py`

**Interfaces:**
- Consumes: `SourceRule`, `_parse_rule`, `_check_keys`, `_str`, `_strs`, `_int`, `SpecError`, `DEFAULT_MODEL` (existing).
- Produces: `EvidenceRule(rule: SourceRule, weight: float)`; `ReviseSpec(model, criteria, evidence, relevance_low, relevance_high, dedup_similarity, min_block_words)`; `GuideSpec.revise: ReviseSpec | None = None`; `VALID_CRITERIA = ("relevance", "dedup", "correctness", "organization")`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_spec.py
import pytest

from agent.study_guide.spec import DEFAULT_MODEL, SpecError, load_spec

BASE = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "file"
  file = "x"
"""
REVISE = """
[revise]
model = "gemini-test"
criteria = ["relevance", "correctness"]
relevance_low = 0.2
relevance_high = 0.7
dedup_similarity = 0.9
min_block_words = 40

  [[revise.evidence]]
  kind = "file"
  file = "class_2024/processed_outputs/2024 midterm-ans-key.md"
  weight = 3.0

  [[revise.evidence]]
  kind = "discover"
  query = "problem"
  doc_types = ["problem_set"]
"""


def _load(tmp_path, text):
    p = tmp_path / "spec.toml"
    p.write_text(text, encoding="utf-8")
    return load_spec(p)


def test_absent_table_means_no_revise(tmp_path):
    assert _load(tmp_path, BASE).revise is None


def test_revise_table_parses(tmp_path):
    r = _load(tmp_path, BASE + REVISE).revise
    assert (r.model, r.criteria, r.relevance_low, r.relevance_high) == ("gemini-test", ("relevance", "correctness"), 0.2, 0.7)
    assert (r.dedup_similarity, r.min_block_words) == (0.9, 40)
    assert [(e.rule.kind, e.weight) for e in r.evidence] == [("file", 3.0), ("discover", 1.0)]
    assert r.evidence[1].rule.doc_types == ("problem_set",)


def test_defaults(tmp_path):
    r = _load(tmp_path, BASE + "\n[revise]\n").revise
    assert r.model == DEFAULT_MODEL and r.criteria == ("relevance", "dedup", "correctness", "organization")
    assert (r.relevance_low, r.relevance_high, r.dedup_similarity, r.min_block_words) == (0.30, 0.60, 0.92, 60)
    assert r.evidence == ()


@pytest.mark.parametrize("old,new,fragment", [
    ('model = "gemini-test"', 'model = "gemini-test"\nbogus = 1', "unknown key"),
    ('criteria = ["relevance", "correctness"]', 'criteria = ["relevance", "style"]', "criteria"),
    ("relevance_low = 0.2", "relevance_low = 0.9", "relevance_low"),
    ("weight = 3.0", "weight = 0", "weight"),
    ('kind = "file"\n  file = "class_2024/processed_outputs/2024 midterm-ans-key.md"', 'kind = "weird"', "kind"),
])
def test_invalid_revise_tables_rejected(tmp_path, old, new, fragment):
    assert old in REVISE
    with pytest.raises(SpecError, match=fragment):
        _load(tmp_path, BASE + REVISE.replace(old, new))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_spec.py -q`
Expected: FAIL (`unknown key(s) ['revise']`)

- [ ] **Step 3: Implement** (edit `agent/study_guide/spec.py`)

Add after `NoteSpec`:

```python
VALID_CRITERIA = ("relevance", "dedup", "correctness", "organization")


@dataclass(frozen=True)
class EvidenceRule:
    rule: SourceRule
    weight: float = 1.0


@dataclass(frozen=True)
class ReviseSpec:
    model: str
    criteria: tuple[str, ...]
    evidence: tuple[EvidenceRule, ...]
    relevance_low: float = 0.30
    relevance_high: float = 0.60
    dedup_similarity: float = 0.92
    min_block_words: int = 60
```

Add `revise: ReviseSpec | None = None` as the last field of `GuideSpec`. Add the parser before `load_spec`:

```python
def _unit_float(table: dict, key: str, default: float, where: str) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise SpecError(f"{where}: {key!r} must be a number between 0 and 1")
    return float(value)


def _parse_revise(data: dict) -> ReviseSpec | None:
    rev = data.get("revise")
    if rev is None:
        return None
    if not isinstance(rev, dict):
        raise SpecError("[revise] must be a table")
    _check_keys(rev, {"model", "criteria", "relevance_low", "relevance_high", "dedup_similarity",
                      "min_block_words", "evidence"}, "[revise]")
    criteria = _strs(rev, "criteria", "[revise]", default=VALID_CRITERIA)
    bad = [c for c in criteria if c not in VALID_CRITERIA]
    if bad:
        raise SpecError(f"[revise]: criteria must be among {VALID_CRITERIA}, got {bad}")
    low = _unit_float(rev, "relevance_low", 0.30, "[revise]")
    high = _unit_float(rev, "relevance_high", 0.60, "[revise]")
    if low >= high:
        raise SpecError("[revise]: relevance_low must be below relevance_high")
    evidence = []
    for i, raw in enumerate(rev.get("evidence", []), 1):
        where = f"[[revise.evidence]] {i}"
        table = dict(raw)
        weight = table.pop("weight", 1.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight <= 0:
            raise SpecError(f"{where}: 'weight' must be a positive number")
        evidence.append(EvidenceRule(_parse_rule(table, where), float(weight)))
    return ReviseSpec(
        model=_str(rev, "model", "[revise]", DEFAULT_MODEL), criteria=criteria, evidence=tuple(evidence),
        relevance_low=low, relevance_high=high, dedup_similarity=_unit_float(rev, "dedup_similarity", 0.92, "[revise]"),
        min_block_words=_int(rev, "min_block_words", "[revise]", 60))
```

In `load_spec`: add `"revise"` to the allowed top-level key set, and pass `revise=_parse_revise(data)` to the `GuideSpec(...)` call.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: PASS (all study_guide tests, including the new 9)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/spec.py tests/agent/study_guide/test_study_guide_revise_spec.py
git commit -m "revise: [revise] table in the guide spec"
```

---

### Task 3: Edit report, apply, post-conditions

**Files:**
- Create: `agent/study_guide/revise/edits.py`
- Create: `agent/study_guide/revise/apply.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_apply.py`

**Interfaces:**
- Consumes: `Block`, `segment`, `check_headings` (Task 1).
- Produces:
  - `ReviseError(Exception)`; `EDIT_TYPES = ("delete", "shrink", "merge", "link", "fix", "move", "retitle", "note")`
  - `Edit(id, type, stage, targets, rationale, evidence=[], severity="medium", confidence=0.5, replacement=None, quote=None, anchor=None, protected=False, conflicts=[])` (dataclass)
  - `EditReport(guide_path, guide_sha256, created_at, blocks: list[dict], edits: list[Edit], protected_blocks: list[str])`; `save_report(report, path)`, `load_report(path)`, `validate_report(report, blocks) -> list[str]`, `mark_conflicts(report)`
  - `apply_edits(body, report, accepted: set[str]) -> str` (raises `ReviseError`), `changelog(report, accepted) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_apply.py
import pytest

from agent.study_guide.revise.apply import apply_edits, changelog
from agent.study_guide.revise.edits import (
    Edit, EditReport, ReviseError, load_report, mark_conflicts, save_report, validate_report,
)
from agent.study_guide.revise.segment import segment

BODY = ("# T\n\nintro words here\n\n## A\n\nalpha one two three\n\n### A1\n\nsub text with several words\n\n"
        "## B\n\nbeta four five six seven eight\n\n## C\n\ngamma tail words\n")


def _ids():
    return {b.heading_path[-1]: b.id for b in segment(BODY)}


def _report(*edits):
    return EditReport("g.md", "sha", "2026-10-08T00:00:00+00:00", [], list(edits), [])


def _e(eid, type_, targets, **kw):
    kw.setdefault("rationale", "why")
    kw.setdefault("stage", "relevance")
    return Edit(eid, type_, targets=targets, **kw)


def test_nothing_accepted_returns_the_body_byte_for_byte():
    ids = _ids()
    assert apply_edits(BODY, _report(_e("e1", "delete", [ids["B"]])), set()) == BODY


def test_delete_removes_only_that_block():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "delete", [ids["B"]])), {"e1"})
    assert "beta" not in out and "alpha" in out and "gamma tail" in out and "sub text" in out


def test_fix_with_quote_replaces_only_the_quote():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "fix", [ids["B"]], quote="four five", replacement="4 5")), {"e1"})
    assert "beta 4 5 six" in out and out.count("## B") == 1


def test_fix_quote_must_occur_exactly_once():
    ids = _ids()
    with pytest.raises(ReviseError, match="exactly once"):
        apply_edits(BODY, _report(_e("e1", "fix", [ids["B"]], quote="nowhere", replacement="x")), {"e1"})


def test_shrink_and_link_replace_the_whole_block():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "link", [ids["C"]], replacement="## C\n\nSee [[#A]].")), {"e1"})
    assert "See [[#A]]." in out and "gamma tail" not in out


def test_merge_replaces_the_first_target_and_deletes_the_rest():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "merge", [ids["A"], ids["B"]], replacement="## A\n\nmerged text")), {"e1"})
    assert "merged text" in out and "beta" not in out and "alpha" not in out


def test_retitle_changes_only_the_heading_line():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "retitle", [ids["B"]], replacement="## Better title")), {"e1"})
    assert "## Better title\n\nbeta four five" in out and "## B\n" not in out


def test_move_places_the_block_after_the_anchor():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "move", [ids["C"]], anchor=ids["A"])), {"e1"})
    assert out.index("alpha") < out.index("gamma tail") < out.index("sub text")


def test_note_edits_change_nothing():
    ids = _ids()
    assert apply_edits(BODY, _report(_e("e1", "note", [ids["B"]])), {"e1"}) == BODY


def test_two_accepted_edits_on_one_block_are_refused():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]]), _e("e2", "retitle", [ids["B"]], replacement="## X"))
    with pytest.raises(ReviseError, match="same block"):
        apply_edits(BODY, rep, {"e1", "e2"})


def test_unknown_accepted_id_is_refused():
    with pytest.raises(ReviseError, match="unknown edit"):
        apply_edits(BODY, _report(), {"nope"})


def test_postcondition_total_words_may_not_grow():
    ids = _ids()
    long_text = "## C\n\n" + " ".join(["more"] * 50)
    with pytest.raises(ReviseError, match="longer"):
        apply_edits(BODY, _report(_e("e1", "shrink", [ids["C"]], replacement=long_text)), {"e1"})


def test_postcondition_no_new_page_citations():
    ids = _ids()
    with pytest.raises(ReviseError, match="citation"):
        apply_edits(BODY, _report(_e("e1", "link", [ids["C"]], replacement="## C\n\nsee (Hansen, p. 9)")), {"e1"})


def test_postcondition_no_new_heading_problems():
    ids = _ids()
    with pytest.raises(ReviseError, match="heading"):
        apply_edits(BODY, _report(_e("e1", "retitle", [ids["B"]], replacement="###### Deep")), {"e1"})


def test_validate_report_flags_bad_edits():
    blocks = segment(BODY)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    bad = _report(_e("e1", "delete", ["missing"]), _e("e2", "link", [ids["A"]]), _e("e3", "move", [ids["A"]]),
                  _e("e4", "merge", [ids["A"]], replacement="x"), _e("e5", "weird", [ids["A"]]),
                  _e("e5", "delete", [ids["B"]]))
    problems = " | ".join(validate_report(bad, blocks))
    for fragment in ("unknown block", "needs a replacement", "needs one target and an anchor", "at least two", "unknown edit type", "duplicate edit id"):
        assert fragment in problems


def test_mark_conflicts_links_edits_sharing_a_block():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]]), _e("e2", "retitle", [ids["B"]], replacement="## X"), _e("e3", "delete", [ids["C"]]))
    mark_conflicts(rep)
    assert rep.edits[0].conflicts == ["e2"] and rep.edits[1].conflicts == ["e1"] and rep.edits[2].conflicts == []


def test_report_round_trips_through_json(tmp_path):
    rep = _report(_e("e1", "delete", ["b1"], evidence=["c1"], protected=True))
    save_report(rep, tmp_path / "x" / "r.json")
    assert load_report(tmp_path / "x" / "r.json") == rep


def test_changelog_lists_applied_and_acknowledged_edits():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]], rationale="off topic"), _e("e2", "note", [ids["C"]], rationale="check this"))
    text = changelog(rep, {"e1", "e2"})
    assert "e1" in text and "off topic" in text and "acknowledged" in text and "check this" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_apply.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.study_guide.revise.edits`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/edits.py
"""The edit report: typed proposals from every stage, validated before review."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agent.study_guide.revise.segment import Block

EDIT_TYPES = ("delete", "shrink", "merge", "link", "fix", "move", "retitle", "note")
NEEDS_REPLACEMENT = ("shrink", "link", "retitle", "merge")


class ReviseError(Exception):
    pass


@dataclass
class Edit:
    id: str
    type: str
    targets: list[str]
    rationale: str
    stage: str = "relevance"
    evidence: list[str] = field(default_factory=list)
    severity: str = "medium"
    confidence: float = 0.5
    replacement: str | None = None
    quote: str | None = None
    anchor: str | None = None
    protected: bool = False
    conflicts: list[str] = field(default_factory=list)


@dataclass
class EditReport:
    guide_path: str
    guide_sha256: str
    created_at: str
    blocks: list[dict]
    edits: list[Edit]
    protected_blocks: list[str]


def save_report(report: EditReport, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(report), indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def load_report(path: str | Path) -> EditReport:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return EditReport(data["guide_path"], data["guide_sha256"], data["created_at"], data["blocks"],
                          [Edit(**e) for e in data["edits"]], data["protected_blocks"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as err:
        raise ReviseError(f"cannot read edit report {path}: {err}") from err


def validate_report(report: EditReport, blocks: list[Block]) -> list[str]:
    known, problems, seen = {b.id for b in blocks}, [], set()
    for e in report.edits:
        if e.id in seen:
            problems.append(f"duplicate edit id {e.id}")
        seen.add(e.id)
        if e.type not in EDIT_TYPES:
            problems.append(f"{e.id}: unknown edit type {e.type!r}")
            continue
        if not e.targets:
            problems.append(f"{e.id}: no targets")
        for t in e.targets:
            if t not in known:
                problems.append(f"{e.id}: unknown block {t}")
        if e.type in NEEDS_REPLACEMENT and not e.replacement:
            problems.append(f"{e.id}: {e.type} needs a replacement")
        if e.type == "fix" and e.replacement is None:
            problems.append(f"{e.id}: fix needs a replacement")
        if e.type == "merge" and len(e.targets) < 2:
            problems.append(f"{e.id}: merge needs at least two targets")
        if e.type == "move" and (len(e.targets) != 1 or e.anchor not in known):
            problems.append(f"{e.id}: move needs one target and an anchor block")
    return problems


def mark_conflicts(report: EditReport) -> None:
    by_block: dict[str, list[Edit]] = {}
    for e in report.edits:
        for t in e.targets:
            by_block.setdefault(t, []).append(e)
    for e in report.edits:
        e.conflicts = sorted({o.id for t in e.targets for o in by_block[t] if o.id != e.id})
```

```python
# agent/study_guide/revise/apply.py
"""Apply accepted edits by block id, then check post-conditions. No model call."""
from __future__ import annotations

import re

from agent.study_guide.revise.edits import Edit, EditReport, ReviseError
from agent.study_guide.revise.segment import Block, check_headings, segment

_PAGE_CITE_RE = re.compile(r"\bpp?\.\s?\d+")


def _trailing_blanks(lines: list[str]) -> int:
    n = 0
    while n < len(lines) and not lines[-1 - n]:
        n += 1
    return n


def _replace_block(block: Block, lines: list[str], text: str) -> list[str]:
    return text.split("\n") + [""] * _trailing_blanks(lines[block.start:block.end])


def _retitled(block: Block, heading: str) -> str:
    return "\n".join([heading] + block.text.split("\n")[1:])


def _fixed(block: Block, edit: Edit) -> str:
    if edit.quote is None:
        return edit.replacement or ""
    if block.text.count(edit.quote) != 1:
        raise ReviseError(f"{edit.id}: the quote must occur exactly once in its block")
    return block.text.replace(edit.quote, edit.replacement or "", 1)


def apply_edits(body: str, report: EditReport, accepted: set[str]) -> str:
    by_id = {e.id: e for e in report.edits}
    unknown = sorted(accepted - set(by_id))
    if unknown:
        raise ReviseError(f"unknown edit id(s): {', '.join(unknown)}")
    selected = [by_id[i] for i in sorted(accepted) if by_id[i].type != "note"]
    owner: dict[str, str] = {}
    for e in selected:
        for t in e.targets:
            if t in owner:
                raise ReviseError(f"{owner[t]} and {e.id} edit the same block ({t}); accept only one")
            owner[t] = e.id
    blocks = segment(body)
    lines = body.split("\n")
    known = {b.id: b for b in blocks}
    for e in selected:
        for t in e.targets + ([e.anchor] if e.anchor else []):
            if t not in known:
                raise ReviseError(f"{e.id}: block {t} is not in this guide")
    delete, replace, moved = set(), {}, {}
    for e in selected:
        first = known[e.targets[0]]
        if e.type == "delete":
            delete.update(e.targets)
        elif e.type in ("shrink", "link"):
            replace[first.id] = e.replacement or ""
        elif e.type == "retitle":
            replace[first.id] = _retitled(first, e.replacement or "")
        elif e.type == "fix":
            replace[first.id] = _fixed(first, e)
        elif e.type == "merge":
            replace[first.id] = e.replacement or ""
            delete.update(e.targets[1:])
        elif e.type == "move":
            if e.anchor in delete:
                raise ReviseError(f"{e.id}: the anchor block is deleted by another edit")
            moved.setdefault(e.anchor, []).append(first.id)
    moving = {i for ids in moved.values() for i in ids}
    out: list[str] = []
    for b in blocks:
        if b.id in delete or b.id in moving:
            continue
        out += _replace_block(b, lines, replace[b.id]) if b.id in replace else lines[b.start:b.end]
        for mid in moved.get(b.id, []):
            m = known[mid]
            if out and out[-1]:
                out.append("")
            out += lines[m.start:m.end]
    after = "\n".join(out)
    _check_postconditions(body, after, blocks, selected, set(owner), moving)
    return after


def _check_postconditions(before: str, after: str, blocks: list[Block], selected: list[Edit],
                          touched: set[str], moving: set[str]) -> None:
    problems = []
    allowed = sum(len((e.replacement or "").split()) for e in selected if e.type == "fix")
    if len(after.split()) > len(before.split()) + allowed:
        problems.append("the revised guide is longer than the original")
    if len(_PAGE_CITE_RE.findall(after)) > len(_PAGE_CITE_RE.findall(before)):
        problems.append("the edits introduce a new page citation")
    new_heading = sorted(set(check_headings(after)) - set(check_headings(before)))
    if new_heading:
        problems.append("the edits introduce heading problems: " + "; ".join(new_heading))
    for b in blocks:
        if b.id not in touched and b.id not in moving and b.text not in after:
            problems.append(f"block {b.id} changed without an accepted edit")
    if problems:
        raise ReviseError("post-condition failed, nothing written: " + " | ".join(problems))


def changelog(report: EditReport, accepted: set[str]) -> str:
    rows = ["# Revision changelog", ""]
    for e in report.edits:
        if e.id not in accepted:
            continue
        verb = "acknowledged (advisory)" if e.type == "note" else "applied"
        rows.append(f"- **{e.id}** ({e.stage}, {e.type}) {verb}: {e.rationale}")
    return "\n".join(rows) + "\n"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_apply.py -q`
Expected: PASS (17 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/edits.py agent/study_guide/revise/apply.py tests/agent/study_guide/test_study_guide_revise_apply.py
git commit -m "revise: edit report, deterministic apply, post-conditions"
```

---

### Task 4: Evidence loading and the relevance stage

**Files:**
- Create: `agent/study_guide/revise/evidence.py`
- Create: `agent/study_guide/revise/relevance.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_relevance.py`

**Interfaces:**
- Consumes: `build_plan`, `PlanError`, `DROPPED` (plan.py); `GuideSpec`, `TopicSpec`, `ReviseSpec` (spec.py); `Block`, `Edit`, `ReviseError`; `load_chunks`, `load_shard`.
- Produces:
  - `EvidenceChunk(chunk_id, citation, weight, embedding: tuple[float, ...])`; `load_evidence(spec, root, *, client=None, search=None, chunks=None, cards=None) -> list[EvidenceChunk]`
  - `cosine(a, b)`; `Relevance(block_id, score, nearest)`; `score_blocks(blocks, evidence, embed, *, min_words) -> dict[str, Relevance]`; `relevance_edits(blocks, scores, *, low, high, start=1) -> tuple[list[Edit], list[str]]` (edits, protected block ids)

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_relevance.py
import dataclasses

import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.evidence import EvidenceChunk, load_evidence
from agent.study_guide.revise.relevance import cosine, relevance_edits, score_blocks
from agent.study_guide.revise.segment import segment
from agent.study_guide.spec import EvidenceRule, ReviseSpec, SourceRule
from rv_helpers import bag_embed
from sg_helpers import CARDS, CHUNKS, make_spec, root  # noqa: F401 (fixtures)

VOCAB = ["wald", "score", "package"]
BODY = ("# T\n\n## Wald statistic\n\n" + "wald wald statistic words " * 12 + "\n\n"
        "## Software packages\n\n" + "package package install " * 12 + "\n\n"
        "## Score test\n\n" + "score test words " * 12 + "\n")
EVIDENCE = [
    EvidenceChunk("e1", "Exam Q1, p. 1", 3.0, (1.0, 0.0, 0.0)),    # about Wald, exam weight
    EvidenceChunk("e2", "Pset 2, p. 3", 1.5, (0.0, 1.0, 0.0)),     # about the score test
]


def test_cosine():
    assert cosine((1, 0), (1, 0)) == pytest.approx(1.0) and cosine((1, 0), (0, 1)) == 0.0 and cosine((0, 0), (1, 1)) == 0.0


def test_scores_use_the_best_weighted_similarity():
    blocks = segment(BODY)
    scores = score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20)
    by = {b.heading_path[-1]: scores[b.id] for b in blocks if b.id in scores}
    assert by["Wald statistic"].score == pytest.approx(1.0)          # exam weight 3 / max 3
    assert by["Score test"].score == pytest.approx(0.5)              # pset weight 1.5 / 3
    assert by["Software packages"].score == 0.0
    assert by["Wald statistic"].nearest[0][0] == "Exam Q1, p. 1"


def test_short_blocks_are_not_scored():
    blocks = segment("# T\n\n## Tiny\n\nfew words\n")
    assert score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20) == {}


def test_low_scores_become_delete_proposals_and_high_scores_are_protected():
    blocks = segment(BODY)
    scores = score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20)
    edits, protected = relevance_edits(blocks, scores, low=0.3, high=0.9)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    assert [(e.type, e.targets) for e in edits] == [("delete", [ids["Software packages"]])]
    assert edits[0].stage == "relevance" and edits[0].id == "rel-001" and edits[0].evidence
    assert protected == [ids["Wald statistic"]]


def test_no_evidence_is_an_error_for_the_relevance_stage():
    with pytest.raises(ReviseError, match="evidence"):
        score_blocks(segment(BODY), [], bag_embed(VOCAB), min_words=20)


def test_evidence_rules_resolve_through_the_plan_machinery(make_spec, root, tmp_path):
    spec = make_spec('[[topic]]\ntitle = "T"\ninstruction = "i"\n\n  [[topic.source]]\n  kind = "file"\n  file = "x"\n')
    revise = ReviseSpec("m", ("relevance",), (EvidenceRule(SourceRule("file", file="sl", max=5), 3.0),))
    spec = dataclasses.replace(spec, revise=revise)
    chunks = [dict(c, embedding=[1.0, 0.0]) for c in CHUNKS]
    found = load_evidence(spec, root, search=lambda *a, **k: [], chunks=chunks, cards=CARDS)
    assert found and all(isinstance(e, EvidenceChunk) and e.weight == 3.0 for e in found)
    assert {e.chunk_id for e in found} <= {"sl-1", "sl-2"}
    assert load_evidence(dataclasses.replace(spec, revise=None), root, chunks=chunks, cards=CARDS) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_relevance.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.study_guide.revise.evidence`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/evidence.py
"""Resolve the [revise] evidence rules to weighted, embedded chunks by reusing the plan machinery."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from agent.study_guide.plan import DROPPED, build_plan
from agent.study_guide.spec import GuideSpec, TopicSpec


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    citation: str
    weight: float
    embedding: tuple[float, ...]


def load_evidence(spec: GuideSpec, root: str, *, client=None, search=None, chunks=None, cards=None) -> list[EvidenceChunk]:
    if spec.revise is None or not spec.revise.evidence:
        return []
    topics = tuple(TopicSpec(f"evidence-{i}", "", (ev.rule,)) for i, ev in enumerate(spec.revise.evidence, 1))
    sub = dataclasses.replace(spec, topics=topics, comparisons=(), notes=())
    plan = build_plan(sub, root, client=client, search=search, chunks=chunks, cards=cards)
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    by_id = {c["chunk_id"]: c for c in chunks}
    found: dict[str, EvidenceChunk] = {}
    for ev, topic in zip(spec.revise.evidence, plan.topics):
        for entry in topic.entries:
            chunk = by_id.get(entry.chunk_id)
            if entry.status == DROPPED or chunk is None or not chunk.get("embedding"):
                continue
            current = found.get(entry.chunk_id)
            if current is None or current.weight < ev.weight:
                found[entry.chunk_id] = EvidenceChunk(entry.chunk_id, entry.citation, ev.weight, tuple(chunk["embedding"]))
    return list(found.values())
```

```python
# agent/study_guide/revise/relevance.py
"""Score each block against the weighted evidence; propose deletes below a floor, mark protected blocks."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.evidence import EvidenceChunk
from agent.study_guide.revise.segment import Block


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return 0.0 if not na or not nb else sum(x * y for x, y in zip(a, b)) / (na * nb)


@dataclass(frozen=True)
class Relevance:
    block_id: str
    score: float
    nearest: tuple[tuple[str, float], ...]


def score_blocks(blocks: list[Block], evidence: list[EvidenceChunk], embed: Callable[[str], list[float]], *,
                 min_words: int) -> dict[str, Relevance]:
    if not evidence:
        raise ReviseError("the relevance stage needs evidence: add [[revise.evidence]] rules that resolve to chunks")
    top = max(e.weight for e in evidence)
    out: dict[str, Relevance] = {}
    for b in blocks:
        if b.words < min_words:
            continue
        vec = embed(b.text)
        ranked = sorted(((cosine(vec, e.embedding) * e.weight / top, e.citation) for e in evidence), reverse=True)
        out[b.id] = Relevance(b.id, ranked[0][0], tuple((c, round(s, 4)) for s, c in ranked[:3]))
    return out


def relevance_edits(blocks: list[Block], scores: dict[str, Relevance], *, low: float, high: float,
                    start: int = 1) -> tuple[list[Edit], list[str]]:
    edits, protected, n = [], [], start
    for b in blocks:
        r = scores.get(b.id)
        if r is None:
            continue
        if r.score >= high:
            protected.append(b.id)
        elif r.score < low:
            edits.append(Edit(
                id=f"rel-{n:03d}", type="delete", stage="relevance", targets=[b.id],
                rationale=f"no course evidence points here (relevance {r.score:.2f}, floor {low:.2f})",
                evidence=[c for c, _ in r.nearest], severity="medium" if b.words > 150 else "low",
                confidence=round(1 - r.score / low, 2)))
            n += 1
    return edits, protected
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_relevance.py -q`
Expected: PASS (6 passed). If `test_evidence_rules_resolve_through_the_plan_machinery` fails because the `sl` file in `sg_helpers.CARDS` is named differently, use the card/file name that `test_study_guide_plan.py` uses for its `kind = "file"` case.

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/evidence.py agent/study_guide/revise/relevance.py tests/agent/study_guide/test_study_guide_revise_relevance.py
git commit -m "revise: weighted evidence loading and the relevance stage"
```

---

### Task 5: Review items and decisions

**Files:**
- Create: `agent/study_guide/revise/review.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_review.py`

**Interfaces:**
- Consumes: `EditReport`, `Edit`, `ReviseError`, `segment`.
- Produces: `review_items(report, body) -> list[dict]`; `write_review_items(report, body, path)`; `accepted_ids(report, decisions: dict[str, str]) -> set[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_review.py
import json

import pytest

from agent.study_guide.revise.edits import Edit, EditReport, ReviseError
from agent.study_guide.revise.review import accepted_ids, review_items, write_review_items
from agent.study_guide.revise.segment import segment

BODY = "# T\n\n## A\n\nalpha text\n\n## B\n\nbeta text\n"


def _report():
    ids = {b.heading_path[-1]: b.id for b in segment(BODY)}
    edits = [Edit("e1", "delete", [ids["A"]], "off topic", stage="relevance", evidence=["Exam, p. 1"], protected=True),
             Edit("e2", "fix", [ids["B"]], "wrong", stage="correctness", quote="beta", replacement="gamma")]
    return EditReport("g.md", "sha", "now", [], edits, [ids["A"]])


def test_review_items_show_before_and_after():
    items = review_items(_report(), BODY)
    assert items[0]["id"] == "e1" and items[0]["before"].startswith("## A") and items[0]["after"] is None
    assert items[0]["protected"] is True and items[0]["evidence"] == ["Exam, p. 1"]
    assert items[1]["after"] == "gamma" and items[1]["quote"] == "beta"


def test_write_review_items(tmp_path):
    write_review_items(_report(), BODY, tmp_path / "r.json")
    assert [i["id"] for i in json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))] == ["e1", "e2"]


def test_only_explicit_accepts_count():
    assert accepted_ids(_report(), {"e1": "accept", "e2": "reject"}) == {"e1"}
    assert accepted_ids(_report(), {}) == set()


@pytest.mark.parametrize("decisions,fragment", [({"zzz": "accept"}, "unknown"), ({"e1": "maybe"}, "accept")])
def test_bad_decisions_are_rejected(decisions, fragment):
    with pytest.raises(ReviseError, match=fragment):
        accepted_ids(_report(), decisions)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_review.py -q`
Expected: FAIL (`ModuleNotFoundError: ...review`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/review.py
"""Review items for the interactive Artifact, and reading its decisions back."""
from __future__ import annotations

import json
from pathlib import Path

from agent.study_guide.revise.edits import EditReport, ReviseError
from agent.study_guide.revise.segment import segment


def review_items(report: EditReport, body: str) -> list[dict]:
    by_id = {b.id: b for b in segment(body)}
    items = []
    for e in report.edits:
        items.append({
            "id": e.id, "type": e.type, "stage": e.stage, "severity": e.severity, "confidence": e.confidence,
            "rationale": e.rationale, "evidence": e.evidence, "protected": e.protected, "conflicts": e.conflicts,
            "targets": e.targets, "quote": e.quote, "anchor": e.anchor,
            "before": "\n\n".join(by_id[t].text for t in e.targets if t in by_id), "after": e.replacement,
        })
    return items


def write_review_items(report: EditReport, body: str, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(review_items(report, body), indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def accepted_ids(report: EditReport, decisions: dict[str, str]) -> set[str]:
    known = {e.id for e in report.edits}
    for key, value in decisions.items():
        if key not in known:
            raise ReviseError(f"unknown edit id in the decisions: {key!r}")
        if value not in ("accept", "reject"):
            raise ReviseError(f"decision for {key!r} must be 'accept' or 'reject', got {value!r}")
    return {k for k, v in decisions.items() if v == "accept"}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_review.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/review.py tests/agent/study_guide/test_study_guide_revise_review.py
git commit -m "revise: review items and decision reading"
```

---

### Task 6: Deduplication stage

**Files:**
- Create: `agent/study_guide/revise/dedup.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_dedup.py`

**Interfaces:**
- Consumes: `Block`, `segment`, `Edit`, `ReviseError`, `cosine`.
- Produces: `normalize_latex(s)`, `equation_set(text)`, `find_duplicate_clusters(blocks, embed, *, similarity, min_words, eq_overlap=0.6) -> list[list[str]]`, `DEDUP_SCHEMA`, `build_dedup_prompt(blocks)`, `parse_dedup(data, cluster, blocks_by_id, start) -> list[Edit]`, `dedup_edits(llm, blocks, embed, *, similarity, min_words, start=1) -> list[Edit]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_dedup.py
import pytest

from agent.study_guide.revise.dedup import (
    build_dedup_prompt, dedup_edits, equation_set, find_duplicate_clusters, normalize_latex, parse_dedup,
)
from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM, bag_embed

VOCAB = ["wald", "score", "package"]
EQ1 = "$$\\left( \\hat\\beta - \\beta_0 \\right)^2 / V$$"
EQ2 = "$$(\\hat\\beta-\\beta_0)^2/V$$"
BODY = ("# T\n\n## Wald\n\n" + "wald statistic words " * 15 + "\n\n" + EQ1 + "\n\n"
        "## Wald again\n\n" + "wald statistic words " * 15 + "\n\n" + EQ2 + "\n\n"
        "## Score\n\n" + "score test words " * 15 + "\n")


def test_normalize_latex_ignores_spacing_and_sizing_macros():
    assert normalize_latex("\\left( x + y \\right)") == normalize_latex("(x+y)")
    assert equation_set(EQ1) == equation_set(EQ2) and len(equation_set(EQ1)) == 1


def test_near_duplicate_blocks_cluster_and_unrelated_blocks_do_not():
    blocks = segment(BODY)
    clusters = find_duplicate_clusters(blocks, bag_embed(VOCAB), similarity=0.95, min_words=20)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    assert clusters == [[ids["Wald"], ids["Wald again"]]]


def test_prompt_lists_the_blocks_with_ids():
    blocks = segment(BODY)[1:3]
    prompt = build_dedup_prompt(blocks)
    assert blocks[0].id in prompt and blocks[1].id in prompt and "canonical" in prompt


def test_parse_links_non_canonical_blocks():
    blocks = segment(BODY)
    by_id = {b.id: b for b in blocks}
    a, b = blocks[1].id, blocks[2].id
    data = {"canonical": a, "actions": [{"block": b, "action": "link", "replacement": "## Wald again\n\nSee [[#Wald]].",
                                         "rationale": "same derivation"}]}
    edits = parse_dedup(data, [a, b], by_id, start=1)
    assert [(e.type, e.targets, e.evidence, e.id) for e in edits] == [("link", [b], [a], "ded-001")]


@pytest.mark.parametrize("data,fragment", [
    ({"canonical": "zzz", "actions": []}, "canonical"),
    ({"canonical": "A", "actions": [{"block": "A", "action": "delete", "rationale": "x"}]}, "canonical block"),
    ({"canonical": "A", "actions": [{"block": "B", "action": "link", "rationale": "x"}]}, "replacement"),
])
def test_parse_rejects_bad_responses(data, fragment):
    blocks = {"A": None, "B": None}
    with pytest.raises(ReviseError, match=fragment):
        parse_dedup(data, ["A", "B"], blocks, start=1)


def test_dedup_edits_makes_one_call_per_cluster():
    blocks = segment(BODY)
    a, b = blocks[1].id, blocks[2].id
    llm = ScriptedLLM([{"canonical": a, "actions": [{"block": b, "action": "delete", "rationale": "repeat"}]}])
    edits = dedup_edits(llm, blocks, bag_embed(VOCAB), similarity=0.95, min_words=20)
    assert len(llm.calls) == 1 and [e.type for e in edits] == ["delete"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_dedup.py -q`
Expected: FAIL (`ModuleNotFoundError: ...dedup`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/dedup.py
"""Find blocks that restate each other (embedding similarity or shared equations) and ask for a decision."""
from __future__ import annotations

import re
from typing import Callable

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.relevance import cosine
from agent.study_guide.revise.segment import Block

MAX_CLUSTER = 6
_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.S)
_SIZING_RE = re.compile(r"\\(?:left|right|displaystyle|bigg?|Bigg?|quad|qquad|,|;|:|!)(?![A-Za-z])")

DEDUP_SCHEMA = {
    "type": "object",
    "properties": {
        "canonical": {"type": "string"},
        "actions": {"type": "array", "items": {
            "type": "object",
            "properties": {"block": {"type": "string"}, "action": {"type": "string", "enum": ["link", "delete", "keep"]},
                           "replacement": {"type": ["string", "null"]}, "rationale": {"type": "string"}},
            "required": ["block", "action", "rationale"]}},
    },
    "required": ["canonical", "actions"],
}


def normalize_latex(s: str) -> str:
    return re.sub(r"\s+", "", _SIZING_RE.sub("", s).replace("\\widehat", "\\hat"))


def equation_set(text: str) -> set[str]:
    return {normalize_latex(m) for m in _DISPLAY_RE.findall(text)}


def find_duplicate_clusters(blocks: list[Block], embed: Callable[[str], list[float]], *, similarity: float,
                            min_words: int, eq_overlap: float = 0.6) -> list[list[str]]:
    pool = [b for b in blocks if b.words >= min_words]
    vecs = {b.id: embed(b.text) for b in pool}
    eqs = {b.id: equation_set(b.text) for b in pool}
    parent = {b.id: b.id for b in pool}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            union = eqs[a.id] | eqs[b.id]
            shared = len(eqs[a.id] & eqs[b.id]) / len(union) if union else 0.0
            if cosine(vecs[a.id], vecs[b.id]) >= similarity or (len(union) >= 2 and shared >= eq_overlap):
                parent[find(a.id)] = find(b.id)
    groups: dict[str, list[str]] = {}
    for b in pool:
        groups.setdefault(find(b.id), []).append(b.id)
    return [ids for ids in groups.values() if len(ids) > 1]


def build_dedup_prompt(blocks: list[Block]) -> str:
    listed = "\n\n".join(f"[{b.id}] {' > '.join(b.heading_path)}\n\"\"\"\n{b.text}\n\"\"\"" for b in blocks)
    return (
        "These blocks of one study guide restate overlapping material. Choose the canonical block: the one "
        "that explains the idea best and should stay. For every other block decide: 'link' (replace it with a "
        "short block that keeps its heading and points to the canonical heading with an Obsidian link such as "
        "[[#Heading]], giving the full replacement text in 'replacement'), 'delete' (it adds nothing), or "
        "'keep' (it adds value here). Never add new claims; do not rewrite the canonical block.\n\n"
        "Return JSON: {\"canonical\": <block id>, \"actions\": [{\"block\", \"action\", \"replacement\", \"rationale\"}]}\n\n"
        f"Blocks:\n{listed}\n")


def parse_dedup(data: dict, cluster: list[str], blocks_by_id: dict, start: int) -> list[Edit]:
    canonical = data.get("canonical")
    if canonical not in cluster:
        raise ReviseError(f"dedup: canonical block {canonical!r} is not in the cluster")
    edits, n = [], start
    for a in data.get("actions", []):
        block, action = a.get("block"), a.get("action")
        if block not in cluster:
            raise ReviseError(f"dedup: block {block!r} is not in the cluster")
        if block == canonical:
            raise ReviseError("dedup: the canonical block cannot be an action target")
        if action == "keep":
            continue
        if action == "link" and not a.get("replacement"):
            raise ReviseError(f"dedup: link for {block} needs a replacement")
        edits.append(Edit(
            id=f"ded-{n:03d}", type=action, stage="dedup", targets=[block], rationale=a.get("rationale", ""),
            evidence=[canonical], severity="low", confidence=0.6, replacement=a.get("replacement")))
        n += 1
    return edits


def dedup_edits(llm, blocks: list[Block], embed, *, similarity: float, min_words: int, start: int = 1) -> list[Edit]:
    by_id = {b.id: b for b in blocks}
    edits: list[Edit] = []
    for cluster in find_duplicate_clusters(blocks, embed, similarity=similarity, min_words=min_words):
        members = sorted(cluster, key=lambda i: -by_id[i].words)[:MAX_CLUSTER]
        data = llm.generate_structured(build_dedup_prompt([by_id[i] for i in members]), DEDUP_SCHEMA)
        edits += parse_dedup(data, members, by_id, start + len(edits))
    return edits
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_dedup.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/dedup.py tests/agent/study_guide/test_study_guide_revise_dedup.py
git commit -m "revise: duplicate clusters and the dedup decision call"
```

---

### Task 7: Correctness audit

**Files:**
- Create: `agent/study_guide/revise/audit.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_audit.py`

**Interfaces:**
- Consumes: `Block`, `Edit`, `ReviseError`.
- Produces: `AUDIT_SCHEMA`; `build_audit_prompt(title, blocks, passages)` where `passages` is `list[tuple[label, citation, text]]`; `parse_audit(data, blocks_by_id, labels, start) -> tuple[list[Edit], list[str]]` (edits, problems); `needs_arithmetic_check(block)`; `build_arith_prompt(block)`; `parse_arith(text, block, start) -> list[Edit]`; `audit_section(llm, title, blocks, passages, start=1) -> tuple[list[Edit], list[str]]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_audit.py
from agent.study_guide.revise.audit import (
    audit_section, build_arith_prompt, build_audit_prompt, needs_arithmetic_check, parse_arith, parse_audit,
)
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM

BODY = ("# T\n\n## Wald\n\nThe statistic has 3 degrees of freedom and equals 9.17 here.\n\n"
        "### Worked\n\n**Constructed example (not from the sources)** n=100, W = 4/0.436 = 9.17.\n")
PASSAGES = [("S1", "Hansen §9.10, p. 268", "The Wald statistic is chi-square with q degrees of freedom.")]


def _blocks():
    blocks = segment(BODY)
    return blocks, {b.id: b for b in blocks}


def test_prompt_contains_blocks_and_labelled_passages():
    blocks, _ = _blocks()
    prompt = build_audit_prompt("The Wald test", blocks[1:], PASSAGES)
    assert blocks[1].id in prompt and "[S1] Hansen §9.10, p. 268" in prompt and "The Wald test" in prompt


def test_a_contradiction_becomes_a_fix_with_its_source():
    blocks, by_id = _blocks()
    data = {"findings": [{"block": blocks[1].id, "quote": "3 degrees of freedom", "verdict": "contradicted",
                          "explanation": "q, not 3", "source_label": "S1", "replacement": "q degrees of freedom"}]}
    edits, problems = parse_audit(data, by_id, {"S1"}, start=1)
    assert problems == [] and len(edits) == 1
    e = edits[0]
    assert (e.type, e.quote, e.replacement, e.evidence, e.stage, e.id) == (
        "fix", "3 degrees of freedom", "q degrees of freedom", ["S1"], "correctness", "cor-001")


def test_a_finding_without_a_replacement_is_an_advisory_note():
    blocks, by_id = _blocks()
    data = {"findings": [{"block": blocks[1].id, "quote": "equals 9.17", "verdict": "unsupported", "explanation": "no source"}]}
    edits, _ = parse_audit(data, by_id, {"S1"}, start=1)
    assert [e.type for e in edits] == ["note"]


def test_missing_or_ambiguous_quotes_and_unknown_labels_are_reported_not_applied():
    blocks, by_id = _blocks()
    data = {"findings": [
        {"block": blocks[1].id, "quote": "not in the block", "verdict": "unsupported", "explanation": "x"},
        {"block": blocks[1].id, "quote": "the", "verdict": "unsupported", "explanation": "x"},
        {"block": "nope", "quote": "x", "verdict": "unsupported", "explanation": "x"},
        {"block": blocks[1].id, "quote": "3 degrees", "verdict": "contradicted", "explanation": "x",
         "source_label": "S9", "replacement": "q degrees"},
    ]}
    edits, problems = parse_audit(data, by_id, {"S1"}, start=1)
    assert edits == [] and len(problems) == 4


def test_arithmetic_check_applies_to_constructed_and_worked_blocks():
    blocks, _ = _blocks()
    assert needs_arithmetic_check(blocks[2]) and not needs_arithmetic_check(blocks[1])
    assert "Python" in build_arith_prompt(blocks[2])


def test_parse_arith_turns_failures_into_notes():
    blocks, _ = _blocks()
    text = 'Here is the result:\n[{"quote": "4/0.436 = 9.17", "computed": "9.174", "ok": true}, ' \
           '{"quote": "W = 4/0.436", "computed": "10.5", "ok": false}]'
    edits = parse_arith(text, blocks[2], start=1)
    assert [(e.type, e.stage, e.targets) for e in edits] == [("note", "correctness", [blocks[2].id])]
    assert "10.5" in edits[0].rationale
    assert parse_arith("no json here", blocks[2], start=1) == []


def test_audit_section_makes_a_structured_call_and_a_code_call_for_worked_blocks():
    blocks, _ = _blocks()
    llm = ScriptedLLM([{"findings": []}, '[{"quote": "x", "computed": "1", "ok": true}]'])
    edits, problems = audit_section(llm, "The Wald test", blocks[1:], PASSAGES)
    assert llm.kinds == ["structured", "code"] and edits == [] and problems == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_audit.py -q`
Expected: FAIL (`ModuleNotFoundError: ...audit`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/audit.py
"""Correctness audit of one guide section against that section's own source passages."""
from __future__ import annotations

import json
import re

from agent.study_guide.revise.edits import Edit
from agent.study_guide.revise.segment import Block

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"block": {"type": "string"}, "quote": {"type": "string"},
                       "verdict": {"type": "string", "enum": ["unsupported", "contradicted", "arithmetic_error"]},
                       "explanation": {"type": "string"}, "source_label": {"type": ["string", "null"]},
                       "replacement": {"type": ["string", "null"]}},
        "required": ["block", "quote", "verdict", "explanation"]}}},
    "required": ["findings"],
}
_WORKED_RE = re.compile(r"problem|worked|step-by-step|example", re.I)


def build_audit_prompt(title: str, blocks: list[Block], passages: list[tuple[str, str, str]]) -> str:
    text = "\n\n".join(f"[{b.id}] {' > '.join(b.heading_path)}\n\"\"\"\n{b.text}\n\"\"\"" for b in blocks)
    sources = "\n\n".join(f"[{label}] {citation}\n\"\"\"\n{body}\n\"\"\"" for label, citation, body in passages)
    return (
        f"You are auditing the section \"{title}\" of a study guide against the source passages below. For each "
        "claim, equation or number in the section that is NOT supported by the passages, or that a passage "
        "contradicts, or that is arithmetically wrong, report a finding. A 'Constructed example (not from the "
        "sources)' is allowed to have no source, but its arithmetic must be right. Rules: 'quote' must be copied "
        "exactly from one block and occur once in it; give 'replacement' (the corrected text for that quote, "
        "supported by a passage) only when a passage supports the correction, and name that passage's label in "
        "'source_label'; otherwise leave 'replacement' null. Do not report style problems. Return JSON "
        "{\"findings\": [...]} (empty list if the section is sound).\n\n"
        f"=== SECTION BLOCKS ===\n{text}\n\n=== SOURCE PASSAGES ===\n{sources}\n")


def parse_audit(data: dict, blocks_by_id: dict[str, Block], labels: set[str], start: int) -> tuple[list[Edit], list[str]]:
    edits, problems, n = [], [], start
    for f in data.get("findings", []):
        block = blocks_by_id.get(f.get("block"))
        quote, label, replacement = f.get("quote", ""), f.get("source_label"), f.get("replacement")
        if block is None:
            problems.append(f"finding names an unknown block {f.get('block')!r}")
        elif block.text.count(quote) != 1 or not quote:
            problems.append(f"{block.id}: the quote is absent or not unique: {quote[:60]!r}")
        elif f.get("verdict") == "contradicted" and label not in labels:
            problems.append(f"{block.id}: the contradicting source {label!r} is not one of this section's passages")
        else:
            fixed = bool(replacement)
            edits.append(Edit(
                id=f"cor-{n:03d}", type="fix" if fixed else "note", stage="correctness", targets=[block.id],
                rationale=f"{f['verdict']}: {f['explanation']}", evidence=[label] if label else [],
                severity="high" if f["verdict"] != "unsupported" else "medium", confidence=0.6,
                replacement=replacement if fixed else None, quote=quote if fixed else None))
            n += 1
    return edits, problems


def needs_arithmetic_check(block: Block) -> bool:
    return bool(re.search(r"\d", block.text)) and (block.constructed or bool(_WORKED_RE.search(block.heading_path[-1] if block.heading_path else "")))


def build_arith_prompt(block: Block) -> str:
    return (
        "Recompute every numerical result stated in the text below using Python (use the code tool). Reply with "
        "ONLY a JSON list of objects {\"quote\": <the stated result, copied>, \"computed\": <your value>, "
        "\"ok\": <true if the stated result matches to the precision shown>}.\n\n" + block.text + "\n")


def parse_arith(text: str, block: Block, start: int) -> list[Edit]:
    m = re.search(r"\[.*\]", text, re.S)
    try:
        rows = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        return []
    edits, n = [], start
    for r in rows:
        if isinstance(r, dict) and r.get("ok") is False:
            edits.append(Edit(
                id=f"cor-{n:03d}", type="note", stage="correctness", targets=[block.id], severity="high", confidence=0.7,
                rationale=f"arithmetic does not check: stated {r.get('quote', '')!r}, computed {r.get('computed', '')!r}"))
            n += 1
    return edits


def audit_section(llm, title: str, blocks: list[Block], passages: list[tuple[str, str, str]],
                  start: int = 1) -> tuple[list[Edit], list[str]]:
    data = llm.generate_structured(build_audit_prompt(title, blocks, passages), AUDIT_SCHEMA)
    edits, problems = parse_audit(data, {b.id: b for b in blocks}, {p[0] for p in passages}, start)
    for b in blocks:
        if needs_arithmetic_check(b):
            edits += parse_arith(llm.generate_text(build_arith_prompt(b), code_execution=True), b, start + len(edits))
    return edits, problems
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_audit.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/audit.py tests/agent/study_guide/test_study_guide_revise_audit.py
git commit -m "revise: per-section correctness audit with arithmetic recheck"
```

---

### Task 8: Organization stage

**Files:**
- Create: `agent/study_guide/revise/organize.py`
- Test: `tests/agent/study_guide/test_study_guide_revise_organize.py`

**Interfaces:**
- Consumes: `Block`, `Edit`, `ReviseError`.
- Produces: `ORGANIZE_SCHEMA`; `mechanical_heading_edits(blocks, start=1) -> list[Edit]`; `build_outline(blocks, flags: dict[str, list[str]]) -> str`; `parse_organize(data, blocks_by_id, start) -> list[Edit]`; `organize_edits(llm, blocks, flags, start=1) -> list[Edit]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_organize.py
import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.organize import (
    build_outline, mechanical_heading_edits, organize_edits, parse_organize,
)
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM

BODY = "# T\n\n## A\n\nalpha words\n\n# Stray\n\nstray words\n\n## B\n\nbeta words\n"


def test_a_body_h1_becomes_a_retitle_to_h2():
    blocks = segment(BODY)
    edits = mechanical_heading_edits(blocks)
    assert [(e.type, e.targets, e.replacement, e.stage) for e in edits] == [
        ("retitle", [blocks[2].id], "## Stray", "organization")]


def test_outline_has_ids_levels_words_and_flags_but_no_body_text():
    blocks = segment(BODY)
    outline = build_outline(blocks, {blocks[1].id: ["duplicate"]})
    assert blocks[1].id in outline and "alpha words" not in outline and "duplicate" in outline and "H2" in outline


def test_parse_retitle_and_move():
    blocks = segment(BODY)
    by_id = {b.id: b for b in blocks}
    data = {"edits": [{"type": "retitle", "block": blocks[1].id, "new_heading": "Alpha", "rationale": "clearer"},
                      {"type": "move", "block": blocks[3].id, "after": blocks[1].id, "rationale": "order"}]}
    edits = parse_organize(data, by_id, start=1)
    assert [(e.type, e.replacement, e.anchor) for e in edits] == [("retitle", "## Alpha", None), ("move", None, blocks[1].id)]


@pytest.mark.parametrize("data", [
    {"edits": [{"type": "retitle", "block": "zzz", "new_heading": "X", "rationale": "r"}]},
    {"edits": [{"type": "move", "block": "A", "after": "zzz", "rationale": "r"}]},
    {"edits": [{"type": "retitle", "block": "A", "rationale": "r"}]},
    {"edits": [{"type": "explode", "block": "A", "rationale": "r"}]},
])
def test_bad_responses_are_rejected(data):
    with pytest.raises(ReviseError):
        parse_organize(data, {"A": segment("## A\n\nx\n")[0]}, start=1)


def test_organize_edits_combines_mechanical_and_model_proposals():
    blocks = segment(BODY)
    llm = ScriptedLLM([{"edits": []}])
    edits = organize_edits(llm, blocks, {})
    assert len(llm.calls) == 1 and [e.type for e in edits] == ["retitle"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_organize.py -q`
Expected: FAIL (`ModuleNotFoundError: ...organize`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/organize.py
"""Heading hierarchy and order: mechanical fixes plus one outline-only model call."""
from __future__ import annotations

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.segment import Block

ORGANIZE_SCHEMA = {
    "type": "object",
    "properties": {"edits": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string", "enum": ["retitle", "move"]}, "block": {"type": "string"},
                       "new_heading": {"type": ["string", "null"]}, "after": {"type": ["string", "null"]},
                       "rationale": {"type": "string"}},
        "required": ["type", "block", "rationale"]}}},
    "required": ["edits"],
}


def mechanical_heading_edits(blocks: list[Block], start: int = 1) -> list[Edit]:
    edits, n, seen_h1 = [], start, False
    for b in blocks:
        if b.level == 1:
            if seen_h1:
                edits.append(Edit(id=f"org-{n:03d}", type="retitle", stage="organization", targets=[b.id],
                                  rationale="a second H1 swallows the sections after it; demote it to H2",
                                  severity="medium", confidence=0.9, replacement="## " + b.heading_path[-1]))
                n += 1
            seen_h1 = True
    return edits


def build_outline(blocks: list[Block], flags: dict[str, list[str]]) -> str:
    rows = []
    for b in blocks:
        if not b.level:
            continue
        tags = f"  [{', '.join(flags[b.id])}]" if flags.get(b.id) else ""
        rows.append(f"{b.id} | H{b.level} | {'  ' * (b.level - 1)}{b.heading_path[-1]} | {b.words} words{tags}")
    return (
        "Below is the heading outline of a study guide (no body text). Propose only changes that improve the "
        "hierarchy and order: 'retitle' (consistent, specific titles; give 'new_heading' text without #) or "
        "'move' (place a block after another block with 'after'). Do not propose deletions or content changes. "
        "Return JSON {\"edits\": [{\"type\", \"block\", \"new_heading\", \"after\", \"rationale\"}]}; an empty "
        "list is fine.\n\n" + "\n".join(rows) + "\n")


def parse_organize(data: dict, blocks_by_id: dict[str, Block], start: int) -> list[Edit]:
    edits, n = [], start
    for e in data.get("edits", []):
        kind, block = e.get("type"), blocks_by_id.get(e.get("block"))
        if block is None:
            raise ReviseError(f"organize: unknown block {e.get('block')!r}")
        if kind == "retitle":
            if not e.get("new_heading"):
                raise ReviseError(f"organize: retitle of {block.id} needs new_heading")
            edit = Edit(id=f"org-{n:03d}", type="retitle", stage="organization", targets=[block.id],
                        rationale=e.get("rationale", ""), severity="low", confidence=0.5,
                        replacement="#" * block.level + " " + e["new_heading"].lstrip("# ").strip())
        elif kind == "move":
            if e.get("after") not in blocks_by_id:
                raise ReviseError(f"organize: move of {block.id} names an unknown anchor {e.get('after')!r}")
            edit = Edit(id=f"org-{n:03d}", type="move", stage="organization", targets=[block.id],
                        rationale=e.get("rationale", ""), severity="low", confidence=0.5, anchor=e["after"])
        else:
            raise ReviseError(f"organize: unknown edit type {kind!r}")
        edits.append(edit)
        n += 1
    return edits


def organize_edits(llm, blocks: list[Block], flags: dict[str, list[str]], start: int = 1) -> list[Edit]:
    edits = mechanical_heading_edits(blocks, start)
    data = llm.generate_structured(build_outline(blocks, flags), ORGANIZE_SCHEMA)
    return edits + parse_organize(data, {b.id: b for b in blocks}, start + len(edits))
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_organize.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add agent/study_guide/revise/organize.py tests/agent/study_guide/test_study_guide_revise_organize.py
git commit -m "revise: organization stage (mechanical heading fixes and outline proposals)"
```

---

### Task 9: Orchestration and the CLI

**Files:**
- Create: `agent/study_guide/revise/run.py`
- Modify: `agent/study_guide/cli.py` (subcommands `revise` and `apply-revise`; imports)
- Modify: `agent/study_guide/README.md` (usage section)
- Test: `tests/agent/study_guide/test_study_guide_revise_run.py`

**Interfaces:**
- Consumes: everything above; `load_plan`, `accepted`, `plan_path_for`, `_load_plan_for` (cli.py); `GeminiClient`.
- Produces:
  - `build_report(spec, guide_path, plan, *, stages, llm, embed, evidence, chunks, now=None) -> EditReport` (raises `ReviseError`)
  - `section_passages(plan, spec, chunks, section_title) -> list[tuple[str, str, str]]`
  - `report_path(root, spec, guide_path, tag)`, `revised_path(guide_path, tag)`
  - `cmd_revise(spec_path, root, *, guide_path, plan_path=None, stages=None, tag="", dry_run=False, force=False, env_file=None, llm=None, embed=None, client=None, chunks=None, cards=None, search=None) -> int`
  - `cmd_apply_revise(spec_path, root, *, guide_path, decisions_path, tag="", force=False) -> int`
  - CLI: `revise <spec> --guide G [--plan P] [--stages a,b] [--tag T] [--dry-run] [--force] [--env-file F]` and `apply-revise <spec> --guide G --decisions D [--tag T] [--force]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/study_guide/test_study_guide_revise_run.py
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import cmd_plan, plan_path_for
from agent.study_guide.revise.edits import ReviseError, load_report
from agent.study_guide.revise.evidence import EvidenceChunk
from agent.study_guide.revise.run import build_report, cmd_apply_revise, cmd_revise, report_path, revised_path
from agent.study_guide.spec import EvidenceRule, ReviseSpec, SourceRule, load_spec
from rv_helpers import ScriptedLLM, bag_embed
from sg_helpers import CARDS, CHUNKS, StubSearch, hit, make_spec, root  # noqa: F401 (fixtures)

SPEC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "file"
  file = "sl"

[revise]
criteria = ["relevance", "organization"]
relevance_low = 0.3
relevance_high = 0.9
min_block_words = 20

  [[revise.evidence]]
  kind = "file"
  file = "sl"
"""
HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'
GUIDE = ("---\ntitle: \"Demo\"\n---\n\n# Demo\n\n## Wald\n\n" + "wald statistic words " * 12 +
         "\n\n## Software packages\n\n" + "package install words " * 12 + "\n")
VOCAB = ["wald", "package"]
EVIDENCE = [EvidenceChunk("e1", "Exam, p. 1", 1.0, (1.0, 0.0))]


@pytest.fixture
def env(make_spec, root, tmp_path):
    make_spec(SPEC, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    search = StubSearch({"textbook": [hit("cam-1", .9)]})
    assert cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS) == 0
    guide = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    guide.write_text(GUIDE, encoding="utf-8")
    return spec_file, load_spec(spec_file), guide


def _build(spec, guide, llm=None, stages=("relevance", "organization")):
    plan = cli.load_plan(plan_path_for(str(guide.parents[3]), spec))
    return build_report(spec, str(guide), plan, stages=stages, llm=llm or ScriptedLLM([{"edits": []}]),
                        embed=bag_embed(VOCAB), evidence=EVIDENCE, chunks=CHUNKS, now="2026-10-08T00:00:00+00:00")


def test_report_has_hash_blocks_and_stage_edits(env):
    _, spec, guide = env
    report = _build(spec, guide)
    assert report.guide_sha256 == hashlib.sha256(guide.read_bytes()).hexdigest()
    assert [(e.stage, e.type) for e in report.edits] == [("relevance", "delete")]
    assert report.edits[0].targets and len(report.blocks) >= 3 and report.protected_blocks


def test_stage_selection_limits_what_runs(env):
    _, spec, guide = env
    llm = ScriptedLLM([])
    report = _build(spec, guide, llm=llm, stages=("relevance",))
    assert llm.calls == [] and {e.stage for e in report.edits} == {"relevance"}


def test_stages_outside_the_spec_criteria_are_refused(env):
    _, spec, guide = env
    with pytest.raises(ReviseError, match="criteria"):
        _build(spec, guide, stages=("dedup",))


def test_cmd_revise_writes_the_report_and_review_items(env, root):
    spec_file, spec, guide = env
    llm = ScriptedLLM([{"edits": []}])
    code = cmd_revise(str(spec_file), root, guide_path=str(guide), llm=llm, embed=bag_embed(VOCAB), chunks=CHUNKS, cards=CARDS,
                      search=lambda *a, **k: [], evidence=EVIDENCE)
    assert code == 0
    rp = report_path(root, spec, str(guide), "")
    assert rp.is_file() and rp.with_name(rp.name.replace(".revise.json", ".revise.review.json")).is_file()


def test_dry_run_makes_no_calls_and_writes_nothing(env, root, capsys):
    spec_file, spec, guide = env
    code = cmd_revise(str(spec_file), root, guide_path=str(guide), dry_run=True, chunks=CHUNKS, cards=CARDS)
    out = capsys.readouterr().out
    assert code == 0 and "DRY RUN" in out and "blocks" in out and not report_path(root, spec, str(guide), "").exists()


def test_apply_revise_applies_accepted_edits_and_records_provenance(env, root, tmp_path):
    spec_file, spec, guide = env
    cmd_revise(str(spec_file), root, guide_path=str(guide), llm=ScriptedLLM([{"edits": []}]), embed=bag_embed(VOCAB),
               chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    edit_id = load_report(report_path(root, spec, str(guide), "")).edits[0].id
    decisions = tmp_path / "d.json"
    decisions.write_text(json.dumps({edit_id: "accept"}), encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 0
    revised = revised_path(str(guide), "").read_text(encoding="utf-8")
    assert "package install" not in revised and "wald statistic" in revised
    assert "revised_from:" in revised and "revise_edits_applied: 1" in revised
    assert "package install" in guide.read_text(encoding="utf-8")
    assert revised_path(str(guide), "").with_name("demo.revised.changelog.md").is_file()


def test_apply_revise_refuses_a_guide_that_changed_and_never_overwrites(env, root, tmp_path, capsys):
    spec_file, spec, guide = env
    cmd_revise(str(spec_file), root, guide_path=str(guide), llm=ScriptedLLM([{"edits": []}]), embed=bag_embed(VOCAB),
               chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    decisions = tmp_path / "d.json"
    decisions.write_text("{}", encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 0
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 2
    assert "already exists" in capsys.readouterr().out
    guide.write_text(GUIDE + "\nextra\n", encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions), force=True) == 2
    assert "changed since" in capsys.readouterr().out


def test_a_spec_without_a_revise_table_is_an_error(make_spec, root, tmp_path, capsys):
    make_spec(SPEC.split("[revise]")[0], header=HEADER)
    assert cmd_revise(str(tmp_path / "spec.toml"), root, guide_path="g.md", dry_run=True) == 2
    assert "[revise]" in capsys.readouterr().out


def test_main_dispatches_revise_commands(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(cli, "cmd_revise", lambda spec, root, **kw: seen.setdefault("revise", kw) and 0)
    monkeypatch.setattr(cli, "cmd_apply_revise", lambda spec, root, **kw: seen.setdefault("apply", kw) and 0)
    assert cli.main(["revise", "s.toml", "--root", str(tmp_path), "--guide", "g.md", "--stages", "relevance,dedup",
                     "--tag", "t", "--dry-run"]) == 0
    assert seen["revise"]["stages"] == ["relevance", "dedup"] and seen["revise"]["dry_run"] is True
    assert cli.main(["apply-revise", "s.toml", "--root", str(tmp_path), "--guide", "g.md", "--decisions", "d.json"]) == 0
    assert seen["apply"]["decisions_path"] == "d.json"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/study_guide/test_study_guide_revise_run.py -q`
Expected: FAIL (`ModuleNotFoundError: ...revise.run`)

- [ ] **Step 3: Implement**

```python
# agent/study_guide/revise/run.py
"""Orchestrate the revise stages into an edit report; apply accepted edits to produce the revised guide."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.study_guide.revise.apply import apply_edits, changelog
from agent.study_guide.revise.audit import audit_section
from agent.study_guide.revise.dedup import dedup_edits, find_duplicate_clusters
from agent.study_guide.revise.edits import (
    EditReport, ReviseError, load_report, mark_conflicts, save_report, validate_report,
)
from agent.study_guide.revise.organize import organize_edits
from agent.study_guide.revise.relevance import relevance_edits, score_blocks
from agent.study_guide.revise.review import accepted_ids, write_review_items
from agent.study_guide.revise.segment import Block, segment, split_frontmatter
from agent.study_guide.plan import PlanError
from agent.study_guide.spec import GuideSpec, SpecError, load_spec

STAGES = ("relevance", "dedup", "correctness", "organization")
EXIT_OK, EXIT_INPUT, EXIT_LLM = 0, 2, 4


def report_path(root: str, spec: GuideSpec, guide_path: str, tag: str) -> Path:
    name = Path(guide_path).stem + (f".{tag}" if tag else "") + ".revise.json"
    return Path(root) / "academic_notes" / spec.course / "guide_plans" / name


def revised_path(guide_path: str, tag: str) -> Path:
    p = Path(guide_path)
    return p.with_name(f"{p.stem}.revised{'.' + tag if tag else ''}.md")


def section_passages(plan, spec: GuideSpec, chunks: list[dict], section_title: str) -> list[tuple[str, str, str]]:
    """The plan passages that back one guide section (a topic, or a comparison's source topics)."""
    from agent.study_guide.plan import accepted
    norm = " ".join(section_title.split()).casefold()
    titles = [t.title for t in spec.topics if " ".join(t.title.split()).casefold() == norm]
    titles = titles or [x for c in spec.comparisons if " ".join(c.title.split()).casefold() == norm for x in c.from_topics]
    text_by_id = {c["chunk_id"]: c["text"] for c in chunks}
    seen, out = set(), []
    for title in titles:
        for e in accepted(plan, title):
            if e.chunk_id not in seen and e.chunk_id in text_by_id:
                seen.add(e.chunk_id)
                out.append((f"S{len(out) + 1}", e.citation, text_by_id[e.chunk_id]))
    return out


def _memoized(embed):
    cache: dict[str, list[float]] = {}

    def cached(text: str) -> list[float]:
        if text not in cache:
            cache[text] = embed(text)
        return cache[text]
    return cached


def build_report(spec: GuideSpec, guide_path: str, plan, *, stages, llm, embed, evidence, chunks, now: str | None = None) -> EditReport:
    if spec.revise is None:
        raise ReviseError("the spec has no [revise] table")
    bad = [s for s in stages if s not in STAGES or s not in spec.revise.criteria]
    if bad:
        raise ReviseError(f"stage(s) {bad} are not enabled by the spec's [revise] criteria {list(spec.revise.criteria)}")
    raw = Path(guide_path).read_bytes()
    _, body = split_frontmatter(raw.decode("utf-8").replace("\r\n", "\n"))
    blocks = segment(body)
    embed = _memoized(embed)
    r, edits, protected, scores = spec.revise, [], [], {}
    if "relevance" in stages:
        scores = score_blocks(blocks, evidence, embed, min_words=r.min_block_words)
        found, protected = relevance_edits(blocks, scores, low=r.relevance_low, high=r.relevance_high)
        edits += found
    flags: dict[str, list[str]] = {}
    if "dedup" in stages:
        for cluster in find_duplicate_clusters(blocks, embed, similarity=r.dedup_similarity, min_words=r.min_block_words):
            for bid in cluster:
                flags.setdefault(bid, []).append("duplicate")
        edits += dedup_edits(llm, blocks, embed, similarity=r.dedup_similarity, min_words=r.min_block_words, start=1)
    if "correctness" in stages:
        for title in dict.fromkeys(b.heading_path[1] for b in blocks if len(b.heading_path) > 1):
            passages = section_passages(plan, spec, chunks, title)
            section = [b for b in blocks if len(b.heading_path) > 1 and b.heading_path[1] == title]
            if passages and section:
                found, problems = audit_section(llm, title, section, passages, start=len([e for e in edits if e.stage == "correctness"]) + 1)
                edits += found
                for p in problems:
                    print(f"WARNING: audit of {title!r}: {p}")
    if "organization" in stages:
        edits += organize_edits(llm, blocks, flags)
    for e in edits:
        e.protected = bool(set(e.targets) & set(protected)) and e.type in ("delete", "shrink", "merge")
    report = EditReport(
        guide_path=Path(guide_path).name, guide_sha256=hashlib.sha256(raw).hexdigest(),
        created_at=now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        blocks=[{"id": b.id, "heading_path": list(b.heading_path), "words": b.words,
                 "relevance": round(scores[b.id].score, 3) if b.id in scores else None} for b in blocks],
        edits=edits, protected_blocks=protected)
    mark_conflicts(report)
    problems = validate_report(report, blocks)
    if problems:
        raise ReviseError("the edit report is invalid: " + "; ".join(problems))
    return report


def _paid_llm(env_file, model):
    from agent.study_guide.cli import _paid_client
    from agent.summary_enhance.llm import GeminiClient
    client = _paid_client(env_file)
    return None if client is None else (GeminiClient(client, model), client)


def cmd_revise(spec_path: str, root: str, *, guide_path: str, plan_path: str | None = None, stages=None, tag: str = "",
               dry_run: bool = False, force: bool = False, env_file: str | None = None, llm=None, embed=None,
               client=None, chunks=None, cards=None, search=None, evidence=None) -> int:
    from agent.study_guide.cli import _load_plan_for
    try:
        spec = load_spec(spec_path)
        if spec.revise is None:
            raise ReviseError("the spec has no [revise] table")
        if not Path(guide_path).is_file():
            raise ReviseError(f"guide not found: {guide_path}")
        stages = list(stages or spec.revise.criteria)
        out = report_path(root, spec, guide_path, tag)
        if out.exists() and not force:
            raise ReviseError(f"{out} already exists; pass --force to replace it")
        plan, _, chunks = _load_plan_for(spec, root, plan_path, chunks, cards)
        _, body = split_frontmatter(Path(guide_path).read_text(encoding="utf-8"))
        blocks = segment(body)
        if dry_run:
            sections = len({b.heading_path[1] for b in blocks if len(b.heading_path) > 1})
            calls = {"relevance": 0, "dedup": "1 per duplicate cluster", "correctness": f"{sections} audit calls + 1 per worked block",
                     "organization": 1}
            print(f"DRY RUN: {len(blocks)} blocks, {sum(b.words for b in blocks)} words, stages {stages}, "
                  f"{len(spec.revise.evidence)} evidence rule(s) (resolved at run time)")
            print("DRY RUN: model calls: " + ", ".join(f"{s}: {calls[s]}" for s in stages))
            print(f"DRY RUN: would write {out}")
            return EXIT_OK
        if llm is None or embed is None or evidence is None:
            paid = _paid_llm(env_file, spec.revise.model)
            if paid is None:
                from agent.study_guide.cli import EXIT_NO_CLIENT
                return EXIT_NO_CLIENT
            llm, client = llm or paid[0], client or paid[1]
            if embed is None:
                from core.indexer.index_search import _embed_query
                embed = lambda text: _embed_query(text[:8000], client)
            if evidence is None:
                from agent.study_guide.revise.evidence import load_evidence
                evidence = load_evidence(spec, root, client=client, search=search, chunks=chunks, cards=cards) if "relevance" in stages else []
        report = build_report(spec, guide_path, plan, stages=stages, llm=llm, embed=embed, evidence=evidence, chunks=chunks)
        save_report(report, out)
        write_review_items(report, body, out.with_name(out.name.replace(".revise.json", ".revise.review.json")))
    except (SpecError, ReviseError, PlanError, OSError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    except Exception as err:  # API failure after the client's own retries
        print(f"ERROR: model or embedding call failed: {err}")
        return EXIT_LLM
    by_stage: dict[str, int] = {}
    for e in report.edits:
        by_stage[e.stage] = by_stage.get(e.stage, 0) + 1
    print(f"Wrote {out}: {len(report.edits)} proposed edits {by_stage}; review them in the Artifact, then apply-revise.")
    usage = getattr(llm, "usage", None)
    if usage:
        print(f"Token usage: {usage['calls']} calls, {usage['prompt_tokens']} prompt tokens, "
              f"{usage['output_tokens']} output tokens, {usage['thinking_tokens']} thinking tokens")
    return EXIT_OK


def cmd_apply_revise(spec_path: str, root: str, *, guide_path: str, decisions_path: str, tag: str = "", force: bool = False) -> int:
    try:
        spec = load_spec(spec_path)
        report = load_report(report_path(root, spec, guide_path, tag))
        raw = Path(guide_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != report.guide_sha256:
            raise ReviseError("the guide changed since the report was made; run revise again")
        out = revised_path(guide_path, tag)
        if out.exists() and not force:
            raise ReviseError(f"{out} already exists; pass --force to replace it")
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
        if not isinstance(decisions, dict):
            raise ReviseError("the decisions file must be a JSON object of edit id -> accept|reject")
        accepted = accepted_ids(report, decisions)
        front, body = split_frontmatter(raw.decode("utf-8").replace("\r\n", "\n"))
        revised = apply_edits(body, report, accepted)
        count = len([e for e in report.edits if e.id in accepted and e.type != "note"])
        if front:
            extra = (f"revised_from: {json.dumps({'path': report.guide_path, 'sha256': report.guide_sha256})}\n"
                     f"revise_edits_applied: {count}\n")
            front = front.replace("\n---\n", "\n" + extra + "---\n", 1)
        out.write_text(front + revised, encoding="utf-8", newline="\n")
        out.with_name(out.stem + ".changelog.md").write_text(changelog(report, accepted), encoding="utf-8", newline="\n")
    except (SpecError, ReviseError, OSError, json.JSONDecodeError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT
    print(f"Wrote {out} ({count} edits applied)")
    return EXIT_OK
```

In `agent/study_guide/cli.py`: import `from agent.study_guide.revise.run import cmd_apply_revise, cmd_revise` (module level, so tests can monkeypatch `cli.cmd_revise`), add the two subparsers and dispatch:

```python
    sp = sub.add_parser("revise")
    common(sp)
    sp.add_argument("--guide", required=True, help="the guide to revise (a draft or enhanced .md)")
    sp.add_argument("--plan", help="plan file (default: the spec's plan in the vault)")
    sp.add_argument("--stages", help="comma-separated subset of relevance,dedup,correctness,organization")
    sp.add_argument("--tag", default="")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("apply-revise")
    common(sp)
    sp.add_argument("--guide", required=True)
    sp.add_argument("--decisions", required=True, help="JSON file of edit id -> accept|reject")
    sp.add_argument("--tag", default="")
    sp.add_argument("--force", action="store_true")
```

and in `main` before the final `return cmd_draft(...)`:

```python
    if args.command == "revise":
        return cmd_revise(args.spec, args.root, guide_path=args.guide, plan_path=args.plan,
                          stages=args.stages.split(",") if args.stages else None, tag=args.tag, force=args.force,
                          dry_run=args.dry_run, env_file=args.env_file)
    if args.command == "apply-revise":
        return cmd_apply_revise(args.spec, args.root, guide_path=args.guide, decisions_path=args.decisions,
                                tag=args.tag, force=args.force)
```

(`common(sp)` already adds `spec`, `--root` and `--env-file`; check its definition and adapt if `apply-revise` should not take `--env-file`.) Add a short `revise` section to `agent/study_guide/README.md` listing the two commands, the `[revise]` table keys and the output files.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/study_guide -q`
Expected: PASS (all study_guide tests). If a circular import appears (`cli` <-> `revise.run`), import `_load_plan_for`/`_paid_client` lazily inside the functions as written.

- [ ] **Step 5: Run the wider suite and commit**

Run: `python -m pytest tests/agent -q`
Expected: PASS

```bash
git add agent/study_guide/revise/run.py agent/study_guide/cli.py agent/study_guide/README.md tests/agent/study_guide/test_study_guide_revise_run.py
git commit -m "revise: orchestration, revise and apply-revise commands"
```

---

### Task 10: First real run on the topic-first guide (manual, paid; needs the owner's go-ahead at each paid step)

**Files:**
- Modify: `guide_specs/econometrics/wald_lm_lr_topic_first.toml` (add the `[revise]` table with evidence rules: the 2024 midterm key, the lecture question sidecars, the problem sets, the syllabus; weights 3 / 2 / 2 / 1.5)
- Modify: `docs/status/agent/2026-10-07-study-guide-comparison-status.md` (results)

- [ ] **Step 1: Add the `[revise]` table and re-plan.** The spec hash changes, so the plan must be rebuilt and the earlier review decisions re-applied (carry them over with the saved decisions file, as for runs a1 to a3). Expected: the plan reports the same accepted counts.
- [ ] **Step 2: Dry-run.** `python -m agent.study_guide revise <spec> --root <hub> --env-file <env> --guide <a3 draft> --dry-run`. Expected: block count, stage list and call counts; no network.
- [ ] **Step 3: Relevance only (embeddings, no generation).** `--stages relevance`. Print the distribution of relevance scores per section and the delete proposals; calibrate `relevance_low`/`relevance_high` with the owner before any model stage runs. Stop here for the owner's go-ahead.
- [ ] **Step 4: Full run.** All stages, after approval. Record token usage in the status doc.
- [ ] **Step 5: Review in the Artifact**, read the decisions, run `apply-revise`, and compare the revised guide with the draft and with the owner's v4 guide.
- [ ] **Step 6: Commit** the spec and the status-doc results.
