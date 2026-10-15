# Concept graph viewer: sections, multi-select, summaries, connection form, layouts - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the section the single grouping of concepts, fix and extend multi-selection (canvas, concept list, section
buttons), show grouped selections with agent-drafted section summaries, improve the connection form, add layout presets.

**Architecture:** Python gains section `topic`/`short`/`summary` fields, a `topic == section topic` validation rule, a
`summary` drafting stage and layout embedding in `build`. The viewer gets pure selection/layout logic in `logic.js`
(Node-tested) and UI wiring in `app.js`, verified with a debug-only hook in headless Edge.

**Tech Stack:** Python 3.13, pydantic v2, ruamel.yaml (via `GraphStore`), pytest; vanilla JS, Cytoscape, Node's built-in
test runner.

**Spec:** `docs/superpowers/specs/agent/2026-10-14-concept-graph-viewer-selection-and-layouts-design.md`

## Global Constraints

- The section is the only grouping. A concept's `topic` must equal its section's `topic` when the section declares one.
- Short labels: Order theory, Preferences and utility, Revealed preference, Stochastic choice, Consumer demand,
  Duality and Slutsky, Producer theory, Risk and uncertainty.
- Summaries are agent-drafted only: at most 110 words and 700 characters, one paragraph, own words, no meta
  commentary. The page never shows composed or concatenated summaries (a composed text exists only behind `?debug`).
- Selection cap for Add connection: 12 concepts. All-pairs mode: at most 4 concepts (6 rows).
- Shift-click ranges are over the full list order and include concepts in collapsed sections; hidden (filtered)
  concepts are never selected.
- Ctrl, Cmd or Shift on a tap or list click toggles; plain click replaces. Section buttons take plain clicks only.
- Layout files: `config/layouts/<name>.json` = `{"name": str, "positions": {id: {"x": n, "y": n}}}`.
- Stage explicit paths only; commit messages end with the repo's attribution line.
- Python tests: `python -m pytest tests/agent/concept_graph -q`; viewer tests: `node --test agent/concept_graph/viewer/tests/*.test.js`.

## Review Focus

1. A graph repo whose sections have no `topic` yet must still validate and build (the sample graph and old repos).
2. Shift-click across a collapsed section must include its concepts; a concept hidden by a filter must not be selected.
3. A section that is only partly visible (filtered) must still reach its summary, labelled "(filtered)".
4. Ctrl-click on an already selected concept removes only that concept, on the canvas, in the list and in the panel.
5. Reversing one connection row must not change the other rows; many-to-one must produce edges from every other
   selected concept to the chosen one.
6. A layout file naming an unknown concept id must fail `build` with a clear message; a missing id falls back.

## File Structure

| File | Responsibility |
|---|---|
| `agent/concept_graph/schema.py` | `Section.topic/short/summary/summary_hash`; `member_hash` helper |
| `agent/concept_graph/validate.py` | topic-mismatch error; missing and stale summary warnings |
| `agent/concept_graph/store.py` | `update_section` |
| `agent/concept_graph/proposals.py`, `reviews.py` | derive topic from the section |
| `agent/concept_graph/stages/summary.py` (new), `stages/__init__.py`, `prompts.py` | the summary stage |
| `agent/concept_graph/build.py` | embed `layouts`; validate layout files |
| `agent/concept_graph/viewer/logic.js` | pure selection, grouping, form-row and layout functions |
| `agent/concept_graph/viewer/app.js`, `template.html`, `style.css` | UI wiring |
| `tests/agent/concept_graph/test_cg_sections.py`, `test_cg_stage_summary.py`, `test_cg_layouts.py` (new) | Python tests |
| `agent/concept_graph/viewer/tests/selection.test.js`, `layouts.test.js` (new) | JS tests |

---

### Task 1: Section fields, topic rule and `update_section`

**Files:**
- Modify: `agent/concept_graph/schema.py` (`Section`; add `member_hash`)
- Modify: `agent/concept_graph/validate.py`
- Modify: `agent/concept_graph/store.py`
- Modify: `agent/concept_graph/proposals.py` (`check_node`), `agent/concept_graph/reviews.py` (node write)
- Test: `tests/agent/concept_graph/test_cg_sections.py`

**Interfaces:**
- Produces: `Section.topic: str | None`, `Section.short: str | None`, `Section.summary: str | None`,
  `Section.summary_hash: str | None`; `member_hash(ids: list[str]) -> str` (16 hex chars of sha256 of sorted ids joined
  by `\n`); `GraphStore.update_section(section_id: str, changes: dict) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from agent.concept_graph.schema import Graph, Node, Section, Vocab, member_hash
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample


def graph(topic_of_section=None, node_topic="t1"):
    sec = Section(id="s1", title="One", order=1, state="taught", topic=topic_of_section, short="One")
    n = Node(id="a", name="A", kind="object", section="s1", topic=node_topic, explanation="x")
    return Graph(sections=[sec], nodes=[n], edges=[], rejected=[], vocab=Vocab(kinds=["object"], topics=["t1", "t2"]))


def test_member_hash_ignores_order_and_changes_with_membership():
    assert member_hash(["b", "a"]) == member_hash(["a", "b"])
    assert member_hash(["a"]) != member_hash(["a", "b"])
    assert len(member_hash(["a"])) == 16


def test_a_section_without_a_topic_does_not_constrain_its_concepts():
    assert not [i for i in validate(graph(None, "t2")) if i.code == "topic-mismatch"]


def test_a_concept_whose_topic_differs_from_its_section_is_an_error():
    found = [i for i in errors(validate(graph("t1", "t2"))) if i.code == "topic-mismatch"]
    assert len(found) == 1 and "a" in found[0].message


def test_missing_and_stale_summaries_are_warnings_not_errors():
    g = graph("t1", "t1")
    codes = {i.code for i in validate(g)}
    assert "missing-summary" in codes
    g.sections[0].summary = "A short summary."
    g.sections[0].summary_hash = "0" * 16
    assert "stale-summary" in {i.code for i in validate(g)}
    g.sections[0].summary_hash = member_hash(["a"])
    assert not {"missing-summary", "stale-summary"} & {i.code for i in validate(g)}
    assert errors(validate(g)) == []


def test_update_section_changes_only_that_section(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    first = store.read_all().sections[0].id
    store.update_section(first, {"summary": "Hello.", "summary_hash": "abc"})
    after = {s.id: s for s in store.read_all().sections}
    assert after[first].summary == "Hello." and after[first].summary_hash == "abc"
    assert all(s.summary is None for sid, s in after.items() if sid != first)
    with pytest.raises(KeyError):
        store.update_section("nope", {"summary": "x"})
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/concept_graph/test_cg_sections.py -q`
Expected: FAIL (`ImportError: cannot import name 'member_hash'`)

- [ ] **Step 3: Implement**

`schema.py`: add to `Section`:

```python
    topic: str | None = None
    short: str | None = None
    summary: str | None = None
    summary_hash: str | None = None
```

and below `field_hash`:

```python
def member_hash(ids: list[str]) -> str:
    """Stable hash of a section's membership; a summary drafted for other members is stale."""
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()[:16]
```

`validate.py`: import `member_hash`; inside `validate`, after the node loop that reports `unknown-topic`, add:

```python
    members = {}
    for n in graph.nodes:
        members.setdefault(n.section, []).append(n.id)
        sec = sections.get(n.section)
        if sec is not None and sec.topic and n.topic != sec.topic:
            err("topic-mismatch", f"node {n.id!r} has topic {n.topic!r} but its section {sec.id!r} has topic "
                                  f"{sec.topic!r}", n.id)
    for sec in graph.sections:
        if sec.state == "planned" or not members.get(sec.id):
            continue
        if not (sec.summary or "").strip():
            warn("missing-summary", f"section {sec.id!r} has no summary yet", sec.id)
        elif sec.summary_hash != member_hash(members[sec.id]):
            warn("stale-summary", f"section {sec.id!r} changed membership since its summary was drafted", sec.id)
```

`store.py`: add next to `update_item`:

```python
    def update_section(self, section_id: str, changes: dict) -> None:
        path = self.root / "data" / "sections.yaml"
        data = self._load(path) or []
        for item in data:
            if item.get("id") == section_id:
                for key, value in changes.items():
                    item[key] = value
                self._save(path, data)
                return
        raise KeyError(f"section {section_id!r} not found")
```

`proposals.py` `check_node`: replace the topic check with
`section = next((s for s in graph.sections if s.id == section), None)`-style lookup: when the section declares a
`topic`, the proposal's `topic` is ignored (and may be empty); otherwise it must be in the vocabulary as before.
`NodeProposal.topic` becomes `topic: str = ""`. In `reviews.apply_proposals` write the node with
`topic = section.topic or merged.topic`. In `merge_cluster`, skip the topic majority when all topics are empty.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/concept_graph -q`
Expected: PASS (existing proposal tests keep passing because a section without `topic` behaves as before; add one
case to `test_cg_apply_proposals.py` where the section has a topic and the proposal's topic is empty or different:
the written node carries the section's topic).

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/schema.py agent/concept_graph/validate.py agent/concept_graph/store.py agent/concept_graph/proposals.py agent/concept_graph/reviews.py tests/agent/concept_graph/test_cg_sections.py tests/agent/concept_graph/test_cg_apply_proposals.py
git commit -m "feat(concept_graph): section topic, short label and summary fields; topic must match the section"
```

---

### Task 2: The `summary` drafting stage

**Files:**
- Create: `agent/concept_graph/stages/summary.py`
- Modify: `agent/concept_graph/stages/__init__.py` (`STAGES = ("seed", "fill", "link", "critic", "summary")`)
- Modify: `agent/concept_graph/prompts.py` (`STEPS["summary"]`, `STAGE_NOUN["summary"]`)
- Test: `tests/agent/concept_graph/test_cg_stage_summary.py`

**Interfaces:**
- Consumes: `member_hash`, `GraphStore.update_section`, `check_meta`, `check_prose`, `passage_texts`, `with_ids`.
- Produces: `make_tasks(store, retriever, *, section=None, redo=False, top_k=6, **_)`, `validate_result(entry, result,
  store)`, `apply_result(store, entry, result, provenance)`; task id `summary-<section id>`; result key `summary`.

- [ ] **Step 1: Write the failing tests**

```python
from agent.concept_graph.schema import member_hash
from agent.concept_graph.stages import summary
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, copy_sample, entry_for

GOOD = "This group of ideas shows how a decision maker's ranking is built from simple properties and what each adds."


def make(tmp_path, **kw):
    store = GraphStore(copy_sample(tmp_path))
    return store, summary.make_tasks(store, FakeRetriever(), **kw)


def test_one_card_per_section_that_has_concepts_and_no_current_summary(tmp_path):
    store, tasks = make(tmp_path)
    g = store.read_all()
    with_nodes = {n.section for n in g.nodes}
    assert {t.subject["section"] for t in tasks} == {s.id for s in g.sections if s.id in with_nodes and s.state != "planned"}
    assert all(t.id == f"summary-{t.subject['section']}" for t in tasks)


def test_a_current_summary_is_skipped_unless_redo(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    g = store.read_all()
    sid = next(s.id for s in g.sections if any(n.section == s.id for n in g.nodes) and s.state != "planned")
    ids = [n.id for n in g.nodes if n.section == sid]
    store.update_section(sid, {"summary": GOOD, "summary_hash": member_hash(ids)})
    assert sid not in {t.subject["section"] for t in summary.make_tasks(store, FakeRetriever())}
    assert sid in {t.subject["section"] for t in summary.make_tasks(store, FakeRetriever(), redo=True)}


def test_validation_rules(tmp_path):
    store, tasks = make(tmp_path)
    entry = entry_for(tasks[0])
    assert summary.validate_result(entry, {"summary": GOOD}, store) == []
    assert any("required" in m for m in summary.validate_result(entry, {}, store))
    assert any("110" in m for m in summary.validate_result(entry, {"summary": "word " * 130}, store))
    assert any("paragraph" in m for m in summary.validate_result(entry, {"summary": GOOD + "\n\n" + GOOD}, store))
    assert any("sources" in m for m in summary.validate_result(
        entry, {"summary": "The offered passages do not cover this section."}, store))
    assert any("unknown key" in m for m in summary.validate_result(entry, {"summary": GOOD, "x": 1}, store))


def test_apply_stores_the_summary_and_the_membership_hash(tmp_path):
    store, tasks = make(tmp_path)
    entry = entry_for(tasks[0])
    assert summary.apply_result(store, entry, {"summary": GOOD}, {"driver": "agent"}) is None
    sid = entry["subject"]["section"]
    after = next(s for s in store.read_all().sections if s.id == sid)
    ids = [n.id for n in store.read_all().nodes if n.section == sid]
    assert after.summary == GOOD and after.summary_hash == member_hash(ids)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/agent/concept_graph/test_cg_stage_summary.py -q`
Expected: FAIL (`ImportError ... summary`)

- [ ] **Step 3: Implement**

`stages/summary.py`:

```python
"""Draft one cohesive summary per section: what the group of concepts is about and how they fit together."""
from __future__ import annotations

from ..ipguard import check_meta, check_prose
from ..schema import member_hash
from ..store import GraphStore
from ..tasks import Task
from .common import passage_texts, with_ids

STAGE = "summary"
ALLOWED = {"summary"}
MAX_WORDS = 110
MAX_CHARS = 700

INSTRUCTIONS = """\
Write one short, cohesive summary of this course section for a graduate student: what the group of concepts is about,
how the main ideas fit together, and why the section matters for what comes next. Put the YAML under `## Result`:

  summary: "..."

Rules:
- One paragraph of at most 110 words, in your OWN words. A run of 8 or more consecutive words shared with a passage is
  rejected.
- Describe the ideas themselves. Never mention the passages, the sources, the lectures, or what they do or do not cover.
- Do not list the concepts one by one; explain how they relate. Close every $ in LaTeX. Quote the value."""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, redo: bool = False, top_k: int = 6,
               **_ignored) -> list[Task]:
    graph = store.read_all()
    tasks = []
    for s in sorted(graph.sections, key=lambda s: s.order):
        if section and s.id != section:
            continue
        members = [n for n in graph.nodes if n.section == s.id]
        if not members or s.state == "planned":
            continue
        current = (s.summary or "").strip() and s.summary_hash == member_hash([n.id for n in members])
        if current and not redo:
            continue
        lines = [f"Section: {s.title}   (id: {s.id})", f"Short label: {s.short or s.title}", "", "Concepts in this section:"]
        for n in sorted(members, key=lambda n: n.name.lower()):
            lines.append(f"- {n.name} ({n.kind}): {n.gist or '(no one-line summary)'}")
        query = f"{s.title} " + " ".join(n.name for n in members[:12])
        passages = with_ids(retriever.retrieve(query, top_k))
        tasks.append(Task(id=f"summary-{s.id}", stage=STAGE, subject={"section": s.id}, instructions=INSTRUCTIONS,
                          context="\n".join(lines), passages=passages))
    return tasks


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - ALLOWED)
    if unknown:
        problems.append(f"unknown key(s) {unknown}; the result has only `summary`")
    text = result.get("summary")
    if not isinstance(text, str) or not text.strip():
        return problems + ["summary: required"]
    text = text.strip()
    if "\n\n" in text:
        problems.append("summary: must be a single paragraph")
    if len(text.split()) > MAX_WORDS or len(text) > MAX_CHARS:
        problems.append(f"summary: must be at most {MAX_WORDS} words and {MAX_CHARS} characters")
    if text.replace("\\$", "").replace("$$", "").count("$") % 2 == 1:
        problems.append("summary: the math delimiters do not balance (an odd number of $)")
    problems += check_meta({"summary": text})
    problems += check_prose({"summary": text}, passage_texts(entry))
    if not any(s.id == entry["subject"]["section"] for s in store.read_all().sections):
        problems.append("the section no longer exists")
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    sid = entry["subject"]["section"]
    graph = store.read_all()
    ids = [n.id for n in graph.nodes if n.section == sid]
    store.update_section(sid, {"summary": result["summary"].strip(), "summary_hash": member_hash(ids)})
    return None
```

`stages/__init__.py`: `STAGES = ("seed", "fill", "link", "critic", "summary")`.
`prompts.py`: add `"summary"` to `STAGE_NOUN` (`"SUMMARY"`) and `STEPS["summary"]`:
`"- One cohesive paragraph of at most 110 words about how the section's concepts fit together; do not list them."`.
(The existing test `test_every_stage_has_steps_and_a_name` will fail until this is added; it is the check.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/agent/concept_graph -q`
Expected: PASS. If `common.passage_texts`/`with_ids` have different names, match the imports used in
`stages/fill.py` (they are imported there from `.common`).

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/stages/summary.py agent/concept_graph/stages/__init__.py agent/concept_graph/prompts.py tests/agent/concept_graph/test_cg_stage_summary.py
git commit -m "feat(concept_graph): summary stage drafts one cohesive summary per section"
```

---

### Task 3: Layout files in `build`

**Files:**
- Modify: `agent/concept_graph/build.py`
- Test: `tests/agent/concept_graph/test_cg_layouts.py`

**Interfaces:**
- Consumes: `GraphStore` data dir layout, `BuildError`.
- Produces: `graph.json` key `layouts`: `[{"id": str, "name": str, "positions": {node_id: {"x": float, "y": float}}}]`
  sorted by id; section fields (`topic`, `short`, `summary`) already flow through `Section.model_dump` (verify in
  step 4).

- [ ] **Step 1: Write the failing tests**

```python
import json

import pytest

from agent.concept_graph.build import BuildError, build
from cg_helpers import copy_sample


def write_layout(root, name, body):
    d = root / "config" / "layouts"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def node_ids(root):
    g = json.loads((root / "build" / "graph.json").read_text(encoding="utf-8")) if (root / "build" / "graph.json").exists() else None
    return g


def test_layouts_are_embedded_sorted_by_id(tmp_path):
    root = copy_sample(tmp_path)
    result = build(root)
    first = json.loads(result.graph_json.read_text(encoding="utf-8"))["nodes"][0]["id"]
    write_layout(root, "b-second", {"name": "Second", "positions": {first: {"x": 1, "y": 2}}})
    write_layout(root, "a-first", {"name": "First", "positions": {first: {"x": 3, "y": 4}}})
    data = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    assert [l["id"] for l in data["layouts"]] == ["a-first", "b-second"]
    assert data["layouts"][0]["positions"][first] == {"x": 3, "y": 4}


def test_an_unknown_concept_id_fails_the_build_with_the_file_name(tmp_path):
    root = copy_sample(tmp_path)
    write_layout(root, "bad", {"name": "Bad", "positions": {"no-such-concept": {"x": 0, "y": 0}}})
    with pytest.raises(BuildError) as exc:
        build(root)
    assert "bad.json" in str(exc.value) and "no-such-concept" in str(exc.value)


def test_a_malformed_layout_fails_clearly(tmp_path):
    root = copy_sample(tmp_path)
    write_layout(root, "oops", {"name": "Oops", "positions": {"x": "not a point"}})
    with pytest.raises(BuildError):
        build(root)


def test_no_layouts_folder_means_an_empty_list(tmp_path):
    root = copy_sample(tmp_path)
    data = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    assert data["layouts"] == []
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/agent/concept_graph/test_cg_layouts.py -q`
  Expected: FAIL (`KeyError: 'layouts'`)

- [ ] **Step 3: Implement** in `build.py`:

```python
def _read_layouts(root: Path, node_ids: set[str]) -> list[dict]:
    folder = root / "config" / "layouts"
    out = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            name, positions = raw["name"], raw["positions"]
            clean = {}
            for node_id, point in positions.items():
                clean[node_id] = {"x": float(point["x"]), "y": float(point["y"])}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BuildError(f"{path.name}: not a valid layout file ({exc}); expected "
                             f'{{"name": ..., "positions": {{id: {{"x": n, "y": n}}}}}}') from exc
        unknown = sorted(set(clean) - node_ids)
        if unknown:
            raise BuildError(f"{path.name}: unknown concept id(s) {unknown[:5]}; rebuild the layout from the current graph")
        out.append({"id": path.stem, "name": str(name), "positions": clean})
    return out
```

and in the payload `body` add `"layouts": _read_layouts(Path(root), {n.id for n in graph.nodes})` (the function that
builds `body` must receive the graph root; thread `root` through as `build` already has it).

- [ ] **Step 4: Run to verify pass** — `python -m pytest tests/agent/concept_graph -q`. Also assert in a quick check that
  a section with `topic`, `short` and `summary` set in the sample data appears with those keys in `graph.json["sections"]`
  (add one assertion to `test_cg_layouts.py` using `GraphStore.update_section` on the sample and a rebuild).

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/build.py tests/agent/concept_graph/test_cg_layouts.py
git commit -m "feat(concept_graph): build embeds and validates layout presets"
```

---

### Task 4: Pure selection, grouping, form-row and layout logic (`logic.js`)

**Files:**
- Modify: `agent/concept_graph/viewer/logic.js`
- Test: `agent/concept_graph/viewer/tests/selection.test.js`, `agent/concept_graph/viewer/tests/layouts.test.js` (new)

**Interfaces (all on `CG`):**
- `listOrder(sections, nodes) -> string[]`: ids in the list's displayed order (sections by `order`, concepts by name).
- `rangeIds(order, a, b) -> string[]`: inclusive slice between two ids in either order; `[b]` if `a` is missing.
- `toggleId(ids, id) -> string[]`: adds or removes, keeping order.
- `groupBySection(sections, nodes, selectedIds, visibleIds) -> [{section, ids, total, full, filtered}]` in course order,
  only sections with at least one selected concept.
- `expandedSection(groups, newlyAddedIds, nodesById) -> sectionId`: the section with the most newly added concepts,
  ties by course order; falls back to the last group.
- `sectionButtonClick(active, sectionId) -> {active, select: sectionId | null}`: the table in the spec.
- `connectionRows(mode, chosen, ids, sectionOrder) -> [{source, target}]` with modes `one_to_many`, `many_to_one`,
  `chain`, `all_pairs`; `sectionOrder` maps node id to `[sectionOrder, name]`.
- `clusterLayout(nodes, sections) -> {id: {x, y}}`, `timelineLayout(nodes, sections) -> {id: {x, y}}`.

- [ ] **Step 1: Write the failing tests**

`selection.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const sections = [{ id: "s2", order: 2, short: "Two" }, { id: "s1", order: 1, short: "One" }];
const nodes = [
  { id: "b", name: "Beta", section: "s1" }, { id: "a", name: "Alpha", section: "s1" },
  { id: "d", name: "Delta", section: "s2" }, { id: "c", name: "Gamma", section: "s2" }
];
const byId = new Map(nodes.map((n) => [n.id, n]));

test("listOrder is sections by order then names", () => {
  assert.deepEqual(CG.listOrder(sections, nodes), ["a", "b", "d", "c"]);
});

test("rangeIds is inclusive, crosses sections and works in either direction", () => {
  const order = CG.listOrder(sections, nodes);
  assert.deepEqual(CG.rangeIds(order, "b", "c"), ["b", "d", "c"]);
  assert.deepEqual(CG.rangeIds(order, "c", "b"), ["b", "d", "c"]);
  assert.deepEqual(CG.rangeIds(order, "zzz", "d"), ["d"]);
});

test("toggleId adds then removes only that id", () => {
  assert.deepEqual(CG.toggleId(["a", "b"], "c"), ["a", "b", "c"]);
  assert.deepEqual(CG.toggleId(["a", "b", "c"], "b"), ["a", "c"]);
});

test("groupBySection marks full sections and reports filtered ones", () => {
  const all = new Set(["a", "b", "c", "d"]);
  let g = CG.groupBySection(sections, nodes, ["a", "b", "d"], all);
  assert.deepEqual(g.map((x) => [x.section.id, x.ids.length, x.total, x.full]), [["s1", 2, 2, true], ["s2", 1, 2, false]]);
  g = CG.groupBySection(sections, nodes, ["d"], new Set(["a", "b", "d"]));   // "c" is hidden by a filter
  assert.equal(g[0].full, true);
  assert.equal(g[0].filtered, true);
});

test("expandedSection picks the section with most newly added concepts, ties by course order", () => {
  const g = CG.groupBySection(sections, nodes, ["a", "b", "d"], new Set(["a", "b", "c", "d"]));
  assert.equal(CG.expandedSection(g, ["a", "b", "d"], byId), "s1");
  assert.equal(CG.expandedSection(g, ["d"], byId), "s2");
  assert.equal(CG.expandedSection(g, ["a", "d"], byId), "s1");   // tie: earlier in the course
});

test("sectionButtonClick follows the three table rows", () => {
  assert.deepEqual(CG.sectionButtonClick([], "s1"), { active: ["s1"], select: "s1" });
  assert.deepEqual(CG.sectionButtonClick(["s1"], "s2"), { active: ["s1", "s2"], select: "s2" });
  assert.deepEqual(CG.sectionButtonClick(["s1", "s2"], "s1"), { active: ["s2"], select: null });
  assert.deepEqual(CG.sectionButtonClick(["s1"], "s1"), { active: [], select: null });
});

test("connectionRows modes", () => {
  const ord = { a: [1, "Alpha"], b: [1, "Beta"], d: [2, "Delta"], c: [2, "Gamma"] };
  const ids = ["a", "b", "d"];
  assert.deepEqual(CG.connectionRows("one_to_many", "b", ids, ord), [{ source: "b", target: "a" }, { source: "b", target: "d" }]);
  assert.deepEqual(CG.connectionRows("many_to_one", "b", ids, ord), [{ source: "a", target: "b" }, { source: "d", target: "b" }]);
  assert.deepEqual(CG.connectionRows("chain", "a", ["d", "a", "b"], ord), [{ source: "a", target: "b" }, { source: "b", target: "d" }]);
  assert.equal(CG.connectionRows("all_pairs", "a", ids, ord).length, 3);
  assert.deepEqual(CG.connectionRows("all_pairs", "a", ["a", "b", "d"], ord)[0], { source: "a", target: "b" });
});

test("all_pairs refuses more than four concepts", () => {
  const ord = {}; ["a", "b", "c", "d", "e"].forEach((i, k) => { ord[i] = [1, i + k]; });
  assert.deepEqual(CG.connectionRows("all_pairs", "a", ["a", "b", "c", "d", "e"], ord), []);
});
```

`layouts.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const sections = [{ id: "s1", order: 1 }, { id: "s2", order: 2 }, { id: "s3", order: 3 }];
const nodes = [];
sections.forEach((s) => { for (let i = 0; i < 7; i++) nodes.push({ id: s.id + "n" + i, name: "N" + i, section: s.id }); });

function overlaps(pos) {
  const ids = Object.keys(pos);
  for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
    const dx = Math.abs(pos[ids[i]].x - pos[ids[j]].x), dy = Math.abs(pos[ids[i]].y - pos[ids[j]].y);
    if (dx < 170 && dy < 56) return true;
  }
  return false;
}

test("clusterLayout places every concept without overlap and keeps a section together", () => {
  const pos = CG.clusterLayout(nodes, sections);
  assert.equal(Object.keys(pos).length, nodes.length);
  assert.ok(!overlaps(pos));
  const xs = ["s1n0", "s1n6"].map((id) => pos[id].x);
  const farX = pos.s3n0.x;
  assert.ok(Math.abs(xs[0] - xs[1]) < Math.abs(xs[0] - farX) + 1);
});

test("timelineLayout orders sections left to right", () => {
  const pos = CG.timelineLayout(nodes, sections);
  assert.ok(!overlaps(pos));
  assert.ok(pos.s1n0.x < pos.s2n0.x && pos.s2n0.x < pos.s3n0.x);
});
```

- [ ] **Step 2: Run to verify failure** — `node --test agent/concept_graph/viewer/tests/selection.test.js agent/concept_graph/viewer/tests/layouts.test.js`
  Expected: FAIL (`CG.listOrder is not a function`)

- [ ] **Step 3: Implement** in `logic.js`, before the final `return {`:

```javascript
  function sortedSections(sections) { return sections.slice().sort(function (a, b) { return a.order - b.order; }); }
  function listOrder(sections, nodes) {
    var out = [];
    sortedSections(sections).forEach(function (s) {
      nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); })
        .forEach(function (n) { out.push(n.id); });
    });
    return out;
  }
  function rangeIds(order, a, b) {
    var i = order.indexOf(a), j = order.indexOf(b);
    if (j === -1) return [];
    if (i === -1) return [b];
    return order.slice(Math.min(i, j), Math.max(i, j) + 1);
  }
  function toggleId(ids, id) {
    return ids.indexOf(id) === -1 ? ids.concat([id]) : ids.filter(function (x) { return x !== id; });
  }
  function groupBySection(sections, nodes, selectedIds, visibleIds) {
    var chosen = new Set(selectedIds);
    var out = [];
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; });
      var shown = members.filter(function (n) { return visibleIds.has(n.id); });
      var ids = shown.filter(function (n) { return chosen.has(n.id); }).map(function (n) { return n.id; });
      if (!ids.length) return;
      out.push({ section: s, ids: ids, total: shown.length, full: ids.length === shown.length,
                 filtered: shown.length < members.length });
    });
    return out;
  }
  function expandedSection(groups, newIds, nodesById) {
    var fresh = new Set(newIds), best = null, bestCount = -1;
    groups.forEach(function (g) {
      var c = g.ids.filter(function (id) { return fresh.has(id); }).length;
      if (c > bestCount) { best = g.section.id; bestCount = c; }
    });
    return best || (groups.length ? groups[groups.length - 1].section.id : null);
  }
  function sectionButtonClick(active, sectionId) {
    var i = active.indexOf(sectionId);
    if (i === -1) return { active: active.concat([sectionId]), select: sectionId };
    var next = active.filter(function (x) { return x !== sectionId; });
    return { active: next, select: null };
  }
  function connectionRows(mode, chosen, ids, ord) {
    function key(id) { var o = ord[id] || [0, id]; return o; }
    function cmp(a, b) { var x = key(a), y = key(b); return x[0] - y[0] || String(x[1]).localeCompare(String(y[1])); }
    var others = ids.filter(function (id) { return id !== chosen; });
    if (mode === "one_to_many") return others.map(function (id) { return { source: chosen, target: id }; });
    if (mode === "many_to_one") return others.map(function (id) { return { source: id, target: chosen }; });
    var sorted = ids.slice().sort(cmp);
    if (mode === "chain") {
      return sorted.slice(1).map(function (id, i) { return { source: sorted[i], target: id }; });
    }
    if (mode === "all_pairs") {
      if (sorted.length > 4) return [];
      var rows = [];
      for (var i = 0; i < sorted.length; i++) for (var j = i + 1; j < sorted.length; j++) rows.push({ source: sorted[i], target: sorted[j] });
      return rows;
    }
    return [];
  }
  var CELL_W = 200, CELL_H = 74;
  function gridInside(members, cx, cy, out) {
    var cols = Math.max(1, Math.ceil(Math.sqrt(members.length)));
    members.forEach(function (n, k) {
      out[n.id] = { x: cx + (k % cols) * CELL_W, y: cy + Math.floor(k / cols) * CELL_H };
    });
    return { w: cols * CELL_W, h: Math.ceil(members.length / cols) * CELL_H };
  }
  function clusterLayout(nodes, sections) {
    var out = {}, perRow = 3, gapX = 260, gapY = 200;
    var rowH = 0, x = 0, y = 0, colIndex = 0;
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!members.length) return;
      var size = gridInside(members, x, y, out);
      rowH = Math.max(rowH, size.h);
      colIndex += 1;
      if (colIndex % perRow === 0) { x = 0; y += rowH + gapY; rowH = 0; } else { x += size.w + gapX; }
    });
    return out;
  }
  function timelineLayout(nodes, sections) {
    var out = {}, x = 0;
    sortedSections(sections).forEach(function (s) {
      var members = nodes.filter(function (n) { return n.section === s.id; })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      members.forEach(function (n, k) { out[n.id] = { x: x, y: k * CELL_H }; });
      x += CELL_W + 80;
    });
    return out;
  }
```

Export: `listOrder, rangeIds, toggleId, groupBySection, expandedSection, sectionButtonClick, connectionRows,
clusterLayout, timelineLayout`.

- [ ] **Step 4: Run to verify pass** — `node --test agent/concept_graph/viewer/tests/*.test.js`
  Expected: PASS (all existing tests plus the new ones). If `clusterLayout` overlaps are reported, increase `gapX`.

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/viewer/logic.js agent/concept_graph/viewer/tests/selection.test.js agent/concept_graph/viewer/tests/layouts.test.js
git commit -m "feat(concept_graph): viewer selection, grouping, connection-row and layout logic"
```

---

### Task 5: Viewer selection, concept list, section buttons and grouped panel

**Files:**
- Modify: `agent/concept_graph/viewer/app.js`, `viewer/template.html`, `viewer/style.css`

**Interfaces:**
- Consumes: `CG.listOrder`, `CG.rangeIds`, `CG.toggleId`, `CG.groupBySection`, `CG.expandedSection`,
  `CG.sectionButtonClick` (Task 4); section `short` and `summary` in `G.sections` (Tasks 1 to 3).
- Produces (inside the IIFE): `selectedIds() -> string[]`, `setSelection(ids)`, `visibleSet() -> Set`,
  `collapsed: Set`, `onSelectionChanged()`; `window.__cg = {cy, selectedIds, setSelection, groups}` only when the URL
  has `debug`.

- [ ] **Step 1: Template and style**

`template.html`: inside `#sidebar-top`, after the Fit button, add
`<div class="list-tools"><button id="btn-collapse-all" type="button">Collapse all</button><button id="btn-expand-all" type="button">Expand all</button></div>`.
Rename the topic filter label in the legend text from "coloured by topic" to "coloured by section".

`style.css` (append):

```css
.list-tools { display: flex; gap: 6px; margin-top: 8px; }
.list-tools button { flex: 1; font-size: 0.85em; }
#name-list h3 { display: flex; align-items: center; gap: 4px; cursor: default; }
#name-list h3 .chev { border: 0; background: none; color: inherit; cursor: pointer; padding: 0 4px; }
#name-list h3 .sec-title { flex: 1; text-align: left; border: 0; background: none; color: inherit; font: inherit; cursor: pointer; }
#name-list h3 .sec-count { font-size: 0.8em; opacity: 0.75; }
#name-list .collapsed-group { display: none; }
#name-list button.sel { outline: 2px solid #f59e0b; }
#panel details { border: 1px solid var(--line); border-radius: 8px; margin: 8px 0; padding: 4px 8px; }
#panel details > summary { cursor: pointer; font-weight: 600; }
#panel .sec-summary { margin: 8px 0; }
#panel .chosen li { display: flex; justify-content: space-between; gap: 6px; }
```

- [ ] **Step 2: Selection model.** In `app.js` add after the `pickOrder` declaration:

```javascript
  var collapsed = new Set();
  try { JSON.parse(storage.get("cg-collapsed-" + G.graph_version) || "[]").forEach(function (id) { collapsed.add(id); }); } catch (e) { /* none */ }
  var activeSections = [];          // section ids whose button is highlighted (the filter)
  var lastListId = null;            // anchor for Shift-click ranges in the concept list
  var lastAdded = [];               // concepts added by the latest selection gesture
  var orderedPick = true;           // true after clicks and Ctrl-clicks (first = source); false after box, range or section
  function selectedIds() {
    return cy.nodes(":selected").filter(function (n) { return !n.hasClass("ghost"); }).map(function (n) { return n.id(); });
  }
  function visibleSet() {
    return new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
  }
  function setSelection(ids) {
    var before = new Set(selectedIds());
    lastAdded = ids.filter(function (id) { return !before.has(id); });
    cy.batch(function () {
      cy.elements().unselect();
      ids.forEach(function (id) { var el = cy.getElementById(id); if (el.nonempty() && !el.hasClass("hidden")) el.select(); });
    });
  }
```

- [ ] **Step 3: Tap handler and selection change.** Replace the `cy.on("tap", "node", ...)` handler with:

```javascript
  cy.on("tap", "node", function (ev) {
    if (ev.target.hasClass("ghost")) return;
    var oe = ev.originalEvent || {};
    if (oe.ctrlKey || oe.metaKey || oe.shiftKey) { lastAdded = [ev.target.id()]; return; } // Cytoscape toggles it
    lastListId = ev.target.id();
    select("node", ev.target.id(), false);
  });
```

Replace the `cy.on("select unselect", "node", ...)` handler near the end with:

```javascript
  var changeQueued = false;
  function onSelectionChanged() {
    changeQueued = false;
    var ids = selectedIds();
    pickOrder = pickOrder.filter(function (id) { return ids.indexOf(id) !== -1; });
    ids.forEach(function (id) { if (pickOrder.indexOf(id) === -1) pickOrder.push(id); });
    if (ids.length === 1) selected = { kind: "node", id: ids[0] };
    else if (ids.length === 0 && selected && selected.kind === "node") selected = null;
    $("#btn-connect").hidden = ids.length < 2 || ids.length > 12;
    renderPanel(); renderNameList();
  }
  cy.on("select unselect", "node", function () {
    if (changeQueued) return;
    changeQueued = true;
    Promise.resolve().then(onSelectionChanged);
  });
```

`orderedPick` is declared in step 2. Set it to `true` in the tap handler above when a modifier key is held or when a plain tap selects one concept; set it to `false` in `setSelection` unless the caller sets it back, and on `cy.on("boxselect", function () { orderedPick = false; });`. The Add-connection button handler is replaced in Task 6.

- [ ] **Step 4: Concept list.** Replace `renderNameList` and its click handler with:

```javascript
  function renderNameList(visibleArg) {
    var visible = visibleArg || visibleSet();
    var sel = new Set(selectedIds());
    var html = "";
    G.sections.slice().sort(function (a, b) { return a.order - b.order; }).forEach(function (s) {
      var list = G.nodes.filter(function (n) { return n.section === s.id && visible.has(n.id); })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!list.length) return;
      var open = !collapsed.has(s.id) || (filters.q || "").trim() !== "";
      var count = list.filter(function (n) { return sel.has(n.id); }).length;
      html += '<h3><button type="button" class="chev" data-chev="' + esc(s.id) + '" aria-expanded="' + open + '">' + (open ? "\u25be" : "\u25b8") + "</button>" +
        '<button type="button" class="sec-title" data-section-head="' + esc(s.id) + '">' + esc(s.title) + (s.state === "planned" ? " (planned)" : "") + "</button>" +
        (count ? '<span class="sec-count">' + count + " of " + list.length + " selected</span>" : "") + "</h3>";
      html += '<div class="sec-group' + (open ? "" : " collapsed-group") + '">';
      list.forEach(function (n) {
        var cls = (s.state === "planned" ? "planned " : "") + (sel.has(n.id) ? "sel" : "");
        html += '<button type="button" class="' + cls + '" data-node="' + esc(n.id) + '">' + esc(n.name) + "</button>";
      });
      html += "</div>";
    });
    $("#name-list").innerHTML = html || '<p class="hint">No concepts match.</p>';
  }
  function saveCollapsed() { storage.set("cg-collapsed-" + G.graph_version, JSON.stringify(Array.from(collapsed))); }
  $("#name-list").addEventListener("click", function (ev) {
    var chev = ev.target.closest("button[data-chev]");
    if (chev) {
      var sid = chev.getAttribute("data-chev");
      if (collapsed.has(sid)) collapsed.delete(sid); else collapsed.add(sid);
      saveCollapsed(); renderNameList(); return;
    }
    var head = ev.target.closest("button[data-section-head]");
    if (head) { selectSection(head.getAttribute("data-section-head")); return; }
    var b = ev.target.closest("button[data-node]"); if (!b) return;
    var id = b.getAttribute("data-node");
    var mod = ev.ctrlKey || ev.metaKey, shift = ev.shiftKey;
    orderedPick = true;
    if (shift && lastListId) {
      var vis = visibleSet();
      setSelection(CG.rangeIds(CG.listOrder(G.sections, G.nodes), lastListId, id).filter(function (x) { return vis.has(x); }));
      orderedPick = false;
    } else if (mod) {
      setSelection(CG.toggleId(selectedIds(), id)); lastListId = id;
    } else {
      lastListId = id; select("node", id, true);
    }
  });
  $("#btn-collapse-all").addEventListener("click", function () {
    G.sections.forEach(function (s) { collapsed.add(s.id); }); saveCollapsed(); renderNameList();
  });
  $("#btn-expand-all").addEventListener("click", function () { collapsed.clear(); saveCollapsed(); renderNameList(); });
  function selectSection(sectionId) {
    var vis = visibleSet();
    setSelection(G.nodes.filter(function (n) { return n.section === sectionId && vis.has(n.id); }).map(function (n) { return n.id; }));
    orderedPick = false;
  }
```

- [ ] **Step 5: Section buttons.** In `buildFilters` replace the topic-button block with:

```javascript
    var topics = $("#f-topics");
    var ordered = G.sections.slice().sort(function (a, b) { return a.order - b.order; });
    topics.innerHTML = ordered.map(function (s) {
      return '<button type="button" data-section="' + esc(s.id) + '" title="' + esc(s.title) + '">' + esc(s.short || s.title) + "</button>";
    }).join("");
    topics.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-section]"); if (!b) return;
      var sid = b.getAttribute("data-section");
      var step = CG.sectionButtonClick(activeSections, sid);
      var removed = activeSections.filter(function (x) { return step.active.indexOf(x) === -1; });
      activeSections = step.active;
      filters.sections = activeSections.slice();
      Array.from(topics.querySelectorAll("button")).forEach(function (x) {
        x.classList.toggle("on", activeSections.indexOf(x.getAttribute("data-section")) !== -1);
      });
      applyFilters();
      if (step.select) selectSection(step.select);
      else if (removed.length) {
        var gone = new Set(G.nodes.filter(function (n) { return removed.indexOf(n.section) !== -1; }).map(function (n) { return n.id; }));
        setSelection(selectedIds().filter(function (id) { return !gone.has(id); }));
      }
    });
```

`applyFilters` already hides nodes through `CG.filterNodes` (`filters.sections`). After `applyFilters`, deselect any
now-hidden selected node by calling `setSelection(selectedIds().filter(function (id) { return !cy.getElementById(id).hasClass("hidden"); }))`
at the end of `applyFilters`.

- [ ] **Step 6: Grouped panel.** Replace `renderPanel` with:

```javascript
  function renderGroupPanel(p, ids) {
    var vis = visibleSet();
    var groups = CG.groupBySection(G.sections, G.nodes, ids, vis);
    var open = CG.expandedSection(groups, lastAdded.length ? lastAdded : ids, nodesById);
    p.innerHTML = "<h2>" + ids.length + " concepts selected</h2>" +
      '<div class="actions"><button type="button" data-act="clear-selection">Clear selection</button>' +
      '<button type="button" data-act="add-connection"' + (ids.length > 12 ? " disabled title=\"Select 12 or fewer concepts to propose connections\"" : "") + ">Add connection</button></div>" +
      groups.map(function (g) {
        var s = g.section;
        var head = esc(s.short || s.title) + ", " + g.ids.length + " of " + g.total + " selected" + (g.filtered ? " (filtered)" : "");
        var body = (g.full && s.summary ? '<p class="sec-summary">' + esc(s.summary) + "</p>" : "") +
          '<ul class="chosen">' + g.ids.map(function (id) {
            return '<li><button type="button" data-node="' + esc(id) + '">' + esc(nameOf(id)) + '</button>' +
              '<button type="button" data-remove="' + esc(id) + '" aria-label="Remove ' + esc(nameOf(id)) + ' from the selection">\u00d7</button></li>';
          }).join("") + "</ul>";
        return "<details" + (s.id === open ? " open" : "") + "><summary>" + head + "</summary>" + body + "</details>";
      }).join("");
  }
  function renderPanel() {
    var p = $("#panel");
    var ids = selectedIds();
    if (ids.length >= 2) return renderGroupPanel(p, ids);
    if (!selected) { p.innerHTML = '<p class="hint">Click a concept or a connection to read about it.</p>'; return; }
    if (selected.kind === "node") return renderNode(p);
    return renderEdge(p);
  }
```

and extend the `#panel` click handler, before the existing `data-node` line:

```javascript
    if (b.hasAttribute("data-remove")) { setSelection(CG.toggleId(selectedIds(), b.getAttribute("data-remove"))); return; }
    if (b.getAttribute("data-act") === "clear-selection") { setSelection([]); return; }
    if (b.getAttribute("data-act") === "add-connection") { $("#btn-connect").click(); return; }
    if (b.hasAttribute("data-node") && (ev.ctrlKey || ev.metaKey)) { setSelection(CG.toggleId(selectedIds(), b.getAttribute("data-node"))); return; }
```

Escape clears: `document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") setSelection([]); });`.

- [ ] **Step 7: Debug hook and verification.** At the end of the IIFE:

```javascript
  if (/[?&]debug\b/.test(location.search)) {
    window.__cg = { cy: cy, selectedIds: selectedIds, setSelection: setSelection,
                    groups: function () { return CG.groupBySection(G.sections, G.nodes, selectedIds(), visibleSet()); } };
  }
```

Verify with the headless method used before (build a copy of the sample graph, append a script before the last
`</body>`, use `--screenshot` with the result text drawn into a fixed `<pre>`; open with `?debug`). Scripted checks,
each pushed into the result text:

1. `__cg.setSelection([a, b]); __cg.selectedIds().length === 2`; `#btn-connect` not hidden; panel contains
   "2 concepts selected".
2. Simulate Ctrl-click: `cy.getElementById(c).emit(...)` is unreliable; instead dispatch on the list:
   `document.querySelector('[data-node="c"]').dispatchEvent(new MouseEvent("click", {bubbles: true, ctrlKey: true}))`
   then expect 3 selected; repeat on `c` and expect 2 (deselect keeps the others).
3. Shift-click in the list from the first to the last concept of the sample: selected count equals the list order
   slice, including a collapsed section (click its chevron first).
4. Click a section button: `activeSections` filter shows only that section, all its concepts selected, panel shows
   the section's `summary` text when the sample graph has one (set it with `GraphStore.update_section` before building).
5. Click the only highlighted button again: everything visible, selection empty.

Then run `python -m pytest tests/agent/concept_graph/test_cg_viewer_logic.py tests/agent/concept_graph/test_cg_build.py -q`.

- [ ] **Step 8: Commit**

```bash
git add agent/concept_graph/viewer/app.js agent/concept_graph/viewer/template.html agent/concept_graph/viewer/style.css
git commit -m "feat(concept_graph): multi-select, collapsible concept list, section buttons and grouped panel"
```

---

### Task 6: Connection form modes, row reverse and layout presets

**Files:**
- Modify: `agent/concept_graph/viewer/app.js`, `viewer/template.html`, `viewer/style.css`

**Interfaces:**
- Consumes: `CG.connectionRows`, `CG.clusterLayout`, `CG.timelineLayout`, `CG.spreadLayout`, `CG.computeLayout`;
  `G.layouts` (Task 3); `orderedPick`, `pickOrder`, `openProposal` (Task 5 and the proposals feature).
- Produces: `openEdgeForm(ids, ordered)` (replaces the old `openEdgeForm(sourceId, targetIds)`),
  `applyLayout(id)`, `resetLayout()`, `downloadLayout()`.

- [ ] **Step 1: Connection form.** Replace `openEdgeForm` with a version driven by a row model
  `rows = [{a, type, b, condition}]` where `a` is the From concept id and `b` the To concept id:

```javascript
  function openEdgeForm(ids, ordered) {
    ids = ids || [];
    var order = {};
    G.nodes.forEach(function (n) { var s = sectionsById.get(n.section); order[n.id] = [s ? s.order : 0, n.name]; });
    var chosen = ids.slice().sort(function (x, y) { return order[x][0] - order[y][0] || String(order[x][1]).localeCompare(String(order[y][1])); })[0] || "";
    if (ordered && ids.length) chosen = ids[0];
    var mode = "one_to_many";
    var rows = [];
    function rebuildRows() {
      rows = (ids.length >= 2 ? CG.connectionRows(mode, chosen, ids, order) : [{ source: chosen, target: "" }])
        .map(function (r) { return { a: r.source, b: r.target, type: "is_a", condition: "" }; });
    }
    function draw() {
      var chooser = (!ordered && ids.length >= 2)
        ? '<label>Mode<select id="e-mode">' +
          [["one_to_many", "One to many"], ["many_to_one", "Many to one"], ["chain", "Chain in course order"],
           ["all_pairs", "All pairs (up to 4 concepts)"]].map(function (m) {
            return '<option value="' + m[0] + '"' + (m[0] === mode ? " selected" : "") + ">" + m[1] + "</option>"; }).join("") + "</select></label>" +
          "<label>" + (mode === "many_to_one" ? "To (the chosen concept)" : "From (the chosen concept)") +
          '<select id="e-chosen">' + ids.map(function (id) {
            return '<option value="' + esc(id) + '"' + (id === chosen ? " selected" : "") + ">" + esc(nameOf(id)) + "</option>"; }).join("") + "</select></label>"
        : "";
      form.innerHTML = '<h2 id="propose-title">Propose a connection</h2>' + chooser +
        (mode === "all_pairs" && ids.length > 4 ? '<div class="errors">All pairs needs four or fewer concepts.</div>' : "") +
        '<div id="e-rows">' + rows.map(function (r, i) {
          return '<div class="row sentence" data-i="' + i + '">' +
            '<span class="from">' + (r.a ? esc(nameOf(r.a)) : '<select data-f="a">' + nodeOptions("") + "</select>") + "</span>" +
            '<select data-f="type">' + typeOptions(r.type) + "</select>" +
            '<select data-f="b">' + nodeOptions(r.b) + "</select>" +
            '<button type="button" data-reverse="' + i + '" title="Reverse this row">\u21c4</button>' +
            '<button type="button" data-remove-row="' + i + '">\u00d7</button>' +
            '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" value="' + esc(r.condition) + '" style="grid-column: 1 / -1">' +
            "</div>";
        }).join("") + "</div>" +
        '<button type="button" id="e-reverse-all">Reverse all rows</button> <button type="button" id="e-add">Add a row</button>' +
        '<div class="errors" id="p-errors" hidden></div>' +
        '<div class="buttons"><button type="button" id="p-cancel">Cancel</button><button type="button" id="p-save">Add proposal</button></div>';
    }
    function readRows() {
      Array.from(form.querySelectorAll("[data-i]")).forEach(function (el) {
        var r = rows[Number(el.getAttribute("data-i"))]; if (!r) return;
        var a = el.querySelector('[data-f="a"]');
        r.type = el.querySelector('[data-f="type"]').value;
        r.b = el.querySelector('[data-f="b"]').value;
        r.condition = el.querySelector('[data-f="condition"]').value;
        if (a) r.a = a.value;
      });
    }
    form.onchange = function (ev) {
      if (ev.target.id === "e-mode") { mode = ev.target.value; rebuildRows(); draw(); }
      else if (ev.target.id === "e-chosen") { chosen = ev.target.value; rebuildRows(); draw(); }
    };
    form.onclick = function (ev) {
      var t = ev.target;
      if (t.id === "p-cancel") return dialog.close();
      if (t.hasAttribute("data-reverse")) {
        readRows(); var r = rows[Number(t.getAttribute("data-reverse"))];
        var tmp = r.a; r.a = r.b; r.b = tmp; draw();
      } else if (t.id === "e-reverse-all") {
        readRows(); rows.forEach(function (r) { var x = r.a; r.a = r.b; r.b = x; }); draw();
      } else if (t.hasAttribute("data-remove-row")) {
        readRows(); rows.splice(Number(t.getAttribute("data-remove-row")), 1); draw();
      } else if (t.id === "e-add") {
        readRows(); rows.push({ a: chosen, b: "", type: "is_a", condition: "" }); draw();
      } else if (t.id === "p-save") {
        readRows();
        var made = rows.map(function (r) {
          return { action: "add_edge", proposal: { source: r.a, type: r.type, target: r.b, condition: (r.condition || "").trim() || null, note: "" } };
        });
        var all = [];
        for (var i = 0; i < made.length; i++) {
          var res = CG.checkProposal(G, made[i].proposal, proposals.concat(all));
          if (res.errors.length) return showErrors(res.errors);
          all.push(made[i]);
        }
        if (!all.length) return showErrors(["Add at least one connection."]);
        proposals = proposals.concat(all);
        dialog.close(); persist(); toast(all.length + " connection" + (all.length === 1 ? "" : "s") + " added to your proposals.");
      }
    };
    rebuildRows(); draw();
    if (!dialog.open) dialog.showModal();
  }
```

The row's From shows as static text of `r.a`; reversing makes the old To the new From (text) and the old From the
selected To in the dropdown, as specified. Remove the old global `#e-swap` handling and the click listener that the
proposals feature registered on `form` for `data-remove-row` (the new `form.onclick` replaces it; keep the
`openNodeForm` path working by giving it its own `form.onclick` assignment that handles `p-cancel`, `data-remove-row`
via `.closest(".row").remove()`, `p-add-conn` and `p-save`, exactly as `finishForm`'s old listener did). Update
`openProposal(kind, sourceId, ids, ordered)` to call `openEdgeForm(ids && ids.length ? ids : sourceId ? [sourceId] : [], ordered)`
and the toolbar "New connection" to call it with no ids. The panel's "Propose a connection from this concept" calls it
with `[selected.id]`; `#btn-connect` calls it with `(pickOrder.slice(), orderedPick)`.

- [ ] **Step 1b: Drop the topic dropdown from the concept form.** In `openNodeForm` remove the `p-topic` select and
  take `topic` from the chosen section: `var sec = sectionsById.get(section); topic: sec && sec.topic ? sec.topic : G.vocab.topics[0]`.
  In `logic.js` `checkProposal`, skip the topic-vocabulary check when the proposal's section has a `topic`, and add a
  test to `proposals.test.js` for that (a section with a topic, a proposal with an empty topic: no topic error).

- [ ] **Step 2: Layout presets.** `template.html` inside `#sidebar-top`, after the list tools:

```html
      <label class="layout-row">Layout <select id="layout-select"></select></label>
      <div class="list-tools"><button id="btn-layout-reset" type="button">Reset layout</button><button id="btn-layout-download" type="button">Download layout</button></div>
```

`app.js`:

```javascript
  var LAYOUTS = [
    { id: "spread", name: "Spread", compute: function () { return CG.spreadLayout(G.nodes, G.edges, G.sections); } },
    { id: "rows", name: "Section rows", compute: function () { return CG.computeLayout(G.nodes, G.edges, G.sections); } },
    { id: "cluster", name: "By section", compute: function () { return CG.clusterLayout(G.nodes, G.sections); } },
    { id: "timeline", name: "Course timeline", compute: function () { return CG.timelineLayout(G.nodes, G.sections); } }
  ].concat((G.layouts || []).map(function (l) {
    return { id: "file:" + l.id, name: l.name, compute: function () {
      var base = CG.spreadLayout(G.nodes, G.edges, G.sections), out = {};
      G.nodes.forEach(function (n) { out[n.id] = l.positions[n.id] || base[n.id]; });
      return out;
    } };
  }));
  var currentLayout = storage.get("cg-layout-" + G.graph_version) || "spread";
  function movedKey(id) { return "cg-moved-" + G.graph_version + "-" + id; }
  function layoutPositions(id) {
    var def = LAYOUTS.filter(function (l) { return l.id === id; })[0] || LAYOUTS[0];
    var pos = def.compute();
    try { var moved = JSON.parse(storage.get(movedKey(def.id)) || "{}"); Object.keys(moved).forEach(function (k) { if (pos[k]) pos[k] = moved[k]; }); } catch (e) { /* none */ }
    return pos;
  }
  function applyLayout(id, animate) {
    currentLayout = id; storage.set("cg-layout-" + G.graph_version, id);
    var pos = layoutPositions(id);
    cy.layout({ name: "preset", positions: function (n) { return pos[n.id()]; }, animate: !!animate, animationDuration: 350, fit: false }).run();
    setTimeout(function () { touched = false; refit(); }, animate ? 400 : 0);
  }
  $("#layout-select").innerHTML = LAYOUTS.map(function (l) {
    return '<option value="' + esc(l.id) + '"' + (l.id === currentLayout ? " selected" : "") + ">" + esc(l.name) + "</option>";
  }).join("");
  $("#layout-select").addEventListener("change", function (ev) { applyLayout(ev.target.value, true); });
  cy.on("dragfree", "node", function () {
    var moved = {};
    cy.nodes().forEach(function (n) { if (!n.hasClass("ghost")) moved[n.id()] = { x: Math.round(n.position("x")), y: Math.round(n.position("y")) }; });
    storage.set(movedKey(currentLayout), JSON.stringify(moved));
  });
  $("#btn-layout-reset").addEventListener("click", function () {
    storage.set(movedKey(currentLayout), "{}"); applyLayout(currentLayout, true);
  });
  $("#btn-layout-download").addEventListener("click", function () {
    var positions = {};
    cy.nodes().forEach(function (n) { if (!n.hasClass("ghost")) positions[n.id()] = { x: Math.round(n.position("x")), y: Math.round(n.position("y")) }; });
    var blob = new Blob([JSON.stringify({ name: "My layout", positions: positions }, null, 2)], { type: "application/json" });
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "layout-my-layout.json"; a.click();
  });
```

Call `if (currentLayout !== "spread") applyLayout(currentLayout, false);` in the start block after `buildFilters()`.
`touched` and `refit` are defined in the start block; make `applyLayout` reference them lazily (it does: they are
looked up at call time inside the setTimeout).

- [ ] **Step 3: Verify (headless, `?debug`).**
  1. `__cg.setSelection([a, b, c])`, click `#btn-connect`: the dialog has Mode and chosen-concept dropdowns when the
     last gesture was a box (`orderedPick` false) and no mode chooser after Ctrl-clicks.
  2. In many-to-one mode with chosen `b`: the rows' text Froms are the other two concepts and the To selects equal `b`.
  3. Reverse one row: only that row's From text and To select change; the other rows are unchanged.
  4. Save: `localStorage` proposals contain one `add_edge` per row with the expected source and target.
  5. `#layout-select` to "Course timeline": node positions satisfy `x(s1) < x(s2)`; Reset layout restores them after a drag.
  6. Take a screenshot of the form and of the grouped panel and read them.

- [ ] **Step 4: Commit**

```bash
git add agent/concept_graph/viewer/app.js agent/concept_graph/viewer/template.html agent/concept_graph/viewer/style.css
git commit -m "feat(concept_graph): connection form modes and row reverse; layout presets"
```

---

### Task 7: Graph repo migration, docs and republish

**Files:**
- Modify (graph repo `microecon-concept-graph`): `data/sections.yaml`, `data/nodes/s02-*.yaml`, `data/nodes/s04-*.yaml`,
  `data/nodes/s06-*.yaml`, `config/vocab.yaml`
- Modify (this repo): `agent/concept_graph/README.md`, `docs/status/agent/concept_graph/2026-10-14-concept-graph-proposals-status.md`
  (append a "Viewer selection and layouts" section), `docs/trackers/academic_hub_to_do.md` (a TODO line for the
  summary-stage run, using the next free `TODO-00NN`)

- [ ] **Step 1: Migrate the data** (run once, in the graph repo, with `ruamel` through `GraphStore`):

```python
from agent.concept_graph.store import GraphStore
store = GraphStore(r"C:/Users/theaa/microecon-concept-graph")
meta = {
    "s01-mathematical-preliminaries": ("order-theory", "Order theory"),
    "s02-preference-and-utility": ("rational-choice", "Preferences and utility"),
    "s03-revealed-preference": ("revealed-preference", "Revealed preference"),
    "s04-stochastic-choice": ("stochastic-choice", "Stochastic choice"),
    "s05-consumer-demand": ("demand", "Consumer demand"),
    "s06-duality-and-classical-demand": ("duality", "Duality and Slutsky"),
    "s07-producer-theory": ("producer-theory", "Producer theory"),
    "s08-choice-under-uncertainty": ("risk-and-uncertainty", "Risk and uncertainty"),
}
for sid, (topic, short) in meta.items():
    store.update_section(sid, {"topic": topic, "short": short})
retopic = {"weak-axiom-of-revealed-preference": "rational-choice", "satisficing-procedure": "stochastic-choice",
           "income-effect": "duality", "substitution-effect": "duality", "slutsky-equation": "duality",
           "slutsky-matrix": "duality", "law-of-compensated-demand": "duality",
           "negative-semidefinite-substitution": "duality"}
for node_id, topic in retopic.items():
    store.update_item("node", node_id, {"topic": topic})
```

Then `python -m agent.concept_graph.cli --graph-repo <repo> validate` must report 0 errors (the `missing-summary`
warnings remain until Task 8). Check that `config/vocab.yaml` topics are exactly the eight section topics.

- [ ] **Step 2: Collect the summary run** (8 cards):
  `python -m agent.concept_graph.cli --graph-repo <repo> collect summary --hub-root <hub> --course microecon --work-dir <work>`;
  the printed prompt goes to Gemini (Antigravity); after "done", `submit <run-id>`; `validate` must then report no
  `missing-summary` or `stale-summary` warnings. If a summary is rejected as meta commentary or for copying, the
  bounce text says how.

- [ ] **Step 3: Build and republish.** `build`, check the page headless with `?debug` against the real graph (the
  section buttons show the eight short labels; clicking "Consumer demand" selects its 14 concepts and shows its
  summary), commit the graph repo and push.

- [ ] **Step 4: Docs and full suite.** Update the README (selection model, section buttons, layouts folder, summary
  stage, `?debug`), append the status section, add the TODO line. Run
  `python -m pytest tests/agent/concept_graph -q` and `node --test agent/concept_graph/viewer/tests/*.test.js`.
  Expected: all pass, no `SyntaxWarning`.

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/README.md docs/status/agent/concept_graph/2026-10-14-concept-graph-proposals-status.md docs/trackers/academic_hub_to_do.md
git commit -m "docs(concept_graph): viewer selection, sections as the grouping, summaries and layouts"
```
