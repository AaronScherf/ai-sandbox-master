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
from rag.session_log import Event


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
    r"\*{0,2}CORRECTNESS\*{0,2}:\*{0,2}\s*\*{0,2}(\d+)(?:\s*/\s*5)?\*{0,2}\s*\n"
    r"\*{0,2}RIGOR\*{0,2}:\*{0,2}\s*\*{0,2}(\d+)(?:\s*/\s*5)?\*{0,2}\s*\n"
    r"\*{0,2}COURSE_FIT\*{0,2}:\*{0,2}\s*\*{0,2}(\d+)(?:\s*/\s*5)?\*{0,2}\s*\n"
    r"\*{0,2}GAP_TAG\*{0,2}:\*{0,2}\s*\*{0,2}(.+?)\*{0,2}\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Tolerates markdown emphasis around labels/values (**CORRECTNESS:** 3) and
# an optional "/5" suffix (CORRECTNESS: 3/5) -- gemini-3.1-flash-lite
# routinely formats its own instructed output this way despite the prompt
# asking for exactly "CORRECTNESS: <0-5>". A final-review finding: the
# original strict pattern rejected this as malformed and crashed the REPL
# on ordinary model output, not just genuinely broken responses.


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
    correctness, rigor, course_fit = int(correctness), int(rigor), int(course_fit)
    if not all(0 <= score <= 5 for score in (correctness, rigor, course_fit)):
        raise DiagnosisParseError(
            f"diagnosis response has an out-of-range rubric score (expected 0-5): "
            f"correctness={correctness}, rigor={rigor}, course_fit={course_fit}"
        )
    return Diagnosis(
        text=text, gap_tag=gap_tag.strip(),
        correctness=correctness, rigor=rigor, course_fit=course_fit,
    )


_HINT_PROMPT_TEMPLATE = """A student is about to attempt the question below, using ONLY the excerpts \
from their own course materials given here. Give them a motivating sketch of the right technique or \
theorem to reach for -- enough to get them unstuck and pointed in the right direction.

Do NOT state the final answer, a verdict (e.g. True/False), or a worked derivation. If you find \
yourself about to write out the conclusion, stop and describe the approach instead.

Excerpts:
{excerpts_block}

Question: {question}

Hint:"""


def generate_hint(question: str, passages: list[PassageResult], client) -> str:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    prompt = _HINT_PROMPT_TEMPLATE.format(excerpts_block=excerpts_block, question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()


_UNGROUNDED_HINT_PROMPT_TEMPLATE = """A student is about to attempt the question below. None of their \
own course materials matched it closely enough to ground a hint in, so use your own general knowledge \
of the subject instead. Give them a motivating sketch of the right technique or theorem to reach for \
-- enough to get them unstuck and pointed in the right direction.

Do NOT state the final answer, a verdict (e.g. True/False), or a worked derivation. If you find \
yourself about to write out the conclusion, stop and describe the approach instead.

Question: {question}

Hint:"""


def generate_ungrounded_hint(question: str, client) -> str:
    """Fallback for /hint's own low-confidence case (rag_agent.py):
    retrieve_passages() found nothing that mentions the question's own
    extracted key terms at all -- usually because the right course
    material simply isn't in the corpus (confirmed live, 2026-09-28:
    homework_3's Question 4 asks about Block Marschak/Luce, and no
    chunk anywhere in microecon's index mentions either). Rather than
    hand over a fluent, confidently-cited hint grounded in the wrong
    topic, this drops the excerpts entirely and asks the same cheap
    tutoring model to hint from its own general knowledge -- ungrounded
    and uncited, but on-topic beats confidently wrong. The caller is
    responsible for telling the student this hint isn't sourced from
    their own materials (see /hint's handler)."""
    prompt = _UNGROUNDED_HINT_PROMPT_TEMPLATE.format(question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()


VERIFY_MODEL = "gemini-3.6-flash"  # this project's existing "stronger" tier (already
# used for textbook conversion and transcription, indexer/index_card.py and
# textbook/convert_textbook.py) -- chosen over TUTOR_MODEL specifically because this
# call exists to catch reasoning errors the cheap tier makes; checking a cheap model's
# output with the same cheap model is weak evidence. Opt-in and per-question, not run
# on every query, so the cost difference doesn't compound the way it would if this
# were the default generation path.

_VERIFY_PROMPT_TEMPLATE = """Solve the following problem yourself, from first principles. Do not \
assume any prior answer is correct -- you have not been shown one. Show your full reasoning.

Question: {question}

Solution:"""


def generate_verification(question: str, client) -> str:
    prompt = _VERIFY_PROMPT_TEMPLATE.format(question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=VERIFY_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()


_SUMMARY_PROMPT_TEMPLATE = """Below is a session's worth of events from a student working through one \
unit of a course (their questions, your grounded answers, their own draft attempts and how those were \
diagnosed, and any independent verifications). Using only this history, write two sections:

## What we learned
Synthesize what the session actually covered, citing sources the same way the events themselves do.

## What to focus on
The recurring gaps and any unresolved discrepancies between a tutor answer and an independent \
verification, prioritized by how often they came up.

Session events:
{events_block}

Summary:"""


def _format_event(event: Event) -> str:
    lines = [f"[{event.type}] Q: {event.question}", event.text]
    if event.gap_tag:
        lines.append(f"(gap tag: {event.gap_tag})")
    if event.citations:
        lines.append("Citations: " + "; ".join(c.citation for c in event.citations))
    return "\n".join(lines)


def _rubric_averages_line(events: list[Event]) -> str | None:
    draft_events = [e for e in events if e.type == "draft"]
    if not draft_events:
        return None
    avg_correctness = sum(e.correctness for e in draft_events) / len(draft_events)
    avg_rigor = sum(e.rigor for e in draft_events) / len(draft_events)
    avg_course_fit = sum(e.course_fit for e in draft_events) / len(draft_events)
    return (
        f"Rubric averages this unit ({len(draft_events)} attempt(s)): "
        f"Correctness {avg_correctness:.1f}/5, Rigor {avg_rigor:.1f}/5, "
        f"Course-fit {avg_course_fit:.1f}/5"
    )


def summarize_unit(events: list[Event], client) -> str:
    events_block = "\n\n---\n\n".join(_format_event(e) for e in events)
    prompt = _SUMMARY_PROMPT_TEMPLATE.format(events_block=events_block)
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    text = (response.text or "").strip()
    stats_line = _rubric_averages_line(events)
    if stats_line:
        text = f"{text}\n\n{stats_line}"
    return text
