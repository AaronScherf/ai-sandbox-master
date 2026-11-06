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
    for name in ("chunk", "retag"):
        monkeypatch.setattr(index_search, name, lambda *a, **k: {})
    monkeypatch.setattr(index_search, "rebuild_plan", lambda *a, **k: {"estimated_paid_cards": 0})
    monkeypatch.setattr(index_search, "markdown_preview", lambda *a, **k: [])
    index_search.main()  # a SystemExit(2) here fails the test
    assert "link preflight skipped" in capsys.readouterr().err


def test_audio_dry_run_warns_instead_of_refusing(tmp_path, monkeypatch, capsys):
    from audio_generator import pipeline
    monkeypatch.setattr(sys, "argv", ["pipeline", "--course", "econ", "--academic-hub-root", str(tmp_path),
                                      "--dry-run"])
    monkeypatch.setattr(pipeline, "discover_source_files", lambda *a, **k: [])
    pipeline.main()
    assert "link preflight skipped" in capsys.readouterr().err
