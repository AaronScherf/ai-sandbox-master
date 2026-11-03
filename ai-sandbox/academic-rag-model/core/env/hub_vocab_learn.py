"""
hub_vocab_learn.py
Learns candidate vocabulary entries from the folder tree. It only proposes:
nothing is classified until the owner confirms a name (tools/hub_vocabulary.py).

Rule (owner-approved, 2026-11-03): a folder name is a category candidate when it
directly holds content files in at least two courses; numbered, year-shaped or
part_N-shaped names, and names that sit above a known category folder, are group
candidates; everything else seen in one course is left unclassified. Names that
look like infrastructure (summaries, images, ...) are listed as ignore candidates
rather than categories. Read-only, no network.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from core.env.hub_vocabulary import Vocabulary

CONTENT_EXTENSIONS = (".md", ".pdf", ".svg", ".png", ".jpg", ".jpeg")
ROOTS = ("academic_notes", "academic_resources")
INFRASTRUCTURE_HINTS = frozenset({"processed_outputs", "images", "assets", "chapters", "summaries", "previous", "solutions"})
_GROUP_SHAPES = (
    re.compile(r"^\d+$"),
    re.compile(r"(^|_)(19|20)\d{2}(_|$)"),
    re.compile(r"^(19|20)\d{2}-\d{2}"),
)


def _group_shaped(name: str, vocab: Vocabulary) -> bool:
    return any(p.search(name) for p in _GROUP_SHAPES) or any(re.search(p, name) for p in vocab.group_patterns)


def propose_vocabulary(hub_root: Path, vocab: Vocabulary) -> dict:
    hub_root = Path(hub_root)
    direct: dict[str, set[str]] = defaultdict(set)  # folder name -> courses where it directly holds content
    above_category: set[str] = set()
    for root_name in ROOTS:
        root = hub_root / root_name
        if not root.is_dir():
            continue
        for course in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
            for dirpath, dirnames, filenames in os.walk(course):
                dirnames[:] = sorted(
                    d for d in dirnames
                    if not d.startswith(".") and d.casefold() not in vocab.textbook_folders and vocab.kind_of(d) != "ignore"
                )
                name = os.path.basename(dirpath)
                if any(vocab.kind_of(d) == "category" for d in dirnames) and dirpath != str(course):
                    above_category.add(name)
                if dirpath != str(course) and any(f.lower().endswith(CONTENT_EXTENSIONS) and not f.startswith(".")
                                                  for f in filenames):
                    direct[name].add(course.name)
    result = {"category_candidates": [], "group_candidates": [], "ignore_candidates": [], "unclassified": []}
    names = set(direct) | above_category
    for name in sorted(names, key=str.casefold):
        if vocab.kind_of(name) is not None:
            continue
        courses = sorted(direct.get(name, ()))
        item = {"name": name, "courses": courses}
        if name.casefold() in INFRASTRUCTURE_HINTS:
            if courses:
                result["ignore_candidates"].append(item)
        elif name in above_category or _group_shaped(name, vocab):
            result["group_candidates"].append(item)
        elif len(courses) >= 2:
            result["category_candidates"].append(item)
        elif courses:
            result["unclassified"].append(item)
    return result
