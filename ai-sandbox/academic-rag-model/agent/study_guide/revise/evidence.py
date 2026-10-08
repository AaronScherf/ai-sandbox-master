# agent/study_guide/revise/evidence.py
"""Resolve the [revise] evidence rules to weighted, embedded chunks by reusing the plan machinery."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from agent.study_guide.plan import DROPPED, build_plan
from agent.study_guide.spec import GuideSpec, TopicSpec


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    citation: str
    weight: float
    embedding: tuple[float, ...]


def load_evidence(spec: GuideSpec, root: str, *, client=None, search=None, chunks=None, cards=None) -> list[EvidenceChunk]:
    if spec.revise is None or not spec.revise.evidence:
        return []
    topics = tuple(TopicSpec(f"evidence-{i}", "", (ev.rule,)) for i, ev in enumerate(spec.revise.evidence, 1))
    sub = dataclasses.replace(spec, topics=topics, comparisons=(), notes=())
    plan = build_plan(sub, root, client=client, search=search, chunks=chunks, cards=cards)
    if chunks is None:
        from core.indexer.chunk_index import load_chunks
        chunks = load_chunks(root, spec.course)
    by_id = {c["chunk_id"]: c for c in chunks}
    found: dict[str, EvidenceChunk] = {}
    for ev, topic in zip(spec.revise.evidence, plan.topics):
        for entry in topic.entries:
            chunk = by_id.get(entry.chunk_id)
            if entry.status == DROPPED or chunk is None or not chunk.get("embedding"):
                continue
            current = found.get(entry.chunk_id)
            if current is None or current.weight < ev.weight:
                found[entry.chunk_id] = EvidenceChunk(entry.chunk_id, entry.citation, ev.weight, tuple(chunk["embedding"]))
    return list(found.values())
