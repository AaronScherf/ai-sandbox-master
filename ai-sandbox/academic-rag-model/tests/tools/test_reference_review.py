"""Fixture-only tests for the reference-review ledger foundation."""
import json

import pytest

from core.indexer.review_envelope import _digest
from tools import reference_review as ledger
from tools.reference_checker import check_note


def test_stable_per_note_doi_id_and_cross_note_dismissal_key():
    expected = _digest("reference_check", "research/note.md", "10.1234/example")
    assert ledger.item_id("research/note.md", "10.1234/EXAMPLE") == expected
    assert ledger.item_id("research/note.md", "10.1234/example") == expected
    assert ledger.item_id("research/other.md", "10.1234/example") != expected
    assert ledger.dismissal_key("10.1234/EXAMPLE", "García (2020).") == (
        "10.1234/example", "garcia 2020")


def test_item_projection_round_trip_and_metadata_boundary(tmp_path):
    item = ledger.make_item("research/note.md", "10.1234/example", [
        {"line": 7, "cited_text": "García (2020)", "note_body": "private note body"},
        {"line": 19, "cited_text": "García (2020)"},
    ], tier="PLAUSIBLE", reason="no title", evidence="", record={
        "title": "Example", "authors": ["García"], "year": 2020, "venue": "Journal",
        "abstract": "private abstract", "raw_response": {"unused": True},
    })
    ledger.save_review([item], tmp_path)
    assert ledger.load_review(tmp_path) == [item]
    saved = (tmp_path / "review.json").read_text(encoding="utf-8")
    assert "private" not in saved
    assert item.candidates[0]["mentions"][0]["normalized_citation"] == "garcia 2020"
    assert len(item.candidates[0]["mentions"]) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["review.json"]


def test_storage_is_atomic_and_refuses_malformed_existing_ledger(tmp_path, monkeypatch):
    ledger.save_dismissals([{"doi": "10.1/old"}], tmp_path)
    original = (tmp_path / "dismissals.json").read_bytes()

    def fail_replace(source, destination):
        raise OSError("simulated interruption")

    monkeypatch.setattr(ledger.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        ledger.save_dismissals([{"doi": "10.1/new"}], tmp_path)
    assert (tmp_path / "dismissals.json").read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dismissals.json"]

    (tmp_path / "defects.json").write_text(json.dumps({"unexpected": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON list"):
        ledger.load_defects(tmp_path)


def _row(doi, tier, citation="Smith (2020)", line=2):
    return {"identifier": doi, "citation": citation, "line": line, "tier": tier,
            "reason": tier.lower(), "evidence": "", "registry_answer": {"record": {
                "title": "Sample paper", "authors": ["Smith"], "year": 2020,
                "venue": "Journal", "abstract": "never store this"}}}


def test_selection_groups_doi_mentions_uses_worst_tier_and_reports_defects():
    rows = [
        _row("10.1234/a", "CONFIRMED"),
        _row("10.1234/b", "CONFIRMED"), _row("10.1234/B", "REVIEW", "Smith and Jones (2020)", 5),
        _row("10.1234/c", "PLAUSIBLE"), _row("10.1234/d", "UNCHECKED"),
        _row("10.1234/e", "WRONG_WORK"), _row("10.1234/f", "NOT_FOUND"),
        _row("10.1234/g", "REVIEW"),
        {**_row("https://example.org", "UNCHECKED"), "identifier": "https://example.org"},
    ]
    items, defects = ledger._selected("research/note.md", rows, set())
    assert {item.subject_ids[1] for item in items} == {"10.1234/b", "10.1234/c", "10.1234/d", "10.1234/g"}
    grouped = next(item for item in items if item.subject_ids[1] == "10.1234/b")
    assert grouped.candidates[0]["tier"] == "REVIEW"
    assert [m["line"] for m in grouped.candidates[0]["mentions"]] == [2, 5]
    assert [d["doi"] for d in defects] == ["10.1234/e", "10.1234/f"]
    unchecked = next(item for item in items if item.subject_ids[1] == "10.1234/d")
    assert unchecked.candidates[0]["reason"] == "checker could not judge"
    assert "never store this" not in json.dumps([item.to_dict() for item in items] + defects)


def test_raise_is_idempotent_updates_mentions_and_clears_stale_checker_findings(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("first", encoding="utf-8")
    rows = [_row("10.1234/a", "PLAUSIBLE")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: list(rows))
    store = tmp_path / "store"
    first = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    second = ledger.raise_items([note, note], object(), store=store, repo_root=tmp_path)
    assert first == second
    assert len(ledger.load_review(store)) == 1
    assert first[0].created == second[0].created == second[0].updated
    rows.append(_row("10.1234/a", "REVIEW", "Smith and Jones (2020)", 9))
    updated = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert len(updated) == 1
    assert len(updated[0].candidates[0]["mentions"]) == 2
    rows[:] = [_row("10.1234/a", "WRONG_WORK")]
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path) == []
    assert ledger.load_review(store) == []
    assert [(d["note"], d["doi"]) for d in ledger.load_defects(store)] == [("note.md", "10.1234/a")]
    rows[:] = [_row("10.1234/a", "CONFIRMED")]
    ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert ledger.load_defects(store) == []


def test_same_work_dismissal_carries_across_notes_only_for_same_citation(tmp_path, monkeypatch):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    rows = {"a": [_row("10.1234/a", "PLAUSIBLE")],
            "b": [_row("10.1234/a", "PLAUSIBLE")]}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows[text])
    store = tmp_path / "store"
    ledger.save_dismissals([{"doi": "10.1234/a", "normalized_citation": "smith 2020"}], store)
    assert ledger.raise_items([a, b], object(), store=store, repo_root=tmp_path) == []
    rows["b"] = [_row("10.1234/a", "PLAUSIBLE", "Smith and Jones (2020)")]
    assert [item.subject_ids[0] for item in ledger.raise_items([a, b], object(), store=store,
                                                                 repo_root=tmp_path)] == ["b.md"]


def test_wrong_work_defect_is_scoped_to_its_note(tmp_path, monkeypatch):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    rows = {"a": [_row("10.1234/a", "WRONG_WORK")],
            "b": [_row("10.1234/a", "PLAUSIBLE")]}  # identical citation, different note
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows[text])
    store = tmp_path / "store"
    items = ledger.raise_items([a, b], object(), store=store, repo_root=tmp_path)
    assert [item.subject_ids[0] for item in items] == ["b.md"]
    assert [defect["note"] for defect in ledger.load_defects(store)] == ["a.md"]


def test_checker_preserves_line_through_reference_linking():
    doi = "10.1234/sample"

    class Client:
        def get(self, url):
            if "/doiRA/" in url:
                return {"data": [{"RA": "Crossref"}]}
            return {"status": 200, "data": {"message": {
                "title": ["Sample paper"], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}, "container-title": ["Journal"]}}}

    note = f"# Notes\n| Smith (2020) | https://doi.org/{doi} |\n## References\n* [Smith (2020). Sample paper](https://doi.org/{doi})\n"
    checked = check_note(note, Client())
    assert len(checked) == 1
    assert checked[0]["line"] == 2


def test_raise_with_recorded_registry_answer_keeps_exact_line(tmp_path):
    class Client:
        def get(self, url):
            if "/doiRA/" in url:
                return {"data": [{"RA": "Crossref"}]}
            return {"status": 200, "data": {"message": {
                "title": ["Sample paper"], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}, "container-title": ["Journal"]}}}

    note = tmp_path / "note.md"
    note.write_text("# References\n\n* [Smith (2020)](https://doi.org/10.1234/sample)\n", encoding="utf-8")
    items = ledger.raise_items([note], Client(), store=tmp_path / "store", repo_root=tmp_path)
    assert len(items) == 1
    assert items[0].candidates[0]["tier"] == "PLAUSIBLE"
    assert items[0].candidates[0]["mentions"] == [
        {"line": 3, "cited_text": "Smith (2020)", "normalized_citation": "smith 2020"}]


def test_resolve_dismisses_every_mention_and_carries_across_notes(tmp_path, monkeypatch):
    a, b, c = (tmp_path / name for name in ("a.md", "b.md", "c.md"))
    for note in (a, b, c):
        note.write_text(note.stem, encoding="utf-8")
    rows = {
        "a": [_row("10.1234/a", "PLAUSIBLE"),
              _row("10.1234/a", "REVIEW", "Smith and Jones (2020)", 4)],
        "b": [_row("10.1234/a", "PLAUSIBLE")],
        "c": [_row("10.1234/a", "PLAUSIBLE"),
              _row("10.1234/a", "REVIEW", "Changed citation (2020)", 7)],
    }
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows[text])
    store = tmp_path / "store"
    items = ledger.raise_items([a, b, c], object(), store=store, repo_root=tmp_path)
    source = next(item for item in items if item.subject_ids[0] == "a.md")
    assert ledger.resolve(source.item_id, store=store)
    assert ledger.resolve(source.item_id, store=store)
    assert len(ledger.load_dismissals(store)) == 2
    assert ledger.is_human_confirmed("10.1234/A", "Smith (2020)", store=store)
    assert not ledger.is_human_confirmed("10.1234/a", "Changed citation (2020)", store=store)
    assert {item.subject_ids[0]: item.status for item in ledger.load_review(store)} == {
        "a.md": "accepted", "b.md": "accepted", "c.md": "pending"}
    assert [item.subject_ids[0] for item in ledger.raise_items([a, b, c], object(), store=store,
                                                                 repo_root=tmp_path)] == ["c.md"]


def test_reject_wrong_work_is_note_local_idempotent_and_invalidated_by_changed_citation(tmp_path, monkeypatch):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    rows = {"a": [_row("10.1234/a", "REVIEW")], "b": [_row("10.1234/a", "REVIEW")]}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows[text])
    store = tmp_path / "store"
    items = ledger.raise_items([a, b], object(), store=store, repo_root=tmp_path)
    source = next(item for item in items if item.subject_ids[0] == "a.md")
    assert ledger.reject(source.item_id, "wrong_work", store=store)
    assert ledger.reject(source.item_id, "wrong_work", store=store)
    assert not ledger.reject(source.item_id, "not_citation", store=store)
    assert [(d["note"], d["source"]) for d in ledger.load_defects(store)] == [("a.md", "human")]
    assert not ledger.is_human_confirmed("10.1234/a", "Smith (2020)", store=store)
    assert {item.subject_ids[0]: item.status for item in ledger.load_review(store)} == {
        "a.md": "declined", "b.md": "pending"}
    assert [item.subject_ids[0] for item in ledger.raise_items([a, b], object(), store=store,
                                                                 repo_root=tmp_path)] == ["b.md"]
    rows["a"] = [_row("10.1234/a", "REVIEW", "Smith and Jones (2020)")]
    refreshed = ledger.raise_items([a], object(), store=store, repo_root=tmp_path)
    assert refreshed[0].status == "pending"
    assert ledger.load_defects(store) == []


def test_reject_not_citation_records_false_positive_without_confirming(tmp_path):
    store = tmp_path / "store"
    item = ledger.make_item("research/note.md", "10.1234/a",
                            [{"line": 9, "cited_text": "Smith (2020)"}],
                            tier="REVIEW", reason="title differs", evidence="")
    ledger.save_review([item], store)
    assert ledger.reject(item.item_id, "not_citation", store=store)
    assert ledger.reject(item.item_id, "not_citation", store=store)
    assert not ledger.reject(item.item_id, "wrong_work", store=store)
    assert ledger.load_review(store)[0].status == "declined"
    assert len(ledger.load_false_positives(store)) == 1
    assert ledger.load_defects(store) == []
    assert not ledger.is_human_confirmed("10.1234/a", "Smith (2020)", store=store)


def test_defer_survives_raise_and_invalid_decisions_do_not_write(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [_row("10.1234/a", "PLAUSIBLE")])
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.defer(item.item_id, store=store)
    assert ledger.defer(item.item_id, store=store)
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0].status == "deferred"
    before = (store / "review.json").read_bytes()
    assert not ledger.resolve("unknown", store=store)
    assert not ledger.reject("unknown", "wrong_work", store=store)
    assert not ledger.defer("unknown", store=store)
    with pytest.raises(ValueError, match="reason must be"):
        ledger.reject(item.item_id, "other", store=store)
    assert (store / "review.json").read_bytes() == before
    assert sorted(p.name for p in store.iterdir()) == ["defects.json", "review.json"]
