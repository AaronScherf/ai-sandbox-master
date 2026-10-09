from __future__ import annotations

import subprocess
import sys

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.postprocess_notes import postprocess_notes as cli


def _repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, *, dry_run=False):
    outer = _repo(tmp_path / "outer")
    hub = outer / "academic-hub"
    hub.mkdir()
    notes = _repo(hub / "academic_notes")
    target = notes / "econometrics" / "processed_outputs" / "one.md"
    target.parent.mkdir(parents=True)
    target.write_text("---\nrouting: local\n---\nbody", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["postprocess_notes", "--root", str(notes),
                                      *(["--dry-run"] if dry_run else [])])
    monkeypatch.setattr(cli, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(cli, "get_gemini_client", lambda: object())
    monkeypatch.setattr(cli, "discover_markdown_files", lambda *args: [str(target)])
    monkeypatch.setattr(cli, "parse_frontmatter", lambda *args: ({"routing": "local"}, "body"))
    monkeypatch.setattr(cli, "is_correction_target", lambda *args: True)
    monkeypatch.setattr(cli, "group_findings_by_signature", lambda *args: [])
    monkeypatch.setattr(cli, "documents_needing_review", lambda *args, **kwargs: [])
    return hub, notes


def test_postprocessing_holds_notes_and_hub_locks(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch)
    observed = []

    def process(*args, **kwargs):
        for root in (hub, notes):
            with pytest.raises(CorpusWriteLockError, match="notes postprocessing"):
                with corpus_write_lock([root], "competing writer"):
                    pass
        observed.append(True)
        return []

    monkeypatch.setattr(cli, "process_document", process)
    cli.main()
    assert observed == [True]


@pytest.mark.parametrize("target", ["hub", "notes"])
def test_postprocessing_refuses_competing_writer(tmp_path, monkeypatch, target):
    hub, notes = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "process_document", lambda *args, **kwargs: pytest.fail("processed"))
    with corpus_write_lock([hub if target == "hub" else notes], "other writer"):
        with pytest.raises(SystemExit, match="other writer"):
            cli.main()


def test_postprocessing_dry_run_needs_no_writer_lock(tmp_path, monkeypatch):
    hub, notes = _setup(tmp_path, monkeypatch, dry_run=True)
    observed = []
    monkeypatch.setattr(cli, "process_document", lambda *args, **kwargs: observed.append(kwargs) or [])
    with corpus_write_lock([hub, notes], "other writer"):
        cli.main()
    assert observed == [{"dry_run": True}]
