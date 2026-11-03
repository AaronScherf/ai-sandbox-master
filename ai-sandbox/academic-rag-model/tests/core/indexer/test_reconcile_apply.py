"""Logged reversible reconcile repairs (hub-path-resilience P3 Task 4). tmp_path hubs, no model."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

import pytest

from core.indexer import reconcile_apply
from core.indexer.index_card import (
    compute_content_hash, content_hash_matches, find_card_by_file_id, save_shard,
)
from core.indexer.reconcile import Candidate, Difference, reconcile
from core.indexer.reconcile_apply import apply_one, apply_repairs, log_path, undo_repair
from tests.core.indexer.hub_fixture import make_hub, write_note

LN = "academic_notes/econ/lecture_notes"
PS = "academic_notes/econ/problem_sets"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3
locks: list[str] = []


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    locks.clear()

    @contextlib.contextmanager
    def fake(roots, action, **kw):
        locks.append(action)
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


def _setup(tmp_path, **extra):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    card = {"file_id": "f1", "path": f"{LN}/a.md", "course": "econ",
            "content_hash": compute_content_hash(str(note)), **extra}
    save_shard(str(hub), "econ", [card])
    return hub


def _move(hub, old, new):
    (hub / new).parent.mkdir(parents=True, exist_ok=True)
    os.replace(hub / old, hub / new)


def _card(hub, fid="f1"):
    return find_card_by_file_id(str(hub), fid)[1]


def _log(hub):
    p = Path(log_path(str(hub)))
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def _moved(hub, new=f"{PS}/a.md"):
    _move(hub, f"{LN}/a.md", new)
    diffs = reconcile(str(hub))
    assert [d.kind for d in diffs] == ["moved"]
    return diffs


def test_move_repairs_card_path_and_hash_still_valid(tmp_path):
    hub = _setup(tmp_path)
    recs = apply_repairs(str(hub), _moved(hub))
    assert len(recs) == 1 and recs[0].status == "done"
    card = _card(hub)
    assert card["path"] == f"{PS}/a.md"
    assert content_hash_matches(str(hub / card["path"]), card["content_hash"])
    assert locks == ["reconcile repair"]
    assert reconcile(str(hub)) == []


def test_repair_logged_and_undo_restores_card(tmp_path):
    hub = _setup(tmp_path)
    rec = apply_repairs(str(hub), _moved(hub))[0]
    assert [e["status"] for e in _log(hub)] == ["pending", "done"]
    assert {e["repair_id"] for e in _log(hub)} == {rec.repair_id}
    assert undo_repair(str(hub), rec.repair_id) is True
    assert _card(hub)["path"] == f"{LN}/a.md"
    assert [e["status"] for e in _log(hub)] == ["pending", "done", "undone"]
    assert undo_repair(str(hub), rec.repair_id) is False  # already undone
    assert undo_repair(str(hub), "nope") is False


def test_rerun_after_interrupted_repair_is_idempotent(tmp_path):
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    new = diffs[0].candidates[0].path
    pending = {"repair_id": "abc-1", "file_id": "f1", "old": f"{LN}/a.md", "new": new,
               "old_rag_md_path": None, "new_rag_md_path": None, "ts": "t", "status": "pending"}
    Path(log_path(str(hub))).parent.mkdir(exist_ok=True)
    Path(log_path(str(hub))).write_text(json.dumps(pending) + "\n", encoding="utf-8")
    recs = apply_repairs(str(hub), diffs)
    assert [r.repair_id for r in recs] == ["abc-1"]
    assert _card(hub)["path"] == new
    assert [e["status"] for e in _log(hub)] == ["pending", "done"]
    # card already written but done missing: completes with just a done line
    Path(log_path(str(hub))).write_text(json.dumps(pending) + "\n", encoding="utf-8")
    assert apply_one(str(hub), diffs[0]).repair_id == "abc-1"
    assert [e["status"] for e in _log(hub)] == ["pending", "done"]


def test_ambiguous_and_orphan_are_never_applied(tmp_path):
    hub = _setup(tmp_path)
    cands = [Candidate(f"{PS}/a.md", "byte_hash", 1.0)]
    (hub / PS / "a.md").write_text("x", encoding="utf-8")
    for kind in ("ambiguous", "orphan"):
        d = Difference(kind, "f1", f"{LN}/a.md", cands, "")
        assert apply_repairs(str(hub), [d]) == []
        assert apply_one(str(hub), d) is None
    assert _card(hub)["path"] == f"{LN}/a.md"
    assert _log(hub) == []


def test_stale_difference_skipped(tmp_path):
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    save_shard(str(hub), "econ", [{**_card(hub), "path": "somewhere/else.md"}])
    assert apply_repairs(str(hub), diffs) == []
    assert _log(hub) == []
    save_shard(str(hub), "econ", [{**_card(hub), "path": diffs[0].old_path}])
    os.remove(hub / diffs[0].candidates[0].path)  # target gone
    assert apply_one(str(hub), diffs[0]) is None and _log(hub) == []


def test_new_path_must_be_a_candidate(tmp_path):
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    with pytest.raises(ValueError):
        apply_one(str(hub), diffs[0], new_path="academic_notes/econ/other.md")
    assert apply_one(str(hub), diffs[0], new_path=diffs[0].candidates[0].path) is not None


def test_undo_refused_after_card_changed_again(tmp_path):
    hub = _setup(tmp_path)
    rec = apply_repairs(str(hub), _moved(hub))[0]
    save_shard(str(hub), "econ", [{**_card(hub), "path": "elsewhere.md"}])
    assert undo_repair(str(hub), rec.repair_id) is False
    assert _card(hub)["path"] == "elsewhere.md"


def test_rag_md_path_rewritten_when_sibling_exists_at_new_location(tmp_path):
    hub = _setup(tmp_path, rag_md_path=f"{LN}/a.rag.md")
    (hub / LN / "a.rag.md").write_text("r", encoding="utf-8")
    _move(hub, f"{LN}/a.rag.md", f"{PS}/a.rag.md")
    rec = apply_repairs(str(hub), _moved(hub))[0]
    assert _card(hub)["rag_md_path"] == f"{PS}/a.rag.md"
    assert undo_repair(str(hub), rec.repair_id)
    assert _card(hub)["rag_md_path"] == f"{LN}/a.rag.md"


def test_rag_md_path_left_alone_when_missing_or_elsewhere(tmp_path):
    hub = _setup(tmp_path / "one", rag_md_path=f"{LN}/a.rag.md")  # sidecar absent at new location
    apply_repairs(str(hub), _moved(hub))
    assert _card(hub)["rag_md_path"] == f"{LN}/a.rag.md"
    hub2 = _setup(tmp_path / "two", rag_md_path="academic_resources/econ/a.rag.md")
    apply_repairs(str(hub2), _moved(hub2))
    assert _card(hub2)["rag_md_path"] == "academic_resources/econ/a.rag.md"


def test_two_repairs_in_one_call_both_logged(tmp_path):
    hub = make_hub(tmp_path)
    cards = []
    for name, body in (("a", BODY), ("b", BODY + "different words entirely here\n")):
        p = write_note(hub, f"{LN}/{name}.md", {"title": name}, body)
        cards.append({"file_id": name, "path": f"{LN}/{name}.md", "course": "econ",
                      "content_hash": compute_content_hash(str(p))})
    save_shard(str(hub), "econ", cards)
    _move(hub, f"{LN}/a.md", f"{PS}/a.md")
    _move(hub, f"{LN}/b.md", f"{PS}/b.md")
    recs = apply_repairs(str(hub), reconcile(str(hub)))
    assert len(recs) == 2 and len({r.repair_id for r in recs}) == 2
    assert [e["status"] for e in _log(hub)] == ["pending", "done", "pending", "done"]
    assert locks == ["reconcile repair"]
