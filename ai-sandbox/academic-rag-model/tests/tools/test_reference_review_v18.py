"""Recorded registry answers for strict reference review and maintenance sweeps."""
import json

import pytest

from tools import reference_review as ledger
from tools.reference_checker import check_note


DOI = "10.1234/sample"
TITLE = "Sample paper"
MISSING_REASON = "no title: write the title of the work you mean"


class RecordedClient:
    def __init__(self, title=TITLE):
        self.title = title

    def get(self, url):
        if "/doiRA/" in url:
            return {"data": [{"RA": "Crossref"}]}
        if "api.crossref.org/works/" in url and "?" not in url:
            return {"status": 200, "data": {"message": {
                "DOI": DOI, "title": [self.title], "author": [{"family": "Smith"}],
                "published": {"date-parts": [[2020]]}, "container-title": ["Example Journal"]}}}
        if "api.openalex.org/works/doi:" in url:
            return {"status": 200, "data": {"authorships": [
                {"author": {"id": "https://openalex.org/A1"}}]}}
        if "api.openalex.org/works?" in url and "search=" not in url:
            return {"status": 200, "data": {"meta": {"count": 1}, "results": [
                {"doi": "https://doi.org/" + DOI, "title": self.title,
                 "publication_year": 2020, "type": "article",
                 "authorships": [{"author": {"id": "https://openalex.org/A1"}}]}]}}
        if "query.bibliographic=" in url:
            return {"status": 200, "data": {"message": {"items": [
                {"DOI": "10.1234/other", "title": ["Another real study"],
                 "issued": {"date-parts": [[2020]]}}]}}}
        if "query.author=" in url:
            return {"status": 200, "data": {"message": {"items": [
                {"DOI": DOI, "title": [self.title], "author": [{"family": "Smith"}],
                 "issued": {"date-parts": [[2020]]}, "type": "journal-article"}],
                "total-results": 1}}}
        if "api.openalex.org/works?" in url:
            return {"status": 200, "data": {"results": []}}
        raise AssertionError(url)


def note_at(tmp_path, text):
    note = tmp_path / "note.md"
    note.write_text(text, encoding="utf-8")
    return note


def test_strict_missing_title_is_defect_and_gate_counts_it(tmp_path):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    assert ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True) == []
    defects = ledger.load_defects(store)
    assert len(defects) == 1 and defects[0]["tier"] == "TITLE_MISSING"
    assert defects[0]["reason"].startswith(MISSING_REASON)
    assert TITLE not in json.dumps(defects)
    gate = ledger.gate([note], RecordedClient(), store=store, repo_root=tmp_path)
    assert gate.notes == [ledger.NoteGateResult("note.md", 1, 0, 0, 0)]


@pytest.mark.parametrize("tier, reason", [
    ("NOT_FOUND", "DOI not found in registry"),
    ("WRONG_WORK", "DOI belongs to another work"),
])
def test_strict_keeps_worse_defect_for_untitled_row(tmp_path, monkeypatch, tier, reason):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    row = {"identifier": DOI, "citation": "Smith (2020)", "line": 2,
           "tier": tier, "reason": reason,
           "registry_answer": {"record": {"title": TITLE}}}
    monkeypatch.setattr(ledger, "check_note", lambda text, client: [row])
    ledger.raise_items([note], object(), store=tmp_path / "store", repo_root=tmp_path, strict=True)
    defects = ledger.load_defects(tmp_path / "store")
    assert [(defect["tier"], defect["reason"]) for defect in defects] == [(tier, reason)]


def test_reference_list_title_confirms_same_doi_in_strict_mode(tmp_path):
    note = note_at(tmp_path, "# Note\n* [Smith (2020)](https://doi.org/10.1234/sample)\n\n"
                   "## References\n- Smith (2020). Sample paper. https://doi.org/10.1234/sample\n")
    store = tmp_path / "store"
    rows = {}
    assert ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path,
                              rows_by_note=rows, strict=True) == []
    assert [row["tier"] for row in rows["note.md"]] == ["CONFIRMED"]
    assert ledger.load_defects(store) == []


def test_titled_body_mention_counts_even_if_linked_entry_has_only_venue():
    rows = check_note("* [Smith (2020). Sample paper](https://doi.org/10.1234/sample)\n",
                      RecordedClient())
    rows[0]["linked_citation"] = "Smith (2020), Example Journal"
    items, defects = ledger._selected("note.md", rows, set(), strict=True)
    assert items == [] and defects == []


def test_other_real_title_stays_in_review_in_strict_mode(tmp_path):
    note = note_at(tmp_path, "# References\n* [Smith (2020). Another real study](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    items = ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert len(items) == 1 and items[0].candidates[0]["tier"] == "REVIEW"
    assert items[0].candidates[0]["cited_title_found"]["doi"] == "10.1234/other"
    assert ledger.load_defects(store) == []


def test_sweep_keeps_author_year_and_existing_title_missing_defect(tmp_path):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    rows = {}
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path,
                       rows_by_note=rows, strict=False)
    assert rows["note.md"][0]["tier"] == "AUTHOR_YEAR"
    assert ledger.load_defects(store) == []
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    original = ledger.load_defects(store)
    note.write_text("# References\n* [Smith (2020). Sample paper](https://doi.org/10.1234/sample)\n",
                    encoding="utf-8")
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=False)
    assert ledger.load_defects(store) == original
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert ledger.load_defects(store) == []


def test_strict_descriptive_links_and_no_doi_scope(tmp_path):
    note = note_at(tmp_path, "# References\n* [Springer chapter 14](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert [d["tier"] for d in ledger.load_defects(store)] == ["TITLE_MISSING"]
    note.write_text("# References\n* [Yemen cash versus food](https://doi.org/10.1234/sample)\n",
                    encoding="utf-8")
    client = RecordedClient("Cash and Food Transfers in Yemen")
    rows = {}
    ledger.raise_items([note], client, store=store, repo_root=tmp_path, rows_by_note=rows, strict=True)
    assert rows["note.md"][0]["tier"] == "DESCRIBED"
    assert ledger.load_defects(store) == []
    note.write_text("# References\n* Smith (2020), no DOI\n", encoding="utf-8")
    ledger.raise_items([note], client, store=store, repo_root=tmp_path, strict=True)
    assert ledger.load_defects(store) == []


def test_quote_clears_exact_text_and_changed_text_reopens(tmp_path):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    decision = {"item_id": ledger.item_id("note.md", DOI), "action": "quoted",
                "note": "note.md", "doi": DOI, "citation_texts": ["Smith (2020)"]}
    assert ledger.apply_decisions([decision], store=store)[0]["outcome"] == "applied"
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert ledger.load_defects(store) == []
    note.write_text("# References\n* [Smith (2020) changed](https://doi.org/10.1234/sample)\n",
                    encoding="utf-8")
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert [d["tier"] for d in ledger.load_defects(store)] == ["TITLE_MISSING"]


def test_prior_accept_does_not_exempt_titleless_strict_note(tmp_path):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    store = tmp_path / "store"
    item = ledger.make_item("note.md", DOI, [{"line": 2, "cited_text": "Smith (2020)"}],
                            tier="PLAUSIBLE", reason="", evidence="")
    item.status = "accepted"
    ledger.save_review([item], store)
    ledger.save_dismissals([{"doi": DOI, "normalized_citation": "smith 2020",
                           "item_id": item.item_id}], store)
    ledger.raise_items([note], RecordedClient(), store=store, repo_root=tmp_path, strict=True)
    assert [d["tier"] for d in ledger.load_defects(store)] == ["TITLE_MISSING"]


def test_cli_raise_is_strict_and_omits_registry_title(tmp_path, monkeypatch, capsys):
    note = note_at(tmp_path, "# References\n* [Smith (2020)](https://doi.org/10.1234/sample)\n")
    monkeypatch.setattr(ledger, "DEFAULT_STORE", tmp_path / "store")
    monkeypatch.setattr(ledger, "DEFAULT_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ledger, "RegistryClient", lambda *args, **kwargs: RecordedClient())
    assert ledger.main(["raise", str(note)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [d["tier"] for d in payload["defects"]] == ["TITLE_MISSING"]
    assert TITLE not in json.dumps(payload)
