#!/usr/bin/env python3
"""
route_notes_transcribe.py
Deterministic, filetype-based orchestrator across every course under
academic_notes/: walks each course's directory tree (pruning
processed_outputs/ so a pipeline's own prior output is never mistaken for
a new source -- notably, transcribe_excalidraw.py's raw output is named
"<name>.excalidraw.md", the exact same suffix as a real source file),
finds source files with no existing output, and dispatches each to the
matching pipeline's own per-file function -- .pdf to
transcribe_notes.process_pdf, .excalidraw.md (+ its .png/.svg sibling) to
transcribe_excalidraw.process_excalidraw_note. No LLM makes the routing
decision: it's pure extension/filename dispatch, so this is safe to run
unattended (cron, or a plain `python -m notes.route_notes_transcribe` call)
without an agent deciding what to run each time. After dispatch, re-checks
that each expected output file actually landed on disk rather than
trusting a "no exception raised" result.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from common.academic_hub_paths import TEXTBOOK_FOLDER_NAMES, resolve_output_dir, to_resources_root
from notes.transcribe_excalidraw import (
    _TRANSCRIBE_MODEL as _EXCALIDRAW_MODEL,
    discover_excalidraw_files,
    process_excalidraw_note,
)
from notes.transcribe_notes import discover_pdf_files, process_pdf

_SKIP_DIR_NAMES = frozenset({"processed_outputs"})


def find_course_dirs(academic_hub_root: str) -> list[str]:
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return []
    return sorted(
        name for name in os.listdir(notes_root)
        if not name.startswith(".") and os.path.isdir(os.path.join(notes_root, name))
    )


def _walk_content_dirs(course_dir: str):
    """Yields every directory under course_dir, pruning processed_outputs/
    and hidden directories (e.g. a nested .obsidian) from recursion --
    what's inside them is a pipeline's own output or plugin state, never a
    new source."""
    for dirpath, dirnames, _filenames in os.walk(course_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.startswith(".")]
        yield dirpath


def discover_pdf_sources(course_dir: str) -> list[str]:
    paths = []
    for dirpath in _walk_content_dirs(course_dir):
        paths.extend(discover_pdf_files(dirpath))
    paths.extend(_discover_migrated_pdf_sources(course_dir))
    return paths


def _discover_migrated_pdf_sources(course_dir: str) -> list[str]:
    """PDFs already moved to academic_resources/<course>/<category>/ --
    only descends into a category that also exists directly under
    academic_notes/<course>/, and never into a textbook folder, so
    academic_resources/<course>/textbooks/ (a completely different
    pipeline's home -- its academic_notes/ counterpart only holds each
    book's mirrored .rag.md) never gets swept in by accident."""
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        return []
    if not os.path.isdir(resources_course_dir):
        return []
    notes_categories = {
        name for name in os.listdir(course_dir) if os.path.isdir(os.path.join(course_dir, name))
    }
    paths = []
    for category in sorted(os.listdir(resources_course_dir)):
        if category not in notes_categories or category in TEXTBOOK_FOLDER_NAMES:
            continue
        category_dir = os.path.join(resources_course_dir, category)
        if not os.path.isdir(category_dir):
            continue
        paths.extend(discover_pdf_files(category_dir))
    return paths


def discover_excalidraw_sources(course_dir: str) -> list[tuple[str, str]]:
    pairs = []
    for dirpath in _walk_content_dirs(course_dir):
        pairs.extend(discover_excalidraw_files(dirpath))
    return pairs


def pdf_output_path(pdf_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    return os.path.join(resolve_output_dir(pdf_path), f"{base_name}.md")


def excalidraw_output_path(md_path: str) -> str:
    # The .rag.md, not the raw .md -- it's the RAG-canonical artifact
    # (write_outputs only registers the .rag.md with the source indexer),
    # so it's the right "is this actually done" marker.
    base_name = os.path.basename(md_path)[: -len(".excalidraw.md")]
    return os.path.join(os.path.dirname(md_path), "processed_outputs", f"{base_name}.excalidraw.rag.md")


def _is_nonempty_file(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def filter_unprocessed_pdfs(pdf_paths, force: bool = False) -> list[str]:
    if force:
        return list(pdf_paths)
    return [p for p in pdf_paths if not _is_nonempty_file(pdf_output_path(p))]


def filter_unprocessed_excalidraw(pairs, force: bool = False) -> list[tuple[str, str]]:
    if force:
        return list(pairs)
    return [(md, img) for md, img in pairs if not _is_nonempty_file(excalidraw_output_path(md))]


@dataclass
class PipelinePlan:
    pdf_todo: list[str] = field(default_factory=list)
    pdf_skipped: list[str] = field(default_factory=list)
    excalidraw_todo: list[tuple[str, str]] = field(default_factory=list)
    excalidraw_skipped: list[tuple[str, str]] = field(default_factory=list)


def build_plan(academic_hub_root: str, courses: list[str] | None = None, force: bool = False) -> PipelinePlan:
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    target_courses = courses if courses is not None else find_course_dirs(academic_hub_root)
    plan = PipelinePlan()
    for course in target_courses:
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            print(f"WARNING: course directory not found, skipping: {course_dir}")
            continue

        pdfs = discover_pdf_sources(course_dir)
        todo_pdfs = filter_unprocessed_pdfs(pdfs, force=force)
        todo_pdf_set = set(todo_pdfs)
        plan.pdf_todo.extend(todo_pdfs)
        plan.pdf_skipped.extend(p for p in pdfs if p not in todo_pdf_set)

        pairs = discover_excalidraw_sources(course_dir)
        todo_pairs = filter_unprocessed_excalidraw(pairs, force=force)
        todo_pair_set = set(todo_pairs)
        plan.excalidraw_todo.extend(todo_pairs)
        plan.excalidraw_skipped.extend(p for p in pairs if p not in todo_pair_set)
    return plan


@dataclass
class RunResult:
    path: str
    status: str  # "ok", "failed", or "output_missing" (ran, no exception, but nothing landed on disk)
    error: str | None = None


@dataclass
class RunReport:
    pdf_results: list[RunResult] = field(default_factory=list)
    excalidraw_results: list[RunResult] = field(default_factory=list)


def run_plan(
    plan: PipelinePlan, client, academic_hub_root: str,
    pdf_model: str | None = None, excalidraw_model: str | None = None,
    expand_backend: str = "gemini", use_grounding: bool = False,
) -> RunReport:
    report = RunReport()

    for pdf_path in plan.pdf_todo:
        try:
            process_pdf(pdf_path, client, pdf_model, academic_hub_root)
        except Exception as err:
            print(f"ERROR: {pdf_path} failed: {err}")
            report.pdf_results.append(RunResult(pdf_path, "failed", str(err)))
            continue
        status = "ok" if _is_nonempty_file(pdf_output_path(pdf_path)) else "output_missing"
        if status == "output_missing":
            print(f"WARNING: {pdf_path} ran with no error but produced no output -- flagging, not trusting.")
        report.pdf_results.append(RunResult(pdf_path, status))

    for md_path, image_path in plan.excalidraw_todo:
        try:
            process_excalidraw_note(
                md_path, image_path, client, excalidraw_model or _EXCALIDRAW_MODEL, expand_backend,
                academic_hub_root, use_grounding=use_grounding,
            )
        except Exception as err:
            print(f"ERROR: {md_path} failed: {err}")
            report.excalidraw_results.append(RunResult(md_path, "failed", str(err)))
            continue
        status = "ok" if _is_nonempty_file(excalidraw_output_path(md_path)) else "output_missing"
        if status == "output_missing":
            print(f"WARNING: {md_path} ran with no error but produced no output -- flagging, not trusting.")
        report.excalidraw_results.append(RunResult(md_path, status))

    return report


def print_summary(plan: PipelinePlan, report: RunReport | None = None) -> None:
    print(f"PDF: {len(plan.pdf_todo)} to process, {len(plan.pdf_skipped)} already done")
    print(f"Excalidraw: {len(plan.excalidraw_todo)} to process, {len(plan.excalidraw_skipped)} already done")
    if report is None:
        return
    all_results = report.pdf_results + report.excalidraw_results
    ok = sum(1 for r in all_results if r.status == "ok")
    problems = [r for r in all_results if r.status != "ok"]
    print(f"Completed: {ok} succeeded, {len(problems)} failed/incomplete")
    for r in problems:
        print(f"  [{r.status}] {r.path}" + (f": {r.error}" if r.error else ""))


def main():
    parser = argparse.ArgumentParser(
        description="Discover notes with no existing transcription across every course under "
                    "academic_notes/, and route each to the right pipeline by filetype -- "
                    ".pdf to transcribe_notes.py, .excalidraw.md (+.png/.svg) to "
                    "transcribe_excalidraw.py. No LLM decides routing; safe to run unattended."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course under academic_notes/.")
    parser.add_argument("--force", action="store_true", help="Reprocess files even if output already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling any API.")
    parser.add_argument("--pdf-model", default=None, help="Model override for transcribe_notes.py (default: its own auto-selection).")
    parser.add_argument("--excalidraw-model", default=None, help=f"Gemini vision model for Excalidraw transcription. Default: {_EXCALIDRAW_MODEL}.")
    parser.add_argument("--expand-backend", default="gemini", choices=("gemini", "ollama"))
    parser.add_argument("--grounding", action="store_true", help="Retrieve textbook passages to ground Excalidraw expansion.")
    parser.add_argument(
        "--use-paid-key", action="store_true",
        help="Use PAID_GEMINI_KEY from ai-sandbox/.env instead of GEMINI_API_KEY -- for when the "
             "default key is pointed at a free-tier project for other work (see gemini_utils.get_gemini_client).",
    )
    args = parser.parse_args()

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    plan = build_plan(str(academic_hub_dir), courses=args.course, force=args.force)
    print_summary(plan)

    total_todo = len(plan.pdf_todo) + len(plan.excalidraw_todo)
    if total_todo == 0:
        print("Nothing to do.")
        return

    if args.dry_run:
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        return

    client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
    if client is None:
        sys.exit(1)

    report = run_plan(
        plan, client, str(academic_hub_dir),
        pdf_model=args.pdf_model, excalidraw_model=args.excalidraw_model,
        expand_backend=args.expand_backend, use_grounding=args.grounding,
    )
    print_summary(plan, report)

    if any(r.status != "ok" for r in report.pdf_results + report.excalidraw_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
