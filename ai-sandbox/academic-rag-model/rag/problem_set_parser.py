"""
problem_set_parser.py
Extracts a single question's text from a fresh, unsolved problem-set
file, for /hint -- spec: docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md
§6. Scoped to clean files like academic-hub's homework_3.md -- NOT the
historical _notes/_guided files, which mix questions and solutions in
ways this parser isn't built to separate (spec §2).
"""
from __future__ import annotations

import re


class QuestionNotFoundError(ValueError):
    """Raised when question_ref doesn't match any heading or numbered
    item in the file -- surfaced directly rather than guessing, since a
    wrong guess would silently generate a hint for the wrong question."""


_STOP_HEADING = re.compile(r"^##\s+")
_STOP_NUMBERED = re.compile(r"^\d+\.\s+")


def extract_question(file_path: str, question_ref: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ref = re.escape(question_ref)
    heading_pattern = re.compile(rf"^##\s+Question\s+{ref}\b")
    numbered_pattern = re.compile(rf"^{ref}\.\s+")

    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if heading_pattern.match(stripped) or numbered_pattern.match(stripped):
            start = i
            break
    if start is None:
        raise QuestionNotFoundError(f"no question matching {question_ref!r} found in {file_path}")

    # Runs until the next top-level heading or numbered item, whichever
    # comes first -- covers both conventions seen across courses
    # (econometrics uses bare numbered items, microecon uses ## Question
    # N headings), so a numbered item's text doesn't run into a later
    # heading's, or vice versa.
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if _STOP_HEADING.match(stripped) or _STOP_NUMBERED.match(stripped):
            end = i
            break

    return "".join(lines[start:end]).strip()
