"""Hub-path-resilience P3 acceptance matrix: real reconcile + apply on tmp_path fixture hubs.

Every test runs with model-client construction and calls forbidden: any API call fails the test.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path

import pytest

from core.indexer import reconcile_apply
from core.indexer.hub_identity import write_hub_id
from core.indexer.index_card import compute_content_hash, compute_file_id, find_card_by_file_id, save_shard
from core.indexer.reconcile import reconcile
from core.indexer.reconcile_apply import apply_repairs, raise_relink_items, reject, resolve
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.state import StateStore

LN = "academic_notes/econ/lecture_notes"
PS = "academic_notes/econ/problem_sets"
RES = "academic_resources/econ"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called in reconcile scenarios")

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


def _move(hub: Path, old: str, new: str) -> None:
    (hub / new).parent.mkdir(parents=True, exist_ok=True)
    os.replace(hub / old, hub / new)


def _card(hub: Path, fid: str) -> dict:
    return find_card_by_file_id(str(hub), fid)[1]


def _note_card(hub: Path, rel: str, fid: str, **extra) -> dict:
    return {"file_id": fid, "path": rel, "course": "econ",
            "content_hash": compute_content_hash(str(hub / rel)), **extra}


def _pdf_card(hub: Path, rel: str) -> dict:
    return {"file_id": compute_file_id(str(hub / rel)), "path": rel, "course": "econ"}


def _digest(hub: Path) -> dict[str, str]:
    return {str(p.relative_to(hub)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(hub.rglob("*")) if p.is_file() and ".index" not in p.parts}


def test_nest_notes_one_layer(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/x.md", {"title": "x"}, BODY)
    write_note(hub, f"{LN}/y.md", {"title": "y"}, "# Other\n\nA completely different note about game theory.\n")
    pdf = hub / f"{RES}/paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake paper")
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/x.md", "n1"), _note_card(hub, f"{LN}/y.md", "n2"),
                                  _pdf_card(hub, f"{RES}/paper.pdf")])
    pdf_id = compute_file_id(str(pdf))
    _move(hub, f"{LN}/x.md", f"{LN}/group/x.md")
    _move(hub, f"{LN}/y.md", f"{LN}/group/y.md")
    _move(hub, f"{RES}/paper.pdf", f"{RES}/group/paper.pdf")
    diffs = reconcile(str(hub))
    apply_repairs(str(hub), diffs)
    raise_relink_items(str(hub), reconcile(str(hub)), store)
    assert _card(hub, "n1")["path"] == f"{LN}/group/x.md"
    assert _card(hub, "n2")["path"] == f"{LN}/group/y.md"
    assert _card(hub, pdf_id)["path"] == f"{RES}/group/paper.pdf"
    for fid in ("n1", "n2", pdf_id):  # nothing linked to a file that is not there
        assert (hub / _card(hub, fid)["path"]).is_file()
    assert reconcile(str(hub)) == []


def test_rename_file_auto_repairs(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1")])
    before = _card(hub, "f1")["content_hash"]
    _move(hub, f"{LN}/a.md", f"{LN}/renamed.md")
    [d] = reconcile(str(hub))
    assert d.kind == "moved"
    [rec] = apply_repairs(str(hub), [d])
    assert rec.status == "done"
    card = _card(hub, "f1")
    assert card["path"] == f"{LN}/renamed.md"
    assert card["content_hash"] == before == compute_content_hash(str(hub / f"{LN}/renamed.md"))


def test_rename_and_edit_raises_ranked_review_item(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    write_note(hub, f"{LN}/syllabus.md", {"title": "s"}, "# Syllabus\n\nOffice hours.\n")
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/lecture_03_regression.md", "f1"),
                                  _note_card(hub, f"{LN}/syllabus.md", "f2")])
    _move(hub, f"{LN}/lecture_03_regression.md", f"{LN}/lecture_03_regression_v2.md")
    with open(hub / LN / "lecture_03_regression_v2.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\nAn added paragraph on heteroskedasticity.\n")
    write_note(hub, f"{LN}/unrelated_topic.md", {"title": "u"}, "# Game theory\n")
    diffs = reconcile(str(hub))
    [d] = diffs
    assert (d.kind, d.file_id) == ("ambiguous", "f1")
    assert d.candidates[0].path == f"{LN}/lecture_03_regression_v2.md"
    assert d.candidates[0].basis == "similarity"
    assert apply_repairs(str(hub), diffs) == []
    items = raise_relink_items(str(hub), diffs, store)
    assert [i.type for i in items] == ["relink"] and len(store.pending()) == 1
    card = _card(hub, "f1")
    assert card["path"] == f"{LN}/lecture_03_regression.md"
    assert card["link_state"] == "unresolved"


def test_scenario_e_course_folder_renamed_auto_repairs_every_file(tmp_path, store):
    hub = make_hub(tmp_path)
    cards = []
    for i in range(3):
        rel = f"{LN}/n{i}.md"
        p = write_note(hub, rel, {"title": f"n{i}"}, BODY + f"\nUnique line number {i} about topic {i}.\n")
        hid = write_hub_id(str(p))
        cards.append(_note_card(hub, rel, f"n{i}", hub_id=hid))
    for i in range(2):
        rel = f"{RES}/r{i}.pdf"
        (hub / rel).write_bytes(f"%PDF-1.4 resource {i}".encode())
        cards.append(_pdf_card(hub, rel))
    save_shard(str(hub), "econ", cards)
    ids = [c["file_id"] for c in cards]
    os.replace(hub / "academic_notes/econ", hub / "academic_notes/econ_renamed")
    os.replace(hub / "academic_resources/econ", hub / "academic_resources/econ_renamed")
    diffs = reconcile(str(hub))
    assert {d.kind for d in diffs} == {"moved"} and len(diffs) == 5
    assert len(apply_repairs(str(hub), diffs)) == 5
    assert raise_relink_items(str(hub), reconcile(str(hub)), store) == []
    assert store.pending() == []
    for fid in ids:
        card = _card(hub, fid)
        assert "_renamed/" in card["path"] and (hub / card["path"]).is_file()
        assert not card.get("link_state")


def test_two_identical_files_after_move_review_neither_linked(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1")])
    data = (hub / f"{LN}/a.md").read_bytes()
    os.remove(hub / f"{LN}/a.md")
    (hub / f"{PS}/one.md").write_bytes(data)
    (hub / f"{PS}/two.md").write_bytes(data)
    diffs = reconcile(str(hub))
    [d] = diffs
    assert d.kind == "ambiguous" and len(d.candidates) == 2
    assert apply_repairs(str(hub), diffs) == []
    raise_relink_items(str(hub), diffs, store)
    assert _card(hub, "f1")["path"] == f"{LN}/a.md"
    assert resolve(str(hub), "f1", f"{PS}/one.md", store=store) is True
    card = _card(hub, "f1")
    assert card["path"] == f"{PS}/one.md" and not card.get("link_state")


def test_delete_file_reports_orphan_deletes_nothing(tmp_path, store):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    write_note(hub, f"{LN}/keep.md", {"title": "k"}, "# Keep\n\nSomething unrelated entirely.\n")
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1"), _note_card(hub, f"{LN}/keep.md", "f2")])
    os.remove(hub / f"{LN}/a.md")
    before = _digest(hub)
    diffs = reconcile(str(hub))
    [d] = diffs
    assert (d.kind, d.file_id, d.candidates) == ("orphan", "f1", [])
    assert apply_repairs(str(hub), diffs) == []
    raise_relink_items(str(hub), diffs, store)
    assert _digest(hub) == before
    assert _card(hub, "f1")["path"] == f"{LN}/a.md"
    assert reject(str(hub), "f1", store=store) is True
    assert raise_relink_items(str(hub), reconcile(str(hub)), store) == []
    assert _digest(hub) == before


@pytest.mark.xfail(strict=True, reason="P4 preflight")
def test_pipeline_refuses_with_unresolved_item_it_needs():
    assert False, "P4 preflight not built"


def test_content_tier_card_with_existing_path_is_not_hashed(tmp_path):
    """Deliberate design (R10): a content-tier (derived-output) card whose path still resolves is never
    hashed, so an in-place edit yields no Difference. That is the indexer's staleness check, not a
    location problem. Hashing there would let `moved` auto-apply for a regenerated file that has a
    stale copy elsewhere, silently relinking the card to the stale copy."""
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/a.md", "f1")])
    with open(hub / LN / "a.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\nEdited in place after indexing.\n")
    assert reconcile(str(hub)) == []


def _rename_and_edit_hub(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_note_card(hub, f"{LN}/lecture_03_regression.md", "f1")])
    _move(hub, f"{LN}/lecture_03_regression.md", f"{LN}/lecture_03_regression_v2.md")
    with open(hub / LN / "lecture_03_regression_v2.md", "a", encoding="utf-8", newline="\n") as f:
        f.write("\nAn added paragraph on heteroskedasticity.\n")
    return hub


def test_raise_relink_items_mark_link_state_false_writes_ledger_only(tmp_path, store):
    hub = _rename_and_edit_hub(tmp_path)
    before = dict(_card(hub, "f1"))
    items = raise_relink_items(str(hub), reconcile(str(hub)), store, mark_link_state=False)
    assert [i.type for i in items] == ["relink"] and len(store.pending()) == 1
    assert _card(hub, "f1") == before and not _card(hub, "f1").get("link_state")


def test_raise_relink_items_mark_link_state_true_is_the_default(tmp_path, store):
    hub = _rename_and_edit_hub(tmp_path)
    raise_relink_items(str(hub), reconcile(str(hub)), store)
    assert _card(hub, "f1")["link_state"] == "unresolved"
