from agent.literature.profile.metadata import parse_crossref_message, title_match, verify_bibliography

REC = {"title": "The Effect of Network Adoption Subsidies", "authors": ["Dan Bjorkegren", "Burak Karaca"],
       "year": 2022, "journal": "Journal of Development Economics", "doi": "10.1016/j.jdeveco.2021.102762"}


def _lookup(record):
    calls = []

    def lookup(doi):
        calls.append(doi)
        return record
    lookup.calls = calls
    return lookup


def test_matching_record_marks_match():
    out = verify_bibliography({"title": "The effect of network adoption subsidies.", "doi": "10.1016/J.JDEVECO.2021.102762"},
                              _lookup(REC))
    assert out["doi_verified"]["match"] == "match"
    assert out["mismatches"] == []


def test_title_mismatch_is_flagged_not_overwritten():
    out = verify_bibliography({"title": "Something Else Entirely", "doi": "10.1016/j.jdeveco.2021.102762"}, _lookup(REC))
    assert out["doi_verified"]["match"] == "mismatch"
    assert "title" in out["mismatches"][0]
    assert "title" not in out["fields"]


def test_no_doi_gives_unverified_without_calling_lookup():
    lookup = _lookup(REC)
    out = verify_bibliography({"title": "X"}, lookup)
    assert out["doi_verified"]["match"] == "unverified"
    assert lookup.calls == []


def test_lookup_returning_none_gives_unverified():
    out = verify_bibliography({"title": "X", "doi": "10.1/none"}, _lookup(None))
    assert out["doi_verified"]["match"] == "unverified"


def test_fields_filled_from_lookup_only_when_card_lacks_them():
    card = {"title": "The effect of network adoption subsidies", "doi": REC["doi"], "publication_year": 2021}
    out = verify_bibliography(card, _lookup(REC))
    assert out["fields"]["authors"] == REC["authors"]
    assert out["fields"]["journal"] == REC["journal"]
    assert "publication_year" not in out["fields"]


def test_title_match_ignores_case_punctuation_whitespace():
    assert title_match("Cash  Transfers: A Review!", "cash transfers a review")
    assert not title_match("Cash transfers", "Microcredit in Kenya")


def test_parse_crossref_message():
    msg = {"title": ["A Title"], "author": [{"given": "Ana", "family": "Diaz"}, {"name": "Org Team"}],
           "issued": {"date-parts": [[2020, 5]]}, "container-title": ["Some Journal"], "DOI": "10.1/ABC"}
    assert parse_crossref_message(msg) == {"title": "A Title", "authors": ["Ana Diaz", "Org Team"], "year": 2020,
                                           "journal": "Some Journal", "doi": "10.1/abc"}


def test_parse_openalex_topics_keeps_score_field_subfield():
    from agent.literature.profile.metadata import parse_openalex_topics
    work = {"topics": [
        {"id": "https://openalex.org/T1", "display_name": "Cash transfers", "score": 0.97,
         "subfield": {"id": "https://openalex.org/subfields/2002", "display_name": "Economics and Econometrics"},
         "field": {"id": "https://openalex.org/fields/20", "display_name": "Economics, Econometrics and Finance"},
         "domain": {"id": "https://openalex.org/domains/2", "display_name": "Social Sciences"}},
        {"id": "https://openalex.org/T2", "display_name": "Orphan", "score": 0.1}]}
    assert parse_openalex_topics(work) == [
        {"id": "T1", "name": "Cash transfers", "score": 0.97, "field_id": "20", "subfield_id": "2002", "domain_id": "2"},
        {"id": "T2", "name": "Orphan", "score": 0.1, "field_id": None, "subfield_id": None, "domain_id": None}]


def test_parse_openalex_work_carries_the_work_id_and_topics():
    from agent.literature.profile.metadata import parse_openalex_work
    work = {"id": "https://openalex.org/W123", "title": "T", "doi": "https://doi.org/10.1/X", "publication_year": 2020,
            "topics": [{"id": "https://openalex.org/T1", "display_name": "Cash", "score": 0.9,
                        "field": {"id": "https://openalex.org/fields/20"}}]}
    record = parse_openalex_work(work)
    assert record["openalex_id"] == "W123" and record["topics"][0]["id"] == "T1" and record["topics"][0]["score"] == 0.9


def test_title_match_accepts_a_title_missing_only_its_subtitle():
    from agent.literature.profile.metadata import title_match
    full = ("Dry farming techniques for the enhancement of climate-smart agriculture in drought-prone landscapes: "
            "implication for smallholder farmers adaptation and resilience to climate change")
    short = "Dry farming techniques for the enhancement of climate-smart agriculture in drought-prone landscapes"
    assert title_match(short, full) and title_match(full, short)


def test_title_prefix_rule_does_not_accept_short_or_unrelated_prefixes():
    from agent.literature.profile.metadata import title_match
    assert not title_match("Climate change", "Climate change and conflict: evidence from Somalia")
    assert not title_match("Risk transfer policies facilitate smallholder farmer climate adaptation",
                           "Risk transfer policies and climate-induced immobility among smallholder farmers")
