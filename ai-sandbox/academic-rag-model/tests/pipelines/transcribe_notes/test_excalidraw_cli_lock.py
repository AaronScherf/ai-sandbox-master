from __future__ import annotations

import subprocess
import sys

import pytest

from core.env import gemini_utils
from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.transcribe_notes import transcribe_excalidraw as exc_cli


def _repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False, reexpand=False):
    outer = _repo(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _repo(hub / "academic_notes")
    script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "transcribe_excalidraw.py"
    monkeypatch.setattr(exc_cli, "__file__", str(script))
    monkeypatch.setattr(sys, "argv", [
        "transcribe_excalidraw", "--notes-subdir", "academic_notes/econometrics",
        *(["--dry-run"] if dry_run else []), *(["--reexpand"] if reexpand else []),
    ])
    monkeypatch.setattr(gemini_utils, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(gemini_utils, "get_gemini_client", lambda: object())
    monkeypatch.setattr(exc_cli, "discover_excalidraw_files", lambda *args: [("one.excalidraw.md", "one.svg")])
    return hub, notes


@pytest.mark.parametrize("reexpand", [False, True])
def test_excalidraw_cli_holds_both_locks_during_write(tmp_path, monkeypatch, reexpand):
    hub, notes = _setup(tmp_path, monkeypatch, reexpand=reexpand)
    observed = []

    def write(*args, **kwargs):
        for root in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="Excalidraw transcription"):
                with corpus_write_lock([root], "competing writer"):
                    pass
        observed.append(True)

    monkeypatch.setattr(exc_cli, "process_excalidraw_note", write)
    monkeypatch.setattr(exc_cli, "reexpand_excalidraw_note", write)
    exc_cli.main()
    assert observed == [True]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_excalidraw_cli_refuses_competing_writer(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(exc_cli, "process_excalidraw_note", lambda *args, **kwargs: pytest.fail("processed"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            exc_cli.main()


def test_excalidraw_dry_run_needs_no_writer_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    observed = []
    monkeypatch.setattr(exc_cli, "process_excalidraw_note", lambda *args, **kwargs: observed.append(kwargs))
    with corpus_write_lock([hub, notes], "other writer"):
        exc_cli.main()
    assert observed and observed[0]["dry_run"] is True
