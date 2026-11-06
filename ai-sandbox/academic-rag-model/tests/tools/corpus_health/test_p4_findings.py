"""scan and apply share one producer for the P4 findings; a skipped producer never sweeps its kind."""
from __future__ import annotations

import contextlib
import json
import subprocess
from pathlib import Path

import pytest

from core.indexer import reconcile_apply
from tools.corpus_health import actions
from tools.corpus_health.cli import main
from tools.corpus_health.config import load_config
from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateStore


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


def _hub(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "academic_resources").mkdir()
    subprocess.run(["git", "init", "-q", str(hub)], check=True)
    (hub / "hub_config.json").write_text(json.dumps({"names": {}}) + "\n", encoding="utf-8")
    for course in ("econ", "micro"):
        p = hub / f"academic_notes/{course}/exam_kits/a.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return hub


def _cfg(tmp_path: Path, hub: Path) -> Path:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"version": 1, "academic_hub_root": str(hub), "academic_notes_root": None,
                               "required_roots": [], "markdown_policies": []}), encoding="utf-8")
    return cfg


def _statuses(store, kind):
    return {e["finding"]["title"]: e["status"] for e in store.entries(kinds={kind})}


def test_apply_after_scan_leaves_vocab_entries_open(tmp_path, capsys):
    hub = _hub(tmp_path)
    state = tmp_path / "state"
    main(["scan", "--config", str(_cfg(tmp_path, hub)), "--state-dir", str(state)])
    store = StateStore(state)
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}
    actions.apply_accepted(load_config(_cfg(tmp_path, hub)), store)
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}


def test_failed_producer_leaves_that_kinds_entries_pending_on_scan_and_apply(tmp_path, monkeypatch, capsys):
    hub = _hub(tmp_path)
    state = tmp_path / "state"
    cfg = _cfg(tmp_path, hub)
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    store = StateStore(state)

    def boom(_):
        raise RuntimeError("config unreadable")

    monkeypatch.setattr("tools.corpus_health.vocab.vocab_findings", boom)
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    assert "vocabulary check skipped" in capsys.readouterr().out
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}
    actions.apply_accepted(load_config(cfg), store)
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}


def test_missing_hub_config_warns_and_keeps_pending_vocab_entry(tmp_path, capsys):
    hub = _hub(tmp_path)
    state = tmp_path / "state"
    cfg = _cfg(tmp_path, hub)
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    store = StateStore(state)
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}
    (hub / "hub_config.json").unlink()
    capsys.readouterr()
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    assert "no hub_config.json; folder-name review disabled" in capsys.readouterr().out
    assert _statuses(store, "vocab_name") == {"exam_kits": "pending_review"}


def test_resolved_name_is_swept_when_producer_ran(tmp_path, monkeypatch, capsys):
    hub = _hub(tmp_path)
    state = tmp_path / "state"
    cfg = _cfg(tmp_path, hub)
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    monkeypatch.setattr("tools.corpus_health.vocab.vocab_findings", lambda _: [])
    main(["scan", "--config", str(cfg), "--state-dir", str(state)])
    assert _statuses(StateStore(state), "vocab_name") == {"exam_kits": "vanished"}


def test_add_p4_findings_reports_kinds_that_ran(tmp_path, monkeypatch):
    from tools.corpus_health.p4_findings import add_p4_findings

    class Report:
        def __init__(self):
            self.findings, self.warnings = [], []

    cfg = load_config(_cfg(tmp_path, _hub(tmp_path)))
    report = Report()
    assert add_p4_findings(report, cfg) == {"duplicate_hub_id", "vocab_name"}
    monkeypatch.setattr("tools.corpus_health.duplicates.duplicate_findings",
                        lambda _: (_ for _ in ()).throw(RuntimeError("git")))
    report = Report()
    assert add_p4_findings(report, cfg) == {"vocab_name"}
    assert "duplicate hub_id check skipped" in report.warnings[0]
    missing = load_config(_cfg(tmp_path, tmp_path / "nowhere"))
    assert add_p4_findings(Report(), missing) == set()


def test_moved_notice_excludes_undone_moves(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace

    from core.indexer import reconcile as reconcile_mod
    diffs = [SimpleNamespace(kind="moved", file_id="a"), SimpleNamespace(kind="moved", file_id="b")]
    monkeypatch.setattr(reconcile_mod, "reconcile", lambda _: diffs)
    monkeypatch.setattr(reconcile_apply, "demote_undone", lambda _h, ds: [d for d in ds if d.file_id == "a"])
    monkeypatch.setattr(reconcile_apply, "raise_relink_items", lambda *a, **k: [])
    hub = _hub(tmp_path)
    main(["scan", "--config", str(_cfg(tmp_path, hub)), "--state-dir", str(tmp_path / "state")])
    assert "1 exact moves waiting" in capsys.readouterr().out


def test_relink_warning_names_the_exception_type(tmp_path, monkeypatch, capsys):
    from core.indexer import reconcile as reconcile_mod
    monkeypatch.setattr(reconcile_mod, "reconcile", lambda _: (_ for _ in ()).throw(KeyError("x")))
    hub = _hub(tmp_path)
    main(["scan", "--config", str(_cfg(tmp_path, hub)), "--state-dir", str(tmp_path / "state")])
    assert "relink check skipped: KeyError: 'x'" in capsys.readouterr().out
