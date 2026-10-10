from agent.concept_graph.cli import main
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, blank_explanations, copy_sample

GOOD = ("gist: A relation that ranks things without forbidding ties.\n"
        "explanation: Two properties define it, so every element relates to itself and comparisons chain together.\n"
        "citations:\n  - {source: rubinstein, ref: 'ch. 2, p. 12'}\n")


def setup(tmp_path):
    root = copy_sample(tmp_path)
    blank_explanations(GraphStore(root), ["preorder"])
    return root, tmp_path / "work"


def cli(root, *args, **kw):
    return main(["--graph-repo", str(root), *args], retriever_factory=lambda a: FakeRetriever(), **kw)


def test_cli_collect_submit_status_round_trip_with_a_fake_retriever(tmp_path, capsys):
    root, work = setup(tmp_path)
    assert cli(root, "collect", "fill", "--work-dir", str(work), "--run-id", "r1") == 0
    assert "r1" in capsys.readouterr().out
    card = work / "r1" / "cards" / "fill-preorder.md"
    card.write_text(card.read_text(encoding="utf-8").replace("```yaml\n```", "```yaml\n" + GOOD + "```"), encoding="utf-8")
    assert cli(root, "submit", "r1", "--work-dir", str(work), "--agent-name", "tester") == 0
    out = capsys.readouterr().out
    assert "1 applied" in out and "fill-preorder" in out
    assert cli(root, "status", "r1", "--work-dir", str(work)) == 0
    assert "applied" in capsys.readouterr().out
    node = next(n for n in GraphStore(root).read_all().nodes if n.id == "preorder")
    assert node.provenance.agent == "tester" and node.provenance.driver == "agent"


def test_cli_collect_with_nothing_to_do_says_so(tmp_path, capsys):
    root = copy_sample(tmp_path)
    assert cli(root, "collect", "fill", "--work-dir", str(tmp_path / "work")) == 0
    assert "nothing to do" in capsys.readouterr().out.lower()


def test_cli_refuses_a_work_dir_inside_the_graph_repo(tmp_path, capsys):
    root, _ = setup(tmp_path)
    assert cli(root, "collect", "fill", "--work-dir", str(root / "work")) == 1
    assert "inside the graph repo" in capsys.readouterr().err


def test_cli_needs_a_work_dir_or_a_hub_root(tmp_path, capsys):
    root, _ = setup(tmp_path)
    assert cli(root, "collect", "fill") == 1
    assert "--work-dir" in capsys.readouterr().err


def test_bootstrap_prints_the_contract_with_paths(tmp_path, capsys):
    root, work = setup(tmp_path)
    cli(root, "collect", "fill", "--work-dir", str(work), "--run-id", "r1")
    capsys.readouterr()
    assert cli(root, "bootstrap", "r1", "--work-dir", str(work)) == 0
    out = capsys.readouterr().out
    assert str(work / "r1") in out and "## Result" in out and "submit r1" in out and "own words" in out.lower()


def test_cli_api_refuses_over_budget_with_exit_code_two_and_no_calls(tmp_path, capsys):
    root, work = setup(tmp_path)
    calls = []
    code = cli(root, "api", "fill", "--work-dir", str(work), "--approve-cost", "0.0000001",
               complete_factory=lambda a: (lambda prompt: calls.append(prompt) or GOOD))
    assert code == 2 and calls == []
    assert "estimate" in capsys.readouterr().err


def test_cli_rejects_a_crafted_run_id(tmp_path, capsys):
    root, work = setup(tmp_path)
    assert cli(root, "collect", "fill", "--work-dir", str(work), "--run-id", "../graph/evil") == 1
    assert "run id" in capsys.readouterr().err
