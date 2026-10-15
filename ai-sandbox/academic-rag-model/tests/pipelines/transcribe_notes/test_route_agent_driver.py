from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from core.env import gemini_utils
from core.indexer.index_card import compute_file_id
from pipelines.transcribe_notes import agent_submit, agent_work
from pipelines.transcribe_notes import route_notes_transcribe as router


def _git_init(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, argv, pdf_todo=None, excalidraw_todo=None):
    outer = _git_init(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    _git_init(hub / "academic_notes")
    fake_script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "router.py"
    monkeypatch.setattr(router, "__file__", str(fake_script))
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", *argv])
    monkeypatch.setattr(router, "build_plan", lambda *args, **kwargs: SimpleNamespace(
        pdf_todo=list(pdf_todo or []), pdf_skipped=[],
        excalidraw_todo=list(excalidraw_todo or []), excalidraw_skipped=[],
    ))
    monkeypatch.setattr(router, "print_summary", lambda *args: None)
    monkeypatch.setattr(router, "sync_resource_backups", lambda *args, **kwargs: [])
    monkeypatch.setattr(router, "print_backup_summary", lambda *args: None)
    monkeypatch.setattr(gemini_utils, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(gemini_utils, "get_gemini_client", lambda *args: object())
    return hub


def test_bootstrap_prints_contract_without_touching_the_corpus(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(router, "build_plan", lambda *a, **k: pytest.fail("bootstrap must not build a plan"))
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", "--bootstrap", "run1"])

    router.main()

    out = capsys.readouterr().out
    assert "run1" in out
    assert "route_notes_transcribe --submit run1" in out
    assert "Excalidraw notes are not part of this run" in out


def test_driver_agent_without_collect_or_submit_exits(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ["--driver", "agent"], pdf_todo=["a.pdf"])
    with pytest.raises(SystemExit):
        router.main()


def test_collect_requires_agent_driver(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ["--collect"], pdf_todo=["a.pdf"])
    with pytest.raises(SystemExit):
        router.main()


def test_collect_defers_excalidraw_and_never_touches_the_api_client(tmp_path, monkeypatch, capsys):
    _setup(
        tmp_path, monkeypatch, ["--driver", "agent", "--collect", "--run-id", "r1"],
        pdf_todo=[str(tmp_path / "a.pdf")],
        excalidraw_todo=[("note.excalidraw.md", "note.excalidraw.svg")],
    )

    captured_kwargs = {}

    def fake_run_plan(plan, client, academic_hub_root, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["client"] = client
        captured_kwargs["excalidraw_todo"] = list(plan.excalidraw_todo)
        return SimpleNamespace(pdf_results=[], excalidraw_results=[])

    monkeypatch.setattr(router, "run_plan", fake_run_plan)
    monkeypatch.setattr(agent_work, "dedupe_by_file_id", lambda paths: (list(paths), {}))
    monkeypatch.setattr(agent_work, "AgentDriver", lambda hub_root, run_id: SimpleNamespace(
        hub_root=hub_root, run_id=run_id,
    ))

    router.main()

    assert captured_kwargs["collect_mode"] is True
    assert captured_kwargs["client"] is None
    assert captured_kwargs["excalidraw_todo"] == []
    out = capsys.readouterr().out
    assert "Deferred" in out
    assert "r1" in out


def test_submit_matches_collected_docs_by_slug_and_skips_unmatched(tmp_path, monkeypatch, capsys):
    pdf_path = tmp_path / "ai-sandbox" / "a.pdf"
    hub = _setup(
        tmp_path, monkeypatch, ["--submit", "r1"],
        pdf_todo=[str(pdf_path)],
    )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"x")

    file_id = compute_file_id(str(pdf_path))
    known_slug = agent_work.doc_slug_for(str(pdf_path), file_id)
    run_dir = hub / ".agent_work" / "r1"
    (run_dir / known_slug).mkdir(parents=True)
    (run_dir / "unmatched--deadbeef").mkdir(parents=True)

    submitted = []
    monkeypatch.setattr(agent_submit, "submit_doc", lambda *args, **kwargs: submitted.append(args) or "ok")

    router.main()

    assert len(submitted) == 1
    assert submitted[0][3] == known_slug
    out = capsys.readouterr().out
    assert "no matching pending PDF" in out
