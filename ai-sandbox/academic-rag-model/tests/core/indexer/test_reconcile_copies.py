"""Accepting identical files as copies of one note: one original card, a provenance-stamped card per copy."""
from __future__ import annotations

import contextlib
import os
from pathlib import Path

import pytest

from core.indexer import reconcile_apply
from core.indexer.hub_identity import read_hub_id, write_hub_id
from core.indexer.index_card import (
    carry_note_identity, compute_content_hash, copy_status, find_card_by_file_id, load_shard, save_shard,
)
from core.indexer.reconcile import reconcile
from core.indexer.reconcile_apply import raise_relink_items, resolve
from tests.core.indexer.hub_fixture import make_hub, write_note
from tests.core.indexer.test_reconcile_scenarios import _fake_lock, _no_model_client, store  # noqa: F401
import tools.hub_review as hub_review

LN = "academic_notes/econ/lecture_notes"
PS = "academic_notes/econ/problem_sets"
BODY = "# Problem set 1\n\nQuestion one. Question two. Question three.\n"


def _twin_hub(tmp_path: Path):
    """Stamped note f1 whose file is gone, while two identical copies (same hub_id) exist elsewhere."""
    hub = make_hub(tmp_path)
    original = write_note(hub, f"{LN}/ps1.md", {"title": "ps1"}, BODY)
    hid = write_hub_id(str(original))
    save_shard(str(hub), "econ", [{
        "file_id": "f1", "path": f"{LN}/ps1.md", "course": "econ", "hub_id": hid, "tags": ["consumer-choice"],
        "summary": "Problem set one.", "source_kind": "note",
        "content_hash": compute_content_hash(str(original))}])
    data = original.read_bytes()
    original.unlink()
    (hub / PS / "one.md").write_bytes(data)
    (hub / PS / "two.md").write_bytes(data)
    return hub, hid


def _card(hub, fid):
    return find_card_by_file_id(str(hub), fid)[1]


def _copy_card(hub, path):
    return next(c for c in load_shard(str(hub), "econ") if c["path"] == path)


def test_accepting_a_copy_gives_it_its_own_card_with_provenance(tmp_path, store):
    hub, hid = _twin_hub(tmp_path)
    raise_relink_items(str(hub), reconcile(str(hub)), store)
    assert resolve(str(hub), "f1", f"{PS}/one.md", copies=[f"{PS}/two.md"], store=store) is True
    assert _card(hub, "f1")["path"] == f"{PS}/one.md"
    copy = _copy_card(hub, f"{PS}/two.md")
    assert copy["copy_of_file_id"] == "f1" and copy["file_id"] != "f1"
    assert copy["tags"] == ["consumer-choice"] and copy["summary"] == "Problem set one."
    assert copy["hub_id"] != hid and read_hub_id(str(hub / PS / "two.md")) == copy["hub_id"]
    assert read_hub_id(str(hub / PS / "one.md")) == hid          # the original keeps its identity
    assert reconcile(str(hub)) == []                              # nothing left to review


def test_copy_is_identical_until_its_content_changes():
    origin = {"file_id": "f1", "content_hash": "a"}
    assert copy_status({"copy_of_file_id": "f1", "content_hash": "a"}, origin) == "identical"
    assert copy_status({"copy_of_file_id": "f1", "content_hash": "b"}, origin) == "diverged"
    assert copy_status({"content_hash": "a"}, origin) is None


def test_copy_provenance_survives_a_card_rebuild(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{PS}/two.md", {"title": "t"}, BODY)
    rebuilt = carry_note_identity(str(hub), {"path": f"{PS}/two.md"}, {"copy_of_file_id": "f1"})
    assert rebuilt["copy_of_file_id"] == "f1"


def test_a_copy_that_is_not_identical_is_refused_and_nothing_changes(tmp_path, store):
    hub, _ = _twin_hub(tmp_path)
    (hub / PS / "two.md").write_text(BODY + "\nAnswer: 42.\n", encoding="utf-8", newline="\n")
    before = load_shard(str(hub), "econ")
    assert resolve(str(hub), "f1", f"{PS}/one.md", copies=[f"{PS}/two.md"], store=store) is False
    assert load_shard(str(hub), "econ") == before


def test_a_copy_must_be_a_candidate_of_the_item(tmp_path, store):
    hub, _ = _twin_hub(tmp_path)
    write_note(hub, f"{PS}/elsewhere.md", {"title": "e"}, BODY)
    assert resolve(str(hub), "f1", f"{PS}/one.md", copies=[f"{PS}/elsewhere.md"], store=store) is False


def test_the_chosen_file_cannot_also_be_its_own_copy(tmp_path, store):
    hub, _ = _twin_hub(tmp_path)
    assert resolve(str(hub), "f1", f"{PS}/one.md", copies=[f"{PS}/one.md"], store=store) is False


def test_decision_with_copies_flows_through_apply(tmp_path, store):
    hub, _ = _twin_hub(tmp_path)
    [item] = hub_review.collect(str(hub), store)
    results = hub_review.apply_decisions(
        str(hub), [{"item_id": item.item_id, "action": "accept", "chosen": f"{PS}/one.md",
                    "copies": [f"{PS}/two.md"]}], store=store)
    assert [r["outcome"] for r in results] == ["applied"]
    assert _copy_card(hub, f"{PS}/two.md")["copy_of_file_id"] == "f1"


def test_malformed_copies_is_an_error_not_a_crash(tmp_path, store):
    hub, _ = _twin_hub(tmp_path)
    [item] = hub_review.collect(str(hub), store)
    results = hub_review.apply_decisions(
        str(hub), [{"item_id": item.item_id, "action": "accept", "chosen": f"{PS}/one.md", "copies": "two"}],
        store=store)
    assert results[0]["outcome"] == "error"
