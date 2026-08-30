"""
rag_agent.py
A RAG tutoring agent grounded in the academic-hub corpus (spec:
docs/superpowers/specs/2026-08-30-rag-agent-design.md). One core
function, answer_question(), serves both usage modes named in the
original project intent -- a callable utility for other code, and an
interactive chat (this module's own main()) -- by keeping conversation
history an explicit input/output rather than internally-owned state.
"""
from __future__ import annotations

from dataclasses import dataclass

from gemini_utils import call_with_retries
from index_card import GENERATION_MODEL
from index_search import PassageResult


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    text: str


@dataclass
class Citation:
    chunk_id: str
    file_id: str
    path: str
    citation: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]


def _diversify_by_file(results: list[PassageResult], max_per_file: int) -> list[PassageResult]:
    """Caps how many of the top-ranked passages can come from the same
    file, preserving relevance order otherwise -- a comparative question
    ("how do two textbooks treat this") needs material from multiple
    sources to actually be answerable as a comparison (spec §4)."""
    per_file_count: dict[str, int] = {}
    kept = []
    for r in results:
        if per_file_count.get(r.file_id, 0) >= max_per_file:
            continue
        per_file_count[r.file_id] = per_file_count.get(r.file_id, 0) + 1
        kept.append(r)
    return kept


_REFORMULATE_PROMPT_TEMPLATE = """Given this recent conversation and a follow-up question, rewrite \
the follow-up as a standalone question that makes sense with no other context -- preserve its \
intent exactly, just make it self-contained. Respond with ONLY the rewritten question, nothing else.

Recent conversation:
{history_block}

Follow-up question: {question}

Standalone question:"""


def _reformulate_query(question: str, history: list[Turn], client) -> str:
    """Condenses a follow-up ("explain that differently") into a
    standalone, retrievable query using recent conversation history --
    only called when history is non-empty (spec §4/§5 -- the caller,
    answer_question(), skips this entirely on the first turn)."""
    recent = history[-6:]  # last 3 exchanges -- enough context to resolve most follow-ups
    history_block = "\n".join(f"{t.role}: {t.text}" for t in recent)
    prompt = _REFORMULATE_PROMPT_TEMPLATE.format(history_block=history_block, question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=GENERATION_MODEL, contents=prompt,
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    ))
    return (response.text or question).strip()
