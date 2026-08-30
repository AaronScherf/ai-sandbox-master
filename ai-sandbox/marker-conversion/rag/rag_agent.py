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

import argparse
import os
from dataclasses import dataclass

from common.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult, search_passages


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


TUTOR_MODEL = "gemini-3.1-flash-lite"  # revised 2026-08-30, confirmed live:
# originally set to gemini-3.6-flash on the assumption that tutoring's
# reasoning demands needed a step up from this project's cheap tier --
# untested at the time, just a heuristic. A real side-by-side comparison
# (same question, same retrieved passages, both models) showed no
# meaningful quality or coverage difference -- correct math, accurate
# citations, same key points covered either way. Switched back to the
# cheaper tier; the assumption that a pricier model was *necessary*
# didn't hold up against actual output. Kept as its own constant here
# (not importing index_card.GENERATION_MODEL directly, even though the
# value is currently identical) since tutoring and card-generation are
# conceptually distinct choices that happen to agree right now, not one
# setting reused -- they could diverge again later without this being
# a stale/forgotten duplicate.

_ANSWER_PROMPT_TEMPLATE = """You are tutoring a student using ONLY the excerpts below, drawn from \
their own course materials. Answer their question clearly and thoroughly, the way a good TA would \
explain it -- but do not introduce any claim, fact, or worked step that isn't supported by the \
excerpts. If the excerpts don't actually contain enough to answer the question, say so plainly \
rather than filling the gap from general knowledge.

When you use something from an excerpt, cite it inline using the citation label given with it \
(e.g. "(§3.7, p. 44)"), so the student can find it in their own materials.
{history_block}
Excerpts:
{excerpts_block}

Question: {question}

Answer:"""


def _generate_answer(question: str, history: list[Turn], passages: list[PassageResult], client) -> str:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    history_block = ""
    if history:
        recent = "\n".join(f"{t.role}: {t.text}" for t in history[-6:])
        history_block = f"\nRecent conversation, for continuity:\n{recent}\n"
    prompt = _ANSWER_PROMPT_TEMPLATE.format(
        history_block=history_block, excerpts_block=excerpts_block, question=question,
    )
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()


def answer_question(
    academic_hub_root: str, question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3,
) -> AnswerResult:
    """The core function serving both usage modes (spec §3/§6): a
    callable utility (call once, use the AnswerResult, done) and the
    interactive chat below (thread .history back in on the next call).
    Stateless per call -- history is an explicit input/output, not
    owned internally, which is what lets both modes share this one
    function without a database or session files."""
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    passages = search_passages(academic_hub_root, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
    citations = [
        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation)
        for p in passages
    ]
    updated_history = history + [Turn(role="user", text=question), Turn(role="assistant", text=answer)]
    return AnswerResult(answer=answer, citations=citations, history=updated_history)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive tutor grounded in the academic-hub corpus.")
    parser.add_argument("--academic-hub", default=os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub"))
    parser.add_argument("--course", default=None)
    args = parser.parse_args()

    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    history: list[Turn] = []
    print("Ask a question (Ctrl+C to exit).")
    while True:
        question = input("> ").strip()
        if not question:
            continue
        result = answer_question(args.academic_hub, question, client, history=history, course=args.course)
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - {c.path} ({c.citation})")
        print()
        history = result.history


if __name__ == "__main__":
    main()
