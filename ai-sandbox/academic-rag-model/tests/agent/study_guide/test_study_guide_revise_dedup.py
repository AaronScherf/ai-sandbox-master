# tests/agent/study_guide/test_study_guide_revise_dedup.py
import pytest

from agent.study_guide.revise.dedup import (
    build_dedup_prompt, dedup_edits, equation_set, find_duplicate_clusters, normalize_latex, parse_dedup,
)
from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM, bag_embed

VOCAB = ["wald", "score", "package"]
EQ1 = "$$\\left( \\hat\\beta - \\beta_0 \\right)^2 / V$$"
EQ2 = "$$(\\hat\\beta-\\beta_0)^2/V$$"
BODY = ("# T\n\n## Wald\n\n" + "wald statistic words " * 15 + "\n\n" + EQ1 + "\n\n"
        "## Wald again\n\n" + "wald statistic words " * 15 + "\n\n" + EQ2 + "\n\n"
        "## Score\n\n" + "score test words " * 15 + "\n")


def test_normalize_latex_ignores_spacing_and_sizing_macros():
    assert normalize_latex("\\left( x + y \\right)") == normalize_latex("(x+y)")
    assert equation_set(EQ1) == equation_set(EQ2) and len(equation_set(EQ1)) == 1


def test_near_duplicate_blocks_cluster_and_unrelated_blocks_do_not():
    blocks = segment(BODY)
    clusters = find_duplicate_clusters(blocks, bag_embed(VOCAB), similarity=0.95, min_words=20)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    assert clusters == [[ids["Wald"], ids["Wald again"]]]


def test_prompt_lists_the_blocks_with_ids():
    blocks = segment(BODY)[1:3]
    prompt = build_dedup_prompt(blocks)
    assert blocks[0].id in prompt and blocks[1].id in prompt and "canonical" in prompt


def test_parse_links_non_canonical_blocks():
    blocks = segment(BODY)
    by_id = {b.id: b for b in blocks}
    a, b = blocks[1].id, blocks[2].id
    data = {"canonical": a, "actions": [{"block": b, "action": "link", "replacement": "## Wald again\n\nSee [[#Wald]].",
                                         "rationale": "same derivation"}]}
    edits = parse_dedup(data, [a, b], by_id, start=1)
    assert [(e.type, e.targets, e.evidence, e.id) for e in edits] == [("link", [b], [a], "ded-001")]


@pytest.mark.parametrize("data,fragment", [
    ({"canonical": "zzz", "actions": []}, "canonical"),
    ({"canonical": "A", "actions": [{"block": "A", "action": "delete", "rationale": "x"}]}, "canonical block"),
    ({"canonical": "A", "actions": [{"block": "B", "action": "link", "rationale": "x"}]}, "replacement"),
])
def test_parse_rejects_bad_responses(data, fragment):
    blocks = {"A": None, "B": None}
    with pytest.raises(ReviseError, match=fragment):
        parse_dedup(data, ["A", "B"], blocks, start=1)


def test_dedup_edits_makes_one_call_per_cluster():
    blocks = segment(BODY)
    a, b = blocks[1].id, blocks[2].id
    llm = ScriptedLLM([{"canonical": a, "actions": [{"block": b, "action": "delete", "rationale": "repeat"}]}])
    edits = dedup_edits(llm, blocks, bag_embed(VOCAB), similarity=0.95, min_words=20)
    assert len(llm.calls) == 1 and [e.type for e in edits] == ["delete"]
