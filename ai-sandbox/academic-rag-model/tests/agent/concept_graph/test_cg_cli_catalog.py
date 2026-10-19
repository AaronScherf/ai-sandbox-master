from agent.concept_graph import cli
from agent.concept_graph.scaffold import scaffold
from core.course_materials import record_decision


def setup(tmp_path):
    graph = tmp_path / "graph"
    scaffold(graph, "someone/g", "Some One", 2026, fetch_text=lambda url: "license")
    hub = tmp_path / "hub"
    s = hub / "academic_notes" / "demo" / "syllabus" / "processed_outputs" / "Syllabus.md"
    s.parent.mkdir(parents=True)
    s.write_text("Topics: regression.\n", encoding="utf-8")  # path word only: flagged
    return graph, hub


def args(graph, hub, *extra):
    return ["--graph-repo", str(graph), "collect", "seed", "--hub-root", str(hub), "--course", "demo",
            "--work-dir", str(hub.parent / "work"), *extra]


def test_seed_stops_while_materials_are_flagged_and_names_them(tmp_path, capsys):
    graph, hub = setup(tmp_path)
    assert cli.main(args(graph, hub)) == 1
    err = capsys.readouterr().err
    assert "flagged" in err and "Syllabus.md" in err and "--allow-unreviewed" in err


def test_seed_runs_once_reviewed_or_when_allowed(tmp_path, capsys):
    graph, hub = setup(tmp_path)
    assert cli.main(args(graph, hub, "--allow-unreviewed")) == 0
    record_decision(hub, "demo", "academic_notes/demo/syllabus/processed_outputs/Syllabus.md", role="syllabus")
    assert cli.main(args(graph, hub, "--run-id", "seed-2")) == 0
    assert "Topics: regression." in (hub.parent / "work" / "seed-2" / "cards" / "seed.md").read_text(encoding="utf-8")


def test_the_retriever_factory_receives_the_runs_catalog(tmp_path):
    graph, hub = setup(tmp_path)
    seen = {}

    def factory(a):
        seen["catalog"] = a.catalog
        raise RuntimeError("stop here")

    cli.main(["--graph-repo", str(graph), "collect", "fill", "--hub-root", str(hub), "--course", "demo",
              "--work-dir", str(tmp_path / "work")], retriever_factory=factory)
    assert seen["catalog"] is not None and seen["catalog"].course == "demo"


def test_collect_reports_retrieved_files_missing_from_the_catalog(tmp_path, capsys):
    from agent.concept_graph.sources import Passage
    from cg_helpers import copy_sample

    graph = copy_sample(tmp_path)
    _, hub = setup(tmp_path / "x")
    record_decision(hub, "demo", "academic_notes/demo/syllabus/processed_outputs/Syllabus.md", role="syllabus")

    class Retriever:
        def __init__(self, catalog):
            self.catalog = catalog

        def retrieve(self, query, top_k):
            from agent.concept_graph.sources import classify_passage
            source, ref = classify_passage("C:/hub/academic_notes/demo/new_folder/new.md", "", self.catalog)
            return [Passage(id="", source=source, ref=ref, text="t", path="p")]

    code = cli.main(["--graph-repo", str(graph), "collect", "fill", "--hub-root", str(hub), "--course", "demo",
                     "--work-dir", str(tmp_path / "work"), "--redo"], retriever_factory=lambda a: Retriever(a.catalog))
    assert code == 0
    assert "academic_notes/demo/new_folder/new.md" in capsys.readouterr().out
