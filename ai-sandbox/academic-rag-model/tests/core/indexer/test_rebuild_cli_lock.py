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


def _run_main(monkeypatch, root):
    monkeypatch.setattr(sys, "argv", [
        "index_search", "--root", str(root), "rebuild",
        "--course", "econometrics", "--force", "--prune",
    ])
    monkeypatch.setattr(index_search, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(index_search, "get_gemini_client", lambda: object())
    index_search.main()


def test_rebuild_cli_holds_lock_through_writer_call(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    observed = []

    def rebuild(root_arg, client, **kwargs):
        assert root_arg == str(root)
        assert kwargs == {"course": "econometrics", "force": True, "prune": True}
        with pytest.raises(CorpusWriteLockError, match="index rebuild"):
            with corpus_write_lock([root], "competing writer"):
                pass
        observed.append(True)
        return {"generated": 0}

    monkeypatch.setattr(index_search, "rebuild", rebuild)
    _run_main(monkeypatch, root)
    assert observed == [True]


def test_rebuild_cli_refuses_concurrent_writer_before_rebuild(tmp_path, monkeypatch):
    root = _repo(tmp_path / "repo")
    monkeypatch.setattr(index_search, "rebuild", lambda *args, **kwargs: pytest.fail("rebuild was called"))
    with corpus_write_lock([root], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            _run_main(monkeypatch, root)
