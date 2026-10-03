"""
rag/report_builder.py
Combines one answer_question() call's question, answer text, citations,
and (optional) visualization into a single self-contained HTML document
(spec: docs/superpowers/specs/2026-09-05-combined-report-design.md). No
external dependencies (no CDN, no template engine) -- plain string
interpolation, matching the style already used throughout viz/.

`citations` and `visualization` below are typed only as lazily-evaluated
string annotations (this module has `from __future__ import
annotations`) -- deliberately not imported at module level from
rag_agent.py/viz_agent.py, matching AnswerResult.visualization's own
existing precedent in rag_agent.py, so a report=True, visualize=False
caller never pulls in either module's heavier dependencies just for a
type hint.

When callers request a combined report, build_markdown_summary() also
writes a tablet-readable Markdown copy under
academic_notes/<course>/summaries/ when the corpus root contains an
academic_notes/ vault.
"""
from __future__ import annotations

import html
import json
import os
import re
from urllib.parse import quote

_SLUG_MAX_LENGTH = 80


def _slugify(text: str) -> str:
    """Duplicated from viz.viz_agent._slugify rather than imported, per
    this module's own module-level-import ban above."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LENGTH].strip("-")
    return slug or "report"


def report_path(question: str, reports_root: str, course: str | None) -> str:
    return os.path.join(reports_root, course or "uncategorized", f"{_slugify(question)}.html")


def summary_path(question: str, academic_hub_root: str, course: str | None) -> str | None:
    """Returns the tablet-readable Markdown destination for a reported
    tutor answer. Keep it in the course's source-notes vault so the summary
    is available alongside the materials it cites. A non-academic corpus
    root has no academic_notes/ tree, so it has no summary destination."""
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return None
    course_dir = _slugify(course) if course else "uncategorized"
    return os.path.join(notes_root, course_dir, "summaries", f"{_slugify(question)}.md")


def build_markdown_summary(
    question: str, answer: str, citations: list[Citation], output_path: str,
    solution: str | None = None,
) -> str | None:
    """Writes the answer and its source citations as a Markdown summary
    under academic_notes/<course>/summaries/. The RAG caller owns the
    destination choice; this function only writes the supplied content."""
    try:
        source_refs = []
        source_lines = []
        seen = set()
        for citation in citations:
            identity = (citation.file_id, citation.chunk_id)
            if identity in seen:
                continue
            seen.add(identity)
            source_refs.append({
                "root": citation.root,
                "path": citation.path,
                "file_id": citation.file_id,
                "chunk_id": citation.chunk_id,
                "citation": citation.citation,
            })

            source_path = (
                citation.path if os.path.isabs(citation.path)
                else os.path.join(citation.root, citation.path)
            )
            linked_path = f"`{citation.path}`"
            try:
                notes_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(output_path))))
                source_path = os.path.abspath(source_path)
                if (os.path.normcase(os.path.commonpath([notes_root, source_path])) == os.path.normcase(notes_root)
                        and os.path.isfile(source_path)):
                    relative_path = os.path.relpath(source_path, os.path.dirname(output_path))
                    target = quote(relative_path.replace(os.sep, "/"), safe="/-._~")
                    linked_path = f"[`{citation.path}`](<{target}>)"
            except (OSError, ValueError):
                # A citation can refer to another corpus, drive, or source
                # that has since moved. Preserve its path and index IDs even
                # when a local Markdown link cannot be formed.
                pass
            source_lines.append(
                f"- {linked_path} ({citation.citation}; file_id: `{citation.file_id}`; "
                f"chunk_id: `{citation.chunk_id}`; corpus: `{citation.root}`)"
            )

        metadata = {
            "title": json.dumps(question, ensure_ascii=False),
            "llm_generated": "true",
            "content_kind": "derived_summary",
            "generated_by": "academic-rag-model/agent/rag/rag_agent.py",
            "indexer_source_refs": json.dumps(source_refs, ensure_ascii=False, separators=(",", ":")),
        }
        frontmatter = "---\n" + "".join(f"{key}: {value}\n" for key, value in metadata.items()) + "---\n\n"
        sources = "\n".join(source_lines)
        solution_block = f"\n\n## Worked solution\n\n{solution}" if solution is not None else ""
        document = (
            f"{frontmatter}# {question}\n\n{answer}{solution_block}\n\n"
            f"## Sources\n\n{sources or '- No source passages were retrieved.'}\n"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(document)
        return output_path
    except Exception as err:
        print(f"WARNING: Markdown summary generation failed ({err})")
        return None


def build_report(
    question: str, answer: str, citations: list[Citation], visualization: VizResult | None,
    output_path: str, solution: str | None = None,
) -> str | None:
    """Writes one self-contained HTML file combining question, answer,
    citations, and (if given) the visualization's embedded fragment.
    `solution`, when given (e.g. a generated practice problem's worked
    solution), renders as its own section rather than being folded into
    `answer` -- kept separate the same way AnswerResult.generated_problem
    .solution_text is kept separate from AnswerResult.answer elsewhere
    in this project. Never raises past its caller -- any failure is
    logged as a WARNING and this returns None, leaving the rest of the
    answer untouched (spec §6)."""
    try:
        citations_html = "\n".join(
            f"  <li>[{html.escape(c.root)}] {html.escape(c.path)} ({html.escape(c.citation)})</li>"
            for c in citations
        )
        solution_block = ""
        if solution is not None:
            solution_block = f"<h2>Solution</h2>\n<p>{html.escape(solution)}</p>\n"
        visualization_block = ""
        if visualization is not None:
            visualization_block = f"<h2>Visualization</h2>\n{visualization.fragment_html}\n"
        document = (
            f"<h1>{html.escape(question)}</h1>\n"
            f"<p>{html.escape(answer)}</p>\n"
            f"{solution_block}"
            f"<h2>Citations</h2>\n"
            f"<ul>\n{citations_html}\n</ul>\n"
            f"{visualization_block}"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(document)
        return output_path
    except Exception as err:
        print(f"WARNING: report generation failed ({err})")
        return None
