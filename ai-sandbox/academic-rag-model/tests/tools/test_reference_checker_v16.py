"""Recorded registry answers for the v16 citation shapes."""
import json
import urllib.parse
from pathlib import Path

import pytest

from tools.reference_checker import check, clean_identifier, extract


RECORDS = {
    "10.1007/s10705-021-10174-1": ("Nziguheba", 2021,
        "Quantifying the prevalence of (non)-response to fertilizers in SSA using on-farm trial data",
        "Nutrient Cycling in Agroecosystems"),
    "10.1016/j.agee.2016.05.012": ("Kihara", 2016,
        "Understanding variability in crop response to fertilizer and amendments in SSA",
        "Agriculture, Ecosystems and Environment"),
    "10.1038/s41597-025-05001-z": ("Lee", 2025,
        "HarvestStat Africa – Harmonized Subnational Crop Statistics for Sub-Saharan Africa",
        "Scientific Data"),
    "10.3982/ECTA17945": ("Egger", 2022,
        "General Equilibrium Effects of Cash Transfers: Experimental Evidence From Kenya", "Econometrica"),
    "10.1257/aer.p20151069": ("Bleakley", 2015, "History and the Sizes of Cities",
        "American Economic Review"),
}
BROWN_DOI = "10.1257/pandp.20251021"
MEAGER_DOI = "10.1257/app.20170299"
RECORDED_ANSWERS = json.loads((Path(__file__).parent / "fixtures" / "reference_checker_v2.json")
                              .read_text(encoding="utf-8"))


class RecordedClient:
    def __init__(self):
        self.searches = []

    def get(self, url):
        if "/doiRA/" in url:
            doi = urllib.parse.unquote(url.split("/doiRA/", 1)[1])
            if doi in {BROWN_DOI, MEAGER_DOI}:
                return RECORDED_ANSWERS[doi]["agency"]
            return {"data": [{"RA": "Crossref"}]}
        if "/works/" in url and "?" not in url:
            doi = urllib.parse.unquote(url.split("/works/", 1)[1])
            if doi in {BROWN_DOI, MEAGER_DOI}:
                answer = RECORDED_ANSWERS[doi]["answer"]
                return {"status": answer["status"], "data": {"message": answer["data"]}}
            author, year, title, venue = RECORDS[doi]
            return {"status": 200, "data": {"message": {"DOI": doi, "title": [title],
                "author": [{"family": author}], "issued": {"date-parts": [[year]]},
                "container-title": [venue]}}}
        if "query.bibliographic=" in url or "api.openalex.org/works?search=" in url:
            self.searches.append(url)
            return ({"status": 200, "data": {"message": {"items": []}}} if "crossref" in url else
                    {"status": 200, "data": {"results": []}})
        raise AssertionError(url)


def _check(citation, doi, client):
    return check({"citation": citation, "identifier": doi, "kind": "doi"}, client,
                 author_year=False)


def test_italic_venue_is_not_a_title_even_before_doi():
    client = RecordedClient()
    for doi, citation in (
        ("10.1007/s10705-021-10174-1", "Nziguheba G et al. (2021). *Nutrient Cycling in Agroecosystems*. doi:10.1007/s10705-021-10174-1"),
        ("10.1016/j.agee.2016.05.012", "Kihara J et al. (2016). *Agriculture, Ecosystems and Environment*. doi:10.1016/j.agee.2016.05.012"),
    ):
        result = _check(citation, doi, client)
        assert result["tier"] == "PLAUSIBLE"
        assert "NO_TITLE" in result["text_fidelity"]
    assert client.searches == []


def test_whole_word_short_title_prefix_is_confirmed_without_search():
    client = RecordedClient()
    result = _check("Lee et al. (2025). HarvestStat Africa. *Scientific Data*.",
                    "10.1038/s41597-025-05001-z", client)
    assert result["tier"] == "CONFIRMED"
    assert client.searches == []


def test_comparison_prose_does_not_trigger_title_search():
    client = RecordedClient()
    for citation in ("Egger et al. (2022) vs Kenya HSNP Phase 2 LEWIE (2019)",
                     "Egger et al. (2022) found spillovers from cash transfers",
                     "Egger et al. (2022) show spillovers from cash transfers"):
        result = _check(citation, "10.3982/ECTA17945", client)
        assert result["tier"] == "PLAUSIBLE"
    assert client.searches == []


@pytest.mark.parametrize("citation", [
    "**Brown, Salisbury & Ball (2025)**, *Evidence-based funding and the value of information*, AEA Papers and Proceedings 115",
    "Brown, Salisbury & Ball (2025) Evidence-based funding and the value of information. AEA Papers and Proceedings.",
    "Brown, Salisbury & Ball (2025) — Evidence-based funding and the value of information, AEA P&P.",
    "**Brown, Salisbury & Ball (2025)**. Evidence-based funding and the value of information.",
])
def test_brown_invented_title_variants_remain_title_wrong(citation):
    client = RecordedClient()
    result = _check(citation, BROWN_DOI, client)
    assert result["tier"] == "TITLE_WRONG"
    assert "TITLE_NOT_FOUND" in result["text_fidelity"]
    assert len(client.searches) == 2


@pytest.mark.parametrize("suffix", ["(pandp.20251068)", "`pandp.20251068`"])
def test_brown_venue_with_trailing_identifier_is_not_an_invented_title(suffix):
    result = _check(f"Brown, Salisbury & Ball (2025), AEA P&P {suffix}", BROWN_DOI, RecordedClient())
    assert result["tier"] == "PLAUSIBLE"
    assert "TITLE_NOT_FOUND" not in result["text_fidelity"]


@pytest.mark.parametrize("citation", [
    "Brown, Salisbury & Ball (2025): Evidence-based funding and the value of information.",
    "Brown, Salisbury & Ball (2025); Evidence-based funding and the value of information.",
    "__Brown, Salisbury & Ball (2025)__: _Evidence-based funding and the value of information_.",
])
def test_brown_colon_semicolon_and_underscore_emphasis(citation):
    result = _check(citation, BROWN_DOI, RecordedClient())
    assert result["tier"] == "TITLE_WRONG"


def test_parenthetical_venue_after_year_is_not_a_title():
    client = RecordedClient()
    result = _check("Meager (2019, AEJ: Applied)", MEAGER_DOI, client)
    assert result["tier"] == "PLAUSIBLE"
    assert client.searches == []


def test_doi_trims_markdown_without_losing_balanced_parentheses():
    doi = "10.1007/s10705-021-10174-1"
    assert clean_identifier(doi + "`**") == doi
    assert clean_identifier(doi + ")):**") == doi
    assert clean_identifier("10.1002/S0000(00)00000-0") == "10.1002/S0000(00)00000-0"


def test_adjacent_links_keep_their_own_doi_mentions():
    line = "* [Meager (2019)](https://doi.org/10.1257/app.20170299) & [Pritchett & Sandefur (2015)](https://doi.org/10.1257/aer.p20151069)"
    rows = extract(line)
    assert [(row["identifier"], row["citation"]) for row in rows] == [
        ("10.1257/app.20170299", "Meager (2019)"),
        ("10.1257/aer.p20151069", "Pritchett & Sandefur (2015)"),
    ]
    slide = """* [Meager (2019)](https://pubs.aeaweb.org/doi/10.1257/app.20170299) & [Vivalt (2020)](https://academic.oup.com/jeea/article/18/6/2782/5819777): Effect variance.
* [Pritchett & Sandefur (2015)](https://www.aeaweb.org/articles?id=10.1257/aer.p20151069): External estimates.
"""
    assert [(row["identifier"], row["citation"]) for row in extract(slide) if row["kind"] == "doi"] == [
        ("10.1257/app.20170299", "Meager (2019)"),
        ("10.1257/aer.p20151069", "Pritchett & Sandefur (2015)"),
    ]


def test_wrong_linked_work_stays_a_defect_with_bare_or_annotated_year():
    client = RecordedClient()
    doi = "10.1257/aer.p20151069"
    for citation in ("Pritchett & Sandefur (2015, AER)", "Pritchett & Sandefur 2015"):
        assert _check(citation, doi, client)["tier"] == "WRONG_WORK"
