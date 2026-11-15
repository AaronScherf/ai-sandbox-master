"""Fixture-only tests for the reference-review ledger foundation."""
import json

import pytest

from core.indexer.review_envelope import _digest
from tools import reference_review as ledger


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
