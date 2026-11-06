"""Pipeline preflight (hub-path-resilience P4, Task 1)."""
from __future__ import annotations

import contextlib
import os
from pathlib import Path

import pytest

from core.indexer import preflight, reconcile_apply
from core.indexer.index_card import compute_content_hash, find_card_by_file_id, save_shard
from core.indexer.preflight import Needs, UnresolvedLinksError, check, require_resolved, tree_fingerprint
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools.corpus_health.state import StateStore

LN = "academic_notes/econ/lecture_notes"
BODY = "# Regression\n\nOrdinary least squares minimizes the sum of squared residuals.\n" * 3


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called in preflight tests")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)
    monkeypatch.setattr(preflight, "corpus_write_lock", fake)


@pytest.fixture
def store(tmp_path):
    return StateStore(tmp_path / "state")


def _card(hub, rel, fid, course="econ"):
    return {"file_id": fid, "path": rel, "course": course,
            "content_hash": compute_content_hash(str(hub / rel))}


def _rename_and_edit(hub, rel_old, rel_new):
    os.replace(hub / rel_old, hub / rel_new)
    with open(hub / rel_new, "a", encoding="utf-8", newline="\n") as f:
        f.write("\nAn added paragraph on heteroskedasticity.\n")


def _ambiguous_hub(tmp_path):
    """econ has one rename-and-edit (ambiguous relink); stats has a clean card."""
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/lecture_03_regression.md", {"title": "a"}, BODY)
    write_note(hub, "academic_notes/stats/lecture_notes/s.md", {"title": "s"}, "# Stats\n\nVariance.\n")
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/lecture_03_regression.md", "f1")])
    save_shard(str(hub), "stats", [_card(hub, "academic_notes/stats/lecture_notes/s.md", "s1", "stats")])
    _rename_and_edit(hub, f"{LN}/lecture_03_regression.md", f"{LN}/lecture_03_regression_v2.md")
    return hub


def _count_reconciles(monkeypatch):
    calls = []
    real = preflight.reconcile

    def counting(*a, **k):
        calls.append(1)
        return real(*a, **k)

    monkeypatch.setattr(preflight, "reconcile", counting)
    return calls


def test_unchanged_tree_still_refuses_on_open_item(tmp_path, store, monkeypatch):
    hub = _ambiguous_hub(tmp_path)
    with pytest.raises(UnresolvedLinksError):
        require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)
    calls = _count_reconciles(monkeypatch)
    with pytest.raises(UnresolvedLinksError) as exc:
        require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)
    assert calls == []
    assert [i.type for i in exc.value.items] == ["relink"]
    assert "python -m tools.hub_review page --hub-root" in str(exc.value)


def test_item_in_other_course_does_not_block(tmp_path, store):
    hub = _ambiguous_hub(tmp_path)
    require_resolved(str(hub), Needs(courses=frozenset({"stats"})), store)
    assert [i.type for i in check(str(hub), Needs(courses=None), store)] == ["relink"]
    assert len(check(str(hub), Needs(file_ids=frozenset({"f1"}), courses=frozenset()), store)) == 1


def test_preflight_does_not_touch_cards(tmp_path, store):
    hub = _ambiguous_hub(tmp_path)
    check(str(hub), Needs(), store)
    assert not find_card_by_file_id(str(hub), "f1")[1].get("link_state")


def test_waiting_exact_move_blocks_and_names_repair(tmp_path, store, monkeypatch):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1")])
    os.replace(hub / f"{LN}/a.md", hub / f"{LN}/renamed.md")
    with pytest.raises(UnresolvedLinksError) as exc:
        require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)
    assert "hub_review repair" in str(exc.value)
    assert [i.type for i in exc.value.items] == ["moved"]
    calls = _count_reconciles(monkeypatch)  # fast path remembers the waiting move
    with pytest.raises(UnresolvedLinksError):
        require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)
    assert calls == []
    # once the card is repaired the stale remembered move stops blocking
    reconcile_apply.apply_repairs(str(hub), reconcile_apply.reconcile(str(hub)))
    require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)


def test_orphan_warns_but_does_not_block(tmp_path, store, capsys):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [_card(hub, f"{LN}/a.md", "f1")])
    os.remove(hub / f"{LN}/a.md")
    require_resolved(str(hub), Needs(courses=frozenset({"econ"})), store)
    assert "orphan" in capsys.readouterr().err.lower()


def test_ignore_flag_returns_with_warning(tmp_path, store, capsys):
    hub = _ambiguous_hub(tmp_path)
    require_resolved(str(hub), Needs(), store, ignore=True)
    err = capsys.readouterr().err
    assert "unresolved" in err.lower() and len(err.strip().splitlines()) == 1


def test_fingerprint_changes_on_rename_and_edit_and_ignores_obsidian_dir(tmp_path):
    hub = make_hub(tmp_path)
    write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    base = tree_fingerprint(str(hub))
    assert tree_fingerprint(str(hub)) == base
    for skipped in (".obsidian", ".index", ".git"):
        d = hub / "academic_notes" / "econ" / skipped
        d.mkdir(parents=True, exist_ok=True)
        (d / "x.json").write_text("{}")
    assert tree_fingerprint(str(hub)) == base
    (hub / "academic_notes/econ/.obsidian/x.json").write_text("changed")
    assert tree_fingerprint(str(hub)) == base
    _rename_and_edit(hub, f"{LN}/a.md", f"{LN}/b.md")
    assert tree_fingerprint(str(hub)) != base
