"""
index_search.py
Rebuild/backfill pass and two-stage search for the academic-hub source
indexer, plus its CLI.

Spec: docs/superpowers/specs/2026-08-27-source-indexer-design.md
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from google.genai import types

from chunk_index import chunk, load_chunks
from gemini_utils import get_gemini_client, load_dotenv_override
from index_card import (
    TEXTBOOK_CONTENT_SAMPLE_CHARS,
    EMBEDDING_DIMENSIONALITY,
    EMBEDDING_MODEL,
    KNOWN_LEVELS,
    compute_content_hash,
    compute_file_id,
    cosine_similarity,
    derive_course,
    find_card_by_file_id,
    load_courses,
    load_shard,
    recompute_course_entry,
    reconcile_and_write,
    save_shard,
    set_rag_md_path,
)
from retag import retag

DEFAULT_COURSE_CANDIDATES = 3


@dataclass
class SearchResult:
    path: str
    course: str
    doc_type: str
    score: float
    reason: str
    file_id: str


def _embed_query(query: str, client) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL, contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def _candidate_courses(academic_hub_root: str, query_embedding: list[float], course: str | None) -> list[str]:
    if course is not None:
        return [course]
    courses = load_courses(academic_hub_root)
    scored = sorted(
        courses.values(),
        key=lambda entry: cosine_similarity(query_embedding, entry.get("embedding") or []),
        reverse=True,
    )
    return [entry["course"] for entry in scored[:DEFAULT_COURSE_CANDIDATES]]


def search(
    academic_hub_root: str, query: str, client, course: str | None = None, top_k: int = 5,
    doc_type: str | None = None, has_solutions: bool | None = None, max_level: str | None = None,
) -> list[SearchResult]:
    query_embedding = _embed_query(query, client)
    candidate_courses = _candidate_courses(academic_hub_root, query_embedding, course)

    scored: list[SearchResult] = []
    for c in candidate_courses:
        for card in load_shard(academic_hub_root, c):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                continue
            if doc_type is not None and card.get("doc_type") != doc_type:
                continue
            if has_solutions is not None and card.get("has_solutions") != has_solutions:
                continue
            if max_level is not None:
                card_level = card.get("level")
                if card_level not in KNOWN_LEVELS or KNOWN_LEVELS.index(card_level) > KNOWN_LEVELS.index(max_level):
                    continue
            score = cosine_similarity(query_embedding, card["embedding"])
            # .rag.md is the same content plus inlined image descriptions --
            # strictly more useful to a text-only consumer, so always
            # preferred over the plain .md when set (spec §3.1/§4.4).
            result_path = card.get("rag_md_path") or card["path"]
            scored.append(SearchResult(
                path=result_path, course=card["course"], doc_type=card["doc_type"],
                score=score, reason=card.get("summary", ""), file_id=card["file_id"],
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


@dataclass
class PassageResult:
    chunk_id: str
    file_id: str
    path: str
    course: str
    score: float
    text: str
    citation: str


def _render_citation(chunk: dict) -> str:
    parts = []
    if chunk.get("heading_path"):
        parts.append(f"§{chunk['heading_path'][-1]}")
    elif chunk.get("problem_label"):
        parts.append(chunk["problem_label"])
    page_range = chunk.get("page_range")
    if page_range:
        start, end = page_range
        parts.append(f"p. {start}" if start == end else f"p. {start}-{end}")
    return ", ".join(parts)


def search_passages(
    academic_hub_root: str, query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5,
) -> list[PassageResult]:
    """Three-stage funnel (spec §6): reuses search() for the file-level
    pass (100% of the existing course-then-file filtering, not
    duplicated), then ranks that shortlist's chunks by cosine similarity
    to the same query embedding. A file with no chunks yet (chunk
    hasn't been run against it) contributes nothing and is silently
    skipped, not an error -- degrades gracefully during the transition
    period before `chunk` has been run corpus-wide."""
    file_results = search(academic_hub_root, query, client, course=course, top_k=file_top_k)
    if not file_results:
        return []

    query_embedding = _embed_query(query, client)
    chunks_by_course: dict[str, list[dict]] = {}
    scored: list[PassageResult] = []
    for file_result in file_results:
        if file_result.course not in chunks_by_course:
            chunks_by_course[file_result.course] = load_chunks(academic_hub_root, file_result.course)
        for c in chunks_by_course[file_result.course]:
            if c["file_id"] != file_result.file_id:
                continue
            score = cosine_similarity(query_embedding, c["embedding"])
            scored.append(PassageResult(
                chunk_id=c["chunk_id"], file_id=c["file_id"], path=file_result.path,
                course=file_result.course, score=score, text=c["text"],
                citation=_render_citation(c),
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


def _notes_pdf_paths(academic_hub_root: str, course_filter: str | None):
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            continue
        for category in sorted(os.listdir(course_dir)):
            category_dir = os.path.join(course_dir, category)
            if not os.path.isdir(category_dir):
                continue
            for name in sorted(os.listdir(category_dir)):
                if name.lower().endswith(".pdf"):
                    yield course, category, os.path.join(category_dir, name)


def _textbook_book_dirs(academic_hub_root: str, course_filter: str | None):
    resources_root = os.path.join(academic_hub_root, "academic_resources")
    if not os.path.isdir(resources_root):
        return
    for course in sorted(os.listdir(resources_root)):
        if course_filter and course != course_filter:
            continue
        processed_outputs_dir = os.path.join(
            resources_root, course, "textbooks-and-papers", "processed_outputs",
        )
        if not os.path.isdir(processed_outputs_dir):
            continue
        for folder_name in sorted(os.listdir(processed_outputs_dir)):
            book_dir = os.path.join(processed_outputs_dir, folder_name)
            if os.path.isdir(book_dir):
                yield course, folder_name, book_dir


def _is_stale(existing: dict, source_mtime: float, content_hash: str) -> bool:
    """True if the .md file's content actually changed since this card
    was last written -- i.e. its file_id (derived from the unchanged
    PDF) and path didn't move, so reconciliation would otherwise never
    notice (e.g. a fixed transcription pipeline was re-run against the
    same PDF).

    content_hash is the real signal, primary and decisive whenever a
    card has one. mtime is only a one-time migration bridge for a
    legacy card indexed before content_hash existed -- confirmed live
    that mtime alone is unsafe as an ongoing signal: something (a
    container/session remount) once reset every .md's mtime to the same
    instant in one real corpus, and a plain mtime comparison would have
    spuriously regenerated cards whose content hadn't actually changed.
    Every reconciliation stores content_hash going forward (see
    reconcile_and_write and _reconcile_one's backfill-on-unchanged
    path), so the mtime branch only ever fires once per card."""
    stored_hash = existing.get("content_hash")
    if stored_hash is not None:
        return stored_hash != content_hash

    raw = existing.get("source_updated_at")
    if not raw:
        return True
    try:
        card_time = datetime.fromisoformat(raw)
    except ValueError:
        return True
    md_time = datetime.fromtimestamp(source_mtime, tz=timezone.utc)
    return md_time > card_time


def _backfill_content_hash(academic_hub_root: str, course: str, file_id: str, content_hash: str) -> None:
    """Cheap, local-only patch (no LLM/embedding call) for a card that
    the mtime bridge in _is_stale just verified is NOT actually stale,
    but that has no content_hash yet (a legacy card, or one that's never
    been touched since content_hash was added) -- migrates it onto
    hash-based tracking so it never needs the mtime bridge again."""
    cards = load_shard(academic_hub_root, course)
    changed = False
    for c in cards:
        if c.get("file_id") == file_id and c.get("content_hash") != content_hash:
            c["content_hash"] = content_hash
            changed = True
    if changed:
        save_shard(academic_hub_root, course, cards)


def _reconcile_one(academic_hub_root, course_name, folder_category, file_id, rel_path,
                    rel_pdf_path, content_sample, page_count, client, force, stats, source_mtime,
                    content_hash):
    existing = None
    for c in load_shard(academic_hub_root, course_name):
        if c.get("file_id") == file_id:
            existing = c
            break

    stale = existing is not None and _is_stale(existing, source_mtime, content_hash)
    already_current = (
        existing is not None and not force and not stale
        and not existing.get("needs_indexing")
        and existing.get("path") == rel_path
    )
    if already_current:
        if existing.get("content_hash") is None:
            _backfill_content_hash(academic_hub_root, course_name, file_id, content_hash)
        stats["unchanged"] += 1
        return

    is_first_time = existing is None
    # Three reasons need a fresh generate_index_card() call, not just a
    # metadata patch: force=True; a stale existing card (its .md content
    # changed even though file_id/path didn't -- e.g. a fixed
    # transcription pipeline was re-run against the same PDF; see
    # _is_stale); or a needs_indexing card (a previous generation attempt
    # failed and was never actually retried -- confirmed live: it
    # correctly bypasses "already current" above, but without this,
    # reconcile_and_write() still finds the old card by file_id and just
    # patches its metadata, never calling generate_index_card() again).
    # reconcile_and_write() only regenerates on a true no-match, so the
    # old card is removed first to force that path in all three cases.
    # A plain path change (file moved, content genuinely unchanged) is
    # deliberately NOT included here -- reconcile_and_write()'s cheap
    # patch-only path is correct for that case, not a bug to route
    # around. Doesn't affect `is_first_time`, which the stats
    # classification below still needs to reflect accurately --
    # "updated", not "generated", for a file that was already indexed.
    needs_retry = existing is not None and existing.get("needs_indexing")
    if (force or stale or needs_retry) and existing is not None:
        remaining = [c for c in load_shard(academic_hub_root, course_name) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, course_name, remaining)
        recompute_course_entry(academic_hub_root, course_name)

    reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_path, source_pdf_path=rel_pdf_path,
        course=course_name, folder_category=folder_category, content_sample=content_sample,
        page_count=page_count, client=client, content_hash=content_hash,
    )
    if is_first_time:
        stats["generated"] += 1
    elif existing is not None and existing.get("course") != course_name:
        stats["moved"] += 1
    else:
        stats["updated"] += 1


def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {
        "generated": 0, "updated": 0, "unchanged": 0, "moved": 0,
        "orphaned": 0, "pruned": 0, "skipped_no_source_pdf": 0, "skipped_empty_md": 0,
    }
    seen_file_ids: set[str] = set()

    for course_name, category, pdf_path in _notes_pdf_paths(academic_hub_root, course):
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", f"{basename}.md")
        if not os.path.exists(md_path):
            continue  # not converted yet -- nothing to index
        if os.path.getsize(md_path) == 0:
            # A 0-byte .md with a real source PDF sitting next to it means
            # the PDF was never actually transcribed (see
            # docs/2026-08-28-known-errors-todo.md) -- generating a card
            # from it would just produce a vacuous "this is empty" summary.
            # Not added to seen_file_ids: if a vacuous card already exists
            # from an earlier run, this lets the normal orphan-flagging
            # pass below clean it up rather than inventing a second
            # "this card is bad" mechanism.
            print(f"WARNING: {md_path} is empty (0 bytes) but its source PDF exists -- "
                  f"skipping. The PDF likely hasn't been transcribed yet.")
            stats["skipped_empty_md"] += 1
            continue

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_md_path,
                       rel_pdf_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(md_path),
                       content_hash=compute_content_hash(md_path))

    for course_name, folder_name, book_dir in _textbook_book_dirs(academic_hub_root, course):
        metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        source_pdf_path = metadata.get("source_pdf_path")
        if not source_pdf_path:
            print(f"WARNING: {folder_name} has no source_pdf_path in its _metadata.json yet "
                  f"(converted before this field existed) -- skipping. Re-run convert_textbook.py "
                  f"on its PDF, or add source_pdf_path by hand, then rerun rebuild.")
            stats["skipped_no_source_pdf"] += 1
            continue

        pdf_path = os.path.join(academic_hub_root, source_pdf_path)
        if not os.path.exists(pdf_path):
            print(f"WARNING: {folder_name}'s source_pdf_path ({source_pdf_path}) does not exist "
                  f"on disk -- skipping.")
            stats["skipped_no_source_pdf"] += 1
            continue

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)
        course_name = derive_course(source_pdf_path)  # trust the PDF's own path, not the folder walk

        md_path = os.path.join(book_dir, f"{folder_name}.md")
        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read(TEXTBOOK_CONTENT_SAMPLE_CHARS)

        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        page_count = metadata.get("total_pages_processed")

        _reconcile_one(academic_hub_root, course_name, "textbooks-and-papers", file_id, rel_md_path,
                       source_pdf_path, content_sample, page_count, client, force, stats,
                       source_mtime=os.path.getmtime(md_path),
                       content_hash=compute_content_hash(md_path))

        # Real-corpus finding: describe_images.py's link_rag_md() writes
        # rag_md_path into _metadata.json unconditionally, but only sets
        # it on the index card if one already existed at that exact
        # moment -- if it ran before (or independent of) a rebuild, the
        # card's own rag_md_path is silently left None forever with no
        # automatic way to catch up. _metadata.json is the durable
        # record, so reconcile from it here every time; cheap local I/O,
        # no LLM/embedding call, safe to repeat even when already correct.
        rag_md_path = metadata.get("rag_md_path")
        if rag_md_path:
            found = find_card_by_file_id(academic_hub_root, file_id)
            if found is not None and found[1].get("rag_md_path") != rag_md_path:
                set_rag_md_path(academic_hub_root, file_id, rag_md_path)

    _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course, prune, stats)
    return stats


def _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course_filter, prune, stats):
    index_dir = os.path.join(academic_hub_root, ".index")
    if not os.path.isdir(index_dir):
        return
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "tags.json"):
            continue
        shard_course = name[:-len(".json")]
        if course_filter and shard_course != course_filter:
            continue
        cards = load_shard(academic_hub_root, shard_course)
        changed = False
        kept = []
        for card in cards:
            if card.get("file_id") in seen_file_ids:
                kept.append(card)
                continue
            if prune:
                stats["pruned"] += 1
                changed = True
                continue
            if not card.get("orphaned"):
                card["orphaned"] = True
                stats["orphaned"] += 1
                changed = True
            kept.append(card)
        if changed:
            save_shard(academic_hub_root, shard_course, kept)
            recompute_course_entry(academic_hub_root, shard_course)


def _bool_arg(value: str) -> bool:
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


def build_arg_parser() -> argparse.ArgumentParser:
    default_root = os.path.join(os.path.dirname(__file__), "..", "academic-hub")
    parser = argparse.ArgumentParser(description="Search and maintain the academic-hub source index.")
    parser.add_argument("--academic-hub", default=default_root, help="Path to the academic-hub root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Search the index for relevant sources.")
    query.add_argument("query")
    query.add_argument("--course", default=None)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--doc-type", default=None)
    query.add_argument("--has-solutions", type=_bool_arg, default=None)
    query.add_argument("--max-level", default=None, choices=list(KNOWN_LEVELS))
    query.add_argument("--passages", action="store_true",
                        help="Return passage-level results instead of file-level results.")

    rebuild_p = subparsers.add_parser("rebuild", help="Backfill/reconcile index cards.")
    rebuild_p.add_argument("--course", default=None)
    rebuild_p.add_argument("--force", action="store_true")
    rebuild_p.add_argument("--prune", action="store_true")

    retag_p = subparsers.add_parser("retag", help="Mine and apply tags across the whole corpus.")
    retag_p.add_argument("--dry-run", action="store_true")

    chunk_p = subparsers.add_parser("chunk", help="Chunk and embed indexed files into citable passages.")
    chunk_p.add_argument("--course", default=None)
    chunk_p.add_argument("--file", default=None)
    chunk_p.add_argument("--dry-run", action="store_true")

    ask_p = subparsers.add_parser("ask", help="Ask a single grounded question (no conversation memory).")
    ask_p.add_argument("question")
    ask_p.add_argument("--course", default=None)

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "query":
        if args.passages:
            results = search_passages(args.academic_hub, args.query, client, course=args.course, top_k=args.top_k)
            for r in results:
                print(f"{r.score:.3f}  [{r.course}]  {r.path}  ({r.citation})\n    {r.text[:200]}")
        else:
            results = search(
                args.academic_hub, args.query, client, course=args.course, top_k=args.top_k,
                doc_type=args.doc_type, has_solutions=args.has_solutions, max_level=args.max_level,
            )
            for r in results:
                print(f"{r.score:.3f}  [{r.course}/{r.doc_type}]  {r.path}\n    {r.reason}")
    elif args.command == "rebuild":
        stats = rebuild(args.academic_hub, client, course=args.course, force=args.force, prune=args.prune)
        print(stats)
    elif args.command == "retag":
        stats = retag(args.academic_hub, client, dry_run=args.dry_run)
        print(stats)
    elif args.command == "chunk":
        stats = chunk(args.academic_hub, client, course=args.course, file=args.file, dry_run=args.dry_run)
        print(stats)
    elif args.command == "ask":
        from rag_agent import answer_question
        result = answer_question(args.academic_hub, args.question, client, course=args.course)
        print(result.answer)
        for c in result.citations:
            print(f"  - {c.path} ({c.citation})")


if __name__ == "__main__":
    main()
