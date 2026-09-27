"""
session_log.py
Per-course, append-only log of REPL tutoring events (answer / draft /
hint / verify) -- spec: docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md
§8. Stored as JSON Lines under <academic_hub_root>/.session_log/<course>.jsonl,
matching where .reports/, .viz/, and .problem_corpus/ already live
(rag/report_builder.py's report_path() convention) -- derived,
corpus-grounded content rooted alongside the corpus itself, not under
academic-rag-model/. JSON Lines rather than a single JSON array so each
event is an independent append (open(path, "a")), not a
read-modify-write of the whole file on every action.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from rag.rag_agent import Citation


@dataclass
class Event:
    type: str              # "answer" | "draft" | "hint" | "verify"
    course: str
    unit: str | None       # e.g. "homework_3"
    question: str
    text: str               # the generated output: answer / diagnosis / hint / verify text
    citations: list[Citation]
    timestamp: str          # ISO 8601
    gap_tag: str | None = None       # set only for type == "draft"
    correctness: int | None = None   # set only for type == "draft"
    rigor: int | None = None         # set only for type == "draft"
    course_fit: int | None = None    # set only for type == "draft"


def _log_path(roots: list[str], course: str) -> str:
    return os.path.join(roots[0], ".session_log", f"{course}.jsonl")


def append_event(roots: list[str], event: Event) -> None:
    path = _log_path(roots, event.course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event)) + "\n")


def load_events(roots: list[str], course: str, unit: str | None = None) -> list[Event]:
    path = _log_path(roots, course)
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            data["citations"] = [Citation(**c) for c in data["citations"]]
            events.append(Event(**data))
    if unit is not None:
        events = [e for e in events if e.unit == unit]
    return events
