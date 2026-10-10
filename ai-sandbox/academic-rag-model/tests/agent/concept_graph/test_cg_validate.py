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
