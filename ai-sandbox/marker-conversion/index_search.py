"""
index_search.py
Rebuild/backfill pass and two-stage search for the academic-hub source
indexer, plus its CLI.

Spec: docs/superpowers/specs/2026-08-27-source-indexer-design.md
"""
from __future__ import annotations

import json
import os

from index_card import (
    TEXTBOOK_CONTENT_SAMPLE_CHARS,
    compute_file_id,
    derive_course,
    load_shard,
    recompute_course_entry,
    reconcile_and_write,
    save_shard,
)


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


def _reconcile_one(academic_hub_root, course_name, folder_category, file_id, rel_path,
                    rel_pdf_path, content_sample, page_count, client, force, stats):
    existing = None
    for c in load_shard(academic_hub_root, course_name):
        if c.get("file_id") == file_id:
            existing = c
            break
    already_current = (
        existing is not None and not force and not existing.get("needs_indexing")
        and existing.get("path") == rel_path
    )
    if already_current:
        stats["unchanged"] += 1
        return

    was_new = existing is None
    # force=True on an existing, otherwise-current card still needs a
    # fresh generate_index_card() call -- reconcile_and_write() only
    # regenerates on a true no-match, so force removes the old card
    # first to force that path.
    if force and existing is not None:
        remaining = [c for c in load_shard(academic_hub_root, course_name) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, course_name, remaining)
        recompute_course_entry(academic_hub_root, course_name)
        was_new = True

    reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_path, source_pdf_path=rel_pdf_path,
        course=course_name, folder_category=folder_category, content_sample=content_sample,
        page_count=page_count, client=client,
    )
    if was_new:
        stats["generated"] += 1
    elif existing is not None and existing.get("course") != course_name:
        stats["moved"] += 1
    else:
        stats["updated"] += 1


def rebuild(academic_hub_root: str, client, course: str | None = None,
            force: bool = False, prune: bool = False) -> dict:
    stats = {
        "generated": 0, "updated": 0, "unchanged": 0, "moved": 0,
        "orphaned": 0, "pruned": 0, "skipped_no_source_pdf": 0,
    }
    seen_file_ids: set[str] = set()

    for course_name, category, pdf_path in _notes_pdf_paths(academic_hub_root, course):
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        md_path = os.path.join(os.path.dirname(pdf_path), "processed_outputs", f"{basename}.md")
        if not os.path.exists(md_path):
            continue  # not converted yet -- nothing to index

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_md_path,
                       rel_pdf_path, content_sample, None, client, force, stats)

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
                       source_pdf_path, content_sample, page_count, client, force, stats)

    _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course, prune, stats)
    return stats


def _flag_or_prune_orphans(academic_hub_root, seen_file_ids, course_filter, prune, stats):
    index_dir = os.path.join(academic_hub_root, ".index")
    if not os.path.isdir(index_dir):
        return
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "topics.json"):
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
