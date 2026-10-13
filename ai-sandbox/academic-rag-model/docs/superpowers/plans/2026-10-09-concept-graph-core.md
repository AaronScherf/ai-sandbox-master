# Concept Graph Core (Plan A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data layer, validator, interactive HTML viewer, review loop (`apply-review`, GitHub-issue intake) and mini-repo scaffolding for the microecon concept graph, proven end to end on a hand-written sample graph.

**Architecture:** A new package `agent/concept_graph/` reads a YAML graph (sections, nodes, edges) from a separate "graph repo" checkout, validates it, and builds one self-contained `index.html` (Cytoscape.js, MathML-only KaTeX, inlined) plus `build/graph.json`. Reviewers make accept/reject/edit/comment decisions in the page and submit them as a review JSON; `apply-review` merges those into the YAML with round-trip formatting and never silently overwrites. The LLM stages (`seed`/`fill`/`link`/`critic`, drivers, IP guard) are **Plan B** and are out of scope here.

**Tech Stack:** Python 3.13, pydantic 2, ruamel.yaml (round-trip), PyYAML, networkx, pytest; vanilla JS tested with `node --test`; Cytoscape.js 3.30.2 and KaTeX 0.16.11 vendored; `gh` CLI for issue intake and repo setup.

**Spec:** `docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md` (read it first; this plan implements everything in it except the "Pipeline" LLM stages, the IP guard, the retrieval/drivers section and the ArtifactDb adapter). The spec was amended on 2026-10-09 by this plan's author: edge type `component_of` added, definitional-vs-logical cycle rule, decision D9 (edge types are a code constant).

## Global Constraints

- Work only in a dedicated worktree on branch `claude/concept-graph-core`, created from branch `claude/concept-graph-spec` (the spec and this plan live there). Stage explicit paths; never `git add -A` / `git add .`. Do not touch other worktrees.
- Run Python from `ai-sandbox/academic-rag-model/` as modules (`python -m agent.concept_graph.cli ...`), tests with `python -m pytest tests/agent/concept_graph -q`. Test files are named `test_cg_*.py` (the repo has no `__init__.py` in `tests/`, so test basenames must be unique).
- Edge types, exactly: `is_a`, `has_property`, `defined_on`, `component_of`, `implies`, `iff`, `hypothesis_of`, `yields`, `counterexample_to` (9). `implies`/`iff` require `condition`; `via` is allowed only on `implies`/`iff` and must name a node of kind `theorem` or `lemma`.
- Status values: `proposed` | `verified`. Section states: `taught` | `in_progress` | `planned`. Critic verdicts: `supports` | `weak` | `unsupported`.
- Node and section ids are slugs matching `^[a-z0-9][a-z0-9-]*$` and are never reused. Edge id is exactly `"{source}--{type}--{target}"`.
- Prose is original wording plus citations only. No source text, no instructor names, no email addresses in any file in the graph repo or the sample data. The takedown contact in `NOTICE.md` defaults to the repo's GitHub issues page.
- The viewer must work as a single static file in Chrome, Edge, Firefox and Safari, on desktop and phone: no network at runtime, no server, `localStorage` access always wrapped in try/catch, node names never truncated, KaTeX in `output: "mathml"` mode (no fonts).
- Every API/network call in tests is faked. The only network use is `vendor_fetch.py` (Task 4) and `scaffold` fetching the Creative Commons legal code (Task 9, injectable), and both run once by hand.
- Do not create the GitHub repository, push, enable Pages, or create labels without the owner's explicit go-ahead (Task 11).

## Review Focus

Failure modes the spec implies but a casual test list would miss, most likely first. Each has a pinning test in the task named.

1. A reviewer **rejects a node** that still has edges: the edges must be removed and tombstoned too, otherwise the next `build` fails on dangling endpoints. (Task 7, `test_reject_node_cascades_to_edges`.)
2. A review was made against an **older version** of a field, or two reviewers edit the same field: the edit must become a conflict entry and leave the YAML untouched, not overwrite. (Task 7, `test_stale_edit_is_a_conflict_not_an_overwrite`, `test_second_reviewer_same_field_conflicts`.)
3. Prose containing `</script>` or a lone `$` (prices) must not break the page or the math renderer. (Task 6, `test_script_closer_in_prose_cannot_break_the_page`; Task 4, `splitMath treats a lone dollar as text`.)
4. A review too large for a URL must fall back to the clipboard path instead of producing a truncated or broken link. (Task 4, `issueUrl falls back when the review is too long`.)
5. `localStorage` throws (private window, blocked site data): the viewer must still load and review in memory. (Task 4, `safeStorage survives a throwing localStorage`.)
6. Unquoted YAML dates (`introduced_in: 2026-09-10`) parse as `date` objects and would fail string fields. (Task 2, `test_unquoted_yaml_dates_become_strings`.)

## File Structure

All paths relative to `ai-sandbox/academic-rag-model/`.

```
agent/concept_graph/
  __init__.py                 empty
  __main__.py                 `python -m agent.concept_graph` -> cli.main
  README.md                   usage (Task 10)
  schema.py                   pydantic models, constants, edge_id(), field_hash()           Task 1
  store.py                    GraphStore: read_all / update_item / remove_item / add_rejected  Task 2
  validate.py                 validate(graph) -> list[Issue]                                 Task 3
  vendor_fetch.py             one-time downloader for vendored JS                            Task 4
  build.py                    graph_payload(), build() -> graph.json + index.html            Task 6
  reviews.py                  ReviewFile model, apply_review(), archive_review()             Task 7
  gh_issues.py                fetch review JSON from GitHub issues via `gh`                  Task 8
  scaffold.py                 write a new graph-repo skeleton                                Task 9
  cli.py                      validate | build | apply-review | scaffold                     Tasks 6, 8, 9
  viewer/
    template.html  style.css  logic.js  app.js        Tasks 4, 5
    vendor.lock.json                                   Task 4
    vendor/cytoscape.min.js  katex.min.js  *.LICENSE   Task 4 (committed)
    tests/logic.test.js                                Task 4
  sample_data/                hand-written 17-node graph (also the test fixture)  Task 2
    config/vocab.yaml  config/site.yaml
    data/sections.yaml  data/nodes/*.yaml  data/edges/*.yaml
tests/agent/concept_graph/
  cg_helpers.py  test_cg_schema.py  test_cg_store.py  test_cg_validate.py
  test_cg_viewer_logic.py  test_cg_vendor_fetch.py  test_cg_build.py
  test_cg_reviews.py  test_cg_gh_issues.py  test_cg_scaffold.py  test_cg_cli.py
```

---

### Task 1: Worktree, dependencies, and the schema

**Files:**
- Create: `agent/concept_graph/__init__.py`, `agent/concept_graph/schema.py`
- Create: `tests/agent/concept_graph/test_cg_schema.py`
- Modify: `requirements.txt` (append three lines)

**Interfaces:**
- Produces (used by every later task):
  - `EDGE_TYPES: tuple[str, ...]` (the 9 types), `CONDITION_REQUIRED = ("implies", "iff")`, `VIA_ALLOWED = ("implies", "iff")`, `VIA_KINDS = ("theorem", "lemma")`, `DEFINITIONAL_TYPES = ("is_a", "defined_on", "has_property", "component_of")`, `LOGICAL_TYPES = ("implies", "hypothesis_of", "yields")`, `EDITABLE_NODE_FIELDS = ("gist", "explanation", "formal", "example")`, `EDITABLE_EDGE_FIELDS = ("condition", "explanation")`
  - models: `Citation(source, ref)`, `Critic(verdict, note)`, `Provenance(driver, agent, model, run)`, `Section(id, title, order, state, lectures, syllabus_ref)`, `Node(...)`, `Edge(...)`, `Vocab(kinds, topics)`, `Rejected(kind, id)`
  - `Graph` dataclass: `sections, nodes, edges, rejected, vocab, site: dict, node_files: dict[str, str]`
  - `edge_id(source: str, type_: str, target: str) -> str`; `field_hash(value: str | None) -> str` (16 hex chars)

- [ ] **Step 1: Create the worktree and a minimal venv**

Run from the repo root `C:\Users\theaa\ai-sandbox-master` (PowerShell):

```powershell
git status --short
git worktree list
$base = git rev-parse claude/concept-graph-spec
git worktree add -b claude/concept-graph-core .worktrees/claude-concept-graph-core $base
Set-Location .worktrees/claude-concept-graph-core/ai-sandbox/academic-rag-model
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --quiet pydantic pyyaml networkx ruamel.yaml pytest
.\.venv\Scripts\python.exe -c "import pydantic, yaml, networkx, ruamel.yaml, pytest; print('deps ok')"
git status --short
```

Expected: `deps ok`; `git status --short` shows no `.venv` (it is gitignored). If `.venv` shows as untracked, stop and report instead of committing it.

- [ ] **Step 2: Append the dependencies**

Append these three lines to `requirements.txt` (the file lists unpinned names):

```
pydantic
networkx
ruamel.yaml
```

- [ ] **Step 3: Write the failing test**

Create `tests/agent/concept_graph/test_cg_schema.py`:

```python
import pytest
from pydantic import ValidationError

from agent.concept_graph.schema import (
    EDGE_TYPES,
    Edge,
    Node,
    Section,
    edge_id,
    field_hash,
)


def test_edge_id_is_canonical():
    assert edge_id("total-order", "is_a", "partial-order") == "total-order--is_a--partial-order"


def test_field_hash_ignores_surrounding_whitespace_and_none():
    assert field_hash("  hello\n") == field_hash("hello")
    assert field_hash(None) == field_hash("")
    assert len(field_hash("x")) == 16


def test_node_rejects_unknown_fields_and_bad_slug():
    with pytest.raises(ValidationError):
        Node(id="Bad Id", name="x", kind="object", section="s", topic="t")
    with pytest.raises(ValidationError):
        Node(id="ok", name="x", kind="object", section="s", topic="t", colour="red")


def test_node_defaults_to_proposed_with_empty_prose():
    n = Node(id="ok", name="Ok", kind="object", section="s", topic="t")
    assert n.status == "proposed"
    assert n.explanation == ""
    assert n.citations == []
    assert n.critic is None


def test_section_state_is_restricted():
    with pytest.raises(ValidationError):
        Section(id="s1", title="T", order=1, state="done")


def test_edge_requires_slug_endpoints():
    with pytest.raises(ValidationError):
        Edge(id="x", source="Not Slug", type="is_a", target="b")
    e = Edge(id="a--is_a--b", source="a", type="is_a", target="b")
    assert e.condition is None and e.via is None and e.status == "proposed"


def test_there_are_nine_edge_types_including_component_of():
    assert len(EDGE_TYPES) == 9
    assert "component_of" in EDGE_TYPES
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_schema.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'agent.concept_graph'`).

- [ ] **Step 5: Write the implementation**

Create `agent/concept_graph/__init__.py` (empty file) and `agent/concept_graph/schema.py`:

```python
"""Pydantic models and shared constants for the concept graph (see the design spec)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SLUG = r"^[a-z0-9][a-z0-9-]*$"

EDGE_TYPES = (
    "is_a",
    "has_property",
    "defined_on",
    "component_of",
    "implies",
    "iff",
    "hypothesis_of",
    "yields",
    "counterexample_to",
)
CONDITION_REQUIRED = ("implies", "iff")
VIA_ALLOWED = ("implies", "iff")
VIA_KINDS = ("theorem", "lemma")
DEFINITIONAL_TYPES = ("is_a", "defined_on", "has_property", "component_of")
LOGICAL_TYPES = ("implies", "hypothesis_of", "yields")
EDITABLE_NODE_FIELDS = ("gist", "explanation", "formal", "example")
EDITABLE_EDGE_FIELDS = ("condition", "explanation")

Status = Literal["proposed", "verified"]
SectionState = Literal["taught", "in_progress", "planned"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(_Model):
    source: str
    ref: str


class Critic(_Model):
    verdict: Literal["supports", "weak", "unsupported"]
    note: str = ""


class Provenance(_Model):
    driver: str
    agent: str | None = None
    model: str | None = None
    run: str | None = None


class _Item(_Model):
    """Review bookkeeping shared by nodes and edges."""

    citations: list[Citation] = Field(default_factory=list)
    status: Status = "proposed"
    critic: Critic | None = None
    provenance: Provenance | None = None
    reviewed_by: str | None = None
    reviewed_on: str | None = None


class Section(_Model):
    id: str = Field(pattern=SLUG)
    title: str
    order: float
    state: SectionState
    lectures: list[str] = Field(default_factory=list)
    syllabus_ref: str | None = None


class Node(_Item):
    id: str = Field(pattern=SLUG)
    name: str
    kind: str
    section: str
    topic: str
    introduced_in: str | None = None
    gist: str = ""
    explanation: str = ""
    formal: str | None = None
    example: str | None = None


class Edge(_Item):
    id: str
    source: str = Field(pattern=SLUG)
    type: str
    target: str = Field(pattern=SLUG)
    condition: str | None = None
    via: str | None = None
    explanation: str = ""


class Vocab(_Model):
    kinds: list[str]
    topics: list[str]


class Rejected(_Model):
    kind: Literal["node", "edge"]
    id: str


@dataclass
class Graph:
    sections: list[Section]
    nodes: list[Node]
    edges: list[Edge]
    rejected: list[Rejected]
    vocab: Vocab
    site: dict = field(default_factory=dict)
    node_files: dict[str, str] = field(default_factory=dict)


def edge_id(source: str, type_: str, target: str) -> str:
    return f"{source}--{type_}--{target}"


def field_hash(value: str | None) -> str:
    """Stable 16-hex-char hash of an editable field; used to detect stale edits."""
    return hashlib.sha256((value or "").strip().encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_schema.py -q`
Expected: PASS (7 passed).

- [ ] **Step 7: Commit**

```powershell
git add requirements.txt agent/concept_graph/__init__.py agent/concept_graph/schema.py tests/agent/concept_graph/test_cg_schema.py
git diff --cached --stat
git commit -m "feat(concept_graph): schema models and constants" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The sample graph and `GraphStore`

**Files:**
- Create: `agent/concept_graph/sample_data/config/vocab.yaml`, `config/site.yaml`, `data/sections.yaml`, `data/nodes/s01-binary-relations.yaml`, `data/nodes/s02-choice.yaml`, `data/nodes/s03-demand.yaml`, `data/edges/s01-binary-relations.yaml`, `data/edges/s02-choice.yaml` (all under `agent/concept_graph/sample_data/`)
- Create: `agent/concept_graph/store.py`
- Create: `tests/agent/concept_graph/cg_helpers.py`, `tests/agent/concept_graph/test_cg_store.py`

**Interfaces:**
- Consumes: Task 1 models.
- Produces:
  - `GraphDataError(Exception)`
  - `GraphStore(root: str | Path)` with
    - `read_all() -> Graph`
    - `update_item(kind: Literal["node","edge"], item_id: str, changes: dict) -> None` (raises `KeyError` if absent; preserves comments and other items)
    - `remove_item(kind, item_id) -> None` (raises `KeyError` if absent)
    - `add_rejected(kind, item_id) -> None`
  - `cg_helpers.copy_sample(dest: Path) -> Path` (copies `sample_data` into `dest / "graph"` and returns that path)
- The sample graph contents are fixed here and later tasks assert on them: sections `s01-binary-relations` (1), `s02-choice` (2), `s03-demand` (3, planned); 17 nodes; 17 edges; the only expected validation warning is one `logical-cycle` (rational-preference <-> warp).

- [ ] **Step 1: Write the sample data (these are the fixture; copy exactly)**

`sample_data/config/vocab.yaml`:

```yaml
kinds: [object, structure, property, axiom, definition, theorem, lemma, model, function, correspondence, identity, technique, example]
topics: [order-theory, rational-choice, revealed-preference, demand]
```

`sample_data/config/site.yaml`:

```yaml
title: Microeconomics concept graph
repo: null
```

`sample_data/data/sections.yaml`:

```yaml
- id: s01-binary-relations
  title: Binary relations and orders
  order: 1
  state: taught
  lectures: []
- id: s02-choice
  title: Choice and revealed preference
  order: 2
  state: taught
  lectures: []
- id: s03-demand
  title: Consumer demand
  order: 3
  state: planned
  lectures: []
```

`sample_data/data/nodes/s01-binary-relations.yaml`:

```yaml
- id: set
  name: Set
  kind: structure
  section: s01-binary-relations
  topic: order-theory
  gist: A collection of distinct objects; the ground floor everything else is built on.
  explanation: |
    A set is just a collection of distinct things, with no order and no repeats. Alternatives, bundles of goods
    and states of the world are all modelled as elements of some set $X$.
  citations:
    - {source: ok, ref: "ch. 1"}
  status: proposed
- id: binary-relation
  name: Binary relation
  kind: object
  section: s01-binary-relations
  topic: order-theory
  gist: A rule that says, for some ordered pairs of elements of a set, that the first is related to the second.
  explanation: |
    A binary relation $R$ on a set $X$ is a collection of ordered pairs of elements of $X$. Writing $x R y$ means
    the pair $(x, y)$ is in the collection. Preferences, "at least as good as" and "is a multiple of" are all
    binary relations.
  formal: |
    $R \subseteq X \times X$.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: reflexivity
  name: Reflexivity
  kind: property
  section: s01-binary-relations
  topic: order-theory
  gist: Everything is related to itself.
  explanation: |
    A relation is reflexive when every element is related to itself. For "at least as good as" this says each
    alternative is at least as good as itself.
  formal: |
    $\forall x \in X:\ x R x$.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: transitivity
  name: Transitivity
  kind: property
  section: s01-binary-relations
  topic: order-theory
  gist: If a is related to b and b to c, then a is related to c.
  explanation: |
    Chains of comparisons carry through. If $x$ is at least as good as $y$ and $y$ is at least as good as $z$,
    then $x$ is at least as good as $z$.
  formal: |
    $\forall x, y, z:\ x R y \wedge y R z \Rightarrow x R z$.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: antisymmetry
  name: Antisymmetry
  kind: property
  section: s01-binary-relations
  topic: order-theory
  gist: Two different elements are never related in both directions.
  explanation: |
    If two elements are related in both directions they must be the same element. This is what rules out ties
    between distinct elements.
  formal: |
    $\forall x, y:\ x R y \wedge y R x \Rightarrow x = y$.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: completeness
  name: Completeness
  kind: property
  section: s01-binary-relations
  topic: order-theory
  gist: Any two elements can be compared.
  explanation: |
    For every pair of elements, at least one is related to the other. Nothing is left incomparable.
  formal: |
    $\forall x, y:\ x R y \vee y R x$.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: preorder
  name: Preorder
  kind: object
  section: s01-binary-relations
  topic: order-theory
  gist: A binary relation that is reflexive and transitive.
  explanation: |
    A preorder is the weakest useful notion of ranking: every element ranks with itself and comparisons chain
    together, but ties between different elements are allowed and some pairs may be incomparable.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: partial-order
  name: Partial order
  kind: object
  section: s01-binary-relations
  topic: order-theory
  gist: A preorder that is also antisymmetric.
  explanation: |
    A partial order ranks elements without ties between distinct elements, but may leave some pairs
    incomparable. Divisibility on the positive integers is the standard example.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: total-order
  name: Total order
  kind: object
  section: s01-binary-relations
  topic: order-theory
  gist: A partial order in which every pair is comparable.
  explanation: |
    A total order lines all the elements up on a single ladder: no ties between distinct elements and no
    incomparable pairs.
  citations:
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
- id: szpilrajn-extension
  name: Szpilrajn extension theorem
  kind: theorem
  section: s01-binary-relations
  topic: order-theory
  gist: Every partial order can be completed into a total order without contradicting it.
  explanation: |
    Given any partial order, one can add comparisons for the incomparable pairs and obtain a total order that
    still ranks every pair the original already ranked in the same way. For infinite sets the proof needs the
    axiom of choice.
  citations:
    - {source: ok, ref: "ch. 1"}
  status: proposed
- id: rational-preference
  name: Rational preference relation
  kind: object
  section: s01-binary-relations
  topic: rational-choice
  gist: A complete and transitive "at least as good as" relation.
  explanation: |
    A decision maker's preferences are called rational when they are complete (any two alternatives can be
    compared) and transitive (comparisons chain). Everything in standard consumer theory starts here.
  formal: |
    $\succsim$ is complete and transitive on $X$.
  citations:
    - {source: mwg, ref: "1.B"}
    - {source: rubinstein, ref: "ch. 2"}
  status: proposed
```

`sample_data/data/nodes/s02-choice.yaml`:

```yaml
- id: choice-structure
  name: Choice structure
  kind: structure
  section: s02-choice
  topic: revealed-preference
  gist: A family of available sets together with what is chosen from each.
  explanation: |
    A choice structure pairs a family of budget sets (the menus that might be offered) with a rule saying which
    elements are chosen from each menu. It describes behaviour directly, without mentioning preferences.
  citations:
    - {source: mwg, ref: "1.C"}
  status: proposed
- id: sen-alpha
  name: Sen's alpha
  kind: axiom
  section: s02-choice
  topic: revealed-preference
  gist: Something chosen from a big menu is still chosen from any smaller menu that contains it.
  explanation: |
    If an element is chosen from a menu and it also belongs to a smaller menu inside it, it must be chosen
    from the smaller one too. Shrinking the menu cannot make a still-available winner lose.
  citations:
    - {source: lecture, ref: "choice and revealed preference"}
  status: proposed
- id: sen-beta
  name: Sen's beta
  kind: axiom
  section: s02-choice
  topic: revealed-preference
  gist: If two elements are both chosen from a small menu, a bigger menu cannot choose one without the other.
  explanation: |
    When two elements tie as chosen in a small menu, then in any larger menu that contains it, choosing one of
    them forces choosing the other as well.
  citations:
    - {source: lecture, ref: "choice and revealed preference"}
  status: proposed
- id: sen-alpha-beta
  name: Sen's alpha and beta together
  kind: axiom
  section: s02-choice
  topic: revealed-preference
  gist: The bundle of both consistency conditions at once.
  explanation: |
    A bundle node: the choice structure satisfies Sen's alpha and Sen's beta simultaneously. It exists so the
    equivalence with the weak axiom can be drawn as one edge.
  citations:
    - {source: lecture, ref: "choice and revealed preference"}
  status: proposed
- id: warp
  name: Weak axiom of revealed preference
  kind: axiom
  section: s02-choice
  topic: revealed-preference
  gist: If x is chosen when y is available, then y is never chosen without x being chosen too whenever both are available.
  explanation: |
    The weak axiom captures "observed consistent choice behaviour". If you ever pick $x$ while $y$ was on the
    menu, you may not pick $y$ without also picking $x$ in another menu where both are available.
  citations:
    - {source: mwg, ref: "1.C"}
  status: proposed
```

`sample_data/data/nodes/s03-demand.yaml`:

```yaml
- id: walrasian-demand
  name: Walrasian demand
  kind: correspondence
  section: s03-demand
  topic: demand
  status: proposed
```

`sample_data/data/edges/s01-binary-relations.yaml`:

```yaml
- id: binary-relation--defined_on--set
  source: binary-relation
  type: defined_on
  target: set
  explanation: A binary relation on $X$ is a set of ordered pairs drawn from $X$.
  status: proposed
- id: preorder--is_a--binary-relation
  source: preorder
  type: is_a
  target: binary-relation
  condition: it is reflexive and transitive
  explanation: A preorder is a binary relation with two extra properties.
  status: proposed
- id: preorder--has_property--reflexivity
  source: preorder
  type: has_property
  target: reflexivity
  status: proposed
- id: preorder--has_property--transitivity
  source: preorder
  type: has_property
  target: transitivity
  status: proposed
- id: partial-order--is_a--preorder
  source: partial-order
  type: is_a
  target: preorder
  condition: it is also antisymmetric
  explanation: Adding antisymmetry removes ties between distinct elements.
  status: proposed
- id: partial-order--has_property--antisymmetry
  source: partial-order
  type: has_property
  target: antisymmetry
  status: proposed
- id: total-order--is_a--partial-order
  source: total-order
  type: is_a
  target: partial-order
  condition: it is also complete, so every pair is comparable
  explanation: Adding completeness removes incomparable pairs.
  status: proposed
- id: total-order--has_property--completeness
  source: total-order
  type: has_property
  target: completeness
  status: proposed
- id: partial-order--hypothesis_of--szpilrajn-extension
  source: partial-order
  type: hypothesis_of
  target: szpilrajn-extension
  explanation: The theorem starts from an arbitrary partial order.
  status: proposed
- id: szpilrajn-extension--yields--total-order
  source: szpilrajn-extension
  type: yields
  target: total-order
  explanation: The conclusion is a total order that extends the original.
  status: proposed
- id: rational-preference--is_a--preorder
  source: rational-preference
  type: is_a
  target: preorder
  condition: it is also complete
  explanation: A rational preference relation is a complete preorder.
  status: proposed
```

`sample_data/data/edges/s02-choice.yaml`:

```yaml
- id: choice-structure--defined_on--set
  source: choice-structure
  type: defined_on
  target: set
  explanation: Menus and choices are subsets of a set $X$ of alternatives.
  status: proposed
- id: sen-alpha--component_of--sen-alpha-beta
  source: sen-alpha
  type: component_of
  target: sen-alpha-beta
  status: proposed
- id: sen-beta--component_of--sen-alpha-beta
  source: sen-beta
  type: component_of
  target: sen-alpha-beta
  status: proposed
- id: sen-alpha-beta--iff--warp
  source: sen-alpha-beta
  type: iff
  target: warp
  condition: choices are defined on a rich enough family of menus (confirm the exact domain condition in the course notes)
  explanation: Satisfying both of Sen's conditions is the same as satisfying the weak axiom.
  status: proposed
- id: rational-preference--implies--warp
  source: rational-preference
  type: implies
  target: warp
  condition: choices are the most-preferred elements of each menu
  explanation: Choosing the best element under a rational preference always satisfies the weak axiom.
  citations:
    - {source: mwg, ref: "1.D"}
  status: proposed
- id: warp--implies--rational-preference
  source: warp
  type: implies
  target: rational-preference
  condition: the family of menus contains every subset of up to three elements
  explanation: Under that richness condition, weak-axiom behaviour can be rationalized by some rational preference.
  citations:
    - {source: mwg, ref: "1.D"}
  status: proposed
```

- [ ] **Step 2: Write the failing tests**

`tests/agent/concept_graph/cg_helpers.py`:

```python
import shutil
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "sample_data"


def copy_sample(dest: Path) -> Path:
    """Copy the sample graph into dest/graph and return that directory."""
    target = Path(dest) / "graph"
    shutil.copytree(SAMPLE, target)
    return target
```

`tests/agent/concept_graph/test_cg_store.py`:

```python
import pytest

from agent.concept_graph.store import GraphDataError, GraphStore
from cg_helpers import copy_sample


def test_read_all_loads_the_sample(tmp_path):
    g = GraphStore(copy_sample(tmp_path)).read_all()
    assert [s.id for s in g.sections] == ["s01-binary-relations", "s02-choice", "s03-demand"]
    assert len(g.nodes) == 17
    assert len(g.edges) == 17
    assert g.node_files["partial-order"] == "s01-binary-relations"
    assert g.rejected == []
    assert "order-theory" in g.vocab.topics
    assert g.site["title"] == "Microeconomics concept graph"


def test_unquoted_yaml_dates_become_strings(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s03-demand.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  introduced_in: 2026-09-10\n", encoding="utf-8")
    g = GraphStore(root).read_all()
    node = next(n for n in g.nodes if n.id == "walrasian-demand")
    assert node.introduced_in == "2026-09-10"


def test_update_item_changes_one_item_and_keeps_comments(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s01-binary-relations.yaml"
    path.write_text("# keep me\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    store = GraphStore(root)
    store.update_item("node", "preorder", {"status": "verified", "reviewed_by": "Ada", "gist": "line one\nline two"})
    assert "# keep me" in path.read_text(encoding="utf-8")
    g = store.read_all()
    preorder = next(n for n in g.nodes if n.id == "preorder")
    assert preorder.status == "verified" and preorder.reviewed_by == "Ada"
    assert preorder.gist.strip() == "line one\nline two"
    assert next(n for n in g.nodes if n.id == "partial-order").status == "proposed"


def test_update_unknown_item_raises(tmp_path):
    with pytest.raises(KeyError):
        GraphStore(copy_sample(tmp_path)).update_item("edge", "nope", {"status": "verified"})


def test_remove_item_and_tombstone(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.remove_item("edge", "preorder--has_property--reflexivity")
    store.add_rejected("edge", "preorder--has_property--reflexivity")
    g = store.read_all()
    assert len(g.edges) == 16
    assert [(r.kind, r.id) for r in g.rejected] == [("edge", "preorder--has_property--reflexivity")]
    with pytest.raises(KeyError):
        store.remove_item("edge", "preorder--has_property--reflexivity")


def test_missing_vocab_raises(tmp_path):
    root = copy_sample(tmp_path)
    (root / "config" / "vocab.yaml").unlink()
    with pytest.raises(GraphDataError, match="vocab"):
        GraphStore(root).read_all()


def test_bad_item_error_names_the_file(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s03-demand.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  colour: red\n", encoding="utf-8")
    with pytest.raises(GraphDataError, match="s03-demand.yaml"):
        GraphStore(root).read_all()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_store.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.concept_graph.store`).

- [ ] **Step 4: Write the implementation**

`agent/concept_graph/store.py`:

```python
"""Read and update a graph repo's YAML (round-trip safe) as pydantic models."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from .schema import Edge, Graph, Node, Rejected, Section, Vocab


class GraphDataError(Exception):
    """A graph data file is missing or malformed; the message names the file."""


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, str):
        return str(obj)
    return obj


class GraphStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    # -- low-level file access ------------------------------------------------
    def _load(self, path: Path):
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return _yaml().load(fh)

    def _save(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            _yaml().dump(data, fh)

    def _files(self, kind: Literal["node", "edge"]) -> list[Path]:
        folder = self.root / "data" / ("nodes" if kind == "node" else "edges")
        return sorted(folder.glob("*.yaml")) if folder.is_dir() else []

    @staticmethod
    def _model(cls, raw, path: Path):
        try:
            return cls(**_plain(raw))
        except (ValidationError, TypeError) as exc:
            raise GraphDataError(f"{path}: {exc}") from exc

    # -- reading ---------------------------------------------------------------
    def read_all(self) -> Graph:
        vocab_path = self.root / "config" / "vocab.yaml"
        raw_vocab = self._load(vocab_path)
        if raw_vocab is None:
            raise GraphDataError(f"missing vocab file: {vocab_path}")
        vocab = self._model(Vocab, raw_vocab, vocab_path)
        site = _plain(self._load(self.root / "config" / "site.yaml") or {})

        sections_path = self.root / "data" / "sections.yaml"
        sections = [self._model(Section, s, sections_path) for s in (self._load(sections_path) or [])]

        nodes: list[Node] = []
        node_files: dict[str, str] = {}
        for path in self._files("node"):
            for raw in self._load(path) or []:
                node = self._model(Node, raw, path)
                nodes.append(node)
                node_files[node.id] = path.stem

        edges: list[Edge] = []
        for path in self._files("edge"):
            for raw in self._load(path) or []:
                edges.append(self._model(Edge, raw, path))

        rejected_path = self.root / "data" / "rejected.yaml"
        rejected = [self._model(Rejected, r, rejected_path) for r in (self._load(rejected_path) or [])]
        return Graph(
            sections=sections, nodes=nodes, edges=edges, rejected=rejected,
            vocab=vocab, site=site, node_files=node_files,
        )

    # -- writing ---------------------------------------------------------------
    def update_item(self, kind: Literal["node", "edge"], item_id: str, changes: dict) -> None:
        for path in self._files(kind):
            data = self._load(path) or []
            for item in data:
                if item.get("id") == item_id:
                    for key, value in changes.items():
                        item[key] = LiteralScalarString(value) if isinstance(value, str) and "\n" in value else value
                    self._save(path, data)
                    return
        raise KeyError(f"{kind} {item_id!r} not found")

    def remove_item(self, kind: Literal["node", "edge"], item_id: str) -> None:
        for path in self._files(kind):
            data = self._load(path) or []
            for index, item in enumerate(data):
                if item.get("id") == item_id:
                    del data[index]
                    self._save(path, data)
                    return
        raise KeyError(f"{kind} {item_id!r} not found")

    def add_rejected(self, kind: Literal["node", "edge"], item_id: str) -> None:
        path = self.root / "data" / "rejected.yaml"
        data = self._load(path)
        if data is None:
            data = []
        data.append({"kind": kind, "id": item_id})
        if hasattr(data, "fa"):  # a file that started as "[]" loads as a flow-style list; keep the file readable
            data.fa.set_block_style()
        self._save(path, data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_store.py -q`
Expected: PASS (7 passed). If `test_update_item_changes_one_item_and_keeps_comments` fails only on the `gist` assertion, ruamel emitted `|-`; the `.strip()` in the test already allows for that, so a failure there means a real bug.

- [ ] **Step 6: Commit**

```powershell
git add agent/concept_graph/sample_data agent/concept_graph/store.py tests/agent/concept_graph/cg_helpers.py tests/agent/concept_graph/test_cg_store.py
git diff --cached --stat
git commit -m "feat(concept_graph): sample graph and round-trip GraphStore" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Build-time validation

**Files:**
- Create: `agent/concept_graph/validate.py`
- Create: `tests/agent/concept_graph/test_cg_validate.py`

**Interfaces:**
- Consumes: `Graph`, `Node`, `Edge`, constants (Task 1); `GraphStore.read_all` and `copy_sample` (Task 2).
- Produces: `Issue(level: str, code: str, message: str, ref: str)` frozen dataclass; `validate(graph: Graph) -> list[Issue]`; `errors(issues: list[Issue]) -> list[Issue]`. Issue codes: `dup-id`, `unknown-section`, `unknown-kind`, `unknown-topic`, `node-file-mismatch`, `unknown-edge-type`, `bad-edge-id`, `dangling-endpoint`, `self-loop`, `missing-condition`, `via-not-allowed`, `bad-via`, `definitional-cycle` (error); `logical-cycle`, `orphan`, `unfilled` (warning).

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_validate.py`:

```python
from agent.concept_graph.schema import Edge, Node
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample


def load(tmp_path):
    return GraphStore(copy_sample(tmp_path)).read_all()


def codes(issues):
    return sorted(i.code for i in issues)


def test_the_sample_has_no_errors_and_one_logical_cycle_warning(tmp_path):
    issues = validate(load(tmp_path))
    assert errors(issues) == []
    assert codes(issues) == ["logical-cycle"]
    assert "rational-preference" in issues[0].message and "warp" in issues[0].message


def test_dangling_endpoint(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="ghost--is_a--set", source="ghost", type="is_a", target="set"))
    assert "dangling-endpoint" in codes(validate(g))


def test_duplicate_node_id(tmp_path):
    g = load(tmp_path)
    g.nodes.append(g.nodes[0].model_copy())
    assert "dup-id" in codes(validate(g))


def test_unknown_kind_topic_and_section(tmp_path):
    g = load(tmp_path)
    g.nodes[0] = g.nodes[0].model_copy(update={"kind": "gizmo", "topic": "astrology", "section": "s99"})
    found = codes(validate(g))
    assert {"unknown-kind", "unknown-topic", "unknown-section"} <= set(found)


def test_node_in_the_wrong_file(tmp_path):
    g = load(tmp_path)
    g.node_files["set"] = "s02-choice"
    assert "node-file-mismatch" in codes(validate(g))


def test_unknown_edge_type_and_non_canonical_id(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="wrong-id", source="set", type="befriends", target="binary-relation"))
    found = codes(validate(g))
    assert "unknown-edge-type" in found and "bad-edge-id" in found


def test_implies_and_iff_need_a_condition(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="set--implies--binary-relation", source="set", type="implies", target="binary-relation"))
    assert "missing-condition" in codes(validate(g))


def test_via_only_on_implies_or_iff_and_must_be_a_theorem(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="set--is_a--binary-relation", source="set", type="is_a", target="binary-relation", via="szpilrajn-extension"))
    g.edges.append(Edge(id="reflexivity--implies--transitivity", source="reflexivity", type="implies",
                        target="transitivity", condition="c", via="set"))
    found = codes(validate(g))
    assert "via-not-allowed" in found and "bad-via" in found


def test_a_valid_via_is_accepted(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="reflexivity--implies--transitivity", source="reflexivity", type="implies",
                        target="transitivity", condition="c", via="szpilrajn-extension"))
    assert errors(validate(g)) == []


def test_self_loop(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="set--is_a--set", source="set", type="is_a", target="set"))
    assert "self-loop" in codes(validate(g))


def test_a_definitional_cycle_is_an_error(tmp_path):
    g = load(tmp_path)
    g.edges.append(Edge(id="binary-relation--is_a--preorder", source="binary-relation", type="is_a", target="preorder"))
    found = [i for i in validate(g) if i.code == "definitional-cycle"]
    assert found and found[0].level == "error"


def test_an_orphan_in_a_taught_section_is_a_warning_but_not_in_a_planned_one(tmp_path):
    g = load(tmp_path)
    g.nodes.append(Node(id="lonely", name="Lonely", kind="object", section="s01-binary-relations",
                        topic="order-theory", explanation="x"))
    g.node_files["lonely"] = "s01-binary-relations"
    orphans = [i.ref for i in validate(g) if i.code == "orphan"]
    assert orphans == ["lonely"]  # walrasian-demand is also unlinked but its section is planned


def test_unfilled_node_in_a_taught_section_is_a_warning(tmp_path):
    g = load(tmp_path)
    g.nodes[0] = g.nodes[0].model_copy(update={"explanation": ""})
    assert [i.ref for i in validate(g) if i.code == "unfilled"] == [g.nodes[0].id]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_validate.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.concept_graph.validate`).

- [ ] **Step 3: Write the implementation**

`agent/concept_graph/validate.py`:

```python
"""Build-time validation of a Graph: errors block a build, warnings are reported."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import networkx as nx

from .schema import (
    CONDITION_REQUIRED, DEFINITIONAL_TYPES, EDGE_TYPES, LOGICAL_TYPES, VIA_ALLOWED, VIA_KINDS,
    Graph, edge_id,
)


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str
    ref: str


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]


def _cycles(edges, types) -> list[list[str]]:
    g = nx.DiGraph()
    for e in edges:
        if e.type in types and e.source != e.target:
            g.add_edge(e.source, e.target)
    return [sorted(c) for c in nx.strongly_connected_components(g) if len(c) > 1]


def validate(graph: Graph) -> list[Issue]:
    issues: list[Issue] = []

    def err(code, message, ref):
        issues.append(Issue("error", code, message, ref))

    def warn(code, message, ref):
        issues.append(Issue("warning", code, message, ref))

    sections = {s.id: s for s in graph.sections}
    nodes = {n.id: n for n in graph.nodes}

    for dup, count in Counter(n.id for n in graph.nodes).items():
        if count > 1:
            err("dup-id", f"node id {dup!r} appears {count} times", dup)
    for dup, count in Counter(e.id for e in graph.edges).items():
        if count > 1:
            err("dup-id", f"edge id {dup!r} appears {count} times", dup)
    for dup, count in Counter(s.id for s in graph.sections).items():
        if count > 1:
            err("dup-id", f"section id {dup!r} appears {count} times", dup)

    for n in graph.nodes:
        if n.section not in sections:
            err("unknown-section", f"node {n.id!r} names unknown section {n.section!r}", n.id)
        if n.kind not in graph.vocab.kinds:
            err("unknown-kind", f"node {n.id!r} has kind {n.kind!r} which is not in config/vocab.yaml", n.id)
        if n.topic not in graph.vocab.topics:
            err("unknown-topic", f"node {n.id!r} has topic {n.topic!r} which is not in config/vocab.yaml", n.id)
        filed_in = graph.node_files.get(n.id)
        if filed_in is not None and filed_in != n.section:
            err("node-file-mismatch", f"node {n.id!r} is in {filed_in}.yaml but its section is {n.section!r}", n.id)

    for e in graph.edges:
        if e.type not in EDGE_TYPES:
            err("unknown-edge-type", f"edge {e.id!r} has unknown type {e.type!r}", e.id)
        if e.id != edge_id(e.source, e.type, e.target):
            err("bad-edge-id", f"edge id {e.id!r} should be {edge_id(e.source, e.type, e.target)!r}", e.id)
        for end in (e.source, e.target):
            if end not in nodes:
                err("dangling-endpoint", f"edge {e.id!r} refers to unknown node {end!r}", e.id)
        if e.source == e.target:
            err("self-loop", f"edge {e.id!r} connects a node to itself", e.id)
        if e.type in CONDITION_REQUIRED and not (e.condition or "").strip():
            err("missing-condition", f"{e.type} edge {e.id!r} needs a condition", e.id)
        if e.via is not None:
            if e.type not in VIA_ALLOWED:
                err("via-not-allowed", f"edge {e.id!r}: 'via' is only allowed on {', '.join(VIA_ALLOWED)}", e.id)
            via_node = nodes.get(e.via)
            if via_node is None or via_node.kind not in VIA_KINDS:
                err("bad-via", f"edge {e.id!r}: via {e.via!r} must be a node of kind {' or '.join(VIA_KINDS)}", e.id)

    for cycle in _cycles(graph.edges, DEFINITIONAL_TYPES):
        err("definitional-cycle", f"definitional edges form a cycle: {', '.join(cycle)}", cycle[0])
    for cycle in _cycles(graph.edges, LOGICAL_TYPES):
        warn("logical-cycle",
             f"these nodes imply each other in a loop; check each edge states its own condition: {', '.join(cycle)}",
             cycle[0])

    linked = {e.source for e in graph.edges} | {e.target for e in graph.edges}
    for n in graph.nodes:
        state = sections[n.section].state if n.section in sections else "planned"
        if state == "planned":
            continue
        if n.id not in linked:
            warn("orphan", f"node {n.id!r} has no edges", n.id)
        if not n.explanation.strip():
            warn("unfilled", f"node {n.id!r} is in a {state} section but has no explanation", n.id)
    return issues
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_validate.py -q`
Expected: PASS (13 passed).

- [ ] **Step 5: Commit**

```powershell
git add agent/concept_graph/validate.py tests/agent/concept_graph/test_cg_validate.py
git diff --cached --stat
git commit -m "feat(concept_graph): build-time graph validation" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Viewer logic (pure JS) and vendored libraries

**Files:**
- Create: `agent/concept_graph/viewer/logic.js`, `agent/concept_graph/viewer/tests/logic.test.js`
- Create: `agent/concept_graph/vendor_fetch.py`, `agent/concept_graph/viewer/vendor.lock.json`
- Create (by running the fetcher): `agent/concept_graph/viewer/vendor/cytoscape.min.js`, `katex.min.js`, `cytoscape.LICENSE`, `katex.LICENSE`
- Create: `tests/agent/concept_graph/test_cg_viewer_logic.py`, `tests/agent/concept_graph/test_cg_vendor_fetch.py`

**Interfaces:**
- Produces JS API on `self.CG` (browser) / `module.exports` (Node), all pure:
  - `edgeSentence(edge, nameOf) -> string`
  - `needsPairs(edge) -> [dependent, prerequisite][]`; `prerequisites(startId, edges) -> Set<string>` (cycle-safe)
  - `computeLayout(nodes, edges, sections, opts?) -> {[id]: {x, y}}` (later sections have smaller `y`, i.e. higher on screen)
  - `splitMath(text) -> {type: "text"|"inline"|"display", value}[]`
  - `filterNodes(nodes, f) -> node[]` where `f = {q, topics[], sections[], kinds[], statuses[]}` (empty array = no filter)
  - `decisionKey(d) -> string`; `recordDecision(decisions, d) -> decisions` (new array; replaces same-key decision; accept/reject on the same target are mutually exclusive)
  - `buildReview(graph, decisions, reviewerName, nowIso) -> reviewObject` (shape of spec "Review files")
  - `issueUrl(repo, review, maxLen = 6000) -> {url, prefilled}`
  - `safeStorage(win) -> {get(key) -> string|null, set(key, value) -> boolean}`
- Python: `vendor_fetch.fetch_all(vendor_dir: Path, lock_path: Path, opener=urllib.request.urlopen) -> None`.

- [ ] **Step 1: Write the failing JS tests**

`agent/concept_graph/viewer/tests/logic.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const CG = require("../logic.js");

const names = { a: "Alpha", b: "Beta", t: "Theorem T", c: "Gamma" };
const nameOf = (id) => names[id] || id;

test("edgeSentence reads naturally for each type and includes condition and via", () => {
  assert.equal(CG.edgeSentence({ type: "is_a", source: "a", target: "b", condition: "it is complete" }, nameOf),
    "Alpha is a Beta, that also: it is complete");
  assert.equal(CG.edgeSentence({ type: "is_a", source: "a", target: "b" }, nameOf), "Alpha is a Beta");
  assert.equal(CG.edgeSentence({ type: "has_property", source: "a", target: "b" }, nameOf), "Alpha has the property Beta");
  assert.equal(CG.edgeSentence({ type: "defined_on", source: "a", target: "b" }, nameOf), "Alpha is defined on Beta");
  assert.equal(CG.edgeSentence({ type: "component_of", source: "a", target: "b" }, nameOf),
    "Alpha is one of the conditions making up Beta");
  assert.equal(CG.edgeSentence({ type: "implies", source: "a", target: "b", condition: "x" }, nameOf), "Alpha implies Beta, when: x");
  assert.equal(CG.edgeSentence({ type: "iff", source: "a", target: "b", condition: "x", via: "t" }, nameOf),
    "Alpha holds exactly when Beta, given: x (via Theorem T)");
  assert.equal(CG.edgeSentence({ type: "hypothesis_of", source: "a", target: "t" }, nameOf), "Alpha is a hypothesis of Theorem T");
  assert.equal(CG.edgeSentence({ type: "yields", source: "t", target: "b" }, nameOf), "Theorem T yields Beta");
  assert.equal(CG.edgeSentence({ type: "counterexample_to", source: "a", target: "b" }, nameOf),
    "Alpha is a counterexample showing the converse of Beta fails");
});

const E = (source, type, target, extra = {}) => ({ source, type, target, ...extra });

test("prerequisites follows what each node needs, in the right direction for every type", () => {
  const edges = [
    E("total", "is_a", "partial"), // total needs partial
    E("partial", "has_property", "anti"), // partial needs anti
    E("partial", "hypothesis_of", "szp"), // szp needs partial
    E("szp", "yields", "total2"), // total2 needs szp
    E("al", "component_of", "bundle"), // bundle needs al
    E("bundle", "iff", "warp", { condition: "c" }), // each needs the other
  ];
  assert.deepEqual([...CG.prerequisites("total", edges)].sort(), ["anti", "partial"]);
  assert.deepEqual([...CG.prerequisites("total2", edges)].sort(), ["anti", "partial", "szp"]);
  assert.deepEqual([...CG.prerequisites("warp", edges)].sort(), ["al", "bundle", "warp"].filter((x) => x !== "warp"));
});

test("prerequisites is safe on cycles and never includes the start node", () => {
  const edges = [E("a", "implies", "b", { condition: "x" }), E("b", "implies", "a", { condition: "y" })];
  assert.deepEqual([...CG.prerequisites("a", edges)], ["b"]);
});

test("prerequisites treats via as a prerequisite of the conclusion", () => {
  const edges = [E("a", "implies", "b", { condition: "x", via: "t" })];
  assert.deepEqual([...CG.prerequisites("b", edges)].sort(), ["a", "t"]);
});

const sections = [{ id: "s1", order: 1 }, { id: "s2", order: 2 }];
const N = (id, section, name = id, topic = "x") => ({ id, section, name, topic });

test("computeLayout puts later sections higher, keeps a band together, and never overlaps nodes", () => {
  const nodes = [N("a1", "s1"), N("a2", "s1"), N("b1", "s2")];
  const pos = CG.computeLayout(nodes, [E("a1", "is_a", "b1")], sections);
  assert.ok(pos.b1.y < pos.a1.y, "later section is higher on screen");
  assert.equal(pos.a1.y, pos.a2.y);
  const keys = new Set(Object.values(pos).map((p) => `${p.x},${p.y}`));
  assert.equal(keys.size, 3);
});

test("computeLayout wraps a crowded band into rows and is deterministic", () => {
  const nodes = Array.from({ length: 12 }, (_, i) => N(`n${i}`, "s1", `Name ${String(i).padStart(2, "0")}`));
  const a = CG.computeLayout(nodes, [], sections, { perRow: 8 });
  const b = CG.computeLayout(nodes, [], sections, { perRow: 8 });
  assert.deepEqual(a, b);
  const ys = new Set(Object.values(a).map((p) => p.y));
  assert.equal(ys.size, 2);
});

test("splitMath finds inline and display math and keeps text in order", () => {
  assert.deepEqual(CG.splitMath("a $x$ b $$y$$ c"), [
    { type: "text", value: "a " }, { type: "inline", value: "x" }, { type: "text", value: " b " },
    { type: "display", value: "y" }, { type: "text", value: " c" },
  ]);
});

test("splitMath treats a lone dollar as text", () => {
  assert.deepEqual(CG.splitMath("costs $5 today"), [{ type: "text", value: "costs $5 today" }]);
});

test("filterNodes combines search with facet filters", () => {
  const nodes = [
    { id: "a", name: "Alpha", gist: "first", topic: "t1", section: "s1", kind: "axiom", status: "proposed" },
    { id: "b", name: "Beta", gist: "second", topic: "t2", section: "s2", kind: "object", status: "verified" },
  ];
  assert.equal(CG.filterNodes(nodes, { q: "", topics: [], sections: [], kinds: [], statuses: [] }).length, 2);
  assert.deepEqual(CG.filterNodes(nodes, { q: "SEC", topics: [], sections: [], kinds: [], statuses: [] }).map((n) => n.id), ["b"]);
  assert.deepEqual(CG.filterNodes(nodes, { q: "", topics: ["t1"], sections: [], kinds: [], statuses: ["proposed"] }).map((n) => n.id), ["a"]);
  assert.equal(CG.filterNodes(nodes, { q: "", topics: ["t1"], sections: [], kinds: [], statuses: ["verified"] }).length, 0);
});

test("recordDecision replaces the same decision and keeps accept and reject exclusive", () => {
  const t = { kind: "node", id: "n" };
  let d = CG.recordDecision([], { target: t, action: "accept" });
  d = CG.recordDecision(d, { target: t, action: "reject" });
  assert.deepEqual(d.map((x) => x.action), ["reject"]);
  d = CG.recordDecision(d, { target: t, action: "edit", field: "gist", base_hash: "h", new_value: "one" });
  d = CG.recordDecision(d, { target: t, action: "edit", field: "gist", base_hash: "h", new_value: "two" });
  assert.deepEqual(d.map((x) => x.action + ":" + (x.new_value || "")), ["reject:", "edit:two"]);
  d = CG.recordDecision(d, { target: t, action: "edit", field: "explanation", base_hash: "h2", new_value: "z" });
  assert.equal(d.length, 3);
});

test("buildReview has the shape apply-review expects", () => {
  const r = CG.buildReview({ graph_version: "abc123" }, [{ target: { kind: "node", id: "n" }, action: "accept" }], "Ada", "2026-10-20T00:00:00Z");
  assert.deepEqual(r, {
    schema_version: 1, graph_version: "abc123", reviewer: { name: "Ada" }, created: "2026-10-20T00:00:00Z",
    decisions: [{ target: { kind: "node", id: "n" }, action: "accept" }],
  });
});

test("issueUrl prefills a short review", () => {
  const review = CG.buildReview({ graph_version: "v" }, [], "Ada", "t");
  const { url, prefilled } = CG.issueUrl("me/graph", review);
  assert.equal(prefilled, true);
  assert.ok(url.startsWith("https://github.com/me/graph/issues/new?template=review.yml&title="));
  assert.ok(url.includes("&review="));
});

test("issueUrl falls back when the review is too long", () => {
  const decisions = Array.from({ length: 400 }, (_, i) => ({ target: { kind: "node", id: "n" + i }, action: "accept" }));
  const review = CG.buildReview({ graph_version: "v" }, decisions, "Ada", "t");
  const { url, prefilled } = CG.issueUrl("me/graph", review);
  assert.equal(prefilled, false);
  assert.ok(!url.includes("&review="));
  assert.ok(url.length < 500);
});

test("safeStorage survives a throwing localStorage", () => {
  const hostile = { get localStorage() { throw new Error("blocked"); } };
  const s = CG.safeStorage(hostile);
  assert.equal(s.get("k"), null);
  assert.equal(s.set("k", "v"), false);
});

test("safeStorage reads and writes through a working localStorage", () => {
  const mem = {};
  const win = { localStorage: { getItem: (k) => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = v; } } };
  const s = CG.safeStorage(win);
  assert.equal(s.set("k", "v"), true);
  assert.equal(s.get("k"), "v");
});
```

- [ ] **Step 2: Write the pytest wrappers and the vendor-fetch test**

`tests/agent/concept_graph/test_cg_viewer_logic.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

TEST_FILE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "viewer" / "tests" / "logic.test.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_viewer_logic_unit_tests_pass():
    result = subprocess.run(["node", "--test", str(TEST_FILE)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
```

`tests/agent/concept_graph/test_cg_vendor_fetch.py`:

```python
import hashlib
import json

import pytest

from agent.concept_graph.vendor_fetch import fetch_all


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


def make_lock(tmp_path, sha=None):
    lock = tmp_path / "vendor.lock.json"
    lock.write_text(json.dumps({"files": [{"file": "lib.js", "url": "https://example.test/lib.js", "sha256": sha}]}), encoding="utf-8")
    return lock


def test_first_fetch_records_the_hash(tmp_path):
    lock = make_lock(tmp_path)
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    fetch_all(vendor, lock, opener=lambda url: FakeResponse(b"console.log(1)"))
    assert (vendor / "lib.js").read_bytes() == b"console.log(1)"
    assert json.loads(lock.read_text(encoding="utf-8"))["files"][0]["sha256"] == hashlib.sha256(b"console.log(1)").hexdigest()


def test_a_changed_download_is_rejected(tmp_path):
    lock = make_lock(tmp_path, sha=hashlib.sha256(b"original").hexdigest())
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    with pytest.raises(ValueError, match="lib.js"):
        fetch_all(vendor, lock, opener=lambda url: FakeResponse(b"tampered"))
    assert not (vendor / "lib.js").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_viewer_logic.py tests/agent/concept_graph/test_cg_vendor_fetch.py -q`
Expected: FAIL (logic.js missing; `vendor_fetch` not importable).

- [ ] **Step 4: Write `viewer/logic.js`**

```js
(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CG = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SENTENCE = {
    is_a: function (s, t, c) { return s + " is a " + t + (c ? ", that also: " + c : ""); },
    has_property: function (s, t) { return s + " has the property " + t; },
    defined_on: function (s, t) { return s + " is defined on " + t; },
    component_of: function (s, t) { return s + " is one of the conditions making up " + t; },
    implies: function (s, t, c) { return s + " implies " + t + (c ? ", when: " + c : ""); },
    iff: function (s, t, c) { return s + " holds exactly when " + t + (c ? ", given: " + c : ""); },
    hypothesis_of: function (s, t) { return s + " is a hypothesis of " + t; },
    yields: function (s, t) { return s + " yields " + t; },
    counterexample_to: function (s, t) { return s + " is a counterexample showing the converse of " + t + " fails"; }
  };

  function edgeSentence(edge, nameOf) {
    var make = SENTENCE[edge.type];
    var text = make ? make(nameOf(edge.source), nameOf(edge.target), edge.condition) : nameOf(edge.source) + " - " + edge.type + " - " + nameOf(edge.target);
    if (edge.via) text += " (via " + nameOf(edge.via) + ")";
    return text;
  }

  // Each pair is [dependent, prerequisite]: "dependent" needs "prerequisite" to be understood.
  function needsPairs(e) {
    var pairs = [];
    switch (e.type) {
      case "is_a": case "has_property": case "defined_on":
        pairs.push([e.source, e.target]); break;
      case "component_of": case "hypothesis_of": case "yields":
        pairs.push([e.target, e.source]); break;
      case "implies":
        pairs.push([e.target, e.source]);
        if (e.via) pairs.push([e.target, e.via]);
        break;
      case "iff":
        pairs.push([e.target, e.source], [e.source, e.target]);
        if (e.via) pairs.push([e.target, e.via], [e.source, e.via]);
        break;
      default: break;
    }
    return pairs;
  }

  function prerequisites(startId, edges) {
    var prereq = new Map();
    edges.forEach(function (e) {
      needsPairs(e).forEach(function (p) {
        if (!prereq.has(p[0])) prereq.set(p[0], new Set());
        prereq.get(p[0]).add(p[1]);
      });
    });
    var seen = new Set();
    var stack = [startId];
    while (stack.length) {
      var id = stack.pop();
      (prereq.get(id) || []).forEach(function (p) {
        if (!seen.has(p)) { seen.add(p); stack.push(p); }
      });
    }
    seen.delete(startId);
    return seen;
  }

  function computeLayout(nodes, edges, sections, opts) {
    opts = opts || {};
    var dx = opts.dx || 190, dy = opts.dy || 240, rowGap = opts.rowGap || 90;
    var perRow = opts.perRow || 8, sweeps = opts.sweeps == null ? 4 : opts.sweeps;
    var orderOf = new Map(sections.map(function (s) { return [s.id, s.order]; }));
    var bands = Array.from(new Set(nodes.map(function (n) { return n.section; })))
      .sort(function (a, b) { return orderOf.get(a) - orderOf.get(b); });
    var bandIndex = new Map(bands.map(function (b, i) { return [b, i]; }));
    var byBand = bands.map(function () { return []; });
    nodes.slice()
      .sort(function (a, b) { return (a.topic + "|" + a.name).localeCompare(b.topic + "|" + b.name); })
      .forEach(function (n) { byBand[bandIndex.get(n.section)].push(n); });

    var x = new Map();
    function renorm() {
      byBand.forEach(function (list) {
        list.forEach(function (n, i) { x.set(n.id, (i + 0.5) / list.length); });
      });
    }
    renorm();
    var nbrs = new Map(nodes.map(function (n) { return [n.id, []]; }));
    edges.forEach(function (e) {
      if (nbrs.has(e.source) && nbrs.has(e.target)) {
        nbrs.get(e.source).push(e.target);
        nbrs.get(e.target).push(e.source);
      }
    });
    for (var k = 0; k < sweeps; k++) {
      byBand.forEach(function (list) {
        var key = new Map();
        list.forEach(function (n) {
          var ns = nbrs.get(n.id);
          var m = ns.length ? ns.reduce(function (acc, id) { return acc + x.get(id); }, 0) / ns.length : x.get(n.id);
          key.set(n.id, m);
        });
        list.sort(function (a, b) { return key.get(a.id) - key.get(b.id) || a.name.localeCompare(b.name); });
      });
      renorm();
    }

    var pos = {};
    var top = 0;
    byBand.forEach(function (list) {
      var rows = Math.max(1, Math.ceil(list.length / perRow));
      list.forEach(function (n, i) {
        var row = Math.floor(i / perRow);
        var inRow = Math.min(perRow, list.length - row * perRow);
        var col = i % perRow;
        pos[n.id] = { x: (col - (inRow - 1) / 2) * dx, y: -(top + row * rowGap) };
      });
      top += (rows - 1) * rowGap + dy;
    });
    return pos;
  }

  function splitMath(text) {
    var out = [];
    var re = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
    var last = 0, m;
    text = text || "";
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ type: "text", value: text.slice(last, m.index) });
      if (m[1] !== undefined) out.push({ type: "display", value: m[1].trim() });
      else out.push({ type: "inline", value: m[2] });
      last = re.lastIndex;
    }
    if (last < text.length) out.push({ type: "text", value: text.slice(last) });
    return out;
  }

  function filterNodes(nodes, f) {
    var q = (f.q || "").trim().toLowerCase();
    function ok(list, value) { return !list || list.length === 0 || list.indexOf(value) !== -1; }
    return nodes.filter(function (n) {
      if (q && (n.name + " " + (n.gist || "") + " " + n.id).toLowerCase().indexOf(q) === -1) return false;
      return ok(f.topics, n.topic) && ok(f.sections, n.section) && ok(f.kinds, n.kind) && ok(f.statuses, n.status);
    });
  }

  function decisionKey(d) {
    return [d.target.kind, d.target.id, d.action, d.field || ""].join("|");
  }

  function recordDecision(decisions, d) {
    var key = decisionKey(d);
    var exclusive = d.action === "accept" ? "reject" : d.action === "reject" ? "accept" : null;
    var kept = decisions.filter(function (x) {
      if (decisionKey(x) === key) return false;
      if (exclusive && x.target.kind === d.target.kind && x.target.id === d.target.id && x.action === exclusive) return false;
      return true;
    });
    kept.push(d);
    return kept;
  }

  function buildReview(graph, decisions, reviewerName, nowIso) {
    return {
      schema_version: 1,
      graph_version: graph.graph_version,
      reviewer: { name: reviewerName },
      created: nowIso,
      decisions: decisions
    };
  }

  function issueUrl(repo, review, maxLen) {
    maxLen = maxLen || 6000;
    var base = "https://github.com/" + repo + "/issues/new?template=review.yml&title=" +
      encodeURIComponent("Review: " + review.reviewer.name);
    var full = base + "&review=" + encodeURIComponent(JSON.stringify(review));
    return full.length <= maxLen ? { url: full, prefilled: true } : { url: base, prefilled: false };
  }

  function safeStorage(win) {
    function store() { try { return win.localStorage || null; } catch (e) { return null; } }
    return {
      get: function (key) { try { var s = store(); return s ? s.getItem(key) : null; } catch (e) { return null; } },
      set: function (key, value) { try { var s = store(); if (!s) return false; s.setItem(key, value); return true; } catch (e) { return false; } }
    };
  }

  return {
    edgeSentence: edgeSentence, needsPairs: needsPairs, prerequisites: prerequisites,
    computeLayout: computeLayout, splitMath: splitMath, filterNodes: filterNodes,
    decisionKey: decisionKey, recordDecision: recordDecision, buildReview: buildReview,
    issueUrl: issueUrl, safeStorage: safeStorage
  };
});
```

- [ ] **Step 5: Write `vendor_fetch.py` and `vendor.lock.json`**

`agent/concept_graph/vendor_fetch.py`:

```python
"""One-time downloader for the vendored viewer libraries (run by hand; output is committed)."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent / "viewer"


def fetch_all(vendor_dir: Path, lock_path: Path, opener=urllib.request.urlopen) -> None:
    """Download every file in the lock; verify known hashes, record unknown ones (trust on first use)."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    downloaded = []
    for entry in lock["files"]:
        data = opener(entry["url"]).read()
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") and entry["sha256"] != digest:
            raise ValueError(f"{entry['file']}: downloaded hash {digest} does not match the locked {entry['sha256']}")
        downloaded.append((entry, data, digest))
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for entry, data, digest in downloaded:
        (vendor_dir / entry["file"]).write_bytes(data)
        entry["sha256"] = digest
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    fetch_all(VIEWER_DIR / "vendor", VIEWER_DIR / "vendor.lock.json")
    print("vendored libraries written to", VIEWER_DIR / "vendor")
```

`agent/concept_graph/viewer/vendor.lock.json`:

```json
{
  "files": [
    {"file": "cytoscape.min.js", "url": "https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js", "sha256": null},
    {"file": "katex.min.js", "url": "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js", "sha256": null},
    {"file": "cytoscape.LICENSE", "url": "https://raw.githubusercontent.com/cytoscape/cytoscape.js/v3.30.2/LICENSE", "sha256": null},
    {"file": "katex.LICENSE", "url": "https://raw.githubusercontent.com/KaTeX/KaTeX/v0.16.11/LICENSE", "sha256": null}
  ]
}
```

- [ ] **Step 6: Run the tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_viewer_logic.py tests/agent/concept_graph/test_cg_vendor_fetch.py -q`
Expected: PASS (3 passed). If a JS assertion fails the pytest output includes Node's TAP diff; fix `logic.js`, not the test, unless the test contradicts the interfaces block above.

- [ ] **Step 7: Run the real fetch once and sanity-check the files (network, run by hand)**

```powershell
.\.venv\Scripts\python.exe -m agent.concept_graph.vendor_fetch
Get-ChildItem agent/concept_graph/viewer/vendor | Select-Object Name, Length
Select-String -Path agent/concept_graph/viewer/vendor/*.js -Pattern '</script' -SimpleMatch | Select-Object -First 3
```

Expected: four files; both `.js` files non-trivially large (cytoscape roughly 350-450 KB, katex roughly 250-300 KB); `.LICENSE` files start with "MIT" text. `Select-String` may print matches: that is fine, the build escapes `</script` (Task 6). If a URL 404s, the package or version path is wrong: look the version up on the package page, fix `vendor.lock.json`, and rerun. If the lock now holds hashes, re-running will verify them.

- [ ] **Step 8: Commit (including the vendored files and recorded hashes)**

```powershell
git add agent/concept_graph/viewer/logic.js agent/concept_graph/viewer/tests/logic.test.js agent/concept_graph/vendor_fetch.py agent/concept_graph/viewer/vendor.lock.json agent/concept_graph/viewer/vendor tests/agent/concept_graph/test_cg_viewer_logic.py tests/agent/concept_graph/test_cg_vendor_fetch.py
git diff --cached --stat
git commit -m "feat(concept_graph): viewer logic, vendored cytoscape and katex" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The viewer page (template, styles, app)

**Files:**
- Create: `agent/concept_graph/viewer/template.html`, `agent/concept_graph/viewer/style.css`, `agent/concept_graph/viewer/app.js`

**Interfaces:**
- Consumes: `self.CG` from `logic.js` (Task 4); `window.cytoscape` and `window.katex` from vendored libs; a `<script type="application/json" id="graph-data">` element holding the payload from `build.graph_payload` (Task 6): `{graph_version, sections[], nodes[], edges[], vocab, site}` where each node/edge also has `hashes: {field: hash}`.
- Template tokens (replaced by `build` in one pass): `{{{TITLE}}}`, `{{{STYLE}}}`, `{{{GRAPH}}}`, `{{{VENDOR}}}`, `{{{LOGIC}}}`, `{{{APP}}}`.
- Produces: no importable API. Verified manually in Task 6, Step 7.

This task has no automated test (there is no headless browser in this repo); its behaviour is checked by the manual checklist in Task 6 Step 7, after `build` can assemble the page.

- [ ] **Step 1: Write `viewer/template.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{{TITLE}}}</title>
<style>{{{STYLE}}}</style>
</head>
<body>
<header id="top">
  <h1 id="title"></h1>
  <div id="review-bar">
    <label>Your name <input id="reviewer" type="text" autocomplete="name" placeholder="for review credit"></label>
    <span id="decision-count" aria-live="polite">0 decisions</span>
    <button id="btn-submit" type="button">Submit review</button>
    <button id="btn-download" type="button">Download review</button>
    <button id="btn-clear" type="button" title="Forget all my pending decisions">Clear</button>
  </div>
</header>
<main id="layout">
  <aside id="sidebar" aria-label="Browse concepts">
    <input id="search" type="search" placeholder="Search concepts" aria-label="Search concepts">
    <div class="filters">
      <div id="f-topics" class="chips" aria-label="Topics"></div>
      <label>Status
        <select id="f-status"><option value="">All</option><option value="verified">Verified</option><option value="proposed">Proposed</option></select>
      </label>
      <label>Kind <select id="f-kind"><option value="">All</option></select></label>
      <div id="f-edges" class="chips" aria-label="Edge types"></div>
    </div>
    <details id="legend"><summary>How to read this</summary><div id="legend-body"></div></details>
    <nav id="name-list" aria-label="Concept list"></nav>
  </aside>
  <div id="cy" role="img" aria-label="Concept graph"></div>
  <section id="panel" aria-live="polite"><p class="hint">Click a concept or a connection to read about it.</p></section>
</main>
<div id="toast" role="status" hidden></div>
<script type="application/json" id="graph-data">{{{GRAPH}}}</script>
<script>{{{VENDOR}}}</script>
<script>{{{LOGIC}}}</script>
<script>{{{APP}}}</script>
</body>
</html>
```

- [ ] **Step 2: Write `viewer/style.css`**

```css
:root {
  --bg: #fafaf9; --fg: #1c1917; --muted: #57534e; --line: #d6d3d1; --card: #ffffff;
  --accent: #1d4ed8; --ok: #15803d; --bad: #b91c1c; --warn: #b45309;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1c1917; --fg: #fafaf9; --muted: #a8a29e; --line: #44403c; --card: #292524;
    --accent: #93c5fd; --ok: #4ade80; --bad: #f87171; --warn: #fbbf24;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; display: flex; flex-direction: column; }
#top { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 8px 16px; border-bottom: 1px solid var(--line); }
#top h1 { font-size: 1.1rem; margin: 0; flex: 1 1 220px; }
#review-bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
#review-bar input { padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--card); color: var(--fg); }
button { font: inherit; padding: 4px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--card); color: var(--fg); cursor: pointer; }
button:hover { border-color: var(--accent); }
button.primary { background: var(--accent); color: var(--bg); border-color: var(--accent); }
button.on { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 18%, var(--card)); }
#layout { flex: 1; min-height: 0; display: grid; grid-template-columns: 280px 1fr 380px; }
#sidebar, #panel { overflow: auto; padding: 12px; background: var(--card); }
#sidebar { border-right: 1px solid var(--line); }
#panel { border-left: 1px solid var(--line); }
#cy { min-height: 60vh; background: var(--bg); }
#search { width: 100%; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); }
.filters { display: grid; gap: 8px; margin: 10px 0; }
.filters label { display: flex; gap: 6px; align-items: center; color: var(--muted); }
.filters select { flex: 1; padding: 3px; background: var(--bg); color: var(--fg); border: 1px solid var(--line); border-radius: 6px; }
.chips { display: flex; flex-wrap: wrap; gap: 4px; }
.chips button { font-size: 0.8rem; padding: 2px 8px; }
#name-list h3 { margin: 14px 0 4px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
#name-list button { display: block; width: 100%; text-align: left; border: none; border-radius: 4px; background: transparent; padding: 3px 6px; }
#name-list button:hover, #name-list button.sel { background: color-mix(in srgb, var(--accent) 16%, var(--card)); }
#name-list .planned { opacity: 0.55; }
#panel h2 { margin: 0 0 4px; font-size: 1.25rem; }
.meta { color: var(--muted); font-size: 0.85rem; margin: 0 0 8px; }
.badge { display: inline-block; padding: 0 6px; border-radius: 10px; border: 1px solid var(--line); font-size: 0.75rem; }
.badge.verified { color: var(--ok); border-color: var(--ok); }
.badge.proposed { color: var(--warn); border-color: var(--warn); }
.badge.flag { color: var(--bad); border-color: var(--bad); }
.field { margin: 12px 0; }
.field h4 { margin: 0 0 2px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
.field p { margin: 4px 0; }
.field textarea { width: 100%; min-height: 110px; padding: 6px; background: var(--bg); color: var(--fg); border: 1px solid var(--accent); border-radius: 6px; font: inherit; }
.conn { list-style: none; padding: 0; margin: 0; }
.conn li { margin: 4px 0; }
.conn button { text-align: left; width: 100%; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.cite { color: var(--muted); font-size: 0.85rem; }
math { font-size: 1.05em; }
#toast { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); background: var(--fg); color: var(--bg); padding: 8px 14px; border-radius: 8px; max-width: 90vw; z-index: 10; }
.hint { color: var(--muted); }
@media (max-width: 1000px) {
  #layout { display: flex; flex-direction: column; overflow: auto; }
  #sidebar { border-right: none; border-bottom: 1px solid var(--line); max-height: 40vh; }
  #cy { height: 62vh; flex: none; }
  #panel { border-left: none; border-top: 1px solid var(--line); }
}
```

- [ ] **Step 3: Write `viewer/app.js`**

```js
(function () {
  "use strict";
  var CG = self.CG;
  var G = JSON.parse(document.getElementById("graph-data").textContent);
  var $ = function (sel) { return document.querySelector(sel); };
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var nodesById = new Map(G.nodes.map(function (n) { return [n.id, n]; }));
  var edgesById = new Map(G.edges.map(function (e) { return [e.id, e]; }));
  var sectionsById = new Map(G.sections.map(function (s) { return [s.id, s]; }));
  function nameOf(id) { var n = nodesById.get(id); return n ? n.name : id; }

  var storage = CG.safeStorage(window);
  var STORE_KEY = "cg-review-" + G.graph_version;
  var decisions = [];
  try { decisions = JSON.parse(storage.get(STORE_KEY) || "[]"); } catch (e) { decisions = []; }
  var reviewer = storage.get("cg-reviewer") || "";
  var selected = null; // {kind, id}
  var prereqMode = false;
  var editing = null; // field name being edited
  var filters = { q: "", topics: [], sections: [], kinds: [], statuses: [] };
  var hiddenEdgeTypes = new Set();

  // ---- rendering helpers ----------------------------------------------------
  function rich(text) {
    if (!text) return "";
    return "<p>" + CG.splitMath(text).map(function (p) {
      if (p.type === "text") return esc(p.value).replace(/\n\n+/g, "</p><p>").replace(/\n/g, "<br>");
      try {
        return window.katex.renderToString(p.value, { displayMode: p.type === "display", output: "mathml", throwOnError: false });
      } catch (e) { return "<code>" + esc(p.value) + "</code>"; }
    }).join("") + "</p>";
  }
  function toast(msg) {
    var t = $("#toast");
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.hidden = true; }, 6000);
  }
  function persist() {
    storage.set(STORE_KEY, JSON.stringify(decisions));
    $("#decision-count").textContent = decisions.length + (decisions.length === 1 ? " decision" : " decisions");
  }

  // ---- decisions ------------------------------------------------------------
  function item(kind, id) { return kind === "node" ? nodesById.get(id) : edgesById.get(id); }
  function decisionsFor(kind, id) {
    return decisions.filter(function (d) { return d.target.kind === kind && d.target.id === id; });
  }
  function effective(kind, id, field) {
    var d = decisionsFor(kind, id).filter(function (x) { return x.action === "edit" && x.field === field; })[0];
    return d ? d.new_value : item(kind, id)[field];
  }
  function decide(kind, id, action, extra) {
    var d = Object.assign({ target: { kind: kind, id: id }, action: action }, extra || {});
    decisions = CG.recordDecision(decisions, d);
    persist(); paintDecisions(); renderPanel();
  }
  function undecide(kind, id, action, field) {
    var key = CG.decisionKey({ target: { kind: kind, id: id }, action: action, field: field });
    decisions = decisions.filter(function (d) { return CG.decisionKey(d) !== key; });
    persist(); paintDecisions(); renderPanel();
  }

  // ---- graph ----------------------------------------------------------------
  var topicIndex = new Map(G.vocab.topics.map(function (t, i) { return [t, i]; }));
  function topicColor(t) { return "hsl(" + (((topicIndex.get(t) || 0) * 67 + 210) % 360) + ", 52%, 36%)"; }
  var EDGE_STYLE = {
    is_a: { color: "#64748b", arrow: "triangle-tee", label: "is a" },
    has_property: { color: "#0e7490", arrow: "vee", label: "has property" },
    defined_on: { color: "#4d7c0f", arrow: "vee", label: "defined on" },
    component_of: { color: "#a16207", arrow: "diamond", label: "part of" },
    implies: { color: "#1d4ed8", arrow: "triangle", label: "implies" },
    iff: { color: "#7e22ce", arrow: "triangle", label: "iff" },
    hypothesis_of: { color: "#be185d", arrow: "triangle", label: "hypothesis of" },
    yields: { color: "#be185d", arrow: "triangle", label: "yields" },
    counterexample_to: { color: "#b91c1c", arrow: "tee", label: "counterexample to" }
  };
  var pos = CG.computeLayout(G.nodes, G.edges, G.sections);
  var elements = G.nodes.map(function (n) {
    var sec = sectionsById.get(n.section);
    return {
      group: "nodes",
      data: { id: n.id, label: n.name, color: topicColor(n.topic), status: n.status },
      classes: sec && sec.state === "planned" ? "planned" : "",
      position: pos[n.id]
    };
  }).concat(G.edges.map(function (e) {
    var st = EDGE_STYLE[e.type] || EDGE_STYLE.is_a;
    return {
      group: "edges",
      data: { id: e.id, source: e.source, target: e.target, type: e.type, status: e.status, color: st.color, arrow: st.arrow, label: st.label }
    };
  }));

  var cy = cytoscape({
    container: $("#cy"),
    elements: elements,
    layout: { name: "preset" },
    wheelSensitivity: 0.25, minZoom: 0.08, maxZoom: 3,
    style: [
      { selector: "node", style: { "background-color": "data(color)", label: "data(label)", color: "#fff", "text-wrap": "wrap", "text-max-width": 170, "font-size": 13, "text-valign": "center", "text-halign": "center", shape: "round-rectangle", width: "label", height: "label", padding: "10px", "border-width": 2, "border-color": "data(color)" } },
      { selector: "node[status = 'proposed']", style: { "border-style": "dashed", "border-color": "#e7e5e4" } },
      { selector: "node.planned", style: { opacity: 0.4 } },
      { selector: "node.accepted", style: { "border-color": "#16a34a", "border-width": 4, "border-style": "solid" } },
      { selector: "node.rejected, edge.rejected", style: { opacity: 0.25 } },
      { selector: "node.faded, edge.faded", style: { opacity: 0.1 } },
      { selector: "node.hidden, edge.hidden", style: { display: "none" } },
      { selector: "node:selected", style: { "border-width": 4, "border-color": "#f59e0b", "border-style": "solid" } },
      { selector: "edge", style: { width: 2, "curve-style": "bezier", "line-color": "data(color)", "target-arrow-color": "data(color)", "target-arrow-shape": "data(arrow)", "arrow-scale": 1.2 } },
      { selector: "edge[status = 'proposed']", style: { "line-style": "dashed" } },
      { selector: "edge[type = 'iff']", style: { "source-arrow-shape": "triangle", "source-arrow-color": "data(color)" } },
      { selector: "edge.accepted", style: { width: 4 } },
      { selector: "edge.labelled", style: { label: "data(label)", "font-size": 11, color: "#111", "text-background-color": "#fff", "text-background-opacity": 0.92, "text-background-padding": 2, "text-rotation": "autorotate" } },
      { selector: "edge:selected", style: { width: 4, "line-color": "#f59e0b", "target-arrow-color": "#f59e0b" } }
    ]
  });
  cy.fit(undefined, 30);

  function paintDecisions() {
    cy.elements().removeClass("accepted rejected");
    decisions.forEach(function (d) {
      var el = cy.getElementById(d.target.id);
      if (!el.nonempty()) return;
      if (d.action === "accept") el.addClass("accepted");
      if (d.action === "reject") el.addClass("rejected");
    });
  }

  function applyFilters() {
    var visible = new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
    cy.nodes().forEach(function (n) { n.toggleClass("hidden", !visible.has(n.id())); });
    cy.edges().forEach(function (e) {
      var hide = hiddenEdgeTypes.has(e.data("type")) || !visible.has(e.data("source")) || !visible.has(e.data("target"));
      e.toggleClass("hidden", hide);
    });
    renderNameList(visible);
  }

  function applyPrereqMode() {
    cy.elements().removeClass("faded");
    if (!prereqMode || !selected || selected.kind !== "node") return;
    var keep = CG.prerequisites(selected.id, G.edges);
    keep.add(selected.id);
    cy.nodes().forEach(function (n) { if (!keep.has(n.id())) n.addClass("faded"); });
    cy.edges().forEach(function (e) { if (!(keep.has(e.data("source")) && keep.has(e.data("target")))) e.addClass("faded"); });
  }

  function select(kind, id, focus) {
    selected = { kind: kind, id: id }; editing = null;
    cy.elements().unselect();
    cy.edges().removeClass("labelled");
    var el = cy.getElementById(id);
    if (el.nonempty()) {
      el.select();
      if (kind === "node") el.connectedEdges().addClass("labelled");
      else el.addClass("labelled");
      if (focus) cy.animate({ center: { eles: el }, duration: 250 });
    }
    applyPrereqMode(); renderPanel(); renderNameList();
  }
  cy.on("tap", "node", function (ev) { select("node", ev.target.id(), false); });
  cy.on("tap", "edge", function (ev) { select("edge", ev.target.id(), false); });
  cy.on("tap", function (ev) { if (ev.target === cy) { selected = null; cy.elements().unselect(); cy.edges().removeClass("labelled"); applyPrereqMode(); renderPanel(); renderNameList(); } });

  // ---- sidebar --------------------------------------------------------------
  function renderNameList(visibleSet) {
    var visible = visibleSet || new Set(CG.filterNodes(G.nodes, filters).map(function (n) { return n.id; }));
    var html = "";
    G.sections.slice().sort(function (a, b) { return a.order - b.order; }).forEach(function (s) {
      var list = G.nodes.filter(function (n) { return n.section === s.id && visible.has(n.id); })
        .sort(function (a, b) { return a.name.localeCompare(b.name); });
      if (!list.length) return;
      html += "<h3>" + esc(s.title) + (s.state === "planned" ? " (planned)" : "") + "</h3>";
      list.forEach(function (n) {
        var cls = (s.state === "planned" ? "planned " : "") + (selected && selected.id === n.id ? "sel" : "");
        html += '<button type="button" class="' + cls + '" data-node="' + esc(n.id) + '">' + esc(n.name) + "</button>";
      });
    });
    $("#name-list").innerHTML = html || '<p class="hint">No concepts match.</p>';
  }
  $("#name-list").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-node]");
    if (b) select("node", b.getAttribute("data-node"), true);
  });

  function buildFilters() {
    var topics = $("#f-topics");
    topics.innerHTML = G.vocab.topics.map(function (t) { return '<button type="button" data-topic="' + esc(t) + '">' + esc(t) + "</button>"; }).join("");
    topics.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-topic]"); if (!b) return;
      var t = b.getAttribute("data-topic"), i = filters.topics.indexOf(t);
      if (i === -1) filters.topics.push(t); else filters.topics.splice(i, 1);
      b.classList.toggle("on", i === -1); applyFilters();
    });
    var kinds = Array.from(new Set(G.nodes.map(function (n) { return n.kind; }))).sort();
    $("#f-kind").insertAdjacentHTML("beforeend", kinds.map(function (k) { return '<option value="' + esc(k) + '">' + esc(k) + "</option>"; }).join(""));
    $("#f-kind").addEventListener("change", function (ev) { filters.kinds = ev.target.value ? [ev.target.value] : []; applyFilters(); });
    $("#f-status").addEventListener("change", function (ev) { filters.statuses = ev.target.value ? [ev.target.value] : []; applyFilters(); });
    $("#search").addEventListener("input", function (ev) { filters.q = ev.target.value; applyFilters(); });
    var used = Array.from(new Set(G.edges.map(function (e) { return e.type; })));
    $("#f-edges").innerHTML = used.map(function (t) { return '<button type="button" class="on" data-etype="' + t + '">' + esc(EDGE_STYLE[t].label) + "</button>"; }).join("");
    $("#f-edges").addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-etype]"); if (!b) return;
      var t = b.getAttribute("data-etype");
      if (hiddenEdgeTypes.has(t)) hiddenEdgeTypes.delete(t); else hiddenEdgeTypes.add(t);
      b.classList.toggle("on", !hiddenEdgeTypes.has(t)); applyFilters();
    });
    $("#legend-body").innerHTML =
      "<p>Boxes are concepts, coloured by topic; higher on the page means later in the course. A dashed outline means not yet reviewed. Faded boxes are in sections not taught yet.</p>" +
      "<p>Arrows read as sentences: select a concept to see every connection written out.</p><ul>" +
      Object.keys(EDGE_STYLE).map(function (t) { return '<li><span style="color:' + EDGE_STYLE[t].color + '">&#9632;</span> ' + esc(EDGE_STYLE[t].label) + "</li>"; }).join("") + "</ul>";
  }

  // ---- detail panel ---------------------------------------------------------
  function fieldBlock(kind, id, field, label) {
    var it = item(kind, id);
    var value = effective(kind, id, field);
    if (!value && editing !== field) {
      return '<div class="field"><h4>' + label + '<button type="button" data-act="edit" data-field="' + field + '">Add</button></h4></div>';
    }
    if (editing === field) {
      return '<div class="field"><h4>' + label + '</h4><textarea id="edit-box">' + esc(value || "") + '</textarea>' +
        '<div class="actions"><button type="button" class="primary" data-act="save-edit" data-field="' + field + '">Save edit</button>' +
        '<button type="button" data-act="cancel-edit">Cancel</button></div></div>';
    }
    var edited = decisionsFor(kind, id).some(function (d) { return d.action === "edit" && d.field === field; });
    return '<div class="field"><h4>' + label + (edited ? ' <span class="badge proposed">edited</span>' : "") +
      '<button type="button" data-act="edit" data-field="' + field + '">Edit</button></h4>' + rich(value) + "</div>";
  }
  function citations(it) {
    if (!it.citations || !it.citations.length) return "";
    return '<div class="field"><h4>Sources</h4><p class="cite">' + it.citations.map(function (c) { return esc(c.source + " " + c.ref); }).join(" &middot; ") + "</p></div>";
  }
  function criticBadge(it) {
    return it.critic && it.critic.verdict !== "supports"
      ? ' <span class="badge flag" title="' + esc(it.critic.note || "") + '">check: ' + esc(it.critic.verdict) + "</span>" : "";
  }
  function reviewControls(kind, id, it) {
    var mine = decisionsFor(kind, id);
    var acc = mine.some(function (d) { return d.action === "accept"; });
    var rej = mine.some(function (d) { return d.action === "reject"; });
    var cm = mine.filter(function (d) { return d.action === "comment"; })[0];
    return '<div class="field"><h4>Your review</h4><div class="actions">' +
      (it.status === "proposed" ? '<button type="button" class="' + (acc ? "on" : "") + '" data-act="accept">Accept</button>' +
        '<button type="button" class="' + (rej ? "on" : "") + '" data-act="reject">Reject</button>' : "") +
      "</div><textarea id=\"comment-box\" placeholder=\"Optional comment for the maintainer\" rows=\"2\" style=\"width:100%\">" + esc(cm ? cm.comment : "") + "</textarea>" +
      '<div class="actions"><button type="button" data-act="comment">Save comment</button></div></div>';
  }
  function renderPanel() {
    var p = $("#panel");
    if (!selected) { p.innerHTML = '<p class="hint">Click a concept or a connection to read about it.</p>'; return; }
    if (selected.kind === "node") return renderNode(p);
    return renderEdge(p);
  }
  function renderNode(p) {
    var n = nodesById.get(selected.id), sec = sectionsById.get(n.section);
    var conns = G.edges.filter(function (e) { return e.source === n.id || e.target === n.id || e.via === n.id; });
    p.innerHTML =
      "<h2>" + esc(n.name) + "</h2>" +
      '<p class="meta">' + esc(n.kind) + " &middot; " + esc(n.topic) + " &middot; " + esc(sec ? sec.title : n.section) +
      ' <span class="badge ' + n.status + '">' + n.status + "</span>" + criticBadge(n) + "</p>" +
      (n.gist ? '<p class="gist"><strong>' + esc(effective("node", n.id, "gist")) + "</strong></p>" : "") +
      '<div class="actions"><button type="button" class="' + (prereqMode ? "on" : "") + '" data-act="prereq">Show what this needs</button></div>' +
      fieldBlock("node", n.id, "explanation", "Explanation") +
      fieldBlock("node", n.id, "formal", "Formal statement") +
      fieldBlock("node", n.id, "example", "Example") +
      citations(n) +
      '<div class="field"><h4>Connections</h4><ul class="conn">' +
      (conns.map(function (e) { return '<li><button type="button" data-edge="' + esc(e.id) + '">' + esc(CG.edgeSentence(e, nameOf)) + "</button></li>"; }).join("") || "<li class=\"hint\">None yet.</li>") +
      "</ul></div>" + reviewControls("node", n.id, n);
  }
  function renderEdge(p) {
    var e = edgesById.get(selected.id);
    p.innerHTML =
      "<h2>" + esc(CG.edgeSentence(e, nameOf)) + "</h2>" +
      '<p class="meta">' + esc(EDGE_STYLE[e.type].label) + ' <span class="badge ' + e.status + '">' + e.status + "</span>" + criticBadge(e) + "</p>" +
      fieldBlock("edge", e.id, "condition", "Condition") +
      fieldBlock("edge", e.id, "explanation", "Why") +
      citations(e) +
      '<div class="actions"><button type="button" data-node="' + esc(e.source) + '">Go to ' + esc(nameOf(e.source)) + '</button>' +
      '<button type="button" data-node="' + esc(e.target) + '">Go to ' + esc(nameOf(e.target)) + "</button></div>" +
      reviewControls("edge", e.id, e);
  }

  $("#panel").addEventListener("click", function (ev) {
    var b = ev.target.closest("button"); if (!b) return;
    if (b.hasAttribute("data-edge")) return select("edge", b.getAttribute("data-edge"), true);
    if (b.hasAttribute("data-node")) return select("node", b.getAttribute("data-node"), true);
    var act = b.getAttribute("data-act"); if (!act || !selected) return;
    var kind = selected.kind, id = selected.id, field = b.getAttribute("data-field");
    if (act === "accept" || act === "reject") {
      var already = decisionsFor(kind, id).some(function (d) { return d.action === act; });
      return already ? undecide(kind, id, act) : decide(kind, id, act);
    }
    if (act === "prereq") { prereqMode = !prereqMode; applyPrereqMode(); return renderPanel(); }
    if (act === "edit") { editing = field; return renderPanel(); }
    if (act === "cancel-edit") { editing = null; return renderPanel(); }
    if (act === "save-edit") {
      var text = $("#edit-box").value;
      editing = null;
      return decide(kind, id, "edit", { field: field, base_hash: item(kind, id).hashes[field], new_value: text });
    }
    if (act === "comment") {
      var c = $("#comment-box").value.trim();
      return c ? decide(kind, id, "comment", { comment: c }) : undecide(kind, id, "comment");
    }
  });

  // ---- header: submit / download / clear -------------------------------------
  function needName() {
    if (reviewer.trim()) return true;
    $("#reviewer").focus(); toast("Please type your name first so your review can be credited.");
    return false;
  }
  function currentReview() { return CG.buildReview(G, decisions, reviewer.trim(), new Date().toISOString()); }
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return false; });
    }
    try {
      var ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
      var ok = document.execCommand("copy"); document.body.removeChild(ta); return Promise.resolve(ok);
    } catch (e) { return Promise.resolve(false); }
  }
  function download() {
    if (!needName() || !decisions.length) { if (!decisions.length) toast("Nothing to download yet: accept, reject, edit or comment first."); return; }
    var text = JSON.stringify(currentReview(), null, 2);
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    a.download = "review-" + reviewer.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); a.remove();
  }
  function submit() {
    if (!needName()) return;
    if (!decisions.length) return toast("Nothing to submit yet: accept, reject, edit or comment first.");
    var review = currentReview();
    var text = JSON.stringify(review, null, 2);
    var repo = G.site && G.site.repo;
    if (!repo) return toast("No GitHub repository is configured for this graph. Use Download review and send the file to the maintainer.");
    var res = CG.issueUrl(repo, review);
    copyText(text).then(function (copied) {
      window.open(res.url, "_blank", "noopener");
      toast(res.prefilled ? "A GitHub issue form opened with your review filled in. Press Submit new issue there."
        : copied ? "Your review is copied. Paste it into the box on the GitHub page that opened, then press Submit new issue."
          : "Could not copy automatically. Use Download review and attach the file to the GitHub issue.");
    });
  }
  $("#btn-submit").addEventListener("click", submit);
  $("#btn-download").addEventListener("click", download);
  $("#btn-clear").addEventListener("click", function () {
    if (decisions.length && !window.confirm("Forget all " + decisions.length + " pending decisions?")) return;
    decisions = []; persist(); paintDecisions(); renderPanel();
  });
  $("#reviewer").value = reviewer;
  $("#reviewer").addEventListener("input", function (ev) { reviewer = ev.target.value; storage.set("cg-reviewer", reviewer); });

  // ---- start ----------------------------------------------------------------
  $("#title").textContent = (G.site && G.site.title) || "Concept graph";
  buildFilters(); persist(); paintDecisions(); applyFilters();
  window.addEventListener("resize", function () { cy.resize(); });
})();
```

- [ ] **Step 4: Commit (the page is verified in Task 6 once `build` exists)**

```powershell
git add agent/concept_graph/viewer/template.html agent/concept_graph/viewer/style.css agent/concept_graph/viewer/app.js
git diff --cached --stat
git commit -m "feat(concept_graph): viewer template, styles and app" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `build` (graph.json + single-file HTML) and the CLI skeleton

**Files:**
- Create: `agent/concept_graph/build.py`, `agent/concept_graph/cli.py`, `agent/concept_graph/__main__.py`
- Create: `tests/agent/concept_graph/test_cg_build.py`, `tests/agent/concept_graph/test_cg_cli.py`

**Interfaces:**
- Consumes: `GraphStore.read_all`, `validate`, `errors`, `field_hash`, `EDITABLE_*` constants.
- Produces:
  - `BuildError(Exception)`
  - `graph_payload(graph: Graph) -> dict`: `{"graph_version": str(12 hex), "sections": [...ordered by order], "nodes": [...each with "hashes"], "edges": [... each with "hashes"], "vocab": {...}, "site": {...}}`
  - `build(root, vendor_dir=None) -> BuildResult` where `BuildResult` has `graph_json: Path`, `index_html: Path`, `graph_version: str`, `warnings: list[Issue]`. Writes `<root>/build/graph.json` and `<root>/index.html`. Raises `BuildError` listing all errors if validation fails.
  - `cli.main(argv: list[str] | None = None) -> int` with subcommands `validate` and `build` now (more added in Tasks 8 and 9); global option `--graph-repo PATH`.

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_build.py`:

```python
import json

import pytest

from agent.concept_graph.build import BuildError, build, graph_payload
from agent.concept_graph.schema import field_hash
from agent.concept_graph.store import GraphStore
from cg_helpers import copy_sample


@pytest.fixture
def vendor(tmp_path):
    d = tmp_path / "vendor"
    d.mkdir()
    (d / "cytoscape.min.js").write_text("/* cytoscape stub */", encoding="utf-8")
    (d / "katex.min.js").write_text("/* katex stub */", encoding="utf-8")
    return d


def test_payload_orders_sections_and_adds_field_hashes(tmp_path):
    g = GraphStore(copy_sample(tmp_path)).read_all()
    p = graph_payload(g)
    assert [s["id"] for s in p["sections"]] == ["s01-binary-relations", "s02-choice", "s03-demand"]
    node = next(n for n in p["nodes"] if n["id"] == "preorder")
    assert node["hashes"]["explanation"] == field_hash(node["explanation"])
    edge = next(e for e in p["edges"] if e["id"] == "preorder--is_a--binary-relation")
    assert edge["hashes"]["condition"] == field_hash("it is reflexive and transitive")
    assert len(p["graph_version"]) == 12


def test_version_changes_when_prose_changes(tmp_path):
    root = copy_sample(tmp_path)
    v1 = graph_payload(GraphStore(root).read_all())["graph_version"]
    GraphStore(root).update_item("node", "set", {"gist": "something else entirely"})
    v2 = graph_payload(GraphStore(root).read_all())["graph_version"]
    assert v1 != v2


def test_build_writes_graph_json_and_a_single_html_file(tmp_path, vendor):
    root = copy_sample(tmp_path)
    result = build(root, vendor_dir=vendor)
    data = json.loads(result.graph_json.read_text(encoding="utf-8"))
    html = result.index_html.read_text(encoding="utf-8")
    assert data["graph_version"] == result.graph_version
    assert result.graph_version in html
    assert "cytoscape stub" in html and "katex stub" in html
    assert "{{{" not in html
    assert "function edgeSentence" in html  # logic.js was inlined
    assert [w.code for w in result.warnings] == ["logical-cycle"]


def test_build_is_deterministic(tmp_path, vendor):
    root = copy_sample(tmp_path)
    first = build(root, vendor_dir=vendor).index_html.read_bytes()
    second = build(root, vendor_dir=vendor).index_html.read_bytes()
    assert first == second


def test_script_closer_in_prose_cannot_break_the_page(tmp_path, vendor):
    root = copy_sample(tmp_path)
    GraphStore(root).update_item("node", "set", {"explanation": "evil </script><script>alert(1)</script> and costs $5"})
    html = build(root, vendor_dir=vendor).index_html.read_text(encoding="utf-8")
    start = html.index('id="graph-data">') + len('id="graph-data">')
    end = html.index("</script>", start)
    payload = json.loads(html[start:end])  # still valid JSON up to the first real closer
    assert "alert(1)" in next(n for n in payload["nodes"] if n["id"] == "set")["explanation"]
    assert "</script><script>alert" not in html  # the closer was escaped to <\/script>


def test_build_refuses_a_graph_with_errors(tmp_path, vendor):
    root = copy_sample(tmp_path)
    GraphStore(root).update_item("edge", "binary-relation--defined_on--set", {"target": "nonexistent"})
    with pytest.raises(BuildError, match="dangling-endpoint"):
        build(root, vendor_dir=vendor)
    assert not (root / "index.html").exists()


def test_build_reports_missing_vendor_files(tmp_path):
    root = copy_sample(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(BuildError, match="vendor_fetch"):
        build(root, vendor_dir=empty)
```

`tests/agent/concept_graph/test_cg_cli.py`:

```python
from agent.concept_graph.cli import main
from cg_helpers import copy_sample


def test_validate_exits_zero_on_the_sample_and_prints_the_warning(tmp_path, capsys):
    root = copy_sample(tmp_path)
    assert main(["--graph-repo", str(root), "validate"]) == 0
    out = capsys.readouterr().out
    assert "0 error(s), 1 warning(s)" in out and "logical-cycle" in out


def test_validate_exits_one_when_there_are_errors(tmp_path, capsys):
    root = copy_sample(tmp_path)
    path = root / "data" / "edges" / "s02-choice.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("target: sen-alpha-beta", "target: nowhere", 1), encoding="utf-8")
    assert main(["--graph-repo", str(root), "validate"]) == 1
    assert "dangling-endpoint" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_build.py tests/agent/concept_graph/test_cg_cli.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.concept_graph.build`).

- [ ] **Step 3: Write `build.py`**

```python
"""Validate a graph repo and build graph.json plus a single self-contained index.html."""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .schema import EDITABLE_EDGE_FIELDS, EDITABLE_NODE_FIELDS, Graph, field_hash
from .store import GraphStore
from .validate import Issue, errors, validate

PACKAGE_DIR = Path(__file__).resolve().parent
VIEWER_DIR = PACKAGE_DIR / "viewer"
VENDOR_FILES = ("cytoscape.min.js", "katex.min.js")


class BuildError(Exception):
    pass


@dataclass
class BuildResult:
    graph_json: Path
    index_html: Path
    graph_version: str
    warnings: list[Issue]


def graph_payload(graph: Graph) -> dict:
    section_order = {s.id: s.order for s in graph.sections}
    sections = [s.model_dump(mode="json") for s in sorted(graph.sections, key=lambda s: s.order)]

    nodes = []
    for n in sorted(graph.nodes, key=lambda n: (section_order.get(n.section, 0), n.name.lower())):
        d = n.model_dump(mode="json", exclude_none=True)
        d["hashes"] = {f: field_hash(getattr(n, f)) for f in EDITABLE_NODE_FIELDS}
        nodes.append(d)

    edges = []
    for e in sorted(graph.edges, key=lambda e: e.id):
        d = e.model_dump(mode="json", exclude_none=True)
        d["hashes"] = {f: field_hash(getattr(e, f)) for f in EDITABLE_EDGE_FIELDS}
        edges.append(d)

    body = {
        "sections": sections,
        "nodes": nodes,
        "edges": edges,
        "vocab": graph.vocab.model_dump(mode="json"),
        "site": graph.site,
    }
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False)
    version = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return {"graph_version": version, **body}


def _script_safe(text: str) -> str:
    """Make text safe to place inside an inline <script> element."""
    return re.sub(r"</(script)", r"<\\/\1", text, flags=re.IGNORECASE)


def _read_vendor(vendor_dir: Path) -> str:
    parts = []
    for name in VENDOR_FILES:
        path = vendor_dir / name
        if not path.is_file():
            raise BuildError(f"missing vendored library {path}; run `python -m agent.concept_graph.vendor_fetch`")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n;\n".join(parts)


def build(root: str | Path, vendor_dir: str | Path | None = None) -> BuildResult:
    root = Path(root)
    graph = GraphStore(root).read_all()
    issues = validate(graph)
    bad = errors(issues)
    if bad:
        raise BuildError("graph has errors:\n" + "\n".join(f"  [{i.code}] {i.message}" for i in bad))

    payload = graph_payload(graph)
    vendor = _read_vendor(Path(vendor_dir) if vendor_dir else VIEWER_DIR / "vendor")
    graph_json_text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    inline_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    parts = {
        "TITLE": html.escape(str(graph.site.get("title") or "Concept graph")),
        "STYLE": (VIEWER_DIR / "style.css").read_text(encoding="utf-8"),
        "GRAPH": _script_safe(inline_json),
        "VENDOR": _script_safe(vendor),
        "LOGIC": _script_safe((VIEWER_DIR / "logic.js").read_text(encoding="utf-8")),
        "APP": _script_safe((VIEWER_DIR / "app.js").read_text(encoding="utf-8")),
    }
    template = (VIEWER_DIR / "template.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{\{(\w+)\}\}\}", lambda m: parts[m.group(1)], template)

    out_dir = root / "build"
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_json = out_dir / "graph.json"
    index_html = root / "index.html"
    graph_json.write_text(graph_json_text, encoding="utf-8", newline="\n")
    index_html.write_text(page, encoding="utf-8", newline="\n")
    return BuildResult(graph_json, index_html, payload["graph_version"], [i for i in issues if i.level == "warning"])
```

- [ ] **Step 4: Write `cli.py` and `__main__.py`**

`agent/concept_graph/cli.py`:

```python
"""Command line for the concept graph: python -m agent.concept_graph.cli --graph-repo PATH <command>."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import BuildError, build
from .store import GraphDataError, GraphStore
from .validate import errors, validate


def _cmd_validate(args) -> int:
    graph = GraphStore(args.graph_repo).read_all()
    issues = validate(graph)
    for i in issues:
        print(f"{i.level.upper():7} [{i.code}] {i.message}")
    bad = errors(issues)
    print(f"{len(bad)} error(s), {len(issues) - len(bad)} warning(s)")
    return 1 if bad else 0


def _cmd_build(args) -> int:
    result = build(args.graph_repo)
    for w in result.warnings:
        print(f"WARNING [{w.code}] {w.message}")
    print(f"built {result.index_html} and {result.graph_json} (graph_version {result.graph_version})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="concept_graph", description=__doc__)
    p.add_argument("--graph-repo", required=True, help="path to the graph repo checkout")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check the graph data; exit 1 on errors")
    sub.add_parser("build", help="write build/graph.json and index.html")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.graph_repo = Path(args.graph_repo)
    handlers = {"validate": _cmd_validate, "build": _cmd_build}
    try:
        return handlers[args.cmd](args)
    except (GraphDataError, BuildError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

`agent/concept_graph/__main__.py`:

```python
from .cli import main

raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_build.py tests/agent/concept_graph/test_cg_cli.py -q`
Expected: PASS (9 passed).

- [ ] **Step 6: Commit the code**

```powershell
git add agent/concept_graph/build.py agent/concept_graph/cli.py agent/concept_graph/__main__.py tests/agent/concept_graph/test_cg_build.py tests/agent/concept_graph/test_cg_cli.py
git diff --cached --stat
git commit -m "feat(concept_graph): build graph.json and single-file viewer, validate/build CLI" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Build the sample with the real libraries and check the page by hand**

```powershell
.\.venv\Scripts\python.exe -m agent.concept_graph.cli --graph-repo agent/concept_graph/sample_data build
Get-Item agent/concept_graph/sample_data/index.html | Select-Object Length
Start-Process agent/concept_graph/sample_data/index.html
```

Expected: a message ending `(graph_version <12 hex>)`; `index.html` roughly 0.7 to 1 MB. In the browser (try Chrome, then Firefox or Edge) confirm every line:

1. The title reads "Microeconomics concept graph"; the graph shows 17 boxes with names fully visible; "Walrasian demand" is faded at the top; the earliest section is at the bottom.
2. Dashed outlines on every box (all `proposed`); dashed arrows.
3. Click "Partial order": the right panel shows gist, explanation with rendered math (e.g. the `$X$` renders as math, no raw `$`), and a connections list written as sentences such as "Partial order is a Preorder, that also: it is also antisymmetric".
4. Click a connection: the panel switches to the edge with its condition and "Why".
5. Click "Show what this needs" on "Total order": unrelated boxes fade, leaving Partial order, Preorder, Binary relation, Set and the properties.
6. Search "choice": the name list and graph narrow to matching concepts; clear it to restore.
7. Toggle a topic chip and an edge-type chip: boxes/arrows hide and reappear.
8. Type a name; click Accept on a node; the counter reads "1 decision" and the box gets a green border; reload the page: the decision and name are still there. Click Edit on Explanation, change the text, Save edit: an "edited" badge appears.
9. Click Download review: a `review-<name>-<date>.json` file downloads; open it and confirm the shape in the spec (schema_version, graph_version, reviewer, decisions with `base_hash` on the edit).
10. Click Submit review: the toast says no GitHub repository is configured (the sample has `repo: null`). This is expected.
11. Narrow the window below 1000 px (or use devtools device mode): the layout stacks, no horizontal page scroll, the graph is still usable.
12. Open devtools console: no errors.

If any check fails, fix `app.js`/`style.css` (not the checklist), rebuild, and recheck all items. Then delete the generated files so the sample directory stays source-only:

```powershell
Remove-Item agent/concept_graph/sample_data/index.html
Remove-Item -Recurse agent/concept_graph/sample_data/build
git status --short
```

Expected: `git status --short` shows no changes except any real fixes to `app.js`/`style.css`; commit those with `git add agent/concept_graph/viewer/app.js agent/concept_graph/viewer/style.css` and message `fix(concept_graph): viewer fixes from manual check`.

---

### Task 7: Review files and `apply_review`

**Files:**
- Create: `agent/concept_graph/reviews.py`
- Create: `tests/agent/concept_graph/test_cg_reviews.py`

**Interfaces:**
- Consumes: `GraphStore` (Task 2), `field_hash`, `EDITABLE_*` (Task 1).
- Produces:
  - Models `Target(kind, id)`, `Decision(target, action, field, base_hash, new_value, comment)`, `Reviewer(name)`, `ReviewFile(schema_version, graph_version, reviewer, created, decisions)`; `ReviewFile.model_validate(dict)` is the parser.
  - `ApplyReport` dataclass: `applied: list[str]`, `conflicts: list[str]`, `skipped: list[str]`, `comments: list[str]`
  - `apply_review(store: GraphStore, review: ReviewFile, today: str) -> ApplyReport`. Side files in the graph repo root: `review-comments.md` and `review-conflicts.md` (appended).
  - `archive_review(root: Path, review: ReviewFile, today: str) -> Path` writes `reviews/applied/<today>-<slug>.json` (a numeric suffix is added if the name exists).

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_reviews.py`:

```python
import json

import pytest
from pydantic import ValidationError

from agent.concept_graph.reviews import ReviewFile, apply_review, archive_review
from agent.concept_graph.schema import field_hash
from agent.concept_graph.store import GraphStore
from cg_helpers import copy_sample

TODAY = "2026-10-20"


def review(name, *decisions, version="v1"):
    return ReviewFile.model_validate({
        "schema_version": 1, "graph_version": version, "reviewer": {"name": name},
        "created": "2026-10-20T10:00:00Z", "decisions": list(decisions),
    })


def node(g, node_id):
    return next(n for n in g.nodes if n.id == node_id)


def test_accept_marks_verified_and_credits_the_reviewer(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    rep = apply_review(store, review("Ada", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"}), TODAY)
    n = node(store.read_all(), "preorder")
    assert (n.status, n.reviewed_by, n.reviewed_on) == ("verified", "Ada", TODAY)
    assert len(rep.applied) == 1 and not rep.conflicts


def test_accepting_something_already_verified_is_skipped(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    d = {"target": {"kind": "node", "id": "preorder"}, "action": "accept"}
    apply_review(store, review("Ada", d), TODAY)
    rep = apply_review(store, review("Bo", d), TODAY)
    assert rep.skipped and not rep.applied
    assert node(store.read_all(), "preorder").reviewed_by == "Ada"


def test_edit_with_a_matching_base_hash_is_applied(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    old = node(store.read_all(), "preorder").gist
    d = {"target": {"kind": "node", "id": "preorder"}, "action": "edit", "field": "gist",
         "base_hash": field_hash(old), "new_value": "A reflexive, transitive relation."}
    apply_review(store, review("Ada", d), TODAY)
    n = node(store.read_all(), "preorder")
    assert n.gist == "A reflexive, transitive relation." and n.status == "verified"


def test_stale_edit_is_a_conflict_not_an_overwrite(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    d = {"target": {"kind": "node", "id": "preorder"}, "action": "edit", "field": "gist",
         "base_hash": field_hash("what the reviewer saw, long ago"), "new_value": "reviewer text"}
    before = node(store.read_all(), "preorder").gist
    rep = apply_review(store, review("Ada", d), TODAY)
    assert node(store.read_all(), "preorder").gist == before
    assert len(rep.conflicts) == 1 and not rep.applied
    text = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "Ada" in text and "preorder.gist" in text and "reviewer text" in text


def test_second_reviewer_same_field_conflicts(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    old = node(store.read_all(), "preorder").gist
    base = field_hash(old)
    first = {"target": {"kind": "node", "id": "preorder"}, "action": "edit", "field": "gist", "base_hash": base, "new_value": "Ada's wording"}
    second = {"target": {"kind": "node", "id": "preorder"}, "action": "edit", "field": "gist", "base_hash": base, "new_value": "Bo's wording"}
    apply_review(store, review("Ada", first), TODAY)
    rep = apply_review(store, review("Bo", second), TODAY)
    assert len(rep.conflicts) == 1
    assert node(store.read_all(), "preorder").gist == "Ada's wording"


def test_second_reviewer_making_the_identical_edit_is_not_a_conflict(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    base = field_hash(node(store.read_all(), "preorder").gist)
    same = {"target": {"kind": "node", "id": "preorder"}, "action": "edit", "field": "gist", "base_hash": base, "new_value": "Same words"}
    apply_review(store, review("Ada", same), TODAY)
    rep = apply_review(store, review("Bo", same), TODAY)
    assert not rep.conflicts and rep.skipped


def test_reject_edge_removes_it_and_leaves_a_tombstone(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    apply_review(store, review("Ada", {"target": {"kind": "edge", "id": "preorder--has_property--reflexivity"}, "action": "reject"}), TODAY)
    g = store.read_all()
    assert all(e.id != "preorder--has_property--reflexivity" for e in g.edges)
    assert [(r.kind, r.id) for r in g.rejected] == [("edge", "preorder--has_property--reflexivity")]


def test_reject_node_cascades_to_edges(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    apply_review(store, review("Ada", {"target": {"kind": "node", "id": "reflexivity"}, "action": "reject"}), TODAY)
    g = store.read_all()
    assert all(n.id != "reflexivity" for n in g.nodes)
    assert all("reflexivity" not in (e.source, e.target) for e in g.edges)
    tomb = {(r.kind, r.id) for r in g.rejected}
    assert ("node", "reflexivity") in tomb and ("edge", "preorder--has_property--reflexivity") in tomb


def test_comment_is_written_to_a_side_file_and_changes_no_data(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    before = store.read_all()
    rep = apply_review(store, review("Ada", {"target": {"kind": "node", "id": "warp"}, "action": "comment", "comment": "Check the domain condition."}), TODAY)
    assert store.read_all().nodes == before.nodes
    assert rep.comments and "Check the domain condition." in (store.root / "review-comments.md").read_text(encoding="utf-8")


def test_decision_for_a_missing_item_is_skipped_not_fatal(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    rep = apply_review(store, review("Ada", {"target": {"kind": "node", "id": "ghost"}, "action": "accept"}), TODAY)
    assert rep.skipped and not rep.applied


def test_invalid_review_files_are_rejected_by_the_model():
    with pytest.raises(ValidationError):  # edit without a base_hash
        review("Ada", {"target": {"kind": "node", "id": "n"}, "action": "edit", "field": "gist", "new_value": "x"})
    with pytest.raises(ValidationError):  # field that cannot be edited
        review("Ada", {"target": {"kind": "node", "id": "n"}, "action": "edit", "field": "kind", "base_hash": "h", "new_value": "x"})
    with pytest.raises(ValidationError):  # comment without text
        review("Ada", {"target": {"kind": "node", "id": "n"}, "action": "comment"})
    with pytest.raises(ValidationError):  # empty reviewer name
        review("", {"target": {"kind": "node", "id": "n"}, "action": "accept"})


def test_archive_review_copies_the_file_without_overwriting(tmp_path):
    root = copy_sample(tmp_path)
    r = review("Ada Lovelace", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"})
    first = archive_review(root, r, TODAY)
    second = archive_review(root, r, TODAY)
    assert first != second and first.parent == root / "reviews" / "applied"
    assert json.loads(first.read_text(encoding="utf-8"))["reviewer"]["name"] == "Ada Lovelace"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_reviews.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.concept_graph.reviews`).

- [ ] **Step 3: Write the implementation**

`agent/concept_graph/reviews.py`:

```python
"""Review files from the viewer, and merging them into the graph YAML without silent overwrites."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schema import EDITABLE_EDGE_FIELDS, EDITABLE_NODE_FIELDS, field_hash
from .store import GraphStore


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Target(_Model):
    kind: Literal["node", "edge"]
    id: str


class Decision(_Model):
    target: Target
    action: Literal["accept", "reject", "edit", "comment"]
    field: str | None = None
    base_hash: str | None = None
    new_value: str | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.action == "edit":
            allowed = EDITABLE_NODE_FIELDS if self.target.kind == "node" else EDITABLE_EDGE_FIELDS
            if self.field not in allowed:
                raise ValueError(f"cannot edit field {self.field!r} of a {self.target.kind}; allowed: {allowed}")
            if self.base_hash is None or self.new_value is None:
                raise ValueError("an edit needs base_hash and new_value")
        if self.action == "comment" and not (self.comment or "").strip():
            raise ValueError("a comment needs text")
        return self


class Reviewer(_Model):
    name: str = Field(min_length=1)


class ReviewFile(_Model):
    schema_version: Literal[1]
    graph_version: str
    reviewer: Reviewer
    created: str
    decisions: list[Decision]


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)


def _find(store: GraphStore, kind: str, item_id: str):
    graph = store.read_all()
    pool = graph.nodes if kind == "node" else graph.edges
    return next((i for i in pool if i.id == item_id), None)


def _append(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def apply_review(store: GraphStore, review: ReviewFile, today: str) -> ApplyReport:
    report = ApplyReport()
    who = review.reviewer.name
    for d in review.decisions:
        kind, item_id = d.target.kind, d.target.id
        label = f"{kind} {item_id}"
        current = _find(store, kind, item_id)
        if current is None:
            report.skipped.append(f"{label}: not found (the graph may have changed since the review was made)")
            continue

        if d.action == "accept":
            if current.status == "verified":
                report.skipped.append(f"{label}: already verified")
                continue
            store.update_item(kind, item_id, {"status": "verified", "reviewed_by": who, "reviewed_on": today})
            report.applied.append(f"{label}: accepted")

        elif d.action == "reject":
            if kind == "node":
                graph = store.read_all()
                for e in [e for e in graph.edges if item_id in (e.source, e.target)]:
                    store.remove_item("edge", e.id)
                    store.add_rejected("edge", e.id)
            store.remove_item(kind, item_id)
            store.add_rejected(kind, item_id)
            report.applied.append(f"{label}: rejected")

        elif d.action == "edit":
            existing = getattr(current, d.field)
            if field_hash(existing) == d.base_hash:
                store.update_item(kind, item_id, {d.field: d.new_value, "status": "verified", "reviewed_by": who, "reviewed_on": today})
                report.applied.append(f"{label}.{d.field}: edited")
            elif (d.new_value or "").strip() == (existing or "").strip():
                report.skipped.append(f"{label}.{d.field}: already has this value")
            else:
                msg = (f"{who} {today}: {label}.{d.field}: the field changed since the review was made "
                       f"(reviewer saw {d.base_hash}, now {field_hash(existing)}); proposed text: {d.new_value!r}")
                _append(store.root / "review-conflicts.md", "- " + msg)
                report.conflicts.append(msg)

        elif d.action == "comment":
            _append(store.root / "review-comments.md", f"- {who} {today} on {label}: {d.comment.strip()}")
            report.comments.append(f"{label}: comment recorded")
    return report


def archive_review(root: Path, review: ReviewFile, today: str) -> Path:
    folder = Path(root) / "reviews" / "applied"
    folder.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", review.reviewer.name.lower()).strip("-") or "reviewer"
    path = folder / f"{today}-{slug}.json"
    n = 2
    while path.exists():
        path = folder / f"{today}-{slug}-{n}.json"
        n += 1
    path.write_text(json.dumps(review.model_dump(mode="json", exclude_none=True), indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_reviews.py -q`
Expected: PASS (13 passed).

- [ ] **Step 5: Commit**

```powershell
git add agent/concept_graph/reviews.py tests/agent/concept_graph/test_cg_reviews.py
git diff --cached --stat
git commit -m "feat(concept_graph): review files and conflict-safe apply_review" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: GitHub issue intake and the `apply-review` command

**Files:**
- Create: `agent/concept_graph/gh_issues.py`
- Modify: `agent/concept_graph/cli.py` (add the `apply-review` subcommand)
- Create: `tests/agent/concept_graph/test_cg_gh_issues.py`
- Modify: `tests/agent/concept_graph/test_cg_cli.py` (append tests)

**Interfaces:**
- Consumes: `ReviewFile`, `apply_review`, `archive_review` (Task 7).
- Produces:
  - `extract_review_json(body: str) -> dict` (accepts a ```json fenced block, any fenced block, or a bare JSON body; raises `ValueError` otherwise)
  - `fetch_review_issues(repo: str, run=subprocess.run) -> tuple[list[tuple[int, ReviewFile]], list[str]]` (parsed reviews with issue numbers, plus error strings for issues that could not be parsed)
  - `close_issue(repo: str, number: int, run=subprocess.run) -> None`
  - CLI: `apply-review [FILES...] [--from-issues OWNER/REPO] [--commit] [--close-applied] [--today YYYY-MM-DD]`. Exit 0 if all inputs parsed (conflicts still exit 0 and are printed), 1 if any input failed to parse.

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_gh_issues.py`:

```python
import json
import subprocess

import pytest

from agent.concept_graph.gh_issues import close_issue, extract_review_json, fetch_review_issues

REVIEW = {"schema_version": 1, "graph_version": "v", "reviewer": {"name": "Ada"}, "created": "t",
          "decisions": [{"target": {"kind": "node", "id": "preorder"}, "action": "accept"}]}


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_extract_from_a_json_fence_a_plain_fence_and_a_bare_body():
    raw = json.dumps(REVIEW)
    assert extract_review_json(f"### Review\n\n```json\n{raw}\n```\n") == REVIEW
    assert extract_review_json(f"### Review\n\n```\n{raw}\n```\n") == REVIEW
    assert extract_review_json(raw) == REVIEW


def test_extract_rejects_non_json():
    with pytest.raises(ValueError):
        extract_review_json("hello, I forgot to paste anything")


def test_fetch_parses_good_issues_and_reports_bad_ones():
    issues = [{"number": 7, "body": "```json\n" + json.dumps(REVIEW) + "\n```"}, {"number": 8, "body": "oops"}]
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return completed(json.dumps(issues))

    reviews, problems = fetch_review_issues("me/graph", run=run)
    assert [n for n, _ in reviews] == [7] and reviews[0][1].reviewer.name == "Ada"
    assert len(problems) == 1 and "#8" in problems[0]
    assert calls[0][:3] == ["gh", "issue", "list"] and "me/graph" in calls[0] and "review" in calls[0]


def test_fetch_raises_when_gh_fails():
    with pytest.raises(RuntimeError, match="gh"):
        fetch_review_issues("me/graph", run=lambda cmd, **kw: completed("", returncode=1))


def test_close_issue_calls_gh():
    calls = []
    close_issue("me/graph", 7, run=lambda cmd, **kw: calls.append(cmd) or completed())
    assert calls[0][:3] == ["gh", "issue", "close"] and "7" in calls[0]
```

Append to `tests/agent/concept_graph/test_cg_cli.py`:

```python
import json
import subprocess

from agent.concept_graph.schema import field_hash
from agent.concept_graph.store import GraphStore


def write_review(path, *decisions, name="Ada"):
    path.write_text(json.dumps({
        "schema_version": 1, "graph_version": "v", "reviewer": {"name": name},
        "created": "2026-10-20T10:00:00Z", "decisions": list(decisions),
    }), encoding="utf-8")
    return path


def test_apply_review_from_a_file_updates_the_graph_and_archives_it(tmp_path, capsys):
    root = copy_sample(tmp_path)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"})
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--today", "2026-10-20"]) == 0
    assert "1 applied" in capsys.readouterr().out
    node = next(n for n in GraphStore(root).read_all().nodes if n.id == "preorder")
    assert node.status == "verified"
    assert list((root / "reviews" / "applied").glob("*.json"))


def test_apply_review_reports_conflicts_but_exits_zero(tmp_path, capsys):
    root = copy_sample(tmp_path)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "edit",
                                            "field": "gist", "base_hash": field_hash("stale"), "new_value": "x"})
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--today", "2026-10-20"]) == 0
    out = capsys.readouterr().out
    assert "1 conflict" in out and "review-conflicts.md" in out


def test_apply_review_exits_one_on_an_unparseable_file(tmp_path):
    root = copy_sample(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["--graph-repo", str(root), "apply-review", str(bad)]) == 1


def test_apply_review_commit_makes_one_commit_per_reviewer(tmp_path):
    root = copy_sample(tmp_path)
    for cmd in (["init", "-q"], ["config", "user.email", "t@example.test"], ["config", "user.name", "Test"], ["add", "."], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"}, name="Ada")
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--commit", "--today", "2026-10-20"]) == 0
    log = subprocess.run(["git", "-C", str(root), "log", "--format=%s"], capture_output=True, text=True, check=True).stdout.split("\n")
    assert log[0] == "review: apply Ada"
    status = subprocess.run(["git", "-C", str(root), "status", "--short"], capture_output=True, text=True, check=True).stdout
    assert status.strip() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_gh_issues.py tests/agent/concept_graph/test_cg_cli.py -q`
Expected: FAIL (`gh_issues` missing; `apply-review` not a subcommand).

- [ ] **Step 3: Write `gh_issues.py`**

```python
"""Read submitted reviews from GitHub issues through the `gh` CLI."""
from __future__ import annotations

import json
import re
import subprocess

from pydantic import ValidationError

from .reviews import ReviewFile

_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def extract_review_json(body: str) -> dict:
    """Pull the review JSON out of an issue body (fenced by the issue form, or pasted bare)."""
    m = _FENCE.search(body or "")
    text = m.group(1) if m else (body or "")
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"no review JSON found: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("review JSON must be an object")
    return data


def fetch_review_issues(repo: str, run=subprocess.run) -> tuple[list[tuple[int, ReviewFile]], list[str]]:
    cmd = ["gh", "issue", "list", "--repo", repo, "--label", "review", "--state", "open",
           "--json", "number,body", "--limit", "100"]
    result = run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh issue list failed for {repo}: {result.stderr.strip() or 'no output'}")
    reviews: list[tuple[int, ReviewFile]] = []
    problems: list[str] = []
    for issue in json.loads(result.stdout or "[]"):
        number = issue["number"]
        try:
            reviews.append((number, ReviewFile.model_validate(extract_review_json(issue.get("body", "")))))
        except (ValueError, ValidationError) as exc:
            problems.append(f"issue #{number}: {exc}")
    return reviews, problems


def close_issue(repo: str, number: int, run=subprocess.run) -> None:
    result = run(["gh", "issue", "close", str(number), "--repo", repo, "--comment", "Applied to the graph. Thank you for the review."],
                 capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh issue close #{number} failed: {result.stderr.strip()}")
```

- [ ] **Step 4: Add the `apply-review` command to `cli.py`**

Add these imports at the top of `agent/concept_graph/cli.py` (merge with the existing import block):

```python
import datetime as dt
import json
import subprocess

from pydantic import ValidationError

from .gh_issues import close_issue, fetch_review_issues
from .reviews import ReviewFile, apply_review, archive_review
```

Add this function above `build_parser`:

```python
def _git_commit(root: Path, who: str) -> None:
    paths = [p for p in ("data", "review-comments.md", "review-conflicts.md", "reviews") if (root / p).exists()]
    subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True, capture_output=True)
    done = subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", f"review: apply {who}"], capture_output=True, text=True)
    if done.returncode != 0:
        print(f"note: nothing committed for {who} ({done.stdout.strip() or done.stderr.strip()})")


def _cmd_apply_review(args) -> int:
    store = GraphStore(args.graph_repo)
    today = args.today or dt.date.today().isoformat()
    inputs: list[tuple[str, ReviewFile, int | None]] = []
    failed = False
    for name in args.files:
        try:
            inputs.append((name, ReviewFile.model_validate(json.loads(Path(name).read_text(encoding="utf-8"))), None))
        except (OSError, ValueError, ValidationError) as exc:
            print(f"error: {name}: {exc}", file=sys.stderr)
            failed = True
    if args.from_issues:
        found, problems = fetch_review_issues(args.from_issues)
        inputs.extend((f"issue #{n}", review, n) for n, review in found)
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
            failed = True

    for label, review, issue_number in inputs:
        report = apply_review(store, review, today)
        archive_review(args.graph_repo, review, today)
        print(f"{label} ({review.reviewer.name}): {len(report.applied)} applied, {len(report.conflicts)} conflict(s), "
              f"{len(report.skipped)} skipped, {len(report.comments)} comment(s)")
        for line in report.applied + report.skipped:
            print("   ", line)
        if report.conflicts:
            print(f"    conflicts need your decision: see {args.graph_repo / 'review-conflicts.md'}")
        if args.commit:
            _git_commit(args.graph_repo, review.reviewer.name)
        if args.close_applied and issue_number is not None:
            close_issue(args.from_issues, issue_number)
    return 1 if failed else 0
```

Extend `build_parser` (add before `return p`):

```python
    ar = sub.add_parser("apply-review", help="merge review files or GitHub review issues into the graph")
    ar.add_argument("files", nargs="*", help="review JSON files downloaded from the viewer")
    ar.add_argument("--from-issues", metavar="OWNER/REPO", help="also read open issues labelled 'review' via gh")
    ar.add_argument("--commit", action="store_true", help="commit the result in the graph repo, one commit per reviewer")
    ar.add_argument("--close-applied", action="store_true", help="close each GitHub issue after applying it")
    ar.add_argument("--today", help="override today's date (YYYY-MM-DD), for tests")
```

and register the handler in `main`:

```python
    handlers = {"validate": _cmd_validate, "build": _cmd_build, "apply-review": _cmd_apply_review}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_gh_issues.py tests/agent/concept_graph/test_cg_cli.py -q`
Expected: PASS (5 + 6 = 11 passed). If the commit test fails with "pathspec" errors, ensure `reviews/` is created before `git add` (it is, by `archive_review`, which runs before `_git_commit`).

- [ ] **Step 6: Commit**

```powershell
git add agent/concept_graph/gh_issues.py agent/concept_graph/cli.py tests/agent/concept_graph/test_cg_gh_issues.py tests/agent/concept_graph/test_cg_cli.py
git diff --cached --stat
git commit -m "feat(concept_graph): apply-review command and GitHub issue intake" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: `scaffold` the graph repo (license, notice, issue template)

**Files:**
- Create: `agent/concept_graph/scaffold.py`
- Modify: `agent/concept_graph/cli.py` (add `scaffold` subcommand)
- Create: `tests/agent/concept_graph/test_cg_scaffold.py`

**Interfaces:**
- Consumes: `agent/concept_graph/sample_data` (Task 2).
- Produces: `scaffold(root: Path, repo: str, holder: str, year: int, with_sample: bool = False, contact: str | None = None, fetch_text=fetch_url_text) -> list[str]` returning created relative paths; raises `FileExistsError` listing any target file that already exists (nothing is written in that case). CLI: `scaffold --repo OWNER/NAME --holder "Full Name" [--with-sample] [--contact TEXT]`.
- Files written in the graph repo: `README.md`, `NOTICE.md`, `LICENSE` (CC BY-NC-SA 4.0 legal code, fetched), `LICENSE-CODE` (MIT), `.gitignore`, `.github/ISSUE_TEMPLATE/review.yml`, `config/vocab.yaml`, `config/site.yaml` (with `repo` set), `data/sections.yaml` (`[]`), `data/rejected.yaml` (`[]`), `data/nodes/.gitkeep`, `data/edges/.gitkeep`; with `--with-sample`, the sample sections/nodes/edges/vocab replace the empty ones (but `site.yaml` keeps the real repo).

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_scaffold.py`:

```python
import pytest
import yaml

from agent.concept_graph.build import build
from agent.concept_graph.cli import main
from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.store import GraphStore


def fake_fetch(url):
    return "FAKE CC BY-NC-SA 4.0 LEGAL CODE from " + url


def run(tmp_path, **kw):
    root = tmp_path / "new-graph"
    created = scaffold(root, "someone/microecon-concept-graph", "Some One", 2026, fetch_text=fake_fetch, **kw)
    return root, created


def test_scaffold_writes_the_expected_files(tmp_path):
    root, created = run(tmp_path)
    for rel in ["README.md", "NOTICE.md", "LICENSE", "LICENSE-CODE", ".gitignore", ".github/ISSUE_TEMPLATE/review.yml",
                "config/vocab.yaml", "config/site.yaml", "data/sections.yaml", "data/rejected.yaml"]:
        assert (root / rel).is_file(), rel
        assert rel in created
    assert "FAKE CC BY-NC-SA" in (root / "LICENSE").read_text(encoding="utf-8")
    mit = (root / "LICENSE-CODE").read_text(encoding="utf-8")
    assert "MIT License" in mit and "2026 Some One" in mit


def test_issue_template_is_a_form_with_a_json_review_box(tmp_path):
    root, _ = run(tmp_path)
    form = yaml.safe_load((root / ".github/ISSUE_TEMPLATE/review.yml").read_text(encoding="utf-8"))
    assert form["labels"] == ["review"]
    box = form["body"][0]
    assert box["id"] == "review" and box["type"] == "textarea" and box["attributes"]["render"] == "json"


def test_notice_states_the_non_commercial_independent_status_and_defaults_the_contact_to_issues(tmp_path):
    root, _ = run(tmp_path)
    text = (root / "NOTICE.md").read_text(encoding="utf-8").lower()
    for phrase in ["independent", "non-commercial", "not affiliated", "takedown", "https://github.com/someone/microecon-concept-graph/issues"]:
        assert phrase in text
    assert "@" not in text  # no email address is published unless the owner passes --contact


def test_site_config_carries_the_repo_for_the_viewer(tmp_path):
    root, _ = run(tmp_path)
    assert yaml.safe_load((root / "config/site.yaml").read_text(encoding="utf-8"))["repo"] == "someone/microecon-concept-graph"


def test_refuses_to_overwrite_and_writes_nothing(tmp_path):
    root, _ = run(tmp_path)
    (root / "NOTICE.md").write_text("mine", encoding="utf-8")
    with pytest.raises(FileExistsError, match="NOTICE.md"):
        scaffold(root, "someone/x", "Some One", 2026, fetch_text=fake_fetch)
    assert (root / "NOTICE.md").read_text(encoding="utf-8") == "mine"


def test_with_sample_gives_a_buildable_graph_that_keeps_the_real_repo(tmp_path):
    root, _ = run(tmp_path, with_sample=True)
    graph = GraphStore(root).read_all()
    assert len(graph.nodes) == 17 and graph.site["repo"] == "someone/microecon-concept-graph"
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "cytoscape.min.js").write_text("/*c*/", encoding="utf-8")
    (vendor / "katex.min.js").write_text("/*k*/", encoding="utf-8")
    assert build(root, vendor_dir=vendor).index_html.is_file()


def test_an_empty_scaffold_validates_cleanly(tmp_path):
    root, _ = run(tmp_path)
    assert main(["--graph-repo", str(root), "validate"]) == 0


def test_cli_scaffold_command(tmp_path, monkeypatch):
    import agent.concept_graph.scaffold as sc
    monkeypatch.setattr(sc, "fetch_url_text", fake_fetch)
    root = tmp_path / "via-cli"
    code = main(["--graph-repo", str(root), "scaffold", "--repo", "someone/g", "--holder", "Some One"])
    assert code == 0 and (root / "NOTICE.md").is_file()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_scaffold.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.concept_graph.scaffold`).

- [ ] **Step 3: Write `scaffold.py`**

```python
"""Create the skeleton of a new public graph repo (docs, licenses, issue form, empty data)."""
from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

SAMPLE = Path(__file__).resolve().parent / "sample_data"
CC_LEGALCODE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt"

MIT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

README = """# Microeconomics concept graph

An interactive study aid: a map of the key concepts in a graduate microeconomic theory course, from binary
relations up through consumer demand, showing how the ideas connect, which results imply or are equivalent to
which, and under what conditions.

**Open it:** https://{owner}.github.io/{name}/

## How to read it

Select a concept to read what it is, what it needs, and what it leads to. Every connection is written out as a
sentence. "Show what this needs" fades everything except a concept's prerequisites. A dashed outline means an
item has not been reviewed yet.

## How to help review it

1. Open the page, type your name, and accept, reject or edit items as you read.
2. Press **Submit review**. A GitHub issue form opens with your review filled in (or copied to your clipboard to
   paste); press **Submit new issue**. You need a free GitHub account. Without one, use **Download review** and
   send the file to the maintainer.

Reviews are applied by the maintainer; nothing you do in the page changes the shared graph directly.

## What is in this repository

- `data/`: the graph as YAML (sections, nodes, edges).
- `build/graph.json` and `index.html`: the built viewer, served by GitHub Pages.
- `reviews/applied/`: reviews that have been merged.
- Content is original wording with citations; see `NOTICE.md` and the licenses.
"""

NOTICE = """# Notice

This is an independent, educational, non-commercial student project.

- It is **not affiliated with, endorsed by, or sponsored by** any textbook author, publisher, instructor or
  university.
- Sources are **cited for orientation only** (for example a chapter or section number). No text from any source
  is reproduced; explanations are written in the project's own words, and quoted text is not used.
- The content (text and data) is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**
  (see `LICENSE`). The viewer code is licensed under the **MIT License** (see `LICENSE-CODE`).
- Nothing here is professional or legal advice, and it may contain mistakes: items marked as not yet reviewed
  have not been checked by a person.

## Takedown and corrections

If you hold rights in something you believe appears here, or you spot an error, please contact: {contact}.
We will respond promptly and remove or correct the material.
"""

ISSUE_FORM = """name: Submit a review
description: Paste the review copied from the viewer. Do not edit it.
title: "Review: "
labels: ["review"]
body:
  - type: textarea
    id: review
    attributes:
      label: Review
      description: Paste the text the viewer copied to your clipboard.
      render: json
    validations:
      required: true
"""

VOCAB = """kinds: [object, structure, property, axiom, definition, theorem, lemma, model, function, correspondence, identity, technique, example]
topics: [order-theory, rational-choice, revealed-preference, demand]
"""


def fetch_url_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def scaffold(root: Path, repo: str, holder: str, year: int, with_sample: bool = False,
             contact: str | None = None, fetch_text=None) -> list[str]:
    fetch_text = fetch_text or fetch_url_text
    root = Path(root)
    owner, name = repo.split("/", 1)
    contact = contact or f"open an issue at https://github.com/{repo}/issues"
    files: dict[str, str] = {
        "README.md": README.format(owner=owner, name=name),
        "NOTICE.md": NOTICE.format(contact=contact),
        "LICENSE": fetch_text(CC_LEGALCODE_URL),
        "LICENSE-CODE": MIT.format(year=year, holder=holder),
        ".gitignore": ".venv/\n__pycache__/\n*.pyc\nwork/\n",
        ".github/ISSUE_TEMPLATE/review.yml": ISSUE_FORM,
        "config/vocab.yaml": VOCAB,
        "config/site.yaml": f"title: Microeconomics concept graph\nrepo: {repo}\n",
        "data/sections.yaml": "[]\n",
        "data/rejected.yaml": "[]\n",
        "data/nodes/.gitkeep": "",
        "data/edges/.gitkeep": "",
    }
    clashes = [rel for rel in files if (root / rel).exists()]
    if clashes:
        raise FileExistsError("refusing to overwrite existing files: " + ", ".join(sorted(clashes)))
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    created = sorted(files)
    if with_sample:
        shutil.copytree(SAMPLE, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("site.yaml"))
        created += ["(sample sections, nodes and edges copied in)"]
    return created
```

Note: `scaffold` resolves `fetch_url_text` at call time through the module global so the CLI test can monkeypatch it. In `scaffold`, the line `fetch_text = fetch_text or fetch_url_text` reads the module global each call.

- [ ] **Step 4: Add the `scaffold` command to `cli.py`**

Add import `from . import scaffold as scaffold_mod` and `import datetime as dt` is already present. Add:

```python
def _cmd_scaffold(args) -> int:
    created = scaffold_mod.scaffold(
        args.graph_repo, args.repo, args.holder, dt.date.today().year,
        with_sample=args.with_sample, contact=args.contact,
    )
    print(f"scaffolded {args.graph_repo}:")
    for rel in created:
        print("   ", rel)
    return 0
```

In `build_parser` add:

```python
    sc = sub.add_parser("scaffold", help="create a new graph repo skeleton at --graph-repo")
    sc.add_argument("--repo", required=True, metavar="OWNER/NAME", help="the GitHub repository this graph will live in")
    sc.add_argument("--holder", required=True, help="copyright holder name for LICENSE-CODE")
    sc.add_argument("--with-sample", action="store_true", help="include the 17-node sample graph")
    sc.add_argument("--contact", help="takedown contact text; defaults to the repo's GitHub issues page")
```

Register `"scaffold": _cmd_scaffold` in the `handlers` dict and catch `FileExistsError` in `main`'s except clause: `except (GraphDataError, BuildError, FileExistsError) as exc:`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph/test_cg_scaffold.py -q`
Expected: PASS (8 passed). The monkeypatched CLI test works because `scaffold()` looks up `fetch_url_text` in module globals when `fetch_text` is `None`.

- [ ] **Step 6: Commit**

```powershell
git add agent/concept_graph/scaffold.py agent/concept_graph/cli.py tests/agent/concept_graph/test_cg_scaffold.py
git diff --cached --stat
git commit -m "feat(concept_graph): scaffold command for the public graph repo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Documentation and a full run

**Files:**
- Create: `agent/concept_graph/README.md`
- Create: `docs/status/agent/concept_graph/2026-10-09-concept-graph-core-status.md` (use the date the work finishes if later)
- Modify: `README.md` of `academic-rag-model` (one bullet in the subproject map)
- Modify: `docs/trackers/academic_hub_to_do.md` is **not** touched here (Plan B is tracked in Task 11)

- [ ] **Step 1: Write the package README**

`agent/concept_graph/README.md` must contain these sections with real content (commands copied from the tested CLI, not paraphrased):

1. **What this is**: one paragraph; link to the spec.
2. **The graph repo layout**: the tree from Task 9's scaffold.
3. **Commands** (each with a runnable example against `agent/concept_graph/sample_data`):
   `validate`, `build`, `apply-review FILE`, `apply-review --from-issues OWNER/REPO --commit --close-applied`, `scaffold --repo ... --holder ... [--with-sample]`.
4. **Data model**: node fields, edge types table (the nine, with the sentence each reads as), status values, how `section` differs from `topic`, edge id rule.
5. **Reviewing**: what the Accept/Reject/Edit/Comment buttons write, what Submit does, why conflicts go to `review-conflicts.md`.
6. **Vendored libraries**: how `vendor_fetch` works and that its output is committed.
7. **Not built yet (Plan B)**: `seed`, `fill`, `link`, `critic`, agent/API drivers, IP guard.

- [ ] **Step 2: Add the bullet to `academic-rag-model/README.md`**

Insert one bullet in the subproject list, next to the other `agent/` entries:

```
- [`agent/concept_graph/`](agent/concept_graph/README.md) — builds an interactive, reviewable concept graph of the microeconomics course (typed, conditioned edges; single-file HTML viewer; conflict-safe review merging) from a YAML graph repo. Core data/viewer/review loop only; the LLM drafting stages are a follow-up plan.
```

- [ ] **Step 3: Run the whole concept_graph suite and a neighbouring suite**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/agent/concept_graph -q
```

Expected: all pass (about 71 tests: 7 + 7 + 13 + 3 + 7 + 13 + 5 + 4 + 8 from Tasks 1-9, give or take). The viewer-logic test is skipped only if `node` is not installed. Nothing outside `agent/concept_graph/`, `tests/agent/concept_graph/` and `requirements.txt` may appear in `git status` apart from the docs below.

- [ ] **Step 4: Write the status doc**

`docs/status/agent/concept_graph/2026-10-09-concept-graph-core-status.md` with headings: `What was built` (module-by-module, one line each), `Verification` (test counts from Step 3, plus the 12-item manual viewer check result from Task 6 Step 7 with browsers used), `Decisions that differ from the spec` (edge types are a code constant; `component_of`; cycle rule), `Known limits` (a lone-`$` price renders as text only when no closing `$` follows on the same line; MathML needs a current browser; issue-form URL prefill limit is 6000 characters, longer reviews use the clipboard), `What's next` (Plan B and the owner-gated publish step).

- [ ] **Step 5: Commit**

```powershell
git add agent/concept_graph/README.md README.md docs/status/agent/concept_graph/2026-10-09-concept-graph-core-status.md
git diff --cached --stat
git commit -m "docs(concept_graph): package README, subproject map entry, core status" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Publish the public graph repo (owner-gated)

**Files:** none in the monorepo. Creates an external repository.

**Gate:** Stop before Step 2 and ask the owner to confirm (a) the repository name and owner, (b) public visibility, (c) the copyright holder name for `LICENSE-CODE`, (d) whether to put the sample graph in the first push. Creating a public repository and enabling Pages publishes content to the internet; do not infer approval from earlier discussion. Also add a pending to-do for Plan B (see Step 6) using the standing to-do rule in the root `CLAUDE.md`.

- [ ] **Step 1: Pick the local path for the graph repo**

The graph repo is a sibling directory outside the monorepo, e.g. `C:\Users\theaa\microecon-concept-graph` (confirm with the owner). Never inside `ai-sandbox-master`.

- [ ] **Step 2: Scaffold and build locally (after the gate)**

```powershell
$g = 'C:\Users\theaa\microecon-concept-graph'
.\.venv\Scripts\python.exe -m agent.concept_graph.cli --graph-repo $g scaffold --repo OWNER/microecon-concept-graph --holder "HOLDER NAME" --with-sample
.\.venv\Scripts\python.exe -m agent.concept_graph.cli --graph-repo $g validate
.\.venv\Scripts\python.exe -m agent.concept_graph.cli --graph-repo $g build
Get-Content "$g\LICENSE" -TotalCount 5
```

Expected: scaffold lists files; `validate` prints `0 error(s), 1 warning(s)`; `build` prints a `graph_version`; the first lines of `LICENSE` are the Creative Commons legal code header (if the fetch failed, the command errors before writing anything: fix network access and rerun).

- [ ] **Step 3: Inspect before anything is public**

Open `$g\index.html` in a browser and repeat checks 1-4 and 8 of Task 6 Step 7. Read `NOTICE.md` and `README.md` once. Confirm: no email address, no instructor name, no copied source text anywhere (`Select-String -Path "$g\*" -Recurse -Pattern '@'` should show nothing outside licence text).

- [ ] **Step 4: Create the repository, push, label, enable Pages (after the gate)**

```powershell
Set-Location $g
git init -b main
git add README.md NOTICE.md LICENSE LICENSE-CODE .gitignore .github config data build index.html
git commit -m "Initial concept graph with sample content"
gh repo create OWNER/microecon-concept-graph --public --source . --push --description "Interactive microeconomics concept graph (study aid)"
gh label create review --repo OWNER/microecon-concept-graph --color 0e8a16 --description "Reviewer submission"
gh api -X POST repos/OWNER/microecon-concept-graph/pages -f "source[branch]=main" -f "source[path]=/"
```

Expected: the repo exists; the Pages call returns JSON with `html_url`. If the Pages API call fails because Pages is already enabled or the plan does not allow it, report the exact error and stop; do not try workarounds.

- [ ] **Step 5: Verify the live flow end to end**

After GitHub reports the Pages build complete (check with `gh api repos/OWNER/microecon-concept-graph/pages/builds/latest --jq .status`, expect `built`):

1. Open `https://OWNER.github.io/microecon-concept-graph/`; repeat Task 6 Step 7 checks 1-9.
2. Type a name, accept two items, edit one explanation, press **Submit review**. Record what actually happened: did the issue form open with the review prefilled, or did it need a paste? Both are acceptable; the toast must match the behaviour. This settles the spec's open item about prefill-by-field-id.
3. Submit the issue. Then run:

```powershell
Set-Location C:\Users\theaa\ai-sandbox-master\.worktrees\claude-concept-graph-core\ai-sandbox\academic-rag-model
.\.venv\Scripts\python.exe -m agent.concept_graph.cli --graph-repo $g apply-review --from-issues OWNER/microecon-concept-graph --commit --close-applied
```

Expected: `1 applied`-style summary lines for the accepted items and the edit, one commit `review: apply <name>` in `$g`, and the issue closed. Run `git -C $g log --stat -1` and confirm only `data/`, `reviews/applied/` changed.
4. Record the prefill finding and the live URL in the status doc from Task 10 (add a `Live check` section), commit that doc in the monorepo worktree.

- [ ] **Step 6: File Plan B as a pending to-do**

Following the root `CLAUDE.md` "Pending to-dos" rule (directly on `main`, one file, a `todo:` commit), add one bullet under a new `## Concept Graph (agent/concept_graph)` heading placed directly under the tracker's title: "Plan B: write and implement the LLM stages for the concept graph (`seed`, `fill`, `link`, `critic`, agent and API drivers, IP guard, retrieval over the `microecon` index), per `docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md` (Pipeline, Drivers, IP guard sections). Depends on this plan's schema/store and on the agent-driven transcription spec for a possible shared collect/submit helper. Also pending: the prior-year microecon transcription (tier-3 pages held for the agent mode) and the ArtifactDb review adapter. (added YYYY-MM-DD)". Reply with the heading used.

---

## Self-Review

**1. Spec coverage.** Mapping each spec section to a task:
- Intent, constraints, success criteria: Global Constraints; Task 5/6 manual check.
- Data model (sections, nodes, edges, 9 types incl. `component_of`, ids, tombstones, statuses): Tasks 1-2.
- Pipeline stages 1-4 (`seed`, `fill`, `link`, `critic`), retrieval, drivers, IP guard: **deliberately Plan B** (stated in the header and Task 11 Step 6).
- Stage 5 `build`, build-time validation (incl. amended cycle rule): Tasks 3 and 6.
- Viewer (layers by section, colour by topic, planned faded, proposed dashed, critic marker, name list, filters, side panel with edge sentences, edge click, dependency-path, any browser/phone, never-truncated names): Tasks 4-6.
- Review layer storage adapter: the viewer implements the LocalFile behaviour directly (localStorage + Download + Submit to issue form). The adapter interface is not a separate abstraction yet; the ArtifactDb adapter is out of scope. I judged an abstraction with one implementation to be YAGNI; when the Artifact adapter is built (Plan C) the functions `persist`, `download`, `submit` in `app.js` are the seam to extract.
- Review files and `apply-review` (accept/edit/reject/comment, stale detection, conflicts file, ruamel round trip, commit per reviewer, archive): Tasks 7-8.
- Mini repo layout, Pages, issue form, README/NOTICE/licences, takedown contact default: Tasks 9 and 11.
- Cost control: no LLM calls in this plan; the only network use is the one-time vendor fetch and licence text.
- Testing section: fixture graph (17 nodes, in place of the spec's "about 12"), unit tests per module, Node tests for pure viewer functions, manual browser check.
- Rollout phases 1, 2 and 5: Tasks 1-9 and 11. Phases 3, 4, 6: Plan B / Plan C.

**2. Placeholder scan.** No TBD/TODO steps. Task 10 Step 1 and Step 4 describe documents by required sections rather than literal text, which is acceptable for prose docs but the implementer must write real content, not stubs.

**3. Type consistency.** `field_hash` (Task 1) is used identically in `build.graph_payload` (hashes sent to the browser) and `reviews.apply_review` (hash compared on apply); both strip whitespace, so a field shown unchanged round-trips. JS `decisionKey` matches the fields Python's `Decision` accepts (`target.kind`, `target.id`, `action`, `field`). `Review.reviewer.name`, `graph_version`, `created`, `decisions` match between `logic.js buildReview`, `reviews.ReviewFile`, and the CLI. Edge ids in `edge_id()` match the sample YAML ids and the validator's canonical check.

**4. Review Focus.** Six items listed, each mapped to a named test above.

**Known risk to watch during execution:** the Cytoscape `width: "label"` style plus `text-max-width` is believed to size boxes to wrapped labels; if boxes clip long names in the manual check (Task 6 Step 7, item 1), set `text-max-width` larger or switch `text-wrap` handling before declaring the task done. The URL paths in `vendor.lock.json` are believed correct for the pinned versions and are verified by the first fetch in Task 4 Step 7.

## Lifecycle references

### Specs

- [2026-10-09-concept-graph-design](../specs/agent/2026-10-09-concept-graph-design.md)

### Tests

- [test_cg_build](../../../tests/agent/concept_graph/test_cg_build.py)
- [test_cg_store](../../../tests/agent/concept_graph/test_cg_store.py)
