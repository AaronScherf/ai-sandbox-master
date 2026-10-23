import subprocess

import pytest

from agent.concept_graph.cli import main
from cg_helpers import copy_sample


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def init_repo(root):
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "publish@example.test")
    git(root, "config", "user.name", "Publisher Test")


def repos(tmp_path, remote="https://github.com/AaronScherf/econometrics-concept-graph-site.git"):
    graph = copy_sample(tmp_path)
    (graph / "config" / "site.yaml").write_text(
        "title: Test graph\nrepo: AaronScherf/econometrics-concept-graph-site\n", encoding="utf-8")
    init_repo(graph)
    git(graph, "add", "--", "config", "data")
    git(graph, "commit", "-q", "-m", "graph data")

    site = tmp_path / "site"
    site.mkdir()
    init_repo(site)
    git(site, "remote", "add", "origin", remote)
    (site / "index.html").write_text("old page", encoding="utf-8")
    (site / "keep.txt").write_text("keep", encoding="utf-8")
    git(site, "add", "--", "index.html", "keep.txt")
    git(site, "commit", "-q", "-m", "old page")
    return graph, site


def publish(graph, site):
    return main(["--graph-repo", str(graph), "publish", "--site-repo", str(site)])


def test_publish_builds_copies_and_commits_only_page_without_push(tmp_path, capsys):
    graph, site = repos(tmp_path)
    graph_sha = git(graph, "rev-parse", "HEAD")
    old_site_sha = git(site, "rev-parse", "HEAD")
    (site / "keep.txt").write_text("other staged work", encoding="utf-8")
    git(site, "add", "--", "keep.txt")

    assert publish(graph, site) == 0
    output = capsys.readouterr().out
    assert (graph / "build" / "graph.json").is_file()
    assert (site / "index.html").read_bytes() == (graph / "index.html").read_bytes()
    assert graph_sha in git(site, "log", "-1", "--format=%s")
    assert git(site, "rev-parse", "HEAD") != old_site_sha
    assert git(site, "show", "--format=", "--name-only", "HEAD") == "index.html"
    assert git(site, "diff", "--cached", "--name-only") == "keep.txt"
    assert "git -C" in output and "push origin main" in output
    assert git(site, "remote", "get-url", "origin").startswith("https://github.com/")


@pytest.mark.parametrize("remote", [
    "git@github.com:AaronScherf/econometrics-concept-graph-site.git",
    "ssh://git@github.com/AaronScherf/econometrics-concept-graph-site.git",
])
def test_publish_accepts_github_ssh_remotes(tmp_path, remote):
    graph, site = repos(tmp_path, remote=remote)
    assert publish(graph, site) == 0


@pytest.mark.parametrize("remote", [
    "https://github.com/AaronScherf/wrong-site.git",
    "https://github.com.evil.invalid/AaronScherf/econometrics-concept-graph-site.git",
])
def test_publish_refuses_wrong_site_remote_before_build(tmp_path, capsys, remote):
    graph, site = repos(tmp_path, remote=remote)
    before = git(site, "rev-parse", "HEAD")
    assert publish(graph, site) == 1
    assert "remote" in capsys.readouterr().err
    assert not (graph / "index.html").exists()
    assert git(site, "rev-parse", "HEAD") == before


def test_publish_refuses_dirty_graph_data_before_build(tmp_path, capsys):
    graph, site = repos(tmp_path)
    with (graph / "data" / "sections.yaml").open("a", encoding="utf-8") as fh:
        fh.write("\n# uncommitted change\n")
    assert publish(graph, site) == 1
    assert "uncommitted" in capsys.readouterr().err
    assert (site / "index.html").read_text(encoding="utf-8") == "old page"


def test_publish_preserves_an_uncommitted_site_page(tmp_path, capsys):
    graph, site = repos(tmp_path)
    (site / "index.html").write_text("someone else's page edit", encoding="utf-8")
    assert publish(graph, site) == 1
    assert "uncommitted" in capsys.readouterr().err
    assert (site / "index.html").read_text(encoding="utf-8") == "someone else's page edit"
    assert not (graph / "index.html").exists()


def test_publish_same_page_is_idempotent(tmp_path, capsys):
    graph, site = repos(tmp_path)
    assert publish(graph, site) == 0
    first = git(site, "rev-parse", "HEAD")
    capsys.readouterr()
    assert publish(graph, site) == 0
    assert git(site, "rev-parse", "HEAD") == first
    assert "already current" in capsys.readouterr().out
