from __future__ import annotations

import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.convert_textbook import describe_images as cli


def _repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False):
    outer = _repo(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _repo(hub / "academic_notes")
    script = outer / "academic-rag-model" / "pipelines" / "convert_textbook" / "describe_images.py"
    monkeypatch.setattr(cli, "__file__", str(script))
    monkeypatch.setattr(sys, "argv", [
        "describe_images", "--textbook-subdir", "academic_resources/econometrics/textbooks",
        *(["--dry-run"] if dry_run else []),
    ])
    monkeypatch.setattr(cli, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(cli, "get_gemini_client", lambda *args: object())
    monkeypatch.setattr(cli, "discover_book_dirs", lambda *args: [str(hub / "Book")])
    return hub, notes


def test_book_naming_and_description_share_both_locks(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch)
    observed = []

    def check_locks():
        for root in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="textbook image description"):
                with corpus_write_lock([root], "competing writer"):
                    pass

    def rename(book_dir, root, dry_run=False):
        check_locks()
        observed.append("rename")
        return book_dir

    def describe(*args, **kwargs):
        check_locks()
        observed.append("describe")

    monkeypatch.setattr(cli, "reconcile_book_naming", rename)
    monkeypatch.setattr(cli, "process_book", describe)
    cli.main()
    assert observed == ["rename", "describe"]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_description_refuses_competing_writer_before_rename(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "reconcile_book_naming", lambda *args, **kwargs: pytest.fail("renamed"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            cli.main()


def test_description_dry_run_needs_no_writer_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    observed = []

    def rename(book_dir, root, dry_run=False):
        observed.append(dry_run)
        return book_dir

    monkeypatch.setattr(cli, "reconcile_book_naming", rename)
    monkeypatch.setattr(cli, "process_book", lambda *args, **kwargs: observed.append(kwargs["dry_run"]))
    with corpus_write_lock([hub, notes], "other writer"):
        cli.main()
    assert observed == [True, True]
