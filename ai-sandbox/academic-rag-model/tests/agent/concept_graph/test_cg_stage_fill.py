from agent.concept_graph.stages import fill
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, PASSAGE_TEXT, blank_explanations, copy_sample, entry_for

PROV = {"driver": "agent", "agent": "test-agent", "run": "r1"}
GOOD = {
    "gist": "A relation that ranks things without forbidding ties.",
    "explanation": "Two properties define it: every element relates to itself, and comparisons chain together.",
    "citations": [{"source": "rubinstein", "ref": "ch. 2, p. 12"}],
}


def tasks_for(store, **kw):
    return fill.make_tasks(store, FakeRetriever(), **kw)


def one(tmp_path, node="preorder"):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, [node])
    task = tasks_for(store, nodes=[node])[0]
    return store, task, entry_for(task)


def test_makes_one_task_per_unfilled_node_in_taught_sections_only(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder", "warp"])
    ids = sorted(t.subject["node"] for t in tasks_for(store))
    assert ids == ["preorder", "warp"]  # walrasian-demand is unfilled too but its section is planned


def test_a_section_filter_narrows_the_tasks(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder", "warp"])
    assert [t.subject["node"] for t in tasks_for(store, section="s02-choice")] == ["warp"]


def test_verified_nodes_are_skipped_and_planned_ones_only_when_named(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder"])
    store.update_item("node", "preorder", {"status": "verified"})
    assert tasks_for(store) == []
    assert [t.subject["node"] for t in tasks_for(store, nodes=["walrasian-demand"])] == ["walrasian-demand"]


def test_redo_regenerates_a_proposed_node_but_never_a_verified_one(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    assert tasks_for(store, nodes=["total-order"]) == []  # already filled
    assert [t.subject["node"] for t in tasks_for(store, nodes=["total-order"], redo=True)] == ["total-order"]
    store.update_item("node", "total-order", {"status": "verified"})
    assert tasks_for(store, nodes=["total-order"], redo=True) == []


def test_card_carries_neighbours_offered_passages_and_the_query(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder"])
    retriever = FakeRetriever()
    task = fill.make_tasks(store, retriever, nodes=["preorder"])[0]
    assert "Preorder is a Binary relation" in task.context
    assert [p.id for p in task.passages] == ["P1", "P2"]
    assert "Preorder" in retriever.queries[0]


def test_valid_result_is_accepted(tmp_path):
    store, task, entry = one(tmp_path)
    assert fill.validate_result(entry, GOOD, store) == []


def test_copied_explanation_is_bounced_with_the_shared_words(tmp_path):
    store, task, entry = one(tmp_path)
    bad = dict(GOOD, explanation="Note that a binary relation that is reflexive and transitive and nothing more is a preorder.")
    msgs = fill.validate_result(entry, bad, store)
    assert len(msgs) == 1 and msgs[0].startswith("explanation") and "reflexive" in msgs[0]


def test_formal_may_match_a_passage(tmp_path):
    store, task, entry = one(tmp_path)
    ok = dict(GOOD, formal="A preorder is a binary relation that is reflexive and transitive and nothing more")
    assert fill.validate_result(entry, ok, store) == []


def test_invented_citation_missing_citations_and_unknown_keys_are_bounced(tmp_path):
    store, task, entry = one(tmp_path)
    assert any("not offered" in m for m in fill.validate_result(entry, dict(GOOD, citations=[{"source": "mwg", "ref": "ch. 99"}]), store))
    assert any("citation" in m for m in fill.validate_result(entry, {k: v for k, v in GOOD.items() if k != "citations"}, store))
    assert any("unknown" in m for m in fill.validate_result(entry, dict(GOOD, status="verified"), store))


def test_gist_must_be_one_short_line_and_explanation_present(tmp_path):
    store, task, entry = one(tmp_path)
    assert any("gist" in m for m in fill.validate_result(entry, dict(GOOD, gist="two\nlines"), store))
    assert any("gist" in m for m in fill.validate_result(entry, dict(GOOD, gist="x" * 161), store))
    assert any("explanation" in m for m in fill.validate_result(entry, dict(GOOD, explanation=" "), store))


def test_apply_writes_proposed_with_provenance(tmp_path):
    store, task, entry = one(tmp_path)
    assert fill.apply_result(store, entry, dict(GOOD, formal="$R$ is reflexive and transitive."), PROV) is None
    node = next(n for n in store.read_all().nodes if n.id == "preorder")
    assert node.explanation.startswith("Two properties") and node.status == "proposed"
    assert node.formal == "$R$ is reflexive and transitive."
    assert node.provenance.run == "r1" and node.provenance.agent == "test-agent"
    assert [(c.source, c.ref) for c in node.citations] == [("rubinstein", "ch. 2, p. 12")]


def test_apply_never_overwrites_a_node_verified_since_collect(tmp_path):
    store, task, entry = one(tmp_path)
    store.update_item("node", "preorder", {"status": "verified", "explanation": "A person wrote this."})
    reason = fill.apply_result(store, entry, GOOD, PROV)
    assert reason and "verified" in reason
    assert next(n for n in store.read_all().nodes if n.id == "preorder").explanation.strip() == "A person wrote this."


def test_the_fixture_text_really_is_what_the_guard_compares_against():
    assert "reflexive and transitive" in PASSAGE_TEXT
