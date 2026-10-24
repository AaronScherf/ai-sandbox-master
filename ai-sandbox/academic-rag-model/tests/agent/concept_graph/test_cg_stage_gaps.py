"""The syllabus-gap card and proposal submit path use local fixture material only."""
from __future__ import annotations

from core.course_materials.model import Catalog, Material
from agent.concept_graph import cli
from agent.concept_graph.stages import gaps
from agent.concept_graph.store import GraphStore
from cg_helpers import copy_sample, entry_for


SYLLABUS = """Topics
1. Time Series Regression and Forecasting (2 classes):
   • Dynamic causal effects SW 16.2, 16.3, 16.5
   • HAC and HAR standard errors, SW 16.4
2. Choice:
   • Demand correspondence CT 13.3
"""
STOCK = """# Estimation of Dynamic Causal Effects 16
## 16.2 Dynamic Causal Effects
### Dynamic multipliers
## 16.3 Estimation with Exogenous Regressors
## 16.4 HAC Standard Errors
## 16.5 Strict Exogeneity
"""
CAMERON = "# Demand 13\n## 13.3 Demand Correspondence\n"


def fixture(tmp_path):
    root = copy_sample(tmp_path)
    (root / "config" / "seed.yaml").write_text(
        "reading_aliases: {SW: stock, CT: cameron}\n", encoding="utf-8")
    hub = tmp_path / "hub"
    paths = {
        "academic_notes/econ/syllabus/ECON6411.md": SYLLABUS,
        "academic_notes/econ/textbooks/stock/chapters/15_dynamic.rag.md": STOCK,
        "academic_notes/econ/textbooks/cameron/chapters/12_demand.rag.md": CAMERON,
    }
    for relative, content in paths.items():
        file = hub / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    catalog = Catalog(course="econ", materials=[
        Material(path=path, role="syllabus" if "syllabus" in path else "textbook",
                 book=None if "syllabus" in path else path.split("/")[3], flagged=False)
        for path in paths
    ])
    return GraphStore(root), hub, catalog


def test_card_covers_all_assignments_headings_and_nodes_despite_filename_numbers(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    task = gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)[0]
    card = task.context
    for phrase in ("Dynamic causal effects SW 16.2, 16.3, 16.5", "HAC and HAR", "Demand correspondence CT 13.3",
                   "16.2 Dynamic Causal Effects", "Dynamic multipliers", "16.3 Estimation", "16.4 HAC",
                   "16.5 Strict Exogeneity", "13.3 Demand Correspondence", "s03-demand", "Walrasian demand",
                   "s01-binary-relations", "Preorder"):
        assert phrase in card
    assert len(gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)) == 1


def test_missing_assigned_reading_is_an_error_instead_of_a_silent_omission(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    (hub / catalog.materials[1].path).write_text(STOCK.replace("## 16.4 HAC Standard Errors\n", ""), encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="SW 16.4"):
        gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)


def test_realistic_hansen_and_cameron_heading_formats():
    hansen = '## <span id="page-96-0"></span>CHAPTER 3 THE ALGEBRA OF LEAST SQUARES\n#### 3.1 INTRODUCTION\n#### 3.2 SAMPLES\n'
    cameron = '# **Bayesian Methods**\n## **13.2. Bayesian Approach**\n## **13.3. Bayesian Analysis of Linear Regression**\n'
    chapter, headings = gaps._headings(hansen)
    assert chapter == 3
    assert gaps._assigned_headings(headings, 3, 2) == ["3.2 SAMPLES"]
    chapter, headings = gaps._headings(cameron)
    assert chapter == 13
    assert gaps._assigned_headings(headings, 13, 3) == ["13.3. Bayesian Analysis of Linear Regression"]


def test_assigned_heading_can_be_recovered_from_textbook_contents():
    contents = "**7 Hypothesis Tests** 223 **7.1** Introduction 223 **7.2** Wald Test 224 **7.3** Likelihood-Based Tests 233\n"
    assert gaps._toc_heading(contents, 7, 2) == "7.2 Wald Test [contents only; section text unavailable]"


def test_card_labels_table_of_contents_fallback(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    chapter = hub / catalog.materials[2].path
    chapter.write_text("# Demand 13\n## 13.4 Another section\n", encoding="utf-8")
    relative = "academic_notes/econ/textbooks/cameron/chapters/00_front_matter.rag.md"
    front = hub / relative
    front.write_text("**13 Bayesian Methods** 411 **13.3** Demand Correspondence 420\n", encoding="utf-8")
    catalog.materials.append(Material(path=relative, role="textbook", book="cameron", flagged=False))
    task = gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)[0]
    assert "13.3 Demand Correspondence [contents only; section text unavailable]" in task.context


def test_unknown_syllabus_book_abbreviation_is_reported(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    syllabus = hub / catalog.materials[0].path
    import pytest
    for reading in ("XYZ 13.3", "XYZ 13"):
        syllabus.write_text(SYLLABUS.replace("CT 13.3", reading), encoding="utf-8")
        with pytest.raises(ValueError, match="XYZ"):
            gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)


def test_submit_routes_proposals_through_clustering_and_tombstones(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    store.add_rejected("node", "forbidden-concept")
    task = gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)[0]
    entry = entry_for(task)
    result = {"proposals": [
        {"name": "Distributed lag model", "kind": "model", "section": "s03-demand", "topic": "demand",
         "note": "SW 16.2: a lagged regressor model"},
        {"name": "Distributed lag model equation", "kind": "model", "section": "s03-demand", "topic": "demand",
         "note": "SW 16.2: same model"},
        {"name": "Forbidden concept", "kind": "model", "section": "s03-demand", "topic": "demand",
         "note": "SW 16.3: excluded earlier"},
    ], "edges": []}
    assert gaps.validate_result(entry, result, store) == []
    gaps.apply_result(store, entry, result, {"driver": "agent", "agent": "gap-agent", "run": "g1"})
    graph = store.read_all()
    assert len([n for n in graph.nodes if n.name.startswith("Distributed lag model")]) == 1
    assert not any(n.id == "forbidden-concept" for n in graph.nodes)
    assert "rejected earlier" in (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert next(n for n in graph.nodes if n.id == "distributed-lag-model-equation").status == "proposed"


def test_stale_input_bounces_and_empty_result_is_valid(tmp_path):
    store, hub, catalog = fixture(tmp_path)
    task = gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)[0]
    entry = entry_for(task)
    assert gaps.validate_result(entry, {"proposals": [], "edges": []}, store) == []
    syllabus = hub / catalog.materials[0].path
    syllabus.write_text(SYLLABUS + "   • Extra topic SW 16.2\n", encoding="utf-8")
    assert any("stale" in error for error in gaps.validate_result(entry, {"proposals": [], "edges": []}, store))
    fresh = gaps.make_tasks(store, None, hub_root=str(hub), course="econ", catalog=catalog)[0]
    store.add_rejected("node", "newly-rejected")
    assert any("stale" in error for error in gaps.validate_result(entry_for(fresh),
                                                                   {"proposals": [], "edges": []}, store))


def test_cli_collect_submit_is_idempotent_and_does_not_make_a_retriever(tmp_path, monkeypatch, capsys):
    store, hub, catalog = fixture(tmp_path)
    monkeypatch.setattr(cli, "_catalog", lambda args: catalog)
    work = tmp_path / "work"
    argv = ["--graph-repo", str(store.root)]
    no_retriever = lambda args: (_ for _ in ()).throw(AssertionError("retriever was created"))
    assert cli.main(argv + ["collect", "gaps", "--hub-root", str(hub), "--course", "econ",
                            "--work-dir", str(work), "--run-id", "g1"], retriever_factory=no_retriever) == 0
    card = work / "g1" / "cards" / "gaps.md"
    answer = "proposals:\n  - {name: Dynamic multiplier, kind: model, section: s03-demand, topic: demand, note: 'SW 16.2: response path'}\nedges: []\n"
    card.write_text(card.read_text(encoding="utf-8").replace("```yaml\n```", f"```yaml\n{answer}```"), encoding="utf-8")
    submit = argv + ["submit", "g1", "--work-dir", str(work), "--agent-name", "gap-agent"]
    assert cli.main(submit, retriever_factory=no_retriever) == 0
    assert cli.main(submit, retriever_factory=no_retriever) == 0
    assert "0 applied" in capsys.readouterr().out
    assert len([n for n in store.read_all().nodes if n.name == "Dynamic multiplier"]) == 1
