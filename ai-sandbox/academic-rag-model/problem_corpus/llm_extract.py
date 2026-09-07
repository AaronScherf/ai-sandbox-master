"""
llm_extract.py
One Gemini call per detected problem span, turning its raw text into a
structured record: a cleaned problem statement, the solution verbatim
if one is present (else None), and a short topic tag (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 4). Always Gemini -- unlike problem_gen/llm_gen.py and
viz/llm_fallback.py, there is no local-Ollama backend toggle here: this
only runs as an occasional offline batch tool, not a live per-request
path, so there's no equivalent reliability-vs-latency tradeoff to weigh.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from common.gemini_utils import call_with_retries

PROBLEM_CORPUS_GEMINI_MODEL = os.environ.get("PROBLEM_CORPUS_GEMINI_MODEL", "gemini-3.1-flash-lite")

_EXTRACTION_PROMPT_TEMPLATE = """You are extracting one practice problem from a student's own course materials \
for a structured problem corpus. Below is one detected problem, possibly followed by the student's own worked \
attempt at a solution.

Source text:
{span_text}

Respond in exactly this format, with all three sections present:

## Problem
<the problem statement, cleaned up -- remove any leading label like "Practice Problem 3." or a bare "1.", but \
keep the actual mathematical content verbatim, do not rephrase or simplify it>

## Solution
<the student's worked solution, verbatim, if the source text above actually contains one -- if there is no \
solution attempt in the source text at all, respond with exactly the word NONE for this section and nothing else>

## Topic
<a short, specific topic tag for this problem, e.g. "compactness" or "diagonalizability" -- not a broad subject \
area like "real analysis" or "linear algebra">
"""

_SECTION_PATTERN = re.compile(
    r"##\s*Problem\s*\n(.*?)\n##\s*Solution\s*\n(.*?)\n##\s*Topic\s*\n(.*)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ExtractedRecord:
    problem_text: str
    solution_text: str | None
    topic_tag: str
    # No solution_provenance field here -- the model reports what it
    # found (solution_text or None), and extractor.py derives
    # solution_provenance deterministically when assembling the final
    # stored record ("student_attempt" if solution_text is not None,
    # else None), rather than asking the model to name it. Keeps the
    # "never verified" guarantee independent of model output.


def _build_extraction_prompt(span_text: str) -> str:
    return _EXTRACTION_PROMPT_TEMPLATE.format(span_text=span_text)


def _parse_response(response_text: str) -> ExtractedRecord | None:
    match = _SECTION_PATTERN.search(response_text)
    if match is None:
        return None
    problem_text = match.group(1).strip()
    solution_raw = match.group(2).strip()
    topic_tag = match.group(3).strip()
    if not problem_text or not topic_tag:
        return None
    solution_text = None if solution_raw.upper() == "NONE" else solution_raw
    return ExtractedRecord(problem_text=problem_text, solution_text=solution_text, topic_tag=topic_tag)


def extract_record(span_text: str, client) -> ExtractedRecord | None:
    """One Gemini call via common.gemini_utils.call_with_retries -- returns
    None (not raising) if the call fails after retries or the response
    doesn't parse into the three expected sections. A None here is a
    per-span failure, isolated from the rest of the file by extractor.py."""
    prompt = _build_extraction_prompt(span_text)
    try:
        response = call_with_retries(lambda: client.models.generate_content(
            model=PROBLEM_CORPUS_GEMINI_MODEL, contents=prompt, config={"temperature": 0.1},
        ))
        response_text = (response.text or "").strip()
    except Exception as err:
        print(f"WARNING: Gemini call to model '{PROBLEM_CORPUS_GEMINI_MODEL}' failed after retries ({err})")
        return None
    return _parse_response(response_text)
