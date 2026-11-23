"""Discipline folders generated from the research profile (spec A, step 5).

Layout: a paper with a project (`projects` in its profile) stays where it is; a loose paper goes to a discipline
folder, and a discipline in `SPLIT_BY_SUBFIELD` gets one sub-folder per OpenAlex subfield (`social-sciences/development`).
A card's `course` is its top-level folder (what `derive_course` returns on a re-index); nested folders live in the path.

`plan_moves` is a dry run; `apply_moves` only touches the file ids it is told are approved, refuses any filename
collision before moving anything, can be re-run after an interruption, and logs an inverse for `undo_moves`.
The card's paths and course are rewritten in place, so the `file_id` (a hash of the PDF bytes) is untouched.
"""

import datetime
import html
import json
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from agent.literature.profile.review import atomic_write_json, effective_value
from core.indexer.chunk_index import load_chunks, save_chunks
from core.indexer.index_card import (derive_course, find_card_by_file_id, load_shard, recompute_course_entry,
                                     save_shard)
from core.indexer.research_profile import RESEARCH_REPORT_TYPES

OTHER = "other"
DEFAULT_MIN_PAPERS = 3
SPLIT_BY_SUBFIELD = frozenset({"Social Sciences"})
GENERAL = "general"
ARTICLES_BASE = "journal-articles"  # only papers under this folder are organised; other corpora (e.g. independent-research) stay put


@dataclass(frozen=True)
class Move:
    file_id: str
    from_folder: str
    to_folder: str
    reason: str
    title: str = ""


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") or OTHER


def current_folder(card: dict) -> str:
    """The folder of the card's PDF below its base directory ('' for a paper loose in the base)."""
    parts = (card.get("source_pdf_path") or card["path"]).split("/")
    return "/".join(parts[1:-1]) if card.get("source_pdf_path") else "/".join(parts[1:-2])


def _target(card: dict, discipline: str) -> str:
    folder = slug(discipline)
    if discipline in SPLIT_BY_SUBFIELD:
        subs = (card.get("research_profile") or {}).get("openalex_subfields") or []
        folder += "/" + (slug(subs[0]["label"]) if subs else GENERAL)
    return folder


def plan_moves(cards: list[dict], decisions_root: str, *, min_papers: int = DEFAULT_MIN_PAPERS) -> list[Move]:
    """Moves that would put each classified card in the folder of its (human-overridden) discipline. Disciplines
    with fewer than `min_papers` research papers, and non-research documents, are held in `other`. Papers that
    belong to a project are left where they are, and so is anything outside `ARTICLES_BASE`."""
    classified = []
    for card in cards:
        profile = card.get("research_profile") or {}
        discipline = effective_value(decisions_root, card, "discipline")
        in_library = (card.get("path") or "").split("/")[0] == ARTICLES_BASE
        if profile and discipline and in_library and not profile.get("projects"):
            research = effective_value(decisions_root, card, "report_type") in RESEARCH_REPORT_TYPES
            classified.append((card, discipline, research))
    counts = Counter(d for _, d, research in classified if research)
    moves = []
    for card, discipline, research in classified:
        if not research:
            target, reason = OTHER, "not a research document"
        elif discipline == OTHER:
            target, reason = OTHER, "discipline is other"
        elif counts[discipline] < min_papers:
            n = counts[discipline]
            target = OTHER
            reason = (f"discipline {discipline!r} has only {n} paper{'s' if n != 1 else ''}, "
                      f"fewer than {min_papers}: held in other")
        else:
            target, reason = _target(card, discipline), f"discipline {discipline!r} ({counts[discipline]} papers)"
        here = current_folder(card)
        if here.casefold() != target.casefold():  # NTFS treats a case-only difference as the same folder
            moves.append(Move(card["file_id"], here, target, reason, card.get("title") or ""))
    return moves


def render_plan_page(moves: list[Move]) -> str:
    """A dry-run listing with one checkbox per move, for the review Artifact."""
    rows = "\n".join(
        f'<tr><td><input type="checkbox" data-file-id="{html.escape(m.file_id)}" checked></td>'
        f"<td>{html.escape(m.title or m.file_id)}</td><td>{html.escape(m.from_folder)}</td><td>{html.escape(m.to_folder)}</td>"
        f"<td>{html.escape(m.reason)}</td></tr>" for m in moves)
    return ("<table><thead><tr><th>Move</th><th>Paper</th><th>From</th><th>To</th><th>Why</th></tr></thead>"
            f"<tbody>\n{rows}\n</tbody></table>")


def _swap(rel: str, old: str, new: str) -> str:
    """Replaces the folder `old` (relative to the base directory, '' for the base itself) with `new` in `rel`."""
    base, _, rest = rel.partition("/")
    if old:
        if not rest.startswith(old + "/"):
            raise ValueError(f"{rel!r} is not inside folder {old!r}")
        rest = rest[len(old) + 1:]
    return f"{base}/{new}/{rest}"


def _files(card: dict, old: str, new: str) -> list[tuple[str, str]]:
    pdf = card.get("source_pdf_path")
    rels = [card["path"]] + ([pdf, str(Path(pdf).with_suffix(".meta.json")).replace("\\", "/")] if pdf else [])
    stem = card["path"][:-3] if card["path"].endswith(".md") else card["path"]
    rels += [f"{stem}_pages_cache.json", f"{stem}_pages_driver.json"]  # the transcriber's page caches sit beside it
    return [(rel, _swap(rel, old, new)) for rel in rels]


def _relocate(index_root: str, file_id: str, renames: dict[str, str]) -> None:
    """Rewrites the card's paths through `renames`, and its course to the new top-level folder (the course a
    re-index would derive), moving it between shards when the course changes."""
    old_course, card = find_card_by_file_id(index_root, file_id)
    card = dict(card)
    for key in ("path", "source_pdf_path", "source_asset_path"):
        if card.get(key) in renames:
            card[key] = renames[card[key]]
    new_course = derive_course(card.get("source_pdf_path") or card["path"])
    card["course"] = new_course
    if new_course == old_course:
        save_shard(index_root, old_course, [card if c["file_id"] == file_id else c for c in load_shard(index_root, old_course)])
        return
    save_shard(index_root, new_course, load_shard(index_root, new_course) + [card])  # add before removing: a crash
    save_shard(index_root, old_course, [c for c in load_shard(index_root, old_course) if c["file_id"] != file_id])
    recompute_course_entry(index_root, old_course)  # leaves a duplicate, never a lost card
    recompute_course_entry(index_root, new_course)
    _move_chunks(index_root, file_id, old_course, new_course)


def _move_chunks(index_root: str, file_id: str, old_course: str, new_course: str) -> None:
    """Search loads chunks by the card's current course, so a moved paper's chunks must follow it."""
    old = load_chunks(index_root, old_course)
    mine = [c for c in old if c.get("file_id") == file_id]
    if not mine:
        return
    save_chunks(index_root, new_course, [c for c in load_chunks(index_root, new_course)
                                         if c.get("file_id") != file_id] + mine)
    save_chunks(index_root, old_course, [c for c in old if c.get("file_id") != file_id])


def log_path(index_root: str) -> str:
    return os.path.join(index_root, ".index", "research_profile", "folder_moves.json")


def _read_log(index_root: str) -> list[dict]:
    try:
        with open(log_path(index_root), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def apply_moves(index_root: str, moves: list[Move], approved: set[str]) -> list[dict]:
    """Applies the approved moves. Raises ValueError, moving nothing, when a destination file already exists
    (and its source still does) or two moves share a destination. Returns the log entries of this call."""
    root = Path(index_root)
    chosen = [m for m in moves if m.file_id in approved]
    work, collisions, seen = [], [], set()
    for move in chosen:
        card = find_card_by_file_id(index_root, move.file_id)[1]
        pairs = _files(card, move.from_folder, move.to_folder)
        for src, dst in pairs:
            if (root / src).exists() and ((root / dst).exists() or dst.casefold() in seen):
                collisions.append(dst)
            seen.add(dst.casefold())
        work.append((move, pairs))
    if collisions:
        raise ValueError("destination already exists, nothing was moved: " + ", ".join(sorted(collisions)))
    log = _read_log(index_root)
    entries = []
    for move, pairs in work:
        done = []
        for src, dst in pairs:
            if (root / src).exists():
                (root / dst).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root / src), str(root / dst))
                done.append([src, dst])
            elif (root / dst).exists():
                done.append([src, dst])  # moved by an interrupted earlier run: undo must still restore it
        _relocate(index_root, move.file_id, dict(pairs))
        entry = {"file_id": move.file_id, "from": move.from_folder, "to": move.to_folder, "files": done,
                 "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        entries.append(entry)
        log.append(entry)
        atomic_write_json(log_path(index_root), log)
    return entries


def undo_moves(index_root: str, entries: list[dict]) -> None:
    """Reverses logged moves, newest first, then drops them from the log so a later undo cannot replay them.
    Raises ValueError, moving nothing, when an original location is occupied by another file or the card no longer
    lives where the log says it moved it (the entry is stale)."""
    root = Path(index_root)
    problems = []
    for entry in entries:
        card = (find_card_by_file_id(index_root, entry["file_id"]) or (None, None))[1]
        dsts = {dst for _, dst in entry["files"]}
        if card is None or card.get("path") not in dsts:
            problems.append(f"{entry['file_id']}: the card is no longer at the logged destination (stale entry)")
            continue
        for src, dst in entry["files"]:
            if (root / dst).exists() and (root / src).exists():
                problems.append(f"{entry['file_id']}: {src} is occupied by another file")
    if problems:
        raise ValueError("undo refused, nothing was moved: " + "; ".join(problems))
    for entry in reversed(entries):
        for src, dst in reversed(entry["files"]):
            if (root / dst).exists():
                (root / src).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root / dst), str(root / src))
        _relocate(index_root, entry["file_id"], {dst: src for src, dst in entry["files"]})
    undone = {(e["file_id"], e["at"]) for e in entries}
    atomic_write_json(log_path(index_root), [e for e in _read_log(index_root) if (e["file_id"], e["at"]) not in undone])
