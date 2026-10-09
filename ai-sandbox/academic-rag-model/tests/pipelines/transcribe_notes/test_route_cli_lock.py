from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from core.env import gemini_utils
from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.transcribe_notes import route_notes_transcribe as router


def _git_init(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False):
    outer = _git_init(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _git_init(hub / "academic_notes")
    fake_script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "router.py"
    monkeypatch.setattr(router, "__file__", str(fake_script))
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", *(["--dry-run"] if dry_run else [])])
    monkeypatch.setattr(router, "build_plan", lambda *args, **kwargs: SimpleNamespace(
        pdf_todo=[str(notes / "one.pdf")], excalidraw_todo=[],
    ))
    monkeypatch.setattr(router, "print_summary", lambda *args: None)
    monkeypatch.setattr(gemini_utils, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(gemini_utils, "get_gemini_client", lambda *args: object())
    return hub, notes


def test_router_holds_outer_and_notes_repository_locks(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch)
    observed = []

    def run(*args, **kwargs):
        for root in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="route notes transcription"):
                with corpus_write_lock([root], "competing writer"):
                    pass
        observed.append(True)
        return SimpleNamespace(pdf_results=[], excalidraw_results=[])

    monkeypatch.setattr(router, "run_plan", run)
    router.main()
    assert observed == [True]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_router_refuses_competing_writer_before_run(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(router, "run_plan", lambda *args, **kwargs: pytest.fail("router ran"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            router.main()


def test_router_dry_run_needs_no_writer_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    monkeypatch.setattr(router, "run_plan", lambda *args, **kwargs: pytest.fail("router ran"))
    with corpus_write_lock([hub, notes], "other writer"):
        router.main()
