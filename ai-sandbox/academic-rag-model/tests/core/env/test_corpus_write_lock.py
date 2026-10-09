from __future__ import annotations

import os
import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock


def _repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _child(code, *args, env=None):
    return subprocess.run(
        [sys.executable, "-c", code, *map(str, args)],
        capture_output=True, text=True, env=env, timeout=10,
    )


def test_second_process_reports_active_owner_and_cannot_write(tmp_path):
    root = _repo(tmp_path / "repo")
    marker = tmp_path / "wrote"
    code = """
import sys
from pathlib import Path
from core.env.corpus_write_lock import corpus_write_lock
with corpus_write_lock([sys.argv[1]], 'second writer'):
    Path(sys.argv[2]).write_text('wrote')
"""
    with corpus_write_lock([root], "first writer"):
        result = _child(code, root, marker)
        assert result.returncode != 0
        assert "first writer" in result.stderr
        assert "pid=" in result.stderr
        assert str(root) in result.stderr
        assert not marker.exists()
    assert _child(code, root, marker).returncode == 0
    assert marker.read_text() == "wrote"


def test_child_joins_only_while_parent_holds_lock(tmp_path):
    root = _repo(tmp_path / "repo")
    code = """
import sys
from core.env.corpus_write_lock import corpus_write_lock
with corpus_write_lock([sys.argv[1]], 'child'):
    print('joined')
"""
    with corpus_write_lock([root], "parent") as lease:
        joined = _child(code, root, env=lease.child_env())
        assert joined.returncode == 0, joined.stderr
        assert joined.stdout.strip() == "joined"
        token = lease.token
    stale_env = {**os.environ, "CORPUS_WRITE_RUN_TOKEN": token}
    stale = _child(code, root, env=stale_env)
    assert stale.returncode != 0
    assert "no live owner" in stale.stderr


def test_stale_metadata_does_not_block_new_owner_or_authorize_old_token(tmp_path):
    root = _repo(tmp_path / "repo")
    with corpus_write_lock([root], "finished") as old:
        old_token = old.token
    with pytest.raises(CorpusWriteLockError, match="no live owner"):
        with corpus_write_lock([root], "stale child", run_token=old_token):
            pass
    with corpus_write_lock([root], "new owner") as new:
        assert new.token != old_token


def test_crashed_owner_releases_os_lock_but_its_metadata_cannot_be_joined(tmp_path):
    root = _repo(tmp_path / "repo")
    code = """
import os
import sys
from core.env.corpus_write_lock import corpus_write_lock
with corpus_write_lock([sys.argv[1]], 'crashing writer') as lease:
    print(lease.token, flush=True)
    os._exit(0)
"""
    result = _child(code, root)
    assert result.returncode == 0, result.stderr
    with pytest.raises(CorpusWriteLockError, match="no live owner"):
        with corpus_write_lock([root], "stale child", run_token=result.stdout.strip()):
            pass
    with corpus_write_lock([root], "recovered"):
        pass


def test_same_repository_worktrees_share_one_lock(tmp_path):
    root = _repo(tmp_path / "repo")
    subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-qm", "init"],
                   check=True, env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
                                    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"})
    second = tmp_path / "worktree"
    subprocess.run(["git", "-C", str(root), "worktree", "add", "-q", "-b", "other", str(second)], check=True)
    with corpus_write_lock([root], "first"):
        with pytest.raises(CorpusWriteLockError, match="first"):
            with corpus_write_lock([second], "second"):
                pass


def test_distinct_repositories_have_distinct_locks(tmp_path):
    first = _repo(tmp_path / "outer")
    second = _repo(tmp_path / "notes")
    with corpus_write_lock([first], "outer"):
        with corpus_write_lock([second], "notes"):
            pass


def test_child_can_join_one_root_of_a_multi_root_parent(tmp_path):
    first = _repo(tmp_path / "outer")
    second = _repo(tmp_path / "notes")
    code = """
import sys
from core.env.corpus_write_lock import corpus_write_lock
with corpus_write_lock([sys.argv[1]], 'child'):
    print('joined')
"""
    with corpus_write_lock([first, second], "parent") as lease:
        result = _child(code, first, env=lease.child_env())
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "joined"


def test_partial_multi_root_acquisition_releases_earlier_root(tmp_path):
    first = _repo(tmp_path / "first")
    second = _repo(tmp_path / "second")
    # Which one is acquired first is a function of canonical Git-common paths.
    from core.env.corpus_write_lock import _repository_identity
    ordered = sorted([first, second], key=lambda root: os.path.normcase(str(_repository_identity(root)[1])))
    with corpus_write_lock([ordered[1]], "holder"):
        with pytest.raises(CorpusWriteLockError):
            with corpus_write_lock(ordered, "both"):
                pass
        with corpus_write_lock([ordered[0]], "after failure"):
            pass
