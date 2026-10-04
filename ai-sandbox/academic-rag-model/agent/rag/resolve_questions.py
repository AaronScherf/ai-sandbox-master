"""
resolve_questions.py
Answers the `[Question]` tags in Excalidraw notes: grounded in the course
corpus when it can be (the same key-term + retrieval + grounded check /hint
uses), clearly labeled when it can't. Answers go to a per-note sidecar; the
.rag.md gets resolved markers (core/indexer/questions.py).

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from agent.rag.rag_agent import _extract_key_terms, _term_match_count, retrieve_passages
from core.env.excalidraw_text import QUESTION_TAG_RE, split_labeled_segments
from core.env.gemini_utils import call_with_retries
from core.indexer.questions import Entry, Tag

RESOLVER_MODEL = "gemini-3.6-flash"  # the stronger tier: answers are persisted and indexed
_CONTEXT_CHARS = 1500
_NEIGHBOR_CHARS = 800
_STORED_CONTEXT_CHARS = 600

_ANSWER_PROMPT_TEMPLATE = """A student wrote this open question in the margin of their lecture notes. \
Explain the answer so the student can understand it, with the reasoning spelled out. Use LaTeX \
($...$ / $$...$$) for math.

The student's handwriting around the question:
{context}

{slides_block}{excerpts_block}Open question: {question}

{grounding_instruction}
Respond with ONLY the explanation in markdown -- no preamble, no code fence."""

_GROUNDED_INSTRUCTION = (
    "Base the explanation on the course excerpts above and do not claim anything they contradict."
)
_UNGROUNDED_INSTRUCTION = (
    "No course material supports this question. Answer from general knowledge and say plainly "
    "where you are unsure."
)


def question_context(raw_body: str, ordinal: int) -> tuple[str, list[str]]:
    """The text around the ordinal-th tag of a raw transcript body (frontmatter
    already stripped): a window of its own block, plus the adjacent slide
    blocks. Splitting preserves tag order, so counting tags across segments in
    order finds the same tag the sidecar's ordinal refers to."""
    segments = split_labeled_segments(raw_body)
    seen = 0
    for idx, (_label, text) in enumerate(segments):
        matches = list(QUESTION_TAG_RE.finditer(text))
        if seen + len(matches) >= ordinal:
            match = matches[ordinal - seen - 1]
            half = _CONTEXT_CHARS // 2
            excerpt = text[max(0, match.start() - half): min(len(text), match.end() + half)].strip()
            neighbors = [
                segments[j][1][:_NEIGHBOR_CHARS]
                for j in (idx - 1, idx + 1)
                if 0 <= j < len(segments) and segments[j][0] == "Slide"
            ]
            return excerpt, neighbors
        seen += len(matches)
    return "", []


def build_answer_prompt(question: str, context: str, neighbor_slides: list[str], passages: list | None) -> str:
    slides_block = ""
    if neighbor_slides:
        slides_block = "Lecture slide content beside the question:\n" + "\n\n---\n\n".join(neighbor_slides) + "\n\n"
    excerpts_block = ""
    if passages:
        excerpts = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
        excerpts_block = f"Course excerpts:\n{excerpts}\n\n"
    return _ANSWER_PROMPT_TEMPLATE.format(
        context=context, slides_block=slides_block, excerpts_block=excerpts_block, question=question,
        grounding_instruction=_GROUNDED_INSTRUCTION if passages else _UNGROUNDED_INSTRUCTION,
    )


def resolve_question(
    tag: Tag, context: str, neighbors: list[str], *, client, roots: list[str], course: str | None,
    model: str, exclude_basenames: set[str], retrieve=retrieve_passages, extract=_extract_key_terms,
) -> Entry:
    """One question -> one Entry. Raises on any failure (including an empty
    answer) so the caller records nothing for it. Grounded means a passage
    survived own-note exclusion and (no key terms, or one mentions a key
    term) -- /hint's check, plus a guard so an empty retrieval can never count
    as grounded."""
    key_terms = extract(f"{tag.text}\n{context}", client)
    found = retrieve(roots, f"{tag.text}\n{context[:300]}", client, course=course, key_terms=key_terms)
    passages = [p for p in found if os.path.basename(p.path) not in exclude_basenames]
    grounded = bool(passages) and (not key_terms or any(_term_match_count(p.text, key_terms) for p in passages))
    prompt = build_answer_prompt(tag.text, context, neighbors, passages if grounded else None)
    response = call_with_retries(lambda: client.models.generate_content(
        model=model, contents=prompt, config={"temperature": 0.2},
    ))
    answer = (response.text or "").strip()
    if not answer:
        raise ValueError(f"model returned an empty answer for {tag.qid}")
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model=model,
        resolved_at=datetime.now(timezone.utc).isoformat(),
        context=" ".join(context.split())[:_STORED_CONTEXT_CHARS], answer=answer,
        sources=[f"{p.path} ({p.citation})" if p.citation else p.path for p in passages] if grounded else [],
    )
