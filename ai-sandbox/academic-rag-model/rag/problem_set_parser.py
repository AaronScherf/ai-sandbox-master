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


_ANY_HEADING = re.compile(r"^##\s+")
_STOP_HEADING = re.compile(r"^##\s+")
_TOP_LEVEL_NUMBERED = re.compile(r"^\d+\.\s+")  # unindented (column 0) only --
# deliberately matched against the raw, unstripped line, not line.strip(),
# so an indented numbered sub-part (e.g. "   1. sub-part") never counts as
# a top-level item. Combined with heading-mode below (final-review fix):
# a file that has ANY "## Question" heading uses heading mode exclusively,
# since real problem sets put their own numbered sub-parts *inside* a
# heading's section (e.g. academic-hub's homework_1_solutions.md) -- the
# old dual-mode search treated every sub-part's "N. " line as its own
# question start/stop, truncating heading-style questions at their first
# sub-part. Numbered mode (no headings in the file at all) is unaffected.


def extract_question(file_path: str, question_ref: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ref = re.escape(question_ref)
    has_headings = any(_ANY_HEADING.match(line) for line in lines)

    if has_headings:
        start_pattern = re.compile(rf"^##\s+Question\s+{ref}\b")
        start = next((i for i, line in enumerate(lines) if start_pattern.match(line.strip())), None)
        if start is None:
            raise QuestionNotFoundError(f"no question matching {question_ref!r} found in {file_path}")
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if _STOP_HEADING.match(lines[i].strip()):
                end = i
                break
        return "".join(lines[start:end]).strip()

    start_pattern = re.compile(rf"^{ref}\.\s+")
    start = next((i for i, line in enumerate(lines) if start_pattern.match(line)), None)
    if start is None:
        raise QuestionNotFoundError(f"no question matching {question_ref!r} found in {file_path}")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _TOP_LEVEL_NUMBERED.match(lines[i]):
            end = i
            break
    return "".join(lines[start:end]).strip()
