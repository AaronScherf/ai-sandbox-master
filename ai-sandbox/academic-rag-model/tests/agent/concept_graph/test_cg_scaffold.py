import pytest
import yaml

from agent.concept_graph.build import build
from agent.concept_graph.cli import main
from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.store import GraphStore


def fake_fetch(url):
    return "FAKE CC BY-NC-SA 4.0 LEGAL CODE from " + url


def run(tmp_path, **kw):
    root = tmp_path / "new-graph"
    created = scaffold(root, "someone/microecon-concept-graph", "Some One", 2026, fetch_text=fake_fetch, **kw)
    return root, created


def test_scaffold_writes_the_expected_files(tmp_path):
    root, created = run(tmp_path)
    for rel in ["README.md", "NOTICE.md", "LICENSE", "LICENSE-CODE", ".gitignore", ".github/ISSUE_TEMPLATE/review.yml",
                "config/vocab.yaml", "config/site.yaml", "data/sections.yaml", "data/rejected.yaml"]:
        assert (root / rel).is_file(), rel
        assert rel in created
    assert "FAKE CC BY-NC-SA" in (root / "LICENSE").read_text(encoding="utf-8")
    mit = (root / "LICENSE-CODE").read_text(encoding="utf-8")
    assert "MIT License" in mit and "2026 Some One" in mit


def test_issue_template_is_a_form_with_a_json_review_box(tmp_path):
    root, _ = run(tmp_path)
    form = yaml.safe_load((root / ".github/ISSUE_TEMPLATE/review.yml").read_text(encoding="utf-8"))
    assert form["labels"] == ["review"]
    box = form["body"][0]
    assert box["id"] == "review" and box["type"] == "textarea" and box["attributes"]["render"] == "json"


def test_notice_states_the_non_commercial_independent_status_and_defaults_the_contact_to_issues(tmp_path):
    root, _ = run(tmp_path)
    text = (root / "NOTICE.md").read_text(encoding="utf-8").lower()
    for phrase in ["independent", "non-commercial", "not affiliated", "takedown", "https://github.com/someone/microecon-concept-graph/issues"]:
        assert phrase in text
    assert "@" not in text  # no email address is published unless the owner passes --contact


def test_site_config_carries_the_repo_for_the_viewer(tmp_path):
    root, _ = run(tmp_path)
    assert yaml.safe_load((root / "config/site.yaml").read_text(encoding="utf-8"))["repo"] == "someone/microecon-concept-graph"


def test_refuses_to_overwrite_and_writes_nothing(tmp_path):
    root, _ = run(tmp_path)
    (root / "NOTICE.md").write_text("mine", encoding="utf-8")
    with pytest.raises(FileExistsError, match="NOTICE.md"):
        scaffold(root, "someone/x", "Some One", 2026, fetch_text=fake_fetch)
    assert (root / "NOTICE.md").read_text(encoding="utf-8") == "mine"


def test_with_sample_gives_a_buildable_graph_that_keeps_the_real_repo(tmp_path):
    root, _ = run(tmp_path, with_sample=True)
    graph = GraphStore(root).read_all()
    assert len(graph.nodes) == 17 and graph.site["repo"] == "someone/microecon-concept-graph"
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "cytoscape.min.js").write_text("/*c*/", encoding="utf-8")
    (vendor / "katex.min.js").write_text("/*k*/", encoding="utf-8")
    assert build(root, vendor_dir=vendor).index_html.is_file()


def test_an_empty_scaffold_validates_cleanly(tmp_path):
    root, _ = run(tmp_path)
    assert main(["--graph-repo", str(root), "validate"]) == 0


def test_cli_scaffold_command(tmp_path, monkeypatch):
    import agent.concept_graph.scaffold as sc
    monkeypatch.setattr(sc, "fetch_url_text", fake_fetch)
    root = tmp_path / "via-cli"
    code = main(["--graph-repo", str(root), "scaffold", "--repo", "someone/g", "--holder", "Some One"])
    assert code == 0 and (root / "NOTICE.md").is_file()
