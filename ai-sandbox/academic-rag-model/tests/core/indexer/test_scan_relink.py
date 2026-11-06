"""Corpus-health scan raises relink/orphan ledger items without writing any hub file."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from core.env.corpus_write_lock import CorpusWriteLockError
from core.indexer import reconcile_apply
from core.indexer.index_card import compute_content_hash, save_shard
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.cli import main
from tools.corpus_health.state import StateStore

LN = "academic_notes/econ/lecture_notes"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called in scan tests")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


def _note_card(hub: Path, rel: str, fid: str) -> dict:
    return {"file_id": fid, "path": rel, "course": "econ", "content_hash": compute_content_hash(str(hub / rel))}


def _cards_digest(hub: Path) -> dict[str, str]:
    return {str(p.relative_to(hub)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((hub / ".index").rglob("*")) if p.is_file()}


def _config(tmp_path: Path, hub: Path) -> Path:
    if not (hub / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=hub, check=True)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "academic_hub_root": str(hub), "academic_notes_root": None,
                                "required_roots": ["hub"], "markdown_policies": []}), encoding="utf-8")
    return path


def _scan(tmp_path, hub, capsys, *extra):
    code = main(["scan", "--config", str(_config(tmp_path, hub)), "--state-dir", str(tmp_path / "state"), *extra])
    return code, capsys.readouterr().out


def _rename_and_edit_hub(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/lecture_03_regression.md", "f1")])
    os.replace(hub / LN / "lecture_03_regression.md", hub / LN / "lecture_03_regression_v2.md")
    with open(hub / LN / "lecture_03_regression_v2.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\nAn added paragraph on heteroskedasticity.\n")
    return hub


def test_scan_raises_relink_item_in_ledger_without_touching_cards(tmp_path, capsys):
    hub = _rename_and_edit_hub(tmp_path)
    before = _cards_digest(hub)
    code, _ = _scan(tmp_path, hub, capsys)
    assert code == 0
    assert _cards_digest(hub) == before
    kinds = [e["finding"]["kind"] for e in StateStore(tmp_path / "state").entries()]
    assert "relink" in kinds


def test_scan_does_not_sweep_existing_relink_items(tmp_path, capsys, monkeypatch):
    hub = _rename_and_edit_hub(tmp_path)
    _scan(tmp_path, hub, capsys)
    ids = {e["finding_id"] for e in StateStore(tmp_path / "state").entries() if e["finding"]["kind"] == "relink"}
    assert ids

    @contextlib.contextmanager
    def busy(roots, action, **kw):
        raise CorpusWriteLockError("writer already active for fake")
        yield

    # relink pass cannot run: the default refresh sweep must still leave the items alone
    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", busy)
    _scan(tmp_path, hub, capsys)
    after = [e for e in StateStore(tmp_path / "state").entries() if e["finding_id"] in ids]
    assert len(after) == len(ids) and all(e["status"] != "vanished" for e in after)


def test_scan_with_busy_write_lock_warns_and_continues(tmp_path, capsys, monkeypatch):
    hub = _rename_and_edit_hub(tmp_path)

    @contextlib.contextmanager
    def busy(roots, action, **kw):
        raise CorpusWriteLockError("writer already active for fake")
        yield

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", busy)
    before = _cards_digest(hub)
    code, out = _scan(tmp_path, hub, capsys)
    assert code == 0
    assert "WARNING" in out and "writer already active" in out
    assert _cards_digest(hub) == before


def test_scan_notes_waiting_exact_moves_in_text_report(tmp_path, capsys):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1")])
    os.replace(hub / LN / "a.md", hub / LN / "renamed.md")
    before = _cards_digest(hub)
    code, out = _scan(tmp_path, hub, capsys)
    assert code == 0
    assert "1 exact moves waiting: run hub_review repair" in out
    assert _cards_digest(hub) == before
    kinds = {e["finding"]["kind"] for e in StateStore(tmp_path / "state").entries()}
    assert kinds <= {"relink", "orphan_card"}


def test_scan_notes_unresolved_orphans_in_text_report(tmp_path, capsys):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1")])
    os.remove(hub / LN / "a.md")
    code, out = _scan(tmp_path, hub, capsys)
    assert code == 0
    assert "1 moved/orphaned files need review: run hub_review export" in out
    assert "exact moves waiting" not in out
