"""
hub_vocabulary.py
The folder-name vocabulary of the academic hub: which names are categories,
which are group layers, which are plain sub-structure to ignore. It lives in
one config file (`academic-hub/hub_config.json`), not in code. A missing or
malformed config degrades to LEGACY_VOCABULARY (the pre-vocabulary behavior)
with a warning; it never raises into a pipeline. Pure: no network, no writes.
See docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

log = logging.getLogger(__name__)

KINDS = ("category", "group", "ignore")
_DEFAULT_TEXTBOOK_FOLDERS = ("textbooks", "textbooks-and-papers")
_DEFAULT_GROUP_PATTERNS = (r"^part_\d+$",)
_DEFAULT_PART_PATTERN = r"^part_\d+$"


@dataclass(frozen=True)
class Vocabulary:
    names: Mapping[str, str] = field(default_factory=dict)  # casefolded folder name -> kind
    textbook_folders: tuple[str, ...] = _DEFAULT_TEXTBOOK_FOLDERS
    group_patterns: tuple[str, ...] = _DEFAULT_GROUP_PATTERNS
    # `part_N` is a pipeline concept (--part, course_output_dir), narrower than a group layer.
    part_pattern: str = _DEFAULT_PART_PATTERN

    def kind_of(self, name: str) -> str | None:
        return self.names.get(name.casefold())


LEGACY_VOCABULARY = Vocabulary()


def default_config_path() -> Path:
    override = os.environ.get("ACADEMIC_HUB_CONFIG")
    if override:
        return Path(override)
    # core/env/hub_vocabulary.py -> academic-rag-model -> ai-sandbox
    return Path(__file__).resolve().parents[3] / "academic-hub" / "hub_config.json"


_CACHE: dict[Path, tuple[float, Vocabulary]] = {}


def _parse(data: object) -> Vocabulary:
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    names: dict[str, str] = {}
    for name, entry in (data.get("names") or {}).items():
        kind = entry.get("kind") if isinstance(entry, dict) else None
        if kind not in KINDS:
            raise ValueError(f"name {name!r} has unknown kind {kind!r}")
        names[name.casefold()] = kind
    textbooks = tuple(str(n).casefold() for n in data.get("textbook_folders", _DEFAULT_TEXTBOOK_FOLDERS))
    patterns = tuple(str(p) for p in data.get("group_patterns", _DEFAULT_GROUP_PATTERNS))
    part_pattern = str(data.get("part_pattern", _DEFAULT_PART_PATTERN))
    for pattern in (*patterns, part_pattern):
        re.compile(pattern)
    return Vocabulary(names=names, textbook_folders=textbooks, group_patterns=patterns, part_pattern=part_pattern)


def load_vocabulary(path: Path | None = None) -> Vocabulary:
    """Load the vocabulary; any problem returns LEGACY_VOCABULARY and logs one warning naming the file."""
    path = Path(path) if path is not None else default_config_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        log.warning("hub vocabulary %s not found; using legacy path rules", path)
        return LEGACY_VOCABULARY
    cached = _CACHE.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        vocab = _parse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, re.error) as exc:  # JSONDecodeError is a ValueError
        log.warning("hub vocabulary %s is invalid (%s); using legacy path rules", path, exc)
        return LEGACY_VOCABULARY
    _CACHE[path] = (mtime, vocab)
    return vocab


# --- path parsing ---------------------------------------------------------------------------------
_NOTES_ROOT_NAME = "academic_notes"
_RESOURCES_ROOT_NAME = "academic_resources"
_LEGACY_PART = re.compile(r"part_\d+")


@dataclass(frozen=True)
class HubPath:
    root: str
    course: str
    groups: tuple[str, ...]
    category: str | None
    source: str  # "vocabulary" or "legacy"


def _legacy_parse(root: str, tail: list[str]) -> HubPath:
    """The position-based parse used before the vocabulary: only a `part_N` folder is a layer."""
    part = tail[1] if _LEGACY_PART.fullmatch(tail[1]) else None
    category_at = 2 if part else 1
    category = tail[category_at] if len(tail) > category_at + 1 else None
    return HubPath(root, tail[0], (part,) if part else (), category, "legacy")


def parse_hub_path(path: str, vocab: Vocabulary | None = None) -> HubPath | None:
    """Split a path below either hub root into course, group layers and category.

    The category is the nearest ancestor folder the vocabulary knows as a category; folders between the
    course and it are group layers. With no known category the legacy positional parse is returned
    unchanged, so nothing moves until the owner confirms a name.
    """
    parts = path.replace("\\", "/").split("/")
    roots = [i for i, name in enumerate(parts) if name in (_NOTES_ROOT_NAME, _RESOURCES_ROOT_NAME)]
    if not roots:
        return None
    root = parts[roots[-1]]
    tail = parts[roots[-1] + 1:]
    if len(tail) < 2:
        return None
    vocab = vocab if vocab is not None else load_vocabulary()
    folders = tail[1:-1]  # directories between the course and the file name
    for i in range(len(folders) - 1, -1, -1):
        if vocab.kind_of(folders[i]) == "category":
            return HubPath(root, tail[0], tuple(folders[:i]), folders[i], "vocabulary")
    return _legacy_parse(root, tail)


def is_group_name(name: str, vocab: Vocabulary | None = None) -> bool:
    """True when the folder name looks like a group layer (part_N, class_2024, 2025_class, ...)."""
    vocab = vocab if vocab is not None else load_vocabulary()
    return vocab.kind_of(name) == "group" or any(re.search(p, name) for p in vocab.group_patterns)


def is_part_name(name: str, vocab: Vocabulary | None = None) -> bool:
    """True when the folder name is a `part_N` folder, the layer pipelines address with --part."""
    vocab = vocab if vocab is not None else load_vocabulary()
    return re.search(vocab.part_pattern, name) is not None
