import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from core.env.gemini_utils import _resolve_env_path

_REL_MODULE = Path("ai-sandbox/academic-rag-model/core/env/gemini_utils.py")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo_and_worktree(tmp_path):
    main = tmp_path / "main"
    (main / _REL_MODULE.parent).mkdir(parents=True)
    (main / _REL_MODULE).write_text("# stand-in module\n")
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "add", ".")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    worktree = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "task", str(worktree))
    return main, worktree


def test_returns_local_env_when_present(repo_and_worktree):
    main, worktree = repo_and_worktree
    (worktree / "ai-sandbox" / ".env").write_text("K=local\n")
    (main / "ai-sandbox" / ".env").write_text("K=main\n")
    assert _resolve_env_path(worktree / _REL_MODULE) == worktree / "ai-sandbox" / ".env"


def test_worktree_without_env_falls_back_to_main_checkout(repo_and_worktree):
    main, worktree = repo_and_worktree
    (main / "ai-sandbox" / ".env").write_text("K=main\n")
    resolved = _resolve_env_path(worktree / _REL_MODULE)
    assert resolved.resolve() == (main / "ai-sandbox" / ".env").resolve()


def test_main_checkout_without_env_returns_local_path(repo_and_worktree):
    main, _ = repo_and_worktree
    assert _resolve_env_path(main / _REL_MODULE) == main / "ai-sandbox" / ".env"


def test_no_env_anywhere_returns_local_path(repo_and_worktree):
    _, worktree = repo_and_worktree
    assert _resolve_env_path(worktree / _REL_MODULE) == worktree / "ai-sandbox" / ".env"


def test_git_unavailable_returns_local_path(repo_and_worktree):
    _, worktree = repo_and_worktree
    with patch("core.env.gemini_utils.subprocess.run", side_effect=FileNotFoundError):
        assert _resolve_env_path(worktree / _REL_MODULE) == worktree / "ai-sandbox" / ".env"


def test_outside_a_git_repo_returns_local_path(tmp_path):
    module = tmp_path / _REL_MODULE
    module.parent.mkdir(parents=True)
    module.write_text("#\n")
    assert _resolve_env_path(module) == tmp_path / "ai-sandbox" / ".env"
