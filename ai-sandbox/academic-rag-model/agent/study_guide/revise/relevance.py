# agent/study_guide/revise/relevance.py
"""Score each block against the weighted evidence; propose deletes below a floor, mark protected blocks."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.evidence import EvidenceChunk
from agent.study_guide.revise.segment import Block


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return 0.0 if not na or not nb else sum(x * y for x, y in zip(a, b)) / (na * nb)


@dataclass(frozen=True)
class Relevance:
    block_id: str
    score: float
    nearest: tuple[tuple[str, float], ...]
    nearest_text: tuple[str, ...] = ()


def score_blocks(blocks: list[Block], evidence: list[EvidenceChunk], embed: Callable[[str], list[float]], *,
                 min_words: int) -> dict[str, Relevance]:
    if not evidence:
        raise ReviseError("the relevance stage needs evidence: add [[revise.evidence]] rules that resolve to chunks")
    top = max(e.weight for e in evidence)
    out: dict[str, Relevance] = {}
    for b in blocks:
        if b.words < min_words:
            continue
        vec = embed(b.text)
        ranked = sorted(((cosine(vec, e.embedding) * e.weight / top, e.citation, e.text) for e in evidence), reverse=True)
        out[b.id] = Relevance(b.id, ranked[0][0], tuple((c, round(s, 4)) for s, c, _ in ranked[:3]),
                              tuple(t for _, _, t in ranked[:3]))
    return out


def relevance_edits(blocks: list[Block], scores: dict[str, Relevance], *, low: float, high: float,
                    start: int = 1) -> tuple[list[Edit], list[str]]:
    edits, protected, n = [], [], start
    for b in blocks:
        r = scores.get(b.id)
        if r is None:
            continue
        if r.score >= high:
            protected.append(b.id)
        elif r.score < low:
            edits.append(Edit(
                id=f"rel-{n:03d}", type="delete", stage="relevance", targets=[b.id],
                rationale=f"no course evidence points here (relevance {r.score:.2f}, floor {low:.2f})",
                evidence=[c for c, _ in r.nearest], severity="medium" if b.words > 150 else "low",
                confidence=round(1 - r.score / low, 2)))
            n += 1
    return edits, protected
