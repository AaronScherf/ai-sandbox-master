"""Recorded OpenAlex and Crossref answers for the same-team guard."""
import json
import urllib.error
import urllib.parse

import pytest

from tools.reference_checker import RegistryClient, same_team_guard


def authors(*ids):
    return [{"author": {"id": "https://openalex.org/" + value}} for value in ids]


def oa_work(doi, title, year, *ids, kind="article"):
    return {"doi": "https://doi.org/" + doi, "title": title,
            "publication_year": year, "type": kind, "authorships": authors(*ids)}


def crossref_work(doi, title, names, year):
    return {"DOI": doi, "title": [title], "author": [{"family": name} for name in names],
            "issued": {"date-parts": [[year]]}, "type": "journal-article"}


class RecordedClient:
    def __init__(self, target, pages, crossref=None):
        self.target, self.pages, self.crossref = target, pages, crossref or []
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if "/works/doi:" in url:
            return self.target if isinstance(self.target, dict) else self.target
        if "api.openalex.org/works?" in url:
            cursor = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["cursor"][0]
            value = self.pages[cursor]
            if isinstance(value, Exception):
                raise value
            return {"status": 200, "data": value}
        if "api.crossref.org/works?" in url:
            if isinstance(self.crossref, Exception):
                raise self.crossref
            return {"status": 200, "data": {"message": {
                "total-results": len(self.crossref), "items": self.crossref}}}
        raise AssertionError(url)


def client(ids, works, *, total=None, crossref=None, target_status=200):
    target = {"status": target_status, "data": {"authorships": authors(*ids)}}
    return RecordedClient(target, {"*": {"meta": {"count": len(works) if total is None else total},
                                           "results": works}}, crossref)


@pytest.mark.parametrize("name,doi,target,other,other_title,team,year", [
    ("Groh", "10.1162/rest_a_00584",
     "Do Wage Subsidies Provide a Stepping-Stone to Employment for Recent College Graduates? Evidence from a Randomized Experiment in Jordan",
     "10.1186/s40172-015-0022-8",
     "Testing the importance of search frictions and matching through a randomized experiment in Jordan",
     ("A1", "A2", "A3", "A4"), 2016),
    ("Raleigh", "10.1016/j.gloenvcha.2015.03.005",
     "The devil is in the details: An investigation of the relationships between conflict, food price and climate across Africa",
     "10.1080/03050629.2017.1235271",
     "Conflict Dynamics and Feedback: Explaining Change in Violence against Civilians within Conflicts",
     ("A1", "A2"), 2015),
])
def test_live_false_pass_cases_now_find_openalex_siblings(name, doi, target, other, other_title, team, year):
    works = [oa_work(doi, target, year, *team),
             oa_work(other, other_title, year + 1, *team)]
    result = same_team_guard(doi, {"title": target, "authors": [name, "Coauthor"]},
                             year, client(team, works))
    assert result.complete and result.sibling_count == 1
    assert result.siblings[0]["doi"] == other


def test_groh_soft_skills_paper_is_distinct_despite_shared_title_boilerplate():
    doi = "10.1162/rest_a_00584"
    title = ("Do Wage Subsidies Provide a Stepping-Stone to Employment for Recent College Graduates? "
             "Evidence from a Randomized Experiment in Jordan")
    other = "10.1186/s40175-016-0055-9"
    works = [oa_work(doi, title, 2016, "A1", "A2", "A3", "A4"),
             oa_work(other, "The impact of soft skills training on female youth employment: "
                     "evidence from a randomized experiment in Jordan", 2016,
                     "A1", "A2", "A3", "A4")]
    result = same_team_guard(doi, {"title": title, "authors": ["Groh", "Krishnan", "McKenzie", "Vishwanath"]},
                             2016, client(("A1", "A2", "A3", "A4"), works))
    assert result.complete and result.sibling_count == 1
    assert result.siblings[0]["doi"] == other


def test_maystadt_version_and_missing_third_coauthor_id_do_not_block_pass():
    doi = "10.1093/ajae/aau010"
    title = "Extreme Weather and Civil War: Does Drought Fuel Conflict in Somalia through Livestock Price Shocks?"
    target = {"status": 200, "data": {"authorships": authors("A1", "A2") +
                                             [{"author": {"id": None}}]}}
    pages = {"*": {"meta": {"count": 2}, "results": [
        oa_work(doi, title, 2014, "A1", "A2"),
        oa_work("10.2139/ssrn.2228878", "Extreme Weather and Civil War in Somalia: "
                "Does Drought Fuel Conflict through Livestock Price Shocks?", 2013, "A1", "A2")]}}
    result = same_team_guard(doi, {"title": title, "authors": ["Maystadt", "Ecker", "Mabiso"]},
                             2014, RecordedClient(target, pages))
    assert result.complete and result.sibling_count == 0


def test_openalex_pages_until_meta_count_is_read():
    doi = "10.1000/target"
    target = {"status": 200, "data": {"authorships": authors("A1", "A2")}}
    filler = [oa_work(f"10.1000/filler-{i}", "Unrelated", 2020, "A3") for i in range(199)]
    pages = {"*": {"meta": {"count": 201, "next_cursor": "second"},
                   "results": [oa_work(doi, "Target", 2020, "A1", "A2")] + filler},
             "second": {"meta": {"count": 201}, "results": [
                 oa_work("10.1000/sibling", "Distinct", 2021, "A1", "A2")]}}
    recorded = RecordedClient(target, pages)
    result = same_team_guard(doi, {"title": "Target", "authors": ["Smith", "Jones"]}, 2020, recorded)
    assert result.complete and result.siblings[0]["doi"] == "10.1000/sibling"
    assert sum("api.openalex.org/works?" in url for url in recorded.urls) == 2


def test_openalex_missing_doi_first_id_over_limit_and_lookup_error_fail_closed():
    record = {"title": "Target", "authors": ["Smith", "Jones"]}
    missing = RecordedClient({"status": 404, "data": None}, {})
    assert not same_team_guard("10.1000/target", record, 2020, missing).complete
    no_id = client((), [])
    assert "first OpenAlex author ID missing" in same_team_guard("10.1000/target", record, 2020, no_id).reason
    too_many = client(("A1",), [], total=1001)
    assert "above 1000" in same_team_guard("10.1000/target", record, 2020, too_many).reason
    failed = RecordedClient({"status": 200, "data": {"authorships": authors("A1")}},
                            {"*": LookupError("not cached")})
    assert "not cached" in same_team_guard("10.1000/target", record, 2020, failed).reason


def test_crossref_only_sibling_counts_but_incomplete_crossref_does_not_block_pass():
    doi = "10.1000/target"
    record = {"title": "Target", "authors": ["Smith", "Jones"]}
    clean = [oa_work(doi, "Target", 2020, "A1", "A2")]
    sibling = crossref_work("10.1000/other", "Other project", ["Smith", "Jones"], 2021)
    found = same_team_guard(doi, record, 2020, client(("A1", "A2"), clean, crossref=[sibling]))
    assert found.complete and found.sibling_count == 1
    incomplete = same_team_guard(doi, record, 2020,
                                 client(("A1", "A2"), clean, crossref=LookupError("not cached")))
    assert incomplete.complete and incomplete.sibling_count == 0


def test_registry_client_paces_openalex_list_and_honors_retry_after(tmp_path, monkeypatch):
    sleeps = []
    requests = []

    class Reply:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"meta": {"count": 0}, "results": []}).encode()

    def fetch(request, timeout):
        requests.append(request.full_url)
        if len(requests) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "slow down",
                                         {"Retry-After": "7"}, None)
        return Reply()

    monkeypatch.setattr("tools.reference_checker.urllib.request.urlopen", fetch)
    monkeypatch.setattr("tools.reference_checker.time.sleep", sleeps.append)
    monkeypatch.setattr("tools.reference_checker.time.monotonic", lambda: 100.0)
    url = "https://api.openalex.org/works?filter=authorships.author.id:A1&cursor=%2A"
    assert RegistryClient(tmp_path, pace=0.2).get(url)["status"] == 200
    assert len(requests) == 2
    assert any(delay >= 7 for delay in sleeps)
    assert any(delay >= 1 for delay in sleeps)
