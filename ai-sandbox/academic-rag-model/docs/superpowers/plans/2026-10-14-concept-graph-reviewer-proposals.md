# Concept graph reviewer proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reviewers propose new concepts and connections from the public page; `apply-review` validates, merges duplicate
proposals and writes `proposed` items that the existing fill, link and critic stages then draft.

**Architecture:** A new pure module `proposals.py` holds name similarity, validation and merging. `reviews.py` gains
schema version 2 with `add_node` and `add_edge` decisions and an `apply_proposals` step that runs once per round after
the per-review loop. The viewer keeps proposals in their own list (so the existing `decision.target` code is
untouched), adds a Propose menu, forms and ghost items, and merges them into the review file when it is built.

**Tech Stack:** Python 3.13, pydantic v2, networkx, ruamel.yaml (via `GraphStore`), pytest; vanilla JS with Cytoscape
and Node's built-in test runner.

**Spec:** `docs/superpowers/specs/agent/2026-10-14-concept-graph-reviewer-proposals-design.md`

## Global Constraints

- Schema version: viewer emits `schema_version: 2`; `apply-review` accepts 1 and 2; proposals are valid only in 2.
- Name at most 120 characters; note at most 200 characters.
- Node id is the slug of the name, never typed by the reviewer.
- `condition` is required for `implies` and `iff` (`schema.CONDITION_REQUIRED`); `via` is not offered.
- Definitional cycle = error, logical cycle = warning (`schema.DEFINITIONAL_TYPES`, `schema.LOGICAL_TYPES`).
- Written items: `status: proposed`, `provenance: {driver: reviewer, agent: "<names joined by '; '>", run: <today>}`.
- Node note becomes `gist`; `explanation` stays empty so `collect fill` picks the node up. Edge note becomes `explanation`.
- The own-words IP guard is not applied; `ipguard.check_meta` is.
- Invalid or ambiguous proposals go to `review-conflicts.md`; nothing is dropped silently.
- Similarity is deterministic (no embeddings); the same rules and fixture cases run in Python and JavaScript.
- Python 3.13. Run tests with `python -m pytest tests/agent/concept_graph -q`; JS tests run through
  `tests/agent/concept_graph/test_cg_viewer_logic.py` (needs `node` on PATH).
- Stage explicit paths only; commit messages end with the attribution line used in this repo.

## Review Focus

1. A name that differs only in case, punctuation or an apostrophe ("Sen's alpha" vs "Sens alpha") must count as a duplicate.
2. "Utility function" and "Indirect utility function" must NOT be merged, while "Walrasian demand" and "Walrasian
   demand correspondence" must be.
3. A connection whose endpoint is a concept proposed in the same round must validate, and must fail cleanly when
   that concept itself bounced.
4. Two reviewers proposing the same connection with different conditions must produce one edge with both conditions.
5. A version 1 review file must still apply exactly as before, and a version 2 file with no proposals must too.

## File Structure

| File | Responsibility |
|---|---|
| `agent/concept_graph/proposals.py` (new) | Input models, `normalize_name`, `slug_from_name`, `similar_names`, `find_similar_existing`, `check_node`, `check_edge`, `merge_cluster`, `cluster` |
| `agent/concept_graph/reviews.py` | `Decision` accepts `add_node`/`add_edge`; `ReviewFile.schema_version` 1 or 2; `apply_proposals` |
| `agent/concept_graph/cli.py` | Calls `apply_proposals` once after the per-review loop; prints its report |
| `agent/concept_graph/viewer/logic.js` | `normalizeName`, `slugFromName`, `similarNames`, `similarNodes`, `checkProposal`, `buildReview` v2 |
| `agent/concept_graph/viewer/app.js`, `template.html`, `style.css` | Propose menu, forms, selection button, proposals list, ghost items |
| `agent/concept_graph/viewer/tests/similarity_cases.json` (new) | Shared similarity fixture, read by Python and JS tests |
| `tests/agent/concept_graph/test_cg_proposals.py` (new) | Unit tests for `proposals.py` |
| `tests/agent/concept_graph/test_cg_apply_proposals.py` (new) | Apply, cluster, conflict and round-trip tests |
| `agent/concept_graph/viewer/tests/proposals.test.js` (new) | JS logic tests |

---

### Task 1: Name similarity, slug and validation rules

**Files:**
- Create: `agent/concept_graph/proposals.py`
- Create: `agent/concept_graph/viewer/tests/similarity_cases.json`
- Test: `tests/agent/concept_graph/test_cg_proposals.py`

**Interfaces:**
- Produces: `normalize_name(name: str) -> str`, `slug_from_name(name: str) -> str`,
  `similar_names(a: str, b: str) -> bool`, `find_similar_existing(graph: Graph, name: str) -> Node | None`,
  `check_node(graph: Graph, name: str, kind: str, section: str, topic: str, note: str) -> list[str]`,
  `check_edge(graph, source, type_, target, condition, note, *, new_ids=frozenset(), staged=()) -> tuple[list[str], list[str]]`,
  models `Connection`, `NodeProposal`, `EdgeProposal`.

- [ ] **Step 1: Write the shared fixture**

`agent/concept_graph/viewer/tests/similarity_cases.json`:

```json
{
  "similar": [
    ["Sen's alpha", "Sens alpha"],
    ["Walrasian demand", "Walrasian demand correspondence"],
    ["Cobb-Douglas utility", "Cobb Douglas utility function"],
    ["Expected utility", "Expected utility theorem"],
    ["Hicksian demand", "Hicksian demnd"],
    ["Weak axiom of revealed preference", "weak axiom of revealed preference"]
  ],
  "different": [
    ["Utility function", "Indirect utility function"],
    ["Strong axiom of revealed preference", "Weak axiom of revealed preference"],
    ["First order stochastic dominance", "Second order stochastic dominance"],
    ["Relative risk aversion", "Absolute risk aversion"],
    ["Set", "Sat"],
    ["Expenditure function", "Expenditure minimization problem"]
  ]
}
```

- [ ] **Step 2: Write the failing tests**

`tests/agent/concept_graph/test_cg_proposals.py`:

```python
import json
from pathlib import Path

import pytest

from agent.concept_graph import proposals as P
from agent.concept_graph.schema import Edge, Graph, Node, Rejected, Section, Vocab

CASES = json.loads((Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "viewer" / "tests"
                    / "similarity_cases.json").read_text(encoding="utf-8"))


def node(i, name, section="s1", kind="object", topic="t"):
    return Node(id=i, name=name, kind=kind, section=section, topic=topic)


def edge(s, t, d, **kw):
    return Edge(id=f"{s}--{t}--{d}", source=s, type=t, target=d, **kw)


def graph(nodes=(), edges=(), rejected=()):
    return Graph(sections=[Section(id="s1", title="One", order=1, state="taught")], nodes=list(nodes),
                 edges=list(edges), rejected=list(rejected), vocab=Vocab(kinds=["object", "property"], topics=["t"]))


@pytest.mark.parametrize("a,b", CASES["similar"])
def test_similar_pairs(a, b):
    assert P.similar_names(a, b) and P.similar_names(b, a)


@pytest.mark.parametrize("a,b", CASES["different"])
def test_different_pairs(a, b):
    assert not P.similar_names(a, b)


def test_slug_is_computed_from_the_name():
    assert P.slug_from_name("Sen's Alpha (axiom)") == "sens-alpha-axiom"
    assert P.slug_from_name("  !!  ") == ""


def test_find_similar_existing_returns_the_node():
    g = graph([node("walrasian-demand", "Walrasian demand")])
    assert P.find_similar_existing(g, "Walrasian demand correspondence").id == "walrasian-demand"
    assert P.find_similar_existing(g, "Budget set") is None


def test_check_node_reports_each_problem():
    g = graph([node("budget-set", "Budget set")], rejected=[Rejected(kind="node", id="banned-idea")])
    ok = P.check_node(g, "Quasi-concavity", "property", "s1", "t", "Upper contour sets are convex.")
    assert ok == []
    assert any("kind" in m for m in P.check_node(g, "X Y", "widget", "s1", "t", ""))
    assert any("section" in m for m in P.check_node(g, "X Y", "object", "nope", "t", ""))
    assert any("topic" in m for m in P.check_node(g, "X Y", "object", "s1", "nope", ""))
    assert any("already" in m for m in P.check_node(g, "Budget set", "object", "s1", "t", ""))
    assert any("rejected" in m for m in P.check_node(g, "Banned idea", "object", "s1", "t", ""))
    assert any("120" in m for m in P.check_node(g, "x" * 121, "object", "s1", "t", ""))
    assert any("200" in m for m in P.check_node(g, "X Y", "object", "s1", "t", "w " * 101))
    assert any("sources" in m for m in P.check_node(g, "X Y", "object", "s1", "t", "The offered passages do not define it."))


def test_check_edge_rules():
    g = graph([node("a", "A"), node("b", "B"), node("c", "C")],
              [edge("a", "implies", "b", condition="x"), edge("b", "component_of", "c"), edge("a", "iff", "c", condition="y")],
              [Rejected(kind="edge", id="c--is_a--a")])
    def run(s, t, d, cond=None, **kw):
        return P.check_edge(g, s, t, d, cond, "", **kw)
    assert run("b", "is_a", "c") == ([], [])
    assert any("not a concept" in m for m in run("zzz", "is_a", "c")[0])
    assert any("unknown connection type" in m for m in run("a", "likes", "c")[0])
    assert any("itself" in m for m in run("a", "is_a", "a")[0])
    assert any("already exists" in m for m in run("a", "implies", "b", "x")[0])
    assert any("rejected earlier" in m for m in run("c", "is_a", "a")[0])
    assert any("condition" in m for m in run("c", "implies", "b")[0])
    assert any("redundant" in m for m in run("a", "implies", "c", "z")[0])        # an iff already covers it
    assert any("redundant" in m for m in run("c", "has_property", "b")[0])         # b component_of c exists
    errors, _ = run("c", "is_a", "b")                                            # b -> c exists as component_of
    assert any("cycle" in m for m in errors)
    _, warnings = run("b", "implies", "a", "q")
    assert any("cycle" in m for m in warnings)
    assert run("a", "is_a", "new-one", new_ids={"new-one"}) == ([], [])
    assert any("already exists" in m for m in run("a", "is_a", "c", staged=[("a", "is_a", "c")])[0])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/agent/concept_graph/test_cg_proposals.py -q`
Expected: FAIL with `ModuleNotFoundError: agent.concept_graph.proposals`

- [ ] **Step 4: Write the implementation**

`agent/concept_graph/proposals.py`:

```python
"""Reviewer proposals: name similarity, validation and merging. Pure functions; no file access."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import networkx as nx
from pydantic import BaseModel, ConfigDict

from .ipguard import check_meta
from .schema import (CONDITION_REQUIRED, DEFINITIONAL_TYPES, EDGE_TYPES, LOGICAL_TYPES, SLUG, Graph, Node,
                     edge_id)

NAME_MAX = 120
NOTE_MAX = 200
# Words that name a kind of thing rather than a different thing: "Walrasian demand" and "Walrasian demand
# correspondence" are one concept, "Utility function" and "Indirect utility function" are not.
GENERIC = frozenset({"function", "correspondence", "relation", "problem", "theorem", "axiom", "condition",
                     "property", "set", "model", "equation", "lemma", "principle", "assumption"})
_FILLER = frozenset({"of", "the", "a", "an", "and", "for", "in", "to"})


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Connection(_Model):
    other: str
    type: str
    direction: str = "out"          # "out": the new concept is the source; "in": it is the target
    condition: str | None = None
    note: str = ""


class NodeProposal(_Model):
    name: str
    kind: str
    section: str
    topic: str
    note: str = ""
    connections: list[Connection] = []


class EdgeProposal(_Model):
    source: str
    type: str
    target: str
    condition: str | None = None
    note: str = ""


def normalize_name(name: str) -> str:
    text = (name or "").lower().replace("’", "").replace("'", "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def slug_from_name(name: str) -> str:
    return "-".join(normalize_name(name).split())


def _tokens(name: str) -> set[str]:
    return {t for t in normalize_name(name).split() if t not in _FILLER}


def _distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similar_names(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if ta and tb:
        small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
        if len(small) >= 2 and small <= big and (big - small) <= GENERIC:
            return True
        if len(ta & tb) / len(ta | tb) >= 0.75:
            return True
    return _distance(na, nb) <= 0.10 * max(len(na), len(nb))


def find_similar_existing(graph: Graph, name: str) -> Node | None:
    return next((n for n in graph.nodes if similar_names(n.name, name)), None)


def check_node(graph: Graph, name: str, kind: str, section: str, topic: str, note: str) -> list[str]:
    problems = []
    if not (name or "").strip():
        problems.append("name is empty")
    elif len(name) > NAME_MAX:
        problems.append(f"name is longer than {NAME_MAX} characters")
    slug = slug_from_name(name)
    if name.strip() and not re.match(SLUG, slug or "!"):
        problems.append(f"name {name!r} does not give a usable id")
    if any(n.id == slug for n in graph.nodes):
        problems.append(f"{slug!r} is already a concept in the graph")
    if any(r.kind == "node" and r.id == slug for r in graph.rejected):
        problems.append(f"{slug!r} was rejected earlier and must not be proposed again")
    if kind not in graph.vocab.kinds:
        problems.append(f"kind {kind!r} is not one of {', '.join(graph.vocab.kinds)}")
    if topic not in graph.vocab.topics:
        problems.append(f"topic {topic!r} is not one of {', '.join(graph.vocab.topics)}")
    if section not in {s.id for s in graph.sections}:
        problems.append(f"section {section!r} does not exist")
    if len(note or "") > NOTE_MAX:
        problems.append(f"note is longer than {NOTE_MAX} characters")
    problems += check_meta({"note": note}) if note else []
    return problems


def check_edge(graph: Graph, source: str, type_: str, target: str, condition: str | None, note: str,
               *, new_ids=frozenset(), staged=()) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one proposed connection. `new_ids` are concepts proposed in the same round;
    `staged` are (source, type, target) triples already accepted earlier in the round."""
    errors: list[str] = []
    warnings: list[str] = []
    known = {n.id for n in graph.nodes} | set(new_ids)
    for label, value in (("source", source), ("target", target)):
        if value not in known:
            errors.append(f"{label} {value!r} is not a concept in the graph")
    if type_ not in EDGE_TYPES:
        errors.append(f"unknown connection type {type_!r}; use one of {', '.join(EDGE_TYPES)}")
    if source == target:
        errors.append("a concept cannot connect to itself")
    if errors:
        return errors, warnings
    eid = edge_id(source, type_, target)
    triples = [(e.source, e.type, e.target) for e in graph.edges] + list(staged)
    have = set(triples)
    if (source, type_, target) in have:
        errors.append(f"{eid} already exists")
    if any(r.kind == "edge" and r.id == eid for r in graph.rejected):
        errors.append(f"{eid} was rejected earlier and must not be proposed again")
    if type_ in CONDITION_REQUIRED and not (condition or "").strip():
        errors.append(f"a {type_} connection needs a condition (when does it hold?)")
    if note:
        errors += check_meta({"note": note})
    if type_ == "implies" and ((source, "iff", target) in have or (target, "iff", source) in have):
        errors.append("redundant: an iff between the same concepts already covers this implies")
    if type_ == "has_property" and (target, "component_of", source) in have:
        errors.append("redundant: the reverse component_of connection already exists")
    if type_ == "component_of" and (target, "has_property", source) in have:
        errors.append("redundant: the reverse has_property connection already exists")
    for group, label, bucket in ((DEFINITIONAL_TYPES, "definitional", errors), (LOGICAL_TYPES, "logical", warnings)):
        if type_ in group:
            g = nx.DiGraph()
            g.add_edges_from((s, d) for s, t, d in triples if t in group and s != d)
            if g.has_node(source) and g.has_node(target) and nx.has_path(g, target, source):
                bucket.append(f"this would close a {label} cycle between {source!r} and {target!r}")
    return errors, warnings
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/agent/concept_graph/test_cg_proposals.py -q`
Expected: PASS (all). If `"Hicksian demand"` vs `"Hicksian demnd"` fails, the edit-distance bound is the cause:
1 edit on 15 characters is within 10%.

- [ ] **Step 6: Commit**

```bash
git add agent/concept_graph/proposals.py agent/concept_graph/viewer/tests/similarity_cases.json tests/agent/concept_graph/test_cg_proposals.py
git commit -m "feat(concept_graph): proposal similarity, slug and validation rules"
```

---

### Task 2: Clustering and merging duplicate proposals

**Files:**
- Modify: `agent/concept_graph/proposals.py` (append)
- Test: `tests/agent/concept_graph/test_cg_proposals.py` (append)

**Interfaces:**
- Consumes: `NodeProposal`, `Connection`, `similar_names` from Task 1.
- Produces: `@dataclass Merged(name, kind, section, topic, note, connections: list[Connection], reviewers: list[str], decisions: list[str])`,
  `cluster(items: list[tuple[NodeProposal, str]]) -> list[list[tuple[NodeProposal, str]]]`,
  `merge_cluster(cluster) -> Merged`, `merge_edges(items: list[tuple[EdgeProposal, str]]) -> list[tuple[EdgeProposal, list[str]]]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent/concept_graph/test_cg_proposals.py`:

```python
def np(name, who, kind="property", section="s1", topic="t", note="", conns=()):
    return (P.NodeProposal(name=name, kind=kind, section=section, topic=topic, note=note, connections=list(conns)), who)


def test_cluster_groups_similar_names_and_leaves_others():
    items = [np("Walrasian demand", "Ana"), np("Budget set", "Ben"), np("Walrasian demand correspondence", "Cy")]
    groups = P.cluster(items)
    assert sorted(len(g) for g in groups) == [1, 2]


def test_merge_takes_majority_name_kind_and_unions_connections():
    c1 = P.Connection(other="u", type="is_a", direction="out", condition=None, note="n1")
    c2 = P.Connection(other="u", type="is_a", direction="out", condition=None, note="n2")
    c3 = P.Connection(other="w", type="implies", direction="out", condition="when convex", note="")
    cl = [np("Quasi concavity", "Ana", kind="property", note="Upper sets are convex.", conns=[c1]),
          np("Quasi-concavity", "Ben", kind="property", note="Ranks bundles.", conns=[c2, c3]),
          np("Quasi concavity", "Cy", kind="axiom")]
    m = P.merge_cluster(cl)
    assert m.name == "Quasi concavity" and m.kind == "property"
    assert sorted(m.reviewers) == ["Ana", "Ben", "Cy"]
    assert {(c.other, c.type) for c in m.connections} == {("u", "is_a"), ("w", "implies")}
    assert "Ana: Upper sets are convex." in m.note and "Ben: Ranks bundles." in m.note
    assert len(m.note) <= P.NOTE_MAX
    assert m.decisions == []


def test_merge_tie_is_flagged_and_does_not_depend_on_read_order():
    a = [np("Foo bar", "Zoe", kind="axiom"), np("Foo bar", "Abe", kind="property")]
    m1, m2 = P.merge_cluster(a), P.merge_cluster(list(reversed(a)))
    assert m1.kind == m2.kind == "property"                  # Abe sorts first
    assert any("kind" in d and "Abe" in d and "Zoe" in d for d in m1.decisions)


def test_merge_name_tie_prefers_the_more_specific_form():
    m = P.merge_cluster([np("Walrasian demand", "Ana"), np("Walrasian demand correspondence", "Ben")])
    assert m.name == "Walrasian demand correspondence"


def test_single_proposal_keeps_its_note_without_a_name_prefix():
    assert P.merge_cluster([np("Foo bar", "Ana", note="Just this.")]).note == "Just this."


def test_merge_edges_joins_conditions_and_notes():
    e1 = (P.EdgeProposal(source="a", type="implies", target="b", condition="single valued", note="x"), "Ana")
    e2 = (P.EdgeProposal(source="a", type="implies", target="b", condition="continuous", note="y"), "Ben")
    e3 = (P.EdgeProposal(source="a", type="is_a", target="b"), "Cy")
    merged = P.merge_edges([e1, e2, e3])
    assert len(merged) == 2
    implies = next(e for e, _ in merged if e.type == "implies")
    assert implies.condition == "continuous; single valued" and "Ana: x" in implies.note and "Ben: y" in implies.note
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/concept_graph/test_cg_proposals.py -q`
Expected: FAIL with `AttributeError: module ... has no attribute 'cluster'`

- [ ] **Step 3: Implement**

Append to `agent/concept_graph/proposals.py`:

```python
@dataclass
class Merged:
    name: str
    kind: str
    section: str
    topic: str
    note: str
    connections: list[Connection]
    reviewers: list[str]
    decisions: list[str] = field(default_factory=list)


def cluster(items: list[tuple[NodeProposal, str]]) -> list[list[tuple[NodeProposal, str]]]:
    """Group proposals whose names are similar (transitively), keeping first-seen order of groups."""
    groups: list[list[tuple[NodeProposal, str]]] = []
    for item in items:
        hits = [g for g in groups if any(similar_names(item[0].name, other[0].name) for other in g)]
        if not hits:
            groups.append([item])
            continue
        hits[0].append(item)
        for extra in hits[1:]:
            hits[0].extend(extra)
            groups.remove(extra)
    return groups


def _majority(values: list[tuple[str, str]], label: str) -> tuple[str, list[str]]:
    """values are (value, reviewer). A tie is broken by reviewer name, never by read order, and reported."""
    counts = Counter(v for v, _ in values)
    top = max(counts.values())
    leaders = sorted((v for v, c in counts.items() if c == top))
    if len(leaders) == 1:
        return leaders[0], []
    first = min((r, v) for v, r in values if v in leaders)
    detail = "; ".join(f"{r} chose {v}" for v, r in sorted(values, key=lambda x: (x[1], x[0])))
    return first[1], [f"{label} needs a decision: {detail} (written as {first[1]!r} by name order)"]


def merge_cluster(items: list[tuple[NodeProposal, str]]) -> Merged:
    decisions: list[str] = []
    forms = Counter(normalize_name(p.name) for p, _ in items)
    top = max(forms.values())
    best = sorted((f for f, c in forms.items() if c == top), key=lambda f: (-len(f), f))[0]
    name = next(p.name for p, _ in items if normalize_name(p.name) == best)
    chosen = {}
    for label in ("kind", "section", "topic"):
        chosen[label], flagged = _majority([(getattr(p, label), who) for p, who in items], label)
        decisions += flagged
    conns: dict[tuple[str, str, str], Connection] = {}
    for p, who in items:
        for c in p.connections:
            key = (c.other, c.type, c.direction)
            if key not in conns:
                conns[key] = c.model_copy()
            else:
                have = conns[key]
                parts = sorted({x for x in (have.condition, c.condition) if x})
                have.condition = "; ".join(parts) or None
    reviewers = sorted({who for _, who in items})
    notes = [(who, p.note.strip()) for p, who in sorted(items, key=lambda i: i[1]) if p.note.strip()]
    if len(items) == 1:
        note = notes[0][1] if notes else ""
    else:
        note = " | ".join(f"{who}: {text}" for who, text in notes)
    if len(note) > NOTE_MAX:
        note = note[: NOTE_MAX - 1].rstrip() + "…"
    return Merged(name=name, note=note, connections=list(conns.values()), reviewers=reviewers,
                  decisions=decisions, **chosen)


def merge_edges(items: list[tuple[EdgeProposal, str]]) -> list[tuple[EdgeProposal, list[str]]]:
    """Collapse proposals for the same edge id; conditions and notes are joined, reviewers kept."""
    out: dict[str, tuple[EdgeProposal, list[str], list[tuple[str, str]]]] = {}
    for e, who in items:
        key = edge_id(e.source, e.type, e.target)
        if key not in out:
            out[key] = (e.model_copy(), [who], [(who, e.note.strip())] if e.note.strip() else [])
            continue
        have, who_list, notes = out[key]
        parts = sorted({x for x in (have.condition, e.condition) if x})
        have.condition = "; ".join(parts) or None
        if who not in who_list:
            who_list.append(who)
        if e.note.strip():
            notes.append((who, e.note.strip()))
    result = []
    for have, who_list, notes in out.values():
        if len(notes) > 1:
            have.note = " | ".join(f"{w}: {t}" for w, t in sorted(notes))[:NOTE_MAX]
        elif notes:
            have.note = notes[0][1] if len(who_list) == 1 else f"{notes[0][0]}: {notes[0][1]}"
        result.append((have, sorted(who_list)))
    return result
```

Note: in `merge_edges` a single reviewer's note keeps no prefix; with several reviewers where only one wrote a note,
the prefix keeps the credit.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/agent/concept_graph/test_cg_proposals.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/proposals.py tests/agent/concept_graph/test_cg_proposals.py
git commit -m "feat(concept_graph): cluster and merge duplicate reviewer proposals"
```

---

### Task 3: Review file version 2 and `apply_proposals`

**Files:**
- Modify: `agent/concept_graph/reviews.py` (`Decision`, `ReviewFile`, new `apply_proposals`)
- Modify: `agent/concept_graph/cli.py` (`_cmd_apply_review`)
- Test: `tests/agent/concept_graph/test_cg_apply_proposals.py`

**Interfaces:**
- Consumes: everything from Tasks 1 and 2; `GraphStore.add_nodes(section_id, nodes)`, `GraphStore.add_edges(edges)`,
  `GraphStore.read_all()`, `ApplyReport`, `_append` (existing in `reviews.py`).
- Produces: `apply_proposals(store: GraphStore, reviews: list[ReviewFile], today: str) -> ApplyReport`.

- [ ] **Step 1: Write the failing tests**

`tests/agent/concept_graph/test_cg_apply_proposals.py`:

```python
import json

import pytest

from agent.concept_graph.reviews import ReviewFile, apply_proposals, apply_review
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample


SECTION = TOPIC = "x"   # replaced by the `store` fixture with real values from the sample graph


def review(who, *decisions, version=2):
    return ReviewFile.model_validate({"schema_version": version, "graph_version": "v", "reviewer": {"name": who},
                                      "created": "t", "decisions": list(decisions)})


def add_node(name, **kw):
    p = {"name": name, "kind": "property", "section": SECTION, "topic": TOPIC, "note": "", "connections": []}
    p.update(kw)
    return {"action": "add_node", "proposal": p}


def add_edge(source, type_, target, **kw):
    p = {"source": source, "type": type_, "target": target}
    p.update(kw)
    return {"action": "add_edge", "proposal": p}


@pytest.fixture
def store(tmp_path):
    global SECTION, TOPIC
    s = GraphStore(copy_sample(tmp_path))
    g = s.read_all()
    SECTION, TOPIC = g.sections[0].id, g.vocab.topics[0]
    assert "property" in g.vocab.kinds
    return s


def test_version_1_files_still_load_and_apply(store):
    r = review("Ada", version=1)
    assert apply_review(store, r, "2026-10-20").applied == []
    assert apply_proposals(store, [r], "2026-10-20").applied == []


def test_proposals_are_rejected_in_a_version_1_file():
    with pytest.raises(ValueError):
        review("Ada", add_node("X Y"), version=1)


def test_a_new_concept_with_a_connection_is_written_as_proposed(store):
    g = store.read_all()
    other = g.nodes[0].id
    r = review("Ada", add_node("Quasi concavity", note="Upper sets are convex.",
                               connections=[{"other": other, "type": "is_a", "direction": "out"}]))
    report = apply_proposals(store, [r], "2026-10-20")
    after = store.read_all()
    n = next(x for x in after.nodes if x.id == "quasi-concavity")
    assert n.status == "proposed" and n.explanation == "" and n.gist == "Upper sets are convex."
    assert n.provenance.driver == "reviewer" and n.provenance.agent == "Ada"
    assert any(e.id == f"quasi-concavity--is_a--{other}" and e.status == "proposed" for e in after.edges)
    assert errors(validate(after)) == []
    assert any("quasi-concavity" in line for line in report.applied)


def test_two_reviewers_proposing_the_same_concept_become_one_merged_node(store):
    a = review("Ana", add_node("Quasi concavity", note="Upper sets are convex."))
    b = review("Ben", add_node("Quasi-concavity", note="Ranks bundles."))
    report = apply_proposals(store, [a, b], "2026-10-20")
    nodes = [n for n in store.read_all().nodes if "quasi" in n.id]
    assert len(nodes) == 1
    assert nodes[0].provenance.agent == "Ana; Ben"
    assert "Ana:" in nodes[0].gist and "Ben:" in nodes[0].gist
    assert any("merged 2 proposals" in line for line in report.applied)


def test_a_proposal_similar_to_an_existing_concept_becomes_edge_proposals_and_a_comment(store):
    g = store.read_all()
    existing, partner = g.nodes[0], g.nodes[1]
    r = review("Ada", add_node(existing.name.upper(), note="A thought.",
                               connections=[{"other": partner.id, "type": "is_a", "direction": "in"}]))
    report = apply_proposals(store, [r], "2026-10-20")
    after = store.read_all()
    assert len(after.nodes) == len(g.nodes)                       # nothing new
    comments = (store.root / "review-comments.md").read_text(encoding="utf-8")
    assert existing.id in comments and "A thought." in comments
    conflicts = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "treated as proposals about" in conflicts
    assert report.conflicts


def test_an_invalid_proposal_goes_to_conflicts_with_the_reason(store):
    r = review("Ada", add_node("Odd one", kind="widget"), add_edge("nope", "is_a", "also-nope"))
    report = apply_proposals(store, [r], "2026-10-20")
    text = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "kind" in text and "not a concept" in text and len(report.conflicts) == 2
    assert not any(n.id == "odd-one" for n in store.read_all().nodes)


def test_a_connection_to_a_bounced_new_concept_bounces_too(store):
    g = store.read_all()
    r = review("Ada", add_node("Odd one", kind="widget"), add_edge("odd-one", "is_a", g.nodes[0].id))
    report = apply_proposals(store, [r], "2026-10-20")
    assert len(report.conflicts) == 2


def test_the_same_edge_from_two_reviewers_is_one_edge_with_both_conditions(store):
    g = store.read_all()
    have = {e.id for e in g.edges}
    ids = [n.id for n in g.nodes]
    a, b = next((a, b) for a in ids for b in ids if a != b
                and f"{a}--implies--{b}" not in have and f"{a}--iff--{b}" not in have and f"{b}--iff--{a}" not in have)
    x = review("Ana", add_edge(a, "implies", b, condition="single valued"))
    y = review("Ben", add_edge(a, "implies", b, condition="continuous"))
    apply_proposals(store, [x, y], "2026-10-20")
    e = next(e for e in store.read_all().edges if e.id == f"{a}--implies--{b}")
    assert "single valued" in e.condition and "continuous" in e.condition
    assert e.provenance.agent == "Ana; Ben"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/agent/concept_graph/test_cg_apply_proposals.py -q`
Expected: FAIL with `ImportError: cannot import name 'apply_proposals'`

- [ ] **Step 3: Extend `Decision` and `ReviewFile`**

In `agent/concept_graph/reviews.py`, replace the `Decision` class and `ReviewFile`:

```python
from .proposals import (Connection, EdgeProposal, NodeProposal, check_edge, check_node, cluster, find_similar_existing,
                        merge_cluster, merge_edges, slug_from_name)
from .schema import edge_id


class Decision(_Model):
    target: Target | None = None
    action: Literal["accept", "reject", "edit", "comment", "add_node", "add_edge"]
    field: str | None = None
    base_hash: str | None = None
    new_value: str | None = None
    comment: str | None = None
    proposal: NodeProposal | EdgeProposal | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.action in ("add_node", "add_edge"):
            want = NodeProposal if self.action == "add_node" else EdgeProposal
            if not isinstance(self.proposal, want) or self.target is not None:
                raise ValueError(f"{self.action} needs a matching proposal and no target")
            return self
        if self.target is None or self.proposal is not None:
            raise ValueError(f"{self.action} needs a target and no proposal")
        if self.action == "edit":
            allowed = EDITABLE_NODE_FIELDS if self.target.kind == "node" else EDITABLE_EDGE_FIELDS
            if self.field not in allowed:
                raise ValueError(f"cannot edit field {self.field!r} of a {self.target.kind}; allowed: {allowed}")
            if self.base_hash is None or self.new_value is None:
                raise ValueError("an edit needs base_hash and new_value")
        if self.action == "comment" and not (self.comment or "").strip():
            raise ValueError("a comment needs text")
        return self


class ReviewFile(_Model):
    schema_version: Literal[1, 2]
    graph_version: str
    reviewer: Reviewer
    created: str
    decisions: list[Decision]

    @model_validator(mode="after")
    def _proposals_need_version_2(self):
        if self.schema_version == 1 and any(d.action in ("add_node", "add_edge") for d in self.decisions):
            raise ValueError("proposals need schema_version 2")
        return self
```

Also, in `apply_review`'s loop, skip proposal decisions at the top of the loop body:
`if d.action in ("add_node", "add_edge"): continue` (before `kind, item_id = d.target.kind, d.target.id`).

- [ ] **Step 4: Add `apply_proposals`**

Append to `agent/concept_graph/reviews.py`:

```python
def apply_proposals(store: GraphStore, reviews: list[ReviewFile], today: str) -> ApplyReport:
    """One pass over every review in the round: cluster duplicate concepts, validate, write proposed items."""
    report = ApplyReport()
    node_items: list[tuple[NodeProposal, str]] = []
    edge_items: list[tuple[EdgeProposal, str]] = []
    for r in reviews:
        for d in r.decisions:
            if d.action == "add_node":
                node_items.append((d.proposal, r.reviewer.name))
            elif d.action == "add_edge":
                edge_items.append((d.proposal, r.reviewer.name))
    if not node_items and not edge_items:
        return report
    graph = store.read_all()
    conflicts_file = store.root / "review-conflicts.md"

    def conflict(who: list[str], label: str, reason: str) -> None:
        msg = f"{'; '.join(who)} {today}: proposal {label}: {reason}"
        _append(conflicts_file, "- " + msg)
        report.conflicts.append(msg)

    new_nodes: list[dict] = []
    new_ids: set[str] = set()
    pending_edges: list[tuple[EdgeProposal, str]] = list(edge_items)
    for group in cluster(node_items):
        merged = merge_cluster(group)
        label = f"concept {merged.name!r}"
        for line in merged.decisions:
            conflict(merged.reviewers, label, line)
        if len(group) > 1:
            report.applied.append(f"{label}: merged {len(group)} proposals from {', '.join(merged.reviewers)}")
        existing = find_similar_existing(graph, merged.name)
        if existing is not None:
            who = merged.reviewers
            if merged.note:
                _append(store.root / "review-comments.md",
                        f"- {'; '.join(who)} {today} on node {existing.id}: proposed as a new concept "
                        f"({merged.name}): {merged.note}")
                report.comments.append(f"node {existing.id}: proposal note recorded")
            conflict(who, label, f"treated as proposals about existing concept {existing.id!r}: confirm, or "
                                 f"re-propose it as a separate concept")
            for c in merged.connections:
                src, dst = (existing.id, c.other) if c.direction == "out" else (c.other, existing.id)
                pending_edges += [(EdgeProposal(source=src, type=c.type, target=dst, condition=c.condition,
                                                note=c.note), w) for w in who]
            continue
        problems = check_node(graph, merged.name, merged.kind, merged.section, merged.topic, merged.note)
        slug = slug_from_name(merged.name)
        if slug in new_ids:
            problems.append(f"{slug!r} was proposed twice in this round")
        if problems:
            conflict(merged.reviewers, label, "; ".join(problems))
            continue
        new_ids.add(slug)
        new_nodes.append({"id": slug, "name": merged.name, "kind": merged.kind, "section": merged.section,
                          "topic": merged.topic, "gist": merged.note, "explanation": "", "status": "proposed",
                          "provenance": {"driver": "reviewer", "agent": "; ".join(merged.reviewers), "run": today}})
        report.applied.append(f"node {slug}: proposed by {', '.join(merged.reviewers)}")
        for c in merged.connections:
            src, dst = (slug, c.other) if c.direction == "out" else (c.other, slug)
            pending_edges += [(EdgeProposal(source=src, type=c.type, target=dst, condition=c.condition,
                                            note=c.note), w) for w in merged.reviewers]

    staged: list[tuple[str, str, str]] = []
    new_edges: list[dict] = []
    for e, who in sorted(merge_edges(pending_edges), key=lambda i: edge_id(i[0].source, i[0].type, i[0].target)):
        eid = edge_id(e.source, e.type, e.target)
        errs, warns = check_edge(graph, e.source, e.type, e.target, e.condition, e.note, new_ids=new_ids,
                                 staged=staged)
        if errs:
            conflict(who, f"connection {eid}", "; ".join(errs))
            continue
        staged.append((e.source, e.type, e.target))
        new_edges.append({"id": eid, "source": e.source, "type": e.type, "target": e.target,
                          "condition": e.condition, "explanation": e.note, "status": "proposed",
                          "provenance": {"driver": "reviewer", "agent": "; ".join(who), "run": today}})
        report.applied.append(f"edge {eid}: proposed by {', '.join(who)}" +
                              (f" (warning: {'; '.join(warns)})" if warns else ""))
    by_section: dict[str, list[dict]] = {}
    for n in new_nodes:
        by_section.setdefault(n["section"], []).append(n)
    for section_id, nodes in by_section.items():
        store.add_nodes(section_id, nodes)
    if new_edges:
        store.add_edges(new_edges)
    return report
```

Note: `merge_edges` receives reviewer names from both standalone proposals and from concept connections; for a
connection that came from a merged concept the reviewer list is the cluster's reviewers (one edge proposal per name,
which `merge_edges` collapses).

- [ ] **Step 5: Call it from the CLI**

In `agent/concept_graph/cli.py` `_cmd_apply_review`, change the import to include `apply_proposals` and add after the
`for label, review, issue_number in inputs:` loop, before `return 1 if failed else 0`:

```python
    if inputs:
        round_report = apply_proposals(store, [r for _, r, _ in inputs], args.today or dt.date.today().isoformat())
        if round_report.applied or round_report.conflicts or round_report.comments:
            print(f"proposals: {len(round_report.applied)} applied, {len(round_report.conflicts)} conflict(s), "
                  f"{len(round_report.comments)} comment(s)")
            for line in round_report.applied:
                print("   ", line)
            if round_report.conflicts:
                print(f"    conflicts need your decision: see {args.graph_repo / 'review-conflicts.md'}")
            if args.commit:
                _git_commit(args.graph_repo, "proposals")
```

Import line: `from .reviews import ReviewFile, apply_proposals, apply_review, archive_review`.

- [ ] **Step 6: Run the new and the existing review tests**

Run: `python -m pytest tests/agent/concept_graph/test_cg_apply_proposals.py tests/agent/concept_graph/test_cg_reviews.py tests/agent/concept_graph/test_cg_cli.py tests/agent/concept_graph/test_cg_gh_issues.py -q`
Expected: PASS. If a `GraphStore.add_edges` call raises "refers to unknown node", nodes were not written first:
the order above (nodes, then edges) is required.

- [ ] **Step 7: Commit**

```bash
git add agent/concept_graph/reviews.py agent/concept_graph/cli.py tests/agent/concept_graph/test_cg_apply_proposals.py
git commit -m "feat(concept_graph): apply reviewer proposals (schema v2, clustering, conflicts)"
```

---

### Task 4: Page logic (`logic.js`) and its tests

**Files:**
- Modify: `agent/concept_graph/viewer/logic.js`
- Test: `agent/concept_graph/viewer/tests/proposals.test.js`
- Modify: `agent/concept_graph/viewer/tests/logic.test.js` (`buildReview` test expects version 2)

**Interfaces:**
- Produces on `CG`: `normalizeName(name)`, `slugFromName(name)`, `similarNames(a, b)`, `similarNodes(nodes, name, limit)`,
  `checkProposal(graph, proposal, pending)` returning `{errors: string[], similar: node[]}`, and `buildReview(graph,
  decisions, reviewerName, nowIso, proposals?)` emitting `schema_version: 2`.

- [ ] **Step 1: Write the failing tests**

`agent/concept_graph/viewer/tests/proposals.test.js`:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const CG = require("../logic.js");

const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "similarity_cases.json"), "utf8"));

test("similarNames agrees with the shared fixture", () => {
  cases.similar.forEach(([a, b]) => assert.ok(CG.similarNames(a, b) && CG.similarNames(b, a), `${a} ~ ${b}`));
  cases.different.forEach(([a, b]) => assert.ok(!CG.similarNames(a, b), `${a} !~ ${b}`));
});

test("slugFromName drops apostrophes and punctuation", () => {
  assert.equal(CG.slugFromName("Sen's Alpha (axiom)"), "sens-alpha-axiom");
  assert.equal(CG.slugFromName("  !!  "), "");
});

const graph = {
  graph_version: "v1",
  nodes: [{ id: "budget-set", name: "Budget set", kind: "object", section: "s1", topic: "demand" },
          { id: "walrasian-demand", name: "Walrasian demand", kind: "object", section: "s1", topic: "demand" }],
  edges: [{ id: "budget-set--is_a--walrasian-demand", source: "budget-set", type: "is_a", target: "walrasian-demand" }],
  sections: [{ id: "s1", order: 1 }],
  vocab: { kinds: ["object", "property"], topics: ["demand"] }
};

test("similarNodes lists the closest existing concepts first", () => {
  const got = CG.similarNodes(graph.nodes, "Walrasian demand correspondence", 3);
  assert.deepEqual(got.map((n) => n.id), ["walrasian-demand"]);
});

test("checkProposal flags the same problems the server does", () => {
  const ok = { action: "add_node", proposal: { name: "Quasi concavity", kind: "property", section: "s1", topic: "demand", note: "", connections: [] } };
  assert.deepEqual(CG.checkProposal(graph, ok.proposal, []).errors, []);
  const bad = { name: "Budget set", kind: "widget", section: "zz", topic: "nope", note: "", connections: [] };
  const errs = CG.checkProposal(graph, bad, []).errors.join(" | ");
  assert.match(errs, /already/); assert.match(errs, /kind/); assert.match(errs, /section/); assert.match(errs, /topic/);
});

test("checkProposal for a connection needs a condition for implies and refuses duplicates", () => {
  const e = { source: "budget-set", type: "implies", target: "walrasian-demand", condition: "", note: "" };
  assert.match(CG.checkProposal(graph, e, []).errors.join(" "), /condition/);
  const dup = { source: "budget-set", type: "is_a", target: "walrasian-demand", condition: null, note: "" };
  assert.match(CG.checkProposal(graph, dup, []).errors.join(" "), /already exists/);
});

test("buildReview emits version 2 and appends proposals after decisions", () => {
  const p = { action: "add_edge", proposal: { source: "a", type: "is_a", target: "b" } };
  const r = CG.buildReview(graph, [{ target: { kind: "node", id: "x" }, action: "accept" }], "Ada", "2026-10-20T00:00:00Z", [p]);
  assert.equal(r.schema_version, 2);
  assert.equal(r.decisions.length, 2);
  assert.equal(r.decisions[1].action, "add_edge");
});
```

In `viewer/tests/logic.test.js`, the test `buildReview has the shape apply-review expects` (about line 106) asserts
`schema_version: 1` in its expected object: change that one value to `2`. Other `schema_version: 1` literals in the
JS tests are inputs and stay.

- [ ] **Step 2: Run to verify it fails**

Run: `node --test agent/concept_graph/viewer/tests/proposals.test.js`
Expected: FAIL (`CG.similarNames is not a function`)

- [ ] **Step 3: Implement in `logic.js`**

Add before the final `return {`:

```javascript
  var GENERIC = ["function", "correspondence", "relation", "problem", "theorem", "axiom", "condition", "property",
    "set", "model", "equation", "lemma", "principle", "assumption"];
  var FILLER = ["of", "the", "a", "an", "and", "for", "in", "to"];
  var NAME_MAX = 120, NOTE_MAX = 200;
  var CONDITION_REQUIRED = ["implies", "iff"];

  function normalizeName(name) {
    return String(name || "").toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/).filter(Boolean).join(" ");
  }
  function slugFromName(name) { return normalizeName(name).split(" ").filter(Boolean).join("-"); }
  function tokens(name) {
    return normalizeName(name).split(" ").filter(function (t) { return t && FILLER.indexOf(t) === -1; });
  }
  function distance(a, b) {
    var prev = []; for (var j = 0; j <= b.length; j++) prev.push(j);
    for (var i = 1; i <= a.length; i++) {
      var cur = [i];
      for (var k = 1; k <= b.length; k++) {
        cur.push(Math.min(prev[k] + 1, cur[k - 1] + 1, prev[k - 1] + (a[i - 1] === b[k - 1] ? 0 : 1)));
      }
      prev = cur;
    }
    return prev[b.length];
  }
  function similarNames(a, b) {
    var na = normalizeName(a), nb = normalizeName(b);
    if (!na || !nb) return false;
    if (na === nb) return true;
    var ta = tokens(a), tb = tokens(b);
    if (ta.length && tb.length) {
      var small = ta.length <= tb.length ? ta : tb, big = ta.length <= tb.length ? tb : ta;
      var inBig = function (t) { return big.indexOf(t) !== -1; };
      var extra = big.filter(function (t) { return small.indexOf(t) === -1; });
      if (small.length >= 2 && small.every(inBig) && extra.every(function (t) { return GENERIC.indexOf(t) !== -1; })) return true;
      var shared = ta.filter(function (t) { return tb.indexOf(t) !== -1; }).length;
      var union = new Set(ta.concat(tb)).size;
      if (shared / union >= 0.75) return true;
    }
    return distance(na, nb) <= 0.10 * Math.max(na.length, nb.length);
  }
  function similarNodes(nodes, name, limit) {
    return nodes.filter(function (n) { return similarNames(n.name, name); }).slice(0, limit || 3);
  }

  // Mirrors proposals.py check_node / check_edge so the form can say what is wrong before anything is sent.
  function checkProposal(graph, p, pending) {
    var errors = [], similar = [];
    var ids = new Set(graph.nodes.map(function (n) { return n.id; }));
    (pending || []).forEach(function (x) { if (x.action === "add_node") ids.add(slugFromName(x.proposal.name)); });
    if (p.name !== undefined) {
      var slug = slugFromName(p.name);
      if (!String(p.name).trim()) errors.push("name is empty");
      else if (p.name.length > NAME_MAX) errors.push("name is longer than " + NAME_MAX + " characters");
      else if (!slug) errors.push("name does not give a usable id");
      if (slug && graph.nodes.some(function (n) { return n.id === slug; })) errors.push("'" + slug + "' is already a concept in the graph");
      if (graph.vocab.kinds.indexOf(p.kind) === -1) errors.push("kind '" + p.kind + "' is not one of " + graph.vocab.kinds.join(", "));
      if (graph.vocab.topics.indexOf(p.topic) === -1) errors.push("topic '" + p.topic + "' is not one of " + graph.vocab.topics.join(", "));
      if (!graph.sections.some(function (s) { return s.id === p.section; })) errors.push("section '" + p.section + "' does not exist");
      if ((p.note || "").length > NOTE_MAX) errors.push("note is longer than " + NOTE_MAX + " characters");
      similar = similarNodes(graph.nodes, p.name, 3);
      (p.connections || []).forEach(function (c) {
        if (!ids.has(c.other)) errors.push("connection to '" + c.other + "': not a concept in the graph");
        if (CONDITION_REQUIRED.indexOf(c.type) !== -1 && !(c.condition || "").trim()) errors.push("a " + c.type + " connection needs a condition");
      });
    } else {
      if (!ids.has(p.source)) errors.push("source '" + p.source + "' is not a concept in the graph");
      if (!ids.has(p.target)) errors.push("target '" + p.target + "' is not a concept in the graph");
      if (p.source === p.target) errors.push("a concept cannot connect to itself");
      if (CONDITION_REQUIRED.indexOf(p.type) !== -1 && !(p.condition || "").trim()) errors.push("a " + p.type + " connection needs a condition (when does it hold?)");
      var id = p.source + "--" + p.type + "--" + p.target;
      var taken = graph.edges.some(function (e) { return e.id === id; }) ||
        (pending || []).some(function (x) { return x.action === "add_edge" && x.proposal.source + "--" + x.proposal.type + "--" + x.proposal.target === id; });
      if (taken) errors.push(id + " already exists");
    }
    return { errors: errors, similar: similar };
  }
```

Replace `buildReview` with:

```javascript
  function buildReview(graph, decisions, reviewerName, nowIso, proposals) {
    return {
      schema_version: 2,
      graph_version: graph.graph_version,
      reviewer: { name: reviewerName },
      created: nowIso,
      decisions: decisions.concat(proposals || [])
    };
  }
```

Add to the exported object: `normalizeName: normalizeName, slugFromName: slugFromName, similarNames: similarNames,
similarNodes: similarNodes, checkProposal: checkProposal,`.

- [ ] **Step 4: Run all viewer tests**

Run: `node --test agent/concept_graph/viewer/tests/*.test.js`
Expected: PASS (existing 20-ish plus the new ones)

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/viewer/logic.js agent/concept_graph/viewer/tests/proposals.test.js agent/concept_graph/viewer/tests/logic.test.js
git commit -m "feat(concept_graph): viewer proposal logic mirrors the server rules"
```

---

### Task 5: The page: Propose menu, forms, selection button, list and ghost items

**Files:**
- Modify: `agent/concept_graph/viewer/template.html`
- Modify: `agent/concept_graph/viewer/style.css`
- Modify: `agent/concept_graph/viewer/app.js`

**Interfaces:**
- Consumes: `CG.checkProposal`, `CG.similarNodes`, `CG.slugFromName`, `CG.buildReview(…, proposals)` from Task 4;
  existing `G`, `cy`, `nodesById`, `EDGE_STYLE`, `toast`, `needName`, `persist`, `select`, `esc`, `$`, `storage`.
- Produces: no new module API; behavior is verified by the screenshot check in Step 6.

- [ ] **Step 1: Template**

In `template.html`, add inside `#review-bar` after the Clear button:

```html
    <span class="menu"><button id="btn-propose" type="button" aria-haspopup="true">Propose &#9662;</button>
      <span id="propose-menu" class="menu-body" hidden>
        <button type="button" data-propose="node">New concept</button>
        <button type="button" data-propose="edge">New connection</button>
      </span></span>
```

Add before `<div id="toast"`:

```html
<button id="btn-connect" type="button" hidden>Add connection</button>
<dialog id="propose-dialog" aria-labelledby="propose-title"><form method="dialog" id="propose-form"></form></dialog>
```

and in the sidebar, after `<nav id="name-list">`: `<section id="my-proposals" hidden><h3>Your proposals</h3><ul id="proposal-list"></ul></section>`.

- [ ] **Step 2: Styles** (append to `style.css`)

```css
.menu { position: relative; display: inline-block; }
.menu-body { position: absolute; right: 0; top: 100%; background: var(--bg); border: 1px solid var(--line, #d6d3d1); border-radius: 8px; padding: 4px; z-index: 12; display: flex; flex-direction: column; min-width: 160px; }
.menu-body[hidden] { display: none; }
#btn-connect { position: fixed; left: 50%; top: 72px; transform: translateX(-50%); z-index: 11; padding: 8px 14px; border-radius: 999px; }
#propose-dialog { border: 1px solid var(--line, #d6d3d1); border-radius: 12px; padding: 16px; max-width: min(560px, 92vw); background: var(--bg); color: var(--fg); }
#propose-form label { display: block; margin: 8px 0 2px; font-weight: 600; font-size: 0.9em; }
#propose-form input[type=text], #propose-form select, #propose-form textarea { width: 100%; box-sizing: border-box; }
#propose-form .row { display: grid; grid-template-columns: 1.4fr 1fr 1fr auto; gap: 6px; margin: 6px 0; align-items: center; }
#propose-form .errors { color: #b91c1c; margin: 8px 0; }
#propose-form .similar { background: #fef9c3; padding: 6px 8px; border-radius: 6px; margin-top: 6px; }
#propose-form .buttons { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
#my-proposals ul { list-style: none; padding: 0; margin: 0; }
#my-proposals li { display: flex; gap: 6px; justify-content: space-between; padding: 4px 0; font-size: 0.9em; }
@media (max-width: 640px) { #propose-form .row { grid-template-columns: 1fr 1fr; } }
```

- [ ] **Step 3: State, storage and ghost items in `app.js`**

Add after the `decisions` initialisation (near line 20):

```javascript
  var PROPOSAL_KEY = "cg-proposals-" + G.graph_version;
  var proposals = [];
  try { proposals = JSON.parse(storage.get(PROPOSAL_KEY) || "[]"); } catch (e) { proposals = []; }
  var KINDS = (G.vocab && G.vocab.kinds) || Array.from(new Set(G.nodes.map(function (n) { return n.kind; }))).sort();
  var pickOrder = []; // concept ids in the order they were selected, so the first one is the source
```

Replace `persist()` with a version that also saves proposals and counts them:

```javascript
  function persist() {
    storage.set(STORE_KEY, JSON.stringify(decisions));
    storage.set(PROPOSAL_KEY, JSON.stringify(proposals));
    var n = decisions.length + proposals.length;
    $("#decision-count").textContent = n + (n === 1 ? " decision" : " decisions");
    renderProposals();
  }
```

Replace `currentReview` body: `return CG.buildReview(G, decisions, reviewer.trim(), new Date().toISOString(), proposals);`.

In the Clear handler, also reset proposals: change the confirm count to `decisions.length + proposals.length`
and set `proposals = [];` next to `decisions = [];`. Replace the `if (decisions.length && ...)` guard accordingly.

Add the proposal list and ghosts (before the `// ---- start` section):

```javascript
  function proposalLabel(p) {
    return p.action === "add_node" ? "Concept: " + p.proposal.name
      : "Connection: " + nameOf(p.proposal.source) + " → " + nameOf(p.proposal.target) + " (" + p.proposal.type + ")";
  }
  function renderProposals() {
    var box = $("#my-proposals");
    box.hidden = proposals.length === 0;
    $("#proposal-list").innerHTML = proposals.map(function (p, i) {
      return "<li><span>" + esc(proposalLabel(p)) + '</span><button type="button" data-withdraw="' + i + '">Withdraw</button></li>';
    }).join("");
    cy.elements(".ghost").remove();
    var placed = new Map();
    proposals.forEach(function (p, i) {
      if (p.action !== "add_node") return;
      var id = "ghost-" + CG.slugFromName(p.proposal.name);
      var near = (p.proposal.connections || []).map(function (c) { return cy.getElementById(c.other); }).filter(function (e) { return e.nonempty(); });
      var base = near.length ? near[0].position() : { x: 0, y: 0 };
      cy.add({ group: "nodes", classes: "ghost", data: { id: id, label: p.proposal.name, color: "#78716c", status: "proposed" },
               position: { x: base.x + 60 + 40 * i, y: base.y + 90 } });
      placed.set(CG.slugFromName(p.proposal.name), id);
      (p.proposal.connections || []).forEach(function (c, k) {
        if (!cy.getElementById(c.other).nonempty()) return;
        var s = c.direction === "in" ? c.other : id, t = c.direction === "in" ? id : c.other;
        cy.add({ group: "edges", classes: "ghost", data: { id: id + "-c" + k, source: s, target: t, color: "#78716c", arrow: "triangle", status: "proposed" } });
      });
    });
    proposals.forEach(function (p, i) {
      if (p.action !== "add_edge") return;
      var s = placed.get(p.proposal.source) || p.proposal.source, t = placed.get(p.proposal.target) || p.proposal.target;
      if (cy.getElementById(s).nonempty() && cy.getElementById(t).nonempty()) {
        cy.add({ group: "edges", classes: "ghost", data: { id: "ghost-e" + i, source: s, target: t, color: "#78716c", arrow: "triangle", status: "proposed" } });
      }
    });
  }
  $("#proposal-list").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-withdraw]"); if (!b) return;
    proposals.splice(Number(b.getAttribute("data-withdraw")), 1);
    persist();
  });
```

Add the ghost style to the Cytoscape style array (next to the `node[status = 'proposed']` rule):
`{ selector: "node.ghost", style: { opacity: 0.75, "border-style": "dotted", "border-width": 3, "border-color": "#a8a29e" } },`
`{ selector: "edge.ghost", style: { opacity: 0.75, "line-style": "dotted" } },`

Ghost items are not in `G`, so two existing handlers must skip them:

- In `applyFilters`, replace the two `toggleClass("hidden", ...)` lines with
  `cy.nodes().forEach(function (n) { n.toggleClass("hidden", !n.hasClass("ghost") && !visible.has(n.id())); });`
  and, inside the edge loop, `e.toggleClass("hidden", !e.hasClass("ghost") && hide);`.
- In the two `cy.on("tap", "node", ...)` and `cy.on("tap", "edge", ...)` handlers, start with
  `if (ev.target.hasClass("ghost")) return;` so tapping a ghost never reaches `select` (the panel would look up a
  concept that does not exist yet). Withdraw is the way to remove one.

`persist()` already calls `renderProposals()`, and `persist()` runs in the start block, so no extra call is needed.

- [ ] **Step 4: Forms**

Add (before the `// ---- start` section):

```javascript
  var dialog = $("#propose-dialog"), form = $("#propose-form");
  function nodeOptions(selectedId) {
    return G.nodes.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).map(function (n) {
      return '<option value="' + esc(n.id) + '"' + (n.id === selectedId ? " selected" : "") + ">" + esc(n.name) + "</option>";
    }).join("");
  }
  function typeOptions(current) {
    return Object.keys(EDGE_STYLE).map(function (t) {
      return '<option value="' + t + '"' + (t === current ? " selected" : "") + ">" + esc(EDGE_STYLE[t].label) + "</option>";
    }).join("");
  }
  function connectionRow(c) {
    c = c || {};
    return '<div class="row" data-conn><select data-f="other">' + nodeOptions(c.other) + '</select>' +
      '<select data-f="type">' + typeOptions(c.type || "is_a") + '</select>' +
      '<select data-f="direction"><option value="out"' + (c.direction === "in" ? "" : " selected") + '>this → that</option>' +
      '<option value="in"' + (c.direction === "in" ? " selected" : "") + '>that → this</option></select>' +
      '<button type="button" data-remove-row>×</button>' +
      '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" value="' + esc(c.condition || "") + '" style="grid-column: 1 / -1">' +
      '</div>';
  }
  function openNodeForm() {
    form.innerHTML = '<h2 id="propose-title">Propose a concept</h2>' +
      '<label>Name<input type="text" id="p-name" maxlength="120"></label><div id="p-similar" class="similar" hidden></div>' +
      '<label>Kind<select id="p-kind">' + KINDS.map(function (k) { return "<option>" + esc(k) + "</option>"; }).join("") + "</select></label>" +
      '<label>Section<select id="p-section">' + G.sections.slice().sort(function (a, b) { return a.order - b.order; }).map(function (s) {
        return '<option value="' + esc(s.id) + '">' + esc(s.title || s.id) + "</option>"; }).join("") + "</select></label>" +
      '<label>Topic<select id="p-topic">' + G.vocab.topics.map(function (t) { return "<option>" + esc(t) + "</option>"; }).join("") + "</select></label>" +
      '<label>One-line note (optional, 200 characters)<input type="text" id="p-note" maxlength="200"></label>' +
      '<label>Connections (optional)</label><div id="p-conns"></div>' +
      '<button type="button" id="p-add-conn">Add a connection</button>' +
      '<div class="errors" id="p-errors" hidden></div>' +
      '<div class="buttons"><button type="button" id="p-cancel">Cancel</button><button type="button" id="p-save">Add proposal</button></div>';
    $("#p-name").addEventListener("input", function () {
      var s = CG.similarNodes(G.nodes, $("#p-name").value, 3), box = $("#p-similar");
      box.hidden = !s.length;
      box.innerHTML = s.length ? "Similar existing: " + s.map(function (n) { return esc(n.name); }).join(", ") +
        ". Propose a connection instead if it is the same idea." : "";
    });
    $("#p-add-conn").addEventListener("click", function () { $("#p-conns").insertAdjacentHTML("beforeend", connectionRow()); });
    $("#p-save").addEventListener("click", function () {
      var conns = Array.from(form.querySelectorAll("[data-conn]")).map(function (row) {
        var g = function (f) { return row.querySelector('[data-f="' + f + '"]').value; };
        return { other: g("other"), type: g("type"), direction: g("direction"), condition: g("condition").trim() || null, note: "" };
      });
      var p = { name: $("#p-name").value.trim(), kind: $("#p-kind").value, section: $("#p-section").value,
                topic: $("#p-topic").value, note: $("#p-note").value.trim(), connections: conns };
      saveProposal({ action: "add_node", proposal: p });
    });
    finishForm();
  }
  function openEdgeForm(sourceId, targetIds) {
    var rows = (targetIds && targetIds.length ? targetIds : [""]).map(function (t) { return t; });
    form.innerHTML = '<h2 id="propose-title">Propose a connection</h2>' +
      '<label>From<select id="e-source">' + nodeOptions(sourceId) + "</select></label>" +
      '<button type="button" id="e-swap" title="Swap direction">Swap direction ⇅</button>' +
      '<label>To</label><div id="e-rows"></div>' +
      '<button type="button" id="e-add">Add another target</button>' +
      '<div class="errors" id="p-errors" hidden></div>' +
      '<div class="buttons"><button type="button" id="p-cancel">Cancel</button><button type="button" id="p-save">Add proposal</button></div>';
    rows.forEach(function (t) {
      $("#e-rows").insertAdjacentHTML("beforeend", '<div class="row" data-edge-row><select data-f="target">' + nodeOptions(t) + "</select>" +
        '<select data-f="type">' + typeOptions("is_a") + '</select><span></span><button type="button" data-remove-row>×</button>' +
        '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" style="grid-column: 1 / -1"></div>');
    });
    $("#e-add").addEventListener("click", function () {
      $("#e-rows").insertAdjacentHTML("beforeend", '<div class="row" data-edge-row><select data-f="target">' + nodeOptions("") + "</select>" +
        '<select data-f="type">' + typeOptions("is_a") + '</select><span></span><button type="button" data-remove-row>×</button>' +
        '<input type="text" data-f="condition" placeholder="Condition (needed for implies / iff)" style="grid-column: 1 / -1"></div>');
    });
    $("#e-swap").addEventListener("click", function () {
      var row = form.querySelector("[data-edge-row] [data-f=target]"), src = $("#e-source");
      if (!row) return;
      var t = row.value; row.value = src.value; src.value = t;
    });
    $("#p-save").addEventListener("click", function () {
      var added = 0, source = $("#e-source").value;
      var made = Array.from(form.querySelectorAll("[data-edge-row]")).map(function (row) {
        var g = function (f) { return row.querySelector('[data-f="' + f + '"]').value; };
        return { action: "add_edge", proposal: { source: source, type: g("type"), target: g("target"), condition: g("condition").trim() || null, note: "" } };
      });
      var all = [];
      for (var i = 0; i < made.length; i++) {
        var res = CG.checkProposal(G, made[i].proposal, proposals.concat(all));
        if (res.errors.length) return showErrors(res.errors);
        all.push(made[i]);
      }
      proposals = proposals.concat(all); added = all.length;
      dialog.close(); persist(); toast(added + " connection" + (added === 1 ? "" : "s") + " added to your proposals.");
    });
    finishForm();
  }
  function showErrors(list) {
    var box = $("#p-errors"); box.hidden = false;
    box.innerHTML = list.map(function (m) { return "<div>" + esc(m) + "</div>"; }).join("");
  }
  function saveProposal(p) {
    var res = CG.checkProposal(G, p.proposal, proposals);
    if (res.errors.length) return showErrors(res.errors);
    proposals.push(p); dialog.close(); persist(); toast("Added to your proposals. Submit your review to send it.");
  }
  function finishForm() {
    form.addEventListener("click", function (ev) {
      if (ev.target.hasAttribute("data-remove-row")) ev.target.closest(".row").remove();
      if (ev.target.id === "p-cancel") dialog.close();
    });
    if (!dialog.open) dialog.showModal();
  }
  function openProposal(kind, sourceId, targetIds) {
    if (!needName()) return;
    if (kind === "node") openNodeForm(); else openEdgeForm(sourceId || "", targetIds || []);
  }

  $("#btn-propose").addEventListener("click", function () { var m = $("#propose-menu"); m.hidden = !m.hidden; });
  $("#propose-menu").addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-propose]"); if (!b) return;
    $("#propose-menu").hidden = true; openProposal(b.getAttribute("data-propose"));
  });
```

`finishForm` re-adds a click listener on every open; because `form.innerHTML` is replaced each time the old
listeners remain on the same `form` element. To avoid duplicates, register the delegated click handler once instead:
move the body of the `form.addEventListener("click", ...)` block out of `finishForm` to top level (once), and have
`finishForm` only call `dialog.showModal()` when the dialog is closed.

- [ ] **Step 5: Selection button and sidebar entry**

```javascript
  cy.on("select unselect", "node", function () {
    var ids = cy.nodes(":selected").filter(function (n) { return !n.hasClass("ghost"); }).map(function (n) { return n.id(); });
    pickOrder = pickOrder.filter(function (id) { return ids.indexOf(id) !== -1; });
    ids.forEach(function (id) { if (pickOrder.indexOf(id) === -1) pickOrder.push(id); });
    $("#btn-connect").hidden = pickOrder.length < 2;
  });
  $("#btn-connect").addEventListener("click", function () {
    openProposal("edge", pickOrder[0], pickOrder.slice(1));
  });
```

In `renderNode` (app.js ~line 264), add to the node panel's action row a button
`'<button type="button" data-act="propose-from">Propose a connection from this concept</button>'` and handle it in the
`#panel` click handler next to the other `data-act` cases:
`if (act === "propose-from") return openProposal("edge", selected.id, []);`.

- [ ] **Step 6: Build and verify**

Run: `python -m agent.concept_graph.cli --graph-repo agent/concept_graph/sample_data build` (builds into the sample
repo; do not commit its `index.html`/`build/`), then a headless screenshot:

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --virtual-time-budget=6000 \
  --window-size=1400,900 --screenshot=propose.png "file:///<abs path>/sample_data/index.html"
```

Expected: page renders with a "Propose" button in the top bar. Then run
`python -m pytest tests/agent/concept_graph/test_cg_viewer_logic.py tests/agent/concept_graph/test_cg_build.py -q`
(the build test checks the template placeholders and that `app.js` parses).
Manual check list (open the built page in a browser): Propose menu opens; New concept shows the three dropdowns and
the similar-names hint while typing; Shift-click two concepts shows "Add connection"; saved proposals appear in "Your
proposals" and as dotted ghost items; Withdraw removes them; Download review contains `schema_version: 2` and the
`add_node`/`add_edge` decisions.

- [ ] **Step 7: Commit**

```bash
git add agent/concept_graph/viewer/template.html agent/concept_graph/viewer/style.css agent/concept_graph/viewer/app.js
git commit -m "feat(concept_graph): propose concepts and connections from the page"
```

---

### Task 6: Round trip, documentation and tracker

**Files:**
- Modify: `agent/concept_graph/README.md` (reviewer section)
- Modify: `docs/trackers/academic_hub_to_do.md` (TODO-0070 line)
- Create: `docs/status/agent/concept_graph/2026-10-14-concept-graph-proposals-status.md`
- Test: `tests/agent/concept_graph/test_cg_apply_proposals.py` (append)

- [ ] **Step 1: Add the round-trip test**

Append:

```python
def test_a_viewer_style_review_round_trips_through_the_cli_and_build(store, tmp_path, capsys):
    from agent.concept_graph.cli import main
    g = store.read_all()
    other = g.nodes[0].id
    payload = {"schema_version": 2, "graph_version": "v", "reviewer": {"name": "Ada"}, "created": "t",
               "decisions": [add_node("Quasi concavity", note="Upper sets are convex.",
                                      connections=[{"other": other, "type": "is_a", "direction": "out"}])]}
    f = tmp_path / "review.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["--graph-repo", str(store.root), "apply-review", str(f), "--today", "2026-10-20"]) == 0
    out = capsys.readouterr().out
    assert "proposals: " in out and "quasi-concavity" in out
    assert main(["--graph-repo", str(store.root), "validate"]) == 0
    assert main(["--graph-repo", str(store.root), "build"]) == 0
    built = json.loads((store.root / "build" / "graph.json").read_text(encoding="utf-8"))
    assert any(n["id"] == "quasi-concavity" and n["status"] == "proposed" for n in built["nodes"])
```

Run: `python -m pytest tests/agent/concept_graph/test_cg_apply_proposals.py -q` — Expected: PASS.

- [ ] **Step 2: README section**

Add under the reviewer/review loop section of `agent/concept_graph/README.md`: what Propose does, that
`apply-review` handles proposals in one pass per round (duplicates merge, near-duplicates of an existing concept turn
into edge proposals plus a comment, conflicts go to `review-conflicts.md`), and the follow-up commands:
`collect fill --node <id>` for each new concept, then `collect link --node <id> --redo`, then `collect critic`.

- [ ] **Step 3: Tracker and status**

In `docs/trackers/academic_hub_to_do.md`, mark TODO-0070 done in place: append `DONE 2026-10-14 (see
docs/status/agent/concept_graph/2026-10-14-concept-graph-proposals-status.md)` to that bullet (do not move it).
Create the status doc: what shipped, the decisions made in the spec, the test commands, and the open items (a
reconcile stage that rewrites merged notes; drag-to-connect; proposing a new section; `via` theorem).

- [ ] **Step 4: Full verification**

Run: `python -m pytest tests/agent/concept_graph -q` and `node --test agent/concept_graph/viewer/tests/*.test.js`
Expected: all pass, no `SyntaxWarning` (see `test_cg_no_syntax_warnings.py`).

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/README.md docs/trackers/academic_hub_to_do.md docs/status/agent/concept_graph/2026-10-14-concept-graph-proposals-status.md tests/agent/concept_graph/test_cg_apply_proposals.py
git commit -m "docs(concept_graph): reviewer proposals README, status and tracker"
```
