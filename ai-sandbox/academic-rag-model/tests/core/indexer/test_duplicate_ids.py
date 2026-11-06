"""Duplicate hub_id detection and repair (hub-path-resilience P4). tmp_path only; no model client."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from core.indexer.duplicate_ids import find_duplicate_hub_ids, restamp_duplicates
from core.indexer.hub_identity import read_hub_id
from core.indexer.index_card import compute_content_hash, load_shard, save_shard
from core.indexer.reconcile import reconcile
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.report import ScanReport

LN = "academic_notes/econ/lecture_notes"
BODY_A = "# Regression\n\nOLS minimizes squared residuals.\n" * 3
BODY_B = "# Demand\n\nA different note about consumer demand.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


def _digest(hub: Path) -> dict[str, str]:
    return {str(p.relative_to(hub)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(hub.rglob("*")) if p.is_file()}


def _card(hub: Path, rel: str, fid: str, **extra) -> dict:
    return {"file_id": fid, "path": rel, "course": "econ",
            "content_hash": compute_content_hash(str(hub / rel)), **extra}


def _dup_hub(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    write_note(hub, f"{LN}/c.md", {"hub_id": "uniq00000001"}, "# C\n\nOther.\n")
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="dup000000001"),
                                  _card(hub, f"{LN}/b.md", "f2", hub_id="dup000000001"),
                                  _card(hub, f"{LN}/c.md", "f3", hub_id="uniq00000001")])
    return hub


def test_two_files_same_id_reported(tmp_path):
    hub = _dup_hub(tmp_path)
    assert find_duplicate_hub_ids(str(hub)) == {"dup000000001": [f"{LN}/a.md", f"{LN}/b.md"]}


def test_derived_outputs_are_not_reported(tmp_path):
    hub = _dup_hub(tmp_path)
    write_note(hub, f"{LN}/a.rag.md", {"hub_id": "dup000000001"}, BODY_A)
    assert find_duplicate_hub_ids(str(hub))["dup000000001"] == [f"{LN}/a.md", f"{LN}/b.md"]


def test_two_cards_same_id_reported(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "aaaaaaaaaaaa"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "bbbbbbbbbbbb"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="cccccccccccc"),
                                  _card(hub, f"{LN}/b.md", "f2", hub_id="cccccccccccc")])
    assert find_duplicate_hub_ids(str(hub)) == {"cccccccccccc": [f"{LN}/a.md", f"{LN}/b.md"]}


def test_dry_run_writes_nothing(tmp_path):
    hub = _dup_hub(tmp_path)
    before = _digest(hub)
    [(path, old, new)] = restamp_duplicates(str(hub), {}, apply=False)
    assert old == "dup000000001" and new != old and path in (f"{LN}/a.md", f"{LN}/b.md")
    assert _digest(hub) == before


def test_apply_restamps_only_the_loser_and_updates_its_card(tmp_path):
    hub = _dup_hub(tmp_path)
    c_before = (hub / LN / "c.md").read_bytes()
    a_before = (hub / LN / "a.md").read_bytes()
    [(path, old, new)] = restamp_duplicates(str(hub), {"dup000000001": f"{LN}/a.md"}, apply=True)
    assert path == f"{LN}/b.md"
    assert (hub / LN / "a.md").read_bytes() == a_before
    assert (hub / LN / "c.md").read_bytes() == c_before
    assert read_hub_id(str(hub / path)) == new != old
    cards = {c["path"]: c for c in load_shard(str(hub), "econ")}
    assert cards[path]["hub_id"] == new
    assert cards[path]["content_hash"] == compute_content_hash(str(hub / path))
    assert cards[f"{LN}/a.md"]["hub_id"] == old
    assert find_duplicate_hub_ids(str(hub)) == {}


def test_default_keeper_is_the_file_its_card_points_at(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/b.md", "f2", hub_id="dup000000001")])
    [(path, _, _)] = restamp_duplicates(str(hub), {}, apply=False)
    assert path == f"{LN}/a.md"


def test_move_with_duplicate_id_is_ambiguous_not_moved(tmp_path):
    """Documents current reconcile behaviour: safe, never silently picks a duplicate."""
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"hub_id": "dup000000001"}, BODY_A)
    write_note(hub, f"{LN}/b.md", {"hub_id": "dup000000001"}, BODY_B)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1", hub_id="dup000000001")])
    os.replace(hub / LN / "a.md", hub / LN / "a_renamed.md")
    diffs = reconcile(str(hub))
    assert diffs and all(d.kind == "ambiguous" for d in diffs)
    assert not any(d.kind == "moved" for d in diffs)


def test_duplicate_reported_in_scan_text(tmp_path):
    from tools.corpus_health.duplicates import duplicate_findings

    hub = _dup_hub(tmp_path)
    findings = duplicate_findings(str(hub))
    assert [f.kind for f in findings] == ["duplicate_hub_id"]
    text = ScanReport(findings=findings).to_text()
    assert "duplicate_hub_id" in text and "dup000000001" in text and f"{LN}/b.md" in text


def test_cli_fix_duplicates_dry_run_then_apply(tmp_path, capsys, monkeypatch):
    import contextlib
    import tools.write_hub_ids as w

    hub = _dup_hub(tmp_path)
    monkeypatch.setattr(w, "corpus_write_lock", lambda *a, **k: contextlib.nullcontext())
    before = _digest(hub)
    monkeypatch.setattr("sys.argv", ["x", "--hub-root", str(hub), "--fix-duplicates"])
    w.main()
    assert f"{LN}/b.md: dup000000001 ->" in capsys.readouterr().out
    assert _digest(hub) == before
    monkeypatch.setattr("sys.argv", ["x", "--hub-root", str(hub), "--fix-duplicates", "--apply"])
    w.main()
    assert find_duplicate_hub_ids(str(hub)) == {}
