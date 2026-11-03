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
  A hub_id-tier card's content-hash fallback is decisive only for files with no hub_id; a file that
  matches by content but carries a different hub_id (a clone) is an `ambiguous` candidate only.
- A content-tier card's hash match onto a file carrying another card's hub_id is not decisive: the
  hub_id proof belongs to that card.
- After all cards are classified, a `moved` whose target is also a decisive exact candidate of another
  card becomes `ambiguous`: two cards never both move onto one file. Non-decisive candidates never
  veto a proven move.
- Path lookup is case-insensitive (per-character lowercase, not str.casefold); when several on-disk
  names share a key, only the exact spelling resolves.
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


_COLLISION = "\0"


def _key(rel: str) -> str:
    """Case-insensitive lookup key. Per-character simple lowercase, length-preserving, closer to NTFS
    than str.casefold (which maps "ß" to "ss" and so would equate names NTFS keeps distinct)."""
    out = []
    for ch in rel.replace("\\", "/"):
        low = ch.lower()
        out.append(low if len(low) == 1 else ch)
    return "".join(out)


def _lookup(snap: dict[str, FileEntry], rel: str) -> FileEntry | None:
    """The file a hub-relative path resolves to: its case-insensitive key, or, when several on-disk
    names share that key (case-sensitive filesystem), only the exact spelling. Never a guess."""
    key = _key(rel)
    entry = snap.get(key)
    if entry is not None:
        return entry
    return snap.get(key + _COLLISION + rel.replace("\\", "/"))


def snapshot(hub_root: str) -> dict[str, FileEntry]:
    """Every regular file under the hub, keyed by case-insensitive hub-relative path (`_key`).

    Dot-directories (.index, .git, .obsidian, .trash) and dotfiles are skipped, as are symlinks.
    No file is opened. When two on-disk names share a key (a case-sensitive filesystem), neither
    keeps the plain key: both are stored under `key + "\\0" + exact spelling`, so `_lookup` resolves
    them only by exact spelling.
    """
    entries: dict[str, FileEntry] = {}
    collided: set[str] = set()
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
            entry, key = FileEntry(rel, st.st_size, st.st_mtime), _key(rel)
            if key in collided:
                entries[key + _COLLISION + rel] = entry
            elif key in entries:
                first = entries.pop(key)
                collided.add(key)
                entries[key + _COLLISION + first.path] = first
                entries[key + _COLLISION + rel] = entry
            else:
                entries[key] = entry
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

    def __init__(self, hub_root: str, snap: dict[str, FileEntry], claimed: set[str], vocab: Vocabulary,
                 card_hub_ids: frozenset[str] = frozenset()):
        self.hub_root = hub_root
        self.card_hub_ids = card_hub_ids
        self.snap = snap
        self.vocab = vocab
        self.unclaimed = [e for e in snap.values() if e.path not in claimed]
        self._hashes: dict[str, tuple[str, str] | None] = {}
        self._file_ids: dict[str, str | None] = {}
        self._hub_ids: dict[str, list[FileEntry]] | None = None
        self._renames: dict[str, str] | None = None
        self._repos: list[tuple[str, str]] | None = None
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
        index = self._hub_ids
        if index is None:
            index = {}
            for entry in self.unclaimed:
                found = self.hub_id_of(entry)
                if found:
                    index.setdefault(found, []).append(entry)
            self._hub_ids = index
        return index.get(hub_id, [])

    def is_exact(self, card: dict, entry: FileEntry, tier: str) -> str | None:
        """The exact-match evidence label if `entry` is this card's file, else None.

        A hub_id-tier card falls back to its content hash only for a file that carries no hub_id
        (the id was lost); a file with a different hub_id is a different note, whatever its body."""
        if tier == "hub_id":
            found = self.hub_id_of(entry)
            if found == card["hub_id"]:
                return "hub_id"
            if found is not None:
                return None
        if tier == "content" and self.hub_id_of(entry) in self.card_hub_ids:
            return None
        if tier in ("hub_id", "content") and card.get("content_hash") and _ext(entry.path) == _ext(card["path"]):
            hashes = self.hashes(entry)
            if hashes and card["content_hash"] in hashes:
                return "canonical content hash"
        if tier == "byte" and card.get("file_id") and _ext(entry.path) == _ext(card["path"]):
            if self.file_id(entry) == card["file_id"]:
                return "byte hash"
        return None

    def exact(self, card: dict, tier: str) -> tuple[list[Candidate], str, bool]:
        """(candidates, evidence label, decisive). Only a decisive single candidate may become `moved`.

        For a hub_id-tier card with no file carrying its id, files that match by content hash but
        carry a different hub_id are returned as non-decisive candidates: they surface for review
        (a clone or a re-stamped copy) but never resolve the card on their own."""
        if tier == "hub_id":
            hits = self.by_hub_id(card["hub_id"])
            if hits:
                return [Candidate(e.path, "hub_id", 1.0) for e in hits], "hub_id", True
        same_ext = [e for e in self.unclaimed if _ext(e.path) == _ext(card["path"])]
        if tier in ("hub_id", "content"):
            if not card.get("content_hash"):
                return [], "", True
            hits = [e for e in same_ext if (h := self.hashes(e)) and card["content_hash"] in h]
            candidates = [Candidate(e.path, "byte_hash", 1.0) for e in hits]
            if tier == "hub_id":
                foreign = [e for e in hits if self.hub_id_of(e) is not None]
                if foreign:
                    return (candidates, f"canonical content hash ({len(foreign)} of them carry a different "
                            f"hub_id, so none is decisive)", False)
            else:
                owned = [e for e in hits if self.hub_id_of(e) in self.card_hub_ids]
                if owned:
                    return (candidates, f"canonical content hash ({len(owned)} of them carry the hub_id of "
                            f"another card, so none is decisive)", False)
            return candidates, "canonical content hash", True
        if not card.get("file_id"):
            return [], "", True
        hits = [e for e in same_ext if self.file_id(e) == card["file_id"]]
        return [Candidate(e.path, "byte_hash", 1.0) for e in hits], "byte hash", True

    # --- git evidence -----------------------------------------------------------------------------
    def repos(self) -> list[tuple[str, str]]:
        """(repo dir, its hub-relative prefix with trailing `/` or ''), deepest first."""
        repos = self._repos
        if repos is None:
            repos = []
            for repo in find_repo_roots(self.hub_root):
                rel = os.path.relpath(repo, self.hub_root).replace(os.sep, "/")
                repos.append((repo, "" if rel == "." else rel + "/"))
            repos.sort(key=lambda r: -len(r[1]))
            self._repos = repos
        return repos

    def git_target(self, old_path: str) -> FileEntry | None:
        renames = self._renames
        if renames is None:
            renames = {}
            for repo, prefix in reversed(self.repos()):  # deeper repos override the outer one
                for old, new in git_renames(repo).items():
                    renames[_key(prefix + old)] = prefix + new
            self._renames = renames
        new = renames.get(_key(old_path))
        return _lookup(self.snap, new) if new else None

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


def _from_exact(card: dict, old: str, candidates: list[Candidate], label: str, decisive: bool,
                why: str) -> Difference:
    if len(candidates) == 1 and decisive:
        return Difference("moved", card["file_id"], old, candidates,
                          f"{why}; single exact match by {label}")
    return Difference("ambiguous", card["file_id"], old, _ranked(candidates),
                      f"{why}; {len(candidates)} file(s) match by {label}, none chosen")


def _demote_contested(differences: list[Difference], decisive: list[bool]) -> None:
    """A `moved` whose target is also a decisive exact candidate of another difference becomes
    `ambiguous`: several cards have proof for one file, and choosing would be a silent guess.

    Only decisive evidence counts as a claim (a `moved`, or several decisive exact matches); a
    non-decisive candidate (a clone carrying another hub_id, an unproven git rename, a similarity
    hint) never vetoes another card's proven move. Computed over all differences, so card order
    does not matter."""
    claims: dict[str, int] = {}
    for d, strong in zip(differences, decisive):
        if not strong:
            continue
        for key in {_key(c.path) for c in d.candidates if c.basis != "similarity"}:
            claims[key] = claims.get(key, 0) + 1
    for d in differences:
        if d.kind == "moved" and claims.get(_key(d.candidates[0].path), 0) > 1:
            d.kind = "ambiguous"
            d.evidence += f"; several cards compete for the same target {d.candidates[0].path}, none chosen"


def reconcile(hub_root: str) -> list[Difference]:
    """Classify every card whose `path` no longer leads to its file. Pure read."""
    snap = snapshot(hub_root)
    cards = [c for c in _all_cards(hub_root) if c.get("path") and c.get("file_id")]
    claimed = {entry.path for c in cards for f in _HINT_FIELDS
               if isinstance(c.get(f), str) and (entry := _lookup(snap, c[f])) is not None}
    card_hub_ids = frozenset(c["hub_id"] for c in cards if isinstance(c.get("hub_id"), str) and c["hub_id"])
    matcher = _Matcher(hub_root, snap, claimed, _vocabulary(hub_root), card_hub_ids)
    differences: list[Difference] = []
    decisive: list[bool] = []  # parallel to differences: does this one carry proof for its candidates
    for card in cards:
        card = dict(card, path=card["path"].replace("\\", "/"))
        old, tier = card["path"], _tier(card)
        here = _lookup(snap, old)
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
            exact, label, strong = matcher.exact(card, tier)
            if exact:
                differences.append(_from_exact(card, old, exact, label, strong, why))
                decisive.append(strong)
            elif tier == "hub_id":
                differences.append(Difference("orphan", card["file_id"], old, [],
                                              f"{why}; no other file carries the card's hub_id or hash"))
                decisive.append(False)
            continue

        why = "card path does not exist"
        exact, label, strong = matcher.exact(card, tier)
        if exact:
            differences.append(_from_exact(card, old, exact, label, strong, why))
            decisive.append(strong)
            continue
        candidates: list[Candidate] = []
        target = matcher.git_target(old)
        if target is not None and target.path not in claimed:
            proof = matcher.is_exact(card, target, tier)
            if proof:
                differences.append(Difference("moved", card["file_id"], old,
                                              [Candidate(target.path, "git_rename", 1.0)],
                                              f"{why}; git rename confirmed by {proof}"))
                decisive.append(True)
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
        decisive.append(False)
    _demote_contested(differences, decisive)
    return differences
