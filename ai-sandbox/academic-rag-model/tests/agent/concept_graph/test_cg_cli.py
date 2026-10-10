from agent.concept_graph.cli import main
from cg_helpers import copy_sample


def test_validate_exits_zero_on_the_sample_and_prints_the_warning(tmp_path, capsys):
    root = copy_sample(tmp_path)
    assert main(["--graph-repo", str(root), "validate"]) == 0
    out = capsys.readouterr().out
    assert "0 error(s), 1 warning(s)" in out and "logical-cycle" in out


def test_validate_exits_one_when_there_are_errors(tmp_path, capsys):
    root = copy_sample(tmp_path)
    path = root / "data" / "edges" / "s02-choice.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("target: sen-alpha-beta", "target: nowhere", 1), encoding="utf-8")
    assert main(["--graph-repo", str(root), "validate"]) == 1
    assert "dangling-endpoint" in capsys.readouterr().out
