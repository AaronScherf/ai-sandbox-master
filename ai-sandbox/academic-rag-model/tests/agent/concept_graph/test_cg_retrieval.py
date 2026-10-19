import sys
import types
from types import SimpleNamespace

from agent.concept_graph.retrieval import IndexRetriever


def test_index_retriever_maps_the_repos_passages_to_source_and_ref(monkeypatch):
    calls = []

    def retrieve_passages(roots, query, client, course=None, top_k=6, **kw):
        calls.append((roots, query, client, course, top_k))
        return [SimpleNamespace(
            path="C:/hub/academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md",
            citation="§1.B, p. 5", text="body text")]

    fake = types.ModuleType("agent.rag.rag_agent")
    fake.retrieve_passages = retrieve_passages
    monkeypatch.setitem(sys.modules, "agent.rag.rag_agent", fake)
    client = object()
    got = IndexRetriever("C:/hub", "microecon", client).retrieve("preference relation", 4)
    assert calls == [(["C:/hub"], "preference relation", client, "microecon", 4)]
    assert [(p.source, p.ref, p.text) for p in got] == [("press", "ch. 1, §1.B, p. 5", "body text")]


def test_index_retriever_uses_the_catalog_for_book_keys(monkeypatch):
    from core.course_materials import Catalog, Material

    path = "C:/hub/academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md"

    def retrieve_passages(roots, query, client, course=None, top_k=6, **kw):
        return [SimpleNamespace(path=path, citation="", text="t")]

    fake = types.ModuleType("agent.rag.rag_agent")
    fake.retrieve_passages = retrieve_passages
    monkeypatch.setitem(sys.modules, "agent.rag.rag_agent", fake)
    cat = Catalog(course="microecon", materials=[Material(
        path="academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md",
        role="textbook", format="chapter", book="mwg")])
    got = IndexRetriever("C:/hub", "microecon", object(), catalog=cat).retrieve("q", 1)
    assert (got[0].source, got[0].ref) == ("mwg", "ch. 1")
