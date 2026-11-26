"""Document types, publisher fields, the re-typing pass and the second-reader folder."""

import json
import tempfile
from pathlib import Path

from agent.literature.profile import classify, evaluate, reader, review
from agent.literature.vocab import Term, Vocabulary
from core.indexer.index_card import find_card_by_file_id, save_shard
from core.indexer.research_profile import PUBLISHER_TYPES, REPORT_TYPES, set_research_profile, validate_profile

PROV = {"driver": "agent", "agent": "gemini", "run": "r1"}
QUOTE = "We evaluate a cash transfer given to households."


def _root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    md = root / "journal-articles" / "business" / "processed_outputs" / "p.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\ntags: [SECRETTAG]\n---\n\n<!-- page 1 -->\n\n" + QUOTE + "\n", encoding="utf-8")
    save_shard(str(root), "business", [{"file_id": "f1", "course": "business", "title": "A Paper",
                                        "doc_type": "journal_article",
                                        "path": "journal-articles/business/processed_outputs/p.md"}])
    return tmp, root


def _card(root):
    return find_card_by_file_id(str(root), "f1")[1]


def _entry():
    return {"subject": {"file_id": "f1", "variant": "type"}}


def _typed(**over):
    return {"report_type": "report", "subtype": "policy_brief", "publisher": "World Bank",
            "publisher_type": "multilateral", **over}


def test_grey_literature_is_merged_away_and_books_and_publishers_are_known():
    assert "grey_literature" not in REPORT_TYPES and {"book", "book_chapter"} <= REPORT_TYPES
    assert PUBLISHER_TYPES == {"academic", "research_institute", "multilateral", "government", "ngo", "other"}
    assert validate_profile({"publisher": "World Bank", "publisher_type": "multilateral"}) == []
    assert validate_profile({"publisher_type": "practitioner"})


def test_both_prompts_state_the_type_rules():
    for text in (classify.INSTRUCTIONS_A, classify.INSTRUCTIONS_TYPE):
        assert classify.TYPE_RULES in text and "publisher_type" in text
    assert "grey_literature" not in classify.TYPE_RULES


def test_retype_card_hides_the_current_type_and_is_not_repeated():
    tmp, root = _root()
    with tmp:
        set_research_profile(str(root), "f1", {"report_type": "thesis"})
        tasks, _ = classify.make_tasks(classify.Target(str(root)), [_card(root)], variant="type")
        assert len(tasks) == 1 and "thesis" not in tasks[0].context
        classify.apply_result(classify.Target(str(root)), _entry(), _typed(), PROV)
        tasks, skipped = classify.make_tasks(classify.Target(str(root)), [_card(root)], variant="type")
        assert tasks == [] and "already" in skipped["f1"]


def test_retype_validation():
    tmp, root = _root()
    with tmp:
        target = classify.Target(str(root))
        assert classify.validate_result(_entry(), _typed(), target) == []
        assert classify.validate_result(_entry(), _typed(report_type="grey_literature", report_type_proposed=True),
                                        target)
        assert classify.validate_result(_entry(), _typed(publisher_type="practitioner"), target)


def test_retype_changes_only_type_and_publisher():
    tmp, root = _root()
    with tmp:
        set_research_profile(str(root), "f1", {"report_type": "grey_literature", "discipline": "Medicine",
                                               "applicability": "both", "intervention_tags": [{"term_id": "x"}]})
        classify.apply_result(classify.Target(str(root)), _entry(), _typed(), PROV)
        p = _card(root)["research_profile"]
        assert (p["report_type"], p["publisher"], p["publisher_type"]) == ("report", "World Bank", "multilateral")
        assert p["discipline"] == "Medicine" and p["applicability"] == "both" and p["intervention_tags"]
        assert not p.get("needs_review") and p["provenance"]["classify_type"]["prompt_version"] == classify.TYPE_VERSION


def test_retype_to_a_non_research_type_is_queued_for_the_owner():
    tmp, root = _root()
    with tmp:
        set_research_profile(str(root), "f1", {"report_type": "report", "applicability": "both"})
        classify.apply_result(classify.Target(str(root)), _entry(), _typed(report_type="notes"), PROV)
        assert _card(root)["research_profile"]["applicability"] == "both"
        assert [i["field"] for i in review.review_queue(str(root))] == ["report_type"]


def test_old_grey_literature_labels_score_as_report():
    key = evaluate.labels_to_key({"p": {"report_type": "grey_literature", "applicability": "both"}})
    assert key[0]["report_type"] == "report"


def _vocabs():
    return {kind: Vocabulary(kind, 1, "3ie", "t", {f"{kind}.cash": Term(f"{kind}.cash", "Cash", definition="Money.")})
            for kind in ("intervention", "outcome")}


def _answer(**over):
    return {"report_type": "journal_article", "publisher": "A Journal", "publisher_type": "academic",
            "evidence": [{"kind": "intervention", "term_id": "intervention.cash", "quote": QUOTE, "page": 1}], **over}


def test_reader_pack_holds_the_paper_and_none_of_the_pipelines_answers():
    tmp, root = _root()
    with tmp:
        set_research_profile(str(root), "f1", {"report_type": "thesis", "discipline": "SECRETFIELD"})
        pack = root / "pack"
        reader.write_pack(str(root), [_card(root)], _vocabs(), pack)
        text = "".join(p.read_text(encoding="utf-8") for p in pack.rglob("*") if p.is_file())
        assert QUOTE in text and "SECRETTAG" not in text and "SECRETFIELD" not in text
        assert "intervention.cash" in text and classify.TYPE_RULES in text


def test_reader_check_derives_applicability_and_rejects_unsupported_evidence():
    tmp, root = _root()
    with tmp:
        pack = root / "pack"
        reader.write_pack(str(root), [_card(root)], _vocabs(), pack)
        assert reader.read_answers(pack, _vocabs())[1] == ["f1: no answer file"]
        answer = pack / "answers" / "f1.json"
        answer.write_text(json.dumps(_answer()), encoding="utf-8")
        labels, problems = reader.read_answers(pack, _vocabs())
        assert problems == [] and labels["f1"]["applicability"] == "intervention_only"
        assert labels["f1"]["main_intervention"] == ["intervention.cash"]
        invented = {"kind": "outcome", "term_id": "outcome.cash", "quote": "Incomes doubled across every village.",
                    "page": 1}
        answer.write_text(json.dumps(_answer(evidence=[invented])), encoding="utf-8")
        labels, problems = reader.read_answers(pack, _vocabs())
        assert "f1" not in labels and "outcome.cash" in problems[0]
