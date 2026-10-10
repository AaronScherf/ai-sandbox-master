import json
import subprocess

from agent.concept_graph.cli import main
from agent.concept_graph.schema import field_hash
from agent.concept_graph.store import GraphStore
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


def write_review(path, *decisions, name="Ada"):
    path.write_text(json.dumps({
        "schema_version": 1, "graph_version": "v", "reviewer": {"name": name},
        "created": "2026-10-20T10:00:00Z", "decisions": list(decisions),
    }), encoding="utf-8")
    return path


def test_apply_review_from_a_file_updates_the_graph_and_archives_it(tmp_path, capsys):
    root = copy_sample(tmp_path)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"})
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--today", "2026-10-20"]) == 0
    assert "1 applied" in capsys.readouterr().out
    node = next(n for n in GraphStore(root).read_all().nodes if n.id == "preorder")
    assert node.status == "verified"
    assert list((root / "reviews" / "applied").glob("*.json"))


def test_apply_review_reports_conflicts_but_exits_zero(tmp_path, capsys):
    root = copy_sample(tmp_path)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "edit",
                                            "field": "gist", "base_hash": field_hash("stale"), "new_value": "x"})
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--today", "2026-10-20"]) == 0
    out = capsys.readouterr().out
    assert "1 conflict" in out and "review-conflicts.md" in out


def test_apply_review_exits_one_on_an_unparseable_file(tmp_path):
    root = copy_sample(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["--graph-repo", str(root), "apply-review", str(bad)]) == 1


def test_apply_review_commit_makes_one_commit_per_reviewer(tmp_path):
    root = copy_sample(tmp_path)
    for cmd in (["init", "-q"], ["config", "user.email", "t@example.test"], ["config", "user.name", "Test"], ["add", "."], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True)
    rf = write_review(tmp_path / "r.json", {"target": {"kind": "node", "id": "preorder"}, "action": "accept"}, name="Ada")
    assert main(["--graph-repo", str(root), "apply-review", str(rf), "--commit", "--today", "2026-10-20"]) == 0
    log = subprocess.run(["git", "-C", str(root), "log", "--format=%s"], capture_output=True, text=True, check=True).stdout.split("\n")
    assert log[0] == "review: apply Ada"
    status = subprocess.run(["git", "-C", str(root), "status", "--short"], capture_output=True, text=True, check=True).stdout
    assert status.strip() == ""
