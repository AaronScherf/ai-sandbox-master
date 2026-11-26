import pytest

from agent.literature.profile import evaluate
from agent.literature.vocab import Term, Vocabulary


@pytest.mark.parametrize("value,expected", [
    ("Journal article", "journal_article"), ("Journal Article", "journal_article"),
    ("Published working paper", "working_paper"), ("Published Working Paper", "working_paper"),
    ("Published report", "report"), ("3ie series report", "report"), ("3ie grantee final report", "report"),
    ("Thesis", "thesis"), ("thesis", "thesis"), ("Published protocol", "protocol"),
    ("Book or book chapter", "other"),
])
def test_map_publication_type_cases_incl_capitalisation(value, expected):
    assert evaluate.map_publication_type(value) == expected


@pytest.mark.parametrize("value", ["Ongoing study", "3ie-funded ongoing study", "", None, "Something new"])
def test_unscored_publication_types_map_to_none(value):
    assert evaluate.map_publication_type(value) is None


def test_load_3ie_csv_reads_columns_and_normalises_no_doi_variants(tmp_path):
    path = tmp_path / "all_study_record.csv"
    path.write_bytes(
        "Title,Author_Names,EGM_Report_URL,Abstract,Publication_Of_Type,DOI,Journal_Name,Journal_Volume,Journal_Issue,Pages,Url\n"
        "A Title,\"Smith, Ann; Jones, Bo\",,An abstract,Journal article,10.1/ABC,Some Journal,1,2,3-4,http://x\n"
        "B Title,\"D�Haese, Marijke\",,,Published report,No DOI,,,,,\n"
        "C Title,X,,,Thesis,no doi,,,,,\n"
        "D Title,Y,,,Thesis,No doi,,,,,\n".encode("utf-8"))
    rows = evaluate.load_3ie_csv(str(path))
    assert [r["doi"] for r in rows] == ["10.1/abc", None, None, None]
    assert rows[0]["authors"] == ["Smith, Ann", "Jones, Bo"] and rows[0]["publication_type"] == "journal_article"
    assert rows[0]["journal"] == "Some Journal" and rows[1]["publication_type"] == "report"


def test_load_3ie_csv_handles_the_byte_order_mark_the_real_exports_start_with(tmp_path):
    path = tmp_path / "all_study_record.csv"
    path.write_bytes("﻿Title,Author_Names,EGM_Report_URL,Abstract,Publication_Of_Type,DOI,Journal_Name,Journal_Volume,"
                     "Journal_Issue,Pages,Url\nA,X,,,Journal article,10.1/a,J,,,,\n".encode("utf-8"))
    assert evaluate.load_3ie_csv(str(path))[0]["title"] == "A"


def _vocab():
    terms = {"intervention.s": Term("intervention.s", "S"),
             "intervention.b": Term("intervention.b", "B", parent="intervention.s"),
             "intervention.l": Term("intervention.l", "L", parent="intervention.b")}
    return Vocabulary("intervention", 1, "3ie", "t", terms)


def test_score_is_per_stratum_not_pooled():
    key = [{"file_id": "1", "title": "Cash transfers in Kenya", "doi": "10.1/a", "report_type": "journal_article",
            "discipline": "Medicine", "applicability": "both", "main_intervention": ["intervention.b"]},
           {"file_id": "2", "title": "Another paper", "doi": "10.1/b", "report_type": "report",
            "discipline": "Medicine", "applicability": "not_applicable"}]
    predicted = [
        {"file_id": "1", "title": "Cash Transfers in Kenya.", "doi": "10.1/a", "report_type": "journal_article",
         "discipline": "Medicine", "applicability": "both", "intervention_tags": [{"term_id": "intervention.l"}]},
        {"file_id": "2", "title": "Totally different", "doi": "10.1/x", "report_type": "journal_article",
         "discipline": "Physics and Astronomy", "applicability": "both", "intervention_tags": []}]
    stratum = {"1": "impact_evaluation", "2": "report"}
    out = evaluate.score_records(predicted, key, lambda r: stratum[r["file_id"]], vocabs={"intervention": _vocab()})
    assert set(out) == {"impact_evaluation", "report"}
    ie, rep = out["impact_evaluation"], out["report"]
    assert ie["n"] == 1 and ie["title_accuracy"] == 1.0 and ie["doi_accuracy"] == 1.0
    assert ie["report_type_agreement"] == 1.0 and ie["applicability_agreement"] == 1.0
    assert ie["tag_recall"] == 1.0  # leaf rolls up to the branch the key names
    assert rep["title_accuracy"] == 0.0 and rep["doi_accuracy"] == 0.0 and rep["report_type_agreement"] == 0.0
    assert rep["discipline_agreement"] == 0.0 and rep["tag_recall"] is None


def test_score_ignores_predictions_without_a_key_and_reports_missing_predictions():
    key = [{"file_id": "1", "report_type": "report"}]
    out = evaluate.score_records([{"file_id": "9", "report_type": "report"}], key, lambda r: "s")
    assert out["s"]["n"] == 1 and out["s"]["missing_predictions"] == 1 and out["s"]["report_type_agreement"] is None


def test_blind_label_page_hides_model_predictions():
    papers = [{"file_id": "p1", "title": "A </script> Paper", "authors": ["Ann Smith"], "excerpt": "Opening text here.",
               "research_profile": {"discipline": "SECRETFIELD", "applicability": "SECRETTIER"}, "report_type": "SECRETTYPE"}]
    page = evaluate.blind_label_page(papers, ["journal_article", "book"])
    assert "Opening text here." in page and '"p1"' in page and '"book"' in page
    assert "</script> Paper" not in page  # paper text cannot close the data block
    for secret in ("SECRETFIELD", "SECRETTIER", "SECRETTYPE"):
        assert secret not in page


def test_excerpt_keeps_the_front_matter_then_jumps_to_the_abstract_past_the_contents_page():
    text = """---
title: x
---

<!-- page 1 -->
Journal header
Executive Summary ........................ 4
""" + "filler " * 40 + """
## Abstract
We study cash.
<!-- page 2 -->
More."""
    out = evaluate.excerpt(text, front=40, limit=200)
    assert out.startswith("Journal header") and "## Abstract" in out and "We study cash." in out
    assert "[…]" in out and "title: x" not in out and "<!--" not in out
    assert len(evaluate.excerpt("word " * 5000, front=50, limit=50)) == 100


def test_labels_become_an_answer_key_and_unfinished_labels_are_left_out():
    labels = {"p1": {"report_type": "report", "applicability": "both", "main_intervention": ["i.a"], "main_outcome": []},
              "p2": {"report_type": "", "applicability": "both"}}
    key = evaluate.labels_to_key(labels)
    assert key == [{"file_id": "p1", "report_type": "report", "applicability": "both",
                    "main_intervention": ["i.a"], "main_outcome": []}]
