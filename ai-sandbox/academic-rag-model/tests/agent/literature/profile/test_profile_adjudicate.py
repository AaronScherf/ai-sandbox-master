"""Three-way comparison of the owner's labels, the pipeline and the second reader, and the owner's rulings."""

import json
import re

from agent.literature.profile import adjudicate, cli
from agent.literature.vocab import Term, Vocabulary
from core.indexer.index_card import save_shard

VOCABS = {kind: Vocabulary(kind, 1, "3ie", "t", {f"{kind}.cash": Term(f"{kind}.cash", "Cash", definition="Money.")})
          for kind in ("intervention", "outcome")}
OWNER = {"p1": {"report_type": "grey_literature", "applicability": "both"},
         "p2": {"report_type": "thesis", "applicability": "outcome_only"},
         "p3": {"report_type": "report", "applicability": "both"}}
PIPELINE = {"p1": {"report_type": "report", "applicability": "both", "publisher": "PIPEPUB",
                   "intervention_tags": [{"term_id": "intervention.cash", "quote": "households got cash",
                                          "quote_locator": 2}]},
            "p2": {"report_type": "report", "applicability": "both"},
            "p3": {"report_type": "report", "applicability": "both"}}
READER = {"p1": {"report_type": "report", "applicability": "both", "publisher": ""},
          "p2": {"report_type": "thesis", "applicability": "intervention_only", "publisher": "READPUB"}}
EVIDENCE = {"p2": [{"kind": "outcome", "term_id": "outcome.cash", "quote": "income rose", "page": 4}]}
PAPERS = {fid: {"title": f"Paper {fid}", "excerpt": "Opening."} for fid in OWNER}


def _compare(decisions=None):
    return adjudicate.compare(OWNER, PIPELINE, READER, EVIDENCE, PAPERS, VOCABS, decisions or {})


def test_only_differences_are_asked_and_a_missing_reading_is_reported():
    result = _compare()
    assert [(i["file_id"], f) for i in result["items"] for f in i["fields"]] == [("p2", "report_type"),
                                                                               ("p2", "applicability")]
    assert result["missing"] == ["p3"]  # no second reading
    item = result["items"][0]
    assert item["fields"]["report_type"] == ["report", "thesis"]
    assert item["fields"]["applicability"] == ["both", "intervention_only", "outcome_only"]
    assert item["evidence"] == [{"kind": "outcome", "term": "Cash", "quote": "income rose", "page": 4}]
    assert result["settled"]["p1"] == {"report_type": "report", "applicability": "both"}


def test_an_earlier_owner_decision_is_not_asked_again():
    result = _compare({"p2": "program_document"})
    assert list(result["items"][0]["fields"]) == ["applicability"]
    assert result["settled"]["p2"]["report_type"] == "program_document"


def test_page_does_not_say_who_answered_what():
    page = adjudicate.page(_compare()["items"], ["report", "thesis"])
    data = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1))
    assert set(data["items"][0]) == {"file_id", "title", "excerpt", "fields", "evidence", "publishers"}
    assert data["items"][0]["publishers"] == ["READPUB"]
    assert "pipeline" not in json.dumps(data).lower() and "owner" not in json.dumps(data).lower()


def test_rulings_settle_the_reference_and_unruled_papers_are_left_out():
    comparison = _compare()
    key, open_fields = adjudicate.apply_rulings(comparison, {"p2": {"report_type": "thesis"}})
    assert set(key) == {"p1"} and open_fields == ["p2: applicability"]
    key, open_fields = adjudicate.apply_rulings(comparison, {"p2": {"report_type": "thesis",
                                                                    "applicability": "both"}})
    assert not open_fields and key["p2"]["applicability"] == "both"
    scores = adjudicate.agreement(comparison, key)
    assert scores["report_type"] == {"n": 2, "owner": 2, "pipeline": 1, "reader": 2}
    assert scores["applicability"] == {"n": 2, "owner": 1, "pipeline": 2, "reader": 1}


def test_both_commands_run_end_to_end(monkeypatch, tmp_path):
    md = tmp_path / "p.md"
    md.write_text("<!-- page 1 -->\n\nWe evaluate a cash transfer given to households.\n", encoding="utf-8")
    save_shard(str(tmp_path), "business", [{"file_id": "p1", "course": "business", "title": "A Paper", "path": "p.md",
                                            "research_profile": {"report_type": "report", "applicability": "both"}}])
    monkeypatch.setattr(cli, "_vocabs", lambda args: VOCABS)
    pack = tmp_path / "pack"
    (pack / "papers").mkdir(parents=True)
    (pack / "answers").mkdir()
    (pack / "papers" / "p1.md").write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
    (pack / "answers" / "p1.json").write_text(json.dumps(
        {"report_type": "thesis", "publisher": "", "publisher_type": "other", "evidence": []}), encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"p1": {"report_type": "report", "applicability": "both"}}), encoding="utf-8")
    root, out = ["--index-root", str(tmp_path)], tmp_path / "out"
    assert cli.main(root + ["compare", "--labels", str(labels), "--reader-pack", str(pack), "--out", str(out)]) == 0
    assert (out / "index.html").exists()
    rulings = tmp_path / "rulings"
    rulings.mkdir()
    (rulings / "p1.json").write_text(json.dumps({"report_type": "report", "applicability": "both"}), encoding="utf-8")
    assert cli.main(root + ["adjudicate", "--comparison", str(out / "comparison.json"), "--rulings",
                            str(rulings)]) == 0
    assert json.loads((out / "reference.json").read_text(encoding="utf-8"))["p1"]["report_type"] == "report"
