# tests/agent/study_guide/test_study_guide_revise_apply.py
import pytest

from agent.study_guide.revise.apply import apply_edits, changelog
from agent.study_guide.revise.edits import (
    Edit, EditReport, ReviseError, load_report, mark_conflicts, save_report, validate_report,
)
from agent.study_guide.revise.segment import segment

BODY = ("# T\n\nintro words here\n\n## A\n\nalpha one two three\n\n### A1\n\nsub text with several words\n\n"
        "## B\n\nbeta four five six seven eight\n\n## C\n\ngamma tail words\n")


def _ids():
    return {b.heading_path[-1]: b.id for b in segment(BODY)}


def _report(*edits):
    return EditReport("g.md", "sha", "2026-10-08T00:00:00+00:00", [], list(edits), [])


def _e(eid, type_, targets, **kw):
    kw.setdefault("rationale", "why")
    kw.setdefault("stage", "relevance")
    return Edit(eid, type_, targets=targets, **kw)


def test_nothing_accepted_returns_the_body_byte_for_byte():
    ids = _ids()
    assert apply_edits(BODY, _report(_e("e1", "delete", [ids["B"]])), set()) == BODY


def test_delete_removes_only_that_block():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "delete", [ids["B"]])), {"e1"})
    assert "beta" not in out and "alpha" in out and "gamma tail" in out and "sub text" in out


def test_fix_with_quote_replaces_only_the_quote():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "fix", [ids["B"]], quote="four five", replacement="4 5")), {"e1"})
    assert "beta 4 5 six" in out and out.count("## B") == 1


def test_fix_quote_must_occur_exactly_once():
    ids = _ids()
    with pytest.raises(ReviseError, match="exactly once"):
        apply_edits(BODY, _report(_e("e1", "fix", [ids["B"]], quote="nowhere", replacement="x")), {"e1"})


def test_shrink_and_link_replace_the_whole_block():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "link", [ids["C"]], replacement="## C\n\nSee [[#A]].")), {"e1"})
    assert "See [[#A]]." in out and "gamma tail" not in out


def test_merge_replaces_the_first_target_and_deletes_the_rest():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "merge", [ids["A"], ids["B"]], replacement="## A\n\nmerged text")), {"e1"})
    assert "merged text" in out and "beta" not in out and "alpha" not in out


def test_retitle_changes_only_the_heading_line():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "retitle", [ids["B"]], replacement="## Better title")), {"e1"})
    assert "## Better title\n\nbeta four five" in out and "## B\n" not in out


def test_move_places_the_block_after_the_anchor():
    ids = _ids()
    out = apply_edits(BODY, _report(_e("e1", "move", [ids["C"]], anchor=ids["A"])), {"e1"})
    assert out.index("alpha") < out.index("gamma tail") < out.index("sub text")


def test_note_edits_change_nothing():
    ids = _ids()
    assert apply_edits(BODY, _report(_e("e1", "note", [ids["B"]])), {"e1"}) == BODY


def test_two_accepted_edits_on_one_block_are_refused():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]]), _e("e2", "retitle", [ids["B"]], replacement="## X"))
    with pytest.raises(ReviseError, match="same block"):
        apply_edits(BODY, rep, {"e1", "e2"})


def test_unknown_accepted_id_is_refused():
    with pytest.raises(ReviseError, match="unknown edit"):
        apply_edits(BODY, _report(), {"nope"})


def test_postcondition_total_words_may_not_grow():
    ids = _ids()
    long_text = "## C\n\n" + " ".join(["more"] * 50)
    with pytest.raises(ReviseError, match="longer"):
        apply_edits(BODY, _report(_e("e1", "shrink", [ids["C"]], replacement=long_text)), {"e1"})


def test_postcondition_no_new_page_citations():
    ids = _ids()
    with pytest.raises(ReviseError, match="citation"):
        apply_edits(BODY, _report(_e("e1", "link", [ids["C"]], replacement="## C\n\nsee (Hansen, p. 9)")), {"e1"})


def test_postcondition_no_new_heading_problems():
    ids = _ids()
    with pytest.raises(ReviseError, match="heading"):
        apply_edits(BODY, _report(_e("e1", "retitle", [ids["B"]], replacement="###### Deep")), {"e1"})


def test_retitle_replacement_must_be_a_single_heading_line():
    ids = _ids()
    rep = _report(_e("e1", "retitle", [ids["B"]], replacement="## Better\n\nsmuggled extra words"))
    with pytest.raises(ReviseError, match="single heading line"):
        apply_edits(BODY, rep, {"e1"})


def test_validate_report_flags_bad_edits():
    blocks = segment(BODY)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    bad = _report(_e("e1", "delete", ["missing"]), _e("e2", "link", [ids["A"]]), _e("e3", "move", [ids["A"]]),
                  _e("e4", "merge", [ids["A"]], replacement="x"), _e("e5", "weird", [ids["A"]]),
                  _e("e5", "delete", [ids["B"]]))
    problems = " | ".join(validate_report(bad, blocks))
    for fragment in ("unknown block", "needs a replacement", "needs one target and an anchor", "at least two", "unknown edit type", "duplicate edit id"):
        assert fragment in problems


def test_mark_conflicts_links_edits_sharing_a_block():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]]), _e("e2", "retitle", [ids["B"]], replacement="## X"), _e("e3", "delete", [ids["C"]]))
    mark_conflicts(rep)
    assert rep.edits[0].conflicts == ["e2"] and rep.edits[1].conflicts == ["e1"] and rep.edits[2].conflicts == []


def test_report_round_trips_through_json(tmp_path):
    rep = _report(_e("e1", "delete", ["b1"], evidence=["c1"], protected=True))
    save_report(rep, tmp_path / "x" / "r.json")
    assert load_report(tmp_path / "x" / "r.json") == rep


def test_changelog_lists_applied_and_acknowledged_edits():
    ids = _ids()
    rep = _report(_e("e1", "delete", [ids["B"]], rationale="off topic"), _e("e2", "note", [ids["C"]], rationale="check this"))
    text = changelog(rep, {"e1", "e2"})
    assert "e1" in text and "off topic" in text and "acknowledged" in text and "check this" in text


def test_blank_lines_before_the_first_heading_survive():
    body = "\n" + BODY
    ids = _ids()
    assert apply_edits(body, _report(_e("e1", "delete", [ids["B"]])), set()) == body
    assert apply_edits(body, _report(_e("e1", "delete", [ids["B"]])), {"e1"}).startswith("\n# T")


def test_a_move_anchored_on_another_moved_block_is_refused_not_lost():
    ids = _ids()
    rep = _report(_e("m1", "move", [ids["B"]], anchor=ids["A"]), _e("m2", "move", [ids["C"]], anchor=ids["B"]))
    with pytest.raises(ReviseError, match="moved"):
        apply_edits(BODY, rep, {"m1", "m2"})
