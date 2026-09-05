"""
generator.py
Retrieves the student's own real problems (style anchor) and textbook
content (correctness anchor) for a topic, then generates a new,
self-verified practice problem via a local Ollama model (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md). One
public entry point, generate_problem().
"""
from __future__ import annotations

from dataclasses import dataclass

from indexer.index_card import load_courses
from indexer.index_search import search_passages
from problem_gen.llm_gen import generate_and_verify


@dataclass
class ProblemSource:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    root: str
    role: str  # "style" | "content"


@dataclass
class GeneratedProblem:
    problem_text: str
    solution_text: str
    sources: list[ProblemSource]


def _match_known_course(question: str, roots: list[str]) -> str | None:
    """Substring-matches the question against every known course name
    across the given roots (normalizing '-'/' ' so 'math camp' and
    'math-camp' both match) -- returns the first hit, or None if no
    known course name appears in the text, in which case
    generate_problem() falls through to search()'s own top-3
    similarity-based candidate selection unchanged."""
    known: set[str] = set()
    for root in roots:
        known.update(load_courses(root).keys())
    normalized_question = question.lower().replace("-", " ")
    for course in known:
        if course.lower().replace("-", " ") in normalized_question:
            return course
    return None


def generate_problem(
    query: str, roots: list[str], client, course: str | None = None,
    style_top_k: int = 3, content_top_k: int = 4,
) -> GeneratedProblem | None:
    """Returns None if there are no style examples to ground a new
    problem on this topic/course, or if generation+verification never
    succeeds (e.g. Ollama not running) -- callers must handle this
    being unavailable and fall back to normal Q&A, never treat problem
    generation as a hard dependency."""
    if course is None:
        course = _match_known_course(query, roots)

    style_passages = search_passages(
        roots, query, client, course=course, doc_type="problem_set", top_k=style_top_k,
    )
    if not style_passages:
        return None

    content_passages = search_passages(
        roots, query, client, course=course, doc_type="textbook", top_k=content_top_k,
    )

    generated = generate_and_verify(
        query, [p.text for p in style_passages], [p.text for p in content_passages],
    )
    if generated is None:
        return None
    problem_text, solution_text = generated

    sources = [
        ProblemSource(
            chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root, role="style",
        )
        for p in style_passages
    ] + [
        ProblemSource(
            chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root, role="content",
        )
        for p in content_passages
    ]
    return GeneratedProblem(problem_text=problem_text, solution_text=solution_text, sources=sources)
