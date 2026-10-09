from __future__ import annotations

import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.transcribe_notes import transcribe_notes as pdf_cli


def _repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False):
    outer = _repo(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _repo(hub / "academic_notes")
    fake_script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "transcribe_notes.py"
    monkeypatch.setattr(pdf_cli, "__file__", str(fake_script))
    monkeypatch.setattr(sys, "argv", [
        "transcribe_notes", "--notes-subdir", "academic_resources/econometrics",
        *(["--dry-run"] if dry_run else []),
    ])
    monkeypatch.setattr(pdf_cli, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(pdf_cli, "get_gemini_client", lambda: object())
    monkeypatch.setattr(pdf_cli, "discover_pdf_files", lambda *args: [str(hub / "one.pdf")])
    return hub, notes


def test_pdf_cli_holds_both_repository_locks_while_processing(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch)
    observed = []

    def process(*args, **kwargs):
        for root in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="notes PDF transcription"):
                with corpus_write_lock([root], "competing writer"):
                    pass
        observed.append(True)

    monkeypatch.setattr(pdf_cli, "process_pdf", process)
    pdf_cli.main()
    assert observed == [True]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_pdf_cli_refuses_competing_writer_before_processing(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(pdf_cli, "process_pdf", lambda *args, **kwargs: pytest.fail("processed"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            pdf_cli.main()


def test_pdf_cli_dry_run_uses_no_writer_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    observed = []
    monkeypatch.setattr(pdf_cli, "process_pdf", lambda *args, **kwargs: observed.append(kwargs))
    with corpus_write_lock([hub, notes], "other writer"):
        pdf_cli.main()
    assert observed == [{"dry_run": True, "force_vision": False}]
