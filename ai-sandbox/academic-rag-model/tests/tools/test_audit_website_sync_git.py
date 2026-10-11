"""Real local Git fixtures for website-sync root and evidence isolation."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess

import pytest

from tools.audit_website_sync import AuditError, GitRepository, select_repositories


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def repo(path: Path, filename: str, content: str) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / filename).parent.mkdir(parents=True, exist_ok=True)
    (path / filename).write_text(content, encoding="utf-8")
    git(path, "add", "--", filename)
    git(path, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")
    return path


def test_independent_repositories_and_worktree_use_own_heads(tmp_path: Path) -> None:
    outer = repo(tmp_path / "outer repo", "ai-sandbox/academic-rag-model/tools/website_sync_registry.py", "one")
    site = repo(tmp_path / "site repo", "content/projects/a/index.md", "old")
    git(site, "worktree", "add", "-qb", "site-review", str(tmp_path / "site worktree"))
    site_worktree = tmp_path / "site worktree"
    (site_worktree / "content/projects/a/index.md").write_text("new", encoding="utf-8")
    git(site_worktree, "add", "--", "content/projects/a/index.md")
    git(site_worktree, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "new")
    assert (site_worktree / ".git").is_file()

    monorepo, website = select_repositories(outer, site_worktree)
    assert monorepo.common_dir != website.common_dir
    assert website.head != git(site, "rev-parse", "HEAD")
    assert website.timestamp("content/projects/a/index.md") == int(git(site_worktree, "log", "-1", "--format=%ct"))
    assert monorepo.head == git(outer, "rev-parse", "HEAD")


def test_git_environment_cannot_redirect_repo_index_or_objects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = repo(tmp_path / "first", "source.txt", "first")
    second = repo(tmp_path / "second", "source.txt", "second")
    for key, value in {
        "GIT_DIR": str(second / ".git"), "GIT_WORK_TREE": str(second),
        "GIT_INDEX_FILE": str(second / ".git/index"),
        "GIT_OBJECT_DIRECTORY": str(second / ".git/objects"),
        "GIT_COMMON_DIR": str(second / ".git"),
        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.bare",
        "GIT_CONFIG_VALUE_0": "true",
    }.items():
        monkeypatch.setenv(key, value)
    evidence = GitRepository(first, kind="monorepo").evidence("source.txt")
    assert evidence["tracked"] == ["source.txt"]
    assert evidence["timestamp"] == int(git_clean(first, "log", "-1", "--format=%ct"))
    assert evidence["dirty"] is False


def git_clean(root: Path, *args: str) -> str:
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "-C", str(root), *args], env=environment,
                          capture_output=True, text=True, check=True).stdout.strip()


def test_literal_paths_dirty_untracked_and_change_detection(tmp_path: Path) -> None:
    root = repo(tmp_path / "repo with spaces", "dir with spaces/[literal].txt", "old")
    checked = GitRepository(root, kind="monorepo")
    path = "dir with spaces/[literal].txt"
    before = checked.snapshot({path})
    assert before[path]["tracked"] == [path]
    assert before[path]["timestamp"] is not None
    (root / path).write_text("changed", encoding="utf-8")
    with pytest.raises(AuditError, match="relevant input changed"):
        checked.assert_unchanged(before)
    after = checked.evidence(path)
    assert after["dirty"] is True
    new = "dir with spaces/new.txt"
    (root / new).write_text("untracked", encoding="utf-8")
    assert checked.evidence(new)["untracked"] == [new]
    assert checked.evidence(new)["timestamp"] is None


def test_staged_and_unrelated_changes_are_scoped_to_relevant_paths(tmp_path: Path) -> None:
    root = repo(tmp_path / "repo", "relevant.txt", "old")
    (root / "unrelated.txt").write_text("unrelated", encoding="utf-8")
    clean = GitRepository(root, kind="monorepo")
    assert clean.evidence("relevant.txt")["dirty"] is False
    (root / "relevant.txt").write_text("staged", encoding="utf-8")
    git(root, "add", "--", "relevant.txt")
    assert clean.snapshot({"relevant.txt"})["relevant.txt"]["dirty"] is True


def test_wrong_roots_and_shared_common_dir_fail(tmp_path: Path) -> None:
    outer = repo(tmp_path / "outer", "ai-sandbox/academic-rag-model/tools/website_sync_registry.py", "one")
    (outer / "content/projects").mkdir(parents=True)
    with pytest.raises(AuditError, match="exact Git toplevel"):
        GitRepository(outer / "ai-sandbox", kind="monorepo")
    with pytest.raises(AuditError, match="distinct Git common"):
        select_repositories(outer, outer)
    bad = repo(tmp_path / "bad", "elsewhere.txt", "x")
    with pytest.raises(AuditError, match="lacks expected"):
        select_repositories(bad, outer)


def test_missing_head_and_shallow_history_fail_incomplete(tmp_path: Path) -> None:
    unborn = tmp_path / "unborn"
    unborn.mkdir()
    subprocess.run(["git", "init", "-q", str(unborn)], check=True)
    with pytest.raises(AuditError, match="Git failed"):
        GitRepository(unborn, kind="website")
    source = repo(tmp_path / "source", "file.txt", "first")
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "1", source.as_uri(), str(shallow)], check=True)
    with pytest.raises(AuditError, match="shallow"):
        GitRepository(shallow, kind="website")


def test_head_change_is_detected(tmp_path: Path) -> None:
    root = repo(tmp_path / "root", "one.txt", "one")
    checked = GitRepository(root, kind="monorepo")
    snapshot = checked.snapshot({"one.txt"})
    (root / "two.txt").write_text("two", encoding="utf-8")
    git(root, "add", "--", "two.txt")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "two")
    with pytest.raises(AuditError, match="HEAD changed"):
        checked.assert_unchanged(snapshot)


def test_missing_local_head_object_fails_without_fetch(tmp_path: Path) -> None:
    root = repo(tmp_path / "root", "one.txt", "one")
    sha = git(root, "rev-parse", "HEAD")
    object_path = root / ".git/objects" / sha[:2] / sha[2:]
    assert object_path.is_file()
    object_path.chmod(stat.S_IWRITE | stat.S_IREAD)
    object_path.unlink()
    with pytest.raises(AuditError, match="Git failed"):
        GitRepository(root, kind="monorepo")
