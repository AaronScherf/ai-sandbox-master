from agent.concept_graph.stages import link
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, copy_sample, entry_for

PROV = {"driver": "agent", "agent": "test-agent", "run": "r1"}
CITE = [{"source": "rubinstein", "ref": "ch. 2, p. 12"}]
NEW = {"id": "choice-function", "name": "Choice function", "kind": "object", "section": "s02-choice",
       "topic": "revealed-preference", "gist": "Picks from each menu.", "explanation": "A rule that picks.", "status": "proposed"}


def store_with_new_node(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.add_nodes("s02-choice", [NEW])
    return store


def edge(**kw):
    base = {"source": "choice-function", "type": "defined_on", "target": "set",
            "explanation": "Menus and choices are drawn from one set of alternatives.", "citations": CITE}
    base.update(kw)
    return base


def prepared(tmp_path, node="choice-function", **kw):
    store = store_with_new_node(tmp_path)
    task = link.make_tasks(store, FakeRetriever(), nodes=[node], **kw)[0]
    return store, task, entry_for(task)


def test_task_per_filled_node_without_edges_and_card_lists_all_candidate_ids(tmp_path):
    store = store_with_new_node(tmp_path)
    tasks = link.make_tasks(store, FakeRetriever())
    assert [t.subject["node"] for t in tasks] == ["choice-function"]  # every other node already has edges
    for node_id in ("set", "warp", "preorder", "walrasian-demand"):
        assert f"- {node_id} |" in tasks[0].context
    assert "choice-function |" not in tasks[0].context  # the subject is not offered as its own neighbour


def test_nodes_that_already_have_edges_are_skipped_unless_redo(tmp_path):
    store = store_with_new_node(tmp_path)
    assert link.make_tasks(store, FakeRetriever(), nodes=["preorder"]) == []
    t = link.make_tasks(store, FakeRetriever(), nodes=["preorder"], redo=True)
    assert "Preorder is a Binary relation" in t[0].context  # existing edges are shown so they are not repeated


def test_unfilled_nodes_are_not_linked_yet(tmp_path):
    store = store_with_new_node(tmp_path)
    store.update_item("node", "choice-function", {"explanation": ""})
    assert link.make_tasks(store, FakeRetriever()) == []


def test_valid_result_is_accepted(tmp_path):
    store, task, entry = prepared(tmp_path)
    assert link.validate_result(entry, {"edges": [edge()]}, store) == []


def test_empty_edges_is_valid_and_applies_nothing(tmp_path):
    store, task, entry = prepared(tmp_path)
    assert link.validate_result(entry, {"edges": []}, store) == []
    before = len(store.read_all().edges)
    assert link.apply_result(store, entry, {"edges": []}, PROV) is None
    assert len(store.read_all().edges) == before


def test_unknown_endpoint_type_and_extra_keys_are_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    assert any("ghost" in m for m in link.validate_result(entry, {"edges": [edge(target="ghost")]}, store))
    assert any("befriends" in m for m in link.validate_result(entry, {"edges": [edge(type="befriends")]}, store))
    assert any("unknown" in m for m in link.validate_result(entry, {"edges": [edge(id="x")]}, store))
    assert any("unknown" in m for m in link.validate_result(entry, {"edges": [edge()], "extra": 1}, store))


def test_edge_not_touching_the_task_node_is_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    msgs = link.validate_result(entry, {"edges": [edge(source="preorder", target="set", type="defined_on")]}, store)
    assert any("choice-function" in m for m in msgs)


def test_a_self_loop_is_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    assert any("itself" in m for m in link.validate_result(entry, {"edges": [edge(target="choice-function")]}, store))


def test_implies_without_condition_is_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    msgs = link.validate_result(entry, {"edges": [edge(type="implies", target="warp")]}, store)
    assert any("condition" in m for m in msgs)
    assert link.validate_result(entry, {"edges": [edge(type="implies", target="warp", condition="menus are rich")]}, store) == []


def test_via_must_be_a_theorem_and_only_on_implies_or_iff(tmp_path):
    store, task, entry = prepared(tmp_path)
    ok = edge(type="implies", target="warp", condition="c", via="szpilrajn-extension")
    assert link.validate_result(entry, {"edges": [ok]}, store) == []
    assert any("via" in m for m in link.validate_result(entry, {"edges": [dict(ok, via="set")]}, store))
    assert any("via" in m for m in link.validate_result(entry, {"edges": [edge(via="szpilrajn-extension")]}, store))


def test_an_edge_that_already_exists_is_skipped_not_bounced(tmp_path):
    store, task, entry = prepared(tmp_path, node="preorder", redo=True)
    dup = {"source": "preorder", "type": "is_a", "target": "binary-relation", "explanation": "Already there.", "citations": CITE}
    assert link.validate_result(entry, {"edges": [dup]}, store) == []


def test_tombstoned_edge_is_not_reproposed(tmp_path):
    store, task, entry = prepared(tmp_path)
    store.add_rejected("edge", "choice-function--defined_on--set")
    assert any("rejected" in m for m in link.validate_result(entry, {"edges": [edge()]}, store))


def test_two_identical_edges_in_one_result_is_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    assert any("twice" in m for m in link.validate_result(entry, {"edges": [edge(), edge()]}, store))


def test_copied_explanation_and_invented_citation_are_bounced(tmp_path):
    store, task, entry = prepared(tmp_path)
    copied = edge(explanation="A preorder is a binary relation that is reflexive and transitive and nothing more.")
    assert any("explanation" in m for m in link.validate_result(entry, {"edges": [copied]}, store))
    invented = edge(citations=[{"source": "mwg", "ref": "ch. 99"}])
    assert any("not offered" in m for m in link.validate_result(entry, {"edges": [invented]}, store))


def test_edge_that_would_create_a_definitional_cycle_is_bounced(tmp_path):
    store = store_with_new_node(tmp_path)
    task = link.make_tasks(store, FakeRetriever(), nodes=["choice-structure"], redo=True)[0]
    cyc = edge(source="set", type="defined_on", target="choice-structure")  # choice-structure is already defined on set
    msgs = link.validate_result(entry_for(task), {"edges": [dict(cyc)]}, store)
    assert any("cycle" in m for m in msgs)


def test_apply_computes_canonical_ids_and_writes_proposed_edges(tmp_path):
    store, task, entry = prepared(tmp_path)
    result = {"edges": [edge(), edge(type="implies", target="warp", condition="menus are rich", via="szpilrajn-extension")]}
    assert link.apply_result(store, entry, result, PROV) is None
    g = store.read_all()
    by_id = {e.id: e for e in g.edges}
    assert "choice-function--defined_on--set" in by_id
    imp = by_id["choice-function--implies--warp"]
    assert imp.status == "proposed" and imp.via == "szpilrajn-extension" and imp.provenance.run == "r1"
    assert imp.condition == "menus are rich"


def test_apply_skips_an_edge_that_appeared_meanwhile_and_still_applies_the_rest(tmp_path):
    store, task, entry = prepared(tmp_path)
    store.add_edges([{"id": "choice-function--defined_on--set", "source": "choice-function", "type": "defined_on",
                      "target": "set", "status": "proposed"}])
    other = edge(type="implies", target="warp", condition="menus are rich", via="szpilrajn-extension")
    assert link.apply_result(store, entry, {"edges": [edge(), other]}, PROV) is None
    ids = {e.id for e in store.read_all().edges}
    assert "choice-function--implies--warp" in ids


def test_a_result_of_only_existing_edges_applies_nothing_and_is_fine(tmp_path):
    store, task, entry = prepared(tmp_path)
    store.add_edges([{"id": "choice-function--defined_on--set", "source": "choice-function", "type": "defined_on",
                      "target": "set", "status": "proposed"}])
    assert link.apply_result(store, entry, {"edges": [edge()]}, PROV) is None
