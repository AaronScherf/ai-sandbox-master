# tests/agent/study_guide/test_study_guide_revise_judge.py
"""The relevance judge: an LLM verdict on the lowest-scoring and unscored blocks, against a stated scope."""
import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.evidence import EvidenceChunk
from agent.study_guide.revise.judge import (
    BATCH, JUDGE_SCHEMA, build_judge_prompt, judge_candidates, judge_edits, parse_judge,
)
from agent.study_guide.revise.relevance import score_blocks
from agent.study_guide.revise.segment import segment
from agent.study_guide.spec import SpecError, load_spec
from rv_helpers import ScriptedLLM, bag_embed

VOCAB = ["wald", "score", "package"]
BODY = ("# T\n\n## Wald statistic\n\n" + "wald wald statistic words " * 12 + "\n\n"
        "## Software packages\n\n" + "package package install " * 12 + "\n\n"
        "## Score test\n\n" + "score test words " * 12 + "\n\n"
        "## Stata\n\nuse the stata command here today ok\n")
EVIDENCE = [
    EvidenceChunk("e1", "Exam Q1, p. 1", 3.0, (1.0, 0.0, 0.0), "Exam question about the Wald statistic."),
    EvidenceChunk("e2", "Pset 2, p. 3", 1.5, (0.0, 1.0, 0.0), "Problem about the score test."),
]


def _scored():
    blocks = segment(BODY)
    return blocks, score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20)


def test_scores_carry_the_nearest_evidence_text():
    blocks, scores = _scored()
    wald = next(b for b in blocks if b.heading_path[-1] == "Wald statistic")
    assert scores[wald.id].nearest_text[0].startswith("Exam question about the Wald")


def test_candidates_are_the_lowest_scored_plus_unscored_blocks_with_enough_words():
    blocks, scores = _scored()
    ids = {b.heading_path[-1]: b.id for b in blocks}
    got = judge_candidates(blocks, scores, fraction=0.34, protected=[], skip=[], min_unscored_words=8)
    assert got[0] == ids["Software packages"]          # lowest score first
    assert ids["Stata"] in got                         # unscored but long enough
    assert ids["Wald statistic"] not in got and ids["T"] not in got


def test_protected_and_already_proposed_blocks_are_never_candidates():
    blocks, scores = _scored()
    ids = {b.heading_path[-1]: b.id for b in blocks}
    got = judge_candidates(blocks, scores, fraction=1.0, protected=[ids["Score test"]], skip=[ids["Software packages"]],
                           min_unscored_words=8)
    assert ids["Score test"] not in got and ids["Software packages"] not in got


def test_prompt_states_the_scope_and_shows_blocks_with_evidence():
    blocks, scores = _scored()
    pk = next(b for b in blocks if b.heading_path[-1] == "Software packages")
    prompt = build_judge_prompt("No software guides.", [pk], scores)
    assert "No software guides." in prompt and pk.id in prompt and "Software packages" in prompt
    assert "Nearest course material" in prompt


def test_parse_makes_delete_edits_only_for_delete_verdicts():
    blocks, _ = _scored()
    by_id = {b.id: b for b in blocks}
    a, b = blocks[2].id, blocks[3].id
    data = {"verdicts": [{"block": a, "verdict": "delete", "rationale": "software tutorial"},
                         {"block": b, "verdict": "keep", "rationale": "examined"}]}
    edits = parse_judge(data, by_id, [a, b], start=3, scores={})
    assert [(e.type, e.targets, e.stage, e.id) for e in edits] == [("delete", [a], "relevance", "rel-003")]
    assert edits[0].rationale.startswith("judge:")


@pytest.mark.parametrize("data", [
    {"verdicts": [{"block": "zzz", "verdict": "delete", "rationale": "x"}]},
    {"verdicts": [{"block": "A", "verdict": "banish", "rationale": "x"}]},
])
def test_parse_rejects_unknown_blocks_and_verdicts(data):
    with pytest.raises(ReviseError):
        parse_judge(data, {"A": segment("## A\n\nx\n")[0]}, ["A"], start=1, scores={})


def test_judge_edits_batches_the_candidates():
    blocks, scores = _scored()
    ids = [b.id for b in blocks if b.level]
    llm = ScriptedLLM([{"verdicts": []}] * 3)
    assert BATCH >= 2 and JUDGE_SCHEMA["required"] == ["verdicts"]
    judge_edits(llm, "scope", {b.id: b for b in blocks}, ids * 1, scores, start=1)
    assert len(llm.calls) == -(-len(ids) // BATCH)


def test_spec_reads_scope_and_judge_fraction(tmp_path):
    base = ('[guide]\nid = "g"\ntitle = "T"\ncourse = "econ"\n\n[[topic]]\ntitle = "A"\ninstruction = "i"\n\n'
            '  [[topic.source]]\n  kind = "file"\n  file = "x"\n\n[revise]\n')
    p = tmp_path / "s.toml"
    p.write_text(base + 'scope = "Only the tests."\njudge_fraction = 0.2\n', encoding="utf-8")
    r = load_spec(p).revise
    assert (r.scope, r.judge_fraction) == ("Only the tests.", 0.2)
    p.write_text(base, encoding="utf-8")
    r = load_spec(p).revise
    assert (r.scope, r.judge_fraction) == ("", 0.0)
    p.write_text(base + "judge_fraction = 2\n", encoding="utf-8")
    with pytest.raises(SpecError, match="judge_fraction"):
        load_spec(p)
