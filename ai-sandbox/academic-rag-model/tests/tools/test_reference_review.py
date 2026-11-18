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
    }, siblings=[{"doi": "10.1234/other", "title": "Other work", "year": 2021,
                  "type": "journal-article", "abstract": "private sibling abstract"}])
    ledger.save_review([item], tmp_path)
    assert ledger.load_review(tmp_path) == [item]
    saved = (tmp_path / "review.json").read_text(encoding="utf-8")
    assert "private" not in saved
    assert item.candidates[0]["mentions"][0]["normalized_citation"] == "garcia 2020"
    assert len(item.candidates[0]["mentions"]) == 2
    assert item.candidates[0]["siblings"] == [{"doi": "10.1234/other", "title": "Other work",
                                               "year": 2021, "type": "journal-article"}]
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


def test_author_year_is_not_queued_and_clears_prior_deferred_item(tmp_path):
    doi = "10.1234/sample"

    class Client:
        sibling = True

        def get(self, url):
            if "/doiRA/" in url:
                return {"data": [{"RA": "Crossref"}]}
            if "api.openalex.org/works/doi:" in url:
                return {"status": 200, "data": {"authorships": [
                    {"author": {"id": "https://openalex.org/A1"}}]}}
            if "api.openalex.org/works?" in url:
                items = [{"doi": "https://doi.org/" + doi, "title": "Sample paper",
                          "authorships": [{"author": {"id": "https://openalex.org/A1"}}],
                          "publication_year": 2020, "type": "article"}]
                return {"status": 200, "data": {"meta": {"count": len(items)}, "results": items}}
            if "query.author=" in url:
                items = [{"DOI": doi, "title": ["Sample paper"],
                          "author": [{"family": "Smith"}],
                          "issued": {"date-parts": [[2020]]}, "type": "journal-article"}]
                if self.sibling:
                    items.append({"DOI": "10.1234/other", "title": ["Distinct work"],
                                  "author": [{"family": "Smith"}],
                                  "issued": {"date-parts": [[2021]]}, "type": "journal-article"})
                return {"status": 200, "data": {"message": {
                    "items": items, "total-results": len(items)}}}
            return {"status": 200, "data": {"message": {
                "DOI": doi, "title": ["Sample paper"], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}, "container-title": ["Journal"]}}}

    note = tmp_path / "note.md"
    note.write_text("# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n", encoding="utf-8")
    store = tmp_path / "store"
    client = Client()
    first = ledger.raise_items([note], client, store=store, repo_root=tmp_path)
    assert len(first) == 1 and first[0].candidates[0]["tier"] == "PLAUSIBLE"
    assert first[0].candidates[0]["siblings"] == [{
        "doi": "10.1234/other", "title": "Distinct work", "year": 2021,
        "type": "journal-article"}]
    assert ledger.defer(first[0].item_id, store=store)
    assert ledger.load_review(store)[0].status == "deferred"
    client.sibling = False
    assert ledger.raise_items([note], client, store=store, repo_root=tmp_path) == []
    assert ledger.load_review(store) == []
    assert ledger.load_defects(store) == []


def test_apply_decisions_reports_unknown_continues_and_is_idempotent(tmp_path):
    store = tmp_path / "store"
    items = [ledger.make_item("a.md", f"10.1234/{suffix}",
                              [{"line": 1, "cited_text": f"Smith ({year})"}],
                              tier="PLAUSIBLE", reason="no title", evidence="")
             for suffix, year in (("a", 2020), ("b", 2021), ("c", 2022))]
    ledger.save_review(items, store)
    decisions = [
        {"item_id": "unknown", "action": "accept", "chosen": None, "ts": "2026-11-15T00:00:00Z"},
        {"item_id": items[0].item_id, "action": "accept", "chosen": None, "ts": "2026-11-15T00:00:00Z"},
        {"item_id": items[1].item_id, "action": "decline", "chosen": "wrong_work", "ts": "2026-11-15T00:00:00Z"},
        {"item_id": items[2].item_id, "action": "defer", "chosen": None, "ts": "2026-11-15T00:00:00Z"},
    ]
    results = ledger.apply_decisions(decisions, store=store)
    assert [result["outcome"] for result in results] == ["stale", "applied", "applied", "applied"]
    assert results[0]["detail"] == "unknown item_id"
    assert [item.status for item in ledger.load_review(store)] == ["accepted", "declined", "deferred"]
    repeated = ledger.apply_decisions(decisions, store=store)
    assert [result["outcome"] for result in repeated] == [
        "stale", "already_applied", "already_applied", "applied"]
    assert len(ledger.load_dismissals(store)) == 1
    assert len(ledger.load_defects(store)) == 1


def test_apply_dry_run_writes_nothing_and_rejects_invalid_chosen(tmp_path):
    store = tmp_path / "store"
    item = ledger.make_item("a.md", "10.1234/a", [{"line": 1, "cited_text": "Smith (2020)"}],
                            tier="REVIEW", reason="title differs", evidence="")
    ledger.save_review([item], store)
    before = {path.name: path.read_bytes() for path in store.iterdir()}
    decisions = [{"item_id": item.item_id, "action": "decline", "chosen": "wrong_work"},
                 {"item_id": item.item_id, "action": "accept"}]
    results = ledger.apply_decisions(decisions, dry_run=True, store=store)
    assert [result["outcome"] for result in results] == ["would_apply", "stale"]
    assert ledger.apply_decisions([{"item_id": item.item_id, "action": "decline", "chosen": "other"}],
                                  store=store)[0]["outcome"] == "error"
    assert {path.name: path.read_bytes() for path in store.iterdir()} == before


def test_cli_list_apply_and_raise_with_recorded_client(tmp_path, monkeypatch, capsys):
    store = tmp_path / "store"
    monkeypatch.setattr(ledger, "DEFAULT_STORE", store)
    monkeypatch.setattr(ledger, "DEFAULT_REPO_ROOT", tmp_path)
    note = tmp_path / "note.md"
    note.write_text("# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n", encoding="utf-8")

    class Client:
        def __init__(self, cache, online):
            assert online is False

        def get(self, url):
            if "/doiRA/" in url:
                return {"data": [{"RA": "Crossref"}]}
            return {"status": 200, "data": {"message": {
                "title": ["Sample paper"], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}, "container-title": ["Journal"]}}}

    monkeypatch.setattr(ledger, "RegistryClient", Client)
    assert ledger.main(["raise", str(note), "--offline", "--cache", str(tmp_path / "cache")]) == 0
    raised = json.loads(capsys.readouterr().out)
    iid = raised["items"][0]["item_id"]
    assert raised["defects"] == []
    assert ledger.main(["list", "--status", "pending"]) == 0
    assert [row["item_id"] for row in json.loads(capsys.readouterr().out)] == [iid]
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps([{"item_id": iid, "action": "defer", "chosen": None,
                                      "ts": "2026-11-15T00:00:00Z"}]), encoding="utf-8")
    assert ledger.main(["apply", str(decisions), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["outcome"] == "would_apply"
    assert ledger.main(["apply", str(decisions)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["outcome"] == "applied"
    assert ledger.main(["list"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["status"] == "deferred"
