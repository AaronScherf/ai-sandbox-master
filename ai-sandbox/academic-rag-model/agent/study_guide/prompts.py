# agent/study_guide/prompts.py
"""Frozen prompt templates for the draft stage.

TUTOR_V1 is a copy of rag_agent._ANSWER_PROMPT_TEMPLATE taken on 2026-10-05 so a baseline
reproduction does not change if the tutor's prompt is edited later (see the recovered recipe in
docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md). GUIDE_V1 is a
study-guide oriented prompt for new work."""
from __future__ import annotations

TUTOR_V1_TEMPLATE = """You are tutoring a student using ONLY the excerpts below, drawn from \
their own course materials. Answer their question clearly and thoroughly, the way a good TA would \
explain it -- but do not introduce any claim, fact, or worked step that isn't supported by the \
excerpts. If the excerpts don't actually contain enough to answer the question, say so plainly \
rather than filling the gap from general knowledge.

When you use something from an excerpt, cite it inline using the citation label given with it \
(e.g. "(§3.7, p. 44)"), so the student can find it in their own materials.
{history_block}{gap_hint_block}
Excerpts:
{excerpts_block}

Question: {question}

Answer:"""

_TUTOR_V1_SUFFIX = ("Use only these excerpts. Cite each substantive claim by its exact source label. "
                    "State plainly where the excerpts do not support an answer.")

GUIDE_V1_TEMPLATE = """You are writing one section of a thorough study guide for a graduate student, \
using ONLY the excerpts below, which come from the student's own course materials (textbooks, class \
notes, slides, recitations). Do not introduce any claim, fact, or worked step that is not supported by \
the excerpts; if they do not contain enough, say so plainly instead of filling the gap from general \
knowledge.

Write at least 800 words, organized under short ### sub-headings. Build the explanation step by step: \
assumptions, the statistic and how it is computed, its distribution and the decision rule, intuition, \
when it is valid or breaks down, and common pitfalls. Where the sources use different notation or \
disagree (for example a textbook versus class notes), say so explicitly and cite both. Class notes may \
contain transcription errors; prefer the textbook where they conflict and say so.

Cite every substantive point inline with the citation label given with its excerpt, for example \
"(§3.7, p. 44)".

Section: {title}
Focus: {instruction}

Excerpts:
{excerpts_block}

Section text:"""


def _excerpts_block(excerpts: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"[{citation}]\n{text}" for citation, text in excerpts)


def tutor_v1_question(title: str, instruction: str) -> str:
    return f"{title}. {instruction} {_TUTOR_V1_SUFFIX}"


def tutor_v1_prompt(question: str, excerpts: list[tuple[str, str]]) -> str:
    return TUTOR_V1_TEMPLATE.format(
        history_block="", gap_hint_block="", excerpts_block=_excerpts_block(excerpts), question=question)


def guide_v1_prompt(title: str, instruction: str, excerpts: list[tuple[str, str]]) -> str:
    return GUIDE_V1_TEMPLATE.format(title=title, instruction=instruction, excerpts_block=_excerpts_block(excerpts))
