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
import re
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
    root: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]
    visualization: VizResult | None = None  # viz.viz_agent.VizResult -- not imported at
    # module level (see answer_question()'s function-scoped import below); resolvable
    # here only because this file already has `from __future__ import annotations`,
    # which makes every annotation a lazily-evaluated string.
    report_path: str | None = None  # rag.report_builder.build_report()'s return value --
    # None whenever report=False (default) or report generation itself failed
    generated_problem: GeneratedProblem | None = None  # problem_gen.generator.GeneratedProblem --
    # not imported at module level either, same reasoning as visualization above. No
    # import or alias is needed for this to resolve: `from __future__ import annotations`
    # (top of this file) makes every annotation a lazily-evaluated string, exactly like
    # `visualization: VizResult | None` above needs none either.


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


_PROBLEM_REQUEST_PATTERNS = [
    re.compile(r"\bpractice problem", re.IGNORECASE),
    re.compile(r"\bgive me a problem", re.IGNORECASE),
    re.compile(r"\bquiz me", re.IGNORECASE),
    re.compile(r"\banother (?:problem|exercise|question)\b", re.IGNORECASE),
    re.compile(r"\b(?:example|practice) (?:problem|question|exercise)", re.IGNORECASE),
    re.compile(r"\btest my (?:understanding|knowledge)", re.IGNORECASE),
]


def _looks_like_problem_request(question: str) -> bool:
    """Cheap keyword/regex intent check routing a question to
    problem_gen instead of the normal retrieval-and-answer flow (spec
    §5) -- checked against the raw question as typed, before any
    follow-up reformulation (reformulation exists to make a retrieval
    query standalone, which is orthogonal to classifying intent)."""
    return any(p.search(question) for p in _PROBLEM_REQUEST_PATTERNS)


_VISUALIZE_REQUEST_PATTERNS = [
    re.compile(r"\bvisuali[sz]e\b", re.IGNORECASE),
    re.compile(r"\bmake (?:a|me a) (?:graph|plot|diagram|chart)\b", re.IGNORECASE),
    re.compile(r"\bshow me a (?:graph|plot|diagram|chart|picture)\b", re.IGNORECASE),
    re.compile(r"\b(?:graph|plot|diagram|chart) (?:this|it)\b", re.IGNORECASE),
]


def _looks_like_visualize_request(question: str) -> bool:
    """Cheap keyword/regex check, mirroring _looks_like_problem_request,
    scoped specifically to the problem-generation branch of
    answer_question(). The normal Q&A path's `visualize` stays a pure
    caller-set flag (viz's own non-goal: deciding *when* a question
    warrants a visualization is left to the caller there) -- but
    problem generation itself is intent-routed, not flag-gated, so a
    student asking for a practice problem has no separate flag to set
    at all. An explicit in-text request is the only way to opt in on
    that path, alongside the existing `visualize` flag for callers that
    already set it (e.g. the REPL's --visualize)."""
    return any(p.search(question) for p in _VISUALIZE_REQUEST_PATTERNS)


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
    roots: list[str], question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3, visualize: bool = False, report: bool = False,
) -> AnswerResult:
    """The core function serving both usage modes (spec §3/§6): a
    callable utility (call once, use the AnswerResult, done) and the
    interactive chat below (thread .history back in on the next call).
    Stateless per call -- history is an explicit input/output, not
    owned internally, which is what lets both modes share this one
    function without a database or session files. roots is a list so a
    tutoring question can be grounded in passages from more than one
    corpus at once (e.g. academic-hub and research/ together).
    visualize=True additionally generates an interactive visualization
    for the question's concept (viz/, spec:
    docs/superpowers/specs/2026-09-02-visualization-agent-design.md) --
    grounded in the first root in `roots`, since a single concept's
    illustrative example doesn't need multi-root grounding the way
    citation retrieval does. report=True additionally combines the
    answer, citations, and (if present) the visualization into one
    self-contained HTML document (rag/report_builder.py, spec:
    docs/superpowers/specs/2026-09-05-combined-report-design.md) --
    independent of visualize: a report can be text+citations-only if no
    visualization exists, whether that's because it wasn't requested or
    the fallback degraded to None. Also applies on the problem-generation
    path (below), where it additionally includes the worked solution as
    its own section -- discovered missing entirely on that path and
    fixed 2026-09-06, the same integration gap visualize had until its
    own fix just above it."""
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    if _looks_like_problem_request(question):
        from problem_gen.generator import generate_problem  # function-scoped import,
        # same circular-import-avoidance / dependency-isolation pattern as viz's own
        # integration -- keeps this package's Ollama dependency out of every plain Q&A
        # caller's import path.
        generated = generate_problem(retrieval_query, roots, client, course=course)
        if generated is not None:
            problem_citations = [
                Citation(chunk_id=s.chunk_id, file_id=s.file_id, path=s.path, citation=s.citation, root=s.root)
                for s in generated.sources
            ]
            updated_history = history + [
                Turn(role="user", text=question), Turn(role="assistant", text=generated.problem_text),
            ]
            problem_visualization = None
            if visualize or _looks_like_visualize_request(question):
                from viz.viz_agent import generate_visualization  # function-scoped: same
                # dependency-isolation reasoning as the normal Q&A path's own import below.
                viz_context = f"{generated.problem_text}\n\n{generated.solution_text}"
                problem_visualization = generate_visualization(
                    question, context=viz_context, academic_hub_root=roots[0], course=course, client=client,
                )
            problem_report_path = None
            if report:
                from rag.report_builder import build_report, report_path  # function-scoped,
                # same dependency-isolation reasoning as the normal Q&A path's own import
                # below -- this branch previously never built a report at all regardless of
                # report=True, an integration gap discovered and fixed 2026-09-06 the same
                # way the visualize gap above was.
                reports_root = os.path.join(roots[0], ".reports")
                output_path = report_path(question, reports_root, course)
                problem_report_path = build_report(
                    question, generated.problem_text, problem_citations, problem_visualization,
                    output_path, solution=generated.solution_text,
                )
            return AnswerResult(
                answer=generated.problem_text, citations=problem_citations,
                history=updated_history, generated_problem=generated,
                visualization=problem_visualization, report_path=problem_report_path,
            )
        # generated is None (no style examples on this topic/course, or Ollama
        # unavailable/never verified) -- fall through to the normal Q&A path below on
        # this same question, same graceful-degradation principle as visualize=None.

    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
    citations = [
        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root)
        for p in passages
    ]
    updated_history = history + [Turn(role="user", text=question), Turn(role="assistant", text=answer)]

    visualization = None
    if visualize:
        from viz.viz_agent import generate_visualization  # function-scoped: keeps viz/'s
        # plotly (and, transitively on the fallback path, subprocess/network) dependency
        # out of every plain-Q&A caller's import path, matching index_search.py's own
        # function-scoped import of answer_question() for the same reason.
        viz_context = "\n\n".join(p.text for p in passages)
        visualization = generate_visualization(
            question, context=viz_context, academic_hub_root=roots[0], course=course, client=client,
        )

    report_path_value = None
    if report:
        from rag.report_builder import build_report, report_path  # function-scoped: keeps
        # report_builder.py's (and, when a visualization exists, transitively viz/'s) import
        # surface out of every caller that never sets report=True, matching this file's own
        # existing function-scoped import of generate_visualization above for the same reason.
        reports_root = os.path.join(roots[0], ".reports")
        output_path = report_path(question, reports_root, course)
        report_path_value = build_report(question, answer, citations, visualization, output_path)

    return AnswerResult(
        answer=answer, citations=citations, history=updated_history,
        visualization=visualization, report_path=report_path_value,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive tutor grounded in one or more indexed corpora.")
    parser.add_argument(
        "--root", action="append", default=None,
        help="Path to a corpus root's own .index/ (repeatable, e.g. --root academic-hub --root "
             "research -- grounds answers in passages from every root given). Default if omitted: "
             "[academic-hub].",
    )
    parser.add_argument("--course", default=None)
    parser.add_argument("--visualize", action="store_true",
                         help="Also generate an interactive visualization for each question's concept.")
    parser.add_argument("--report", action="store_true",
                         help="Also combine the answer, citations, and visualization (if any) into one "
                              "self-contained HTML report.")
    args = parser.parse_args()
    roots = args.root or [os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")]

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
        result = answer_question(
            roots, question, client, history=history, course=args.course,
            visualize=args.visualize, report=args.report,
        )
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.generated_problem:
            print(f"\n--- Solution ---\n{result.generated_problem.solution_text}\n")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        if result.report_path:
            print(f"  report: {result.report_path}")
        print()
        history = result.history


if __name__ == "__main__":
    main()
