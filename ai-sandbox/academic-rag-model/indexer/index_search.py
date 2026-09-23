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

from indexer.chunk_index import chunk, load_chunks
from common.academic_hub_paths import TEXTBOOK_FOLDER_NAMES, resolve_output_dir, to_resources_root
from common.frontmatter import parse_frontmatter
from common.gemini_utils import get_gemini_client, load_dotenv_override
from indexer.index_card import (
    TEXTBOOK_CONTENT_SAMPLE_CHARS,
    EMBEDDING_DIMENSIONALITY,
    EMBEDDING_MODEL,
    EXCALIDRAW_DOC_TYPES,
    KNOWN_DOC_TYPES,
    KNOWN_LEVELS,
    LECTURE_NOTE_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    compute_id_from_parts,
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
from indexer.retag import retag

DEFAULT_COURSE_CANDIDATES = 3


@dataclass
class SearchResult:
    path: str
    course: str
    doc_type: str
    score: float
    reason: str
    file_id: str
    root: str


def _embed_query(query: str, client) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL, contents=query,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def _candidate_courses(
    roots: list[str], query_embedding: list[float], course: str | None,
) -> list[tuple[str, str]]:
    """Returns (root, course) pairs, not bare course names -- two
    different corpora can each have a course with the same name (e.g.
    both academic-hub and research/ could have a 'notes' course), so a
    candidate is only unambiguous once qualified by which root it came
    from. With an explicit course filter, every given root is checked
    for that course name rather than picking one root arbitrarily."""
    if course is not None:
        return [(root, course) for root in roots]
    scored: list[tuple[float, str, str]] = []
    for root in roots:
        for entry in load_courses(root).values():
            score = cosine_similarity(query_embedding, entry.get("embedding") or [])
            scored.append((score, root, entry["course"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [(root, c) for _, root, c in scored[:DEFAULT_COURSE_CANDIDATES]]


def search(
    roots: list[str], query: str, client, course: str | None = None, top_k: int = 5,
    doc_type: str | None = None, has_solutions: bool | None = None, max_level: str | None = None,
) -> list[SearchResult]:
    query_embedding = _embed_query(query, client)
    candidate_courses = _candidate_courses(roots, query_embedding, course)

    scored: list[SearchResult] = []
    for root, c in candidate_courses:
        for card in load_shard(root, c):
            # orphaned=true means "this card's source couldn't be found on
            # the last rebuild" -- a provenance note, not a verdict on the
            # card's own content (real finding, 2026-09-23: a deleted or
            # unmatched-rename source PDF must not blackhole already-
            # transcribed, still-real .md content from search). Only
            # needs_indexing (generation failed, no real card yet) and a
            # missing embedding still exclude a card.
            if card.get("needs_indexing") or not card.get("embedding"):
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
                score=score, reason=card.get("summary", ""), file_id=card["file_id"], root=root,
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
    root: str


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
    paragraph_range = chunk.get("paragraph_range")
    if paragraph_range:
        start, end = paragraph_range
        parts.append(f"¶{start}" if start == end else f"¶{start}-{end}")
    return ", ".join(parts)


def search_passages(
    roots: list[str], query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5, doc_type: str | None = None,
) -> list[PassageResult]:
    """Three-stage funnel (spec §6): reuses search() for the file-level
    pass (100% of the existing course-then-file filtering, not
    duplicated), then ranks that shortlist's chunks by cosine similarity
    to the same query embedding. A file with no chunks yet (chunk
    hasn't been run against it) contributes nothing and is silently
    skipped, not an error -- degrades gracefully during the transition
    period before `chunk` has been run corpus-wide. doc_type filters
    which files are eligible at the file-level pass (e.g. "problem_set"
    vs "textbook" -- see problem_gen/generator.py's two-pool retrieval,
    docs/superpowers/specs/2026-09-03-problem-generation-design.md §3)."""
    file_results = search(roots, query, client, course=course, top_k=file_top_k, doc_type=doc_type)
    if not file_results:
        return []

    query_embedding = _embed_query(query, client)
    chunks_by_root_course: dict[tuple[str, str], list[dict]] = {}
    scored: list[PassageResult] = []
    for file_result in file_results:
        key = (file_result.root, file_result.course)
        if key not in chunks_by_root_course:
            chunks_by_root_course[key] = load_chunks(file_result.root, file_result.course)
        for c in chunks_by_root_course[key]:
            if c["file_id"] != file_result.file_id:
                continue
            score = cosine_similarity(query_embedding, c["embedding"])
            scored.append(PassageResult(
                chunk_id=c["chunk_id"], file_id=c["file_id"], path=file_result.path,
                course=file_result.course, score=score, text=c["text"],
                citation=_render_citation(c), root=file_result.root,
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


def _notes_pdf_paths(academic_hub_root: str, course_filter: str | None):
    """Recursive as of 2026-09-22 (was hardcoded to exactly course/category/
    *.pdf, two levels, no deeper) -- a user reorganizing ta_notes/ into year
    subfolders (ta_notes/2026/foo.pdf) found those PDFs silently invisible
    to rebuild(), even though route_notes_transcribe.py's own discovery
    already recursed and found them fine. `category` is the PDF's own
    immediate parent directory basename, whatever the depth -- matches
    transcribe_notes.py's derive_folder_category() exactly (same value for
    a flat course/category/foo.pdf as before this change; the actual
    subfolder name, e.g. "2026", for a nested one), so folder_category
    classification stays consistent between the live transcription
    pipeline and this rebuild-time walker.

    Also discovers PDFs already migrated to academic_resources/ (2026-09-23,
    real finding from the first real migration run) -- without this, a
    previously-transcribed PDF becomes invisible to this walker the moment
    its source moves, so its file_id is never re-added to seen_file_ids and
    the orphan pass silently flags its still-good card. Only descends into
    an academic_resources/<course>/<category>/ whose <category> also
    exists directly under academic_notes/<course>/ -- same guard
    route_notes_transcribe.py's own _discover_migrated_pdf_sources uses --
    and never into a textbook folder, even though academic_notes/<course>/
    textbooks/ exists to hold each book's mirrored .rag.md, so
    academic_resources/<course>/textbooks/ (a different pipeline's home)
    never gets swept in."""
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir):
            dirnames[:] = [d for d in sorted(dirnames) if d != "processed_outputs" and not d.startswith(".")]
            category = os.path.basename(dirpath)
            for name in sorted(filenames):
                if name.lower().endswith(".pdf"):
                    yield course, category, os.path.join(dirpath, name)

        notes_top_level_categories = {
            name for name in os.listdir(course_dir) if os.path.isdir(os.path.join(course_dir, name))
        }
        try:
            resources_course_dir = to_resources_root(course_dir)
        except ValueError:
            resources_course_dir = None
        if resources_course_dir and os.path.isdir(resources_course_dir):
            for top_category in sorted(os.listdir(resources_course_dir)):
                # textbooks/ is excluded by name: it has an academic_notes/
                # counterpart only because each book's .rag.md is mirrored
                # there, not because its PDFs are notes.
                if top_category not in notes_top_level_categories or top_category in TEXTBOOK_FOLDER_NAMES:
                    continue
                top_category_dir = os.path.join(resources_course_dir, top_category)
                if not os.path.isdir(top_category_dir):
                    continue
                for dirpath, dirnames, filenames in os.walk(top_category_dir):
                    dirnames[:] = [d for d in sorted(dirnames) if not d.startswith(".")]
                    category = os.path.basename(dirpath)
                    for name in sorted(filenames):
                        if name.lower().endswith(".pdf"):
                            yield course, category, os.path.join(dirpath, name)


def _excalidraw_note_paths(academic_hub_root: str, course_filter: str | None):
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
                if name.lower().endswith(".excalidraw.md"):
                    yield course, category, os.path.join(category_dir, name)


_EXCALIDRAW_IMAGE_EXTENSIONS = (".png", ".svg")


def _find_excalidraw_image(excalidraw_md_path: str, academic_hub_root: str) -> str | None:
    stem = excalidraw_md_path[: -len(".md")]
    for ext in _EXCALIDRAW_IMAGE_EXTENSIONS:
        local = stem + ext
        if os.path.exists(local):
            return local
    try:
        mirrored_stem = to_resources_root(stem)
    except ValueError:
        return None
    for ext in _EXCALIDRAW_IMAGE_EXTENSIONS:
        mirrored = mirrored_stem + ext
        if os.path.exists(mirrored):
            return mirrored
    return None


# Real-corpus finding (2026-09-06): math-camp's textbook folder was
# renamed on disk from "textbooks-and-papers" to "textbooks" at some
# point, but every other course still uses "textbooks-and-papers".
# Recognizing only the old name here made this walk silently see zero
# book dirs for math-camp -- rebuild() never touched those files again,
# with no error to signal it (see docs/status/2026-09-06-problem-corpus-extraction-status.md).
# Checking both aliases makes the walk match whichever name a course
# actually uses on disk.
_TEXTBOOK_FOLDER_NAMES = ("textbooks", "textbooks-and-papers")


def _textbook_book_dirs(academic_hub_root: str, course_filter: str | None):
    resources_root = os.path.join(academic_hub_root, "academic_resources")
    if not os.path.isdir(resources_root):
        return
    for course in sorted(os.listdir(resources_root)):
        if course_filter and course != course_filter:
            continue
        for category_folder_name in _TEXTBOOK_FOLDER_NAMES:
            category_root = os.path.join(resources_root, course, category_folder_name)
            if not os.path.isdir(category_root):
                continue
            # A course's textbook folder can itself have subfolders -- e.g.
            # "Bonus", for supplementary readings deliberately converted in
            # their own later batch rather than the main run (see
            # convert_textbook_agent_instructions.md's subdirectory
            # guidance). Walking the whole category tree for any directory
            # literally named processed_outputs/, rather than assuming one
            # sits directly under category_folder_name, is what makes a
            # book converted under such a subfolder still get indexed.
            # Confirmed live: a course's Bonus/ books (3 real, successfully
            # converted textbooks) were silently invisible to rebuild
            # before this fix -- zero index cards, no error anywhere.
            for dirpath, dirnames, _ in os.walk(category_root):
                if os.path.basename(dirpath) != "processed_outputs":
                    continue
                dirnames[:] = []  # found it -- don't walk into book subdirs (images/, etc.)
                # Effective category including any subfolder path between
                # category_folder_name and processed_outputs/ (e.g.
                # "textbooks/Bonus"), so the fallback PDF lookup below and
                # log messages stay accurate for nested subfolders too.
                rel_category = os.path.relpath(dirpath, os.path.join(resources_root, course))
                effective_category = os.path.dirname(rel_category).replace(os.sep, "/")
                for folder_name in sorted(os.listdir(dirpath)):
                    book_dir = os.path.join(dirpath, folder_name)
                    if os.path.isdir(book_dir):
                        yield course, effective_category, folder_name, book_dir


def _video_lecture_note_paths(academic_hub_root: str, course_filter: str | None):
    """lecture_notes/ (underscored) is shared with the Excalidraw pipeline's
    own category of the same name in every course except math-camp (folder
    vocabulary unification, 2026-09-22) -- an .excalidraw.md is never a
    video-lecture-note candidate at all (it's the Excalidraw pipeline's own
    source scene file, never paired with a .meta.json sidecar by design),
    so it's excluded up front rather than treated as "a candidate missing
    its sidecar" and warned about on every single rebuild in every course."""
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        lecture_notes_dir = os.path.join(notes_root, course, "lecture_notes")
        if not os.path.isdir(lecture_notes_dir):
            continue
        for name in sorted(os.listdir(lecture_notes_dir)):
            lower = name.lower()
            if not lower.endswith(".md") or lower.endswith(".excalidraw.md"):
                continue
            slug = name[:-3]
            meta_path = os.path.join(lecture_notes_dir, f"{slug}.meta.json")
            if not os.path.exists(meta_path):
                print(f"WARNING: {os.path.join(lecture_notes_dir, name)} has no sidecar "
                      f"{slug}.meta.json -- skipping.")
                continue
            yield course, os.path.join(lecture_notes_dir, name), meta_path


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


def _backfill_source_asset_path(academic_hub_root: str, course: str, file_id: str, source_asset_path: str) -> None:
    """Same treatment as _backfill_content_hash, for a legacy card (created
    before Task 2 added this field) that's otherwise not stale -- fills in
    the key without going through the full reconcile path, so a corpus-wide
    legacy backfill doesn't get misreported as a wave of real "updated"
    cards in rebuild()'s stats."""
    cards = load_shard(academic_hub_root, course)
    changed = False
    for c in cards:
        if c.get("file_id") == file_id and "source_asset_path" not in c:
            c["source_asset_path"] = source_asset_path
            changed = True
    if changed:
        save_shard(academic_hub_root, course, cards)


def _reconcile_one(academic_hub_root, course_name, folder_category, file_id, rel_path,
                    rel_pdf_path, content_sample, page_count, client, force, stats, source_mtime,
                    content_hash, known_doc_types=KNOWN_DOC_TYPES, source_asset_path=None):
    existing = None
    for c in load_shard(academic_hub_root, course_name):
        if c.get("file_id") == file_id:
            existing = c
            break

    stale = existing is not None and _is_stale(existing, source_mtime, content_hash)
    # source_asset_path=None means "this caller can't currently determine
    # it" (Task 2's convention), not "no change". A legacy card that never
    # had the key at all (pre-Task-2) is a silent backfill below, same
    # treatment as content_hash -- only a *present* value that disagrees
    # with a freshly-resolved one (the real post-migration case) forces a
    # refresh through the full reconcile path.
    source_asset_path_changed = (
        existing is not None and source_asset_path is not None
        and "source_asset_path" in existing
        and existing.get("source_asset_path") != source_asset_path
    )
    already_current = (
        existing is not None and not force and not stale
        and not existing.get("needs_indexing")
        and existing.get("path") == rel_path
        and existing.get("source_pdf_path") == rel_pdf_path
        and not source_asset_path_changed
    )
    if already_current:
        if existing.get("content_hash") is None:
            _backfill_content_hash(academic_hub_root, course_name, file_id, content_hash)
        if "source_asset_path" not in existing and source_asset_path is not None:
            _backfill_source_asset_path(academic_hub_root, course_name, file_id, source_asset_path)
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
        known_doc_types=known_doc_types, source_asset_path=source_asset_path,
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
        "skipped_duplicate_clone": 0,
    }
    seen_file_ids: set[str] = set()

    for course_name, category, pdf_path in _notes_pdf_paths(academic_hub_root, course):
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        md_path = os.path.join(resolve_output_dir(pdf_path), f"{basename}.md")
        if not os.path.exists(md_path):
            continue  # not converted yet -- nothing to index
        if os.path.getsize(md_path) == 0:
            # A 0-byte .md with a real source PDF sitting next to it means
            # the PDF was never actually transcribed (see
            # docs/trackers/2026-08-30-academic-hub-status.md) -- generating a card
            # from it would just produce a vacuous "this is empty" summary.
            # Not added to seen_file_ids: if a vacuous card already exists
            # from an earlier run, this lets the normal orphan-flagging
            # pass below clean it up rather than inventing a second
            # "this card is bad" mechanism.
            print(f"WARNING: {md_path} is empty (0 bytes) but its source PDF exists -- "
                  f"skipping. The PDF likely hasn't been transcribed yet.")
            stats["skipped_empty_md"] += 1
            continue

        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        # A clone linked by notes.transcribe_notes.link_duplicate_note
        # (real finding, 2026-09-23: two byte-identical econometrics PDFs
        # in different categories were independently transcribed before
        # that fix existed) -- never re-hash its PDF: that would always
        # equal the canonical card's own file_id (the PDFs are byte-
        # identical by definition), which is exactly what silently made
        # the second one processed overwrite the first one's card `path`
        # in place. Re-derive the same id link_duplicate_note wrote onto
        # the card, purely so --prune doesn't evict it as an apparent
        # orphan -- mirrors the textbook duplicate-clone skip below.
        frontmatter_fields, _body = parse_frontmatter(content_sample)
        duplicate_of_file_id = frontmatter_fields.get("duplicate_of_file_id")
        if duplicate_of_file_id:
            seen_file_ids.add(compute_id_from_parts([duplicate_of_file_id, rel_pdf_path]))
            stats["skipped_duplicate_clone"] += 1
            continue

        file_id = compute_file_id(pdf_path)
        seen_file_ids.add(file_id)

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_md_path,
                       rel_pdf_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(md_path),
                       content_hash=compute_content_hash(md_path),
                       source_asset_path=rel_pdf_path)

    for course_name, category_folder_name, folder_name, book_dir in _textbook_book_dirs(academic_hub_root, course):
        metadata_path = os.path.join(book_dir, f"{folder_name}_metadata.json")
        if not os.path.exists(metadata_path):
            continue
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        duplicate_of_file_id = metadata.get("duplicate_of_file_id")
        if duplicate_of_file_id:
            # A clone directory (indexer/duplicate_check.py's
            # copy_duplicate_artifacts) -- never re-hash or reconcile it.
            # For a Tier 1 (byte-identical) clone, hashing this directory's
            # own PDF yields the SAME file_id as the canonical book, which
            # used to make reconcile_and_write's cross-course "file moved"
            # handling relocate the canonical card out of its own shard
            # (see docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
            # Component 3). The clone's own card already exists, correctly,
            # under a derived (non-hash) id -- re-derive that same id here,
            # from data already on hand, purely so --prune doesn't evict it
            # as an apparent orphan.
            clone_course = derive_course(metadata["source_pdf_path"])
            seen_file_ids.add(compute_id_from_parts([duplicate_of_file_id, clone_course]))
            stats["skipped_duplicate_clone"] += 1
            continue

        source_pdf_path = metadata.get("source_pdf_path")
        if not source_pdf_path:
            print(f"WARNING: {folder_name} has no source_pdf_path in its _metadata.json yet "
                  f"(converted before this field existed) -- skipping. Re-run convert_textbook.py "
                  f"on its PDF, or add source_pdf_path by hand, then rerun rebuild.")
            stats["skipped_no_source_pdf"] += 1
            continue

        pdf_path = os.path.join(academic_hub_root, source_pdf_path)
        if not os.path.exists(pdf_path):
            # source_pdf_path can be wrong for a book converted from a gs://
            # input on the VM: convert_textbook.py records the VM's own
            # local temp-download path there, which is meaningless once
            # back on this machine (see that script's own comment next to
            # source_pdf_filename, added to fix a related naming bug this
            # same root cause produced). The real source PDF is still
            # present locally though -- Step 3.2 uploads it to GCS without
            # moving/deleting the local copy -- so look for it by its real
            # filename (source_pdf_filename) in the directory this book's
            # processed_outputs/ folder lives under, before giving up.
            fallback_filename = metadata.get("source_pdf_filename")
            fallback_path = os.path.join(
                academic_hub_root, "academic_resources", course_name, category_folder_name, fallback_filename,
            ) if fallback_filename else None
            if fallback_path and os.path.exists(fallback_path):
                pdf_path = fallback_path
                source_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
            else:
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

        _reconcile_one(academic_hub_root, course_name, category_folder_name, file_id, rel_md_path,
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

    for course_name, md_path, meta_path in _video_lecture_note_paths(academic_hub_root, course):
        with open(meta_path, "r", encoding="utf-8") as f:
            sidecar = json.load(f)
        member_video_ids = sidecar.get("member_video_ids") or []
        if not member_video_ids:
            print(f"WARNING: {meta_path} has no member_video_ids -- skipping.")
            continue

        file_id = compute_id_from_parts(member_video_ids)
        seen_file_ids.add(file_id)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_meta_path = os.path.relpath(meta_path, academic_hub_root).replace(os.sep, "/")

        with open(md_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        _reconcile_one(academic_hub_root, course_name, "lecture_notes", file_id, rel_md_path,
                       rel_meta_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(md_path),
                       content_hash=compute_content_hash(md_path),
                       known_doc_types=LECTURE_NOTE_DOC_TYPES)

    for course_name, category, md_path in _excalidraw_note_paths(academic_hub_root, course):
        base_name = os.path.basename(md_path)[: -len(".excalidraw.md")]
        rag_path = os.path.join(os.path.dirname(md_path), "processed_outputs", f"{base_name}.excalidraw.rag.md")
        if not os.path.exists(rag_path):
            continue  # not transcribed yet -- nothing to index
        if os.path.getsize(rag_path) == 0:
            print(f"WARNING: {rag_path} is empty (0 bytes) but its source .excalidraw.md exists -- "
                  f"skipping. It likely hasn't been transcribed yet.")
            stats["skipped_empty_md"] += 1
            continue

        file_id = compute_file_id(md_path)
        seen_file_ids.add(file_id)
        rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")

        with open(rag_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        image_path = _find_excalidraw_image(md_path, academic_hub_root)
        rel_image_path = (
            os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/") if image_path else None
        )

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_rag_path,
                       rel_md_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(rag_path),
                       content_hash=compute_content_hash(rag_path),
                       known_doc_types=EXCALIDRAW_DOC_TYPES, source_asset_path=rel_image_path)

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
    default_root = os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")
    parser = argparse.ArgumentParser(description="Search and maintain a source index (academic-hub, research, or any other corpus root).")
    parser.add_argument(
        "--root", action="append", default=None,
        help="Path to a corpus root's own .index/ (repeatable, e.g. --root academic-hub --root "
             f"research -- query/ask search across every root given). Default if omitted: [{default_root}]. "
             "rebuild/retag/chunk are per-corpus maintenance operations and require exactly one --root.",
    )
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
    ask_p.add_argument("--visualize", action="store_true",
                        help="Also generate an interactive visualization for the question's concept.")
    ask_p.add_argument("--report", action="store_true",
                        help="Also combine the answer, citations, and visualization (if any) into one "
                             "self-contained HTML report.")

    return parser


_DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")


def _single_root(args) -> str:
    """rebuild/retag/chunk are per-corpus maintenance operations, not
    query-time federation -- each writes into exactly one root's own
    .index/, so more than one --root is a usage error, not something
    to silently pick the first of."""
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

    roots = args.root or [_DEFAULT_ROOT]
    if args.command == "query":
        if args.passages:
            results = search_passages(roots, args.query, client, course=args.course, top_k=args.top_k)
            for r in results:
                print(f"{r.score:.3f}  [{r.root}:{r.course}]  {r.path}  ({r.citation})\n    {r.text[:200]}")
        else:
            results = search(
                roots, args.query, client, course=args.course, top_k=args.top_k,
                doc_type=args.doc_type, has_solutions=args.has_solutions, max_level=args.max_level,
            )
            for r in results:
                print(f"{r.score:.3f}  [{r.root}:{r.course}/{r.doc_type}]  {r.path}\n    {r.reason}")
    elif args.command == "rebuild":
        stats = rebuild(_single_root(args), client, course=args.course, force=args.force, prune=args.prune)
        print(stats)
    elif args.command == "retag":
        stats = retag(_single_root(args), client, dry_run=args.dry_run)
        print(stats)
    elif args.command == "chunk":
        stats = chunk(_single_root(args), client, course=args.course, file=args.file, dry_run=args.dry_run)
        print(stats)
    elif args.command == "ask":
        from rag.rag_agent import answer_question
        result = answer_question(
            roots, args.question, client, course=args.course,
            visualize=args.visualize, report=args.report,
        )
        print(result.answer)
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        if result.report_path:
            print(f"  report: {result.report_path}")


if __name__ == "__main__":
    main()
