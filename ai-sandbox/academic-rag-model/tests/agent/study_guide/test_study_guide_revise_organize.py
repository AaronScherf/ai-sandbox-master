# tests/agent/study_guide/test_study_guide_revise_organize.py
import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.organize import (
    build_outline, mechanical_heading_edits, organize_edits, parse_organize,
)
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM

BODY = "# T\n\n## A\n\nalpha words\n\n# Stray\n\nstray words\n\n## B\n\nbeta words\n"


def test_a_body_h1_becomes_a_retitle_to_h2():
    blocks = segment(BODY)
    edits = mechanical_heading_edits(blocks)
    assert [(e.type, e.targets, e.replacement, e.stage) for e in edits] == [
        ("retitle", [blocks[2].id], "## Stray", "organization")]


def test_outline_has_ids_levels_words_and_flags_but_no_body_text():
    blocks = segment(BODY)
    outline = build_outline(blocks, {blocks[1].id: ["duplicate"]})
    assert blocks[1].id in outline and "alpha words" not in outline and "duplicate" in outline and "H2" in outline


def test_parse_retitle_and_move():
    blocks = segment(BODY)
    by_id = {b.id: b for b in blocks}
    data = {"edits": [{"type": "retitle", "block": blocks[1].id, "new_heading": "Alpha", "rationale": "clearer"},
                      {"type": "move", "block": blocks[3].id, "after": blocks[1].id, "rationale": "order"}]}
    edits = parse_organize(data, by_id, start=1)
    assert [(e.type, e.replacement, e.anchor) for e in edits] == [("retitle", "## Alpha", None), ("move", None, blocks[1].id)]


@pytest.mark.parametrize("data", [
    {"edits": [{"type": "retitle", "block": "zzz", "new_heading": "X", "rationale": "r"}]},
    {"edits": [{"type": "move", "block": "A", "after": "zzz", "rationale": "r"}]},
    {"edits": [{"type": "retitle", "block": "A", "rationale": "r"}]},
    {"edits": [{"type": "explode", "block": "A", "rationale": "r"}]},
])
def test_bad_responses_are_rejected(data):
    with pytest.raises(ReviseError):
        parse_organize(data, {"A": segment("## A\n\nx\n")[0]}, start=1)


def test_organize_edits_combines_mechanical_and_model_proposals():
    blocks = segment(BODY)
    llm = ScriptedLLM([{"edits": []}])
    edits = organize_edits(llm, blocks, {})
    assert len(llm.calls) == 1 and [e.type for e in edits] == ["retitle"]


def test_a_malformed_organize_response_keeps_the_mechanical_edits(capsys):
    blocks = segment(BODY)
    llm = ScriptedLLM([{"edits": [{"type": "explode", "block": blocks[1].id, "rationale": "r"}]}])
    edits = organize_edits(llm, blocks, {})
    assert [e.type for e in edits] == ["retitle"] and "WARNING" in capsys.readouterr().out
