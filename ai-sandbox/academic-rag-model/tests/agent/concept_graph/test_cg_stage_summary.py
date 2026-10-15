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
