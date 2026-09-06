"""
extractor.py
Orchestration and CLI for the problem corpus extraction tool (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 6). Iterates indexed cards via indexer/index_card.py (the same
public interface indexer/chunk_index.py's chunk() already uses for its
own per-file iteration) -- never that or any other module's private
internals. Own standalone CLI entry point, mirroring viz/viz_agent.py's
and rag/rag_agent.py's own argparse-based main(), rather than a new
index_search.py subcommand: extraction is a problem_gen-adjacent
subproject that depends on the indexer, not an indexer-internal
operation (indexer/ gains no new dependency in the other direction).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re

from common.gemini_utils import get_gemini_client, load_dotenv_override
from indexer.index_card import list_courses, load_shard, now_iso
from problem_corpus.boundaries import detect_spans
from problem_corpus.llm_extract import extract_record
from problem_corpus.store import load_records, save_file_records

_PROBLEM_BEARING_FOLDER_CATEGORIES = ("problem_sets", "textbooks", "textbooks-and-papers", "recitation_slides")
# "textbooks-and-papers" included alongside "textbooks" for the same
# reason the root .gitignore lists both explicitly: some courses'
# textbook folders were renamed from "textbooks-and-papers" to
# "textbooks" and some weren't (confirmed live during this tool's own
# 2026-09-06 real validation run -- math-camp's indexed cards still
# carry the pre-rename "textbooks-and-papers" path, even though the
# folder on disk is now "textbooks"; without this alias, those 5 cards
# were silently filtered out here as "not problem-bearing" before ever
# reaching the file-level try/except that would have correctly reported
# them as failed-with-a-clear-reason instead).

# Duplicated from indexer/chunk_index.py's own _FRONTMATTER_RE, per this
# package's module-boundary convention (see boundaries.py's own docstring).
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.DOTALL)

_DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")


def _folder_category_from_path(path: str) -> str:
    """Duplicated from indexer/chunk_index.py's own private helper of the
    same name -- card paths are always stored with "/" separators
    regardless of OS (matching that function's own assumption)."""
    parts = path.split("/")
    if "processed_outputs" not in parts:
        return ""
    idx = parts.index("processed_outputs")
    return parts[idx - 1] if idx >= 1 else ""


def _record_id(file_id: str, span_index: int, problem_label: str) -> str:
    """Truncated SHA-256 of file_id + the span's own index within the
    file + its label -- the span index keeps this collision-safe even
    when two spans in the same file both fall back to the bare label
    "Problem" (see boundaries.ProblemSpan's own docstring)."""
    joined = f"{file_id}:{span_index}:{problem_label}"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _extract_file(academic_hub_root: str, course: str, card: dict, client) -> dict:
    """Extracts every problem in one file, mirroring
    chunk_index.generate_chunks_for_file()'s content-hash-based
    idempotency and per-file atomicity. Returns {"status": "unchanged"}
    if this file's content_hash already matches its stored records,
    {"status": "skipped_no_problems"} if zero spans are detected, or
    {"status": "extracted", "problems_extracted": N} otherwise. Per span,
    a None from llm_extract.extract_record() is skipped (logged as a
    WARNING) without aborting the rest of the file."""
    file_id = card["file_id"]
    existing = load_records(academic_hub_root, course)
    current_for_file = [r for r in existing if r["source"]["file_id"] == file_id]
    if current_for_file and all(r["content_hash"] == card["content_hash"] for r in current_for_file):
        return {"status": "unchanged"}

    md_path = os.path.join(academic_hub_root, card["path"])
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    body = _FRONTMATTER_RE.sub("", text, count=1)

    spans = detect_spans(body)
    if not spans:
        return {"status": "skipped_no_problems"}

    folder_category = _folder_category_from_path(card["path"])
    new_records = []
    for i, span in enumerate(spans):
        extracted = extract_record(span.text, client)
        if extracted is None:
            print(f"WARNING: extraction failed for {card['path']} ({span.problem_label}); skipping this problem.")
            continue
        solution_provenance = "student_attempt" if extracted.solution_text is not None else None
        new_records.append({
            "id": _record_id(file_id, i, span.problem_label),
            "course": course,
            "topic_tag": extracted.topic_tag,
            "problem_text": extracted.problem_text,
            "solution_text": extracted.solution_text,
            "solution_provenance": solution_provenance,
            "source": {
                "file_id": file_id,
                "path": card["path"],
                "root": academic_hub_root,
                "citation": f"{os.path.basename(card['path'])}, {span.problem_label}",
                "folder_category": folder_category,
            },
            "content_hash": card["content_hash"],
            "extracted_at": now_iso(),
        })

    save_file_records(academic_hub_root, course, file_id, new_records)
    return {"status": "extracted", "problems_extracted": len(new_records)}


def extract_problems(
    academic_hub_root: str, client, course: str | None = None,
    file: str | None = None, dry_run: bool = False,
) -> dict:
    """Iterates every non-orphaned, non-needs_indexing card across the
    given course (or every course via list_courses() if course is None)
    whose folder_category is problem-bearing. A file-level exception
    (unreadable file, bad frontmatter) is caught, logged as a WARNING
    with a rerun hint, and processing continues to the next file --
    never aborts the whole run. dry_run reports what WOULD be
    (re-)extracted (by the same content_hash comparison _extract_file
    uses) without calling Gemini or writing anything."""
    stats = {"extracted": 0, "unchanged": 0, "skipped_no_problems": 0, "failed": 0, "problems_extracted": 0}

    for course_name in list_courses(academic_hub_root):
        if course is not None and course_name != course:
            continue
        for card in load_shard(academic_hub_root, course_name):
            if card.get("orphaned") or card.get("needs_indexing"):
                continue
            folder_category = _folder_category_from_path(card["path"])
            if folder_category not in _PROBLEM_BEARING_FOLDER_CATEGORIES:
                continue
            if file is not None and not card["path"].endswith(file):
                continue

            if dry_run:
                existing = load_records(academic_hub_root, course_name)
                current = [r for r in existing if r["source"]["file_id"] == card["file_id"]]
                if current and all(r["content_hash"] == card["content_hash"] for r in current):
                    stats["unchanged"] += 1
                else:
                    stats["extracted"] += 1
                continue

            try:
                result = _extract_file(academic_hub_root, course_name, card, client)
            except Exception as err:
                print(f"WARNING: extraction failed for {card['path']} ({err}); "
                      f"rerun `python -m problem_corpus.extractor extract` later to retry.")
                stats["failed"] += 1
                continue

            if result["status"] == "unchanged":
                stats["unchanged"] += 1
            elif result["status"] == "skipped_no_problems":
                stats["skipped_no_problems"] += 1
            else:
                stats["extracted"] += 1
                stats["problems_extracted"] += result["problems_extracted"]

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract a structured problem corpus from indexed course content.")
    parser.add_argument(
        "--root", action="append", default=None,
        help=f"Path to a corpus root's own .index/ (default: {_DEFAULT_ROOT}). Exactly one root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_p = subparsers.add_parser("extract", help="Extract problems into .problem_corpus/<course>.json.")
    extract_p.add_argument("--course", default=None)
    extract_p.add_argument("--file", default=None)
    extract_p.add_argument("--dry-run", action="store_true")
    return parser


def _single_root(args) -> str:
    """extract is a per-corpus maintenance operation, not query-time
    federation -- it writes into exactly one root's own .problem_corpus/,
    so more than one --root is a usage error, matching
    indexer/index_search.py's own _single_root for the same reason."""
    roots = args.root or [_DEFAULT_ROOT]
    if len(roots) > 1:
        raise SystemExit(
            f"'{args.command}' operates on one corpus root at a time, got {len(roots)} "
            f"(--root {', '.join(roots)}). Pass exactly one --root."
        )
    return roots[0]


def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "extract":
        stats = extract_problems(
            _single_root(args), client, course=args.course, file=args.file, dry_run=args.dry_run,
        )
        print(stats)


if __name__ == "__main__":
    main()
