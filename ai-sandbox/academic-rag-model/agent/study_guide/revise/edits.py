# agent/study_guide/revise/edits.py
"""The edit report: typed proposals from every stage, validated before review."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agent.study_guide.revise.segment import Block

EDIT_TYPES = ("delete", "shrink", "merge", "link", "fix", "move", "retitle", "note")
NEEDS_REPLACEMENT = ("shrink", "link", "retitle", "merge")


class ReviseError(Exception):
    pass


@dataclass
class Edit:
    id: str
    type: str
    targets: list[str]
    rationale: str
    stage: str = "relevance"
    evidence: list[str] = field(default_factory=list)
    severity: str = "medium"
    confidence: float = 0.5
    replacement: str | None = None
    quote: str | None = None
    anchor: str | None = None
    protected: bool = False
    conflicts: list[str] = field(default_factory=list)


@dataclass
class EditReport:
    guide_path: str
    guide_sha256: str
    created_at: str
    blocks: list[dict]
    edits: list[Edit]
    protected_blocks: list[str]


def save_report(report: EditReport, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(report), indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def load_report(path: str | Path) -> EditReport:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return EditReport(data["guide_path"], data["guide_sha256"], data["created_at"], data["blocks"],
                          [Edit(**e) for e in data["edits"]], data["protected_blocks"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as err:
        raise ReviseError(f"cannot read edit report {path}: {err}") from err


def validate_report(report: EditReport, blocks: list[Block]) -> list[str]:
    known, problems, seen = {b.id for b in blocks}, [], set()
    for e in report.edits:
        if e.id in seen:
            problems.append(f"duplicate edit id {e.id}")
        seen.add(e.id)
        if e.type not in EDIT_TYPES:
            problems.append(f"{e.id}: unknown edit type {e.type!r}")
            continue
        if not e.targets:
            problems.append(f"{e.id}: no targets")
        for t in e.targets:
            if t not in known:
                problems.append(f"{e.id}: unknown block {t}")
        if e.type in NEEDS_REPLACEMENT and not e.replacement:
            problems.append(f"{e.id}: {e.type} needs a replacement")
        if e.type == "fix" and e.replacement is None:
            problems.append(f"{e.id}: fix needs a replacement")
        if e.type == "merge" and len(e.targets) < 2:
            problems.append(f"{e.id}: merge needs at least two targets")
        if e.type == "move" and (len(e.targets) != 1 or e.anchor not in known):
            problems.append(f"{e.id}: move needs one target and an anchor block")
    return problems


def mark_conflicts(report: EditReport) -> None:
    by_block: dict[str, list[Edit]] = {}
    for e in report.edits:
        for t in e.targets:
            by_block.setdefault(t, []).append(e)
    for e in report.edits:
        e.conflicts = sorted({o.id for t in e.targets for o in by_block[t] if o.id != e.id})
