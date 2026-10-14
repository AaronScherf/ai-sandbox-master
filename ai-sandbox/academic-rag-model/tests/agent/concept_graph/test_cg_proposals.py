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
