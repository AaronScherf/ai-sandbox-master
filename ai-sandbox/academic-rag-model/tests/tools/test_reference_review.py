"""Fixture-only tests for the reference-review ledger foundation."""
import json
import subprocess
from pathlib import Path

import pytest

from core.indexer.review_envelope import _digest
from tools import reference_review as ledger
from tools import reference_checker as checker
from tools.reference_checker import check_note


def test_default_store_and_cache_resolve_to_main_from_worktree_layout(tmp_path):
    main = tmp_path / "main"
    main.mkdir()

    def git(cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, check=True).stdout.strip()

    git(main, "init", "-b", "main")
    (main / "seed.txt").write_text("seed", encoding="utf-8")
    git(main, "add", "seed.txt")
    git(main, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", "seed")
    worktree = tmp_path / "worktree"
    git(main, "worktree", "add", "-b", "codex/test", str(worktree))
    project = Path("ai-sandbox/academic-rag-model")
    (worktree / project).mkdir(parents=True)

    assert checker.shared_project_root(worktree / project) == main / project
    assert checker.DEFAULT_CACHE == ledger.DEFAULT_STORE.parent / ".reference_checker_cache"
    assert ledger.DEFAULT_STORE == checker.shared_project_root() / ".reference_checker_review"


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


def test_quoted_checker_defect_is_note_local_and_changed_text_reopens(tmp_path, monkeypatch):
    first, second = tmp_path / "first.md", tmp_path / "second.md"
    first.write_text("citation", encoding="utf-8")
    second.write_text("citation", encoding="utf-8")
    doi = "10.1234/example"
    citation = "Smith (2020). Quoted wrong title"
    rows = [_row(doi, "TITLE_WRONG", citation)]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    ledger.raise_items([first, second], None, store=tmp_path / "ledger", repo_root=tmp_path)
    store = tmp_path / "ledger"
    decision = {"item_id": ledger.item_id("first.md", doi), "action": "quoted",
                "note": "first.md", "doi": doi, "citation_texts": [citation]}
    assert ledger.apply_decisions([decision], store=store)[0]["outcome"] == "applied"
    assert ledger.apply_decisions([decision], store=store)[0]["outcome"] == "already_applied"
    assert [(d["note"], d["tier"]) for d in ledger.load_defects(store)] == [
        ("second.md", "TITLE_WRONG")]
    assert not ledger.gate([first], None, store=store, repo_root=tmp_path).blocked
    assert ledger.gate([second], None, store=store, repo_root=tmp_path).blocked
    ledger.raise_items([first, second], None, store=store, repo_root=tmp_path)
    assert [d["note"] for d in ledger.load_defects(store)] == ["second.md"]
    rows[:] = [_row(doi, "TITLE_WRONG", citation + " changed")]
    ledger.raise_items([first], None, store=store, repo_root=tmp_path)
    assert sorted(d["note"] for d in ledger.load_defects(store)) == ["first.md", "second.md"]
    assert ledger.load_quoted(store) == []


def test_quoted_item_rejects_another_notes_identity(tmp_path, monkeypatch):
    note = tmp_path / "first.md"
    note.write_text("citation", encoding="utf-8")
    doi = "10.1234/example"
    citation = "Smith (2020)"
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [_row(doi, "PLAUSIBLE", citation)])
    store = tmp_path / "ledger"
    ledger.raise_items([note], None, store=store, repo_root=tmp_path)
    wrong = {"item_id": ledger.item_id("first.md", doi), "action": "quoted",
             "note": "second.md", "doi": doi, "citation_texts": [citation]}
    assert ledger.apply_decisions([wrong], store=store)[0]["outcome"] == "stale"
    assert not ledger.load_quoted(store)
    right = {**wrong, "note": "first.md"}
    assert ledger.apply_decisions([right], store=store)[0]["outcome"] == "applied"
    assert ledger.list_items("open", store=store) == []
    ledger.raise_items([note], None, store=store, repo_root=tmp_path)
    assert ledger.list_items("open", store=store) == []
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [
        _row(doi, "PLAUSIBLE", citation + " changed")])
    ledger.raise_items([note], None, store=store, repo_root=tmp_path)
    assert len(ledger.list_items("open", store=store)) == 1


def test_defect_cards_expose_note_local_quote_target(tmp_path):
    ledger.save_defects([{"note": "research/example.md", "doi": "10.1234/example",
                          "tier": "TITLE_WRONG", "reason": "registered title differs",
                          "registry_title": "Sample paper", "source": "checker",
                          "mentions": [{"line": 9, "cited_text": "Smith (2020). Quoted wrong title"}]}],
                        tmp_path)
    cards = ledger.list_defect_cards(store=tmp_path)
    assert cards == [{"item_id": ledger.item_id("research/example.md", "10.1234/example"),
                      "note": "research/example.md", "note_name": "example.md",
                      "doi": "10.1234/example", "tier": "TITLE_WRONG",
                      "reason": "registered title differs", "is_defect": True,
                      "mentions": [{"line": 9, "cited_text": "Smith (2020). Quoted wrong title"}],
                      "citation_texts": ["Smith (2020). Quoted wrong title"],
                      "registry": {"title": "Sample paper"}}]


def test_incomplete_title_search_preserves_declined_item_and_human_defect(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    citation = "Smith (2020). Invented title."
    rows = [_row("10.1234/a", "REVIEW", citation)]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.reject(item.item_id, "wrong_title", store=store)
    before_item = ledger.load_review(store)[0].to_dict()
    before_defects = ledger.load_defects(store)
    rows[0] = {**_row("10.1234/a", "REVIEW", citation),
               "reason": "author overlap; title search unavailable"}

    stats = {}
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats) == []
    assert stats == {"incomplete_lookup_kept": 1}
    assert ledger.load_review(store)[0].to_dict() == before_item
    assert ledger.load_defects(store) == before_defects
    assert ledger.list_items("open", store=store) == []
    result = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert result.notes == [ledger.NoteGateResult("note.md", 1, 0, 1, 0)]


def test_incomplete_title_search_keeps_matching_checker_defect_without_new_item(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [_row("10.1234/a", "TITLE_WRONG")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    before = ledger.load_defects(store)
    assert ledger.load_review(store) == []
    rows[0] = {**_row("10.1234/a", "REVIEW"), "reason": "title search unavailable"}

    stats = {}
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats) == []
    assert stats == {"incomplete_lookup_kept": 1}
    assert ledger.load_defects(store) == before
    assert ledger.load_review(store) == []
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes[0].unresolved == 1

    rows[0] = {**_row("10.1234/a", "REVIEW", "Smith (2020). Changed title."),
               "reason": "title search unavailable"}
    assert len(ledger.raise_items([note], object(), store=store, repo_root=tmp_path)) == 1
    assert ledger.load_defects(store) == []


def test_incomplete_title_search_keeps_matching_human_defect_without_prior_item(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    citation = "Smith (2020). Invented title."
    store = tmp_path / "store"
    defect = {"note": "note.md", "doi": "10.1234/a", "tier": "TITLE_WRONG",
              "reason": "human reviewer: DOI correct; title wrong", "source": "human",
              "mentions": [{"line": 2, "cited_text": citation}]}
    ledger.save_defects([defect], store)
    rows = [{**_row("10.1234/a", "REVIEW", citation),
             "reason": "title search unavailable"}]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)

    stats = {}
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats) == []
    assert stats == {"incomplete_lookup_kept": 1}
    assert ledger.load_review(store) == []
    assert ledger.load_defects(store) == [defect]
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes == [
        ledger.NoteGateResult("note.md", 1, 0, 1, 0)]

    rows[0] = {**_row("10.1234/a", "REVIEW", citation), "reason": "alternate title found"}
    complete = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert len(complete) == 1 and complete[0].status == "pending"
    assert ledger.load_defects(store) == [defect]


def test_incomplete_title_search_does_not_keep_human_defect_for_changed_mention(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    store = tmp_path / "store"
    ledger.save_defects([{"note": "note.md", "doi": "10.1234/a", "tier": "TITLE_WRONG",
                          "source": "human", "reason": "old title wrong",
                          "mentions": [{"line": 2, "cited_text": "Smith (2020). Old title."}]}], store)
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [
        {**_row("10.1234/a", "REVIEW", "Smith (2020). Changed title."),
         "reason": "title search unavailable"}])

    stats = {}
    opened = ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats)
    assert len(opened) == 1 and opened[0].status == "pending"
    assert ledger.load_defects(store) == []
    assert stats == {"incomplete_lookup_kept": 0}


def test_incomplete_doi_lookup_preserves_accepted_item_and_candidate(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [_row("10.1234/a", "REVIEW")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.resolve(item.item_id, store=store)
    before = ledger.load_review(store)[0].to_dict()
    rows[0] = {**_row("10.1234/a", "UNRESOLVED"),
               "reason": "registry lookup unavailable: HTTP 503", "registry_answer": None}

    stats = {}
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats) == []
    assert stats == {"incomplete_lookup_kept": 1}
    assert ledger.load_review(store)[0].to_dict() == before
    assert ledger.list_items("open", store=store) == []
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes[0].unresolved == 1


def test_new_incomplete_lookup_is_pending_and_complete_change_reopens(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [{**_row("10.1234/a", "REVIEW"), "reason": "title search unavailable"}]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    stats = {}
    first = ledger.raise_items([note], object(), store=store, repo_root=tmp_path, stats=stats)
    assert len(first) == 1 and first[0].status == "pending"
    assert stats == {"incomplete_lookup_kept": 0}
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes[0].unresolved == 1

    rows[0] = _row("10.1234/a", "REVIEW")
    assert ledger.resolve(first[0].item_id, store=store)
    rows[0] = _row("10.1234/a", "REVIEW", "Smith (2020). Changed title.")
    reopened = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert len(reopened) == 1 and reopened[0].status == "pending"
    assert reopened[0].candidates[0]["mentions"][0]["cited_text"] == "Smith (2020). Changed title."


@pytest.mark.parametrize(("field", "changed_value"), [
    ("title", "A different registered title"), ("authors", ["Jones"]),
    ("year", 2021), ("venue", "Another Journal"),
])
def test_complete_registry_change_reopens_accepted_item_with_same_citation(
        tmp_path, monkeypatch, field, changed_value):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [_row("10.1234/a", "REVIEW")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.resolve(item.item_id, store=store)
    assert ledger.load_review(store)[0].status == "accepted"

    changed = _row("10.1234/a", "REVIEW")
    changed["registry_answer"]["record"][field] = changed_value
    rows[0] = changed
    reopened = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert len(reopened) == 1 and reopened[0].status == "pending"
    assert reopened[0].candidates[0]["registry"][field] == changed_value


def test_complete_tier_change_reopens_accepted_item(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [_row("10.1234/a", "REVIEW")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.resolve(item.item_id, store=store)

    rows[0] = _row("10.1234/a", "PLAUSIBLE")
    reopened = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)
    assert len(reopened) == 1 and reopened[0].status == "pending"
    assert reopened[0].candidates[0]["tier"] == "PLAUSIBLE"


@pytest.mark.parametrize("change", ["line", "siblings"])
def test_accepted_item_ignores_nonmaterial_complete_lookup_change(tmp_path, monkeypatch, change):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    rows = [_row("10.1234/a", "REVIEW")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    item = ledger.raise_items([note], object(), store=store, repo_root=tmp_path)[0]
    assert ledger.resolve(item.item_id, store=store)
    before = ledger.load_review(store)[0]

    changed = _row("10.1234/a", "REVIEW", line=19 if change == "line" else 2)
    if change == "siblings":
        changed["siblings"] = [{"doi": "10.1234/b", "title": "Another work",
                                "year": 2021, "type": "article"}]
    rows[0] = changed
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path) == []
    kept = ledger.load_review(store)[0]
    assert kept.status == "accepted" and kept.updated == before.updated
    if change == "line":
        assert kept.candidates[0]["mentions"][0]["line"] == 19
    else:
        assert kept.candidates[0]["siblings"][0]["doi"] == "10.1234/b"


def test_raise_cli_reports_incomplete_kept_count_and_retry_advice(tmp_path, monkeypatch, capsys):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    store = tmp_path / "store"
    ledger.save_defects([{"note": "note.md", "doi": "10.1234/a", "tier": "TITLE_WRONG",
                          "reason": "cited title not found", "source": "checker",
                          "mentions": [{"line": 2, "cited_text": "Smith (2020)"}]}], store)
    monkeypatch.setattr(ledger, "DEFAULT_STORE", store)
    monkeypatch.setattr(ledger, "DEFAULT_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ledger, "RegistryClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [
        {**_row("10.1234/a", "REVIEW"), "reason": "title search unavailable"}])

    assert ledger.main(["raise", str(note), "--sweep", "--offline", "--cache", str(tmp_path / "cache")]) == 0
    captured = capsys.readouterr()
    assert captured.err.splitlines() == ["Incomplete lookups kept prior state: 1; retry later",
                                         "Review load: no queued items or decisions"]
    payload = json.loads(captured.out)
    assert payload["incomplete_lookup_kept"] == 1
    assert payload["items"] == [] and len(payload["defects"]) == 1


def test_raise_cli_omits_retry_line_when_no_prior_state_is_kept(tmp_path, monkeypatch, capsys):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    monkeypatch.setattr(ledger, "DEFAULT_STORE", tmp_path / "store")
    monkeypatch.setattr(ledger, "DEFAULT_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ledger, "RegistryClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [_row("10.1234/a", "REVIEW")])

    assert ledger.main(["raise", str(note), "--sweep", "--offline", "--cache", str(tmp_path / "cache")]) == 0
    captured = capsys.readouterr()
    assert captured.err == "Review load: REVIEW: 1 queued, no decisions\n"
    assert json.loads(captured.out)["incomplete_lookup_kept"] == 0


@pytest.mark.parametrize("tier", ["WRONG_WORK", "NOT_FOUND", "TITLE_WRONG"])
def test_gate_blocks_checker_defects_by_note(tmp_path, monkeypatch, tier):
    note = tmp_path / "note.md"
    note.write_text("# References\n", encoding="utf-8")
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [_row("10.1234/a", tier)])
    result = ledger.gate([note], object(), store=tmp_path / "store", repo_root=tmp_path)
    assert result.blocked
    assert result.notes == [ledger.NoteGateResult("note.md", 1, 0, 0, 0)]


def test_gate_open_item_blocks_until_resolved_and_deferred_still_blocks(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("# References\n", encoding="utf-8")
    row = {**_row("10.1234/a", "REVIEW"), "linked_citation": "Smith (2020). Sample paper"}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [row])
    store = tmp_path / "store"
    first = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert first.blocked and first.notes[0].open_items == 1
    item = ledger.list_items(store=store)[0]
    assert ledger.defer(item.item_id, store=store)
    deferred = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert deferred.blocked and deferred.notes[0].open_items == 1
    assert ledger.resolve(item.item_id, store=store)
    resolved = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert not resolved.blocked and resolved.notes[0].open_items == 0


def test_gate_preserves_matching_human_defect_after_acceptance(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("# References\n", encoding="utf-8")
    row = {**_row("10.1234/a", "CONFIRMED"), "linked_citation": "Smith (2020). Sample paper"}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [row])
    store = tmp_path / "store"
    ledger.save_defects([{"note": "note.md", "doi": "10.1234/a", "tier": "TITLE_WRONG",
                          "reason": "fix title", "source": "human",
                          "mentions": [{"line": 2, "cited_text": "Smith (2020)"}]}], store)
    result = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert result.blocked and result.notes[0].defects == 1


def test_gate_fails_closed_on_lookup_and_reports_url_only_rows(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("# References\n", encoding="utf-8")
    rows = [{**_row("10.1234/a", "CONFIRMED"), "linked_citation": "Smith (2020). Sample paper"},
            {**_row("10.1234/b", "AUTHOR_YEAR"), "linked_citation": "Smith (2020). Sample paper"},
            _row("https://example.org/paper", "UNCHECKED")]
    monkeypatch.setattr(ledger, "check_note", lambda text, client: rows)
    store = tmp_path / "store"
    passed = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert not passed.blocked
    assert passed.notes == [ledger.NoteGateResult("note.md", 0, 0, 0, 1)]

    failure = {**_row("10.1234/c", "UNRESOLVED"), "linked_citation": "Smith (2020). Sample paper"}
    failure["reason"] = "registry lookup unavailable: HTTP 503"
    rows.append(failure)
    blocked = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert blocked.blocked and blocked.notes[0].unresolved == 1
    title_failure = {**_row("10.1234/d", "REVIEW"), "linked_citation": "Smith (2020). Sample paper"}
    title_failure["reason"] = "title search unavailable"
    rows.append(title_failure)
    blocked = ledger.gate([note], object(), store=store, repo_root=tmp_path)
    assert blocked.notes[0].unresolved == 2
    guard_failure = {**_row("10.1234/e", "PLAUSIBLE"), "linked_citation": "Smith (2020). Sample paper"}
    guard_failure["reason"] = "same-team guard incomplete: Crossref lookup unavailable"
    rows.append(guard_failure)
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes[0].unresolved == 3
    metadata_gap = {**_row("10.1234/f", "PLAUSIBLE"), "linked_citation": "Smith (2020). Sample paper"}
    metadata_gap["reason"] = "same-team guard incomplete: first OpenAlex author ID missing"
    rows.append(metadata_gap)
    assert ledger.gate([note], object(), store=store, repo_root=tmp_path).notes[0].unresolved == 3


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


def test_checker_title_wrong_does_not_duplicate_matching_human_defect(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.write_text("note", encoding="utf-8")
    row = {**_row("10.1234/a", "TITLE_WRONG"), "registry_title": "Sample paper"}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [row])
    store = tmp_path / "store"
    human = {"note": "note.md", "doi": "10.1234/a", "tier": "TITLE_WRONG",
             "reason": "human reviewer: DOI correct; use Sample paper",
             "mentions": [{"line": 2, "cited_text": "Smith (2020)"}],
             "source": "human", "registry_title": "Sample paper"}
    ledger.save_defects([human], store)
    assert ledger.raise_items([note], object(), store=store, repo_root=tmp_path) == []
    assert ledger.load_defects(store) == [human]


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
    note.write_text("# References\n\n* [Smith (2021)](https://doi.org/10.1234/sample)\n", encoding="utf-8")
    items = ledger.raise_items([note], Client(), store=tmp_path / "store", repo_root=tmp_path)
    assert len(items) == 1
    assert items[0].candidates[0]["tier"] == "PLAUSIBLE"
    assert items[0].candidates[0]["mentions"] == [
        {"line": 3, "cited_text": "Smith (2021)", "normalized_citation": "smith 2021"}]


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


def test_wrong_title_decision_is_note_local_and_apply_is_idempotent(tmp_path):
    store = tmp_path / "store"
    title = "The registered title"
    items = [ledger.make_item(note, "10.1234/a", [{"line": 3, "cited_text": "Smith (2020). Invented title."}],
                              tier="REVIEW", reason="title differs", evidence="",
                              record={"title": title, "authors": ["Smith"], "year": 2020})
             for note in ("research/a.md", "research/b.md")]
    ledger.save_review(items, store)
    decision = {"item_id": items[0].item_id, "action": "decline", "chosen": "wrong_title"}
    assert ledger.apply_decisions([decision], store=store)[0]["outcome"] == "applied"
    assert ledger.apply_decisions([decision], store=store)[0]["outcome"] == "already_applied"
    assert not ledger.reject(items[0].item_id, "wrong_work", store=store)
    assert [item.status for item in ledger.load_review(store)] == ["declined", "pending"]
    defects = ledger.load_defects(store)
    assert len(defects) == 1
    assert defects[0]["tier"] == "TITLE_WRONG"
    assert defects[0]["registry_title"] == title
    assert "confirm which work you meant" in defects[0]["reason"] and title in defects[0]["reason"]
    assert defects[0]["note"] == "research/a.md"
    assert ledger.load_dismissals(store) == []


def test_relabel_defect_requires_hand_annotation_and_is_idempotent(tmp_path):
    store = tmp_path / "store"
    title = "The registered title"
    item = ledger.make_item("research/a.md", "10.1234/a",
                            [{"line": 3, "cited_text": "Smith (2020). Invented title."}],
                            tier="REVIEW", reason="title differs", evidence="",
                            record={"title": title, "authors": ["Smith"], "year": 2020})
    item.status = "declined"
    ledger.save_review([item], store)
    original = {"note": "research/a.md", "doi": "10.1234/a", "tier": "WRONG_WORK",
                "reason": f"human reviewer: DOI and registry record are correct; use '{title}'",
                "mentions": [{"line": 3, "cited_text": "Smith (2020). Invented title."}],
                "source": "human"}
    ledger.save_defects([original], store)
    assert ledger.relabel_defect("research/a.md", "10.1234/a", store=store)
    migrated = ledger.load_defects(store)
    assert migrated == [{**original, "tier": "TITLE_WRONG", "registry_title": title}]
    before = (store / "defects.json").read_bytes()
    assert ledger.relabel_defect("research/a.md", "10.1234/a", store=store)
    assert (store / "defects.json").read_bytes() == before
    assert not ledger.reject_reason_matches(item, "wrong_work", store)
    assert ledger.reject_reason_matches(item, "wrong_title", store)
    ledger.save_defects([original | {"reason": "human reviewer: wrong work"}], store)
    assert not ledger.relabel_defect("research/a.md", "10.1234/a", store=store)
    assert ledger.load_defects(store)[0]["tier"] == "WRONG_WORK"


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
    prior = ledger.make_item("note.md", doi, [{"line": 2, "cited_text": "Smith (2020)"}],
                             tier="PLAUSIBLE", reason="same-team sibling", evidence="")
    prior.status = "deferred"
    ledger.save_review([prior], store)
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
    note.write_text("# References\n* [Smith (2021)](https://doi.org/10.1234/sample)\n", encoding="utf-8")

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
    assert ledger.main(["raise", str(note), "--sweep", "--offline", "--cache", str(tmp_path / "cache")]) == 0
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


def test_review_load_summary_counts_decisions_and_automation_candidate(tmp_path):
    accepted = [ledger.make_item(f"a{i}.md", f"10.1234/a{i}",
                                 [{"line": 1, "cited_text": "Smith (2020)"}],
                                 tier="PLAUSIBLE", reason="", evidence="") for i in range(10)]
    declined = ledger.make_item("b.md", "10.1234/b",
                                [{"line": 1, "cited_text": "Smith (2020)"}],
                                tier="REVIEW", reason="", evidence="")
    ledger.save_review(accepted + [declined], tmp_path)
    decisions = [{"item_id": item.item_id, "action": "accept", "chosen": None} for item in accepted]
    decisions.append({"item_id": declined.item_id, "action": "decline", "chosen": "wrong_work"})
    assert all(result["outcome"] == "applied" for result in ledger.apply_decisions(decisions, store=tmp_path))
    summary = ledger.review_load_summary(accepted[:2] + [declined], tmp_path)
    assert summary["PLAUSIBLE"] == {"queued": 2, "accepted": 10, "decisions": 10,
                                   "accept_rate": 1.0, "automation_candidate": True}
    assert summary["REVIEW"]["accept_rate"] == 0.0
    assert summary["REVIEW"]["automation_candidate"] is False


def test_review_load_summary_reads_applied_accept_and_decline_tiers(tmp_path):
    accepted = ledger.make_item("a.md", "10.1234/a",
                                [{"line": 1, "cited_text": "Smith (2020)"},
                                 {"line": 2, "cited_text": "Smith et al. (2020)"}],
                                tier="PLAUSIBLE", reason="", evidence="")
    declined = ledger.make_item("b.md", "10.1234/b",
                                [{"line": 1, "cited_text": "Jones (2020)"}],
                                tier="PLAUSIBLE", reason="", evidence="")
    ledger.save_review([accepted, declined], tmp_path)
    results = ledger.apply_decisions([
        {"item_id": accepted.item_id, "action": "accept", "chosen": None},
        {"item_id": declined.item_id, "action": "decline", "chosen": "wrong_work"},
    ], store=tmp_path)
    assert [result["outcome"] for result in results] == ["applied", "applied"]
    assert len(ledger.load_dismissals(tmp_path)) == 2
    assert all(entry["review_tier"] == "PLAUSIBLE" for entry in ledger.load_dismissals(tmp_path))
    assert ledger.load_defects(tmp_path)[0]["review_tier"] == "PLAUSIBLE"
    ledger.save_review([], tmp_path)
    assert ledger.review_load_summary([], tmp_path)["PLAUSIBLE"] == {
        "queued": 0, "accepted": 1, "decisions": 2,
        "accept_rate": 0.5, "automation_candidate": False,
    }
