from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

from core.indexer.chunk_index import save_chunks
from core.indexer.index_card import compute_content_hash, save_shard
from tools.corpus_health import actions
from tools.corpus_health.cli import build_parser
from tools.corpus_health.config import ScanConfig
from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateStore


def _setup(tmp_path, monkeypatch):
    hub = tmp_path / "hub"
    source = hub / "academic_notes" / "econ" / "summaries" / "one.md"
    source.parent.mkdir(parents=True)
    source.write_text("# One\nUseful content.\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(hub)], check=True)
    index_path = "academic_notes/econ/summaries/one.md"
    content_hash = compute_content_hash(str(source))
    card = {"path": index_path, "file_id": "source-id", "content_hash": content_hash,
            "embedding": [0.1], "needs_indexing": False, "orphaned": False,
            "doc_type": "ta_notes"}
    save_shard(str(hub), "econ", [card])
    config = ScanConfig(hub, hub / "academic_notes", (), (), required_roots=("hub",))
    finding = Finding("index_chunks_missing_or_stale", "academic-hub-index", index_path,
                      "one.md", "missing_chunks", suggested_action="rebuild passage chunks",
                      fingerprint=content_hash, cost_category="paid_api", scope="notes/econ/summaries")
    store = StateStore(tmp_path / "state")
    approved = store.refresh([finding])[0]
    store.decide(approved.finding_id, "accepted", approved.fingerprint)
    monkeypatch.setattr(actions, "scan", lambda _: SimpleNamespace(complete=True, findings=[finding]))
    return config, store, source, card, finding, approved


def test_apply_runs_exact_file_id_under_lock_and_verifies_chunks(tmp_path, monkeypatch):
    config, store, _, card, _, approved = _setup(tmp_path, monkeypatch)
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        assert command[-3:] == ["--file-id", "source-id", "--json"]
        assert "CORPUS_WRITE_RUN_TOKEN" in kwargs["env"]
        assert kwargs["cwd"] == actions._PACKAGE_ROOT
        assert kwargs.get("shell") is not True
        save_chunks(str(config.academic_hub_root), "econ",
                    [{"file_id": card["file_id"], "content_hash": card["content_hash"]}])
        return SimpleNamespace(returncode=0, stdout=json.dumps(
            {"file_id": "source-id", "matched": True, "chunks_written": 1, "failed": 0}), stderr="")

    result = actions.apply_accepted(config, store, runner=runner)
    assert result[0]["status"] == "applied"
    assert len(calls) == 1
    assert store.get_entry(approved.finding_id)["status"] == "applied"


def test_changed_source_invalidates_approval_without_lock_or_process(tmp_path, monkeypatch):
    config, store, source, _, _, approved = _setup(tmp_path, monkeypatch)
    source.write_text("changed", encoding="utf-8")
    monkeypatch.setattr(actions, "corpus_write_lock", lambda *a, **k: (_ for _ in ()).throw(AssertionError("lock taken")))
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "pending_review"
    assert store.get_entry(approved.finding_id)["status"] == "pending_review"


def test_card_needs_indexing_is_blocked_before_process(tmp_path, monkeypatch):
    config, store, _, card, _, approved = _setup(tmp_path, monkeypatch)
    card["needs_indexing"] = True
    save_shard(str(config.academic_hub_root), "econ", [card])
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "blocked"
    assert "needs_indexing" in result[0]["reason"]
    assert store.get_entry(approved.finding_id)["status"] == "blocked"


def test_unsupported_accepted_card_repair_is_blocked(tmp_path, monkeypatch):
    config, store, _, _, _, _ = _setup(tmp_path, monkeypatch)
    finding = Finding("index_card_missing", "academic-hub-index", "academic_notes/econ/summaries/two.md",
                      "two.md", "missing_card", suggested_action="index this Markdown file",
                      fingerprint="1234", cost_category="paid_api")
    approved = store.refresh([finding])[0]
    store.decide(approved.finding_id, "accepted", approved.fingerprint)
    monkeypatch.setattr(actions, "scan", lambda _: SimpleNamespace(complete=True, findings=[finding]))
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "blocked"
    assert "no exact-file" in result[0]["reason"]


def test_failed_command_is_recorded_and_requires_new_review_after_scan(tmp_path, monkeypatch):
    config, store, _, _, finding, approved = _setup(tmp_path, monkeypatch)
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: SimpleNamespace(
        returncode=3, stdout="", stderr="API_KEY=very-secret"))
    assert result[0]["status"] == "failed"
    assert "very-secret" not in result[0]["stderr"]
    assert store.get_entry(approved.finding_id)["status"] == "failed"
    store.refresh([finding])
    assert store.get_entry(approved.finding_id)["status"] == "pending_review"


def test_blocked_entry_rechecks_and_applies_when_card_becomes_current(tmp_path, monkeypatch):
    config, store, _, card, _, approved = _setup(tmp_path, monkeypatch)
    card["needs_indexing"] = True
    save_shard(str(config.academic_hub_root), "econ", [card])
    assert actions.apply_accepted(config, store, runner=lambda *a, **k: None)[0]["status"] == "blocked"
    card["needs_indexing"] = False
    save_shard(str(config.academic_hub_root), "econ", [card])

    def runner(*args, **kwargs):
        save_chunks(str(config.academic_hub_root), "econ",
                    [{"file_id": card["file_id"], "content_hash": card["content_hash"]}])
        return SimpleNamespace(returncode=0, stdout=json.dumps(
            {"file_id": "source-id", "matched": True, "chunks_written": 1, "failed": 0}), stderr="")

    assert actions.apply_accepted(config, store, runner=runner)[0]["status"] == "applied"
    assert store.get_entry(approved.finding_id)["status"] == "applied"


def test_success_claim_without_verified_chunks_is_failed(tmp_path, monkeypatch):
    config, store, _, _, _, approved = _setup(tmp_path, monkeypatch)
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=json.dumps({"file_id": "source-id", "matched": True,
                                            "chunks_written": 1, "failed": 0}), stderr=""))
    assert result[0]["status"] == "failed"
    assert store.get_entry(approved.finding_id)["status"] == "failed"


def test_separate_notes_checkout_blocks_indexer_source_mismatch(tmp_path, monkeypatch):
    config, store, _, _, _, _ = _setup(tmp_path, monkeypatch)
    config = replace(config, academic_notes_root=tmp_path / "other-notes")
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "blocked"
    assert "notes checkout differs" in result[0]["reason"]


def test_lock_failure_is_recorded_without_invoking_child(tmp_path, monkeypatch):
    config, store, _, _, _, approved = _setup(tmp_path, monkeypatch)
    from core.env.corpus_write_lock import CorpusWriteLockError

    def unavailable(*args, **kwargs):
        raise CorpusWriteLockError("another writer")

    monkeypatch.setattr(actions, "corpus_write_lock", unavailable)
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "failed"
    assert "another writer" in result[0]["reason"]
    assert store.get_entry(approved.finding_id)["status"] == "failed"


def test_apply_cli_requires_explicit_accepted_queue():
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(["apply", "--config", "scan.json"])
    assert build_parser().parse_args(["apply", "--config", "scan.json", "--accepted"]).accepted


def test_index_path_outside_configured_roots_is_blocked(tmp_path, monkeypatch):
    config, store, _, _, _, _ = _setup(tmp_path, monkeypatch)
    finding = Finding("index_chunks_missing_or_stale", "academic-hub-index",
                      "academic_notes/econ/../../outside.md", "outside.md", "missing_chunks",
                      suggested_action="rebuild passage chunks", fingerprint="abcd",
                      cost_category="paid_api")
    approved = store.refresh([finding])[0]
    store.decide(approved.finding_id, "accepted", approved.fingerprint)
    monkeypatch.setattr(actions, "scan", lambda _: SimpleNamespace(complete=True, findings=[finding]))
    result = actions.apply_accepted(config, store, runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert result[0]["status"] == "blocked"
    assert "outside configured" in result[0]["reason"]
