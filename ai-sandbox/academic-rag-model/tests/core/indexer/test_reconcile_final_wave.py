"""Regression tests for the hub-path-resilience P3 final review wave (C1, I3, I4).

tmp_path fixture hubs only; any model-client construction fails the test.
"""
from __future__ import annotations

import contextlib
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.indexer import reconcile_apply
from core.indexer.hub_identity import write_hub_id
from core.indexer.index_card import compute_content_hash, find_card_by_file_id, save_shard
from core.indexer.index_search import rebuild
from core.indexer.reconcile import reconcile
from core.indexer.reconcile_apply import (
    apply_repairs, raise_relink_items, resolve, undo_repair,
)
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.state import StateStore

LN = "academic_notes/econ/lecture_notes"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / "state")


def _no_calls_client():
    client = MagicMock()
    client.models.generate_content.side_effect = AssertionError("no generation call expected")
    client.models.embed_content.side_effect = AssertionError("no embedding call expected")
    return client


def _move(hub: Path, old: str, new: str) -> None:
    (hub / new).parent.mkdir(parents=True, exist_ok=True)
    os.replace(hub / old, hub / new)


def _card(hub: Path, fid: str) -> dict:
    return find_card_by_file_id(str(hub), fid)[1]


def _note_card(hub: Path, rel: str, fid: str, **extra) -> dict:
    return {"file_id": fid, "path": rel, "course": "econ",
            "content_hash": compute_content_hash(str(hub / rel)), **extra}


# --- C1: a moved clone without a hub_id is repaired and un-orphaned -------------------------------

def _clone_hub(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "hub"
    pdf = root / "academic_resources/econometrics/problem_sets/clone.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 byte-identical duplicate")
    md = root / "academic_notes/econometrics/problem_sets/processed_outputs/clone.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\nduplicate_of_file_id: canonical\n---\n\nClone transcription body.\n",
                  encoding="utf-8", newline="\n")
    rel_md = md.relative_to(root).as_posix()
    save_shard(str(root), "econometrics", [{
        "file_id": "clone-id", "path": rel_md,
        "source_pdf_path": pdf.relative_to(root).as_posix(),
        "duplicate_of_file_id": "canonical", "course": "econometrics",
        "embedding": [1, 0], "content_hash": compute_content_hash(str(md)),
    }])
    return root, rel_md, pdf.relative_to(root).as_posix()


def test_moved_unstamped_clone_is_repaired_and_not_orphaned_after_rebuild(tmp_path):
    root, rel_md, rel_pdf = _clone_hub(tmp_path)
    rebuild(str(root), _no_calls_client(), course="econometrics")
    assert not _card(root, "clone-id").get("orphaned")

    new_md = rel_md.replace("econometrics/problem_sets", "econometrics/part_1/problem_sets")
    new_pdf = rel_pdf.replace("econometrics/problem_sets", "econometrics/part_1/problem_sets")
    _move(root, rel_md, new_md)
    _move(root, rel_pdf, new_pdf)
    (root / "academic_notes/econometrics/problem_sets").rmdir() if not any(
        (root / "academic_notes/econometrics/problem_sets").rglob("*")) else None

    rebuild(str(root), _no_calls_client(), course="econometrics")
    assert _card(root, "clone-id").get("orphaned") is True  # unseen: the clone moved, no hub_id

    diffs = reconcile(str(root))
    assert [(d.kind, d.file_id, d.candidates[0].path) for d in diffs] == [("moved", "clone-id", new_md)]
    (rec,) = apply_repairs(str(root), diffs)
    assert rec.was_orphaned is True
    card = _card(root, "clone-id")
    assert card["path"] == new_md and not card.get("orphaned")  # repair clears the flag

    rebuild(str(root), _no_calls_client(), course="econometrics")
    card = _card(root, "clone-id")
    assert card["path"] == new_md
    assert not card.get("orphaned")
    assert (root / card["path"]).is_file()
    assert reconcile(str(root)) == []


def test_rebuild_clears_a_stale_orphan_flag_on_a_seen_card(tmp_path):
    root, rel_md, _ = _clone_hub(tmp_path)
    cards = [dict(_card(root, "clone-id"), orphaned=True)]
    save_shard(str(root), "econometrics", cards)
    rebuild(str(root), _no_calls_client(), course="econometrics")
    assert not _card(root, "clone-id").get("orphaned")


def test_undo_restores_only_the_logged_orphan_flag(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    write_note(hub, f"{LN}/b.md", {"title": "b"}, BODY + "b\n")
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "n1", orphaned=True),
                                  _note_card(hub, f"{LN}/b.md", "n2")])
    _move(hub, f"{LN}/a.md", f"{LN}/g/a.md")
    _move(hub, f"{LN}/b.md", f"{LN}/g/b.md")
    recs = {r.file_id: r for r in apply_repairs(str(hub), reconcile(str(hub)))}
    assert not _card(hub, "n1").get("orphaned")
    assert undo_repair(str(hub), recs["n1"].repair_id)
    assert undo_repair(str(hub), recs["n2"].repair_id)
    assert _card(hub, "n1").get("orphaned") is True   # logged as orphaned before the repair
    assert "orphaned" not in _card(hub, "n2")          # was not: undo leaves it unflagged


# --- I3: undo sticks ------------------------------------------------------------------------------

def test_undo_then_apply_repairs_does_nothing_and_offers_the_move_for_review(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/x.md", {"title": "x"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/x.md", "n1")])
    _move(hub, f"{LN}/x.md", f"{LN}/g/x.md")
    (rec,) = apply_repairs(str(hub), reconcile(str(hub)))
    assert undo_repair(str(hub), rec.repair_id, store=store)
    assert _card(hub, "n1")["path"] == f"{LN}/x.md"

    assert apply_repairs(str(hub), reconcile(str(hub))) == []
    assert _card(hub, "n1")["path"] == f"{LN}/x.md"

    items = raise_relink_items(str(hub), None, store)
    assert [(i.type, i.status, [c["path"] for c in i.candidates]) for i in items] == [
        ("relink", "pending", [f"{LN}/g/x.md"])]
    assert _card(hub, "n1").get("link_state") == "unresolved"

    # The owner can still choose the move on the page: a fresh repair id.
    assert resolve(str(hub), "n1", f"{LN}/g/x.md", store=store)
    assert _card(hub, "n1")["path"] == f"{LN}/g/x.md"


def test_undo_after_resolve_reopens_the_item_and_marks_the_card_unresolved(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/lecture_03_regression.md", "n1")])
    # Rename + edit: no exact match, so only a review candidate.
    _move(hub, f"{LN}/lecture_03_regression.md", f"{LN}/lecture_03_regression_v2.md")
    with open(hub / f"{LN}/lecture_03_regression_v2.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("An added line.\n")
    (item,) = raise_relink_items(str(hub), None, store)
    assert (item.type, item.status) == ("relink", "pending")
    assert resolve(str(hub), "n1", f"{LN}/lecture_03_regression_v2.md", store=store)
    assert _card(hub, "n1")["path"] == f"{LN}/lecture_03_regression_v2.md"
    log = reconcile_apply._read_log(str(hub))
    repair_id = log[-1]["repair_id"]
    assert log[-1]["origin"] == "resolve"

    assert undo_repair(str(hub), repair_id, store=store)
    assert _card(hub, "n1")["path"] == f"{LN}/lecture_03_regression.md"
    assert _card(hub, "n1").get("link_state") == "unresolved"

    items = raise_relink_items(str(hub), None, store)
    assert [(i.item_id, i.status) for i in items] == [(item.item_id, "pending")]
    assert _card(hub, "n1").get("link_state") == "unresolved"

