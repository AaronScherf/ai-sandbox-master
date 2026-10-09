# agent/study_guide/revise/review.py
"""Review items for the interactive Artifact, and reading its decisions back."""
from __future__ import annotations

import json
from pathlib import Path

from agent.study_guide.revise.edits import EditReport, ReviseError
from agent.study_guide.revise.segment import segment, subtree_ids


def review_items(report: EditReport, body: str) -> list[dict]:
    blocks = segment(body)
    by_id = {b.id: b for b in blocks}
    items = []
    for e in report.edits:
        beneath = []
        if e.type in ("delete", "move"):
            for t in e.targets:
                if t in by_id:
                    beneath += [{"id": i, "heading": by_id[i].heading_path[-1] if by_id[i].heading_path else "",
                                 "words": by_id[i].words} for i in subtree_ids(blocks, t)[1:]]
        anchor = by_id.get(e.anchor) if e.anchor else None
        items.append({
            "id": e.id, "type": e.type, "stage": e.stage, "severity": e.severity, "confidence": e.confidence,
            "rationale": e.rationale, "evidence": e.evidence, "protected": e.protected, "conflicts": e.conflicts,
            "targets": e.targets, "quote": e.quote, "anchor": e.anchor,
            "before": "\n\n".join(by_id[t].text for t in e.targets if t in by_id), "after": e.replacement,
            "beneath": beneath, "anchor_heading": anchor.heading_path[-1] if anchor and anchor.heading_path else None,
        })
    return items


def write_review_items(report: EditReport, body: str, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(review_items(report, body), indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def accepted_ids(report: EditReport, decisions: dict[str, str]) -> set[str]:
    known = {e.id for e in report.edits}
    for key, value in decisions.items():
        if key not in known:
            raise ReviseError(f"unknown edit id in the decisions: {key!r}")
        if value not in ("accept", "reject"):
            raise ReviseError(f"decision for {key!r} must be 'accept' or 'reject', got {value!r}")
    return {k for k, v in decisions.items() if v == "accept"}
