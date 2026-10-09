from __future__ import annotations

import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.indexer import index_search


def _repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _run_main(monkeypatch, root, *, dry_run=False):
    argv = ["index_search", "--root", str(root), "chunk", "--file", "one.md"]
    if dry_run:
        argv.append("--dry-run")
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(index_search, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(index_search, "get_gemini_client", lambda: object())
    index_search.main()


def test_chunk_cli_holds_lock_while_writer_runs(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    observed = []

    def chunk(root_arg, client, **kwargs):
        assert root_arg == str(root)
        assert kwargs == {"course": None, "file": "one.md"}
        with pytest.raises(CorpusWriteLockError, match="index chunk"):
            with corpus_write_lock([root], "competing writer"):
                pass
        observed.append(True)
        return {"chunked": 1}

    monkeypatch.setattr(index_search, "chunk", chunk)
    _run_main(monkeypatch, root)
    assert observed == [True]


def test_chunk_cli_refuses_concurrent_writer_before_calling_chunk(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    monkeypatch.setattr(index_search, "chunk", lambda *args, **kwargs: pytest.fail("chunk was called"))
    with corpus_write_lock([root], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            _run_main(monkeypatch, root)


def test_chunk_dry_run_does_not_need_a_writer_lock(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    observed = []

    def chunk(root_arg, client, **kwargs):
        observed.append(kwargs)
        return {"chunked": 0}

    monkeypatch.setattr(index_search, "chunk", chunk)
    with corpus_write_lock([root], "other writer"):
        _run_main(monkeypatch, root, dry_run=True)
    assert observed == [{"course": None, "file": "one.md", "dry_run": True}]
