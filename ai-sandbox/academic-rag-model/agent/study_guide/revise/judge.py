# agent/study_guide/revise/judge.py
"""Relevance judge: an LLM verdict on the lowest-scoring and unscored blocks against a stated scope.

Embedding scores say how close a block is to the course evidence, but a whole guide on one topic scores
uniformly high, so the score alone cannot find out-of-scope material. The judge reads the blocks that the
score ranks lowest (and short blocks the score skips) together with the nearest course material."""
from __future__ import annotations

import math

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.relevance import Relevance
from agent.study_guide.revise.segment import Block

BATCH = 12
BLOCK_CHARS = 1500
EVIDENCE_CHARS = 300

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object",
        "properties": {"block": {"type": "string"}, "verdict": {"type": "string", "enum": ["keep", "delete"]},
                       "rationale": {"type": "string"}},
        "required": ["block", "verdict", "rationale"]}}},
    "required": ["verdicts"],
}


def judge_candidates(blocks: list[Block], scores: dict[str, Relevance], *, fraction: float, protected: list[str],
                     skip: list[str], min_unscored_words: int = 15) -> list[str]:
    """Block ids to judge: the lowest `fraction` of scored blocks, then unscored blocks with enough words."""
    excluded = set(protected) | set(skip)
    scored = sorted((b for b in blocks if b.id in scores and b.id not in excluded and b.level),
                    key=lambda b: scores[b.id].score)
    take = math.ceil(fraction * len([b for b in blocks if b.id in scores])) if fraction > 0 else 0
    chosen = [b.id for b in scored[:take]]
    chosen += [b.id for b in blocks if b.level and b.id not in scores and b.id not in excluded
               and b.words >= min_unscored_words]
    return chosen


def build_judge_prompt(scope: str, blocks: list[Block], scores: dict[str, Relevance]) -> str:
    parts = []
    for b in blocks:
        r = scores.get(b.id)
        if r is None:
            near = "  (not scored: too short)"
        else:
            near = "\n".join(f"  - {c} (similarity {s:.2f}): {t[:EVIDENCE_CHARS]!r}"
                             for (c, s), t in zip(r.nearest, r.nearest_text or ("",) * len(r.nearest)))
        parts.append(f"[{b.id}] {' > '.join(b.heading_path)} ({b.words} words)\n\"\"\"\n{b.text[:BLOCK_CHARS]}\n\"\"\"\n"
                     f"Nearest course material:\n{near}")
    return (
        "You are judging whether blocks of a study guide belong in it. The guide's scope:\n"
        f"{scope or '(no scope given; judge by the nearest course material only)'}\n\n"
        "For each block answer 'delete' if it is outside that scope or nothing in the course material shown "
        "supports teaching it, otherwise 'keep'. Core derivations, definitions, recipes and worked problems on "
        "the guide's own topic are 'keep' even when the nearest material is weak. Be conservative: delete only "
        "what is clearly out of scope. Return JSON {\"verdicts\": [{\"block\", \"verdict\", \"rationale\"}]} with one "
        "entry per block.\n\n" + "\n\n".join(parts) + "\n")


def parse_judge(data: dict, blocks_by_id: dict[str, Block], candidates: list[str], start: int,
                scores: dict[str, Relevance]) -> list[Edit]:
    edits, n = [], start
    for v in data.get("verdicts", []):
        bid, verdict = v.get("block"), v.get("verdict")
        if bid not in candidates:
            raise ReviseError(f"judge: block {bid!r} was not one of the blocks asked about")
        if verdict not in ("keep", "delete"):
            raise ReviseError(f"judge: verdict for {bid} must be 'keep' or 'delete', got {verdict!r}")
        if verdict == "keep":
            continue
        block, r = blocks_by_id[bid], scores.get(bid)
        edits.append(Edit(
            id=f"rel-{n:03d}", type="delete", stage="relevance", targets=[bid], rationale="judge: " + v.get("rationale", ""),
            evidence=[c for c, _ in r.nearest] if r else [], severity="medium" if block.words > 150 else "low",
            confidence=0.5))
        n += 1
    return edits


def judge_edits(llm, scope: str, blocks_by_id: dict[str, Block], candidates: list[str], scores: dict[str, Relevance],
                start: int = 1) -> list[Edit]:
    edits: list[Edit] = []
    for i in range(0, len(candidates), BATCH):
        batch = candidates[i:i + BATCH]
        data = llm.generate_structured(build_judge_prompt(scope, [blocks_by_id[b] for b in batch], scores), JUDGE_SCHEMA)
        edits += parse_judge(data, blocks_by_id, batch, start + len(edits), scores)
    return edits
