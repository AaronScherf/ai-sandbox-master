import tempfile
from pathlib import Path

from agent.literature.profile import tagging
from agent.literature.vocab import Term, Vocabulary
from core.indexer.index_card import find_card_by_file_id, save_shard
from core.indexer.research_profile import set_research_profile

PROV = {"driver": "agent", "agent": "gemini", "run": "r1"}
QUOTE = "households received monthly cash transfers"
OUTCOME_QUOTE = "child school attendance rose sharply"


def _vocab(name):
    ids = {k: f"{name}.{k}" for k in ("s1", "b1", "l1", "l2", "s2", "b2")}
    terms = {
        ids["s1"]: Term(ids["s1"], "Sector one", definition="first sector"),
        ids["b1"]: Term(ids["b1"], "Branch one", parent=ids["s1"], definition="first branch"),
        ids["l1"]: Term(ids["l1"], "Leaf one", parent=ids["b1"], definition="first leaf"),
        ids["l2"]: Term(ids["l2"], "Leaf two", parent=ids["b1"], definition="second leaf"),
        ids["s2"]: Term(ids["s2"], "Sector two", definition="second sector"),
        ids["b2"]: Term(ids["b2"], "Branch two", parent=ids["s2"], definition="second branch"),
    }
    return Vocabulary(name, 1, "3ie", "test", terms), ids


def _setup(report_type="journal_article", pages=None, size_pad=0):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    md = root / "j" / "p.md"
    md.parent.mkdir(parents=True)
    body = pages or {1: "Abstract.", 2: f"In the programme, {QUOTE} for two years. Also, {OUTCOME_QUOTE} in the\nfollow-up.",
                     3: "Closing remarks." + "x" * size_pad}
    md.write_text("".join(f"\n<!-- page {n} -->\n\n{t}\n" for n, t in body.items()), encoding="utf-8")
    save_shard(str(root), "business", [{"file_id": "f1", "course": "business", "title": "A Paper",
                                        "doc_type": "journal_article", "path": "j/p.md"}])
    set_research_profile(str(root), "f1", {"report_type": report_type})
    iv, iids = _vocab("intervention")
    ov, oids = _vocab("outcome")
    target = tagging.Target(index_root=str(root), vocabs={"intervention": iv, "outcome": ov})
    return tmp, root, target, iids, oids


def _card(root):
    return find_card_by_file_id(str(root), "f1")[1]


def _entry(target, card, kind, level, prior=None):
    tasks, skipped = tagging.make_round_tasks(target, [card], kind, level, prior or {})
    assert not skipped, skipped
    t = tasks[0]
    return {"id": t.id, "subject": t.subject,
            "passages": [{"id": p.id, "source": p.source, "ref": p.ref, "text": p.text} for p in t.passages]}


def _tag(term_id, quote=QUOTE, locator=2):
    return {"term_id": term_id, "quote": quote, "locator": locator}


def test_level1_card_lists_only_sectors_and_level2_only_children_of_prior():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        e1 = _entry(target, _card(root), "intervention", 1)
        assert sorted(e1["subject"]["offered"]) == sorted([iids["s1"], iids["s2"]])
        e2 = _entry(target, _card(root), "intervention", 2, {"f1": [iids["s1"]]})
        assert e2["subject"]["offered"] == [iids["b1"]]


def test_non_research_report_type_gets_no_tagging_task():
    tmp, root, target, *_ = _setup(report_type="notes")
    with tmp:
        tasks, skipped = tagging.make_round_tasks(target, [_card(root)], "intervention", 1, {})
        assert tasks == [] and "not a research document" in skipped["f1"]


def test_over_length_transcript_is_skipped_never_truncated():
    tmp, root, target, *_ = _setup(size_pad=tagging.MAX_CARD_CHARS)
    with tmp:
        tasks, skipped = tagging.make_round_tasks(target, [_card(root)], "intervention", 1, {})
        assert tasks == [] and "too_long" in skipped["f1"]


def test_level2_without_prior_choice_is_skipped():
    tmp, root, target, *_ = _setup()
    with tmp:
        tasks, skipped = tagging.make_round_tasks(target, [_card(root)], "intervention", 2, {})
        assert tasks == [] and "previous level" in skipped["f1"]


def test_quote_survives_line_break_in_page_text():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        entry = _entry(target, _card(root), "outcome", 1)
        ok = tagging.validate_result(entry, {"tags": [_tag("outcome.s1", "child school attendance rose sharply in the follow-up")]},
                                     target)
        assert ok == []


def test_invented_quote_rejected():
    tmp, root, target, *_ = _setup()
    with tmp:
        entry = _entry(target, _card(root), "intervention", 1)
        problems = tagging.validate_result(entry, {"tags": [_tag("intervention.s1", "a sentence that is nowhere in it")]}, target)
        assert problems and "not found" in problems[0]


def test_tag_without_quote_rejected():
    tmp, root, target, *_ = _setup()
    with tmp:
        entry = _entry(target, _card(root), "intervention", 1)
        assert tagging.validate_result(entry, {"tags": [{"term_id": "intervention.s1", "locator": 2}]}, target)


def test_term_not_offered_at_this_level_rejected():
    tmp, root, target, *_ = _setup()
    with tmp:
        entry = _entry(target, _card(root), "intervention", 1)
        problems = tagging.validate_result(entry, {"tags": [_tag("intervention.l1")]}, target)
        assert problems and "not offered" in problems[0]


def test_empty_result_is_valid_and_gives_not_applicable():
    tmp, root, target, *_ = _setup()
    with tmp:
        for kind in ("intervention", "outcome"):
            entry = _entry(target, _card(root), kind, 1)
            assert tagging.validate_result(entry, {"tags": []}, target) == []
            tagging.apply_result(target, entry, {"tags": []}, PROV)
        p = _card(root)["research_profile"]
        assert p["applicability"] == "not_applicable" and p["intervention_tags"] == [] and p["outcome_tags"] == []


def test_apply_records_tags_and_derives_applicability_both():
    tmp, root, target, iids, oids = _setup()
    with tmp:
        tagging.apply_result(target, _entry(target, _card(root), "intervention", 1),
                             {"tags": [_tag(iids["s1"])]}, PROV)
        assert _card(root)["research_profile"]["applicability"] == "intervention_only"
        tagging.apply_result(target, _entry(target, _card(root), "outcome", 1),
                             {"tags": [_tag(oids["s2"], OUTCOME_QUOTE)]}, PROV)
        p = _card(root)["research_profile"]
        assert p["applicability"] == "both"
        assert p["intervention_tags"] == [{"term_id": iids["s1"], "level": 1, "quote": QUOTE, "quote_locator": 2}]


def test_reapplying_a_level_replaces_that_level_only_and_is_idempotent():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        e1 = _entry(target, _card(root), "intervention", 1)
        tagging.apply_result(target, e1, {"tags": [_tag(iids["s1"])]}, PROV)
        e2 = _entry(target, _card(root), "intervention", 2, {"f1": [iids["s1"]]})
        tagging.apply_result(target, e2, {"tags": [_tag(iids["b1"])]}, PROV)
        before = _card(root)["research_profile"]["intervention_tags"]
        tagging.apply_result(target, e2, {"tags": [_tag(iids["b1"])]}, PROV)
        assert _card(root)["research_profile"]["intervention_tags"] == before
        assert {t["level"] for t in before} == {1, 2}


def test_branch_only_tag_kept_at_branch_and_not_expanded_to_leaves():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        vocab = target.vocabs["intervention"]
        tags = [{"term_id": iids["s1"], "level": 1}, {"term_id": iids["b1"], "level": 2}]
        deepest = tagging.deepest_tags(vocab, tags)
        assert [t["term_id"] for t in deepest] == [iids["b1"]]
        assert iids["l1"] not in tagging.covered_terms(vocab, tags)
        assert tagging.covered_terms(vocab, tags) == {iids["b1"], iids["s1"]}


def test_leaf_tag_rolls_up_to_ancestors():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        vocab = target.vocabs["intervention"]
        tags = [{"term_id": iids["l1"], "level": 3}]
        assert tagging.covered_terms(vocab, tags) == {iids["l1"], iids["b1"], iids["s1"]}


def test_instructions_say_each_kind_is_tagged_on_its_own_and_version_was_bumped():
    text = tagging.INSTRUCTIONS.format(kind="outcome")
    assert "without evaluating or modelling any intervention" in text
    assert "never leave" in text.casefold()
    assert tagging.PROMPT_VERSION not in ("tag-v1", "tag-v2")


def test_instructions_count_a_synthesis_as_reporting_what_it_synthesises():
    text = tagging.INSTRUCTIONS.format(kind="intervention").casefold()
    assert "systematic review" in text and "synthesises" in text


def test_redoing_a_level_drops_the_deeper_tags_chosen_under_the_old_choice():
    tmp, root, target, iids, _ = _setup()
    with tmp:
        e1 = _entry(target, _card(root), "intervention", 1)
        tagging.apply_result(target, e1, {"tags": [_tag(iids["s1"])]}, PROV)
        tagging.apply_result(target, _entry(target, _card(root), "intervention", 2, {"f1": [iids["s1"]]}),
                             {"tags": [_tag(iids["b1"])]}, PROV)
        tagging.apply_result(target, e1, {"tags": [_tag(iids["s2"])]}, PROV)  # a redo of level 1
        assert [t["term_id"] for t in _card(root)["research_profile"]["intervention_tags"]] == [iids["s2"]]


def test_an_owner_decision_on_report_type_makes_a_note_taggable():
    from agent.literature.profile import review
    tmp, root, target, *_ = _setup(report_type="notes")
    with tmp:
        review.record_decision(str(root), "f1", "report_type", "journal_article", "owner")
        tasks, skipped = tagging.make_round_tasks(target, [_card(root)], "intervention", 1, {})
        assert len(tasks) == 1 and not skipped
