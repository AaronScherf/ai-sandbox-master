# tests/agent/study_guide/test_study_guide_revise_relevance.py
import dataclasses

import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.evidence import EvidenceChunk, load_evidence
from agent.study_guide.revise.relevance import cosine, relevance_edits, score_blocks
from agent.study_guide.revise.segment import segment
from agent.study_guide.spec import EvidenceRule, ReviseSpec, SourceRule
from rv_helpers import bag_embed
from sg_helpers import CARDS, CHUNKS, make_spec, root  # noqa: F401 (fixtures)

VOCAB = ["wald", "score", "package"]
BODY = ("# T\n\n## Wald statistic\n\n" + "wald wald statistic words " * 12 + "\n\n"
        "## Software packages\n\n" + "package package install " * 12 + "\n\n"
        "## Score test\n\n" + "score test words " * 12 + "\n")
EVIDENCE = [
    EvidenceChunk("e1", "Exam Q1, p. 1", 3.0, (1.0, 0.0, 0.0)),    # about Wald, exam weight
    EvidenceChunk("e2", "Pset 2, p. 3", 1.5, (0.0, 1.0, 0.0)),     # about the score test
]


def test_cosine():
    assert cosine((1, 0), (1, 0)) == pytest.approx(1.0) and cosine((1, 0), (0, 1)) == 0.0 and cosine((0, 0), (1, 1)) == 0.0


def test_scores_use_the_best_weighted_similarity():
    blocks = segment(BODY)
    scores = score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20)
    by = {b.heading_path[-1]: scores[b.id] for b in blocks if b.id in scores}
    assert by["Wald statistic"].score == pytest.approx(1.0)          # exam weight 3 / max 3
    assert by["Score test"].score == pytest.approx(0.5)              # pset weight 1.5 / 3
    assert by["Software packages"].score == 0.0
    assert by["Wald statistic"].nearest[0][0] == "Exam Q1, p. 1"


def test_short_blocks_are_not_scored():
    blocks = segment("# T\n\n## Tiny\n\nfew words\n")
    assert score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20) == {}


def test_low_scores_become_delete_proposals_and_high_scores_are_protected():
    blocks = segment(BODY)
    scores = score_blocks(blocks, EVIDENCE, bag_embed(VOCAB), min_words=20)
    edits, protected = relevance_edits(blocks, scores, low=0.3, high=0.9)
    ids = {b.heading_path[-1]: b.id for b in blocks}
    assert [(e.type, e.targets) for e in edits] == [("delete", [ids["Software packages"]])]
    assert edits[0].stage == "relevance" and edits[0].id == "rel-001" and edits[0].evidence
    assert protected == [ids["Wald statistic"]]


def test_no_evidence_is_an_error_for_the_relevance_stage():
    with pytest.raises(ReviseError, match="evidence"):
        score_blocks(segment(BODY), [], bag_embed(VOCAB), min_words=20)


def test_evidence_rules_resolve_through_the_plan_machinery(make_spec, root, tmp_path):
    spec = make_spec('[[topic]]\ntitle = "T"\ninstruction = "i"\n\n  [[topic.source]]\n  kind = "file"\n  file = "x"\n')
    revise = ReviseSpec("m", ("relevance",), (EvidenceRule(SourceRule("file", file="sl", max=5), 3.0),))
    spec = dataclasses.replace(spec, revise=revise)
    chunks = [dict(c, embedding=[1.0, 0.0]) for c in CHUNKS]
    found = load_evidence(spec, root, search=lambda *a, **k: [], chunks=chunks, cards=CARDS)
    assert found and all(isinstance(e, EvidenceChunk) and e.weight == 3.0 for e in found)
    assert {e.chunk_id for e in found} <= {"sl-1", "sl-2"}
    assert load_evidence(dataclasses.replace(spec, revise=None), root, chunks=chunks, cards=CARDS) == []
