"""Review envelope, relink ledger items, resolve/reject (hub-path-resilience P3 Task 5).

tmp_path hubs and a tmp_path StateStore; no model, no git, no API.
"""
from __future__ import annotations

import contextlib
import json
import os

import pytest

from core.indexer import reconcile_apply
from core.indexer.index_card import compute_content_hash, find_card_by_file_id, load_shard, save_shard
from core.indexer.reconcile import Candidate, Difference, reconcile
from core.indexer.reconcile_apply import raise_relink_items, raise_relink_items_unlocked, reject, resolve
from core.indexer.review_envelope import (
    ReviewItem, difference_to_item, is_unresolved, offering_link_to_item, pairing_to_item,
)
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.state import StateStore

LN = "academic_notes/econ/lecture_notes"
PS = "academic_notes/econ/problem_sets"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / "state")


def _setup(tmp_path):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": f"{LN}/a.md", "course": "econ",
                                   "content_hash": compute_content_hash(str(note))}])
    return hub


def _ambiguous(tmp_path):
    """The note was copied to two places and the original removed: two exact candidates."""
    hub = _setup(tmp_path)
    text = (hub / f"{LN}/a.md").read_bytes()
    (hub / f"{PS}/a.md").write_bytes(text)
    (hub / f"{PS}/a_copy.md").write_bytes(text)
    os.remove(hub / f"{LN}/a.md")
    diffs = reconcile(str(hub))
    assert [d.kind for d in diffs] == ["ambiguous"]
    return hub, diffs


def _orphan(tmp_path):
    hub = _setup(tmp_path)
    os.remove(hub / f"{LN}/a.md")
    diffs = reconcile(str(hub))
    assert [d.kind for d in diffs] == ["orphan"]
    return hub, diffs


def _card(hub, fid="f1"):
    return find_card_by_file_id(str(hub), fid)[1]


def _entries(store):
    return list(json.loads(store.state_path.read_text(encoding="utf-8"))["findings"].values())


# --- envelope (pure) ---

def test_difference_to_item_ranks_candidates_and_round_trips():
    d = Difference("ambiguous", "f1", f"{LN}/a.md",
                   [Candidate(f"{PS}/b.md", "byte_hash", 1.0), Candidate(f"{PS}/a.md", "similarity", 0.7)])
    item = difference_to_item(d)
    assert item.type == "relink" and item.subject_ids == ["f1"] and item.status == "pending"
    assert item.candidates == [{"path": f"{PS}/b.md", "basis": "byte_hash", "score": 1.0},
                               {"path": f"{PS}/a.md", "basis": "similarity", "score": 0.7}]
    assert ReviewItem.from_dict(item.to_dict()) == item


def test_item_id_stable_across_runs(tmp_path):
    hub, diffs = _ambiguous(tmp_path)
    again = reconcile(str(hub))
    assert difference_to_item(diffs[0]).item_id == difference_to_item(again[0]).item_id
    reordered = Difference("ambiguous", "f1", diffs[0].old_path, list(reversed(diffs[0].candidates)))
    assert difference_to_item(reordered).item_id == difference_to_item(diffs[0]).item_id
    other = Difference("ambiguous", "f1", diffs[0].old_path, diffs[0].candidates[:1])
    assert difference_to_item(other).item_id != difference_to_item(diffs[0]).item_id


def test_orphan_difference_is_report_only_item_and_moved_is_not_an_item():
    item = difference_to_item(Difference("orphan", "f1", f"{LN}/a.md"))
    assert item.type == "orphan" and item.candidates == []
    with pytest.raises(ValueError):
        difference_to_item(Difference("moved", "f1", f"{LN}/a.md", [Candidate(f"{PS}/a.md", "byte_hash", 1.0)]))


def _real_offering_review(tmp_path):
    """review.json written by the real producer (offering_links.run_for_course, review band)."""
    from core.indexer.offering_links import load_review, run_for_course
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    cards = [{"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]},
             {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}]
    for card in cards:
        (tmp_path / card["path"]).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / card["path"]).write_text("body\n")
    save_shard(str(tmp_path), "econometrics", cards)
    assert run_for_course(str(tmp_path), "econometrics")["review_matches"] == 1
    return load_review(str(tmp_path))


def test_envelope_adapters_cover_offering_links_entry(tmp_path):
    (entry,) = _real_offering_review(tmp_path)
    snapshot = json.dumps(entry, sort_keys=True)
    item = offering_link_to_item(entry)
    assert item.type == "offering_link" and item.subject_ids == ["fa", "fb"]
    assert item.status == "pending" and (item.created, item.updated) == ("", "")
    (cand,) = item.candidates
    assert cand["file_id"] == "fb" and cand["score"] == entry["similarity"]
    assert cand["path"] is None and cand["subject_paths"] == [None, None]
    with_paths = offering_link_to_item(entry, hub_root=str(tmp_path))
    assert with_paths.candidates[0]["subject_paths"] == [
        "academic_notes/econometrics/professor_notes/a.md", "academic_notes/econometrics/class_2024/b.md"]
    assert with_paths.candidates[0]["path"] == "academic_notes/econometrics/class_2024/b.md"
    assert with_paths.item_id == item.item_id
    assert json.dumps(entry, sort_keys=True) == snapshot  # read only


def test_envelope_adapter_covers_document_pairing_entry(tmp_path):
    from core.indexer.document_pairing import load_review, run_for_course
    cards = [{"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "course": "microecon"},
             {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/processed_outputs/HW_4.md",
              "course": "microecon"},
             {"file_id": "fc", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "course": "microecon"}]
    (tmp_path / "academic_notes" / "microecon").mkdir(parents=True)
    save_shard(str(tmp_path), "microecon", cards)
    run_for_course(str(tmp_path), "microecon")
    review = load_review(str(tmp_path))
    assert len(review) == 2
    items = [pairing_to_item(e, hub_root=str(tmp_path)) for e in review]
    paths = {c["file_id"]: c["path"] for c in cards}
    for entry, item in zip(review, items):
        assert item.type == "document_pairing"
        assert item.subject_ids == [entry["file_id_a"], entry["file_id_b"]]
        assert item.candidates[0]["basis"] == entry["pair_type"] and item.candidates[0]["score"] is None
        assert item.candidates[0]["subject_paths"] == [paths[entry["file_id_a"]], paths[entry["file_id_b"]]]
    assert len({i.item_id for i in items}) == 2
    assert items[0].item_id != offering_link_to_item({**review[0], "similarity": 0.9}).item_id


def test_is_unresolved():
    assert is_unresolved({"link_state": "unresolved"}) is True
    assert is_unresolved({}) is False


# --- ledger + card mark ---

def test_ambiguous_difference_becomes_pending_relink_item_and_card_marked_unresolved(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    items = raise_relink_items(str(hub), diffs, store)
    assert [(i.type, i.status) for i in items] == [("relink", "pending")]
    assert items[0].item_id == difference_to_item(diffs[0]).item_id
    assert items[0].created and items[0].updated
    card = _card(hub)
    assert is_unresolved(card) and card["path"] == f"{LN}/a.md"
    pending = store.pending()
    assert [e["finding"]["kind"] for e in pending] == ["relink"]
    assert pending[0]["finding"]["fingerprint"] == items[0].item_id


def test_double_raise_does_not_duplicate_findings(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    first = raise_relink_items(str(hub), diffs, store)
    second = raise_relink_items(str(hub), reconcile(str(hub)), store)
    assert [i.item_id for i in first] == [i.item_id for i in second]
    assert len(_entries(store)) == 1
    assert second[0].created == first[0].created


def test_raise_leaves_other_scan_findings_alone(tmp_path, store):
    from tools.corpus_health.finding import Finding
    store.refresh([Finding("note_transcription_missing", "academic_notes", "x.pdf", "x", "e",
                           fingerprint="abc")])
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    assert {e["status"] for e in _entries(store)} == {"pending_review"}


def test_orphan_raised_as_report_only_item_card_not_marked(tmp_path, store):
    hub, diffs = _orphan(tmp_path)
    items = raise_relink_items(str(hub), diffs, store)
    assert [i.type for i in items] == ["orphan"]
    assert [e["finding"]["kind"] for e in store.pending()] == ["orphan_card"]
    assert not is_unresolved(_card(hub))
    assert resolve(str(hub), "f1", f"{PS}/a.md", store=store) is False
    assert reject(str(hub), "f1", store=store) is True
    assert raise_relink_items(str(hub), reconcile(str(hub)), store) == []


def test_raise_clears_stale_unresolved_mark_when_difference_gone(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    (hub / f"{LN}/a.md").write_bytes((hub / f"{PS}/a.md").read_bytes())  # file came back
    assert reconcile(str(hub)) == []
    assert raise_relink_items(str(hub), [], store) == []
    assert not is_unresolved(_card(hub))


def test_raise_defaults_to_running_reconcile_and_holds_the_lock(tmp_path, store, monkeypatch):
    hub, _ = _ambiguous(tmp_path)
    held = []

    @contextlib.contextmanager
    def fake(roots, action, **kw):
        held.append(action)
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)
    items = raise_relink_items(str(hub), store=store)
    assert [i.type for i in items] == ["relink"] and is_unresolved(_card(hub))
    assert held == ["reconcile relink raise"]
    held.clear()
    assert [i.item_id for i in raise_relink_items_unlocked(str(hub), store=store)] == [items[0].item_id]
    assert held == []


def test_raise_with_partial_list_unraises_the_rest_as_documented(tmp_path, store):
    hub, _ = _ambiguous(tmp_path)
    note = write_note(hub, f"{LN}/b.md", {"title": "b"}, "# Probit\n\nLatent index model. " * 9)
    cards = load_shard(str(hub), "econ") + [{"file_id": "f2", "path": f"{LN}/b.md", "course": "econ",
                                            "content_hash": compute_content_hash(str(note))}]
    save_shard(str(hub), "econ", cards)
    text = note.read_bytes()
    (hub / f"{PS}/b1.md").write_bytes(text)
    (hub / f"{PS}/b2.md").write_bytes(text)
    os.remove(note)
    full = reconcile(str(hub))
    assert sorted(d.file_id for d in full if d.kind == "ambiguous") == ["f1", "f2"]
    raise_relink_items(str(hub), full, store)
    assert is_unresolved(_card(hub, "f1")) and is_unresolved(_card(hub, "f2"))
    partial = [d for d in full if d.file_id == "f1"]
    raise_relink_items(str(hub), partial, store)  # documented: a partial list un-raises the rest
    assert is_unresolved(_card(hub, "f1")) and not is_unresolved(_card(hub, "f2"))
    assert [e["finding"]["scope"] for e in store.pending()] == ["file_id:f1"]
    raise_relink_items(str(hub), store=store)  # the default (full reconcile) restores it
    assert is_unresolved(_card(hub, "f2")) and len(store.pending()) == 2


# --- resolve / reject ---

def test_resolve_with_chosen_candidate_repairs_and_clears_unresolved(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    assert resolve(str(hub), "f1", f"{PS}/a_copy.md", store=store) is True
    card = _card(hub)
    assert card["path"] == f"{PS}/a_copy.md" and not is_unresolved(card)
    lines = [json.loads(l) for l in open(reconcile_apply.log_path(str(hub)), encoding="utf-8")]
    assert [l["status"] for l in lines] == ["pending", "done"]
    (entry,) = _entries(store)
    assert entry["decision"]["status"] == "accepted" and entry["status"] == "applied"
    assert store.pending() == []


def test_resolve_with_path_not_in_candidates_refused(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    assert resolve(str(hub), "f1", f"{LN}/elsewhere.md", store=store) is False
    assert resolve(str(hub), "nope", f"{PS}/a.md", store=store) is False
    card = _card(hub)
    assert card["path"] == f"{LN}/a.md" and is_unresolved(card)
    assert len(store.pending()) == 1


def test_stale_resolve_returns_false(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    os.remove(hub / f"{PS}/a_copy.md")  # tree changed since the item was raised
    assert resolve(str(hub), "f1", f"{PS}/a_copy.md", store=store) is False
    assert _card(hub)["path"] == f"{LN}/a.md"


def test_resolve_refused_when_target_claimed_leaves_state(tmp_path, store, monkeypatch):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)

    def refuse(*a, **k):
        raise ValueError("already the path of another card")

    monkeypatch.setattr(reconcile_apply, "apply_one_unlocked", refuse)
    assert resolve(str(hub), "f1", f"{PS}/a.md", store=store) is False
    assert is_unresolved(_card(hub)) and len(store.pending()) == 1


def test_reject_dismisses_and_is_not_reraised(tmp_path, store):
    hub, diffs = _ambiguous(tmp_path)
    raise_relink_items(str(hub), diffs, store)
    assert reject(str(hub), "f1", store=store) is True
    card = _card(hub)
    assert not is_unresolved(card) and card["path"] == f"{LN}/a.md"
    assert reject(str(hub), "f1", store=store) is True  # idempotent
    assert raise_relink_items(str(hub), reconcile(str(hub)), store) == []
    assert not is_unresolved(_card(hub))
    (entry,) = _entries(store)
    assert entry["status"] == "declined"
    assert reject(str(hub), "nope", store=store) is False


def test_reject_without_prior_raise_records_decline(tmp_path, store):
    hub, _ = _ambiguous(tmp_path)
    assert reject(str(hub), "f1", store=store) is True
    assert raise_relink_items(str(hub), reconcile(str(hub)), store) == []


# --- consumers skip unresolved cards (ruling R5) ---

def test_offering_links_skips_unresolved_card(tmp_path):
    from core.indexer.offering_links import run_for_course
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199], "link_state": "unresolved"}
    for card in (card_a, card_b):
        full = tmp_path / card["path"]
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("body\n")
    save_shard(str(tmp_path), "econometrics", [card_a, card_b])
    stats = run_for_course(str(tmp_path), "econometrics")
    assert stats["auto_matches"] == 0 and stats["review_matches"] == 0
    assert not any(c.get("related_offerings") for c in load_shard(str(tmp_path), "econometrics"))


def test_document_pairing_skips_unresolved_card(tmp_path):
    from core.indexer.document_pairing import run_for_course
    card_a = {"file_id": "fa", "path": "academic_notes/microecon/problem_sets/processed_outputs/Homework_4.md",
              "title": "Homework 4", "course": "microecon"}
    card_b = {"file_id": "fb", "path": "academic_notes/microecon/problem_sets/homework_4_solutions.md",
              "title": "Homework 4 Solutions", "course": "microecon", "link_state": "unresolved"}
    (tmp_path / "academic_notes" / "microecon").mkdir(parents=True)
    save_shard(str(tmp_path), "microecon", [card_a, card_b])
    stats = run_for_course(str(tmp_path), "microecon")
    assert stats["auto_matches"] == 0 and stats["review_matches"] == 0
