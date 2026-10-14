"""Retrieval keeps working when a Gemini key is out of quota; orphan and hint options for the collect stages."""
import json

import pytest

from agent.concept_graph.cli import main
from agent.concept_graph.retrieval import LexicalRetriever, ResilientRetriever
from agent.concept_graph.sources import Passage
from agent.concept_graph.stages import fill
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, blank_explanations, copy_sample

OK = [Passage(id="", source="mwg", ref="ch. 1", text="found")]


class Backend:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def retrieve(self, query, top_k=6):
        self.calls += 1
        if self.error:
            raise self.error
        return OK


def test_a_quota_failure_moves_to_the_next_backend_and_stays_there():
    notes = []
    paid, free = Backend(RuntimeError("429 RESOURCE_EXHAUSTED: monthly spending cap")), Backend()
    r = ResilientRetriever([("paid key", paid), ("free key", free)], notify=notes.append)
    assert r.retrieve("a") == OK and r.retrieve("b") == OK
    assert paid.calls == 1 and free.calls == 2  # the paid key is not retried
    assert len(notes) == 1 and "free key" in notes[0]


def test_an_error_that_is_not_about_quota_is_raised_not_hidden():
    r = ResilientRetriever([("paid key", Backend(ValueError("bad index"))), ("keyword", Backend())])
    with pytest.raises(ValueError):
        r.retrieve("a")


def test_the_last_backend_failing_raises():
    r = ResilientRetriever([("paid key", Backend(RuntimeError("429 quota"))), ("free key", Backend(RuntimeError("429 quota")))])
    with pytest.raises(RuntimeError):
        r.retrieve("a")


def hub_with_chunks(tmp_path):
    hub = tmp_path / "hub"
    (hub / ".index" / "chunks").mkdir(parents=True)
    note = "academic_notes/microecon/professor_notes/processed_outputs/6.Consumer_Choice_1.md"
    (hub / ".index" / "microecon.json").write_text(json.dumps([{"file_id": "f1", "path": note}, {"file_id": "f2", "path": note}]),
                                                   encoding="utf-8")
    chunks = [
        {"chunk_id": "c1", "file_id": "f1", "text": "The Slutsky equation splits a price change into substitution and income effects.",
         "heading_path": ["Slutsky"], "page_range": [3, 3]},
        {"chunk_id": "c2", "file_id": "f1", "text": "A budget set is the bundles a consumer can afford.", "page_range": [1, 1]},
        {"chunk_id": "c3", "file_id": "f2", "text": "Expected utility under risk aversion.", "page_range": [9, 9]},
    ]
    (hub / ".index" / "chunks" / "microecon.json").write_text(json.dumps(chunks), encoding="utf-8")
    return str(hub)


def test_keyword_retrieval_ranks_by_overlap_and_names_the_source(tmp_path):
    got = LexicalRetriever(hub_with_chunks(tmp_path), "microecon").retrieve("Slutsky equation substitution effect", 2)
    assert got[0].text.startswith("The Slutsky equation")
    assert (got[0].source, got[0].ref) == ("slides", "Consumer Choice 1")
    assert all("budget" not in p.text for p in got)  # no overlap, not offered


def test_keyword_retrieval_returns_nothing_when_no_term_matches(tmp_path):
    assert LexicalRetriever(hub_with_chunks(tmp_path), "microecon").retrieve("zzzz qqqq", 3) == []


def test_fill_card_shows_the_owners_request_for_that_node(tmp_path):
    root = copy_sample(tmp_path)
    store = GraphStore(root)
    blank_explanations(store, ["preorder"])
    cfg = root / "config" / "seed.yaml"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text("fill_hints:\n  preorder: Cover the two-commodity case with a worked example.\n", encoding="utf-8")
    task = fill.make_tasks(store, FakeRetriever(), nodes=["preorder"])[0]
    assert "worked example" in task.context and "also covers" in task.context
    assert "worked example" not in fill.make_tasks(GraphStore(copy_sample(tmp_path / "other")), FakeRetriever(),
                                                  nodes=["preorder"], redo=True)[0].context


def test_collect_orphans_picks_only_explained_nodes_without_edges(tmp_path, capsys):
    root = copy_sample(tmp_path)
    store = GraphStore(root)
    graph = store.read_all()
    linked = {end for e in graph.edges for end in (e.source, e.target, e.via)}
    orphans = [n.id for n in graph.nodes if n.id not in linked and n.explanation.strip()]
    work = tmp_path / "work"
    rc = main(["--graph-repo", str(root), "collect", "link", "--orphans", "--work-dir", str(work), "--run-id", "o1"],
              retriever_factory=lambda a: FakeRetriever())
    out = capsys.readouterr().out.lower()
    assert rc == 0
    if orphans:
        cards = sorted(p.stem for p in (work / "o1" / "cards").glob("*.md"))
        assert cards == sorted(f"link-{i}" for i in orphans)
    else:
        assert "nothing to do" in out
