import json
import os
import hashlib
import io
import time
import urllib.error
import urllib.parse
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from tools.reference_checker import RegistryClient, check, clean_identifier, coverage, extract, load_references, markdown, registry_record, similarity


FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "reference_checker.json").read_text(encoding="utf-8"))
V2_FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "reference_checker_v2.json").read_text(encoding="utf-8"))
V2_REFERENCES = json.loads((Path(__file__).parent / "fixtures" / "reference_checker_v2_references.json").read_text(encoding="utf-8"))


class RecordedClient:
    def get(self, url):
        from urllib.parse import unquote
        doi = unquote(url.rsplit("/", 1)[1])
        row = V2_FIXTURES[doi]
        if "/doiRA/" in url:
            return row["agency"]
        if "api.crossref.org" in url:
            answer = row["answer"]
            return {"status": 200, "data": {"message": answer["data"]}} if row["registry"] == "Crossref" and answer["status"] == 200 else {"status": 404, "data": None}
        if "api.datacite.org" in url:
            answer = row["answer"]
            return {"status": 200, "data": {"data": {"attributes": answer["data"]}}} if row["registry"] == "DataCite" and answer["status"] == 200 else {"status": 404, "data": None}
        raise AssertionError(url)


class FixtureClient:
    """Offline responses in the two registry API shapes."""

    def get(self, url):
        if "/doiRA/" in url:
            from urllib.parse import unquote
            doi = unquote(url.split("/doiRA/", 1)[1])
            row = FIXTURES.get(doi)
            return {"status": 200, "data": [{"RA": row["agency"]}] if row else []}
        if "api.crossref.org/works/" in url:
            from urllib.parse import unquote
            row = FIXTURES[unquote(url.split("/works/", 1)[1])]
            return {"status": 200, "data": {"message": {"title": [row["title"]],
                "author": [{"family": row["author"]}], "published": {"date-parts": [[row["year"]]]},
                "container-title": [row["venue"]]}}}
        if "api.datacite.org/dois/" in url:
            from urllib.parse import unquote
            row = FIXTURES[unquote(url.split("/dois/", 1)[1])]
            return {"status": 200, "data": {"data": {"attributes": {"titles": [{"title": row["title"]}],
                "creators": [{"familyName": row["author"]}], "publicationYear": row["year"]}}}}
        if "query.title" in url:
            return {"status": 200, "data": {"message": {"items": [
                {"title": ["Candidate title"], "DOI": "10.1/candidate"}]}}}
        raise AssertionError(url)


def test_wiley_sici_preserves_balanced_parentheses_and_angle_brackets():
    doi = "10.1002/(SICI)1099-1050(199906)8:4<341::AID-HEC449>3.0.CO;2-9"
    assert clean_identifier(doi + ").") == doi
    assert extract(f"* [Claxton (1999)](https://doi.org/{doi})")[0]["identifier"] == doi


def test_regression_wrong_and_correct_dois():
    client = FixtureClient()
    for citation, doi in [("Vivalt (2020)", "10.1093/jeea/jvz054"),
                          ("Pritchett & Sandefur (2015)", "10.1257/aer.p20151034")]:
        result = check({"citation": citation, "identifier": doi, "kind": "doi"}, client)
        assert result["classification"] == "MISMATCH"
        assert result["identity"] == "WRONG_WORK"
    result = check({"citation": "Hjort et al. (2021)", "identifier": "10.1257/aer.20190830", "kind": "doi"}, client)
    assert result["classification"] == "PARTIAL"  # no explicit title in the note
    assert "NO_TITLE" in result["text_fidelity"]


def test_full_title_can_earn_match():
    row = {"citation": "Hjort (2021). How Research Affects Policy: Experimental Evidence from 2,150 Brazilian Municipalities", "identifier": "10.1257/aer.20190830", "kind": "doi"}
    assert check(row, FixtureClient())["classification"] == "MATCH"


def test_arxiv_uses_datacite():
    row = {"citation": "Montiel Olea (2023)", "identifier": "2307.03901", "kind": "arxiv"}
    result = check(row, FixtureClient())
    assert result["registry_answer"]["registry"] == "DataCite"
    assert result["classification"] == "MISMATCH"


def test_no_identifier_candidates_are_suggestions_and_url_is_not_verified():
    client = FixtureClient()
    no_id = check({"citation": "Someone (2020). A Candidate Title", "identifier": "", "kind": ""}, client)
    assert no_id["classification"] == "NO_IDENTIFIER"
    assert no_id["registry_answer"]["candidates"]
    url = check({"citation": "Someone (2020)", "identifier": "https://example.org/paper", "kind": "url"}, client)
    assert url["classification"] == "NO_IDENTIFIER"
    assert url["registry_answer"]["candidates"]
    assert "VERIFIED" not in markdown([url])


def test_markdown_note_extracts_reference_bullets_only(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Notes\nSome claim from 2020 is discussed.\n* [Hjort et al. (2021)](https://doi.org/10.1257/aer.20190830)\n  *Hjort (2021). How Research Affects Policy: Experimental Evidence from 2,150 Brazilian Municipalities.*\n", encoding="utf-8")
    rows = load_references(path)
    assert len(rows) == 1
    assert rows[0]["identifier"] == "10.1257/aer.20190830"
    assert check(rows[0], FixtureClient())["classification"] == "MATCH"


def test_table_prefers_author_year_citation_over_year_in_claim():
    text = "| Citation | Claim | DOI |\n|---|---|---|\n| Abushama et al. (2023) | Economywide CGE modeling of Sudan 2023 conflict disruptions | 10.2499/p15738coll2.137021 |"
    rows = extract(text)
    assert rows[0]["citation"].startswith("Abushama et al. (2023)")


def test_author_year_followed_by_journal_is_not_a_title():
    from tools.reference_checker import citation_fields
    assert citation_fields("Thalheimer et al. (2023), *Global Environmental Change*")["title"] == ""


def test_table_binds_each_identifier_to_its_nearest_author_year():
    text = "| Reference | Dataset | Paper |\n|---|---|---|\n| Hjort (2021) [dataset](https://doi.org/10.5555/data) [paper](https://doi.org/10.5555/paper) | | |"
    found = extract(text)
    assert [row["identifier"] for row in found] == ["10.5555/data", "10.5555/paper"]
    assert all("Hjort (2021)" in row["citation"] for row in found)


def test_memo_ground_truth_counts_from_recorded_registry_results():
    from tools.reference_checker import identity_counts
    rows = []
    for i in range(4):
        rows.extend([{"identity": "SAME_WORK", "identifier": f"10.5555/good{i}", "kind": "doi"}] * 2)
    for i, repeats in enumerate((2, 2, 2, 1, 1)):
        rows.extend([{"identity": "WRONG_WORK", "identifier": f"10.5555/wrong{i}", "kind": "doi"}] * repeats)
    rows += [{"identity": "UNCHECKED", "identifier": "https://example.org", "kind": "url"}] * 2
    counts = identity_counts(rows)
    assert counts["mentions"] == {"SAME_WORK": 8, "WRONG_WORK": 8, "UNCHECKED": 2}
    assert counts["distinct_dois"] == {"SAME_WORK": 4, "WRONG_WORK": 5}
    repeated = [{"identity": "SAME_WORK", "identifier": "10.5555/reused", "kind": "doi"},
                {"identity": "WRONG_WORK", "identifier": "10.5555/reused", "kind": "doi"}]
    assert identity_counts(repeated)["distinct_dois"] == {"WRONG_WORK": 1}


def test_memo_doi_ground_truth_against_recorded_raw_registry_answers():
    raw = json.loads((Path(__file__).parent / "fixtures/reference_checker_memo_registry_raw.json").read_text(encoding="utf-8"))
    class MemoRecordedClient:
        def get(self, url):
            for doi, endpoints in raw.items():
                encoded = urllib.parse.quote(doi, safe="")
                if url.endswith("doiRA/" + encoded): return endpoints["agency"]
                if url.endswith("/works/" + encoded): return endpoints["crossref"]
            raise AssertionError(url)
    expected = {
        "10.1016/j.jenvman.2012.03.046": ("Marchiori, Maystadt, & Schumacher (2012)", "WRONG_WORK"),
        "10.1086/709977": ("McGuirk & Burke (2020)", "WRONG_WORK"),
        "10.1088/1748-9326/ad13b8": ("Flores (2024)", "WRONG_WORK"),
        "10.1214/24-AOAS1921": ("Zens & Thalheimer (2025)", "WRONG_WORK"),
        "10.2499/p15738coll2.137021": ("Abushama, Resnick, Siddig, & Kirui (2023)", "WRONG_WORK"),
        "10.1016/j.gloenvcha.2023.102641": ("Thalheimer, Schwarz, & Pretis (2023)", "SAME_WORK"),
        "10.1093/ajae/aau010": ("Maystadt & Ecker (2014)", "SAME_WORK"),
        "10.1162/rest_a_00730": ("Harari & La Ferrara (2018)", "SAME_WORK"),
        "10.1016/j.gloenvcha.2015.03.005": ("Raleigh, Choi, & Kniveton (2015)", "SAME_WORK"),
    }
    for doi, (citation, identity) in expected.items():
        result = check({"citation": citation, "identifier": doi, "kind": "doi"}, MemoRecordedClient())
        assert result["identity"] == identity, (doi, result)
        if identity == "WRONG_WORK": assert result["classification"] == "MISMATCH"
        else: assert result["text_fidelity"] == ["NO_TITLE"]


def test_plain_text_and_json_inputs_include_identifier_free_citations(tmp_path):
    plain = tmp_path / "references.txt"
    plain.write_text("Hjort (2021). How Research Affects Policy\nSomeone (2020). Another Paper Title\n", encoding="utf-8")
    assert [row["kind"] for row in load_references(plain)] == ["", ""]
    structured = tmp_path / "references.json"
    structured.write_text(json.dumps([{"citation": "Hjort (2021)", "doi": "10.1257/aer.20190830"},
                                      "Someone (2020). Another Paper Title"]), encoding="utf-8")
    assert [row["kind"] for row in load_references(structured)] == ["doi", ""]


def test_registry_cache_works_offline(tmp_path):
    url = "https://doi.org/doiRA/10.1257%2Faer.20190830"
    cache = tmp_path / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    cache.write_text('{"status": 200, "data": [{"RA": "Crossref"}]}', encoding="utf-8")
    assert RegistryClient(tmp_path, online=False).get(url)["data"][0]["RA"] == "Crossref"


def test_corrupt_cache_is_a_miss_offline_and_heals_online(tmp_path, monkeypatch):
    url = "https://doi.org/doiRA/10.1257%2Faer.20190830"
    cache = tmp_path / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    cache.write_text("{broken", encoding="utf-8")
    with pytest.raises(LookupError):
        RegistryClient(tmp_path, online=False).get(url)

    class Reply:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'[{"RA":"Crossref"}]'

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Reply())
    assert RegistryClient(tmp_path, pace=0).get(url)["data"][0]["RA"] == "Crossref"
    assert json.loads(cache.read_text(encoding="utf-8"))["status"] == 200


def test_retry_after_rate_limit(tmp_path, monkeypatch):
    attempts = []

    class Reply:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'[{"RA":"Crossref"}]'

    def fetch(request, timeout):
        attempts.append(request.full_url)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "rate limited", None, None)
        return Reply()

    monkeypatch.setattr("urllib.request.urlopen", fetch)
    monkeypatch.setattr("tools.reference_checker.time.sleep", lambda _: None)
    url = "https://doi.org/doiRA/10.1257%2Faer.20190830"
    assert RegistryClient(tmp_path, pace=0).get(url)["status"] == 200
    assert len(attempts) == 2


def test_negative_cache_expiry_refresh_and_atomic_replace(tmp_path, monkeypatch):
    from tools.reference_checker import RegistryClient
    url = "https://doi.org/doiRA/10.1257%2Faer.20190830"
    cache = tmp_path / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    cache.write_text('{"status":404,"data":null}', encoding="utf-8")
    old = time.time() - 8 * 86400
    os.utime(cache, (old, old))
    calls = []

    class Reply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'[{"RA":"Crossref"}]'

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (calls.append(1), Reply())[1])
    import tools.reference_checker as module
    real_replace = module.os.replace
    def replace(source, target):
        assert Path(source).exists()
        assert Path(target) == cache
        real_replace(source, target)
    monkeypatch.setattr(module.os, "replace", replace)
    client = RegistryClient(tmp_path, pace=0)
    assert client.get(url)["status"] == 200
    assert len(calls) == 1
    assert client.get(url)["status"] == 200
    assert len(calls) == 1
    assert RegistryClient(tmp_path, pace=0, refresh=True).get(url)["status"] == 200
    assert len(calls) == 2


def test_unwritable_cache_does_not_lose_registry_answer(tmp_path, monkeypatch):
    class Reply:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'[{"RA":"Crossref"}]'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Reply())
    def deny(*args, **kwargs):
        raise OSError("read-only cache")
    monkeypatch.setattr(Path, "mkdir", deny)
    assert RegistryClient(tmp_path / "missing", pace=0).get("https://doi.org/doiRA/10.1257%2Faer.20190830")["status"] == 200


def test_crossref_organization_name_and_german_surname_equivalence():
    from tools.reference_checker import compare
    class OrganizationClient:
        def get(self, url):
            if "/doiRA/" in url:
                return {"status": 200, "data": [{"RA": "Crossref"}]}
            return {"status": 200, "data": {"message": {"title": ["A Report"],
                "author": [{"name": "World Bank"}], "published": {"date-parts": [[2020]]}}}}
    _, record, _ = registry_record("10.9999/report", OrganizationClient())
    assert record["authors"] == ["World Bank"]
    assert compare("Mueller (2020). A Test Paper", {"authors": ["Müller"],
                   "title": "A Test Paper", "years": [2020]})[0] == "SAME_WORK"


def test_cli_exit_codes_are_advisory_by_default(tmp_path, monkeypatch):
    import tools.reference_checker as module
    path = tmp_path / "refs.json"
    path.write_text('[{"citation":"Wrong (2020)","doi":"10.9999/wrong"}]', encoding="utf-8")
    monkeypatch.setattr(module, "check", lambda row, client: {"citation": row["citation"],
        "identifier": row["identifier"], "registry_answer": None, "identity": "WRONG_WORK",
        "text_fidelity": ["TITLE_DIFFERS"], "classification": "MISMATCH", "reason": "different work"})
    with redirect_stdout(io.StringIO()):
        assert module.main([str(path), "--offline", "--format", "json"]) == 0
        assert module.main([str(path), "--offline", "--format", "json", "--exit-nonzero-on-findings"]) == 1
    empty = tmp_path / "empty.txt"
    empty.write_text("No references here", encoding="utf-8")
    with redirect_stdout(io.StringIO()):
        assert module.main([str(empty), "--offline"]) == 1
    uncovered = tmp_path / "uncovered.md"
    uncovered.write_text("# Note\nUnattached DOI 10.9999/orphan\n", encoding="utf-8")
    with redirect_stdout(io.StringIO()):
        assert module.main([str(uncovered), "--offline"]) == 2


def test_abbreviated_page_ranges_and_in_chapter_venues_are_not_mismatches():
    from tools.reference_checker import compare
    identity, fidelity, _ = compare("Author (2020). A Study Title. In: Edited Book, 12(3), 1055–68.",
        {"authors": ["Author"], "title": "A Study Title", "years": [2020], "venue": "Edited Book", "pages": "1055-1068"})
    assert identity == "SAME_WORK"
    assert "PAGES_DIFFER" not in fidelity
    assert "VENUE_DIFFERS" not in fidelity


def test_v2_compound_surnames_and_title_variants():
    cases = [
        ("Hotz, V. J., Imbens, G. W., & Mortimer, J. H. (2005). Predicting the efficacy of future training programs using past experiences at other locations.", "10.1016/j.jeconom.2004.04.009"),
        ("Montiel Olea, J. L., et al. (2024). Externally valid policy choice.", "10.48550/arXiv.2408.09187"),
        ("Brown, D., Salisbury, M., & Ball, E. (2025). Evidence-based funding and the value of information: A case study from GiveWell.", "10.1257/pandp.20251021"),
        ("Lopez, A., et al. (2020). Bridging forecasts and humanitarian decisions.", "10.1016/j.wace.2018.03.006"),
        ("White, H., Saran, A., & Welch, V. (2020). Evidence and gap maps: A tool for promoting evidence informed policy and strategic research agendas.", "10.1002/cl2.1075"),
    ]
    for citation, doi in cases:
        result = check({"citation": citation, "identifier": doi, "kind": "doi"}, RecordedClient())
        expected = "AMBIGUOUS" if doi == "10.1002/cl2.1075" else "SAME_WORK"
        assert result["identity"] == expected, (doi, result)
        assert result["classification"] != "MISMATCH"
        if doi in {"10.48550/arXiv.2408.09187", "10.1257/pandp.20251021", "10.1016/j.wace.2018.03.006"}:
            assert "TITLE_DIFFERS" in result["text_fidelity"]


def test_v2_missing_doi_is_distinct_from_registry_failure():
    row = {"citation": "Hjort (2021)", "identifier": "10.1257/aer.20191834", "kind": "doi"}
    result = check(row, RecordedClient())
    assert result["classification"] == "NOT_FOUND"


@pytest.mark.parametrize("citation,doi", [
    ("Butler and Broockman (2011)", "10.1111/j.1540-5907.2011.00518.x"),
    ("Vivalt and Coville (2023)", "10.1016/j.jdeveco.2023.103074"),
    ("Bongers et al. (2021)", "10.1214/20-AOS1970"),
    ("Allcott (2015)", "10.1093/qje/qjv001"),
    ("Brok et al. (2008)", "10.1016/j.jclinepi.2007.10.012"),
    ("Egger et al. (2022)", "10.1016/j.jdeveco.2022.102867"),
    ("Groh et al. (2016)", "10.1093/wber/lhw023"),
])
def test_v2_seven_wrong_work_cases(citation, doi):
    row = {"citation": citation, "identifier": doi, "kind": "doi"}
    result = check(row, RecordedClient())
    assert result["identity"] == "WRONG_WORK"
    assert result["classification"] == "MISMATCH"


@pytest.mark.parametrize("citation,doi", [
    ("Hjort (2021)", "10.1257/aer.20191834"),
    ("DellaVigna, Pope and Vivalt (2020)", "10.1126/science.abb7442"),
    ("Pearl and Bareinboim (2014)", "10.1515/jci-2012-0022"),
])
def test_v2_three_not_found_cases(citation, doi):
    row = {"citation": citation, "identifier": doi, "kind": "doi"}
    result = check(row, RecordedClient())
    assert result["identity"] == "NOT_FOUND"
    assert result["classification"] == "NOT_FOUND"


def test_full_v2_doi_regression_set_offline():
    from collections import Counter
    results = [check(row, RecordedClient()) for row in V2_REFERENCES]
    assert len(results) == 42
    assert Counter(row["identity"] for row in results) == {"SAME_WORK": 31, "AMBIGUOUS": 1, "WRONG_WORK": 7, "NOT_FOUND": 3}
    assert all(row["identity"] == source["expected_identity"] for row, source in zip(results, V2_REFERENCES))
    olea = next(row for row in results if row["identifier"] == "10.48550/arXiv.2408.09187")
    assert olea["registry_answer"]["registry"] == "DataCite"
    assert "TITLE_DIFFERS" in olea["text_fidelity"]


def test_clean_v2_citations_have_no_parser_artifact_flags():
    for doi in ("10.1093/jeea/jvaa019", "10.1016/j.jeconom.2004.04.009",
                "10.1016/j.jclinepi.2007.03.013"):
        row = next(row for row in V2_REFERENCES if row["identifier"] == doi)
        assert check(row, RecordedClient())["text_fidelity"] == ["OK"], doi
    brown = next(row for row in V2_REFERENCES if row["identifier"] == "10.1257/pandp.20251021")
    assert check(brown, RecordedClient())["text_fidelity"] == ["TITLE_DIFFERS"]


def test_unsupported_agency_and_offline_miss_remain_unresolved(tmp_path):
    class OtherAgency:
        def get(self, url):
            assert "/doiRA/" in url
            return {"status": 200, "data": [{"RA": "mEDRA"}]}
    row = {"citation": "Someone (2020)", "identifier": "10.9999/example", "kind": "doi"}
    unsupported = check(row, OtherAgency())
    assert unsupported["classification"] == "UNRESOLVED"
    assert "unsupported registration agency: medra" in unsupported["reason"]
    offline = check(row, RegistryClient(tmp_path, online=False))
    assert offline["classification"] == "UNRESOLVED"
    assert "not cached" in offline["reason"]


def test_shared_second_author_or_particle_does_not_establish_identity():
    from tools.reference_checker import compare
    identity, _, _ = compare("Brown, Saran, & Ball (2020). An unrelated title",
                             {"authors": ["Saran", "Else"], "title": "Other work entirely", "years": [2020]})
    assert identity == "AMBIGUOUS"
    identity, _, _ = compare("van der Meer (2020). An unrelated title",
                             {"authors": ["den Berg"], "title": "Other work entirely", "years": [2020]})
    assert identity == "WRONG_WORK"


def test_v2_reference_line_and_table_extraction():
    note = """# References
* [Hotz (2005)](https://doi.org/10.1016/j.jeconom.2004.04.009) — Hotz, V. J., et al. (2005). Predicting the efficacy of future training programs using past experiences at other locations.
| Brown (2025) | https://doi.org/10.1257/pandp.20251021 |
"""
    rows = extract(note)
    assert len(rows) == 2
    assert "Predicting the efficacy" in rows[0]["citation"]


def test_identifier_only_table_uses_adjacent_citation_and_never_accuses():
    row = "| 1 | **Thalheimer, Schwarz, & Pretis (2023)**<br>[10.1016/j.gloenvcha.2023.102641](https://doi.org/10.1016/j.gloenvcha.2023.102641) | Somalia |"
    found = extract("# References\n" + row)[0]
    assert found["citation"] == "Thalheimer, Schwarz, & Pretis (2023)"
    assert found["identifier"] == "10.1016/j.gloenvcha.2023.102641"
    record = {"title": "A climate displacement study", "authors": ["Thalheimer", "Schwarz", "Pretis"], "years": [2023]}
    from tools.reference_checker import compare
    assert compare("10.1016/j.gloenvcha.2023.102641", record)[0] == "UNCHECKED"
    assert check(found, RecordedClient())["identity"] != "WRONG_WORK"


def test_prose_year_without_author_year_pattern_is_unchecked():
    from tools.reference_checker import compare
    record = {"authors": ["Alderman"], "title": "Men can cook", "years": [2023]}
    assert compare("Economywide CGE modeling of Sudan 2023 conflict disruptions", record)[0] == "UNCHECKED"


def test_source_verification_tag_is_never_repeated():
    note = "# References\n* [Hjort (2021)](https://doi.org/10.1257/aer.20190830) — Hjort (2021). How Research Affects Policy. **[VERIFIED]**\n"
    row = extract(note)[0]
    result = check(row, FixtureClient())
    assert "VERIFIED" not in row["citation"]
    assert "VERIFIED" not in markdown([result])


def test_multiple_dois_on_one_bullet_keep_nearby_authors():
    line = "* Full Text Audited: Allcott (2015, DOI `10.1093/qje/qjv001`); Brok (2008, DOI `10.1016/j.jclinepi.2007.10.012`)."
    rows = extract(line)
    assert [r["identifier"] for r in rows] == ["10.1093/qje/qjv001", "10.1016/j.jclinepi.2007.10.012"]
    assert rows[0]["citation"].startswith("Allcott")
    assert rows[1]["citation"].startswith("Brok")


def test_quoted_correction_is_counted_separately():
    note = """# Notes
* Corrected Lopez (2020) DOI: `10.1016/wace.2018.03.006`.
## References
* [Lopez (2020)](https://doi.org/10.1016/j.wace.2018.03.006)
"""
    found = extract(note)
    counted = coverage(note, found)
    assert len(found) == 1
    assert counted["doi_like_in_source"] == 1
    assert counted["excluded_quoted_corrections"] == 1
    assert counted["unattached"] == 0


def test_crossref_uses_online_and_print_years():
    _, record, _ = registry_record("10.1093/restud/rdz021", RecordedClient())
    assert record["years"] == [2019, 2020]
    _, fenwick, _ = registry_record("10.1177/0272989x07308751", RecordedClient())
    assert fenwick["years"] == [2007, 2008]


def test_year_difference_reports_cited_and_registry_years():
    from tools.reference_checker import compare
    identity, notes, reason = compare("Smith (2020). A Test Article",
                                      {"authors": ["Smith"], "title": "A Test Article", "years": [2019]})
    assert identity == "SAME_WORK"
    assert "YEAR_DIFFERS" in notes
    assert "cited 2020" in reason and "registry 2019" in reason


def test_html_entities_and_book_without_venue():
    assert similarity("Evidence & Policy", "Evidence &amp; Policy") == 1.0
    row = {"citation": "Barbrook-Johnson, P., & Penn, A. (2022). Systems Mapping: How to Build and Use Causal Models of Systems. Palgrave Macmillan.",
           "identifier": "10.1007/978-3-031-01919-7", "kind": "doi"}
    result = check(row, RecordedClient())
    assert result["identity"] == "SAME_WORK"
    assert "VENUE_DIFFERS" not in result["text_fidelity"]
    v2 = next(row for row in V2_REFERENCES if row["identifier"] == "10.1007/978-3-031-01919-7")
    assert "TITLE_DIFFERS" not in check(v2, RecordedClient())["text_fidelity"]


@pytest.mark.skipif(os.getenv("REFERENCE_CHECKER_ONLINE_SMOKE") != "1", reason="opt-in live registry check")
def test_online_smoke(tmp_path):
    row = {"citation": "Hjort (2021). How Research Affects Policy: Experimental Evidence from 2,150 Brazilian Municipalities",
           "identifier": "10.1257/aer.20190830", "kind": "doi"}
    result = check(row, RegistryClient(tmp_path))
    assert result["classification"] == "MATCH"
