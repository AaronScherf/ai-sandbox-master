"""
tutor_diagnosis.py
Four LLM-calling functions closing the loop between rag_agent's
grounded Q&A and the student's own problem-set workflow -- spec:
docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md. Each
mirrors rag_agent._generate_answer()'s existing shape: build a prompt,
call_with_retries, return/parse the result. Kept out of rag_agent.py
for the same isolation reason viz/ and problem_gen/ are their own
packages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from common.gemini_utils import call_with_retries
from indexer.index_search import PassageResult
from rag.rag_agent import TUTOR_MODEL


@dataclass
class Diagnosis:
    text: str          # what the draft covered correctly, what's missing or wrong --
                        # each claim grounded back to the reference answer/excerpts
    gap_tag: str        # short free-text label, e.g. "vacuous-case-overlooked"
    correctness: int    # 0-5
    rigor: int           # 0-5
    course_fit: int      # 0-5


class DiagnosisParseError(ValueError):
    """Raised when a diagnosis response is missing or malforms its
    CORRECTNESS/RIGOR/COURSE_FIT/GAP_TAG lines -- surfaced rather than
    silently defaulting a score to 0, which would corrupt every later
    /summarize rubric average with fabricated data."""


_DIAGNOSIS_PROMPT_TEMPLATE = """You are comparing a student's own attempt at a problem against a \
reference answer grounded in their course materials. Identify what the attempt covers correctly, \
and what's missing, incorrect, or under-justified -- ground each claim you make back to the \
reference answer or the excerpts below, the same way you would cite a source.

Then score the attempt on three 0-5 scales:
- CORRECTNESS: does it reach the right conclusion through valid reasoning?
- RIGOR: is each step justified or proven rather than asserted -- are edge cases and assumptions \
addressed the way the reference does?
- COURSE_FIT: does it use the course's own notation, definitions, and framing (as reflected in the \
excerpts) rather than generic phrasing?

End your response with exactly these four lines, in this order, and nothing after them:
CORRECTNESS: <0-5>
RIGOR: <0-5>
COURSE_FIT: <0-5>
GAP_TAG: <a short kebab-case label for the single most important gap, e.g. vacuous-case-overlooked>

Reference answer:
{reference_answer}

Excerpts the reference answer was grounded in:
{excerpts_block}

Question: {question}

Student's attempt:
{draft}

Diagnosis:"""


_DIAGNOSIS_LINE_PATTERN = re.compile(
    r"CORRECTNESS:\s*(\d+)\s*\n"
    r"RIGOR:\s*(\d+)\s*\n"
    r"COURSE_FIT:\s*(\d+)\s*\n"
    r"GAP_TAG:\s*(.+)",
    re.IGNORECASE,
)


def diagnose_draft(
    question: str, reference_answer: str, passages: list[PassageResult],
    draft: str, client,
) -> Diagnosis:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    prompt = _DIAGNOSIS_PROMPT_TEMPLATE.format(
        reference_answer=reference_answer, excerpts_block=excerpts_block,
        question=question, draft=draft,
    )
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    raw = (response.text or "").strip()
    match = _DIAGNOSIS_LINE_PATTERN.search(raw)
    if match is None:
        raise DiagnosisParseError(
            f"diagnosis response missing CORRECTNESS/RIGOR/COURSE_FIT/GAP_TAG lines: {raw!r}"
        )
    text = raw[:match.start()].strip()
    correctness, rigor, course_fit, gap_tag = match.groups()
    return Diagnosis(
        text=text, gap_tag=gap_tag.strip(),
        correctness=int(correctness), rigor=int(rigor), course_fit=int(course_fit),
    )
