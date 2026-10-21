"""Read-only discovery and preflight for academic-hub Markdown sources.

Classification is deliberately based on producer paths/metadata and existing
cards, never on a claim that an unpaired Markdown file must be derivative.
"""
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from core.env.frontmatter import parse_frontmatter
from core.indexer.index_card import (
    compute_content_hash, compute_id_from_parts, list_courses, load_shard,
)

SOURCE_KINDS = frozenset({"markdown_only", "generated_companion"})
_AUXILIARY_SUFFIXES = (
    "_gemini_solutions", "_guided_solutions", "_solutions_long", "_solutions_short",
    "_hints", "_hint", "_solutions", "_solution", "_answers",
)


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _all_cards(root: str) -> list[dict]:
    return [card for course in list_courses(root) for card in load_shard(root, course)]


def _safe_file(root: str, path: str) -> bool:
    notes = Path(root, "academic_notes").resolve()
    target = Path(path)
    try:
        return target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(notes)
    except (OSError, ValueError):
        return False


def exact_markdown_path(root: str, course: str, rel_path: str) -> str:
    """Resolve an exact hub-relative selector without permitting path escape."""
    if not course or not rel_path or "\\" in rel_path or not rel_path.endswith(".md"):
        raise ValueError("--file must be an exact hub-relative .md path")
    parts = Path(rel_path).parts
    if len(parts) < 4 or parts[:2] != ("academic_notes", course) or any(p in (".", "..") for p in parts):
        raise ValueError("--file must be beneath academic_notes/<course>/")
    path = os.path.join(root, *parts)
    if not _safe_file(root, path):
        raise ValueError("--file is missing, a symlink, or outside academic_notes")
    return path


def _iter_notes(root: str, course: str | None, exact: str | None):
    if exact is not None:
        yield exact
        return
    notes = os.path.join(root, "academic_notes")
    if not os.path.isdir(notes):
        return
    for course_name in sorted(os.listdir(notes)):
        if course is not None and course_name != course:
            continue
        course_dir = os.path.join(notes, course_name)
        if not os.path.isdir(course_dir) or os.path.islink(course_dir) or course_name.startswith("."):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir, followlinks=False):
            dirnames[:] = [d for d in sorted(dirnames) if not d.startswith(".") and not os.path.islink(os.path.join(dirpath, d))]
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                if name.lower().endswith(".md") and not name.startswith(".") and _safe_file(root, path):
                    yield path


def _other_live_copy(root: str, rel_path: str, content_hash: str) -> bool:
    """Exact-file move repair must also see copies outside its selector."""
    selected = os.path.join(root, *rel_path.split("/"))
    size = os.path.getsize(selected)
    for path in _iter_notes(root, None, None):
        if os.path.normcase(path) == os.path.normcase(selected):
            continue
        if os.path.getsize(path) == size and compute_content_hash(path) == content_hash:
            return True
    return False


def _book_parent(rel_path: str, cards: list[dict]) -> tuple[dict | None, bool]:
    parts = rel_path.split("/")
    if len(parts) < 7 or parts[2] != "textbooks" or parts[3] != "processed_outputs" or parts[5] != "chapters":
        return None, False
    prefix = "/".join(parts[:5]) + "/"
    matches = [c for c in cards if c.get("doc_type") == "textbook" and (c.get("rag_md_path") or "").startswith(prefix)]
    return (matches[0] if len(matches) == 1 else None), len(matches) > 1


def _auxiliary_parent(rel_path: str, cards: list[dict]) -> tuple[dict | None, str | None, bool]:
    stem = Path(rel_path).stem.lower()
    role = None
    base = None
    for suffix in _AUXILIARY_SUFFIXES:
        if stem.endswith(suffix):
            base = stem[:-len(suffix)]
            role = "hints" if "hint" in suffix else "solutions"
            break
    if not base:
        return None, None, False
    parts = rel_path.split("/")
    category = parts[:3]
    matches = []
    for card in cards:
        card_path = card.get("path") or ""
        card_parts = card_path.split("/")
        if card_parts[:3] != category or card_path == rel_path:
            continue
        card_stem = Path(card_path).stem.lower()
        if card_stem == base:
            matches.append(card)
    return (matches[0] if len(matches) == 1 else None), role, len(matches) > 1


def classify_markdown(root: str, course: str | None = None, exact: str | None = None,
                      reserved_paths: set[str] | None = None) -> list[dict]:
    """Return one structured, read-only classification per Markdown path."""
    cards = _all_cards(root)
    by_path = {c.get("path"): c for c in cards if c.get("path")}
    by_id = {c.get("file_id"): c for c in cards if c.get("file_id")}
    attached = {c.get("rag_md_path"): c for c in cards if c.get("rag_md_path")}
    reserved = reserved_paths or set()
    found: list[dict] = []
    seen_case: dict[str, str] = {}
    for path in _iter_notes(root, course, exact):
        rel = _rel(root, path)
        parts = rel.split("/")
        row = {
            "path": rel, "course": parts[1], "folder_category": parts[2] if len(parts) > 3 else parts[-2],
            "classification": "unknown_origin", "source_kind": "markdown_only",
            "index_separately": True, "companion_of_file_id": None, "companion_of_path": None,
            "companion_role": None, "relationship_basis": None,
            "existing_file_id": (by_path.get(rel) or {}).get("file_id"),
        }
        lower = rel.casefold()
        if lower in seen_case and seen_case[lower] != rel:
            row.update(classification="case_collision", index_separately=False)
            found.append(row)
            continue
        seen_case[lower] = rel
        if os.path.getsize(path) == 0:
            row.update(classification="empty", index_separately=False)
        elif rel in attached:
            row.update(classification="attached_rendering", index_separately=False,
                       companion_of_file_id=attached[rel]["file_id"], relationship_basis="rag_md_path")
        elif rel in reserved:
            row.update(classification="producer_owned", index_separately=False)
        elif rel.endswith(".excalidraw.md") and "/processed_outputs/" in rel:
            rag_rel = rel[:-3] + ".rag.md"
            rag_card = by_path.get(rag_rel)
            if rag_card:
                row.update(classification="attached_rendering", index_separately=False,
                           companion_of_file_id=rag_card["file_id"],
                           relationship_basis="excalidraw_rag_sibling")
            elif os.path.isfile(os.path.join(root, *rag_rel.split("/"))):
                row.update(classification="producer_owned", index_separately=False)
            else:
                row.update(classification="ambiguous_owner", index_separately=False)
        elif rel.endswith(".excalidraw.md") or os.path.basename(rel) == "__index.md":
            row.update(classification="non_content_auxiliary", index_separately=False)
        elif rel in by_path and by_path[rel].get("source_kind") not in SOURCE_KINDS:
            row.update(classification="producer_owned", index_separately=False)
        else:
            parent, ambiguous = _book_parent(rel, cards)
            if parent:
                parent_rendering = parent.get("rag_md_path")
                parent_file = os.path.join(root, *parent_rendering.split("/")) if parent_rendering else None
                if (parent_file and os.path.isfile(parent_file)
                        and os.path.getsize(path) == os.path.getsize(parent_file)
                        and compute_content_hash(path) == compute_content_hash(parent_file)):
                    row.update(classification="attached_rendering", index_separately=False,
                               companion_of_file_id=parent["file_id"],
                               relationship_basis="identical_parent_rendering")
                else:
                    row.update(classification="generated_companion", source_kind="generated_companion",
                               companion_of_file_id=parent["file_id"], companion_role="chapter",
                               relationship_basis="textbook_chapter_path")
            else:
                parent, role, aux_ambiguous = _auxiliary_parent(rel, cards)
                if parent:
                    row.update(classification="linked_auxiliary", companion_of_file_id=parent["file_id"],
                               companion_role=role, relationship_basis="unique_category_stem")
                elif role:
                    row.update(classification="ambiguous_parent" if aux_ambiguous else "unlinked_auxiliary",
                               companion_role=role)
                elif ambiguous:
                    row["classification"] = "ambiguous_parent"
            if rel.endswith(".excalidraw.questions.md"):
                with open(path, encoding="utf-8") as handle:
                    fields, _ = parse_frontmatter(handle.read())
                parent_id = fields.get("source_note_file_id")
                if parent_id:
                    row.update(classification="generated_companion", source_kind="generated_companion",
                               companion_of_file_id=parent_id, companion_role="questions",
                               relationship_basis="question_sidecar_frontmatter")
            old_card = by_path.get(rel)
            if (old_card and row["companion_of_file_id"] is None
                    and old_card.get("companion_of_file_id")
                    and old_card.get("source_kind") in SOURCE_KINDS):
                row.update(classification="dangling_companion",
                           source_kind=old_card["source_kind"],
                           companion_of_file_id=old_card["companion_of_file_id"],
                           companion_role=old_card.get("companion_role"),
                           relationship_basis=old_card.get("relationship_basis"))
        found.append(row)
        parent = by_id.get(row["companion_of_file_id"])
        row["companion_of_path"] = parent.get("path") if parent else None
    return found


def plan_markdown(root: str, course: str | None = None, exact: str | None = None,
                  reserved_paths: set[str] | None = None, force: bool = False) -> list[dict]:
    """Attach stable IDs, content hashes, actions, and paid-call estimates."""
    cards = _all_cards(root)
    by_path = {c.get("path"): c for c in cards if c.get("path")}
    rows = classify_markdown(root, course, exact, reserved_paths)
    active_paths = {r["path"] for r in rows}
    for row in rows:
        row["content_hash"] = None
        if row["index_separately"]:
            path = os.path.join(root, *row["path"].split("/"))
            try:
                row["content_hash"] = compute_content_hash(path)
            except OSError:
                pass
    new_hash_counts = Counter(r["content_hash"] for r in rows
                              if r["index_separately"] and r["path"] not in by_path
                              and r["content_hash"] is not None)
    for row in rows:
        row.update(file_id=None, action="skip", estimated_paid_cards=0, estimated_paid_calls=0,
                   prior_file_id=row.pop("existing_file_id"), status="preview")
        if not row["index_separately"]:
            row["action"] = "attach" if row["classification"] == "attached_rendering" else "skip"
            continue
        if row["content_hash"] is None:
            row.update(action="error", status="cannot read Markdown source")
            continue
        old = by_path.get(row["path"])
        if old is None and new_hash_counts[row["content_hash"]] == 1:
            matches = [c for c in cards if c.get("source_kind") == row["source_kind"]
                       and c.get("content_hash") == row["content_hash"]
                       and c.get("path") not in active_paths
                       and not os.path.isfile(os.path.join(root, *(c.get("path") or "").split("/")))]
            old = matches[0] if len(matches) == 1 else None
            if len(matches) > 1:
                row["classification"] = "ambiguous_move"
            if old is not None and _other_live_copy(root, row["path"], row["content_hash"]):
                old = None
                row["classification"] = "ambiguous_move"
        elif old is None and new_hash_counts[row["content_hash"]] > 1:
            row["classification"] = "ambiguous_move"
        if old:
            row["file_id"] = old["file_id"]
        elif row["companion_role"] == "questions" and row["companion_of_file_id"]:
            row["file_id"] = compute_id_from_parts(["excalidraw_questions", row["companion_of_file_id"]])
        else:
            row["file_id"] = compute_id_from_parts([row["source_kind"], row["path"]])
        if old is None:
            row["action"] = "new"
        elif old.get("path") != row["path"]:
            row["action"] = "move"
        elif force or old.get("content_hash") != row["content_hash"] or old.get("needs_indexing"):
            row["action"] = "refresh"
        elif (old.get("source_kind") != row["source_kind"]
              or old.get("companion_of_file_id") != row["companion_of_file_id"]
              or old.get("companion_role") != row["companion_role"]
              or old.get("relationship_basis") != row["relationship_basis"]
              or old.get("orphaned")):
            row["action"] = "update_metadata"
        else:
            row["action"] = "unchanged"
        row["estimated_paid_cards"] = int(row["action"] in ("new", "refresh"))
        row["estimated_paid_calls"] = 2 * row["estimated_paid_cards"]
    return rows
