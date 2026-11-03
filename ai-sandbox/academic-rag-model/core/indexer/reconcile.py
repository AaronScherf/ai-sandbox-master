"""Reconcile engine, read-only core (hub-path-resilience P3).

`reconcile(hub_root)` compares the index cards with a snapshot of the hub tree and classifies every
card whose `path` no longer leads to its file. It is PURE READ: it never writes cards, notes or the
tree and never builds a model client. Applying a `moved` difference is `apply_repairs`' job (Task 4);
`ambiguous`/`orphan` become review items (Task 5).

Spec: docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md, sections 1 and 4.

Identity tier per card (decided from the card's own fields and the extension of its `path`):

| Card                                         | Tier      | Exact match on a tree file                  | Candidate basis |
|----------------------------------------------|-----------|---------------------------------------------|-----------------|
| has `hub_id` (authored note, clone)          | hub_id    | `read_hub_id(file) == card.hub_id`; if none | `hub_id`        |
|                                              |           | found, falls back to the content tier       |                 |
| `path` ends `.md` / `.excalidraw`, no hub_id | content   | `content_hash_matches(file, content_hash)`  | `byte_hash`     |
|   (derived outputs: transcriptions, .rag.md) |           |   (canonical or legacy hash)                |                 |
| any other `path` (PDFs, binaries)            | byte      | `compute_file_id(file) == card.file_id`     | `byte_hash`     |

`byte_hash` is the basis for both hash tiers: the Candidate basis vocabulary is fixed and both are
exact content hashes; the evidence string says which hash matched.

Rules (spec section 4, strongest first):
- Card path resolves (case-insensitively) -> no difference, unless the file there positively belongs
  to something else (a different `hub_id`, or for the byte tier different bytes); then the exact pass
  runs. Content-tier files are not hashed at their own path: a changed hash there is an in-place edit,
  which is the indexer's staleness check, not a location problem.
- Exact candidates (hub_id / hash) among files no card claims: one -> `moved`, several -> `ambiguous`.
- Only with no exact candidate: a git rename of the card path is a candidate; it is `moved` only if
  the renamed file also passes the tier's exact check, else an `ambiguous` candidate (`git_rename`).
- Filename stem + course + body shingles similarity adds ranked `ambiguous` candidates
  (`similarity`), never `moved`.
- No candidate at all -> `orphan`.

Hashes are computed lazily, once per file, and only for files no card already points at.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from core.env.hub_vocabulary import Vocabulary, load_vocabulary, parse_hub_path
from core.indexer.hub_identity import read_hub_id
from core.indexer.index_card import (
    compute_content_hash,
    compute_file_id,
    compute_legacy_content_hash,
    list_courses,
    load_shard,
)
from core.indexer.reconcile_git import find_repo_roots, git_last_text, git_renames

Basis = Literal["hub_id", "byte_hash", "git_rename", "similarity"]
_BASIS_RANK = {"hub_id": 0, "byte_hash": 0, "git_rename": 1, "similarity": 2}
_HINT_FIELDS = ("path", "source_pdf_path", "source_asset_path", "rag_md_path")
_TEXT_EXTS = (".md", ".excalidraw")
_SUB_SUFFIXES = (".excalidraw", ".rag", ".questions")

SIMILARITY_THRESHOLD = 0.5
MAX_SIMILARITY_CANDIDATES = 5
_W_STEM, _W_COURSE, _W_BODY = 0.6, 0.15, 0.25


@dataclass(frozen=True)
class FileEntry:
    path: str  # hub-relative, `/`-separated, spelled as on disk
    size: int
    mtime: float


@dataclass
class Candidate:
    path: str
    basis: Basis
    score: float


@dataclass
class Difference:
    kind: Literal["moved", "orphan", "ambiguous"]
    file_id: str
    old_path: str
    candidates: list[Candidate] = field(default_factory=list)
    evidence: str = ""


def _key(rel: str) -> str:
    return rel.replace("\\", "/").casefold()


def snapshot(hub_root: str) -> dict[str, FileEntry]:
    """Every regular file under the hub, keyed by casefolded hub-relative path.

    Dot-directories (.index, .git, .obsidian, .trash) and dotfiles are skipped, as are symlinks.
    No file is opened. On a case-sensitive filesystem two names differing only in case collide on
    one key; the later one (sorted order) wins.
    """
    entries: dict[str, FileEntry] = {}
    for dirpath, dirnames, filenames in os.walk(hub_root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, hub_root).replace(os.sep, "/")
            entries[_key(rel)] = FileEntry(rel, st.st_size, st.st_mtime)
    return entries


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].casefold()


def _tier(card: dict) -> str:
    if card.get("hub_id"):
        return "hub_id"
    return "content" if _ext(card["path"]) in _TEXT_EXTS else "byte"


def _stem(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    changed = True
    while changed:
        changed = False
        for suffix in _SUB_SUFFIXES:
            if stem.casefold().endswith(suffix):
                stem, changed = stem[: -len(suffix)], True
    return stem.casefold()


def _body(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0].lstrip("﻿").rstrip("\r") == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip("\r") == "---":
                return "\n".join(lines[i + 1:])
    return text


def _shingles(text: str, k: int = 3) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", _body(text).casefold())
    if len(words) < k:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + k]) for i in range(len(words) - k + 1)}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


class _Matcher:
    """Lazy, cached evidence over the files no card claims."""

    def __init__(self, hub_root: str, snap: dict[str, FileEntry], claimed: set[str], vocab: Vocabulary):
        self.hub_root = hub_root
        self.snap = snap
        self.vocab = vocab
        self.unclaimed = [e for k, e in snap.items() if k not in claimed]
        self._hashes: dict[str, tuple[str, str] | None] = {}
        self._file_ids: dict[str, str | None] = {}
        self._hub_ids: dict[str, list[FileEntry]] | None = None
        self._renames: dict[str, str] | None = None
        self._repos: list[str] | None = None
        self._shingles: dict[str, set] = {}

    def abspath(self, entry: FileEntry) -> str:
        return os.path.join(self.hub_root, *entry.path.split("/"))

    # --- exact evidence ---------------------------------------------------------------------------
    def hashes(self, entry: FileEntry) -> tuple[str, str] | None:
        if entry.path not in self._hashes:
            try:
                path = self.abspath(entry)
                self._hashes[entry.path] = (compute_content_hash(path), compute_legacy_content_hash(path))
            except OSError:
                self._hashes[entry.path] = None
        return self._hashes[entry.path]

    def file_id(self, entry: FileEntry) -> str | None:
        if entry.path not in self._file_ids:
            try:
                self._file_ids[entry.path] = compute_file_id(self.abspath(entry))
            except OSError:
                self._file_ids[entry.path] = None
        return self._file_ids[entry.path]

    def hub_id_of(self, entry: FileEntry) -> str | None:
        if _ext(entry.path) not in _TEXT_EXTS:
            return None
        try:
            return read_hub_id(self.abspath(entry))
        except OSError:
            return None

    def by_hub_id(self, hub_id: str) -> list[FileEntry]:
        if self._hub_ids is None:
            self._hub_ids = {}
            for entry in self.unclaimed:
                found = self.hub_id_of(entry)
                if found:
                    self._hub_ids.setdefault(found, []).append(entry)
        return self._hub_ids.get(hub_id, [])

    def is_exact(self, card: dict, entry: FileEntry, tier: str) -> str | None:
        """The exact-match evidence label if `entry` is this card's file, else None."""
        if tier == "hub_id" and self.hub_id_of(entry) == card["hub_id"]:
            return "hub_id"
        if tier in ("hub_id", "content") and card.get("content_hash") and _ext(entry.path) == _ext(card["path"]):
            hashes = self.hashes(entry)
            if hashes and card["content_hash"] in hashes:
                return "canonical content hash"
        if tier == "byte" and card.get("file_id") and _ext(entry.path) == _ext(card["path"]):
            if self.file_id(entry) == card["file_id"]:
                return "byte hash"
        return None

    def exact(self, card: dict, tier: str) -> tuple[list[Candidate], str]:
        if tier == "hub_id":
            hits = self.by_hub_id(card["hub_id"])
            if hits:
                return [Candidate(e.path, "hub_id", 1.0) for e in hits], "hub_id"
        same_ext = [e for e in self.unclaimed if _ext(e.path) == _ext(card["path"])]
        if tier in ("hub_id", "content"):
            if not card.get("content_hash"):
                return [], ""
            hits = [e for e in same_ext if (h := self.hashes(e)) and card["content_hash"] in h]
            return [Candidate(e.path, "byte_hash", 1.0) for e in hits], "canonical content hash"
        if not card.get("file_id"):
            return [], ""
        hits = [e for e in same_ext if self.file_id(e) == card["file_id"]]
        return [Candidate(e.path, "byte_hash", 1.0) for e in hits], "byte hash"

    # --- git evidence -----------------------------------------------------------------------------
    def repos(self) -> list[tuple[str, str]]:
        """(repo dir, its hub-relative prefix with trailing `/` or ''), deepest first."""
        if self._repos is None:
            self._repos = find_repo_roots(self.hub_root)
        out = []
        for repo in self._repos:
            rel = os.path.relpath(repo, self.hub_root).replace(os.sep, "/")
            out.append((repo, "" if rel == "." else rel + "/"))
        return sorted(out, key=lambda r: -len(r[1]))

    def git_target(self, old_path: str) -> FileEntry | None:
        if self._renames is None:
            self._renames = {}
            for repo, prefix in reversed(self.repos()):  # deeper repos override the outer one
                for old, new in git_renames(repo).items():
                    self._renames[_key(prefix + old)] = prefix + new
        new = self._renames.get(_key(old_path))
        return self.snap.get(_key(new)) if new else None

    def old_text(self, old_path: str) -> str | None:
        for repo, prefix in self.repos():
            if old_path.casefold().startswith(prefix.casefold()):
                return git_last_text(repo, old_path[len(prefix):])
        return None

    # --- similarity -------------------------------------------------------------------------------
    def shingles_of(self, entry: FileEntry) -> set:
        if entry.path not in self._shingles:
            try:
                with open(self.abspath(entry), encoding="utf-8", errors="replace") as f:
                    self._shingles[entry.path] = _shingles(f.read())
            except OSError:
                self._shingles[entry.path] = set()
        return self._shingles[entry.path]

    def course_of(self, path: str) -> str | None:
        parsed = parse_hub_path(path, self.vocab)
        return parsed.course if parsed else None

    def similar(self, card: dict, exclude: set[str]) -> list[Candidate]:
        old = card["path"]
        course = card.get("course") or self.course_of(old)
        stem = _stem(old)
        old_shingles: set = set()
        if _ext(old) in _TEXT_EXTS:
            text = self.old_text(old)
            old_shingles = _shingles(text) if text else set()
        out = []
        for entry in self.unclaimed:
            if _ext(entry.path) != _ext(old) or entry.path in exclude:
                continue
            stem_score = SequenceMatcher(None, stem, _stem(entry.path)).ratio()
            course_score = 1.0 if course and self.course_of(entry.path) == course else 0.0
            if old_shingles:
                score = (_W_STEM * stem_score + _W_COURSE * course_score
                         + _W_BODY * _jaccard(old_shingles, self.shingles_of(entry)))
            else:
                score = (_W_STEM * stem_score + _W_COURSE * course_score) / (_W_STEM + _W_COURSE)
            if score >= SIMILARITY_THRESHOLD:
                out.append(Candidate(entry.path, "similarity", round(score, 4)))
        out.sort(key=lambda c: (-c.score, c.path))
        return out[:MAX_SIMILARITY_CANDIDATES]


def _ranked(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=lambda c: (_BASIS_RANK[c.basis], -c.score, c.path))


def _all_cards(hub_root: str) -> list[dict]:
    return [card for course in list_courses(hub_root) for card in load_shard(hub_root, course)]


def _vocabulary(hub_root: str) -> Vocabulary:
    config = Path(hub_root) / "hub_config.json"
    return load_vocabulary(config if config.is_file() else None)


def _from_exact(card: dict, old: str, candidates: list[Candidate], label: str, why: str) -> Difference:
    if len(candidates) == 1:
        return Difference("moved", card["file_id"], old, candidates,
                          f"{why}; single exact match by {label}")
    return Difference("ambiguous", card["file_id"], old, _ranked(candidates),
                      f"{why}; {len(candidates)} files match by {label}, none chosen")


def reconcile(hub_root: str) -> list[Difference]:
    """Classify every card whose `path` no longer leads to its file. Pure read."""
    snap = snapshot(hub_root)
    cards = [c for c in _all_cards(hub_root) if c.get("path") and c.get("file_id")]
    claimed = {_key(c[f]) for c in cards for f in _HINT_FIELDS
               if isinstance(c.get(f), str) and _key(c[f]) in snap}
    matcher = _Matcher(hub_root, snap, claimed, _vocabulary(hub_root))
    differences: list[Difference] = []
    for card in cards:
        card = dict(card, path=card["path"].replace("\\", "/"))
        old, tier = card["path"], _tier(card)
        here = snap.get(_key(old))
        if here is not None:
            if tier == "hub_id":
                found = matcher.hub_id_of(here)
                if found is None or found == card["hub_id"]:
                    continue
                why = f"file at card path has hub_id {found}, not {card['hub_id']}"
            elif tier == "byte":
                if matcher.file_id(here) == card["file_id"]:
                    continue
                why = "file at card path has different bytes"
            else:
                continue
            exact, label = matcher.exact(card, tier)
            if exact:
                differences.append(_from_exact(card, old, exact, label, why))
            elif tier == "hub_id":
                differences.append(Difference("orphan", card["file_id"], old, [],
                                              f"{why}; no other file carries the card's hub_id or hash"))
            continue

        why = "card path does not exist"
        exact, label = matcher.exact(card, tier)
        if exact:
            differences.append(_from_exact(card, old, exact, label, why))
            continue
        candidates: list[Candidate] = []
        target = matcher.git_target(old)
        if target is not None and _key(target.path) not in claimed:
            proof = matcher.is_exact(card, target, tier)
            if proof:
                differences.append(Difference("moved", card["file_id"], old,
                                              [Candidate(target.path, "git_rename", 1.0)],
                                              f"{why}; git rename confirmed by {proof}"))
                continue
            candidates.append(Candidate(target.path, "git_rename", 1.0))
        candidates += matcher.similar(card, {c.path for c in candidates})
        if candidates:
            bases = sorted({c.basis for c in candidates})
            differences.append(Difference("ambiguous", card["file_id"], old, _ranked(candidates),
                                          f"{why}; no exact match; candidates by {', '.join(bases)}"))
        else:
            differences.append(Difference("orphan", card["file_id"], old, [],
                                          f"{why}; no hub_id, hash, git rename or similar file found"))
    return differences
