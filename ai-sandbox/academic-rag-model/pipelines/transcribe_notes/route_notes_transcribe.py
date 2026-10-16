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
decision: it's pure extension/filename dispatch. After dispatch, re-checks
that each expected output file actually landed on disk rather than
trusting a "no exception raised" result.

`--driver` defaults to "agent" (the Antigravity subscription), which
requires `--collect` or `--submit` -- a bare unattended invocation (cron, or
a plain `python -m pipelines.transcribe_notes.route_notes_transcribe` call)
now needs an explicit `--driver api` to run the old fully-metered, no-agent
loop without anyone deciding what to run each time.

A directory under academic_resources/<course>/ marked with a
.notes_subset.json file (see README.md) is additionally swept at
arbitrary depth, for a whole prior course offering staged outside
academic_notes/ without flattening its structure.

AGENT COORDINATION: Do not start this writer independently or concurrently
when acting on a corpus-health finding. Its apply adapter is not implemented
yet; until then, run only when explicitly directed and after confirming no
other writer is touching the same targets. Once apply support exists, route
finding-driven runs through that orchestrator.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from core.env.academic_hub_paths import (
    TEXTBOOK_FOLDER_NAMES,
    read_subset_marker,
    resolve_output_dir,
    to_resources_root,
)
from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from pipelines.transcribe_notes.transcribe_excalidraw import (
    _TRANSCRIBE_MODEL as _EXCALIDRAW_MODEL,
    discover_excalidraw_files,
    process_excalidraw_note,
)
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.transcribe_notes import discover_pdf_files, process_pdf
from agent.rag.resolve_questions import discover_pending_notes, resolve_note
from core.indexer.chunk_index import chunk as chunk_notes

if TYPE_CHECKING:
    from pipelines.transcribe_notes.agent_driver import TranscriptionDriver

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


def _dedupe(items):
    """Removes duplicates while preserving first-seen order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def discover_pdf_sources(course_dir: str, subset_roots: list[str] | None = None) -> list[str]:
    paths = []
    for dirpath in _walk_content_dirs(course_dir):
        paths.extend(discover_pdf_files(dirpath))
    paths.extend(_discover_migrated_pdf_sources(course_dir))
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        resources_course_dir = None
    if resources_course_dir is not None:
        paths.extend(discover_marked_subset_pdf_sources(resources_course_dir, subset_roots))
    return _dedupe(paths)


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


def _is_textbook_dir_name(name: str) -> bool:
    """Case-insensitive match against TEXTBOOK_FOLDER_NAMES -- a Title-Case
    "Textbooks" nested inside a marked subset (this project's folder names
    are otherwise Title Case, e.g. "Class Notes") must be excluded exactly
    like the lowercase convention used elsewhere in this corpus."""
    return name.lower() in TEXTBOOK_FOLDER_NAMES


def find_subset_roots(resources_course_dir: str) -> list[str]:
    """Recursively finds every directory under resources_course_dir whose
    own root holds a valid _SUBSET_MARKER_FILENAME. Once a root is found,
    stops looking for further nested markers inside it -- one marker
    claims its whole subtree, no stacking. Never descends into a textbook
    folder: a marker placed there (even by mistake) must not sweep book
    PDFs into notes transcription."""
    if not os.path.isdir(resources_course_dir):
        return []
    roots = []
    for dirpath, dirnames, _filenames in os.walk(resources_course_dir):
        dirnames[:] = [
            d for d in dirnames
            if d not in _SKIP_DIR_NAMES and not _is_textbook_dir_name(d) and not d.startswith(".")
        ]
        if read_subset_marker(dirpath) is not None:
            roots.append(dirpath)
            dirnames[:] = []  # claimed -- don't search inside for nested markers
    return sorted(roots)


def _walk_marked_subset(subset_root: str):
    """Yields every directory under subset_root, pruning processed_outputs/,
    hidden directories, and any textbook-named directory (case-insensitive)
    at any depth -- the same invariant _discover_migrated_pdf_sources
    enforces via its category-match gate, needed here directly since that
    gate doesn't apply to this path."""
    for dirpath, dirnames, _filenames in os.walk(subset_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in _SKIP_DIR_NAMES and not _is_textbook_dir_name(d) and not d.startswith(".")
        ]
        yield dirpath


def discover_marked_subset_pdf_sources(
    resources_course_dir: str, subset_roots: list[str] | None = None,
) -> list[str]:
    paths = []
    roots = subset_roots if subset_roots is not None else find_subset_roots(resources_course_dir)
    for subset_root in roots:
        for dirpath in _walk_marked_subset(subset_root):
            paths.extend(discover_pdf_files(dirpath))
    return paths


def discover_marked_subset_excalidraw_sources(
    resources_course_dir: str, subset_roots: list[str] | None = None,
) -> list[tuple[str, str]]:
    pairs = []
    roots = subset_roots if subset_roots is not None else find_subset_roots(resources_course_dir)
    for subset_root in roots:
        for dirpath in _walk_marked_subset(subset_root):
            pairs.extend(discover_excalidraw_files(dirpath))
    return pairs


def discover_excalidraw_sources(course_dir: str, subset_roots: list[str] | None = None) -> list[tuple[str, str]]:
    pairs = []
    for dirpath in _walk_content_dirs(course_dir):
        pairs.extend(discover_excalidraw_files(dirpath))
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        resources_course_dir = None
    if resources_course_dir is not None:
        pairs.extend(discover_marked_subset_excalidraw_sources(resources_course_dir, subset_roots))
    return _dedupe(pairs)


def pdf_output_path(pdf_path: str) -> str:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    return os.path.join(resolve_output_dir(pdf_path), f"{base_name}.md")


def excalidraw_output_path(md_path: str) -> str:
    # The .rag.md, not the raw .md -- it's the RAG-canonical artifact
    # (write_outputs only registers the .rag.md with the source indexer),
    # so it's the right "is this actually done" marker. resolve_output_dir
    # (not a plain sibling dirname) so a scene discovered under
    # academic_resources/ (a marked subset) resolves to where write_outputs
    # actually writes -- the mirrored academic_notes/ location, matching
    # pdf_output_path's own handling of the same migrated case.
    base_name = os.path.basename(md_path)[: -len(".excalidraw.md")]
    return os.path.join(resolve_output_dir(md_path), f"{base_name}.excalidraw.rag.md")


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
class BackupResult:
    source: str
    dest: str
    status: str  # "copied", "up_to_date", or "failed"
    error: str | None = None


def sync_resource_backups(pairs, dry_run: bool = False) -> list[BackupResult]:
    """Copies each Excalidraw pair's plugin-auto-exported image (the
    .svg/.png next to the note under academic_notes/) to its mirrored
    location under academic_resources/, so the auto-export -- which the
    plugin overwrites on every note open, independent of transcription
    status -- gets a persistent backup. Runs over every discovered pair,
    not just ones still needing transcription: the owner wants the latest
    export preserved every run regardless of whether the note itself was
    reprocessed. Deduplicates by destination first, since a marked prior-
    offering subset can make the same image_path appear via more than one
    discovery path. Deliberate duplication between the two trees is
    accepted (not deleting the academic_notes/ copy); only copies when the
    destination is missing or older than the source, so an unrelated
    corpus with many already-backed-up notes doesn't rewrite every file
    on every run."""
    results: list[BackupResult] = []
    seen_dests: set[str] = set()
    for _md_path, image_path in pairs:
        try:
            dest = to_resources_root(image_path)
        except ValueError:
            continue  # image not under academic_notes/ (already resources-side); nothing to mirror.
        if dest in seen_dests:
            continue
        seen_dests.add(dest)
        if os.path.normcase(os.path.abspath(dest)) == os.path.normcase(os.path.abspath(image_path)):
            continue  # source and destination are the same path; nothing to back up.

        needs_copy = not os.path.isfile(dest) or os.path.getmtime(image_path) > os.path.getmtime(dest)
        if not needs_copy:
            results.append(BackupResult(image_path, dest, "up_to_date"))
            continue
        if dry_run:
            results.append(BackupResult(image_path, dest, "copied"))
            continue
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(image_path, dest)
            results.append(BackupResult(image_path, dest, "copied"))
        except OSError as err:
            print(f"WARNING: failed to back up {image_path} to {dest}: {err}")
            results.append(BackupResult(image_path, dest, "failed", str(err)))
    return results


@dataclass
class PipelinePlan:
    pdf_todo: list[str] = field(default_factory=list)
    pdf_skipped: list[str] = field(default_factory=list)
    excalidraw_todo: list[tuple[str, str]] = field(default_factory=list)
    excalidraw_skipped: list[tuple[str, str]] = field(default_factory=list)
    courses: list[str] = field(default_factory=list)
    resolve_questions_todo: list[str] = field(default_factory=list)


def build_plan(academic_hub_root: str, courses: list[str] | None = None, force: bool = False) -> PipelinePlan:
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    target_courses = courses if courses is not None else find_course_dirs(academic_hub_root)
    plan = PipelinePlan(courses=list(target_courses))
    for course in target_courses:
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            print(f"WARNING: course directory not found, skipping: {course_dir}")
            continue

        try:
            resources_course_dir = to_resources_root(course_dir)
        except ValueError:
            resources_course_dir = None
        # Computed once and shared below -- discover_pdf_sources and
        # discover_excalidraw_sources each need it, and calling
        # find_subset_roots from both separately walked the whole
        # marked-subset tree twice per course.
        subset_roots = find_subset_roots(resources_course_dir) if resources_course_dir is not None else []

        pdfs = discover_pdf_sources(course_dir, subset_roots=subset_roots)
        todo_pdfs = filter_unprocessed_pdfs(pdfs, force=force)
        todo_pdf_set = set(todo_pdfs)
        plan.pdf_todo.extend(todo_pdfs)
        plan.pdf_skipped.extend(p for p in pdfs if p not in todo_pdf_set)

        pairs = discover_excalidraw_sources(course_dir, subset_roots=subset_roots)
        todo_pairs = filter_unprocessed_excalidraw(pairs, force=force)
        todo_pair_set = set(todo_pairs)
        plan.excalidraw_todo.extend(todo_pairs)
        plan.excalidraw_skipped.extend(p for p in pairs if p not in todo_pair_set)
        plan.resolve_questions_todo.extend(discover_pending_notes(academic_hub_root, course=course))
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
    resolve_questions_resolved: int = 0
    resolve_questions_failed: list[str] = field(default_factory=list)
    chunk_stats: dict = field(default_factory=lambda: {
        "chunked": 0, "unchanged": 0, "failed": 0, "skipped_no_embedding": 0,
    })


def run_plan(
    plan: PipelinePlan, client, academic_hub_root: str,
    pdf_model: str | None = None, excalidraw_model: str | None = None,
    expand_backend: str = "gemini", use_grounding: bool = False,
    force_vision: bool = False,
    driver: "TranscriptionDriver | None" = None, collect_mode: bool = False,
    excalidraw_driver=None, resolve_questions_model: str | None = None,
) -> RunReport:
    """driver/excalidraw_driver/collect_mode plumb transcribe_notes.py's and
    transcribe_excalidraw.py's agent-driven transport through unchanged."""
    report = RunReport()

    for pdf_path in plan.pdf_todo:
        try:
            process_pdf(
                pdf_path, client, pdf_model, academic_hub_root,
                force_vision=force_vision, driver=driver, collect_mode=collect_mode,
            )
        except Exception as err:
            print(f"ERROR: {pdf_path} failed: {err}")
            report.pdf_results.append(RunResult(pdf_path, "failed", str(err)))
            continue
        if collect_mode:
            # Collect only ever writes task cards under .agent_work/, never
            # the real output file -- there is nothing to verify on disk yet.
            report.pdf_results.append(RunResult(pdf_path, "collected"))
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
                driver=excalidraw_driver, collect_mode=collect_mode,
            )
        except AgentPending:
            # A card was staged for this note -- expected and not a failure,
            # same as process_pdf's own AgentPending contract (process_pdf
            # catches it internally; process_excalidraw_note deliberately
            # lets it propagate, so it must be caught here instead).
            report.excalidraw_results.append(RunResult(md_path, "collected"))
            continue
        except Exception as err:
            print(f"ERROR: {md_path} failed: {err}")
            report.excalidraw_results.append(RunResult(md_path, "failed", str(err)))
            continue
        if collect_mode:
            report.excalidraw_results.append(RunResult(md_path, "collected"))
            continue
        status = "ok" if _is_nonempty_file(excalidraw_output_path(md_path)) else "output_missing"
        if status == "output_missing":
            print(f"WARNING: {md_path} ran with no error but produced no output -- flagging, not trusting.")
        report.excalidraw_results.append(RunResult(md_path, status))

    if not collect_mode:
        for raw_path in plan.resolve_questions_todo:
            try:
                note_result = resolve_note(
                    raw_path, academic_hub_root, client, [academic_hub_root],
                    **({"model": resolve_questions_model} if resolve_questions_model else {}),
                )
            except Exception as err:
                print(f"ERROR: resolve-questions failed for {raw_path}: {err}")
                report.resolve_questions_failed.append(raw_path)
                continue
            report.resolve_questions_resolved += note_result.resolved
            report.resolve_questions_failed.extend(note_result.failed)

        for course_name in plan.courses:
            try:
                stats = chunk_notes(academic_hub_root, client, course=course_name)
            except Exception as err:
                print(f"ERROR: chunking failed for course {course_name!r}: {err}")
                report.chunk_stats["failed"] += 1
                continue
            for key in report.chunk_stats:
                report.chunk_stats[key] += stats.get(key, 0)

    return report


_TERMINAL_OK_STATUSES = frozenset({"ok", "collected"})


def print_chunk_stats(chunk_stats: dict) -> None:
    if any(chunk_stats.values()):
        print(f"Chunk/embed: {chunk_stats['chunked']} chunked, {chunk_stats['unchanged']} unchanged, "
              f"{chunk_stats['failed']} failed, {chunk_stats['skipped_no_embedding']} skipped (no embedding)")


def print_summary(plan: PipelinePlan, report: RunReport | None = None) -> None:
    print(f"PDF: {len(plan.pdf_todo)} to process, {len(plan.pdf_skipped)} already done")
    print(f"Excalidraw: {len(plan.excalidraw_todo)} to process, {len(plan.excalidraw_skipped)} already done")
    if report is None:
        return
    all_results = report.pdf_results + report.excalidraw_results
    ok = sum(1 for r in all_results if r.status in _TERMINAL_OK_STATUSES)
    problems = [r for r in all_results if r.status not in _TERMINAL_OK_STATUSES]
    print(f"Completed: {ok} succeeded, {len(problems)} failed/incomplete")
    for r in problems:
        print(f"  [{r.status}] {r.path}" + (f": {r.error}" if r.error else ""))
    if report.resolve_questions_resolved or report.resolve_questions_failed:
        print(f"Resolve-questions: {report.resolve_questions_resolved} resolved, "
              f"{len(report.resolve_questions_failed)} failed")
    print_chunk_stats(report.chunk_stats)


def print_backup_summary(results: list[BackupResult]) -> None:
    if not results:
        return
    copied = [r for r in results if r.status == "copied"]
    failed = [r for r in results if r.status == "failed"]
    up_to_date = len(results) - len(copied) - len(failed)
    print(f"SVG/PNG backups: {len(copied)} copied, {up_to_date} already current, {len(failed)} failed")
    for r in failed:
        print(f"  [failed] {r.source} -> {r.dest}: {r.error}")


def resolve_questions_slug_map(plan: PipelinePlan) -> dict[str, str]:
    """doc_slug -> raw_path for every note in plan.resolve_questions_todo,
    using the same file_id-derived slug scheme resolve_questions.py's own
    --collect/--submit use -- lets this module's submit loop match
    resolve-questions task-card directories alongside its own PDF/
    Excalidraw ones under the same .agent_work/<run-id>/ tree."""
    from core.indexer.index_card import compute_file_id
    from pipelines.transcribe_notes.agent_work import doc_slug_for

    return {doc_slug_for(p, compute_file_id(p)): p for p in plan.resolve_questions_todo}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover notes with no existing transcription across every course under "
                    "academic_notes/, and route each to the right pipeline by filetype -- "
                    ".pdf to transcribe_notes.py, .excalidraw.md (+.png/.svg) to "
                    "transcribe_excalidraw.py. No LLM decides routing; safe to run unattended. "
                    "Also backs up every discovered Excalidraw note's auto-exported .svg/.png "
                    "into academic_resources/, independent of transcription status."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course under academic_notes/.")
    parser.add_argument("--force", action="store_true", help="Reprocess files even if output already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling any API.")
    parser.add_argument("--pdf-model", default=None, help="Model override for transcribe_notes.py (default: its own auto-selection).")
    parser.add_argument("--excalidraw-model", default=None, help=f"Gemini vision model for Excalidraw transcription. Default: {_EXCALIDRAW_MODEL}.")
    parser.add_argument("--resolve-questions-model", default=None,
                         help="Model override for agent/rag/resolve_questions.py (default: its own RESOLVER_MODEL).")
    parser.add_argument("--expand-backend", default="gemini", choices=("gemini", "ollama"))
    parser.add_argument("--grounding", action="store_true", help="Retrieve textbook passages to ground Excalidraw expansion.")
    parser.add_argument(
        "--use-paid-key", action="store_true",
        help="Use PAID_GEMINI_KEY from ai-sandbox/.env instead of GEMINI_API_KEY -- for when the "
             "default key is pointed at a free-tier project for other work (see gemini_utils.get_gemini_client).",
    )
    parser.add_argument(
        "--force-vision", action="store_true",
        help="Force vision transcription via Gemini for all routed PDFs, bypassing local text extraction.",
    )
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Transcription transport for both PDFs and Excalidraw notes. Default: agent (the "
             "Antigravity subscription). Use 'api' for a fully metered run.",
    )
    parser.add_argument("--collect", action="store_true",
                         help="With --driver agent: write task cards instead of transcribing.")
    parser.add_argument("--run-id", default=None,
                         help="Run id for --collect/--submit's .agent_work/ directory (default: a timestamp).")
    parser.add_argument("--submit", default=None, metavar="RUN_ID",
                         help="Validate this run's filled task cards and write them through.")
    parser.add_argument(
        "--allow-api-fallback", action="store_true",
        help="With --submit: finish any still-pending/bounced cards via the metered API instead of "
             "leaving them pending. Explicit opt-in only -- never automatic.",
    )
    parser.add_argument("--bootstrap", default=None, metavar="RUN_ID",
                         help="Print the agent's operating contract for this run.")
    return parser


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.bootstrap:
        print(f"""Agent-driven transcription contract for run '{args.bootstrap}':

1. Open each document's directory under .agent_work/{args.bootstrap}/<doc-slug>/.
2. Read worklist.md to see which task cards are pending.
3. For each pending task-NNNN.md: read every page's image and prompt in
   the card, then fill ONLY the "Agent output" section at the bottom with
   one "--- PAGE <number> ---" section per page, in order, using exactly
   the page numbers the card lists. Never edit any other file or section.
4. For a tier-3 card with more than one page: only the first page has
   real prior-page context supplied. For every later page in that same
   card, carry forward your own transcription of the card's earlier
   pages as continuity context.
5. Once you've filled one or more cards, run:
   python -m pipelines.transcribe_notes.route_notes_transcribe --submit {args.bootstrap}
6. If a card comes back marked "bounced: <reason>" in worklist.md, redo
   only that card in place and re-run step 5.
7. Stop once worklist.md shows nothing "pending"/"filled" left for this run.
   Excalidraw notes go through two stages in the same run: chunk
   transcription first, then (once all chunks are submitted) a second
   expansion card gets staged automatically on your next --submit. Fill
   expansion cards the same way, using "--- SEGMENT <number> ---" instead
   of "--- PAGE <number> ---" / "--- CHUNK <number> ---".
""")
        return

    from core.env.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"
    plan = build_plan(str(academic_hub_dir), courses=args.course, force=args.force)
    print_summary(plan)
    all_excalidraw_pairs = plan.excalidraw_todo + plan.excalidraw_skipped

    if args.dry_run:
        for p in plan.pdf_todo:
            print(f"  [pdf] would process: {p}")
        for md, img in plan.excalidraw_todo:
            print(f"  [excalidraw] would process: {md} (+ {os.path.basename(img)})")
        for r in sync_resource_backups(all_excalidraw_pairs, dry_run=True):
            if r.status == "copied":
                print(f"  [backup] would copy: {r.source} -> {r.dest}")
        for raw_path in plan.resolve_questions_todo:
            print(f"  [resolve-questions] would process: {raw_path}")
        for course_name in plan.courses:
            try:
                stats = chunk_notes(str(academic_hub_dir), None, course=course_name, dry_run=True)
            except Exception as err:
                print(f"  [chunk] {course_name}: ERROR previewing ({err})")
                continue
            print(f"  [chunk] {course_name}: {stats['chunked']} to (re)chunk, {stats['unchanged']} unchanged")
        return

    if args.collect and args.driver != "agent":
        print("--collect requires --driver agent.")
        sys.exit(1)
    if args.driver == "agent" and not args.collect and not args.submit:
        print("--driver agent requires --collect or --submit.")
        sys.exit(1)

    if args.collect:
        import datetime

        from pipelines.transcribe_notes.agent_work import AgentDriver, dedupe_by_file_id
        from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver

        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        canonical_pdf_paths, _duplicates_of = dedupe_by_file_id(plan.pdf_todo)
        plan.pdf_todo = canonical_pdf_paths
        canonical_excalidraw_md_paths, _ = dedupe_by_file_id([md for md, _ in plan.excalidraw_todo])
        plan.excalidraw_todo = [
            (md, img) for md, img in plan.excalidraw_todo if md in canonical_excalidraw_md_paths
        ]
        from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver

        pdf_driver = AgentDriver(str(academic_hub_dir), run_id)
        excalidraw_driver = ExcalidrawAgentDriver(str(academic_hub_dir), run_id)
        rq_client = None
        if plan.resolve_questions_todo:
            rq_client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
            if rq_client is None:
                sys.exit(1)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent collect)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                report = run_plan(
                    plan, None, str(academic_hub_dir), pdf_model=args.pdf_model,
                    force_vision=args.force_vision, driver=pdf_driver, collect_mode=True,
                    excalidraw_driver=excalidraw_driver, use_grounding=args.grounding,
                )
                rq_driver = QuestionResolverAgentDriver(str(academic_hub_dir), run_id)
                for raw_path in plan.resolve_questions_todo:
                    try:
                        resolve_note(
                            raw_path, str(academic_hub_dir), rq_client, [str(academic_hub_dir)],
                            driver=rq_driver, collect_mode=True,
                        )
                    except AgentPending:
                        pass
                    except Exception as err:
                        print(f"ERROR: resolve-questions collect failed for {raw_path}: {err}")
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_summary(plan, report)
        print(f"Collect run '{run_id}' complete under {academic_hub_dir / '.agent_work' / run_id}.")
        return

    if args.submit:
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_submit import submit_doc as submit_pdf_doc
        from pipelines.transcribe_notes.agent_work import agent_work_dir, doc_slug_for
        from pipelines.transcribe_notes.excalidraw_agent_submit import submit_doc as submit_excalidraw_doc

        client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
        if client is None:
            sys.exit(1)
        run_dir = agent_work_dir(str(academic_hub_dir), args.submit)
        if not os.path.isdir(run_dir):
            print(f"No .agent_work run directory found for run '{args.submit}' at {run_dir}.")
            sys.exit(1)

        # Matched the same way agent_submit's own CLI does: by the
        # file_id-derived slug AgentDriver/ExcalidrawAgentDriver used, built
        # from whatever is still pending transcription under this course
        # filter -- a collected-but-not-yet-submitted document has no output
        # file yet, so it's still in plan.pdf_todo/plan.excalidraw_todo.
        from agent.rag.resolve_questions_submit import submit_doc as submit_resolve_questions_doc

        pdf_by_slug = {doc_slug_for(p, compute_file_id(p)): p for p in plan.pdf_todo}
        excalidraw_by_slug = {
            doc_slug_for(md, compute_file_id(md)): (md, img) for md, img in plan.excalidraw_todo
        }
        resolve_questions_by_slug = resolve_questions_slug_map(plan)
        try:
            with corpus_write_lock(
                [academic_hub_dir, academic_hub_dir / "academic_notes"],
                "route notes transcription (agent submit)",
            ):
                backup_results = sync_resource_backups(all_excalidraw_pairs)
                for doc_slug in sorted(os.listdir(run_dir)):
                    pdf_path = pdf_by_slug.get(doc_slug)
                    excalidraw_pair = excalidraw_by_slug.get(doc_slug)
                    raw_path = resolve_questions_by_slug.get(doc_slug)
                    if pdf_path is None and excalidraw_pair is None and raw_path is None:
                        print(f"WARNING: no matching pending document for collected doc '{doc_slug}' "
                              f"(already submitted, or outside this --course filter?) -- skipping.")
                        continue
                    try:
                        if pdf_path is not None:
                            status = submit_pdf_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                pdf_path, client, args.pdf_model, force_vision=args.force_vision,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                        elif excalidraw_pair is not None:
                            md_path, image_path = excalidraw_pair
                            status = submit_excalidraw_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                md_path, image_path, client, args.excalidraw_model or _EXCALIDRAW_MODEL,
                                expand_backend=args.expand_backend, allow_api_fallback=args.allow_api_fallback,
                                use_grounding=args.grounding,
                            )
                        else:
                            status = submit_resolve_questions_doc(
                                str(academic_hub_dir), str(academic_hub_dir), args.submit, doc_slug,
                                raw_path, str(academic_hub_dir), client, args.resolve_questions_model,
                                allow_api_fallback=args.allow_api_fallback,
                            )
                    except Exception as err:
                        print(f"[{doc_slug}] error: {err}")
                        continue
                    print(f"[{doc_slug}] {status}")
                chunk_stats = {"chunked": 0, "unchanged": 0, "failed": 0, "skipped_no_embedding": 0}
                for course_name in plan.courses:
                    try:
                        stats = chunk_notes(str(academic_hub_dir), client, course=course_name)
                    except Exception as err:
                        print(f"ERROR: chunking failed for course {course_name!r}: {err}")
                        chunk_stats["failed"] += 1
                        continue
                    for key in chunk_stats:
                        chunk_stats[key] += stats.get(key, 0)
        except CorpusWriteLockError as exc:
            raise SystemExit(str(exc)) from exc
        print_backup_summary(backup_results)
        print_chunk_stats(chunk_stats)
        return

    total_todo = len(plan.pdf_todo) + len(plan.excalidraw_todo) + len(plan.resolve_questions_todo)
    if total_todo == 0 and not all_excalidraw_pairs and not plan.courses:
        print("Nothing to do.")
        return

    client = get_gemini_client("PAID_GEMINI_KEY" if args.use_paid_key else "GEMINI_API_KEY")
    if client is None:
        sys.exit(1)

    try:
        # The router writes Markdown in the nested notes repository and
        # cards in the outer hub index. Keep both leases for the whole batch.
        with corpus_write_lock(
            [academic_hub_dir, academic_hub_dir / "academic_notes"],
            "route notes transcription",
        ):
            backup_results = sync_resource_backups(all_excalidraw_pairs)
            report = run_plan(
                plan, client, str(academic_hub_dir),
                pdf_model=args.pdf_model, excalidraw_model=args.excalidraw_model,
                expand_backend=args.expand_backend, use_grounding=args.grounding,
                force_vision=args.force_vision, resolve_questions_model=args.resolve_questions_model,
            )
    except CorpusWriteLockError as exc:
        raise SystemExit(str(exc)) from exc
    print_backup_summary(backup_results)
    print_summary(plan, report)

    if any(r.status not in _TERMINAL_OK_STATUSES for r in report.pdf_results + report.excalidraw_results):
        sys.exit(1)


if __name__ == "__main__":
    main()
