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
    before = _card(hub)["content_hash"]
    recs = apply_repairs(str(hub), _moved(hub))
    assert len(recs) == 1 and recs[0].status == "done"
    card = _card(hub)
    assert card["path"] == f"{PS}/a.md"
    assert card["content_hash"] == before
    assert content_hash_matches(str(hub / f"{PS}/a.md"), card["content_hash"])
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


def _pending(hub, new, **extra):
    rec = {"repair_id": "abc-1", "file_id": "f1", "old": f"{LN}/a.md", "new": new,
           "old_rag_md_path": None, "new_rag_md_path": None, "ts": "t", "status": "pending", **extra}
    Path(log_path(str(hub))).parent.mkdir(exist_ok=True)
    with open(log_path(str(hub)), "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec) + "\n")


def test_rerun_after_interrupted_repair_is_idempotent(tmp_path):
    # crash before the card write: pending line only, fresh Difference
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    new = diffs[0].candidates[0].path
    _pending(hub, new)
    recs = apply_repairs(str(hub), diffs)
    assert [r.repair_id for r in recs] == ["abc-1"]
    assert _card(hub)["path"] == new
    assert [e["status"] for e in _log(hub)] == ["pending", "done"]


def test_crash_after_card_write_is_recovered_and_undoable(tmp_path):
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    new = diffs[0].candidates[0].path
    _pending(hub, new)
    save_shard(str(hub), "econ", [{**_card(hub), "path": new}])  # card written, no done
    assert reconcile(str(hub)) == []
    assert apply_repairs(str(hub), reconcile(str(hub))) == []
    assert [e["status"] for e in _log(hub)] == ["pending", "done"]
    assert undo_repair(str(hub), "abc-1") is True
    assert _card(hub)["path"] == f"{LN}/a.md"


def test_undo_recovers_pending_itself(tmp_path):
    hub = _setup(tmp_path)
    new = _moved(hub)[0].candidates[0].path
    _pending(hub, new)
    save_shard(str(hub), "econ", [{**_card(hub), "path": new}])
    assert undo_repair(str(hub), "abc-1") is True


def test_resume_leaves_rag_alone_when_recorded_target_missing(tmp_path):
    hub = _setup(tmp_path, rag_md_path=f"{LN}/a.rag.md")
    diffs = _moved(hub)
    _pending(hub, diffs[0].candidates[0].path, old_rag_md_path=f"{LN}/a.rag.md",
             new_rag_md_path=f"{PS}/a.rag.md")
    apply_repairs(str(hub), diffs)
    assert _card(hub)["rag_md_path"] == f"{LN}/a.rag.md"


def test_torn_last_log_line_does_not_swallow_next_record(tmp_path):
    hub = _setup(tmp_path)
    Path(log_path(str(hub))).parent.mkdir(exist_ok=True)
    Path(log_path(str(hub))).write_text('{"repair_id": "x", "stat', encoding="utf-8")
    rec = apply_repairs(str(hub), _moved(hub))[0]
    assert [e["status"] for e in _log_ok(hub)] == ["pending", "done"]
    assert undo_repair(str(hub), rec.repair_id) is True


def _log_ok(hub):
    out = []
    for l in Path(log_path(str(hub))).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def test_ambiguous_applied_only_with_explicit_candidate(tmp_path):
    hub = _setup(tmp_path)
    _move(hub, f"{LN}/a.md", f"{PS}/a.md")
    c1 = Candidate(f"{PS}/a.md", "byte_hash", 1.0)
    d = Difference("ambiguous", "f1", f"{LN}/a.md", [c1, Candidate(f"{PS}/b.md", "similarity", .6)], "")
    assert apply_one(str(hub), d) is None
    with pytest.raises(ValueError):
        apply_one(str(hub), d, new_path=f"{PS}/zzz.md")
    assert apply_repairs(str(hub), [d]) == []
    assert _card(hub)["path"] == f"{LN}/a.md"
    assert apply_one(str(hub), d, new_path=c1.path).status == "done"
    assert _card(hub)["path"] == f"{PS}/a.md"


def test_apply_one_unlocked_takes_no_lock(tmp_path):
    hub = _setup(tmp_path)
    assert reconcile_apply.apply_one_unlocked(str(hub), _moved(hub)[0]) is not None
    assert locks == []


def test_another_card_now_holding_new_skips_and_raises_for_explicit(tmp_path):
    hub = _setup(tmp_path)
    diffs = _moved(hub)
    new = diffs[0].candidates[0].path
    other = {"file_id": "f2", "path": new.upper(), "course": "econ", "content_hash": "h"}
    save_shard(str(hub), "econ", [_card(hub), other])
    assert apply_repairs(str(hub), diffs) == []
    assert _log(hub) == []
    with pytest.raises(ValueError):
        apply_one(str(hub), diffs[0], new_path=new)
    assert _card(hub)["path"] == f"{LN}/a.md"


def test_two_differences_same_new_second_skipped(tmp_path):
    hub = _setup(tmp_path)
    d1 = _moved(hub)[0]
    c = d1.candidates[0]
    other = {"file_id": "f2", "path": f"{LN}/gone.md", "course": "econ", "content_hash": "h"}
    save_shard(str(hub), "econ", [_card(hub), other])
    d2 = Difference("moved", "f2", f"{LN}/gone.md", [Candidate(c.path, "byte_hash", 1.0)], "")
    recs = apply_repairs(str(hub), [d1, d2])
    assert [r.file_id for r in recs] == ["f1"]
    assert _card(hub, "f2")["path"] == f"{LN}/gone.md"


def test_moved_with_empty_candidates_is_skipped_not_fatal(tmp_path):
    hub = _setup(tmp_path)
    bad = Difference("moved", "zz", f"{LN}/q.md", [], "")
    recs = apply_repairs(str(hub), [bad] + _moved(hub))
    assert len(recs) == 1
    assert apply_one(str(hub), bad) is None


def test_undo_false_after_second_repair_of_same_card(tmp_path):
    hub = _setup(tmp_path)
    first = apply_repairs(str(hub), _moved(hub))[0]
    _move(hub, f"{PS}/a.md", f"{LN}/c.md")
    second = apply_repairs(str(hub), reconcile(str(hub)))[0]
    assert undo_repair(str(hub), first.repair_id) is False
    assert undo_repair(str(hub), second.repair_id) is True


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
