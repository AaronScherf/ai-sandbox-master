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


@dataclass(frozen=True)
class Vocabulary:
    names: Mapping[str, str] = field(default_factory=dict)  # casefolded folder name -> kind
    textbook_folders: tuple[str, ...] = _DEFAULT_TEXTBOOK_FOLDERS
    group_patterns: tuple[str, ...] = _DEFAULT_GROUP_PATTERNS

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
    for pattern in patterns:
        re.compile(pattern)
    return Vocabulary(names=names, textbook_folders=textbooks, group_patterns=patterns)


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
