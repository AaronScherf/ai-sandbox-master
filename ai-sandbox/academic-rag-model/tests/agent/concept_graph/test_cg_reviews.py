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


def test_reject_of_an_item_someone_else_already_verified_is_a_conflict_not_a_deletion(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    apply_review(store, review("Ada", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"}), TODAY)
    rep = apply_review(store, review("Bo", {"target": {"kind": "node", "id": "preorder"}, "action": "reject"}), TODAY)
    g = store.read_all()
    assert node(g, "preorder").status == "verified"  # still there
    assert g.rejected == []  # no tombstone
    assert len(rep.conflicts) == 1 and not rep.applied
    text = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "Bo" in text and "node preorder" in text


def test_rejecting_a_theorem_clears_via_on_edges_that_named_it_instead_of_breaking_the_build(tmp_path):
    from agent.concept_graph.validate import errors, validate
    root = copy_sample(tmp_path)
    path = root / "data" / "edges" / "s02-choice.yaml"
    path.write_text(path.read_text(encoding="utf-8") + (
        "- id: reflexivity--implies--transitivity\n  source: reflexivity\n  type: implies\n  target: transitivity\n"
        "  condition: just for the test\n  via: szpilrajn-extension\n  status: proposed\n"), encoding="utf-8")
    store = GraphStore(root)
    rep = apply_review(store, review("Ada", {"target": {"kind": "node", "id": "szpilrajn-extension"}, "action": "reject"}), TODAY)
    g = store.read_all()
    kept = next(e for e in g.edges if e.id == "reflexivity--implies--transitivity")
    assert kept.via is None
    assert errors(validate(g)) == []
    assert any("via" in line for line in rep.applied)


def test_rejecting_a_node_reports_the_edges_it_took_with_it(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    rep = apply_review(store, review("Ada", {"target": {"kind": "node", "id": "reflexivity"}, "action": "reject"}), TODAY)
    assert any("preorder--has_property--reflexivity" in line for line in rep.applied)
