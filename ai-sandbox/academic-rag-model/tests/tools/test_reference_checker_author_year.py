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
        if "api.openalex.org/works/doi:" in url:
            return {"status": 200, "data": {"authorships": [
                {"author": {"id": f"https://openalex.org/A{i + 1}"}}
                for i in range(len(self.authors))]}}
        if "api.openalex.org/works?" in url:
            self.guard_queries.append(url)
            if self.guard_error:
                raise self.guard_error
            target = {"doi": "https://doi.org/" + DOI, "title": "A target study",
                      "publication_year": self.year, "type": "article",
                      "authorships": [{"author": {"id": f"https://openalex.org/A{i + 1}"}}
                                      for i in range(len(self.authors))]}
            return {"status": 200, "data": {"meta": {"count": 201 if self.incomplete else 1},
                                              "results": [target]}}
        if "query.author=" in url:
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
    assert "author/year agreement" in result["reason"]
    assert "siblings" not in result
    assert len(client.guard_queries) == 1


def test_same_team_sibling_passes_with_display_metadata():
    sibling = {"DOI": "10.1000/other", "title": ["A distinct paper"],
               "author": [{"family": "Smith"}, {"family": "Jones"}],
               "issued": {"date-parts": [[2021]]}, "type": "journal-article"}
    result = check(row("Smith & Jones (2020)"), RecordedClient(siblings=[sibling]))
    assert result["tier"] == "AUTHOR_YEAR"
    assert result["siblings"] == [{"doi": "10.1000/other", "title": "A distinct paper",
                                   "year": 2021, "type": "journal-article"}]
    assert "author/year agreement" in result["reason"]


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


def test_datacite_and_incomplete_sibling_lookup_pass():
    datacite = RecordedClient(registry="DataCite")
    result = check(row("Smith & Jones (2020)"), datacite)
    assert result["tier"] == "AUTHOR_YEAR"
    assert datacite.guard_queries == []
    incomplete = check(row("Smith & Jones (2020)"), RecordedClient(incomplete=True))
    assert incomplete["tier"] == "AUTHOR_YEAR"
    failed = check(row("Smith & Jones (2020)"), RecordedClient(guard_error=LookupError("not cached")))
    assert failed["tier"] == "AUTHOR_YEAR"


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


def test_matching_venue_volume_pages_pass_and_wrong_volume_stays_open():
    class Client(RecordedClient):
        def get(self, url):
            answer = super().get(url)
            if "api.crossref.org/works/" in url and "?" not in url:
                answer["data"]["message"].update(
                    {"container-title": ["American Economic Review"], "volume": "107", "page": "1165-1206"})
            return answer

    good = check(row("Smith & Jones (2020). American Economic Review, 107(4), 1165-1206"), Client())
    assert good["tier"] == "AUTHOR_YEAR"
    assert "venue, volume, pages agree" in good["reason"]
    bad = check(row("Smith & Jones (2020). American Economic Review, 108(4), 1165-1206"), Client())
    assert bad["tier"] == "PLAUSIBLE"
    assert "VOLUME_DIFFERS" in bad["text_fidelity"]


def test_descriptive_link_needs_two_content_words():
    class Client(RecordedClient):
        def get(self, url):
            answer = super().get(url)
            if "api.crossref.org/works/" in url and "?" not in url:
                answer["data"]["message"]["title"] = ["Cash and Food Transfers in Yemen"]
            return answer

    assert check({**row("Yemen, cash versus food in a crisis"), "descriptive_link": True}, Client())["tier"] == "DESCRIBED"
    assert check({**row("Springer chapter 14"), "descriptive_link": True}, Client())["tier"] == "UNCHECKED"
    assert check(row("Yemen, cash versus food in a crisis"), Client())["tier"] == "UNCHECKED"
    note = "# References\n- [Yemen cash versus food](https://doi.org/10.1000/target)\n"
    assert check_note(note, Client())[0]["tier"] == "DESCRIBED"


def test_table_br_title_and_quoted_field_title_are_read():
    class Client(RecordedClient):
        def get(self, url):
            answer = super().get(url)
            if "api.crossref.org/works/" in url and "?" not in url:
                answer["data"]["message"]["title"] = ["A target study"]
            return answer

    table = "# References\n| Citation | DOI |\n|---|---|\n| **Smith & Jones (2020)**<br>*A target study*, *Journal* | https://doi.org/10.1000/target |"
    assert check_note(table, Client())[0]["tier"] == "CONFIRMED"
    quoted = check(row("Smith & Jones (2020). 'A target study'. Journal"), Client())
    assert quoted["tier"] == "CONFIRMED"


def test_same_year_sibling_with_better_venue_stays_in_review(monkeypatch):
    from tools import reference_checker as checker

    class Client(RecordedClient):
        def get(self, url):
            answer = super().get(url)
            if "api.crossref.org/works/" in url and "?" not in url:
                answer["data"]["message"]["container-title"] = ["Target Journal"]
            return answer

    sibling = {"doi": "10.1000/other", "title": "A different study", "year": 2020,
               "venue": "Other Journal", "type": "article"}
    monkeypatch.setattr(checker, "same_team_guard", lambda *args: checker.SameTeamGuardResult(True, [sibling], 1))
    result = check(row("Smith & Jones (2020). Other Journal, 10, 1-4"), Client())
    assert result["tier"] == "REVIEW"
    assert "cited venue/year match a different work by the same team" in result["reason"]
    assert result["siblings"] == [sibling]


def test_initials_and_italic_venue_are_author_year_evidence():
    class Client(RecordedClient):
        def get(self, url):
            answer = super().get(url)
            if "api.crossref.org/works/" in url and "?" not in url:
                answer["data"]["message"]["container-title"] = ["Scientific Reports"]
            return answer

    note = "# References\n- Smith J et al. (2020). *Scientific Reports*. doi:10.1000/target\n"
    result = check_note(note, Client())[0]
    assert result["tier"] == "AUTHOR_YEAR"
    assert "venue agree" in result["reason"]
