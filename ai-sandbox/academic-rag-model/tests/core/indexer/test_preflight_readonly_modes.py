"""Read-only modes only warn when preflight cannot run (non-git hub, held lock); they never exit 2."""
from __future__ import annotations

import sys

import pytest

from core.indexer import index_search


@pytest.mark.parametrize("argv", [
    ["chunk", "--dry-run"],
    ["retag", "--dry-run"],
    ["index-md", "--course", "econ"],
    ["rebuild", "--plan"],
])
def test_read_only_index_modes_warn_instead_of_refusing(tmp_path, monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", ["index_search", "--root", str(tmp_path), *argv])
    monkeypatch.setattr(index_search, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(index_search, "get_gemini_client", lambda *a, **k: object())
    called = []
    for name in ("chunk", "retag"):
        monkeypatch.setattr(index_search, name, lambda *a, _n=name, **k: called.append(_n) or {})
    monkeypatch.setattr(index_search, "rebuild_plan",
                        lambda *a, **k: called.append("rebuild_plan") or {"estimated_paid_cards": 0})
    monkeypatch.setattr(index_search, "markdown_preview", lambda *a, **k: called.append("markdown_preview") or [])
    index_search.main()  # a SystemExit(2) here fails the test
    assert called == [{"chunk": "chunk", "retag": "retag", "index-md": "markdown_preview",
                       "rebuild": "rebuild_plan"}[argv[0]]]
    assert "link preflight skipped" in capsys.readouterr().err


def test_audio_dry_run_warns_instead_of_refusing(tmp_path, monkeypatch, capsys):
    from audio_generator import pipeline
    monkeypatch.setattr(sys, "argv", ["pipeline", "--course", "econ", "--academic-hub-root", str(tmp_path),
                                      "--dry-run"])
    called = []
    monkeypatch.setattr(pipeline, "discover_source_files", lambda *a, **k: called.append(True) or [])
    pipeline.main()
    assert called == [True]
    assert "link preflight skipped" in capsys.readouterr().err


@pytest.mark.parametrize("extra", [["--submit", "r1"], ["--collect"]])
def test_transcribe_dry_run_with_writing_flags_still_refuses(tmp_path, monkeypatch, capsys, extra):
    """--dry-run does not make --submit/--collect read-only: both still write, so an open item refuses."""
    from core.indexer import preflight
    from core.indexer.review_envelope import ReviewItem
    from pipelines.transcribe_notes import transcribe_notes as tn

    monkeypatch.setenv("ACADEMIC_HUB_ROOT_OVERRIDE", str(tmp_path))
    monkeypatch.setattr(tn, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(preflight, "check",
                        lambda *a, **k: [ReviewItem("i1", "relink", ["f1"], [], "pending")])
    monkeypatch.setattr(sys, "argv", ["transcribe_notes", "--notes-subdir", "academic_notes/econ/x",
                                      "--dry-run", *extra])
    with pytest.raises(SystemExit) as exc:
        tn.main()
    assert exc.value.code == 2
    assert "hub_review page" in capsys.readouterr().err
