import sys
import types
from types import SimpleNamespace

from agent.concept_graph.retrieval import OVERFETCH, IndexRetriever


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
    assert calls == [(["C:/hub"], "preference relation", client, "microecon", 4 + OVERFETCH)]
    assert [(p.source, p.ref, p.text) for p in got] == [("press", "ch. 1, §1.B, p. 5", "body text")]


def test_index_retriever_drops_excluded_files_and_second_copies(monkeypatch):
    from core.course_materials import Catalog

    n = "C:/hub/academic_notes/econometrics"
    syllabus = "Part A consists of 13 classes. Topics: linear regression, hypothesis testing, Bayesian estimation."
    found = [SimpleNamespace(path=f"{n}/syllabus/processed_outputs/ec6411A.md", citation="", text=syllabus),
             SimpleNamespace(path=f"{n}/syllabus/ECON6411_syllabus.md", citation="", text=syllabus),
             SimpleNamespace(path=f"{n}/notes/copy_b.md", citation="", text="Gauss Markov: OLS is BLUE under A1 to A4."),
             SimpleNamespace(path=f"{n}/notes/copy_c.md", citation="", text="Gauss Markov:\nOLS is BLUE under A1 to A4."),
             SimpleNamespace(path=f"{n}/notes/other.md", citation="", text="The delta method linearizes g at theta.")]
    fake = types.ModuleType("agent.rag.rag_agent")
    fake.retrieve_passages = lambda roots, query, client, course=None, top_k=6, **kw: found[:top_k]
    monkeypatch.setitem(sys.modules, "agent.rag.rag_agent", fake)
    cat = Catalog(course="econometrics", materials=[],
                  excluded=["academic_notes/econometrics/syllabus/processed_outputs/ec6411A.md"])
    got = IndexRetriever("C:/hub", "econometrics", object(), catalog=cat).retrieve("q", 3)
    assert [p.path.rsplit("/", 1)[-1] for p in got] == ["ECON6411_syllabus.md", "copy_b.md", "other.md"]


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
