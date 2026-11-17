"""Recorded Crossref answers for the title-less same-team guard."""
import json
import urllib.error
import urllib.parse

from tools.reference_checker import RegistryClient, same_team_guard


def work(doi, title, authors, year=2008, kind="journal-article"):
    return {"DOI": doi, "title": [title], "author": [{"family": name} for name in authors],
            "issued": {"date-parts": [[year]]}, "type": kind}


class RecordedClient:
    def __init__(self, pages):
        self.pages = pages
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        cursor = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["cursor"][0]
        value = self.pages[cursor]
        if isinstance(value, Exception):
            raise value
        return {"status": 200, "data": {"message": value}}


def page(items, total=None, next_cursor=None):
    return {"items": items, "total-results": len(items) if total is None else total,
            "next-cursor": next_cursor}


def test_guard_query_shape_and_brok_same_team_sibling():
    record = {"title": "Trial sequential analysis", "authors": ["Brok", "Thorlund", "Wetterslev", "Gluud", "Extra"]}
    sibling = work("10.1000/other", "A different clinical review", ["Brok", "Thorlund"], 2009)
    client = RecordedClient({"*": page([
        work("10.1093/ije/dyn188", "Trial sequential analysis", record["authors"]), sibling])})
    result = same_team_guard("10.1093/ije/dyn188", record, 2008, client)
    assert result.complete and result.sibling_count == 1
    assert result.siblings == [{"doi": "10.1000/other", "title": "A different clinical review",
                                "year": 2009, "type": "journal-article"}]
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(client.urls[0]).query)
    assert params == {"query.author": ["Brok Thorlund Wetterslev Gluud"],
                      "filter": ["from-pub-date:2007-01-01,until-pub-date:2009-12-31"],
                      "rows": ["100"], "select": ["DOI,title,author,issued,type"], "cursor": ["*"]}


def test_guard_ignores_same_project_versions_unrelated_people_and_excluded_types():
    record = {"title": "Extreme Weather and Civil War in Somalia", "authors": ["Maystadt", "Ecker"]}
    client = RecordedClient({"*": page([
        work("10.1000/preprint", "Extreme Weather and Civil War in Somalia: Evidence", ["Maystadt", "Ecker"]),
        work("10.1000/other-hjort", "Unrelated paper", ["Maystadt", "Someone"]),
        work("10.1000/data", "Different data", ["Maystadt", "Ecker"], kind="dataset"),
    ])})
    result = same_team_guard("10.1093/ajae/aau010", record, 2014, client)
    assert result.complete and result.sibling_count == 0 and result.siblings == []


def test_guard_single_author_other_work_is_sibling_and_caps_display_at_five():
    record = {"title": "The target study", "authors": ["Allcott"]}
    candidates = [work(f"10.1000/other-{i}", f"Distinct work {i}", ["Allcott"], 2015)
                  for i in range(7)]
    result = same_team_guard("10.1000/target", record, 2015,
                             RecordedClient({"*": page(candidates)}))
    assert result.complete and result.sibling_count == 7
    assert len(result.siblings) == 5


def test_guard_ignores_hjort_surname_noise_without_shared_coauthor():
    record = {"title": "The target study", "authors": ["Hjort", "Miller"]}
    unrelated = work("10.1000/other", "A different study", ["Hjort", "Someone Else"], 2021)
    result = same_team_guard("10.1000/target", record, 2021,
                             RecordedClient({"*": page([unrelated])}))
    assert result.complete and result.sibling_count == 0


def test_guard_pages_when_first_author_continues_near_page_end():
    record = {"title": "The target study", "authors": ["Brok", "Thorlund"]}
    fillers = [work(f"10.1000/filler-{i}", "Unrelated", ["Other"], 2008) for i in range(99)]
    first_page = fillers + [work("10.1000/target", "The target study", ["Brok", "Thorlund"])]
    client = RecordedClient({"*": page(first_page, total=101, next_cursor="second"),
                             "second": page([work("10.1000/sibling", "A separate work", ["Brok", "Thorlund"])],
                                            total=101)})
    result = same_team_guard("10.1000/target", record, 2008, client)
    assert result.complete and result.sibling_count == 1
    assert [urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["cursor"][0]
            for url in client.urls] == ["*", "second"]


def test_guard_fails_closed_on_page_limit_missing_cursor_and_lookup_error(tmp_path):
    record = {"title": "The target study", "authors": ["Brok", "Thorlund"]}
    full = [work(f"10.1000/other-{i}", "Different study", ["Brok", "Thorlund"])
            for i in range(100)]
    client = RecordedClient({"*": page(full, total=400, next_cursor="two"),
                             "two": page(full, total=400, next_cursor="three"),
                             "three": page(full, total=400, next_cursor="four")})
    result = same_team_guard("10.1000/target", record, 2008, client)
    assert not result.complete and result.reason == "three-page limit reached"
    assert len(client.urls) == 3
    missing = same_team_guard("10.1000/target", record, 2008,
                              RecordedClient({"*": page(full, total=101)}))
    assert not missing.complete and missing.reason == "cursor unavailable"
    failed = same_team_guard("10.1000/target", record, 2008,
                             RecordedClient({"*": LookupError("not cached")}))
    assert not failed.complete and "lookup unavailable" in failed.reason
    offline = same_team_guard("10.1000/target", record, 2008,
                              RegistryClient(tmp_path / "cache", online=False))
    assert not offline.complete and "not cached" in offline.reason


def test_guard_stops_after_page_without_first_author_near_end():
    record = {"title": "The target study", "authors": ["Hjort", "Smith"]}
    items = [work("10.1000/target", "The target study", ["Hjort", "Smith"])]
    items += [work(f"10.1000/noise-{i}", "Unrelated study", ["Other", "Smith"])
              for i in range(99)]
    client = RecordedClient({"*": page(items, total=200, next_cursor="second")})
    result = same_team_guard("10.1000/target", record, 2021, client)
    assert result.complete and result.sibling_count == 0
    assert len(client.urls) == 1


def test_guard_fails_closed_on_malformed_crossref_answer():
    record = {"title": "The target study", "authors": ["Brok", "Thorlund"]}
    malformed = work("10.1000/other", "Different study", ["Brok", "Thorlund"])
    malformed["author"] = "Brok and Thorlund"
    result = same_team_guard("10.1000/target", record, 2008,
                             RecordedClient({"*": page([malformed])}))
    assert not result.complete and "incomplete" in result.reason


def test_registry_client_paces_guard_search_and_honors_retry_after(tmp_path, monkeypatch):
    sleeps = []
    requests = []

    class Reply:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"message": page([])}).encode()

    def fetch(request, timeout):
        requests.append(request.full_url)
        if len(requests) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "slow down",
                                         {"Retry-After": "7"}, None)
        return Reply()

    monkeypatch.setattr("tools.reference_checker.urllib.request.urlopen", fetch)
    monkeypatch.setattr("tools.reference_checker.time.sleep", sleeps.append)
    monkeypatch.setattr("tools.reference_checker.time.monotonic", lambda: 100.0)
    url = "https://api.crossref.org/works?query.author=Brok&rows=100&cursor=%2A"
    assert RegistryClient(tmp_path, pace=0.2).get(url)["status"] == 200
    assert len(requests) == 2
    assert any(delay >= 7 for delay in sleeps)
    assert any(delay >= 1 for delay in sleeps)
