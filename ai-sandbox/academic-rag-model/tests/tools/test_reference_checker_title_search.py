"""Recorded answers for cited-title discovery before TITLE_WRONG routing."""
import urllib.parse

import pytest

from tools import reference_review as ledger
from tools.reference_checker import TIER_RANK, check, search_cited_title, similarity


RECORDS = {
    "10.1093/restud/rdz021": ("Rosenzweig", "Udry", 2020,
        "External Validity in a Stochastic World: Evidence from Low-Income Countries"),
    "10.1016/j.wace.2018.03.006": ("Lopez", "Coughlan de Perez", 2020,
        "Bridging forecast verification and humanitarian decisions: A valuation approach for setting up action-oriented early warnings"),
}


class RecordedClient:
    def __init__(self, *, crossref=(), openalex=()):
        self.crossref, self.openalex = crossref, openalex
        self.search_urls = []

    def get(self, url):
        if "/doiRA/" in url:
            return {"data": [{"RA": "Crossref"}]}
        if url.startswith("https://api.crossref.org/works/"):
            doi = urllib.parse.unquote(url.split("/works/", 1)[1])
            first, second, year, title = RECORDS[doi]
            return {"status": 200, "data": {"message": {
                "DOI": doi, "title": [title],
                "author": [{"family": first}, {"family": second}],
                "issued": {"date-parts": [[year]]}, "container-title": ["Journal"]}}}
        if "query.bibliographic=" in url:
            self.search_urls.append(url)
            if isinstance(self.crossref, Exception):
                raise self.crossref
            return {"status": 200, "data": {"message": {"items": list(self.crossref)}}}
        if "api.openalex.org/works?search=" in url:
            self.search_urls.append(url)
            if isinstance(self.openalex, Exception):
                raise self.openalex
            return {"status": 200, "data": {"results": list(self.openalex)}}
        raise AssertionError(url)


@pytest.mark.parametrize("citation,doi", [
    ("Rosenzweig, M. R., & Udry, C. (2020). External validity, information and prices: Methods and results from investments in Indian agriculture.",
     "10.1093/restud/rdz021"),
    ("Lopez, A., Coughlan de Perez, E., Bazo, J., Suarez, P., et al. (2020). Bridging the gap between climate science and humanitarian action: An analysis of forecast-based financing in Peru.",
     "10.1016/j.wace.2018.03.006"),
])
def test_low_scoring_invented_titles_have_complete_empty_search(citation, doi):
    client = RecordedClient()
    result = check({"citation": citation, "identifier": doi, "kind": "doi"}, client)
    assert result["identity"] == "SAME_WORK"
    assert result["tier"] == "TITLE_WRONG"
    assert "TITLE_NOT_FOUND" in result["text_fidelity"]
    assert result["registry_title"] == RECORDS[doi][3]
    assert "cited title not found in Crossref or OpenAlex" in result["reason"]
    assert len(client.search_urls) == 2
    result["line"] = 9
    queued, defects = ledger._selected("research/note.md", [result], set())
    assert queued == []
    assert len(defects) == 1
    assert defects[0]["tier"] == "TITLE_WRONG"
    assert defects[0]["registry_title"] == RECORDS[doi][3]
    assert TIER_RANK["REVIEW"] < TIER_RANK["TITLE_WRONG"] < TIER_RANK["NOT_FOUND"]
    crossref_query = urllib.parse.parse_qs(urllib.parse.urlsplit(client.search_urls[0]).query)
    assert crossref_query["rows"] == ["5"]
    assert crossref_query["select"] == ["DOI,title,author,issued"]
    assert crossref_query["query.author"] == (["lopez perez bazo suarez"] if doi.startswith("10.1016")
                                             else ["rosenzweig udry"])


def test_other_low_scoring_aer_work_stays_review_with_found_title():
    title = "Rainfall Forecasts, Weather, and Wages over the Agricultural Production Cycle"
    client = RecordedClient(crossref=[{"DOI": "10.1257/aer.104.5.278", "title": [title],
                                      "issued": {"date-parts": [[2014]]}}])
    citation = "Rosenzweig & Udry (2014). " + title
    result = check({"citation": citation, "identifier": "10.1093/restud/rdz021", "kind": "doi"}, client)
    assert similarity(title, RECORDS["10.1093/restud/rdz021"][3]) < 0.5
    assert result["identity"] == "SAME_WORK"
    assert result["tier"] == "REVIEW"
    assert result["cited_title_found"] == {
        "doi": "10.1257/aer.104.5.278", "title": title, "year": 2014, "source": "Crossref"}
    assert "TITLE_NOT_FOUND" not in result["text_fidelity"]
    assert len(client.search_urls) == 2
    result["line"] = 4
    queued, defects = ledger._selected("research/note.md", [result], set())
    assert defects == []
    assert len(queued) == 1
    assert queued[0].candidates[0]["cited_title_found"] == result["cited_title_found"]


def test_openalex_alone_can_supply_a_matching_title():
    title = "An entirely different work"
    client = RecordedClient(openalex=[{"doi": "https://doi.org/10.1000/other",
                                       "title": title, "publication_year": 2020,
                                       "authorships": []}])
    found, complete = search_cited_title("Rosenzweig & Udry (2020). " + title, client)
    assert complete
    assert found == {"doi": "10.1000/other", "title": title, "year": 2020,
                     "source": "OpenAlex"}


@pytest.mark.parametrize("failure_source", ["Crossref", "OpenAlex"])
def test_lookup_failure_keeps_review_and_reports_unavailable(failure_source):
    kwargs = {failure_source.lower(): LookupError("not cached")}
    client = RecordedClient(**kwargs)
    citation = ("Rosenzweig & Udry (2020). External validity, information and prices: "
                "Methods and results from investments in Indian agriculture.")
    result = check({"citation": citation, "identifier": "10.1093/restud/rdz021", "kind": "doi"}, client)
    assert result["tier"] == "REVIEW"
    assert "title search unavailable" in result["reason"]
    assert "TITLE_NOT_FOUND" not in result["text_fidelity"]
    assert len(client.search_urls) == 2


def test_title_search_skips_high_scoring_and_titleless_rows():
    client = RecordedClient()
    doi = "10.1093/restud/rdz021"
    title = RECORDS[doi][3]
    for citation in ("Rosenzweig & Udry (2020). " + title, "Rosenzweig & Udry (2020)"):
        check({"citation": citation, "identifier": doi, "kind": "doi"}, client, author_year=False)
    assert client.search_urls == []
    assert similarity("External Validity in a Stochastic World", title) > 0.5
