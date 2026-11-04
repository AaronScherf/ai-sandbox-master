"""tools.hub_review export/apply/page (hub-path-resilience P3 Task 6). tmp_path hubs, real producers,
no API, no git (the corpus write lock is faked as in the reconcile tests)."""
from __future__ import annotations

import contextlib
import json
import os
import re

import pytest

from core.indexer import document_pairing, offering_links, reconcile_apply
from core.indexer.index_card import compute_content_hash, find_card_by_file_id, load_shard, save_shard
from tests.core.indexer.hub_fixture import make_hub, write_note
from tools import hub_review
from tools.corpus_health.state import SELF_REFRESHED_KINDS, StateStore

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


def _touch(hub, rel):
    p = hub / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("body\n", encoding="utf-8")


def build_hub(tmp_path, relink=True, offering=True, pairing=True):
    """One hub holding an ambiguous relink plus real offering-link and document-pairing review entries."""
    hub = make_hub(tmp_path)
    if relink:
        note = write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
        save_shard(str(hub), "econ", [{"file_id": "f1", "path": f"{LN}/a.md", "course": "econ",
                                       "content_hash": compute_content_hash(str(note))}])
        text = note.read_bytes()
        (hub / f"{PS}/a.md").write_bytes(text)
        (hub / f"{PS}/a_copy.md").write_bytes(text)
        os.remove(note)
    if offering:
        subset = hub / "academic_resources" / "econometrics" / "class_2024"
        subset.mkdir(parents=True)
        (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
        cards = [{"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
                  "title": "A", "embedding": [1.0, 0.0]},
                 {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
                  "title": "B", "embedding": [0.85, 0.5266403851195171]}]
        for c in cards:
            _touch(hub, c["path"])
        save_shard(str(hub), "econometrics", cards)
        assert offering_links.run_for_course(str(hub), "econometrics")["review_matches"] == 1
    if pairing:
        base = "academic_notes/microecon/problem_sets"
        cards = [{"file_id": "pa", "path": f"{base}/processed_outputs/Homework_4.md", "course": "microecon"},
                 {"file_id": "pb", "path": f"{base}/processed_outputs/HW_4.md", "course": "microecon"},
                 {"file_id": "pc", "path": f"{base}/homework_4_solutions.md", "course": "microecon"}]
        for c in cards:
            _touch(hub, c["path"])
        save_shard(str(hub), "microecon", cards)
        document_pairing.run_for_course(str(hub), "microecon")
        assert document_pairing.load_review(str(hub))
    return hub


def _by_type(items, t):
    return [i for i in items if i["type"] == t]


def _decision(item, action, chosen=None):
    return {"item_id": item["item_id"], "action": action, "chosen": chosen}


def _snapshot(hub, store):
    shards = {}
    for root, _, files in os.walk(hub / ".index"):
        for f in files:
            p = os.path.join(root, f)
            shards[p] = open(p, "rb").read()
    return shards, store.state_path.read_bytes() if store.state_path.exists() else None


def _card_path(hub, fid):
    return find_card_by_file_id(str(hub), fid)[1]["path"]


def test_export_lists_items_from_all_three_ledgers(tmp_path, store):
    hub = build_hub(tmp_path)
    out = hub_review.export(str(hub), store=store)
    types = {i["type"] for i in out["items"]}
    assert types == {"relink", "offering_link", "document_pairing"}
    assert len(_by_type(out["items"], "document_pairing")) == 2
    relink = _by_type(out["items"], "relink")[0]
    assert relink["subject_paths"] == [f"{LN}/a.md"]
    assert {c["path"] for c in relink["candidates"]} == {f"{PS}/a.md", f"{PS}/a_copy.md"}
    offer = _by_type(out["items"], "offering_link")[0]
    assert offer["candidates"][0]["path"] == "academic_notes/econometrics/class_2024/b.md"
    assert out["hub_root"] == str(hub) and out["generated"]


def test_export_is_deterministic_and_sorted(tmp_path, store):
    hub = build_hub(tmp_path)
    a = hub_review.export(str(hub), store=store)["items"]
    b = hub_review.export(str(hub), store=store)["items"]
    assert a == b
    assert a == sorted(a, key=lambda i: (i["type"], i["item_id"]))


def test_apply_dispatches_relink_to_reconcile_resolve(tmp_path, store):
    hub = build_hub(tmp_path)
    relink = _by_type(hub_review.export(str(hub), store=store)["items"], "relink")[0]
    res = hub_review.apply_decisions(str(hub), [_decision(relink, "accept", f"{PS}/a_copy.md")], store=store)
    assert res[0]["outcome"] == "applied"
    assert _card_path(hub, "f1") == f"{PS}/a_copy.md"


def test_relink_accept_without_valid_chosen_is_error_for_that_item_only(tmp_path, store):
    hub = build_hub(tmp_path)
    items = hub_review.export(str(hub), store=store)["items"]
    relink = _by_type(items, "relink")[0]
    offer = _by_type(items, "offering_link")[0]
    res = hub_review.apply_decisions(str(hub), [
        _decision(relink, "accept", None),
        _decision(relink, "accept", "somewhere/else.md"),
        _decision(offer, "accept"),
    ], store=store)
    assert [r["outcome"] for r in res[:2]] == ["error", "error"]
    assert res[2]["outcome"] == "applied"
    assert _card_path(hub, "f1") == f"{LN}/a.md"


def test_apply_dispatches_offering_link_to_offering_links_resolve(tmp_path, store):
    hub = build_hub(tmp_path)
    offer = _by_type(hub_review.export(str(hub), store=store)["items"], "offering_link")[0]
    res = hub_review.apply_decisions(str(hub), [_decision(offer, "accept")], store=store)
    assert res[0]["outcome"] == "applied"
    assert offering_links.load_review(str(hub)) == []
    card = find_card_by_file_id(str(hub), "fa")[1]
    assert [r["file_id"] for r in card["related_offerings"]] == ["fb"]


def test_decline_dispatch_for_all_types(tmp_path, store):
    hub = build_hub(tmp_path)
    items = hub_review.export(str(hub), store=store)["items"]
    res = hub_review.apply_decisions(str(hub), [_decision(i, "decline") for i in items], store=store)
    assert {r["outcome"] for r in res} == {"applied"}
    assert offering_links.load_review(str(hub)) == [] and document_pairing.load_review(str(hub)) == []
    assert _card_path(hub, "f1") == f"{LN}/a.md"
    assert hub_review.export(str(hub), store=store)["items"] == []


def test_defer_records_in_ledger_for_relink_and_noops_for_pairs(tmp_path, store):
    hub = build_hub(tmp_path)
    items = hub_review.export(str(hub), store=store)["items"]
    relink = _by_type(items, "relink")[0]
    offer = _by_type(items, "offering_link")[0]
    res = hub_review.apply_decisions(str(hub), [_decision(relink, "defer"), _decision(offer, "defer")], store=store)
    assert [r["outcome"] for r in res] == ["deferred", "noop"]
    statuses = [e["status"] for e in store.entries(kinds=SELF_REFRESHED_KINDS)]
    assert statuses == ["deferred"]
    assert len(offering_links.load_review(str(hub))) == 1


def test_stale_item_id_reported_not_raised(tmp_path, store):
    hub = build_hub(tmp_path)
    offer = _by_type(hub_review.export(str(hub), store=store)["items"], "offering_link")[0]
    res = hub_review.apply_decisions(str(hub), [
        {"item_id": "deadbeef", "action": "accept", "chosen": None},
        {"item_id": "x", "action": "bogus"},
        _decision(offer, "decline"),
    ], store=store)
    assert [r["outcome"] for r in res] == ["stale", "error", "applied"]


def test_dry_run_writes_nothing(tmp_path, store):
    hub = build_hub(tmp_path)
    items = hub_review.export(str(hub), store=store)["items"]
    before = _snapshot(hub, store)
    review_before = offering_links.load_review(str(hub))
    decisions = [_decision(i, "accept", f"{PS}/a_copy.md" if i["type"] == "relink" else None) for i in items]
    res = hub_review.apply_decisions(str(hub), decisions, dry_run=True, store=store)
    assert {r["outcome"] for r in res} == {"would_apply"}
    assert _snapshot(hub, store) == before
    assert offering_links.load_review(str(hub)) == review_before
    assert _card_path(hub, "f1") == f"{LN}/a.md"


def test_main_apply_unreadable_file_exits_nonzero(tmp_path, capsys):
    bad = tmp_path / "d.json"
    bad.write_text("{not json")
    assert hub_review.main(["apply", str(bad), "--hub-root", str(tmp_path)]) == 2
    bad.write_text('{"a": 1}')
    assert hub_review.main(["apply", str(bad), "--hub-root", str(tmp_path)]) == 2


# --- page ---

def _embedded(html):
    m = re.search(r'<script type="application/json" id="review-items">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_page_embeds_items_and_survives_script_breakers():
    nasty = 'x</script><script>alert(1)</script><!-- "q" \'s\'  '
    payload = {"generated": "t", "hub_root": "h", "items": [
        {"item_id": "i1", "type": "relink", "subject_ids": ["f"], "subject_paths": [nasty],
         "candidates": [{"path": nasty, "basis": "b", "score": 1.0}], "status": "pending"}]}
    html = hub_review.render_page(payload)
    assert _embedded(html) == {k: v for k, v in payload.items() if k != "hub_root"}
    assert html.count("</script>") == 2 and "<!--" not in html.split('id="review-items">')[1].split("</script>")[0]
    assert "__REVIEW_ITEMS__" not in html


def test_page_template_has_dark_mode_tokens_and_decisions_collection():
    html = hub_review.render_page({"items": []})
    assert "<title>Hub Review Queue</title>" in html
    assert ":root:not([data-theme=\"light\"])" in html and ":root[data-theme=\"dark\"]" in html
    assert "prefers-color-scheme: dark" in html and "--bg:" in html
    assert 'collection("decisions")' in html and 'claude.use("db")' in html
    assert "<script src=" not in html


# --- fix round 1 ---

def test_deferred_relink_stays_listed_and_can_be_decided_later(tmp_path, store):
    hub = build_hub(tmp_path, offering=False, pairing=False)
    relink = _by_type(hub_review.export(str(hub), store=store)["items"], "relink")[0]
    for _ in range(2):  # defer twice is fine
        res = hub_review.apply_decisions(str(hub), [_decision(relink, "defer")], store=store)
        assert res[0]["outcome"] == "deferred"
    for raise_items in (True, False):
        (item,) = hub_review.export(str(hub), store=store, raise_items=raise_items)["items"]
        assert item["status"] == "deferred" and item["item_id"] == relink["item_id"]
    res = hub_review.apply_decisions(str(hub), [_decision(relink, "accept", f"{PS}/a.md")], store=store)
    assert res[0]["outcome"] == "applied" and _card_path(hub, "f1") == f"{PS}/a.md"


def test_decline_after_defer_works(tmp_path, store):
    hub = build_hub(tmp_path, offering=False, pairing=False)
    relink = _by_type(hub_review.export(str(hub), store=store)["items"], "relink")[0]
    hub_review.apply_decisions(str(hub), [_decision(relink, "defer")], store=store)
    res = hub_review.apply_decisions(str(hub), [_decision(relink, "decline")], store=store)
    assert res[0]["outcome"] == "applied"
    assert hub_review.export(str(hub), store=store)["items"] == []


def test_no_raise_export_is_a_pure_read(tmp_path, store):
    hub = build_hub(tmp_path)
    before = _snapshot(hub, store)
    items = hub_review.export(str(hub), store=store, raise_items=False)["items"]
    assert {i["type"] for i in items} == {"relink", "offering_link", "document_pairing"}
    assert _snapshot(hub, store) == before
    assert not store.state_path.exists()
    hub_review.export(str(hub), store=store)  # plain export raises into the ledger
    assert store.state_path.exists()
    assert find_card_by_file_id(str(hub), "f1")[1].get("link_state") == "unresolved"


def test_export_help_documents_writes(capsys):
    assert "WRITES" in (hub_review.__doc__ or "")
    with pytest.raises(SystemExit):
        hub_review.main(["export", "--help"])
    out = capsys.readouterr().out
    assert "WRITES" in out and "--no-raise" in out


def test_hub_root_is_required():
    with pytest.raises(SystemExit):
        hub_review.main(["export"])


def test_orphan_accept_refused_decline_rejects(tmp_path, store):
    hub = make_hub(tmp_path)
    note = write_note(hub, f"{LN}/a.md", {"title": "a"}, BODY)
    save_shard(str(hub), "econ", [{"file_id": "f1", "path": f"{LN}/a.md", "course": "econ",
                                   "content_hash": compute_content_hash(str(note))}])
    os.remove(note)
    (orphan,) = hub_review.export(str(hub), store=store)["items"]
    assert orphan["type"] == "orphan"
    res = hub_review.apply_decisions(str(hub), [_decision(orphan, "accept", f"{PS}/a.md")], store=store)
    assert res[0]["outcome"] == "error"
    res = hub_review.apply_decisions(str(hub), [_decision(orphan, "decline")], store=store)
    assert res[0]["outcome"] == "applied"
    assert hub_review.export(str(hub), store=store)["items"] == []


def test_duplicate_decisions_first_non_error_wins(tmp_path, store):
    hub = build_hub(tmp_path)
    offer = _by_type(hub_review.export(str(hub), store=store)["items"], "offering_link")[0]
    res = hub_review.apply_decisions(str(hub), [_decision(offer, "decline"), _decision(offer, "accept")], store=store)
    assert [r["outcome"] for r in res] == ["applied", "stale"]


def test_page_payload_has_no_hub_root():
    html = hub_review.render_page({"hub_root": "C:/secret/hub", "items": []})
    assert "secret" not in html and "hub_root" not in html
