"""Recorded registry cases for the AUTHOR_YEAR tier."""
from tools.reference_checker import check, check_note


DOI = "10.1000/target"


class RecordedClient:
    def __init__(self, *, authors=("Smith", "Jones"), year=2020, registry="Crossref",
                 siblings=(), guard_error=None, incomplete=False):
        self.authors = authors
        self.year = year
        self.registry = registry
        self.siblings = siblings
        self.guard_error = guard_error
        self.incomplete = incomplete
        self.guard_queries = []

    def get(self, url):
        if "/doiRA/" in url:
            return {"data": [{"RA": self.registry}]}
        if "query.title=" in url:
            return {"status": 200, "data": {"message": {"items": []}}}
        if "query.author=" in url:
            self.guard_queries.append(url)
            if self.guard_error:
                raise self.guard_error
            items = [{"DOI": DOI, "title": ["A target study"],
                      "author": [{"family": author} for author in self.authors],
                      "issued": {"date-parts": [[self.year]]}, "type": "journal-article"}]
            items += list(self.siblings)
            total = 101 if self.incomplete else len(items)
            return {"status": 200, "data": {"message": {
                "items": items, "total-results": total}}}
        if "api.crossref.org/works/" in url:
            return {"status": 200, "data": {"message": {
                "DOI": DOI, "title": ["A target study"],
                "author": [{"family": author} for author in self.authors],
                "published": {"date-parts": [[self.year]]},
                "container-title": ["Journal"]}}}
        if "api.datacite.org/dois/" in url:
            return {"status": 200, "data": {"data": {"attributes": {
                "doi": DOI, "titles": [{"title": "A target study"}],
                "creators": [{"familyName": author} for author in self.authors],
                "publicationYear": self.year}}}}
        raise AssertionError(url)


def row(citation):
    return {"citation": citation, "identifier": DOI, "kind": "doi"}


def test_all_cited_authors_exact_year_no_siblings_passes():
    client = RecordedClient()
    result = check(row("Smith & Jones (2020)"), client)
    assert result["identity"] == "SAME_WORK"
    assert result["tier"] == "AUTHOR_YEAR"
    assert result["classification"] == "PARTIAL"  # legacy field unchanged
    assert "same-team guard found no sibling" in result["reason"]
    assert "siblings" not in result
    assert len(client.guard_queries) == 1


def test_same_team_sibling_stays_plausible_with_display_metadata():
    sibling = {"DOI": "10.1000/other", "title": ["A distinct paper"],
               "author": [{"family": "Smith"}, {"family": "Jones"}],
               "issued": {"date-parts": [[2021]]}, "type": "journal-article"}
    result = check(row("Smith & Jones (2020)"), RecordedClient(siblings=[sibling]))
    assert result["tier"] == "PLAUSIBLE"
    assert result["siblings"] == [{"doi": "10.1000/other", "title": "A distinct paper",
                                   "year": 2021, "type": "journal-article"}]
    assert "same team: 1 other work 2019 to 2021" in result["reason"]


def test_exact_year_and_complete_cited_author_list_are_required():
    year_client = RecordedClient(year=2020)
    year_result = check(row("Smith & Jones (2019)"), year_client)
    assert year_result["identity"] == "SAME_WORK"
    assert year_result["tier"] == "PLAUSIBLE"
    assert "cited year does not exactly match" in year_result["reason"]
    assert year_client.guard_queries == []

    author_client = RecordedClient()
    author_result = check(row("Smith & Wrong (2020)"), author_client)
    assert author_result["identity"] == "SAME_WORK"
    assert author_result["tier"] == "PLAUSIBLE"
    assert "cited surnames not all registered" in author_result["reason"]
    assert author_client.guard_queries == []


def test_et_al_requires_registered_first_author():
    good = check(row("Smith et al. (2020)"), RecordedClient())
    assert good["tier"] == "AUTHOR_YEAR"
    client = RecordedClient()
    wrong_first = check(row("Jones & Smith et al. (2020)"), client)
    assert wrong_first["identity"] == "SAME_WORK"
    assert wrong_first["tier"] == "PLAUSIBLE"
    assert "first author differs" in wrong_first["reason"]
    assert client.guard_queries == []


def test_datacite_incomplete_and_lookup_failure_stay_plausible():
    datacite = RecordedClient(registry="DataCite")
    result = check(row("Smith & Jones (2020)"), datacite)
    assert result["tier"] == "PLAUSIBLE"
    assert datacite.guard_queries == []
    incomplete = check(row("Smith & Jones (2020)"), RecordedClient(incomplete=True))
    assert incomplete["tier"] == "PLAUSIBLE"
    assert "guard incomplete" in incomplete["reason"]
    failed = check(row("Smith & Jones (2020)"), RecordedClient(guard_error=LookupError("not cached")))
    assert failed["tier"] == "PLAUSIBLE"
    assert "not cached" in failed["reason"]


def test_reference_list_linking_runs_before_author_year_guard():
    note = """# Note
| Citation | DOI |
|---|---|
| Smith & Jones (2020) | https://doi.org/10.1000/target |

## References
- Smith & Jones (2020). A target study.
"""
    client = RecordedClient()
    result = check_note(note, client)[0]
    assert result["tier"] == "CONFIRMED"
    assert result["evidence"] == "list_entry"
    assert client.guard_queries == []
