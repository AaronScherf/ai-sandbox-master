"""route_notes_transcribe and transcribe_excalidraw refuse on unresolved links before any client or lease."""
from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from core.env import gemini_utils
from core.indexer import preflight
from core.indexer.review_envelope import ReviewItem
from pipelines.transcribe_notes import route_notes_transcribe as router
from pipelines.transcribe_notes import transcribe_excalidraw as exc_cli


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed before preflight passes")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(gemini_utils, "load_dotenv_override", lambda: None)


@pytest.fixture
def seen(monkeypatch):
    calls = []
    monkeypatch.setattr(preflight, "check", lambda hub, needs, *a, **k: calls.append((hub, needs)) or
                        [ReviewItem("i1", "relink", ["f1"], [], "pending")])
    return calls


def _route(monkeypatch, tmp_path, *argv):
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", "--root", str(tmp_path), *argv])
    planned = []
    monkeypatch.setattr(router, "build_plan", lambda *a, **k: planned.append(1) or SimpleNamespace(
        pdf_todo=[], pdf_skipped=[], excalidraw_todo=[], excalidraw_skipped=[], courses=[],
        resolve_questions_todo=[]))
    monkeypatch.setattr(router, "print_summary", lambda *a: None)
    return planned


def test_router_refuses_with_course_needs(tmp_path, monkeypatch, seen, capsys):
    planned = _route(monkeypatch, tmp_path, "--course", "econ", "--driver", "api")
    with pytest.raises(SystemExit) as e:
        router.main()
    assert e.value.code == 2 and planned == []
    assert "hub_review page" in capsys.readouterr().err
    assert seen[0][1].courses == frozenset({"econ"})


def test_router_whole_hub_without_course_and_ignore_flag(tmp_path, monkeypatch, seen, capsys):
    planned = _route(monkeypatch, tmp_path, "--driver", "api", "--ignore-unresolved", "--dry-run")
    router.main()
    assert seen[0][1].courses is None and planned == [1]
    assert "ignoring" in capsys.readouterr().err


def test_router_dry_run_only_warns(tmp_path, monkeypatch, seen, capsys):
    planned = _route(monkeypatch, tmp_path, "--driver", "api", "--dry-run")
    router.main()
    assert planned == [1]
    assert "unresolved" in capsys.readouterr().err


@pytest.mark.parametrize("extra", [["--submit", "r1"], ["--collect"]])
def test_router_dry_run_with_writing_flags_still_refuses(tmp_path, monkeypatch, seen, extra):
    _route(monkeypatch, tmp_path, "--dry-run", *extra)
    with pytest.raises(SystemExit) as e:
        router.main()
    assert e.value.code == 2


def _excalidraw(monkeypatch, tmp_path, *argv):
    outer = tmp_path / "ai-sandbox"
    (outer / "academic-hub").mkdir(parents=True)
    script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "transcribe_excalidraw.py"
    monkeypatch.setattr(exc_cli, "__file__", str(script))
    monkeypatch.setattr(sys, "argv", ["transcribe_excalidraw", "--notes-subdir", "academic_notes/econ/lecture_notes",
                                      *argv])
    found = []
    monkeypatch.setattr(exc_cli, "discover_excalidraw_files",
                        lambda *a: found.append(1) or [("one.excalidraw.md", "one.svg")])
    return found


def test_excalidraw_refuses_before_discovery_or_client(tmp_path, monkeypatch, seen, capsys):
    found = _excalidraw(monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as e:
        exc_cli.main()
    assert e.value.code == 2 and found == []
    assert seen[0][1].courses == frozenset({"econ"})
    assert "hub_review page" in capsys.readouterr().err


def test_excalidraw_dry_run_warns_and_ignore_flag_runs(tmp_path, monkeypatch, seen, capsys):
    found = _excalidraw(monkeypatch, tmp_path, "--dry-run")
    monkeypatch.setattr(exc_cli, "process_excalidraw_note", lambda *a, **k: None)
    exc_cli.main()
    assert found == [1]
    monkeypatch.setattr(sys, "argv", ["x", "--notes-subdir", "academic_notes/econ/x", "--dry-run",
                                      "--ignore-unresolved"])
    exc_cli.main()
