from __future__ import annotations

import subprocess

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.indexer import related


def _repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_related_cli_holds_lock_for_shard_write(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    observed = []

    def link(root_arg, course, dry_run=False):
        assert (root_arg, course, dry_run) == (str(root), "microecon", False)
        with pytest.raises(CorpusWriteLockError, match="index subset links"):
            with corpus_write_lock([root], "competing writer"):
                pass
        observed.append(True)
        return []

    monkeypatch.setattr(related, "link_subsets", link)
    related.main(["--root", str(root), "--course", "microecon"])
    assert observed == [True]


def test_related_cli_refuses_competing_writer_before_shard_write(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    monkeypatch.setattr(related, "link_subsets", lambda *args, **kwargs: pytest.fail("writer ran"))
    with corpus_write_lock([root], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            related.main(["--root", str(root), "--course", "microecon"])


def test_related_dry_run_is_read_only_under_another_writer(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    calls = []

    def link(root_arg, course, dry_run=False):
        calls.append((root_arg, course, dry_run))
        return []

    monkeypatch.setattr(related, "link_subsets", link)
    with corpus_write_lock([root], "other writer"):
        related.main(["--root", str(root), "--course", "microecon", "--dry-run"])
    assert calls == [(str(root), "microecon", True)]
