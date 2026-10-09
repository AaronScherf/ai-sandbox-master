from __future__ import annotations

import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.indexer import index_search


def _repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False, with_notes=True):
    outer = _repo(tmp_path / "outer")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _repo(hub / "academic_notes") if with_notes else None
    monkeypatch.setattr(sys, "argv", [
        "index_search", "--root", str(hub), "retag", *(["--dry-run"] if dry_run else []),
    ])
    monkeypatch.setattr(index_search, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(index_search, "get_gemini_client", lambda: object())
    return hub, notes


def test_retag_holds_index_and_nested_notes_locks(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch)
    observed = []

    def retag(root, client, **kwargs):
        assert root == str(hub)
        for path in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="index retag"):
                with corpus_write_lock([path], "competing writer"):
                    pass
        observed.append(True)
        return {"retagged": 1}

    monkeypatch.setattr(index_search, "retag", retag)
    index_search.main()
    assert observed == [True]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_retag_refuses_competing_writer_before_mutation(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(index_search, "retag", lambda *args, **kwargs: pytest.fail("retag ran"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            index_search.main()


def test_retag_dry_run_needs_no_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    observed = []
    monkeypatch.setattr(index_search, "retag", lambda *args, **kwargs: observed.append(kwargs) or {})
    with corpus_write_lock([hub, notes], "other writer"):
        index_search.main()
    assert observed == [{"dry_run": True}]


def test_retag_without_nested_notes_locks_only_corpus_repo(tmp_path, monkeypatch):
    hub, _ = _setup(tmp_path, monkeypatch, with_notes=False)
    observed = []
    monkeypatch.setattr(index_search, "retag", lambda *args, **kwargs: observed.append(True) or {})
    index_search.main()
    assert observed == [True]
